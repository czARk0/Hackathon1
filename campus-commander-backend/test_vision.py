"""
test_vision.py -- Verify Gemini Vision Analysis & POST /agent/analyze-image endpoint
"""

import io
import sys
import requests

BACKEND_URL = "http://127.0.0.1:8000"

# Minimal 1x1 valid PNG bytes
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

def main():
    print("=" * 70)
    print("TESTING POST /agent/analyze-image")
    print("=" * 70)

    # 1. Health check
    h = requests.get(f"{BACKEND_URL}/health")
    assert h.status_code == 200, f"Health check failed: {h.status_code}"
    print("  PASS  Backend online")

    # 2. Test analyze-image endpoint with image + user text
    user_text = "This is the projector in Lab 3. Display is cracked."
    files = {"file": ("test_projector.png", io.BytesIO(TINY_PNG), "image/png")}
    data = {"user_text": user_text}

    res = requests.post(f"{BACKEND_URL}/agent/analyze-image", files=files, data=data)
    print(f"  HTTP Status: {res.status_code}")
    print(f"  Response: {res.text}")

    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert "analysis" in body, "Response missing 'analysis'"
    assert "combined_goal" in body, "Response missing 'combined_goal'"
    assert "issue" in body["analysis"], "Analysis missing 'issue'"
    assert "equipment" in body["analysis"], "Analysis missing 'equipment'"

    print("  PASS  POST /agent/analyze-image returned structured analysis and combined_goal:")
    print(f"    Issue: {body['analysis'].get('issue')}")
    print(f"    Equipment: {body['analysis'].get('equipment')}")
    print(f"    Combined Goal: {body['combined_goal']}")

    # 3. Test invalid file type rejection
    bad_files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
    bad_res = requests.post(f"{BACKEND_URL}/agent/analyze-image", files=bad_files, data=data)
    assert bad_res.status_code == 400, f"Expected 400 for bad mime type, got {bad_res.status_code}"
    print("  PASS  Correctly rejects unsupported file types with HTTP 400")

    print("\n" + "=" * 70)
    print("ALL VISION BACKEND TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
