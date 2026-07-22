# -*- coding: utf-8 -*-
"""
  ai_memory.py — ذاكرة الأمة (هذا اليوم في التاريخ)

  يُصدِّر نظام الذاكرة التاريخية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _check_followed_stories(items_by_lang):
    """
    يفحص الأخبار الجديدة ويُرسل للمستخدمين الذين يتابعون كلمة مفتاحية معينة
    """
    if not _story_followers:
        return
    for keyword, followers in list(_story_followers.items()):
        kw_lower = keyword.lower()
        for uid_str, lang in list(followers.items()):
            uid = int(uid_str)
            items = items_by_lang.get(lang, [])
            for entry in items:
                link = entry[0] if len(entry) > 0 else ''
                title = entry[1] if len(entry) > 1 else ''
                feed_url = entry[2] if len(entry) > 2 else ''
                item_sum = entry[3] if len(entry) > 3 else ''
                pub_dt = entry[4] if len(entry) > 4 else None
                if kw_lower in title.lower():
                    src_name = get_source_name_from_url(feed_url)
                    pub_time_str = _format_pub_time(pub_dt, lang=lang)
                    story_label = t(lang, "label_breaking") + " 🔔"
                    msg_body = format_news_item(story_label, title, lang, src_name, pub_time_str, summary=item_sum)
                    # سطر متابعة يُضاف في الأعلى
                    follow_note = NEWS_SHARE_LABELS.get(lang, NEWS_SHARE_LABELS["English 🇬🇧"]).get("story_update", "🔔 Story Update")
                    msg = f"{follow_note}: `{keyword}`\n\n{msg_body}"
                    markup = make_news_share_markup(link, title, lang, item_sum)
                    try:
                        bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=markup)
                    except Exception as _exc:
                        _log_exc(_exc)
                    break  # خبر واحد لكل قصة لكل دورة


@bot.message_handler(commands=["follow"])
def cmd_follow(m):
    """متابعة كلمة مفتاحية — سيُرسل البوت فور ظهورها في الأخبار"""
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    parts = m.text.strip().split(None, 1)
    if len(parts) < 2:
        user = users.get(str(uid), {})
        followed = user.get("followed_stories", [])
        if not followed:
            bot.send_message(uid, _ui("cmd_follow_usage", lang), parse_mode="Markdown")
        else:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for kw in followed:
                markup.add(types.InlineKeyboardButton(
                    _ui("cmd_follow_unfollow_btn", lang).format(kw=kw),
                    callback_data=f"unfollow_{kw[:30]}"
                ))
            bot.send_message(uid,
                f"{_ui('cmd_follow_list_hdr', lang)}\n" +
                "\n".join(f"• `{kw}`" for kw in followed) +
                _ui("cmd_follow_press_unfollow", lang),
                parse_mode="Markdown", reply_markup=markup
            )
        return
    keyword = parts[1].strip()[:50]
    # أضف للقائمة العامة
    if keyword not in _story_followers:
        _story_followers[keyword] = {}
    _story_followers[keyword][str(uid)] = lang
    # أضف لإعدادات المستخدم
    if str(uid) in users:
        followed = users[str(uid)].get("followed_stories", [])
        if keyword not in followed:
            followed.append(keyword)
            users[str(uid)]["followed_stories"] = followed
            _db_save_user(uid, users[str(uid)])
    unfollow_hint = {
        "العربية 🇮🇶": f"✅ *ستصلك أخبار عن:* `{keyword}`\n\nلإلغاء: `/unfollow {keyword}`",
        "English 🇬🇧":  f"✅ *You'll receive news about:* `{keyword}`\n\nTo stop: `/unfollow {keyword}`",
    }
    bot.send_message(uid,
        unfollow_hint.get(lang, unfollow_hint["English 🇬🇧"]),
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["unfollow"])
def cmd_unfollow(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    parts = m.text.strip().split(None, 1)
    if len(parts) < 2:
        bot.send_message(uid, _ui("cmd_unfollow_usage", lang), parse_mode="Markdown")
        return
    keyword = parts[1].strip()
    _story_followers.pop(keyword, None)
    if str(uid) in users:
        followed = users[str(uid)].get("followed_stories", [])
        followed = [f for f in followed if f != keyword]
        users[str(uid)]["followed_stories"] = followed
        _db_save_user(uid, users[str(uid)])
    bot.send_message(uid, _ui("cmd_unfollow_done", lang).format(kw=keyword), parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("unfollow_") and not c.data.startswith("unfollow_story_"))
def cb_unfollow(call):
    # إصلاح #2: نستثني unfollow_story_ لتجنب التعارض مع handle_unfollow_story_button
    bot.answer_callback_query(call.id)
    uid = call.from_user.id
    keyword = call.data[len("unfollow_"):]
    _story_followers.pop(keyword, None)
    if str(uid) in users:
        followed = users[str(uid)].get("followed_stories", [])
        followed = [f for f in followed if f != keyword]
        users[str(uid)]["followed_stories"] = followed
        _db_save_user(uid, users[str(uid)])
    bot.send_message(uid, f"✅ تم إلغاء متابعة: `{keyword}`", parse_mode="Markdown")


# ======================================================
# ميزة: الملخص الأسبوعي (كل جمعة الساعة 10:00)
# ======================================================
_weekly_top_news = {}  # lang → list of (title, link, count)
_weekly_news_lock = False


@bot.message_handler(commands=["storyline"])
def cmd_storyline(m):
    """
    /storyline <كلمة مفتاحية>
    يُنشئ خطاً زمنياً للأحداث المتعلقة بالكلمة المفتاحية.
    """
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return

    user  = users.get(str(uid), {})
    lang  = user.get("lang", "العربية 🇮🇶")
    topic = m.text.strip()[len("/storyline"):].strip()
    if not topic:
        bot.send_message(uid,
            "🗓 *خط الأحداث*\n\n"
            "أرسل: `/storyline <موضوع>`\n\n"
            "مثال: `/storyline العراق`\n"
            "_سأبني خطاً زمنياً للأحداث الرئيسية المتعلقة بهذا الموضوع_",
            parse_mode="Markdown")
        return

    wait_msg = bot.send_message(uid,
        f"🗓 *جاري بناء خط الأحداث لـ '{topic}'...*\n_بضع ثوانٍ_",
        parse_mode="Markdown")

    def _do():
        timeline = _ai_build_timeline(topic)
        sep = "━━━━━━━━━━━━━━"
        reply = (
            f"🗓 *خط الأحداث: {topic}*\n{sep}\n\n"
            f"{timeline}\n{sep}"
        )
        try:
            bot.edit_message_text(reply, uid, wait_msg.message_id,
                                  parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            try:
                bot.send_message(uid, reply, parse_mode="Markdown", disable_web_page_preview=True)
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== /audiobriefing — ملخص الأخبار كنص منسّق (جاهز لـ TTS) ========
def _update_narrative(title: str, source: str):
    """
    يُتتبع الأحداث الكبيرة ويبني ملف حي لها.
    يُضيف الخبر لأقرب موضوع موجود (Jaccard ≥ 50%).
    """
    words_new = set(w for w in title.split() if len(w) > 3)
    best_key, best_sim = None, 0.0
    for key, events in _narrative_store.items():
        if not events: continue
        first_title = events[0].get("title", "")
        words_old   = set(w for w in first_title.split() if len(w) > 3)
        if not words_old: continue
        sim = len(words_new & words_old) / len(words_new | words_old) if (words_new | words_old) else 0
        if sim > best_sim:
            best_sim, best_key = sim, key

    entry = {"title": title, "source": source, "ts": time.time()}
    if best_sim >= 0.50 and best_key:
        _narrative_store[best_key].append(entry)
        if len(_narrative_store[best_key]) > 20:
            _narrative_store[best_key] = _narrative_store[best_key][-20:]
    else:
        import hashlib
        key = hashlib.md5(title.encode()).hexdigest()[:8]
        _narrative_store[key] = [entry]
        # لا نحتفظ بأكثر من 500 موضوع
        if len(_narrative_store) > 500:
            oldest = sorted(_narrative_store.keys(),
                            key=lambda k: _narrative_store[k][-1]["ts"])[:100]
            for k in oldest:
                del _narrative_store[k]
    _save_narratives()

