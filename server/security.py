"""Small ASGI boundary: bound API bodies before FastAPI parses JSON."""
import asyncio
import json
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from server.i18n import translate

MAX_BODY_BYTES = 64 * 1024
BODY_TIMEOUT_SECONDS = 10


def valid_origin(value, local_http=False):
    if not isinstance(value, str) or any(c.isspace() or c in ";'\\*" for c in value):
        return False
    try:
        url = urlsplit(value)
        _ = url.port  # Reject invalid/out-of-range ports too.
        secure = url.scheme == 'https' or (local_http and url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1'))
        return bool(secure and url.hostname and not (url.username or url.password or url.path or url.query or url.fragment))
    except ValueError:
        return False


class RequestBodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith('/api/'):
            return await self.app(scope, receive, send)
        headers = dict(scope['headers'])
        language = headers.get(b'accept-language', b'').decode('latin-1')

        async def reject(status, message):
            await JSONResponse({'detail': translate(message, language)}, status_code=status)(scope, receive, send)

        length = headers.get(b'content-length')
        if length is not None:
            try:
                if int(length) < 0:
                    raise ValueError
                if int(length) > MAX_BODY_BYTES:
                    return await reject(413, 'So‘rov hajmi juda katta.')
            except ValueError:
                return await reject(400, 'Maydonlarni tekshiring.')
        chunks, size = [], 0
        try:
            async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    size += len(chunk)
                    if size > MAX_BODY_BYTES:
                        return await reject(413, 'So‘rov hajmi juda katta.')
                    chunks.append(chunk)
                    if not message.get('more_body', False):
                        break
        except TimeoutError:
            return await reject(408, 'So‘rov vaqti tugadi.')
        body = b''.join(chunks)
        if body and headers.get(b'content-type', b'').split(b';')[0].strip().lower() == b'application/json':
            try:
                json.loads(body)
            except (ValueError, RecursionError):
                return await reject(422, 'Maydonlarni tekshiring.')

        async def replay():
            nonlocal body
            if body is not None:
                result, body = body, None
                return {'type': 'http.request', 'body': result, 'more_body': False}
            return await receive()

        await self.app(scope, replay, send)
