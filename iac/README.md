# Infrastructure

Terraform deploys the full runtime stack to the Kubernetes context you select:

- ingress-nginx for HTTP ingress
- kube-prometheus-stack for Prometheus, Grafana, kube-state-metrics, and node-exporter
- Loki and Promtail for request/response log collection
- the `my-webapp` Helm chart for the FastAPI model serving app
- a Grafana dashboard ConfigMap named `ml-serving-dashboard`

For local testing, create the Kind cluster first:

```bash
kind create cluster --config iac/kind-config.yaml
docker build -t ml-serving:local ./serving
kind load docker-image ml-serving:local --name ml-serving
cd iac
terraform init
terraform apply -auto-approve -var="kube_context=kind-ml-serving"
```

For EKS or another cloud cluster, make that cluster the current kubeconfig context and run Terraform with the image pushed to your registry:

```bash
terraform apply -auto-approve \
  -var="image_repository=<registry>/<repo>" \
  -var="image_tag=<tag>" \
  -var="image_pull_policy=Always"
```
