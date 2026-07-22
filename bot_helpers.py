# -*- coding: utf-8 -*-
# bot_helpers.py — دوال مساعدة عامة (logging, json, time, users)

def _log_exc(exc, context=""):
    _logger.error("Exception%s: %s", f" in {context}" if context else "", exc, exc_info=False)

# ── JSON helpers ──────────────────────────────────────────────────────────────
def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as _f:
            return json.load(_f)
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    """
    FIX-4: كتابة ذرية — إما تنجح كاملة أو لا شيء.
    1. نسخة احتياطية .bak أولاً.
    2. كتابة في ملف مؤقت بنفس المجلد (يضمن نفس الـ filesystem).
    3. os.replace ذري.
    """
    import tempfile as _tmpfile, shutil as _shutil
    dir_name = os.path.dirname(os.path.abspath(path))
    if os.path.exists(path):
        try: _shutil.copy2(path, path + '.bak')
        except Exception: pass
    tmp_path = None
    try:
        with _tmpfile.NamedTemporaryFile('w', dir=dir_name, delete=False,
                                         suffix='.tmp', encoding='utf-8') as _f:
            json.dump(data, _f, ensure_ascii=False, indent=2)
            _f.flush()
            os.fsync(_f.fileno())
            tmp_path = _f.name
        os.replace(tmp_path, path)
    except Exception as _e:
        _log_exc(_e, f"save_json({path})")
        if tmp_path:
            try: os.remove(tmp_path)
            except Exception: pass

# ── File path constants ───────────────────────────────────────────────────────
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
# FIX: كانت مُستخدَمة في admin_channels_mgmt.py/db_backup.py/handler_callbacks.py
# لكنها لم تكن مُعرَّفة إطلاقاً في مساحة bot_legacy المشتركة.
BLACKLIST_FILE          = "blacklist.json"
TELEGRAM_NEWS_CHANNELS: dict = {}   # populated at runtime by channel managers
RSS: dict = {}              # lang→[url,...]; populated by rss_fetcher at runtime
BOT_USERNAME = "Iraqnowbot"   # @handle without @

# auto_backup is defined in db_backup.py; provide a safe stub until that module loads

def _register_module(name: str, fn):
    _module_registry[name] = fn

# ── _safe_job wrapper ─────────────────────────────────────────────────────────
def _safe_job(fn):
    def _wrapper(*args, **kwargs):
        if _SIGTERM_RECEIVED:
            return
        try:
            return fn(*args, **kwargs)
        except Exception as _exc:
            _log_exc(_exc, getattr(fn, "__name__", str(fn)))
    _wrapper.__name__ = getattr(fn, "__name__", "_safe_job_wrapper")
    return _wrapper

# ── Alert helper ──────────────────────────────────────────────────────────────
def send_alert(message="", exc=None, func_name="", show_traceback=False):  # noqa: E302
    try:
        txt = f"\U0001f6a8 *Alert* — `{func_name}`\n{message}"
        if exc:
            txt += f"\n`{type(exc).__name__}: {str(exc)[:300]}`"
        if show_traceback:
            import traceback as _tb
            txt += f"\n```{_tb.format_exc()[-500:]}```"
        bot.send_message(ADMIN_ID, txt[:4096], parse_mode="Markdown")
    except Exception:
        pass

# ── SQLite (simple users persistence) ────────────────────────────────────────
_db_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
# FIX-3: WAL Mode — يمنع "database is locked" عند التزامن
for _pragma in ("PRAGMA journal_mode=WAL","PRAGMA synchronous=NORMAL","PRAGMA busy_timeout=30000","PRAGMA cache_size=10000"):
    try: _db_conn.execute(_pragma)
    except Exception: pass
_db_conn.commit()
_db_cursor = _db_conn.cursor()
_db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS users_store (
        uid TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
""")
# FIX: كانت db_cache.py تستدعي _load_button_cache/_save_button_cache لتخزين
# ذاكرة أزرار الأخبار (لماذا يهم/ماذا بعد/فحص شائعة...) لكن الجدول والدوال
# لم تكن موجودة في أي مكان — فكانت الذاكرة تُفرَّغ عند كل إعادة تشغيل.
_db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS button_cache_store (
        name TEXT PRIMARY KEY,
        data TEXT NOT NULL
    )
""")
_db_conn.commit()
_button_cache_db_lock = threading.Lock()


def _load_button_cache(name: str) -> dict:
    # FIX: استخدام _db_conn.execute() بدلاً من _db_cursor العالمي
    # لأن كل thread يجب أن يستخدم cursor مستقل
    try:
        with _button_cache_db_lock:
            row = _db_conn.execute(
                "SELECT data FROM button_cache_store WHERE name = ?", (name,)
            ).fetchone()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return {}


def _save_button_cache(name: str, data: dict) -> None:
    # FIX: استخدام _db_conn.execute() بدلاً من _db_cursor العالمي
    # لأن كل thread يجب أن يستخدم cursor مستقل
    try:
        payload = json.dumps(data, ensure_ascii=False)
        with _button_cache_db_lock:
            _db_conn.execute(
                "INSERT INTO button_cache_store (name, data) VALUES (?, ?) "
                "ON CONFLICT(name) DO UPDATE SET data = excluded.data",
                (name, payload),
            )
            _db_conn.commit()
    except Exception:
        pass

def _now_sa() -> datetime.datetime:
    """يُعيد الوقت الحالي بتوقيت السعودية / العراق (UTC+3)."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + _SA_TZ_OFFSET

def _sa_str(fmt: str = "%H:%M:%S — %d/%m/%Y") -> str:
    """يُعيد الوقت الحالي كنص بتوقيت السعودية."""
    return _now_sa().strftime(fmt)

# FIX: متغيرات مشتركة تحتاجها الوحدات المتعددة — تُعرَّف هنا لتصدَر عبر __all__
# (كانت مُعرَّفة في وحدات فرعية، مما يُسبب NameError عند الاستيراد الدائري)
_sys_health: dict = {
    "ram_pct": 0.0, "cpu_pct": 0.0, "disk_pct": 0.0,
    "start_ts": time.time(), "recoveries": 0,
}
_broadcast_log_lock   = gl._broadcast_log_lock    # من state
_broadcast_call_log: list = []
_broadcast_errors:   list = []
_broadcast_stats_lock = gl._broadcast_stats_lock  # من state
# _UI_STRINGS يُعرَّف لاحقاً في bot_legacy؛ هذا fallback مبدئي لمنع NameError مبكراً
if "_UI_STRINGS" not in dir():
    _UI_STRINGS: dict = {}

def _get_cached_weather(city, lang_code):
    key = f"{city}_{lang_code}"
    if key in _weather_cache:
        data, ts = _weather_cache[key]
        if (datetime.datetime.now() - ts).total_seconds() < _WEATHER_CACHE_TTL:
            return data
    return None

def _set_cached_weather(city, lang_code, data):
    _weather_cache[f"{city}_{lang_code}"] = (data, datetime.datetime.now())

def _fetch_weather_cached(city, lang_code):
    d = _get_cached_weather(city, lang_code)
    if d:
        return d
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}"
    try:
        d = requests.get(url, timeout=10).json()
        if d.get("cod") == 200:
            _set_cached_weather(city, lang_code, d)
            return d
    except Exception as _exc:
        _log_exc(_exc)
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# IMMORTAL DELIVERY ENGINE — تصنيف الأخطاء + ضمان التسليم + ضبط الحمل التلقائي
# ═══════════════════════════════════════════════════════════════════════════════

# ── ثوابت تصنيف الأخطاء ─────────────────────────────────────────────────────
_ERR_TELEGRAM_API  = "telegram_api"   # خطأ من API تيليغرام
_ERR_DELIVERY      = "delivery"       # فشل التسليم (مستخدم حجب / حذف)
_ERR_PARSE         = "parse"          # خطأ Markdown/HTML
_ERR_RATE_LIMIT    = "rate_limit"     # 429 Too Many Requests
_ERR_NETWORK       = "network"        # انقطاع الشبكة
_ERR_RESOURCE      = "resource"       # CPU/RAM مرتفع
_ERR_UNKNOWN       = "unknown"        # غير معروف

# ── قائمة الـ chats المعطّلة مؤقتاً (blacklist) ─────────────────────────────
_dead_chats: dict = {}
_dead_chats_lock  = gl._dead_chats_lock    # من state
_DEAD_CHAT_TTL    = 86400

# ── إحصاءات التسليم المتقدمة ──────────────────────────────────────────────────
_delivery_stats: dict = {
    "sent_ok":        0,
    "sent_fail":      0,
    "retried":        0,
    "rate_limited":   0,
    "auto_resolved":  0,    # مشاكل حُلّت تلقائياً
    "admin_alerted":  0,    # مشاكل أُبلغ عنها للأدمن
}
_delivery_stats_lock = gl._delivery_stats_lock    # من state


def _safe_users_snapshot():
    """إرجاع نسخة آمنة من users للتكرار بدون race condition"""
    with _users_rlock:
        return list(users.items())

def _safe_update_user(uid: str, updates: dict):
    """تحديث بيانات مستخدم بشكل thread-safe"""
    with _users_rlock:
        if uid in users:
            users[uid].update(updates)

banned = load_json(BANNED_FILE, [])
banned = [int(b) for b in banned]

stats = load_json(STATS_FILE, {
    "total_users": 0,
    "daily_users": {},
    "button_presses": {},
    "countries_count": {},
    "languages_count": {},
    "premium_users": [],
    "revenue": 0.0
})


def st(lang, key, **kwargs):
    """ترجمة رسائل الإعداد والتفاعل حسب لغة المستخدم."""
    text = SETUP_MSGS.get(lang, SETUP_MSGS["English 🇬🇧"]).get(
        key, SETUP_MSGS["English 🇬🇧"].get(key, "")
    )
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception as _exc:
            _log_exc(_exc)
    return text

