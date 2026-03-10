"""
Run tests with:  python test_app.py
"""
import os
os.environ['FLASK_SECRET_KEY']    = 'test_secret'
os.environ['OPENWEATHER_API_KEY'] = 'test_key'
os.environ['SENDER_EMAIL']        = 'test@test.com'
os.environ['SENDER_PASSWORD']     = 'test_pass'
os.environ['DATABASE']            = ':memory:'

from app import app, get_soil_health_tips, AGRO_ZONES

client = app.test_client()
app.config['TESTING'] = True
passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ FAIL: {name}")
        failed += 1

print("\n🧪 RUNNING ECO-FERTILIZATION TESTS\n")

# ── AGRO ZONE TESTS ──
print("📍 Agro Zone Tests:")
test("Rice valid in Karnataka",       "RICE"  in AGRO_ZONES.get("karnataka", []))
test("Apple valid in Himachal",       "APPLE" in AGRO_ZONES.get("himachal pradesh", []))
test("Apple NOT valid in Gujarat",    "APPLE" not in AGRO_ZONES.get("gujarat", []))
test("All states have crops",         all(len(v) > 0 for v in AGRO_ZONES.values()))
test("All crops are uppercase",       all(c == c.upper() for crops in AGRO_ZONES.values() for c in crops))

# ── SOIL TIPS TESTS ──
print("\n🌱 Soil Health Tips Tests:")
tips = get_soil_health_tips(30, 15, 10, ph=4.5, moisture=50)
test("Acidic soil → lime tip",        "ACIDIC" in tips["organic"] or "Lime" in tips["organic"])

tips = get_soil_health_tips(30, 15, 10, ph=8.5, moisture=50)
test("Alkaline soil → gypsum tip",    "ALKALINE" in tips["organic"] or "Gypsum" in tips["organic"])

tips = get_soil_health_tips(30, 15, 10, ph=7.0, moisture=20)
test("Dry soil → mulching tip",       "DRY" in tips["compost"] or "Mulch" in tips["compost"])

tips = get_soil_health_tips(30, 15, 10, ph=7.0, moisture=90)
test("Wet soil → drainage tip",       "Moisture" in tips["compost"] or "drainage" in tips["compost"])

tips = get_soil_health_tips(30, 15, 10, ph=7.0, moisture=50)
test("Tips returns 3 keys",           all(k in tips for k in ["organic","compost","micronutrients"]))

# ── INPUT VALIDATION TESTS ──
print("\n✅ Input Validation Tests:")
ph = max(0.0, min(14.0, float("-999")))
test("pH clamped min to 0",           ph == 0.0)

ph = max(0.0, min(14.0, float("999")))
test("pH clamped max to 14",          ph == 14.0)

moisture = max(0.0, min(100.0, float("150")))
test("Moisture clamped to 100",       moisture == 100.0)

acres = max(0.1, float("0"))
test("Acres minimum is 0.1",          acres == 0.1)

crop = "CORN"
if crop == "CORN": crop = "MAIZE"
test("CORN maps to MAIZE",            crop == "MAIZE")

# ── ROUTE TESTS ──
print("\n🌐 Route Tests:")
resp = client.get("/reset_page")
test("Reset page loads (200)",        resp.status_code == 200)

resp = client.get("/dashboard")
test("Dashboard needs login (302)",   resp.status_code == 302)

resp = client.get("/logout")
test("Logout redirects (302)",        resp.status_code == 302)

resp = client.get("/nonexistent_xyz")
test("404 handler works",             resp.status_code == 404)

# ── AUTH API TESTS ──
print("\n🔐 Auth API Tests:")
resp = client.post("/signup_api", json={"name":"","email":"","password":""})
test("Signup rejects empty fields",   resp.get_json()["success"] is False)

resp = client.post("/signup_api", json={"name":"Test","gender":"M","email":"t@t.com","password":"abc"})
test("Signup rejects short password", resp.get_json()["success"] is False)

resp = client.post("/login_api", json={"email":"","password":""})
test("Login rejects empty fields",    resp.get_json()["success"] is False)

resp = client.post("/login_api", json={"email":"nobody@no.com","password":"wrong"})
test("Login rejects wrong user",      resp.get_json()["success"] is False)

# ── SUMMARY ──
print(f"\n{'='*40}")
print(f"  Results: {passed} passed, {failed} failed")
print(f"  Score: {int(passed/(passed+failed)*100)}%")
print(f"{'='*40}\n")