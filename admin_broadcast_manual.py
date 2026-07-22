# -*- coding: utf-8 -*-
"""
  admin_broadcast_manual.py — البث اليدوي + خبر عاجل مخصص

  يُصدِّر دوال البث اليدوي وإرسال الأخبار العاجلة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def breaking_news_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    lines = message.text.strip().split("\n")
    news_text = lines[0].strip()
    link = lines[1].strip() if len(lines) > 1 and lines[1].startswith("http") else ""
    full_msg = f"🚨 *خبر عاجل*\n\n📰 {news_text}{BOT_SIGNATURE}"
    sent_users = 0
    failed_users = 0
    for target_uid in list(users.keys()):
        if int(target_uid) in banned:
            continue
        try:
            user_lang = users.get(target_uid, {}).get("lang", "English 🇬🇧")
            user_markup = make_news_share_markup(link, news_text, user_lang) if link else None
            bot.send_message(target_uid, full_msg, parse_mode="Markdown", reply_markup=user_markup)
            sent_users += 1
        except Exception:
            failed_users += 1
    sent_ch = 0
    for ch in list(channels_groups):
        try:
            # القنوات: زر رابط المصدر فقط — بدون أزرار تفاعلية
            _lnk_lower = (link or "").lower()
            if link and _lnk_lower.startswith(("http://", "https://")):
                _is_tg = "t.me/" in _lnk_lower or "telegram.me/" in _lnk_lower
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
                    _btn_lbl = "🔗 المصدر"
                ch_markup.add(types.InlineKeyboardButton(_btn_lbl, url=link))
            else:
                ch_markup = None
            bot.send_message(ch["id"], full_msg, parse_mode="Markdown", reply_markup=ch_markup)
            sent_ch += 1
        except Exception as _exc:
            _log_exc(_exc)
    bot.send_message(uid,
        f"✅ *تم إرسال الخبر العاجل:*\n\n"
        f"👤 المستخدمون: `{sent_users}` وصل، `{failed_users}` فشل\n"
        f"📺 القنوات/المجموعات: `{sent_ch}` وصل",
        parse_mode="Markdown"
    )

def broadcast_all_step(message):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    count, failed = 0, 0
    uid_list = list(users.keys())
    bot.send_message(message.from_user.id, f"⏳ جاري الإرسال لـ {len(uid_list)} مستخدم...")
    def _send_one(uid):
        try:
            bot.send_message(uid, text)
            return True
        except Exception:
            return False
    from concurrent.futures import ThreadPoolExecutor as _TPE2
    with _TPE2(max_workers=4) as ex:  # HEROKU: حد 4 خيوط للإرسال الجماعي
        results = list(ex.map(_send_one, uid_list))
    count = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    bot.send_message(message.from_user.id, f"📢 *تم الإرسال:*\n✅ نجح: `{count}`\n❌ فشل: `{failed}`", parse_mode="Markdown")

def broadcast_country_step(message):
    if not is_admin(message.from_user.id):
        return
    lines = message.text.split("\n", 1)
    if len(lines) < 2:
        bot.send_message(message.from_user.id, "❌ أرسل الدولة ثم الرسالة في سطرين.")
        return
    country, text = lines[0].strip(), lines[1].strip()
    targets = [uid for uid, info in list(users.items()) if info.get("country") == country]
    bot.send_message(message.from_user.id, f"⏳ جاري الإرسال لـ {len(targets)} مستخدم في {country}...")
    count = 0
    for uid in targets:
        try:
            bot.send_message(uid, text)
            count += 1
            time.sleep(0.05)
        except Exception as _exc:
            _log_exc(_exc)
    bot.send_message(message.from_user.id, f"✅ تم الإرسال لـ `{count}` مستخدم في {country}", parse_mode="Markdown")

def broadcast_lang_step(message):
    if not is_admin(message.from_user.id):
        return
    lines = message.text.split("\n", 1)
    if len(lines) < 2:
        bot.send_message(message.from_user.id, "❌ أرسل اللغة ثم الرسالة في سطرين.")
        return
    lang, text = lines[0].strip(), lines[1].strip()
    targets = [uid for uid, info in list(users.items()) if info.get("lang") == lang]
    bot.send_message(message.from_user.id, f"⏳ جاري الإرسال لـ {len(targets)} مستخدم...")
    count = 0
    for uid in targets:
        try:
            bot.send_message(uid, text)
            count += 1
            time.sleep(0.05)
        except Exception as _exc:
            _log_exc(_exc)
    bot.send_message(message.from_user.id, f"✅ تم الإرسال لـ `{count}` مستخدم يتحدث {lang}", parse_mode="Markdown")

def broadcast_premium_step(message):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    targets = list(stats.get("premium_users", []))
    bot.send_message(message.from_user.id, f"⏳ جاري الإرسال لـ {len(targets)} مستخدم مميز...")
    count = 0
    for uid in targets:
        try:
            bot.send_message(uid, text)
            count += 1
            time.sleep(0.05)
        except Exception as _exc:
            _log_exc(_exc)
    bot.send_message(message.from_user.id, f"⭐ تم الإرسال لـ `{count}` مستخدم مميز", parse_mode="Markdown")

def pause_bot_step(message):
    global bot_paused, pause_message, _pause_since
    if message.text.strip() != "افتراضي":
        pause_message = message.text.strip()
    bot_paused = True
    _pause_since = datetime.datetime.now()
    bot.send_message(message.from_user.id, "🔴 تم إيقاف البوت مؤقتاً.\nأرسل /admin ثم 'إيقاف/تشغيل البوت' لإعادة التشغيل.")

@bot.message_handler(commands=["resetbroadcast"])
def cmd_resetbroadcast(m):
    """إعادة تشغيل البث كاملاً: يرفع الإيقاف + يحرر الأقفال + يمسح global_sent — للأدمن فقط"""
    global bot_paused, broadcast_paused, pause_message
    uid = m.from_user.id
    if not is_admin(uid):
        return
    # 1. رفع جميع حالات الإيقاف
    was_paused = bot_paused or broadcast_paused
    bot_paused = False
    broadcast_paused = False
    pause_message = ""
    # 2. تحرير الأقفال إن كانت عالقة
    locks_cleared = 0
    if _broadcast_news_lock.is_set():
        _broadcast_news_lock.clear()
        locks_cleared += 1
    if _broadcast_channels_lock.is_set():
        _broadcast_channels_lock.clear()
        locks_cleared += 1
    # 3. مسح global_sent_news لإرسال الأخبار الجديدة فوراً
    with _global_sent_lock:
        old_count = sum(len(s) for s in _global_sent_news.values())
        _global_sent_news.clear()
    _save_global_sent_news()
    # 4. إرسال تقرير
    active_u = sum(1 for i in users.values() if i.get("notifications", True) and i.get("lang"))
    status = "✅ كان متوقفاً — تم إعادة التشغيل" if was_paused else "✅ لم يكن متوقفاً"
    bot.send_message(uid,
        f"🔄 *إعادة تشغيل البث الكاملة*\n\n"
        f"حالة الإيقاف: {status}\n"
        f"أقفال محررة: {locks_cleared}\n"
        f"روابط محذوفة من global_sent: {old_count:,}\n\n"
        f"👥 مستخدمون فعّالون: {active_u}\n"
        f"📡 البث سيبدأ في الدورة القادمة (30 ثانية)\n\n"
        f"{'⚠️ لا يوجد مستخدمون نشطون! أرسل /start واختر لغة' if active_u == 0 else ''}",
        parse_mode="Markdown"
    )
    # 5. إطلاق بث فوري — FIX: مباشر بدل Thread منفصل
    if active_u > 0 or channels_groups:
        _safe_job(broadcast_news)()


@bot.message_handler(commands=["forcenews"])
def cmd_forcenews(m):
    """
    يُشغّل دورة بث فورية — للأدمن فقط.
    - يُفرج عن أي قفل عالق تلقائياً (إذا >5 دقائق)
    - يُبلّغ بالنتيجة: كم خبر أُرسل لكم مستخدم/قناة
    - لا يتوقف بسبب broadcast_paused (يُجبر البث)
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    # ── 1. تحقق من القفل ──
    if _broadcast_news_lock.is_set():
        lock_age = time.time() - _broadcast_lock_ts[0] if _broadcast_lock_ts[0] else 0
        if lock_age < 300:  # أقل من 5 دقائق — ربما شغّال فعلاً
            remaining = int(300 - lock_age)
            bot.send_message(
                uid,
                f"⚠️ دورة بث شغّالة الآن (عمرها {lock_age/60:.0f} دقيقة).\n"
                f"انتظر {remaining//60}:{remaining%60:02d} دقيقة أو أعد المحاولة."
            )
            return
        else:
            # القفل عالق — افرج عنه بالقوة
            _broadcast_news_lock.clear()
            _broadcast_lock_ts[0] = 0
            bot.send_message(uid, f"🔓 أُفرج عن قفل عالق (كان مشغولاً {lock_age/60:.0f} دقيقة)")

    # ── 2. تحقق من إيقاف البوت الكلي ──
    global bot_paused, broadcast_paused
    if bot_paused:
        bot.send_message(uid, "❌ البوت متوقف كلياً (bot_paused=True). أرسل /resetbroadcast أولاً.")
        return

    # ── 3. إذا broadcast_paused، أوقف مؤقتاً للبث القسري ──
    was_paused = broadcast_paused
    if was_paused:
        broadcast_paused = False
        bot.send_message(uid, "⚡ تم تعليق إيقاف البث مؤقتاً لإجراء البث الفوري...")

    # ── 4. سجّل إحصائيات ما قبل البث ──
    try:
        with _broadcast_stats_lock:
            before_sent = _broadcast_stats.get("today_news_sent", 0)
            before_usr  = _broadcast_stats.get("today_users_reached", 0)
    except Exception:
        before_sent = before_usr = 0

    status_msg = bot.send_message(uid, "⏳ يُطلق البث الفوري...")

    def _force_run():
        global broadcast_paused
        try:
            broadcast_news()
        finally:
            # أعد حالة البث إذا كانت موقوفة
            if was_paused:
                broadcast_paused = True
            # أرسل ملخص النتيجة
            try:
                with _broadcast_stats_lock:
                    after_sent = _broadcast_stats.get("today_news_sent", 0)
                    after_usr  = _broadcast_stats.get("today_users_reached", 0)
                delta_sent = after_sent - before_sent
                delta_usr  = after_usr  - before_usr
                ch_count   = len(channels_groups) if channels_groups else 0
                result_txt = (
                    f"✅ اكتملت دورة البث الفوري\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📨 أُرسل: {delta_sent} خبر جديد\n"
                    f"👥 وصل: {delta_usr} مستخدم\n"
                    f"📢 القنوات/المجموعات: {ch_count}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                )
                if delta_sent == 0:
                    result_txt += (
                        "⚠️ لم يُرسل شيء — الأسباب المحتملة:\n"
                        "  • global_sent ممتلئ → /clearcache\n"
                        "  • لا مستخدمون فعّالون → /start واختر لغة\n"
                        "  • الأخبار قديمة → انتظر 30 دقيقة\n"
                        "🔍 للتشخيص التفصيلي: /debugnews"
                    )
                bot.edit_message_text(result_txt, uid, status_msg.message_id)
            except Exception as _exc:
                _log_exc(_exc)

    _start_thread_once("ForceBroadcast", _force_run)


@bot.message_handler(commands=["testnews"])
def cmd_testnews(m):
    """
    اختبار خط أنابيب الأخبار خطوة بخطوة — للأدمن فقط.
    يُجيب على: لماذا لا تصل الأخبار؟
    يتجاوز global_sent ويُرسل خبراً حقيقياً مباشرة.
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return
    bot.send_message(uid, "🧪 بدء اختبار خط أنابيب الأخبار... انتظر 15 ثانية")

    report = []
    lang = "العربية 🇮🇶"

    # ══ المرحلة 1: جلب RSS ══
    feeds = RSS.get(lang, [])
    report.append(f"📡 المرحلة 1: RSS feeds متاحة = {len(feeds)}")
    if not feeds:
        bot.send_message(uid, "\n".join(report) + "\n❌ توقف: لا توجد feeds للعربية!")
        return

    test_url = feeds[0]
    try:
        entries = _fetch_one_feed(test_url)
        report.append(f"  ✅ {test_url.split('/')[2]}: {len(entries)} مقال")
    except Exception as e:
        report.append(f"  ❌ فشل الجلب: {e}")
        entries = []
    if not entries:
        bot.send_message(uid, "\n".join(report) + "\n❌ توقف: RSS يعيد فارغاً!")
        return

    # ══ المرحلة 2: فلتر الحداثة ══
    fresh = [e for e in entries if _is_fresh(e.get("published_dt"))]
    report.append(f"⏱ المرحلة 2: بعد فلتر الحداثة (120 دق) = {len(fresh)}/{len(entries)}")
    if fresh:
        ex = fresh[0]
        pd = ex.get("published_dt")
        age_str = f"{int((datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)-pd).total_seconds()/60)}د" if pd else "مجهول"
        report.append(f"  أحدث خبر: عمره={age_str} | {ex['title'][:40]}")
    else:
        report.append("  ⚠️ كل الأخبار عمرها > 120 دقيقة!")
    source = fresh if fresh else entries[:5]

    # ══ المرحلة 3: فلتر البلاك ليست ══
    after_bl = [e for e in source if not is_blacklisted(e["title"])]
    report.append(f"🚫 المرحلة 3: بعد البلاك ليست = {len(after_bl)}/{len(source)}")
    dropped_bl = len(source) - len(after_bl)
    if dropped_bl > 0:
        report.append(f"  ⚠️ {dropped_bl} خبر محذوف بالبلاك ليست")

    # ══ المرحلة 4a: فلتر global_sent ══
    with _global_sent_lock:
        ar_sent = set(_global_sent_news.get(lang, set()))
    after_sent = [e for e in after_bl if e["link"] not in ar_sent]
    report.append(f"📦 المرحلة 4a: بعد global_sent ({len(ar_sent)} رابط) = {len(after_sent)}/{len(after_bl)}")
    if not after_sent:
        report.append("  ⚠️ كل الأخبار موجودة في global_sent — جرّب /clearcache")

    # ══ المرحلة 4b: فلتر user_sent (per-user history) ══
    my_info = users.get(str(uid), {})
    my_sent = my_info.get("sent_news", {})
    report.append(f"📋 المرحلة 4b: user_sent لحسابك = {len(my_sent)} رابط")
    if not my_info:
        report.append("  ❌ أنت غير مسجّل — أرسل /start واختر لغة!")
    elif not my_info.get("lang"):
        report.append("  ❌ لم تختر لغة — أرسل /start واختر لغة!")
    after_user_sent = [e for e in after_sent if e["link"] not in my_sent]
    report.append(f"  بعد user_sent = {len(after_user_sent)}/{len(after_sent)}")
    if not after_user_sent and after_sent:
        report.append("  ⚠️ كل الأخبار في user_sent الخاص بك! جرّب إعادة تشغيل البوت")

    # نُجبر على المتابعة بمرشح واحد على الأقل حتى لو في global_sent/user_sent
    test_pool = after_user_sent if after_user_sent else (after_sent[:3] if after_sent else after_bl[:3])

    # ══ المرحلة 5: فلتر اللغة ══
    after_lang = [e for e in test_pool if _title_in_lang(e["title"], lang)]
    report.append(f"🔤 المرحلة 5: بعد فلتر اللغة = {len(after_lang)}/{len(test_pool)}")
    if not after_lang and test_pool:
        sample = test_pool[0]["title"]
        report.append(f"  ⚠️ نموذج محجوب: '{sample[:40]}'")
        # احسب نسبة العربية
        import re as _re2
        ar_chars = len(_re2.findall(r'[\u0600-\u06FF]', sample))
        ratio = ar_chars / max(len([c for c in sample if not c.isspace()]), 1)
        report.append(f"  نسبة الحروف العربية: {ratio:.0%} (يحتاج ≥25%)")
    pick = after_lang if after_lang else test_pool

    # ══ المرحلة 6: اختبار AI ══
    test_entry = pick[0] if pick else None
    if test_entry:
        ai_in  = test_entry["title"]
        ai_out = None
        try:
            ai_out = _ai_clean_news(ai_in, body=test_entry.get("summary","")[:300], link=test_entry["link"])
        except Exception as ae:
            report.append(f"❌ المرحلة 6 AI: استثناء: {ae}")
        if ai_out is None:
            report.append(f"🤖 المرحلة 6 AI: أعاد None → يستخدم العنوان الأصلي (fallback)")
            ai_out = ai_in
        elif ai_out == ai_in:
            report.append(f"🤖 المرحلة 6 AI: غير متاح / يعيد نفس العنوان")
        else:
            report.append(f"🤖 المرحلة 6 AI: ✅ نظّف العنوان")

        # ══ المرحلة 7: إرسال تجريبي مباشر ══
        report.append(f"\n📨 المرحلة 7: إرسال خبر حقيقي مباشرة إليك...")
        bot.send_message(uid, "\n".join(report))

        try:
            src_name = test_entry["feed_url"].split('/')[2] if test_entry.get("feed_url") else "RSS"
            pub_dt   = test_entry.get("published_dt")
            pub_str  = _format_pub_time(pub_dt, lang=lang)
            msg_text = (
                f"🧪 *اختبار مباشر*\n\n"
                f"📰 {ai_out}\n\n"
                f"🔗 {test_entry['link']}\n"
                f"{pub_str} | {src_name}"
            )
            bot.send_message(uid, msg_text, parse_mode="Markdown", disable_web_page_preview=False)
            bot.send_message(uid,
                "✅ وصل الخبر إليك!\n\n"
                "👉 إذن: البوت يستطيع إرسال الأخبار.\n"
                "المشكلة في المقارنة مع global_sent أو عدم وجود مستخدمين فعّالين.\n"
                "الحل: /clearcache ثم /resetbroadcast"
            )
        except Exception as send_e:
            bot.send_message(uid, f"❌ فشل الإرسال التجريبي: {send_e}")
    else:
        bot.send_message(uid, "\n".join(report) + "\n❌ لا يوجد أي خبر للاختبار!")


# scheduler is shared from bot_legacy via 'from bot_legacy import *' — no duplicate instance
# FIX: الفاصل الزمني قُلِّل من 60 إلى 25 ثانية — لتقريب زمن اكتشاف/بث الخبر من
# لحظة نشره الفعلية (بدل انتظار دقيقة كاملة). الحد الأدنى 25ث بدل 60ث.
# القيمة القديمة المحفوظة "1 دقيقة" هي الافتراضي القديم نفسه — لو الأدمن ما
# غيّرها يدوياً لقيمة أخرى، نطبّق الافتراضي الجديد (25ث) مباشرة.
_interval_minutes_setting = broadcast_settings.get("interval_minutes", 1)
if _interval_minutes_setting == 1:
    _default_interval_sec = 60  # FIX: كان 25 — رُفع إلى 60 ثانية.
    # broadcast_news تستغرق ~45-60 ثانية في أسوأ حالة (AI budget كامل) + overhead.
    # بفاصل 25 ثانية كانت كل دورة تتداخل مع التالية → max instances reached.
    # 60 ثانية هي أدنى قيمة آمنة بعد إصلاح NewsAPI non-blocking.
    # الأخبار لا تزال حديثة: كاش RSS يُحدَّث كل 300 ثانية وأعمار الأخبار 60 دقيقة.
else:
    _default_interval_sec = int(_interval_minutes_setting * 60)
if _default_interval_sec < 60:
    _default_interval_sec = 60  # FIX: كان 25 — الحد الأدنى الآمن 60 ثانية
# ─── أول دورة بث بعد 120 ثانية من الإقلاع ─────────────────────────────────
# هذا يعطي _rss_prefetcher وقتاً كافياً (يحتاج ~60-90 ثانية لجلب 210 feed)
# فنضمن أن الكاش ممتلئ عند أول broadcast_news
_first_broadcast_delay = datetime.datetime.now() + datetime.timedelta(seconds=120)
_broadcast_news_job = scheduler.add_job(
    _safe_job(broadcast_news), 'interval',
    seconds=_default_interval_sec, id="broadcast_news_job",
    next_run_time=_first_broadcast_delay,
    max_instances=1, misfire_grace_time=30, coalesce=True
)
_broadcast_channels_job = scheduler.add_job(
    _safe_job(broadcast_to_channels), 'interval',
    seconds=_default_interval_sec, id="broadcast_channels_job",
    next_run_time=_first_broadcast_delay,
    max_instances=1, misfire_grace_time=30, coalesce=True
)
scheduler.add_job(_safe_job(send_morning_summary), 'interval', hours=1, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_weather_alerts), 'interval', hours=6, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_currency_alerts), 'interval', hours=3, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_keyword_alerts), 'interval', minutes=15, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(auto_clean_sent_news), 'interval', hours=1, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_sports_live_broadcaster), 'interval', seconds=30, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_prematch_notifier), 'interval', minutes=15, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_crisis_monitor_check), 'interval', minutes=10, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_live_events_broadcaster), 'interval', minutes=2, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_check_economic_alerts), 'interval', hours=2, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_get_parliament_summary), 'cron', hour=9, minute=0, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(check_pause_reminder), 'interval', hours=2, max_instances=1, coalesce=True)
scheduler.add_job(_safe_job(_send_backup_to_channel), 'interval', hours=6, id="heroku_channel_backup_job", max_instances=1, coalesce=True, next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=10))
_logger.info("✅ جدولة النسخ الاحتياطي التلقائي إلى قناة تيليغرام كل 20 دقيقة")
# FIX: دوال مُسمَّاة بدلاً من lambdas حتى تظهر بأسماء واضحة في تنبيهات الأخطاء
