# -*- coding: utf-8 -*-
"""
  safe_send.py — safe_send_message/audio/photo

  يُصدِّر دوال الإرسال الآمن مع إعادة المحاولة.
  """

import sys as _sys_legacy
import os
# FIX: إضافة _re كاسم مستعار لـ re لأن دوال الإرسال الآمن تستخدم _re.search
# بينما bot_legacy يستورد re باسم _re_san
import re as _re  # noqa: F401 — يُصلح NameError في safe_send_message (retry after X)
import time        # noqa: F401 — قد لا يكون مُستورَداً من bot_legacy في بعض الحالات
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: _exponential_backoff مُعرَّفة في utils.py (تُستورَد بعد safe_send في bot_legacy)
# نُعرِّف نسخة محلية تُفوَّض لـ utils عند توفره
def _exponential_backoff(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    import sys as _s
    _u = _s.modules.get("utils")
    if _u and hasattr(_u, "_exponential_backoff"):
        return _u._exponential_backoff(attempt, base, cap)
    return min(cap, base * (2 ** attempt))

def split_message(text, max_len=4096):
    """FIX-6: يُقسِّم الرسائل الطويلة عند فاصل السطر."""
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        cut = text.rfind('\n', 0, max_len)
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    return parts


def safe_send_message(chat_id, text, max_retries: int = 4, **kwargs):
    """
    FIX-6: إرسال آمن مع تقسيم تلقائي + FloodWait صحيح + backoff.
    """
    last_err = None
    parts = split_message(text)
    results = []
    for part in parts:
        for attempt in range(max_retries):
            try:
                msg = bot.send_message(chat_id, part, **kwargs)
                time.sleep(0.04)
                results.append(msg)
                break
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "Too Many Requests" in err_str or "Flood" in err_str:
                    try:
                        wait = int(_re.search(r'retry after (\d+)', err_str, _re.I).group(1)) + 5
                    except Exception:
                        wait = 35
                    _logger.warning(f"FloodWait {wait}s — chat {chat_id}")
                    time.sleep(wait)
                    continue
                if any(x in err_str for x in ("bot was blocked", "user is deactivated",
                                               "chat not found", "PEER_ID_INVALID")):
                    _logger.info(f"chat {chat_id} غير متاح — تجاوز")
                    return None
                if "Message is not modified" in err_str:
                    break
                if "can't parse" in err_str or "parse entities" in err_str:
                    plain = {k: v for k, v in kwargs.items() if k != "parse_mode"}
                    try: results.append(bot.send_message(chat_id, part, **plain))
                    except Exception: pass
                    break
                wait = _exponential_backoff(attempt)
                _logger.warning(f"safe_send_message محاولة {attempt+1}/{max_retries} — {e} — انتظار {wait:.0f}s")
                time.sleep(wait)
        else:
            _logger.error(f"safe_send_message فشل نهائي — chat {chat_id}: {last_err}")
    return results[0] if len(results) == 1 else (results if results else None)


def safe_send_audio(chat_id, audio, max_retries: int = 3, **kwargs):
    """إرسال ملف صوتي آمن مع retry + fallback إلى رسالة نصية."""
    caption = kwargs.pop("caption", "")
    last_err = None
    for attempt in range(max_retries):
        try:
            return bot.send_audio(chat_id, audio, caption=caption, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e)
            if any(x in err_str for x in ("bot was blocked", "user is deactivated",
                                           "chat not found")):
                return None
            if "429" in err_str or "Flood" in err_str:
                time.sleep(30)
                continue
            wait = _exponential_backoff(attempt)
            _logger.warning(f"safe_send_audio محاولة {attempt+1}/{max_retries} — انتظار {wait:.0f}s")
            time.sleep(wait)
    # Fallback: نص بدلاً من صوت
    _logger.error(f"safe_send_audio فشل — fallback نصي — {last_err}")
    if caption:
        try:
            return safe_send_message(chat_id, f"🔊 {caption}")
        except Exception as _exc:
            _log_exc(_exc)
    return None


def safe_send_photo(chat_id, photo, max_retries: int = 3, **kwargs):
    """إرسال صورة آمن مع retry + fallback إلى رسالة نصية."""
    caption = kwargs.pop("caption", "")
    last_err = None
    for attempt in range(max_retries):
        try:
            return bot.send_photo(chat_id, photo, caption=caption, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e)
            if any(x in err_str for x in ("bot was blocked", "user is deactivated",
                                           "chat not found")):
                return None
            if "429" in err_str or "Flood" in err_str:
                time.sleep(30)
                continue
            wait = _exponential_backoff(attempt)
            _logger.warning(f"safe_send_photo محاولة {attempt+1}/{max_retries} — انتظار {wait:.0f}s")
            time.sleep(wait)
    _logger.error(f"safe_send_photo فشل — fallback نصي — {last_err}")
    if caption:
        try:
            return safe_send_message(chat_id, f"🖼 {caption}")
        except Exception as _exc:
            _log_exc(_exc)
    return None

# ======== تحديث الإحصائيات ========
_stats_lock = threading.Lock()
