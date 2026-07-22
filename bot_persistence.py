# -*- coding: utf-8 -*-
# bot_persistence.py — دوال حفظ البيانات (bookmarks, sleep, votes, tracks, rss, etc.)

def save_read_stats():
    save_json(READ_STATS_FILE, read_stats)

# ======== إعدادات توقيت البث ========
broadcast_settings = load_json(BROADCAST_SETTINGS_FILE, {"interval_minutes": 1})

def save_broadcast_settings():
    save_json(BROADCAST_SETTINGS_FILE, broadcast_settings)

news_settings = load_json(NEWS_SETTINGS_FILE, {
    "label": "🚨 خبر عاجل",
    "separator": "━━━━━━━━━━━━━━",
    "signature": "✨ Powered by InsightX\n@Iraqnowbot"
})

def save_news_settings():
    save_json(NEWS_SETTINGS_FILE, news_settings)

inbox_messages = load_json(INBOX_FILE, [])

def save_inbox():
    save_json(INBOX_FILE, inbox_messages[-200:])

ratings_data = load_json(RATINGS_FILE, {"entries": [], "bot_sum": 0, "news_sum": 0, "count": 0})

def save_ratings():
    save_json(RATINGS_FILE, ratings_data)

# ======== إحصائيات القنوات ========
# يُحفظ داخل كل عنصر في channels_groups تحت مفتاح "news_sent_count"

# ======== حالة البوت ========
bot_paused = False
_pause_since = None   # وقت آخر إيقاف — لإرسال تذكير للأدمن
pause_message = "🔧 البوت متوقف مؤقتاً، سيعود قريباً."
broadcast_paused = False   # إيقاف/تشغيل البث الإخباري تحديداً (مستقل عن إيقاف البوت كله)
_welcome_data = load_json(WELCOME_FILE, {"override": None})
welcome_override = _welcome_data.get("override", None)


def _save_bookmarks():
    save_json(_BOOKMARKS_FILE, _bookmarks)

# Sleep mode settings
_sleep_settings: dict = {}     # {uid_str: {"enabled": bool, "start": 23, "end": 7}}
_SLEEP_FILE = "sleep_settings.json"
try:
    import json as _json_sl
    if os.path.exists(_SLEEP_FILE):
        with open(_SLEEP_FILE, "r", encoding="utf-8") as _f:
            _sleep_settings = _json_sl.load(_f)
except Exception:
    _sleep_settings = {}

def _save_sleep():
    save_json(_SLEEP_FILE, _sleep_settings)

def _is_sleeping(uid) -> bool:
    """يتحقق إذا كان المستخدم في وضع الصمت الآن."""
    s = _sleep_settings.get(str(uid), {})
    if not s.get("enabled"):
        return False
    # FIX: استخدم UTC+3 (توقيت العراق) بدلاً من توقيت السيرفر
    tz_offset = int(users.get(str(uid), {}).get("tz_offset", 3))
    now_h = (datetime.datetime.now(datetime.timezone.utc).hour + tz_offset) % 24
    start = s.get("start", 23)
    end   = s.get("end", 7)
    if start > end:    # يتجاوز منتصف الليل
        return now_h >= start or now_h < end
    return start <= now_h < end

# News votes
_news_votes: dict = {}         # {hash: {"up": N, "down": N, "voters": [uid]}}
_VOTES_FILE = "news_votes.json"
try:
    import json as _json_vt
    if os.path.exists(_VOTES_FILE):
        with open(_VOTES_FILE, "r", encoding="utf-8") as _f:
            _news_votes = _json_vt.load(_f)
except Exception:
    _news_votes = {}

def _save_votes():
    save_json(_VOTES_FILE, _news_votes)

# Quiz state
_quiz_questions: list = []     # [{q, answer, options, news_title}]
_user_quiz: dict = {}          # {uid_str: {q_idx, answered, score, date}}
_QUIZ_FILE = "quiz_state.json"
try:
    import json as _json_qz
    if os.path.exists(_QUIZ_FILE):
        with open(_QUIZ_FILE, "r", encoding="utf-8") as _f:
            _user_quiz = _json_qz.load(_f)
except Exception:
    _user_quiz = {}

# Narrative Arc
_narrative_store: dict = {}    # {topic_key: [{"title","ts","source"}]}
_NARRATIVE_FILE = "narratives.json"
try:
    import json as _json_na
    if os.path.exists(_NARRATIVE_FILE):
        with open(_NARRATIVE_FILE, "r", encoding="utf-8") as _f:
            _narrative_store = _json_na.load(_f)
except Exception:
    _narrative_store = {}

def _save_narratives():
    save_json(_NARRATIVE_FILE, _narrative_store)

# Entity tracking
_entity_tracks: dict = {}      # {uid_str: [{"entity", "added_ts"}]}
_TRACKS_FILE  = "entity_tracks.json"
try:
    import json as _json_et
    if os.path.exists(_TRACKS_FILE):
        with open(_TRACKS_FILE, "r", encoding="utf-8") as _f:
            _entity_tracks = _json_et.load(_f)
except Exception:
    _entity_tracks = {}

def _save_tracks():
    save_json(_TRACKS_FILE, _entity_tracks)

# Custom RSS (مستخدم مميز)
_custom_rss_store: dict = {}   # {uid_str: [{"url","name","added_ts"}]}
_CUSTOM_RSS_USER_FILE = "custom_rss_users.json"
try:
    import json as _json_cr
    if os.path.exists(_CUSTOM_RSS_USER_FILE):
        with open(_CUSTOM_RSS_USER_FILE, "r", encoding="utf-8") as _f:
            _custom_rss_store = _json_cr.load(_f)
except Exception:
    _custom_rss_store = {}

def _save_custom_rss():
    save_json(_CUSTOM_RSS_USER_FILE, _custom_rss_store)

# Scheduled broadcasts
_scheduled_bcasts: list = []   # [{"text","target","scheduled_ts","added_by"}]
_SCHEDULED_FILE = "scheduled_broadcasts.json"
try:
    import json as _json_sc
    if os.path.exists(_SCHEDULED_FILE):
        with open(_SCHEDULED_FILE, "r", encoding="utf-8") as _f:
            _scheduled_bcasts = _json_sc.load(_f)
except Exception:
    _scheduled_bcasts = []

def _save_scheduled():
    save_json(_SCHEDULED_FILE, _scheduled_bcasts)

# Sponsored news queue
_sponsored_queue: list = []    # [{"title","text","url","label","added_ts"}]
_SPONSORED_FILE = "sponsored_queue.json"
try:
    import json as _json_sp
    if os.path.exists(_SPONSORED_FILE):
        with open(_SPONSORED_FILE, "r", encoding="utf-8") as _f:
            _sponsored_queue = _json_sp.load(_f)
except Exception:
    _sponsored_queue = []

def _save_sponsored():
    save_json(_SPONSORED_FILE, _sponsored_queue)

# Segment cache  (يُعاد بناؤه عند الطلب)
_segment_cache: dict = {}      # {"active":[uid],"inactive_7":[uid],"inactive_30":[uid],"blocked":[uid]}
_segment_cache_ts: float = 0.0

# Disinfo alert keywords (patterns that signal fact-checks)
_DISINFO_PATTERNS = [
    "تحقق من", "كذب", "مزيف", "خبر مزيف", "تفنيد",
    "fact check", "false claim", "misleading", "debunked", "fact-check",
    "تحقق:", "خبر كاذب", "معلومة مضللة",
]


# ─────────────────────────────────────────────────────────────────────────
# §3  AUTO-FEATURES — تعمل تلقائياً بدون تدخل
# ─────────────────────────────────────────────────────────────────────────

