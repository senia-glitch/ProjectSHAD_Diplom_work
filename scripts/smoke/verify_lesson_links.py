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


tutor = call("POST", "/users/register", {"role": "tutor", "username": f"lnk_tutor_{SFX}",
    "password": "password123", "full_name": "Lnk Tutor", "email": f"lnk_tutor_{SFX}@t.t"})
student = call("POST", "/users/register", {"role": "student", "username": f"lnk_stud_{SFX}",
    "password": "password123", "full_name": "Lnk Student", "email": f"lnk_stud_{SFX}@t.t"})
ttok, stok = tutor[1]["access_token"], student[1]["access_token"]
tutor_uid = call("GET", "/users/me", token=ttok)[1]["user_id"]

LINKS = [{"alias": "zoom", "url": "https://zoom.us/j/1"}]
call("PATCH", "/tutor/me/settings", {"default_links": LINKS}, ttok)
cfg = call("POST", "/tutor/configurations", {"student_user_id": student[1]["user_id"]}, ttok)[1]

# 1. tutor create без ссылок -> из настроек
t1, t1d = call("POST", "/tutor/lessons", token=ttok, body={
    "start_time": "2026-11-02T10:00:00", "end_time": "2026-11-02T11:00:00"})
check("1. tutor create копирует из настроек", t1 == 200 and t1d.get("lesson_links") == LINKS, f"{t1} {t1d}")
lid = t1d.get("lesson_id")

# 2. tutor GET содержит ссылки
g, gd = call("GET", "/tutor/me/lessons", token=ttok)
row = next((x for x in gd.get("lessons", []) if x["lesson_id"] == lid), {})
check("2. tutor GET отдаёт links", row.get("lesson_links") == LINKS, str(row))

# 3. tutor update ссылок
u, ud = call("PATCH", f"/tutor/lessons/{lid}", token=ttok, body={
    "lesson_links": [{"alias": "meet", "url": "https://meet.example/x"}]})
check("3. tutor update возвращает links", u == 200 and ud.get("lesson_links") == [{"alias": "meet", "url": "https://meet.example/x"}], f"{u} {ud}")

# 4. student create без ссылок -> из своей конфигурации
call("POST", "/tutor/bookings", token=ttok, body={
    "weekday": "MONDAY", "start_time": "12:00", "end_time": "13:00", "access_rule": "EVERYONE"})
s1, s1d = call("POST", "/student/lessons", token=stok, body={
    "tutor_user_id": tutor_uid, "start_time": "2026-11-02T12:00:00", "end_time": "2026-11-02T13:00:00"})
check("4. student create копирует из конфигурации", s1 == 200 and s1d.get("lesson_links") == LINKS, f"{s1} {s1d}")
slid = s1d.get("lesson_id")

# 5. student GET содержит ссылки
g2, g2d = call("GET", "/student/me/lessons", token=stok)
row2 = next((x for x in g2d.get("lessons", []) if x["lesson_id"] == slid), {})
check("5. student GET отдаёт links", row2.get("lesson_links") == LINKS, str(row2))

# cleanup
for x in (lid, slid):
    if x:
        call("DELETE", f"/tutor/lessons/{x}", token=ttok)
call("DELETE", f"/tutor/configurations/{cfg['config_id']}", token=ttok)
call("POST", "/users/me/delete", {}, ttok)
call("POST", "/users/me/delete", {}, stok)
print(f"\nPASSED {len(passed)} FAILED {len(failed)}")
if failed:
    raise SystemExit(1)
