import pytest
from fastapi.testclient import TestClient

import serving.main as serving_app

client = TestClient(serving_app.app)


@pytest.fixture(autouse=True)
def reset_app_state():
    serving_app.deployment_status = "NOT_DEPLOYED"
    serving_app.current_model_id = None
    serving_app.model_pipeline = None
    yield
    serving_app.deployment_status = "NOT_DEPLOYED"
    serving_app.current_model_id = None
    serving_app.model_pipeline = None


def test_status_initial():
    res = client.get("/status")

    assert res.status_code == 200
    assert res.json() == {"status": "NOT_DEPLOYED"}


def test_get_model_initial():
    res = client.get("/model")

    assert res.status_code == 200
    assert res.json() == {"model_id": None}


def test_model_deploy_success(monkeypatch):
    def fake_pipeline(model_id):
        assert model_id == "sshleifer/tiny-gpt2"
        return lambda text: [{"generated_text": f"reply to {text}"}]

    monkeypatch.setattr(serving_app, "create_pipeline", fake_pipeline)

    res = client.post("/model", json={"model_id": "sshleifer/tiny-gpt2"})

    assert res.status_code == 200
    assert res.json() == {"status": "success", "model_id": "sshleifer/tiny-gpt2"}
    assert client.get("/status").json() == {"status": "RUNNING"}
    assert client.get("/model").json() == {"model_id": "sshleifer/tiny-gpt2"}


def test_model_deploy_failure_reverts_to_not_deployed(monkeypatch):
    def failing_pipeline(model_id):
        raise RuntimeError("model could not be loaded")

    monkeypatch.setattr(serving_app, "create_pipeline", failing_pipeline)

    res = client.post("/model", json={"model_id": "invalid-model"})

    assert res.status_code == 200
    assert res.json() == {"status": "success", "model_id": "invalid-model"}
    assert client.get("/status").json() == {"status": "NOT_DEPLOYED"}
    assert client.get("/model").json() == {"model_id": None}


def test_empty_model_id_is_rejected():
    res = client.post("/model", json={"model_id": "   "})

    assert res.status_code == 200
    assert res.json()["status"] == "error"
    assert client.get("/status").json() == {"status": "NOT_DEPLOYED"}


def test_completion_requires_running_model():
    res = client.post(
        "/completion",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert res.status_code == 503
    assert res.json()["detail"] == "Model not deployed"


def test_completion_success(monkeypatch):
    monkeypatch.setattr(
        serving_app,
        "create_pipeline",
        lambda model_id: lambda text: [{"generated_text": "Hello from the model"}],
    )
    client.post("/model", json={"model_id": "demo-model"})

    res = client.post(
        "/completion",
        json={"messages": [{"role": "user", "content": "Hello"}]},
    )

    assert res.status_code == 200
    assert res.json() == {
        "status": "success",
        "response": [{"role": "assistant", "message": "Hello from the model"}],
    }


def test_metrics_endpoint_exposes_request_counter(monkeypatch):
    monkeypatch.setattr(
        serving_app,
        "create_pipeline",
        lambda model_id: lambda text: [{"generated_text": "ok"}],
    )
    client.post("/model", json={"model_id": "demo-model"})
    client.post("/completion", json={"messages": [{"role": "user", "content": "Hi"}]})

    res = client.get("/metrics")

    assert res.status_code == 200
    assert "completion_requests_total" in res.text
