# Hugging Face Model Serving Infrastructure

This repository contains a complete, automated model-serving deployment for a FastAPI application that loads Hugging Face text-generation models on demand.

## Structure

```text
iac/        Terraform, Helm chart, Kind config, and monitoring assets
serving/    FastAPI serving application and Dockerfile
tests/      Unit tests for public API behavior
README.md   Deployment, testing, and design documentation
```

## Design

The solution is Kubernetes based so the same deployment definitions can run locally on Kind/Minikube or against a cloud Kubernetes cluster such as EKS.

Key components:

- **Serving app**: FastAPI service with `/model`, `/status`, `/completion`, `/metrics`, and `/model` read endpoints.
- **Model lifecycle**: `POST /model` accepts a Hugging Face `model_id`, moves status to `PENDING`, loads the model in a background task, then sets `RUNNING`. If loading fails, the app clears the model and reverts to `NOT_DEPLOYED`.
- **Inference API**: `POST /completion` returns assistant text from the currently loaded model, or `503` when no model is serving.
- **Metrics**: Prometheus scrapes `/metrics`, including request metrics from `starlette-exporter` and `completion_requests_total` split by success/error.
- **Logs**: Request/response access logs are written to stdout. Promtail ships pod logs to Loki.
- **Dashboard**: Grafana dashboard shows infrastructure health, completion request throughput, p95 latency, and request/response logs.
- **CI/CD**: GitHub Actions runs unit tests and Docker build first, validates Terraform, publishes the image, then applies Terraform. Deployments are gated by successful tests and validation.

## Local deployment with Kind

Prerequisites:

- Docker
- Kind
- kubectl
- Terraform >= 1.5
- Helm, used by Terraform through the Helm provider

Create a one-node local cluster:

```bash
kind create cluster --config iac/kind-config.yaml
```

Build and load the serving image into Kind:

```bash
docker build -t ml-serving:local ./serving
kind load docker-image ml-serving:local --name ml-serving
```

Deploy infrastructure, monitoring, and the application:

```bash
cd iac
terraform init
terraform apply -auto-approve -var="kube_context=kind-ml-serving"
```

Open the application:

```bash
curl http://localhost/status
curl -X POST http://localhost/model \
  -H "Content-Type: application/json" \
  -d '{"model_id":"sshleifer/tiny-gpt2"}'
curl http://localhost/model
curl -X POST http://localhost/completion \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

Open Grafana:

```bash
kubectl -n monitoring port-forward svc/kube-prom-stack-grafana 3000:80
```

Then browse to `http://localhost:3000` and log in with `admin` / `admin`. Open the `ML Serving Overview` dashboard.

## Cloud deployment through GitHub Actions

The workflow in `.github/workflows/ci-cd.yaml` expects an existing EKS cluster and ECR repository. Add these repository secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_ACCOUNT_ID
ECR_REPOSITORY
EKS_CLUSTER_NAME
```

On pull requests, CI runs tests, Docker build, and Terraform validation. On pushes to `main`, the pipeline pushes the Docker image to ECR and runs `terraform apply` to deploy ingress, monitoring, Loki/Promtail, the Grafana dashboard, and the serving application.

## API

### Deploy model

```http
POST /model
Content-Type: application/json

{"model_id":"sshleifer/tiny-gpt2"}
```

Success:

```json
{"status":"success","model_id":"sshleifer/tiny-gpt2"}
```

### Get status

```http
GET /status
```

```json
{"status":"NOT_DEPLOYED"}
```

Valid statuses are `NOT_DEPLOYED`, `PENDING`, `DEPLOYING`, and `RUNNING`.

### Get model

```http
GET /model
```

```json
{"model_id":"sshleifer/tiny-gpt2"}
```

### Completion

```http
POST /completion
Content-Type: application/json

{"messages":[{"role":"user","content":"message"}]}
```

Success:

```json
{"status":"success","response":[{"role":"assistant","message":"response"}]}
```

Error:

```json
{"status":"error","message":"error message"}
```

When no model is deployed, `/completion` returns HTTP `503` with `Model not deployed`.

## Tests

Install test dependencies and run unit tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

The tests mock the Hugging Face pipeline so they do not download models or require network access.

## Resource target

The Helm chart deploys a single serving replica with limits of `6` CPU and `12Gi` memory, matching the required one-node p99 envelope. The Kind configuration uses one node; make sure Docker Desktop or your local container runtime is configured with enough CPU and memory for model loading.
