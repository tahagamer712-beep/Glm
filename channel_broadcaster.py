# -*- coding: utf-8 -*-
"""
  channel_broadcaster.py — بث للقنوات والمجموعات

  يُصدِّر نظام البث للقنوات والمجموعات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: F401
# FIX: _fetch_one_feed من rss_fetcher — rss_fetcher مُحمَّل قبل channel_broadcaster
# في قائمة features_news.py (الترتيب: rss_fetcher=#8، channel_broadcaster=#10)
# لذا هذا الاستيراد الصريح آمن ويعمل بشكل مضمون.
from rss_fetcher import _fetch_one_feed  # noqa: F401

def broadcast_to_channels():
    """
    يُعالج فقط القنوات/المجموعات ذات المصادر المخصصة.
    القنوات العادية تحصل على أخبارها من broadcast_news مباشرة.
    """
    if bot_paused or broadcast_paused:
        return
    if _broadcast_channels_lock.is_set():
        return
    _broadcast_channels_lock.set()
    _broadcast_ch_lock_ts[0] = time.time()
    try:
        custom_chs = [ch for ch in channels_groups if ch.get('custom_sources') and not ch.get('paused')]
        if not custom_chs:
            return
        changed = False
        for ch in custom_chs:
            try:
                chat_id = ch["id"]
                lang = ch.get('lang', 'العربية 🇮🇶')
                custom_sources = ch.get('custom_sources', [])
                feeds = custom_sources if custom_sources else RSS.get(lang, RSS.get('العربية 🇮🇶', []))
                sent = set(ch.setdefault('sent_news', []))
                candidates = []

                # --- 1: RSS — يقرأ من _global_rss_cache فقط (لا جلب متزامن) ---
                # إذا لم يكن feed_url في الكاش بعد، نجلبه بشكل متوازٍ مرة واحدة
                missing = []
                with _global_rss_cache_lock:
                    for feed_url in feeds:
                        if feed_url not in _global_rss_cache:
                            missing.append(feed_url)
                if missing:
                    def _fetch_m(url):
                        entries = _fetch_one_feed(url)
                        with _global_rss_cache_lock:
                            _global_rss_cache[url] = (entries, time.time())
                    with ThreadPoolExecutor(max_workers=min(3, len(missing))) as _ex:  # HEROKU: حد 3 خيوط
                        _futs = {_ex.submit(_fetch_m, u): u for u in missing}
                        for _f in as_completed(_futs, timeout=15):
                            try: _f.result()
                            except Exception: pass

                with _global_rss_cache_lock:
                    all_ch_entries = []
                    for feed_url in feeds:
                        cached = _global_rss_cache.get(feed_url)
                        if cached:
                            all_ch_entries.extend(cached[0])

                for entry in all_ch_entries:
                    link  = entry.get("link", "")
                    title = entry.get("title", "")
                    if not link or link in sent:
                        continue
                    if is_blacklisted(title):
                        continue
                    pub_dt = entry.get("published_dt")
                    if pub_dt is not None and not _is_fresh(pub_dt):
                        continue
                    candidates.append((link, title, entry.get("feed_url", ""), entry.get("summary", ""), pub_dt))

                # --- 2: Scraping مواقع إخبارية ---
                if _BS4_AVAILABLE and not custom_sources:
                    for src in SCRAPE_SOURCES.get(lang, []):
                        try:
                            scraped = _scrape_news_site(src['url'], src['base_url'], max_items=10)
                            for s_title, s_link in scraped:
                                if s_link in sent or is_blacklisted(s_title):
                                    continue
                                if not _title_in_lang(s_title, lang):
                                    continue
                                candidates.append((s_link, s_title, src['url'], '', None))
                        except Exception as _exc:
                            _log_exc(_exc)

                # --- 3: قنوات تلغرام (حصة مضمونة 30 خبر) ---
                if _BS4_AVAILABLE and not custom_sources:
                    tg_collected = 0
                    for tg_ch in TELEGRAM_NEWS_CHANNELS.get(lang, []):
                        if tg_collected >= 9999:
                            break
                        try:
                            tg_posts = _scrape_telegram_channel(tg_ch['handle'], max_items=8)
                            for tg_item in tg_posts:
                                raw_text, tg_link = tg_item[0], tg_item[1]
                                tg_pub_dt = tg_item[2] if len(tg_item) > 2 else None
                                if tg_collected >= 9999:
                                    break
                                # تطبيع الرابط: تجاهل معاملات URL لمنع تكرار نفس الخبر برابط مختلف
                                uid_key = _normalize_news_link(tg_link) if tg_link else raw_text[:80]
                                if uid_key in sent or is_blacklisted(raw_text):
                                    continue
                                if _is_tg_spam(raw_text, tg_link):
                                    continue
                                clean_title = _ai_clean_news(raw_text, link=tg_link)
                                if not clean_title or len(clean_title) < 15:
                                    continue
                                src_label = f"t.me/{tg_ch['handle']}"
                                candidates.append((tg_link or uid_key, clean_title, src_label, raw_text, tg_pub_dt))
                                tg_collected += 1
                        except Exception as _exc:
                            _log_exc(_exc)

                # --- 4: NewsAPI (non-blocking) ---
                # FIX: نفس إصلاح news_broadcaster.py — نُشغّل في executor منفصل
                # مع timeout قاسٍ (4ث) لمنع تعليق دورة بث القنوات.
                if NEWS_KEY and not custom_sources:
                    try:
                        lang_code = LANG_CODES.get(lang, "ar")
                        na_url = (
                            f"https://newsapi.org/v2/top-headlines"
                            f"?language={lang_code}&pageSize=10&apiKey={NEWS_KEY}"
                        )
                        from concurrent.futures import ThreadPoolExecutor as _CHEX, TimeoutError as _CHTO
                        def _fetch_ch_newsapi():
                            return requests.get(na_url, timeout=5)
                        with _CHEX(max_workers=1) as _chex:
                            _ch_fut = _chex.submit(_fetch_ch_newsapi)
                            try:
                                na_r = _ch_fut.result(timeout=4)
                            except (_CHTO, Exception) as _ch_exc:
                                _logger.debug("⚡ channel NewsAPI skipped (non-blocking timeout): %s", _ch_exc)
                                na_r = None
                        if na_r is not None and na_r.status_code == 200:
                            for art in na_r.json().get("articles", []):
                                na_link  = art.get("url", "")
                                na_title = art.get("title", "")
                                na_desc  = art.get("description", "") or ""
                                if na_link and na_title and na_link not in sent:
                                    if not is_blacklisted(na_title):
                                        src_name = art.get("source", {}).get("name", "NewsAPI")
                                        na_pub_str = art.get("publishedAt", "")
                                        try:
                                            na_pub_dt = datetime.datetime.strptime(
                                                na_pub_str, "%Y-%m-%dT%H:%M:%SZ"
                                            ) if na_pub_str else None
                                        except Exception:
                                            na_pub_dt = None
                                        candidates.append((na_link, na_title, src_name, na_desc, na_pub_dt))
                    except Exception as _exc:
                        _log_exc(_exc)

                # --- فلتر اللغة + كشف التكرار الذكي ---
                candidates = [c for c in candidates if _title_in_lang(c[1], lang)]
                candidates = _dedup_news_list(candidates)

                # --- إرسال حتى MAX_NEWS_PER_BROADCAST خبر ---
                sent_this_channel = 0
                for cand in candidates:
                    if sent_this_channel >= MAX_NEWS_PER_BROADCAST:
                        break
                    link  = cand[0]
                    title = cand[1]
                    feed_url     = cand[2]
                    item_summary = cand[3]
                    pub_dt       = cand[4] if len(cand) > 4 else None
                    # تطبيع الرابط: إزالة معاملات URL (timestamps, utm_source) لمنع تكرار نفس الخبر
                    link_key = _normalize_news_link(link) if link else title[:80]
                    title_key = title.strip()[:70]  # تتبع العنوان لمنع التكرار بروابط مختلفة
                    if link_key in sent or title_key in sent:
                        continue
                    sent.add(link_key)
                    sent.add(title_key)
                    ch["sent_news"] = list(sent)[-2000:]   # FIX: كان -5000 يُثقل الذاكرة
                    ch["news_sent_count"] = ch.get("news_sent_count", 0) + 1
                    changed = True
                    sent_this_channel += 1
                    src_name = get_source_name_from_url(feed_url)
                    pub_time_str = _format_pub_time(pub_dt, lang=lang)
                    # AI تنظيف العنوان لأخبار RSS/Scraping (قنوات TG نُنظَّف مسبقاً)
                    if _AI_AVAILABLE and not str(feed_url).startswith("t.me/"):
                        try:
                            _clean = _ai_clean_news(title, body=item_summary[:600] if item_summary else '', link=link)
                            if _clean and len(_clean) > 10:
                                title = _clean
                        except Exception as _exc:
                            _log_exc(_exc)
                    news_text = format_news_item(t(lang, "label_breaking"), title, lang, src_name, pub_time_str, summary=item_summary)
                    # القنوات: زر مصدر فقط — المجموعات: markup كامل
                    _ch_type   = ch.get('type', 'channel')
                    _lnk_lower = (link or "").lower()
                    _is_tg = "t.me/" in _lnk_lower or "telegram.me/" in _lnk_lower
                    if _ch_type in ('group', 'supergroup'):
                        ch_markup = make_news_share_markup(link, title, lang, item_summary)
                    elif link and _lnk_lower.startswith(("http://", "https://")):
                        ch_markup = types.InlineKeyboardMarkup()
                        if _is_tg:
                            _tg_handle = ""
                            try:
                                _tg_parts = link.rstrip('/').split('t.me/')
                                if len(_tg_parts) > 1:
                                    _tg_handle = "@" + _tg_parts[1].split('/')[0].lstrip('@')
                            except Exception:
                                pass
                            _btn_lbl = f"📢 {_tg_handle}" if _tg_handle else "📢 المصدر"
                        else:
                            _btn_lbl = f"🔗 {src_name}" if src_name else "🔗 المصدر"
                        ch_markup.add(types.InlineKeyboardButton(_btn_lbl, url=link))
                    else:
                        ch_markup = None
                    queue_send(chat_id, news_text, parse_mode="Markdown", reply_markup=ch_markup)
            except Exception:
                continue
        if changed:
            save_channels_groups()
    except Exception as e:
        try:
            bot.send_message(ADMIN_ID, f"⚠️ خطأ في broadcast_to_channels: {e}")
        except Exception as _exc:
            _log_exc(_exc)
    finally:
        _broadcast_channels_lock.clear()

def _send_group_news(chat_id, title, link, lang, summary=""):
    """يرسل خبراً للمجموعة مع أزرار تصويت"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    msg_placeholder = bot.send_message(chat_id,
        f"📰 *{title}*\n🔗 [اقرأ الخبر]({link})",
        parse_mode="Markdown"
    )
    mid = msg_placeholder.message_id
    _group_votes[mid] = {"title": title, "link": link, "yes": set(), "no": set(), "chat_id": chat_id}
    markup.add(
        types.InlineKeyboardButton("👍 مهم", callback_data=f"gvote_yes_{mid}"),
        types.InlineKeyboardButton("👎 غير مهم", callback_data=f"gvote_no_{mid}"),
        types.InlineKeyboardButton("🔗 فتح", url=link),
    )
    try:
        bot.edit_message_reply_markup(chat_id, mid, reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)
    return mid


@bot.callback_query_handler(func=lambda c: c.data.startswith("gvote_"))
def on_bot_chat_member_update(update):
    new_status = update.new_chat_member.status
    old_status = update.old_chat_member.status
    chat = update.chat
    chat_id = chat.id
    chat_type = chat.type

    if chat_type not in ("channel", "group", "supergroup"):
        return

    if new_status in ("administrator", "member") and old_status in ("left", "kicked", "restricted"):
        title = chat.title or str(chat_id)
        already = any(ch["id"] == chat_id for ch in channels_groups)
        if not already:
            default_lang = "العربية 🇮🇶"
            auto_feeds = RSS.get(default_lang, [])
            initial_sent = list(prefill_sent_news(auto_feeds).keys())
            channels_groups.append({
                "id": chat_id,
                "title": title,
                "type": chat_type,
                "lang": default_lang,
                "city": "",
                "sent_news": initial_sent
            })
            save_channels_groups()
        try:
            bot.send_message(chat_id, CHANNEL_WELCOME_MSG, parse_mode="Markdown")
        except Exception as e:
            notify_admin_error(f"خطأ في إرسال رسالة الترحيب للقناة {title}: {e}")
        notify_admin_error(f"✅ تمت إضافة البوت لـ: *{title}* (`{chat_id}`) — النوع: {chat_type}")

    elif new_status in ("left", "kicked") and old_status in ("administrator", "member"):
        title = chat.title or str(chat_id)
        for i, ch in enumerate(channels_groups):
            if ch["id"] == chat_id:
                channels_groups.pop(i)
                save_channels_groups()
                break
        notify_admin_error(f"⚠️ تمت إزالة البوت من: *{title}* (`{chat_id}`)")


# ======== أوامر التحكم داخل القناة/المجموعة ========
VALID_LANGS = ["العربية 🇮🇶", "English 🇬🇧", "فارسی 🇮🇷", "Türkçe 🇹🇷"]
