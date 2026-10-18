import json
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel

from services.api.app.api.dependencies import require_addon_request_signature, get_addon_request_signature_verifier
from services.api.app.auth.request_signing import AddonRequestSignatureVerifier

# create a small app that uses the dependency to emulate your real route
app = FastAPI()

class Payload(BaseModel):
    hello: str

# override the verifier with an instance that has no secret (disabled)
def disabled_verifier_override():
    return AddonRequestSignatureVerifier(secret="", max_age_seconds=300)

app.dependency_overrides[get_addon_request_signature_verifier] = disabled_verifier_override

@app.post("/test", dependencies=[Depends(require_addon_request_signature)])
def test_endpoint(payload: Payload):
    return {"received": payload.hello}

client = TestClient(app)

def test_body_not_consumed_when_verifier_disabled():
    resp = client.post("/test", json={"hello": "world"})
    assert resp.status_code == 200
    assert resp.json() == {"received": "world"}
