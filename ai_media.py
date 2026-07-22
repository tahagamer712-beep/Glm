# -*- coding: utf-8 -*-
"""
  ai_media.py — تحليل الصور بـ AI

  يُصدِّر دوال تحليل الوسائط بالذكاء الاصطناعي.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_analyze_image_url(img_url: str, user_question: str = "") -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    try:
        import urllib.request
        req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_bytes = resp.read()
        question = user_question or "حلل هذه الصورة إخبارياً: ما الحدث؟ من الأشخاص؟ ما السياق؟"
        # الواجهة الجديدة google-genai
        try:
            from google import genai as _gai
            import base64
            _cli = _gai.Client(api_key=GEMINI_API_KEY)
            from google.genai import types as _gtypes
            img_b64 = base64.b64encode(img_bytes).decode()
            part = _gtypes.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
            r = _cli.models.generate_content(model="gemini-1.5-flash", contents=[question, part])
            return (r.text or "")[:1000]
        except Exception:
            # fallback legacy
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            vision_model = genai.GenerativeModel("gemini-1.5-flash")
            img_part = {"mime_type": "image/jpeg", "data": img_bytes}
            response = vision_model.generate_content([question, img_part])
            return (response.text or "")[:1000]
    except Exception as e:
        return _ai_friendly_error(e, "vision")

def _ai_analyze_photo_file(file_bytes: bytes, user_question: str = "") -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    try:
        question = user_question or "حلل هذه الصورة إخبارياً: ما الحدث؟ من الأشخاص؟ ما السياق؟ هل تبدو حقيقية أم مفبركة؟"
        try:
            from google import genai as _gai
            from google.genai import types as _gtypes
            _cli = _gai.Client(api_key=GEMINI_API_KEY)
            part = _gtypes.Part.from_bytes(data=file_bytes, mime_type="image/jpeg")
            r = _cli.models.generate_content(model="gemini-1.5-flash", contents=[question, part])
            return (r.text or "")[:1000]
        except Exception:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            vision_model = genai.GenerativeModel("gemini-1.5-flash")
            img_part = {"mime_type": "image/jpeg", "data": file_bytes}
            response = vision_model.generate_content([question, img_part])
            return (response.text or "")[:1000]
    except Exception as e:
        return _ai_friendly_error(e, "vision")

# ─── 4. التنبؤ بالأحداث ────────────────────────────────────────
@bot.message_handler(content_types=['photo'])
def handle_photo_analysis(message):
    uid = message.from_user.id

    # ── وضع تعيين صورة الغلاف للسوشيال ميديا (أدمن فقط) ──
    if is_admin(uid) and _social_settings.get("awaiting_image"):
        file_id = message.photo[-1].file_id
        _set_social_image(file_id)
        _social_settings.pop("awaiting_image", None)
        _save_social_settings()
        bot.send_message(uid,
            "✅ *تم حفظ الصورة!*\n\nسيتم استخدامها مع كل منشور على فيسبوك وانستغرام تلقائياً.",
            parse_mode="Markdown"
        )
        return

    caption = message.caption or ""
    # فحص إذا المستخدم يريد التحليل
    if not any(w in caption.lower() for w in ["حلل", "analyze", "شنو", "ما هذا", "اقرأ", "تحقق", "verify"]):
        # لا تحلل كل صورة تلقائياً، فقط عند الطلب
        return
    msg = bot.send_message(message.chat.id, "📸 جاري تحليل الصورة بـ AI...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        import urllib.request
        with urllib.request.urlopen(file_url, timeout=10) as resp:
            img_bytes = resp.read()
        result = _ai_analyze_photo_file(img_bytes, caption)
        reply = f"📸 *تحليل الصورة*\n\n{result}"
        try:
            bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")
    except Exception as e:
        try:
            bot.edit_message_text(_ai_friendly_error(e, "vision"), message.chat.id, msg.message_id, parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)

