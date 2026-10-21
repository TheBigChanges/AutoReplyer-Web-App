"""Validate Telegram Mini App initData. No client-supplied identity is trusted."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def validate_init_data(raw: str, token: str, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    if not token or not raw or len(raw) > 16384:
        raise ValueError('Telegram orqali oching yoki sessiyani yangilang.')
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True)
        fields = dict(pairs)
        if len(fields) != len(pairs):
            raise ValueError('duplicate fields')
        received = fields.pop('hash')
        # Telegram's HMAC validation includes every field except hash.
        check = '\n'.join(f'{key}={value}' for key, value in sorted(fields.items()))
        secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
        expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, received):
            raise ValueError('signature')
        age = now - int(fields['auth_date'])
        if not -30 <= age <= 3600:
            raise ValueError('expired')
        user = json.loads(fields['user'])
        if not isinstance(user, dict) or type(user.get('id')) is not int or user['id'] <= 0:
            raise ValueError('user')
        return user
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Telegram sessiyasi yaroqsiz yoki eskirgan. Ilovani qayta oching.') from exc
