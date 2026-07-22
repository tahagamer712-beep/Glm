# -*- coding: utf-8 -*-
# data_ui.py — أزرار وعناصر واجهة المستخدم
# مُستخرَج من bot_legacy.py

BUTTONS = {
    "العربية 🇮🇶": {
        "weather": "🌤 الطقس الآن",
        "forecast": "📅 توقعات 3 أيام",
        "news": "📰 آخر الأخبار",
        "all_news": "📰 إرسال كل الأخبار",
        "mena_politics": "📰 أخبار الشرق الأوسط",
        "trending": "🔥 الأكثر تداولاً",
        "sports": "⚽ أخبار الرياضة",
        "daily_summary": "📋 ملخص أخبار اليوم",
        "weekly_summary": "📆 ملخص أسبوعي",
        "news_cats": "🗂 اختيار أنواع الأخبار",
        "currency": "💱 أسعار العملات",
        "dollar_parallel": "💵 دولار السوق",
        "convert": "🔄 محوّل العملات",
        "crypto": "💎 العملات الرقمية",
        "track_asset": "📌 تتبع عملة/سهم",
        "prayer": "🕌 أوقات الصلاة",
        "search": "🔍 بحث في الأخبار",
        "deepsearch": "🧠 بحث عميق بالذكاء الاصطناعي",
        "my_stats": "📈 إحصائياتي",
        "referral": "🎁 دعواتي",
        "top_referrers": "🏆 أفضل الداعين",
        "share_bot": "📢 انشر البوت",
        "public_stats": "📊 إحصائيات البوت",
        "voice_news": "🎙️ أخبار صوتية",
        "audio_podcast": "🎧 بودكاست يومي",
        "notif_on": "🔔 إيقاف الإشعارات",
        "notif_off": "🔕 تفعيل الإشعارات",
        "premium": "⭐ المميز",
        "settings": "🔄 تغيير الإعدادات",
        "mode30": "⚡ وضع 30 ثانية",
        "noanalysis": "😐 بدون تحليل",
        "zbda": "💡 زبدة الموضوع",
        "before_happen": "🔮 قبل ما يصير",
        "imgcard": "🖼 خبر بصورة",
        "cat_world": "🌍 عالمي",
        "cat_arab": "🇮🇶 عربي",
        "cat_econ": "💰 اقتصاد",
        "cat_sport": "⚽ رياضة",
        "news_select": "📋 اختيار الأخبار",
        "choose": "✅ اختر ما تريد:"
    },
    "English 🇬🇧": {
        "weather": "🌤 Weather Now",
        "forecast": "📅 3-Day Forecast",
        "news": "📰 Latest News",
        "all_news": "📰 Send All News",
        "mena_politics": "📰 Middle East News",
        "trending": "🔥 Trending News",
        "sports": "⚽ Sports News",
        "daily_summary": "📋 Daily News Summary",
        "weekly_summary": "📆 Weekly Summary",
        "news_cats": "🗂 News Categories",
        "currency": "💱 Currency Rates",
        "dollar_parallel": "💵 Parallel Dollar",
        "convert": "🔄 Currency Converter",
        "crypto": "💎 Crypto Prices",
        "track_asset": "📌 Track Asset",
        "prayer": "🕌 Prayer Times",
        "search": "🔍 Search News",
        "deepsearch": "🧠 AI Deep Search",
        "my_stats": "📈 My Statistics",
        "referral": "🎁 My Referrals",
        "top_referrers": "🏆 Top Referrers",
        "share_bot": "📢 Share Bot",
        "public_stats": "📊 Bot Statistics",
        "voice_news": "🎙️ Voice News",
        "audio_podcast": "🎧 Daily Podcast",
        "notif_on": "🔔 Disable Notifications",
        "notif_off": "🔕 Enable Notifications",
        "premium": "⭐ Premium",
        "settings": "🔄 Change Settings",
        "mode30": "⚡ 30-Second Mode",
        "noanalysis": "😐 No Analysis",
        "zbda": "💡 Quick Summary",
        "before_happen": "🔮 What Might Happen",
        "imgcard": "🖼 News Card",
        "cat_world": "🌍 World",
        "cat_arab": "🇮🇶 Arab",
        "cat_econ": "💰 Economy",
        "cat_sport": "⚽ Sports",
        "news_select": "📋 Select News Type",
        "choose": "✅ Choose what you want:"
    },
    "Русский 🇷🇺": {
        "weather": "🌤 Погода сейчас",
        "forecast": "📅 Прогноз на 3 дня",
        "news": "📰 Последние новости",
        "all_news": "📰 Все новости",
        "mena_politics": "📰 Ближний Восток",
        "trending": "🔥 В тренде",
        "sports": "⚽ Спортивные новости",
        "daily_summary": "📋 Сводка дня",
        "weekly_summary": "📆 Недельный итог",
        "news_cats": "🗂 Категории новостей",
        "currency": "💱 Курсы валют",
        "dollar_parallel": "💵 Параллельный доллар",
        "convert": "🔄 Конвертер валют",
        "crypto": "💎 Криптовалюты",
        "track_asset": "📌 Отслеживать актив",
        "prayer": "🕌 Время намаза",
        "search": "🔍 Поиск новостей",
        "deepsearch": "🧠 Глубокий поиск ИИ",
        "my_stats": "📈 Моя статистика",
        "referral": "🎁 Мои приглашения",
        "top_referrers": "🏆 Лучшие",
        "share_bot": "📢 Поделиться ботом",
        "public_stats": "📊 Статистика бота",
        "voice_news": "🎙️ Голосовые новости",
        "audio_podcast": "🎧 Ежедневный подкаст",
        "notif_on": "🔔 Отключить уведомления",
        "notif_off": "🔕 Включить уведомления",
        "premium": "⭐ Премиум",
        "settings": "🔄 Изменить настройки",
        "mode30": "⚡ Режим 30 секунд",
        "noanalysis": "😐 Без анализа",
        "zbda": "💡 Кратко",
        "before_happen": "🔮 Что может случиться",
        "imgcard": "🖼 Новость с картинкой",
        "cat_world": "🌍 Мир",
        "cat_arab": "🇮🇶 Арабский",
        "cat_econ": "💰 Экономика",
        "cat_sport": "⚽ Спорт",
        "news_select": "📋 Выбор новостей",
        "choose": "✅ Выберите:"
    },
    "فارسی 🇮🇷": {
        "weather": "🌤 آبوهوا",
        "forecast": "📅 پیشبینی ۳ روزه",
        "news": "📰 آخرین اخبار",
        "all_news": "📰 ارسال همه اخبار",
        "mena_politics": "📰 اخبار خاورمیانه",
        "trending": "🔥 پرتداولترین",
        "sports": "⚽ اخبار ورزشی",
        "daily_summary": "📋 خلاصه اخبار امروز",
        "weekly_summary": "📆 خلاصه هفتگی",
        "news_cats": "🗂 دستهبندی اخبار",
        "currency": "💱 نرخ ارز",
        "dollar_parallel": "💵 دلار موازی",
        "convert": "🔄 تبدیل ارز",
        "crypto": "💎 ارز دیجیتال",
        "track_asset": "📌 پیگیری دارایی",
        "prayer": "🕌 اوقات نماز",
        "search": "🔍 جستجوی اخبار",
        "deepsearch": "🧠 جستجوی عمیق هوش مصنوعی",
        "my_stats": "📈 آمار من",
        "referral": "🎁 دعوتهایم",
        "top_referrers": "🏆 برترینها",
        "share_bot": "📢 اشتراکگذاری ربات",
        "public_stats": "📊 آمار ربات",
        "voice_news": "🎙️ اخبار صوتی",
        "audio_podcast": "🎧 پادکست روزانه",
        "notif_on": "🔔 غیرفعالکردن اعلانها",
        "notif_off": "🔕 فعالکردن اعلانها",
        "premium": "⭐ ویژه",
        "settings": "🔄 تغییر تنظیمات",
        "mode30": "⚡ حالت ۳۰ ثانیه",
        "noanalysis": "😐 بدون تحلیل",
        "zbda": "💡 خلاصه یک‌خطی",
        "before_happen": "🔮 قبل از وقوع",
        "imgcard": "🖼 خبر با تصویر",
        "cat_world": "🌍 جهانی",
        "cat_arab": "🇮🇶 عربی",
        "cat_econ": "💰 اقتصاد",
        "cat_sport": "⚽ ورزش",
        "news_select": "📋 انتخاب خبر",
        "choose": "✅ انتخاب کنید:"
    },
    "हिन्दी 🇮🇳": {
        "weather": "🌤 मौसम अभी",
        "forecast": "📅 3-दिन का पूर्वानुमान",
        "news": "📰 ताज़ा खबरें",
        "all_news": "📰 सभी खबरें भेजें",
        "mena_politics": "📰 मध्य पूर्व समाचार",
        "trending": "🔥 ट्रेंडिंग",
        "sports": "⚽ खेल समाचार",
        "daily_summary": "📋 आज की खबर सारांश",
        "weekly_summary": "📆 साप्ताहिक सारांश",
        "news_cats": "🗂 समाचार श्रेणियाँ",
        "currency": "💱 मुद्रा दरें",
        "dollar_parallel": "💵 Parallel Dollar",
        "convert": "🔄 मुद्रा परिवर्तक",
        "crypto": "💎 क्रिप्टो कीमतें",
        "track_asset": "📌 Asset Track",
        "prayer": "🕌 नमाज़ के वक्त",
        "search": "🔍 खबर खोजें",
        "deepsearch": "🧠 AI गहन खोज",
        "my_stats": "📈 मेरे आँकड़े",
        "referral": "🎁 मेरे रेफरल",
        "top_referrers": "🏆 शीर्ष",
        "share_bot": "📢 बॉट शेयर करें",
        "public_stats": "📊 बॉट आँकड़े",
        "voice_news": "🎙️ आवाज़ समाचार",
        "audio_podcast": "🎧 दैनिक पॉडकास्ट",
        "notif_on": "🔔 सूचनाएं बंद करें",
        "notif_off": "🔕 सूचनाएं चालू करें",
        "premium": "⭐ प्रीमियम",
        "settings": "🔄 सेटिंग बदलें",
        "mode30": "⚡ 30 सेकंड मोड",
        "noanalysis": "😐 बिना विश्लेषण",
        "zbda": "💡 एक लाइन सारांश",
        "before_happen": "🔮 क्या हो सकता है",
        "imgcard": "🖼 फोटो खबर",
        "cat_world": "🌍 विश्व",
        "cat_arab": "🇮🇶 अरब",
        "cat_econ": "💰 अर्थव्यवस्था",
        "cat_sport": "⚽ खेल",
        "news_select": "📋 समाचार चुनें",
        "choose": "✅ चुनें:"
    },
    "Português 🇧🇷": {
        "weather": "🌤 Clima agora",
        "forecast": "📅 Previsão 3 dias",
        "news": "📰 Últimas notícias",
        "all_news": "📰 Enviar todas notícias",
        "mena_politics": "📰 Oriente Médio",
        "trending": "🔥 Em alta",
        "sports": "⚽ Esportes",
        "daily_summary": "📋 Resumo do dia",
        "weekly_summary": "📆 Resumo semanal",
        "news_cats": "🗂 Categorias de notícias",
        "currency": "💱 Taxas de câmbio",
        "dollar_parallel": "💵 Dólar paralelo",
        "convert": "🔄 Conversor de moeda",
        "crypto": "💎 Criptomoedas",
        "track_asset": "📌 Monitorar ativo",
        "prayer": "🕌 Horários de oração",
        "search": "🔍 Buscar notícias",
        "deepsearch": "🧠 Pesquisa profunda IA",
        "my_stats": "📈 Minhas estatísticas",
        "referral": "🎁 Minhas indicações",
        "top_referrers": "🏆 Melhores",
        "share_bot": "📢 Compartilhar bot",
        "public_stats": "📊 Estatísticas",
        "voice_news": "🎙️ Notícias por voz",
        "audio_podcast": "🎧 Podcast Diário",
        "notif_on": "🔔 Desativar notificações",
        "notif_off": "🔕 Ativar notificações",
        "premium": "⭐ Premium",
        "settings": "🔄 Mudar configurações",
        "mode30": "⚡ Modo 30 Segundos",
        "noanalysis": "😐 Sem Análise",
        "zbda": "💡 Resumo Rápido",
        "before_happen": "🔮 O que pode acontecer",
        "imgcard": "🖼 Notícia com Imagem",
        "cat_world": "🌍 Mundial",
        "cat_arab": "🇮🇶 Árabe",
        "cat_econ": "💰 Economia",
        "cat_sport": "⚽ Esportes",
        "news_select": "📋 Selecionar Notícias",
        "choose": "✅ Escolha:"
    },
    "Türkçe 🇹🇷": {
        "weather": "🌤 Hava durumu",
        "forecast": "📅 3 Günlük Tahmin",
        "news": "📰 Son haberler",
        "all_news": "📰 Tüm haberleri gönder",
        "mena_politics": "📰 Orta Doğu",
        "trending": "🔥 Trend haberler",
        "sports": "⚽ Spor haberleri",
        "daily_summary": "📋 Günlük özet",
        "weekly_summary": "📆 Haftalık özet",
        "news_cats": "🗂 Haber kategorileri",
        "currency": "💱 Döviz kurları",
        "dollar_parallel": "💵 Paralel dolar",
        "convert": "🔄 Döviz çevirici",
        "crypto": "💎 Kripto fiyatları",
        "track_asset": "📌 Varlık takibi",
        "prayer": "🕌 Namaz vakitleri",
        "search": "🔍 Haber ara",
        "deepsearch": "🧠 Yapay Zeka Derin Arama",
        "my_stats": "📈 İstatistiklerim",
        "referral": "🎁 Davetlerim",
        "top_referrers": "🏆 En İyiler",
        "share_bot": "📢 Botu paylaş",
        "public_stats": "📊 Bot istatistikleri",
        "voice_news": "🎙️ Sesli Haberler",
        "audio_podcast": "🎧 Günlük Podcast",
        "notif_on": "🔔 Bildirimleri kapat",
        "notif_off": "🔕 Bildirimleri aç",
        "premium": "⭐ Premium",
        "settings": "🔄 Ayarları değiştir",
        "mode30": "⚡ 30 Saniye Modu",
        "noanalysis": "😐 Analizsiz",
        "zbda": "💡 Tek Cümle Özet",
        "before_happen": "🔮 Ne Olabilir",
        "imgcard": "🖼 Görüntülü Haber",
        "cat_world": "🌍 Dünya",
        "cat_arab": "🇮🇶 Arap",
        "cat_econ": "💰 Ekonomi",
        "cat_sport": "⚽ Spor",
        "news_select": "📋 Haber Türü Seçin",
        "choose": "✅ Seçin:"
    },
    "اردو 🇵🇰": {
        "weather": "🌤 موسم ابھی",
        "forecast": "📅 3 دن کی پیشگوئی",
        "news": "📰 تازہ خبریں",
        "all_news": "📰 تمام خبریں بھیجیں",
        "mena_politics": "📰 مشرق وسطی خبریں",
        "trending": "🔥 ٹرینڈنگ خبریں",
        "sports": "⚽ کھیل کی خبریں",
        "daily_summary": "📋 آج کا خلاصہ",
        "weekly_summary": "📆 ہفتہ وار خلاصہ",
        "news_cats": "🗂 خبروں کی اقسام",
        "currency": "💱 کرنسی ریٹ",
        "dollar_parallel": "💵 پیرالل ڈالر",
        "convert": "🔄 کرنسی کنورٹر",
        "crypto": "💎 کرپٹو قیمتیں",
        "track_asset": "📌 اثاثہ ٹریک",
        "prayer": "🕌 نماز کے اوقات",
        "search": "🔍 خبریں تلاش کریں",
        "deepsearch": "🧠 AI گہری تلاش",
        "my_stats": "📈 میرے اعداد",
        "referral": "🎁 میری دعوتیں",
        "top_referrers": "🏆 بہترین",
        "share_bot": "📢 بوٹ شیئر کریں",
        "public_stats": "📊 بوٹ اعداد",
        "voice_news": "🎙️ آواز خبریں",
        "audio_podcast": "🎧 روزانہ پوڈکاسٹ",
        "notif_on": "🔔 اطلاعات بند کریں",
        "notif_off": "🔕 اطلاعات چالو کریں",
        "premium": "⭐ پریمیم",
        "settings": "🔄 ترتیبات بدلیں",
        "mode30": "⚡ 30 سیکنڈ موڈ",
        "noanalysis": "😐 تجزیہ کے بغیر",
        "zbda": "💡 ایک لائن خلاصہ",
        "before_happen": "🔮 کیا ہو سکتا ہے",
        "imgcard": "🖼 تصویر کے ساتھ خبر",
        "cat_world": "🌍 عالمی",
        "cat_arab": "🇮🇶 عربی",
        "cat_econ": "💰 معیشت",
        "cat_sport": "⚽ کھیل",
        "news_select": "📋 خبریں منتخب کریں",
        "choose": "✅ انتخاب کریں:"
    },
    "Deutsch 🇩🇪": {
        "weather": "🌤 Wetter jetzt",
        "forecast": "📅 3-Tage-Prognose",
        "news": "📰 Neueste Nachrichten",
        "all_news": "📰 Alle Nachrichten",
        "mena_politics": "📰 Nahost-Nachrichten",
        "trending": "🔥 Trending",
        "sports": "⚽ Sportnachrichten",
        "daily_summary": "📋 Tageszusammenfassung",
        "weekly_summary": "📆 Wochenzusammenfassung",
        "news_cats": "🗂 Nachrichtenkategorien",
        "currency": "💱 Wechselkurse",
        "dollar_parallel": "💵 Parallelkurs Dollar",
        "convert": "🔄 Währungsrechner",
        "crypto": "💎 Kryptowährungen",
        "track_asset": "📌 Asset verfolgen",
        "prayer": "🕌 Gebetszeiten",
        "search": "🔍 Nachrichten suchen",
        "deepsearch": "🧠 KI-Tiefensuche",
        "my_stats": "📈 Meine Statistiken",
        "referral": "🎁 Meine Einladungen",
        "top_referrers": "🏆 Beste",
        "share_bot": "📢 Bot teilen",
        "public_stats": "📊 Bot-Statistiken",
        "voice_news": "🎙️ Sprachnachrichten",
        "audio_podcast": "🎧 Täglicher Podcast",
        "notif_on": "🔔 Benachrichtigungen aus",
        "notif_off": "🔕 Benachrichtigungen ein",
        "premium": "⭐ Premium",
        "settings": "🔄 Einstellungen ändern",
        "mode30": "⚡ 30-Sekunden-Modus",
        "noanalysis": "😐 Ohne Analyse",
        "zbda": "💡 Kurzzusammenfassung",
        "before_happen": "🔮 Was könnte passieren",
        "imgcard": "🖼 Nachricht mit Bild",
        "cat_world": "🌍 Welt",
        "cat_arab": "🇮🇶 Arabisch",
        "cat_econ": "💰 Wirtschaft",
        "cat_sport": "⚽ Sport",
        "news_select": "📋 Nachrichten auswählen",
        "choose": "✅ Wählen Sie:"
    },
    "Українська 🇺🇦": {
        "weather": "🌤 Погода зараз",
        "forecast": "📅 Прогноз на 3 дні",
        "news": "📰 Останні новини",
        "all_news": "📰 Всі новини",
        "mena_politics": "📰 Близький Схід",
        "trending": "🔥 Тренди",
        "sports": "⚽ Спортивні новини",
        "daily_summary": "📋 Зведення дня",
        "weekly_summary": "📆 Тижневий підсумок",
        "news_cats": "🗂 Категорії новин",
        "currency": "💱 Курси валют",
        "dollar_parallel": "💵 Паралельний долар",
        "convert": "🔄 Конвертер валют",
        "crypto": "💎 Криптовалюти",
        "track_asset": "📌 Стежити за активом",
        "prayer": "🕌 Час молитви",
        "search": "🔍 Пошук новин",
        "deepsearch": "🧠 Глибокий пошук ШІ",
        "my_stats": "📈 Моя статистика",
        "referral": "🎁 Мої запрошення",
        "top_referrers": "🏆 Найкращі",
        "share_bot": "📢 Поділитися ботом",
        "public_stats": "📊 Статистика",
        "voice_news": "🎙️ Голосові новини",
        "audio_podcast": "🎧 Щоденний подкаст",
        "notif_on": "🔔 Вимкнути сповіщення",
        "notif_off": "🔕 Увімкнути сповіщення",
        "premium": "⭐ Преміум",
        "settings": "🔄 Змінити налаштування",
        "mode30": "⚡ Режим 30 секунд",
        "noanalysis": "😐 Без аналізу",
        "zbda": "💡 Коротко",
        "before_happen": "🔮 Що може статися",
        "imgcard": "🖼 Новина з фото",
        "cat_world": "🌍 Світ",
        "cat_arab": "🇮🇶 Арабський",
        "cat_econ": "💰 Економіка",
        "cat_sport": "⚽ Спорт",
        "news_select": "📋 Вибір новин",
        "choose": "✅ Оберіть:"
    },
    "Italiano 🇮🇹": {
        "weather": "🌤 Meteo ora",
        "forecast": "📅 Previsioni 3 giorni",
        "news": "📰 Ultime notizie",
        "all_news": "📰 Tutte le notizie",
        "mena_politics": "📰 Medio Oriente",
        "trending": "🔥 Notizie di tendenza",
        "sports": "⚽ Notizie sportive",
        "daily_summary": "📋 Riepilogo del giorno",
        "weekly_summary": "📆 Riepilogo settimanale",
        "news_cats": "🗂 Categorie notizie",
        "currency": "💱 Tassi di cambio",
        "dollar_parallel": "💵 Dollaro parallelo",
        "convert": "🔄 Convertitore valuta",
        "crypto": "💎 Criptovalute",
        "track_asset": "📌 Traccia attivo",
        "prayer": "🕌 Orari di preghiera",
        "search": "🔍 Cerca notizie",
        "deepsearch": "🧠 Ricerca profonda IA",
        "my_stats": "📈 Le mie statistiche",
        "referral": "🎁 I miei inviti",
        "top_referrers": "🏆 I migliori",
        "share_bot": "📢 Condividi bot",
        "public_stats": "📊 Statistiche bot",
        "voice_news": "🎙️ Notizie vocali",
        "audio_podcast": "🎧 Podcast Quotidiano",
        "notif_on": "🔔 Disattiva notifiche",
        "notif_off": "🔕 Attiva notifiche",
        "premium": "⭐ Premium",
        "settings": "🔄 Cambia impostazioni",
        "mode30": "⚡ Modalità 30 Secondi",
        "noanalysis": "😐 Senza Analisi",
        "zbda": "💡 Riassunto Rapido",
        "before_happen": "🔮 Cosa potrebbe succedere",
        "imgcard": "🖼 Notizia con Immagine",
        "cat_world": "🌍 Mondo",
        "cat_arab": "🇮🇶 Arabo",
        "cat_econ": "💰 Economia",
        "cat_sport": "⚽ Sport",
        "news_select": "📋 Seleziona Notizie",
        "choose": "✅ Scegli:"
    },
    "Español 🇲🇽": {
        "weather": "🌤 Clima ahora",
        "forecast": "📅 Pronóstico 3 días",
        "news": "📰 Últimas noticias",
        "all_news": "📰 Todas las noticias",
        "mena_politics": "📰 Oriente Medio",
        "trending": "🔥 Tendencias",
        "sports": "⚽ Noticias deportivas",
        "daily_summary": "📋 Resumen del día",
        "weekly_summary": "📆 Resumen semanal",
        "news_cats": "🗂 Categorías de noticias",
        "currency": "💱 Tipos de cambio",
        "dollar_parallel": "💵 Dólar paralelo",
        "convert": "🔄 Conversor de divisas",
        "crypto": "💎 Criptomonedas",
        "track_asset": "📌 Rastrear activo",
        "prayer": "🕌 Horarios de oración",
        "search": "🔍 Buscar noticias",
        "deepsearch": "🧠 Búsqueda profunda IA",
        "my_stats": "📈 Mis estadísticas",
        "referral": "🎁 Mis invitaciones",
        "top_referrers": "🏆 Mejores",
        "share_bot": "📢 Compartir bot",
        "public_stats": "📊 Estadísticas",
        "voice_news": "🎙️ Noticias de voz",
        "audio_podcast": "🎧 Podcast Diario",
        "notif_on": "🔔 Desactivar notificaciones",
        "notif_off": "🔕 Activar notificaciones",
        "premium": "⭐ Premium",
        "settings": "🔄 Cambiar configuración",
        "mode30": "⚡ Modo 30 Segundos",
        "noanalysis": "😐 Sin Análisis",
        "zbda": "💡 Resumen Rápido",
        "before_happen": "🔮 Qué podría pasar",
        "imgcard": "🖼 Noticia con Imagen",
        "cat_world": "🌍 Mundial",
        "cat_arab": "🇮🇶 Árabe",
        "cat_econ": "💰 Economía",
        "cat_sport": "⚽ Deportes",
        "news_select": "📋 Seleccionar Noticias",
        "choose": "✅ Elige lo que quieres:"
    },
    "Français 🇫🇷": {
        "weather": "🌤 Météo maintenant",
        "forecast": "📅 Prévisions 3 jours",
        "news": "📰 Dernières nouvelles",
        "all_news": "📰 Toutes les nouvelles",
        "mena_politics": "📰 Moyen-Orient",
        "trending": "🔥 Tendances",
        "sports": "⚽ Actualités sportives",
        "daily_summary": "📋 Résumé du jour",
        "weekly_summary": "📆 Résumé hebdomadaire",
        "news_cats": "🗂 Catégories d'actualités",
        "currency": "💱 Taux de change",
        "dollar_parallel": "💵 Dollar parallèle",
        "convert": "🔄 Convertisseur de devises",
        "crypto": "💎 Cryptomonnaies",
        "track_asset": "📌 Suivre un actif",
        "prayer": "🕌 Horaires de prière",
        "search": "🔍 Rechercher des nouvelles",
        "deepsearch": "🧠 Recherche approfondie IA",
        "my_stats": "📈 Mes statistiques",
        "referral": "🎁 Mes parrainages",
        "top_referrers": "🏆 Meilleurs parrains",
        "share_bot": "📢 Partager le bot",
        "public_stats": "📊 Statistiques",
        "voice_news": "🎙️ Nouvelles vocales",
        "audio_podcast": "🎧 Podcast Quotidien",
        "notif_on": "🔔 Désactiver les notifications",
        "notif_off": "🔕 Activer les notifications",
        "premium": "⭐ Premium",
        "settings": "🔄 Modifier les paramètres",
        "mode30": "⚡ Mode 30 Secondes",
        "noanalysis": "😐 Sans Analyse",
        "zbda": "💡 Résumé Rapide",
        "before_happen": "🔮 Ce qui pourrait arriver",
        "imgcard": "🖼 Actualité avec Image",
        "cat_world": "🌍 Monde",
        "cat_arab": "🇮🇶 Arabe",
        "cat_econ": "💰 Économie",
        "cat_sport": "⚽ Sport",
        "news_select": "📋 Sélectionner Actualités",
        "choose": "✅ Choisissez ce que vous voulez:"
    },
}

# ======== رسائل الترقية للمميز ========
PREMIUM_UPGRADE_MSG = {
    "العربية 🇮🇶": (
        "⭐ *الاشتراك المميز*\n\n"
        "احصل على مميزات حصرية:\n\n"
        "🌤 توقعات الطقس لـ 7 أيام\n"
        "🏙 إضافة أكثر من مدينة\n"
        "📌 أخبار حسب اهتماماتك\n"
        "⚡ أخبار عاجلة فورية كل 15 دقيقة\n"
        "🌅 ملخص صباحي يومي\n"
        "💱 تنبيه عند تغير سعر العملة\n"
        "🌧 تنبيه تغيرات الطقس\n"
        "🕐 اختيار وقت الإشعارات\n\n"
        "للاشتراك اضغط الزر أدناه 👇"
    ),
    "English 🇬🇧": (
        "⭐ *Premium Subscription*\n\n"
        "Get exclusive features:\n\n"
        "🌤 7-day weather forecast\n"
        "🏙 Add multiple cities\n"
        "📌 News by your interests\n"
        "⚡ Instant breaking news every 15 min\n"
        "🌅 Daily morning summary\n"
        "💱 Currency rate alerts\n"
        "🌧 Weather change alerts\n"
        "🕐 Choose your notification time\n\n"
        "Press the button below to subscribe 👇"
    ),
    "Русский 🇷🇺": (
        "⭐ *Премиум подписка*\n\n"
        "Получите эксклюзивные функции:\n\n"
        "🌤 Прогноз погоды на 7 дней\n"
        "🏙 Добавить несколько городов\n"
        "📌 Новости по интересам\n"
        "⚡ Срочные новости каждые 15 минут\n"
        "🌅 Утренние сводки\n"
        "💱 Оповещения о курсе валют\n"
        "🌧 Оповещения о погоде\n"
        "🕐 Выбор времени уведомлений\n\n"
        "Нажмите кнопку ниже 👇"
    ),
    "فارسی 🇮🇷": (
        "⭐ *اشتراک ویژه*\n\n"
        "امکانات انحصاری:\n\n"
        "🌤 پیشبینی آبوهوا برای ۷ روز\n"
        "🏙 افزودن چند شهر\n"
        "📌 اخبار بر اساس علایق\n"
        "⚡ اخبار فوری هر ۱۵ دقیقه\n"
        "🌅 خلاصه صبحگاهی\n"
        "💱 هشدار نرخ ارز\n"
        "🌧 هشدار تغییرات آبوهوا\n"
        "🕐 انتخاب زمان اطلاعرسانی\n\n"
        "برای اشتراک دکمه زیر را بزنید 👇"
    ),
    "हिन्दी 🇮🇳": (
        "⭐ *प्रीमियम सदस्यता*\n\n"
        "विशेष सुविधाएं:\n\n"
        "🌤 7 दिनों का मौसम पूर्वानुमान\n"
        "🏙 कई शहर जोड़ें\n"
        "📌 आपकी रुचि की खबरें\n"
        "⚡ हर 15 मिनट में ताज़ा खबरें\n"
        "🌅 सुबह का सारांश\n"
        "💱 मुद्रा दर अलर्ट\n"
        "🌧 मौसम परिवर्तन अलर्ट\n"
        "🕐 अधिसूचना समय चुनें\n\n"
        "सदस्यता के लिए नीचे बटन दबाएं 👇"
    ),
    "Português 🇧🇷": (
        "⭐ *Assinatura Premium*\n\n"
        "Recursos exclusivos:\n\n"
        "🌤 Previsão do tempo por 7 dias\n"
        "🏙 Adicionar várias cidades\n"
        "📌 Notícias por seus interesses\n"
        "⚡ Últimas notícias a cada 15 min\n"
        "🌅 Resumo matinal diário\n"
        "💱 Alertas de câmbio\n"
        "🌧 Alertas de clima\n"
        "🕐 Escolha o horário de notificações\n\n"
        "Pressione o botão abaixo 👇"
    ),
    "Türkçe 🇹🇷": (
        "⭐ *Premium Üyelik*\n\n"
        "Özel özellikler:\n\n"
        "🌤 7 günlük hava durumu tahmini\n"
        "🏙 Birden fazla şehir ekle\n"
        "📌 İlgi alanına göre haberler\n"
        "⚡ Her 15 dakikada son dakika haberleri\n"
        "🌅 Günlük sabah özeti\n"
        "💱 Döviz kuru uyarıları\n"
        "🌧 Hava durumu uyarıları\n"
        "🕐 Bildirim saatini seç\n\n"
        "Abone olmak için aşağıdaki butona bas 👇"
    ),
    "اردو 🇵🇰": (
        "⭐ *پریمیم سبسکرپشن*\n\n"
        "خصوصی خصوصیات:\n\n"
        "🌤 7 دن کی موسم کی پیش گوئی\n"
        "🏙 متعدد شہر شامل کریں\n"
        "📌 آپ کی دلچسپی کی خبریں\n"
        "⚡ ہر 15 منٹ میں تازہ ترین خبریں\n"
        "🌅 روزانہ صبح کا خلاصہ\n"
        "💱 کرنسی ریٹ الرٹ\n"
        "🌧 موسم تبدیلی الرٹ\n"
        "🕐 اطلاع کا وقت منتخب کریں\n\n"
        "سبسکرائب کرنے کے لیے نیچے بٹن دبائیں 👇"
    ),
    "Deutsch 🇩🇪": (
        "⭐ *Premium-Abonnement*\n\n"
        "Exklusive Funktionen:\n\n"
        "🌤 7-Tage-Wettervorhersage\n"
        "🏙 Mehrere Städte hinzufügen\n"
        "📌 Nachrichten nach Interessen\n"
        "⚡ Breaking News alle 15 Minuten\n"
        "🌅 Tägliche Morgenzusammenfassung\n"
        "💱 Wechselkurs-Benachrichtigungen\n"
        "🌧 Wetterwarnungen\n"
        "🕐 Benachrichtigungszeit wählen\n\n"
        "Drücken Sie die Schaltfläche unten 👇"
    ),
    "Українська 🇺🇦": (
        "⭐ *Преміум підписка*\n\n"
        "Ексклюзивні функції:\n\n"
        "🌤 Прогноз погоди на 7 днів\n"
        "🏙 Додати кілька міст\n"
        "📌 Новини за інтересами\n"
        "⚡ Термінові новини кожні 15 хвилин\n"
        "🌅 Ранкова зведення\n"
        "💱 Сповіщення про курс валют\n"
        "🌧 Погодні попередження\n"
        "🕐 Вибір часу сповіщень\n\n"
        "Натисніть кнопку нижче 👇"
    ),
    "Italiano 🇮🇹": (
        "⭐ *Abbonamento Premium*\n\n"
        "Funzionalità esclusive:\n\n"
        "🌤 Previsioni meteo per 7 giorni\n"
        "🏙 Aggiungi più città\n"
        "📌 Notizie per i tuoi interessi\n"
        "⚡ Ultime notizie ogni 15 minuti\n"
        "🌅 Riassunto mattutino\n"
        "💱 Avvisi sul tasso di cambio\n"
        "🌧 Avvisi meteo\n"
        "🕐 Scegli l'orario delle notifiche\n\n"
        "Premi il pulsante qui sotto 👇"
    ),
    "Español 🇲🇽": (
        "⭐ *Suscripción Premium*\n\n"
        "Funciones exclusivas:\n\n"
        "🌤 Pronóstico del tiempo por 7 días\n"
        "🏙 Agregar varias ciudades\n"
        "📌 Noticias según tus intereses\n"
        "⚡ Últimas noticias cada 15 minutos\n"
        "🌅 Resumen matutino diario\n"
        "💱 Alertas de tipo de cambio\n"
        "🌧 Alertas meteorológicas\n"
        "🕐 Elige el horario de notificaciones\n\n"
        "Presiona el botón de abajo 👇"
    ),
}

# ======== الاهتمامات والكلمات المفتاحية ========