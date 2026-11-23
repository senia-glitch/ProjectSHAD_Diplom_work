"""Полный тест всех API-эндпоинтов."""
import requests, sys, uuid

BASE = "http://localhost:8000/api/v1"
passed = 0
failed = 0
errors = []
uid = uuid.uuid4().hex[:6]

def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  OK  {name}")
    else:
        failed += 1
        errors.append(f"{name}: {detail}")
        print(f"  FAIL {name} -- {detail}")

def h(tok):
    return {"Authorization": f"Bearer {tok}"}

# ============================================================
print("=" * 60)
print("  1. AUTH")
print("=" * 60)

r = requests.post(f"{BASE}/users/register", json={
    "username": f"ts{uid}", "password": "testpass123",
    "full_name": "Stud", "email": f"s{uid}@t.com", "role": "student"
}, timeout=10)
check("register student", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

r = requests.post(f"{BASE}/users/register", json={
    "username": f"tt{uid}", "password": "testpass123",
    "full_name": "Tutor", "email": f"t{uid}@t.com", "role": "tutor"
}, timeout=10)
check("register tutor", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

r = requests.post(f"{BASE}/auth/login", json={"username": f"ts{uid}", "password": "testpass123"}, timeout=10)
check("login student", r.status_code == 200, f"{r.status_code}")
st = r.json().get("access_token")

r = requests.post(f"{BASE}/auth/login", json={"username": f"tt{uid}", "password": "testpass123"}, timeout=10)
check("login tutor", r.status_code == 200, f"{r.status_code}")
tt = r.json().get("access_token")

r = requests.post(f"{BASE}/auth/login", json={"username": f"ts{uid}", "password": "wrong"}, timeout=10)
check("login wrong pass", r.status_code in (400, 401, 422), f"{r.status_code}")

r = requests.post(f"{BASE}/auth/login", json={"username": f"tt{uid}", "password": "testpass123"}, timeout=10)
rt = r.json().get("refresh_token")
if rt:
    r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": rt}, timeout=10)
    check("refresh token", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  2. USERS")
print("=" * 60)

r = requests.get(f"{BASE}/users/me", headers=h(st), timeout=10)
check("get me (student)", r.status_code == 200 and r.json()["role"] == "student", f"{r.status_code}")
student_user_id = r.json()["user_id"]

r = requests.get(f"{BASE}/users/me", headers=h(tt), timeout=10)
check("get me (tutor)", r.status_code == 200 and r.json()["role"] == "tutor", f"{r.status_code}")
tutor_user_id = r.json()["user_id"]

r = requests.patch(f"{BASE}/users/me", headers=h(st), json={"full_name": "New Stud"}, timeout=10)
check("update me", r.status_code == 200, f"{r.status_code}")

r = requests.post(f"{BASE}/users/me/change-password", headers=h(st),
                  json={"old_password": "testpass123", "new_password": "newpass123"}, timeout=10)
check("change password", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

# ============================================================
print("=" * 60)
print("  3. TUTOR SETTINGS")
print("=" * 60)

r = requests.get(f"{BASE}/tutor/me", headers=h(tt), timeout=10)
check("get tutor profile", r.status_code == 200, f"{r.status_code}")
s = r.json()
check("settings has hourly_rate", s.get("hourly_rate") == 0, f"{s.get('hourly_rate')}")
check("settings has booking_lead_time", "booking_lead_time_hours" in s, f"{list(s.keys())}")

r = requests.patch(f"{BASE}/tutor/me/settings", headers=h(tt), json={
    "hourly_rate": 2000, "discount": 20, "self_booking_mode": "YES",
    "display_time_from": "08:00", "display_time_to": "22:00",
    "default_links": [{"alias": "zoom", "url": "https://zoom.us"}]
}, timeout=10)
check("patch settings", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
d = r.json()
check("settings hourly=2000", d.get("hourly_rate") == 2000, f"{d.get('hourly_rate')}")
check("settings discount=20", d.get("discount") == 20, f"{d.get('discount')}")
has_links = d.get("default_links") is not None and len(d["default_links"]) > 0
check("settings links saved", has_links, f"{d.get('default_links')}")
check("settings time_from=08:00", d.get("display_time_from") == "08:00", f"{d.get('display_time_from')}")

# whitelist propagation
r = requests.patch(f"{BASE}/tutor/me/settings", headers=h(tt),
                   json={"self_booking_mode": "NO", "self_booking_whitelist": []}, timeout=10)
check("settings NO whitelist=[]", r.status_code == 200, f"{r.status_code}")

r = requests.patch(f"{BASE}/tutor/me/settings", headers=h(tt),
                   json={"self_booking_mode": "NO", "self_booking_whitelist": [6]}, timeout=10)
check("settings NO whitelist=[6]", r.status_code == 200, f"{r.status_code}")

r = requests.patch(f"{BASE}/tutor/me/settings", headers=h(tt),
                   json={"self_booking_mode": "YES"}, timeout=10)
check("settings YES", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  4. CONFIGURATIONS")
print("=" * 60)

r = requests.post(f"{BASE}/tutor/configurations", headers=h(tt),
                  json={"student_user_id": student_user_id}, timeout=10)
check("create config (tutor)", r.status_code == 200, f"{r.status_code} {r.text[:300]}")
cfg_id = r.json().get("config_id") if r.status_code == 200 else None

r = requests.get(f"{BASE}/tutor/configurations", headers=h(tt), timeout=10)
configs = r.json().get("configurations", [])
check("list configs", r.status_code == 200 and len(configs) > 0, f"{r.status_code} {r.text[:200]}")

if cfg_id:
    r = requests.get(f"{BASE}/tutor/configurations/{cfg_id}", headers=h(tt), timeout=10)
    check("get config by id", r.status_code == 200, f"{r.status_code}")

r = requests.post(f"{BASE}/tutor/configurations", headers=h(tt),
                  json={"student_user_id": student_user_id}, timeout=10)
check("create config duplicate = 409", r.status_code == 409, f"{r.status_code}")

# Student configs
r = requests.get(f"{BASE}/student/configurations", headers=h(st), timeout=10)
check("student list configs", r.status_code == 200, f"{r.status_code}")

if cfg_id:
    r = requests.get(f"{BASE}/student/configurations/{cfg_id}", headers=h(st), timeout=10)
    check("student get config", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

# ============================================================
print("=" * 60)
print("  5. LESSONS")
print("=" * 60)

r = requests.post(f"{BASE}/tutor/lessons", headers=h(tt), json={
    "start_time": "2026-10-15T10:00", "end_time": "2026-10-15T11:00", "is_group": False
}, timeout=10)
check("create lesson", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
lid = r.json().get("lesson_id") if r.status_code == 200 else None

r = requests.post(f"{BASE}/tutor/lessons", headers=h(tt), json={
    "start_time": "2026-10-15T12:00", "end_time": "2026-10-15T11:00", "is_group": False
}, timeout=10)
check("create lesson bad times", r.status_code in (400, 422), f"{r.status_code}")

r = requests.get(f"{BASE}/tutor/me/lessons", headers=h(tt), timeout=10)
check("list tutor lessons", r.status_code == 200, f"{r.status_code}")

r = requests.get(f"{BASE}/student/me/lessons", headers=h(st), timeout=10)
check("list student lessons", r.status_code == 200, f"{r.status_code}")

if lid:
    r = requests.patch(f"{BASE}/tutor/lessons/{lid}", headers=h(tt), json={
        "start_time": "2026-10-15T12:00", "end_time": "2026-10-15T13:00", "is_group": True
    }, timeout=10)
    check("update lesson", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

# ============================================================
print("=" * 60)
print("  6. PARTICIPANTS")
print("=" * 60)

if lid:
    r = requests.post(f"{BASE}/tutor/lessons/{lid}/participants", headers=h(tt),
                      json={"student_user_id": student_user_id}, timeout=10)
    check("add participant", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    r = requests.get(f"{BASE}/tutor/lessons/{lid}/participants", headers=h(tt), timeout=10)
    parts = r.json().get("participants", [])
    check("get participants", r.status_code == 200 and len(parts) > 0, f"{r.status_code} {r.text[:200]}")

    r = requests.delete(f"{BASE}/tutor/lessons/{lid}/participants/{student_user_id}", headers=h(tt), timeout=10)
    check("remove participant", r.status_code == 200, f"{r.status_code}")

    r = requests.delete(f"{BASE}/tutor/lessons/{lid}", headers=h(tt), timeout=10)
    check("delete lesson", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  7. BOOKINGS")
print("=" * 60)

r = requests.post(f"{BASE}/tutor/bookings", headers=h(tt), json={
    "weekday": "WEDNESDAY", "start_time": "09:00", "end_time": "10:00",
    "access_rule": "EVERYONE"
}, timeout=10)
check("create booking", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
bid = r.json().get("booking_id") if r.status_code == 200 else None

r = requests.get(f"{BASE}/tutor/me/bookings", headers=h(tt), timeout=10)
check("list bookings", r.status_code == 200, f"{r.status_code}")

if bid:
    r = requests.patch(f"{BASE}/tutor/bookings/{bid}", headers=h(tt),
                       json={"start_time": "09:30", "end_time": "10:30"}, timeout=10)
    check("update booking", r.status_code == 200, f"{r.status_code}")

    r = requests.delete(f"{BASE}/tutor/bookings/{bid}", headers=h(tt), timeout=10)
    check("delete booking", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  8. STUDENT LESSONS & SLOTS")
print("=" * 60)

r = requests.get(f"{BASE}/student/tutors/{tutor_user_id}/slots", headers=h(st),
                 params={"date_from": "2026-10-13", "date_to": "2026-10-17"}, timeout=10)
check("get available slots", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

r = requests.get(f"{BASE}/student/tutors/{tutor_user_id}/lessons", headers=h(st), timeout=10)
check("get tutor lessons", r.status_code == 200, f"{r.status_code}")

# Честная цепочка: сначала репетитор открывает окно на пятницу,
# потом ученик записывается. Без брони запись обязана отклоняться.
r = requests.post(f"{BASE}/tutor/bookings", headers=h(tt), json={
    "weekday": "FRIDAY", "start_time": "14:00", "end_time": "15:00",
    "access_rule": "EVERYONE"
}, timeout=10)
check("create friday booking for lesson", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
fbid = r.json().get("booking_id") if r.status_code == 200 else None

r = requests.post(f"{BASE}/student/lessons", headers=h(st), json={
    "tutor_user_id": tutor_user_id, "start_time": "2026-10-16T14:00", "end_time": "2026-10-16T15:00"
}, timeout=10)
check("student create lesson", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
slid = r.json().get("lesson_id") if r.status_code == 200 else None

if slid:
    r = requests.post(f"{BASE}/student/lessons/{slid}/join", headers=h(st), timeout=10)
    check("student join lesson", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

    r = requests.delete(f"{BASE}/student/lessons/{slid}/leave", headers=h(st), timeout=10)
    check("student leave lesson", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

    requests.delete(f"{BASE}/tutor/lessons/{slid}", headers=h(tt), timeout=10)

if fbid:
    r = requests.delete(f"{BASE}/tutor/bookings/{fbid}", headers=h(tt), timeout=10)
    check("delete friday booking", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  9. STUDENT PROFILE")
print("=" * 60)

r = requests.get(f"{BASE}/student/me", headers=h(st), timeout=10)
check("student profile", r.status_code == 200, f"{r.status_code}")

r = requests.patch(f"{BASE}/student/me/settings", headers=h(st),
                   json={"status": "ACTIVE", "schedule_view": "MINIMALISTIC"}, timeout=10)
check("student settings", r.status_code == 200, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  10. EDGE CASES")
print("=" * 60)

r = requests.get(f"{BASE}/users/me", timeout=5)
check("no token = 401", r.status_code in (401, 403, 422), f"{r.status_code}")

r = requests.get(f"{BASE}/tutor/me", headers=h(st), timeout=5)
check("student->tutor = 403", r.status_code in (401, 403), f"{r.status_code}")

r = requests.get(f"{BASE}/student/me", headers=h(tt), timeout=5)
check("tutor->student = 403", r.status_code in (401, 403), f"{r.status_code}")

r = requests.post(f"{BASE}/users/register", json={
    "username": f"ts{uid}", "password": "testpass123", "full_name": "x", "email": f"x{uid}@x.x", "role": "student"
}, timeout=5)
check("dup register = 409", r.status_code == 409, f"{r.status_code}")

# ============================================================
print("=" * 60)
print("  11. DELETE USERS")
print("=" * 60)

r = requests.post(f"{BASE}/auth/login", json={"username": f"ts{uid}", "password": "newpass123"}, timeout=10)
tmp = r.json().get("access_token")
r = requests.post(f"{BASE}/users/me/delete", headers=h(tmp), json={}, timeout=10)
check("delete student", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

r = requests.post(f"{BASE}/auth/login", json={"username": f"tt{uid}", "password": "testpass123"}, timeout=10)
tmp = r.json().get("access_token")
r = requests.post(f"{BASE}/users/me/delete", headers=h(tmp), json={}, timeout=10)
check("delete tutor", r.status_code == 200, f"{r.status_code} {r.text[:100]}")

# Verify deleted users can't login
r = requests.post(f"{BASE}/auth/login", json={"username": f"ts{uid}", "password": "newpass123"}, timeout=10)
check("deleted student can't login", r.status_code != 200, f"{r.status_code}")

# ============================================================
print("\n" + "=" * 60)
print(f"  ИТОГО: {passed} OK / {failed} FAIL")
if errors:
    print("\n  Ошибки:")
    for e in errors:
        print(f"    - {e}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
