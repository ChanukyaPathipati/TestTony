from time import perf_counter
from typing import Any
import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette_exporter import PrometheusMiddleware, handle_metrics
from prometheus_client import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ml-serving")

app = FastAPI()

app.add_middleware(PrometheusMiddleware)


@app.middleware("http")
async def request_response_logger(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    duration_ms = round((perf_counter() - start) * 1000, 2)
    logger.info(
        "request method=%s path=%s status_code=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/metrics")
async def metrics(request: Request):
    return handle_metrics(request)


completion_requests_total = Counter(
    "completion_requests_total",
    "Number of completion requests processed by the serving application.",
    ["status"],
)

deployment_status = "NOT_DEPLOYED"
current_model_id = None
model_pipeline: Any | None = None


class Message(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    messages: list[Message]


class ModelRequest(BaseModel):
    model_id: str


def create_pipeline(model_id: str):
    from transformers import pipeline

    return pipeline("text-generation", model=model_id)


def _load_model(model_id: str) -> None:
    global deployment_status, current_model_id, model_pipeline

    try:
        deployment_status = "DEPLOYING"
        loaded_pipeline = create_pipeline(model_id)
        model_pipeline = loaded_pipeline
        current_model_id = model_id
        deployment_status = "RUNNING"
        logger.info("model_deployment status=RUNNING model_id=%s", model_id)
    except Exception as exc:
        model_pipeline = None
        current_model_id = None
        deployment_status = "NOT_DEPLOYED"
        logger.exception("model_deployment status=NOT_DEPLOYED model_id=%s error=%s", model_id, exc)


@app.post("/completion")
async def completion(request: CompletionRequest):
    global model_pipeline
    if not model_pipeline:
        completion_requests_total.labels(status="error").inc()
        raise HTTPException(status_code=503, detail="Model not deployed")

    try:
        input_text = request.messages[-1].content
        result = model_pipeline(input_text)[0]["generated_text"]
        completion_requests_total.labels(status="success").inc()
        return {
            "status": "success",
            "response": [{"role": "assistant", "message": result}],
        }
    except Exception as e:
        completion_requests_total.labels(status="error").inc()
        return {"status": "error", "message": str(e)}


@app.get("/status")
async def get_status():
    return {"status": deployment_status}


@app.get("/model")
async def get_model():
    return {"model_id": current_model_id}


@app.post("/model")
async def deploy_model(request: ModelRequest, background_tasks: BackgroundTasks):
    global deployment_status, current_model_id, model_pipeline

    if deployment_status in {"PENDING", "DEPLOYING"}:
        return {"status": "error", "message": "Model deployment already in progress"}

    model_id = request.model_id.strip()
    if not model_id:
        return {"status": "error", "message": "model_id is required"}

    deployment_status = "PENDING"
    current_model_id = model_id
    model_pipeline = None
    logger.info("model_deployment status=PENDING model_id=%s", model_id)
    background_tasks.add_task(_load_model, model_id)
    return {"status": "success", "model_id": model_id}
