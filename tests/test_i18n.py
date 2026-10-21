import unittest
import test_api
from server import app as adapter
from server.i18n import language_code, translate


class LanguageTests(unittest.TestCase):
    def test_language_headers_and_fallback(self):
        for header, expected in [('en-US,en;q=0.9', 'en'), ('ru', 'ru'), ('uz-UZ', 'uz'), ('de', 'uz'), (None, 'uz')]:
            self.assertEqual(language_code(header), expected)

    def test_conflict_keeps_schedule_number(self):
        self.assertEqual(translate('Vaqt 12-jadval bilan kesishadi.', 'en'), 'The time overlaps schedule #12.')
        self.assertIn('№12', translate('Vaqt 12-jadval bilan kesishadi.', 'ru'))


class LocalizedAPITests(unittest.TestCase):
    setUp = test_api.APIIsolationTests.setUp
    tearDown = test_api.APIIsolationTests.tearDown
    def test_bootstrap_reads_bot_language(self):
        self.db.get_settings.return_value = {'name_clock_tz': 'Asia/Tashkent'}
        self.db.get_connection.return_value = None
        self.db.get_user_lang.return_value = 'ru'
        self.db.list_faq_entries.return_value = []
        self.db.list_kb_entries.return_value = []
        self.db.list_schedule_rules.return_value = []
        self.db.get_ai_usage.return_value = 0
        response = self.client.get('/api/bootstrap')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['language'], 'ru')
        self.db.get_user_lang.assert_called_once_with(123)
        self.db.set_user_lang.assert_not_called()

    def test_validation_is_localized(self):
        response = self.client.patch('/api/settings', json={'offline': 'false'}, headers={'Accept-Language': 'en-US'})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['detail'], 'Check the form fields.')

    def test_tariff_denial_is_localized(self):
        response = self.client.patch('/api/settings', json={'ai_enabled': True}, headers={'Accept-Language': 'ru'})
        self.assertEqual(response.status_code, 403)
        self.assertIn('тариф', response.json()['detail'])
        self.db.update_settings.assert_not_called()

    def test_unsigned_request_is_localized(self):
        adapter.app.dependency_overrides.clear()
        response = self.client.get('/api/bootstrap', headers={'Accept-Language': 'en'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], 'Open the app in Telegram or refresh your session.')

    def test_preview_preserves_reply_content(self):
        self.db.get_settings.return_value = {'auto_reply_text': 'User-authored original text', 'faq_enabled': False}
        self.logic.match_faq = lambda message, entries: None
        response = self.client.post('/api/test', json={'message': 'Hello'}, headers={'Accept-Language': 'ru'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'source': 'Обычный ответ', 'text': 'User-authored original text'})

    def test_browser_translation_files_are_served(self):
        for path in ['/i18n.js', '/translations.js']:
            self.assertEqual(self.client.get(path).status_code, 200)
