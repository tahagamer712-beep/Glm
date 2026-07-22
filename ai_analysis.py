# -*- coding: utf-8 -*-
"""
  ai_analysis.py — تحليل سياسي + مقارنة وجهات نظر + خط زمني

  يُصدِّر دوال التحليل السياسي والمقارنة والخط الزمني.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_political_analysis(title: str, body: str = "", lang: str = "العربية 🇮🇶") -> str:
    """يحلل الخبر السياسي ويتوقع ما سيحدث"""
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    try:
        prompt = f"""أنت محلل سياسي متخصص بالشأن العراقي والمنطقة العربية.

الخبر: {title}
{('التفاصيل: ' + body[:500]) if body else ''}

قدم تحليلاً سريعاً ومباشراً بهذه النقاط:
1. 🎯 الأثر الفوري (جملة واحدة)
2. 🔮 التوقعات (ماذا سيحدث خلال أسبوع؟)
3. 🏛️ الأطراف المؤثرة (من المستفيد؟)
4. ⚡ مستوى الخطورة: [منخفض/متوسط/عالي/حرج]

كن مختصراً وجريئاً في تقييمك."""
        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:800]
    except Exception as e:
        return _ai_friendly_error(e, "timeline")

# ═══════════════════════════════════════════════════════════════════
# 3. مقارنة وجهات النظر
# ═══════════════════════════════════════════════════════════════════
def _ai_compare_perspectives(topic: str) -> str:
    """يقارن كيف غطّت مصادر مختلفة نفس الموضوع"""
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    try:
        # جمع أخبار من مصادر متنوعة
        sources_coverage = {}
        search_feeds = {
            "🇶🇦 الجزيرة": "https://www.aljazeera.net/xml/rss",
            "🇷🇺 RT عربي": "https://arabic.rt.com/rss/",
            "🇬🇧 BBC عربي": "https://feeds.bbci.co.uk/arabic/rss.xml",
            "🇺🇸 CNN عربي": "https://arabic.cnn.com/rss/latest",
        }
        for src_name, feed_url in search_feeds.items():
            try:
                feed = _parse_feed(feed_url)
                if not feed:
                    continue
                for entry in feed.entries[:20]:
                    entry_title = getattr(entry, 'title', '')
                    if topic.lower() in entry_title.lower():
                        sources_coverage[src_name] = entry_title
                        break
            except Exception as _exc:
                _log_exc(_exc)

        if len(sources_coverage) < 2:
            prompt = f"""قدّم مقارنة تحليلية لكيفية تغطية هذا الموضوع من منظور مصادر إعلامية مختلفة:
موضوع: {topic}
وضّح الفروق المتوقعة بين: الجزيرة، RT، BBC، CNN العربي، والإعلام العراقي.
اجعل الإجابة مختصرة (3-4 جمل لكل مصدر)."""
        else:
            coverage_text = "\n".join(f"{src}: {title}" for src, title in sources_coverage.items())
            prompt = f"""قارن هذه التغطيات الإعلامية لنفس الموضوع:

{coverage_text}

حلل:
1. نقاط الاتفاق بين المصادر
2. نقاط الاختلاف
3. من يُقدّم أكثر تحيزاً؟
4. ما الذي أغفله الجميع؟

كن موضوعياً وجريئاً."""
        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:1000]
    except Exception as e:
        return _ai_friendly_error(e, "compare")

# ═══════════════════════════════════════════════════════════════════
# 4. خريطة الأخبار الزمنية
# ═══════════════════════════════════════════════════════════════════
def _ai_build_timeline(topic: str) -> str:
    """يبني تسلسل زمني للأحداث المتعلقة بموضوع"""
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    try:
        # جمع أخبار متعلقة بالموضوع
        related_news = []
        for lang_feeds in RSS.values():
            for feed_url in lang_feeds[:5]:
                try:
                    feed = _parse_feed(feed_url)
                    if not feed:
                        continue
                    for entry in feed.entries[:15]:
                        title = getattr(entry, 'title', '')
                        if topic.lower() in title.lower():
                            pub = _pub_dt_from_item(entry)
                            pub_str = pub.strftime('%Y-%m-%d') if pub else 'تاريخ غير معروف'
                            related_news.append(f"[{pub_str}] {title}")
                except Exception as _exc:
                    _log_exc(_exc)

        if related_news:
            news_text = "\n".join(related_news[:15])
            prompt = f"""بناءً على هذه الأخبار المتعلقة بـ "{topic}"، ابنِ تسلسلاً زمنياً واضحاً للأحداث:

{news_text}

رتّبها من الأقدم للأحدث وأضف سياقاً لكل حدث."""
        else:
            prompt = f"""ابنِ تسلسلاً زمنياً تحليلياً لأبرز أحداث موضوع: "{topic}"
        
        من البداية حتى اليوم. استخدم معلوماتك العامة.
        الشكل: 📅 [تاريخ] — [الحدث] — [الأهمية]"""

        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:1500]
    except Exception as e:
        return _ai_friendly_error(e, "timeline")


# ═══════════════════════════════════════════════════════════════════
# الجيل الثاني — 8 ميزات أسطورية
# ═══════════════════════════════════════════════════════════════════

# ─── كاش البيانات ────────────────────────────────────────────────
_profile_cache    = {}   # name → {profile_text, timestamp}
_econ_last_alert  = {}   # indicator → timestamp
_user_interests   = {}   # uid → {topics: Counter, sources: Counter}
_parliament_cache = {"text": "", "timestamp": 0}

# ─── 1. محقق الشخصيات ──────────────────────────────────────────
@bot.message_handler(commands=["analyze"])
def handle_analyze_cmd(message):
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    text = message.text.replace('/analyze', '').strip()
    if not text:
        bot.send_message(message.chat.id, _ui("cmd_analyze_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id, _ui("cmd_analyze_loading", lang))
    result = _ai_political_analysis(text, lang=lang)
    reply = f"{_ui('cmd_analyze_hdr', lang)}\n\n📰 _{text[:60]}_\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

@bot.message_handler(commands=['compare'])
def handle_compare_cmd(message):
    uid = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    text = message.text.replace('/compare', '').strip()
    if not text:
        bot.send_message(message.chat.id, _ui("cmd_compare_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id, _ui("cmd_compare_loading", lang))
    result = _ai_compare_perspectives(text)
    reply = f"{_ui('cmd_compare_hdr', lang).format(topic=text)}\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

@bot.message_handler(commands=['timeline'])
def handle_timeline_cmd(message):
    if not _FF.get("timeline", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid_int = message.from_user.id
    uid = str(uid_int)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid_int, "timeline"):
        bot.send_message(message.chat.id, "⏳ انتظر دقيقة بين كل طلب للجدول الزمني.")
        return
    allowed, used, limit = _check_daily_ai_limit(uid_int, "timeline")
    if not allowed:
        bot.send_message(message.chat.id, f"📊 وصلت الحد اليومي للجداول الزمنية ({limit}/يوم). يتجدد الرصيد غداً.")
        return
    text = message.text.replace('/timeline', '').strip()
    if not text:
        bot.send_message(message.chat.id, _ui("cmd_timeline_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id, _ui("cmd_timeline_loading", lang))
    result = _ai_build_timeline(text)
    reply = f"{_ui('cmd_timeline_hdr', lang).format(topic=text)}\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

