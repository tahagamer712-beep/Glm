# -*- coding: utf-8 -*-
"""
state.py — المصدر الوحيد للحالة المشتركة (Single Source of Truth)
Stage 3 — Production-Grade Hardening

استخدم: import state as gl  ثم: gl.variable_name

القواعد الصارمة:
  * state.py يملك: locks / queues / caches / flags / executors
  * bot_legacy يملك: bot instance / scheduler / handlers / config injection
  * باقي الملفات: logic فقط — لا إنشاء state جديد أبداً
"""
import sys
import threading
import queue
import concurrent.futures
import time
import logging

_module_logger = logging.getLogger("state")

# ═══════════════════════════════════════════════════════════════════════════════
# ── نسخة النظام ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
VERSION   = "refactor-v3"
INIT_OK   = True
BOOT_TIME = time.time()

# ═══════════════════════════════════════════════════════════════════════════════
# ── IMMUTABLE_KEYS — المفاتيح التي يملكها state.py حصراً ─────────────────────
# ── أي ملف آخر يُنشئ نسخة محلية من هذه الأسماء = shadow state خطير ──────────
# ═══════════════════════════════════════════════════════════════════════════════
IMMUTABLE_KEYS: frozenset = frozenset({
    # Locks
    "_users_rlock", "_stats_lock", "_db_lock", "_retry_lock",
    "_title_seen_lock", "_rss_etag_lock", "_broadcast_news_lock",
    "_broadcast_channels_lock", "_global_rss_cache_lock",
    "_broadcast_log_lock", "_broadcast_stats_lock",
    "_dead_chats_lock", "_delivery_stats_lock",
    "_alert_lock", "_ci_lock", "_prematch_lock",
    # Queues & Executors
    "_send_queue", "_AI_EXECUTOR", "_BC_FORCE_EXECUTOR", "_RSS_EXECUTOR",
})

# ── Freeze flag ────────────────────────────────────────────────────────────────
_STATE_FROZEN = False

# ═══════════════════════════════════════════════════════════════════════════════
# ── Module-level guard — يمنع تغيير IMMUTABLE_KEYS بعد الـ freeze ─────────────
# ═══════════════════════════════════════════════════════════════════════════════
class _GuardedModule(sys.modules[__name__].__class__):
    """
    Custom module class — يعترض أي __setattr__ على IMMUTABLE_KEYS
    بعد تجميد الحالة (_STATE_FROZEN = True).
    يُسجّل warning ولا يوقف البوت (soft guard).
    """
    def __setattr__(self, name: str, value) -> None:
        frozen = object.__getattribute__(self, '__dict__').get('_STATE_FROZEN', False)
        if frozen and name in object.__getattribute__(self, '__dict__').get('IMMUTABLE_KEYS', frozenset()):
            _module_logger.warning(
                "⚠️ STATE GUARD: محاولة تعديل '%s' بعد الـ freeze — مرفوض", name
            )
            return  # soft block — لا نُوقف البوت
        object.__setattr__(self, name, value)

sys.modules[__name__].__class__ = _GuardedModule

# ═══════════════════════════════════════════════════════════════════════════════
# ── Shutdown flag ─────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
_SIGTERM_RECEIVED = False

# ═══════════════════════════════════════════════════════════════════════════════
# ── Telegram Bot instance & Logger (يُعيَّنان من bot_legacy) ─────────────────
# ═══════════════════════════════════════════════════════════════════════════════
bot    = None
_logger  = None
_log_exc = None

# ═══════════════════════════════════════════════════════════════════════════════
# ── Thread Locks & Events (state.py يُنشئها — لا أحد غيره) ─────────────────
# ═══════════════════════════════════════════════════════════════════════════════
_users_rlock             = threading.RLock()
_stats_lock              = threading.Lock()
_db_lock                 = threading.RLock()  # FIX: RLock بدل Lock — يمنع Deadlock عند backup
_retry_lock              = threading.Lock()
_title_seen_lock         = threading.Lock()
_rss_etag_lock           = threading.Lock()
_broadcast_news_lock     = threading.Event()
_broadcast_channels_lock = threading.Event()
_global_rss_cache_lock   = threading.Lock()
_broadcast_log_lock      = threading.Lock()
_broadcast_stats_lock    = threading.Lock()
_dead_chats_lock         = threading.Lock()
_delivery_stats_lock     = threading.Lock()
_alert_lock              = threading.Lock()
_ci_lock                 = threading.Lock()
# FIX (SSOT): كل الاستخدامات الفعلية (sports_notifications.py) تعامل هذا
# الكائن كـ Event (is_set/set/clear) وليس Lock — تم تصحيحه هنا ليطابق
# الاستخدام الحقيقي، بدل ترك كل ملف يُنشئ Event منفصلاً خاصاً به.
_prematch_lock           = threading.Event()

# ═══════════════════════════════════════════════════════════════════════════════
# ── Queues & Executors (state.py يُنشئها — لا أحد غيره) ─────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
_send_queue        = queue.Queue(maxsize=2000)
_AI_EXECUTOR       = concurrent.futures.ThreadPoolExecutor(max_workers=4,  thread_name_prefix="ai")
_BC_FORCE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2,  thread_name_prefix="bc")
# PERF-FIX: executor دائم لجلب RSS — بدلاً من إنشاء ThreadPoolExecutor جديد
# في كل دفعة (تكلفة إنشاء threads عالية تُبطئ أوامر المستخدمين).
# max_workers=4: توازن بين سرعة الجلب وعدم استنزاف الـ GIL
_RSS_EXECUTOR      = concurrent.futures.ThreadPoolExecutor(max_workers=4,  thread_name_prefix="rss")

# ═══════════════════════════════════════════════════════════════════════════════
# ── Scheduler (يُعيَّن من bot_legacy بعد إنشائه) ─────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
scheduler = None

# ═══════════════════════════════════════════════════════════════════════════════
# ── AI & Runtime flags ────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
_AI_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# ── Data Caches & Shared Mutable State ───────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
TELEGRAM_NEWS_CHANNELS = {}
RSS                    = {}
_weather_cache         = {}
_WEATHER_CACHE_TTL     = 600
_broadcast_lock_ts     = [0.0]
_broadcast_impl_thread = [None]
_broadcast_stats       = {
    "total": 0, "success": 0, "fail": 0,
    "last_run": None, "active": False,
}
_global_sent_news      = {}
# FIX-11: قفل thread-safe لـ _global_sent_news — يمنع إرسال نفس الخبر مرتين
_global_sent_lock      = threading.RLock()
# FIX-8: TTLCache بدل dict عادي — يمنع نمو الذاكرة إلى ما لا نهاية
try:
    from cachetools import TTLCache as _TTLCache
    _title_seen_cache   = _TTLCache(maxsize=5000,  ttl=3600)    # ساعة
    _rss_item_cache     = _TTLCache(maxsize=10000, ttl=86400)   # يوم
except ImportError:
    _title_seen_cache   = {}   # fallback إذا لم تُثبَّت cachetools
    _rss_item_cache     = {}
_title_dedup_ttl       = 86400
_rss_etag_store        = {}
_GLOBAL_RSS_CACHE      = {}
_retry_heap            = []

# ═══════════════════════════════════════════════════════════════════════════════
# ── File path constants ───────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
USERS_FILE              = "users_data.json"
BANNED_FILE             = "banned.json"
STATS_FILE              = "stats.json"
ADMINS_FILE             = "extra_admins.json"
INBOX_FILE              = "inbox.json"
READ_STATS_FILE         = "read_stats.json"
RATINGS_FILE            = "ratings.json"
BROADCAST_SETTINGS_FILE = "broadcast_settings.json"
NEWS_SETTINGS_FILE      = "news_settings.json"
CHANNELS_FILE           = "channels_groups.json"
WELCOME_FILE            = "welcome.json"
RSS_SOURCES_FILE        = "rss_sources.json"
CRISIS_FILE             = "crisis_tips.json"
RSS_FILE                = "rss_data.json"
CUSTOM_TG_CHANNELS_FILE = "custom_tg_channels.json"
KEYWORDS_FILE           = "user_keywords.json"
TRACK_FILE              = "tracked_assets.json"
_SCHEDULED_FILE         = "scheduled_bcasts.json"
_SPONSORED_FILE         = "sponsored.json"
_CAPSULE_FILE           = "capsule.json"
_RADAR_MAX_KW           = 30
BOT_USERNAME            = "Iraqnowbot"

# ═══════════════════════════════════════════════════════════════════════════════
# ── Shared functions (تُعيَّن من bot_legacy بعد تعريفها) ──────────────────────
# ═══════════════════════════════════════════════════════════════════════════════
broadcast_news        = None
send_alert            = None
_db_save_all_channels = None
_job_save_all_users   = None
notify_admin_error    = None

# ═══════════════════════════════════════════════════════════════════════════════
# ── Stage 3 Guard Functions ───────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

def validate_state() -> bool:
    """
    يتحقق أن كل IMMUTABLE_KEYS في الـ modules المُستوردة
    تشير لنفس الكائن في state.py (id مطابق).
    يُسجّل warning لكل تعارض — لا يوقف البوت.
    يُستدعى مرة واحدة عند startup.
    """
    import sys as _sys
    this_module = _sys.modules[__name__]
    violations  = []

    for mod_name, mod in list(_sys.modules.items()):
        if mod is None or mod is this_module:
            continue
        if not hasattr(mod, '__file__') or mod.__file__ is None:
            continue
        # تحقق فقط من ملفات المشروع (لا مكتبات خارجية)
        try:
            if 'nahrain' not in (mod.__file__ or '') and 'bot_legacy' not in mod_name:
                continue
        except Exception:
            continue

        for key in IMMUTABLE_KEYS:
            local_val = getattr(mod, key, None)
            state_val = getattr(this_module, key, None)
            if local_val is not None and local_val is not state_val:
                violations.append(f"{mod_name}.{key}")

    if violations:
        _module_logger.warning(
            "⚠️ SSOT violations — shadow state detected in: %s", ", ".join(violations)
        )
        return False

    _module_logger.info("✅ validate_state: all IMMUTABLE_KEYS verified — no shadow state")
    return True


def scan_for_shadow_state() -> list:
    """
    يفحص جميع الـ modules المُحمَّلة عن أي متغير باسم موجود في IMMUTABLE_KEYS
    لكنه ليس نفس الكائن في state.py.
    يُرجع قائمة بالمخالفات لتسجيلها أو عرضها.
    """
    import sys as _sys
    this_module = _sys.modules[__name__]
    found = []

    for mod_name, mod in list(_sys.modules.items()):
        if mod is None or mod is this_module:
            continue
        for key in IMMUTABLE_KEYS:
            local_val = getattr(mod, key, None)
            state_val = getattr(this_module, key, None)
            if local_val is not None and state_val is not None and local_val is not state_val:
                found.append({
                    "module": mod_name,
                    "key":    key,
                    "local_id": id(local_val),
                    "state_id": id(state_val),
                })
    return found


def freeze_state() -> None:
    """
    يُجمّد الحالة بعد انتهاء الـ startup.
    بعد هذه الدالة: أي محاولة لتغيير IMMUTABLE_KEYS تُسجَّل كـ warning.
    """
    import sys as _sys
    mod = _sys.modules[__name__]
    object.__setattr__(mod, '_STATE_FROZEN', True)
    _module_logger.info("🔒 State frozen — IMMUTABLE_KEYS محمية من التغيير")
