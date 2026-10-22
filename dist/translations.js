// Source text, Russian, English. User-authored replies and knowledge are never translated.
const rows = `
API manzili ishonchli ro‘yxatda yo‘q. Administrator bilan bog‘laning.|Адрес API отсутствует в списке доверенных. Обратитесь к администратору.|The API address is not trusted. Contact the administrator.
Umumiy ko‘rinish|Обзор|Overview
Avtojavob|Автоответ|Auto-reply
AI yordamchi|ИИ-помощник|AI assistant
Bilimlar bazasi|База знаний|Knowledge base
Smart jadval|Умное расписание|Smart scheduler
Statistika|Статистика|Analytics
Uyqu rejimi|Режим сна|Sleep mode
Profil vositalari|Инструменты профиля|Profile tools
Sozlamalar|Настройки|Settings
Tariflar|Тарифы|Plans
Yordam markazi|Центр помощи|Help center
Asosiy|Главная|Home
Jadval|Расписание|Schedule
Shaxsiy kabinet|Личный кабинет|My workspace
Namoyish hisobi|Демонстрационный аккаунт|Demo account
BOSHQARUV|УПРАВЛЕНИЕ|MANAGEMENT
Asosiy menyu|Основное меню|Main navigation
Mobil menyu|Мобильное меню|Mobile navigation
Imkoniyatlaringizni kengaytiring|Откройте больше возможностей|Unlock more features
Biznesingiz uchun aqlli yordamchi.|Умный помощник для вашего бизнеса.|A smart assistant for your business.
Tariflarni ko‘rish|Посмотреть тарифы|View plans
Tariflarni ko‘rish ↗|Посмотреть тарифы ↗|View plans ↗
Rang mavzusini almashtirish|Сменить тему|Switch theme
Rang mavzusi|Цветовая тема|Color theme
Hisob sozlamalari|Настройки аккаунта|Account settings
Siz band bo‘ling. Javoblarni bizga qoldiring.|Занимайтесь делами. Ответы оставьте нам.|Stay focused. Leave the replies to us.
Yangiliklar|Новости|Updates
Yangiliklar ↗|Новости ↗|Updates ↗
Demo rejim|Деморежим|Demo mode
Demo|Демо|Demo
— namunaviy ma’lumotlar. O‘zgarishlar faqat shu qurilmada saqlanadi.|— пример данных. Изменения сохраняются только на этом устройстве.|— sample data. Changes are saved only on this device.
Botni ulash|Подключить бота|Connect bot
Botni ulash ↗|Подключить бота ↗|Connect bot ↗
Telegram orqali tasdiqlangan|Подтверждено через Telegram|Verified by Telegram
— o‘zgarishlar bot hisobingizga saqlanadi.|— изменения сохраняются в аккаунте бота.|— changes are saved to your bot account.
Hisob ↗|Аккаунт ↗|Account ↗
Botga ulanish talab etiladi|Требуется подключение к боту|Bot connection required
Ulanishni sozlash|Настроить подключение|Set up connection
Ulanishni sozlash ↗|Настроить подключение ↗|Set up connection ↗
Hisobga ulanish|Подключение аккаунта|Connect your account
Haqiqiy sozlamalarni ochish uchun API bilan ulaning.|Подключите API, чтобы открыть настройки аккаунта.|Connect the API to access your account settings.
API bilan aloqa o‘rnatilmadi|Не удалось подключиться к API|Could not connect to the API
API manzilini sozlang yoki demo rejimini tanlab ilovani ko‘rib chiqing.|Укажите адрес API или ознакомьтесь с приложением в деморежиме.|Set the API address or explore the app in demo mode.
Demoni ochish|Открыть демо|Open demo
Telegram hisobingiz tekshirilmoqda…|Проверяем ваш аккаунт Telegram…|Verifying your Telegram account…
SIZNING BOSHQARUV MARKAZINGIZ|ВАШ ЦЕНТР УПРАВЛЕНИЯ|YOUR CONTROL CENTER
Salom, {0}|Здравствуйте, {0}|Hello, {0}
Sizning vaqtingiz qadrli. Muloqotlaringiz esa ishonchli qo‘llarda.|Ваше время ценно. Ваше общение — в надёжных руках.|Your time matters. Your conversations are in good hands.
Botni ochish|Открыть бота|Open bot
Javobni sinash|Проверить ответ|Test reply
SIZNING SHAXSIY YORDAMCHINGIZ|ВАШ ЛИЧНЫЙ ПОМОЩНИК|YOUR PERSONAL ASSISTANT
Siz band bo‘lsangiz ham, aloqada qoling.|Оставайтесь на связи, даже когда заняты.|Stay connected, even when you’re busy.
Avtojavoblar, aqlli yordamchi va rejalashtirilgan xabarlar.|Автоответы, умный помощник и сообщения по расписанию.|Auto-replies, a smart assistant, and scheduled messages.
Mijozlaringizning hech bir murojaati e’tiborsiz qolmasin.|Пусть ни одно обращение клиента не останется без внимания.|Give every customer message the attention it deserves.
Avtojavobni sozlash|Настроить автоответ|Configure auto-reply
Avtojavob {0}|Автоответ {0}|Auto-reply {0}
yoqilgan|включён|enabled
o‘chirilgan|выключен|disabled
Offline holatda javob beradi|Отвечает в режиме Offline|Replies in Offline mode
Online — oddiy avtojavob yo‘q|Online — обычный автоответ выключен|Online — standard auto-reply is off
Avtojavobni yoqish|Включить автоответ|Enable auto-reply
Kelgan xabarlar|Входящие сообщения|Incoming messages
Yuborilgan javoblar|Отправленные ответы|Replies sent
AI javoblari|Ответы ИИ|AI replies
Eng faol vaqt|Пик активности|Busiest time
Bugun|Сегодня|Today
7 kun|7 дней|7 days
30 kun|30 дней|30 days
So‘nggi {0} kun|Последние {0} дн.|Last {0} days
namuna|пример|sample
jami xabarlar|всего сообщений|total messages
Muvaffaqiyatli|Успешно|Successfully
yuborilgan|отправлено|sent
Gemini yordamida yuborilgan|Отправлено с помощью Gemini|Sent using Gemini
{0} oralig‘i|Интервал {0}|{0} window
Hozircha ma’lumot yo‘q|Данных пока нет|No data yet
Xabarlar faolligi|Активность сообщений|Message activity
Muloqotlaringiz qanday kechayotganini kuzating.|Следите за ходом общения.|Keep track of your conversations.
Statistika davri|Период статистики|Analytics period
Kelgan xabarlar va yuborilgan javoblar grafigi|График входящих сообщений и отправленных ответов|Incoming messages and replies chart
Har bir xabar — yangi imkoniyat.|Каждое сообщение — новая возможность.|Every message is a new opportunity.
Batafsil statistika ↗|Подробная статистика ↗|Detailed analytics ↗
Javoblar taqsimoti|Распределение ответов|Reply breakdown
{0} kun|{0} дн.|{0} days
Oddiy javob|Обычный ответ|Standard reply
jami javoblar|всего ответов|total replies
Statistika xabarlar matnini saqlamaydi. Faqat umumiy hisoblagichlar.|Статистика не хранит тексты сообщений — только общие счётчики.|Analytics stores aggregate counters, without message text.
Tezkor amallar|Быстрые действия|Quick actions
Bir qadamda boshqaring|Управляйте в один шаг|Manage in one step
Javob matni|Текст ответа|Reply text
Xabaringizni tahrirlang|Измените текст сообщения|Edit your message
Aqlli muloqotni sozlang|Настройте умное общение|Configure smart conversations
Yangi FAQ|Новый FAQ|New FAQ
Tayyor javob qo‘shing|Добавьте готовый ответ|Add a saved answer
Jadval qo‘shish|Добавить расписание|Add schedule
Vaqtni rejalashtiring|Запланируйте время|Plan your time
Avtomatlashtirish holati|Состояние автоматизации|Automation status
Boshqarish ↗|Управление ↗|Manage ↗
Mijoz tilida, sizning nomingizdan|На языке клиента, от вашего имени|In the customer’s language, on your behalf
{0} ta faol jadval|Активных расписаний: {0}|Active schedules: {0}
Sizning hisobingiz|Ваш аккаунт|Your account
Hisob ulangan, javob berishga tayyor|Аккаунт подключён и готов отвечать|Account connected and ready to reply
Hali ulanmagan|Ещё не подключено|Not connected yet
Ulangan|Подключено|Connected
Ulanmagan|Не подключено|Not connected
AI kunlik limiti|Дневной лимит ИИ|Daily AI limit
{0} / 50 ta javob|{0} / 50 ответов|{0} / 50 replies
Ko‘rish|Посмотреть|View
Ko‘proq imkoniyatlar|Больше возможностей|More features
Biznesingizga mos tarifni tanlang|Выберите тариф для вашего бизнеса|Choose a plan for your business
Siz yo‘qligingizda ham suhbatni iliq boshlang.|Начните тёплый разговор, даже когда вас нет рядом.|Start a warm conversation, even while you’re away.
Oddiy avtojavob|Обычный автоответ|Standard auto-reply
Offline rejimi|Режим Offline|Offline mode
Yoqilganda kelgan xabarlarga javob beriladi.|При включении бот отвечает на входящие сообщения.|When enabled, the bot replies to incoming messages.
500 belgigacha|До 500 символов|Up to 500 characters
Matnni o‘zgartirish Plus, Pro va Ultra tariflarida.|Редактирование текста доступно на Plus, Pro и Ultra.|Text editing is available on Plus, Pro, and Ultra.
Bir suhbatga takroriy javob oralig‘i|Интервал повторного ответа в одном чате|Repeat reply interval per chat
Bir suhbatga juda ko‘p javob yuborilishining oldini oladi.|Предотвращает слишком частые ответы в одном чате.|Prevents sending too many replies in the same chat.
1 daqiqa|1 минута|1 minute
30 daqiqa|30 минут|30 minutes
1 soat|1 час|1 hour
3 soat|3 часа|3 hours
6 soat|6 часов|6 hours
12 soat|12 часов|12 hours
24 soat|24 часа|24 hours
{0} daqiqa|{0} мин.|{0} min
Saqlash|Сохранить|Save
Xabar qanday ko‘rinadi?|Как выглядит сообщение?|How will the message look?
Telegram’dagi javobingizning oldindan ko‘rinishi.|Предварительный просмотр ответа в Telegram.|Preview of your reply in Telegram.
AutoReplyer orqali|Через AutoReplyer|Via AutoReplyer
Assalomu alaykum!|Здравствуйте!|Hello!
Bu oldindan ko‘rinish. Hech kimga xabar yuborilmaydi.|Это предварительный просмотр. Сообщения никому не отправляются.|This is a preview. No messages are sent.
Javob tanlash tartibi|Порядок выбора ответа|Reply selection order
Uyqu rejimi → faol jadval / Offline → mos Smart FAQ → AI yordamchi → oddiy javob. Jadval Online holatda ham ishlashi mumkin.|Режим сна → активное расписание / Offline → подходящий Smart FAQ → ИИ-помощник → обычный ответ. Расписание может работать и в режиме Online.|Sleep mode → active schedule / Offline → matching Smart FAQ → AI assistant → standard reply. Schedules can also run in Online mode.
Dam oling. Mijozlar qachon qaytishingizni bilib turishadi.|Отдыхайте. Клиенты будут знать, когда вы вернётесь.|Get some rest. Let customers know you’ll be back.
Tungi avtojavob|Ночной автоответ|Nighttime auto-reply
Belgilangan vaqtda alohida javob yuboriladi.|В заданное время отправляется отдельный ответ.|A separate reply is sent during the selected hours.
Boshlanish|Начало|Start
Tugash|Окончание|End
Vaqt zonasi: {0}. Yarim tundan o‘tuvchi vaqtlar qo‘llab-quvvatlanadi. Boshlanish va tugash teng bo‘lsa, uyqu rejimi faol bo‘lmaydi.|Часовой пояс: {0}. Поддерживаются интервалы через полночь. Если начало и конец совпадают, режим сна не активен.|Time zone: {0}. Overnight windows are supported. Sleep mode is inactive when the start and end times match.
Uyqudagi javob matni|Текст ответа в режиме сна|Sleep mode reply text
Maxsus matn Plus tarifidan boshlab mavjud.|Свой текст доступен начиная с Plus.|Custom text is available on Plus and above.
Sizning uslubingizda javob beradigan aqlli hamroh.|Умный помощник, который отвечает в вашем стиле.|A smart companion that replies in your style.
Yordamchini sozlash|Настройка помощника|Assistant settings
Javoblar mijoz tilida shakllantiriladi.|Ответы формируются на языке клиента.|Replies are generated in the customer’s language.
Yordamchi roli|Роль помощника|Assistant role
Shaxsiy yordamchi|Личный помощник|Personal assistant
Sotuv menejeri|Менеджер по продажам|Sales representative
Mijozlarga yordam|Поддержка клиентов|Customer support
Do‘stona suhbatdosh|Дружелюбный собеседник|Friendly responder
Dasturchi|Представитель разработчика|Developer representative
Rasmiy / biznes|Деловой помощник|Formal business assistant
Shaxsiy ko‘rsatmalar|Ваши инструкции|Custom instructions
Qanday ohangda javob bersin? Nimalarni bilishi kerak?|Каким тоном отвечать? Что нужно знать помощнику?|What tone should it use? What should it know?
Muhim faktlarni Bilimlar bazasiga kiriting.|Добавьте важные факты в базу знаний.|Add important facts to the knowledge base.
Bugungi foydalanish|Использование сегодня|Today’s usage
/ 50 javob|/ 50 ответов|/ 50 replies
Ultra uchun kuniga 50 ta AI javob. Administrator uchun alohida qoida mavjud.|На Ultra — 50 ответов ИИ в день. Для администратора действует исключение.|Ultra includes 50 AI replies per day. The administrator has an exception.
Bilimlar bazasini boyitish ↗|Дополнить базу знаний ↗|Expand your knowledge base ↗
Muloqot qanday ishlaydi?|Как работает общение?|How do conversations work?
AI so‘nggi suhbat va bilimlar bazasidan foydalanadi. Siz suhbatga qo‘shilsangiz, yordamchi vaqtincha to‘xtaydi. AI ishlamasa, oddiy javob qo‘llanadi.|ИИ использует недавнюю переписку и базу знаний. Когда вы вступаете в разговор, помощник временно приостанавливается. При сбое ИИ используется обычный ответ.|AI uses recent conversation and knowledge base context. It pauses when you join the conversation. If AI fails, the standard reply is used.
AI ishlatilganda xabarlar Google Gemini’ga yuboriladi. AI muhim ma’lumotlarda xato qilishi mumkin.|При использовании ИИ сообщения передаются Google Gemini. ИИ может ошибаться в важных деталях.|When AI is used, messages are sent to Google Gemini. AI can get important details wrong.
Biznesingiz haqidagi faktlar yordamchingizning xotirasida.|Факты о вашем бизнесе в памяти помощника.|Give your assistant the facts about your business.
Ko‘p so‘raladigan savollarga aniq va tezkor javoblar.|Точные и быстрые ответы на частые вопросы.|Clear, quick answers to frequently asked questions.
Ma’lumot qo‘shish|Добавить информацию|Add knowledge
Savol qo‘shish|Добавить вопрос|Add question
Shaxsiy ma’lumotlar|Ваша информация|Your knowledge entries
Savol-javoblar|Вопросы и ответы|Questions and answers
AI uchun kontekst|Контекст для ИИ|Context for AI
Avtomatik javoblar|Автоматические ответы|Automatic answers
Faktlar javob uchun kontekst bo‘ladi. Ular alohida xabar yubormaydi.|Факты дают контекст для ответа. Они не отправляются отдельным сообщением.|Facts provide reply context. They do not send a separate message.
Kalit so‘zga mos savol topilsa, bot AI’dan oldin tayyor javobni yuboradi.|Если найден вопрос по ключевым словам, бот отправляет готовый ответ до обращения к ИИ.|When keywords match a question, the bot sends its saved answer before using AI.
Ma’lumot|Информация|Knowledge
Savol yoki kalit so‘z|Вопрос или ключевое слово|Question or keyword
{0} qidirish…|Поиск: {0}…|Search: {0}…
PLUS VA YUQORI|PLUS И ВЫШЕ|PLUS AND ABOVE
Birinchi ma’lumotni qo‘shing|Добавьте первую запись|Add your first knowledge entry
Birinchi savolni qo‘shing|Добавьте первый вопрос|Add your first question
Ish vaqti, xizmatlar yoki biznesingiz haqida yozing.|Расскажите о часах работы, услугах или вашем бизнесе.|Describe your business, services, or opening hours.
Mijozlaringiz nimani ko‘p so‘rashadi?|О чём чаще всего спрашивают клиенты?|What do your customers ask most often?
Qidirish|Поиск|Search
Qidiruvga mos natija topilmadi.|Ничего не найдено.|No matching results found.
Faol|Активно|Active
Pauzada|Приостановлено|Paused
Tahrirlash|Изменить|Edit
O‘chirish|Удалить|Delete
{0} holati|Состояние: {0}|{0} status
Javoblar kerakli vaqtda, har hafta avtomatik ishga tushadi.|Ответы автоматически включаются в нужное время каждую неделю.|Replies start automatically at the right time each week.
Haftalik jadvallar|Еженедельные расписания|Weekly schedules
Jadvallarni ishlatish|Использовать расписания|Use schedules
{0} · Uyqu rejimi jadvaldan ustun turadi. Kesishuvchi jadvallarga ruxsat berilmaydi.|{0} · Режим сна имеет приоритет. Пересекающиеся расписания не допускаются.|{0} · Sleep mode takes priority. Overlapping schedules are not allowed.
Kun bo‘yi|Весь день|All day
Standart avtojavob matni|Стандартный текст автоответа|Standard auto-reply text
Keyingi kunga o‘tadi|Продолжается на следующий день|Continues into the next day
Jadval holati|Состояние расписания|Schedule status
Hali jadval yo‘q|Расписаний пока нет|No schedules yet
Ish yoki dam olish vaqtlaringiz uchun yangi jadval yarating.|Создайте расписание для работы или отдыха.|Create a schedule for your work or rest hours.
API orqali saqlangan jadvallar botda kesh yangilangach, odatda 60 soniya ichida ko‘rinadi.|Расписания, сохранённые через API, появятся в боте после обновления кеша, обычно в течение 60 секунд.|Schedules saved through the API appear in the bot after its cache refreshes, usually within 60 seconds.
Xabarlar va avtojavoblar haqida aniq tasavvur.|Наглядная картина сообщений и автоответов.|A clear view of your messages and auto-replies.
Jami kuzatilgan xabarlar|Всего учтённых сообщений|Total observed messages
Muvaffaqiyatli javoblar|Успешные ответы|Successful replies
Kunlik o‘rtacha|В среднем за день|Daily average
Kiruvchi xabarlar|Входящие сообщения|Incoming messages
Cooldown tufayli o‘tkazilgan|Пропущено из-за интервала|Skipped due to cooldown
Takroriy javob cheklovi|Ограничение повторных ответов|Repeat reply limit
Raqamlar nimani anglatadi?|Что означают показатели?|What do the numbers mean?
Kiruvchi xabarlar noyob foydalanuvchilar soni emas. Har bir xabarga javob yuborilishi kafolatlanmaydi: Online rejimi, cooldown va ruxsatlar ta’sir qiladi. Statistika ishga tushirilishidan oldingi suhbatlar hisoblanmaydi.|Входящие сообщения — не число уникальных пользователей. Ответ зависит от режима Online, интервала и разрешений. Переписка до включения статистики не учитывается.|Incoming messages do not represent unique users. Replies depend on Online mode, cooldown, and permissions. Conversations before analytics was enabled are not counted.
Demo: raqamlar namunaviy.|Демо: показаны примерные данные.|Demo: figures are illustrative.
Hisoblagichlar kechikib yangilanishi mumkin.|Счётчики могут обновляться с задержкой.|Counters may take time to update.
{0} Statistika faqat jamlangan hisoblagichlarni saqlaydi. AI suhbat tarixi alohida saqlanadi.|{0} Статистика хранит только общие счётчики. История переписки ИИ хранится отдельно.|{0} Analytics stores only aggregate counters. AI conversation history is stored separately.
Telegram profilingizni bot orqali bezang.|Настройте оформление профиля Telegram через бота.|Customize your Telegram profile through the bot.
Ism soati|Часы в имени|Name clock
Profil nomida vaqt|Время в имени профиля|Time in your profile name
Botdagi davriy vazifa bilan yangilanadi.|Обновляется периодической задачей бота.|Updated by the bot’s scheduled task.
Yoqilgan|Включено|Enabled
O‘chiq|Выключено|Off
Ism, shrift va vaqt zonasini sozlash uchun botning “Ism soati” bo‘limidan foydalaning. Bot akkaunt nomini tahrirlash ruxsatini tekshiradi.|Настройте имя, шрифт и часовой пояс в разделе бота «Часы в имени». Бот проверит разрешение на изменение имени.|Set the name, font, and time zone in the bot’s Name Clock section. The bot checks permission to edit your name.
Ko‘rinish namunasi|Пример отображения|Display preview
Botda sozlash|Настроить в боте|Configure in bot
BIO hisoblagich|Счётчик в BIO|BIO countdown
Yangi yil, Navro‘z yoki tug‘ilgan kuningizgacha qolgan kunlar profilingizda. Pro va Ultra tariflarida mavjud.|Показывайте в профиле дни до Нового года, Навруза или дня рождения. Доступно на Pro и Ultra.|Show days until New Year, Navruz, or your birthday in your profile. Available on Pro and Ultra.
🌷 Navro‘zgacha {0} kun qoldi.|🌷 До Навруза осталось {0} дн.|🌷 {0} days until Navruz.
BIO’ni tahrirlash uchun Telegram Business ruxsati kerak. Tadbir va tug‘ilgan kun bot ichida tanlanadi.|Для изменения BIO нужно разрешение Telegram Business. Событие и день рождения выбираются в боте.|Editing your BIO requires Telegram Business permission. Select the event and birthday in the bot.
Sizga mos tarif|Тариф для вас|Your ideal plan
Kichik qadamdan katta imkoniyatlargacha.|От небольших шагов к большим возможностям.|From small steps to bigger possibilities.
Oddiy avtojavob va uyqu rejimi|Обычный автоответ и режим сна|Standard auto-reply and sleep mode
1 ta haftalik jadval|1 еженедельное расписание|1 weekly schedule
3 ta haftalik jadval|3 еженедельных расписания|3 weekly schedules
10 ta haftalik jadval|10 еженедельных расписаний|10 weekly schedules
30 ta haftalik jadval|30 еженедельных расписаний|30 weekly schedules
Bugungi statistika|Статистика за сегодня|Today’s analytics
Standart ism soati|Стандартные часы в имени|Standard name clock
15 ta Smart FAQ|15 записей Smart FAQ|15 Smart FAQ entries
30 ta Smart FAQ|30 записей Smart FAQ|30 Smart FAQ entries
65 ta Smart FAQ|65 записей Smart FAQ|65 Smart FAQ entries
Shaxsiy javob matnlari|Свои тексты ответов|Custom reply texts
7 kunlik statistika|Статистика за 7 дней|7-day analytics
30 kunlik statistika|Статистика за 30 дней|30-day analytics
Reklamasiz foydalanish|Без рекламы|Ad-free experience
Qo‘shimcha vaqt zonalari|Дополнительные часовые пояса|Extra time zones
Kuniga 50 ta AI javob|50 ответов ИИ в день|50 AI replies per day
55 ta bilimlar yozuvi|55 записей базы знаний|55 knowledge entries
Barcha statistika grafiklari|Все графики статистики|All analytics charts
Qo‘shimcha soat shriftlari|Дополнительные шрифты часов|Extra clock fonts
Joriy tarif|Текущий тариф|Current plan
so‘m|сум|UZS
oyiga|в месяц|per month
Botda ko‘rish ↗|Посмотреть в боте ↗|View in bot ↗
Tarif bot ichida to‘lov tasdig‘ini administratorga yuborish orqali faollashtiriladi. Yakuniy narx va amaldagi tarifni botdan tekshiring.|Тариф активируется после отправки подтверждения оплаты администратору в боте. Актуальную цену и тариф уточняйте в боте.|Activate a plan by sending payment proof to the administrator in the bot. Check the bot for the current price and plan.
Hisobingiz va Web App ulanishini boshqaring.|Управляйте аккаунтом и подключением Web App.|Manage your account and Web App connection.
Hisob holati|Состояние аккаунта|Account status
Telegram Business ulangan|Telegram Business подключён|Telegram Business connected
Business hisobini botga ulang|Подключите Business-аккаунт к боту|Connect your Business account to the bot
Hozir namoyish hisobi ochilgan|Сейчас открыт демонстрационный аккаунт|A demo account is currently open
Haqiqiy hisob|Ваш аккаунт|Live account
Telegram → Sozlamalar → Telegram Business → Chatbotlar → @autoreplyer_dbot. Xabarlarga javob berish ruxsatini bering.|Telegram → Настройки → Telegram Business → Чат-боты → @autoreplyer_dbot. Разрешите отвечать на сообщения.|Telegram → Settings → Telegram Business → Chatbots → @autoreplyer_dbot. Allow replies to messages.
Web App ulanishi|Подключение Web App|Web App connection
API server manzili|Адрес API-сервера|API server address
Alohida API serveringiz manzili. Web App va API bir serverda bo‘lsa, bo‘sh qoldiring. Bot tokenini bu yerga kiritmang.|Адрес отдельного API-сервера. Оставьте пустым, если Web App и API на одном сервере. Не вводите сюда токен бота.|Your separate API server address. Leave blank if the Web App and API share a server. Do not enter a bot token here.
Haqiqiy hisobga kirish uchun ilovani Telegram bot menyusidan oching. Telegram tasdiqlagan ma’lumot serverda tekshiriladi.|Для входа откройте приложение из меню бота в Telegram. Сервер проверяет данные, подтверждённые Telegram.|Open the app from the Telegram bot menu to sign in. The server verifies the data signed by Telegram.
Ulanishni tekshirish|Проверить подключение|Check connection
Ko‘rinish|Оформление|Appearance
Tungi rang mavzusi|Тёмная тема|Dark theme
Qurilmada saqlanadi.|Сохраняется на устройстве.|Saved on this device.
Almashtirish|Переключить|Switch
Interfeys tili|Язык интерфейса|Interface language
Tilni tanlash|Выбор языка|Choose language
Tanlov shu qurilmada saqlanadi.|Выбор сохраняется на этом устройстве.|Your choice is saved on this device.
Til saqlandi|Язык сохранён|Language saved
Ma’lumotlar|Данные|Data
Demo sozlamalari faqat shu brauzerda saqlanadi. Ular haqiqiy botingizga ta’sir qilmaydi.|Демонастройки сохраняются только в этом браузере и не влияют на вашего бота.|Demo settings are saved only in this browser and do not affect your live bot.
Sozlamalar Telegram hisobingiz bilan bog‘langan umumiy bot bazasiga saqlanadi.|Настройки сохраняются в общей базе бота, связанной с вашим аккаунтом Telegram.|Settings are saved to the shared bot database linked to your Telegram account.
Demo ma’lumotlarini tiklash|Сбросить демоданные|Reset demo data
Boshlash oson|Начать просто|Getting started is easy
AutoReplyer’ni Telegram Business hisobingizga ulang.|Подключите AutoReplyer к аккаунту Telegram Business.|Connect AutoReplyer to your Telegram Business account.
Uch qadamda tayyor|Готово за три шага|Ready in three steps
Botni ishga tushiring|Запустите бота|Start the bot
@autoreplyer_dbot’ni ochib /start yuboring. Tilni tanlab boshlang.|Откройте @autoreplyer_dbot и отправьте /start. Выберите язык.|Open @autoreplyer_dbot and send /start. Choose your language.
Telegram Business orqali ulang|Подключите через Telegram Business|Connect through Telegram Business
Telegram Sozlamalar → Telegram Business → Chatbotlar bo‘limida @autoreplyer_dbot’ni tanlang. Xabarlarga javob berish ruxsatini yoqing.|В Telegram откройте Настройки → Telegram Business → Чат-боты и выберите @autoreplyer_dbot. Разрешите ответы на сообщения.|In Telegram, open Settings → Telegram Business → Chatbots and select @autoreplyer_dbot. Allow replies to messages.
Avtojavobni yoqing va sinang|Включите и проверьте автоответ|Enable and test auto-reply
Offline rejimini yoqing. Boshqa Telegram hisobidan sizga xabar yuborib, haqiqiy javobni tekshiring.|Включите режим Offline. Отправьте себе сообщение с другого аккаунта Telegram и проверьте ответ.|Enable Offline mode. Send yourself a message from another Telegram account to test the reply.
Telegram’da boshlash ↗|Начать в Telegram ↗|Start in Telegram ↗
Foydali havolalar|Полезные ссылки|Useful links
Yordam va takliflar|Помощь и предложения|Help and feedback
Botning yordam bo‘limi|Раздел помощи в боте|Bot help section
Ochish ↗|Открыть ↗|Open ↗
AutoReplyer yangilanishlari|Обновления AutoReplyer|AutoReplyer updates
Loyiha hujjatlari|Документация проекта|Project documentation
GitHub’dagi qo‘llanma|Руководство на GitHub|Guide on GitHub
Bu Web App alohida loyiha. Mavjud AutoReplyer kodi o‘zgartirilmagan.|Этот Web App — отдельный проект. Код существующего AutoReplyer не изменён.|This Web App is a separate project. The existing AutoReplyer code is unchanged.
Barcha bo‘limlar|Все разделы|All sections
Yopish|Закрыть|Close
Yangi jadval|Новое расписание|New schedule
Yangi ma’lumot|Новая запись|New knowledge entry
Yangi savol-javob|Новый вопрос и ответ|New question and answer
Hafta kunlari|Дни недели|Days of the week
Kun bo‘yi uchun ikkala vaqtni ham 00:00 qiling.|Для целого дня установите оба времени на 00:00.|For an all-day schedule, set both times to 00:00.
Maxsus javob (ixtiyoriy)|Свой ответ (необязательно)|Custom reply (optional)
Bo‘sh qoldirsangiz, standart matn ishlatiladi.|Оставьте пустым для стандартного текста.|Leave blank to use the standard text.
Free tarifida standart matn qo‘llanadi.|На тарифе Free используется стандартный текст.|The Free plan uses the standard text.
Sarlavha|Заголовок|Title
Savol|Вопрос|Question
Kalit so‘zlar|Ключевые слова|Keywords
ish vaqti, soat nechada|часы работы, в какое время|opening hours, what time
Vergul bilan ajrating. Ko‘pi bilan 10 ta, har biri 40 belgigacha.|Разделяйте запятыми. Не более 10 слов или фраз, до 40 символов каждое.|Separate with commas. Up to 10 keywords or phrases, each up to 40 characters.
Tayyor javob|Готовый ответ|Saved answer
Bekor qilish|Отмена|Cancel
Javobni sinab ko‘ring|Проверьте ответ|Test your reply
Smart FAQ mosligini va oddiy javobni ko‘ring. Bu sinov hech kimga xabar yubormaydi, AI so‘rovi bajarmaydi.|Проверьте совпадение Smart FAQ и обычный ответ. Тест не отправляет сообщения и не обращается к ИИ.|Preview a Smart FAQ match or the standard reply. This test sends no messages and makes no AI requests.
Mijoz xabari|Сообщение клиента|Customer message
Ish vaqtingiz qanday?|Каковы ваши часы работы?|What are your opening hours?
Sinash|Проверить|Test
Shu qurilmadagi demo o‘zgarishlari o‘chiriladi va dastlabki namuna tiklanadi.|Демоизменения на этом устройстве будут удалены, исходный пример будет восстановлен.|Demo changes on this device will be removed and the original sample restored.
Tiklash|Сбросить|Reset
Demo tiklandi|Демоданные сброшены|Demo data reset
Yozuvni o‘chirish|Удалить запись|Delete entry
Ushbu yozuv o‘chiriladi. Davom etasizmi?|Запись будет удалена. Продолжить?|This entry will be deleted. Continue?
Yozuv o‘chirildi|Запись удалена|Entry deleted
Demo qurilmada saqlandi|Демо сохранено на устройстве|Demo saved on this device
Bot sozlamalari saqlandi|Настройки бота сохранены|Bot settings saved
Demo sozlamalari saqlandi|Демонастройки сохранены|Demo settings saved
Sozlamalar botga saqlandi|Настройки сохранены в боте|Settings saved to the bot
Saqlandi|Сохранено|Saved
API ulanmagan. Sozlamalarda API manzilini kiriting.|API не подключён. Укажите адрес API в настройках.|API not connected. Enter the API address in Settings.
So‘rov bajarilmadi. Ma’lumotlarni tekshiring.|Не удалось выполнить запрос. Проверьте данные.|The request failed. Check your input.
Avval botga ulaning.|Сначала подключитесь к боту.|Connect to the bot first.
API manzili HTTPS bo‘lishi kerak.|Адрес API должен использовать HTTPS.|The API address must use HTTPS.
API manzili saqlandi. Haqiqiy hisobga kirish uchun Telegram’dan oching.|Адрес API сохранён. Для входа откройте приложение в Telegram.|API address saved. Open the app in Telegram to sign in.
Telegram hisobiga ulandi|Аккаунт Telegram подключён|Telegram account connected
Smart FAQ (demo)|Smart FAQ (демо)|Smart FAQ (demo)
Oddiy javob (demo)|Обычный ответ (демо)|Standard reply (demo)
Kamida bitta kunni tanlang.|Выберите хотя бы один день.|Select at least one day.
Boshlanish va tugash vaqti teng bo‘lmasin.|Время начала и окончания не должно совпадать.|Start and end times must differ.
Bu vaqt boshqa jadval bilan kesishadi.|Время пересекается с другим расписанием.|This time overlaps another schedule.
1–10 ta kalit so‘z kiriting, har biri 40 belgigacha.|Введите от 1 до 10 ключевых слов, до 40 символов каждое.|Enter 1–10 keywords, each up to 40 characters.
Maydonlarni to‘ldiring.|Заполните поля.|Fill in the fields.
Yozuvlar limiti to‘ldi.|Достигнут лимит записей.|The entry limit has been reached.
Faollik grafigi Plus tarifidan boshlab mavjud.|График активности доступен начиная с Plus.|The activity chart is available on Plus and above.
Taqsimot diagrammasi Pro va Ultra tariflarida mavjud.|Диаграмма распределения доступна на Pro и Ultra.|The breakdown chart is available on Pro and Ultra.
Tariflar ↗|Тарифы ↗|Plans ↗
Sizga qaysi yordamchi ko‘proq ko‘maklashmoqda?|Какой помощник помогает вам чаще?|Which assistant helps you the most?
{0}:00 – {1}:00 oralig‘i|Интервал {0}:00 – {1}:00|{0}:00 – {1}:00 window
Boshqaruv paneli|Панель управления|Control panel
AutoReplyer — Telegram Business avtojavoblarini bir joydan boshqaring.|AutoReplyer — управляйте автоответами Telegram Business в одном месте.|AutoReplyer — manage Telegram Business auto-replies in one place.
`.trim().split('\n').map(row => row.split('|'));

export const messages = Object.fromEntries(rows.map(([uz, ru, en]) => [uz, {uz, ru, en}]));
