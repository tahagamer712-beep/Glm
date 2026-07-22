# -*- coding: utf-8 -*-
"""
  db_channels.py — CRUD القنوات والمجموعات

  يُصدِّر دوال قراءة وكتابة بيانات القنوات.
  FIX: تم لفّ scheduler.add_job في try/except ونقله لدالة
       لأن _job_save_all_users يُعرَّف في db_users.py لا هنا.
"""

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء المبدوءة بـ _ لأن `import *` لا يستوردها
#      عند الاستيراد الدائري (قبل تعريف __all__ في السطر 6985 من bot_legacy).
#      هذه الأسماء مُعرَّفة مبكرًا في bot_legacy (السطور 49، 51، 189)
#      فيكون الاستيراد الصريح آمنًا حتى في حالة الاستيراد الدائري.
from bot_legacy import _log_exc, _safe_job, _logger  # noqa: F401

def _mark_dead_user(chat_id):
    """FIX C1: دالة كانت مفقودة — تُعطّل إشعارات المستخدم الميت وتُضيفه للقائمة السوداء.
    تُستدعى من _queue_worker عند فشل التسليم المتكرر."""
    try:
        uid_str = str(chat_id)
        if uid_str in users:
            users[uid_str]["notifications"] = False
        _blacklist_chat(chat_id)
    except Exception as _exc:
        _log_exc(_exc)

def _job_save_all_channels():
    _db_save_all_channels(channels_groups)
_job_save_all_channels.__name__ = "_job_save_all_channels"

# ── تسجيل مهام الـ Scheduler ──────────────────────────────────────────────────
# FIX: _job_save_all_users مُعرَّف في db_users.py وسيُتاح عبر globals() من bot_legacy
#      لأن db_users يُستورَد قبل هذا الملف في التسلسل الصحيح.
#      نلفّ كل add_job في try/except لمنع الانهيار عند خلل في الترتيب.

def _register_scheduler_jobs():
    """تسجيل مهام الـ Scheduler — تُستدعى بعد اكتمال تحميل كل الوحدات."""
    _jobs = []

    # ── مهام الحفظ الدوري ──────────────────────────────────────────────────
    # FIX: db_users يُستورَد قبل db_channels لكن هذا الملف يُنفَّذ "from bot_legacy
    # import *" أثناء استيراد دائري (bot_legacy لم يكتمل بعد)، فلا يرى
    # _job_save_all_users المُعرَّفة في db_users.py عبر globals() هنا مباشرةً.
    # نبحث عنها مباشرةً في وحدة db_users بدلاً من الاعتماد على globals().
    _job_save_fn = globals().get("_job_save_all_users")
    if not _job_save_fn:
        _db_users_mod = _sys_legacy.modules.get("db_users")
        _job_save_fn = getattr(_db_users_mod, "_job_save_all_users", None) if _db_users_mod else None
    if _job_save_fn:
        _jobs.append(("_job_save_all_users", _job_save_fn, {"minutes": 3}))
    _jobs.append(("_job_save_all_channels", _job_save_all_channels, {"minutes": 5}))

    _sg_fn = globals().get("_save_global_sent_news")
    if _sg_fn:
        _jobs.append(("_save_global_sent_news", _sg_fn, {"minutes": 5}))

    # ── مهام المراقبة والصيانة ──────────────────────────────────────────────
    for _name, _interval in [
        ("_send_admin_health_report", {"hours": 1}),
        ("_auto_db_backup",           {"hours": 6}),
        ("_crisis_room_broadcaster",  {"minutes": 2}),
        ("_politician_statement_tracker", {"hours": 2}),
        ("_foreign_intel_monitor",    {"minutes": 25}),
        ("_process_crowd_tips",       {"minutes": 10}),
    ]:
        _fn = globals().get(_name)
        if _fn:
            _jobs.append((_name, _fn, _interval))

    # ── Heartbeat و RSS ────────────────────────────────────────────────────
    _rss_fn = globals().get("_rss_prefetcher")
    if _rss_fn:
        try:
            # FIX: رُفع الفاصل من 90 ثانية إلى 300 ثانية (5 دقائق).
            # كان _rss_prefetcher ينتهي في ~153 ثانية لكن يُشغَّل كل 90 ثانية،
            # مما يسبب رسالة "maximum number of running instances reached"
            # لأن الدورة القديمة لم تنتهِ بعد. الآن الفاصل (300ث) أكبر من
            # أقصى وقت تنفيذ متوقع (~180ث) فلا تداخل ممكن.
            # misfire_grace_time=60 يعطي هامشاً إضافياً إذا تأخّر التشغيل.
            scheduler.add_job(
                _safe_job(_rss_fn), "interval", seconds=300,
                id="rss_prefetch_job", max_instances=1, coalesce=True,
                misfire_grace_time=60
            )
        except Exception as _exc:
            _log_exc(_exc)

    _hb_fn = globals().get("_send_heartbeat")
    if _hb_fn:
        try:
            scheduler.add_job(
                _safe_job(_hb_fn), "interval", minutes=10,
                id="heartbeat_job", max_instances=1, coalesce=True
            )
        except Exception as _exc:
            _log_exc(_exc)

    _pr_fn = globals().get("_prune_button_cache_db")
    if _pr_fn:
        try:
            scheduler.add_job(
                _safe_job(_pr_fn), "interval", hours=12,
                id="btn_cache_prune_job", max_instances=1, coalesce=True
            )
        except Exception as _exc:
            _log_exc(_exc)

    # ── تسجيل باقي المهام ──────────────────────────────────────────────────
    for _jname, _jfn, _interval in _jobs:
        try:
            # تحقق من عدم تكرار المهمة
            existing_ids = {j.id for j in scheduler.get_jobs()}
            if _jname not in existing_ids:
                scheduler.add_job(
                    _safe_job(_jfn), "interval",
                    id=_jname, max_instances=1, coalesce=True,
                    **_interval
                )
        except Exception as _exc:
            _log_exc(_exc)


# ── تشغيل التسجيل الآمن للمهام ────────────────────────────────────────────────
# FIX: نُشغِّل في daemon thread بعد 2 ثانية لضمان اكتمال تحميل كل الوحدات
import threading as _dch_threading

def _delayed_register():
    import time as _t
    _t.sleep(2)
    try:
        _register_scheduler_jobs()
        _logger.info("✅ db_channels: تم تسجيل مهام الـ Scheduler")
    except Exception as _exc:
        _log_exc(_exc)

_dch_threading.Thread(target=_delayed_register, daemon=True, name="SchedulerJobsReg").start()
