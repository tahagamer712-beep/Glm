# -*- coding: utf-8 -*-
"""
  social_media.py — Facebook + Instagram + ImgBB

  يُصدِّر دوال النشر على وسائل التواصل الاجتماعي.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _save_social_settings():
    save_json(SOCIAL_SETTINGS_FILE, _social_settings)

def _set_social_image(file_id):
    """يحفظ file_id صورة الغلاف من تيليغرام"""
    _social_settings["image_file_id"] = file_id
    _save_social_settings()

def _get_social_image_bytes():
    """يحمّل بايتات صورة الغلاف من تيليغرام"""
    file_id = _social_settings.get("image_file_id")
    if not file_id:
        return None
    try:
        file_info = bot.get_file(file_id)
        file_url  = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        r = requests.get(file_url, timeout=10)
        return r.content if r.status_code == 200 else None
    except Exception:
        return None

def _upload_to_imgbb(image_bytes):
    """يرفع الصورة على imgbb ويُرجع الرابط العام (مطلوب لـ Instagram)"""
    if not IMGBB_API_KEY or not image_bytes:
        return None
    try:
        b64 = _b64.b64encode(image_bytes).decode("utf-8")
        r = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64},
            timeout=20
        )
        if r.status_code == 200:
            return r.json()["data"]["url"]
    except Exception as _exc:
        _log_exc(_exc)
    return None

def _post_to_facebook(message, image_bytes=None):
    """ينشر على صفحة فيسبوك (نص + صورة اختيارية)"""
    if not FB_PAGE_TOKEN or not FB_PAGE_ID:
        return False
    try:
        if image_bytes:
            url  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
            resp = requests.post(
                url,
                data={"message": message, "access_token": FB_PAGE_TOKEN},
                files={"source": ("cover.jpg", image_bytes, "image/jpeg")},
                timeout=30
            )
        else:
            url  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
            resp = requests.post(
                url,
                data={"message": message, "access_token": FB_PAGE_TOKEN},
                timeout=30
            )
        ok = resp.status_code == 200
        if not ok:
            _logger.warning(f"Facebook post failed: {resp.text[:200]}")
        return ok
    except Exception as e:
        _logger.warning(f"Facebook post error: {e}")
        return False

def _post_to_instagram(caption, image_url):
    """ينشر على انستغرام Business عبر Graph API"""
    if not FB_PAGE_TOKEN or not IG_USER_ID or not image_url:
        return False
    try:
        # الخطوة 1: إنشاء media container
        r1 = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            data={
                "image_url": image_url,
                "caption":   caption[:2200],
                "access_token": FB_PAGE_TOKEN
            },
            timeout=30
        )
        if r1.status_code != 200:
            _logger.warning(f"Instagram container failed: {r1.text[:200]}")
            return False
        creation_id = r1.json().get("id")
        if not creation_id:
            return False
        # الخطوة 2: نشر المنشور
        r2 = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            data={"creation_id": creation_id, "access_token": FB_PAGE_TOKEN},
            timeout=30
        )
        ok = r2.status_code == 200
        if not ok:
            _logger.warning(f"Instagram publish failed: {r2.text[:200]}")
        return ok
    except Exception as e:
        _logger.warning(f"Instagram post error: {e}")
        return False

def _post_social_media(title, link, lang="العربية 🇮🇶"):
    """
    يُرسل منشوراً لفيسبوك + انستغرام.
    يتجاهل المنشور إذا مضت أقل من SOCIAL_MIN_INTERVAL على آخر نشر،
    أو إذا نُشر هذا الرابط مسبقاً.
    """
    if not FB_PAGE_TOKEN:
        return  # لا يوجد إعداد بعد
    if link in _social_posted_links:
        return
    now = time.time()
    if now - _social_last_post["ts"] < SOCIAL_MIN_INTERVAL:
        return
    _social_posted_links.add(link)
    _social_last_post["ts"] = now

    # إعداد نص المنشور
    signature = "#عراق_ناو #أخبار #IraqNow"
    message   = f"📰 {title}\n\n🔗 {link}\n\n{signature}"

    # تشغيل النشر في خيط منفصل لا يعطّل البوت
    def _do_post():
        image_bytes = _get_social_image_bytes()
        # فيسبوك
        _post_to_facebook(message, image_bytes)
        # انستغرام (يحتاج رابط عام للصورة)
        if image_bytes and IMGBB_API_KEY:
            img_url = _upload_to_imgbb(image_bytes)
            if img_url:
                _post_to_instagram(message, img_url)
        elif image_bytes:
            # بدون IMGBB: انستغرام بدون صورة غير ممكن، نتخطاه
            _logger.info("Instagram skipped: no IMGBB_API_KEY set")

    import threading as _th
    _th.Thread(target=_do_post, daemon=True).start()

# ======== مصادر أخبار الرياضة ========
SPORTS_RSS = {
    "العربية 🇮🇶": [
        "https://www.skynewsarabia.com/rss/sport.xml",
        "https://www.filgoal.com/rss",
        "https://www.yallakora.com/rss",
        "https://arabic.euronews.com/rss/sport",
        "https://sport.al-ain.com/rss",
        "https://arabic.goal.com/ar/news/rss",
        "https://www.beinsports.com/ar/rss",
        "https://www.kooora.com/?rss",
        # F1 / موتور سبورت
        "https://ar.motorsport.com/rss/f1/news/",
        "https://ar.motorsport.com/rss/motogp/news/",
        # رالي داكار
        "https://ar.motorsport.com/rss/dakar/news/",
        # تنس
        "https://ar.wtatennis.com/news/rss",
    ],
    "English 🇬🇧": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://www.espn.com/espn/rss/news",
        "https://www.theguardian.com/sport/rss",
        "https://sports.yahoo.com/rss/",
        "https://www.goal.com/feeds/en/news",
        # F1
        "https://www.motorsport.com/rss/f1/news/",
        "https://www.formula1.com/content/fom-website/en/latest/all.xml",
        # NASCAR
        "https://www.motorsport.com/rss/nascar/news/",
        "https://www.nascar.com/rss/news.xml",
        # MotoGP
        "https://www.motorsport.com/rss/motogp/news/",
        # Rally Dakar
        "https://www.dakar.com/en/rss",
        "https://www.motorsport.com/rss/dakar/news/",
        # WRC
        "https://www.motorsport.com/rss/wrc/news/",
        # Tennis
        "https://www.atptour.com/en/media/rss-feed/xml-feed",
        "https://www.wtatennis.com/news/rss",
        # NBA / Basketball
        "https://www.nba.com/feeds/nba/league/stories.rss",
        # NFL
        "https://www.nfl.com/rss/rsslanding?searchString=news",
        # NHL Hockey
        "https://www.nhl.com/rss/news.xml",
        # MLB Baseball
        "https://www.mlb.com/feeds/news/rss.xml",
        # Golf
        "https://www.pgatour.com/news/rss.xml",
        # Boxing / MMA
        "https://www.espn.com/espn/rss/boxing/news",
        "https://mmajunkie.usatoday.com/feed",
    ],
    "Русский 🇷🇺": [
        "https://rsport.ria.ru/export/rss2/index.xml",
        "https://www.sports.ru/rss/main.xml",
        "https://ru.motorsport.com/rss/f1/news/",
    ],
    "فارسی 🇮🇷": [
        "https://feeds.bbci.co.uk/persian/rss.xml",
        "https://www.varzesh3.com/rss/all",
        "https://fa.motorsport.com/rss/f1/news/",
    ],
    "Türkçe 🇹🇷": [
        "https://www.ntv.com.tr/spor.rss",
        "https://www.sabah.com.tr/rss/spor.xml",
        "https://tr.motorsport.com/rss/f1/news/",
    ],
    "Deutsch 🇩🇪": [
        "https://rss.dw.com/rdf/rss-de-sports",
        "https://www.sport1.de/rss/sport1-news.rss",
        "https://de.motorsport.com/rss/f1/news/",
    ],
    "Español 🇲🇽": [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada",
        "https://cnnespanol.cnn.com/deportes/feed/",
        "https://es.motorsport.com/rss/f1/news/",
        "https://es.motorsport.com/rss/motogp/news/",
    ],
    "Português 🇧🇷": [
        "https://globoesporte.globo.com/dynamo/esportes/futebol/rss2.xml",
        "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "https://pt.motorsport.com/rss/f1/news/",
    ],
    "Italiano 🇮🇹": [
        "https://www.gazzetta.it/rss/home.xml",
        "https://it.motorsport.com/rss/f1/news/",
        "https://it.motorsport.com/rss/motogp/news/",
    ],
    "हिन्दी 🇮🇳": [
        "https://feeds.bbci.co.uk/hindi/rss.xml",
        "https://hi.motorsport.com/rss/f1/news/",
    ],
    "اردو 🇵🇰": [
        "https://www.geo.tv/rss",
        "https://www.dawn.com/feeds/sport",
    ],
    "Українська 🇺🇦": [
        "https://www.ukrinform.ua/rss/block-sport",
        "https://uk.motorsport.com/rss/f1/news/",
    ],
}

# ======== نظام Scraping — سحب الأخبار مباشرة من المواقع ========
try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False
    _logger.warning("⚠️ مكتبة beautifulsoup4 غير مثبتة. ثبّتها بـ:  pip install beautifulsoup4")

_SCRAPE_TIMEOUT = 20                # ثانية قبل تجاهل الموقع
_SCRAPE_CACHE = {}                  # url -> (items_list, timestamp)
_SCRAPE_CACHE_TTL = 300             # 5 دقائق — لا نطلب نفس الصفحة أكثر من مرة كل 5 دقائق
_SCRAPE_LOCK = threading.Lock()

# User-Agent واقعي يحاكي متصفح Chrome لتجنب الحجب
_SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ======== مصادر الـ Scraping (مواقع بدون RSS أو RSS ضعيف) ========
# كل مصدر يحتوي: url, name, base_url
# base_url يُستخدم لتحويل الروابط النسبية (/news/123) إلى روابط مطلقة
SCRAPE_SOURCES = {
    # ======== وكالات وصحف عراقية ========
    "العربية 🇮🇶": [
        {"url": "https://www.rudaw.net/arabic/latest-news",   "name": "رووداو",               "base_url": "https://www.rudaw.net"},
        {"url": "https://mawazin.net/",                        "name": "موازين نيوز",          "base_url": "https://mawazin.net"},
        {"url": "https://www.alsabah.iq/",                    "name": "الصباح",               "base_url": "https://www.alsabah.iq"},
        {"url": "https://www.ina.iq/arabic/latest.php",       "name": "وكالة الأنباء العراقية","base_url": "https://www.ina.iq"},
        {"url": "https://www.iraqia.news/news",               "name": "العراقية نيوز",        "base_url": "https://www.iraqia.news"},
        {"url": "https://alkafeel.net/news/",                 "name": "الكفيل",               "base_url": "https://alkafeel.net"},
        {"url": "https://www.nrttv.com/ar/news",              "name": "NRT عربي",             "base_url": "https://www.nrttv.com"},
        {"url": "https://shafaq.com/ar/",                     "name": "شفق نيوز",             "base_url": "https://shafaq.com"},
        {"url": "https://www.almaalomah.com/",                "name": "المعلومة",             "base_url": "https://www.almaalomah.com"},
        {"url": "https://almada-paper.com/",                  "name": "المدى",                "base_url": "https://almada-paper.com"},
        {"url": "https://www.alsumaria.tv/",                  "name": "السومرية",             "base_url": "https://www.alsumaria.tv"},
        {"url": "https://www.baghdadtoday.news/",             "name": "بغداد اليوم",          "base_url": "https://www.baghdadtoday.news"},
        {"url": "https://www.basnews.com/ar/",                "name": "باس نيوز",             "base_url": "https://www.basnews.com"},
        {"url": "https://www.ankawa.com/",                    "name": "عنكاوا",               "base_url": "https://www.ankawa.com"},
        {"url": "https://www.buratha.news/",                  "name": "بروثا نيوز",           "base_url": "https://www.buratha.news"},
        {"url": "https://www.alforatnews.iq/",               "name": "الفرات نيوز",          "base_url": "https://www.alforatnews.iq"},
        {"url": "https://www.nasnews.com/",                   "name": "ناس نيوز",             "base_url": "https://www.nasnews.com"},
        {"url": "https://www.krsc.org/ar/",                   "name": "KirkukNow",            "base_url": "https://www.krsc.org"},
        # ======== وكالات عالمية باللغة العربية ========
        {"url": "https://arabic.rt.com/news/",                "name": "RT عربي",              "base_url": "https://arabic.rt.com"},
        {"url": "https://www.dw.com/ar/",                     "name": "DW عربي",              "base_url": "https://www.dw.com"},
        {"url": "https://www.france24.com/ar/",               "name": "فرانس 24",             "base_url": "https://www.france24.com"},
        {"url": "https://arabic.euronews.com/news",           "name": "يورونيوز عربي",        "base_url": "https://arabic.euronews.com"},
        {"url": "https://www.alarabiya.net/",                 "name": "العربية",              "base_url": "https://www.alarabiya.net"},
        {"url": "https://www.middleeasteye.net/ar/",          "name": "Middle East Eye",      "base_url": "https://www.middleeasteye.net"},
        {"url": "https://www.independentarabia.com/",         "name": "إندبندنت عربية",       "base_url": "https://www.independentarabia.com"},
        {"url": "https://arabi21.com/",                       "name": "عربي 21",              "base_url": "https://arabi21.com"},
    ],
    "English 🇬🇧": [
        {"url": "https://www.rudaw.net/english/latest-news",  "name": "Rudaw English",        "base_url": "https://www.rudaw.net"},
        {"url": "https://www.iraqinews.com/latest/",          "name": "Iraq News",            "base_url": "https://www.iraqinews.com"},
        {"url": "https://www.nrttv.com/en/news",              "name": "NRT English",          "base_url": "https://www.nrttv.com"},
        {"url": "https://www.basnews.com/en/",                "name": "Bas News English",     "base_url": "https://www.basnews.com"},
        {"url": "https://www.reuters.com/world/",             "name": "Reuters",              "base_url": "https://www.reuters.com"},
        {"url": "https://apnews.com/",                        "name": "AP News",              "base_url": "https://apnews.com"},
        {"url": "https://www.bbc.com/news/world/",            "name": "BBC World",            "base_url": "https://www.bbc.com"},
        {"url": "https://www.dw.com/en/news/",                "name": "DW English",           "base_url": "https://www.dw.com"},
        {"url": "https://www.aljazeera.com/news/",            "name": "Al Jazeera",           "base_url": "https://www.aljazeera.com"},
        {"url": "https://www.middleeasteye.net/",             "name": "Middle East Eye",      "base_url": "https://www.middleeasteye.net"},
        {"url": "https://english.alarabiya.net/",             "name": "Al Arabiya English",   "base_url": "https://english.alarabiya.net"},
    ],
    "Русский 🇷🇺": [
        {"url": "https://lenta.ru/",                          "name": "Лента.ру",             "base_url": "https://lenta.ru"},
        {"url": "https://www.gazeta.ru/news/",                "name": "Газета.ру",            "base_url": "https://www.gazeta.ru"},
        {"url": "https://tass.ru/",                           "name": "ТАСС",                 "base_url": "https://tass.ru"},
        {"url": "https://ria.ru/",                            "name": "РИА Новости",          "base_url": "https://ria.ru"},
        {"url": "https://www.kommersant.ru/",                 "name": "Коммерсантъ",          "base_url": "https://www.kommersant.ru"},
        {"url": "https://russian.rt.com/",                    "name": "RT Русский",           "base_url": "https://russian.rt.com"},
    ],
    "Türkçe 🇹🇷": [
        {"url": "https://www.haberturk.com/son-dakika",       "name": "Haber Türk",           "base_url": "https://www.haberturk.com"},
        {"url": "https://www.milliyet.com.tr/son-dakika/",    "name": "Milliyet",             "base_url": "https://www.milliyet.com.tr"},
        {"url": "https://www.hurriyet.com.tr/gundem/",        "name": "Hürriyet",             "base_url": "https://www.hurriyet.com.tr"},
        {"url": "https://www.sabah.com.tr/son-dakika/",       "name": "Sabah",                "base_url": "https://www.sabah.com.tr"},
        {"url": "https://www.ntv.com.tr/son-dakika",          "name": "NTV",                  "base_url": "https://www.ntv.com.tr"},
        {"url": "https://tr.sputniknews.com/",                "name": "Sputnik Türkçe",       "base_url": "https://tr.sputniknews.com"},
    ],
    "فارسی 🇮🇷": [
        {"url": "https://www.farsnews.ir/",                   "name": "فارس نیوز",            "base_url": "https://www.farsnews.ir"},
        {"url": "https://www.tasnimnews.com/fa/news",         "name": "تسنیم",                "base_url": "https://www.tasnimnews.com"},
        {"url": "https://www.isna.ir/",                       "name": "ایسنا",                "base_url": "https://www.isna.ir"},
        {"url": "https://www.irna.ir/",                       "name": "ایرنا",                "base_url": "https://www.irna.ir"},
        {"url": "https://ir.sputniknews.com/",                "name": "اسپوتنیک فارسی",       "base_url": "https://ir.sputniknews.com"},
    ],
    "Deutsch 🇩🇪": [
        {"url": "https://www.focus.de/",                      "name": "Focus",                "base_url": "https://www.focus.de"},
        {"url": "https://www.spiegel.de/",                    "name": "Der Spiegel",          "base_url": "https://www.spiegel.de"},
        {"url": "https://www.zeit.de/",                       "name": "Die Zeit",             "base_url": "https://www.zeit.de"},
        {"url": "https://www.n-tv.de/",                       "name": "n-tv",                 "base_url": "https://www.n-tv.de"},
        {"url": "https://www.sueddeutsche.de/",               "name": "Süddeutsche Zeitung",  "base_url": "https://www.sueddeutsche.de"},
    ],
    "Español 🇲🇽": [
        {"url": "https://www.clarin.com/ultimo-momento/",     "name": "Clarín",               "base_url": "https://www.clarin.com"},
        {"url": "https://www.infobae.com/",                   "name": "Infobae",              "base_url": "https://www.infobae.com"},
        {"url": "https://www.elmundo.es/",                    "name": "El Mundo",             "base_url": "https://www.elmundo.es"},
        {"url": "https://elpais.com/",                        "name": "El País",              "base_url": "https://elpais.com"},
        {"url": "https://es.sputniknews.com/",                "name": "Sputnik Español",      "base_url": "https://es.sputniknews.com"},
    ],
    "Português 🇧🇷": [
        {"url": "https://noticias.uol.com.br/",               "name": "UOL Notícias",         "base_url": "https://noticias.uol.com.br"},
        {"url": "https://www.terra.com.br/noticias/",         "name": "Terra Brasil",         "base_url": "https://www.terra.com.br"},
        {"url": "https://www.correiobraziliense.com.br/",     "name": "Correio Braziliense",  "base_url": "https://www.correiobraziliense.com.br"},
        {"url": "https://pt.sputniknews.com/",                "name": "Sputnik Português",    "base_url": "https://pt.sputniknews.com"},
    ],
    "हिन्दी 🇮🇳": [
        {"url": "https://www.ndtv.com/india/",                "name": "NDTV Hindi",           "base_url": "https://www.ndtv.com"},
        {"url": "https://www.bhaskar.com/",                   "name": "Dainik Bhaskar",       "base_url": "https://www.bhaskar.com"},
        {"url": "https://hindi.news18.com/",                  "name": "News18 Hindi",         "base_url": "https://hindi.news18.com"},
    ],
    "اردو 🇵🇰": [
        {"url": "https://www.geo.tv/",                        "name": "Geo TV",               "base_url": "https://www.geo.tv"},
        {"url": "https://www.dunyanews.tv/",                  "name": "Dunya News",           "base_url": "https://www.dunyanews.tv"},
        {"url": "https://jang.com.pk/",                       "name": "جنگ",                  "base_url": "https://jang.com.pk"},
    ],
    "Українська 🇺🇦": [
        {"url": "https://www.pravda.com.ua/",                 "name": "Українська правда",    "base_url": "https://www.pravda.com.ua"},
        {"url": "https://www.unian.ua/",                      "name": "УНІАН",                "base_url": "https://www.unian.ua"},
        {"url": "https://ukrinform.ua/",                      "name": "Укрінформ",            "base_url": "https://ukrinform.ua"},
    ],
    "Italiano 🇮🇹": [
        {"url": "https://www.ansa.it/sito/notizie/topnews/",  "name": "ANSA",                 "base_url": "https://www.ansa.it"},
        {"url": "https://www.corriere.it/",                   "name": "Corriere della Sera",  "base_url": "https://www.corriere.it"},
        {"url": "https://www.repubblica.it/",                 "name": "La Repubblica",        "base_url": "https://www.repubblica.it"},
    ],
}

# ======== قنوات تلغرام كمصادر أخبار (عراقية وعالمية) ========
TELEGRAM_NEWS_CHANNELS = {
    "العربية 🇮🇶": [
        # ===== وكالات أخبار عراقية (مُختبَرة وتعمل) =====
        {"handle": "inainaiq",          "name": "وكالة الأنباء العراقية"},
        {"handle": "shafaq",            "name": "شفق نيوز"},
        {"handle": "alsbaahiq",         "name": "الصباح العراقية"},
        {"handle": "almaalomah",        "name": "المعلومة"},
        {"handle": "baghdadtoday",      "name": "بغداد اليوم"},
        {"handle": "RN24_IQ",           "name": "راديو نوا 24"},
        {"handle": "StevenNabilIraq",   "name": "ستيفن نبيل"},
        {"handle": "baghdad7city",      "name": "بغداد سيتي"},
        {"handle": "RudawArabic",       "name": "رووداو عربي"},
        {"handle": "NRT_Arabic",        "name": "NRT عربي"},
        {"handle": "burathanews",       "name": "بروثا نيوز"},
        {"handle": "iraq_news_now",     "name": "أخبار العراق"},
        {"handle": "kirkuk_now",        "name": "كركوك ناو"},
        {"handle": "iraq11e",           "name": "عين العراق"},
        {"handle": "iraqi1_news",       "name": "شبكة أخبار العراق"},
        {"handle": "Iraq_now3",         "name": "عراق ناو"},
        # ===== وكالات عالمية بالعربية =====
        {"handle": "RT_ar",             "name": "RT عربي"},
        {"handle": "aljazeera",         "name": "الجزيرة"},
        {"handle": "alarabiya",         "name": "العربية"},
        {"handle": "bbcarabic",         "name": "بي بي سي عربي"},
        {"handle": "france24_ar",       "name": "فرانس 24 عربي"},
        {"handle": "DWArabic",          "name": "DW عربي"},
        {"handle": "independentarabia", "name": "إندبندنت عربية"},
        {"handle": "arabi21news",       "name": "عربي 21"},
        {"handle": "almayadeen_ar",     "name": "الميادين"},
    ],
    "English 🇬🇧": [
        {"handle": "ap_news",           "name": "Associated Press"},
        {"handle": "BBCWorld",          "name": "BBC World"},
        {"handle": "AlJazeera",         "name": "Al Jazeera English"},
        {"handle": "cnnbrk",            "name": "CNN Breaking News"},
        {"handle": "guardian",          "name": "The Guardian"},
        {"handle": "Independent",       "name": "The Independent"},
        {"handle": "TheEconomist",      "name": "The Economist"},
        {"handle": "politico",          "name": "Politico"},
    ],
    "Русский 🇷🇺": [
        {"handle": "tass_agency",       "name": "ТАСС"},
        {"handle": "rianewsru",         "name": "РИА Новости"},
        {"handle": "lenta_ru",          "name": "Лента.ру"},
        {"handle": "kommersant",        "name": "Коммерсантъ"},
        {"handle": "izvestia",          "name": "Известия"},
        {"handle": "rbc_news",          "name": "РБК Новости"},
    ],
    "Türkçe 🇹🇷": [
        {"handle": "anadoluajansi",     "name": "Anadolu Ajansı"},
    ],
    "فارسی 🇮🇷": [
        {"handle": "bbcpersian",        "name": "بیبیسی فارسی"},
    ],
    "Deutsch 🇩🇪": [
        {"handle": "dwnachrichten",     "name": "DW Nachrichten"},
    ],
    "Español 🇲🇽": [
        {"handle": "RTenEspanol",       "name": "RT en Español"},
        {"handle": "elpais",            "name": "El País"},
    ],
    "Français 🇫🇷": [
        {"handle": "lemondefr",         "name": "Le Monde"},
        {"handle": "rfi_francais",      "name": "RFI Français"},
    ],
    "中文 🇨🇳": [
        {"handle": "xinhua_cn",         "name": "新华社"},
        {"handle": "cgtn_cn",           "name": "CGTN中文"},
    ],
    "हिन्दी 🇮🇳": [
        {"handle": "ndtvindia",         "name": "NDTV India"},
        {"handle": "bbc_hindi",         "name": "BBC Hindi"},
    ],
    "Italiano 🇮🇹": [
        {"handle": "larepubblica",      "name": "la Repubblica"},
    ],
}

_TG_SCRAPE_CACHE = {}       # handle -> (items, timestamp)
_TG_SCRAPE_CACHE_TTL = 180  # 3 دقائق

def handle_set_social_cmd(message):
    """أدمن فقط — يبدأ وضع تعيين صورة الغلاف للسوشيال ميديا"""
    uid = message.from_user.id
    if not is_admin(uid):
        return
    _social_settings["awaiting_image"] = True
    _save_social_settings()
    bot.send_message(
        uid,
        "📸 *تعيين صورة الغلاف*\n\n"
        "الحين أرسل الصورة التي تريدها تُنشر مع كل خبر على فيسبوك وانستغرام.\n\n"
        "⚠️ يجب أن تكون الصورة بنسبة 1:1 أو 4:5 للأفضل على انستغرام.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['socialtoggle'])
def handle_social_toggle(message):
    """أدمن فقط — يفعّل أو يوقف النشر على السوشيال ميديا"""
    uid = message.from_user.id
    if not is_admin(uid):
        return
    current = _social_settings.get("enabled", True)
    _social_settings["enabled"] = not current
    _save_social_settings()
    state = "✅ مفعّل" if not current else "⏸ موقوف"
    bot.send_message(uid, f"📢 النشر على السوشيال ميديا: *{state}*", parse_mode="Markdown")

@bot.message_handler(commands=['socialstatus'])
def handle_social_status(message):
    """أدمن فقط — يعرض حالة إعداد السوشيال ميديا"""
    uid = message.from_user.id
    if not is_admin(uid):
        return
    has_image  = bool(_social_settings.get("image_file_id"))
    enabled    = _social_settings.get("enabled", True)
    has_fb     = bool(FB_PAGE_TOKEN and FB_PAGE_ID)
    has_ig     = bool(IG_USER_ID and IMGBB_API_KEY)
    msg = (
        f"📊 *حالة السوشيال ميديا*\n\n"
        f"{'✅' if enabled else '⏸'} النشر: {'مفعّل' if enabled else 'موقوف'}\n"
        f"{'✅' if has_image else '❌'} صورة الغلاف: {'محددة' if has_image else 'غير محددة — أرسل /setsocial'}\n"
        f"{'✅' if has_fb else '❌'} فيسبوك: {'جاهز' if has_fb else 'يحتاج FB_PAGE_TOKEN + FB_PAGE_ID'}\n"
        f"{'✅' if has_ig else '❌'} انستغرام: {'جاهز' if has_ig else 'يحتاج IG_USER_ID + IMGBB_API_KEY'}\n"
        f"⏱ كل {SOCIAL_MIN_INTERVAL // 60} دقيقة بين منشور ومنشور"
    )
    bot.send_message(uid, msg, parse_mode="Markdown")

