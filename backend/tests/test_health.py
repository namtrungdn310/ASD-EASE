def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_available(client):
    assert client.get("/openapi.json").status_code == 200

