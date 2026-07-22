# -*- coding: utf-8 -*-
# data_interests.py — اهتمامات المستخدمين وكلمات البحث والتواقيع
# مُستخرَج من bot_legacy.py

INTERESTS = {
    "العربية 🇮🇶": [
        "📰 سياسة", "💰 اقتصاد", "⚽ رياضة", "💻 تكنولوجيا",
        "🌍 أخبار العالم", "🚗 سيارات", "🏥 صحة",
        "🎬 فن وثقافة", "✈️ سفر وسياحة", "🔬 علوم", "🎲 منوعات"
    ],
    "English 🇬🇧": [
        "📰 Politics", "💰 Economy", "⚽ Sports", "💻 Technology",
        "🌍 World News", "🚗 Automotive", "🏥 Health",
        "🎬 Arts & Culture", "✈️ Travel", "🔬 Science", "🎲 Entertainment"
    ],
    "Русский 🇷🇺": [
        "📰 Политика", "💰 Экономика", "⚽ Спорт", "💻 Технологии",
        "🌍 Мировые новости", "🚗 Авто", "🏥 Здоровье",
        "🎬 Культура", "✈️ Путешествия", "🔬 Наука", "🎲 Развлечения"
    ],
    "فارسی 🇮🇷": [
        "📰 سیاست", "💰 اقتصاد", "⚽ ورزش", "💻 فناوری",
        "🌍 اخبار جهان", "🚗 خودرو", "🏥 سلامت",
        "🎬 هنر و فرهنگ", "✈️ سفر", "🔬 علوم", "🎲 سرگرمی"
    ],
    "हिन्दी 🇮🇳": [
        "📰 राजनीति", "💰 अर्थव्यवस्था", "⚽ खेल", "💻 प्रौद्योगिकी",
        "🌍 विश्व समाचार", "🚗 ऑटो", "🏥 स्वास्थ्य",
        "🎬 कला और संस्कृति", "✈️ यात्रा", "🔬 विज्ञान", "🎲 मनोरंजन"
    ],
    "Português 🇧🇷": [
        "📰 Política", "💰 Economia", "⚽ Esporte", "💻 Tecnologia",
        "🌍 Mundo", "🚗 Automóveis", "🏥 Saúde",
        "🎬 Arte e Cultura", "✈️ Viagem", "🔬 Ciência", "🎲 Entretenimento"
    ],
    "Türkçe 🇹🇷": [
        "📰 Siyaset", "💰 Ekonomi", "⚽ Spor", "💻 Teknoloji",
        "🌍 Dünya", "🚗 Otomotiv", "🏥 Sağlık",
        "🎬 Sanat ve Kültür", "✈️ Seyahat", "🔬 Bilim", "🎲 Eğlence"
    ],
    "اردو 🇵🇰": [
        "📰 سیاست", "💰 معیشت", "⚽ کھیل", "💻 ٹیکنالوجی",
        "🌍 عالمی خبریں", "🚗 آٹو", "🏥 صحت",
        "🎬 فن و ثقافت", "✈️ سفر", "🔬 سائنس", "🎲 تفریح"
    ],
    "Deutsch 🇩🇪": [
        "📰 Politik", "💰 Wirtschaft", "⚽ Sport", "💻 Technologie",
        "🌍 Welt", "🚗 Auto", "🏥 Gesundheit",
        "🎬 Kunst & Kultur", "✈️ Reisen", "🔬 Wissenschaft", "🎲 Unterhaltung"
    ],
    "Українська 🇺🇦": [
        "📰 Політика", "💰 Економіка", "⚽ Спорт", "💻 Технології",
        "🌍 Світ", "🚗 Авто", "🏥 Здоров'я",
        "🎬 Культура", "✈️ Подорожі", "🔬 Наука", "🎲 Розваги"
    ],
    "Italiano 🇮🇹": [
        "📰 Politica", "💰 Economia", "⚽ Sport", "💻 Tecnologia",
        "🌍 Mondo", "🚗 Auto", "🏥 Salute",
        "🎬 Arte e Cultura", "✈️ Viaggi", "🔬 Scienza", "🎲 Intrattenimento"
    ],
    "Español 🇲🇽": [
        "📰 Política", "💰 Economía", "⚽ Deporte", "💻 Tecnología",
        "🌍 Mundo", "🚗 Automóviles", "🏥 Salud",
        "🎬 Arte y Cultura", "✈️ Viajes", "🔬 Ciencia", "🎲 Entretenimiento"
    ],
    "Français 🇫🇷": [
        "📰 Politique", "💰 Économie", "⚽ Sport", "💻 Technologie",
        "🌍 Monde", "🚗 Auto", "🏥 Santé",
        "🎬 Arts & Culture", "✈️ Voyage", "🔬 Science", "🎲 Divertissement"
    ],
}

INTEREST_KEYWORDS = {
    "سياسة": ["سياسة", "حكومة", "رئيس", "وزير", "برلمان", "انتخاب", "حزب", "قرار", "مجلس"],
    "اقتصاد": ["اقتصاد", "نفط", "دولار", "تجارة", "بنك", "مال", "بورصة", "سوق", "ميزانية", "استثمار"],
    "رياضة": ["رياضة", "كرة", "مباراة", "بطولة", "لاعب", "فريق", "هدف", "ملعب", "منتخب", "دوري"],
    "تكنولوجيا": ["تقنية", "تكنولوجيا", "ذكاء اصطناعي", "هاتف", "إنترنت", "تطبيق", "برنامج", "شركة تقنية"],
    "أخبار العالم": ["عالم", "دولي", "أمريكا", "أوروبا", "آسيا", "أفريقيا", "خارجية", "ناتو", "أمم متحدة"],
    "سيارات": ["سيارة", "سيارات", "مركبة", "سباق", "محرك", "كهربائية", "وقود", "أوتوماتيك"],
    "صحة": ["صحة", "مستشفى", "طبيب", "علاج", "مرض", "لقاح", "وباء", "دواء", "جراحة"],
    "فن وثقافة": ["فن", "ثقافة", "فيلم", "مسلسل", "موسيقى", "مهرجان", "معرض", "روائي", "شاعر", "فنان"],
    "سفر وسياحة": ["سفر", "سياحة", "رحلة", "فندق", "مطار", "وجهة", "سياحي", "جواز", "تأشيرة"],
    "علوم": ["علوم", "بحث", "اكتشاف", "فضاء", "ناسا", "كواكب", "تجربة", "دراسة", "باحثون"],
    "منوعات": ["منوعات", "طريف", "غريب", "عجيب", "حيوان", "طبيعة", "بيئة", "مناخ"],
    "politics": ["politics", "government", "president", "minister", "parliament", "election", "policy"],
    "economy": ["economy", "oil", "dollar", "trade", "bank", "finance", "market", "stock", "budget"],
    "sports": ["sport", "football", "match", "tournament", "player", "team", "goal", "league"],
    "technology": ["tech", "ai", "artificial intelligence", "internet", "app", "software", "phone", "digital"],
    "world news": ["world", "international", "global", "united nations", "nato", "foreign", "crisis"],
    "automotive": ["car", "vehicle", "automotive", "electric vehicle", "motor", "race", "fuel"],
    "health": ["health", "hospital", "doctor", "treatment", "disease", "vaccine", "medicine", "surgery"],
    "arts & culture": ["art", "culture", "film", "movie", "music", "festival", "exhibition", "artist"],
    "travel": ["travel", "tourism", "trip", "hotel", "airport", "destination", "visa", "flight"],
    "science": ["science", "research", "discovery", "space", "nasa", "planet", "experiment", "study"],
    "entertainment": ["entertainment", "celebrity", "viral", "funny", "trend", "social media"],
    "спорт": ["спорт", "футбол", "матч", "турнир", "игрок", "команда", "гол", "лига"],
    "экономика": ["экономика", "нефть", "доллар", "торговля", "банк", "рынок", "бюджет"],
    "технологии": ["технологии", "ии", "интернет", "приложение", "программа", "цифровой"],
    "политика": ["политика", "правительство", "президент", "министр", "парламент", "выборы"],
    "мировые новости": ["мир", "международный", "глобальный", "нато", "оон"],
    "авто": ["автомобиль", "машина", "гонки", "двигатель", "электромобиль"],
    "здоровье": ["здоровье", "больница", "врач", "лечение", "болезнь", "вакцина"],
    "культура": ["культура", "искусство", "фильм", "музыка", "фестиваль"],
    "путешествия": ["путешествие", "туризм", "отель", "аэропорт", "виза"],
    "наука": ["наука", "исследование", "открытие", "космос", "эксперимент"],
    "развлечения": ["развлечение", "знаменитость", "вирусный", "юмор"],
    "ورزش": ["ورزش", "فوتبال", "مسابقه", "تیم", "بازیکن", "لیگ"],
    "اقتصاد_fa": ["اقتصاد", "نفت", "دلار", "تجارت", "بانک", "بازار"],
    "فناوری": ["فناوری", "هوش مصنوعی", "اینترنت", "نرمافزار", "دیجیتال"],
    "سیاست": ["سیاست", "دولت", "رئیس جمهور", "وزیر", "مجلس", "انتخابات"],
    "اخبار جهان": ["جهان", "بینالملل", "ناتو", "سازمان ملل"],
    "خودرو": ["خودرو", "ماشین", "برقی", "موتور", "مسابقه"],
    "سلامت": ["سلامت", "بیمارستان", "پزشک", "درمان", "بیماری", "واکسن"],
    "هنر و فرهنگ": ["هنر", "فرهنگ", "فیلم", "موسیقی", "جشنواره"],
    "سفر": ["سفر", "گردشگری", "هتل", "فرودگاه", "ویزا"],
    "علوم_fa": ["علوم", "تحقیق", "کشف", "فضا", "آزمایش"],
    "سرگرمی": ["سرگرمی", "مشهور", "ویروسی", "طنز"],
    "spor": ["spor", "futbol", "maç", "turnuva", "oyuncu", "takım", "gol", "lig"],
    "ekonomi": ["ekonomi", "petrol", "dolar", "ticaret", "banka", "piyasa", "bütçe"],
    "teknoloji": ["teknoloji", "yapay zeka", "internet", "uygulama", "yazılım"],
    "siyaset": ["siyaset", "hükümet", "cumhurbaşkanı", "bakan", "meclis", "seçim"],
    "dünya": ["dünya", "uluslararası", "nato", "bm", "küresel"],
    "otomotiv": ["araba", "otomobil", "elektrikli", "motor", "yarış"],
    "sağlık": ["sağlık", "hastane", "doktor", "tedavi", "hastalık", "aşı"],
    "sanat ve kültür": ["sanat", "kültür", "film", "müzik", "festival"],
    "seyahat": ["seyahat", "turizm", "otel", "havalimanı", "vize"],
    "bilim": ["bilim", "araştırma", "keşif", "uzay", "deney"],
    "eğlence": ["eğlence", "ünlü", "viral", "komedi"],
    "sport_de": ["sport", "fußball", "spiel", "turnier", "spieler", "mannschaft", "liga"],
    "wirtschaft": ["wirtschaft", "öl", "dollar", "handel", "bank", "markt", "budget"],
    "technologie": ["technologie", "ki", "internet", "app", "software", "digital"],
    "politik": ["politik", "regierung", "präsident", "minister", "parlament", "wahl"],
    "welt": ["welt", "international", "global", "nato", "un"],
    "auto": ["auto", "fahrzeug", "elektroauto", "motor", "rennen"],
    "gesundheit": ["gesundheit", "krankenhaus", "arzt", "behandlung", "krankheit", "impfstoff"],
    "kunst & kultur": ["kunst", "kultur", "film", "musik", "festival"],
    "reisen": ["reisen", "tourismus", "hotel", "flughafen", "visum"],
    "wissenschaft": ["wissenschaft", "forschung", "entdeckung", "weltraum", "experiment"],
    "unterhaltung": ["unterhaltung", "promi", "viral", "humor"],
    # ── Français ──
    "politique":       ["politique", "gouvernement", "président", "ministre", "parlement", "élection"],
    "économie":        ["économie", "pétrole", "dollar", "commerce", "banque", "marché", "budget"],
    "sport_fr":        ["sport", "football", "match", "tournoi", "joueur", "équipe", "but", "ligue"],
    "technologie_fr":  ["technologie", "ia", "internet", "application", "logiciel", "numérique"],
    "monde":           ["monde", "international", "global", "otan", "onu", "europe", "asie"],
    "auto_fr":         ["voiture", "automobile", "électrique", "moteur", "course"],
    "santé":           ["santé", "hôpital", "médecin", "traitement", "maladie", "vaccin"],
    "arts & culture":  ["art", "culture", "film", "musique", "festival", "exposition"],
    "voyage":          ["voyage", "tourisme", "hôtel", "aéroport", "visa"],
    "science":         ["science", "recherche", "découverte", "espace", "expérience"],
    "divertissement":  ["divertissement", "célébrité", "viral", "humour"],
}

# ======== العملات حسب اللغة ========
CURRENCY_MAP = {
    "العربية 🇮🇶": ("IQD", "الدينار العراقي 🇮🇶"),
    "English 🇬🇧": ("GBP", "British Pound 🇬🇧"),
    "Русский 🇷🇺": ("RUB", "Российский рубль 🇷🇺"),
    "فارسی 🇮🇷": ("IRR", "ریال ایرانی 🇮🇷"),
    "हिन्दी 🇮🇳": ("INR", "Indian Rupee 🇮🇳"),
    "Português 🇧🇷": ("BRL", "Real Brasileiro 🇧🇷"),
    "Türkçe 🇹🇷": ("TRY", "Türk Lirası 🇹🇷"),
    "اردو 🇵🇰": ("PKR", "Pakistani Rupee 🇵🇰"),
    "Deutsch 🇩🇪": ("EUR", "Euro 🇩🇪"),
    "Українська 🇺🇦": ("UAH", "Українська гривня 🇺🇦"),
    "Italiano 🇮🇹": ("EUR", "Euro 🇮🇹"),
    "Español 🇲🇽": ("MXN", "Peso Mexicano 🇲🇽"),
    "Français 🇫🇷": ("EUR", "Euro 🇫🇷"),
}

# ======== مصادر MENA ========
MENA_RSS = {
    "العربية 🇮🇶": [
        "https://www.alsumaria.tv/rss/latest-news",
        "https://shafaq.com/ar/rss.xml",
        "https://www.rudaw.net/arabic/rss",
        "https://www.almaalomah.com/feed/",
        "https://almada-paper.com/feed/",
        "https://www.alarabiya.net/.mrss/ar/0/0/0.xml",
        "https://www.aljazeera.net/aljazeera/feeds/rss.xml",
        "https://feeds.skynewsarabia.com/web/rss/2",
        "https://arabic.rt.com/rss/",
        "https://www.bbc.com/arabic/index.xml",
        "https://www.independentarabia.com/rss.xml",
        "https://rss.almasryalyoum.com/rss.xml",
        "https://arabi21.com/rss.xml",
        "https://www.elnashra.com/rss",
        "https://www.france24.com/ar/rss",
        "https://arabic.euronews.com/rss",
        "https://www.middleeasteye.net/ar/rss",
        "https://www.aawsat.com/rss.xml",
        "https://www.alquds.com/feed/",
        "https://www.alriyadh.com/tools/rss/rss.xml",
    ],
    "English 🇬🇧": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://feeds.skynews.com/feeds/rss/world.xml",
        "https://rss.cnn.com/rss/edition_world.rss",
    ],
    "Русский 🇷🇺": [
        "https://arabic.rt.com/rss/",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "Türkçe 🇹🇷": [
        "https://www.aljazeera.com.tr/feed",
        "https://www.aa.com.tr/tr/rss/default",
    ],
    "Deutsch 🇩🇪": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.dw.com/rdf/rss-de-all",
    ],
    "Español 🇲🇽": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
    ],
    "Italiano 🇮🇹": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml",
    ],
    "فارسی 🇮🇷": [
        "https://www.radiofarda.com/api/zrqomtmopp",
        "https://www.bbc.com/persian/index.xml",
    ],
    "हिन्दी 🇮🇳": [
        "https://feeds.bbci.co.uk/hindi/rss.xml",
    ],
    "Português 🇧🇷": [
        "https://feeds.bbci.co.uk/portuguese/rss.xml",
    ],
    "اردو 🇵🇰": [
        "https://feeds.bbci.co.uk/urdu/rss.xml",
        "https://www.geo.tv/rss",
    ],
    "Українська 🇺🇦": [
        "https://feeds.bbci.co.uk/ukrainian/rss.xml",
    ],
}

# ======== كلمات مفتاحية للشرق الأوسط (fallback) ========
MENA_KEYWORDS = [
    "عراق", "سوريا", "لبنان", "فلسطين", "غزة", "إيران", "السعودية", "تركيا", "اليمن", "ليبيا",
    "مصر", "الأردن", "الخليج", "حماس", "حزب الله", "إسرائيل", "بغداد", "دمشق", "طهران",
    "iraq", "syria", "lebanon", "palestine", "gaza", "iran", "saudi", "turkey", "yemen", "libya",
    "egypt", "jordan", "gulf", "hamas", "hezbollah", "israel", "baghdad", "damascus", "tehran",
    "middle east", "الشرق الأوسط", "الخليج العربي", "القدس", "jerusalem"
]

# ======== حالة البحث ========
user_states = {}

# ======== إشعار الأدمن بالأخطاء ========
# ═══════════════════════════════════════════════════════════════════════════════
# MONITORING + ALERT SYSTEM — نظام المراقبة والتنبيه
# ═══════════════════════════════════════════════════════════════════════════════
_alert_lock   = gl._alert_lock    # من state
_alert_count  = {}        # {minute_key: count} — منع التشبع
_MAX_ALERTS_PER_MIN = 5   # حد أقصى 5 تنبيهات في الدقيقة

def _addtrack_step(message):
    uid = message.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "English 🇬🇧")
    if not message.text or message.text.startswith('/'):
        bot.send_message(uid, _ui("track_cancelled", lang))
        return
    symbol = message.text.strip().upper()
    _do_addtrack(uid, symbol)

def _removetrack_step(message):
    uid = message.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "English 🇬🇧")
    symbol = message.text.strip().upper()
    data = tracked_assets.get(str(uid), {})
    assets = data.get("assets", [])
    if symbol in assets:
        assets.remove(symbol)
        save_tracked_assets()
        bot.send_message(uid, t(lang, "track_removed").format(symbol=f"*{symbol}*"), parse_mode="Markdown")
    else:
        bot.send_message(uid, t(lang, "track_not_found").format(symbol=f"*{symbol}*"), parse_mode="Markdown")

def bl_add_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    words_input = message.text.strip()
    new_words = [w.strip() for w in words_input.replace("،", ",").split(",") if w.strip()]
    added = []
    for w in new_words:
        if w not in blacklist_words:
            blacklist_words.append(w)
            added.append(w)
    save_blacklist()
    bot.send_message(uid,
        f"✅ تم إضافة `{len(added)}` كلمة للقائمة السوداء:\n" +
        "\n".join(f"• `{w}`" for w in added),
        parse_mode="Markdown"
    )

def bl_remove_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    word = message.text.strip()
    if word in blacklist_words:
        blacklist_words.remove(word)
        save_blacklist()
        bot.send_message(uid, f"✅ تم حذف الكلمة `{word}` من القائمة السوداء.", parse_mode="Markdown")
    else:
        bot.send_message(uid, f"⚠️ الكلمة `{word}` غير موجودة في القائمة.", parse_mode="Markdown")

def _generate_iraq_map_text(lang="العربية 🇮🇶"):
    """يولّد خريطة نصية للعراق مع حالة الأخبار لكل محافظة — متعددة اللغات"""
    provinces = ["بغداد","البصرة","الموصل","أربيل","النجف","كربلاء",
                 "الأنبار","ديالى","صلاح الدين","كركوك","السليمانية",
                 "دهوك","ذي قار","المثنى","القادسية","واسط","بابل","ميسان"]
    province_news = {p: [] for p in provinces}
    feeds = (RSS.get("العربية 🇮🇶") or [])[:8]
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if not feed: continue
            for entry in feed.entries[:20]:
                t_ = (getattr(entry, "title", "") or "").strip()
                for prov in provinces:
                    if prov in t_:
                        province_news[prov].append(t_)
        except Exception as _exc:
            _log_exc(_exc)
    now_str = datetime.datetime.now().strftime("%H:%M")
    _title   = _NEW_FEAT_I18N["map_title"].get(lang, _NEW_FEAT_I18N["map_title"]["العربية 🇮🇶"])
    _quiet   = _NEW_FEAT_I18N["map_quiet"].get(lang, "هادئة")
    _one     = _NEW_FEAT_I18N["map_1news"].get(lang, "خبر واحد")
    _few     = _NEW_FEAT_I18N["map_news_count"].get(lang, "{n} أخبار")
    _active  = _NEW_FEAT_I18N["map_active_news"].get(lang, "{n} أخبار نشطة")
    _upd_lbl = _NEW_FEAT_I18N["map_last_update"].get(lang, "🕐 آخر تحديث")
    _ref_lbl = _NEW_FEAT_I18N["map_refresh_btn"].get(lang, "🔄 /map")
    lines = [_title, "━━━━━━━━━━━━━━━━━━", ""]
    for prov in provinces:
        news = province_news[prov]
        c    = len(news)
        if   c == 0: status, icon = _quiet,                    "🟢"
        elif c == 1: status, icon = _one,                      "🟡"
        elif c <= 3: status, icon = _few.replace("{n}", str(c)), "🟠"
        else:        status, icon = _active.replace("{n}", str(c)), "🔴"
        has_urgent = any(_news_importance_score(n) == 2 for n in news)
        tag = " 🚨" if has_urgent else ""
        lines.append(f"{icon} *{prov}*: {status}{tag}")
    lines += ["", "━━━━━━━━━━━━━━━━━━",
              f"{_upd_lbl}: {now_str}",
              "━━━━━━━━━━━━━━━━━━",
              f"🔄 /map"]
    return "\n".join(lines)

def change_welcome_step(message):
    global welcome_override
    if message.text.strip() == "افتراضي":
        welcome_override = None
        save_welcome_override()
        bot.send_message(message.from_user.id, "✅ تم الرجوع لرسالة الترحيب الافتراضية.")
    else:
        welcome_override = message.text.strip()
        save_welcome_override()
        bot.send_message(message.from_user.id, "✅ تم تغيير رسالة الترحيب.")

# ======== رسالة الترحيب الأولى ========
LANG_SELECT_MSG = (
    "🌍 *World News & Weather Bot*\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "🇸🇦 *العربية:*\nمرحباً! 👋 الرجاء اختيار لغتك المفضلة للاستمرار في استخدام البوت.\n\n"
    "🇺🇸 *English:*\nHello! 👋 Please select your preferred language to continue using the bot.\n\n"
    "🇪🇸 *Español:*\n¡Hola! 👋 Por favor, selecciona tu idioma preferido para continuar usando el bot.\n\n"
    "🇮🇹 *Italiano:*\nCiao! 👋 Seleziona la tua lingua preferita per continuare a usare il bot.\n\n"
    "🇷🇺 *Русский:*\nПривет! 👋 Пожалуйста, выберите предпочитаемый язык для продолжения использования бота.\n\n"
    "🇵🇹 *Português:*\nOlá! 👋 Por favor, selecione seu idioma preferido para continuar usando o bot.\n\n"
    "🇺🇦 *Українська:*\nПривіт! 👋 Будь ласка, оберіть бажану мову для продовження користування ботом.\n\n"
    "🇮🇷 *فارسی:*\nسلام! 👋 لطفاً زبان مورد نظر خود را برای ادامه استفاده از ربات انتخاب کنید.\n\n"
    "🇮🇳 *हिंदी:*\nनमस्ते! 👋 कृपया बॉट का उपयोग जारी रखने के लिए अपनी पसंदीदा भाषा चुनें।\n\n"
    "🇹🇷 *Türkçe:*\nMerhaba! 👋 Lütfen botu kullanmaya devam etmek için tercih ettiğiniz dili seçin.\n\n"
    "🇩🇪 *Deutsch:*\nHallo! 👋 Bitte wähle deine bevorzugte Sprache, um den Bot weiter zu verwenden.\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "👇 اختر لغتك  |  Choose your language"
)

COUNTRY_SELECT_MSG = {
    "العربية 🇮🇶":   "مرحباً عزيزي! 👋\nيرجى أن تقوم باختيار بلدك من الأزرار أدناه لتنفتح لك جميع مميزات البوت المفيدة لك.",
    "English 🇬🇧":  "Hello dear! 👋\nPlease select your country from the buttons below to unlock all the useful features of the bot for you.",
    "Español 🇲🇽":  "¡Hola querido! 👋\nPor favor, selecciona tu país de los botones de abajo para desbloquear todas las funciones útiles del bot para ti.",
    "Italiano 🇮🇹": "Ciao caro! 👋\nSeleziona il tuo paese dai pulsanti qui sotto per sbloccare tutte le funzionalità utili del bot per te.",
    "Русский 🇷🇺":  "Привет, дорогой! 👋\nПожалуйста, выберите свою страну из кнопок ниже, чтобы открыть все полезные функции бота для вас.",
    "Português 🇧🇷":"Olá querido! 👋\nPor favor, selecione seu país nos botões abaixo para desbloquear todos os recursos úteis do bot para você.",
    "Українська 🇺🇦":"Привіт, дорогий! 👋\nБудь ласка, оберіть свою країну з кнопок нижче, щоб відкрити всі корисні функції бота для вас.",
    "فارسی 🇮🇷":    "سلام عزیز! 👋\nلطفاً کشور خود را از دکمههای زیر انتخاب کنید تا تمام ویژگیهای مفید ربات برای شما فعال شود.",
    "हिन्दी 🇮🇳":   "नमस्ते प्रिय! 👋\nकृपया नीचे दिए गए बटन से अपना देश चुनें ताकि आपके लिए बॉट की सभी उपयोगी सुविधाएँ खुल सकें।",
    "Türkçe 🇹🇷":   "Merhaba sevgili! 👋\nSenin için botun tüm faydalı özelliklerini açmak için lütfen aşağıdaki düğmelerden ülkeni seç.",
    "Deutsch 🇩🇪":  "Hallo lieber! 👋\nBitte wähle dein Land aus den untenstehenden Buttons, um alle nützlichen Funktionen des Bots für dich freizuschalten.",
    "اردو 🇵🇰":     "ہیلو عزیز! 👋\nبوٹ کی تمام مفید خصوصیات کو کھولنے کے لیے براہ کرم نیچے دیے گئے بٹنوں سے اپنا ملک منتخب کریں۔",
}

def _fetch_oil_price(symbol):
    try:
        encoded = requests.utils.quote(symbol, safe='')
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1d&range=1d",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10
        ).json()
        result = r.get("chart", {}).get("result")
        if result:
            closes = result[0]["indicators"]["quote"][0].get("close", [])
            price = next((p for p in reversed(closes) if p is not None), None)
            return round(float(price), 2) if price else None
    except Exception as _exc:
        _log_exc(_exc)
    return None

def send_currency(uid):
    user = users.get(str(uid)) or {}
    lang = user.get("lang", "English 🇬🇧")
    local_code, local_name = CURRENCY_MAP.get(lang, ("EUR", "Euro"))
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10).json()
        rates = r.get("rates", {})
        local_rate = rates.get(local_code, t(lang, "track_unavailable"))
        eur = rates.get("EUR", "-")
        gbp = rates.get("GBP", "-")
        iqd = rates.get("IQD", "-")
        try_rate = rates.get("TRY", "-")
        sar = rates.get("SAR", "-")
        oil_wti = _fetch_oil_price("CL=F")
        oil_brent = _fetch_oil_price("BZ=F")
        oil_wti_str = f"${oil_wti}" if oil_wti else "—"
        oil_brent_str = f"${oil_brent}" if oil_brent else "—"
        msg = (
            f"{t(lang, 'currency_rate_header')}"
            f"{t(lang, 'currency_local_label').format(name=local_name)}: `{local_rate}`\n"
            f"━━━━━━━━━━━━━━\n"
            f"{t(lang, 'currency_eur')}: `{eur}`\n"
            f"{t(lang, 'currency_gbp')}: `{gbp}`\n"
            f"{t(lang, 'currency_iqd')}: `{iqd}`\n"
            f"{t(lang, 'currency_try')}: `{try_rate}`\n"
            f"{t(lang, 'currency_sar')}: `{sar}`\n"
            f"━━━━━━━━━━━━━━\n"
            f"🛢 النفط WTI: `{oil_wti_str}`\n"
            f"🛢 النفط Brent: `{oil_brent_str}`\n"
        )
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "currency_error"))
        notify_admin_error(f"خطأ في أسعار العملات: {e}")

# ======== بحث في الأخبار (عنوان فقط — بدون رابط أو مصدر) ========
def search_news(uid, query, sort_by="publishedAt", sources=None, from_date=None):
    """بحث متقدم بفلاتر الترتيب والمصدر والتاريخ"""
    user = users.get(str(uid)) or {}
    lang = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    # ─ احفظ آخر استعلام للفلترة لاحقاً ─
    users[str(uid)]["_last_search"] = query
    users[str(uid)]["total_searches"] = users[str(uid)].get("total_searches", 0) + 1
    try:
        params = {
            "q": query, "language": lang_code,
            "pageSize": 6, "sortBy": sort_by, "apiKey": NEWS_KEY,
        }
        if from_date:
            params["from"] = from_date
        if sources:
            params["sources"] = sources
            params.pop("language", None)
        url = "https://newsapi.org/v2/everything?" + "&".join(f"{k}={v}" for k, v in params.items())
        r = requests.get(url, timeout=10).json()
        articles = r.get("articles", [])
        if not articles:
            # جرب من RSS المحلي
            _search_from_rss(uid, query, lang)
            return
        header_map = {
            "publishedAt": "🕐 الأحدث أولاً",
            "relevancy":   "🎯 الأكثر صلة",
            "popularity":  "🔥 الأكثر انتشاراً",
        }
        bot.send_message(uid,
            f"🔍 *نتائج البحث عن:* `{query}`\n_{header_map.get(sort_by, '')}_ — {len(articles)} نتيجة",
            parse_mode="Markdown"
        )
        for article in articles[:5]:
            title = article.get("title", "")
            link  = article.get("url",   "")
            src   = article.get("source", {}).get("name", "")
            pub   = article.get("publishedAt", "")[:10]
            if title:
                s_e = _sentiment_emoji(title)
                display = f"{s_e} " if s_e else ""
                display += f"*{title}*"
                if src or pub:
                    display += f"\n└ 📡 {src}  |  📅 {pub}"
                if link:
                    art_summary = article.get("description", "") or ""
                    markup = make_news_share_markup(link, title, lang, art_summary)
                    bot.send_message(uid, display, parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.send_message(uid, display, parse_mode="Markdown")
        # ── فلاتر البحث المتقدم ──
        filter_markup = types.InlineKeyboardMarkup(row_width=3)
        filter_markup.add(
            types.InlineKeyboardButton("🕐 الأحدث",   callback_data=f"srch_sort_publishedAt"),
            types.InlineKeyboardButton("🎯 الأصلح",    callback_data=f"srch_sort_relevancy"),
            types.InlineKeyboardButton("🔥 الرائج",    callback_data=f"srch_sort_popularity"),
        )
        filter_markup.add(
            types.InlineKeyboardButton("📅 اليوم فقط",       callback_data="srch_today"),
            types.InlineKeyboardButton("📅 آخر 3 أيام",      callback_data="srch_3days"),
            types.InlineKeyboardButton("📅 آخر أسبوع",       callback_data="srch_week"),
        )
        bot.send_message(uid, "⚙️ *فلاتر البحث:*", parse_mode="Markdown", reply_markup=filter_markup)
    except Exception as e:
        bot.send_message(uid, t(lang, "search_error"))
        notify_admin_error(f"خطأ في البحث: {e}")


def _search_from_rss(uid, query, lang):
    """بحث محلي في مصادر RSS عند فشل NewsAPI"""
    feeds  = RSS.get(lang, [])
    results = []
    q_low = query.lower()
    for feed_url in feeds[:5]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for item in feed.entries[:20]:
                title = getattr(item, 'title', '')
                if q_low in title.lower():
                    results.append((getattr(item, 'link', ''), title, feed_url,
                                    getattr(item, 'summary', '')))
        except Exception as _exc:
            _log_exc(_exc)
    if results:
        bot.send_message(uid, f"🔍 *نتائج RSS لـ:* `{query}`", parse_mode="Markdown")
        for link, title, feed_url, summ in results[:5]:
            src_name = get_source_name_from_url(feed_url)
            s_e = _sentiment_emoji(title)
            markup = make_news_share_markup(link, title, lang, summ)
            bot.send_message(uid, f"{s_e + ' ' if s_e else ''}*{title}*\n└ 📡 {src_name}",
                             parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(uid, t(lang, "search_no_results") or "❌ لا توجد نتائج")


@bot.callback_query_handler(func=lambda c: c.data.startswith("srch_"))
def cb_advanced_search(call):
    bot.answer_callback_query(call.id)
    uid   = call.from_user.id
    query = users.get(str(uid), {}).get("_last_search", "")
    if not query:
        bot.send_message(uid, "❌ أعد البحث من جديد.")
        return
    d = call.data
    if d.startswith("srch_sort_"):
        sort = d.replace("srch_sort_", "")
        search_news(uid, query, sort_by=sort)
    elif d == "srch_today":
        from_date = datetime.date.today().isoformat()
        search_news(uid, query, from_date=from_date)
    elif d == "srch_3days":
        from_date = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
        search_news(uid, query, from_date=from_date)
    elif d == "srch_week":
        from_date = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        search_news(uid, query, from_date=from_date)

def send_7day_forecast(uid):
    user = users.get(str(uid)) or {}
    lang = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    country = user.get("country", "").strip()
    province = user.get("province", "").strip()
    cities = ([province] if province else []) + user.get("extra_cities", [])
    if not cities:
        _no_city_msgs_7 = {
            "العربية 🇮🇶": "⚠️ لم تحدد محافظتك بعد.\nاكتب /start لإعادة الإعداد وتعيين محافظتك.",
            "English 🇬🇧":  "⚠️ You haven't set your city yet.\nType /start to set up your location.",
        }
        bot.send_message(uid, _no_city_msgs_7.get(lang, _no_city_msgs_7["English 🇬🇧"]))
        return
    for city in cities[:3]:
        try:
            owm_city = _to_owm_city(city, country)
            url = f"https://api.openweathermap.org/data/2.5/forecast?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}&cnt=40"
            data = requests.get(url, timeout=10).json()
            if str(data.get("cod")) != "200":
                continue
            days = {}
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]
                if date not in days:
                    days[date] = {"temps": [], "desc": item["weather"][0]["description"]}
                days[date]["temps"].append(item["main"]["temp"])
            msg = t(lang, "forecast_7day_header").format(city=city)
            for date, info in list(days.items())[:7]:
                min_t = round(min(info["temps"]))
                max_t = round(max(info["temps"]))
                msg += f"📅 {date}: {min_t}°C — {max_t}°C | {info['desc']}\n"
            bot.send_message(uid, msg, parse_mode="Markdown")
        except Exception as e:
            notify_admin_error(f"خطأ في توقعات 7 أيام ({city}): {e}")

def get_weather_emoji(weather_id):
    if weather_id < 300:
        return "⚡"
    elif weather_id < 500:
        return "🌦"
    elif weather_id < 600:
        return "🌧"
    elif weather_id < 700:
        return "❄️"
    elif weather_id < 800:
        return "🌫"
    elif weather_id == 800:
        return "☀️"
    elif weather_id < 803:
        return "🌤"
    else:
        return "☁️"

def get_uv_level(uvi, lang="English 🇬🇧"):
    if uvi is None:
        return t(lang, "uv_na")
    uvi = float(uvi)
    if uvi < 3:
        return f"{uvi:.1f} 🟢 {t(lang, 'uv_low')}"
    elif uvi < 6:
        return f"{uvi:.1f} 🟡 {t(lang, 'uv_moderate')}"
    elif uvi < 8:
        return f"{uvi:.1f} 🟠 {t(lang, 'uv_high')}"
    elif uvi < 11:
        return f"{uvi:.1f} 🔴 {t(lang, 'uv_very_high')}"
    else:
        return f"{uvi:.1f} 🟣 {t(lang, 'uv_extreme')}"

def get_wind_direction(deg, lang="English 🇬🇧"):
    keys = ["wind_N", "wind_NE", "wind_E", "wind_SE",
            "wind_S", "wind_SW", "wind_W", "wind_NW"]
    if deg is None:
        return "-"
    return t(lang, keys[round(deg / 45) % 8])

def send_detailed_weather(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang      = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    province  = user.get("province", "").strip()
    country   = user.get("country", "").strip()
    loc_lat   = user.get("location_lat")
    loc_lon   = user.get("location_lon")
    if not province and loc_lat is None:
        _no_city_msgs = {
            "العربية 🇮🇶": "⚠️ لم تحدد محافظتك بعد.\nاكتب /start لإعادة الإعداد وتعيين محافظتك.",
            "English 🇬🇧":  "⚠️ You haven't set your city yet.\nType /start to set up your location.",
            "Русский 🇷🇺":  "⚠️ Вы не указали свой город.\nНапишите /start для настройки.",
            "فارسی 🇮🇷":    "⚠️ شما هنوز شهر خود را تعیین نکرده‌اید.\n/start بزنید.",
            "Türkçe 🇹🇷":   "⚠️ Şehrinizi henüz belirlediniz.\n/start yazın.",
            "Deutsch 🇩🇪":  "⚠️ Sie haben Ihre Stadt noch nicht festgelegt.\nSchreiben Sie /start.",
            "Español 🇲🇽":  "⚠️ Aún no has establecido tu ciudad.\nEscribe /start para configurar.",
            "Français 🇫🇷": "⚠️ Vous n'avez pas encore défini votre ville.\nTapez /start.",
        }
        bot.send_message(uid, _no_city_msgs.get(lang, _no_city_msgs["English 🇬🇧"]))
        return
    try:
        if loc_lat is not None and loc_lon is not None:
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?lat={loc_lat}&lon={loc_lon}"
                   f"&appid={WEATHER_KEY}&units=metric&lang={lang_code}")
        else:
            owm_city = _to_owm_city(province, country)
            url = (f"https://api.openweathermap.org/data/2.5/weather"
                   f"?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}")
        data = requests.get(url, timeout=10).json()
        if data.get("cod") != 200:
            bot.send_message(uid, t(lang, "city_not_found").format(city=province))
            return
        temp = round(data['main']['temp'], 1)
        feels = round(data['main']['feels_like'], 1)
        temp_min = round(data['main']['temp_min'], 1)
        temp_max = round(data['main']['temp_max'], 1)
        humidity = data['main']['humidity']
        pressure = data['main']['pressure']
        desc = data['weather'][0]['description'].capitalize()
        weather_id = data['weather'][0]['id']
        weather_emoji = get_weather_emoji(weather_id)
        wind_speed = data['wind']['speed']
        wind_deg = data['wind'].get('deg')
        wind_gust = data['wind'].get('gust', '-')
        visibility = data.get('visibility', 0)
        visibility_km = round(visibility / 1000, 1) if visibility else '-'
        clouds = data['clouds']['all']
        sunrise_ts = data['sys'].get('sunrise', 0)
        sunset_ts = data['sys'].get('sunset', 0)
        sunrise = datetime.datetime.fromtimestamp(sunrise_ts).strftime("%H:%M") if sunrise_ts else "-"
        sunset = datetime.datetime.fromtimestamp(sunset_ts).strftime("%H:%M") if sunset_ts else "-"
        lat = data['coord']['lat']
        lon = data['coord']['lon']
        try:
            one_call_url = f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}&exclude=minutely,hourly,daily,alerts&appid={WEATHER_KEY}&units=metric"
            one_call = requests.get(one_call_url, timeout=5).json()
            uvi = one_call.get('current', {}).get('uvi')
        except Exception:
            uvi = None
        msg = t(lang, "weather_header").format(
            emoji=weather_emoji, city=province, temp=temp, feels=feels,
            temp_max=temp_max, temp_min=temp_min, desc=desc, clouds=clouds,
            visibility_km=visibility_km, humidity=humidity, pressure=pressure,
            uvi=get_uv_level(uvi, lang),
            wind_speed=wind_speed, wind_dir=get_wind_direction(wind_deg, lang),
            wind_gust=wind_gust, sunrise=sunrise, sunset=sunset
        )
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "weather_error"))
        notify_admin_error(f"خطأ في الطقس لـ {uid}: {e}")

def add_extra_city(uid, city):
    users[str(uid)].setdefault("extra_cities", [])
    if city not in users[str(uid)]["extra_cities"]:
        users[str(uid)]["extra_cities"].append(city)
    _db_save_all_users(users)
    bot.send_message(uid, f"✅ تمت إضافة مدينة: *{city}*", parse_mode="Markdown")

def send_hourly_weather_forecast(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    province = user.get("province", "").strip()
    country  = user.get("country", "").strip()
    if not province:
        bot.send_message(uid, "⚠️ لم تحدد محافظتك بعد.\nاكتب /start لإعادة الإعداد.")
        return
    owm_city = _to_owm_city(province, country)
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}&cnt=8"
        data = requests.get(url, timeout=10).json()
        if str(data.get("cod")) != "200":
            bot.send_message(uid, t(lang, "forecast_error"))
            return
        msg = t(lang, "hourly_header").format(city=province)
        wind_unit = t(lang, "wind_unit")
        for item in data["list"][:8]:
            time_str = item["dt_txt"].split(" ")[1][:5]
            date_str = item["dt_txt"].split(" ")[0][5:]
            temp = round(item["main"]["temp"], 1)
            desc = item["weather"][0]["description"].capitalize()
            wid = item["weather"][0]["id"]
            emoji = get_weather_emoji(wid)
            humidity = item["main"]["humidity"]
            wind = item["wind"]["speed"]
            msg += f"{emoji} *{date_str} | {time_str}*\n"
            msg += f"   🌡 {temp}°C | {desc}\n"
            msg += f"   💧 {humidity}% | 💨 {wind} {wind_unit}\n\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "forecast_error"))
        notify_admin_error(f"خطأ في الطقس الساعي لـ {uid}: {e}")

def send_full_currency_table(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10).json()
        rates = r.get("rates", {})
        pairs = [
            ("🇪🇺", "EUR"), ("🇬🇧", "GBP"), ("🇮🇶", "IQD"),
            ("🇸🇦", "SAR"), ("🇦🇪", "AED"), ("🇹🇷", "TRY"),
            ("🇮🇷", "IRR"), ("🇷🇺", "RUB"), ("🇵🇰", "PKR"),
            ("🇮🇳", "INR"), ("🇧🇷", "BRL"), ("🇲🇽", "MXN"),
            ("🇨🇳", "CNY"), ("🇯🇵", "JPY"), ("🇨🇦", "CAD"),
            ("🇦🇺", "AUD"), ("🇰🇼", "KWD"), ("🇪🇬", "EGP"),
            ("🇯🇴", "JOD"), ("🇵🇱", "PLN"), ("🇨🇭", "CHF"),
            ("🇸🇬", "SGD"), ("🇿🇦", "ZAR"), ("🇳🇬", "NGN"),
        ]
        msg = t(lang, "currency_table_header")
        for flag, code in pairs:
            rate = rates.get(code, "-")
            msg += f"{flag} {code}: `{rate}`\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "currency_error"))
        notify_admin_error(f"خطأ في جدول العملات: {e}")

def _fetch_quick_weather(province, lang, country=""):
    """يجلب بيانات الطقس السريعة لعرضها في الملخص الصباحي"""
    try:
        lang_codes = {
            "العربية 🇮🇶": "ar", "English 🇬🇧": "en", "Русский 🇷🇺": "ru",
            "فارسی 🇮🇷": "fa", "हिन्दी 🇮🇳": "hi", "Português 🇧🇷": "pt",
            "Türkçe 🇹🇷": "tr", "اردو 🇵🇰": "ur", "Deutsch 🇩🇪": "de",
            "Українська 🇺🇦": "uk", "Italiano 🇮🇹": "it", "Español 🇲🇽": "es",
        }
        lang_code = lang_codes.get(lang, "en")
        owm_city = _to_owm_city(province, country)
        url = f"https://api.openweathermap.org/data/2.5/weather?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            temp  = round(d["main"]["temp"])
            feels = round(d["main"]["feels_like"])
            desc  = d["weather"][0].get("description", "")
            emoji = get_weather_emoji(d["weather"][0].get("id", 800))
            return f"{emoji} *{province}*: {temp}°C ({desc}), يُشعر بـ {feels}°C"
    except Exception as _exc:
        _log_exc(_exc)
    return None

def _fetch_quick_weather_latlon(lat, lon, lang):
    """يجلب الطقس السريع بالإحداثيات الجغرافية (GPS)"""
    try:
        lang_codes = {
            "العربية 🇮🇶": "ar", "English 🇬🇧": "en", "Русский 🇷🇺": "ru",
            "فارسی 🇮🇷": "fa", "हिन्दी 🇮🇳": "hi", "Português 🇧🇷": "pt",
            "Türkçe 🇹🇷": "tr", "اردو 🇵🇰": "ur", "Deutsch 🇩🇪": "de",
            "Українська 🇺🇦": "uk", "Italiano 🇮🇹": "it", "Español 🇲🇽": "es",
        }
        lang_code = lang_codes.get(lang, "en")
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang={lang_code}")
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d     = r.json()
            temp  = round(d["main"]["temp"])
            feels = round(d["main"]["feels_like"])
            desc  = d["weather"][0].get("description", "")
            emoji = get_weather_emoji(d["weather"][0].get("id", 800))
            city  = d.get("name", "")
            return f"{emoji} *{city}*: {temp}°C ({desc}), يُشعر بـ {feels}°C"
    except Exception as _exc:
        _log_exc(_exc)
    return None

def _fetch_quick_prayer(province, lat=None, lon=None):
    """يجلب أوقات الصلاة القادمة لعرضها في الملخص الصباحي (GPS أو اسم المدينة)"""
    try:
        today = datetime.date.today().strftime("%d-%m-%Y")
        if lat is not None and lon is not None:
            url = (f"https://api.aladhan.com/v1/timings/{today}"
                   f"?latitude={lat}&longitude={lon}&method=4")
        else:
            owm_city = _to_owm_city(province)
            url = f"https://api.aladhan.com/v1/timingsByCity?city={owm_city}&country=&method=4&date={today}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            timings = r.json()["data"]["timings"]
            now = _now_sa()
            now_str = now.strftime("%H:%M")
            prayer_names = {
                "Fajr": "🌅 الفجر", "Dhuhr": "🌞 الظهر",
                "Asr": "🌇 العصر", "Maghrib": "🌆 المغرب", "Isha": "🌙 العشاء"
            }
            next_p = None
            for p_key, p_name in prayer_names.items():
                p_time = timings.get(p_key, "")
                if p_time > now_str:
                    next_p = f"{p_name}: `{p_time}`"
                    break
            return next_p
    except Exception as _exc:
        _log_exc(_exc)
    return None

def send_morning_summary():
    if bot_paused: return
    now_hour = _now_sa().hour
    for uid, info in list(users.items()):
        if int(uid) in banned:
            continue
        if not info.get("notifications", True):
            continue
        notif_hour = info.get("notif_hour", 8)
        if now_hour != notif_hour:
            continue
        lang     = info.get("lang", "English 🇬🇧")
        province = info.get("province", "")
        country  = info.get("country", "")
        loc_lat  = info.get("location_lat")
        loc_lon  = info.get("location_lon")
        feeds    = RSS.get(lang, [])
        # ── جمع أبرز الأخبار ──
        headlines = []
        for feed_url in feeds:
            try:
                feed = _parse_feed(feed_url)
                if feed is None:
                    feed = feedparser.parse(feed_url)
                if not feed:
                    continue
                for item in feed.entries[:3]:
                    if hasattr(item, 'title'):
                        s_e = _sentiment_emoji(item.title)
                        headlines.append(f"{'• ' + s_e + ' ' if s_e else '• '}{item.title}")
                if len(headlines) >= 8:
                    break
            except Exception as _exc:
                _log_exc(_exc)
        parts = [_ul(lang, "morning_title")]
        # ── الطقس ──
        if WEATHER_KEY and (province or (loc_lat is not None and loc_lon is not None)):
            if loc_lat is not None and loc_lon is not None:
                w = _fetch_quick_weather_latlon(loc_lat, loc_lon, lang)
            else:
                w = _fetch_quick_weather(province, lang, country)
            if w:
                parts.append(_ul(lang, "morning_weather") + w)
        # ── وقت الصلاة القادم ──
        if province or (loc_lat is not None and loc_lon is not None):
            prayer = _fetch_quick_prayer(province, lat=loc_lat, lon=loc_lon)
            if prayer:
                parts.append(_ul(lang, "morning_prayer") + prayer)
        # ── الأخبار ──
        if headlines:
            parts.append(_ul(lang, "morning_news") + "\n".join(headlines[:8]))
        if len(parts) > 1:
            msg = "\n".join(parts)
            try:
                bot.send_message(uid, msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

def check_weather_alerts():
    if bot_paused: return
    for uid, info in list(users.items()):
        if int(uid) in banned:
            continue
        province = info.get("province")
        if not province:
            continue
        country  = info.get("country", "")
        lang = info.get("lang", "English 🇬🇧")
        lang_code = LANG_CODES.get(lang, "en")
        owm_city = _to_owm_city(province, country)
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}"
            data = requests.get(url, timeout=10).json()
            if data.get("cod") != 200:
                continue
            temp = data['main']['temp']
            weather_id = data['weather'][0]['id']
            desc = data['weather'][0]['description']
            if temp >= 45:
                bot.send_message(uid, _ul(lang, "weather_heat", city=province, temp=temp), parse_mode="Markdown")
            elif weather_id < 700:
                bot.send_message(uid, _ul(lang, "weather_alert", city=province, desc=desc), parse_mode="Markdown")
        except Exception as e:
            notify_admin_error(f"خطأ في تنبيهات الطقس: {e}")

def check_currency_alerts():
    if bot_paused: return
    alerted_users = [uid for uid, info in list(users.items()) if "currency_alert" in info]
    if not alerted_users:
        return
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10).json()
        rates = r.get("rates", {})
        for uid in alerted_users:
            info = users[uid]
            lang = info.get("lang", "English 🇬🇧")
            local_code, local_name = CURRENCY_MAP.get(lang, ("EUR", "Euro"))
            current_rate = rates.get(local_code)
            target = info.get("currency_alert")
            if current_rate and target:
                last = info.get("currency_alert_last", 0)
                if abs(current_rate - target) <= target * 0.01 and abs(current_rate - last) > target * 0.005:
                    users[uid]["currency_alert_last"] = current_rate
                    _db_save_all_users(users)
                    bot.send_message(int(uid), _ul(lang, "currency_alert", rate=current_rate, currency=local_name), parse_mode="Markdown")
    except Exception as e:
        notify_admin_error(f"خطأ في تنبيهات العملة: {e}")

# ======== طلب تقييم يومي (مهمة مجدولة فقط — FIX: كان مربوطاً بالخطأ بأمر /start
# ويمنع تشغيل معالج /start الحقيقي في handler_start.py؛ فُصل الديكوريتور) ========
def send_rating_request():
    if bot_paused: return
    for uid, info in list(users.items()):
        try:
            if int(uid) in banned:
                continue
            if not info.get("notifications", True):
                continue
            if info.get("rating_sent_today"):
                continue
            markup = types.InlineKeyboardMarkup(row_width=5)
            markup.add(
                types.InlineKeyboardButton("1⭐", callback_data=f"rate_bot_1_{uid}"),
                types.InlineKeyboardButton("2⭐", callback_data=f"rate_bot_2_{uid}"),
                types.InlineKeyboardButton("3⭐", callback_data=f"rate_bot_3_{uid}"),
                types.InlineKeyboardButton("4⭐", callback_data=f"rate_bot_4_{uid}"),
                types.InlineKeyboardButton("5⭐", callback_data=f"rate_bot_5_{uid}"),
            )
            markup2 = types.InlineKeyboardMarkup(row_width=5)
            markup2.add(
                types.InlineKeyboardButton("1⭐", callback_data=f"rate_news_1_{uid}"),
                types.InlineKeyboardButton("2⭐", callback_data=f"rate_news_2_{uid}"),
                types.InlineKeyboardButton("3⭐", callback_data=f"rate_news_3_{uid}"),
                types.InlineKeyboardButton("4⭐", callback_data=f"rate_news_4_{uid}"),
                types.InlineKeyboardButton("5⭐", callback_data=f"rate_news_5_{uid}"),
            )
            bot.send_message(int(uid),
                "⭐ *كيف تقيّم البوت اليوم؟*\n\nاختر عدد النجوم:",
                parse_mode="Markdown", reply_markup=markup)
            bot.send_message(int(uid),
                "📰 *كيف تقيّم أخبار اليوم؟*\n\nاختر عدد النجوم:",
                parse_mode="Markdown", reply_markup=markup2)
            info["rating_sent_today"] = True
            _db_save_user(uid, info)
        except Exception:
            continue

def check_inactive_users():
    if bot_paused: return
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    for uid, info in list(users.items()):
        try:
            if int(uid) in banned:
                continue
            last_seen = info.get("last_seen", info.get("join_date", ""))
            if last_seen and last_seen < cutoff:
                reminders = info.get("inactive_reminders", 0)
                if reminders >= 2:
                    continue
                bot.send_message(int(uid),
                    "👋 *مرحباً، اشتقنا إليك!*\n\n"
                    "📰 لا تفوت آخر أخبار الشرق الأوسط.\n"
                    "اضغط /start للعودة للبوت.",
                    parse_mode="Markdown")
                info["inactive_reminders"] = reminders + 1
                _db_save_user(uid, info)
        except Exception:
            continue

def check_summary_hint():
    if bot_paused: return
    for uid, info in list(users.items()):
        try:
            if int(uid) in banned:
                continue
            if info.get("summary_hint_sent"):
                continue
            if info.get("used_summary"):
                continue
            join = info.get("join_date", "")
            if join:
                joined = datetime.datetime.strptime(join, "%Y-%m-%d")
                if (datetime.datetime.now() - joined).days >= 3:
                    bot.send_message(int(uid),
                        "📖 *هل تعلم؟*\n\n"
                        "يمكنك الحصول على ملخص يومي للأخبار!\n"
                        "اضغط على زر *📋 ملخص اليوم* من القائمة الرئيسية.",
                        parse_mode="Markdown")
                    info["summary_hint_sent"] = True
                    _db_save_user(uid, info)
        except Exception:
            continue

def reset_daily_rating_flags():
    for uid, info in list(users.items()):
        if info.get("rating_sent_today"):
            info["rating_sent_today"] = False

# ═══════════════════════════════════════════════════════════════
# ميزات الواجهة الجديدة — سريعة ومباشرة
# ═══════════════════════════════════════════════════════════════

def _make_location_keyboard(lang):
    """يبني لوحة مفاتيح Telegram لإرسال الموقع الجغرافي."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton(
        st(lang, "location_btn_text") or "📍 Share location",
        request_location=True
    ))
    return markup

def _send_location_choice(uid, lang, country, provinces):
    """يرسل رسالة الإقناع مع زرَّي 'اختر محافظتك' أو 'أرسل موقعك'."""
    msg_text = st(lang, "location_choice_msg")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(
            st(lang, "btn_loc_province") or "📌 Choose city",
            callback_data="loc_choose_prov"
        ),
        types.InlineKeyboardButton(
            st(lang, "btn_loc_share") or "📍 Share location",
            callback_data="loc_share_gps"
        ),
    )
    bot.send_message(uid, msg_text, parse_mode="Markdown", reply_markup=markup)

BOT_SIGNATURE = "\n━━━━━━━━━━━━━━\n✨ Powered by InsightX\n@Iraqnowbot"

_NEWS_SIGNATURE_LOCALIZED = {
    "العربية 🇮🇶":   "✨ Powered by InsightX\n@Iraqnowbot",
    "English 🇬🇧":  "✨ Powered by InsightX\n@Iraqnowbot",
    "Русский 🇷🇺":  "✨ Powered by InsightX\n@Iraqnowbot",
    "فارسی 🇮🇷":    "✨ Powered by InsightX\n@Iraqnowbot",
    "हिन्दी 🇮🇳":   "✨ Powered by InsightX\n@Iraqnowbot",
    "Português 🇧🇷": "✨ Powered by InsightX\n@Iraqnowbot",
    "Türkçe 🇹🇷":   "✨ Powered by InsightX\n@Iraqnowbot",
    "اردو 🇵🇰":     "✨ Powered by InsightX\n@Iraqnowbot",
    "Deutsch 🇩🇪":  "✨ Powered by InsightX\n@Iraqnowbot",
    "Українська 🇺🇦": "✨ Powered by InsightX\n@Iraqnowbot",
    "Italiano 🇮🇹": "✨ Powered by InsightX\n@Iraqnowbot",
    "Español 🇲🇽":  "✨ Powered by InsightX\n@Iraqnowbot",
    "Français 🇫🇷": "✨ Powered by InsightX\n@Iraqnowbot",
}

_DEFAULT_NEWS_SIGNATURE = "✨ Powered by InsightX\n@Iraqnowbot"

def t(lang, key):
    """ترجمة رسالة نظام حسب لغة المستخدم مع الرجوع للإنجليزية إذا لم توجد."""
    return MSGS.get(lang, MSGS["English 🇬🇧"]).get(key, MSGS["English 🇬🇧"].get(key, ""))

# ======== رسائل الإعداد والتفاعل المترجمة ========

# ═══════════════════════════════════════════════════════════════════
# قاموس الرسائل متعددة اللغات — كل رسالة تصل للمستخدم
# ═══════════════════════════════════════════════════════════════════