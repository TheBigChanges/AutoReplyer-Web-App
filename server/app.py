"""Serve this independent Web App beside an unchanged AutoReplyer checkout.

Uses the bot's existing owner-scoped DB helpers, not Telegram polling/webhooks.
BOT_TOKEN and DATABASE_URL stay on the server. No schema migrations are run.
"""
from __future__ import annotations

import importlib
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

from server.auth import validate_init_data

logging.getLogger('httpx').setLevel(logging.WARNING)
app = FastAPI(title='AutoReplyer Web App API', docs_url=None, redoc_url=None)
origins = [v.strip() for v in os.getenv('WEBAPP_ORIGINS', '').split(',') if v.strip()]
if origins:
    if '*' in origins:
        raise RuntimeError('WEBAPP_ORIGINS requires explicit HTTPS origins, not *.')
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Content-Type', 'X-Telegram-Init-Data'])

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
    cooldown_hours: float | None = Field(None, ge=1 / 60, le=8760, allow_inf_nan=False)
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


def plan(uid):
    db, _, _ = modules()
    return 'ultra' if str(uid) == os.getenv('ADMIN_ID') else db.get_user_plan(uid)


def require(uid, feature):
    p = plan(uid)
    allowed = {'custom': ['plus', 'pro', 'ultra'], 'faq': ['plus', 'pro', 'ultra'], 'knowledge': ['ultra'], 'ai': ['ultra'], '7': ['plus', 'pro', 'ultra'], '30': ['pro', 'ultra']}
    if p not in allowed.get(feature, [p]):
        raise HTTPException(403, 'Bu imkoniyat uchun yuqoriroq tarif kerak. Tarifni botda yangilang.')
    return p


@app.middleware('http')
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'autoreplyer-webapp'}


@app.get('/api/bootstrap')
def bootstrap(user: User):
    db, _, _ = modules()
    uid = user['id']
    settings = db.get_settings(uid)
    connection = db.get_connection(uid)
    # get_connection uses a RealDictCursor in the current upstream version.
    if connection and not isinstance(connection, dict):
        raise HTTPException(503, 'AutoReplyer kodi versiyasi mos emas.')
    zone = ZoneInfo(settings.get('name_clock_tz') or 'Asia/Tashkent')
    return {'user': {'id': uid, 'first_name': user.get('first_name', 'Foydalanuvchi')}, 'plan': plan(uid), 'connection': {k: connection.get(k) for k in ['is_enabled', 'can_reply']} if connection else None, 'settings': settings, 'faq': db.list_faq_entries(uid), 'knowledge': db.list_kb_entries(uid), 'schedules': db.list_schedule_rules(uid), 'ai_usage': db.get_ai_usage(uid, datetime.now(zone).date().isoformat())}


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
def edit_faq(entry_id: int, body: FAQ, user: User):
    return save_item('faq', body, user, entry_id)


@app.post('/api/knowledge')
def create_knowledge(body: Knowledge, user: User):
    return save_item('knowledge', body, user)


@app.patch('/api/knowledge/{entry_id}')
def edit_knowledge(entry_id: int, body: Knowledge, user: User):
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
def edit_schedule(entry_id: int, body: Schedule, user: User):
    db, _, _ = modules()
    check_schedule(body, user)
    return schedule_result(db.update_schedule_rule(user['id'], entry_id, **body.model_dump()))


@app.post('/api/{kind}/{entry_id}/toggle')
def toggle(kind: Literal['faq', 'knowledge', 'schedule'], entry_id: int, user: User):
    db, _, _ = modules()
    uid = user['id']
    if kind == 'schedule':
        rule = db.get_schedule_rule(uid, entry_id)
        if not rule:
            raise HTTPException(404, 'Jadval topilmadi.')
        return schedule_result(db.update_schedule_rule(uid, entry_id, is_enabled=not rule['is_enabled']))
    item_limit(uid, kind)
    result = getattr(db, f'toggle_{item_prefix(kind)}_entry')(uid, entry_id)
    if result is None:
        raise HTTPException(404, 'Yozuv topilmadi.')
    return {'is_enabled': result}


@app.delete('/api/{kind}/{entry_id}')
def delete(kind: Literal['faq', 'knowledge', 'schedule'], entry_id: int, user: User):
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
    zone = ZoneInfo(settings.get('name_clock_tz') or 'Asia/Tashkent')
    start = reports.period_start(days, zone).timestamp()
    summary = reports.summarize(db.get_analytics_rows(uid, start), days, zone)
    if days == 1:
        series = {'inc': summary['hourly'], 'sent': summary['hourly_sent'], 'labels': [f'{n:02d}' for n in range(24)]}
    else:
        series = {'inc': [r[1] for r in summary['daily']], 'sent': [r[2] for r in summary['daily']], 'labels': [r[0].strftime('%d.%m') for r in summary['daily']]}
    p = plan(uid)
    return {'incoming': summary['incoming'], 'sent': summary['sent'], 'kinds': summary['kinds'], 'peak': summary['peak'], 'skipped': summary['skipped'] if p == 'ultra' else None, 'series': series if p != 'free' else None}


@app.post('/api/test')
def test_reply(body: TestMessage, user: User):
    db, logic, _ = modules()
    uid = user['id']
    settings = db.get_settings(uid)
    entries = db.get_enabled_faq_entries(uid) if settings.get('faq_enabled') and plan(uid) in ['plus', 'pro', 'ultra'] else []
    match = logic.match_faq(body.message, entries)
    # Preview only: does not consume AI quota or send Telegram messages.
    return {'source': 'Smart FAQ' if match else 'Oddiy javob', 'text': match['answer'] if match else settings.get('auto_reply_text') or db.DEFAULT_AUTO_REPLY_TEXT}


app.mount('/', StaticFiles(directory=Path(__file__).resolve().parents[1] / 'dist', html=True), name='webapp')
