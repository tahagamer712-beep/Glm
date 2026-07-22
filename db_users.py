# -*- coding: utf-8 -*-
"""
  db_users.py — CRUD المستخدمين

  يُصدِّر دوال قراءة وكتابة بيانات المستخدمين.
  FIX: تم تغليف الأوامر المُنفَّذة عند الاستيراد في try/except
       لأن _migrate_users_from_json وأخواتها يعتمدن على DB مُهيَّأة مسبقاً.
"""

import sys as _sys_legacy
import os
import threading

# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الأساسية — ضمان للاستيراد الدائري
from bot_legacy import _logger, _log_exc, _db_lock, _db_conn, _db_cursor, _users_rlock, _AI_EXECUTOR  # noqa: F811

def save_users():
    """دالة مساعدة: حفظ بيانات المستخدمين."""
    save_json(USERS_FILE, users)

def _save_users_soon():
    """حفظ بيانات المستخدمين في الخلفية (non-blocking)."""
    try:
        _AI_EXECUTOR.submit(save_users)
    except Exception as _exc:
        _log_exc(_exc)


def _migrate_users_from_json():
    """
    FIX: كانت هذه الدالة تُستدعى عند الاستيراد لكنها لم تكن مُعرَّفة في أي
    مكان — نقل لمرة واحدة بيانات المستخدمين من ملف JSON القديم (USERS_FILE)
    إلى جدول users_store في SQLite، بدون الكتابة فوق بيانات أحدث موجودة
    فعلاً في SQLite (INSERT OR IGNORE).
    """
    try:
        _json_users = load_json(USERS_FILE, {})
        if not isinstance(_json_users, dict) or not _json_users:
            return
        with _db_lock:
            for _uid, _data in _json_users.items():
                try:
                    _db_cursor.execute(
                        "INSERT OR IGNORE INTO users_store (uid, data) VALUES (?, ?)",
                        (str(_uid), json.dumps(_data, ensure_ascii=False)),
                    )
                except Exception:
                    continue
            _db_conn.commit()
        _logger.info("✅ _migrate_users_from_json: تمت مراجعة %d مستخدم من JSON", len(_json_users))
    except Exception as _exc:
        _log_exc(_exc, "_migrate_users_from_json")


def _init_button_cache_table():
    """
    FIX: كانت تُستدعى عند الاستيراد لكن غير مُعرَّفة — جدول button_cache_store
    يُنشَأ فعلياً في bot_helpers.py عند التحميل، لذا هذه دالة تأكيد idempotent
    فقط (لا ضرر إذا استُدعيت أكثر من مرة).
    """
    try:
        with _db_lock:
            _db_cursor.execute("""
                CREATE TABLE IF NOT EXISTS button_cache_store (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                )
            """)
            _db_conn.commit()
    except Exception as _exc:
        _log_exc(_exc, "_init_button_cache_table")

# ── تهيئة قاعدة البيانات عند الاستيراد ─────────────────────────────────────
# FIX: كل استدعاء مُغلَّف في try/except لمنع انهيار الاستيراد عند أي خطأ
try:
    _migrate_users_from_json()
except Exception as _exc:
    _log_exc(_exc)

try:
    _init_button_cache_table()
except Exception as _exc:
    _log_exc(_exc)

try:
    _load_global_sent_news()
except Exception as _exc:
    _log_exc(_exc)

# FIX: نتحقق إذا كانت users مُحمَّلة مسبقاً (من bot_legacy) قبل إعادة التحميل
# لتجنب استبدال users المُحمَّل في bot_legacy بنسخة جديدة
try:
    _fresh_users = _db_load_users()
    if _fresh_users and len(_fresh_users) >= len(globals().get("users", {})):
        # نُحدِّث users العالمية في bot_legacy مباشرةً عبر sys.modules
        import sys as _sys_du
        _bl_mod = _sys_du.modules.get("bot_legacy")
        if _bl_mod is not None:
            _bl_mod.users = _fresh_users
            users = _fresh_users  # تحديث النسخة المحلية أيضاً
except Exception as _exc:
    _log_exc(_exc)

# ── قفل thread-safe للوصول لـ users ──────────────────────────────────────────
# FIX BUG-01: إنشاء _users_rlock إذا لم يكن موجوداً
try:
    _ = _users_rlock  # اختبار الوجود
except NameError:
    _users_rlock = threading.RLock()
    try:
        import sys as _sys_du2
        _bl_mod2 = _sys_du2.modules.get("bot_legacy")
        if _bl_mod2:
            _bl_mod2._users_rlock = _users_rlock
    except Exception:
        pass

def _job_save_all_users():
    _db_save_all_users(users)
_job_save_all_users.__name__ = "_job_save_all_users"
