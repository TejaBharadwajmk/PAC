import httpx

c = httpx.Client()
creds = [
    ("ADMIN001", "Admin@2024"),
    ("SUP001",   "Sup@2024"),
    ("SUP002",   "Sup@2024"),
    ("ANA001",   "Ana@2024"),
    ("OFF001",   "Off@2024"),
    ("OFF002",   "Off@2024"),
    ("OFF003",   "Off@2024"),
]

print("=" * 50)
print("USER CREDENTIALS VERIFICATION")
print("=" * 50)
for badge, pwd in creds:
    resp = c.post("http://localhost:8000/api/v1/auth/login", json={"badge_number": badge, "password": pwd})
    status_str = "PASS" if resp.status_code == 200 else "FAIL"
    print(f"  [{status_str}] Badge: {badge:<10} Password: {pwd:<12} -> HTTP {resp.status_code}")
print("=" * 50)
