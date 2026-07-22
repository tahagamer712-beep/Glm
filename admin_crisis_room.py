# -*- coding: utf-8 -*-
"""
  admin_crisis_room.py — غرفة الأزمات + مراقبة البيانات المظلمة

  يُصدِّر نظام غرفة الأزمات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _crisis_monitor_check():
    """يراقب تكرار الكلمات الحرجة ويُنذر عند الارتفاع المفاجئ"""
    try:
        now = time.time()
        window = 30 * 60  # 30 دقيقة
        for feed_url in list(RSS.get("العربية 🇮🇶", []))[:10]:
            try:
                feed = _parse_feed(feed_url)
                if not feed:
                    continue
                for entry in feed.entries[:5]:
                    title = getattr(entry, 'title', '').lower()
                    for kw in _CRISIS_KEYWORDS:
                        if kw.lower() in title:
                            _crisis_keyword_freq[kw].append(now)
            except Exception as _exc:
                _log_exc(_exc)

        # تنظيف الأحداث القديمة
        for kw in list(_crisis_keyword_freq.keys()):
            _crisis_keyword_freq[kw] = [t for t in _crisis_keyword_freq[kw] if now - t < window]

        # كشف الأزمة
        for kw, times in _crisis_keyword_freq.items():
            if len(times) >= _CRISIS_FREQ_THRESHOLD:
                last_alert = _last_crisis_alert.get(kw, 0)
                if now - last_alert > 3600:  # لا تُنبّه أكثر من مرة كل ساعة
                    _last_crisis_alert[kw] = now
                    for uid_s, info in list(users.items()):
                        try:
                            level = info.get("alert_level", "medium")
                            if level in ("high", "critical") and info.get("notifications", True):
                                u_lang = info.get("lang", "English 🇬🇧")
                                alert_text = _ul(u_lang, "crisis_alert", kw=kw, n=len(times))
                                bot.send_message(int(uid_s), alert_text, parse_mode="Markdown")
                        except Exception as _exc:
                            _log_exc(_exc)
                    # إشعار الأدمن دائماً
                    try:
                        bot.send_message(ADMIN_ID, alert_text, parse_mode="Markdown")
                    except Exception as _exc:
                        _log_exc(_exc)
    except Exception as _exc:
        _log_exc(_exc)

# ═══════════════════════════════════════════════════════════════════
# 6. بث مباشر للأحداث
# ═══════════════════════════════════════════════════════════════════
def _scrape_dark_sources() -> list:
    """يسكرب المواقع الحكومية الرسمية"""
    results = []
    if not _BS4_AVAILABLE:
        return results
    for src in DARK_SOURCES:
        try:
            items = _scrape_news_site(src["url"], src["base"], max_items=5)
            for title, link in items:
                if len(title) > 20 and not is_blacklisted(title):
                    results.append((link, title, src["name"], "", None))
        except Exception as _exc:
            _log_exc(_exc)
    return results



# ═══════════════════════════════════════════════════════════════════
# 🔍 DEEPSEARCH — بحث عميق مثل ChatGPT Deep Research
# ═══════════════════════════════════════════════════════════════════
_deepsearch_active = {}  # uid → True/False (لمنع تشغيل بحثين معاً)

def _track_crisis(title: str, source_url: str = "") -> dict:
    """يتتبع الخبر من مصادر متعددة — يُعيد تنبيهاً إذا غطّته 3+ مصادر خلال 15 دقيقة"""
    if not title or len(title) < 15:
        return None
    import re as _re_cr
    key = _re_cr.sub(r'[^\w\s]', '', title[:55].lower()).strip()[:50]
    if not key:
        return None
    now = time.time()
    if len(_crisis_tracker) > 600:
        stale = [k for k, v in list(_crisis_tracker.items()) if now - v["first_seen"] > 7200]
        for sk in stale: _crisis_tracker.pop(sk, None)
    if key not in _crisis_tracker or now - _crisis_tracker[key]["first_seen"] > _CRISIS_WINDOW:
        _crisis_tracker[key] = {"sources": set(), "first_seen": now,
                                 "notified": False, "count": 0, "title": title}
    entry = _crisis_tracker[key]
    entry["sources"].add(source_url or "unknown")
    entry["count"] = len(entry["sources"])
    if entry["count"] >= _CRISIS_THRESHOLD and not entry["notified"]:
        entry["notified"] = True
        _severity = min(5, max(1, entry["count"] - _CRISIS_THRESHOLD + 1))
        return {"title": title, "topic": title, "count": entry["count"],
                "severity": _severity, "sources": entry["sources"], "crisis_alert": True}
    return None

def _crisis_room_broadcaster():
    """
    عند تفعيل وضع الأزمة: يُرسل تحديثات كل 30 ثانية ويبني خط زمني
    ثم يُرسل تقريراً استخباراتياً AI كاملاً
    """
    global _crisis_room_active, _crisis_room_keyword, _crisis_room_timeline
    global _crisis_room_start, _crisis_report_sent_at

    if bot_paused:
        return

    # كشف الأزمة الجديدة من _crisis_keyword_freq
    with _crisis_room_lock:
        if not _crisis_room_active:
            now = time.time()
            for kw, times in list(_crisis_keyword_freq.items()):
                recent = [t for t in times if now - t < 600]  # آخر 10 دقائق
                if len(recent) >= _CRISIS_THRESHOLD + 2:       # حد أعلى من المراقبة العادية
                    _crisis_room_active  = True
                    _crisis_room_keyword = kw
                    _crisis_room_start   = now
                    _crisis_room_timeline = []
                    _crisis_report_sent_at = 0.0
                    # إشعار الأدمن
                    try:
                        bot.send_message(
                            ADMIN_ID,
                            f"🚨 *غرفة الأزمات تفعّلت!*\n"
                            f"الكلمة المفتاحية: `{kw}`\n"
                            f"عدد الإشارات: `{len(recent)}` في 10 دقائق\n"
                            f"سيبدأ البث الفوري الآن...",
                            parse_mode="Markdown"
                        )
                    except Exception as _exc:
                        _log_exc(_exc)
                    break
            if not _crisis_room_active:
                return

    # جمع تحديثات جديدة خلال وضع الأزمة
    now = time.time()
    # إيقاف تلقائي بعد 3 ساعات
    if now - _crisis_room_start > 3 * 3600:
        with _crisis_room_lock:
            _crisis_room_active = False
            _crisis_room_keyword = ""
        try:
            bot.send_message(ADMIN_ID, "✅ غرفة الأزمات: انتهى وضع الأزمة تلقائياً (3 ساعات)")
        except Exception as _exc:
            _log_exc(_exc)
        return

    kw = _crisis_room_keyword
    new_items = []
    for feed_url in list(RSS.get("العربية 🇮🇶", []))[:12]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:5]:
                title = getattr(entry, 'title', '')
                if kw.lower() in title.lower():
                    link = getattr(entry, 'link', '')
                    time_str = _now_sa().strftime("%H:%M:%S")
                    item = {"time_str": time_str, "text": title, "source": feed_url[:40]}
                    # تجنب التكرار
                    existing_texts = {x["text"] for x in _crisis_room_timeline}
                    if title not in existing_texts:
                        new_items.append(item)
        except Exception as _exc:
            _log_exc(_exc)

    if new_items:
        with _crisis_room_lock:
            _crisis_room_timeline.extend(new_items)

        # إرسال التحديثات للمستخدمين ذوي تنبيهات الأزمة
        for uid_s, uinfo in list(users.items()):
            try:
                if not uinfo.get("notifications", True):
                    continue
                if int(uid_s) in banned:
                    continue
                level = uinfo.get("alert_level", "medium")
                if level not in ("high", "critical"):
                    continue
                for it in new_items[:3]:
                    bot.send_message(
                        int(uid_s),
                        f"🚨 *[غرفة الأزمات]* `{kw}`\n"
                        f"🕐 `{it['time_str']}`\n\n"
                        f"📌 {it['text']}",
                        parse_mode="Markdown"
                    )
                    time.sleep(0.05)
            except Exception as _exc:
                _log_exc(_exc)

    # إرسال التقرير الاستخباراتي كل 30 دقيقة
    if now - _crisis_report_sent_at > 1800 and len(_crisis_room_timeline) >= 5:
        with _crisis_room_lock:
            timeline_copy = list(_crisis_room_timeline)
        report_text = _ai_crisis_intelligence_report(kw, timeline_copy)
        if report_text:
            msg = (
                f"🕵️ *تقرير استخباراتي — أزمة: {kw}*\n"
                f"📅 {_now_sa().strftime('%H:%M')} (توقيت السعودية) | "
                f"{len(timeline_copy)} حدث مرصود\n"
                f"━━━━━━━━━━━━━━\n"
                f"{report_text[:3500]}"
            )
            # إرسال للأدمن
            try:
                bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
            # إرسال للمستخدمين critical
            for uid_s, uinfo in list(users.items()):
                try:
                    if uinfo.get("alert_level") == "critical" and uinfo.get("notifications", True):
                        bot.send_message(int(uid_s), msg[:4096], parse_mode="Markdown")
                        time.sleep(0.05)
                except Exception as _exc:
                    _log_exc(_exc)
            _crisis_report_sent_at = now


# ─── 4. كاشف تناقضات السياسيين ───────────────────────────────────
def _politician_statement_tracker():
    """
    يفحص الأخبار الجديدة، يستخرج تصريحات السياسيين،
    ويبحث عن تناقضات مع تصريحاتهم السابقة
    """
    if bot_paused:
        return
    try:
        for feed_url in list(RSS.get("العربية 🇮🇶", []))[:10]:
            try:
                feed = _parse_feed(feed_url)
                if not feed:
                    continue
                for entry in feed.entries[:8]:
                    title = getattr(entry, 'title', '') or ''
                    summary = getattr(entry, 'summary', '') or ''
                    combined = f"{title} {summary}"
                    for name in POLITICIAN_NAMES_WATCH:
                        if name not in combined:
                            continue
                        # استخرج الجملة التي تحتوي على الاسم
                        sentences = combined.split('.')
                        stmt_sentence = next(
                            (s.strip() for s in sentences if name in s and len(s.strip()) > 15),
                            None
                        )
                        if not stmt_sentence:
                            continue
                        with _politician_lock:
                            history = _politician_statements.get(name, [])
                            # تجنب تكرار نفس التصريح
                            if any(stmt_sentence[:50] in h["text"] for h in history[-20:]):
                                continue
                            # إضافة للتاريخ
                            history.append({
                                "text": stmt_sentence,
                                "date": datetime.date.today().isoformat(),
                                "source": feed_url[:50]
                            })
                            _politician_statements[name] = history[-100:]  # الاحتفاظ بآخر 100

                            # فحص التناقض مع آخر تصريح مختلف
                            if len(history) >= 3:
                                old = history[-3]
                                if old["date"] != datetime.date.today().isoformat():
                                    contradiction = _ai_detect_contradiction(
                                        name, old["text"], stmt_sentence, old["date"]
                                    )
                                    if contradiction and "لا تناقض" not in contradiction and len(contradiction) > 20:
                                        alert_msg = (
                                            f"🔍 *كاشف التناقضات السياسية*\n\n"
                                            f"👤 *{name}*\n\n"
                                            f"📅 قبل ({old['date']}):\n_{old['text'][:200]}_\n\n"
                                            f"📅 اليوم:\n_{stmt_sentence[:200]}_\n\n"
                                            f"⚠️ *التحليل:*\n{contradiction[:300]}"
                                        )
                                        # إرسال للأدمن
                                        try:
                                            bot.send_message(ADMIN_ID, alert_msg, parse_mode="Markdown")
                                        except Exception as _exc:
                                            _log_exc(_exc)
                                        # إرسال للمهتمين بالأخبار السياسية
                                        for uid_s, uinfo in list(users.items()):
                                            try:
                                                if int(uid_s) in banned:
                                                    continue
                                                cats = uinfo.get("categories", [])
                                                if "سياسة" in cats or "politics" in str(cats).lower():
                                                    bot.send_message(int(uid_s), alert_msg[:4096], parse_mode="Markdown")
                                                    time.sleep(0.05)
                                            except Exception as _exc:
                                                _log_exc(_exc)
            except Exception as _exc:
                _log_exc(_exc)
    except Exception as _e:
        _logger.warning(f"[PoliticianTracker] {_e}")


# ─── 5. الخبر قبل الخبر (المراقبة الأجنبية) ─────────────────────
def _foreign_intel_monitor():
    """
    يُراقب وسائل الإعلام الأجنبية ويُرسل الأخبار التي تخص العراق
    قبل أن تغطيها وسائل الإعلام العراقية
    """
    global _foreign_intel_last_run
    if bot_paused:
        return
    now = time.time()
    if now - _foreign_intel_last_run < 1500:  # كل 25 دقيقة
        return
    _foreign_intel_last_run = now

    iraq_news = []
    for feed_url in _FOREIGN_INTEL_FEEDS:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            source_name = getattr(feed.feed, 'title', feed_url[:30])
            for entry in feed.entries[:10]:
                title = getattr(entry, 'title', '') or ''
                summary = getattr(entry, 'summary', '') or ''
                combined = f"{title} {summary}"
                # فلترة: فقط الأخبار ذات الصلة بالعراق
                if not any(w.lower() in combined.lower() for w in _IRAQ_FILTER_WORDS):
                    continue
                if title in _foreign_intel_sent:
                    continue
                _foreign_intel_sent.add(title)
                # تجنب تضخم المجموعة
                if len(_foreign_intel_sent) > 2000:
                    old = list(_foreign_intel_sent)[:500]
                    for o in old:
                        _foreign_intel_sent.discard(o)
                pub_dt = _pub_dt_from_item(entry)
                age_min = (now - pub_dt.timestamp()) / 60 if pub_dt else 999
                # أخبار الساعات الأربع الأخيرة فقط
                if age_min > 240:
                    continue
                link = getattr(entry, 'link', '')
                iraq_news.append({
                    "title": title, "link": link,
                    "source": source_name, "age_min": int(age_min)
                })
        except Exception as _exc:
            _log_exc(_exc)

    if not iraq_news:
        return

    # إرسال للمستخدمين الذين فعّلوا هذه الميزة أو للأدمن مباشرة
    for item in iraq_news[:5]:
        age_str = f"{item['age_min']}د" if item['age_min'] < 60 else f"{item['age_min']//60}س"
        link_line = f"\n🔗 {item['link']}" if item['link'] else ""
        msg = (
            f"🌐 *رصد دولي — خبر عن العراق*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📺 *{item['source']}*  ·  ⏱ منذ {age_str}\n\n"
            f"📌 {item['title']}"
            f"{link_line}"
        )
        try:
            bot.send_message(ADMIN_ID, msg, parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)
        for uid_s, uinfo in list(users.items()):
            try:
                if int(uid_s) in banned:
                    continue
                if not uinfo.get("foreign_intel", False):
                    continue
                if not uinfo.get("notifications", True):
                    continue
                bot.send_message(int(uid_s), msg[:4096], parse_mode="Markdown")
                time.sleep(0.04)
            except Exception as _exc:
                _log_exc(_exc)


# ─── 6. الذكاء الجماعي — معالجة البلاغات الواردة ────────────────
def _process_crowd_tips():
    """
    يُراجع البلاغات الواردة من المستخدمين ويُوجّهها للأدمن للموافقة
    """
    if bot_paused:
        return
    with _crowd_tips_lock:
        pending = [t for t in _crowd_tips if t.get("status") == "pending"]

    for tip in pending[:5]:  # حد 5 بلاغات كل دورة
        try:
            uid  = tip.get("uid")
            text = tip.get("text", "")
            ts   = tip.get("time", 0)
            age  = int((time.time() - ts) / 60)
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ نشر", callback_data=f"tip_approve_{uid}_{ts}"),
                types.InlineKeyboardButton("❌ رفض", callback_data=f"tip_reject_{uid}_{ts}")
            )
            bot.send_message(
                ADMIN_ID,
                f"📢 *بلاغ من مستخدم* (منذ {age}د)\n"
                f"المستخدم: `{uid}`\n\n"
                f"_{text[:500]}_",
                parse_mode="Markdown",
                reply_markup=markup
            )
            with _crowd_tips_lock:
                for t in _crowd_tips:
                    if t.get("uid") == uid and t.get("time") == ts:
                        t["status"] = "reviewing"
                        break
        except Exception as _exc:
            _log_exc(_exc)


# ═══════════════════════════════════════════════════════════════════
# أوامر الجيل المتقدم (بحث، تحقق، روابط، تاريخ، بلاغ)
# ═══════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["tip"])
def handle_tip_cmd(message):
    """الذكاء الجماعي — المستخدم يُرسل خبراً شاهده"""
    uid  = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    text = message.text.replace('/tip', '').strip()
    if not text or len(text) < 10:
        bot.send_message(message.chat.id, _ui("cmd_tip_usage", lang), parse_mode="Markdown")
        return
    tip = {
        "uid": uid,
        "text": text,
        "time": time.time(),
        "status": "pending",
        "username": message.from_user.username or f"user_{uid}",
    }
    with _crowd_tips_lock:
        _crowd_tips.append(tip)
        if len(_crowd_tips) > _CROWD_TIP_MAX:
            _crowd_tips.pop(0)
    bot.send_message(message.chat.id, _ui("cmd_tip_success", lang), parse_mode="Markdown")
    # إشعار فوري للأدمن
    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ نشر الآن", callback_data=f"tip_approve_{uid}_{int(tip['time'])}"),
            types.InlineKeyboardButton("❌ رفض", callback_data=f"tip_reject_{uid}_{int(tip['time'])}")
        )
        bot.send_message(ADMIN_ID,
            f"📢 *بلاغ جديد من مستخدم*\n"
            f"👤 `{uid}` (@{tip['username']})\n\n"
            f"_{text[:500]}_",
            parse_mode="Markdown", reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)


@bot.message_handler(commands=['intel'])
def handle_intel_cmd(message):
    """تفعيل/إيقاف ميزة 'الخبر قبل الخبر' للمستخدم"""
    uid = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    current = users.get(uid, {}).get("foreign_intel", False)
    users.setdefault(uid, {})["foreign_intel"] = not current
    _save_users_soon()
    bot.send_message(message.chat.id,
        _ui("cmd_intel_on" if not current else "cmd_intel_off", lang),
        parse_mode="Markdown")


# ─── Callbacks: الموافقة/رفض بلاغات الذكاء الجماعي ───────────────
@bot.callback_query_handler(func=lambda c: c.data.startswith("tip_approve_") or c.data.startswith("tip_reject_"))
def cb_tip_admin(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ غير مصرح")
        return
    parts = call.data.split("_")
    action = parts[1]   # approve / reject
    tip_uid = parts[2]
    tip_ts  = float(parts[3]) if len(parts) > 3 else 0

    with _crowd_tips_lock:
        tip = next((t for t in _crowd_tips if t.get("uid") == tip_uid and abs(t.get("time", 0) - tip_ts) < 2), None)

    if not tip:
        bot.answer_callback_query(call.id, "❌ البلاغ غير موجود أو انتهى")
        return

    if action == "approve":
        tip["status"] = "approved"
        news_text = (
            f"📢 *خبر من المستخدمين (ذكاء جماعي)*\n\n"
            f"_{tip['text'][:600]}_"
        )
        # بث للجميع
        count = 0
        for uid_s, uinfo in list(users.items()):
            try:
                if int(uid_s) in banned:
                    continue
                if not uinfo.get("notifications", True):
                    continue
                bot.send_message(int(uid_s), news_text, parse_mode="Markdown")
                count += 1
                time.sleep(0.03)
            except Exception as _exc:
                _log_exc(_exc)
        bot.answer_callback_query(call.id, f"✅ نُشر لـ {count} مستخدم")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception as _exc:
            _log_exc(_exc)
        # إشعار صاحب البلاغ
        try:
            bot.send_message(int(tip_uid), "🎉 *تم نشر تقريرك!* شكراً على مساهمتك.", parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)
    else:
        tip["status"] = "rejected"
        bot.answer_callback_query(call.id, "❌ رُفض البلاغ")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception as _exc:
            _log_exc(_exc)


# ─── Callback: Fact Check من رسالة الخبر ──────────────────────────
