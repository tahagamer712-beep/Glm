# -*- coding: utf-8 -*-
"""
  admin_panel.py — اللوحة الرئيسية + admin_command

  يُصدِّر لوحة الإدارة الرئيسية وأوامرها.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def is_admin(uid):
    return int(uid) == ADMIN_ID or int(uid) in extra_admins

def save_extra_admins():
    save_json(ADMINS_FILE, extra_admins)

# ======== القنوات والمجموعات ========
# كل عنصر: {"id": chat_id, "title": "اسم القناة", "type": "channel"/"group", "lang": "العربية 🇮🇶"}
# مخزنة في SQLite لضمان البقاء بعد إعادة تشغيل Heroku
_migrate_channels_from_json()   # نقل من JSON إلى SQLite عند أول تشغيل
channels_groups = _db_load_channels()
if not channels_groups:         # fallback: إذا SQLite فارغ، حاول JSON
    channels_groups = load_json(CHANNELS_FILE, [])

# =====================================================================
# ==================== نظام الرياضة ==================================
# =====================================================================
SPORTS_LEAGUES = {
    # ══════════════ كرة القدم ══════════════
    "pl":           {"name": "الدوري الإنجليزي الممتاز",  "espn": "soccer/eng.1",                  "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "sport": "football"},
    "laliga":       {"name": "الدوري الإسباني",            "espn": "soccer/esp.1",                  "flag": "🇪🇸", "sport": "football"},
    "bundesliga":   {"name": "الدوري الألماني",            "espn": "soccer/ger.1",                  "flag": "🇩🇪", "sport": "football"},
    "seriea":       {"name": "الدوري الإيطالي",            "espn": "soccer/ita.1",                  "flag": "🇮🇹", "sport": "football"},
    "ligue1":       {"name": "الدوري الفرنسي",             "espn": "soccer/fra.1",                  "flag": "🇫🇷", "sport": "football"},
    "ucl":          {"name": "دوري أبطال أوروبا",          "espn": "soccer/uefa.champions",         "flag": "🏆", "sport": "football"},
    "uel":          {"name": "الدوري الأوروبي",            "espn": "soccer/uefa.europa",            "flag": "🟠", "sport": "football"},
    "uecl":         {"name": "دوري المؤتمر الأوروبي",      "espn": "soccer/uefa.europa.conf",       "flag": "🟢", "sport": "football"},
    "eredivisie":   {"name": "الدوري الهولندي",            "espn": "soccer/ned.1",                  "flag": "🇳🇱", "sport": "football"},
    "primera":      {"name": "الدوري البرتغالي",           "espn": "soccer/por.1",                  "flag": "🇵🇹", "sport": "football"},
    "superlig":     {"name": "الدوري التركي",              "espn": "soccer/tur.1",                  "flag": "🇹🇷", "sport": "football"},
    "saudi":        {"name": "الدوري السعودي",             "espn": "soccer/ksa.1",                  "flag": "🇸🇦", "sport": "football"},
    "egypt":        {"name": "الدوري المصري",              "espn": "soccer/egy.1",                  "flag": "🇪🇬", "sport": "football"},
    "iraqleague":   {"name": "الدوري العراقي",             "espn": None, "scores365_id": 6822,    "flag": "🇮🇶", "sport": "football"},
    "mls":          {"name": "الدوري الأمريكي (MLS)",      "espn": "soccer/usa.1",                  "flag": "🇺🇸", "sport": "football"},
    "libertadores": {"name": "كوبا ليبرتادوريس",          "espn": "soccer/conmebol.libertadores",  "flag": "🌎", "sport": "football"},
    "copaamerica":  {"name": "كوبا أمريكا",                "espn": "soccer/conmebol.copa_america",  "flag": "🌎", "sport": "football"},
    "argentinal":   {"name": "الدوري الأرجنتيني",          "espn": "soccer/arg.1",                  "flag": "🇦🇷", "sport": "football"},
    "brasileirao":  {"name": "الدوري البرازيلي",           "espn": "soccer/bra.1",                  "flag": "🇧🇷", "sport": "football"},
    "wc":           {"name": "كأس العالم FIFA",            "espn": "soccer/fifa.world",             "flag": "🌍", "sport": "football"},
    "acl":          {"name": "دوري أبطال آسيا",            "espn": "soccer/afc.champions",          "flag": "🌏", "sport": "football"},
    "concacaf":     {"name": "CONCACAF أبطال",             "espn": "soccer/concacaf.champions",     "flag": "🌍", "sport": "football"},
    "scottish":     {"name": "الدوري الاسكتلندي",          "espn": "soccer/sco.1",                  "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "sport": "football"},
    "mxleague":     {"name": "الدوري المكسيكي",            "espn": "soccer/mex.1",                  "flag": "🇲🇽", "sport": "football"},
    # ══════════════ كرة السلة ══════════════
    "nba":          {"name": "دوري NBA",                   "espn": "basketball/nba",                "flag": "🏀", "sport": "basketball"},
    "wnba":         {"name": "دوري WNBA (نسائي)",          "espn": "basketball/wnba",               "flag": "🏀", "sport": "basketball"},
    "euroleague":   {"name": "يوروليغ للسلة",              "espn": "basketball/euroleague",         "flag": "🇪🇺", "sport": "basketball"},
    "ncaab":        {"name": "سلة الجامعات الأمريكية",    "espn": "basketball/mens-college-basketball","flag":"🏀","sport":"basketball"},
    # ══════════════ التنس ══════════════
    "atp":          {"name": "ATP - رجال",                 "espn": "tennis/atp.singles",            "flag": "🎾", "sport": "tennis"},
    "wta":          {"name": "WTA - نساء",                 "espn": "tennis/wta.singles",            "flag": "🎾", "sport": "tennis"},
    "wimbledon":    {"name": "ويمبلدون",                   "espn": "tennis/wimbledon",              "flag": "🌿", "sport": "tennis"},
    "usopen_t":     {"name": "يو إس أوبن (تنس)",           "espn": "tennis/us-open",               "flag": "🎾", "sport": "tennis"},
    "frenchopen":   {"name": "رولان غاروس",               "espn": "tennis/french-open",           "flag": "🎾", "sport": "tennis"},
    "ausopen":      {"name": "أستراليان أوبن",             "espn": "tennis/australian-open",       "flag": "🎾", "sport": "tennis"},
    # ══════════════ السيارات ══════════════
    "f1":           {"name": "الفورمولا 1",                "espn": "racing/f1",                     "flag": "🏎️", "sport": "racing"},
    "nascar":       {"name": "ناسكار كاب سيريز",           "espn": "racing/nascar-winston-cup",     "flag": "🏁", "sport": "racing"},
    "nascar_xfin":  {"name": "ناسكار Xfinity",            "espn": "racing/nascar-xfinity",         "flag": "🏁", "sport": "racing"},
    "motogp":       {"name": "موتو جي بي MotoGP",          "espn": "racing/motogp",                 "flag": "🏍️", "sport": "racing"},
    "indycar":      {"name": "إندي كار IndyCar",           "espn": "racing/indycar",                "flag": "🏎️", "sport": "racing"},
    "wrc":          {"name": "WRC - رالي العالم",          "espn": None,                             "flag": "🚗", "sport": "racing"},
    "dakar":        {"name": "رالي داكار",                 "espn": None,                             "flag": "🏜️", "sport": "racing"},
    # ══════════════ الهوكي ══════════════
    "nhl":          {"name": "دوري NHL (هوكي الجليد)",     "espn": "hockey/nhl",                    "flag": "🏒", "sport": "hockey"},
    # ══════════════ البيسبول ══════════════
    "mlb":          {"name": "دوري MLB (بيسبول)",          "espn": "baseball/mlb",                  "flag": "⚾", "sport": "baseball"},
    # ══════════════ كرة القدم الأمريكية ══════════════
    "nfl":          {"name": "دوري NFL (أمريكي)",          "espn": "football/nfl",                  "flag": "🏈", "sport": "american_football"},
    "ncaaf":        {"name": "كرة الجامعات الأمريكية",    "espn": "football/college-football",     "flag": "🏈", "sport": "american_football"},
    # ══════════════ الغولف ══════════════
    "pga":          {"name": "PGA Tour (غولف)",            "espn": "golf/pga",                      "flag": "⛳", "sport": "golf"},
    "lpga":         {"name": "LPGA Tour (غولف نسائي)",    "espn": "golf/lpga",                     "flag": "⛳", "sport": "golf"},
    "masters":      {"name": "بطولة الماسترز",            "espn": "golf/masters",                  "flag": "🏆", "sport": "golf"},
    # ══════════════ كريكيت ══════════════
    "ipl":          {"name": "دوري IPL (كريكيت هندي)",    "espn": "cricket/ipl",                   "flag": "🏏", "sport": "cricket"},
    "icc_wc":       {"name": "كأس العالم كريكيت",          "espn": "cricket/icc.wc",                "flag": "🏏", "sport": "cricket"},
    # ══════════════ كرة اليد ══════════════
    "handball_wc":  {"name": "كأس العالم كرة اليد",       "espn": None,                             "flag": "🤾", "sport": "handball"},
    # ══════════════ الرياضات الإلكترونية ══════════════
    "esports":      {"name": "Esports / رياضات إلكترونية","espn": None,                             "flag": "🎮", "sport": "esports"},
    # ══════════════ كرة اليد (إضافة) ══════════════
    "handball_ecl": {"name": "دوري أبطال كرة اليد",       "espn": None,                             "flag": "🤾", "sport": "handball"},
    "handball_ehf": {"name": "EHF Euro كرة اليد",          "espn": None,                             "flag": "🤾", "sport": "handball"},
    # ══════════════ سباق السيارات (إضافة) ══════════════
    "f1_sprint":    {"name": "فورمولا 1 — سباق السبرينت", "espn": "racing/f1",                     "flag": "🏎️", "sport": "racing"},
    "f2":           {"name": "فورمولا 2 (F2)",             "espn": None,                             "flag": "🏎️", "sport": "racing"},
    "f3":           {"name": "فورمولا 3 (F3)",             "espn": None,                             "flag": "🏎️", "sport": "racing"},
    "fe":           {"name": "فورمولا E (كهربائي)",        "espn": None,                             "flag": "⚡", "sport": "racing"},
    "superbike":    {"name": "World Superbike WSBK",        "espn": None,                             "flag": "🏍️", "sport": "racing"},
    # ══════════════ تنس إضافي ══════════════
    "atp_doubles":  {"name": "ATP زوجي",                   "espn": "tennis/atp.doubles",            "flag": "🎾", "sport": "tennis"},
    "wta_doubles":  {"name": "WTA زوجي",                   "espn": "tennis/wta.doubles",            "flag": "🎾", "sport": "tennis"},
    # ══════════════ سلة إضافي ══════════════
    "nba_summer":   {"name": "NBA Summer League",           "espn": "basketball/nba",                "flag": "🏀", "sport": "basketball"},
    "fiba_wc":      {"name": "كأس العالم للسلة FIBA",       "espn": None,                             "flag": "🏀", "sport": "basketball"},
    # ══════════════ كرة القدم الأمريكية إضافي ══════════════
    "xfl":          {"name": "دوري XFL",                   "espn": "football/xfl",                  "flag": "🏈", "sport": "american_football"},
    "cfl":          {"name": "الدوري الكندي CFL",          "espn": "football/cfl",                  "flag": "🏈", "sport": "american_football"},
    # ══════════════ غولف إضافي ══════════════
    "open_champ":   {"name": "البطولة المفتوحة (بريطانية)","espn": "golf/theopen",                  "flag": "⛳", "sport": "golf"},
    "usopen_g":     {"name": "US Open غولف",               "espn": "golf/usopen",                   "flag": "⛳", "sport": "golf"},
    "ryder_cup":    {"name": "كأس رايدر",                  "espn": "golf/rydercup",                 "flag": "⛳", "sport": "golf"},
    # ══════════════ كريكيت إضافي ══════════════
    "cricket_t20":  {"name": "T20 World Cup كريكيت",        "espn": "cricket/icc.wt20",              "flag": "🏏", "sport": "cricket"},
    "cricket_odi":  {"name": "ODI Series كريكيت",           "espn": None,                             "flag": "🏏", "sport": "cricket"},
    "bbl":          {"name": "Big Bash League كريكيت",     "espn": "cricket/bbl",                   "flag": "🏏", "sport": "cricket"},
    # ══════════════ هوكي إضافي ══════════════
    "iihf_wc":      {"name": "كأس العالم هوكي IIHF",       "espn": "hockey/world-men",              "flag": "🏒", "sport": "hockey"},
    "khl":          {"name": "دوري KHL الروسي",            "espn": None,                             "flag": "🏒", "sport": "hockey"},
    # ══════════════ بيسبول إضافي ══════════════
    "npb":          {"name": "Nippon Pro Baseball (ياباني)","espn": None,                             "flag": "⚾", "sport": "baseball"},
    "wbc":          {"name": "World Baseball Classic",      "espn": None,                             "flag": "⚾", "sport": "baseball"},
}

SPORTS_NEWS_RSS = {
    "العربية 🇮🇶": [
        "https://feeds.bbci.co.uk/arabic/sport/rss.xml",
        "https://www.france24.com/ar/sport/rss",
        "https://arabic.rt.com/rss/sport/",
        "https://arabic.sport360.com/feed/",
    ],
    "English 🇬🇧": [
        "https://www.skysports.com/rss/12040",
        "https://feeds.bbci.co.uk/sport/football/rss.xml",
    ],
}


def admin_panel(uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
        types.InlineKeyboardButton("👥 المستخدمون", callback_data="admin_users"),
        types.InlineKeyboardButton("📢 إرسال رسالة للكل", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🚨 خبر عاجل مخصص", callback_data="admin_breaking_news"),
        types.InlineKeyboardButton("🔴 إيقاف/تشغيل البوت", callback_data="admin_pause"),
        types.InlineKeyboardButton("⏱ توقيت البث", callback_data="admin_interval"),
        types.InlineKeyboardButton("📡 إدارة RSS", callback_data="admin_rss"),
        types.InlineKeyboardButton("🚫 القائمة السوداء", callback_data="admin_blacklist"),
        types.InlineKeyboardButton("💰 المالية", callback_data="admin_finance"),
        types.InlineKeyboardButton("📖 عداد القراءة", callback_data="admin_read_stats"),
        types.InlineKeyboardButton("✏️ تغيير رسالة الترحيب", callback_data="admin_welcome"),
        types.InlineKeyboardButton("👑 إدارة الأدمن", callback_data="admin_manage_admins"),
        types.InlineKeyboardButton("📺 إدارة القنوات/المجموعات", callback_data="admin_channels"),
        types.InlineKeyboardButton("📈 إحصائيات القنوات", callback_data="admin_channel_stats"),
        types.InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user"),
        types.InlineKeyboardButton("✉️ رسالة لمستخدم", callback_data="admin_msg_user"),
        types.InlineKeyboardButton("📋 قائمة الأوامر", callback_data="admin_commands"),
        types.InlineKeyboardButton("✏️ شكل رسالة الخبر", callback_data="admin_news_format"),
        types.InlineKeyboardButton("💬 صندوق الرسائل", callback_data="admin_inbox"),
        types.InlineKeyboardButton("⭐ تقييمات المستخدمين", callback_data="admin_ratings"),
        types.InlineKeyboardButton("💾 نسخة احتياطية", callback_data="admin_backup"),
        types.InlineKeyboardButton("🔄 إعادة تعيين الأخبار", callback_data="admin_reset_sent_news"),
        types.InlineKeyboardButton("📴 إيقاف البث" if not broadcast_paused else "📡 تشغيل البث", callback_data="admin_toggle_broadcast"),
        types.InlineKeyboardButton("🗑 إعادة تعيين البوت كاملاً", callback_data="admin_full_reset"),
        types.InlineKeyboardButton("🔍 تشخيص الإرسال", callback_data="admin_debugnews"),
        types.InlineKeyboardButton("🧹 مسح كاش الأخبار", callback_data="admin_clearcache"),
        types.InlineKeyboardButton("⚡ بث فوري الآن", callback_data="admin_forcenews"),
        types.InlineKeyboardButton("⚙️ إدارة الميزات", callback_data="admin_features"),
    )
    bot.send_message(uid, "👑 *لوحة تحكم الأدمن:*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        return
    admin_panel(message.from_user.id)

HELP_TEXTS = {
    "العربية 🇮🇶": (
        "📖 *دليل بوت @Iraqnowbot الشامل*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 بوت أخبار ذكي مجاني 100% — أخبار لحظية من 50+ مصدر عالمي بلغتك.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *أخبار وبحث*\n"
        "`/news` — آخر الأخبار الآن\n"
        "`/trending` — الأكثر تداولاً\n"
        "`/summary` — ملخص أخبار اليوم (أبرز 5)\n"
        "`/search` كلمة — بحث في أخبار 24 ساعة\n"
        "`/deepsearch` موضوع — بحث عميق بالذكاء الاصطناعي\n"
        "`/menu` — قائمة الاختيارات الذكية\n\n"
        "🤖 *تحليل بالذكاء الاصطناعي*\n"
        "`/ask` سؤال — اسأل الذكاء الاصطناعي\n"
        "`/verify` خبر — تحقق من صحة خبر\n"
        "`/analyze` موضوع — تحليل شامل بـ AI\n"
        "`/compare` موضوع — مقارنة المصادر\n"
        "`/timeline` موضوع — خط زمني للأحداث\n"
        "`/predict` موضوع — توقع المستقبل\n"
        "`/intel` موضوع — تقرير استخباراتي\n"
        "`/history` موضوع — السياق التاريخي\n"
        "`/connections` موضوع — شبكة التأثير والروابط\n"
        "`/sources` — أبرز مصادر الأخبار\n\n"
        "🎙 *صوت وبودكاست*\n"
        "`/podcast` — بودكاست يومي صوتي كامل (AI+TTS)\n"
        "`/audiobriefing` — موجز إخباري نصي للقراءة\n\n"
        "👁 *متابعة القصص*\n"
        "`/follow` موضوع — تابع قصة وتلقَّ تحديثاتها\n"
        "`/unfollow` موضوع — إلغاء متابعة قصة\n"
        "`/tip` — أرسل معلومة أو خبر للفريق\n\n"
        "💰 *أسواق وتتبع الأصول*\n"
        "`/markets` — الأسواق المالية الكاملة\n"
        "`/currency` — أسعار العملات والذهب والنفط\n"
        "`/chart` BTC — رسم بياني لأي سهم أو عملة\n"
        "`/addtrack` BTC — أضف أصلاً لقائمة تتبعك\n"
        "`/removetrack` BTC — احذف أصلاً من التتبع\n"
        "`/mytrack` — شوف قائمة أصولك المتتبّعة\n\n"
        "🌍 *خدمات أخرى*\n"
        "`/weather` — الطقس التفصيلي لمدينتك\n"
        "`/sports` — الرياضة والمباريات المباشرة\n"
        "`/parliament` — نتائج وأخبار البرلمان\n"
        "`/influence` — تحليل التأثير والقوى السياسية\n"
        "`/econ` — الوضع الاقتصادي والمؤشرات\n"
        "`/discover` — اكتشاف مصادر إخبارية جديدة\n"
        "`/map` — خريطة الأحداث والأزمات\n\n"
        "⚙️ *الإعدادات*\n"
        "`/start` — القائمة الرئيسية\n"
        "`/profile` — ملفك الشخصي وإحصائياتك\n"
        "`/settings` — اللغة والمدينة والإشعارات\n"
        "`/restart` — إعادة ضبط الإعدادات\n"
        "`/help` — هذا الدليل\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 الأخبار تصلك تلقائياً · كل الميزات مجانية 100%\n"
        "🤖 @Iraqnowbot"
    ),
    "English 🇬🇧": (
        "📖 *@Iraqnowbot — Complete Guide*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 100% free smart news bot — breaking news from 50+ global sources in your language.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *News & Search*\n"
        "`/news` — Latest news now\n"
        "`/trending` — Most trending stories\n"
        "`/summary` — Today's top 5 digest\n"
        "`/search` keyword — Search news from last 24h\n"
        "`/deepsearch` topic — AI deep research (8-section analysis)\n"
        "`/menu` — Smart selection menu\n\n"
        "🤖 *AI Analysis*\n"
        "`/ask` question — Ask the AI anything\n"
        "`/verify` claim — Fact-check a news story\n"
        "`/analyze` topic — Full AI analysis\n"
        "`/compare` topic — Compare news sources\n"
        "`/timeline` topic — Event timeline\n"
        "`/predict` topic — AI future prediction\n"
        "`/intel` topic — Intelligence report\n"
        "`/history` topic — Historical context\n"
        "`/connections` topic — Influence network\n"
        "`/sources` — Top news sources list\n\n"
        "🎙 *Voice & Podcast*\n"
        "`/podcast` — Full daily podcast episode (AI+TTS)\n"
        "`/audiobriefing` — Text news briefing for reading\n\n"
        "👁 *Story Tracking*\n"
        "`/follow` story — Follow a story & get updates\n"
        "`/unfollow` story — Unfollow a story\n"
        "`/tip` — Send a news tip to the team\n\n"
        "💰 *Markets & Asset Tracking*\n"
        "`/markets` — Full financial markets overview\n"
        "`/currency` — Currency, gold & oil rates\n"
        "`/chart` BTC — Price chart for any stock or crypto\n"
        "`/addtrack` BTC — Add asset to your watchlist\n"
        "`/removetrack` BTC — Remove asset from watchlist\n"
        "`/mytrack` — View your watchlist\n\n"
        "🌍 *Other Services*\n"
        "`/weather` — Detailed weather for your city\n"
        "`/sports` — Sports & live matches\n"
        "`/parliament` — Parliament news & results\n"
        "`/influence` — Political influence analysis\n"
        "`/econ` — Economic indicators & analysis\n"
        "`/discover` — Discover new news sources\n"
        "`/map` — Events & crisis map\n\n"
        "⚙️ *Settings*\n"
        "`/start` — Main menu\n"
        "`/profile` — Your profile & stats\n"
        "`/settings` — Language, city, notifications\n"
        "`/restart` — Reset your settings\n"
        "`/help` — This guide\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 News arrives automatically · All features are 100% free\n"
        "🤖 @Iraqnowbot"
    ),
    "Русский 🇷🇺": (
        "📖 *@Iraqnowbot — Полное руководство*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Бесплатный новостной бот — новости от 50+ источников на вашем языке.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Новости и поиск*\n"
        "`/news` — Последние новости\n"
        "`/trending` — Самые популярные\n"
        "`/summary` — Топ-5 новостей дня\n"
        "`/search` слово — Поиск за 24 часа\n"
        "`/deepsearch` тема — Глубокий AI-анализ\n"
        "`/menu` — Умное меню выбора\n\n"
        "🤖 *AI-анализ*\n"
        "`/ask` вопрос — Задать вопрос ИИ\n"
        "`/verify` заявление — Проверить факты\n"
        "`/analyze` тема — Полный анализ\n"
        "`/compare` тема — Сравнение источников\n"
        "`/timeline` тема — Хронология событий\n"
        "`/predict` тема — Прогноз ИИ\n"
        "`/intel` тема — Аналитический отчёт\n"
        "`/history` тема — Исторический контекст\n"
        "`/connections` тема — Сеть влияния\n"
        "`/sources` — Список источников\n\n"
        "🎙 *Голос и подкаст*\n"
        "`/podcast` — Ежедневный аудиоподкаст (AI+TTS)\n"
        "`/audiobriefing` — Текстовый новостной брифинг\n\n"
        "👁 *Отслеживание*\n"
        "`/follow` тема — Следить за темой\n"
        "`/unfollow` тема — Отписаться от темы\n"
        "`/tip` — Отправить информацию\n\n"
        "💰 *Рынки и активы*\n"
        "`/markets` — Финансовые рынки\n"
        "`/currency` — Валюта, золото, нефть\n"
        "`/chart` BTC — График цены\n"
        "`/addtrack` BTC — Добавить в отслеживание\n"
        "`/removetrack` BTC — Удалить из отслеживания\n"
        "`/mytrack` — Мой список активов\n\n"
        "🌍 *Другие сервисы*\n"
        "`/weather` — Подробный прогноз погоды\n"
        "`/sports` — Спорт и матчи\n"
        "`/parliament` — Парламентские новости\n"
        "`/influence` — Анализ влияния\n"
        "`/econ` — Экономические показатели\n"
        "`/discover` — Найти новые источники\n"
        "`/map` — Карта событий\n\n"
        "⚙️ *Настройки*\n"
        "`/start` — Главное меню\n"
        "`/profile` — Ваш профиль\n"
        "`/settings` — Язык, город, уведомления\n"
        "`/restart` — Сбросить настройки\n"
        "`/help` — Это руководство\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Новости приходят автоматически · Все функции бесплатны\n"
        "🤖 @Iraqnowbot"
    ),
    "فارسی 🇮🇷": (
        "📖 *راهنمای کامل @Iraqnowbot*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 بات خبری هوشمند رایگان — اخبار از ۵۰+ منبع به زبان شما.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *اخبار و جستجو*\n"
        "`/news` — آخرین اخبار\n"
        "`/trending` — پرطرفدارترین\n"
        "`/summary` — خلاصه ۵ خبر برتر روز\n"
        "`/search` کلمه — جستجو در ۲۴ ساعت اخیر\n"
        "`/deepsearch` موضوع — تحلیل عمیق AI\n"
        "`/menu` — منوی انتخاب هوشمند\n\n"
        "🤖 *تحلیل هوش مصنوعی*\n"
        "`/ask` سوال — از هوش مصنوعی بپرسید\n"
        "`/verify` ادعا — تایید واقعیت خبر\n"
        "`/analyze` موضوع — تحلیل کامل\n"
        "`/compare` موضوع — مقایسه منابع\n"
        "`/timeline` موضوع — جدول زمانی رویدادها\n"
        "`/predict` موضوع — پیش‌بینی آینده\n"
        "`/intel` موضوع — گزارش اطلاعاتی\n"
        "`/history` موضوع — زمینه تاریخی\n"
        "`/connections` موضوع — شبکه تاثیر\n"
        "`/sources` — فهرست منابع\n\n"
        "🎙 *صدا و پادکست*\n"
        "`/podcast` — پادکست روزانه صوتی (AI+TTS)\n"
        "`/audiobriefing` — خلاصه خبری متنی\n\n"
        "👁 *دنبال کردن*\n"
        "`/follow` موضوع — دنبال کردن خبر\n"
        "`/unfollow` موضوع — لغو دنبال کردن\n"
        "`/tip` — ارسال اطلاعات\n\n"
        "💰 *بازارها و ردیابی*\n"
        "`/markets` — بازارهای مالی\n"
        "`/currency` — ارز، طلا، نفت\n"
        "`/chart` BTC — نمودار قیمت\n"
        "`/addtrack` BTC — اضافه به ردیابی\n"
        "`/removetrack` BTC — حذف از ردیابی\n"
        "`/mytrack` — فهرست دارایی‌ها\n\n"
        "🌍 *خدمات دیگر*\n"
        "`/weather` — آب‌وهوای شهر\n"
        "`/sports` — ورزش و مسابقات\n"
        "`/parliament` — اخبار پارلمان\n"
        "`/econ` — شاخص‌های اقتصادی\n"
        "`/discover` — منابع خبری جدید\n\n"
        "⚙️ *تنظیمات*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 اخبار خودکار ارسال می‌شود · همه امکانات رایگان\n"
        "🤖 @Iraqnowbot"
    ),
    "हिन्दी 🇮🇳": (
        "📖 *@Iraqnowbot — पूर्ण मार्गदर्शिका*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 100% मुफ़्त न्यूज़ बॉट — 50+ स्रोतों से आपकी भाषा में खबरें।\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *समाचार और खोज*\n"
        "`/news` — ताज़ा समाचार\n"
        "`/trending` — सबसे ज़्यादा चर्चित\n"
        "`/summary` — दिन की टॉप 5 खबरें\n"
        "`/search` शब्द — 24 घंटे में खोज\n"
        "`/deepsearch` विषय — AI गहन विश्लेषण\n"
        "`/menu` — स्मार्ट चयन मेनू\n\n"
        "🤖 *AI विश्लेषण*\n"
        "`/ask` सवाल — AI से पूछें\n"
        "`/verify` दावा — खबर की जांच\n"
        "`/analyze` विषय — पूर्ण विश्लेषण\n"
        "`/compare` विषय — स्रोत तुलना\n"
        "`/timeline` विषय — घटना क्रम\n"
        "`/predict` विषय — भविष्यवाणी\n"
        "`/intel` विषय — खुफिया रिपोर्ट\n"
        "`/history` विषय — ऐतिहासिक संदर्भ\n"
        "`/sources` — समाचार स्रोत सूची\n\n"
        "🎙 *आवाज़ और पॉडकास्ट*\n"
        "`/podcast` — दैनिक ऑडियो पॉडकास्ट\n"
        "`/audiobriefing` — टेक्स्ट समाचार सारांश\n\n"
        "💰 *बाज़ार और ट्रैकिंग*\n"
        "`/markets` `/currency` `/chart` BTC\n"
        "`/addtrack` BTC `/removetrack` BTC `/mytrack`\n\n"
        "🌍 *अन्य सेवाएँ*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover`\n\n"
        "⚙️ *सेटिंग्स*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 समाचार स्वचालित आते हैं · सब कुछ 100% मुफ़्त\n"
        "🤖 @Iraqnowbot"
    ),
    "Português 🇧🇷": (
        "📖 *@Iraqnowbot — Guia Completo*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Bot de notícias inteligente 100% gratuito — 50+ fontes globais no seu idioma.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Notícias e Busca*\n"
        "`/news` — Últimas notícias agora\n"
        "`/trending` — Mais populares\n"
        "`/summary` — Top 5 do dia\n"
        "`/search` palavra — Busca nas últimas 24h\n"
        "`/deepsearch` tema — Pesquisa profunda com AI\n"
        "`/menu` — Menu de seleção inteligente\n\n"
        "🤖 *Análise com AI*\n"
        "`/ask` pergunta — Pergunte à IA\n"
        "`/verify` afirmação — Verificação de fatos\n"
        "`/analyze` tema — Análise completa\n"
        "`/compare` tema — Comparar fontes\n"
        "`/timeline` tema — Linha do tempo\n"
        "`/predict` tema — Previsão futura\n"
        "`/intel` tema — Relatório de inteligência\n"
        "`/history` tema — Contexto histórico\n"
        "`/connections` tema — Rede de influência\n"
        "`/sources` — Lista de fontes\n\n"
        "🎙 *Voz e Podcast*\n"
        "`/podcast` — Podcast diário em áudio (AI+TTS)\n"
        "`/audiobriefing` — Resumo de notícias em texto\n\n"
        "👁 *Acompanhamento*\n"
        "`/follow` tema — Acompanhar uma história\n"
        "`/unfollow` tema — Deixar de acompanhar\n"
        "`/tip` — Enviar uma informação\n\n"
        "💰 *Mercados e Ativos*\n"
        "`/markets` — Mercados financeiros completos\n"
        "`/currency` — Câmbio, ouro e petróleo\n"
        "`/chart` BTC — Gráfico de preço\n"
        "`/addtrack` BTC — Adicionar à lista\n"
        "`/removetrack` BTC — Remover da lista\n"
        "`/mytrack` — Minha lista de ativos\n\n"
        "🌍 *Outros Serviços*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Configurações*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Notícias chegam automaticamente · Tudo 100% gratuito\n"
        "🤖 @Iraqnowbot"
    ),
    "Türkçe 🇹🇷": (
        "📖 *@Iraqnowbot — Tam Rehber*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 %100 ücretsiz akıllı haber botu — 50+ küresel kaynaktan seçtiğiniz dilde haberler.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Haberler ve Arama*\n"
        "`/news` — Son haberler\n"
        "`/trending` — En popüler haberler\n"
        "`/summary` — Günün öne çıkan 5 haberi\n"
        "`/search` kelime — Son 24 saatte ara\n"
        "`/deepsearch` konu — AI derin araştırma\n"
        "`/menu` — Akıllı seçim menüsü\n\n"
        "🤖 *AI Analizi*\n"
        "`/ask` soru — AI'ya sor\n"
        "`/verify` iddia — Haber doğrulama\n"
        "`/analyze` konu — Tam analiz\n"
        "`/compare` konu — Kaynak karşılaştırması\n"
        "`/timeline` konu — Olay zaman çizelgesi\n"
        "`/predict` konu — Gelecek tahmini\n"
        "`/intel` konu — İstihbarat raporu\n"
        "`/history` konu — Tarihsel bağlam\n"
        "`/connections` konu — Etki ağı\n"
        "`/sources` — Kaynak listesi\n\n"
        "🎙 *Ses ve Podcast*\n"
        "`/podcast` — Günlük sesli podcast (AI+TTS)\n"
        "`/audiobriefing` — Metin haber özeti\n\n"
        "👁 *Takip*\n"
        "`/follow` konu — Haber takibi\n"
        "`/unfollow` konu — Takibi bırak\n"
        "`/tip` — Bilgi gönder\n\n"
        "💰 *Piyasalar ve Takip*\n"
        "`/markets` — Finansal piyasalar\n"
        "`/currency` — Döviz, altın, petrol\n"
        "`/chart` BTC — Fiyat grafiği\n"
        "`/addtrack` BTC — İzleme listesine ekle\n"
        "`/removetrack` BTC — Listeden çıkar\n"
        "`/mytrack` — Takip listem\n\n"
        "🌍 *Diğer Servisler*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Ayarlar*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Haberler otomatik gelir · Her şey ücretsiz\n"
        "🤖 @Iraqnowbot"
    ),
    "اردو 🇵🇰": (
        "📖 *@Iraqnowbot — مکمل رہنما*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 100% مفت ذہین خبر بوٹ — 50+ عالمی ذرائع سے آپ کی زبان میں خبریں۔\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *خبریں اور تلاش*\n"
        "`/news` — تازہ ترین خبریں\n"
        "`/trending` — سب سے زیادہ زیر بحث\n"
        "`/summary` — دن کی ٹاپ 5 خبریں\n"
        "`/search` لفظ — 24 گھنٹے میں تلاش\n"
        "`/deepsearch` موضوع — AI گہری تحقیق\n"
        "`/menu` — ذہین انتخاب مینو\n\n"
        "🤖 *AI تجزیہ*\n"
        "`/ask` سوال — AI سے پوچھیں\n"
        "`/verify` دعوٰی — خبر کی تصدیق\n"
        "`/analyze` موضوع — مکمل تجزیہ\n"
        "`/compare` موضوع — ذرائع کا موازنہ\n"
        "`/timeline` موضوع — واقعات کی ترتیب\n"
        "`/predict` موضوع — مستقبل کی پیشگوئی\n"
        "`/intel` موضوع — انٹیلیجنس رپورٹ\n"
        "`/history` موضوع — تاریخی پس منظر\n"
        "`/connections` موضوع — اثر و رسوخ کا جال\n"
        "`/sources` — ذرائع کی فہرست\n\n"
        "🎙 *آواز اور پوڈکاسٹ*\n"
        "`/podcast` — روزانہ آڈیو پوڈکاسٹ (AI+TTS)\n"
        "`/audiobriefing` — متنی خبری خلاصہ\n\n"
        "👁 *پیروی*\n"
        "`/follow` موضوع — کہانی کی پیروی\n"
        "`/unfollow` موضوع — پیروی ختم کریں\n"
        "`/tip` — معلومات بھیجیں\n\n"
        "💰 *منڈیاں اور ٹریکنگ*\n"
        "`/markets` — مالی منڈیاں\n"
        "`/currency` — کرنسی، سونا، تیل\n"
        "`/chart` BTC — قیمت کا گراف\n"
        "`/addtrack` BTC — فہرست میں شامل\n"
        "`/removetrack` BTC — فہرست سے ہٹائیں\n"
        "`/mytrack` — میری فہرست\n\n"
        "🌍 *دیگر خدمات*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *ترتیبات*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 خبریں خودکار آتی ہیں · سب کچھ مفت ہے\n"
        "🤖 @Iraqnowbot"
    ),
    "Deutsch 🇩🇪": (
        "📖 *@Iraqnowbot — Vollständige Anleitung*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 100% kostenloser intelligenter Nachrichtenbot — 50+ globale Quellen in Ihrer Sprache.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Nachrichten & Suche*\n"
        "`/news` — Aktuelle Nachrichten\n"
        "`/trending` — Meistbesprochene Themen\n"
        "`/summary` — Top 5 des Tages\n"
        "`/search` Begriff — Suche der letzten 24 Std.\n"
        "`/deepsearch` Thema — KI-Tiefenanalyse\n"
        "`/menu` — Intelligentes Auswahlmenü\n\n"
        "🤖 *KI-Analyse*\n"
        "`/ask` Frage — KI befragen\n"
        "`/verify` Aussage — Faktencheck\n"
        "`/analyze` Thema — Vollständige Analyse\n"
        "`/compare` Thema — Quellen vergleichen\n"
        "`/timeline` Thema — Chronologie\n"
        "`/predict` Thema — KI-Prognose\n"
        "`/intel` Thema — Analysebericht\n"
        "`/history` Thema — Historischer Kontext\n"
        "`/connections` Thema — Einfluss-Netzwerk\n"
        "`/sources` — Quellenliste\n\n"
        "🎙 *Sprache & Podcast*\n"
        "`/podcast` — Täglicher Audio-Podcast (KI+TTS)\n"
        "`/audiobriefing` — Text-Nachrichtenbriefing\n\n"
        "👁 *Nachverfolgung*\n"
        "`/follow` Thema — Story verfolgen\n"
        "`/unfollow` Thema — Nicht mehr verfolgen\n"
        "`/tip` — Hinweis einsenden\n\n"
        "💰 *Märkte & Assets*\n"
        "`/markets` — Finanzmärkte\n"
        "`/currency` — Devisen, Gold, Öl\n"
        "`/chart` BTC — Preischart\n"
        "`/addtrack` BTC — Zur Liste hinzufügen\n"
        "`/removetrack` BTC — Von Liste entfernen\n"
        "`/mytrack` — Meine Watchlist\n\n"
        "🌍 *Weitere Dienste*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Einstellungen*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Nachrichten kommen automatisch · Alles kostenlos\n"
        "🤖 @Iraqnowbot"
    ),
    "Українська 🇺🇦": (
        "📖 *@Iraqnowbot — Повний посібник*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Безкоштовний новинний бот — 50+ джерел вашою мовою.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Новини та пошук*\n"
        "`/news` — Останні новини\n"
        "`/trending` — Найпопулярніші\n"
        "`/summary` — Топ-5 новин дня\n"
        "`/search` слово — Пошук за 24 год.\n"
        "`/deepsearch` тема — ШІ-аналіз\n"
        "`/menu` — Розумне меню\n\n"
        "🤖 *ШІ-аналіз*\n"
        "`/ask` питання — Запитати ШІ\n"
        "`/verify` твердження — Перевірка фактів\n"
        "`/analyze` тема — Повний аналіз\n"
        "`/compare` тема — Порівняти джерела\n"
        "`/timeline` тема — Хронологія подій\n"
        "`/predict` тема — Прогноз ШІ\n"
        "`/intel` тема — Аналітичний звіт\n"
        "`/history` тема — Історичний контекст\n"
        "`/connections` тема — Мережа впливу\n"
        "`/sources` — Список джерел\n\n"
        "🎙 *Голос і подкаст*\n"
        "`/podcast` — Щоденний аудіоподкаст (ШІ+TTS)\n"
        "`/audiobriefing` — Текстовий новинний брифінг\n\n"
        "👁 *Відстеження*\n"
        "`/follow` тема — Стежити за темою\n"
        "`/unfollow` тема — Відписатись\n"
        "`/tip` — Надіслати інформацію\n\n"
        "💰 *Ринки та активи*\n"
        "`/markets` — Фінансові ринки\n"
        "`/currency` — Валюта, золото, нафта\n"
        "`/chart` BTC — Графік ціни\n"
        "`/addtrack` BTC — Додати до списку\n"
        "`/removetrack` BTC — Видалити зі списку\n"
        "`/mytrack` — Мій список активів\n\n"
        "🌍 *Інші сервіси*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Налаштування*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Новини надходять автоматично · Усе безкоштовно\n"
        "🤖 @Iraqnowbot"
    ),
    "Italiano 🇮🇹": (
        "📖 *@Iraqnowbot — Guida Completa*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Bot di notizie 100% gratuito — 50+ fonti globali nella tua lingua.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Notizie e Ricerca*\n"
        "`/news` — Ultime notizie\n"
        "`/trending` — Più discusse\n"
        "`/summary` — Top 5 del giorno\n"
        "`/search` parola — Cerca nelle ultime 24 ore\n"
        "`/deepsearch` argomento — Ricerca profonda AI\n"
        "`/menu` — Menu di selezione intelligente\n\n"
        "🤖 *Analisi AI*\n"
        "`/ask` domanda — Chiedi all'AI\n"
        "`/verify` affermazione — Verifica dei fatti\n"
        "`/analyze` argomento — Analisi completa\n"
        "`/compare` argomento — Confronta fonti\n"
        "`/timeline` argomento — Linea del tempo\n"
        "`/predict` argomento — Previsione AI\n"
        "`/intel` argomento — Rapporto di intelligence\n"
        "`/history` argomento — Contesto storico\n"
        "`/connections` argomento — Rete di influenza\n"
        "`/sources` — Elenco delle fonti\n\n"
        "🎙 *Voce e Podcast*\n"
        "`/podcast` — Podcast audio giornaliero (AI+TTS)\n"
        "`/audiobriefing` — Briefing notizie testuale\n\n"
        "👁 *Monitoraggio*\n"
        "`/follow` argomento — Seguire una storia\n"
        "`/unfollow` argomento — Smettere di seguire\n"
        "`/tip` — Inviare una segnalazione\n\n"
        "💰 *Mercati e Asset*\n"
        "`/markets` — Mercati finanziari\n"
        "`/currency` — Valute, oro, petrolio\n"
        "`/chart` BTC — Grafico prezzi\n"
        "`/addtrack` BTC — Aggiungi alla lista\n"
        "`/removetrack` BTC — Rimuovi dalla lista\n"
        "`/mytrack` — La mia watchlist\n\n"
        "🌍 *Altri Servizi*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Impostazioni*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Le notizie arrivano automaticamente · Tutto gratuito\n"
        "🤖 @Iraqnowbot"
    ),
    "Español 🇲🇽": (
        "📖 *@Iraqnowbot — Guía Completa*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Bot de noticias 100% gratuito — 50+ fuentes globales en tu idioma.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Noticias y Búsqueda*\n"
        "`/news` — Últimas noticias\n"
        "`/trending` — Más comentadas\n"
        "`/summary` — Top 5 del día\n"
        "`/search` palabra — Buscar en últimas 24h\n"
        "`/deepsearch` tema — Investigación profunda IA\n"
        "`/menu` — Menú de selección inteligente\n\n"
        "🤖 *Análisis con IA*\n"
        "`/ask` pregunta — Preguntar a la IA\n"
        "`/verify` afirmación — Verificar hechos\n"
        "`/analyze` tema — Análisis completo\n"
        "`/compare` tema — Comparar fuentes\n"
        "`/timeline` tema — Línea de tiempo\n"
        "`/predict` tema — Predicción futura\n"
        "`/intel` tema — Informe de inteligencia\n"
        "`/history` tema — Contexto histórico\n"
        "`/connections` tema — Red de influencia\n"
        "`/sources` — Lista de fuentes\n\n"
        "🎙 *Voz y Podcast*\n"
        "`/podcast` — Podcast diario en audio (IA+TTS)\n"
        "`/audiobriefing` — Resumen de noticias en texto\n\n"
        "👁 *Seguimiento*\n"
        "`/follow` tema — Seguir una historia\n"
        "`/unfollow` tema — Dejar de seguir\n"
        "`/tip` — Enviar información\n\n"
        "💰 *Mercados y Activos*\n"
        "`/markets` — Mercados financieros\n"
        "`/currency` — Divisas, oro, petróleo\n"
        "`/chart` BTC — Gráfico de precios\n"
        "`/addtrack` BTC — Agregar a lista\n"
        "`/removetrack` BTC — Quitar de lista\n"
        "`/mytrack` — Mi lista de seguimiento\n\n"
        "🌍 *Otros Servicios*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Configuración*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Las noticias llegan automáticamente · Todo es gratuito\n"
        "🤖 @Iraqnowbot"
    ),
    "Français 🇫🇷": (
        "📖 *@Iraqnowbot — Guide Complet*\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🤖 Bot d'actualités 100% gratuit — 50+ sources mondiales dans votre langue.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📰 *Actualités et Recherche*\n"
        "`/news` — Dernières actualités\n"
        "`/trending` — Les plus commentées\n"
        "`/summary` — Top 5 du jour\n"
        "`/search` mot — Recherche sur 24h\n"
        "`/deepsearch` sujet — Recherche approfondie IA\n"
        "`/menu` — Menu de sélection intelligent\n\n"
        "🤖 *Analyse IA*\n"
        "`/ask` question — Interroger l'IA\n"
        "`/verify` affirmation — Vérification des faits\n"
        "`/analyze` sujet — Analyse complète\n"
        "`/compare` sujet — Comparer les sources\n"
        "`/timeline` sujet — Chronologie des événements\n"
        "`/predict` sujet — Prédiction IA\n"
        "`/intel` sujet — Rapport de renseignement\n"
        "`/history` sujet — Contexte historique\n"
        "`/connections` sujet — Réseau d'influence\n"
        "`/sources` — Liste des sources\n\n"
        "🎙 *Voix et Podcast*\n"
        "`/podcast` — Podcast audio quotidien (IA+TTS)\n"
        "`/audiobriefing` — Briefing d'actualités en texte\n\n"
        "👁 *Suivi*\n"
        "`/follow` sujet — Suivre une histoire\n"
        "`/unfollow` sujet — Arrêter de suivre\n"
        "`/tip` — Envoyer une information\n\n"
        "💰 *Marchés et Actifs*\n"
        "`/markets` — Marchés financiers\n"
        "`/currency` — Devises, or, pétrole\n"
        "`/chart` BTC — Graphique de prix\n"
        "`/addtrack` BTC — Ajouter à la liste\n"
        "`/removetrack` BTC — Retirer de la liste\n"
        "`/mytrack` — Ma liste de suivi\n\n"
        "🌍 *Autres Services*\n"
        "`/weather` `/sports` `/parliament` `/econ` `/discover` `/map`\n\n"
        "⚙️ *Paramètres*\n"
        "`/start` `/profile` `/settings` `/restart` `/help`\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 Les actualités arrivent automatiquement · Tout est gratuit\n"
        "🤖 @Iraqnowbot"
    ),
}

HELP_CMD_LABELS = {
    "العربية 🇮🇶": {
        "sec_start":   "⚡ البدء والإعدادات",
        "sec_trade":   "💹 التداول والمتابعة",
        "sec_news":    "📢 الأخبار والطقس",
        "start":  "▶️ /start", "help":  "❓ /help", "settings": "⚙️ /settings",
        "mytrack":"📋 /mytrack","addtrack":"➕ /addtrack","removetrack":"➖ /removetrack",
        "markets":"💹 /markets","alerts":"🔔 /alerts","chart":"📊 /chart",
        "news":"📰 /news","trending":"🔥 /trending","summary":"📝 /summary","weather":"🌤 /weather",
    },
    "English 🇬🇧": {
        "sec_start":   "⚡ Start & Settings",
        "sec_trade":   "💹 Trading & Tracking",
        "sec_news":    "📢 News & Weather",
        "start":  "▶️ /start", "help":  "❓ /help", "settings": "⚙️ /settings",
        "mytrack":"📋 /mytrack","addtrack":"➕ /addtrack","removetrack":"➖ /removetrack",
        "markets":"💹 /markets","alerts":"🔔 /alerts","chart":"📊 /chart",
        "news":"📰 /news","trending":"🔥 /trending","summary":"📝 /summary","weather":"🌤 /weather",
    },
    "Русский 🇷🇺": {
        "sec_start":   "⚡ Начало и настройки",
        "sec_trade":   "💹 Торговля и отслеживание",
        "sec_news":    "📢 Новости и погода",
        "start":"▶️ /start","help":"❓ /help","settings":"⚙️ /settings",
        "mytrack":"📋 /mytrack","addtrack":"➕ /addtrack","removetrack":"➖ /removetrack",
        "markets":"💹 /markets","alerts":"🔔 /alerts","chart":"📊 /chart",
        "news":"📰 /news","trending":"🔥 /trending","summary":"📝 /summary","weather":"🌤 /weather",
    },
    "فارسی 🇮🇷": {
        "sec_start":"⚡ شروع و تنظیمات","sec_trade":"💹 معاملات و پیگیری","sec_news":"📢 اخبار و آبوهوا",
        "start":"▶️ /start","help":"❓ /help","settings":"⚙️ /settings",
        "mytrack":"📋 /mytrack","addtrack":"➕ /addtrack","removetrack":"➖ /removetrack",
        "markets":"💹 /markets","alerts":"🔔 /alerts","chart":"📊 /chart",
        "news":"📰 /news","trending":"🔥 /trending","summary":"📝 /summary","weather":"🌤 /weather",
    },
    "Français 🇫🇷": {
        "sec_start":"⚡ Démarrage & Paramètres","sec_trade":"💹 Trading & Suivi","sec_news":"📢 Actualités & Météo",
        "start":"▶️ /start","help":"❓ /help","settings":"⚙️ /settings",
        "mytrack":"📋 /mytrack","addtrack":"➕ /addtrack","removetrack":"➖ /removetrack",
        "markets":"💹 /markets","alerts":"🔔 /alerts","chart":"📊 /chart",
        "news":"📰 /news","trending":"🔥 /trending","summary":"📝 /summary","weather":"🌤 /weather",
    },
}

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_") or c.data.startswith("broadcast_") or c.data.startswith("rss_") or c.data.startswith("quick_") or c.data.startswith("ch_") or c.data.startswith("interval_") or c.data.startswith("bl_") or c.data.startswith("backup_") or c.data == "noop")
def admin_callbacks(call):
    global users, stats, banned, inbox_messages, RSS, bot_paused, _pause_since, broadcast_paused
    if not is_admin(call.from_user.id):
        return
    uid = call.from_user.id
    data = call.data
    bot.answer_callback_query(call.id)

    # ======== الإحصائيات ========
    if data == "admin_stats":
        today = str(datetime.date.today())
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        weekly = sum(v for k, v in stats["daily_users"].items() if datetime.date.fromisoformat(k) >= week_ago)
        today_count = stats["daily_users"].get(today, 0)
        yesterday_count = stats["daily_users"].get(yesterday, 0)
        total = stats.get("total_users", len(users))
        active = sum(1 for u in users.values() if "province" in u)
        top_countries = sorted(stats["countries_count"].items(), key=lambda x: x[1], reverse=True)[:3]
        top_langs = sorted(stats["languages_count"].items(), key=lambda x: x[1], reverse=True)[:3]
        top_buttons = sorted(stats["button_presses"].items(), key=lambda x: x[1], reverse=True)[:3]
        msg = "📊 *الإحصائيات التفصيلية*\n\n"
        msg += f"👥 إجمالي المستخدمين: `{total}`\n"
        msg += f"✅ مستخدمون نشطون: `{active}`\n"
        msg += f"🆕 اليوم: `{today_count}`\n"
        msg += f"📅 أمس: `{yesterday_count}`\n"
        msg += f"📆 هذا الأسبوع: `{weekly}`\n"
        msg += f"⭐ مميزون: `{len(stats.get('premium_users', []))}`\n"
        msg += f"🚫 محظورون: `{len(banned)}`\n\n"
        if top_countries:
            msg += "🌍 *أكثر الدول:*\n"
            for c, n in top_countries:
                msg += f"  {c}: `{n}`\n"
        if top_langs:
            msg += "\n🗣 *أكثر اللغات:*\n"
            for l, n in top_langs:
                msg += f"  {l}: `{n}`\n"
        if top_buttons:
            msg += "\n🔘 *أكثر الأزرار استخداماً:*\n"
            for b, n in top_buttons:
                msg += f"  {b}: `{n}`\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
        # --- إحصائيات البث ---
        with _broadcast_stats_lock:
            bs = dict(_broadcast_stats)
            err_count = len(_broadcast_errors)
        interval_now = broadcast_settings.get("interval_minutes", 1)
        _lbt = bs.get("last_broadcast_time")
        if _lbt and isinstance(_lbt, (int, float)):
            try:
                _lbt_dt = datetime.datetime.fromtimestamp(float(_lbt)) + _SA_TZ_OFFSET
                last_time = _lbt_dt.strftime("%H:%M:%S")
            except Exception:
                last_time = str(_lbt)
        else:
            last_time = _lbt or "لم يحدث بعد"
        bcast_msg = (
            "📡 *إحصائيات البث:*\n\n"
            f"⏱ التوقيت: كل `{interval_now}` دقيقة\n"
            f"🕒 آخر بث: `{last_time}`\n"
            f"📰 أخبار اليوم: `{bs.get('today_news_sent', 0)}`\n"
            f"👥 مستخدمون وصلتهم اليوم: `{bs.get('today_users_reached', 0)}`\n"
            f"📊 إجمالي الأخبار المُرسلة: `{bs.get('total_news_all_time', 0)}`\n"
            f"⚠️ أخطاء مسجّلة: `{err_count}`"
        )
        markup_bs = types.InlineKeyboardMarkup()
        if err_count > 0:
            markup_bs.add(types.InlineKeyboardButton("📋 عرض سجل الأخطاء", callback_data="admin_broadcast_errors"))
        bot.send_message(uid, bcast_msg, parse_mode="Markdown", reply_markup=markup_bs if err_count > 0 else None)

    # ======== إدارة المستخدمين ========
    elif data == "admin_users":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 قائمة جميع المستخدمين", callback_data="admin_users_list_0"),
            types.InlineKeyboardButton("🔍 معلومات مستخدم", callback_data="admin_user_info"),
            types.InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban"),
            types.InlineKeyboardButton("✅ رفع حظر", callback_data="admin_unban"),
            types.InlineKeyboardButton("📋 قائمة المحظورين", callback_data="admin_banned_list"),
            types.InlineKeyboardButton("⭐ ترقية لمميز", callback_data="admin_premium"),
            types.InlineKeyboardButton("❌ إلغاء اشتراك مميز", callback_data="admin_unpremium"),
        )
        bot.send_message(uid, "👥 *إدارة المستخدمين:*\n\nإجمالي المستخدمين: `{}`".format(len(users)), parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("admin_users_list_"):
        page = int(data.split("_")[-1])
        per_page = 10
        all_uids = list(users.keys())
        total = len(all_uids)
        total_pages = max(1, (total + per_page - 1) // per_page)
        start = page * per_page
        end = start + per_page
        page_uids = all_uids[start:end]
        premium_list = stats.get("premium_users", [])
        lines = [f"👥 *قائمة المستخدمين* — صفحة {page+1}/{total_pages}\n━━━━━━━━━━━━━━"]
        for i, u_id in enumerate(page_uids, start + 1):
            u = users[u_id]
            name = u.get("name", "—")[:20]
            country = u.get("country", "—")[:15]
            lang = u.get("lang", "")[:4]
            is_prem = "⭐" if int(u_id) in premium_list else ""
            is_ban = "🚫" if int(u_id) in banned else ""
            lines.append(f"{i}. {is_prem}{is_ban} *{name}*\n    🆔 `{u_id}` | 🌍 {country} | 🗣 {lang}")
        msg = "\n".join(lines)
        nav_markup = types.InlineKeyboardMarkup(row_width=3)
        nav_btns = []
        if page > 0:
            nav_btns.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"admin_users_list_{page-1}"))
        nav_btns.append(types.InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
        if end < total:
            nav_btns.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"admin_users_list_{page+1}"))
        if nav_btns:
            nav_markup.add(*nav_btns)
        nav_markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_users"))
        try:
            bot.edit_message_text(msg, uid, call.message.message_id, parse_mode="Markdown", reply_markup=nav_markup)
        except Exception:
            bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=nav_markup)

    elif data == "admin_user_info":
        msg = bot.send_message(uid, "أرسل ID المستخدم:")
        bot.register_next_step_handler(msg, get_user_info)

    elif data == "admin_ban":
        msg = bot.send_message(uid, "أرسل ID المستخدم لحظره:")
        bot.register_next_step_handler(msg, ban_user_step)

    elif data == "admin_unban":
        msg = bot.send_message(uid, "أرسل ID المستخدم لرفع حظره:")
        bot.register_next_step_handler(msg, unban_user_step)

    elif data == "admin_banned_list":
        if not banned:
            bot.send_message(uid, "✅ لا يوجد مستخدمون محظورون.")
        else:
            bot.send_message(uid, "🚫 *المحظورون:*\n" + "\n".join(f"`{b}`" for b in banned), parse_mode="Markdown")

    elif data == "admin_premium":
        msg = bot.send_message(uid, "أرسل ID المستخدم لترقيته للمميز:")
        bot.register_next_step_handler(msg, promote_premium_step)

    elif data == "admin_unpremium":
        msg = bot.send_message(uid, "أرسل ID المستخدم لإلغاء اشتراكه المميز:")
        bot.register_next_step_handler(msg, demote_premium_step)

    # ======== الإرسال الجماعي ========
    elif data == "admin_broadcast":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📢 للكل", callback_data="broadcast_all"),
            types.InlineKeyboardButton("🌍 حسب الدولة", callback_data="broadcast_country"),
            types.InlineKeyboardButton("🗣 حسب اللغة", callback_data="broadcast_lang"),
            types.InlineKeyboardButton("⭐ للمميزين فقط", callback_data="broadcast_premium"),
        )
        bot.send_message(uid, "📢 *اختر نوع الإرسال:*", parse_mode="Markdown", reply_markup=markup)

    elif data == "broadcast_all":
        msg = bot.send_message(uid, "أرسل الرسالة لإرسالها لجميع المستخدمين:")
        bot.register_next_step_handler(msg, broadcast_all_step)

    elif data == "broadcast_country":
        msg = bot.send_message(uid, "أرسل اسم الدولة في السطر الأول، والرسالة في السطر الثاني:")
        bot.register_next_step_handler(msg, broadcast_country_step)

    elif data == "broadcast_lang":
        msg = bot.send_message(uid, "أرسل اللغة في السطر الأول، والرسالة في السطر الثاني:")
        bot.register_next_step_handler(msg, broadcast_lang_step)

    elif data == "broadcast_premium":
        msg = bot.send_message(uid, "أرسل الرسالة لإرسالها للمستخدمين المميزين:")
        bot.register_next_step_handler(msg, broadcast_premium_step)

    # ======== إيقاف/تشغيل البوت ========
    elif data == "admin_pause":
        if bot_paused:
            bot_paused = False
            _pause_since = None
            bot.send_message(uid, "✅ البوت يعمل الآن.")
        else:
            msg = bot.send_message(uid, "أرسل رسالة الإيقاف (أو أرسل 'افتراضي'):")
            bot.register_next_step_handler(msg, pause_bot_step)

    # ======== إدارة RSS ========
    elif data == "admin_rss":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة مصدر RSS", callback_data="rss_add"),
            types.InlineKeyboardButton("📥 إضافة متعددة", callback_data="rss_bulk_add"),
            types.InlineKeyboardButton("➖ حذف مصدر", callback_data="rss_remove"),
            types.InlineKeyboardButton("📋 عرض المصادر", callback_data="rss_list"),
            types.InlineKeyboardButton("🔍 اكتشاف RSS تلقائي", callback_data="rss_discover_help"),
            types.InlineKeyboardButton("📺 إضافة قناة تيليغرام", callback_data="rss_addchannel_help"),
            types.InlineKeyboardButton("🗑 حذف قناة مخصصة", callback_data="rss_removechannel_help"),
            types.InlineKeyboardButton("📋 قنوات مُضافة يدوياً", callback_data="rss_custom_channels_list"),
            types.InlineKeyboardButton("🔄 استعادة المصادر الافتراضية", callback_data="rss_reset_defaults"),
        )
        total_rss = sum(len(v) for v in RSS.values())
        total_tg = sum(len(v) for v in TELEGRAM_NEWS_CHANNELS.values())
        custom_tg = sum(len(v) for v in _custom_tg_channels.values())
        bot.send_message(uid,
            f"📡 *إدارة مصادر الأخبار*\n\n"
            f"📰 مصادر RSS: *{total_rss}*\n"
            f"📺 قنوات تيليغرام: *{total_tg}* (منها *{custom_tg}* مخصصة)\n\n"
            f"💡 استخدم الأوامر السريعة:\n"
            f"• `/discover <url>` — اكتشاف RSS من موقع\n"
            f"• `/addchannel <handle>` — إضافة قناة تيليغرام\n"
            f"• `/listsources` — القنوات المضافة يدوياً",
            parse_mode="Markdown", reply_markup=markup
        )

    elif data == "rss_bulk_add":
        msg = bot.send_message(uid,
            "📥 *إضافة مصادر متعددة دفعة واحدة*\n\n"
            "أرسل رسالة بالشكل التالي:\n\n"
            "`اللغة`\n"
            "`https://مصدر1.com/rss`\n"
            "`https://مصدر2.com/feed`\n"
            "`https://مصدر3.com/rss.xml`\n"
            "...\n\n"
            "مثال:\n"
            "`العربية 🇮🇶`\n"
            "`https://site1.com/rss`\n"
            "`https://site2.com/feed`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, rss_bulk_add_step)

    elif data == "rss_discover_help":
        bot.send_message(uid,
            "🔍 *اكتشاف RSS تلقائي من موقع ويب*\n\n"
            "*كيفية الاستخدام:*\n"
            "`/discover <رابط الموقع> [اللغة]`\n\n"
            "*أمثلة:*\n"
            "`/discover https://www.almayadeen.net العربية 🇮🇶`\n"
            "`/discover https://www.bbc.com/arabic`\n"
            "`/discover https://www.reuters.com English 🇬🇧`\n\n"
            "⚙️ يجرب البوت تلقائياً أكثر من 9 أنماط شائعة للـ RSS،\n"
            "ويبحث أيضاً في كود الصفحة عن روابط RSS مخفية.",
            parse_mode="Markdown"
        )

    elif data == "rss_addchannel_help":
        langs_list = "\n".join(f"• `{l}`" for l in list(TELEGRAM_NEWS_CHANNELS.keys())[:8])
        bot.send_message(uid,
            "📺 *إضافة قناة تيليغرام كمصدر أخبار*\n\n"
            "*كيفية الاستخدام:*\n"
            "`/addchannel <handle> [اللغة] [الاسم]`\n\n"
            "*أمثلة:*\n"
            "`/addchannel AlJazeeraArabic العربية 🇮🇶 الجزيرة`\n"
            "`/addchannel BBCBreaking English 🇬🇧 BBC Breaking`\n\n"
            f"*اللغات المتاحة:*\n{langs_list}\n...\n\n"
            "💡 القناة ستساهم بالأخبار في دورة البث القادمة.",
            parse_mode="Markdown"
        )

    elif data == "rss_removechannel_help":
        bot.send_message(uid,
            "🗑 *حذف قناة تيليغرام من مصادر الأخبار*\n\n"
            "*كيفية الاستخدام:*\n"
            "`/removechannel <handle>`\n\n"
            "*مثال:*\n"
            "`/removechannel OldChannelHandle`\n\n"
            "⚠️ يعمل فقط على القنوات المُضافة يدوياً.\n"
            "القنوات الافتراضية تحتاج تعديل الكود لحذفها.",
            parse_mode="Markdown"
        )

    elif data == "rss_custom_channels_list":
        if not _custom_tg_channels or all(len(v) == 0 for v in _custom_tg_channels.values()):
            bot.send_message(uid,
                "📭 لم تُضف أي قنوات مخصصة بعد.\n"
                "استخدم `/addchannel` لإضافة قنوات جديدة.",
                parse_mode="Markdown"
            )
        else:
            msg = "📺 *قنوات التيليغرام المضافة يدوياً:*\n\n"
            for lang, channels in _custom_tg_channels.items():
                if channels:
                    msg += f"*{lang}:*\n"
                    for ch in channels:
                        msg += f"  • `@{ch['handle']}` — {ch['name']}\n"
                    msg += "\n"
            msg += "لحذف قناة: `/removechannel <handle>`"
            bot.send_message(uid, msg, parse_mode="Markdown")

    elif data == "rss_reset_defaults":
        RSS = {lang: list(feeds) for lang, feeds in DEFAULT_RSS.items()}
        save_rss()
        total = sum(len(v) for v in RSS.values())
        arabic_count = len(RSS.get("العربية 🇮🇶", []))
        bot.answer_callback_query(call.id, "✅ تم استعادة المصادر")
        bot.send_message(uid,
            f"✅ *تم استعادة المصادر الافتراضية*\n\n"
            f"• إجمالي المصادر: *{total}*\n"
            f"• مصادر العربية: *{arabic_count}* مصدر عامل مؤكد\n\n"
            f"⚠️ ملاحظة: المصادر القديمة المحذوفة كانت معطلة (404/403).",
            parse_mode="Markdown"
        )

    elif data == "rss_add":
        msg = bot.send_message(uid, "أرسل اللغة في السطر الأول، والرابط في السطر الثاني:")
        bot.register_next_step_handler(msg, rss_add_step)

    elif data == "rss_remove":
        msg = bot.send_message(uid, "أرسل اللغة في السطر الأول، ورقم المصدر في السطر الثاني:")
        bot.register_next_step_handler(msg, rss_remove_step)

    elif data == "rss_list":
        msg = "📡 *مصادر RSS الحالية:*\n\n"
        for lang, feeds in RSS.items():
            msg += f"*{lang}*\n"
            for i, f in enumerate(feeds):
                msg += f"  `{i+1}`. {f}\n"
            msg += "\n"
        bot.send_message(uid, msg, parse_mode="Markdown")

    # ======== المالية ========
    elif data == "admin_finance":
        premium_count = len(stats.get("premium_users", []))
        revenue = stats.get("revenue", 0.0)
        msg = (
            f"💰 *المالية*\n\n"
            f"⭐ المميزون: `{premium_count}`\n"
            f"💵 الدخل الكلي: `${revenue:.2f}`\n"
        )
        bot.send_message(uid, msg, parse_mode="Markdown")

    # ======== تغيير رسالة الترحيب ========
    elif data == "admin_welcome":
        msg = bot.send_message(uid, "أرسل رسالة الترحيب الجديدة (أو 'افتراضي' للرجوع للأصلية):")
        bot.register_next_step_handler(msg, change_welcome_step)

    # ======== إدارة الأدمن ========
    elif data == "admin_manage_admins":
        # فقط الأدمن الرئيسي يستطيع إدارة الأدمن الآخرين
        if int(uid) != ADMIN_ID:
            bot.send_message(uid, "⛔ هذه الصلاحية للأدمن الرئيسي فقط.")
            return
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة أدمن", callback_data="admin_addadmin"),
            types.InlineKeyboardButton("➖ إزالة أدمن", callback_data="admin_removeadmin"),
            types.InlineKeyboardButton("📋 قائمة الأدمن", callback_data="admin_listadmins"),
        )
        bot.send_message(uid, "👑 *إدارة الأدمن:*", parse_mode="Markdown", reply_markup=markup)

    elif data == "admin_addadmin":
        if int(uid) != ADMIN_ID:
            bot.send_message(uid, "⛔ هذه الصلاحية للأدمن الرئيسي فقط.")
            return
        msg = bot.send_message(uid, "أرسل ID المستخدم الذي تريد تعيينه أدمن:")
        bot.register_next_step_handler(msg, add_admin_step)

    elif data == "admin_removeadmin":
        if int(uid) != ADMIN_ID:
            bot.send_message(uid, "⛔ هذه الصلاحية للأدمن الرئيسي فقط.")
            return
        msg = bot.send_message(uid, "أرسل ID الأدمن الذي تريد إزالته:")
        bot.register_next_step_handler(msg, remove_admin_step)

    elif data == "admin_listadmins":
        if int(uid) != ADMIN_ID:
            bot.send_message(uid, "⛔ هذه الصلاحية للأدمن الرئيسي فقط.")
            return
        if not extra_admins:
            bot.send_message(uid, f"👑 *قائمة الأدمن:*\n\n🔑 الأدمن الرئيسي: `{ADMIN_ID}`\n\nلا يوجد أدمن إضافيون.", parse_mode="Markdown")
        else:
            admins_list = "\n".join(f"  `{a}`" for a in extra_admins)
            bot.send_message(uid,
                f"👑 *قائمة الأدمن:*\n\n"
                f"🔑 الأدمن الرئيسي: `{ADMIN_ID}`\n\n"
                f"👥 الأدمن الإضافيون:\n{admins_list}",
                parse_mode="Markdown"
            )

    elif data == "admin_features":
        # ← تفويض للـ handler المتخصص
        _build_features_panel(uid)

    elif data == "noop":
        bot.answer_callback_query(call.id)

    elif data.startswith("admin_view_"):
        target_id = data.split("admin_view_")[-1]
        user = users.get(target_id)
        if not user:
            bot.answer_callback_query(call.id, "❌ المستخدم غير موجود")
            return
        is_banned_user = int(target_id) in banned
        is_premium_user = int(target_id) in stats.get("premium_users", [])
        referrals = user.get("referrals", [])
        referred_by = user.get("referred_by", None)
        join_date = user.get("join_date", "غير معروف")
        interests = user.get("interests", [])
        notif = "✅" if user.get("notifications", True) else "❌"
        track_data = tracked_assets.get(target_id, {})
        tracked = track_data.get("assets", [])
        msg = (
            f"👤 *ملف المستخدم*\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{target_id}`\n"
            f"👤 الاسم: *{user.get('name', '—')}*\n"
            f"🗣 اللغة: {user.get('lang', '-')}\n"
            f"🌍 الدولة: {user.get('country', '-')}\n"
            f"📍 المحافظة: {user.get('province', '-')}\n"
            f"📅 الانضمام: `{join_date}`\n"
            f"━━━━━━━━━━━━━━\n"
            f"🚫 محظور: {'نعم' if is_banned_user else 'لا'} | "
            f"⭐ مميز: {'نعم' if is_premium_user else 'لا'}\n"
            f"🔔 إشعارات: {notif} | 🎁 دعوات: `{len(referrals)}`\n"
            f"👈 جاء عبر: `{referred_by if referred_by else 'مباشر'}`\n"
            f"📌 يتتبع: `{', '.join(tracked) if tracked else '—'}`\n"
            f"📰 اهتمامات: `{', '.join(interests) if interests else '—'}`\n"
        )
        view_markup = types.InlineKeyboardMarkup(row_width=2)
        view_markup.add(
            types.InlineKeyboardButton("🚫 حظر", callback_data=f"quick_ban_{target_id}"),
            types.InlineKeyboardButton("⭐ ترقية مميز", callback_data=f"quick_premium_{target_id}"),
            types.InlineKeyboardButton("📢 راسله", url=f"tg://user?id={target_id}"),
        )
        bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=view_markup)

    elif data.startswith("quick_ban_"):
        target_id_str = data.split("quick_ban_")[-1]
        try:
            target_id_int = int(target_id_str)
            if target_id_int not in banned:
                banned.append(target_id_int)
                save_json(BANNED_FILE, banned)
                bot.answer_callback_query(call.id, f"✅ تم حظر المستخدم {target_id_str}")
                bot.send_message(uid, f"🚫 تم حظر المستخدم `{target_id_str}` بنجاح.", parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, "⚠️ هذا المستخدم محظور مسبقاً")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطأ: {e}")

    elif data.startswith("quick_premium_"):
        target_id_str = data.split("quick_premium_")[-1]
        try:
            target_id_int = int(target_id_str)
            premium_list = stats.get("premium_users", [])
            if target_id_int not in premium_list:
                premium_list.append(target_id_int)
                stats["premium_users"] = premium_list
                save_json(STATS_FILE, stats)
                bot.answer_callback_query(call.id, "✅ تمت الترقية لـ ⭐ مميز")
                bot.send_message(uid, f"⭐ تم ترقية المستخدم `{target_id_str}` للمميز.", parse_mode="Markdown")
                try:
                    bot.send_message(target_id_int, "🎉 تهانينا! تمت ترقيتك للاشتراك المميز ⭐\nاستمتع بجميع الميزات الحصرية!")
                except Exception as _exc:
                    _log_exc(_exc)
            else:
                bot.answer_callback_query(call.id, "⚠️ هذا المستخدم مميز مسبقاً")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ خطأ: {e}")

    elif data == "admin_channels":
        handle_admin_channels(uid, call)

    elif data == "ch_add":
        bot.send_message(uid,
            "➕ *إضافة قناة أو مجموعة*\n\n"
            "أرسل المعلومات في رسالة واحدة بهذا الشكل:\n\n"
            "`-1001234567890`\n"
            "`العربية 🇮🇶`\n\n"
            "📌 السطر الأول: ID القناة/المجموعة\n"
            "📌 السطر الثاني: لغة الأخبار التي ستُرسل لها\n\n"
            "⚠️ تأكد أن البوت أدمن في القناة/المجموعة أولاً",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler_by_chat_id(uid, add_channel_step)

    elif data == "ch_remove":
        if not channels_groups:
            bot.send_message(uid, "📭 لا توجد قنوات/مجموعات مضافة حالياً.")
            return
        msg = "➖ *حذف قناة أو مجموعة*\n\nأرسل ID القناة/المجموعة للحذف:\n\n"
        for ch in channels_groups:
            msg += f"📺 *{ch['title']}* — `{ch['id']}`\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
        bot.register_next_step_handler_by_chat_id(uid, remove_channel_step)

    elif data == "ch_list":
        if not channels_groups:
            bot.send_message(uid, "📭 لا توجد قنوات/مجموعات مضافة حالياً.")
            return
        msg = "📋 *قائمة القنوات والمجموعات:*\n\n"
        for i, ch in enumerate(channels_groups, 1):
            emoji = "📢" if ch.get("type") == "channel" else "👥"
            msg += (
                f"{i}. {emoji} *{ch['title']}*\n"
                f"   🆔 ID: `{ch['id']}`\n"
                f"   🗣 اللغة: {ch.get('lang', 'غير محددة')}\n\n"
            )
        bot.send_message(uid, msg, parse_mode="Markdown")

    elif data == "ch_broadcast_now":
        bot.send_message(uid, "📡 جاري إرسال الأخبار للقنوات والمجموعات...")
        try:
            broadcast_to_channels()
            bot.send_message(uid, f"✅ تم إرسال الأخبار لـ {len(channels_groups)} قناة/مجموعة.")
        except Exception as e:
            bot.send_message(uid, f"❌ خطأ أثناء البث: {e}")

    # ======== خبر عاجل مخصص ========
    elif data == "admin_breaking_news":
        bot.send_message(uid,
            "🚨 *إرسال خبر عاجل مخصص*\n\n"
            "أرسل نص الخبر العاجل، وسيُرسَل فوراً لجميع المستخدمين والقنوات مع الأزرار.\n\n"
            "💡 يمكنك إضافة رابط في السطر الثاني (اختياري):\n"
            "`نص الخبر العاجل`\n"
            "`https://رابط-الخبر (اختياري)`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler_by_chat_id(uid, breaking_news_step)

    # ======== توقيت البث ========
    elif data == "admin_interval":
        current = broadcast_settings.get("interval_minutes", 1)
        markup_int = types.InlineKeyboardMarkup(row_width=3)
        markup_int.add(
            types.InlineKeyboardButton("1 دقيقة ✅" if current == 1 else "1 دقيقة", callback_data="interval_1"),
            types.InlineKeyboardButton("3 دقائق ✅" if current == 3 else "3 دقائق", callback_data="interval_3"),
            types.InlineKeyboardButton("5 دقائق ✅" if current == 5 else "5 دقائق", callback_data="interval_5"),
            types.InlineKeyboardButton("10 دقائق ✅" if current == 10 else "10 دقائق", callback_data="interval_10"),
            types.InlineKeyboardButton("15 دقيقة ✅" if current == 15 else "15 دقيقة", callback_data="interval_15"),
            types.InlineKeyboardButton("30 دقيقة ✅" if current == 30 else "30 دقيقة", callback_data="interval_30"),
            types.InlineKeyboardButton("60 دقيقة ✅" if current == 60 else "60 دقيقة", callback_data="interval_60"),
        )
        bot.send_message(uid,
            f"⏱ *توقيت البث الحالي:* كل `{current}` دقيقة\n\nاختر التوقيت الجديد:",
            parse_mode="Markdown", reply_markup=markup_int
        )

    elif data.startswith("interval_"):
        minutes = int(data.split("_")[1])
        broadcast_settings["interval_minutes"] = minutes
        save_broadcast_settings()
        interval_sec = max(30, minutes * 60)
        try:
            scheduler.reschedule_job("broadcast_news_job", trigger='interval', seconds=interval_sec)
            scheduler.reschedule_job("broadcast_channels_job", trigger='interval', seconds=interval_sec)
            applied = "✅ طُبِّق فوراً بدون إعادة تشغيل."
        except Exception as e:
            applied = f"⚠️ سيُطبَّق بعد إعادة التشغيل. ({e})"
        bot.send_message(uid,
            f"✅ تم تغيير توقيت البث إلى كل *{minutes}* دقيقة.\n{applied}",
            parse_mode="Markdown"
        )

    # ======== القائمة السوداء ========
    elif data == "admin_blacklist":
        words = blacklist_words
        count = len(words)
        words_preview = "، ".join(words[:10]) if words else "لا توجد كلمات"
        markup_bl = types.InlineKeyboardMarkup(row_width=2)
        markup_bl.add(
            types.InlineKeyboardButton("➕ إضافة كلمة", callback_data="bl_add"),
            types.InlineKeyboardButton("➖ حذف كلمة", callback_data="bl_remove"),
            types.InlineKeyboardButton("📋 عرض الكل", callback_data="bl_list"),
            types.InlineKeyboardButton("🗑 مسح الكل", callback_data="bl_clear"),
        )
        bot.send_message(uid,
            f"🚫 *القائمة السوداء للكلمات*\n\n"
            f"📊 عدد الكلمات: `{count}`\n"
            f"📝 عينة: {words_preview}\n\n"
            f"أي خبر يحتوي كلمة من هذه القائمة لن يُرسَل.",
            parse_mode="Markdown", reply_markup=markup_bl
        )

    elif data == "bl_add":
        bot.send_message(uid, "➕ أرسل الكلمة أو الكلمات التي تريد حجبها (كلمة واحدة أو أكثر مفصولة بفاصلة):")
        bot.register_next_step_handler_by_chat_id(uid, bl_add_step)

    elif data == "bl_remove":
        if not blacklist_words:
            bot.send_message(uid, "📭 القائمة السوداء فارغة.")
            return
        bot.send_message(uid, f"➖ أرسل الكلمة التي تريد حذفها:\n\n{', '.join(blacklist_words)}")
        bot.register_next_step_handler_by_chat_id(uid, bl_remove_step)

    elif data == "bl_list":
        if not blacklist_words:
            bot.send_message(uid, "📭 القائمة السوداء فارغة.")
            return
        bot.send_message(uid, "📋 *الكلمات المحجوبة:*\n\n" + "\n".join(f"• `{w}`" for w in blacklist_words), parse_mode="Markdown")

    elif data == "bl_clear":
        blacklist_words.clear()
        save_blacklist()
        bot.send_message(uid, "✅ تم مسح القائمة السوداء بالكامل.")

    # ======== عداد القراءة ========
    elif data == "admin_read_stats":
        total = read_stats.get("total_opens", 0)
        today = str(datetime.date.today())
        today_count = read_stats.get("daily", {}).get(today, 0)
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        yesterday_count = read_stats.get("daily", {}).get(yesterday, 0)
        bot.send_message(uid,
            f"📖 *إحصائيات القراءة (فتح الأخبار):*\n\n"
            f"📊 الإجمالي: `{total}` ضغطة\n"
            f"📅 اليوم: `{today_count}` ضغطة\n"
            f"📅 أمس: `{yesterday_count}` ضغطة",
            parse_mode="Markdown"
        )

    # ======== إحصائيات القنوات ========
    elif data == "admin_channel_stats":
        if not channels_groups:
            bot.send_message(uid, "📭 لا توجد قنوات/مجموعات مضافة.")
            return
        msg = "📈 *إحصائيات القنوات والمجموعات:*\n\n"
        total_sent = 0
        for ch in channels_groups:
            count_ch = ch.get("news_sent_count", 0)
            total_sent += count_ch
            emoji = "📢" if ch.get("type") == "channel" else "👥"
            msg += (
                f"{emoji} *{ch['title']}*\n"
                f"   📰 أخبار مُرسَلة: `{count_ch}`\n"
                f"   🌐 اللغة: {ch.get('lang', '-')}\n\n"
            )
        msg += f"━━━━━━━━━━━━━━\n📊 *إجمالي الأخبار المُرسَلة:* `{total_sent}`"
        bot.send_message(uid, msg, parse_mode="Markdown")

    # ======== بحث عن مستخدم ========
    elif data == "admin_search_user":
        bot.send_message(uid, "🔍 *بحث عن مستخدم*\n\nأرسل ID المستخدم أو اسمه للبحث:", parse_mode="Markdown")
        bot.register_next_step_handler_by_chat_id(uid, search_user_step)

    # ======== رسالة لمستخدم محدد ========
    elif data == "admin_msg_user":
        bot.send_message(uid,
            "✉️ *إرسال رسالة لمستخدم محدد*\n\n"
            "أرسل في سطرين:\n"
            "السطر 1: ID المستخدم\n"
            "السطر 2: نص الرسالة",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler_by_chat_id(uid, msg_user_step)

    # ======== قائمة الأوامر ========
    elif data == "admin_commands":
        commands_text = (
            "📋 *قائمة جميع أوامر البوت:*\n\n"
            "━━━━━━━━━ *للأدمن* ━━━━━━━━━\n"
            "👑 `/admin` — لوحة تحكم الأدمن\n"
            "📊 `/stats` — إحصائيات البوت (إن وُجد)\n\n"
            "━━━━━━━━━ *للمستخدم* ━━━━━━━━━\n"
            "🚀 `/start` — بدء البوت\n"
            "❓ `/help` — المساعدة\n"
            "🔔 `/notify` — تفعيل/إيقاف الإشعارات (إن وُجد)\n\n"
            "━━━━━━━━━ *لأدمن القناة/المجموعة* ━━━━━━━━━\n"
            "🌐 `/setlang اسم_اللغة` — تغيير لغة الأخبار\n"
            "🏙 `/setcity اسم_المدينة` — تعيين المدينة\n"
            "📡 `/setsource رابط_RSS` — إضافة مصدر أخبار\n"
            "🗑 `/removesource رابط_RSS` — حذف مصدر أخبار\n"
            "📋 `/listsources` — عرض مصادر الأخبار\n"
            "⏸ `/pause` — إيقاف البث مؤقتاً\n"
            "▶️ `/resume` — استئناف البث\n"
            "⚙️ `/settings` — عرض الإعدادات الحالية\n\n"
            "━━━━━━━━━ *الأزرار على كل خبر* ━━━━━━━━━\n"
            "🔗 فتح الخبر — يفتح رابط الخبر\n"
            "📤 شارك الخبر — يشارك الخبر\n"
            f"🤖 شارك البوت — يشارك @{BOT_USERNAME}"
        )
        bot.send_message(uid, commands_text, parse_mode="Markdown")

    elif data == "admin_news_format":
        sep = news_settings.get("separator", "━━━━━━━━━━━━━━")
        sig = news_settings.get("signature", "عبر بوت أخبار العالم\n@Iraqnowbot")
        label = news_settings.get("label", "🚨 خبر عاجل")
        preview = f"{label}\n\n📰 عنوان الخبر التجريبي\n{sep}\n{sig}"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ تعديل العنوان", callback_data="admin_nf_label"),
            types.InlineKeyboardButton("➖ تعديل الفاصل", callback_data="admin_nf_sep"),
            types.InlineKeyboardButton("📝 تعديل التوقيع", callback_data="admin_nf_sig"),
            types.InlineKeyboardButton("🔬 بث تجريبي للأدمن", callback_data="admin_nf_test"),
            types.InlineKeyboardButton("🔄 إعادة تعيين الإعدادات", callback_data="admin_nf_reset"),
        )
        try:
            bot.send_message(uid, f"✏️ *شكل رسالة الخبر الحالي:*\n\n{preview}", parse_mode="Markdown", reply_markup=markup)
        except Exception:
            # إذا فشل Markdown (بسبب رموز خاصة في الإعدادات)، أرسل بدون تنسيق
            bot.send_message(uid,
                f"✏️ شكل رسالة الخبر الحالي:\n\n{preview}\n\n"
                "⚠️ تنبيه: الإعدادات الحالية تحتوي على رموز غير صحيحة.\n"
                "استخدم 'إعادة تعيين' لإرجاع الإعدادات الافتراضية.",
                reply_markup=markup)

    elif data == "admin_broadcast_errors":
        with _broadcast_stats_lock:
            errors = list(_broadcast_errors)
        if not errors:
            bot.send_message(uid, "✅ لا توجد أخطاء مسجّلة.")
        else:
            text = "📋 *سجل آخر أخطاء البث:*\n\n" + "\n".join(f"`{e}`" for e in errors[-15:])
            try:
                bot.send_message(uid, text, parse_mode="Markdown")
            except Exception:
                bot.send_message(uid, "📋 سجل الأخطاء:\n\n" + "\n".join(errors[-10:]))

    elif data == "admin_nf_test":
        lang_test = "العربية 🇮🇶"
        feeds_test = RSS.get(lang_test, [])
        sent_test = False
        for feed_url in feeds_test:
            try:
                feed = _parse_feed(feed_url, timeout=15)
                if feed and feed.entries:
                    item = feed.entries[0]
                    title = getattr(item, 'title', 'عنوان تجريبي')
                    link = getattr(item, 'link', '')
                    summary = getattr(item, 'summary', '')
                    src_name = get_source_name_from_url(feed_url)
                    markup = make_news_share_markup(link, title, lang_test, summary)
                    pub_time_str = _format_pub_time(_pub_dt_from_item(item) if hasattr(item, 'published_parsed') else None, lang=lang_test)
                    text = format_news_item(t(lang_test, "label_breaking"), title, lang_test, src_name, pub_time_str, summary=summary)
                    bot.send_message(uid, "🔬 *بث تجريبي — هكذا سيصل الخبر للمستخدمين:*", parse_mode="Markdown")
                    try:
                        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=markup)
                    except Exception:
                        bot.send_message(uid, text, reply_markup=markup)
                    sent_test = True
                    break
            except Exception:
                continue
        if not sent_test:
            bot.send_message(uid, "⚠️ لم يتم العثور على أخبار حالياً للاختبار.")

    elif data == "admin_nf_label":
        msg = bot.send_message(uid, "📝 أرسل العنوان الجديد للخبر (مثال: 🚨 خبر عاجل):")
        bot.register_next_step_handler(msg, _nf_label_step)

    elif data == "admin_nf_sep":
        msg = bot.send_message(uid, "📝 أرسل الفاصل الجديد (مثال: ━━━━━━━━━━━━━━ أو --- أو اكتب 'بدون' لحذفه):")
        bot.register_next_step_handler(msg, _nf_sep_step)

    elif data == "admin_nf_sig":
        msg = bot.send_message(uid, "📝 أرسل التوقيع الجديد (مثال: عبر بوتي\\n@username):")
        bot.register_next_step_handler(msg, _nf_sig_step)

    elif data == "admin_nf_reset":
        news_settings["label"] = "🚨 خبر عاجل"
        news_settings["separator"] = "━━━━━━━━━━━━━━"
        news_settings["signature"] = "عبر بوت أخبار العالم\n@Iraqnowbot"
        news_settings.pop("label_i18n", None)
        news_settings.pop("signature_i18n", None)
        save_news_settings()
        bot.send_message(uid, "✅ تم إعادة تعيين شكل الخبر إلى الإعدادات الافتراضية.")

    elif data == "admin_inbox":
        if not inbox_messages:
            bot.send_message(uid, "📭 صندوق الرسائل فارغ حالياً.")
        else:
            last = inbox_messages[-10:]
            for entry in reversed(last):
                u_id = entry.get("uid")
                name = entry.get("name", "مجهول")
                text = entry.get("text", "")
                utype = "⭐ مميز" if entry.get("premium") else "👤 عادي"
                ts = entry.get("time", "")
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"↩️ رد على {name}", callback_data=f"admin_reply_{u_id}"))
                bot.send_message(uid,
                    f"💬 *رسالة من:* {name}\n"
                    f"🆔 `{u_id}` | {utype}\n"
                    f"🕐 {ts}\n\n"
                    f"📩 {text}",
                    parse_mode="Markdown", reply_markup=markup)

    elif data.startswith("admin_reply_"):
        target_uid = data.split("admin_reply_")[-1]
        msg = bot.send_message(uid, f"✏️ اكتب ردك على المستخدم `{target_uid}`:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m, tid=target_uid: _admin_reply_step(m, tid))

    elif data == "admin_ratings":
        count = ratings_data.get("count", 0)
        if count == 0:
            bot.send_message(uid, "⭐ لا توجد تقييمات بعد.")
        else:
            bot_avg = round(ratings_data.get("bot_sum", 0) / count, 1)
            news_avg = round(ratings_data.get("news_sum", 0) / count, 1)
            bot.send_message(uid,
                f"⭐ *تقييمات المستخدمين*\n\n"
                f"📊 إجمالي التقييمات: `{count}`\n"
                f"🤖 متوسط تقييم البوت: `{bot_avg}/5`\n"
                f"📰 متوسط تقييم الأخبار: `{news_avg}/5`",
                parse_mode="Markdown")

    elif data == "admin_backup":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📦 نسخة كاملة",      callback_data="backup_full"),
            types.InlineKeyboardButton("👥 قاعدة المستخدمين", callback_data="backup_users"),
            types.InlineKeyboardButton("📡 مصادر RSS",        callback_data="backup_rss"),
            types.InlineKeyboardButton("📺 القنوات والمجموعات", callback_data="backup_channels"),
            types.InlineKeyboardButton("⚙️ إعدادات البوت",    callback_data="backup_settings"),
        )
        bot.send_message(uid, "💾 *اختر نوع النسخة الاحتياطية:*", parse_mode="Markdown", reply_markup=markup)

    elif data == "backup_full":
        bot.answer_callback_query(call.id, "📤 جاري إرسال النسخة الكاملة...")
        send_backup(uid)

    elif data == "backup_users":
        bot.answer_callback_query(call.id, "👥 جاري إرسال بيانات المستخدمين...")
        _send_sectioned_backup(uid, "users")

    elif data == "backup_rss":
        bot.answer_callback_query(call.id, "📡 جاري إرسال مصادر RSS...")
        _send_sectioned_backup(uid, "rss")

    elif data == "backup_channels":
        bot.answer_callback_query(call.id, "📺 جاري إرسال القنوات...")
        _send_sectioned_backup(uid, "channels")

    elif data == "backup_settings":
        bot.answer_callback_query(call.id, "⚙️ جاري إرسال الإعدادات...")
        _send_sectioned_backup(uid, "settings")

    elif data == "admin_toggle_broadcast":
        broadcast_paused = not broadcast_paused
        if broadcast_paused:
            bot.answer_callback_query(call.id, "📴 تم إيقاف البث")
            bot.send_message(uid,
                "📴 *تم إيقاف البث الإخباري*\n\n"
                "البوت لا يزال يعمل ويستقبل الأوامر، لكن لن تُرسل أخبار تلقائية للمستخدمين.\n"
                "اضغط */admin* ← *📡 تشغيل البث* لإعادة التشغيل.",
                parse_mode="Markdown"
            )
        else:
            bot.answer_callback_query(call.id, "📡 تم تشغيل البث")
            bot.send_message(uid,
                "📡 *تم تشغيل البث الإخباري*\n\n"
                "سيبدأ إرسال الأخبار للمستخدمين في الدورة القادمة (خلال دقيقتين).",
                parse_mode="Markdown"
            )

    elif data == "admin_reset_sent_news":
        bot.answer_callback_query(call.id, "🔄 جاري إعادة التعيين...")
        count = 0
        for user_uid, user_data in list(users.items()):
            if "sent_news" in user_data:
                user_data["sent_news"] = {}   # dict فارغ — البنية الجديدة
                count += 1
        for ch in channels_groups:
            if "sent_news" in ch:
                ch["sent_news"] = []
        # مسح التتبع العالمي أيضاً
        with _global_sent_lock:
            _global_sent_news.clear()
        _db_save_all_users(users)
        save_channels_groups()
        _save_global_sent_news()
        bot.send_message(uid,
            f"✅ *تم إعادة تعيين سجل الأخبار*\n\n"
            f"• تم مسح sent\\_news لـ *{count}* مستخدم\n"
            f"• تم مسح سجل القنوات أيضاً\n"
            f"• تم مسح التتبع العالمي للأخبار\n\n"
            f"🚀 سيبدأ البث فوراً في الدورة القادمة (خلال دقيقتين)",
            parse_mode="Markdown"
        )

    elif data == "admin_full_reset":
        # خطوة التأكيد الأولى
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⚠️ نعم، امسح كل شيء", callback_data="admin_full_reset_confirm"),
            types.InlineKeyboardButton("❌ إلغاء", callback_data="admin_cancel"),
        )
        bot.send_message(uid,
            "🗑 *إعادة تعيين البوت كاملاً*\n\n"
            "⚠️ *تحذير: هذا الإجراء لا يمكن التراجع عنه!*\n\n"
            "سيتم مسح:\n"
            "• ✂️ كل بيانات المستخدمين (اللغة، المدينة، الإعدادات)\n"
            "• 📰 سجل الأخبار المُرسلة\n"
            "• 📊 الإحصائيات\n"
            "• 🚫 قائمة المحظورين\n"
            "• 💬 صندوق الرسائل والتقييمات\n"
            "• ✏️ شكل رسالة الخبر (يُعاد للافتراضي)\n\n"
            "سيتم *الاحتفاظ* بـ:\n"
            "• 👑 قائمة الأدمن\n"
            "• 📡 مصادر RSS المخصصة\n"
            "• 📺 القنوات والمجموعات\n\n"
            "هل أنت متأكد؟",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data == "admin_full_reset_confirm":
        bot.answer_callback_query(call.id, "⏳ جاري إعادة التعيين الكاملة...")
        # --- مسح بيانات المستخدمين ---
        users.clear()
        save_json(USERS_FILE, {})
        _db_save_all_users({})
        # --- مسح الإحصائيات ---
        stats.clear()
        stats.update({"total_users": 0, "daily_users": {}, "lang_dist": {}, "country_dist": {}})
        save_json(STATS_FILE, stats)
        # --- مسح قائمة المحظورين ---
        banned.clear()
        save_json(BANNED_FILE, [])
        # --- مسح صندوق الرسائل ---
        inbox_messages.clear()
        save_json(INBOX_FILE, [])
        # --- مسح التقييمات ---
        save_json(RATINGS_FILE, {})
        # --- مسح سجل القراءة ---
        save_json(READ_STATS_FILE, {"total_opens": 0, "daily": {}})
        # --- إعادة شكل الخبر للافتراضي ---
        news_settings["label"] = "🚨 خبر عاجل"
        news_settings["separator"] = "━━━━━━━━━━━━━━"
        news_settings["signature"] = "عبر بوت أخبار العالم\n@Iraqnowbot"
        news_settings.pop("label_i18n", None)
        news_settings.pop("signature_i18n", None)
        save_news_settings()
        # --- مسح سجل الأخبار المُرسلة (global + per-channel) ---
        with _global_sent_lock:
            _global_sent_news.clear()
        _save_global_sent_news()
        for ch in channels_groups:
            ch["sent_news"] = []
        save_channels_groups()
        bot.send_message(uid,
            "✅ *تمت إعادة التعيين الكاملة بنجاح*\n\n"
            "• بيانات المستخدمين: ✅ ممسوحة\n"
            "• الإحصائيات: ✅ ممسوحة\n"
            "• قائمة المحظورين: ✅ ممسوحة\n"
            "• صندوق الرسائل: ✅ ممسوح\n"
            "• شكل الخبر: ✅ أُعيد للافتراضي\n"
            "• سجل الأخبار: ✅ ممسوح\n\n"
            "📡 قائمة الأدمن ومصادر RSS والقنوات محتفظ بها.\n\n"
            "🚀 البوت جاهز لاستقبال مستخدمين جدد!",
            parse_mode="Markdown"
        )

    elif data == "admin_cancel":
        bot.answer_callback_query(call.id, "❌ تم الإلغاء")
        bot.send_message(uid, "❌ تم إلغاء العملية.")

    elif data == "admin_debugnews":
        bot.answer_callback_query(call.id, "🔍 جاري التشخيص...")
        # استدعاء نفس منطق /debugnews
        now_utc = _now_sa()
        news_lock_status  = "🔴 مشغول" if _broadcast_news_lock.is_set() else "🟢 حر"
        ch_lock_status    = "🔴 مشغول" if _broadcast_channels_lock.is_set() else "🟢 حر"
        with _global_sent_lock:
            gsn_counts = {lang: len(s) for lang, s in _global_sent_news.items()}
        gsn_text = "\n".join([f"  `{l[:15]}`: {cnt}" for l, cnt in gsn_counts.items()]) or "  فارغ ✅"
        active_users = sum(1 for info in users.values()
                           if info.get("notifications", True) and info.get("lang"))
        gsn_age = "—"
        try:
            if os.path.exists(_GLOBAL_SENT_FILE):
                age_secs = time.time() - os.path.getmtime(_GLOBAL_SENT_FILE)
                gsn_age = f"{age_secs/60:.0f} دقيقة"
        except Exception as _exc:
            _log_exc(_exc)
        msg = (
            f"🔍 تشخيص نظام الإرسال\n"
            f"🕐 {now_utc.strftime('%H:%M:%S')} (توقيت السعودية)\n\n"
            f"الأقفال: بث={news_lock_status} | قنوات={ch_lock_status}\n"
            f"الإيقاف: bot={bot_paused}, bcast={broadcast_paused}\n"
            f"المستخدمون: إجمالي={len(users)} | فعّالون={active_users}\n\n"
            f"global_sent_news (عمر الملف: {gsn_age}):\n{gsn_text}\n\n"
            f"الأوامر: /clearcache | /forcenews"
        )
        bot.send_message(uid, msg)

    elif data == "admin_clearcache":
        bot.answer_callback_query(call.id, "🧹 جاري المسح...")
        with _global_sent_lock:
            old_count = sum(len(s) for s in _global_sent_news.values())
            _global_sent_news.clear()
        _save_global_sent_news()
        bot.send_message(uid,
            f"✅ *تم مسح كاش الأخبار*\n"
            f"حُذف `{old_count:,}` رابط — سيبدأ البث الفوري خلال 30 ثانية",
            parse_mode="Markdown")

    elif data == "admin_forcenews":
        bot.answer_callback_query(call.id, "⚡ جاري إطلاق البث...")
        # نكسر أي قفل قديم تلقائياً ثم نطلق دورة جديدة
        was_locked = _broadcast_news_lock.is_set()
        _broadcast_news_lock.clear()
        _broadcast_channels_lock.clear()
        note = " (تم تجاوز قفل قديم)" if was_locked else ""
        bot.send_message(uid, f"✅ تم إطلاق دورة البث الفورية!{note}")
        # FIX: مباشر بدل Thread منفصل لمنع تراكم الخيوط
        _safe_job(broadcast_news)()

# ======== لوحة إدارة الميزات (أزرار بصرية) ========
_FEATURE_FRIENDLY_NAMES = {
    "summary":        "📄 ملخص الخبر",
    "why_matters":    "💡 لماذا يهمك؟",
    "what_next":      "🔮 ماذا بعد؟",
    "intel_report":   "🧠 تقرير ذكي شامل",
    "context":        "📚 السياق التاريخي",
    "factcheck":      "🔍 التحقق من الخبر",
    "deepdive":       "🔬 تحليل عميق",
    "storyline":      "🗓 خط الأحداث",
    "entity_track":   "📡 تتبع شخص/شركة",
    "custom_rss":     "📰 مصادر مخصصة",
    "bookmark":       "🔖 حفظ الأخبار",
    "keywords_alert": "🔑 تنبيه كلمات مفتاحية",
    "weekly_report":  "📆 تقرير أسبوعي",
    "news_quiz":      "🧩 اختبار الأخبار",
    "catchup":        "⏩ ماذا فاتني؟",
    "compare":        "🔄 مقارنة المصادر",
    "audiobriefing":  "🎙 الموجز الإخباري",
    "cross_lang":     "🌍 مقارنة متعددة اللغات",
    "audio_podcast":  "🎧 بودكاست يومي",
    "sleep_mode":     "😴 وضع الصمت الذكي",
    "prediction":     "🔮 توقع المستقبل",
    "audio_article":  "🎧 اسمع الخبر",
    "discuss":        "🤝 ناقش الخبر",
    "ai_duel":        "⚔️ جدال ذكي",
    "news_dna":       "🧬 بصمة الخبر",
}

_MODE_ICONS = {"free": "🟢", "limited": "🔢", "premium_only": "⭐", "disabled": "🚫"}
