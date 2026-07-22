# -*- coding: utf-8 -*-
"""
  ai_rag.py — Chat with news (RAG — محادثة مع الأخبار)

  يُصدِّر نظام المحادثة مع الأخبار باستخدام RAG.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_chat_with_news(question: str, lang: str = "العربية 🇮🇶") -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    # جمع أخبار ذات صلة بالسؤال
    keywords = [w for w in question.split() if len(w) > 3]
    related = []
    for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", []))[:12]):
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:15]:
                title = getattr(entry, 'title', '')
                summary = getattr(entry, 'summary', '') or ''
                if any(kw.lower() in title.lower() for kw in keywords):
                    related.append(f"• {title}")
        except Exception as _exc:
            _log_exc(_exc)
    context = "\n".join(related[:15]) if related else "لا توجد أخبار مرتبطة مباشرة"
    today_str = _now_sa().strftime("%Y-%m-%d")
    prompt = f"""أنت محلل أخباري متخصص في الشؤون العراقية والعربية — بوت "عراق ناو".
اليوم: {today_str}

السؤال: {question}

أخبار ذات صلة من اليوم:
{context}

قواعد الإجابة:
• ابدأ بالإجابة مباشرة دون مقدمات
• اذكر مصدر المعلومة إذا كان في الأخبار المرفقة
• إذا كان السؤال خارج نطاق الأخبار الحالية، قدّم إجابة من معرفتك مع الإشارة لذلك
• لا تتجاوز 5 جمل — الإيجاز أولاً
• أنهِ بـ 💡 نقطة تحليلية واحدة إضافية إذا كانت مفيدة"""
    try:
        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:800]
    except Exception as e:
        return _ai_friendly_error(e, "ask")

# ─── 3. تحليل الصور بـ AI ──────────────────────────────────────
@bot.message_handler(commands=["ask"])
def handle_ask_cmd(message):
    if not _FF.get("ask", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    if _is_rate_limited(uid, "ask"):
        bot.send_message(message.chat.id, "⏳ استخدمت هذا الأمر مؤخراً. انتظر 45 ثانية قبل المحاولة.", parse_mode="Markdown")
        return
    allowed, used, limit = _check_daily_ai_limit(uid, "ask")
    if not allowed:
        bot.send_message(message.chat.id, f"📊 *وصلت الحد اليومي* للذكاء الاصطناعي ({limit} استفسار/يوم). يتجدد الرصيد غداً.\n\n💎 المميزون يحصلون على 30 استفساراً يومياً.", parse_mode="Markdown")
        return
    question = message.text.replace('/ask', '').strip()
    if not question:
        bot.send_message(message.chat.id, _ui("cmd_ask_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id, _ui("cmd_ask_loading", lang))
    _ci_track_topic(question[:50])
    result = _ai_chat_with_news(question, lang)
    reply = f"💬 *{question}*\n\n{result}\n\n{_ui('cmd_ask_footer', lang)}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

