"""Serve this independent Web App beside an unchanged AutoReplyer checkout.

Uses the bot's existing owner-scoped DB helpers, not Telegram polling/webhooks.
BOT_TOKEN and DATABASE_URL stay on the server. No schema migrations are run.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi import Path as PathParameter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from server.auth import validate_init_data
from server.i18n import translate
from server.security import RequestBodyLimit, valid_origin

logging.getLogger('httpx').setLevel(logging.WARNING)
app = FastAPI(title='AutoReplyer Web App API', docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(RequestBodyLimit)
DIST = Path(__file__).resolve().parents[1] / 'dist'
api_origins = json.loads((DIST / 'config.json').read_text())['apiOrigins']
# Origin tokens are deployment configuration, never request-header content.
if not isinstance(api_origins, list) or not all(valid_origin(origin) for origin in api_origins):
    raise RuntimeError('config.json apiOrigins must contain explicit HTTPS origins.')
origins = [v.strip() for v in os.getenv('WEBAPP_ORIGINS', '').split(',') if v.strip()]
if origins:
    if not all(valid_origin(origin, local_http=True) for origin in origins):
        raise RuntimeError('WEBAPP_ORIGINS requires explicit HTTPS origins (HTTP only for loopback development).')
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Content-Type', 'X-Telegram-Init-Data', 'Accept-Language'])


@app.exception_handler(StarletteHTTPException)
async def localized_http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={'detail': translate(str(exc.detail), request.headers.get('accept-language'))})


@app.exception_handler(RequestValidationError)
async def localized_validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        'detail': translate('Maydonlarni tekshiring.', request.headers.get('accept-language'))})

_modules = None
_module_lock = threading.Lock()


def modules():
    global _modules
    with _module_lock:
        if _modules is None:
            root = Path(os.environ.get('AUTOREPLYER_SOURCE', '')).resolve()
            if not os.environ.get('AUTOREPLYER_SOURCE') or not all((root / f).is_file() for f in ['db.py', 'logic.py', 'i18n.py', 'analytics.py']):
                raise HTTPException(503, 'AUTOREPLYER_SOURCE yangi AutoReplyer kodi papkasiga ko‘rsatilishi kerak.')
            sys.path.insert(0, str(root))
            _modules = tuple(importlib.import_module(name) for name in ['db', 'logic', 'analytics'])
        return _modules


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Settings(Input):
    offline: StrictBool | None = None
    cooldown_hours: float | None = Field(None, ge=1 / 60, le=8760, allow_inf_nan=False, strict=True)
    auto_reply_text: str | None = Field(None, min_length=1, max_length=500)
    sleep_mode_enabled: StrictBool | None = None
    sleep_start_minutes: int | None = Field(None, ge=0, le=1439, strict=True)
    sleep_end_minutes: int | None = Field(None, ge=0, le=1439, strict=True)
    sleep_reply_text: str | None = Field(None, min_length=1, max_length=500)
    ai_enabled: StrictBool | None = None
    ai_role: Literal['assistant', 'seller', 'support', 'friend', 'developer', 'business'] | None = None
    ai_info: str | None = Field(None, max_length=2000)
    faq_enabled: StrictBool | None = None
    kb_enabled: StrictBool | None = None
    scheduler_enabled: StrictBool | None = None


class Keywords(Input):
    keywords: list[str] = Field(min_length=1, max_length=10)

    @field_validator('keywords')
    @classmethod
    def keywords_valid(cls, values):
        cleaned = list(dict.fromkeys(v.strip() for v in values))
        if any(not v or len(v) > 40 for v in cleaned):
            raise ValueError('Kalit so‘z 1–40 belgi bo‘lishi kerak.')
        return cleaned


class FAQ(Keywords):
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=1000)


class Knowledge(Keywords):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=1000)


class Schedule(Input):
    days: int = Field(ge=1, le=127, strict=True)
    start_min: int = Field(ge=0, le=1439, strict=True)
    end_min: int = Field(ge=0, le=1440, strict=True)
    text: str | None = Field(None, max_length=500)


class EntryState(Input):
    is_enabled: StrictBool


class TestMessage(Input):
    message: str = Field(min_length=1, max_length=1000)


_rate_lock = threading.Lock()
_requests = {}
_membership = {}


def identity(x_telegram_init_data: Annotated[str, Header()] = ''):
    try:
        user = validate_init_data(x_telegram_init_data, os.environ.get('BOT_TOKEN', ''))
    except ValueError as exc:
        raise HTTPException(401, str(exc)) from exc
    uid = user['id']
    now = time.monotonic()
    with _rate_lock:
        if len(_requests) > 10000:
            for key in list(_requests):
                if now - _requests[key][0] >= 60:
                    del _requests[key]
        start, count = _requests.get(uid, (now, 0))
        start, count = (now, 0) if now - start >= 60 else (start, count)
        if count >= 120:
            raise HTTPException(429, 'Juda ko‘p so‘rov. Bir oz kuting.')
        _requests[uid] = (start, count + 1)
    db, _, _ = modules()
    if db.get_block(uid):
        raise HTTPException(403, 'Hisob cheklangan. Botdagi yordam bo‘limiga murojaat qiling.')
    channel = os.environ.get('REQUIRED_CHANNEL_ID')
    if channel and str(uid) != os.getenv('ADMIN_ID'):
        cached = _membership.get(uid)
        if not cached or now - cached[0] >= 30:
            try:
                response = httpx.get(f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/getChatMember", params={'chat_id': channel, 'user_id': uid}, timeout=8).json()
                member = response.get('result', {})
                allowed = response.get('ok') and (member.get('status') in ['creator', 'administrator', 'member'] or (member.get('status') == 'restricted' and member.get('is_member')))
            except Exception:
                raise HTTPException(503, 'Kanal obunasini tekshirish imkoni bo‘lmadi.') from None
            if len(_membership) > 10000:
                _membership.clear()
            _membership[uid] = (now, bool(allowed))
        else:
            allowed = cached[1]
        if not allowed:
            raise HTTPException(403, 'Avval botda ko‘rsatilgan kanalga obuna bo‘ling.')
    return user


User = Annotated[dict, Depends(identity)]
EntryId = Annotated[int, PathParameter(ge=1, le=2147483647)]


def plan(uid):
    db, _, _ = modules()
    value = 'ultra' if str(uid) == os.getenv('ADMIN_ID') else db.get_user_plan(uid)
    return value if value in ('free', 'plus', 'pro', 'ultra') else 'free'


def require(uid, feature):
    p = plan(uid)
    allowed = {'custom': ['plus', 'pro', 'ultra'], 'faq': ['plus', 'pro', 'ultra'], 'knowledge': ['ultra'], 'ai': ['ultra'], '7': ['plus', 'pro', 'ultra'], '30': ['pro', 'ultra']}
    if p not in allowed.get(feature, ()):
        raise HTTPException(403, 'Bu imkoniyat uchun yuqoriroq tarif kerak. Tarifni botda yangilang.')
    return p


def user_zone(settings):
    try:
        return ZoneInfo(settings.get('name_clock_tz') or 'Asia/Tashkent')
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return ZoneInfo('Asia/Tashkent')


@app.middleware('http')
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self' https://telegram.org; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
        "connect-src 'self' " + ' '.join(api_origins) + "; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org"
    )
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path == '/' or request.url.path.endswith(('.html', '.js', '.css', '.json')):
        response.headers['Cache-Control'] = 'no-cache'
    return response


@app.get('/api/health')
def health():
    revision = os.environ.get('RENDER_GIT_COMMIT', '')
    return {'status': 'ok', 'service': 'autoreplyer-webapp',
            'revision': revision if re.fullmatch(r'[0-9a-f]{40}', revision) else None}


@app.get('/api/bootstrap')
def bootstrap(user: User):
    db, _, _ = modules()
    uid = user['id']
    settings = db.get_settings(uid)
    connection = db.get_connection(uid)
    # get_connection uses a RealDictCursor in the current upstream version.
    if connection and not isinstance(connection, dict):
        raise HTTPException(503, 'AutoReplyer kodi versiyasi mos emas.')
    zone = user_zone(settings)
    bot_language = db.get_user_lang(uid)
    return {'user': {'id': uid, 'first_name': user.get('first_name', 'Foydalanuvchi')},
            'language': bot_language if bot_language in ('uz', 'ru', 'en') else user.get('language_code', 'uz'),
            'plan': plan(uid), 'connection': {k: connection.get(k) for k in ['is_enabled', 'can_reply']} if connection else None, 'settings': settings, 'faq': db.list_faq_entries(uid), 'knowledge': db.list_kb_entries(uid), 'schedules': db.list_schedule_rules(uid), 'ai_usage': db.get_ai_usage(uid, datetime.now(zone).date().isoformat())}


@app.patch('/api/settings')
def settings_update(body: Settings, user: User):
    db, _, _ = modules()
    values = body.model_dump(exclude_unset=True)
    if not values or any(v is None for v in values.values()):
        raise HTTPException(422, 'Sozlamalar bo‘sh yoki null bo‘lishi mumkin emas.')
    for key in values:
        if key in ['auto_reply_text', 'sleep_reply_text']:
            require(user['id'], 'custom')
        elif key.startswith('ai_'):
            require(user['id'], 'ai')
        elif key in ['faq_enabled', 'kb_enabled']:
            require(user['id'], 'faq' if key == 'faq_enabled' else 'knowledge')
    db.update_settings(user['id'], **values)
    return {'ok': True}


def item_prefix(kind):
    return 'kb' if kind == 'knowledge' else 'faq'


def item_limit(uid, kind):
    p = require(uid, kind)
    return 55 if kind == 'knowledge' else {'plus': 15, 'pro': 30, 'ultra': 65}[p]


def save_item(kind, body, user, entry_id=None):
    db, _, _ = modules()
    uid = user['id']
    limit = item_limit(uid, kind)
    values = body.model_dump()
    prefix = item_prefix(kind)
    if entry_id is None:
        result = getattr(db, f'add_{prefix}_entry')(uid, **values, max_entries=limit)
        if result is None:
            raise HTTPException(409, 'Tarifingizdagi yozuvlar limiti to‘lgan.')
        return {'id': result}
    if not getattr(db, f'update_{prefix}_entry')(uid, entry_id, **values):
        raise HTTPException(404, 'Yozuv topilmadi.')
    return {'id': entry_id}


@app.post('/api/faq')
def create_faq(body: FAQ, user: User):
    return save_item('faq', body, user)


@app.patch('/api/faq/{entry_id}')
def edit_faq(entry_id: EntryId, body: FAQ, user: User):
    return save_item('faq', body, user, entry_id)


@app.post('/api/knowledge')
def create_knowledge(body: Knowledge, user: User):
    return save_item('knowledge', body, user)


@app.patch('/api/knowledge/{entry_id}')
def edit_knowledge(entry_id: EntryId, body: Knowledge, user: User):
    return save_item('knowledge', body, user, entry_id)


def schedule_result(result):
    status, value = result
    if status == 'limit':
        raise HTTPException(409, 'Jadvallar limiti to‘lgan.')
    if status == 'conflict':
        raise HTTPException(409, f'Vaqt {value}-jadval bilan kesishadi.')
    if status == 'gone':
        raise HTTPException(404, 'Jadval topilmadi.')
    return {'id': value, 'ok': True}


def check_schedule(body, user):
    if body.text:
        require(user['id'], 'custom')
    _, logic, _ = modules()
    if not logic.valid_schedule_time(body.start_min, body.end_min):
        raise HTTPException(422, 'Kun bo‘yi uchun 00:00 — 00:00 kiriting.')


@app.post('/api/schedule')
def create_schedule(body: Schedule, user: User):
    db, logic, _ = modules()
    check_schedule(body, user)
    return schedule_result(db.add_schedule_rule(user['id'], **body.model_dump(), max_rules=logic.SCHEDULE_PLAN_LIMITS.get(plan(user['id']), 1)))


@app.patch('/api/schedule/{entry_id}')
def edit_schedule(entry_id: EntryId, body: Schedule, user: User):
    db, _, _ = modules()
    check_schedule(body, user)
    return schedule_result(db.update_schedule_rule(user['id'], entry_id, **body.model_dump()))


@app.post('/api/{kind}/{entry_id}/toggle')
def toggle(kind: Literal['faq', 'knowledge', 'schedule'], entry_id: EntryId, body: EntryState, user: User):
    db, _, _ = modules()
    uid = user['id']
    # Explicit state is idempotent across tabs, workers and retried requests.
    # Schedule validation/cache invalidation stay inside the upstream transaction.
    if kind == 'schedule':
        result = schedule_result(db.update_schedule_rule(uid, entry_id, is_enabled=body.is_enabled))
        return {**result, 'id': entry_id, 'is_enabled': body.is_enabled}
    item_limit(uid, kind)
    if not getattr(db, f'set_{item_prefix(kind)}_entry_enabled')(uid, entry_id, body.is_enabled):
        raise HTTPException(404, 'Yozuv topilmadi.')
    return {'is_enabled': body.is_enabled}


@app.delete('/api/{kind}/{entry_id}')
def delete(kind: Literal['faq', 'knowledge', 'schedule'], entry_id: EntryId, user: User):
    db, _, _ = modules()
    # Allow owners to delete their saved data even after a plan downgrade.
    fn = db.delete_schedule_rule if kind == 'schedule' else getattr(db, f'delete_{item_prefix(kind)}_entry')
    if not fn(user['id'], entry_id):
        raise HTTPException(404, 'Yozuv topilmadi.')
    return {'ok': True}


@app.get('/api/analytics')
def analytics(user: User, days: int = Query(1)):
    if days not in [1, 7, 30]:
        raise HTTPException(422, 'Davr 1, 7 yoki 30 kun bo‘lishi kerak.')
    uid = user['id']
    if days > 1:
        require(uid, str(days))
    db, _, reports = modules()
    settings = db.get_settings(uid)
    zone = user_zone(settings)
    start = reports.period_start(days, zone).timestamp()
    summary = reports.summarize(db.get_analytics_rows(uid, start), days, zone)
    if days == 1:
        series = {'inc': summary['hourly'], 'sent': summary['hourly_sent'], 'labels': [f'{n:02d}' for n in range(24)]}
    else:
        series = {'inc': [r[1] for r in summary['daily']], 'sent': [r[2] for r in summary['daily']], 'labels': [r[0].strftime('%d.%m') for r in summary['daily']]}
    p = plan(uid)
    kinds = {key: summary['kinds'][key] for key in ('ai', 'faq', 'static', 'sleep')} if p in ('pro', 'ultra') else {'ai': summary['kinds']['ai']}
    return {'incoming': summary['incoming'], 'sent': summary['sent'], 'kinds': kinds, 'peak': summary['peak'], 'skipped': summary['skipped'] if p == 'ultra' else None, 'series': series if p != 'free' else None}


@app.post('/api/test')
def test_reply(body: TestMessage, user: User, request: Request):
    db, logic, _ = modules()
    uid = user['id']
    settings = db.get_settings(uid)
    limit = {'plus': 15, 'pro': 30, 'ultra': 65}.get(plan(uid), 0)
    entries = db.get_enabled_faq_entries(uid)[:limit] if settings.get('faq_enabled') and limit else []
    match = logic.match_faq(body.message, entries)
    # Preview only: does not consume AI quota or send Telegram messages.
    return {'source': 'Smart FAQ' if match else translate('Oddiy javob', request.headers.get('accept-language')),
            'text': match['answer'] if match else settings.get('auto_reply_text') or db.DEFAULT_AUTO_REPLY_TEXT}


app.mount('/', StaticFiles(directory=DIST, html=True), name='webapp')

