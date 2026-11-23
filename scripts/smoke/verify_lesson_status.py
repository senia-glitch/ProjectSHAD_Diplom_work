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


def call(method, path, body=None, token=None):
    req = urllib.request.Request(
        BASE + path,
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


tutor = call("POST", "/users/register", {"role": "tutor", "username": f"st_tutor_{SFX}",
    "password": "password123", "full_name": "St Tutor", "email": f"st_tutor_{SFX}@t.t"})
student = call("POST", "/users/register", {"role": "student", "username": f"st_stud_{SFX}",
    "password": "password123", "full_name": "St Student", "email": f"st_stud_{SFX}@t.t"})
ttok, stok = tutor[1]["access_token"], student[1]["access_token"]
cfg = call("POST", "/tutor/configurations", {"student_user_id": student[1]["user_id"]}, ttok)[1]

# 1. create -> SCHEDULED
c, cd = call("POST", "/tutor/lessons", token=ttok, body={
    "start_time": "2026-11-03T10:00:00", "end_time": "2026-11-03T11:00:00"})
check("1. create даёт SCHEDULED", c == 200 and cd.get("status") == "SCHEDULED", f"{c} {cd}")
lid = cd.get("lesson_id")

# 2. ручной CANCELLED держится
u, _ = call("PATCH", f"/tutor/lessons/{lid}", token=ttok, body={"status": "CANCELLED"})
g, gd = call("GET", "/tutor/me/lessons", token=ttok)
row = next((x for x in gd.get("lessons", []) if x["lesson_id"] == lid), {})
check("2. CANCELLED держится при чтении", row.get("status") == "CANCELLED", str(row))

# 3. повторная правка времени терминального — 422
u3, _ = call("PATCH", f"/tutor/lessons/{lid}", token=ttok, body={
    "start_time": "2026-11-03T12:00:00", "end_time": "2026-11-03T13:00:00"})
check("3. время терминального — 422", u3 == 422, str(u3))

# 4. богусный статус — 422
u4, _ = call("PATCH", f"/tutor/lessons/{lid}", token=ttok, body={"status": "SCHEDULED"})
check("4. ручной SCHEDULED — 422", u4 == 422, str(u4))

# 5. join в отменённый — 403
call("POST", f"/tutor/lessons/{lid}/participants", token=ttok,
     body={"lesson_id": lid, "student_user_id": student[1]["user_id"]})
j, _ = call("POST", f"/student/lessons/{lid}/join", token=stok)
check("5. join в CANCELLED — 403", j == 403, str(j))

# 6. студент видит статус
g6, g6d = call("GET", "/student/me/lessons", token=stok)
row6 = next((x for x in g6d.get("lessons", []) if x["lesson_id"] == lid), {})
check("6. студент видит CANCELLED", row6.get("status") == "CANCELLED", str(row6))

call("DELETE", f"/tutor/lessons/{lid}", token=ttok)
call("DELETE", f"/tutor/configurations/{cfg['config_id']}", token=ttok)
call("POST", "/users/me/delete", {}, ttok)
call("POST", "/users/me/delete", {}, stok)
print(f"\nPASSED {len(passed)} FAILED {len(failed)}")
if failed:
    raise SystemExit(1)
