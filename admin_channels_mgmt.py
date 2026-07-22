# -*- coding: utf-8 -*-
"""
  admin_channels_mgmt.py — إضافة/حذف القنوات + إحصائيات

  يُصدِّر دوال إدارة القنوات والمجموعات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def save_channels_groups():
    _db_save_all_channels(channels_groups)
    save_json(CHANNELS_FILE, channels_groups)   # نسخة احتياطية فقط

# ======== القائمة السوداء للكلمات ========
blacklist_words = load_json(BLACKLIST_FILE, [])

def save_blacklist():
    save_json(BLACKLIST_FILE, blacklist_words)

# ======== عداد القراءة ========
read_stats = load_json(READ_STATS_FILE, {"total_opens": 0, "daily": {}})

def save_custom_tg_channels():
    save_json(CUSTOM_TG_CHANNELS_FILE, _custom_tg_channels)

def add_custom_tg_channel(lang, handle, name):
    """يضيف قناة تيليغرام جديدة لمصادر الأخبار ديناميكياً"""
    handle = handle.lstrip("@").strip()
    if not name:
        name = f"@{handle}"
    entry = {"handle": handle, "name": name}
    if lang not in TELEGRAM_NEWS_CHANNELS:
        TELEGRAM_NEWS_CHANNELS[lang] = []
    if lang not in _custom_tg_channels:
        _custom_tg_channels[lang] = []
    existing_handles = {c["handle"] for c in TELEGRAM_NEWS_CHANNELS[lang]}
    if handle in existing_handles:
        return False, "موجودة مسبقاً"
    TELEGRAM_NEWS_CHANNELS[lang].append(entry)
    _custom_tg_channels[lang].append(entry)
    save_custom_tg_channels()
    return True, entry

def remove_custom_tg_channel(handle):
    """يحذف قناة تيليغرام مخصصة من قائمة المصادر"""
    handle = handle.lstrip("@").strip()
    removed_from = []
    for lang in list(_custom_tg_channels.keys()):
        before = len(_custom_tg_channels[lang])
        _custom_tg_channels[lang] = [c for c in _custom_tg_channels[lang] if c["handle"] != handle]
        if len(_custom_tg_channels[lang]) < before:
            removed_from.append(lang)
    for lang in list(TELEGRAM_NEWS_CHANNELS.keys()):
        TELEGRAM_NEWS_CHANNELS[lang] = [c for c in TELEGRAM_NEWS_CHANNELS[lang] if c["handle"] != handle]
    if removed_from:
        save_custom_tg_channels()
        return True, removed_from
    return False, []

# ======== نظام النشر على وسائل التواصل الاجتماعي ========
import base64 as _b64

SOCIAL_SETTINGS_FILE = "social_settings.json"
_social_settings     = load_json(SOCIAL_SETTINGS_FILE, {})
_social_last_post    = {"ts": 0}          # آخر وقت نشر (rate limit)
_social_posted_links = set()              # الروابط التي نُشرت مسبقاً
SOCIAL_MIN_INTERVAL  = 5 * 60            # 5 دقائق بين كل منشور على الأقل

def handle_admin_channels(uid, call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ إضافة قناة/مجموعة", callback_data="ch_add"),
        types.InlineKeyboardButton("➖ حذف قناة/مجموعة", callback_data="ch_remove"),
        types.InlineKeyboardButton("📋 قائمة القنوات", callback_data="ch_list"),
        types.InlineKeyboardButton("📢 بث أخبار للقنوات الآن", callback_data="ch_broadcast_now"),
    )
    count = len(channels_groups)
    bot.send_message(uid,
        f"📺 *إدارة القنوات والمجموعات*\n\n"
        f"📊 عدد القنوات/المجموعات المضافة: `{count}`\n\n"
        f"💡 *كيفية الإضافة:*\n"
        f"1. أضف البوت كأدمن في القناة/المجموعة\n"
        f"2. أرسل ID القناة أو المجموعة (مثال: -1001234567890)\n"
        f"3. حدد اللغة المناسبة لإرسال الأخبار",
        parse_mode="Markdown", reply_markup=markup
    )

def add_channel_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    lines = message.text.strip().split("\n")
    if len(lines) < 2:
        bot.send_message(uid,
            "❌ أرسل في سطرين:\n"
            "السطر 1: ID القناة/المجموعة (مثال: -1001234567890)\n"
            "السطر 2: اللغة (مثال: العربية 🇮🇶)"
        )
        return
    try:
        chat_id = int(lines[0].strip())
        lang = lines[1].strip()
        try:
            chat_info = bot.get_chat(chat_id)
            title = chat_info.title or str(chat_id)
            chat_type = chat_info.type
        except Exception as e:
            bot.send_message(uid, f"❌ تعذّر الوصول للقناة/المجموعة: {e}\nتأكد أن البوت أدمن فيها.")
            return
        for ch in channels_groups:
            if ch["id"] == chat_id:
                bot.send_message(uid, f"⚠️ هذه القناة/المجموعة مضافة مسبقاً: *{title}*", parse_mode="Markdown")
                return
        feeds = RSS.get(lang, RSS.get("العربية 🇮🇶", []))
        initial_sent = list(prefill_sent_news(feeds).keys())  # dict keys → list of links
        channels_groups.append({"id": chat_id, "title": title, "type": chat_type, "lang": lang, "sent_news": initial_sent})
        save_channels_groups()
        bot.send_message(uid,
            f"✅ تمت الإضافة بنجاح!\n"
            f"📺 *{title}*\n"
            f"🆔 ID: `{chat_id}`\n"
            f"🗣 اللغة: {lang}\n"
            f"📡 النوع: {chat_type}\n"
            f"📰 تم حفظ {len(initial_sent)} خبر موجود — ستصل فقط الأخبار الجديدة من الآن.",
            parse_mode="Markdown"
        )
    except ValueError:
        bot.send_message(uid, "❌ ID غير صحيح. يجب أن يكون رقماً مثل: -1001234567890")
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {e}")

def remove_channel_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    try:
        chat_id = int(message.text.strip())
        removed = None
        for i, ch in enumerate(channels_groups):
            if ch["id"] == chat_id:
                removed = channels_groups.pop(i)
                break
        if removed:
            save_channels_groups()
            bot.send_message(uid, f"✅ تم حذف القناة/المجموعة: *{removed['title']}*", parse_mode="Markdown")
        else:
            bot.send_message(uid, "⚠️ هذا ID غير موجود في القائمة.")
    except ValueError:
        bot.send_message(uid, "❌ أرسل ID رقمياً فقط.")
    except Exception as e:
        bot.send_message(uid, f"❌ خطأ: {e}")

@bot.message_handler(commands=["addchannel"])
def cmd_addchannel(m):
    """
    أمر للأدمن: إضافة قناة تيليغرام ديناميكياً لقائمة مصادر الأخبار.
    الاستخدام:  /addchannel <handle> [اللغة] [الاسم]
    مثال:       /addchannel AlJazeeraArabic العربية 🇮🇶 الجزيرة العربية
    """
    uid = m.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ هذا الأمر للمشرفين فقط.")
        return
    parts = m.text.strip().split(None, 3)
    if len(parts) < 2:
        langs_list = "\n".join(f"• `{l}`" for l in list(TELEGRAM_NEWS_CHANNELS.keys())[:8])
        bot.send_message(uid,
            "📺 *إضافة قناة تيليغرام كمصدر أخبار*\n\n"
            "*الاستخدام:*\n"
            "`/addchannel <handle> [اللغة] [الاسم]`\n\n"
            "*أمثلة:*\n"
            "`/addchannel NewChannelHandle العربية 🇮🇶 اسم القناة`\n"
            "`/addchannel BBCBreaking English 🇬🇧 BBC Breaking`\n\n"
            f"*اللغات المتاحة:*\n{langs_list}\n...",
            parse_mode="Markdown"
        )
        return
    handle = parts[1].lstrip("@")
    lang = parts[2] if len(parts) > 2 else "العربية 🇮🇶"
    # إذا اللغة تبدأ بـ "ال" وبعدها مسافة (معظمها عربية) دمجها مع الإيموجي
    # ابحث عن أقرب تطابق للغة
    matched_lang = None
    for l in TELEGRAM_NEWS_CHANNELS.keys():
        if lang in l or l.startswith(lang.split()[0]):
            matched_lang = l
            break
    if not matched_lang:
        matched_lang = lang  # أضفها كلغة جديدة
    name = parts[3] if len(parts) > 3 else f"@{handle}"
    ok, result = add_custom_tg_channel(matched_lang, handle, name)
    if ok:
        total = len(TELEGRAM_NEWS_CHANNELS.get(matched_lang, []))
        bot.send_message(uid,
            f"✅ *تمت الإضافة بنجاح!*\n\n"
            f"📺 القناة: `@{handle}`\n"
            f"📛 الاسم: {name}\n"
            f"🌐 اللغة: {matched_lang}\n"
            f"📊 إجمالي قنوات {matched_lang}: *{total}*\n\n"
            f"ستبدأ القناة في المساهمة بالأخبار في دورة البث القادمة.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(uid, f"⚠️ `@{handle}` {result} في {matched_lang}", parse_mode="Markdown")


@bot.message_handler(commands=["removechannel"])
def cmd_removechannel(m):
    """
    أمر للأدمن: حذف قناة تيليغرام من قائمة المصادر المخصصة.
    الاستخدام: /removechannel <handle>
    """
    uid = m.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ هذا الأمر للمشرفين فقط.")
        return
    parts = m.text.strip().split()
    if len(parts) < 2:
        bot.send_message(uid,
            "🗑 *حذف قناة من مصادر الأخبار*\n\n"
            "*الاستخدام:*\n`/removechannel <handle>`\n\n"
            "*مثال:*\n`/removechannel OldChannelHandle`\n\n"
            "⚠️ يعمل فقط على القنوات المُضافة يدوياً (المخصصة).",
            parse_mode="Markdown"
        )
        return
    handle = parts[1].lstrip("@")
    ok, langs = remove_custom_tg_channel(handle)
    if ok:
        bot.send_message(uid,
            f"✅ تم حذف `@{handle}` من مصادر الأخبار.\n"
            f"اللغات المتأثرة: {', '.join(langs)}",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(uid,
            f"⚠️ `@{handle}` غير موجودة في قائمة المصادر المخصصة.\n"
            f"(القنوات الافتراضية لا يمكن حذفها بهذا الأمر)",
            parse_mode="Markdown"
        )


@bot.message_handler(commands=["listchannels"])
def cmd_listchannels(m):
    """يعرض القنوات المضافة ديناميكياً فقط (المخصصة) مع إمكانية حذفها"""
    uid = m.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ هذا الأمر للمشرفين فقط.")
        return
    if not _custom_tg_channels or all(len(v) == 0 for v in _custom_tg_channels.values()):
        bot.send_message(uid,
            "📭 لم تُضف أي قنوات مخصصة بعد.\n"
            "استخدم `/addchannel` لإضافة قنوات جديدة.",
            parse_mode="Markdown"
        )
        return
    msg = "📺 *قنوات التيليغرام المضافة يدوياً:*\n\n"
    for lang, channels in _custom_tg_channels.items():
        if channels:
            msg += f"*{lang}:*\n"
            for ch in channels:
                msg += f"  • `@{ch['handle']}` — {ch['name']}\n"
                msg += f"    🗑 `/removechannel {ch['handle']}`\n"
            msg += "\n"
    bot.send_message(uid, msg, parse_mode="Markdown")


# ======== /chart ========

CHART_CATEGORIES = {
    "crypto": (
        "🪙 Crypto",
        ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
         "LINK", "DOT", "MATIC", "LTC", "TRX", "ATOM", "TON",
         "SHIB", "NEAR", "ARB", "UNI", "ALGO"],
    ),
    "forex": (
        "💱 Forex",
        ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
         "USDCHF=X", "NZDUSD=X", "USDTRY=X", "USDEGP=X",
         "USDSAR=X", "USDKWD=X", "USDIQD=X"],
    ),
    "metals": (
        "🥇 Metals & Commodities",
        ["GC=F", "SI=F", "PL=F", "HG=F", "CL=F", "BZ=F", "NG=F",
         "ZW=F", "ZC=F", "CC=F"],
    ),
    "stocks": (
        "📈 Stocks",
        ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL",
         "META", "NFLX", "BABA", "2222.SR"],
    ),
    "indices": (
        "📊 Indices",
        ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^DAX",
         "^N225", "^HSI", "^BSESN", "^STOXX50E"],
    ),
}

CHART_ASSET_LABELS = {
    "BTC": "Bitcoin",    "ETH": "Ethereum",  "SOL": "Solana",    "BNB": "BNB",
    "XRP": "XRP",        "DOGE": "Dogecoin", "ADA": "Cardano",   "AVAX": "Avalanche",
    "LINK": "Chainlink", "DOT": "Polkadot",  "MATIC": "Polygon", "LTC": "Litecoin",
    "TRX": "TRON",       "ATOM": "Cosmos",   "TON": "TON",       "SHIB": "SHIB",
    "NEAR": "NEAR",      "ARB": "Arbitrum",  "UNI": "Uniswap",   "ALGO": "Algorand",
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF",
    "NZDUSD=X": "NZD/USD", "USDTRY=X": "USD/TRY", "USDEGP=X": "USD/EGP",
    "USDSAR=X": "USD/SAR", "USDKWD=X": "USD/KWD", "USDIQD=X": "USD/IQD",
    "GC=F": "Gold",     "SI=F": "Silver",     "PL=F": "Platinum",
    "HG=F": "Copper",   "CL=F": "WTI Oil",    "BZ=F": "Brent Oil",
    "NG=F": "Nat. Gas", "ZW=F": "Wheat",      "ZC=F": "Corn",    "CC=F": "Cocoa",
    "AAPL": "Apple",    "TSLA": "Tesla",      "NVDA": "NVIDIA",  "MSFT": "Microsoft",
    "AMZN": "Amazon",   "GOOGL": "Google",    "META": "Meta",    "NFLX": "Netflix",
    "BABA": "Alibaba",  "2222.SR": "Aramco",
    "^GSPC": "S&P 500", "^IXIC": "NASDAQ",    "^DJI": "Dow Jones",
    "^FTSE": "FTSE 100","^DAX": "DAX",        "^N225": "Nikkei 225",
    "^HSI": "Hang Seng","^BSESN": "Sensex",   "^STOXX50E": "Euro Stoxx 50",
}

CHART_CAT_PROMPTS = {
    "العربية 🇮🇶":    "📊 *اختر فئة الأصل:*\n\n🪙 عملات رقمية │ 💱 فوركس │ 🥇 معادن وسلع │ 📈 أسهم │ 📊 مؤشرات",
    "English 🇬🇧":   "📊 *Choose asset category:*\n\n🪙 Crypto │ 💱 Forex │ 🥇 Metals & Commodities │ 📈 Stocks │ 📊 Indices",
    "Русский 🇷🇺":   "📊 *Выберите категорию:*\n\n🪙 Крипто │ 💱 Форекс │ 🥇 Металлы │ 📈 Акции │ 📊 Индексы",
    "فارسی 🇮🇷":     "📊 *دستهبندی را انتخاب کنید:*\n\n🪙 رمزارز │ 💱 فارکس │ 🥇 فلزات │ 📈 سهام │ 📊 شاخصها",
    "हिन्दी 🇮🇳":    "📊 *श्रेणी चुनें:*\n\n🪙 क्रिप्टो │ 💱 फ़ॉरेक्स │ 🥇 धातु │ 📈 स्टॉक │ 📊 सूचकांक",
    "Português 🇧🇷": "📊 *Escolha a categoria:*\n\n🪙 Cripto │ 💱 Forex │ 🥇 Metais │ 📈 Ações │ 📊 Índices",
    "Türkçe 🇹🇷":    "📊 *Kategori seçin:*\n\n🪙 Kripto │ 💱 Forex │ 🥇 Metaller │ 📈 Hisseler │ 📊 Endeksler",
    "اردو 🇵🇰":      "📊 *زمرہ منتخب کریں:*\n\n🪙 کرپٹو │ 💱 فاریکس │ 🥇 دھاتیں │ 📈 حصص │ 📊 اشاریے",
    "Deutsch 🇩🇪":   "📊 *Kategorie wählen:*\n\n🪙 Krypto │ 💱 Forex │ 🥇 Metalle │ 📈 Aktien │ 📊 Indizes",
    "Українська 🇺🇦":"📊 *Виберіть категорію:*\n\n🪙 Крипто │ 💱 Форекс │ 🥇 Метали │ 📈 Акції │ 📊 Індекси",
    "Italiano 🇮🇹":  "📊 *Scegli categoria:*\n\n🪙 Cripto │ 💱 Forex │ 🥇 Metalli │ 📈 Azioni │ 📊 Indici",
    "Español 🇲🇽":   "📊 *Elige categoría:*\n\n🪙 Cripto │ 💱 Forex │ 🥇 Metales │ 📈 Acciones │ 📊 Índices",
}

CHART_INTERVALS = {
    "Minutes": {"label": "آخر 10 دقائق",  "label_en": "Last 10 Minutes (Minute)", "range": "1d",  "yf_interval": "1m",  "ts_fmt": "%H:%M",   "ts_label": "Minute"},
    "Hours":   {"label": "آخر 10 ساعات",  "label_en": "Last 10 Hours (Hourly)",   "range": "7d",  "yf_interval": "1h",  "ts_fmt": "%H:%M",   "ts_label": "Hourly"},
    "Days":    {"label": "آخر 10 أيام",   "label_en": "Last 10 Days (Daily)",     "range": "90d", "yf_interval": "1d",  "ts_fmt": "%d %b",   "ts_label": "Daily"},
}

CHART_PROMPTS = {
    "العربية 🇮🇶":   "📊 اختر الأصل الذي تريد رسمه:",
    "English 🇬🇧":  "📊 Choose the asset you want to chart:",
    "Русский 🇷🇺":  "📊 Выберите актив для графика:",
    "فارسی 🇮🇷":    "📊 دارایی مورد نظر برای نمودار را انتخاب کنید:",
    "हिन्दी 🇮🇳":   "📊 चार्ट के लिए संपत्ति चुनें:",
    "Português 🇧🇷":"📊 Escolha o ativo para o gráfico:",
    "Türkçe 🇹🇷":   "📊 Grafik için varlık seçin:",
    "اردو 🇵🇰":     "📊 چارٹ کے لیے اثاثہ منتخب کریں:",
    "Deutsch 🇩🇪":  "📊 Wählen Sie das Asset für den Chart:",
    "Українська 🇺🇦":"📊 Оберіть актив для графіка:",
    "Italiano 🇮🇹": "📊 Scegli l'asset per il grafico:",
    "Español 🇲🇽":  "📊 Elige el activo para el gráfico:",
}

INTERVAL_PROMPTS = {
    "العربية 🇮🇶":   "⏱ اختر الفاصل الزمني:",
    "English 🇬🇧":  "⏱ Choose the time interval:",
    "Русский 🇷🇺":  "⏱ Выберите временной интервал:",
    "فارسی 🇮🇷":    "⏱ بازه زمانی را انتخاب کنید:",
    "हिन्दी 🇮🇳":   "⏱ समय अंतराल चुनें:",
    "Português 🇧🇷":"⏱ Escolha o intervalo de tempo:",
    "Türkçe 🇹🇷":   "⏱ Zaman aralığı seçin:",
    "اردو 🇵🇰":     "⏱ وقت کا وقفہ منتخب کریں:",
    "Deutsch 🇩🇪":  "⏱ Zeitintervall wählen:",
    "Українська 🇺🇦":"⏱ Виберіть часовий інтервал:",
    "Italiano 🇮🇹": "⏱ Scegli l'intervallo di tempo:",
    "Español 🇲🇽":  "⏱ Elige el intervalo de tiempo:",
}

