import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_flow():
    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    print("1. Health check passed")

    # 2. Create Job
    req_payload = {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "voice": "en-US-AriaNeural",
        "whisper_model": "tiny",
    }
    res = client.post("/api/jobs", json=req_payload)
    assert res.status_code == 202
    job_data = res.json()
    job_id = job_data["id"]
    print(f"2. Job created with ID: {job_id}")

    # 3. Poll until completed
    start_time = time.time()
    completed = False
    while time.time() - start_time < 60:
        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200
        st = res.json()
        print(f"Status: {st['status']}, Progress: {st['progress']}%, Message: {st['message']}")
        if st["status"] == "completed":
            completed = True
            break
        elif st["status"] == "failed":
            raise RuntimeError(f"Job failed: {st.get('error')}")
        time.sleep(1.5)

    assert completed, "Job did not complete within timeout"
    print("3. Job successfully completed end-to-end!")

    # 4. Test download endpoint
    dl_res = client.get(f"/api/jobs/{job_id}/download")
    assert dl_res.status_code == 200
    assert "video/mp4" in dl_res.headers.get("content-type", "")
    assert len(dl_res.content) > 0
    print(f"4. Download verified! Received {len(dl_res.content)} bytes of MP4 video.")

if __name__ == "__main__":
    test_full_flow()
    print("ALL API FLOW TESTS PASSED SUCCESSFULLY!")
