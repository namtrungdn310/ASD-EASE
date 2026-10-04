def raw_payload():
    return {
        "schema_version": "1.0", "device_id": "SIM-001", "session_id": "SYN-SESSION001",
        "batch_id": 1, "start_timestamp_ms": 0, "data_origin": "SYNTHETIC",
        "ppg": {"sample_rate_hz": 100, "red": [100, 101], "ir": [200, 201]},
        "imu": {"sample_rate_hz": 50, "ax": [0, 0], "ay": [0, 0], "az": [1, 1], "gx": [0, 0], "gy": [0, 0], "gz": [0, 0]},
        "gsr": {"sample_rate_hz": 20, "adc": [1800, 1801]}
    }


def test_raw_batch_schema(client):
    response = client.post("/api/v1/raw-batch", json=raw_payload())
    assert response.status_code == 202


def test_mismatched_ppg_arrays_rejected(client):
    data = raw_payload(); data["ppg"]["ir"] = []
    assert client.post("/api/v1/raw-batch", json=data).status_code == 422

