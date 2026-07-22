# -*- coding: utf-8 -*-
"""
  ai_factcheck.py — Fact Check + كاشف الشائعات

  يُصدِّر نظام التحقق من الأخبار وكشف الشائعات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_verify_news(title: str, body: str = "") -> dict:
    """يقارن الخبر بمصادر متعددة ويعطي نسبة موثوقية"""
    if not _AI_MODEL:
        return {"score": None, "verdict": "AI غير متاح", "reason": ""}
    try:
        prompt = f"""أنت محقق إعلامي متخصص في كشف الأخبار الكاذبة.

الخبر: {title}
{('التفاصيل: ' + body[:400]) if body else ''}

قيّم موثوقية هذا الخبر من 0 إلى 100 بناءً على:
1. هل يحتوي على ادعاءات قابلة للتحقق؟
2. هل الصياغة إثارية أم موضوعية؟
3. هل يتوافق مع الأحداث المعروفة؟
4. هل يحتوي على مبالغة أو أرقام غير منطقية؟

أجب بهذا الشكل الحرفي:
SCORE: [رقم 0-100]
VERDICT: [موثوق/مشكوك فيه/كاذب على الأرجح]
REASON: [سبب واحد مختصر]"""
        _response_ai = _ai_generate(prompt)
        text = (_response_ai or "")
        score, verdict, reason = None, "غير محدد", ""
        for line in text.splitlines():
            if line.startswith("SCORE:"):
                try:
                    score = int(line.split(":", 1)[1].strip())
                except Exception as _exc:
                    _log_exc(_exc)
            elif line.startswith("VERDICT:"):
                verdict = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        return {"score": score, "verdict": verdict, "reason": reason}
    except Exception:
        return {"score": None, "verdict": "تعذر التحقق", "reason": ""}

def _format_verify_result(result: dict, title: str) -> str:
    score = result.get("score")
    verdict = result.get("verdict", "غير محدد")
    reason = result.get("reason", "")
    if score is None:
        meter = "⬜⬜⬜⬜⬜"
        score_str = "؟"
    else:
        filled = round(score / 20)
        colors = ["🔴","🟠","🟡","🟢","🟢"]
        meter = "".join(colors[min(i, len(colors)-1)] for i in range(filled)) + "⬜" * (5 - filled)
        score_str = f"{score}%"
    icon = "✅" if (score or 0) >= 70 else "⚠️" if (score or 0) >= 40 else "🚨"
    return (
        f"🔍 *تحقق من الخبر*\n\n"
        f"📰 {title[:80]}\n\n"
        f"{meter} `{score_str}`\n"
        f"{icon} *{verdict}*\n"
        f"📝 {reason}"
    )

# ═══════════════════════════════════════════════════════════════════
# 2. تحليل المزاج السياسي والتوقعات
# ═══════════════════════════════════════════════════════════════════
def _ai_verify_user_news(text: str) -> dict:
    """يتحقق AI من خبر أرسله مستخدم"""
    if not _AI_MODEL:
        return {"valid": False, "reason": "AI غير متاح", "score": 0}
    try:
        prompt = f"""مستخدم أرسل هذا الخبر من أرض الواقع:

"{text[:500]}"

حكم عليه:
1. هل يبدو خبراً حقيقياً أم إشاعة أم محتوى عشوائي؟
2. هل يستحق النشر للمشتركين؟
3. ما نسبة موثوقيته 0-100؟

أجب بالشكل:
VALID: [yes/no]
SCORE: [0-100]
REASON: [سبب مختصر]
CLEANED: [الخبر بعد تنقيحه للنشر، أو "لا يصلح"]"""
        _response_ai = _ai_generate(prompt)
        text_out = (_response_ai or "")
        result = {"valid": False, "score": 0, "reason": "", "cleaned": ""}
        for line in text_out.splitlines():
            if line.startswith("VALID:"):
                result["valid"] = "yes" in line.lower()
            elif line.startswith("SCORE:"):
                try:
                    result["score"] = int(line.split(":", 1)[1].strip())
                except Exception as _exc:
                    _log_exc(_exc)
            elif line.startswith("REASON:"):
                result["reason"] = line.split(":", 1)[1].strip()
            elif line.startswith("CLEANED:"):
                result["cleaned"] = line.split(":", 1)[1].strip()
        return result
    except Exception:
        return {"valid": False, "reason": "خطأ في التحقق", "score": 0, "cleaned": ""}

# ═══════════════════════════════════════════════════════════════════
# 8. تصنيف المصادر
# ═══════════════════════════════════════════════════════════════════
def _load_factcheck_cache() -> dict:
    try:
        if os.path.exists(_FACTCHECK_CACHE_FILE):
            with open(_FACTCHECK_CACHE_FILE, "r", encoding="utf-8") as _f:
                data = json.load(_f)
            if isinstance(data, dict):
                return data
    except Exception as _exc:
        _log_exc(_exc)
    return {}

def _save_factcheck_cache(cache: dict):
    try:
        # نحتفظ بآخر 1000 مفتاح فقط لتحديد حجم الملف
        if len(cache) > 1000:
            keys = list(cache.keys())[-800:]
            cache = {k: cache[k] for k in keys}
        with open(_FACTCHECK_CACHE_FILE, "w", encoding="utf-8") as _f:
            json.dump(cache, _f, ensure_ascii=False)
    except Exception as _exc:
        _log_exc(_exc)

_factcheck_key_cache = _load_factcheck_cache()  # يُحمَّل من القرص عند الإقلاع

# FIX: الاستدعاء المباشر لـ _restore_button_caches() هنا كان يفشل بصمت لأن
# db_cache.py (مصدر الدالة) غير مضمون أن يكون محمَّلاً قبل هذا الملف بترتيب
# الاستيراد — نُقل الاستدعاء إلى bot_legacy.py بعد اكتمال تحميل كل الوحدات.

