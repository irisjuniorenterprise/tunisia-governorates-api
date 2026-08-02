# test_api.py
import requests
import time
import statistics

BASE_URL = "http://localhost:8000/api"

def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    print("✅ Health check passed")

def test_list_governorates():
    response = requests.get(f"{BASE_URL}/governorates")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    print(f"✅ Found {data['count']} governorates")

def test_get_governorate():
    response = requests.get(f"{BASE_URL}/governorates/Ariana")
    assert response.status_code == 200
    data = response.json()
    assert data["properties"]["gouv_fr"] == "Ariana"
    print("✅ Get governorate passed")

def test_not_found():
    response = requests.get(f"{BASE_URL}/governorates/Nonexistent")
    assert response.status_code == 404
    print("✅ 404 handling passed")

def test_search():
    response = requests.get(f"{BASE_URL}/search?q=aria")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    print("✅ Search passed")

def test_metrics():
    response = requests.get(f"{BASE_URL}/metrics")
    assert response.status_code == 200
    print("✅ Metrics endpoint passed")

if __name__ == "__main__":
    print("🏃 Running tests...")
    test_health()
    test_list_governorates()
    test_get_governorate()
    test_not_found()
    test_search()
    test_metrics()
    print("\n✅ All tests passed!")