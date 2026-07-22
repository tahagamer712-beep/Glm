# -*- coding: utf-8 -*-
"""
  queue_worker.py — طابور الرسائل + rate-limiting

  يُصدِّر كل ما يتعلق بطابور الإرسال والـ rate limiting.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _classify_error(err_str: str) -> str:
    """
    يصنّف الخطأ إلى أحد الأنواع المعروفة.
    يُعيد أحد ثوابت _ERR_* لاتخاذ إجراء مخصص.
    """
    e = err_str.lower()
    if "429" in e or "too many requests" in e or "flood" in e:
        return _ERR_RATE_LIMIT
    if any(x in e for x in ("bot was blocked", "user is deactivated",
                             "chat not found", "peer_id_invalid",
                             "kicked", "not a member", "forbidden")):
        return _ERR_DELIVERY
    if "can't parse" in e or "parse entities" in e or ("400" in e and "parse" in e):
        return _ERR_PARSE
    if any(x in e for x in ("network", "timeout", "connection", "timed out",
                             "connection reset", "connection aborted", "eof")):
        return _ERR_NETWORK
    if any(x in e for x in ("400", "401", "403", "500", "502", "503")):
        return _ERR_TELEGRAM_API
    return _ERR_UNKNOWN

def _is_dead_chat(chat_id) -> bool:
    """هل هذا الـ chat محظور مؤقتاً بسبب فشل متكرر؟"""
    with _dead_chats_lock:
        ts = _dead_chats.get(str(chat_id))
        if ts is None:
            return False
        if time.time() - ts > _DEAD_CHAT_TTL:
            del _dead_chats[str(chat_id)]
            return False
        return True

def _blacklist_chat(chat_id):
    """يُدرج الـ chat في القائمة السوداء مؤقتاً."""
    with _dead_chats_lock:
        _dead_chats[str(chat_id)] = time.time()

def _smart_admin_alert(func_name: str, error: str, chat_id=None, resolution: str = ""):
    """
    يُرسل تنبيهاً للأدمن فقط عندما يفشل الحل التلقائي.
    يتضمن: نوع الخطأ + الإجراء المتخذ + اقتراح الحل.
    """
    with _delivery_stats_lock:
        _delivery_stats["admin_alerted"] += 1
    err_type = _classify_error(error)
    suggestions = {
        _ERR_RATE_LIMIT:   "⏳ تلغرام يحد الإرسال — انخفض معدل البث مؤقتاً.",
        _ERR_DELIVERY:     "🚫 مستخدم حذف/حجب البوت — تم تعطيل إشعاراته.",
        _ERR_PARSE:        "✏️ خطأ تنسيق — أُرسل بدون Markdown.",
        _ERR_NETWORK:      "🌐 انقطاع شبكة — البوت يُعيد المحاولة تلقائياً.",
        _ERR_TELEGRAM_API: "⚙️ خطأ API — تحقق من الـ token وحالة خوادم تيليغرام.",
        _ERR_UNKNOWN:      "❓ خطأ غير معروف — راجع السجل.",
    }
    msg = (
        f"🤖 *تنبيه ذكي — فشل التعافي التلقائي*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📍 الوظيفة: `{func_name}`\n"
        f"🏷 نوع الخطأ: `{err_type}`\n"
        f"💬 التفاصيل: `{error[:200]}`\n"
        + (f"👤 Chat: `{chat_id}`\n" if chat_id else "")
        + (f"⚙️ الإجراء التلقائي: {resolution}\n" if resolution else "")
        + f"💡 اقتراح: {suggestions.get(err_type, '—')}"
    )
    try:
        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)

# ── ضبط سرعة البث تلقائياً بحسب حمل النظام ─────────────────────────────────
_dynamic_delay: float = 0.05   # التأخير بين رسائل الـ queue (ثانية)
_dynamic_delay_lock   = threading.Lock()

def _update_dynamic_delay():
    """
    يُعدّل التأخير بين الرسائل بحسب حمل النظام والـ queue:
    - حمل طبيعي  → 0.05s (20 رسالة/ثانية)
    - حمل متوسط  → 0.10s (10 رسالة/ثانية)
    - حمل عالٍ   → 0.25s (4 رسائل/ثانية)
    - حمل حرج    → 0.50s (2 رسالة/ثانية)
    """
    global _dynamic_delay
    ram = _sys_health.get("ram_pct", 0)
    q   = _send_queue.qsize() if hasattr(_send_queue, "qsize") else 0
    q_pct = q / _QUEUE_MAX_SIZE * 100 if _QUEUE_MAX_SIZE > 0 else 0
    if ram > 88 or q_pct > 80:
        delay = 0.50
    elif ram > 75 or q_pct > 60:
        delay = 0.25
    elif ram > 65 or q_pct > 40:
        delay = 0.10
    else:
        delay = 0.05
    with _dynamic_delay_lock:
        _dynamic_delay = delay

def _dynamic_delay_adjuster():
    """خيط يُحدّث التأخير الديناميكي كل 30 ثانية."""
    while True:
        time.sleep(30)
        try:
            _update_dynamic_delay()
        except Exception as _exc:
            _log_exc(_exc)

threading.Thread(
    target=_dynamic_delay_adjuster,
    daemon=True,
    name="DynamicDelayAdjuster"
).start()

# ═══════════════════════════════════════════════════════════════════════════════
# نهاية IMMORTAL DELIVERY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# ======== قائمة الإرسال — محدودة الحجم لمنع امتلاء الذاكرة ========
_QUEUE_MAX_SIZE  = 20000  # حدّ أقصى (يكفي لـ 20K مستخدم)
_QUEUE_WORKERS   = 3      # FIX: كان 5 — خُفِّض لتوفير خيوط على Heroku (حد 256)
_send_queue      = queue.Queue(maxsize=_QUEUE_MAX_SIZE)
_queue_dropped   = 0      # عدد الرسائل التي سقطت بسبب الامتلاء (للإحصاء)
_queue_threads: list = []  # pool من الخيوط


# ── BUG-02 FIX: Retry Heap — رسائل Rate-Limited تُعاد بدون تجميد الـ worker ──
# FIX: كان يُدفَع لـ _retry_heap بدون أي كود يُصرِّفه (لا heappop ولا scheduled job
# بأي ملف) — كل رسالة تُحظر بريف ليميت تُفقد نهائياً بصمت. الحل: مؤقّت ذاتي
# (threading.Timer) يُعيد الرسالة لطابور الإرسال تلقائياً بعد الانتظار، بدون
# الاعتماد على أي آلية تصريف خارجية.
import heapq as _heapq  # noqa: F401 — يبقى للتوافق مع أي كود قديم يستورده
_retry_heap  = []   # موروث — غير مستخدم بعد الآن، تُرك للتوافق فقط
_retry_lock  = threading.Lock()

def _schedule_retry(chat_id, text, kwargs, delay):
    """يُعيد رسالة إلى طابور الإرسال بعد `delay` ثانية بدون تجميد أي خيط."""
    def _requeue():
        try:
            queue_send(chat_id, text, **kwargs)
        except Exception as _exc:
            _log_exc(_exc)
    timer = threading.Timer(delay, _requeue)
    timer.daemon = True
    timer.start()

def _queue_worker():
    """
    ═══ IMMORTAL QUEUE WORKER ═══
    مُشغّل الإرسال المحسّن — يستخدم:
    • تصنيف الأخطاء (classify) لاتخاذ قرار مخصص لكل نوع
    • Exponential backoff حقيقي (1s → 2s → 4s → 8s → 16s)
    • تنبيه الأدمن فقط عند فشل الحل التلقائي
    • ضبط سرعة الإرسال ديناميكياً بحسب حمل النظام
    • قائمة سوداء مؤقتة للـ chats التي تفشل باستمرار
    """
    while True:
        try:
            chat_id, text, kwargs = _send_queue.get(timeout=1)

            # ── تخطّ الـ chats الميتة مؤقتاً ──────────────────────────
            if _is_dead_chat(chat_id):
                _send_queue.task_done()
                continue

            # ── توافق pyTelegramBotAPI الجديد: حوّل الكلمة المهجورة ──
            # disable_web_page_preview → link_preview_options (يلغي تحذيرات DEPRECATION)
            if "disable_web_page_preview" in kwargs:
                _dwpp_val = kwargs.pop("disable_web_page_preview")
                if "link_preview_options" not in kwargs:
                    try:
                        kwargs["link_preview_options"] = types.LinkPreviewOptions(is_disabled=bool(_dwpp_val))
                    except Exception:
                        # لو الإصدار قديم وما يدعم LinkPreviewOptions — رجّع الكلمة الأصلية
                        kwargs["disable_web_page_preview"] = _dwpp_val

            sent          = False
            auto_resolved = False
            last_err      = ""

            # ── صورة الخبر (اختيارية) — تبقى بالـ kwargs حتى تُحفظ صحيحة عند إعادة المحاولة ──
            _photo_url = kwargs.get("photo")

            # FIX: نحاول إرسال الصورة مرة واحدة فقط على الإطلاق عبر كل محاولات
            # إعادة الإرسال (لمنع تكرار إرسال نفس الصورة الحقيقية إذا نجحت على
            # تيليغرام رغم استثناء محلي). وإذا فشلت لأي سبب (شبكة/توقيت/رابط
            # معطوب) نتحوّل فوراً لرسالة نصية — لضمان عدم فقدان الخبر بالكامل
            # بانتظار محاولات صورة متكررة قد تستهلك كل الوقت وتفشل كلها.
            _photo_attempted = [False]

            def _do_send(_kwargs):
                """يرسل كصورة+تعليق إذا فيه photo (مرة واحدة فقط)، وإلا كرسالة نصية عادية."""
                _pk = {k: v for k, v in _kwargs.items() if k not in ("photo", "disable_web_page_preview", "link_preview_options")}
                if _photo_url and not _photo_attempted[0]:
                    _photo_attempted[0] = True
                    try:
                        # صورة محلية (مثل شعار الوكالة الافتراضي) تحتاج فتح كملف
                        # ثنائي — أما رابط RSS فيُرسَل كسلسلة نصية مباشرة.
                        if isinstance(_photo_url, str) and os.path.isfile(_photo_url):
                            with open(_photo_url, "rb") as _f:
                                bot.send_photo(chat_id, _f, caption=text[:1024], **_pk)
                        else:
                            bot.send_photo(chat_id, _photo_url, caption=text[:1024], **_pk)
                        return
                    except Exception as _photo_exc:
                        _log_exc(_photo_exc)
                        # فشلت الصورة (لأي سبب) → لا نعيد محاولتها أبداً، نتحوّل لنص فوراً
                _tk = {k: v for k, v in _kwargs.items() if k != "photo"}
                bot.send_message(chat_id, text, **_tk)

            for attempt in range(5):
                try:
                    _do_send(kwargs)
                    sent = True
                    with _delivery_stats_lock:
                        _delivery_stats["sent_ok"] += 1
                        if attempt > 0:
                            _delivery_stats["retried"] += 1
                    break

                except Exception as e:
                    err_str   = str(e)
                    last_err  = err_str
                    err_type  = _classify_error(err_str)

                    # ── Rate Limit: انتظر حسب تعليمات تيليغرام ────────
                    if err_type == _ERR_RATE_LIMIT:
                        with _delivery_stats_lock:
                            _delivery_stats["rate_limited"] += 1
                        try:
                            _rl_after = int(
                                getattr(e, "result_json", {}).get("parameters", {}).get("retry_after", None)
                                or _re.search(r"retry after (\\d+)", err_str, _re.I).group(1)
                            )
                        except Exception:
                            _rl_after = 30
                        # ← non-blocking: مؤقّت ذاتي يُعيد الرسالة تلقائياً بدل نوم الـ worker
                        _schedule_retry(chat_id, text, kwargs, _rl_after + 1)
                        _send_queue.task_done()
                        break  # حرر الـ worker فوراً

                    # ── فشل التسليم: عطّل المستخدم تلقائياً ──────────
                    elif err_type == _ERR_DELIVERY:
                        try:
                            uid_str = str(chat_id)
                            if uid_str in users:
                                users[uid_str]["notifications"] = False
                                _db_save_user(uid_str, users[uid_str])
                            _blacklist_chat(chat_id)
                            _mark_dead_user(chat_id)  # HEROKU FIX v4
                        except Exception as _exc:
                            _log_exc(_exc)
                        auto_resolved = True
                        with _delivery_stats_lock:
                            _delivery_stats["auto_resolved"] += 1
                        break   # لا نُعيد المحاولة — مستخدم غير متاح

                    # ── خطأ Parse: أرسل بدون تنسيق ───────────────────
                    elif err_type == _ERR_PARSE:
                        try:
                            plain_kw = {k: v for k, v in kwargs.items()
                                        if k != 'parse_mode'}
                            _do_send(plain_kw)
                            sent = True
                            auto_resolved = True
                            with _delivery_stats_lock:
                                _delivery_stats["sent_ok"]       += 1
                                _delivery_stats["auto_resolved"] += 1
                        except Exception as _exc:
                            _log_exc(_exc)
                        break

                    # ── خطأ شبكة: exponential backoff ─────────────────
                    elif err_type == _ERR_NETWORK:
                        wait = min(1 * (2 ** attempt), 32)   # 1→2→4→8→16→32
                        _logger.debug("🌐 network error attempt=%d wait=%.1fs", attempt, wait)
                        time.sleep(wait)
                        auto_resolved = True

                    # ── خطأ API عام: exponential backoff ──────────────
                    elif err_type == _ERR_TELEGRAM_API:
                        wait = min(2 * (2 ** attempt), 60)   # 2→4→8→16→32→60
                        _logger.debug("⚙️ telegram_api error attempt=%d wait=%.1fs", attempt, wait)
                        time.sleep(wait)

                    # ── غير معروف: exponential backoff متحفظ ──────────
                    else:
                        wait = min(1 * (2 ** attempt), 16)   # 1→2→4→8→16
                        time.sleep(wait)

            # ── إحصاءات الفشل + تنبيه الأدمن إذا فشل الحل التلقائي ──
            if not sent:
                with _delivery_stats_lock:
                    _delivery_stats["sent_fail"] += 1
                _track_error("_queue_worker", None)
                if not auto_resolved:
                    _smart_admin_alert(
                        func_name  = "_queue_worker",
                        error      = last_err,
                        chat_id    = chat_id,
                        resolution = "فشل بعد 5 محاولات — لم يُحل تلقائياً"
                    )

            _send_queue.task_done()

            # ── تأخير ديناميكي بحسب حمل النظام ───────────────────────
            with _dynamic_delay_lock:
                _sleep_t = _dynamic_delay
            time.sleep(_sleep_t)

        except queue.Empty:
            continue
        except Exception as _qe:
            _logger.debug("_queue_worker loop error: %s", _qe)
            time.sleep(1)
            continue


def _start_queue_workers():
    """يبدأ pool من خيوط الإرسال المتوازية."""
    global _queue_threads
    _queue_threads = []
    for i in range(_QUEUE_WORKERS):
        t = threading.Thread(target=_queue_worker, daemon=True, name=f"SendWorker-{i+1}")
        t.start()
        _queue_threads.append(t)
    _logger.info("✅ Queue workers started: %d", _QUEUE_WORKERS)


_start_queue_workers()


def _queue_watchdog():
    """
    مراقب: يتحقق كل 15 ثانية أن خيوط الإرسال حية.
    يُعيد تشغيل أي خيط مات — يحافظ دائماً على _QUEUE_WORKERS خيوط.
    """
    while True:
        time.sleep(15)
        try:
            # FIX: نظّف الميتة أولاً قبل حساب العدد لمنع تراكم الخيوط
            _queue_threads[:] = [t for t in _queue_threads if t.is_alive()]
            alive = len(_queue_threads)
            dead  = _QUEUE_WORKERS - alive
            if dead > 0:
                _logger.warning("⚠️ %d queue worker(s) dead — restarting...", dead)
                for i in range(dead):
                    t = threading.Thread(target=_queue_worker, daemon=True, name=f"SendWorker-R{alive+i}")
                    t.start()
                    _queue_threads.append(t)
        except Exception as _exc:
            _log_exc(_exc)


_start_thread_once("QueueWatchdog", _queue_watchdog)


def queue_send(chat_id, text, **kwargs):
    """
    يضع رسالة في القائمة.
    إذا كانت القائمة ممتلئة، يُسقط الرسالة القديمة لإفساح مجال للجديدة.
    لا يُعلّق البوت أبداً بسبب القائمة.
    """
    global _queue_dropped
    try:
        _send_queue.put_nowait((chat_id, text, kwargs))
    except queue.Full:
        # القائمة ممتلئة — احذف أقدم رسالة وأضف الجديدة
        try:
            _send_queue.get_nowait()
            _send_queue.task_done()
            _queue_dropped += 1
        except Exception as _exc:
            _log_exc(_exc)
        try:
            _send_queue.put_nowait((chat_id, text, kwargs))
        except Exception as _exc:
            _log_exc(_exc)

# FIX: تباعد بين رسائل الأخبار المتعددة لنفس المحادثة بالدورة الواحدة — بدون
# حجب حلقة البث عن باقي المستخدمين/القنوات (مؤقّت خلفي غير مُعطِّل).
_NEWS_SPACING_SECONDS = 6  # الفاصل بين خبر وخبر لنفس المستخدم/القناة

def queue_send_delayed(chat_id, text, delay=0, **kwargs):
    """مثل queue_send لكن يؤخّر الإضافة للطابور بـ `delay` ثانية — يُستخدم لتفريق
    عدة أخبار تصل لنفس المحادثة بدورة بث واحدة بدل إرسالها كلها دفعة واحدة."""
    if delay <= 0:
        queue_send(chat_id, text, **kwargs)
        return
    def _do():
        try:
            queue_send(chat_id, text, **kwargs)
        except Exception as _exc:
            _log_exc(_exc)
    timer = threading.Timer(delay, _do)
    timer.daemon = True
    timer.start()

# ======== ملفات الحفظ ========
USERS_FILE = "users.json"
STATS_FILE = "stats.json"
BANNED_FILE = "banned.json"
RSS_FILE = "rss.json"
CUSTOM_TG_CHANNELS_FILE = "custom_tg_channels.json"  # قنوات تيليغرام أضافها الأدمن ديناميكياً
ADMINS_FILE = "admins.json"
KEYWORDS_FILE = "keywords.json"
TRACK_FILE = "tracking.json"
CHANNELS_FILE = "channels.json"
BLACKLIST_FILE = "blacklist.json"
READ_STATS_FILE = "read_stats.json"
BROADCAST_SETTINGS_FILE = "broadcast_settings.json"
NEWS_SETTINGS_FILE = "news_settings.json"
INBOX_FILE = "inbox.json"
RATINGS_FILE = "ratings.json"
WELCOME_FILE = "welcome.json"

# ======== اسم البوت ========
BOT_USERNAME = "Iraqnowbot"

# ======== تحميل وحفظ البيانات ========
