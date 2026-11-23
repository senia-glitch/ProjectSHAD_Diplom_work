"""Проверка краевых случаев ТЗ: нет броней = закрыто."""
import json
import time
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000/api/v1"
SFX = str(int(time.time()))[-6:]
passed, failed = [], []


def check(name, ok, detail=""):
    (passed if ok else failed).append(name)
    print(f"  {'OK ' if ok else 'FAIL'} {name} {detail if not ok else ''}")


def call(method, path, body=None, token=None, params=None):
    url = BASE + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode() or "{}")
        except Exception:
            payload = {}
        return e.code, payload


tutor = call("POST", "/users/register", {"role": "tutor", "username": f"tz_tutor_{SFX}",
    "password": "password123", "full_name": "TZ Tutor", "email": f"tz_tutor_{SFX}@t.t"})
student = call("POST", "/users/register", {"role": "student", "username": f"tz_stud_{SFX}",
    "password": "password123", "full_name": "TZ Student", "email": f"tz_stud_{SFX}@t.t"})
ttok, stok = tutor[1]["access_token"], student[1]["access_token"]
tutor_uid = call("GET", "/users/me", token=ttok)[1]["user_id"]
cfg = call("POST", "/tutor/configurations", {"student_user_id": student[1]["user_id"]}, ttok)[1]
SID = cfg["student_id"]

WEEK = ("2026-10-12", "2026-10-18")  # Пн..Вс
MON_9_10 = ("2026-10-12T09:00", "2026-10-12T10:00")


def slots():
    s, data = call("GET", f"/student/tutors/{tutor_uid}/slots", token=stok,
                   params={"date_from": WEEK[0], "date_to": WEEK[1]})
    assert s == 200, data
    return data.get("slots", [])


def book(start, end):
    return call("POST", "/student/lessons", token=stok, body={
        "tutor_user_id": tutor_uid, "start_time": start, "end_time": end})


# 1. Нет броней — пусто, запись отклонена
s = slots()
check("1a. без броней слотов нет", s == [], str(s))
c, _ = book(*MON_9_10)
check("1b. без броней запись отклонена", c != 200, str(c))

# 2. Окно отображения не открывает
call("PATCH", "/tutor/me/settings", {"display_time_from": "08:00", "display_time_to": "22:00"}, ttok)
s = slots()
check("2a. display 08-22 слотов не даёт", s == [], str(s))
c, _ = book(*MON_9_10)
check("2b. display 08-22 запись отклонена", c != 200, str(c))

# 3. Одна бронь EVERYONE Пн 09-10
b, bdata = call("POST", "/tutor/bookings", token=ttok, body={
    "weekday": "MONDAY", "start_time": "09:00", "end_time": "10:00", "access_rule": "EVERYONE"})
bid = bdata.get("booking_id")
s = slots()
check("3a. ровно окно Пн 09-10", len(s) == 1 and s[0]["start"][:16] == "2026-10-12T09:00"
      and s[0]["end"][:16] == "2026-10-12T10:00", str(s))
c, ldata = book(*MON_9_10)
check("3b. запись в окно проходит", c == 200, f"{c} {ldata}")
lid = ldata.get("lesson_id")
c2, _ = book("2026-10-13T09:00", "2026-10-13T10:00")
check("3c. запись во вторник отклонена", c2 != 200, str(c2))
c3, _ = book("2026-10-12T11:00", "2026-10-12T12:00")
check("3d. запись в Пн 11-12 отклонена", c3 != 200, str(c3))
if lid:
    call("DELETE", f"/tutor/lessons/{lid}", token=ttok)
call("DELETE", f"/tutor/bookings/{bid}", token=ttok)

# 4. NOBODY и ONLY
b1, b1d = call("POST", "/tutor/bookings", token=ttok, body={
    "weekday": "TUESDAY", "start_time": "09:00", "end_time": "10:00", "access_rule": "NOBODY"})
b2, b2d = call("POST", "/tutor/bookings", token=ttok, body={
    "weekday": "WEDNESDAY", "start_time": "09:00", "end_time": "10:00",
    "access_rule": "ONLY", "access_targets": [SID]})
b3, b3d = call("POST", "/tutor/bookings", token=ttok, body={
    "weekday": "THURSDAY", "start_time": "09:00", "end_time": "10:00",
    "access_rule": "ONLY", "access_targets": []})
s = slots()
days = sorted(x["start"][:10] for x in s)
check("4a. NOBODY Вт скрыт, ONLY Ср виден, ONLY[] Чт скрыт",
      days == ["2026-10-14"], str(days))
for bdata in (b1d, b2d, b3d):
    if bdata.get("booking_id"):
        call("DELETE", f"/tutor/bookings/{bdata['booking_id']}", token=ttok)

# cleanup
call("DELETE", f"/tutor/configurations/{cfg['config_id']}", token=ttok)
call("POST", "/users/me/delete", {}, ttok)
call("POST", "/users/me/delete", {}, stok)
print(f"\nPASSED {len(passed)} FAILED {len(failed)}")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
