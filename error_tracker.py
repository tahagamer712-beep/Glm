# -*- coding: utf-8 -*-
"""
  error_tracker.py — تتبع الأخطاء + timeline

  يُصدِّر نظام تتبع الأخطاء والتنبؤ بها.
  """

import sys as _sys_legacy
import os
import threading as _et_threading
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# ── FIX: تعريف محلي للأسماء المتقاطعة عبر الوحدات ─────────────────────────
# _broadcast_errors و _broadcast_stats_lock قد تأتي من bot_legacy (بعد إصلاح __all__)
# نُعرِّفها محلياً احتياطاً في حال عدم توفرها في namespace هذه الوحدة
if "_broadcast_errors" not in dir():
    _broadcast_errors: list = []
if "_broadcast_stats_lock" not in dir():
    _broadcast_stats_lock = _et_threading.Lock()

def _classify_error(err_str: str) -> str:
    """نسخة محلية — تُفوَّض لـ queue_worker عند توفره."""
    import sys as _s
    _qw = _s.modules.get("queue_worker")
    if _qw and hasattr(_qw, "_classify_error"):
        return _qw._classify_error(err_str)
    e = (err_str or "").lower()
    if "429" in e or "flood" in e:         return "rate_limit"
    if "blocked" in e or "deactivated" in e: return "delivery"
    if "timeout" in e or "connection" in e: return "network"
    return "unknown"

def _record_broadcast_error(err_msg):
    with _broadcast_stats_lock:
        ts = _now_sa().strftime("%Y-%m-%d %H:%M:%S")
        _broadcast_errors.append(f"[{ts}] {err_msg}")
        if len(_broadcast_errors) > 30:
            _broadcast_errors.pop(0)

# ═══════════════════════════════════════════════════════════════════════════════
# SELF-HEALING ENGINE v2.0 — مراقبة النظام، التعافي التلقائي، الصيانة الاستباقية
# ═══════════════════════════════════════════════════════════════════════════════

# ── محاولة تحميل psutil (اختياري) ──────────────────────────────────────────
try:
    import psutil as _psutil
    _PSUTIL_OK = True
except ImportError:
    _psutil = None
    _PSUTIL_OK = False

# ── تتبع الأخطاء التنبؤية (Predictive Error Tracking + Timeline) ────────────
_error_freq: dict = {}          # func_name → total count
_error_freq_lock = threading.Lock()

# Timeline: قائمة مرتّبة زمنياً لآخر 200 خطأ بالتفاصيل الكاملة
_error_timeline: list = []          # [{ts, func, type, msg}]
_error_timeline_lock = threading.Lock()
_ERROR_TIMELINE_MAX  = 200

def _track_error(func_name: str, exc: Exception = None, err_type: str = ""):
    """
    سجّل خطأ في وظيفة معيّنة:
    • يُحدّث عداد التكرار
    • يُضيف سجلاً في التيملاين بطابع زمني
    • يُرسل تحذيراً استباقياً عند أعداد محددة
    """
    err_msg  = str(exc)[:300] if exc else ""
    if not err_type:
        try:
            err_type = _classify_error(err_msg) if err_msg else "unknown"
        except Exception:
            err_type = "unknown"

    # ── تحديث العداد ──
    with _error_freq_lock:
        _error_freq[func_name] = _error_freq.get(func_name, 0) + 1
        total = _error_freq[func_name]

    # ── تحديث التيملاين ──
    entry = {
        "ts":   time.time(),
        "func": func_name,
        "type": err_type,
        "msg":  err_msg,
    }
    with _error_timeline_lock:
        _error_timeline.append(entry)
        if len(_error_timeline) > _ERROR_TIMELINE_MAX:
            del _error_timeline[0]

    # ── تحذير الأدمن الاستباقي ──
    if total in (5, 10, 25, 50, 100) or total % 100 == 0:
        try:
            bot.send_message(
                ADMIN_ID,
                f"⚠️ *تحذير استباقي* — `{func_name}` أخطأت *{total}* مرة\n"
                f"نوع الخطأ: `{err_type}`\n"
                + (f"`{err_msg[:200]}`" if err_msg else ""),
                parse_mode="Markdown"
            )
        except Exception as _exc:
            _log_exc(_exc)

# ── إحصاءات صحة النظام ──────────────────────────────────────────────────────
_sys_health: dict = {
    "ram_pct":   0.0,
    "cpu_pct":   0.0,
    "disk_pct":  0.0,
    "start_ts":  time.time(),
    "recoveries": 0,   # عدد مرات التعافي التلقائي
}

def send_alert(message: str, exc: Exception = None, func_name: str = "",
               show_traceback: bool = True):
    """
    إرسال تنبيه فوري للأدمن عند أي خطأ.
    مع traceback كامل + مكان الخطأ + محاولة إعادة ثلاث مرات.
    """
    global _alert_count
    # ─── منع التشبع ──────────────────────────────────────────────────────────
    min_key = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with _alert_lock:
        cnt = _alert_count.get(min_key, 0)
        if cnt >= _MAX_ALERTS_PER_MIN:
            return
        _alert_count[min_key] = cnt + 1
        # تنظيف القديم
        old_keys = [k for k in _alert_count if k != min_key]
        for k in old_keys:
            _alert_count.pop(k, None)

    # ─── بناء نص التنبيه ──────────────────────────────────────────────────────
    now_str = _now_sa().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"🚨 *تنبيه فوري — IraqNow Bot*", f"🕐 `{now_str}` (توقيت السعودية)"]
    if func_name:
        lines.append(f"📌 *المكان:* `{func_name}`")
    if message:
        lines.append(f"📋 *الرسالة:* `{str(message)[:300]}`")
    if exc is not None:
        lines.append(f"❌ *نوع الخطأ:* `{type(exc).__name__}`")
        lines.append(f"💬 *التفاصيل:* `{str(exc)[:200]}`")
        if show_traceback:
            tb = traceback.format_exc()
            if tb and "NoneType" not in tb:
                tb_short = tb[-800:].replace("`", "'")
                lines.append(f"🔍 *Traceback:*\n```\n{tb_short}\n```")

    alert_text = "\n".join(lines)
    all_admins = [ADMIN_ID] + extra_admins

    # ─── إرسال مع إعادة المحاولة ──────────────────────────────────────────────
    for admin_id in all_admins:
        for attempt in range(3):
            try:
                bot.send_message(admin_id, alert_text, parse_mode="Markdown")
                _logger.info(f"✅ تنبيه أُرسل للأدمن {admin_id}")
                break
            except Exception as send_err:
                if attempt == 2:
                    _logger.error(f"فشل إرسال التنبيه للأدمن {admin_id}: {send_err}")
                else:
                    time.sleep(2 ** attempt)


def notify_admin_error(msg: str, exc: Exception = None):
    """دالة مشتركة — ترسل التنبيه عبر send_alert الجديدة."""
    frame = sys._getframe(1)
    func_name = frame.f_code.co_name
    lineno    = frame.f_lineno
    send_alert(
        message      = f"{msg}  (line {lineno})",
        exc          = exc,
        func_name    = func_name,
        show_traceback = exc is not None
    )
    _logger.error(f"[{func_name}:{lineno}] {msg}" + (f" | {exc}" if exc else ""))


# ─── Global Exception Hook — يصطاد أي خطأ غير محاط بـ try ───────────────────
# FIX RecursionError: _global_exception_hook كانت تستدعي send_alert التي قد ترمي
# exception جديد فيستدعي Hook مرة أخرى → recursion لا نهائي حتى sys.setrecursionlimit
# الحل: threading.local() guard يمنع الاستدعاء المتداخل
_exc_hook_local = threading.local()

def _global_exception_hook(exc_type, exc_value, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    # منع الاستدعاء المتداخل (RecursionError أو أي exception داخل send_alert)
    if getattr(_exc_hook_local, 'active', False):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    _exc_hook_local.active = True
    try:
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        _lg = globals().get("_logger") or __import__("logging").getLogger("IraqNowBot")
        _lg.critical(f"UNCAUGHT EXCEPTION:\n{tb_str}")
        try:
            send_alert(
                message    = "خطأ غير محاط بـ try/except",
                exc        = exc_value,
                func_name  = "GLOBAL",
                show_traceback = True
            )
        except Exception as _exc:
            _log_exc(_exc)
    finally:
        _exc_hook_local.active = False

sys.excepthook = _global_exception_hook


# ═══════════════════════════════════════════════════════════════════════════════
# SAFE EXECUTION LAYER — طبقة الإرسال الآمن مع Exponential Backoff
# ═══════════════════════════════════════════════════════════════════════════════
