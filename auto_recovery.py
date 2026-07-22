# -*- coding: utf-8 -*-
"""
  auto_recovery.py — watchdog + إعادة تشغيل الوحدات

  يُصدِّر نظام الاسترداد التلقائي وسجل الوحدات.
  """

import sys as _sys_legacy
import os
import threading as _ar_threading
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: _broadcast_errors و _broadcast_stats_lock — تأكيد وجودهما
if "_broadcast_errors" not in dir():
    _broadcast_errors: list = []
if "_broadcast_stats_lock" not in dir():
    _broadcast_stats_lock = _ar_threading.Lock()

def _trigger_forced_broadcast(source: str) -> bool:
    """
    FIX: _trigger_forced_broadcast قد تكون معرَّفة في health_monitor.py (مُستورَد بعد هذه الوحدة).
    نُحيل للنسخة الحقيقية عند توفرها، وإلا نُنفِّذ نسخة مبسَّطة.
    """
    import sys as _s
    _hm = _s.modules.get("health_monitor")
    if _hm and hasattr(_hm, "_trigger_forced_broadcast"):
        return _hm._trigger_forced_broadcast(source)
    # fallback مبسَّط — يستدعي broadcast_news مباشرة إن وُجد
    try:
        _bc_fn = globals().get("broadcast_news")
        if _bc_fn:
            _safe_job(_bc_fn)()
            return True
    except Exception as _exc:
        _log_exc(_exc)
    return False

def _eternal_broadcast_keeper():
    """
    الضامن الأخير للبث الأبدي — يعمل كل 2 دقيقة.
    مستقل عن كل watchdog آخر — لا يعتمد على scheduler.
    يطلق دورة بث مباشرةً إذا توقف البث أكثر من 5 دقائق.
    """
    _last_trigger = [0.0]
    while True:
        time.sleep(60)    # كل دقيقة
        try:
            if bot_paused or broadcast_paused:
                continue
            now = time.time()
            # BUGFIX: last_news_sent_time فقط — fallback لوقت الإقلاع لا last_broadcast_time
            _bstats = globals().get('_broadcast_stats', {})
            _ek_lns = _bstats.get("last_news_sent_time") or _bot_start_time
            try:
                _ek_ts  = _ek_lns.timestamp() if hasattr(_ek_lns, 'timestamp') else float(_ek_lns)
                elapsed = now - _ek_ts
            except Exception:
                elapsed = 9999

            # إذا لم يُرسَل أي خبر أكثر من 10 دقائق → تدخّل
            if elapsed > 600 and now - _last_trigger[0] > 90:
                _last_trigger[0] = now
                # فك القفل العالق فقط إذا تجاوز عمره _BROADCAST_MAX_SECS
                _lock_age = now - _broadcast_lock_ts[0]
                if _broadcast_news_lock.is_set() and _lock_age > _BROADCAST_MAX_SECS:
                    _broadcast_news_lock.clear()
                    _broadcast_channels_lock.clear()
                    _logger.warning("🔓 EternalKeeper: فُكّ قفل عالق (%.0fث)", _lock_age)
                # FIX: حُذف مسح sent_news — كان يُعيد إرسال كل الأخبار ويسبب spam
                # FIX: استدعاء مباشر بدل _BC_FORCE_EXECUTOR لمنع تراكم الخيوط
                if not _broadcast_news_lock.is_set():
                    _trigger_forced_broadcast("eternal_keeper")
        except Exception as _exc:
            _log_exc(_exc)


_start_thread_once("EternalBroadcastKeeper", _eternal_broadcast_keeper)

# ── مُنفّذ مشترك لدورات البث الإجبارية (يمنع Thread Leak) ──────────────
# FIX (SSOT): كان يُنشئ ThreadPoolExecutor منفصلاً بنفس الاسم بدل استخدام
# المُنفِّذ الوحيد في state.py — يُبطل الحماية من تسرّب الخيوط (Thread Leak)
# لأن كل ملف كان يُشغّل executor خاصاً به بدل مشاركة واحد محدود.
_BC_FORCE_EXECUTOR = gl._BC_FORCE_EXECUTOR


# ======== نظام الإصلاح التلقائي الذكي ========
_auto_recovery_last = {
    "clearcache": 0.0,
    "forcenews":  0.0,
    "ai_retry":   0.0,
}
_QUEUE_OVERFLOW_THRESHOLD = 300    # إذا تجاوز عدد الرسائل المنتظرة هذا الرقم
_NO_NEWS_TIMEOUT_SEC      = 10*60  # إذا لم يُرسَل أي خبر خلال 10 دقائق

def _auto_recovery_watchdog():
    """
    نظام الإصلاح التلقائي الذكي — يعمل في الخلفية كل 60 ثانية ويُنفّذ:
    1. تنظيف القائمة تلقائياً إذا تراكمت أكثر من 300 رسالة
    2. إعادة البث تلقائياً إذا لم يُرسَل خبر خلال 25 دقيقة
    3. محاولة إعادة تهيئة الذكاء الاصطناعي كل 30 دقيقة
    """
    global _AI_AVAILABLE, _AI_MODEL
    while True:
        time.sleep(60)
        try:
            now = time.time()

            # ─── 1. تنظيف القائمة إذا طفحت ────────────────────────
            q_size = _send_queue.qsize() if hasattr(_send_queue, 'qsize') else 0
            if q_size > _QUEUE_OVERFLOW_THRESHOLD:
                cooldown = 300  # مرة واحدة كل 5 دقائق كحد أقصى
                if now - _auto_recovery_last["clearcache"] > cooldown:
                    _auto_recovery_last["clearcache"] = now
                    # تفريغ العناصر الزائدة (نبقي آخر 50)
                    dropped = 0
                    while _send_queue.qsize() > 50:
                        try:
                            _send_queue.get_nowait()
                            _send_queue.task_done()
                            dropped += 1
                        except Exception:
                            break
                    msg = (
                        f"🤖 *إصلاح تلقائي — تنظيف القائمة*\n"
                        f"📬 كانت القائمة: `{q_size}` رسالة\n"
                        f"🗑 تم حذف: `{dropped}` رسالة قديمة\n"
                        f"✅ القائمة الآن: `{_send_queue.qsize()}` رسالة"
                    )
                    try:
                        bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
                    except Exception as _exc:
                        _log_exc(_exc)

            # ─── 2. إعادة البث إذا توقف الخبر ──────────────────────
            # BUGFIX: يفحص last_news_sent_time (آخر خبر فعلي) لا last_broadcast_time
            _bstats_ar = globals().get('_broadcast_stats', {})
            # BUGFIX: last_news_sent_time فقط — fallback لوقت الإقلاع لا last_broadcast_time
            _lns = _bstats_ar.get("last_news_sent_time") or _bot_start_time
            try:
                last_bc_ts = _lns.timestamp() if hasattr(_lns, 'timestamp') else float(_lns)
                elapsed_since = now - last_bc_ts
            except Exception:
                elapsed_since = 0
            if not bot_paused and not broadcast_paused:
                if elapsed_since > _NO_NEWS_TIMEOUT_SEC:
                    cooldown2 = 8 * 60   # مرة واحدة كل 8 دقائق
                    if now - _auto_recovery_last["forcenews"] > cooldown2:
                        _auto_recovery_last["forcenews"] = now
                        # إعادة تعيين القفل أولاً
                        _broadcast_news_lock.clear()
                        _broadcast_channels_lock.clear()
                        # FIX: حُذف مسح sent_news و global_sent — كانا يسببان spam بإعادة إرسال كل الأخبار
                        # الحل الصحيح: فك القفل فقط والسماح للدورة بالعمل بشكل طبيعي
                        _launched = _trigger_forced_broadcast("auto_recovery")
                        msg2 = (
                            f"🤖 *إصلاح تلقائي — إعادة تشغيل البث*\n"
                            f"⏱ لم يُرسَل أي خبر منذ: `{elapsed_since/60:.0f}` دقيقة\n"
                            f"🔄 تم إعادة تعيين أقفال البث\n"
                            f"{'🚀 جاري إرسال البث الآن...' if _launched else '⚠️ تعذّر تشغيل البث — راجع /debugnews'}"
                        )
                        try:
                            bot.send_message(ADMIN_ID, msg2, parse_mode="Markdown")
                        except Exception as _exc:
                            _log_exc(_exc)

            # ─── 2.5 مراقبة عدد الخيوط (thread count) ──────────────
            active_threads = threading.active_count()
            if active_threads > 220:
                # تحذير فقط — لا يمكن قتل الخيوط مباشرة
                try:
                    bot.send_message(ADMIN_ID,
                        f"⚠️ *تحذير: خيوط مفتوحة كثيرة*\n"
                        f"   عدد الخيوط الحالية: `{active_threads}`\n"
                        f"   حد Heroku: ~256\n"
                        f"   البوت سيُعيد تشغيله تلقائياً قريباً إذا وصل للحد"
                    , parse_mode="Markdown")
                except Exception as _exc:
                    _log_exc(_exc)

            # ─── 3. إعادة محاولة تهيئة الذكاء الاصطناعي ───────────
            if not _AI_AVAILABLE and GEMINI_API_KEY:
                cooldown3 = 30 * 60  # كل 30 دقيقة
                if now - _auto_recovery_last["ai_retry"] > cooldown3:
                    _auto_recovery_last["ai_retry"] = now
                    try:
                        _init_gemini()
                        if _AI_AVAILABLE:
                            try:
                                bot.send_message(ADMIN_ID,
                                    "✅ *تم تفعيل الذكاء الاصطناعي تلقائياً!*",
                                    parse_mode="Markdown")
                            except Exception as _exc:
                                _log_exc(_exc)
                    except Exception as _exc:
                        _log_exc(_exc)

        except Exception as _exc:
            _log_exc(_exc)

_start_thread_once("auto_recovery_watchdog", _auto_recovery_watchdog)

# ======== إحصائيات البث ========
_broadcast_stats = {
    "today_date": "",
    "today_news_sent": 0,
    "today_users_reached": 0,
    "total_news_all_time": 0,
    "last_broadcast_time": None,
    "last_news_sent_time": None,   # آخر مرة أُرسل فيها خبر فعلاً (لا تُحدَّث عند 0)
    "hourly_activity": {},      # {"0": N, "1": N, ..., "23": N}  — إجمالي إرسالات كل ساعة
}
_broadcast_errors = []   # آخر 30 خطأ في البث
# FIX (SSOT): كان يُنشئ Lock منفصلاً بنفس الاسم بدل استخدام قفل state.py
# الوحيد — يُبطل أي تزامن حقيقي بين هذا الملف وباقي الوحدات التي تتشارك
# قفل إحصاءات البث نفسه.
_broadcast_stats_lock = gl._broadcast_stats_lock

def _register_module(name: str, target_fn):
    """يُسجّل خيطاً جديداً للوحدة في السجل المركزي ويُشغّله."""
    t = threading.Thread(target=target_fn, daemon=True, name=name)
    t.start()
    with _module_registry_lock:
        _module_registry[name] = {
            "target":     target_fn,
            "thread":     t,
            "started_at": time.time(),
            "restarts":   0,
        }
    return t

def _restart_module(name: str) -> str:
    """
    يُعيد تشغيل وحدة بالاسم مع الحفاظ على البيانات.
    يُعيد رسالة نصية توضح نتيجة العملية.
    """
    with _module_registry_lock:
        entry = dict(_module_registry.get(name, {}))
    if not entry:
        available = ", ".join(_module_registry.keys()) or "لا شيء"
        return f"❌ لا توجد وحدة باسم `{name}`.\nالمتاح: `{available}`"
    alive  = entry["thread"].is_alive() if entry.get("thread") else False
    t      = threading.Thread(target=entry["target"], daemon=True, name=name)
    t.start()
    with _module_registry_lock:
        _module_registry[name]["thread"]     = t
        _module_registry[name]["started_at"] = time.time()
        _module_registry[name]["restarts"]  += 1
        restarts = _module_registry[name]["restarts"]
    status = "كان حياً" if alive else "كان ميتاً"
    _logger.info("🔄 _restart_module: %s | %s | إعادة #%d", name, status, restarts)
    return (
        f"✅ أُعيد تشغيل `{name}`\n"
        f"الحالة السابقة: {status}\n"
        f"إجمالي إعادات التشغيل: `{restarts}`"
    )

def _get_module_status() -> str:
    """يُعيد جدولاً نصياً بحالة كل الوحدات المسجّلة."""
    with _module_registry_lock:
        items = list(_module_registry.items())
    if not items:
        return "لا توجد وحدات مسجّلة بعد."
    lines = []
    now = time.time()
    for name, info in items:
        alive   = info["thread"].is_alive() if info.get("thread") else False
        icon    = "🟢" if alive else "🔴"
        uptime  = int(now - info.get("started_at", now))
        h, m    = uptime // 3600, (uptime % 3600) // 60
        lines.append(f"{icon} `{name}` — {h}h{m}m | إعادات: {info.get('restarts', 0)}")
    return "\n".join(lines)

# ======== كشف التكرار الذكي (Jaccard Similarity) ========
