import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

os.environ["DAITFO_API_KEY"] = "test-key"
os.environ["ADMIN_API_KEY"] = "admin-key"

from ui.backend import app


client = TestClient(app)

valid_headers = {"X-API-Key": "test-key"}
admin_headers = {"X-API-Key": "admin-key"}

def test_root_no_auth_required():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "DAITFO Backend Online" in data["status"]

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code in (200, 503)

def test_health_structure():
    resp = client.get("/health")
    data = resp.json()
    assert "status" in data
    assert "checks" in data

def test_controller_config_missing_key():
    resp = client.post("/api/controller-config", json={})
    assert resp.status_code == 401


def test_controller_config_user_key_rejected():
    resp = client.post("/api/controller-config", json={}, headers=valid_headers)
    assert resp.status_code == 403

def test_controller_config_admin_key_accepted():
    resp = client.post("/api/controller-config", json={"mode": "auto"}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

def test_controller_config_invalid_mode():
    resp = client.post("/api/controller-config", json={"mode": "invalid"}, headers=admin_headers)
    assert resp.status_code == 422

def test_controller_config_invalid_vps_type():
    resp = client.post("/api/controller-config", json={"vps": "not-a-dict"}, headers=admin_headers)
    assert resp.status_code == 422

def test_controller_config_duration_out_of_range():
    resp = client.post("/api/controller-config", json={"duration": 200}, headers=admin_headers)
    assert resp.status_code == 422

def test_select_phase_missing_key():
    resp = client.post("/api/select-phase", json={"phase": "N"})
    assert resp.status_code == 401


def test_select_phase_user_key_rejected():
    resp = client.post("/api/select-phase", json={"phase": "N"}, headers=valid_headers)
    assert resp.status_code == 403

def test_select_phase_admin_key_accepted():
    resp = client.post("/api/select-phase", json={"phase": "N"}, headers=admin_headers)
    assert resp.status_code == 200
    assert "Phase updated" in resp.json()["status"]

def test_select_phase_invalid_value():
    resp = client.post("/api/select-phase", json={"phase": "INVALID"}, headers=admin_headers)
    assert resp.status_code == 422

def test_select_phase_missing_field():
    resp = client.post("/api/select-phase", json={}, headers=admin_headers)
    assert resp.status_code == 422

def test_emergency_request_missing_key():
    resp = client.post("/api/emergency/request", json={})
    assert resp.status_code == 401


def test_emergency_request_user_key_rejected():
    resp = client.post("/api/emergency/request", json={}, headers=valid_headers)
    assert resp.status_code == 403

def test_emergency_request_admin_key_accepted():
    resp = client.post("/api/emergency/request", json={}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

def test_emergency_clear_no_key():
    resp = client.post("/api/emergency/clear")
    assert resp.status_code == 401


def test_ai_inference_missing_key():
    resp = client.post("/api/ai-inference", json={"phase": "N", "vps": {"N": 10, "S": 10, "E": 10, "W": 10}})
    assert resp.status_code == 401


def test_ai_inference_user_key_accepted():
    payload = {"phase": "N-S", "vps": {"N": 15, "S": 10, "E": 5, "W": 20}}
    resp = client.post("/api/ai-inference", json=payload, headers=valid_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "duration" in data
    assert "reasoning" in data

def test_ai_inference_invalid_phase():
    payload = {"phase": "", "vps": {"N": 10, "S": 10, "E": 10, "W": 10}}
    resp = client.post("/api/ai-inference", json=payload, headers=valid_headers)
    assert resp.status_code == 200

def test_ai_inference_invalid_vps_key():
    payload = {"phase": "N", "vps": {"X": 10, "Y": 10}}
    resp = client.post("/api/ai-inference", json=payload, headers=valid_headers)
    assert resp.status_code == 422

def test_slm_analyze_no_key():
    resp = client.get("/api/slm-analyze")
    assert resp.status_code == 401


def test_slm_analyze_user_key_accepted():
    resp = client.get("/api/slm-analyze?zone=INT_001", headers=valid_headers)
    assert resp.status_code in (200, 500)

def test_slm_status_no_key():
    resp = client.get("/api/slm-status")
    assert resp.status_code == 401


def test_ask_assistant_no_key():
    resp = client.post("/api/ask", json={"query": "test"})
    assert resp.status_code == 401


def test_ask_assistant_user_key_accepted():
    resp = client.post("/api/ask", json={"query": "test query"}, headers=valid_headers)
    assert resp.status_code == 200

def test_ask_assistant_empty_query():
    resp = client.post("/api/ask", json={"query": ""}, headers=valid_headers)
    assert resp.status_code == 200

def test_metrics_no_auth():
    resp = client.get("/api/metrics")
    assert resp.status_code == 200

def test_invalid_method():
    resp = client.put("/api/controller-config", json={}, headers=admin_headers)
    assert resp.status_code == 405

def test_websocket_no_api_key():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as ws:
            ws.receive_text()


def test_controller_config_scoot_splits():
    payload = {"mode": "auto", "vps": {"N": 15, "S": 12}, "duration": 45}
    resp = client.post("/api/controller-config", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["duration"] == 45
    assert data["vps"]["N"] == 15
    assert data["vps"]["S"] == 12

def test_rate_limit_returns_429():
    triggered = False
    for _ in range(15):
        resp = client.post("/api/emergency/clear", headers=admin_headers)
        if resp.status_code == 429:
            triggered = True
            break
    assert triggered


