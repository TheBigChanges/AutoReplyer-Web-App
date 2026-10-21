import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from server.auth import validate_init_data


def signed(token='test-token', **changes):
    data = {'auth_date': '1000', 'query_id': 'test-query', 'user': json.dumps({'id': 123, 'first_name': 'Test'})}
    data.update(changes)
    secret = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    check = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    return urlencode({**data, 'hash': hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()})


class AuthenticationTests(unittest.TestCase):
    def test_valid_signed_user(self):
        self.assertEqual(validate_init_data(signed(), 'test-token', now=1010)['id'], 123)

    def test_modified_identity_rejected(self):
        raw = signed().replace('123', '456')
        with self.assertRaises(ValueError):
            validate_init_data(raw, 'test-token', now=1010)

    def test_wrong_bot_and_expired_session_rejected(self):
        for token, now in [('wrong-token', 1010), ('test-token', 5000), ('test-token', 900)]:
            with self.subTest(token=token, now=now), self.assertRaises(ValueError):
                validate_init_data(signed(), token, now=now)

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            validate_init_data(signed() + '&user=%7B%22id%22%3A456%7D', 'test-token', now=1010)

    def test_non_integer_user_rejected(self):
        for user in ['{"id":true}', '{"id":"123"}', '[]', '{"id":-1}']:
            with self.subTest(user=user), self.assertRaises(ValueError):
                validate_init_data(signed(user=user), 'test-token', now=1010)


if __name__ == '__main__':
    unittest.main()
