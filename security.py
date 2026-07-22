# -*- coding: utf-8 -*-
"""
  security.py — sanitize input + is_admin + SIGTERM

  يُصدِّر دوال الأمان وتنظيف المدخلات والصلاحيات.
  """

import sys as _sys_legacy
import os
import re as _sec_re
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: تأكيد وجود _HTML_TAG_RE و _CTRL_RE (مُعرَّفتان في bot_legacy مبكراً)
if "_HTML_TAG_RE" not in dir():
    _HTML_TAG_RE = _sec_re.compile(r'<[^>]{0,200}>', _sec_re.DOTALL)
if "_CTRL_RE" not in dir():
    _CTRL_RE = _sec_re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]')
if "_FF" not in dir():
    _FF: dict = {}

def _sanitize_input(text: str, max_len: int = 1000) -> str:
    """Strip HTML tags, control characters, and truncate user-supplied text."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    text = _HTML_TAG_RE.sub('', text)          # remove HTML tags
    text = _CTRL_RE.sub('', text)              # remove control chars
    text = text.replace('\ufffd', '')          # remove Unicode replacement char
    return text[:max_len]


# =============================================================================
# HEROKU FIX v4: Feature Flags — toggle features without re-deploying
# Set env var FF_<NAME>=0 on Heroku to disable a feature instantly
# =============================================================================
import os as _os_ff
_FF: dict = {
    # ── أوامر البث والأخبار ──────────────────────────────────────────────────
    "broadcast":      _os_ff.getenv("FF_BROADCAST",      "1") == "1",
    "breaking_news":  _os_ff.getenv("FF_BREAKING",       "1") == "1",
    "sports":         _os_ff.getenv("FF_SPORTS",         "1") == "1",
    "voice":          _os_ff.getenv("FF_VOICE",          "1") == "1",
    "crisis":         _os_ff.getenv("FF_CRISIS",         "1") == "1",
    # ── الذكاء الاصطناعي ─────────────────────────────────────────────────────
    "ai_summary":     _os_ff.getenv("FF_AI_SUMMARY",     "1") == "1",
    "ai_factcheck":   _os_ff.getenv("FF_AI_FACTCHECK",   "1") == "1",
    "ai_why":         _os_ff.getenv("FF_AI_WHY",         "1") == "1",
    "ai_duel":        _os_ff.getenv("FF_AI_DUEL",        "1") == "1",
    "ask":            _os_ff.getenv("FF_ASK",            "1") == "1",
    "verify":         _os_ff.getenv("FF_VERIFY",         "1") == "1",
    "profile":        _os_ff.getenv("FF_PROFILE",        "1") == "1",
    "influence":      _os_ff.getenv("FF_INFLUENCE",      "1") == "1",
    "v5":             _os_ff.getenv("FF_V5",             "1") == "1",
    # ── الأوامر والخدمات ─────────────────────────────────────────────────────
    "weather":        _os_ff.getenv("FF_WEATHER",        "1") == "1",
    "economy":        _os_ff.getenv("FF_ECONOMY",        "1") == "1",
    "crypto":         _os_ff.getenv("FF_CRYPTO",         "1") == "1",
    "search":         _os_ff.getenv("FF_SEARCH",         "1") == "1",
    "timeline":       _os_ff.getenv("FF_TIMELINE",       "1") == "1",
    # ── النظام والأداء ───────────────────────────────────────────────────────
    "quiet_hours":    _os_ff.getenv("FF_QUIET_HOURS",    "1") == "1",
    "rss_etag":       _os_ff.getenv("FF_RSS_ETAG",       "1") == "1",
    "title_dedup":    _os_ff.getenv("FF_TITLE_DEDUP",    "1") == "1",
    "feed_health":    _os_ff.getenv("FF_FEED_HEALTH",    "1") == "1",
    "bc_checkpoint":  _os_ff.getenv("FF_BC_CHECKPOINT",  "1") == "1",
}
_logger_ff = __import__("logging").getLogger("feature_flags")
_logger_ff.info("Feature flags loaded: %s", {k: v for k, v in _FF.items() if not v})


# =============================================================================
# HEROKU FIX v3: SIGTERM handler
# Heroku sends SIGTERM 10 seconds before killing the dyno.
# We flush all state and send an emergency backup to Telegram before dying.
# =============================================================================
import signal as _signal

_SIGTERM_RECEIVED = False


# ─── مساعد تسجيل الاستثناءات الصامتة ───────────────────────────────────────
def _handle_sigterm(signum, frame):
    global _SIGTERM_RECEIVED
    if _SIGTERM_RECEIVED:
        return
    _SIGTERM_RECEIVED = True
    _logger.warning("⚠️ SIGTERM — saving state and exiting quickly")
    # 1) Flush all in-memory state to SQLite (fast — no network)
    try:
        _save_global_sent_news()
    except Exception as _exc:
        _log_exc(_exc)
    try:
        _db_save_all_users(users)
    except Exception as _exc:
        _log_exc(_exc)
    try:
        _save_all_button_caches()
    except Exception as _exc:
        _log_exc(_exc)
    try:
        with _db_lock:
            _db_conn.commit()
    except Exception as _exc:
        _log_exc(_exc)
    # 2) Notify admin + backup in background thread (لا يُعيق الخروج)
    # FIX R12: الإرسال لتلغرام كان يُعيق الخروج > 30s فيُقتل البوت بـ SIGKILL
    # الحل: نُشغّل العمليات الشبكية في خيط خلفي بمهلة 8 ثوانٍ فقط
    def _bg_notify():
        try:
            bot.send_message(
                ADMIN_ID,
                "🔴 *البوت يُوقَف (SIGTERM)*\n✅ تم حفظ كل البيانات",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        try:
            _send_backup_to_channel()
        except Exception:
            pass
    import threading as _thr_sig
    _t = _thr_sig.Thread(target=_bg_notify, daemon=True, name="SigTermNotify")
    _t.start()
    _t.join(timeout=8)   # أقصى 8 ثوانٍ للشبكة — Heroku يعطي 30s قبل SIGKILL
    import sys as _sys
    _sys.exit(0)

# Register AFTER functions are defined — see bottom of file
import os
import json
import datetime
import time
import sqlite3
import threading
import queue
import asyncio
import tempfile
import math
import logging
import traceback
import functools
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor, as_completed
import re as _re

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING SYSTEM — احترافي مع تدوير الملف
# ═══════════════════════════════════════════════════════════════════════════════
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATE   = "%Y-%m-%d %H:%M:%S"

# Logger رئيسي
_logger = logging.getLogger("IraqNow")

# ── BUG-07 FIX: يمنع تراكم الـ threads عند إعادة التشغيل ────────────────
