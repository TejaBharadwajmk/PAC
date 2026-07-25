import httpx

BASE = "http://localhost:8000"

# Auth
r = httpx.post(f"{BASE}/api/v1/auth/login", json={"badge_number": "ADMIN001", "password": "Admin@2024"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}

# Endpoints to test: (path, method)
tests = [
    ("/health", "GET"),
    ("/api/v1/health", "GET"),
    ("/api/v1/crimes/?limit=5", "GET"),
    ("/api/v1/criminals/?limit=5", "GET"),
    ("/api/v1/geo/statistics", "GET"),
    ("/api/v1/geo/hotspots?eps=1000&min_samples=3", "GET"),
    ("/api/v1/graph/statistics", "GET"),
    ("/api/v1/predictions/statistics", "GET"),
    ("/api/v1/audit/logs?limit=5", "GET"),
    ("/api/v1/cctns/logs?limit=5", "GET"),
    ("/api/v1/similarity/stats", "GET"),
    ("/api/v1/behavior/statistics", "GET"),
    ("/api/v1/predictions/criminals?limit=5", "GET"),
]

print("=" * 60)
print("API ENDPOINT VERIFICATION")
print("=" * 60)
for path, method in tests:
    try:
        resp = httpx.get(f"{BASE}{path}", headers=h, timeout=10.0)
        tag = "PASS" if resp.status_code < 400 else "FAIL"
        print(f"  [{tag}] {method} {path} -> {resp.status_code}")
    except Exception as e:
        print(f"  [FAIL] {method} {path} -> ERROR: {e}")

# Test unauthorized access (no token)
r_unauth = httpx.get(f"{BASE}/api/v1/crimes/", timeout=5)
print(f"  [{'PASS' if r_unauth.status_code == 401 else 'FAIL'}] GET /crimes/ (no auth) -> {r_unauth.status_code} (expect 401)")

# Test RBAC: wrong role for audit logs (use analyst role if exists)
print("=" * 60)
print("DONE")
