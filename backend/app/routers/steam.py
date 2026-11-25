"""Steam OpenID のアカウント連携と、ディスク内のプレイ状況。"""

from __future__ import annotations

import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from pymysql.err import IntegrityError

from ..config import PUBLIC_BASE_URL
from ..db import execute, fetch_one, transaction
from ..security import hash_token, rate_limit, require_user
from ..vendor.steamscordbot.disk import playing_title

router = APIRouter(prefix="/api/steam", tags=["steam"])
OPENID = "https://steamcommunity.com/openid/login"
NAMESPACE = "http://specs.openid.net/auth/2.0"
STEAM_ID = re.compile(r"https://steamcommunity\.com/openid/id/([0-9]{17})")
STATE = re.compile(r"[A-Za-z0-9_-]{43}")
COOKIE = "floppy_steam_link"
KEY = os.getenv("FLOPPY_STEAM_API_KEY", "").strip()
BASE = os.getenv("FLOPPY_STEAM_RETURN_BASE", PUBLIC_BASE_URL).strip().rstrip("/")
COOKIE_PATH = urlsplit(BASE).path + "/api/steam/"
ENABLED = bool(KEY and urlsplit(BASE).scheme == "https" and urlsplit(BASE).hostname)
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, str | None]] = {}
_SUMMARIES = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"


class SteamStateIn(BaseModel):
    state: str


class SteamVisibilityIn(BaseModel):
    show_in_disks: bool


def playing_games(steam_ids: list[str]) -> dict[str, str]:
    if not ENABLED or not steam_ids:
        return {}
    now = time.monotonic()
    with _CACHE_LOCK:
        missing = [steam_id for steam_id in steam_ids if _CACHE.get(steam_id, (0, None))[0] <= now]
    if missing:
        games = {}
        try:
            response = httpx.get(
                _SUMMARIES,
                params={"key": KEY, "steamids": ",".join(missing)},
                timeout=3,
            )
            response.raise_for_status()
            for profile in response.json()["response"]["players"]:
                if title := playing_title(profile):
                    games[profile["steamid"]] = title
            ttl = 60
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError):
            ttl = 30
        with _CACHE_LOCK:
            for expired in [key for key, entry in _CACHE.items() if entry[0] <= now]:
                del _CACHE[expired]
            _CACHE.update({steam_id: (now + ttl, games.get(steam_id)) for steam_id in missing})
    with _CACHE_LOCK:
        return {steam_id: title for steam_id in steam_ids
                if (entry := _CACHE.get(steam_id)) and entry[0] > now and (title := entry[1])}


def ensure_enabled() -> None:
    if not ENABLED:
        raise HTTPException(503, "Steam連携は準備中です。")


def return_to(state: str) -> str:
    return f"{BASE}/api/steam/callback?{urlencode({'state': state})}"


def browser_token(request: Request, state: str) -> tuple[str, str]:
    token = request.cookies.get(COOKIE, "")
    if not STATE.fullmatch(state) or not STATE.fullmatch(token):
        raise HTTPException(400, "Steam連携の有効期限が切れました。設定からやり直してください。")
    return hash_token(state), hash_token(token)


@router.get("")
def steam_settings(request: Request) -> dict:
    user_id = int(require_user(request)["id"])
    link = fetch_one("SELECT show_in_disks FROM steam_accounts WHERE user_id = %s", (user_id,))
    return {"available": ENABLED, "linked": bool(link), "show_in_disks": bool(link and link["show_in_disks"])}


@router.post("/start")
def start_link(request: Request, response: Response) -> dict:
    user_id = int(require_user(request)["id"])
    ensure_enabled()
    rate_limit(request, "steam_link", limit=10, window_seconds=600)
    state, token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with transaction() as cur:
        cur.execute("DELETE FROM steam_link_states WHERE expires_at <= UTC_TIMESTAMP()")
        cur.execute(
            """INSERT INTO steam_link_states (state_hash, browser_hash, user_id, expires_at)
               VALUES (%s, %s, %s, UTC_TIMESTAMP() + INTERVAL 10 MINUTE)""",
            (hash_token(state), hash_token(token), user_id),
        )
    response.set_cookie(COOKIE, token, max_age=600, path=COOKIE_PATH, httponly=True, secure=True, samesite="lax")
    params = {
        "openid.ns": NAMESPACE,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to(state),
        "openid.realm": f"{BASE}/",
        "openid.identity": NAMESPACE + "/identifier_select",
        "openid.claimed_id": NAMESPACE + "/identifier_select",
    }
    return {"url": OPENID + "?" + urlencode(params)}


@router.get("/callback")
def callback(request: Request, state: str = ""):
    ensure_enabled()
    state_hash, browser_hash = browser_token(request, state)
    fields = {key: value for key, value in request.query_params.items() if key.startswith("openid.")}
    if fields.get("openid.mode") == "cancel":
        return RedirectResponse(f"{BASE}/settings?steam=cancelled", status_code=303)

    match = STEAM_ID.fullmatch(fields.get("openid.claimed_id", ""))
    signed = set(fields.get("openid.signed", "").split(","))
    required = {"op_endpoint", "claimed_id", "identity", "return_to", "response_nonce", "assoc_handle"}
    nonce = fields.get("openid.response_nonce", "")
    try:
        nonce_at = datetime.strptime(nonce[:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        fresh_nonce = abs((datetime.now(timezone.utc) - nonce_at).total_seconds()) <= 600
    except ValueError:
        fresh_nonce = False
    if (
        not match or not required <= signed or not fresh_nonce
        or fields.get("openid.ns") != NAMESPACE or fields.get("openid.mode") != "id_res"
        or fields.get("openid.op_endpoint") != OPENID or fields.get("openid.identity") != match[0]
        or fields.get("openid.return_to") != return_to(state)
    ):
        raise HTTPException(400, "Steamからの応答を確認できませんでした。")

    pending = fetch_one(
        """SELECT 1 FROM steam_link_states WHERE state_hash = %s AND browser_hash = %s
             AND steam_id IS NULL AND expires_at > UTC_TIMESTAMP()""",
        (state_hash, browser_hash),
    )
    if not pending:
        raise HTTPException(400, "Steam連携の有効期限が切れました。")
    fields["openid.mode"] = "check_authentication"
    try:
        verified = httpx.post(OPENID, data=fields, timeout=5)
        verified.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "Steamに接続できません。設定からやり直してください。") from None
    if "is_valid:true" not in verified.text.splitlines():
        raise HTTPException(400, "Steamからの署名を確認できませんでした。")

    execute(
        """UPDATE steam_link_states SET steam_id = %s WHERE state_hash = %s AND browser_hash = %s
             AND steam_id IS NULL AND expires_at > UTC_TIMESTAMP()""",
        (match[1], state_hash, browser_hash),
    )
    return RedirectResponse(f"{BASE}/settings#steam={state}", status_code=303, headers={"Referrer-Policy": "no-referrer"})


@router.post("/complete")
def complete_link(request: Request, response: Response, payload: SteamStateIn) -> dict:
    user_id = int(require_user(request)["id"])
    ensure_enabled()
    state_hash, browser_hash = browser_token(request, payload.state)
    try:
        with transaction() as cur:
            cur.execute(
                """SELECT steam_id FROM steam_link_states WHERE state_hash = %s AND browser_hash = %s
                     AND user_id = %s AND steam_id IS NOT NULL AND expires_at > UTC_TIMESTAMP()
                   FOR UPDATE""",
                (state_hash, browser_hash, user_id),
            )
            linked = cur.fetchone()
            if not linked:
                raise HTTPException(400, "Steam連携を確認できませんでした。設定からやり直してください。")
            cur.execute("DELETE FROM steam_accounts WHERE user_id = %s", (user_id,))
            cur.execute("INSERT INTO steam_accounts (user_id, steam_id) VALUES (%s, %s)", (user_id, linked["steam_id"]))
            cur.execute("DELETE FROM steam_link_states WHERE state_hash = %s", (state_hash,))
    except IntegrityError as exc:
        if exc.args[0] != 1062:
            raise
        raise HTTPException(409, "このSteamアカウントは既に連携されています。") from None
    response.delete_cookie(COOKIE, path=COOKIE_PATH, secure=True, httponly=True, samesite="lax")
    return {"linked": True, "show_in_disks": False}


@router.post("/visibility")
def update_visibility(request: Request, payload: SteamVisibilityIn) -> dict:
    user_id = int(require_user(request)["id"])
    execute("UPDATE steam_accounts SET show_in_disks = %s WHERE user_id = %s", (payload.show_in_disks, user_id))
    return steam_settings(request)


@router.post("/disconnect")
def disconnect(request: Request) -> dict:
    user_id = int(require_user(request)["id"])
    with transaction() as cur:
        cur.execute("DELETE FROM steam_accounts WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM steam_link_states WHERE user_id = %s", (user_id,))
    return {"linked": False, "show_in_disks": False}
