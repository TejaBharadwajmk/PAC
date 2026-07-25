import httpx

c = httpx.Client()
r = c.post("http://localhost:8000/api/v1/auth/login", json={"badge_number": "ADMIN001", "password": "Admin@2024"})
t = r.json()["access_token"]
h = {"Authorization": f"Bearer {t}"}

print("=== E2E WORKFLOW AUDIT ===")
r1 = c.post("http://localhost:8000/api/v1/cctns/seed-staging?batch_size=2", headers=h)
print(f"1. Seed CCTNS staging: {r1.status_code}")

r2 = c.post("http://localhost:8000/api/v1/cctns/sync", headers=h)
sync_log = r2.json()["log"]
imported = sync_log["records_imported"]
print(f"2. CCTNS ETL Sync: {r2.status_code} | imported={imported}")

r3 = c.post("http://localhost:8000/api/v1/similarity/search",
    json={"query_text": "robbery motorcycle snatching bus stop", "limit": 5, "min_similarity": 0.01},
    headers=h, timeout=20)
matches = len(r3.json().get("results", []))
print(f"3. Hybrid Search: {r3.status_code} | matches={matches}")

r4 = c.get("http://localhost:8000/api/v1/predictions/statistics", headers=h)
print(f"4. Predictions Stats: {r4.status_code}")

r5 = c.get("http://localhost:8000/api/v1/audit/logs?limit=5", headers=h)
print(f"5. Audit Logs: {r5.status_code} | count={len(r5.json())}")

r6 = c.get("http://localhost:8000/api/v1/cctns/logs?limit=5", headers=h)
print(f"6. CCTNS Import Logs: {r6.status_code} | count={len(r6.json())}")

r7 = c.get("http://localhost:8000/api/v1/graph/statistics", headers=h)
g = r7.json()
total_n = sum(g.get("node_counts", {}).values())
print(f"7. Graph Stats: {r7.status_code} | nodes={total_n}")

r8 = c.get("http://localhost:8000/api/v1/geo/statistics", headers=h)
print(f"8. Geo Statistics: {r8.status_code}")

print("=========================")
print("ALL E2E STEPS COMPLETE")
