# -*- coding: utf-8 -*-
"""
  utils.py — توقيت UTC+3 + backoff + مساعدات عامة

  يُصدِّر الأدوات المساعدة العامة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: تأكيد وجود _SA_TZ_OFFSET للاستخدام في _now_sa (مُعرَّف في bot_legacy)
if "_SA_TZ_OFFSET" not in dir():
    import datetime as _dt_utils
    _SA_TZ_OFFSET = _dt_utils.timedelta(hours=3)
# FIX: إذا لم يكن _UI_STRINGS موجوداً بعد، نُعيّن dict فارغاً مؤقتاً
if "_UI_STRINGS" not in dir():
    _UI_STRINGS: dict = {}

def _now_sa() -> datetime.datetime:
    """يُعيد الوقت الحالي بتوقيت السعودية / العراق (UTC+3)."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + _SA_TZ_OFFSET

def _sa_str(fmt="%H:%M:%S — %d/%m/%Y") -> str:
    """يُعيد الوقت الحالي كنص بتوقيت السعودية بالصيغة المطلوبة."""
    return _now_sa().strftime(fmt)

# ======== Edge TTS (رسائل صوتية مجانية) ========
_TTS_AVAILABLE = False
try:
    import edge_tts
    _TTS_AVAILABLE = True
except ImportError:
    pass

# ======== صوت لكل لغة في Edge TTS ========
TTS_VOICES = {
    "العربية 🇮🇶":   "ar-IQ-BasselNeural",
    "English 🇬🇧":   "en-GB-RyanNeural",
    "Русский 🇷🇺":   "ru-RU-DmitryNeural",
    "فارسی 🇮🇷":    "fa-IR-FaridNeural",
    "हिन्दी 🇮🇳":    "hi-IN-MadhurNeural",
    "Português 🇧🇷": "pt-BR-AntonioNeural",
    "Türkçe 🇹🇷":   "tr-TR-AhmetNeural",
    "اردو 🇵🇰":     "ur-PK-AsadNeural",
    "Deutsch 🇩🇪":   "de-DE-ConradNeural",
    "Українська 🇺🇦":"uk-UA-OstapNeural",
    "Italiano 🇮🇹":  "it-IT-DiegoNeural",
    "Español 🇲🇽":   "es-MX-JorgeNeural",
    "Français 🇫🇷":  "fr-FR-HenriNeural",
}

# ======== Gemini AI — تنظيف وتلخيص الأخبار ========
GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
# دعم مفاتيح Gemini متعددة (مفصولة بفاصلة) لتوزيع الضغط
_GEMINI_KEYS = [k.strip() for k in GEMINI_API_KEY.split(",") if k.strip()]
_gemini_key_idx = 0   # يدور بين المفاتيح عند الـ 429

# ── AI الإضافية (كل provider quota مستقل) ───────────────────────────────────
_DS_GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")       # groq.com — free tier
_DS_OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")     # openrouter.ai — free models
_DS_TOGETHER_KEY   = os.environ.get("TOGETHER_API_KEY", "")   # together.ai — free tier
_DS_MISTRAL_KEY    = os.environ.get("MISTRAL_API_KEY", "")    # mistral.ai — free tier
_DS_COHERE_KEY     = os.environ.get("COHERE_API_KEY", "")     # cohere.com — free tier

# ── تحليل ذكي بدون AI (keyword-based fallback) ─────────────────────────────
def _ui(key: str, lang: str = "العربية 🇮🇶") -> str:
    """يُعيد رسالة واجهة المستخدم بلغة المستخدم، أو العربية كاحتياط."""
    block = _UI_STRINGS.get(key, {})
    return block.get(lang) or block.get("العربية 🇮🇶") or key

_AI_AVAILABLE = False
_AI_MODEL = None

def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if file == USERS_FILE:
                _now_load = time.time()
                for uid in data:
                    if "sent_news" in data[uid]:
                        sn = data[uid]["sent_news"]
                        if isinstance(sn, list):
                            # بنية قديمة: حوّلها لـ dict مع fake timestamp
                            fake_ts = _now_load - (_USER_SENT_TTL / 2)
                            data[uid]["sent_news"] = {lnk: fake_ts for lnk in sn}
                        elif isinstance(sn, set):
                            fake_ts = _now_load - (_USER_SENT_TTL / 2)
                            data[uid]["sent_news"] = {lnk: fake_ts for lnk in sn}
                        # إذا كان dict → يبقى كما هو
            return data
    except Exception:
        return default

def save_json(file, data):
    try:
        save_data = data
        if file == USERS_FILE:
            save_data = {}
            _now_save = time.time()
            for uid, val in data.items():
                save_data[uid] = dict(val)
                if "sent_news" in save_data[uid]:
                    sn = save_data[uid]["sent_news"]
                    if isinstance(sn, dict):
                        # احفظ الروابط النشطة فقط كـ list للتوافق مع JSON
                        save_data[uid]["sent_news"] = [
                            lnk for lnk, ts in sn.items()
                            if (_now_save - ts) < _USER_SENT_TTL
                        ][-2000:]
                    else:
                        save_data[uid]["sent_news"] = list(sn)[-2000:]
        with open(file, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        notify_admin_error(f"خطأ في حفظ البيانات: {e}")

def _exponential_backoff(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
    """حساب وقت الانتظار: 1s, 2s, 4s, 8s ... حد أقصى 60s"""
    return min(cap, base * (2 ** attempt))


def _safe_job(fn):
    """
    Wrapper لكل مهام الـ Scheduler:
    - يصطاد أي Exception
    - يُسجّل الخطأ في الـ log
    - يُرسل تنبيه فوري للأدمن مع traceback
    - لا يوقف الـ Scheduler أبداً
    - FIX: يتجاهل المهمة إذا استُقبل SIGTERM لمنع "cannot schedule new futures after shutdown"
    """
    @functools.wraps(fn)
    def wrapper():
        # FIX: لا تُنفّذ المهمة بعد استلام SIGTERM — يمنع RuntimeError من الـ executor المُغلق
        if _SIGTERM_RECEIVED:
            return
        try:
            fn()
        except RuntimeError as e:
            if "cannot schedule new futures after shutdown" in str(e):
                return  # الـ executor مُغلق بسبب SIGTERM — تجاهل بصمت
            _logger.error(f"❌ خطأ في المهمة المجدولة [{fn.__name__}]: {e}", exc_info=True)
            try:
                send_alert(
                    message    = f"خطأ في المهمة المجدولة: {fn.__name__}",
                    exc        = e,
                    func_name  = fn.__name__,
                    show_traceback = True
                )
            except Exception as _exc:
                _log_exc(_exc)
        except Exception as e:
            _logger.error(f"❌ خطأ في المهمة المجدولة [{fn.__name__}]: {e}", exc_info=True)
            try:
                send_alert(
                    message    = f"خطأ في المهمة المجدولة: {fn.__name__}",
                    exc        = e,
                    func_name  = fn.__name__,
                    show_traceback = True
                )
            except Exception as _exc:
                _log_exc(_exc)
    return wrapper


# ─── Heartbeat: كل 10 دقائق يُرسل للأدمن تأكيد أن البوت يعمل ────────────────
_heartbeat_fail_count = 0
