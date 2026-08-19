import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_live_server():
    print("Testing live backend server at", BASE_URL)
    
    # 1. Health check
    res = requests.get(f"{BASE_URL}/api/health", timeout=5)
    print("1. Health check:", res.status_code, res.json())
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert res.json()["ffmpeg"]["available"] is True

    # 2. Create Job
    payload = {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "voice": "en-US-AriaNeural",
        "whisper_model": "tiny"
    }
    res = requests.post(f"{BASE_URL}/api/jobs", json=payload, timeout=5)
    print("2. Job created:", res.status_code, res.json())
    assert res.status_code == 202
    job_id = res.json()["id"]

    # 3. Poll job status
    start = time.time()
    completed = False
    while time.time() - start < 90:
        res = requests.get(f"{BASE_URL}/api/jobs/{job_id}", timeout=5)
        assert res.status_code == 200
        data = res.json()
        print(f"Status: {data['status']:<12} Progress: {data['progress']:>3}%  Stage: {str(data.get('stage')):<10} Message: {data['message']}")
        if data["status"] == "completed":
            completed = True
            break
        elif data["status"] == "failed":
            raise RuntimeError(f"Job failed: {data.get('error')} | Suggested: {data.get('suggested_action')}")
        time.sleep(2)

    assert completed, "Job did not complete in time"
    print("3. Job successfully completed!")
    print("Metrics:", data.get("metrics"))

    # 4. Test download endpoint
    dl_res = requests.get(f"{BASE_URL}/api/jobs/{job_id}/download", timeout=10)
    print("4. Download status:", dl_res.status_code)
    print("Content-Type:", dl_res.headers.get("content-type"))
    print("Content-Disposition:", dl_res.headers.get("content-disposition"))
    print("Downloaded size:", len(dl_res.content), "bytes")
    assert dl_res.status_code == 200
    assert "video/mp4" in dl_res.headers.get("content-type", "")
    assert len(dl_res.content) > 100000

    print("ALL LIVE HTTP TESTS PASSED 100%!")

if __name__ == "__main__":
    test_live_server()
