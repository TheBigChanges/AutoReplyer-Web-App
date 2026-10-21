"""Translations for API status messages, independent of user-authored content."""
import re


def language_code(value: str | None) -> str:
    code = (value or '').split(',')[0].split(';')[0].split('-')[0].lower().strip()
    return code if code in ('uz', 'ru', 'en') else 'uz'


MESSAGES = {
    'Telegram orqali oching yoki sessiyani yangilang.': ('Откройте приложение в Telegram или обновите сеанс.', 'Open the app in Telegram or refresh your session.'),
    'Telegram sessiyasi yaroqsiz yoki eskirgan. Ilovani qayta oching.': ('Сеанс Telegram недействителен или устарел. Откройте приложение заново.', 'Your Telegram session is invalid or expired. Reopen the app.'),
    'Juda ko‘p so‘rov. Bir oz kuting.': ('Слишком много запросов. Немного подождите.', 'Too many requests. Please wait a moment.'),
    'Hisob cheklangan. Botdagi yordam bo‘limiga murojaat qiling.': ('Аккаунт ограничен. Обратитесь в раздел помощи бота.', 'This account is restricted. Contact support in the bot.'),
    'Kanal obunasini tekshirish imkoni bo‘lmadi.': ('Не удалось проверить подписку на канал.', 'Could not verify channel membership.'),
    'Avval botda ko‘rsatilgan kanalga obuna bo‘ling.': ('Сначала подпишитесь на канал, указанный в боте.', 'First join the channel shown in the bot.'),
    'Bu imkoniyat uchun yuqoriroq tarif kerak. Tarifni botda yangilang.': ('Для этой функции нужен более высокий тариф. Обновите тариф в боте.', 'This feature requires a higher plan. Upgrade your plan in the bot.'),
    'AutoReplyer kodi versiyasi mos emas.': ('Версия кода AutoReplyer несовместима.', 'The AutoReplyer source version is incompatible.'),
    'AUTOREPLYER_SOURCE yangi AutoReplyer kodi papkasiga ko‘rsatilishi kerak.': ('AUTOREPLYER_SOURCE должен указывать на папку с актуальным кодом AutoReplyer.', 'AUTOREPLYER_SOURCE must point to a current AutoReplyer source directory.'),
    'Sozlamalar bo‘sh yoki null bo‘lishi mumkin emas.': ('Настройки не могут быть пустыми или null.', 'Settings cannot be empty or null.'),
    'Tarifingizdagi yozuvlar limiti to‘lgan.': ('Достигнут лимит записей вашего тарифа.', 'Your plan’s entry limit has been reached.'),
    'Yozuv topilmadi.': ('Запись не найдена.', 'Entry not found.'),
    'Jadvallar limiti to‘lgan.': ('Достигнут лимит расписаний.', 'The schedule limit has been reached.'),
    'Jadval topilmadi.': ('Расписание не найдено.', 'Schedule not found.'),
    'Kun bo‘yi uchun 00:00 — 00:00 kiriting.': ('Для целого дня укажите 00:00 — 00:00.', 'For an all-day schedule, enter 00:00 — 00:00.'),
    'Davr 1, 7 yoki 30 kun bo‘lishi kerak.': ('Период должен составлять 1, 7 или 30 дней.', 'The period must be 1, 7, or 30 days.'),
    'Maydonlarni tekshiring.': ('Проверьте заполненные поля.', 'Check the form fields.'),
    'Oddiy javob': ('Обычный ответ', 'Standard reply'),
    'Not Found': ('Не найдено.', 'Not found.'),
    'Method Not Allowed': ('Метод не поддерживается.', 'Method not allowed.'),
}


def translate(message: str, language: str | None) -> str:
    lang = language_code(language)
    if lang == 'uz':
        return message
    conflict = re.fullmatch(r'Vaqt (\d+)-jadval bilan kesishadi\.', message)
    if conflict:
        number = conflict.group(1)
        return f'Время пересекается с расписанием №{number}.' if lang == 'ru' else f'The time overlaps schedule #{number}.'
    return MESSAGES.get(message, (message, message))[0 if lang == 'ru' else 1]
