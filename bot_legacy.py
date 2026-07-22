# -*- coding: utf-8 -*-
# bot_legacy.py — النواة الرئيسية (بعد التقسيم)
# -*- coding: utf-8 -*-
# ===== IRAQNOW BOT - PRODUCTION READY v4.0 - Self-Healing + Monitoring =====
# ─── UTF-8 Fix (أولاً قبل أي شيء) ───────────────────────────────────────────
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import telebot
from telebot import types
import requests
import feedparser
import atexit


# =============================================================================
# HEROKU FIX v4: Input Sanitization — strip HTML/injections from user text
# =============================================================================
import re as _re_san
# FIX: إضافة _re كاسم مستعار — يُصلح NameError في safe_send.py ودوال أخرى تستخدم _re
_re = _re_san
_HTML_TAG_RE = _re_san.compile(r'<[^>]{0,200}>', _re_san.DOTALL)
_CTRL_RE     = _re_san.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]')

# FIX: تعريف _SIGTERM_RECEIVED — كان مفقوداً وكان يُسبِّب NameError في utils.py/_safe_job
# يُضبط على True عند استقبال إشارة SIGTERM لمنع تشغيل مهام جديدة بعد الإيقاف
_SIGTERM_RECEIVED: bool = False

import logging
from logging.handlers import RotatingFileHandler
import datetime
import threading
import time
import sqlite3
import json
import os
import heapq as _heapq
import queue
import traceback
import signal as _signal
import concurrent.futures

from config import *
# Private config names not exported by star import
from config import _FF, _GEMINI_KEYS, _DS_GROQ_KEY, _DS_OPENROUTER_KEY, _DS_TOGETHER_KEY, _DS_MISTRAL_KEY, _DS_COHERE_KEY   # noqa: F401,F403 — BOT_TOKEN, ADMIN_ID, WEATHER_KEY, etc.

# ── مصدر الحالة المشتركة — state.py ──────────────────────────────────────────
import state as gl  # noqa: E402

# ── Logger ────────────────────────────────────────────────────────────────────
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE   = "%Y-%m-%d %H:%M:%S"
_logger = logging.getLogger("IraqNowBot")

# ── إنشاء نسخة البوت (لم تكن موجودة في الملفات المرفوعة أصلاً) ──────────────
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=True)
gl.bot     = bot
gl._logger = _logger

# ── صورة افتراضية (شعار الوكالة) لأي خبر بلا صورة من المصدر ─────────────────
DEFAULT_NEWS_IMAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "iraqnow_logo.png")
if not os.path.isfile(DEFAULT_NEWS_IMAGE):
    _logger.warning("⚠️ صورة الشعار الافتراضية غير موجودة: %s", DEFAULT_NEWS_IMAGE)
    DEFAULT_NEWS_IMAGE = None

# ── سجل الوحدات (Module Registry) — كان مفقوداً ─────────────────────────────
_module_registry: dict = {}
# FIX: كان _get_module_status و _restart_module يستخدمان _module_registry_lock
# دون أن يُعرَّف في أي مكان بالمشروع — أي استدعاء لهما كان يتوقف بـ NameError.
_module_registry_lock = threading.Lock()

# FIX: _AI_EXECUTOR مُعرَّف فعلياً في state.py لكن db_users.py يستورده بصيغة
# `from bot_legacy import _AI_EXECUTOR` صريحة (وليس عبر LOAD_GLOBAL داخل دالة)
# لذا لا يستطيع global_healer إصلاحه لاحقاً — يجب إعادة تصديره هنا صراحة قبل
# استيراد db_users.py.
_AI_EXECUTOR = gl._AI_EXECUTOR

# ── قفل وقاموس فحص صحة RSS (كانا مُعرَّفين فقط في ai_engine.py غير المُحمَّل) ──
_RSS_HEALTH_LOCK = threading.Lock()
_rss_health: dict = {}

# ── إنشاء المُجدوِل (كان مفقوداً أيضاً) ──────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler(timezone="Asia/Baghdad")
gl.scheduler = scheduler

# ── تتبع الأخبار المُرسَلة عالمياً (news_tracker.py كانت وحدة يتيمة لم تُستورد) ──
_GLOBAL_SENT_TTL  = 6 * 3600  # 6 ساعات
_GLOBAL_SENT_FILE = "global_sent_news.json"

def _load_global_sent_news():
    global _global_sent_news
    _global_sent_news = {}
    try:
        if not os.path.exists(_GLOBAL_SENT_FILE):
            return
        with open(_GLOBAL_SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        now = time.time()
        loaded = {}
        for lang, val in data.items():
            if isinstance(val, dict):
                loaded[lang] = {lnk: ts for lnk, ts in val.items() if (now - ts) < _GLOBAL_SENT_TTL}
        _global_sent_news = loaded
    except Exception as _e:
        _logger.warning(f"فشل تحميل global_sent_news: {_e}")
        _global_sent_news = {}

def _save_global_sent_news():
    try:
        now = time.time()
        data = {}
        for lang, val in _global_sent_news.items():
            if isinstance(val, dict):
                active = {lnk: ts for lnk, ts in val.items() if (now - ts) < _GLOBAL_SENT_TTL}
                if active:
                    data[lang] = active
        with open(_GLOBAL_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as _exc:
        _log_exc(_exc)

_load_global_sent_news()

def _start_thread_once(name: str, target, **kwargs):
    """يُطلق thread فقط إذا لم يكن هناك thread بنفس الاسم حياً."""
    import threading as _th_chk
    existing = {t.name for t in _th_chk.enumerate() if t.is_alive()}
    if name in existing:
        _logger.debug("⏭ Thread '%s' موجود — تخطي", name)
        return None
    t = _th_chk.Thread(target=target, daemon=True, name=name, **kwargs)
    t.start()
    return t

# ─── استيراد الوحدات المُقسَّمة ───
# FIX (RESTRUCTURE): هذه الوحدات كانت في الأصل جزءاً من ملف واحد (نفس مساحة
# الأسماء العالمية). عند تقسيمها لملفات مستقلة بقيت تستخدم متغيرات ودوال
# بعضها البعض بدون استيراد صريح، مما يُسبب NameError عند التشغيل كوحدات
# Python عادية. الحل: تنفيذ كل ملف مباشرة داخل مساحة أسماء bot_legacy
# (بدل import عادي) لاستعادة نموذج "المساحة المشتركة" الذي كُتب الكود لأجله.
import importlib.util as _ilu_merge

def _merge_module_into_globals(_modname):
    _spec = _ilu_merge.find_spec(_modname)
    if _spec is None or _spec.origin is None:
        raise ImportError(f"لم يتم العثور على الوحدة: {_modname}")
    with open(_spec.origin, "r", encoding="utf-8") as _f:
        _src = _f.read()
    _code = compile(_src, _spec.origin, "exec")
    _this_mod_name = __name__  # FIX: احفظه قبل التنفيذ — بعض الملفات المدموجة
    # (مثل rss_cache.py عبر db._export_all_to) تكتب فوق __name__ في مساحة
    # الأسماء المشتركة، مما يُفسد اسم الوحدة الحالية إذا قُرئ بعد exec.
    exec(_code, globals())
    globals()["__name__"] = _this_mod_name  # استعادة القيمة الصحيحة دائماً
    import sys as _sys_merge
    _sys_merge.modules.setdefault(_modname, _sys_merge.modules.get(_this_mod_name))

for _merged_mod in (
    "bot_helpers", "bot_persistence", "bot_finance",
    "bot_scheduled_jobs", "bot_prayers_weather",
    "data_localization", "data_rss", "data_ui",
    "data_interests", "data_translations", "data_assets",
):
    _merge_module_into_globals(_merged_mod)

gl._log_exc = _log_exc

def _db_save_user(uid, info):
    # FIX-THREAD: cursor محلي لكل استدعاء — يمنع "Recursive use of cursors not allowed"
    # عند الوصول من أكثر من thread في نفس الوقت
    try:
        with _db_lock:
            _cur = _db_conn.cursor()
            _cur.execute(
                "INSERT OR REPLACE INTO users_store (uid, data) VALUES (?, ?)",
                (str(uid), json.dumps(info, ensure_ascii=False))
            )
            _db_conn.commit()
    except Exception as _e:
        try: _db_conn.rollback()
        except Exception: pass
        _log_exc(_e, "_db_save_user")

def _db_save_all_users(users_dict):
    # FIX-THREAD: cursor محلي لكل استدعاء — يمنع "Recursive use of cursors not allowed"
    # عند الوصول من أكثر من thread في نفس الوقت (Scheduler + SIGTERM handler)
    try:
        with _db_lock:
            _cur = _db_conn.cursor()
            for _uid, _info in list(users_dict.items()):
                _cur.execute(
                    "INSERT OR REPLACE INTO users_store (uid, data) VALUES (?, ?)",
                    (str(_uid), json.dumps(_info, ensure_ascii=False))
                )
            _db_conn.commit()
    except Exception as _e:
        try: _db_conn.rollback()
        except Exception: pass
        _log_exc(_e, "_db_save_all_users")

def _db_load_users():
    """FIX: كانت مُستدعاة من db_users.py لكن لم تكن مُعرَّفة في أي مكان،
    مما يعني أن المستخدمين لم يُستعادوا من SQLite أبداً بعد إعادة التشغيل.
    FIX-THREAD: cursor محلي لضمان أمان الـ threads."""
    try:
        with _db_lock:
            _rows = _db_conn.execute("SELECT uid, data FROM users_store").fetchall()
        _result = {}
        for _uid, _data in _rows:
            try:
                _result[_uid] = json.loads(_data)
            except Exception:
                pass
        return _result
    except Exception as _e:
        _log_exc(_e, "_db_load_users")
        return {}

# FIX: users تُحمَّل من ملف JSON (لا يُكتَب إليه أبداً) — بينما الحفظ الدوري
# يذهب فعلياً إلى SQLite (users_store). لذا نُدمِج بيانات SQLite هنا لضمان
# بقاء المستخدمين بعد إعادة تشغيل الخدمة.
try:
    _sqlite_users = _db_load_users()
    if _sqlite_users:
        users.update(_sqlite_users)
        _logger.info("✅ استُعيد %d مستخدم من SQLite", len(_sqlite_users))
except Exception as _e:
    _log_exc(_e, "_db_load_users_startup_merge")

# ── القنوات والمجموعات ────────────────────────────────────────────────────────
# FIX: هذه الدوال كانت مُستدعاة من admin_panel.py و db_channels.py وغيرهما
#      لكنها لم تكن مُعرَّفة في أي مكان في الكود (سقطت أثناء تقسيم الملف الأصلي).
#      لا يوجد جدول SQLite مخصص للقنوات (فقط users_store) — لذلك نعتمد على نفس
#      آلية ملف JSON المستخدمة أصلاً كـ fallback (CHANNELS_FILE) لتبسيط الحل.
def _db_load_channels():
    try:
        return load_json(CHANNELS_FILE, [])
    except Exception as _e:
        _log_exc(_e, "_db_load_channels")
        return []

def _db_save_all_channels(channels_data):
    try:
        save_json(CHANNELS_FILE, channels_data)
    except Exception as _e:
        _log_exc(_e, "_db_save_all_channels")

def _migrate_channels_from_json():
    """لا حاجة لهجرة فعلية — القنوات تُخزَّن مباشرة في JSON. موجودة فقط
    لأن admin_panel.py يستدعيها عند التحميل."""
    pass

# ── Send queue worker ─────────────────────────────────────────────────────────

def _send_queue_worker():
    while True:
        try:
            _cid, _txt, _kw = _send_queue.get(timeout=1)
            try:
                bot.send_message(_cid, _txt, **_kw)
            except Exception as _e:
                _log_exc(_e, "_send_queue_worker")
            _send_queue.task_done()
        except queue.Empty:
            pass
        except Exception:
            pass

# ── SIGTERM handler ───────────────────────────────────────────────────────────
def _handle_sigterm(signum, frame):
    global _SIGTERM_RECEIVED
    _SIGTERM_RECEIVED = True
    gl._SIGTERM_RECEIVED = True  # مزامنة state
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass

# ── Security audit ────────────────────────────────────────────────────────────
try:
    from config import security_audit as _sec_audit
    _sec_audit()
except Exception:
    pass

# ── Button caches persistence stubs ──────────────────────────────────────────
def _save_all_button_caches():
    pass  # caches are in-memory only in this build




def _start_thread_once(name: str, target, **kwargs):
    """يُطلق thread فقط إذا لم يكن هناك thread بنفس الاسم حياً."""
    import threading as _th_chk
    existing = {t.name for t in _th_chk.enumerate() if t.is_alive()}
    if name in existing:
        _logger.debug("⏭ Thread '%s' موجود — تخطي", name)
        return None
    t = _th_chk.Thread(target=target, daemon=True, name=name, **kwargs)
    t.start()
    return t

_logger.setLevel(logging.DEBUG)

# Handler للملف (5MB × 3 نسخ احتياطية)
try:
    _fh = RotatingFileHandler(
        "iraqnow_bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    _fh.setLevel(logging.INFO)
    _fh.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE))
    _logger.addHandler(_fh)
except Exception as _exc:
    _log_exc(_exc)

# Handler للكونسول
_ch = logging.StreamHandler(sys.stdout)
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE))
_logger.addHandler(_ch)

# منع تضاعف رسائل الـ logging من telebot


logging.getLogger("TeleBot").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

_logger.info("🚀 IraqNow Bot v4.0 — بدء التشغيل")

# ─── توقيت السعودية (UTC+3) ──────────────────────────────────────
_SA_TZ_OFFSET = datetime.timedelta(hours=3)

# FIX: تعريف _now_sa و _sa_str هنا (يستخدمهما bot_legacy نفسه والوحدات الأخرى)

# ======== قائمة الأدمن المتعددين ========
extra_admins = load_json(ADMINS_FILE, [])
extra_admins = [int(a) for a in extra_admins]
ADMINS = [ADMIN_ID] + extra_admins


def save_welcome_override():
    save_json(WELCOME_FILE, {"override": welcome_override})

# ======== رابط التواصل ========
CONTACT_LINK = "https://t.me/Ilovedaddyandmommybot"

# ======== تلميحات الاستخدام بعد اختيار اللغة/الدولة ========
USAGE_HINTS = {
    "العربية 🇮🇶": (
        "💡 *طريقة الاستخدام:*\n\n"
        "📰 اضغط *آخر الأخبار* لأحدث الأخبار\n"
        "⚽ اضغط *أخبار الرياضة* لأخبار الملاعب\n"
        "🌤 اضغط *الطقس الآن* لحالة الطقس\n"
        "🕌 اضغط *أوقات الصلاة* لمواقيت الصلاة\n"
        "💱 اضغط *أسعار العملات* لأسعار الصرف\n"
        "💎 اضغط *العملات الرقمية* لأسعار الكريبتو\n"
        "🔍 اضغط *بحث* للبحث السريع في الأخبار\n"
        "🧠 اضغط *بحث عميق* لتحليل أي موضوع بالذكاء الاصطناعي\n"
        "📋 اضغط *ملخص أخبار اليوم* لأبرز أخبار اليوم\n"
        "🔔 اضغط *الإشعارات* لتفعيل/إيقاف التنبيهات\n"
        "🔄 اضغط *الإعدادات* لتغيير اللغة أو البلد"
    ),
    "English 🇬🇧": (
        "💡 *How to use:*\n\n"
        "📰 Tap *Latest News* for top stories\n"
        "⚽ Tap *Sports News* for sports updates\n"
        "🌤 Tap *Weather Now* for weather\n"
        "🕌 Tap *Prayer Times* for daily prayer schedule\n"
        "💱 Tap *Currency Rates* for exchange rates\n"
        "💎 Tap *Crypto* for cryptocurrency prices\n"
        "🔍 Tap *Search* for quick news search\n"
        "🧠 Tap *AI Deep Search* for in-depth AI analysis\n"
        "📋 Tap *Daily Summary* for today's top stories\n"
        "🔔 Tap *Notifications* to toggle alerts\n"
        "🔄 Tap *Settings* to change language or country"
    ),
    "Русский 🇷🇺": (
        "💡 *Как использовать:*\n\n"
        "📰 Нажмите *Новости* для свежих новостей\n"
        "⚽ Нажмите *Спорт* для спортивных новостей\n"
        "🌤 Нажмите *Погода* для погоды\n"
        "🕌 Нажмите *Время молитвы* для расписания\n"
        "💱 Нажмите *Курсы валют* для курсов обмена\n"
        "💎 Нажмите *Крипто* для цен криптовалют\n"
        "🔍 Нажмите *Поиск* для поиска новостей\n"
        "🧠 Нажмите *Глубокий поиск* для анализа ИИ\n"
        "📋 Нажмите *Сводка дня* для главных новостей\n"
        "🔔 Нажмите *Уведомления* для управления оповещениями\n"
        "🔄 Нажмите *Настройки* для смены языка или страны"
    ),
    "فارسی 🇮🇷": (
        "💡 *نحوه استفاده:*\n\n"
        "📰 روی *اخبار* بزنید برای آخرین خبرها\n"
        "⚽ روی *اخبار ورزشی* بزنید\n"
        "🌤 روی *آبوهوا* بزنید برای وضعیت هوا\n"
        "🕌 روی *اوقات نماز* بزنید\n"
        "💱 روی *نرخ ارز* بزنید\n"
        "💎 روی *ارزهای دیجیتال* بزنید\n"
        "🔍 روی *جستجو* بزنید برای جستجوی سریع\n"
        "🧠 روی *جستجوی عمیق* بزنید برای تحلیل هوش مصنوعی\n"
        "📋 روی *خلاصه روز* بزنید\n"
        "🔔 روی *اعلانها* بزنید برای مدیریت اطلاعرسانی\n"
        "🔄 روی *تنظیمات* بزنید برای تغییر زبان یا کشور"
    ),
    "हिन्दी 🇮🇳": (
        "💡 *उपयोग कैसे करें:*\n\n"
        "📰 खबरों के लिए *ताज़ा खबरें* दबाएं\n"
        "⚽ खेल खबरों के लिए *खेल समाचार* दबाएं\n"
        "🌤 मौसम के लिए *मौसम अभी* दबाएं\n"
        "🕌 नमाज़ के समय के लिए *नमाज़ का समय* दबाएं\n"
        "💱 विनिमय दर के लिए *मुद्रा दरें* दबाएं\n"
        "💎 क्रिप्टो के लिए *क्रिप्टो* दबाएं\n"
        "🔍 त्वरित खोज के लिए *खोज* दबाएं\n"
        "🧠 AI विश्लेषण के लिए *डीप सर्च* दबाएं\n"
        "📋 दिन की खबरों के लिए *दैनिक सारांश* दबाएं\n"
        "🔔 अलर्ट के लिए *सूचनाएं* दबाएं\n"
        "🔄 भाषा बदलने के लिए *सेटिंग्स* दबाएं"
    ),
    "Português 🇧🇷": (
        "💡 *Como usar:*\n\n"
        "📰 Toque em *Notícias* para as últimas notícias\n"
        "⚽ Toque em *Esportes* para notícias esportivas\n"
        "🌤 Toque em *Clima* para o tempo atual\n"
        "🕌 Toque em *Horários de Oração* para os horários\n"
        "💱 Toque em *Câmbio* para taxas de câmbio\n"
        "💎 Toque em *Cripto* para preços de criptomoedas\n"
        "🔍 Toque em *Buscar* para pesquisa rápida\n"
        "🧠 Toque em *Busca Profunda* para análise de IA\n"
        "📋 Toque em *Resumo do Dia* para as principais notícias\n"
        "🔔 Toque em *Notificações* para gerenciar alertas\n"
        "🔄 Toque em *Configurações* para mudar idioma ou país"
    ),
    "Türkçe 🇹🇷": (
        "💡 *Nasıl kullanılır:*\n\n"
        "📰 Haberler için *Son haberler* düğmesine basın\n"
        "⚽ Spor için *Spor haberleri* düğmesine basın\n"
        "🌤 Hava durumu için *Hava durumu* düğmesine basın\n"
        "🕌 Namaz vakitleri için *Namaz vakitleri* düğmesine basın\n"
        "💱 Döviz için *Döviz kurları* düğmesine basın\n"
        "💎 Kripto için *Kripto* düğmesine basın\n"
        "🔍 Hızlı arama için *Ara* düğmesine basın\n"
        "🧠 Yapay zeka analizi için *Derin Arama* düğmesine basın\n"
        "📋 Günlük özet için *Günlük özet* düğmesine basın\n"
        "🔔 Bildirimler için *Bildirimler* düğmesine basın\n"
        "🔄 Dili değiştirmek için *Ayarlar* düğmesine basın"
    ),
    "اردو 🇵🇰": (
        "💡 *استعمال کا طریقہ:*\n\n"
        "📰 خبروں کے لیے *تازہ خبریں* دبائیں\n"
        "⚽ کھیلوں کے لیے *کھیل کی خبریں* دبائیں\n"
        "🌤 موسم کے لیے *موسم ابھی* دبائیں\n"
        "🕌 نماز کے اوقات کے لیے *نماز کے اوقات* دبائیں\n"
        "💱 کرنسی کے لیے *کرنسی ریٹ* دبائیں\n"
        "💎 کریپٹو کے لیے *کریپٹو* دبائیں\n"
        "🔍 فوری تلاش کے لیے *تلاش* دبائیں\n"
        "🧠 AI تجزیہ کے لیے *گہری تلاش* دبائیں\n"
        "📋 روزانہ خلاصے کے لیے *روزانہ خلاصہ* دبائیں\n"
        "🔔 الرٹ کے لیے *اطلاعات* دبائیں\n"
        "🔄 زبان تبدیل کرنے کے لیے *ترتیبات* دبائیں"
    ),
    "Deutsch 🇩🇪": (
        "💡 *Anleitung:*\n\n"
        "📰 Tippen Sie auf *Nachrichten* für aktuelle Nachrichten\n"
        "⚽ Tippen Sie auf *Sport* für Sportnachrichten\n"
        "🌤 Tippen Sie auf *Wetter* für das aktuelle Wetter\n"
        "🕌 Tippen Sie auf *Gebetszeiten* für den Zeitplan\n"
        "💱 Tippen Sie auf *Wechselkurse* für Wechselkurse\n"
        "💎 Tippen Sie auf *Krypto* für Kryptowährungspreise\n"
        "🔍 Tippen Sie auf *Suchen* für die schnelle Suche\n"
        "🧠 Tippen Sie auf *Deep Search* für KI-Analyse\n"
        "📋 Tippen Sie auf *Tagesübersicht* für die besten Nachrichten\n"
        "🔔 Tippen Sie auf *Benachrichtigungen* für Alarme\n"
        "🔄 Tippen Sie auf *Einstellungen* für Sprache oder Land"
    ),
    "Українська 🇺🇦": (
        "💡 *Як користуватись:*\n\n"
        "📰 Натисніть *Новини* для останніх новин\n"
        "⚽ Натисніть *Спорт* для спортивних новин\n"
        "🌤 Натисніть *Погода* для перегляду погоди\n"
        "🕌 Натисніть *Час молитви* для розкладу\n"
        "💱 Натисніть *Курси валют* для курсів обміну\n"
        "💎 Натисніть *Крипто* для цін криптовалют\n"
        "🔍 Натисніть *Пошук* для швидкого пошуку\n"
        "🧠 Натисніть *Глибокий пошук* для аналізу ШІ\n"
        "📋 Натисніть *Зведення дня* для головних новин\n"
        "🔔 Натисніть *Сповіщення* для керування оповіщеннями\n"
        "🔄 Натисніть *Налаштування* для зміни мови або країни"
    ),
    "Italiano 🇮🇹": (
        "💡 *Come usare:*\n\n"
        "📰 Tocca *Notizie* per le ultime notizie\n"
        "⚽ Tocca *Sport* per le notizie sportive\n"
        "🌤 Tocca *Meteo* per il meteo attuale\n"
        "🕌 Tocca *Orari di preghiera* per gli orari\n"
        "💱 Tocca *Tassi di cambio* per i cambi valuta\n"
        "💎 Tocca *Cripto* per i prezzi delle criptovalute\n"
        "🔍 Tocca *Cerca* per la ricerca rapida\n"
        "🧠 Tocca *Ricerca profonda* per l'analisi AI\n"
        "📋 Tocca *Riepilogo del giorno* per le principali notizie\n"
        "🔔 Tocca *Notifiche* per gestire gli avvisi\n"
        "🔄 Tocca *Impostazioni* per cambiare lingua o paese"
    ),
    "Español 🇲🇽": (
        "💡 *Cómo usar:*\n\n"
        "📰 Toca *Noticias* para las últimas noticias\n"
        "⚽ Toca *Deportes* para noticias deportivas\n"
        "🌤 Toca *Clima* para el tiempo actual\n"
        "🕌 Toca *Horarios de oración* para el horario\n"
        "💱 Toca *Tipos de cambio* para tasas de cambio\n"
        "💎 Toca *Cripto* para precios de criptomonedas\n"
        "🔍 Toca *Buscar* para búsqueda rápida\n"
        "🧠 Toca *Búsqueda profunda* para análisis de IA\n"
        "📋 Toca *Resumen del día* para las principales noticias\n"
        "🔔 Toca *Notificaciones* para gestionar alertas\n"
        "🔄 Toca *Configuración* para cambiar idioma o país"
    ),
    "Français 🇫🇷": (
        "💡 *Comment utiliser :*\n\n"
        "📰 Appuie sur *Dernières nouvelles* pour l'actualité\n"
        "⚽ Appuie sur *Sports* pour les résultats sportifs\n"
        "🌤 Appuie sur *Météo* pour la météo actuelle\n"
        "🕌 Appuie sur *Heures de prière* pour les horaires\n"
        "💱 Appuie sur *Taux de change* pour les devises\n"
        "💎 Appuie sur *Crypto* pour les cryptomonnaies\n"
        "🔍 Appuie sur *Rechercher* pour chercher rapidement\n"
        "🧠 Appuie sur *Recherche approfondie* pour l'analyse IA\n"
        "📋 Appuie sur *Résumé du jour* pour les principales nouvelles\n"
        "🔔 Appuie sur *Notifications* pour gérer les alertes\n"
        "🔄 Appuie sur *Paramètres* pour changer la langue ou le pays"
    ),
}

# ======== اللغات ========
languages = {
    "Arabic": "العربية 🇮🇶",
    "English": "English 🇬🇧",
    "Russian": "Русский 🇷🇺",
    "Farsi": "فارسی 🇮🇷",
    "Hindi": "हिन्दी 🇮🇳",
    "Portuguese": "Português 🇧🇷",
    "Turkish": "Türkçe 🇹🇷",
    "Urdu": "اردو 🇵🇰",
    "German": "Deutsch 🇩🇪",
    "Ukrainian": "Українська 🇺🇦",
    "Italian": "Italiano 🇮🇹",
    "Spanish": "Español 🇲🇽",
    "French": "Français 🇫🇷",
}


# ======= بيانات اللغة والمناطق، RSS، الأزرار، الاهتمامات، الترجمات =======
# (تم دمجها بالفعل أعلى الملف عبر _merge_module_into_globals)




# ======== cache مؤقت لملخصات الأخبار ========
import hashlib
# FIX-8: TTLCache بدل dict — يمنع تراكم الملخصات في الذاكرة إلى الأبد
try:
    from cachetools import TTLCache as _TTLCache_bl
    _news_summary_cache = _TTLCache_bl(maxsize=1000, ttl=7200)  # ساعتين
except ImportError:
    _news_summary_cache = {}   # fallback
_why_key_cache: dict   = {}   # key → {title, summary}  للزر "لماذا يهمك؟"
_next_key_cache: dict  = {}   # key → {title, summary}  للزر "ماذا بعد؟"
_intel_key_cache: dict = {}   # key → {title, summary}  للزر "تقرير ذكي"
_ctx_key_cache: dict   = {}   # key → {title, summary}  للزر "السياق التاريخي"
_bm_key_cache:  dict   = {}   # key → {title, link, source}  للزر 🔖
_duel_key_cache: dict  = {}   # key → {title, summary}  للزر ⚔️ AI Duel
_dna_key_cache:  dict  = {}   # key → {title, summary}  للزر 🧬 DNA
_pred_key_cache: dict  = {}   # key → title  للزر "🔮 توقع المستقبل"
_disc_key_cache: dict  = {}   # key → {title, summary, link}  للزر "🤝 ناقش"
_tts_art_cache:  dict  = {}   # key → {title, summary}  للزر "🎧 اسمع"
_crisis_tracker: dict  = {}   # title_key → {sources, first_seen, notified, count, title}

# ═══════════════════════════════════════════════════════════════════
# قاموس ترجمات الميزات الجديدة — كل لغة مدعومة بالكامل
# ═══════════════════════════════════════════════════════════════════
_NEW_FEAT_I18N = {
    # ─── أزرار ─────────────────────────────────────────────────────
    "btn_pred": {
        "العربية 🇮🇶": "🔮 توقع المستقبل",
        "English 🇬🇧":  "🔮 Future Prediction",
        "Русский 🇷🇺":  "🔮 Прогноз событий",
        "فارسی 🇮🇷":    "🔮 پیش‌بینی آینده",
        "हिन्दी 🇮🇳":   "🔮 भविष्य की भविष्यवाणी",
        "Português 🇧🇷": "🔮 Previsão do Futuro",
        "Türkçe 🇹🇷":   "🔮 Geleceği Tahmin Et",
        "اردو 🇵🇰":     "🔮 مستقبل کی پیش گوئی",
        "Deutsch 🇩🇪":  "🔮 Zukunftsprognose",
        "Українська 🇺🇦": "🔮 Прогноз подій",
        "Italiano 🇮🇹": "🔮 Previsione del Futuro",
        "Español 🇲🇽":  "🔮 Predicción del Futuro",
        "Français 🇫🇷": "🔮 Prédiction du Futur",
    },
    "btn_tts": {
        "العربية 🇮🇶": "🎧 اسمع الخبر",
        "English 🇬🇧":  "🎧 Listen to News",
        "Русский 🇷🇺":  "🎧 Слушать новость",
        "فارسی 🇮🇷":    "🎧 گوش بده",
        "हिन्दी 🇮🇳":   "🎧 खबर सुनें",
        "Português 🇧🇷": "🎧 Ouvir a Notícia",
        "Türkçe 🇹🇷":   "🎧 Haberi Dinle",
        "اردو 🇵🇰":     "🎧 خبر سنیں",
        "Deutsch 🇩🇪":  "🎧 Nachricht anhören",
        "Українська 🇺🇦": "🎧 Слухати новину",
        "Italiano 🇮🇹": "🎧 Ascolta la Notizia",
        "Español 🇲🇽":  "🎧 Escuchar Noticia",
        "Français 🇫🇷": "🎧 Écouter la Nouvelle",
    },
    "btn_disc": {
        "العربية 🇮🇶": "🤝 ناقش مع صديق",
        "English 🇬🇧":  "🤝 Discuss with Friend",
        "Русский 🇷🇺":  "🤝 Обсудить с другом",
        "فارسی 🇮🇷":    "🤝 با دوست بحث کن",
        "हिन्दी 🇮🇳":   "🤝 दोस्त से चर्चा करें",
        "Português 🇧🇷": "🤝 Discutir com Amigo",
        "Türkçe 🇹🇷":   "🤝 Arkadaşınla Tartış",
        "اردو 🇵🇰":     "🤝 دوست سے بات کریں",
        "Deutsch 🇩🇪":  "🤝 Mit Freund diskutieren",
        "Українська 🇺🇦": "🤝 Обговорити з другом",
        "Italiano 🇮🇹": "🤝 Discuti con un Amico",
        "Español 🇲🇽":  "🤝 Discutir con Amigo",
        "Français 🇫🇷": "🤝 Discuter avec un Ami",
    },
    # ─── رسائل انتظار handlers ───────────────────────────────────────
    "pred_wait": {
        "العربية 🇮🇶": "🔮 يحلل البوت الأنماط ويرسم صورة المستقبل...",
        "English 🇬🇧":  "🔮 Analyzing patterns and predicting future events...",
        "Русский 🇷🇺":  "🔮 Анализирую события и составляю прогноз...",
        "فارسی 🇮🇷":    "🔮 در حال تحلیل الگوها و پیش‌بینی آینده...",
        "हिन्दी 🇮🇳":   "🔮 पैटर्न विश्लेषण और भविष्यवाणी जारी है...",
        "Português 🇧🇷": "🔮 Analisando padrões e prevendo o futuro...",
        "Türkçe 🇹🇷":   "🔮 Kalıpları analiz edip geleceği tahmin ediyor...",
        "اردو 🇵🇰":     "🔮 نمونوں کا تجزیہ اور مستقبل کی پیش گوئی...",
        "Deutsch 🇩🇪":  "🔮 Muster werden analysiert und Prognose erstellt...",
        "Українська 🇺🇦": "🔮 Аналізую події та складаю прогноз...",
        "Italiano 🇮🇹": "🔮 Analisi dei pattern e previsione del futuro...",
        "Español 🇲🇽":  "🔮 Analizando patrones y prediciendo el futuro...",
        "Français 🇫🇷": "🔮 Analyse des tendances et prédiction de l'avenir...",
    },
    "pred_header": {
        "العربية 🇮🇶": "🔮 *توقع المستقبل*\n━━━━━━━━━━━━━━━━━━\n",
        "English 🇬🇧":  "🔮 *Future Prediction*\n━━━━━━━━━━━━━━━━━━\n",
        "Русский 🇷🇺":  "🔮 *Прогноз событий*\n━━━━━━━━━━━━━━━━━━\n",
        "فارسی 🇮🇷":    "🔮 *پیش‌بینی آینده*\n━━━━━━━━━━━━━━━━━━\n",
        "हिन्दी 🇮🇳":   "🔮 *भविष्यवाणी*\n━━━━━━━━━━━━━━━━━━\n",
        "Português 🇧🇷": "🔮 *Previsão do Futuro*\n━━━━━━━━━━━━━━━━━━\n",
        "Türkçe 🇹🇷":   "🔮 *Gelecek Tahmini*\n━━━━━━━━━━━━━━━━━━\n",
        "اردو 🇵🇰":     "🔮 *مستقبل کی پیش گوئی*\n━━━━━━━━━━━━━━━━━━\n",
        "Deutsch 🇩🇪":  "🔮 *Zukunftsprognose*\n━━━━━━━━━━━━━━━━━━\n",
        "Українська 🇺🇦": "🔮 *Прогноз майбутнього*\n━━━━━━━━━━━━━━━━━━\n",
        "Italiano 🇮🇹": "🔮 *Previsione del Futuro*\n━━━━━━━━━━━━━━━━━━\n",
        "Español 🇲🇽":  "🔮 *Predicción del Futuro*\n━━━━━━━━━━━━━━━━━━\n",
        "Français 🇫🇷": "🔮 *Prédiction du Futur*\n━━━━━━━━━━━━━━━━━━\n",
    },
    "pred_news_label": {
        "العربية 🇮🇶": "📰 الخبر",
        "English 🇬🇧":  "📰 News",
        "Русский 🇷🇺":  "📰 Новость",
        "فارسی 🇮🇷":    "📰 خبر",
        "हिन्दी 🇮🇳":   "📰 खबर",
        "Português 🇧🇷": "📰 Notícia",
        "Türkçe 🇹🇷":   "📰 Haber",
        "اردو 🇵🇰":     "📰 خبر",
        "Deutsch 🇩🇪":  "📰 Nachricht",
        "Українська 🇺🇦": "📰 Новина",
        "Italiano 🇮🇹": "📰 Notizia",
        "Español 🇲🇽":  "📰 Noticia",
        "Français 🇫🇷": "📰 Actualité",
    },
    "pred_expired": {
        "العربية 🇮🇶": "🔄 أُعيد تشغيل البوت — الزر لم يعد صالحاً. اطلب الخبر من جديد.",
        "English 🇬🇧":  "🔄 Bot was restarted — this button is no longer valid. Request the news again.",
        "Русский 🇷🇺":  "⚠️ Срок кнопки истёк, откройте новость заново.",
        "فارسی 🇮🇷":    "⚠️ این دکمه منقضی شده، خبر را دوباره باز کنید.",
        "हिन्दी 🇮🇳":   "⚠️ यह बटन समाप्त हो गया, कृपया खबर फिर खोलें।",
        "Português 🇧🇷": "⚠️ Botão expirado, por favor reabra a notícia.",
        "Türkçe 🇹🇷":   "⚠️ Bu düğme süresi doldu, haberi yeniden açın.",
        "اردو 🇵🇰":     "⚠️ یہ بٹن ختم ہوگیا، خبر دوبارہ کھولیں۔",
        "Deutsch 🇩🇪":  "⚠️ Schaltfläche abgelaufen, Nachricht erneut öffnen.",
        "Українська 🇺🇦": "⚠️ Термін кнопки минув, відкрийте новину знову.",
        "Italiano 🇮🇹": "⚠️ Pulsante scaduto, riapri la notizia.",
        "Español 🇲🇽":  "⚠️ Botón expirado, vuelve a abrir la noticia.",
        "Français 🇫🇷": "⚠️ Bouton expiré, rouvrez la nouvelle.",
    },
    # ─── TTS messages ────────────────────────────────────────────────
    "tts_wait": {
        "العربية 🇮🇶": "🎧 جاري تحويل الخبر إلى صوت...",
        "English 🇬🇧":  "🎧 Converting news to audio...",
        "Русский 🇷🇺":  "🎧 Преобразование новости в аудио...",
        "فارسی 🇮🇷":    "🎧 در حال تبدیل خبر به صوت...",
        "हिन्दी 🇮🇳":   "🎧 खबर को ऑडियो में बदला जा रहा है...",
        "Português 🇧🇷": "🎧 Convertendo notícia em áudio...",
        "Türkçe 🇹🇷":   "🎧 Haber sese dönüştürülüyor...",
        "اردو 🇵🇰":     "🎧 خبر کو آڈیو میں تبدیل کیا جا رہا ہے...",
        "Deutsch 🇩🇪":  "🎧 Nachricht wird in Audio umgewandelt...",
        "Українська 🇺🇦": "🎧 Перетворення новини на аудіо...",
        "Italiano 🇮🇹": "🎧 Conversione notizia in audio...",
        "Español 🇲🇽":  "🎧 Convirtiendo noticia a audio...",
        "Français 🇫🇷": "🎧 Conversion de la nouvelle en audio...",
    },
    "tts_error": {
        "العربية 🇮🇶": "⚠️ تعذّر تحويل الخبر لصوت، حاول مرة أخرى.",
        "English 🇬🇧":  "⚠️ Could not convert to audio, please try again.",
        "Русский 🇷🇺":  "⚠️ Не удалось преобразовать в аудио, попробуйте ещё раз.",
        "فارسی 🇮🇷":    "⚠️ تبدیل به صوت ممکن نشد، دوباره امتحان کنید.",
        "हिन्दी 🇮🇳":   "⚠️ ऑडियो में बदलाव नहीं हो सका, पुनः प्रयास करें।",
        "Português 🇧🇷": "⚠️ Não foi possível converter para áudio, tente novamente.",
        "Türkçe 🇹🇷":   "⚠️ Sese dönüştürülemedi, lütfen tekrar deneyin.",
        "اردو 🇵🇰":     "⚠️ آڈیو میں تبدیل نہیں ہو سکا، دوبارہ کوشش کریں۔",
        "Deutsch 🇩🇪":  "⚠️ Konvertierung fehlgeschlagen, bitte erneut versuchen.",
        "Українська 🇺🇦": "⚠️ Не вдалося перетворити на аудіо, спробуйте знову.",
        "Italiano 🇮🇹": "⚠️ Impossibile convertire in audio, riprova.",
        "Español 🇲🇽":  "⚠️ No se pudo convertir a audio, inténtalo de nuevo.",
        "Français 🇫🇷": "⚠️ Impossible de convertir en audio, réessayez.",
    },
    # ─── TTS lang codes (gTTS) ─────────────────────────────────────────
    "tts_lang_code": {
        "العربية 🇮🇶": "ar",
        "English 🇬🇧":  "en",
        "Русский 🇷🇺":  "ru",
        "فارسی 🇮🇷":    "fa",
        "हिन्दी 🇮🇳":   "hi",
        "Português 🇧🇷": "pt",
        "Türkçe 🇹🇷":   "tr",
        "اردو 🇵🇰":     "ur",
        "Deutsch 🇩🇪":  "de",
        "Українська 🇺🇦": "uk",
        "Italiano 🇮🇹": "it",
        "Español 🇲🇽":  "es",
        "Français 🇫🇷": "fr",
    },
    "tts_caption_prefix": {
        "العربية 🇮🇶": "🎧 خبر صوتي",
        "English 🇬🇧":  "🎧 Audio News",
        "Русский 🇷🇺":  "🎧 Аудионовость",
        "فارسی 🇮🇷":    "🎧 خبر صوتی",
        "हिन्दी 🇮🇳":   "🎧 ऑडियो समाचार",
        "Português 🇧🇷": "🎧 Notícia em Áudio",
        "Türkçe 🇹🇷":   "🎧 Sesli Haber",
        "اردو 🇵🇰":     "🎧 آڈیو خبر",
        "Deutsch 🇩🇪":  "🎧 Audio-Nachricht",
        "Українська 🇺🇦": "🎧 Аудіоновина",
        "Italiano 🇮🇹": "🎧 Notizia Audio",
        "Español 🇲🇽":  "🎧 Noticia en Audio",
        "Français 🇫🇷": "🎧 Nouvelle Audio",
    },
    # ─── Discussion messages ─────────────────────────────────────────────
    "disc_header": {
        "العربية 🇮🇶": "🤝 *بطاقة النقاش*\nشارك هذا الخبر وابدأ حواراً مثمراً:",
        "English 🇬🇧":  "🤝 *Discussion Card*\nShare this news and start a meaningful conversation:",
        "Русский 🇷🇺":  "🤝 *Карточка обсуждения*\nПоделитесь новостью и начните разговор:",
        "فارسی 🇮🇷":    "🤝 *کارت بحث*\nاین خبر را به اشتراک بگذارید:",
        "हिन्दी 🇮🇳":   "🤝 *चर्चा कार्ड*\nयह खबर साझा करें और बातचीत शुरू करें:",
        "Português 🇧🇷": "🤝 *Cartão de Discussão*\nCompartilhe esta notícia e inicie uma conversa:",
        "Türkçe 🇹🇷":   "🤝 *Tartışma Kartı*\nBu haberi paylaş ve sohbet başlat:",
        "اردو 🇵🇰":     "🤝 *گفتگو کارڈ*\nیہ خبر شیئر کریں اور گفتگو شروع کریں:",
        "Deutsch 🇩🇪":  "🤝 *Diskussionskarte*\nTeile diese Nachricht und beginne ein Gespräch:",
        "Українська 🇺🇦": "🤝 *Картка обговорення*\nПоділіться новиною та почніть розмову:",
        "Italiano 🇮🇹": "🤝 *Scheda Discussione*\nCondividi questa notizia e inizia una conversazione:",
        "Español 🇲🇽":  "🤝 *Tarjeta de Discusión*\nComparte esta noticia e inicia una conversación:",
        "Français 🇫🇷": "🤝 *Carte de Discussion*\nPartagez cette actualité et lancez une conversation:",
    },
    "disc_tag": {
        "العربية 🇮🇶": "💬 _شاركه مع أصدقائك لتبادل الآراء!_",
        "English 🇬🇧":  "💬 _Share with friends to exchange ideas!_",
        "Русский 🇷🇺":  "💬 _Поделитесь с друзьями и обменяйтесь мнениями!_",
        "فارسی 🇮🇷":    "💬 _با دوستان به اشتراک بگذارید!_",
        "हिन्दी 🇮🇳":   "💬 _दोस्तों के साथ साझा करें!_",
        "Português 🇧🇷": "💬 _Compartilhe com amigos e troque ideias!_",
        "Türkçe 🇹🇷":   "💬 _Arkadaşlarınla paylaş ve fikir alışverişi yap!_",
        "اردو 🇵🇰":     "💬 _دوستوں کے ساتھ شیئر کریں!_",
        "Deutsch 🇩🇪":  "💬 _Mit Freunden teilen und Meinungen austauschen!_",
        "Українська 🇺🇦": "💬 _Поділіться з друзями та обміняйтеся думками!_",
        "Italiano 🇮🇹": "💬 _Condividi con gli amici e scambia opinioni!_",
        "Español 🇲🇽":  "💬 _¡Comparte con amigos e intercambia ideas!_",
        "Français 🇫🇷": "💬 _Partagez avec vos amis et échangez vos idées!_",
    },
    "disc_send_btn": {
        "العربية 🇮🇶": "📤 أرسل لصديق",
        "English 🇬🇧":  "📤 Send to a Friend",
        "Русский 🇷🇺":  "📤 Отправить другу",
        "فارسی 🇮🇷":    "📤 برای دوست بفرست",
        "हिन्दी 🇮🇳":   "📤 दोस्त को भेजें",
        "Português 🇧🇷": "📤 Enviar para um Amigo",
        "Türkçe 🇹🇷":   "📤 Arkadaşına Gönder",
        "اردو 🇵🇰":     "📤 دوست کو بھیجیں",
        "Deutsch 🇩🇪":  "📤 An Freund senden",
        "Українська 🇺🇦": "📤 Надіслати другу",
        "Italiano 🇮🇹": "📤 Invia a un Amico",
        "Español 🇲🇽":  "📤 Enviar a un Amigo",
        "Français 🇫🇷": "📤 Envoyer à un Ami",
    },
    "disc_invite_btn": {
        "العربية 🇮🇶": "🤖 دعوة لـ InsightX",
        "English 🇬🇧":  "🤖 Invite to InsightX",
        "Русский 🇷🇺":  "🤖 Пригласить в InsightX",
        "فارسی 🇮🇷":    "🤖 دعوت به InsightX",
        "हिन्दी 🇮🇳":   "🤖 InsightX में आमंत्रित करें",
        "Português 🇧🇷": "🤖 Convidar para InsightX",
        "Türkçe 🇹🇷":   "🤖 InsightX'e Davet Et",
        "اردو 🇵🇰":     "🤖 InsightX پر مدعو کریں",
        "Deutsch 🇩🇪":  "🤖 Zu InsightX einladen",
        "Українська 🇺🇦": "🤖 Запросити до InsightX",
        "Italiano 🇮🇹": "🤖 Invita su InsightX",
        "Español 🇲🇽":  "🤖 Invitar a InsightX",
        "Français 🇫🇷": "🤖 Inviter sur InsightX",
    },
    # ─── Map command messages ─────────────────────────────────────────
    "map_loading": {
        "العربية 🇮🇶": "🗺️ يحضّر خريطة العراق الحية...",
        "English 🇬🇧":  "🗺️ Loading Iraq Live Map...",
        "Русский 🇷🇺":  "🗺️ Загружаю карту Ирака...",
        "فارسی 🇮🇷":    "🗺️ نقشه عراق در حال بارگذاری...",
        "हिन्दी 🇮🇳":   "🗺️ इराक मानचित्र लोड हो रहा है...",
        "Português 🇧🇷": "🗺️ Carregando mapa ao vivo do Iraque...",
        "Türkçe 🇹🇷":   "🗺️ Irak canlı haritası yükleniyor...",
        "اردو 🇵🇰":     "🗺️ عراق کا نقشہ لوڈ ہو رہا ہے...",
        "Deutsch 🇩🇪":  "🗺️ Irak-Live-Karte wird geladen...",
        "Українська 🇺🇦": "🗺️ Завантаження карти Іраку...",
        "Italiano 🇮🇹": "🗺️ Caricamento mappa in diretta dell'Iraq...",
        "Español 🇲🇽":  "🗺️ Cargando mapa en vivo de Iraq...",
        "Français 🇫🇷": "🗺️ Chargement de la carte en direct de l'Irak...",
    },
    "map_error": {
        "العربية 🇮🇶": "⚠️ تعذّر تحميل الخريطة، حاول مرة أخرى لاحقاً.",
        "English 🇬🇧":  "⚠️ Could not load the map, please try again later.",
        "Русский 🇷🇺":  "⚠️ Не удалось загрузить карту, попробуйте позже.",
        "فارسی 🇮🇷":    "⚠️ بارگذاری نقشه ممکن نشد، بعداً تلاش کنید.",
        "हिन्दी 🇮🇳":   "⚠️ मानचित्र लोड नहीं हो सका, बाद में पुनः प्रयास करें।",
        "Português 🇧🇷": "⚠️ Não foi possível carregar o mapa, tente mais tarde.",
        "Türkçe 🇹🇷":   "⚠️ Harita yüklenemedi, daha sonra tekrar deneyin.",
        "اردو 🇵🇰":     "⚠️ نقشہ لوڈ نہیں ہو سکا، بعد میں کوشش کریں۔",
        "Deutsch 🇩🇪":  "⚠️ Karte konnte nicht geladen werden, bitte später erneut.",
        "Українська 🇺🇦": "⚠️ Карту не вдалося завантажити, спробуйте пізніше.",
        "Italiano 🇮🇹": "⚠️ Impossibile caricare la mappa, riprova più tardi.",
        "Español 🇲🇽":  "⚠️ No se pudo cargar el mapa, inténtalo más tarde.",
        "Français 🇫🇷": "⚠️ Impossible de charger la carte, réessayez plus tard.",
    },
    "map_refresh_btn": {
        "العربية 🇮🇶": "🔄 تحديث الخريطة",
        "English 🇬🇧":  "🔄 Refresh Map",
        "Русский 🇷🇺":  "🔄 Обновить карту",
        "فارسی 🇮🇷":    "🔄 به‌روزرسانی نقشه",
        "हिन्दी 🇮🇳":   "🔄 मानचित्र रीफ्रेश करें",
        "Português 🇧🇷": "🔄 Atualizar Mapa",
        "Türkçe 🇹🇷":   "🔄 Haritayı Güncelle",
        "اردو 🇵🇰":     "🔄 نقشہ تازہ کریں",
        "Deutsch 🇩🇪":  "🔄 Karte aktualisieren",
        "Українська 🇺🇦": "🔄 Оновити карту",
        "Italiano 🇮🇹": "🔄 Aggiorna mappa",
        "Español 🇲🇽":  "🔄 Actualizar mapa",
        "Français 🇫🇷": "🔄 Actualiser la carte",
    },
    "map_refresh_toast": {
        "العربية 🇮🇶": "🔄 يحدّث الخريطة...",
        "English 🇬🇧":  "🔄 Refreshing map...",
        "Русский 🇷🇺":  "🔄 Обновляю карту...",
        "فارسی 🇮🇷":    "🔄 در حال به‌روزرسانی نقشه...",
        "हिन्दी 🇮🇳":   "🔄 मानचित्र अपडेट हो रहा है...",
        "Português 🇧🇷": "🔄 Atualizando mapa...",
        "Türkçe 🇹🇷":   "🔄 Harita güncelleniyor...",
        "اردو 🇵🇰":     "🔄 نقشہ اپڈیٹ ہو رہا ہے...",
        "Deutsch 🇩🇪":  "🔄 Karte wird aktualisiert...",
        "Українська 🇺🇦": "🔄 Оновлення карти...",
        "Italiano 🇮🇹": "🔄 Aggiornamento mappa...",
        "Español 🇲🇽":  "🔄 Actualizando mapa...",
        "Français 🇫🇷": "🔄 Mise à jour de la carte...",
    },
    "map_title": {
        "العربية 🇮🇶": "🗺️ *خريطة العراق الحية — توزيع الأخبار*",
        "English 🇬🇧":  "🗺️ *Iraq Live Map — News Distribution*",
        "Русский 🇷🇺":  "🗺️ *Карта Ирака — распределение новостей*",
        "فارسی 🇮🇷":    "🗺️ *نقشه زنده عراق — توزیع اخبار*",
        "हिन्दी 🇮🇳":   "🗺️ *इराक लाइव मैप — समाचार वितरण*",
        "Português 🇧🇷": "🗺️ *Mapa ao Vivo do Iraque — Distribuição de Notícias*",
        "Türkçe 🇹🇷":   "🗺️ *Irak Canlı Haritası — Haber Dağılımı*",
        "اردو 🇵🇰":     "🗺️ *عراق کا زندہ نقشہ — خبروں کی تقسیم*",
        "Deutsch 🇩🇪":  "🗺️ *Irak Live-Karte — Nachrichtenverteilung*",
        "Українська 🇺🇦": "🗺️ *Жива карта Іраку — розподіл новин*",
        "Italiano 🇮🇹": "🗺️ *Mappa in Diretta dell'Iraq — Distribuzione Notizie*",
        "Español 🇲🇽":  "🗺️ *Mapa en Vivo de Iraq — Distribución de Noticias*",
        "Français 🇫🇷": "🗺️ *Carte en Direct de l'Irak — Distribution des Nouvelles*",
    },
    "map_quiet": {
        "العربية 🇮🇶": "هادئة",
        "English 🇬🇧": "Quiet",
        "Русский 🇷🇺": "Тихо",
        "فارسی 🇮🇷":   "آرام",
        "हिन्दी 🇮🇳":  "शांत",
        "Português 🇧🇷": "Calmo",
        "Türkçe 🇹🇷":  "Sakin",
        "اردو 🇵🇰":    "پُرسکون",
        "Deutsch 🇩🇪": "Ruhig",
        "Українська 🇺🇦": "Спокійно",
        "Italiano 🇮🇹": "Tranquillo",
        "Español 🇲🇽":  "Tranquilo",
        "Français 🇫🇷": "Calme",
    },
    "map_1news": {
        "العربية 🇮🇶": "خبر واحد",
        "English 🇬🇧": "1 news item",
        "Русский 🇷🇺": "1 новость",
        "فارسی 🇮🇷":   "یک خبر",
        "हिन्दी 🇮🇳":  "1 खबर",
        "Português 🇧🇷": "1 notícia",
        "Türkçe 🇹🇷":  "1 haber",
        "اردو 🇵🇰":    "1 خبر",
        "Deutsch 🇩🇪": "1 Meldung",
        "Українська 🇺🇦": "1 новина",
        "Italiano 🇮🇹": "1 notizia",
        "Español 🇲🇽":  "1 noticia",
        "Français 🇫🇷": "1 actualité",
    },
    "map_news_count": {
        "العربية 🇮🇶": "{n} أخبار",
        "English 🇬🇧": "{n} news items",
        "Русский 🇷🇺": "{n} новостей",
        "فارسی 🇮🇷":   "{n} خبر",
        "हिन्दी 🇮🇳":  "{n} खबरें",
        "Português 🇧🇷": "{n} notícias",
        "Türkçe 🇹🇷":  "{n} haber",
        "اردو 🇵🇰":    "{n} خبریں",
        "Deutsch 🇩🇪": "{n} Meldungen",
        "Українська 🇺🇦": "{n} новин",
        "Italiano 🇮🇹": "{n} notizie",
        "Español 🇲🇽":  "{n} noticias",
        "Français 🇫🇷": "{n} actualités",
    },
    "map_active_news": {
        "العربية 🇮🇶": "{n} أخبار نشطة",
        "English 🇬🇧": "{n} active news",
        "Русский 🇷🇺": "{n} активных новостей",
        "فارسی 🇮🇷":   "{n} خبر فعال",
        "हिन्दी 🇮🇳":  "{n} सक्रिय खबरें",
        "Português 🇧🇷": "{n} notícias ativas",
        "Türkçe 🇹🇷":  "{n} aktif haber",
        "اردو 🇵🇰":    "{n} فعال خبریں",
        "Deutsch 🇩🇪": "{n} aktive Meldungen",
        "Українська 🇺🇦": "{n} активних новин",
        "Italiano 🇮🇹": "{n} notizie attive",
        "Español 🇲🇽":  "{n} noticias activas",
        "Français 🇫🇷": "{n} actualités actives",
    },
    "map_last_update": {
        "العربية 🇮🇶": "🕐 آخر تحديث",
        "English 🇬🇧":  "🕐 Last update",
        "Русский 🇷🇺":  "🕐 Последнее обновление",
        "فارسی 🇮🇷":    "🕐 آخرین بروزرسانی",
        "हिन्दी 🇮🇳":   "🕐 अंतिम अपडेट",
        "Português 🇧🇷": "🕐 Última atualização",
        "Türkçe 🇹🇷":   "🕐 Son güncelleme",
        "اردو 🇵🇰":     "🕐 آخری اپڈیٹ",
        "Deutsch 🇩🇪":  "🕐 Letztes Update",
        "Українська 🇺🇦": "🕐 Останнє оновлення",
        "Italiano 🇮🇹": "🕐 Ultimo aggiornamento",
        "Español 🇲🇽":  "🕐 Última actualización",
        "Français 🇫🇷": "🕐 Dernière mise à jour",
    },
    # ─── Crisis radar messages ──────────────────────────────────────
    "crisis_alert_header": {
        "العربية 🇮🇶": "🚨🚨 *تنبيه رادار الأزمات* 🚨🚨",
        "English 🇬🇧":  "🚨🚨 *Crisis Radar Alert* 🚨🚨",
        "Русский 🇷🇺":  "🚨🚨 *Тревога радара кризисов* 🚨🚨",
        "فارسی 🇮🇷":    "🚨🚨 *هشدار رادار بحران* 🚨🚨",
        "हिन्दी 🇮🇳":   "🚨🚨 *संकट रडार अलर्ट* 🚨🚨",
        "Português 🇧🇷": "🚨🚨 *Alerta do Radar de Crise* 🚨🚨",
        "Türkçe 🇹🇷":   "🚨🚨 *Kriz Radar Uyarısı* 🚨🚨",
        "اردو 🇵🇰":     "🚨🚨 *بحران رادار الرٹ* 🚨🚨",
        "Deutsch 🇩🇪":  "🚨🚨 *Krisen-Radar-Alarm* 🚨🚨",
        "Українська 🇺🇦": "🚨🚨 *Тривога радару криз* 🚨🚨",
        "Italiano 🇮🇹": "🚨🚨 *Allerta Radar Crisi* 🚨🚨",
        "Español 🇲🇽":  "🚨🚨 *Alerta del Radar de Crisis* 🚨🚨",
        "Français 🇫🇷": "🚨🚨 *Alerte Radar de Crise* 🚨🚨",
    },
    "crisis_severity_label": {
        "العربية 🇮🇶": "📊 الحدة",
        "English 🇬🇧":  "📊 Severity",
        "Русский 🇷🇺":  "📊 Серьёзность",
        "فارسی 🇮🇷":    "📊 شدت",
        "हिन्दी 🇮🇳":   "📊 गंभीरता",
        "Português 🇧🇷": "📊 Gravidade",
        "Türkçe 🇹🇷":   "📊 Şiddet",
        "اردو 🇵🇰":     "📊 شدت",
        "Deutsch 🇩🇪":  "📊 Schweregrad",
        "Українська 🇺🇦": "📊 Серйозність",
        "Italiano 🇮🇹": "📰 Gravità",
        "Español 🇲🇽":  "📊 Gravedad",
        "Français 🇫🇷": "📊 Gravité",
    },
    "crisis_related_news": {
        "العربية 🇮🇶": "📰 الأخبار المرتبطة",
        "English 🇬🇧":  "📰 Related news",
        "Русский 🇷🇺":  "📰 Связанных новостей",
        "فارسی 🇮🇷":    "📰 اخبار مرتبط",
        "हिन्दी 🇮🇳":   "📰 संबंधित खबरें",
        "Português 🇧🇷": "📰 Notícias relacionadas",
        "Türkçe 🇹🇷":   "📰 İlgili haberler",
        "اردو 🇵🇰":     "📰 متعلقہ خبریں",
        "Deutsch 🇩🇪":  "📰 Verwandte Meldungen",
        "Українська 🇺🇦": "📰 Пов'язаних новин",
        "Italiano 🇮🇹": "📰 Notizie correlate",
        "Español 🇲🇽":  "📰 Noticias relacionadas",
        "Français 🇫🇷": "📰 Actualités connexes",
    },
    "crisis_in_hour": {
        "العربية 🇮🇶": "خبر خلال ساعة",
        "English 🇬🇧":  "items in the last hour",
        "Русский 🇷🇺":  "новостей за час",
        "فارسی 🇮🇷":    "خبر در یک ساعت",
        "हिन्दी 🇮🇳":   "एक घंटे में खबरें",
        "Português 🇧🇷": "itens na última hora",
        "Türkçe 🇹🇷":   "son bir saatte haber",
        "اردو 🇵🇰":     "ایک گھنٹے میں خبریں",
        "Deutsch 🇩🇪":  "Meldungen in der letzten Stunde",
        "Українська 🇺🇦": "новин за годину",
        "Italiano 🇮🇹": "notizie nell'ultima ora",
        "Español 🇲🇽":  "noticias en la última hora",
        "Français 🇫🇷": "actualités dans la dernière heure",
    },
    "crisis_last_news": {
        "العربية 🇮🇶": "⚡ آخر خبر",
        "English 🇬🇧":  "⚡ Latest",
        "Русский 🇷🇺":  "⚡ Последняя",
        "فارسی 🇮🇷":    "⚡ آخرین خبر",
        "हिन्दी 🇮🇳":   "⚡ ताज़ा खबर",
        "Português 🇧🇷": "⚡ Última notícia",
        "Türkçe 🇹🇷":   "⚡ Son haber",
        "اردو 🇵🇰":     "⚡ آخری خبر",
        "Deutsch 🇩🇪":  "⚡ Neueste Meldung",
        "Українська 🇺🇦": "⚡ Остання новина",
        "Italiano 🇮🇹": "⚡ Ultima notizia",
        "Español 🇲🇽":  "⚡ Última noticia",
        "Français 🇫🇷": "⚡ Dernière actualité",
    },
    "crisis_footer": {
        "العربية 🇮🇶": "⚠️ _رادار الأزمات رصد نشاطاً متصاعداً!_",
        "English 🇬🇧":  "⚠️ _Crisis Radar detected escalating activity!_",
        "Русский 🇷🇺":  "⚠️ _Радар кризисов обнаружил нарастающую активность!_",
        "فارسی 🇮🇷":    "⚠️ _رادار بحران فعالیت رو به افزایش شناسایی کرد!_",
        "हिन्दी 🇮🇳":   "⚠️ _संकट रडार ने बढ़ती गतिविधि का पता लगाया!_",
        "Português 🇧🇷": "⚠️ _O Radar de Crise detectou atividade crescente!_",
        "Türkçe 🇹🇷":   "⚠️ _Kriz Radarı artan aktivite tespit etti!_",
        "اردو 🇵🇰":     "⚠️ _کرائسز ریڈار نے بڑھتی سرگرمی کا پتہ لگایا!_",
        "Deutsch 🇩🇪":  "⚠️ _Krisen-Radar erkannte eskalierende Aktivität!_",
        "Українська 🇺🇦": "⚠️ _Радар криз виявив зростаючу активність!_",
        "Italiano 🇮🇹": "⚠️ _Il Radar Crisi ha rilevato un'attività crescente!_",
        "Español 🇲🇽":  "⚠️ _¡El Radar de Crisis detectó actividad creciente!_",
        "Français 🇫🇷": "⚠️ _Le Radar de Crise a détecté une activité croissante!_",
    },
}

_CRISIS_THRESHOLD = 3          # عدد المصادر اللي يطلق رادار الأزمات
_CRISIS_WINDOW    = 15 * 60    # 15 دقيقة
# HEROKU FIX: restore button caches from SQLite on startup

def send_weekly_summary_text(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    feeds = RSS.get(lang, [])
    if not feeds:
        bot.send_message(uid, t(lang, "no_source"))
        return
    bot.send_message(uid, t(lang, "weekly_summary_text_wait"))
    headlines = []
    seen_titles = set()
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for feed_url in feeds[:6]:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:8]:
                title = getattr(entry, "title", "").strip()
                if not title or title in seen_titles:
                    continue
                pub = getattr(entry, "published_parsed", None)
                if pub:
                    try:
                        pub_dt = datetime.datetime(*pub[:6])
                        if pub_dt < cutoff:
                            continue
                    except Exception as _exc:
                        _log_exc(_exc)
                seen_titles.add(title)
                headlines.append(title)
                if len(headlines) >= 25:
                    break
        except Exception:
            continue
        if len(headlines) >= 25:
            break
    if not headlines:
        bot.send_message(uid, t(lang, "no_weekly"))
        return
    week_start = (_now_sa() - datetime.timedelta(days=6)).strftime("%d/%m")
    week_end = _now_sa().strftime("%d/%m/%Y")
    lines = [t(lang, "weekly_summary_text_header").format(start=week_start, end=week_end)]
    for i, title in enumerate(headlines, 1):
        lines.append(f"{i}. {title}")
    lines.append(t(lang, "public_stats_footer").format(username=BOT_USERNAME))
    full_msg = "\n".join(lines)
    if len(full_msg) > 4000:
        full_msg = full_msg[:3990] + "\n..."
    bot.send_message(uid, full_msg, parse_mode="Markdown")

# ======== تتبع العملات والأسهم والسلع والمؤشرات ========

# ======= بيانات الأصول المالية (تم دمجها أعلى الملف) =======




def _ml(lang, key):
    return _MENU_LABELS.get(lang, _MENU_LABELS["English 🇬🇧"]).get(key, key)

def _build_main_menu(lang):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"news"),    callback_data="menu_news"),
        types.InlineKeyboardButton(_ml(lang,"deep"),    callback_data="menu_deep"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai"),      callback_data="menu_ai"),
        types.InlineKeyboardButton(_ml(lang,"sports"),  callback_data="menu_sports"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"weather"), callback_data="menu_weather"),
        types.InlineKeyboardButton(_ml(lang,"markets"), callback_data="menu_markets"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"settings"),callback_data="menu_settings"),
        types.InlineKeyboardButton(_ml(lang,"help"),    callback_data="menu_help"),
    )
    kb.add(
        types.InlineKeyboardButton("🔖 محفوظاتي",      callback_data="menu_saved"),
        types.InlineKeyboardButton("🎁 دعوة أصدقاء",  callback_data="menu_referral"),
    )
    kb.add(
        types.InlineKeyboardButton("🌅 الملخص الصباحي", callback_data="menu_digest"),
    )
    return kb

def _build_ai_menu(lang):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai_verify"),   callback_data="aimenu_verify"),
        types.InlineKeyboardButton(_ml(lang,"ai_analyze"),  callback_data="aimenu_analyze"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai_compare"),  callback_data="aimenu_compare"),
        types.InlineKeyboardButton(_ml(lang,"ai_timeline"), callback_data="aimenu_timeline"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai_predict"),  callback_data="aimenu_predict"),
        types.InlineKeyboardButton(_ml(lang,"ai_influence"),callback_data="aimenu_influence"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai_profile"),  callback_data="aimenu_profile"),
        types.InlineKeyboardButton(_ml(lang,"ai_ask"),      callback_data="aimenu_ask"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"ai_parliament"),callback_data="aimenu_parliament"),
        types.InlineKeyboardButton(_ml(lang,"ai_econ"),     callback_data="aimenu_econ"),
    )
    kb.add(
        types.InlineKeyboardButton(_ml(lang,"live"),        callback_data="aimenu_live"),
        types.InlineKeyboardButton(_ml(lang,"submit"),      callback_data="aimenu_submit"),
    )
    kb.add(types.InlineKeyboardButton(_ml(lang,"back"), callback_data="menu_main"))
    return kb

def _cleanup_caches():
    """تنظيف الكاشات القديمة لمنع memory leaks."""
    try:
        # AI cache
        with _AI_CACHE_LOCK:
            if len(_AI_CACHE) > 800:
                for k in list(_AI_CACHE.keys())[:300]:
                    _AI_CACHE.pop(k, None)
        # AI summary cache
        with _AI_SUMMARY_LOCK:
            if len(_AI_SUMMARY_CACHE) > 500:
                for k in list(_AI_SUMMARY_CACHE.keys())[:200]:
                    _AI_SUMMARY_CACHE.pop(k, None)
        # Alert count (تنظيف الدقائق القديمة)
        now_min = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with _alert_lock:
            old = [k for k in _alert_count if k != now_min]
            for k in old:
                _alert_count.pop(k, None)
        # BUG-14 FIX: تشذيب _global_rss_cache — حد 30 خبر لكل feed
        try:
            _MAX_RSS_PER_FEED = 30
            with _global_rss_cache_lock:
                for _feed_url in list(_global_rss_cache.keys()):
                    _entries, _ts = _global_rss_cache[_feed_url]
                    if len(_entries) > _MAX_RSS_PER_FEED:
                        _global_rss_cache[_feed_url] = (_entries[-_MAX_RSS_PER_FEED:], _ts)
        except Exception as _rss_prune_exc:
            _logger.debug("rss_cache prune: %s", _rss_prune_exc)
        
        # HEROKU FIX v4: Prune per-user sent_news (cap 500 per user)
        try:
            _PER_USER_SENT_CAP = 2000
            _now_prune = time.time()
            for _uid, _uinfo in _safe_users_snapshot():
                _sn = _uinfo.get("sent_news")
                if isinstance(_sn, (set, list)):
                    # حوّل البنية القديمة لـ dict
                    fake_ts = _now_prune - (_USER_SENT_TTL / 2)
                    _uinfo["sent_news"] = {lnk: fake_ts for lnk in _sn}
                elif isinstance(_sn, dict) and len(_sn) > _PER_USER_SENT_CAP:
                    # احذف المنتهية الصلاحية أولاً
                    _uinfo["sent_news"] = {
                        lnk: ts for lnk, ts in _sn.items()
                        if (_now_prune - ts) < _USER_SENT_TTL
                    }
        except Exception as _pe:
            _logger.debug("sent_news prune error: %s", _pe)
        # HEROKU FIX v4: Cap global_sent_news per language at 50 000
        try:
            _GLOBAL_SENT_CAP = 50000
            _now_cap = time.time()
            for _lang, _gset in list(_global_sent_news.items()):
                if not isinstance(_gset, dict):
                    _global_sent_news[_lang] = {}
                    continue
                if len(_gset) > _GLOBAL_SENT_CAP:
                    # FIX: was set(list(_gset)[-_GLOBAL_SENT_CAP:]) which converts
                    # {link:timestamp} dict to a plain set, breaking all TTL lookups.
                    # Correct: keep newest entries as dict, sorted by timestamp.
                    sorted_items = sorted(_gset.items(), key=lambda kv: kv[1])
                    trimmed = sorted_items[-_GLOBAL_SENT_CAP:]
                    _global_sent_news[_lang] = dict(trimmed)
        except Exception as _ge:
            _logger.debug("global_sent_news cap error: %s", _ge)
        # HEROKU FIX v4: Prune title_seen_cache (evict older than 24h)
        try:
            _now_ts_c = time.time()
            with _title_seen_lock:
                _stale_titles = [k for k, (t, _) in _title_seen_cache.items()
                                 if _now_ts_c - t > _TITLE_DEDUP_TTL]
                for k in _stale_titles:
                    _title_seen_cache.pop(k, None)
        except Exception as _exc:
            _log_exc(_exc)
        # تنظيف _rss_etag_store — احتفظ بآخر 300 feed فقط
        try:
            with _rss_etag_lock:
                if len(_rss_etag_store) > 300:
                    overflow = len(_rss_etag_store) - 300
                    for _k in list(_rss_etag_store.keys())[:overflow]:
                        _rss_etag_store.pop(_k, None)
        except Exception as _exc:
            _logger.debug("rss_etag_store prune error: %s", _exc)
        _logger.info("🧹 تنظيف الكاش تم بنجاح")
    except Exception as e:
        _logger.warning(f"cleanup_caches خطأ: {e}")

scheduler.add_job(_safe_job(_cleanup_caches), 'interval', hours=1, id="cache_cleanup_job", max_instances=1, coalesce=True)
# broadcast_weather أُزيلت من الجدولة — تُرسل عند طلب المستخدم فقط
scheduler.start()

def _bounded_scheduler_shutdown(timeout=10):
    # FIX: ينتظر اكتمال المهام الجارية (wait=True) بحد أقصى `timeout` ثانية
    # عبر thread منفصل بدل قطعها فوراً بـ wait=False.
    _t = threading.Thread(target=lambda: scheduler.shutdown(wait=True), daemon=True)
    _t.start()
    _t.join(timeout)

atexit.register(_bounded_scheduler_shutdown)
atexit.register(_save_global_sent_news)
atexit.register(lambda: _save_all_button_caches())  # HEROKU FIX v3: persist button caches on exit
atexit.register(lambda: _db_save_all_users(users))  # HEROKU FIX v3: persist users on exit
# FIX: _handle_sigterm مُعرَّفة في security.py لكنها تُستخدَم هنا قبل استيراده.
# الحل: نُعرِّف نسخة بديلة محلية الآن، وتُستبدَل لاحقاً عند استيراد security.py
def _handle_sigterm(signum, frame):  # noqa: F811 — يُستبدَل بنسخة security.py لاحقاً
    global _SIGTERM_RECEIVED
    if _SIGTERM_RECEIVED:
        return
    _SIGTERM_RECEIVED = True
    gl._SIGTERM_RECEIVED = True  # مزامنة state
    try:
        _logger.warning("⚠️ SIGTERM — حفظ الحالة والخروج...")
    except Exception:
        pass
    try:
        _save_global_sent_news()
    except Exception:
        pass
    try:
        _db_save_all_users(users)
    except Exception:
        pass
    try:
        _save_all_button_caches()
    except Exception:
        pass
    try:
        with _db_lock:
            _db_conn.commit()
    except Exception:
        pass

try:
    _signal.signal(_signal.SIGTERM, _handle_sigterm)
except (OSError, ValueError, AttributeError):
    pass  # في بيئات بعض الـ threads لا يمكن تسجيل SIGTERM
_logger.info("✅ Scheduler بدأ بنجاح — كل المهام المجدولة نشطة")

# ── تسجيل الوحدات الحرجة في Module Registry لإتاحة /restartmod ─────────────
for _reg_name, _reg_fn_name in [
    ("rss_prefetcher", "_rss_prefetcher"),
    ("broadcast_news", "broadcast_news"),
    ("system_health",  "_system_health_monitor"),
    ("dynamic_delay",  "_dynamic_delay_adjuster"),
]:
    _reg_fn = globals().get(_reg_fn_name)
    if _reg_fn:
        _register_module(_reg_name, _reg_fn)
_logger.info("📋 Module Registry: %d وحدة مسجّلة", len(_module_registry))

# ─── تحميل مسبق لفرق الدوريات الشهيرة في الخلفية عند الإطلاق ────
def is_chat_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

# ============================================================
# نظام الاكتشاف التلقائي للمصادر بالذكاء الاصطناعي
# يعمل كل 24 ساعة — يبحث بنفسه عن مصادر RSS لكل لغة في العالم
# ============================================================
_AI_DISCOVERED_RSS_FILE = "ai_discovered_rss.json"
_ai_discovered_log: dict = load_json(_AI_DISCOVERED_RSS_FILE, {})

def _do_addtrack(uid, symbol):
    existing = tracked_assets.get(str(uid), {}).get("assets", [])
    if symbol in existing:
        bot.send_message(uid, f"📌 *{symbol}* مضافة مسبقاً في قائمة التتبع.", parse_mode="Markdown")
        return
    if len(existing) >= 20:
        bot.send_message(uid, "⚠️ الحد الأقصى 20 أصل. استخدم /removetrack لحذف واحد.")
        return
    bot.send_message(uid, f"🔍 جارٍ التحقق من الرمز *{symbol}*...", parse_mode="Markdown")
    price = fetch_asset_price(symbol)
    if price is None:
        bot.send_message(uid, f"⚠️ لم يتم التعرف على الرمز *{symbol}*.\nتأكد من الرمز وأعد المحاولة، مثال: `BTC`، `AAPL`، `GC=F`", parse_mode="Markdown")
        return
    if str(uid) not in tracked_assets:
        tracked_assets[str(uid)] = {"assets": [], "last_prices": {}}
    tracked_assets[str(uid)]["assets"].append(symbol)
    tracked_assets[str(uid)]["last_prices"][symbol] = price
    save_tracked_assets()
    bot.send_message(uid,
        f"✅ تمت إضافة *{symbol}* للتتبع!\n"
        f"💰 السعر الحالي: `${price:,.4f}`\n\n"
        f"📋 /mytrack — لعرض قائمتك",
        parse_mode="Markdown"
    )

def _addtrack_step_cmd(message):
    uid = message.from_user.id
    if not message.text or message.text.startswith('/'):
        bot.send_message(uid, "⚠️ تم إلغاء إضافة الرمز. أرسل /addtrack للمحاولة مجدداً.")
        return
    symbol = message.text.strip().upper()
    _do_addtrack(uid, symbol)

@bot.message_handler(commands=["addtrack"])
def cmd_addtrack(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/addtrack")
    parts = m.text.strip().split()
    if len(parts) < 2:
        bot.send_message(uid,
            "➕ *إضافة رمز للتتبع*\n\n"
            "أرسل رمز الأصل الذي تريد تتبعه:\n\n"
            "🪙 عملات رقمية: `BTC`، `ETH`، `SOL`\n"
            "📈 أسهم: `AAPL`، `TSLA`، `NVDA`\n"
            "🥇 سلع: `GC=F` (ذهب)، `CL=F` (نفط)\n"
            "💱 عملات: `USD`، `EUR`، `GBP`",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler_by_chat_id(uid, _addtrack_step_cmd)
        return
    symbol = parts[1].upper()
    _do_addtrack(uid, symbol)

# ======== /addchannel ========
@bot.message_handler(commands=["discover"])
def cmd_discover(m):
    """
    أمر للأدمن: اكتشاف RSS تلقائياً من رابط موقع ويب وإضافته.
    الاستخدام: /discover <url> [اللغة]
    مثال:      /discover https://www.example-news.com العربية 🇮🇶
    """
    uid = m.from_user.id
    if not is_admin(uid):
        bot.send_message(uid, "❌ هذا الأمر للمشرفين فقط.")
        return
    parts = m.text.strip().split(None, 2)
    if len(parts) < 2:
        bot.send_message(uid,
            "🔍 *اكتشاف RSS تلقائياً*\n\n"
            "*الاستخدام:*\n"
            "`/discover <url> [اللغة]`\n\n"
            "*أمثلة:*\n"
            "`/discover https://www.example-news.com العربية 🇮🇶`\n"
            "`/discover https://www.bbc.com/arabic`\n\n"
            "سيحاول البوت اكتشاف رابط RSS للموقع تلقائياً وإضافته.",
            parse_mode="Markdown"
        )
        return
    url = parts[1].strip()
    lang = parts[2].strip() if len(parts) > 2 else "العربية 🇮🇶"
    # أقرب لغة
    matched_lang = None
    for l in RSS.keys():
        if lang in l or l.startswith(lang.split()[0]):
            matched_lang = l
            break
    if not matched_lang:
        matched_lang = lang
    status_msg = bot.send_message(uid,
        f"🔍 *أبحث عن مصدر RSS للموقع:*\n`{url}`\n\nانتظر...",
        parse_mode="Markdown"
    )
    discovered = _auto_discover_rss(url)
    if not discovered:
        bot.edit_message_text(
            f"❌ *لم أجد مصدر RSS للموقع:*\n`{url}`\n\n"
            "جربت الأنماط الشائعة ولم أجد شيئاً صالحاً.\n"
            "يمكنك إضافة الرابط مباشرة من لوحة الإدارة إذا كنت تعرفه.",
            uid, status_msg.message_id, parse_mode="Markdown"
        )
        return
    # أضف إلى RSS
    if matched_lang not in RSS:
        RSS[matched_lang] = []
    if discovered in RSS[matched_lang]:
        bot.edit_message_text(
            f"⚠️ *المصدر موجود مسبقاً:*\n`{discovered}`",
            uid, status_msg.message_id, parse_mode="Markdown"
        )
        return
    RSS[matched_lang].append(discovered)
    save_rss()
    diff = f"\n_(تم اكتشافه من: `{url}`)_" if discovered != url else ""
    bot.edit_message_text(
        f"✅ *تم اكتشاف وإضافة المصدر بنجاح!*\n\n"
        f"🔗 الرابط: `{discovered}`{diff}\n"
        f"🌐 اللغة: {matched_lang}\n"
        f"📡 إجمالي مصادر {matched_lang}: *{len(RSS[matched_lang])}*",
        uid, status_msg.message_id, parse_mode="Markdown"
    )


def _db_bloat_cleanup():
    """
    يُنظف قاعدة البيانات أسبوعياً:
    - يحذف sent_news القديم من المستخدمين الخاملين
    - يُرسل تقريراً للأدمن
    """
    while True:
        try:
            time.sleep(604800)   # أسبوع
            cutoff = time.time() - 90 * 86400   # 90 يوم
            cleaned = 0
            for uid_str, u in list(users.items()):
                last_active = u.get("last_active", 0)
                if isinstance(last_active, str):
                    try:
                        last_active = datetime.datetime.fromisoformat(last_active).timestamp()
                    except Exception:
                        last_active = 0
                if last_active and last_active < cutoff:
                    old_len = len(u.get("sent_news", {}))
                    u["sent_news"] = {}  # FIX: dict not list (TTL-based structure)
                    cleaned += old_len
            _db_save_all_users(users)  # FIX: was save_json→JSON; data lives in SQLite now
            try:
                adm = int(os.environ.get("ADMIN_ID", 0))
                if adm:
                    bot.send_message(adm,
                        f"🧹 *تنظيف أسبوعي:*\nحُذف {cleaned} سجل sent_news من الحسابات الخاملة (+90 يوم).",
                        parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
        except Exception as _exc:
            _log_exc(_exc)

_start_thread_once("DbbloatCleanup", _db_bloat_cleanup)


# ── 1d. Memory Pressure Auto-Guard ────────────────────────────────────────
def _memory_guard_loop():
    """يُراقب RAM كل 5 دقائق — ينظّف الكاشات عند الضغط."""
    try:
        import psutil
        _has_psutil = True
    except ImportError:
        _has_psutil = False

    while True:
        try:
            if _has_psutil:
                pct = psutil.virtual_memory().percent
                if pct >= 95:
                    # حرج — نظّف كل شيء
                    _WHY_MATTERS_CACHE.clear(); _WHAT_NEXT_CACHE.clear()
                    _IMPACT_CACHE.clear(); _CONTEXT_CACHE.clear()
                    _news_summary_cache.clear()
                    try:
                        adm = int(os.environ.get("ADMIN_ID", 0))
                        if adm:
                            bot.send_message(adm,
                                f"🚨 *Memory Guard:* RAM وصل {pct:.0f}% — تم تفريغ الكاشات.",
                                parse_mode="Markdown")
                    except Exception as _exc:
                        _log_exc(_exc)
                elif pct >= 85:
                    # تحذير — نظّف الأقل أهمية
                    _IMPACT_CACHE.clear(); _CONTEXT_CACHE.clear()
        except Exception as _exc:
            _log_exc(_exc)
        time.sleep(300)   # كل 5 دقائق

_start_thread_once("MemoryGuard", _memory_guard_loop)


# ── 1e. Source Credibility Scores ─────────────────────────────────────────
_SOURCE_CREDIBILITY: dict = {
    # مصادر عربية موثوقة
    "aljazeera":        92, "alarabiya":       88, "bbc":             95,
    "reuters":          97, "apnews":          96, "almayadeen":      70,
    "almada":           82, "azzaman":         80, "buratha":         65,
    "shafaq":           78, "rudaw":           80, "kirkuknow":       75,
    "iraqinews":        72, "ninawanews":      68, "ikhnews":         70,
    "alsumaria":        83, "alforat":         71, "mawazin":         69,
    "ankawa":           74, "nrtv":            76,
}

def _get_credibility(source_name: str) -> int:
    """يُعطي درجة موثوقية 0-100 للمصدر."""
    name = source_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    for key, score in _SOURCE_CREDIBILITY.items():
        if key in name:
            return score
    return 60   # افتراضي

def _credibility_badge(score: int) -> str:
    if score >= 90: return "🟢"
    if score >= 75: return "🟡"
    if score >= 60: return "🟠"
    return "🔴"


# ─────────────────────────────────────────────────────────────────────────
# §2  DATA STORES — مخازن البيانات للميزات الجديدة
# ─────────────────────────────────────────────────────────────────────────

# Bookmarks
_bookmarks: dict = {}          # {uid_str: [{"title","link","ts","source"}]}
_BOOKMARKS_FILE = "bookmarks.json"
try:
    import json as _json_bk
    if os.path.exists(_BOOKMARKS_FILE):
        with open(_BOOKMARKS_FILE, "r", encoding="utf-8") as _f:
            _bookmarks = _json_bk.load(_f)
        if not isinstance(_bookmarks, dict):
            _bookmarks = {}
except Exception:
    _bookmarks = {}


@bot.message_handler(commands=["schedule"])
def cmd_schedule(m):
    """
    /schedule — يعرض القائمة والأوامر
    /schedule add <HH:MM> <all|premium> <نص> — يُضيف بثاً مجدولاً لليوم
    /schedule list — القائمة الحالية
    /schedule del <رقم> — حذف
    """
    uid = m.from_user.id
    if not is_admin(uid): return
    parts = m.text.strip().split(None, 3)
    sep = "━━━━━━━━━━━━━━"

    if len(parts) == 1:
        bot.send_message(uid,
            f"🗓 *جدولة البث*\n{sep}\n\n"
            "أوامر:\n"
            "`/schedule add 14:30 all نص الرسالة` — بث لكل المستخدمين\n"
            "`/schedule add 20:00 premium نص` — بث للمميزين فقط\n"
            "`/schedule list` — قائمة المجدولة\n"
            "`/schedule del 1` — حذف البند رقم 1",
            parse_mode="Markdown")
        return

    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub == "list":
        if not _scheduled_bcasts:
            bot.send_message(uid, "📋 لا يوجد بث مجدول حالياً.")
            return
        lines = [f"🗓 *البث المجدول ({len(_scheduled_bcasts)}):*\n{sep}"]
        for i, b in enumerate(_scheduled_bcasts):
            t = datetime.datetime.fromtimestamp(b["scheduled_ts"]).strftime("%H:%M")
            lines.append(f"{i+1}. [{b['target']}] {t} — {b['text'][:50]}")
        bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")
        return

    if sub == "del":
        try:
            idx = int(parts[2]) - 1
            removed = _scheduled_bcasts.pop(idx)
            _save_scheduled()
            bot.send_message(uid, f"✅ تم حذف البث: _{removed['text'][:50]}_", parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, "⚠️ رقم غير صحيح.")
        return

    if sub == "add" and len(parts) >= 4:
        try:
            time_parts = parts[2].split(":")
            target_raw = parts[3].split(None, 1)
            target     = target_raw[0].lower()
            text       = target_raw[1] if len(target_raw) > 1 else ""
            if not text:
                bot.send_message(uid, "⚠️ الرسالة فارغة."); return
            h2, m2 = int(time_parts[0]), int(time_parts[1])
            now_dt  = datetime.datetime.now()
            sched   = now_dt.replace(hour=h2, minute=m2, second=0, microsecond=0)
            if sched < now_dt:
                sched += datetime.timedelta(days=1)
            _scheduled_bcasts.append({
                "text":         text,
                "target":       target if target in ("all","premium") else "all",
                "scheduled_ts": sched.timestamp(),
                "added_by":     uid,
            })
            _save_scheduled()
            bot.send_message(uid,
                f"✅ *تم جدولة البث:*\n"
                f"🕐 الوقت: `{sched.strftime('%Y-%m-%d %H:%M')}`\n"
                f"👥 الهدف: `{target}`\n"
                f"📝 النص: _{text[:80]}_",
                parse_mode="Markdown")
        except Exception as e:
            bot.send_message(uid, f"⚠️ خطأ: {e}\nمثال: `/schedule add 14:30 all نص الرسالة`")
        return

    bot.send_message(uid, "⚠️ أمر غير صحيح. أرسل `/schedule` للمساعدة.")


# ── /cleanup — تنظيف الحسابات المحظورة ──────────────────────────────────
def _save_sleep_hours(m):
    uid = m.from_user.id
    try:
        parts = m.text.strip().split()
        start = int(parts[0]) % 24
        end   = int(parts[1]) % 24
        uid_str = str(uid)
        _sleep_settings.setdefault(uid_str, {"enabled": True})
        _sleep_settings[uid_str]["start"] = start
        _sleep_settings[uid_str]["end"]   = end
        _sleep_settings[uid_str]["enabled"] = True
        _save_sleep()
        bot.send_message(uid,
            f"✅ *تم تعيين وضع الصمت:*\n"
            f"😴 من {start}:00 حتى {end}:00\n"
            f"الحالة: مُفعَّل",
            parse_mode="Markdown")
    except Exception:
        bot.send_message(uid, "⚠️ صيغة غير صحيحة. مثال: `23 7`")


# ── /catchup — ماذا فاتني؟ ────────────────────────────────────────────────
def _update_predictive(title: str):
    """يتتبع تكرار الموضوعات لكشف الأخبار العاجلة المبكرة."""
    global _predictive_last_reset
    # reset كل ساعة
    if time.time() - _predictive_last_reset > 3600:
        _predictive_counts.clear()
        _predictive_last_reset = time.time()

    words = [w for w in title.split() if len(w) > 4]
    for w in words:
        _predictive_counts[w] = _predictive_counts.get(w, 0) + 1
        if _predictive_counts[w] == _PREDICTIVE_THRESHOLD:
            # إرسال تنبيه للأدمن
            try:
                adm = int(os.environ.get("ADMIN_ID", 0))
                if adm:
                    bot.send_message(adm,
                        f"⚡ *إشارة تطور مبكرة:*\n"
                        f"الكلمة *'{w}'* تكررت {_PREDICTIVE_THRESHOLD} مرات في آخر ساعة.\n"
                        f"_آخر ظهور: {title[:80]}_",
                        parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)


# ── Disinformation Alert — تنبيه أخبار التحقق ────────────────────────────
def _alert_disinfo_if_needed(title: str, lang: str):
    """
    إذا كان الخبر تحققاً من ادعاء → يُرسل تنبيهاً لكل المشتركين النشطين.
    يعمل في thread منفصل.
    """
    if not _check_disinfo(title, lang):
        return

    def _do():
        msg = (
            f"🚨 *تحقق من معلومة:*\n━━━━━━━━━━━━━━\n\n"
            f"_{title}_\n\n"
            "_تحقق من مصادر متعددة قبل مشاركة هذه المعلومة_"
        )
        sent = 0
        for uid_str, u in list(users.items()):
            if not u.get("notifications", True): continue
            if u.get("lang") != lang: continue
            try:
                bot.send_message(int(uid_str), msg, parse_mode="Markdown")
                sent += 1
                time.sleep(0.05)
                if sent >= 200: break   # حد أقصى لحماية rate
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


def cmd_bookmarks_alias(m):
    cmd_saved(m)


# ══════════════════════════════════════════════════════════════════════════════
#  🔴  KEYWORD RADAR — رادار الكلمات المفتاحية: تنبيه فوري عند ذكر كلمتك
#  FIX: _RADAR_FILE/_radar_data/_radar_lock كانت معرَّفة في handler_ai.py
#       بينما ميزة الرادار الفعلية (هنا) لا تراها — نُقلت هنا لتكون بجانب استخدامها.
# ══════════════════════════════════════════════════════════════════════════════
_RADAR_FILE     = "radar_keywords.json"
_radar_data: dict = {}        # {uid_str: {"keywords": [...], "sent": [link_hash...]}}
_radar_lock = threading.Lock()
try:
    if os.path.exists(_RADAR_FILE):
        _radar_data = json.load(open(_RADAR_FILE, "r", encoding="utf-8"))
except Exception:
    _radar_data = {}

def _save_radar():
    save_json(_RADAR_FILE, _radar_data)

_RADAR_MAX_KW  = 5    # أقصى عدد كلمات لكل مستخدم
_RADAR_MAX_SENT = 500  # أقصى عدد روابط محفوظة لتجنب التكرار

@bot.message_handler(commands=["radar"])
def cmd_radar(m):
    uid     = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    if uid_str not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return
    parts = m.text.strip().split(maxsplit=2)
    if len(parts) == 1:
        # عرض الحالة الحالية
        kws = _radar_data.get(uid_str, {}).get("keywords", [])
        if not kws:
            msg = (
                "🔴 *رادار الكلمات المفتاحية*\n"
                "━━━━━━━━━━━━━━\n\n"
                "لا توجد كلمات مضافة بعد.\n\n"
                "*كيف يعمل:*\n"
                "أضف حتى 5 كلمات، وسيُنبّهك البوت فوراً\n"
                "عند ظهور أي خبر يذكرها من بين 223 مصدر!\n\n"
                "*الأوامر:*\n"
                "`/radar add النفط العراقي` — إضافة كلمة\n"
                "`/radar list` — عرض كلماتك\n"
                "`/radar remove النفط العراقي` — حذف كلمة"
            )
        else:
            kw_list = "\n".join(f"  🔴 `{k}`" for k in kws)
            msg = (
                f"🔴 *رادار الكلمات المفتاحية*\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"كلماتك المراقَبة ({len(kws)}/{_RADAR_MAX_KW}):\n{kw_list}\n\n"
                f"`/radar add كلمة` — إضافة\n"
                f"`/radar remove كلمة` — حذف"
            )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ إضافة كلمة", callback_data="radar_add_prompt"))
        if _radar_data.get(uid_str, {}).get("keywords"):
            markup.add(types.InlineKeyboardButton("🗑 مسح الكل", callback_data="radar_clear"))
        bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)
        return
    sub = parts[1].lower()
    kw  = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
    if sub == "list":
        kws = _radar_data.get(uid_str, {}).get("keywords", [])
        if kws:
            bot.send_message(uid, "🔴 كلماتك:\n" + "\n".join(f"  • `{k}`" for k in kws), parse_mode="Markdown")
        else:
            bot.send_message(uid, "لا توجد كلمات مضافة.")
    elif sub == "add":
        if not kw:
            bot.send_message(uid, "أرسل: `/radar add الكلمة`", parse_mode="Markdown"); return
        with _radar_lock:
            entry = _radar_data.setdefault(uid_str, {"keywords": [], "sent": []})
            if len(entry["keywords"]) >= _RADAR_MAX_KW:
                bot.send_message(uid, f"⚠️ وصلت للحد الأقصى ({_RADAR_MAX_KW} كلمات). احذف كلمة أولاً."); return
            if kw in entry["keywords"]:
                bot.send_message(uid, "⚠️ هذه الكلمة موجودة مسبقاً."); return
            entry["keywords"].append(kw)
            _save_radar()
        bot.send_message(uid, f"✅ تمت إضافة `{kw}` للرادار!\nستُنبَّه فور ظهور خبر يذكرها.", parse_mode="Markdown")
    elif sub == "remove":
        if not kw:
            bot.send_message(uid, "أرسل: `/radar remove الكلمة`", parse_mode="Markdown"); return
        with _radar_lock:
            entry = _radar_data.get(uid_str, {})
            if kw in entry.get("keywords", []):
                entry["keywords"].remove(kw)
                _save_radar()
                bot.send_message(uid, f"✅ تم حذف `{kw}` من الرادار.", parse_mode="Markdown")
            else:
                bot.send_message(uid, "⚠️ الكلمة غير موجودة.")
    else:
        bot.send_message(uid, "أمر غير معروف. أرسل `/radar` لعرض المساعدة.")

@bot.callback_query_handler(func=lambda c: c.data in ("radar_add_prompt", "radar_clear"))
def cb_radar_actions(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    bot.answer_callback_query(call.id)
    if call.data == "radar_add_prompt":
        msg = bot.send_message(uid, "🔴 أرسل الكلمة أو العبارة التي تريد مراقبتها:\n_(مثال: النفط العراقي، بغداد، البرلمان)_", parse_mode="Markdown")
        def _step(m):
            kw = m.text.strip()
            with _radar_lock:
                entry = _radar_data.setdefault(uid_str, {"keywords": [], "sent": []})
                if len(entry["keywords"]) >= _RADAR_MAX_KW:
                    bot.send_message(uid, f"⚠️ الحد الأقصى {_RADAR_MAX_KW} كلمات."); return
                if kw in entry["keywords"]:
                    bot.send_message(uid, "⚠️ الكلمة موجودة."); return
                entry["keywords"].append(kw)
                _save_radar()
            bot.send_message(uid, f"✅ تمت إضافة `{kw}` للرادار!", parse_mode="Markdown")
        bot.register_next_step_handler(msg, _step)
    elif call.data == "radar_clear":
        with _radar_lock:
            if uid_str in _radar_data:
                _radar_data[uid_str]["keywords"] = []
                _save_radar()
        bot.send_message(uid, "✅ تم مسح جميع كلمات الرادار.")

def _radar_scanner_job():
    """يفحص كل الـ feeds ويُنبّه المستخدمين عند تطابق كلماتهم — يعمل كل 5 دقائق."""
    if bot_paused: return
    if not _radar_data: return
    try:
        for uid_str, entry in list(_radar_data.items()):
            kws = entry.get("keywords", [])
            if not kws: continue
            try:
                uid_int = int(uid_str)
            except Exception:
                continue
            if uid_int in banned: continue
            user = users.get(uid_str, {})
            lang = user.get("lang", "العربية 🇮🇶")
            sent_hashes = set(entry.get("sent", []))
            feeds = RSS.get(lang, []) + RSS.get("English 🇬🇧", [])
            for feed_url in feeds[:30]:
                try:
                    feed = _parse_feed(feed_url)
                    if not feed: continue
                    for item in feed.entries[:5]:
                        title = getattr(item, "title", "").strip()
                        link  = getattr(item, "link",  "").strip()
                        if not title or not link: continue
                        h = hashlib.md5(link.encode()).hexdigest()[:12]
                        if h in sent_hashes: continue
                        title_lower = title.lower()
                        matched_kw = next((k for k in kws if k.lower() in title_lower), None)
                        if matched_kw:
                            sent_hashes.add(h)
                            entry["sent"] = list(sent_hashes)[-_RADAR_MAX_SENT:]
                            _save_radar()
                            try:
                                markup = types.InlineKeyboardMarkup()
                                if link.startswith("http"):
                                    markup.add(types.InlineKeyboardButton("🔗 فتح الخبر", url=link))
                                bot.send_message(
                                    uid_int,
                                    f"🔴 *تنبيه الرادار!*\n"
                                    f"━━━━━━━━━━━━━━\n"
                                    f"🔑 الكلمة: `{matched_kw}`\n\n"
                                    f"📰 {title}",
                                    parse_mode="Markdown",
                                    reply_markup=markup
                                )
                            except Exception as _exc:
                                _log_exc(_exc)
                except Exception:
                    continue
    except Exception as e:
        _logger.warning(f"_radar_scanner_job: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  🕰️  TIME CAPSULE — كبسولة الوقت: احفظ اليوم واستقبله بعد سنة
# ══════════════════════════════════════════════════════════════════════════════
_CAPSULE_FILE = "time_capsule.json"
_capsule_data: dict = {}  # {uid_str: [{date, headlines, saved_at}]}
try:
    if os.path.exists(_CAPSULE_FILE):
        _capsule_data = json.load(open(_CAPSULE_FILE, "r", encoding="utf-8"))
except Exception:
    _capsule_data = {}

def _save_capsule():
    save_json(_CAPSULE_FILE, _capsule_data)

@bot.message_handler(commands=["capsule"])
def cmd_capsule(m):
    uid     = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    if uid_str not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return
    user = users[uid_str]
    lang = user.get("lang", "العربية 🇮🇶")

    capsules = _capsule_data.get(uid_str, [])
    # اجمع أبرز 5 عناوين اليوم
    headlines = []
    for feed_url in RSS.get(lang, [])[:5]:
        try:
            feed = _parse_feed(feed_url)
            if not feed: continue
            for item in feed.entries[:3]:
                t_txt = getattr(item, "title", "").strip()
                if t_txt and _title_in_lang(t_txt, lang):
                    headlines.append(t_txt)
            if len(headlines) >= 5: break
        except Exception:
            continue

    if not headlines:
        bot.send_message(uid, "⚠️ لا توجد أخبار متاحة الآن لحفظها."); return

    today     = _now_sa().strftime("%Y-%m-%d")
    headlines = headlines[:5]

    # تحقق إذا حفظ اليوم مسبقاً
    already = any(c.get("date") == today for c in capsules)
    if already:
        hl_txt = "\n".join(f"  {i+1}. {h[:70]}" for i, h in enumerate(headlines))
        bot.send_message(uid,
            f"⏳ *حفظت كبسولة اليوم مسبقاً!*\n\n"
            f"ستصلك هذه الأخبار في مثل هذا اليوم **عام {int(today[:4])+1}** مع مقارنة بما حدث!\n\n"
            f"📰 *أخبار اليوم المحفوظة:*\n{hl_txt}",
            parse_mode="Markdown"
        )
        return

    capsules.append({
        "date": today,
        "headlines": headlines,
        "saved_at": _now_sa().isoformat(),
        "lang": lang
    })
    _capsule_data[uid_str] = capsules[-10:]  # احتفظ بـ 10 كبسولات فقط
    _save_capsule()

    hl_txt = "\n".join(f"  {i+1}. _{h[:70]}_" for i, h in enumerate(headlines))
    bot.send_message(uid,
        f"🕰️ *تم حفظ كبسولة الوقت!*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"📅 التاريخ: `{today}`\n\n"
        f"📰 *الأخبار المحفوظة:*\n{hl_txt}\n\n"
        f"🔮 ستصلك هذه الكبسولة في `{today[:4]}` القادم\n"
        f"مع تحليل ذكي لما حدث بعدها!",
        parse_mode="Markdown"
    )

def _capsule_delivery_job():
    """يفحص يومياً ويُرسل الكبسولات المستحقة (نفس اليوم من السنة الماضية)."""
    if bot_paused: return
    today = _now_sa().strftime("%Y-%m-%d")
    today_md = today[5:]   # MM-DD
    for uid_str, capsules in list(_capsule_data.items()):
        try:
            uid_int = int(uid_str)
        except Exception:
            continue
        if uid_int in banned: continue
        for cap in capsules:
            cap_date = cap.get("date", "")
            if not cap_date: continue
            cap_md   = cap_date[5:]        # MM-DD
            cap_year = cap_date[:4]
            if cap_md != today_md: continue
            if cap.get("delivered"): continue
            if cap_year == today[:4]: continue   # لا ترسل لنفس السنة
            headlines = cap.get("headlines", [])
            lang      = cap.get("lang", "العربية 🇮🇶")
            hl_txt    = "\n".join(f"  {i+1}. _{h[:70]}_" for i, h in enumerate(headlines))
            # توليد مقارنة ذكية
            ai_compare = ""
            if _AI_AVAILABLE:
                prompt = (
                    f"في مثل هذا اليوم عام {cap_year} كانت هذه الأخبار:\n"
                    + "\n".join(f"- {h}" for h in headlines)
                    + f"\n\nاليوم هو {today}. قدّم تحليلاً موجزاً (4 جمل) يقارن ما وعد به ذلك اليوم وما قد يكون حدث لاحقاً. "
                    f"اكتب بلغة {'العربية' if 'عرب' in lang else 'English'}."
                )
                ai_compare = _ai_call_safe(prompt, timeout=15) or ""
            try:
                msg = (
                    f"🕰️ *كبسولة الوقت — من {cap_year}!*\n"
                    f"━━━━━━━━━━━━━━\n\n"
                    f"📅 في مثل هذا اليوم عام *{cap_year}* كانت الأخبار:\n\n"
                    f"{hl_txt}\n\n"
                    f"━━━━━━━━━━━━━━\n"
                )
                if ai_compare:
                    msg += f"🤖 *تحليل ما بعدها:*\n{ai_compare}\n"
                bot.send_message(uid_int, msg, parse_mode="Markdown")
                cap["delivered"] = True
                _save_capsule()
            except Exception as _exc:
                _log_exc(_exc)


# ══════════════════════════════════════════════════════════════════════════════
#  🧠  COLLECTIVE INTELLIGENCE — ذكاء جماعي: تقرير يومي بأكثر المواضيع بحثاً
# ══════════════════════════════════════════════════════════════════════════════
_ci_topic_counter: dict = {}
_ci_lock = gl._ci_lock    # من state

def _ci_track_topic(topic: str):
    """يتتبع المواضيع التي يسأل عنها المستخدمون."""
    if not topic: return
    key = topic.strip().lower()[:50]
    with _ci_lock:
        _ci_topic_counter[key] = _ci_topic_counter.get(key, 0) + 1

def _ci_daily_broadcast():
    """يرسل يومياً الساعة 18:00 تقرير الذكاء الجماعي لمن يريده."""
    if bot_paused: return
    with _ci_lock:
        if not _ci_topic_counter: return
        top_topics = sorted(_ci_topic_counter.items(), key=lambda x: x[1], reverse=True)[:8]
        _ci_topic_counter.clear()
    topics_list = "\n".join(f"  {i+1}. *{t}* — {c} بحث" for i, (t, c) in enumerate(top_topics))
    # توليد تقرير بالذكاء الاصطناعي
    if _AI_AVAILABLE:
        kws = ", ".join(t for t, _ in top_topics[:5])
        prompt = (
            f"هذه المواضيع الأكثر بحثاً اليوم: {kws}\n\n"
            "اكتب تقريراً موجزاً (5 جمل) يربط هذه المواضيع بالأحداث الجارية ويشرح سبب اهتمام الناس بها اليوم. "
            "اكتب بالعربية."
        )
        ai_summary = _ai_call_safe(prompt, timeout=15) or ""
    else:
        ai_summary = ""
    msg = (
        f"🧠 *تقرير الذكاء الجماعي — اليوم*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🔥 *أكثر ما بحث عنه المستخدمون اليوم:*\n{topics_list}\n\n"
    )
    if ai_summary:
        msg += f"━━━━━━━━━━━━━━\n🤖 *تحليل ذكي:*\n{ai_summary}\n\n"
    msg += "✨ _Powered by InsightX @Iraqnowbot_"
    for uid_str, u in list(users.items()):
        if not u.get("ci_subscribe", False): continue
        try:
            uid_int = int(uid_str)
            if uid_int in banned: continue
            bot.send_message(uid_int, msg, parse_mode="Markdown")
        except Exception:
            continue

@bot.message_handler(commands=["ci", "collective"])
def cmd_ci(m):
    uid     = m.from_user.id
    if uid in banned: return
    uid_str = str(uid)
    if uid_str not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً."); return
    current = users[uid_str].get("ci_subscribe", False)
    users[uid_str]["ci_subscribe"] = not current
    _db_save_user(uid, users[uid_str])
    if not current:
        bot.send_message(uid,
            "🧠 *تم الاشتراك في تقرير الذكاء الجماعي!*\n\n"
            "كل يوم الساعة 6 مساءً ستصلك:\n"
            "  📊 أكثر المواضيع بحثاً اليوم\n"
            "  🤖 تحليل ذكي بالذكاء الاصطناعي\n\n"
            "ألغِ الاشتراك في أي وقت بـ `/ci`.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(uid, "❌ تم إلغاء اشتراكك في تقرير الذكاء الجماعي.")


# ── تسجيل مهام الميزات الأسطورية في الـ scheduler ────────────────────────
scheduler.add_job(_safe_job(_radar_scanner_job),    'interval', minutes=5,   id="radar_scan_job", max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_capsule_delivery_job), 'cron',     hour=9,  minute=30, id="capsule_job", max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_ci_daily_broadcast),   'cron',     hour=18, minute=0,  id="ci_broadcast_job", max_instances=1, coalesce=True)


# ======== تسجيل الأوامر مع تيليغرام ========
try:
    from telebot.types import BotCommand
    # ── قائمة الأوامر الكاملة للمستخدمين ─────────────────────────────
    _USER_COMMANDS = [
        # ── الأساسيات ──
        BotCommand("start",        "🚀 رسالة الترحيب وبدء البوت"),
        BotCommand("menu",         "📋 القائمة الرئيسية"),
        BotCommand("help",         "📖 دليل الاستخدام الكامل"),
        BotCommand("settings",     "⚙️ تعديل تفضيلاتك ولغتك"),
        BotCommand("restart",      "🔄 إعادة ضبط إعداداتك"),
        BotCommand("reset",        "♻️ إعادة إعداد البوت من البداية"),
        # ── الأخبار ──
        BotCommand("news",         "📰 آخر الأخبار حسب لغتك"),
        BotCommand("trending",     "🔥 أبرز الأخبار الرائجة الآن"),
        BotCommand("sports",       "⚽ أخبار ومباريات رياضية مباشرة"),
        BotCommand("summary",      "📋 ملخص يومي لأبرز 3 أحداث"),
        BotCommand("weekly",       "🗓 ملخص أبرز أخبار الأسبوع"),
        BotCommand("catchup",      "⏩ ماذا فاتني؟ أهم أخبار غيابك"),
        BotCommand("live",         "🔴 الأحداث الجارية مباشرة"),
        BotCommand("search",       "🔍 البحث في الأخبار"),
        BotCommand("sources",      "📡 قائمة مصادر الأخبار"),
        # ── الذكاء الاصطناعي ──
        BotCommand("ask",          "🤖 اسأل الذكاء الاصطناعي عن أي حدث"),
        BotCommand("analyze",      "🧐 تحليل موضوع أو قضية بالذكاء الاصطناعي"),
        BotCommand("econ",         "💹 التقرير الاقتصادي الذكي"),
        BotCommand("parliament",   "🏛 ملخص جلسات البرلمان"),
        BotCommand("predict",      "🔮 توقعات الذكاء الاصطناعي لأبرز القضايا"),
        BotCommand("intel",        "🕵️ تقرير استخباراتي ذكي"),
        BotCommand("deepsearch",   "🔬 بحث عميق شامل بالذكاء الاصطناعي"),
        BotCommand("verify",       "✅ التحقق من صحة الأخبار"),
        # ── الشخصية والتخصيص ──
        BotCommand("saved",        "📌 أخباري المحفوظة"),
        BotCommand("bookmarks",    "🔖 المحفوظات (اختصار saved)"),
        BotCommand("digest",       "🌅 الملخص الصباحي — اختر وقته"),
        BotCommand("sleep",        "😴 ضبط ساعات الصمت"),
        BotCommand("quiz",         "🧩 اختبار أخبار اليوم"),
        BotCommand("narratives",   "📖 الخطوط الزمنية للأحداث"),
        BotCommand("storyline",    "🎬 الخط الزمني لقصة معينة"),
        BotCommand("subscribe",    "🔔 إدارة اشتراكاتك وإشعاراتك"),
        # ── الميزات الأسطورية ──
        BotCommand("radar",        "🔴 رادار الكلمات — تنبيه فوري عند ذكر كلمتك"),
        BotCommand("capsule",      "🕰️ كبسولة الوقت — احفظ اليوم واستقبله بعد سنة"),
        BotCommand("ci",           "🧠 تقرير الذكاء الجماعي اليومي"),
        # ── الأسواق المالية ──
        BotCommand("markets",      "💰 أسعار العملات والأسهم والسلع"),
        BotCommand("chart",        "📈 رسم بياني تفاعلي لأي رمز"),
        BotCommand("alerts",       "🔔 تنبيهات تغير الأسعار ±1%"),
        BotCommand("mytrack",      "📊 قائمة الرموز التي تتابعها"),
        BotCommand("addtrack",     "➕ إضافة رمز مالي للتتبع"),
        BotCommand("removetrack",  "➖ حذف رمز من التتبع"),
        # ── الطقس ──
        BotCommand("weather",      "🌤 طقس المدن التي تتابعها"),
        # ── متابعة القصص ──
        BotCommand("follow",       "🔔 متابعة قصة إخبارية بكلمة مفتاحية"),
        BotCommand("unfollow",     "🔕 إلغاء متابعة قصة"),
        # ── إحصائياتك ──
        BotCommand("mystats",      "📊 إحصائياتي الشخصية مع البوت"),
        BotCommand("profile",      "👤 ملفي الشخصي"),
        # ── المجتمع والدعوة ──
        BotCommand("referral",     "🎁 رابط دعوتك ومكافآت الإحالة"),
        BotCommand("tip",          "💡 أرسل تلميحاً أو خبراً للبوت"),
        # ── الميزات المميزة (Premium) ──
        BotCommand("deepdive",     "⭐ تحليل عميق بالذكاء الاصطناعي"),
        BotCommand("addrss",       "⭐ إضافة مصدر RSS مخصص"),
        BotCommand("myrss",        "⭐ مصادر RSS الخاصة بي"),
        BotCommand("delrss",       "⭐ حذف مصدر RSS مخصص"),
        BotCommand("track",        "⭐ تتبع شخص أو شركة أو جهة"),
        BotCommand("mytracks",     "⭐ قائمة المتتبَّعين"),
        BotCommand("untrack",      "⭐ إيقاف تتبع"),
        BotCommand("crosslang",    "⭐ مقارنة التغطية عربي/إنجليزي"),
        BotCommand("influence",    "⭐ خريطة تأثير الشخصيات"),
        BotCommand("connections",  "⭐ شبكة الاتصالات بين الأطراف"),
        BotCommand("timeline",     "⭐ الجدول الزمني للأحداث"),
        BotCommand("history",      "⭐ السياق التاريخي لأي حدث"),
        BotCommand("audiobriefing","⭐ التقرير الصوتي اليومي"),
        BotCommand("compare",      "⭐ مقارنة تغطية قصة من مصادر مختلفة"),
        BotCommand("podcast",      "🎧 حلقة بودكاست يومية صوتية"),
        BotCommand("currency",     "💱 أسعار العملات الحية"),
        BotCommand("submit",       "📨 إرسال خبر/تلميح للبوت"),
        BotCommand("map",          "🗺️ خريطة الأحداث الجارية"),
        BotCommand("stop",         "🛑 إيقاف الإشعارات مؤقتاً"),
    ]
    bot.set_my_commands(_USER_COMMANDS)

    # ── قائمة موسّعة للأدمن (تُضاف فوق قائمة المستخدم) ─────────────
    _ADMIN_EXTRA = [
        BotCommand("admin",          "🔧 لوحة تحكم الأدمن الرئيسية"),
        BotCommand("dashboard",      "📊 لوحة البيانات المتقدمة"),
        BotCommand("analytics",      "📈 إحصائيات البوت الكاملة"),
        BotCommand("feedstats",      "📡 إحصائيات مصادر RSS"),
        BotCommand("featurepanel",   "⚙️ إدارة الميزات والـ Gating"),
        BotCommand("grantpremium",   "✅ منح اشتراك مميز لمستخدم"),
        BotCommand("revokepremium",  "❌ إلغاء اشتراك مميز"),
        BotCommand("premiumlist",    "📋 قائمة المشتركين المميزين"),
        BotCommand("addchannel",     "📺 إضافة قناة تيليغرام مصدراً"),
        BotCommand("removechannel",  "🗑 حذف قناة من المصادر"),
        BotCommand("discover",       "🔍 اكتشاف RSS تلقائياً من موقع"),
        BotCommand("listsources",    "📋 قائمة مصادر RSS اليدوية"),
        BotCommand("listchannels",   "📺 قائمة القنوات المضافة"),
        BotCommand("schedule",       "🗓 عرض جدول المهام المجدولة"),
        BotCommand("segment",        "👥 إرسال إشعار لشريحة مستخدمين"),
        BotCommand("sponsored",      "💼 إدارة المحتوى المموّل"),
        BotCommand("killswitch",     "🛑 إيقاف البث الإخباري مؤقتاً"),
        BotCommand("resume_all",     "▶️ استئناف البث بعد الإيقاف"),
        BotCommand("health",         "🏥 تقرير صحة البوت والـ APIs"),
        BotCommand("cleanup",        "🧹 تنظيف البيانات القديمة"),
        BotCommand("clearcache",     "💾 مسح ذاكرة الكاش"),
        BotCommand("forcenews",      "📰 إرسال جولة أخبار فورية"),
        BotCommand("sysinfo",        "💻 معلومات النظام والموارد"),
        BotCommand("errlogs",        "🔴 آخر 20 خطأ في السجلات"),
        BotCommand("resetbroadcast", "🔄 إعادة تعيين قائمة الأخبار المرسلة"),
    ] + _USER_COMMANDS

    for _admin_uid in ADMINS:
        try:
            bot.set_my_commands(
                _ADMIN_EXTRA,
                scope=types.BotCommandScopeChat(chat_id=_admin_uid)
            )
        except Exception as _exc:
            _log_exc(_exc)
except Exception as _e:
    _logger.warning(f"[set_my_commands] {_e}")

# ======== Watchdog — يراقب الـ scheduler ويعيد تشغيله لو مات ========
def _scheduler_watchdog():
    while True:
        time.sleep(60)
        try:
            if not scheduler.running:
                scheduler.start()
                try:
                    bot.send_message(ADMIN_ID, "⚠️ الـ scheduler توقف وأُعيد تشغيله تلقائياً!")
                except Exception as _exc:
                    _log_exc(_exc)
        except Exception as _exc:
            _log_exc(_exc)

_watchdog_thread = threading.Thread(target=_scheduler_watchdog, daemon=True)
_watchdog_thread.start()

# ======== تشغيل البوت — يعيد التشغيل تلقائياً عند أي انهيار ========
_logger.info("🔄 حذف أي webhook قديم قبل البدء...")
try:
    bot.delete_webhook(drop_pending_updates=True)
    _logger.info("✅ تم حذف الـ webhook")
except Exception as _wh_err:
    _logger.warning(f"⚠️ خطأ في حذف webhook: {_wh_err}")

_retry_count    = 0
_last_poll_ping = time.time()


def _polling_watchdog():
    """
    يراقب حالة البوت الفعلية عبر ping get_me() كل دقيقة.
    إذا فشل 3 مرات متتالية → يُرسل تنبيه send_alert للأدمن.
    """
    fail_count = 0
    _last_alert_time = 0
    while True:
        time.sleep(60)
        try:
            bot.get_me()
            fail_count = 0
        except Exception as _e:
            fail_count += 1
            _logger.warning(f"⚠️ PollingWatchdog: فشل ping #{fail_count} — {_e}")
            if fail_count >= 3:
                now = time.time()
                if now - _last_alert_time > 600:
                    _last_alert_time = now
                    send_alert(
                        message   = f"البوت لا يستجيب — فشل {fail_count} ping متتالية",
                        exc       = _e,
                        func_name = "PollingWatchdog",
                        show_traceback = False
                    )


_start_thread_once("PollingWatchdog", _polling_watchdog)

# ═══════════════════════════════════════════════════════════════════════════════
# SELF-HEALING MAIN LOOP — حلقة التشغيل الذاتي الإصلاح
# ═══════════════════════════════════════════════════════════════════════════════
_logger.info("🤖 IraqNow Bot — بدء الحلقة الرئيسية (Self-Healing)")




# ═══════════════════════════════════════════════════════════════
# Backward-compatibility re-exports من الملفات المُقسَّمة
# ═══════════════════════════════════════════════════════════════
# ملاحظة: هذه الاستيرادات تُفعَّل بعد تحميل كل المتغيرات العالمية
# لتجنب مشاكل الاستيراد الدائري (circular imports)


# ═══════════════════════════════════════════════════════════════
# FIX: Backward-compatibility re-exports من الملفات المُقسَّمة
# يجب أن تكون في النهاية لتجنب الاستيراد الدائري
# ═══════════════════════════════════════════════════════════════

# ── دمج وحدات الأخبار/RSS اليتيمة (كانت تُحمَّل بمعزل عن bot_legacy عبر
#    features_news.py مما يجعل دوالها — مثل broadcast_news — غير مرئية
#    لأي كود يبحث عنها داخل مساحة أسماء bot_legacy) ──────────────────────────
_global_sent_lock = gl._global_sent_lock

_AI_AVAILABLE = gl._AI_AVAILABLE
# ملاحظة: state.py يُعرّف _prematch_lock كـ Lock، لكن sports_live.py يستخدمه
# كـ Event (يستدعي .is_set())، لذا نُنشئه هنا كـ Event ليطابق كيفية استخدامه فعلياً.
_prematch_lock = gl._prematch_lock

for _merged_news_mod in (
    "auto_recovery", "error_tracker", "health_monitor", "ai_memory", "admin_rss_mgmt",
    "news_dedup", "news_filter", "news_formatter", "news_scraper",
    "news_tracker", "rss_cache", "rss_fetcher", "rss_validator",
    "channel_broadcaster", "news_broadcaster",
):
    try:
        _merge_module_into_globals(_merged_news_mod)
    except Exception as _news_merge_err:
        _logger.warning("⚠️ فشل دمج %s: %s", _merged_news_mod, _news_merge_err)

# ── Expose private names for `from bot_legacy import *` ──────────────────────
# FIX (ROOT CAUSE): يجب تعريف __all__ قبل أي import يُحمِّل وحدة تنفّذ
# "from bot_legacy import *"، بما فيها from error_tracker import أدناه.
# بدون __all__ مُعرَّف مسبقاً، Python يُفلتر كل الأسماء المبدوءة بـ _ تلقائياً،
# مما يُسبب NameError في كل وحدة تعتمد على هذه الأسماء عند الاستيراد الدائري.
__all__ = [_n for _n in dir() if not _n.startswith("__")]

# FIX: تعريف notify_admin_error إذا لم تُستورَد من error_tracker
# (تُستخدَم في bot_legacy نفسه في مناطق عدة)
# يأتي هذا الاستيراد بعد __all__ لضمان تصدير _ للأسماء المبدوءة بـ _ عند تحميل error_tracker
try:
    from error_tracker import notify_admin_error  # noqa: F401
except (ImportError, Exception):
    def notify_admin_error(msg: str, exc=None) -> None:  # noqa: F811
        """بديل بسيط عند تعذّر استيراد error_tracker."""
        try:
            send_alert(
                message=msg, exc=exc,
                func_name="notify_admin_error",
                show_traceback=False
            )
        except Exception:
            try:
                _logger.error("[notify_admin_error] %s — %s", msg, exc)
            except Exception:
                pass

# ── استيراد وحدات قاعدة البيانات المُقسَّمة (بالترتيب الصحيح) ───────────────
# db_users يجب أن يُستورَد قبل db_channels لأن db_channels يحتاج _job_save_all_users
# FIX: هذا القسم نُقل ليُنفَّذ *قبل* قسم وحدات المساعدة أدناه، لأن بعض تلك
# الوحدات (مثل ai_factcheck.py) تستدعي _restore_button_caches() عند تحميلها
# مباشرة — وهي دالة مُعرَّفة في db_cache.py؛ إذا استُورِدت db_cache بعدها
# يفشل الاستيراد كاملاً بـ NameError.
for _bl_db_mod in ["db_schema", "db_users", "db_channels", "db_cache", "db_backup"]:
    try:
        __import__(_bl_db_mod)
    except Exception as _bl_db_err:
        pass  # لا تُوقِف البوت عند خطأ استيراد DB

# ── استيراد وحدات المساعدة التي قد تُعرِّف دوالاً تُستخدَم في handlers ──
for _bl_mod in [
    "error_tracker", "utils", "safe_send", "auto_recovery",
    "health_monitor", "security", "keepalive", "admin_panel",
    # FIX: هذه الوحدات كانت مكتوبة بالكامل ووظائفها مطلوبة من ملفات أخرى
    # (مثل handler_callbacks.py و handler_ai.py) لكنها لم تكن مُستورَدة من
    # أي مكان في المشروع كله — أي أمر يعتمد عليها كان يفشل بصمت أو يتوقف.
    "sports_preferences", "sports_keyboards", "sports_espn", "sports_news",
    "sports_field", "sports_fixtures", "users_core", "users_premium",
    "users_referral", "users_stats", "ai_analysis", "ai_prediction",
    "ai_factcheck", "ai_insight", "ai_personalization", "social_media",
    "tts_engine", "admin_news_format", "admin_features_panel",
    "admin_crisis_room", "admin_stats_view", "news_filter",
    "admin_channels_mgmt", "sports_live",
    # FIX الأهم: ai_engine.py (محرك Gemini الحقيقي + _ai_call_safe) لم يكن
    # مُستورَداً من أي مكان في المشروع كله — أي ميزة ذكاء اصطناعي (فحص
    # شائعات، تحليل مشاعر، توقعات...) كانت معطّلة تماماً بلا استثناء.
    "ai_engine",
    # sports_365.py: مصدر مباريات/تنسيق الأسطر المستخدم من sports_fixtures.py
    # و sports_espn.py، ولم يكن مُستورَداً من أي مكان.
    "sports_365",
    # queue_worker.py: **جذر شكوى "ماكو اخبار"** — يُعرِّف queue_send() وهي
    # الدالة الوحيدة التي يستخدمها _broadcast_news_impl/news_broadcaster
    # لإرسال الأخبار فعلياً للمستخدمين. الملف لم يكن مستورَداً من أي مكان،
    # فكانت كل دورة بث تفشل بصمت عند queue_send() (NameError مُلتقَط ضمن
    # try/except عام) بعد جلب وتجهيز الأخبار بنجاح بالكامل — لذلك كان
    # الكاش يمتلئ بمئات الأخبار لكن لا شيء يصل للمستخدمين أبداً.
    "queue_worker",
    # admin_broadcast_manual.py: **جذر شكوى "اختفى زر متابعة المباراة"** —
    # هذا الملف هو من يُسجِّل تقريباً كل مهام الـ scheduler الدورية
    # (broadcast_to_channels, _sports_live_broadcaster, _prematch_notifier,
    # _crisis_monitor_check, _live_events_broadcaster, check_weather_alerts,
    # check_currency_alerts, check_keyword_alerts, send_morning_summary,
    # _send_backup_to_channel...) عبر استدعاءات scheduler.add_job() على
    # مستوى الوحدة. الملف لم يكن مستورَداً من أي مكان في المشروع، فكل هذه
    # المهام لم تُسجَّل إطلاقاً منذ الإقلاع — بما فيها البث التلقائي لتحديثات
    # المباريات المباشرة (الملعب المباشر). نجا broadcast_news_job وحده لأن
    # health_monitor.py يملك watchdog خاص يعيد تسجيله يدوياً عند اختفائه.
    "admin_broadcast_manual",
    # admin_users_mgmt.py: إدارة المستخدمين (بحث، حظر، ترقية مميز، تعيين أدمن)
    # — دوالها كانت تُستدعى من admin_panel.py عبر register_next_step_handler
    # بالاسم فقط، لكن الملف نفسه لم يكن مستورَداً من أي مكان، فكانت كل هذه
    # الأزرار تنهار بـ NameError عند الاستخدام الفعلي.
    "admin_users_mgmt",
    # ai_media.py: تحليل الصور بالذكاء الاصطناعي — لم يكن مستورَداً فيُفقَد
    # تسجيل @bot.message_handler(content_types=['photo']) بالكامل.
    "ai_media",
    # ai_rag.py: أمر /ask (محادثة مع الأخبار) — لم يكن مستورَداً فيُفقَد
    # تسجيل @bot.message_handler(commands=["ask"]) بالكامل.
    "ai_rag",
]:
    try:
        __import__(_bl_mod)
    except Exception as _bl_err:
        pass  # لا تُوقِف البوت إذا فشل استيراد وحدة مساعدة

# ── FIX: نسخ أسماء عالمية مُعرَّفة في وحدات أخرى إلى مساحة bot_legacy ──────────
# (is_admin كانت معرَّفة في admin_panel.py وحده — أي ملف يعتمد على
#  `from bot_legacy import *` لا يراها إطلاقاً بدون هذا النسخ الصريح.
#  نفس الأمر لـ _db_save_all_channels/_job_save_all_users من وحدات db_*.)
import sys as _bl_sys
for _bl_src_mod, _bl_names in (
    ("admin_panel", ["is_admin", "save_extra_admins"]),
    ("db_channels", ["_db_save_all_channels"]),
    ("db_users", ["_job_save_all_users"]),
):
    _bl_mod_obj = _bl_sys.modules.get(_bl_src_mod)
    if _bl_mod_obj is not None:
        for _bl_name in _bl_names:
            _bl_val = getattr(_bl_mod_obj, _bl_name, None)
            if _bl_val is not None:
                globals()[_bl_name] = _bl_val
                # FIX: __all__ تم حسابه قبل هذا السطر (سطر __all__ أعلاه) لذا
                # لا يشمل هذه الأسماء المُضافة لاحقاً — يجب إضافتها يدوياً
                # وإلا فإن `from bot_legacy import *` لن يراها أبداً.
                if _bl_name not in __all__:
                    __all__.append(_bl_name)

# ═══════════════════════════════════════════════════════════════════════════════
# تسجيل الدوال الرئيسية في state.py (بعد تعريفها جميعاً)
# ═══════════════════════════════════════════════════════════════════════════════
# ── تسجيل الدوال في state (بعد تعريفها جميعاً) ────────────────────────────────
gl.send_alert = send_alert
for _fn_name in ('broadcast_news', 'notify_admin_error',
                 '_db_save_all_channels', '_job_save_all_users', 'is_admin'):
    _fn = globals().get(_fn_name)
    if _fn is not None:
        setattr(gl, _fn_name, _fn)

# ── Stage 3: validate + freeze (بعد اكتمال الـ startup) ──────────────────────
try:
    gl.validate_state()   # يكشف أي shadow state في الملفات المحمَّلة
except Exception as _vs_err:
    _logger.warning("⚠️ validate_state error: %s", _vs_err)

try:
    gl.freeze_state()     # يقفل IMMUTABLE_KEYS — أي تعديل بعدها = warning
except Exception as _fs_err:
    _logger.warning("⚠️ freeze_state error: %s", _fs_err)

# ═══════════════════════════════════════════════════════════════════════════════
# FIX: أدوات تحديد المعدّل والحصة اليومية لميزات الذكاء الاصطناعي
# ═══════════════════════════════════════════════════════════════════════════════
# كانت هذه الدوال مُستخدَمة من handler_ai.py و handler_callbacks.py وغيرها
# (فحص الشائعات، البحث العميق، تحليل الأخبار...) لكنها لم تكن مُعرَّفة في أي
# مكان في المشروع كله — فكانت كل تلك الأوامر تتوقف بخطأ NameError صامت.
_FEATURE_DAILY_LIMITS: dict = {
    "deepsearch":   {"free": 3, "premium": 8},
    "verify":       {"free": 5, "premium": 20},
    "intel_report": {"free": 3, "premium": 15},
    "context":      {"free": 5, "premium": 20},
    "timeline":     {"free": 3, "premium": 15},
    "profile":      {"free": 3, "premium": 15},
    "influence":    {"free": 3, "premium": 15},
    "ask":          {"free": 5, "premium": 20},
    "why_matters":  {"free": 10, "premium": 40},
    "what_next":    {"free": 10, "premium": 40},
}
_FEATURE_USAGE_TODAY: dict = {}   # (uid, feature, "YYYY-MM-DD") -> عدد مرات الاستخدام
_feature_usage_lock = threading.Lock()
_RATE_LIMIT_COOLDOWN_SEC = 4
_last_feature_call: dict = {}    # (uid, feature) -> آخر وقت استخدام (لمنع الضغط المتكرر)
_rate_limit_lock = threading.Lock()


def _is_rate_limited(uid, feature, cooldown=_RATE_LIMIT_COOLDOWN_SEC) -> bool:
    """يمنع المستخدم من الضغط على نفس الميزة بشكل متكرر جداً (خلال ثوانٍ)."""
    now = time.time()
    key = (uid, feature)
    with _rate_limit_lock:
        last = _last_feature_call.get(key, 0)
        if now - last < cooldown:
            return True
        _last_feature_call[key] = now
        return False


def _check_daily_ai_limit(uid, feature):
    """يفحص الحصة اليومية ويستهلك استخداماً واحداً إذا كانت متاحة.
    يُرجِع (allowed: bool, used: int, limit: int)."""
    limits = _FEATURE_DAILY_LIMITS.get(feature, {"free": 5, "premium": 20})
    try:
        prem = bool(is_admin(uid)) or bool(is_premium(uid))
    except Exception:
        prem = False
    limit = limits["premium"] if prem else limits["free"]
    today = datetime.date.today().isoformat()
    key = (uid, feature, today)
    with _feature_usage_lock:
        used = _FEATURE_USAGE_TODAY.get(key, 0)
        if used >= limit:
            return False, used, limit
        _FEATURE_USAGE_TODAY[key] = used + 1
        return True, used, limit


def _check_and_consume_feature(uid, feature) -> bool:
    """نسخة تُستخدَم من أزرار الـ callback — نفس منطق _check_daily_ai_limit."""
    allowed, _used, _limit = _check_daily_ai_limit(uid, feature)
    return allowed


def _get_limit_msg(lang, feature) -> str:
    limits = _FEATURE_DAILY_LIMITS.get(feature, {"free": 5, "premium": 20})
    if lang == "English 🇬🇧":
        return f"📊 Daily limit reached for this feature ({limits['free']}/day free). Upgrade to Premium for more."
    return f"📊 استهلكت الحد اليومي لهذه الميزة ({limits['free']}/يوم للمجاني). ⭐ الترقية للمميز تمنحك المزيد."


# ═══════════════════════════════════════════════════════════════════════════
# FIX: لوحة تحكم الميزات (admin_features_panel.py / admin_panel.py) — كانت
# تستخدم _FEATURE_REGISTRY / _FEATURE_GATING_ACTIVE / _MODE_CYCLE / _MODE_LABELS
# / _save_feature_registry من دون أن تُعرَّف في أي مكان بالمشروع، فكان أمر
# /featuregate وكل أزرار لوحة الميزات يتوقف بـ NameError فوراً.
# ملاحظة مهمة: news_filter.py يُعرِّف _feat_ok(key) بمعامل واحد فقط وهي
# الدالة *الحقيقية* المُستخدَمة في news_formatter.py — لا تُضِف نسخة أخرى
# بنفس الاسم بتوقيع مختلف هنا، لأن from-import-* يجعل كل الوحدات تتشارك
# نفس الاسم، وأي نسخة إضافية بعدد معاملات مختلف تُسبِّب TypeError عشوائياً
# بحسب ترتيب الاستيراد (هذا ما حدث فعلياً وكان يُسقِط بث الأخبار بالكامل).
# ═══════════════════════════════════════════════════════════════════════════
_FEATURE_GATING_ACTIVE: bool = False   # مُعطَّل افتراضياً = كل الميزات مجانية بلا قيود
_MODE_CYCLE  = ["free", "limited", "premium_only", "disabled"]
_MODE_LABELS = {
    "free": "🟢 مجاني للجميع", "limited": "🔢 محدود يومياً",
    "premium_only": "⭐ للمميزين فقط", "disabled": "🚫 ملغية",
}
_FEATURE_REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feature_registry.json")
# نفس مفاتيح الميزات المُعرَّفة في admin_panel.py._FEATURE_FRIENDLY_NAMES —
# مُكرَّرة هنا لأن هذا الملف يُحمَّل قبل admin_panel.py في ترتيب الاستيراد.
_FEATURE_REGISTRY: dict = {
    key: {"mode": "free", "free_daily": _FEATURE_DAILY_LIMITS.get(key, {}).get("free", -1),
          "prem_daily": _FEATURE_DAILY_LIMITS.get(key, {}).get("premium", -1)}
    for key in [
        "summary", "why_matters", "what_next", "intel_report", "context",
        "factcheck", "deepdive", "storyline", "entity_track", "custom_rss",
        "bookmark", "keywords_alert", "weekly_report", "news_quiz", "catchup",
        "compare", "audiobriefing", "cross_lang", "audio_podcast", "sleep_mode",
        "prediction", "audio_article", "discuss", "ai_duel", "news_dna",
    ]
}
try:
    _frf_loaded = load_json(_FEATURE_REGISTRY_FILE, None)
    if isinstance(_frf_loaded, dict) and _frf_loaded:
        _FEATURE_REGISTRY.update(_frf_loaded)
except Exception:
    pass


def _save_feature_registry() -> None:
    try:
        save_json(_FEATURE_REGISTRY_FILE, _FEATURE_REGISTRY)
    except Exception as _sfr_exc:
        _log_exc(_sfr_exc, "_save_feature_registry")


# ── ميزات الداشبورد الخارجي (users_premium.py) — بلا داشبورد = كل شيء متاح ──
_feature_flags_cache: dict = {}
_feature_flags_ts: float = 0.0
_FEATURE_FLAGS_TTL = 300  # 5 دقائق

# ── تبريد استخدام AI للمستخدم الواحد (handler_callbacks._handle_user_document) ──
_user_ai_cooldown: dict = {}
_cooldown_lock = threading.Lock()

# ── ذاكرة أزرار InsightX التحليلية (سياق/لماذا يهم/ماذا بعد/مشاعر/كيانات/خطورة) ──
# يقرأها admin_stats_view.py لعرض حجم كل كاش في /health و /analytics.
_CONTEXT_CACHE: dict = {}
_WHY_MATTERS_CACHE: dict = {}
_WHAT_NEXT_CACHE: dict = {}
_SENTIMENT_AI_CACHE: dict = {}
_ENTITY_CACHE: dict = {}
_RISK_CACHE: dict = {}
_IMPACT_CACHE: dict = {}

# ── كاش الردود العامة لاستدعاءات AI الحرة (ask/deepsearch) + قفل ملخصات AI ──
_AI_CACHE: dict = {}
_AI_CACHE_LOCK = threading.Lock()
_AI_SUMMARY_CACHE: dict = {}
_AI_SUMMARY_LOCK = threading.Lock()

# ── إحصاءات الاستخدام لعرضها في /analytics ──────────────────────────────────
_user_daily_usage: dict = {}          # (uid, "YYYY-MM-DD") -> عدد الأوامر
_feature_usage_stats: dict = {}       # feature -> عدد مرات الاستخدام الكلي
_click_log_lock = threading.Lock()    # يحمي _user_click_log في handler_ai.py

# ═══════════════════════════════════════════════════════════════════════════
# FIX: **جذر شكوى "ماكو اخبار"** — news_broadcaster.py يستدعي
# _is_semantic_duplicate() / _rank_news_by_interests() / _register_broadcast_title()
# داخل حلقة إرسال الأخبار لكل مستخدم، ولم تكن مُعرَّفة في أي مكان بالمشروع
# إطلاقاً؛ كانت هذه NameError تُلغي كل دورة إرسال لكل مستخدم بصمت (مُلتقَطة
# ضمن try/except عام)، لذا كان كاش RSS يمتلئ بمئات الأخبار الطازجة لكن لا
# يصل أي خبر لأي مستخدم أبداً.
# ═══════════════════════════════════════════════════════════════════════════
import difflib as _difflib_dedup

_recent_sent_titles: dict = {}   # lang -> [(عنوان مُطبَّع, وقت الإرسال), ...]
_recent_titles_lock = threading.Lock()
_SEMANTIC_DEDUP_TTL = 6 * 3600     # 6 ساعات — بعدها يُسمح بتكرار نفس الموضوع
_SEMANTIC_DEDUP_MAX = 300          # أقصى عدد عناوين محفوظة لكل لغة


def _normalize_title_for_dedup(title: str) -> str:
    try:
        t = (title or "").strip().lower()
        t = re.sub(r"[\u0617-\u061A\u064B-\u0652]", "", t)  # إزالة التشكيل العربي
        t = re.sub(r"[^\w\s\u0600-\u06FF]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t
    except Exception:
        return (title or "").strip().lower()


def _is_semantic_duplicate(title: str, lang: str) -> bool:
    """يفحص إذا كان هذا العنوان مشابهاً جداً (نفس الموضوع) لعنوان أُرسل مؤخراً
    لنفس اللغة — يمنع بثّ نفس الخبر بصياغات مختلفة من مصادر متعددة."""
    try:
        norm = _normalize_title_for_dedup(title)
        if not norm:
            return False
        now = time.time()
        with _recent_titles_lock:
            recent = _recent_sent_titles.get(lang, [])
            for old_norm, ts in recent:
                if now - ts > _SEMANTIC_DEDUP_TTL:
                    continue
                if _difflib_dedup.SequenceMatcher(None, norm, old_norm).ratio() >= 0.82:
                    return True
        return False
    except Exception as _exc:
        _log_exc(_exc, "_is_semantic_duplicate")
        return False


def _register_broadcast_title(title: str, lang: str) -> None:
    """يُسجّل عنواناً بعد بثّه فعلياً حتى يُستخدَم في فحص _is_semantic_duplicate لاحقاً."""
    try:
        norm = _normalize_title_for_dedup(title)
        if not norm:
            return
        now = time.time()
        with _recent_titles_lock:
            lst = _recent_sent_titles.setdefault(lang, [])
            lst.append((norm, now))
            # تنظيف: احذف المنتهي زمنياً واقصر الطول الأقصى
            cutoff = now - _SEMANTIC_DEDUP_TTL
            lst[:] = [x for x in lst if x[1] >= cutoff][-_SEMANTIC_DEDUP_MAX:]
    except Exception as _exc:
        _log_exc(_exc, "_register_broadcast_title")


def _rank_news_by_interests(pool: list, uid) -> list:
    """يُعيد ترتيب قائمة الأخبار بحيث تتصدّر الأخبار المطابقة لاهتمامات
    المستخدم — لا يحذف أي عنصر أبداً (الفلترة الفعلية تحدث لاحقاً في حلقة
    الإرسال)، فقط يُرتِّب لتحسين تجربة المستخدم الشخصية."""
    try:
        if not pool:
            return pool
        info = users.get(str(uid), {}) or {}
        interests = info.get("interests", [])
        if not interests:
            return pool
        matched, unmatched = [], []
        for item in pool:
            try:
                title = item[1] if len(item) > 1 else ""
                (matched if news_matches_interests(title, interests) else unmatched).append(item)
            except Exception:
                unmatched.append(item)
        return matched + unmatched
    except Exception as _exc:
        _log_exc(_exc, "_rank_news_by_interests")
        return pool

# ── تأخير ديناميكي بين دورات البث (يُعرَض في /sysinfo) ──────────────────────
_dynamic_delay: float = 3.0


for _bl_name in ("_is_rate_limited", "_check_daily_ai_limit",
                 "_check_and_consume_feature", "_get_limit_msg",
                 "_FEATURE_DAILY_LIMITS"):
    if _bl_name not in __all__:
        __all__.append(_bl_name)

_logger.info("✅ STATE LOADED: %s | boot=%.2fs", gl.VERSION, time.time() - gl.BOOT_TIME)

