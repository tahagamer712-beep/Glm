# -*- coding: utf-8 -*-
"""
main.py — نقطة الدخول الرئيسية
التشغيل: python main.py
البيئة المستهدفة: Termux على Android (Long Polling، بدون Webhook)
"""

import sys
import os
import time
import atexit
import signal
import logging
import threading

# ── إعداد متغيرات البيئة من .env إذا وجد (Termux) ──────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv اختياري — يمكن ضبط متغيرات البيئة يدوياً

import config  # noqa: F401 — يتحقق من المتغيرات الإلزامية ويوقف البوت إن غابت

# ── تحميل bot_legacy (النواة الرئيسية) ──────────────────────────────────────
import bot_legacy as _legacy

# ── تحميل الوحدات المُقسَّمة (الملفات المفقودة أُنشئت الآن كـ stubs) ──────
# FIX: هذه الوحدات كانت مفقودة — تم إنشاؤها جميعاً الآن
_optional_modules = [
    "bot_core",
    "db",
    "ai",
    "features_news",
    "features_sports",
    "features_users",
    "handlers",
]

for _mod in _optional_modules:
    try:
        __import__(_mod)
    except Exception as _mod_err:
        # لا تُوقِف البوت إذا فشل تحميل وحدة — سجِّل فقط
        try:
            _legacy._logger.warning("⚠️ لم يُحمَّل %s: %s", _mod, _mod_err)
        except Exception:
            logging.getLogger("IraqNowBot").warning("لم يُحمَّل %s: %s", _mod, _mod_err)

# ── FIX: إصلاح شامل لكل "الأسماء العالمية التائهة" في كل وحدات البوت ──────
# يعمل مرة واحدة بعد اكتمال تحميل كل الملفات، ويصلح تلقائياً أي دالة تشير
# لاسم مُعرَّف في ملف آخر دون استيراد صريح (نفس مشكلة is_admin/_radar_data
# السابقة، لكن بشكل شامل لكل الأوامر بدلاً من إصلاحها واحدة تلو الأخرى).
try:
    import global_healer
    global_healer.run(os.path.dirname(os.path.abspath(__file__)), bot=_legacy.bot)
except Exception as _healer_err:
    logging.getLogger("IraqNowBot").warning("⚠️ global_healer فشل: %s", _healer_err)

# ── استرجاع ذاكرة أزرار الأخبار (why/next/ctx/fc...) من SQLite ──────────────
# FIX: يجب أن يُنفَّذ هذا *بعد* global_healer، لأن db_cache._restore_button_caches
# تحتاج أسماء مُعرَّفة في وحدة أخرى (ai_factcheck.py) مثل _factcheck_key_cache،
# والتي لا تصل إلى مساحة db_cache إلا عبر الإصلاح الشامل لـ global_healer.
try:
    import sys as _sys_main
    _db_cache_mod = _sys_main.modules.get("db_cache")
    if _db_cache_mod is not None and hasattr(_db_cache_mod, "_restore_button_caches"):
        _db_cache_mod._restore_button_caches()
except Exception as _restore_err:
    logging.getLogger("IraqNowBot").warning("⚠️ فشل استرجاع ذاكرة الأزرار: %s", _restore_err)

# ── استخراج المكوّنات الأساسية ───────────────────────────────────────────────
bot        = _legacy.bot
_logger    = _legacy._logger
_log_exc   = _legacy._log_exc
send_alert = getattr(_legacy, "send_alert", None)
_retry_count = 0


# ═══════════════════════════════════════════════════════════════════════════════
# SIGTERM / SIGINT — إيقاف نظيف (مهم للـ Termux وكيل الـ Android)
# ═══════════════════════════════════════════════════════════════════════════════
def _set_sigterm_flag(signum, frame):
    """يضبط علم الإيقاف ليمنع تشغيل مهام جديدة."""
    try:
        _legacy._SIGTERM_RECEIVED = True
    except Exception:
        pass
    try:
        import state as _gl
        _gl._SIGTERM_RECEIVED = True  # مزامنة state
    except Exception:
        pass
    _logger.info("🛑 تم استقبال إشارة %s — جارٍ الإيقاف النظيف...", signum)
    _shutdown()
    sys.exit(0)


try:
    signal.signal(signal.SIGTERM, _set_sigterm_flag)
    signal.signal(signal.SIGINT,  _set_sigterm_flag)
except (OSError, ValueError):
    pass  # قد لا تتوفر الإشارات في بعض بيئات الـ threading


def _bounded_wait_shutdown(fn, timeout=10):
    """
    FIX: ينتظر اكتمال المهام الجارية (wait=True) لكن بحد أقصى `timeout` ثانية
    عبر thread منفصل — يمنع تعليق العملية للأبد إذا علقت مهمة، بينما يمنع
    قطع بث/طلب AI نشط فجأة في الحالة الطبيعية.
    """
    t = threading.Thread(target=lambda: fn(wait=True), daemon=True)
    t.start()
    t.join(timeout)


def _shutdown():
    """إيقاف نظيف: APScheduler + ThreadPoolExecutor (ينتظر حتى 10 ثوانٍ لإنهاء المهام الجارية)."""
    try:
        s = getattr(_legacy, "scheduler", None)
        if s and getattr(s, "running", False):
            _bounded_wait_shutdown(s.shutdown, timeout=10)
    except Exception:
        pass
    try:
        e = getattr(_legacy, "_AI_EXECUTOR", None)
        if e:
            _bounded_wait_shutdown(e.shutdown, timeout=10)
    except Exception:
        pass
    try:
        e2 = getattr(_legacy, "_BC_FORCE_EXECUTOR", None)
        if e2:
            _bounded_wait_shutdown(e2.shutdown, timeout=10)
    except Exception:
        pass


atexit.register(_shutdown)


# ═══════════════════════════════════════════════════════════════════════════════
# حلقة التشغيل الرئيسية — Self-Healing Polling Loop
# ═══════════════════════════════════════════════════════════════════════════════
def run():
    global _retry_count
    try:
        import state as _gl
        _logger.info("🟢 STATE LOADED: %s | uptime=%.2fs", _gl.VERSION, __import__('time').time() - _gl.BOOT_TIME)
    except Exception:
        pass
    _logger.info("🤖 IraqNow Bot — بدء Long Polling (Termux Mode)")

    while True:
        try:
            _logger.info("🚀 بدء التشغيل (محاولة #%d)", _retry_count + 1)
            bot.infinity_polling(
                allowed_updates=["message", "callback_query", "my_chat_member"],
                timeout=60,
                long_polling_timeout=60,
                # PERF-FIX: رفع عدد الـ threads المخصصة لمعالجة أوامر المستخدمين
                # من 4 (افتراضي) إلى 12 — يضمن استجابة فورية حتى أثناء البث/RSS
                # لأن كل thread يعالج أمراً واحداً؛ مع 4 فقط تتراكم الأوامر
                num_threads=12,
                restart_on_change=False,
            )
            _retry_count = 0  # نجح الـ polling — أعِد العداد

        except KeyboardInterrupt:
            _logger.info("🛑 إيقاف يدوي (Ctrl+C)")
            _shutdown()
            break

        except RuntimeError as _rterr:
            # "cannot schedule new futures after shutdown" — الـ executor مُغلق
            if "cannot schedule new futures" in str(_rterr):
                time.sleep(3)
                continue
            _retry_count += 1
            _wait = min(5 * (2 ** (_retry_count - 1)), 60)
            _logger.error("💥 RuntimeError #%d: %s — إعادة خلال %ds", _retry_count, _rterr, _wait)
            time.sleep(_wait)

        except Exception as _err:
            _retry_count += 1
            _wait = min(5 * (2 ** (_retry_count - 1)), 60)
            _logger.error("💥 انهيار #%d: %s — إعادة خلال %ds", _retry_count, _err, _wait)

            # تنبيه الأدمن (أول 5 مرات فقط لمنع spam)
            if _retry_count <= 5 and send_alert:
                try:
                    send_alert(
                        message=f"كراش #{_retry_count}",
                        exc=_err,
                        func_name="polling",
                        show_traceback=True,
                    )
                except Exception:
                    pass

            # حذف أي webhook قد يكون سبب الخلل
            try:
                bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass

            time.sleep(_wait)


if __name__ == "__main__":
    run()
