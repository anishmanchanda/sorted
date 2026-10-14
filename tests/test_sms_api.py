from fastapi.testclient import TestClient

from brain.orchestrator import Orchestrator
from brain.sources import sms_api


def test_sms_webhook_auth_otp_and_ingest(monkeypatch, make_llm):
    monkeypatch.setenv("BRAIN_INGEST_TOKENS", "rohan:secret-token")
    llm = make_llm(lambda user, schema: {"type": "bill_due", "provider": "Airtel", "amount": 1178.82,
                                         "due_date": "2026-10-20"})
    sms_api.app.dependency_overrides[sms_api.get_orchestrator] = lambda: Orchestrator(llm=llm)
    client = TestClient(sms_api.app)
    body = {"sender": "AX-AIRTEL", "body": "Your Airtel bill of Rs 1178.82 is due on 20-Oct-2026.",
            "received_at": "2026-10-01T10:00:00+05:30"}
    auth = {"Authorization": "Bearer secret-token"}

    assert client.post("/ingest/sms", json=body).status_code == 401
    assert client.post("/ingest/sms", json=body, headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.post("/ingest/sms", json=body, headers=auth)
    assert ok.status_code == 200 and ok.json()["outcome"] == "open"
    otp = client.post("/ingest/sms", json={"sender": "VM-HDFCBK", "body": "123456 is your OTP. Do not share."},
                      headers=auth)
    assert otp.json() == {"outcome": "dropped_otp"} and len(llm.calls) == 1
    sms_api.app.dependency_overrides.clear()
