"""
hongqingting_runner — FastAPI proxy backend.

Three teaching endpoints. The frontend (GitHub Pages) sends a config + form values
here; this process does the gzip / MD5 / header / trajectory time-stamp work that a
browser cannot do, then forwards to whatever target the JSON config points at.
The response includes the assembled raw payload so the frontend's teaching panel
can show students what was actually sent on the wire.
"""

import gzip
import hashlib
import json
import random
import re
import time
import urllib.parse
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ANDROID_UA = "Dalvik/2.1.0 (Linux; U; Android 12; LIO-AN00 Build/PQ3B.190801.002)"
OKHTTP_UA = "okhttp/5.0.0-alpha.10"
HTTP_TIMEOUT = 30.0

app = FastAPI(title="hongqingting_runner proxy", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


# ---------- /proxy/auth -------------------------------------------------------

class AuthIn(BaseModel):
    authUrl: str
    schoolNo: str
    passwordPrefix: str = "Stu"
    studentNo: str


@app.post("/proxy/auth")
async def proxy_auth(body: AuthIn):
    plain = body.passwordPrefix + body.studentNo
    md5pw = md5_hex(plain)
    name_list = f"['bangding','{body.schoolNo}','student','{body.studentNo}','{md5pw}']"
    form_body = "name=" + urllib.parse.quote(name_list, safe="")
    headers = {
        "User-Agent": ANDROID_UA,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Length": str(len(form_body)),
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as cli:
        try:
            r = await cli.post(body.authUrl, headers=headers, content=form_body)
        except httpx.RequestError as e:
            raise HTTPException(502, f"upstream error: {e}")
    return {
        "upstreamStatus": r.status_code,
        "upstreamBody": r.text,
        "debug": {
            "plainPassword": plain,
            "md5Password": md5pw,
            "formBodyDecoded": name_list,
            "formBodyEncoded": form_body,
            "headers": headers,
            "url": body.authUrl,
        },
    }


# ---------- /proxy/summary ----------------------------------------------------

class SummaryIn(BaseModel):
    summaryUrl: str
    schoolNo: str
    studentNo: str
    queryUid: str


@app.post("/proxy/summary")
async def proxy_summary(body: SummaryIn):
    payload = (
        "{'studentno':" + body.studentNo
        + ",'uid':'" + body.queryUid + "'"
        + ",'schoolno':'" + body.schoolNo + "'}"
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
            r = await cli.post(body.summaryUrl, headers=headers, content=gz)
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
        "debug": {
            "rawPayload": payload,
            "gzipLength": len(gz),
            "headers": headers,
            "url": body.summaryUrl,
        },
    }


# ---------- /proxy/upload -----------------------------------------------------

class UploadIn(BaseModel):
    uploadUrl: str
    schoolNo: str
    studentNo: str
    uid: str
    distance: float            # meters
    locationText: str          # raw location_*km file contents
    dayOffset: float = 1.0     # how many days back the run "happened"
    baseUseTime: int = 5800    # baseline run duration in seconds
    useTimeJitter: int = 600
    eventNo: str = "803"
    atttype: str = "3"
    pointstatus: str = "1"


def rewrite_trajectory(text: str, begintime: int, usetime: int) -> str:
    """Replace each frame's timestamp so the trajectory looks like a real-time
    capture across [begintime, begintime+usetime]. Mirrors hongqingting.py."""
    frames = re.findall(r".*?@", text)
    if not frames:
        raise HTTPException(400, "locationText is empty or has no frames")
    delta = usetime / len(frames)
    runtime = float(begintime)
    out = []
    for fr in frames:
        m = re.search(r"(?P<loc>.*?);.*?;", fr)
        if not m:
            continue
        loc = m.group("loc")
        rewritten = re.sub(
            r".*?;.*?;null;null;",
            f"{loc};{int(runtime)};null;null;",
            fr,
        )
        out.append(rewritten)
        runtime += delta
    joined = "".join(out)
    return re.sub(r".$", "", joined)  # strip trailing '@'


@app.post("/proxy/upload")
async def proxy_upload(body: UploadIn):
    if body.dayOffset != 0:
        begintime = int(time.time() - 86400 * body.dayOffset + random.randint(1, 3600))
        endtime = begintime + body.baseUseTime + random.randint(1, body.useTimeJitter)
    else:
        endtime = int(time.time() - random.randint(1, 3600))
        begintime = endtime - body.baseUseTime - random.randint(1, body.useTimeJitter)

    usetime = endtime - begintime - random.randint(1, 10)
    if usetime <= 0:
        raise HTTPException(400, "computed usetime <= 0; widen baseUseTime")

    distance = body.distance + random.uniform(-50.0, 50.0)
    speed = (usetime / 60) / (distance / 1000)  # min/km

    location = rewrite_trajectory(body.locationText, begintime, usetime)

    upload_payload = (
        "{'begintime':'" + str(begintime)
        + "','endtime':'" + str(endtime)
        + "','uid':'" + body.uid
        + "','schoolno':'" + body.schoolNo
        + "','distance':'" + f"{distance:.1f}"
        + "','speed':'" + str(speed)
        + "','studentno':'" + body.studentNo
        + "','atttype':'" + body.atttype
        + "','eventno':'" + body.eventNo
        + "','location':'" + location
        + "','pointstatus':'" + body.pointstatus
        + "','usetime':'" + str(usetime)
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
            r = await cli.post(body.uploadUrl, headers=headers, content=gz)
        except httpx.RequestError as e:
            raise HTTPException(502, f"upstream error: {e}")

    return {
        "upstreamStatus": r.status_code,
        "upstreamBody": r.text,
        "debug": {
            "begintime": begintime,
            "endtime": endtime,
            "begintimeFormatted": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(begintime)),
            "endtimeFormatted": time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(endtime)),
            "usetimeSeconds": usetime,
            "distanceMeters": round(distance, 1),
            "speedMinPerKm": round(speed, 4),
            "frameCount": len(re.findall(r".*?@", body.locationText)),
            "rawPayload": upload_payload,
            "gzipLength": len(gz),
            "headers": headers,
            "url": body.uploadUrl,
        },
    }


# ---------- /tunnel-info -------------------------------------------------------

@app.get("/tunnel-info")
def tunnel_info():
    """Read cloudflared journal to surface the current trycloudflare URL."""
    import subprocess
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
    return {"ok": True, "service": "hongqingting_runner proxy"}
