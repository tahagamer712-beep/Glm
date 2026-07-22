# -*- coding: utf-8 -*-
"""
  db_cache.py — button_cache + broadcast checkpoint

  يُصدِّر نظام التخزين المؤقت ونقاط تفتيش البث.
  """

import sys as _sys_legacy
import os
import threading as _dbc_threading
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الأساسية — ضمان للاستيراد الدائري
from bot_legacy import _logger, _log_exc, _db_lock, _db_conn, _db_cursor  # noqa: F811

# FIX: تأكيد وجود متغيرات الـ title dedup (قد تأتي من bot_legacy)
if "_title_seen_cache" not in dir():
    _title_seen_cache: dict = {}
if "_title_seen_lock" not in dir():
    _title_seen_lock = _dbc_threading.Lock()
if "_TITLE_DEDUP_TTL" not in dir():
    _TITLE_DEDUP_TTL = 6 * 3600

def _restore_button_caches():
    global _why_key_cache, _next_key_cache, _intel_key_cache
    global _ctx_key_cache, _bm_key_cache, _news_summary_cache, _story_key_cache
    global _duel_key_cache, _dna_key_cache, _factcheck_key_cache
    _why_key_cache.update(_load_button_cache("why"))
    _next_key_cache.update(_load_button_cache("next"))
    _intel_key_cache.update(_load_button_cache("intel"))
    _ctx_key_cache.update(_load_button_cache("ctx"))
    _bm_key_cache.update(_load_button_cache("bm"))
    _duel_key_cache.update(_load_button_cache("duel"))
    _dna_key_cache.update(_load_button_cache("dna"))
    _news_summary_cache.update(_load_button_cache("sum"))
    for k, v in _load_button_cache("story").items():
        _story_key_cache[k] = v if isinstance(v, str) else str(v)
    _factcheck_key_cache.update(_load_button_cache("fc"))
    import logging as _lg2
    _lg2.getLogger(__name__).info(
        "Caches restored: why=%d next=%d ctx=%d bm=%d sum=%d story=%d fc=%d",
        len(_why_key_cache), len(_next_key_cache), len(_ctx_key_cache),
        len(_bm_key_cache), len(_news_summary_cache),
        len(_story_key_cache), len(_factcheck_key_cache)
    )


# _restore_button_caches() — MOVED: called after _factcheck_key_cache is declared (line ~18920)


# =============================================================================
# HEROKU FIX v4: Content dedup by title hash
# Prevents the same news story from being sent twice when multiple RSS sources
# publish it with slightly different URLs.
# =============================================================================
_title_seen_cache: dict = {}       # normalized_hash -> (timestamp, full_title)
_title_seen_lock  = threading.Lock()
_TITLE_DEDUP_TTL  = 6 * 3600       # FIX: 6 ساعات (كان 24h → يحجب كل الأخبار بعد أول دورة)

# =============================================================================
# HEROKU FIX v4: RSS Feed Health Scoring
# Auto-disables unreliable feeds after repeated failures.
# =============================================================================
_feed_health: dict  = {}    # url -> {"ok": int, "fail": int, "disabled": bool}
_feed_health_lock   = threading.Lock()
_FEED_FAIL_RATIO    = 0.70  # disable if 70%+ of last N fetches failed
_FEED_MIN_SAMPLES   = 10    # need at least 10 samples before disabling

def _save_all_button_caches():
    """Save all 10 button caches to SQLite in one call (used by SIGTERM and atexit)."""
    try:
        _save_button_cache("why",   _why_key_cache)
        _save_button_cache("next",  _next_key_cache)
        _save_button_cache("intel", _intel_key_cache)
        _save_button_cache("ctx",   _ctx_key_cache)
        _save_button_cache("bm",    _bm_key_cache)
        _save_button_cache("duel",  _duel_key_cache)
        _save_button_cache("dna",   _dna_key_cache)
        _save_button_cache("sum",   _news_summary_cache)
        _save_button_cache("story", _story_key_cache)
        _save_button_cache("fc",    _factcheck_key_cache)
    except Exception as _sae:
        _logger.debug("_save_all_button_caches: %s", _sae)


