import httpx, time, asyncio, sys

sys.path.insert(0, '.')
from app.core.cache import invalidate_cache_pattern

c = httpx.Client()
r = c.post("http://localhost:8000/api/v1/auth/login", json={"badge_number": "ADMIN001", "password": "Admin@2024"})
t = r.json()["access_token"]
h = {"Authorization": f"Bearer {t}"}

print("=" * 60)
print("PERFORMANCE BENCHMARKS")
print("=" * 60)

# Hybrid Search
start = time.monotonic()
r1 = c.post("http://localhost:8000/api/v1/similarity/search",
    json={"query_text": "robbery with knife at night", "limit": 10, "min_similarity": 0.01},
    headers=h, timeout=30)
ms1 = (time.monotonic() - start) * 1000
res_count = len(r1.json().get("results", []))
print(f"  Hybrid Search:     {ms1:.1f}ms | status={r1.status_code} | matches={res_count}")

# Neo4j Stats
start = time.monotonic()
r2 = c.get("http://localhost:8000/api/v1/graph/statistics", headers=h, timeout=15)
ms2 = (time.monotonic() - start) * 1000
print(f"  Neo4j Stats:       {ms2:.1f}ms | status={r2.status_code}")

# Geo Hotspots cold
asyncio.run(invalidate_cache_pattern("pac:cache:geo:*"))
start = time.monotonic()
r3 = c.get("http://localhost:8000/api/v1/geo/hotspots?eps=1000&min_samples=3", headers=h, timeout=30)
ms3 = (time.monotonic() - start) * 1000
print(f"  Geo Hotspots Cold: {ms3:.1f}ms | status={r3.status_code}")

# Geo Hotspots warm
start = time.monotonic()
r4 = c.get("http://localhost:8000/api/v1/geo/hotspots?eps=1000&min_samples=3", headers=h, timeout=15)
ms4 = (time.monotonic() - start) * 1000
speedup = round(ms3 / max(ms4, 0.1), 1)
print(f"  Geo Hotspots Warm: {ms4:.1f}ms | speedup={speedup}x")

# Crimes list
start = time.monotonic()
r5 = c.get("http://localhost:8000/api/v1/crimes/?limit=20", headers=h, timeout=10)
ms5 = (time.monotonic() - start) * 1000
print(f"  Crimes List (20):  {ms5:.1f}ms | status={r5.status_code}")

# Predictions stats
start = time.monotonic()
r6 = c.get("http://localhost:8000/api/v1/predictions/statistics", headers=h, timeout=10)
ms6 = (time.monotonic() - start) * 1000
print(f"  Predictions Stats: {ms6:.1f}ms | status={r6.status_code}")

# Graph network
criminals_resp = c.get("http://localhost:8000/api/v1/criminals/?limit=1", headers=h, timeout=10)
crim_data = criminals_resp.json()
if crim_data.get("items"):
    crim_id = crim_data["items"][0]["id"]
    start = time.monotonic()
    r7 = c.get(f"http://localhost:8000/api/v1/graph/network/{crim_id}", headers=h, timeout=15)
    ms7 = (time.monotonic() - start) * 1000
    print(f"  Graph Network:     {ms7:.1f}ms | status={r7.status_code}")

print("=" * 60)
