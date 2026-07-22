# -*- coding: utf-8 -*-
"""
  ai_profile.py — محقق الشخصيات + خريطة النفوذ

  يُصدِّر دوال تحليل الشخصيات وخريطة النفوذ.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_build_profile(name: str) -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    cached = _profile_cache.get(name)
    if cached and time.time() - cached["timestamp"] < 3600:
        return cached["text"]
    # جمع أخبار عن الشخص
    related = []
    for feed_url in list(RSS.get("العربية 🇮🇶", []))[:10]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:20]:
                title = getattr(entry, 'title', '')
                if name.split()[0].lower() in title.lower():
                    pub = _pub_dt_from_item(entry)
                    pub_str = pub.strftime('%Y-%m-%d') if pub else ''
                    related.append(f"[{pub_str}] {title}")
        except Exception as _exc:
            _log_exc(_exc)
    news_ctx = "\n".join(related[:20]) if related else "لا توجد أخبار حديثة عنه في المصادر"
    today_str = _now_sa().strftime("%Y-%m-%d")
    prompt = f"""أنت محقق صحفي استقصائي متخصص في الشأن العراقي والعربي.
المطلوب: ملف استخباراتي شامل عن شخصية: **{name}**
التاريخ: {today_str}

أخبار موثقة حديثة عنه:
{news_ctx}

اكتب الملف بهذا الهيكل الدقيق:

🎖️ **{name} — ملف الشخصية**

👤 **الهوية:**
[المنصب الحالي، الانتماء السياسي، الطائفة/القومية إذا كانت ذات صلة عامة، المنطقة الجغرافية]

📋 **آخر التطورات والقرارات:**
[استناداً للأخبار المرفقة — رتّبها من الأحدث للأقدم]

🤝 **الحلفاء والتحالفات:**
[أبرز التحالفات السياسية والعلاقات مع الكتل والأحزاب والدول]

⚔️ **الخصوم والمعارضون:**
[من يعارضه وما أسباب الخلاف]

⚠️ **نقاط الجدل والانتقاد:**
[أبرز الاتهامات أو المواقف المثيرة للجدل — بموضوعية]

🔮 **التقييم والتوقعات:**
[تقييم موضوعي لموقعه السياسي وتوقعات دوره خلال 6 أشهر]

📊 **مستوى النفوذ:** [محلي / وطني / إقليمي / دولي]

كن دقيقاً وموضوعياً. استند للأخبار المرفقة أولاً ثم معرفتك العامة."""
    try:
        _response_ai = _ai_generate(prompt)
        result = (_response_ai or "")[:1500]
        _profile_cache[name] = {"text": result, "timestamp": time.time()}
        return result
    except Exception as e:
        return _ai_friendly_error(e, "profile")

# ─── 2. محادثة مع الأخبار (RAG) ────────────────────────────────
def _ai_influence_map(name: str) -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "influence")
    related = []
    for feed_url in list(RSS.get("العربية 🇮🇶", []))[:10]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:15]:
                title = getattr(entry, 'title', '')
                if name.split()[0] in title:
                    related.append(title)
        except Exception as _exc:
            _log_exc(_exc)
    context = "\n".join(related[:15]) if related else ""
    _ctx_influence = ('أخبار حديثة:\n' + context) if context else ''
    prompt = f"""أنت محلل سياسي. ارسم خريطة نفوذ لـ: {name}

{_ctx_influence}

الخريطة تشمل:
🤝 **الحلفاء الرئيسيون** (مع طبيعة العلاقة)
⚔️ **المنافسون والخصوم**
🏛️ **المؤسسات التي يؤثر عليها**
💰 **مصادر قوته** (سياسية/اقتصادية/قبلية/دينية)
🌍 **ارتباطاته الخارجية**
📊 **مستوى نفوذه: [محلي/وطني/إقليمي/دولي]**"""
    try:
        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:1500]
    except Exception as e:
        return _ai_friendly_error(e, "influence")

# ─── 8. بث مخصص بـ AI ─────────────────────────────────────────
def handle_profile_cmd(message):
    if not _FF.get("profile", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid_int = message.from_user.id
    uid = str(uid_int)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid_int, "profile"):
        bot.send_message(message.chat.id, "⏳ أنشأت ملفاً مؤخراً. انتظر دقيقتين قبل طلب ملف جديد.", parse_mode="Markdown")
        return
    allowed, used, limit = _check_daily_ai_limit(uid_int, "profile")
    if not allowed:
        bot.send_message(message.chat.id, f"📊 *وصلت الحد اليومي* لبناء الملفات ({limit}/يوم). يتجدد الرصيد غداً.", parse_mode="Markdown")
        return
    name = message.text.replace('/profile', '').strip()
    if not name:
        bot.send_message(message.chat.id, _ui("cmd_profile_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id,
        _ui("cmd_profile_loading", lang).format(name=name), parse_mode="Markdown")
    result = _ai_build_profile(name)
    reply = f"{_ui('cmd_profile_hdr', lang)} {name}\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

@bot.message_handler(commands=["influence"])
def handle_influence_cmd(message):
    if not _FF.get("influence", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid_int = message.from_user.id
    uid = str(uid_int)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid_int, "influence"):
        bot.send_message(message.chat.id, "⏳ انتظر دقيقتين بين كل طلب لخريطة النفوذ.")
        return
    allowed, used, limit = _check_daily_ai_limit(uid_int, "influence")
    if not allowed:
        bot.send_message(message.chat.id, f"📊 وصلت الحد اليومي لخرائط النفوذ ({limit}/يوم). يتجدد الرصيد غداً.")
        return
    name = message.text.replace('/influence', '').strip()
    if not name:
        bot.send_message(message.chat.id,
            _ui("cmd_influence_usage", lang),
            parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id,
        _ui("cmd_influence_loading", lang).format(name=escape_md(name)), parse_mode="Markdown")
    result = _ai_influence_map(name)
    reply = f"{_ui('cmd_influence_hdr', lang).format(name=escape_md(name))}\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

