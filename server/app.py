"""
hongqingting_runner — FastAPI proxy backend (sk-token edition).

The frontend on GitHub Pages sends only `{token, studentNo, ...}`. Any URL,
queryUid, uidList lives encrypted in the on-disk vault (see vault.py).
"""

import gzip
import hashlib
import json
import random
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import vault

ANDROID_UA = "Dalvik/2.1.0 (Linux; U; Android 12; LIO-AN00 Build/PQ3B.190801.002)"
OKHTTP_UA  = "okhttp/5.0.0-alpha.10"
HTTP_TIMEOUT = 30.0

TRAJECTORY_DIR = Path("/opt/hongqingting_runner/trajectories")
TRACK_DEFAULTS = {
    "location_1km":    {"distance": 1000.0,  "base": 320,  "jitter": 100},
    "location_1_16km": {"distance": 1160.0,  "base": 320,  "jitter": 900},
    "location_1_6km":  {"distance": 1600.0,  "base": 320,  "jitter": 100},
    "location_12km":   {"distance": 12000.0, "base": 5800, "jitter": 600},
}

app = FastAPI(title="hongqingting_runner proxy", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- helpers -----------------------------------------------------------

def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def resolve_config(token: str) -> dict:
    try:
        plain = vault.decrypt(token)
    except KeyError:
        raise HTTPException(401, "invalid sk token")
    try:
        cfg = json.loads(plain)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"vault entry corrupt: {e}")
    return cfg


def uid_list(cfg: dict) -> list[str]:
    raw = cfg.get("uidList") or ""
    return [s.strip() for s in re.split(r"\r?\n", raw) if s.strip()]


def load_track(name: str) -> str:
    if name not in TRACK_DEFAULTS:
        raise HTTPException(400, f"unknown track: {name}")
    p = TRAJECTORY_DIR / name
    if not p.is_file():
        raise HTTPException(500, f"trajectory file missing on server: {name}")
    return p.read_text(encoding="utf-8")


def rewrite_trajectory(text: str, begintime: int, usetime: int) -> str:
    frames = re.findall(r".*?@", text)
    if not frames:
        raise HTTPException(400, "trajectory file has no frames")
    delta = usetime / len(frames)
    runtime = float(begintime)
    out = []
    for fr in frames:
        m = re.search(r"(?P<loc>.*?);.*?;", fr)
        if not m:
            continue
        rewritten = re.sub(
            r".*?;.*?;null;null;",
            f"{m.group('loc')};{int(runtime)};null;null;",
            fr,
        )
        out.append(rewritten)
        runtime += delta
    return re.sub(r".$", "", "".join(out))


# ---------- /v1/summary -------------------------------------------------------

class SummaryIn(BaseModel):
    token: str
    studentNo: str


@app.post("/v1/summary")
async def v1_summary(body: SummaryIn):
    cfg = resolve_config(body.token)
    payload = (
        "{'studentno':" + body.studentNo
        + ",'uid':'" + cfg["queryUid"] + "'"
        + ",'schoolno':'" + cfg["schoolNo"] + "'}"
    )
    gz = gzip.compress(payload.encode("utf-8"))
    headers = {
        "User-Agent": ANDROID_UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Length": str(len(gz)),
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cli:
        try:
            r = await cli.post(cfg["summaryUrl"], headers=headers, content=gz)
        except httpx.RequestError as e:
            raise HTTPException(502, f"upstream error: {e}")

    parsed = None
    try:
        d = json.loads(r.text)
        if "lasttime" in d:
            d["lasttimeFormatted"] = time.strftime(
                "%Y/%m/%d %H:%M:%S", time.localtime(d["lasttime"])
            )
        parsed = d
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "upstreamStatus": r.status_code,
        "upstreamBody": r.text,
        "parsed": parsed,
    }


# ---------- /v1/upload --------------------------------------------------------

class UploadIn(BaseModel):
    token: str
    studentNo: str
    track: str
    dayOffset: float
    uidIdx: int = 0


@app.post("/v1/upload")
async def v1_upload(body: UploadIn):
    cfg = resolve_config(body.token)
    uids = uid_list(cfg)
    if not uids:
        raise HTTPException(400, "vault uidList is empty")
    if body.uidIdx < 0 or body.uidIdx >= len(uids):
        raise HTTPException(400, "uidIdx out of range")
    defaults = TRACK_DEFAULTS[body.track]
    distance_target = float(defaults["distance"])
    base_use = int(defaults["base"])
    jitter   = int(defaults["jitter"])

    if body.dayOffset != 0:
        begintime = int(time.time() - 86400 * body.dayOffset + random.randint(1, 3600))
        endtime   = begintime + base_use + random.randint(1, jitter)
    else:
        endtime   = int(time.time() - random.randint(1, 3600))
        begintime = endtime - base_use - random.randint(1, jitter)

    usetime = endtime - begintime - random.randint(1, 10)
    if usetime <= 0:
        raise HTTPException(400, "computed usetime <= 0")

    distance = distance_target + random.uniform(-50.0, 50.0)
    speed    = (usetime / 60) / (distance / 1000)

    location_text = load_track(body.track)
    location      = rewrite_trajectory(location_text, begintime, usetime)

    upload_payload = (
        "{'begintime':'" + str(begintime)
        + "','endtime':'" + str(endtime)
        + "','uid':'" + uids[body.uidIdx]
        + "','schoolno':'" + cfg["schoolNo"]
        + "','distance':'" + f"{distance:.1f}"
        + "','speed':'" + str(speed)
        + "','studentno':'" + body.studentNo
        + "','atttype':'3','eventno':'803','location':'" + location
        + "','pointstatus':'1','usetime':'" + str(usetime)
        + "','path':'null'}"
    )
    gz = gzip.compress(upload_payload.encode("utf-8"))
    headers = {
        "User-Agent": OKHTTP_UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Length": str(len(gz)),
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cli:
        try:
            r = await cli.post(cfg["uploadUrl"], headers=headers, content=gz)
        except httpx.RequestError as e:
            raise HTTPException(502, f"upstream error: {e}")

    return {
        "upstreamStatus": r.status_code,
        "upstreamBody": r.text,
        "begintime": begintime,
        "endtime": endtime,
        "begintimeFormatted": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(begintime)),
        "endtimeFormatted":   time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(endtime)),
        "usetimeSeconds": usetime,
        "distanceMeters": round(distance, 1),
    }


# ---------- introspection -----------------------------------------------------

@app.post("/v1/check")
def v1_check(body: dict):
    """Validate an sk token without revealing the plaintext config."""
    sk = body.get("token", "")
    try:
        cfg = resolve_config(sk)
    except HTTPException as e:
        if e.status_code == 401:
            return {"valid": False}
        raise
    return {
        "valid": True,
        "schoolNo": cfg.get("schoolNo"),
        "uidCount": len(uid_list(cfg)),
    }


@app.get("/tunnel-info")
def tunnel_info():
    try:
        out = subprocess.check_output(
            ["journalctl", "-u", "cloudflared-tunnel", "-n", "200", "--no-pager"],
            stderr=subprocess.STDOUT, timeout=5,
        ).decode("utf-8", "replace")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"error": str(e)}
    urls = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", out)
    return {"latestUrl": urls[-1] if urls else None, "allSeen": list(dict.fromkeys(urls))}


@app.get("/")
def root():
    return {"ok": True, "service": "hongqingting_runner proxy", "version": "2.0"}
