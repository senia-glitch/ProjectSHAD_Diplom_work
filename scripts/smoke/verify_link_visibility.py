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


tutor = call("POST", "/users/register", {"role": "tutor", "username": f"vis_tutor_{SFX}",
    "password": "password123", "full_name": "Vis Tutor", "email": f"vis_tutor_{SFX}@t.t"})
student = call("POST", "/users/register", {"role": "student", "username": f"vis_stud_{SFX}",
    "password": "password123", "full_name": "Vis Student", "email": f"vis_stud_{SFX}@t.t"})
ttok, stok = tutor[1]["access_token"], student[1]["access_token"]
cfg = call("POST", "/tutor/configurations", {"student_user_id": student[1]["user_id"]}, ttok)[1]
cid = cfg["config_id"]

g, gd = call("GET", f"/tutor/configurations/{cid}", token=ttok)
check("1. дефолты выкл+0", g == 200 and gd.get("link_visibility_enabled") is False
      and gd.get("link_lead_time_minutes") == 0, f"{g} {gd}")

p, _ = call("PATCH", f"/tutor/configurations/{cid}", token=ttok, body={
    "link_visibility_enabled": True, "link_lead_time_minutes": 10})
g2, gd2 = call("GET", f"/tutor/configurations/{cid}", token=ttok)
check("2. включение + лид сохранились", p == 200 and gd2.get("link_visibility_enabled") is True
      and gd2.get("link_lead_time_minutes") == 10, f"{p} {gd2}")

p3, _ = call("PATCH", f"/tutor/configurations/{cid}", token=ttok, body={"link_lead_time_minutes": 20})
check("3. лид 20 отклонён", p3 == 422, str(p3))
p4, _ = call("PATCH", f"/tutor/configurations/{cid}", token=ttok, body={"link_lead_time_minutes": -1})
check("4. лид -1 отклонён", p4 == 422, str(p4))

gs, gsd = call("GET", f"/student/configurations/{cid}", token=stok)
check("5. ученик видит настройки", gsd.get("link_visibility_enabled") is True
      and gsd.get("link_lead_time_minutes") == 10, str(gsd))

gl, gld = call("GET", "/student/configurations", token=stok)
row = next((x for x in gld.get("configurations", []) if x["config_id"] == cid), {})
check("6. список отдаёт поля", row.get("link_visibility_enabled") is True
      and row.get("link_lead_time_minutes") == 10, str(row))

r, _ = call("POST", f"/tutor/configurations/{cid}/reset", token=ttok)
g5, gd5 = call("GET", f"/tutor/configurations/{cid}", token=ttok)
check("7. сброс гасит оба поля", gd5.get("link_visibility_enabled") is False
      and gd5.get("link_lead_time_minutes") == 0, str(gd5))

call("DELETE", f"/tutor/configurations/{cid}", token=ttok)
call("POST", "/users/me/delete", {}, ttok)
call("POST", "/users/me/delete", {}, stok)
print(f"\nPASSED {len(passed)} FAILED {len(failed)}")
if failed:
    raise SystemExit(1)
