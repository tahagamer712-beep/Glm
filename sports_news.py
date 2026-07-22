# -*- coding: utf-8 -*-
"""
  sports_news.py — أخبار رياضية (RSS مخصص)

  يُصدِّر دوال جلب وعرض الأخبار الرياضية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _send_sports_news(uid, chat_id, msg_id=None):
    """
    إصلاح #6: يستخدم SPORTS_RSS (dict بلغات، 14+ مصدر)
    بدلاً من SPORTS_NEWS_RSS (4 مصادر فقط).
    """
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    # إصلاح #6: ابحث عن المصادر المناسبة للغة في SPORTS_RSS (dict)
    filtered_feeds = SPORTS_RSS.get(lang) or SPORTS_RSS.get('العربية 🇮🇶', [])

    items = []
    seen_titles = set()
    for feed_url in filtered_feeds:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:5]:
                title = getattr(entry, 'title', '').strip()
                link  = getattr(entry, 'link', '').strip()
                key   = title[:40].lower()
                if title and link and key not in seen_titles:
                    seen_titles.add(key)
                    items.append((title, link))
            if len(items) >= 15:
                break
        except Exception as _exc:
            _log_exc(_exc)

    if not items:
        text = "📰 *أخبار رياضية*\n\nلا توجد أخبار الآن، حاول لاحقاً."
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("🔄 تحديث", callback_data="sp_news"),
            types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_main"),
        )
        try:
            if msg_id:
                bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=kb)
            else:
                bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=kb)
        return
    # إرسال كل خبر بشكل منفصل بنفس تنسيق الأخبار العادية (format_news_item + أزرار)
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    label_sports = "⚽ رياضة"
    sent_count = 0
    for title, link in items[:8]:
        try:
            markup = make_news_share_markup(link, title, lang, "")
            news_text = format_news_item(label_sports, title, lang, "", "", summary="")
            bot.send_message(chat_id, news_text, parse_mode="Markdown",
                             reply_markup=markup, disable_web_page_preview=True)
            sent_count += 1
        except Exception as _exc:
            _log_exc(_exc)
    if sent_count == 0:
        bot.send_message(chat_id, "📰 *أخبار رياضية*\n\nلا توجد أخبار الآن، حاول لاحقاً.", parse_mode="Markdown")

# كاش الأحداث الرياضية: match_id → {state, home_score, away_score, known_events: set}
_sports_match_cache = {}

def send_sports_news(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "العربية 🇮🇶")
    feeds = SPORTS_RSS.get(lang) or SPORTS_RSS.get("العربية 🇮🇶", [])
    if not feeds:
        bot.send_message(uid, t(lang, "no_sports_source"))
        return
    sent = user.setdefault("sent_news", {})
    count = 0
    bot.send_message(uid, t(lang, "sports_header"), parse_mode="Markdown")
    for feed_url in feeds:
        try:
            feed = _parse_feed(feed_url)
            if feed is None:
                feed = feedparser.parse(feed_url)
            if not feed:
                continue
            for item in feed.entries[:5]:
                if not hasattr(item, 'link') or item.link in sent:
                    continue
                sent[item.link] = time.time()
                item_sum = getattr(item, 'summary', '') or getattr(item, 'description', '')
                markup = make_news_share_markup(item.link, getattr(item, 'title', ''), lang, item_sum)
                src_name = get_source_name_from_feed(feed, feed_url)
                title_s = getattr(item, 'title', '').strip()
                pub_time_str = _format_pub_time(_pub_dt_from_item(item), lang=lang)
                bot.send_message(uid, format_news_item(t(lang, "label_sports"), title_s, lang, src_name, pub_time_str, summary=item_sum), parse_mode="Markdown", reply_markup=markup)
                count += 1
                if count >= 8:
                    break
        except Exception as _exc:
            _log_exc(_exc)  # فشل مصدر رياضي لا يوقف باقي المصادر
        if count >= 8:
            break
    if count == 0:
        bot.send_message(uid, t(lang, "no_sports"))
    else:
        _db_save_all_users(users)

# ======== محوّل العملات ========
CURRENCY_SYMBOLS = {
    "USD": "🇺🇸 دولار أمريكي",
    "EUR": "🇪🇺 يورو",
    "GBP": "🇬🇧 جنيه إسترليني",
    "IQD": "🇮🇶 دينار عراقي",
    "SAR": "🇸🇦 ريال سعودي",
    "AED": "🇦🇪 درهم إماراتي",
    "TRY": "🇹🇷 ليرة تركية",
    "IRR": "🇮🇷 ريال إيراني",
    "KWD": "🇰🇼 دينار كويتي",
    "JOD": "🇯🇴 دينار أردني",
    "EGP": "🇪🇬 جنيه مصري",
    "RUB": "🇷🇺 روبل روسي",
    "CNY": "🇨🇳 يوان صيني",
    "INR": "🇮🇳 روبية هندية",
}
