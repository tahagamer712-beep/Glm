# -*- coding: utf-8 -*-
"""
  admin_stats_view.py — عرض الإحصائيات التفصيلية

  يُصدِّر دوال عرض الإحصائيات من لوحة الأدمن.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def send_public_stats(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    total = stats.get("total_users", len(users))
    today = str(datetime.date.today())
    today_count = stats.get("daily_users", {}).get(today, 0)
    active = sum(1 for u in users.values() if "province" in u)
    premium_count = len(stats.get("premium_users", []))
    top_langs = sorted(stats.get("languages_count", {}).items(), key=lambda x: x[1], reverse=True)[:5]
    msg = t(lang, "public_stats_header").format(
        total=total, active=active, today=today_count, premium=premium_count
    )
    if top_langs:
        msg += t(lang, "public_stats_langs")
        for lang_name, count in top_langs:
            msg += f"  • {lang_name}: {count}\n"
    msg += t(lang, "public_stats_footer").format(username=BOT_USERNAME)
    bot.send_message(uid, msg, parse_mode="Markdown")

# ======== دولار السوق الموازية ========
def _send_admin_health_report():
    """يُرسل للأدمن تقريراً شاملاً في الساعة 8 صباحاً يشمل مقاييس النظام."""
    if bot_paused:
        return
    now_h = _now_sa().hour
    if now_h != 8:
        return
    try:
        total_users = len(users)
        active_24h  = sum(
            1 for u in users.values()
            if time.time() - u.get("last_active", 0) < 86400
        )
        with _daily_new_users_lock:
            new_today = len(_daily_new_users)
            _daily_new_users.clear()

        with _broadcast_stats_lock:
            news_sent   = _broadcast_stats.get("today_news_sent", 0)
            users_reach = _broadcast_stats.get("today_users_reached", 0)
            hourly      = _broadcast_stats.get("hourly_activity", {})
            errors      = list(_broadcast_errors[-5:])

        # ساعة الذروة
        peak_h, peak_v = max(hourly.items(), key=lambda x: x[1]) if hourly else ("—", 0)

        # أكثر لغة
        lang_count: dict = {}
        for u in users.values():
            l = u.get("lang", "Unknown")
            lang_count[l] = lang_count.get(l, 0) + 1
        top_lang = max(lang_count, key=lang_count.get) if lang_count else "—"

        # أرشيف
        with _news_archive_lock:
            arc_count = len(_news_archive)

        # غرفة الأزمات
        crisis_status = "🔴 نشطة" if _crisis_room_active else "🟢 هادئة"

        # ── مقاييس النظام (SELF-HEALING ENGINE) ──
        sys_m  = _get_sys_metrics()
        ram    = sys_m.get("ram_pct", _sys_health.get("ram_pct", 0))
        cpu    = sys_m.get("cpu_pct", _sys_health.get("cpu_pct", 0))
        disk   = sys_m.get("disk_pct", _sys_health.get("disk_pct", 0))
        uptime_s  = int(time.time() - _sys_health["start_ts"])
        uptime_h  = uptime_s // 3600
        uptime_m  = (uptime_s % 3600) // 60
        recoveries = _sys_health.get("recoveries", 0)

        # ── أكثر الوظائف خطأً ──
        with _error_freq_lock:
            top_errs = sorted(_error_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        top_err_str = "\n".join(f"  `{fn}`: {cnt}x" for fn, cnt in top_errs) or "  لا أخطاء 🎉"

        # ── القنوات ──
        total_chs = len(channels_groups)

        ram_icon  = "🔴" if ram > 85 else ("🟡" if ram > 65 else "🟢")
        cpu_icon  = "🔴" if cpu > 85 else ("🟡" if cpu > 65 else "🟢")
        disk_icon = "🔴" if disk > 85 else ("🟡" if disk > 65 else "🟢")

        report = (
            f"📊 *تقرير البوت اليومي — {datetime.date.today()}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👥 *المستخدمون*\n"
            f"  إجمالي: `{total_users:,}` | قنوات/مجموعات: `{total_chs}`\n"
            f"  نشط (24h): `{active_24h:,}` | جديد اليوم: `{new_today:,}`\n\n"
            f"📰 *الأخبار*\n"
            f"  بُثّت: `{news_sent:,}` خبر | وصلت لـ `{users_reach:,}` مستخدم\n"
            f"  في الأرشيف: `{arc_count:,}` | أكثر لغة: `{top_lang}`\n"
            f"  ساعة الذروة: `{peak_h}:00` — `{peak_v:,}` إرسال\n\n"
            f"🖥 *صحة النظام*\n"
            f"  {ram_icon} RAM: `{ram:.1f}%` | {cpu_icon} CPU: `{cpu:.1f}%` | {disk_icon} Disk: `{disk:.1f}%`\n"
            f"  ⏱ Uptime: `{uptime_h}h {uptime_m}m` | 🔄 تعافيات تلقائية: `{recoveries}`\n\n"
            f"🛡 *الاستقرار*\n"
            f"  غرفة الأزمات: {crisis_status}\n"
            f"  أخطاء البث: `{len(errors)}`\n"
            f"  أكثر الوظائف خطأً:\n{top_err_str}\n"
        )
        if errors:
            report += "\n*آخر أخطاء البث:*\n" + "\n".join(f"`{e[-100:]}`" for e in errors)

        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
    except Exception as _e:
        _logger.error("[HealthReport] %s", _e)


# ─── 3. غرفة الأزمات المتقدمة ────────────────────────────────────
@bot.message_handler(commands=["sysinfo"])
def cmd_sysinfo(m):
    """تقرير صحي فوري للنظام — للأدمن فقط"""
    uid = m.from_user.id
    if not is_admin(uid):
        return
    try:
        # مقاييس النظام
        sys_m = _get_sys_metrics()
        ram   = sys_m.get("ram_pct", 0)
        cpu   = sys_m.get("cpu_pct", 0)
        disk  = sys_m.get("disk_pct", 0)
        uptime_s = int(time.time() - _sys_health["start_ts"])
        uptime_h = uptime_s // 3600
        uptime_m = (uptime_s % 3600) // 60
        recoveries = _sys_health.get("recoveries", 0)

        # حجم الكاشات
        with _AI_CACHE_LOCK:
            ai_sz = len(_AI_CACHE)
        with _AI_SUMMARY_LOCK:
            sum_sz = len(_AI_SUMMARY_CACHE)
        ns_sz = len(_news_summary_cache)
        with _news_archive_lock:
            arc_sz = len(_news_archive)

        # أكثر الوظائف خطأً
        with _error_freq_lock:
            top_errs = sorted(_error_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        top_err_str = "\n".join(f"  `{fn}`: {cnt}x" for fn, cnt in top_errs) or "  لا أخطاء 🎉"

        # رسائل في الكيو
        q_size = _send_queue.qsize() if hasattr(_send_queue, "qsize") else "؟"

        ram_icon  = "🔴" if ram  > 85 else ("🟡" if ram  > 65 else "🟢")
        cpu_icon  = "🔴" if cpu  > 85 else ("🟡" if cpu  > 65 else "🟢")
        disk_icon = "🔴" if disk > 85 else ("🟡" if disk > 65 else "🟢")

        msg = (
            f"🏥 *تقرير صحة النظام — فوري*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🖥 *الموارد*\n"
            f"  {ram_icon} RAM: `{ram:.1f}%`\n"
            f"  {cpu_icon} CPU: `{cpu:.1f}%`\n"
            f"  {disk_icon} Disk: `{disk:.1f}%`\n"
            f"  ⏱ Uptime: `{uptime_h}h {uptime_m}m`\n"
            f"  🔄 تعافيات تلقائية: `{recoveries}`\n\n"
            f"📦 *الكاشات*\n"
            f"  AI: `{ai_sz}` | ملخصات: `{sum_sz}` | خبر: `{ns_sz}` | أرشيف: `{arc_sz}`\n"
            f"  رسائل في الطابور: `{q_size}`\n\n"
            f"📬 *إحصاءات التسليم*\n"
            f"  ✅ نجح: `{_delivery_stats.get('sent_ok', 0):,}`\n"
            f"  ❌ فشل: `{_delivery_stats.get('sent_fail', 0):,}`\n"
            f"  🔁 أُعيد إرساله: `{_delivery_stats.get('retried', 0):,}`\n"
            f"  ⏳ Rate Limited: `{_delivery_stats.get('rate_limited', 0):,}`\n"
            f"  🔧 حُل تلقائياً: `{_delivery_stats.get('auto_resolved', 0):,}`\n"
            f"  🔔 أُبلغ الأدمن: `{_delivery_stats.get('admin_alerted', 0):,}`\n"
            f"  🚫 Chats ميتة: `{len(_dead_chats)}`\n"
            f"  ⚡ تأخير الإرسال: `{_dynamic_delay*1000:.0f}ms`\n\n"
            f"⚠️ *أكثر الوظائف خطأً*\n{top_err_str}\n"
        )
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as _e:
        bot.send_message(uid, f"خطأ في /sysinfo: {_e}")


@bot.message_handler(commands=["analytics"])
def cmd_analytics(m):
    """
    لوحة تحليلات InsightX:
    - إجمالي استخدام كل ميزة AI
    - عدد المستخدمين النشطين اليوم
    - أكثر اهتمامات المستخدمين شيوعاً
    - حالة Feature Gating
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    sep = "━━━━━━━━━━━━━━"
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # إجمالي استخدام الميزات
    with _stats_lock:
        stats_copy = dict(_feature_usage_stats)

    sorted_stats = sorted(stats_copy.items(), key=lambda x: x[1], reverse=True)
    feature_lines = "\n".join(
        f"  • {feat}: *{count}* مرة"
        for feat, count in sorted_stats[:12]
    ) or "  — لا يوجد بيانات بعد"

    # المستخدمون النشطون اليوم (لديهم استخدام يومي)
    active_today = sum(
        1 for d in _user_daily_usage.values()
        if today in d and sum(d[today].values()) > 0
    )

    # حجم سجل النقرات
    with _click_log_lock:
        users_tracked = len(_user_click_log)

    # كاشات AI
    cache_sizes = {
        "Why Matters":  len(_WHY_MATTERS_CACHE),
        "What Next":    len(_WHAT_NEXT_CACHE),
        "Impact/Bias":  len(_IMPACT_CACHE),
        "Sentiment":    len(_SENTIMENT_AI_CACHE),
        "Entities":     len(_ENTITY_CACHE),
        "Risk Level":   len(_RISK_CACHE),
        "Context":      len(_CONTEXT_CACHE),
    }
    cache_lines = "  " + " | ".join(f"{k}:{v}" for k, v in cache_sizes.items())

    gating_status = "🔴 مُفعّل (الحدود مُطبّقة)" if _FEATURE_GATING_ACTIVE else "🟢 مُعطّل (كل شيء مجاني)"

    report = (
        f"📊 *InsightX Analytics Dashboard*\n{sep}\n\n"
        f"🗓 التاريخ: `{today}`\n"
        f"👥 مجموع المستخدمين: *{len(users)}*\n"
        f"⚡ نشطون اليوم: *{active_today}*\n"
        f"🖱️ مستخدمون متتبَّعون: *{users_tracked}*\n\n"
        f"🔐 Feature Gating: {gating_status}\n\n"
        f"{sep}\n"
        f"📈 *استخدام الميزات (إجمالي):*\n{feature_lines}\n\n"
        f"{sep}\n"
        f"🧠 *حجم كاشات AI:*\n{cache_lines}\n"
        f"{sep}\n\n"
        f"_لتفعيل/تعطيل حدود الاستخدام: /featuregate_"
    )
    bot.send_message(uid, report, parse_mode="Markdown")


# ======== /featuregate — تحكم بنظام حدود الاستخدام (أدمن فقط) ========
@bot.message_handler(commands=["health"])
def cmd_health(m):
    """
    تقرير صحة البوت الشامل:
    - حالة نظام البث
    - Uptime
    - Semantic Dedup stats
    - Cache sizes
    - Rate limiter stats
    - آخر broadcast
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    sep = "━━━━━━━━━━━━━━"
    now = time.time()
    uptime_secs = int(now - _bot_start_ts)
    h, rem = divmod(uptime_secs, 3600)
    m2, s  = divmod(rem, 60)
    uptime_str = f"{h}h {m2}m {s}s"

    bh = _check_broadcast_health()
    status_emoji = {"healthy": "🟢", "dry": "🟡", "stopped": "🔴", "unknown": "⚪"}
    bcast_status = status_emoji.get(bh["status"], "⚪") + f" {bh['status'].upper()}"
    last_run     = f"{bh['last_run_ago']}s ago" if bh["last_run_ago"] is not None else "never"

    # semantic dedup stats
    sem_total = sum(len(v) for v in _recent_sent_titles.values())
    # rate limiter: active users being tracked
    with _cooldown_lock:
        rl_users = len(_user_ai_cooldown)
    # users with active sent_news
    users_active = sum(1 for u in users.values() if u.get("notifications", True))

    # AI caches total
    ai_caches_total = (len(_WHY_MATTERS_CACHE) + len(_WHAT_NEXT_CACHE) + len(_IMPACT_CACHE) +
                       len(_SENTIMENT_AI_CACHE) + len(_ENTITY_CACHE) + len(_RISK_CACHE) +
                       len(_CONTEXT_CACHE) + len(_news_summary_cache))

    report = (
        f"🏥 *Bot Health Report*\n{sep}\n"
        f"⏱ Uptime: `{uptime_str}`\n"
        f"👥 Total users: `{len(users)}`\n"
        f"🔔 Notifications ON: `{users_active}`\n\n"
        f"{sep}\n"
        f"📡 *Broadcast System:*\n"
        f"  Status: {bcast_status}\n"
        f"  Last run: `{last_run}`\n"
        f"  Avg/cycle: `{bh['avg_per_cycle']}`\n"
        f"  Total cycles: `{bh['total_cycles']}`\n\n"
        f"{sep}\n"
        f"🔄 *Deduplication:*\n"
        f"  Semantic titles tracked: `{sem_total}`\n\n"
        f"🛡️ *Rate Limiter:*\n"
        f"  Users in cooldown map: `{rl_users}`\n\n"
        f"🧠 *AI Caches total:* `{ai_caches_total}`\n"
        f"{sep}\n"
        f"_أوامر أخرى: /analytics /featuregate /debugnews_"
    )
    bot.send_message(uid, report, parse_mode="Markdown")


# ======== /featurepanel — لوحة التحكم الكاملة بالميزات (أدمن) ========
def cmd_dashboard(m):
    uid = m.from_user.id
    if not is_admin(uid): return

    text, markup = _make_dashboard(uid)
    msg = bot.send_message(uid, text, parse_mode="Markdown", reply_markup=markup)
    _dashboard_msg_ids[uid] = msg.message_id


@bot.callback_query_handler(func=lambda c: c.data == "dash_refresh")
def cb_dashboard_refresh(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔")
        return
    bot.answer_callback_query(call.id, "🔄 تحديث...")
    text, markup = _make_dashboard(uid)
    try:
        bot.edit_message_text(text, uid, call.message.message_id,
                              parse_mode="Markdown", reply_markup=markup)
    except Exception as _exc:
        _log_exc(_exc)


def _make_dashboard(uid) -> tuple:
    sep = "━━━━━━━━━━━━━━"
    now = time.time()
    uptime_s = int(now - _bot_start_ts)
    h, rem = divmod(uptime_s, 3600); m2, s = divmod(rem, 60)
    bh = _check_broadcast_health()
    st = {"healthy":"🟢","dry":"🟡","stopped":"🔴","unknown":"⚪"}
    prem_count = len(stats.get("premium_users", []))
    active_now = sum(1 for u in users.values()
                     if time.time() - _ts(u.get("last_active", 0)) < 86400)
    rss_ok  = sum(1 for v in _rss_health.values() if v["status"] == "ok")
    rss_tot = len(_rss_health)
    cb_status = "🔴 مفتوح" if time.time() < _cb_open_until else "🟢 مغلق"
    gating = "✅" if _FEATURE_GATING_ACTIVE else "⏸"

    text = (
        f"📊 *لوحة القيادة الحية*\n{sep}\n"
        f"⏱ Uptime: `{h}h {m2}m`\n"
        f"👥 إجمالي: `{len(users)}` | نشط 24h: `{active_now}`\n"
        f"⭐ مميزون: `{prem_count}`\n"
        f"{sep}\n"
        f"📡 البث: {st.get(bh['status'],'⚪')} `{bh['status']}` | آخر: `{bh['last_run_ago']}s`\n"
        f"📰 RSS: `{rss_ok}/{rss_tot}` مصدر سليم\n"
        f"🧠 AI Circuit: {cb_status}\n"
        f"⚙️ Feature Gating: {gating}\n"
        f"{sep}\n"
        f"🔖 Bookmarks: `{sum(len(v) for v in _bookmarks.values())}`\n"
        f"📡 Entity Tracks: `{sum(len(v) for v in _entity_tracks.values())}`\n"
        f"🗓 Scheduled: `{len(_scheduled_bcasts)}`\n"
        f"📣 Sponsored Queue: `{len(_sponsored_queue)}`\n"
        f"{sep}\n"
        f"_آخر تحديث: {datetime.datetime.now().strftime('%H:%M:%S')}_"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 تحديث الآن", callback_data="dash_refresh"))
    return text, markup


def cmd_segment(m):
    uid = m.from_user.id
    if not is_admin(uid): return
    _build_segment_cache()
    sep = "━━━━━━━━━━━━━━"
    sc  = _segment_cache
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🟢 نشط 24h ({len(sc['active'])})", callback_data="seg_msg_active"),
        types.InlineKeyboardButton(f"🟡 خامل 7d ({len(sc['inactive_7'])})", callback_data="seg_msg_inactive_7"),
        types.InlineKeyboardButton(f"🔴 خامل 30d ({len(sc['inactive_30'])})", callback_data="seg_msg_inactive_30"),
    )
    bot.send_message(uid,
        f"👥 *تصنيف المستخدمين*\n{sep}\n\n"
        f"🟢 نشط خلال 24h: *{len(sc['active'])}*\n"
        f"🟡 خامل 7 أيام: *{len(sc['inactive_7'])}*\n"
        f"🔴 خامل 30 يوم: *{len(sc['inactive_30'])}*\n\n"
        f"_اضغط على شريحة لإرسال رسالة مخصصة_",
        parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("seg_msg_"))
def cb_seg_msg(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔"); return
    bot.answer_callback_query(call.id)
    seg = call.data[len("seg_msg_"):]
    bot.send_message(uid,
        f"✍️ أرسل الرسالة التي تريد إرسالها لشريحة *{seg}*:\n_يمكنك استخدام Markdown_",
        parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(uid, lambda msg: _do_seg_send(msg, seg))


def _do_seg_send(m, seg):
    uid = m.from_user.id
    if not is_admin(uid): return
    _build_segment_cache()
    targets = _segment_cache.get(seg, [])
    if not targets:
        bot.send_message(uid, "⚠️ لا يوجد مستخدمون في هذه الشريحة.")
        return
    sent = fail = 0
    for t_uid in targets:
        try:
            bot.send_message(t_uid, m.text, parse_mode="Markdown")
            sent += 1
            time.sleep(0.05)
        except Exception:
            fail += 1
    bot.send_message(uid,
        f"✅ *إرسال الشريحة مكتمل*\n✉️ نجح: {sent} | ❌ فشل: {fail}",
        parse_mode="Markdown")


# ── /feedstats — أداء مصادر RSS ──────────────────────────────────────────
@bot.message_handler(commands=["feedstats"])
def cmd_feedstats(m):
    uid = m.from_user.id
    if not is_admin(uid): return
    sep = "━━━━━━━━━━━━━━"
    with _RSS_HEALTH_LOCK:
        health_copy = dict(_rss_health)

    ok   = [(u,v) for u,v in health_copy.items() if v["status"]=="ok"]
    slow = [(u,v) for u,v in health_copy.items() if v["status"]=="slow"]
    dead = [(u,v) for u,v in health_copy.items() if v["status"]=="dead"]

    lines = [f"📊 *أداء مصادر RSS*\n{sep}",
             f"🟢 سليم: {len(ok)} | 🟡 بطيء: {len(slow)} | 🔴 ميت: {len(dead)}\n{sep}"]

    if dead:
        lines.append("*🔴 مصادر متوقفة:*")
        for u, v in dead[:5]:
            name = get_source_name_from_url(u) if 'get_source_name_from_url' in dir() else u[:40]
            lines.append(f"  • {name}")

    if slow:
        lines.append("\n*🟡 مصادر بطيئة:*")
        for u, v in slow[:5]:
            name = get_source_name_from_url(u) if 'get_source_name_from_url' in dir() else u[:40]
            lines.append(f"  • {name} ({v['latency']}ms)")

    if ok:
        avg_lat = sum(v["latency"] for _, v in ok) / len(ok)
        lines.append(f"\n✅ متوسط سرعة المصادر السليمة: *{avg_lat:.0f}ms*")

    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")


# ── /schedule — جدولة البث ────────────────────────────────────────────────
