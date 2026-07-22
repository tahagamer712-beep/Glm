# -*- coding: utf-8 -*-
"""
  health_monitor.py — مراقبة RAM + CPU + threads

  يُصدِّر دوال مراقبة صحة النظام.
  """

import sys as _sys_legacy
import os
import threading as _hm_threading
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: _broadcast_log_lock / _broadcast_call_log — تأكيد وجودهما (قد تأتيان من bot_legacy)
if "_broadcast_log_lock" not in dir():
    _broadcast_log_lock = _hm_threading.Lock()
if "_broadcast_call_log" not in dir():
    _broadcast_call_log: list = []
# FIX: _sys_health — تأكيد وجوده (قد يأتي من bot_legacy أو error_tracker)
if "_sys_health" not in dir():
    import time as _hm_time
    _sys_health: dict = {
        "ram_pct": 0.0, "cpu_pct": 0.0, "disk_pct": 0.0,
        "start_ts": _hm_time.time(), "recoveries": 0,
    }

def _log_broadcast_cycle(count_sent: int):
    """يُسجّل نتيجة دورة بث (عدد الأخبار المرسلة)."""
    with _broadcast_log_lock:
        _broadcast_call_log.append((time.time(), count_sent))
        if len(_broadcast_call_log) > 50:
            del _broadcast_call_log[:-50]

def _check_broadcast_health() -> dict:
    """
    يُقيّم صحة نظام البث:
    - هل يعمل بانتظام؟
    - آخر بث
    - متوسط الأخبار لكل دورة
    """
    now = time.time()
    with _broadcast_log_lock:
        log = list(_broadcast_call_log)
    if not log:
        return {"status": "unknown", "last_run_ago": None, "avg_per_cycle": 0}
    last_ts, _ = log[-1]
    ago_secs    = int(now - last_ts)
    avg_sent    = sum(c for _, c in log) / len(log)
    zero_cycles = sum(1 for _, c in log[-5:] if c == 0)  # آخر 5 دورات بصفر
    if ago_secs > 1200:        # أكثر من 20 دقيقة بلا بث
        status = "stopped"
    elif zero_cycles >= 4:     # 4 من 5 دورات فارغة
        status = "dry"
    else:
        status = "healthy"
    return {
        "status":        status,
        "last_run_ago":  ago_secs,
        "avg_per_cycle": round(avg_sent, 1),
        "total_cycles":  len(log),
    }


# ======== قفل تداخل دورات البث ========
# FIX (SSOT): كان هذا الملف يُنشئ Event منفصل بنفس الاسم بدل استخدام الكائن
# الوحيد في state.py — النتيجة أن مراقبة health_monitor لحالة "البث مشغول"
# كانت تفحص قفلاً لا يضبطه أحد أبداً (bot_scheduled_jobs يستخدم قفل state
# الحقيقي)، فتُصبح مراقبة التعليق/split-brain عديمة الفائدة عملياً.
_broadcast_news_lock     = gl._broadcast_news_lock
_broadcast_channels_lock = gl._broadcast_channels_lock
_broadcast_lock_ts      = [0.0]               # وقت بدء دورة البث الحالية
_BROADCAST_MAX_SECS     = 300                 # أقصى مدة لدورة بث واحدة (5 دقائق — كان 90ث وكان يقطع البث الطبيعي)
_bot_start_time         = time.time()         # وقت إقلاع البوت — يُستخدم كمرجع إذا لم يُرسَل أي خبر بعد

_broadcast_ch_lock_ts   = [0.0]               # وقت بدء دورة بث القنوات


# ── مُنظّم البث الإجباري: يمنع تشغيل أكثر من دورة واحدة كل 5 دقائق ──
_force_bcast_lock = threading.Lock()
_force_bcast_last = [0.0]

def _trigger_forced_broadcast(source: str) -> bool:
    """الدالة الوحيدة المسموح لها بتشغيل دورة بث إجبارية."""
    with _force_bcast_lock:
        _now_fb = time.time()
        if _now_fb - _force_bcast_last[0] < 300:
            _logger.debug("🔒 [%s] throttled — آخر بث إجباري منذ %.0fث", source, _now_fb - _force_bcast_last[0])
            return False
        _force_bcast_last[0] = _now_fb
    _logger.warning("🔄 [%s] يُطلق دورة بث إجبارية", source)
    _bc_fn = globals().get('broadcast_news')
    if _bc_fn:
        try:
            _safe_job(_bc_fn)()
        except Exception as _exc:
            _log_exc(_exc)
    return True

def _broadcast_watchdog():
    """خيط مراقبة قوي للبث."""
    _last_forced = [0.0]
    while True:
      time.sleep(15)
      try:
          now = time.time()
          if _broadcast_news_lock.is_set():
              elapsed = now - _broadcast_lock_ts[0]
              if elapsed > _BROADCAST_MAX_SECS:
                  _broadcast_news_lock.clear()
                  _logger.warning("⚠️ watchdog: بث الأخبار علق %.0fث — تم إعادة التعيين", elapsed)
                  try:
                      bot.send_message(ADMIN_ID,
                          f"⚠️ watchdog: بث الأخبار علق {elapsed:.0f}ث — تم إعادة التعيين")
                  except Exception as _exc:
                      _log_exc(_exc)
              # FIX: elif (not if) — لا نقتل العملية في نفس الـ iteration اللي نُصفّر فيها القفل
              # القفل تُصفّر أعلاه عند > _BROADCAST_MAX_SECS، هذا الشرط لن يُنفَّذ أبداً في نفس الدورة
              elif elapsed > 1200:
                  _logger.critical("☠️ watchdog: thread معلّق %.0fث — إعادة تشغيل العملية", elapsed)
                  try:
                      bot.send_message(ADMIN_ID,
                          f"☠️ thread البث معلّق {elapsed:.0f}ث — إعادة تشغيل العملية تلقائياً")
                  except Exception:
                      pass
          if _broadcast_channels_lock.is_set():
              elapsed2 = now - _broadcast_ch_lock_ts[0]
              if elapsed2 > _BROADCAST_MAX_SECS:
                  _broadcast_channels_lock.clear()
              # FIX: elif — لا نقتل العملية بعد التصفير مباشرة
              elif elapsed2 > 1200:
                  try:
                      _logger.critical("☠️ watchdog: channels lock عالق %.0fث", elapsed2)
                  except Exception:
                      pass
          try:
              _sched = globals().get('scheduler')
              if _sched is not None:
                  _sched_job = _sched.get_job("broadcast_news_job")
                  if _sched_job is None and not bot_paused and not broadcast_paused:
                      _logger.error("❌ broadcast_news_job اختفى — يُعاد تسجيله")
                      _sched.add_job(
                          _safe_job(broadcast_news), 'interval',
                          seconds=60, id="broadcast_news_job",
                          replace_existing=True, max_instances=1,
                          misfire_grace_time=30, coalesce=True
                      )
                      try:
                          bot.send_message(ADMIN_ID, "🔧 watchdog: أعاد تسجيل broadcast_news_job")
                      except Exception:
                          pass
          except Exception as _exc:
              _log_exc(_exc)
          _bstats = globals().get('_broadcast_stats', {})
          _lns_wd = _bstats.get("last_news_sent_time") or _bot_start_time
          if not bot_paused and not broadcast_paused:
              try:
                  _lns_wd_ts = _lns_wd.timestamp() if hasattr(_lns_wd, 'timestamp') else float(_lns_wd)
                  _elapsed_since = now - _lns_wd_ts
                  if _elapsed_since > 600 and now - _last_forced[0] > 600:
                      _last_forced[0] = now
                      _broadcast_news_lock.clear()
                      # FIX: حُذف مسح sent_news — كان يسبب spam بإعادة إرسال كل الأخبار
                      _trigger_forced_broadcast("broadcast_watchdog")
                      _logger.warning("\ud83d\udd04 watchdog: أطلق دورة بث تلقائية")
              except Exception as _exc:
                  _log_exc(_exc)
      except Exception as _exc:
          _log_exc(_exc)

_start_thread_once("broadcast_watchdog", _broadcast_watchdog)


def _record_broadcast_stat(users_reached=0, news_count=0):
    with _broadcast_stats_lock:
      today = str(datetime.date.today())
      if _broadcast_stats["today_date"] != today:
          _broadcast_stats["today_date"] = today
          _broadcast_stats["today_news_sent"] = 0
          _broadcast_stats["today_users_reached"] = 0
      _broadcast_stats["today_news_sent"] += news_count
      _broadcast_stats["today_users_reached"] += users_reached
      _broadcast_stats["total_news_all_time"] += news_count
      _broadcast_stats["last_broadcast_time"] = time.time()  # float timestamp للـ watchdog
      if news_count > 0:
          _broadcast_stats["last_news_sent_time"] = time.time()  # يُحدَّث فقط عند إرسال خبر فعلي
      # تتبع ساعات الذروة
      hour_key = str(_now_sa().hour)
      hourly = _broadcast_stats.setdefault("hourly_activity", {})
      hourly[hour_key] = hourly.get(hour_key, 0) + users_reached

def _get_sys_metrics() -> dict:
    """يُعيد مقاييس النظام الحالية بدون تعليق."""
    ram = cpu = disk = 0.0
    if _PSUTIL_OK:
      # FIX: على Termux (Android) بعض استدعاءات psutil تحاول قراءة /proc/stat
      # أو /proc/meminfo وتفشل بـ PermissionError — نُعالج كل حالة بشكل مستقل
      # حتى لا يُوقف فشل CPU قراءة RAM والعكس.
      try:
          ram = _psutil.virtual_memory().percent
      except Exception:
          ram = 0.0
      try:
          # interval=0 بدل 0.5 لتجنب تعليق الـ thread 0.5 ثانية + أقل استهلاكاً لـ /proc/stat
          cpu = _psutil.cpu_percent(interval=0)
      except (PermissionError, OSError):
          # Termux: /proc/stat محمي — نتجاهل CPU بصمت بدون تسجيل
          cpu = 0.0
      except Exception:
          cpu = 0.0
      try:
          disk = _psutil.disk_usage('/').percent
      except Exception:
          disk = 0.0
    else:
      # fallback: /proc/meminfo للنظم التي لا تملك psutil
      try:
          with open("/proc/meminfo") as _mf:
              lines = {l.split(':')[0]: l.split(':')[1].strip() for l in _mf}
          _total = int(lines.get("MemTotal","0 kB").split()[0])
          _avail = int(lines.get("MemAvailable","0 kB").split()[0])
          if _total > 0:
              ram = (_total - _avail) / _total * 100
      except Exception:
          ram = 0.0
    return {"ram_pct": ram, "cpu_pct": cpu, "disk_pct": disk}

def _auto_memory_cleanup():
    """يُطلق garbage collector ويُنظف الكاشات الكبيرة عند ارتفاع الذاكرة."""
    import gc
    gc.collect()
    now = time.time()
    # تنظيف _AI_CACHE: المنتهية أولاً، ثم الأقدم
    with _AI_CACHE_LOCK:
      if len(_AI_CACHE) > 500:
          expired = [k for k, (_, t) in _AI_CACHE.items() if now - t > _AI_CACHE_TTL]
          for k in expired:
              _AI_CACHE.pop(k, None)
          if len(_AI_CACHE) > 400:
              oldest = sorted(_AI_CACHE.items(), key=lambda x: x[1][1])[:200]
              for k, _ in oldest:
                  _AI_CACHE.pop(k, None)
    # تنظيف _AI_SUMMARY_CACHE بنفس الأسلوب
    with _AI_SUMMARY_LOCK:
      if len(_AI_SUMMARY_CACHE) > 200:
          expired_s = [k for k, (_, t) in _AI_SUMMARY_CACHE.items() if now - t > _AI_SUMMARY_TTL]
          for k in expired_s:
              _AI_SUMMARY_CACHE.pop(k, None)
          if len(_AI_SUMMARY_CACHE) > 150:
              oldest_s = sorted(_AI_SUMMARY_CACHE.items(), key=lambda x: x[1][1])[:80]
              for k, _ in oldest_s:
                  _AI_SUMMARY_CACHE.pop(k, None)
    # تنظيف _news_summary_cache
    if len(_news_summary_cache) > 1000:
      oldest = list(_news_summary_cache.keys())[:300]
      for k in oldest:
          _news_summary_cache.pop(k, None)
    _logger.info("🧹 auto_memory_cleanup: تنظيف ذاكرة تام")
    _sys_health["recoveries"] += 1

def _system_health_monitor():
    """
    خيط مراقبة النظام — يعمل كل 60 ثانية.
    يفحص RAM/CPU ويتخذ إجراءات تعافي تلقائية عند تجاوز الحدود.
    """
    _WARN_RAM  = 85.0   # % — تحذير
    _CRIT_RAM  = 92.0   # % — تنظيف فوري
    _WARN_CPU  = 90.0   # % — تحذير فقط (لا يمكن التحكم فيه)
    _notified_ram = False
    while True:
      time.sleep(60)
      try:
          m = _get_sys_metrics()
          _sys_health.update(m)
          ram = m["ram_pct"]
          cpu = m["cpu_pct"]
          # ── RAM حرجة: تنظيف فوري ──────────────────────────────
          if ram > _CRIT_RAM:
              _logger.warning("🔴 RAM حرجة %.1f%% — بدء التنظيف التلقائي", ram)
              _auto_memory_cleanup()
              _notified_ram = False
              try:
                  bot.send_message(
                      ADMIN_ID,
                      f"🔴 *تحذير: RAM حرجة* `{ram:.1f}%`\n"
                      f"⚙️ تم تشغيل التنظيف التلقائي للذاكرة.",
                      parse_mode="Markdown"
                  )
              except Exception as _exc:
                  _log_exc(_exc)
              # HEROKU FIX v2: force self-restart if RAM still critical after cleanup
              time.sleep(15)
              try:
                  m2 = _get_sys_metrics()
                  if m2["ram_pct"] > 90:
                      _logger.warning("🚨 RAM still %.1f%% after cleanup — self-restart", m2["ram_pct"])
                      try:
                          bot.send_message(ADMIN_ID, "🚨 *RAM لا تزال حرجة بعد التنظيف — إعادة تشغيل تلقائي*", parse_mode="Markdown")
                      except Exception as _exc:
                          _log_exc(_exc)
                      _logger.warning("🔄 RAM حرجة — حفظ البيانات قبل إعادة التشغيل...")
                      try:
                          _db_save_all_users(users)
                          _db_save_all_channels(channels_groups)
                          _save_global_sent_news()
                          # FIX: ينتظر اكتمال المهام الجارية بحد أقصى 10 ثوانٍ
                          # بدل قطعها فوراً بـ wait=False.
                          _sd_t = _hm_threading.Thread(target=lambda: scheduler.shutdown(wait=True), daemon=True)
                          _sd_t.start()
                          _sd_t.join(10)
                      except Exception as _save_exc:
                          _logger.error("خطأ في الحفظ قبل الـ restart: %s", _save_exc)
                      time.sleep(2)
                      import os as _os, sys as _sys
                      _os.execv(_sys.executable, [_sys.executable] + _sys.argv)
              except Exception as _re:
                  _logger.debug("self-restart failed: %s", _re)
          # ── RAM مرتفعة: تحذير مبكر ────────────────────────────
          elif ram > _WARN_RAM and not _notified_ram:
              _notified_ram = True
              try:
                  bot.send_message(
                      ADMIN_ID,
                      f"⚠️ *تحذير: RAM مرتفعة* `{ram:.1f}%`\n"
                      f"🖥 CPU: `{cpu:.1f}%`",
                      parse_mode="Markdown"
                  )
              except Exception as _exc:
                  _log_exc(_exc)
          elif ram < 75:
              _notified_ram = False
      except Exception as _she:
          _logger.debug("_system_health_monitor: %s", _she)

threading.Thread(
    target=_system_health_monitor,
    daemon=True,
    name="SystemHealthMonitor"
).start()

# ── نسخ احتياطي تلقائي لقاعدة البيانات ────────────────────────────────────
