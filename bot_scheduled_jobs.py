# -*- coding: utf-8 -*-
# bot_scheduled_jobs.py — المهام الدورية المجدولة

def auto_backup():
    try:
        import db_backup as _dbb
        if hasattr(_dbb, "auto_backup"):
            _dbb.auto_backup()
    except Exception as _e:
        _log_exc(_e, "auto_backup_stub")


KEYWORDS_FILE           = "user_keywords.json"
TRACK_FILE              = "tracked_assets.json"
_SCHEDULED_FILE         = "scheduled_bcasts.json"
_SPONSORED_FILE         = "sponsored.json"
_CAPSULE_FILE           = "capsule.json"
_RADAR_MAX_KW           = 30
_RADAR_MAX_SENT         = 100
_CRISIS_THRESHOLD       = 3
_CRISIS_WINDOW          = 600

# ── Thread locks — مستوردة من state.py (المصدر الوحيد) ──────────────────────
# state.py يُنشئها، bot_legacy يستوردها فقط — لا dual-init
_users_rlock             = gl._users_rlock
_stats_lock              = gl._stats_lock
_db_lock                 = gl._db_lock
_retry_lock              = gl._retry_lock
_title_seen_lock         = gl._title_seen_lock
_rss_etag_lock           = gl._rss_etag_lock

# ── Retry / send queue ────────────────────────────────────────────────────────
_retry_heap              = gl._retry_heap
_send_queue              = gl._send_queue

# ── Weather cache ─────────────────────────────────────────────────────────────
_weather_cache           = gl._weather_cache
_WEATHER_CACHE_TTL       = gl._WEATHER_CACHE_TTL

# ── Broadcast control ─────────────────────────────────────────────────────────
_broadcast_news_lock     = gl._broadcast_news_lock
_broadcast_channels_lock = gl._broadcast_channels_lock
_broadcast_lock_ts       = gl._broadcast_lock_ts
_BROADCAST_MAX_SECS      = 300
_BROADCAST_HARD_TIMEOUT  = 600
_USER_SENT_TTL           = 86400
_bot_start_time          = time.time()
_broadcast_impl_thread   = gl._broadcast_impl_thread
_broadcast_stats         = gl._broadcast_stats

# ── Global sent news dedup ────────────────────────────────────────────────────
_global_sent_news        = gl._global_sent_news
_title_seen_cache        = gl._title_seen_cache
_TITLE_DEDUP_TTL         = 86400
_rss_etag_store          = gl._rss_etag_store

# ── RSS global cache ──────────────────────────────────────────────────────────
_global_rss_cache        = gl._GLOBAL_RSS_CACHE   # alias — نفس الكائن
_global_rss_cache_lock   = gl._global_rss_cache_lock
_GLOBAL_RSS_CACHE_TTL    = 300  # FIX: رُفع من 120 إلى 300 ثانية ليتوافق مع فاصل prefetcher الجديد (300ث)

# ── Users and core data ───────────────────────────────────────────────────────
users: dict         = load_json(USERS_FILE, {})
read_stats: dict    = load_json(READ_STATS_FILE, {})
channels_groups     = load_json(CHANNELS_FILE, [])
rss_sources         = load_json(RSS_SOURCES_FILE, [])
crisis_tips         = load_json(CRISIS_FILE, [])
user_keywords: dict = load_json(KEYWORDS_FILE, {})
user_states:  dict  = {}
_scheduled_bcasts   = load_json(_SCHEDULED_FILE, [])
_sponsored_queue    = load_json(_SPONSORED_FILE, [])
_group_votes: dict  = {}
MAX_NEWS_PER_USER_CYCLE = 30

# ── Global sent news persistence ──────────────────────────────────────────────
_GLOBAL_SENT_FILE = "global_sent_news.json"


def broadcast_weather():
    # تم إزالة البث التلقائي للطقس — الطقس يُرسل فقط عند طلب المستخدم
    # هذه الدالة محجوزة للاستخدام اليدوي إذا أراد الأدمن ذلك
    pass

MAX_NEWS_PER_BROADCAST  = 8   # قنوات/مجموعات: 8 أخبار كحد أقصى لكل دورة بث
MAX_NEWS_PER_USER_CYCLE = 15  # مستخدمون: 15 خبر كحد أقصى لكل مستخدم لكل دورة

# ════════════════════════════════════════════════════════════════════════
# HARD TIMEOUT WRAPPER — يمنع تعليق دورات البث للأبد
# الـ impl يشتغل بخيط منفصل، والـ wrapper يقطعه بعد _BROADCAST_HARD_TIMEOUT.
# هذا يضمن أن أي تعليق بـ HTTP/AI/scrape لن يحجز كل دورات البث القادمة.
# ════════════════════════════════════════════════════════════════════════
_BROADCAST_HARD_TIMEOUT = 80   # ثانية — أقل من interval الدورة (60ث × 2)
_broadcast_impl_thread  = [None]  # holder لخيط الـ impl الجاري


def check_keyword_alerts():
    if bot_paused: return
    for uid, keywords in list(user_keywords.items()):
        if not keywords:
            continue
        if int(uid) in banned:
            continue
        user = users.get(uid)
        if not user:
            continue
        lang = user.get("lang", "English 🇬🇧")
        feeds = RSS.get(lang, [])
        sent = user.setdefault("sent_news", {})
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
                    title = getattr(item, 'title', '')
                    title_lower = title.lower()
                    matched_kw = None
                    for kw in keywords:
                        if kw.lower() in title_lower:
                            matched_kw = kw
                            break
                    if matched_kw:
                        sent[item.link] = time.time()
                        queue_send(
                            uid,
                            _ul(lang, "keyword_alert", kw=escape_md(matched_kw), title=escape_md(title)) + BOT_SIGNATURE,
                            parse_mode="Markdown"
                        )
            except Exception as e:
                notify_admin_error(f"خطأ في فحص الكلمات المفتاحية: {e}")
    _db_save_all_users(users)

# ======== الجدولة ========


def check_pause_reminder():
    global bot_paused, _pause_since
    if not bot_paused or _pause_since is None:
        return
    hours_paused = (datetime.datetime.now() - _pause_since).total_seconds() / 3600
    if hours_paused >= 6:
        try:
            bot.send_message(
                ADMIN_ID,
                f"⚠️ *تنبيه:* البوت متوقف منذ {int(hours_paused)} ساعة!\n"
                f"🕐 وقت الإيقاف: {_pause_since.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"افتح /admin واضغط *إيقاف/تشغيل البوت* لإعادة تشغيله.",
                parse_mode="Markdown"
            )
        except Exception as _exc:
            _log_exc(_exc)


  # ═══════════════════════════════════════════════════════════════════════
# HEROKU: النسخ الاحتياطي التلقائي إلى قناة تيليغرام
# ═══════════════════════════════════════════════════════════════════════

def send_weekly_summary():
    if bot_paused: return
    """ترسل ملخص أبرز أخبار الأسبوع لكل المستخدمين كل جمعة"""
    if not _weekly_top_news:
        return
    _logger.info("📆 إرسال الملخص الأسبوعي...")
    week_end = datetime.date.today().strftime("%Y/%m/%d")
    week_start = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y/%m/%d")
    for uid_str, info in list(users.items()):
        try:
            if not info.get("notifications", True):
                continue
            uid = int(uid_str)
            lang = info.get("lang", "العربية 🇮🇶")
            top = sorted(
                _weekly_top_news.get(lang, {}).values(),
                key=lambda x: x["count"], reverse=True
            )[:7]
            if not top:
                continue
            lines = []
            for i, item in enumerate(top, 1):
                lines.append(f"{i}. [{item['title']}]({item['link']})")
            msg = (
                f"📆 *الملخص الأسبوعي*\n"
                f"🗓 {week_start} — {week_end}\n"
                f"━━━━━━━━━━━━━━\n\n"
                + "\n\n".join(lines) +
                "\n\n━━━━━━━━━━━━━━\n"
                "_أبرز الأخبار التي غطّتها مصادر متعددة هذا الأسبوع_"
            )
            try:
                bot.send_message(uid, msg, parse_mode="Markdown",
                                 disable_web_page_preview=True)
            except Exception as _exc:
                _log_exc(_exc)
        except Exception:
            continue
    # إعادة تعيين قائمة الأسبوع
    _weekly_top_news.clear()
    _logger.info("✅ انتهى الملخص الأسبوعي")


# ======================================================
# ميزة: وضع المجموعات مع التصويت على الأخبار
# ======================================================
_group_votes = {}  # message_id → {"title": .., "yes": set(), "no": set(), "link": ..}


def send_evening_recap():
    if bot_paused: return
    """ترسل ملخصاً لأبرز أخبار اليوم العاجلة إلى كل المستخدمين المشتركين"""
    today = str(datetime.date.today())
    sent_links = set()
    breaking_items = []

    # اجمع الأخبار العاجلة من كل اللغات
    for lang in set(info.get("lang", "") for info in users.values() if info.get("lang")):
        feeds = RSS.get(lang, [])
        for feed_url in feeds[:5]:
            try:
                feed = _parse_feed(feed_url, timeout=10)
                if not feed:
                    continue
                for item in feed.entries[:15]:
                    title = getattr(item, 'title', '')
                    link  = getattr(item, 'link', '')
                    if not title or not link or link in sent_links:
                        continue
                    if _news_importance_score(title) >= 2:
                        sent_links.add(link)
                        breaking_items.append((lang, title, link))
                if len(breaking_items) >= 20:
                    break
            except Exception as _exc:
                _log_exc(_exc)

    if not breaking_items:
        return

    # أرسل لكل مستخدم بلغته
    for uid, info in list(users.items()):
        try:
            if int(uid) in banned:
                continue
            if not info.get("notifications", True):
                continue
            # لا ترسل للوضع الصامت (إلا إذا عطّل)
            if info.get("quiet_mode_enabled", True) and _is_quiet_hours(uid):
                continue
            # تحقق أنها لم تُرسل اليوم
            if _evening_recap_sent.get(str(uid)) == today:
                continue
            lang = info.get("lang", "")
            if not lang:
                continue
            user_items = [(t, l) for (lg, t, l) in breaking_items if lg == lang]
            if not user_items:
                continue
            lines = []
            for title, link in user_items[:8]:
                s_e = _sentiment_emoji(title)
                lines.append(f"🚨 [{s_e + ' ' if s_e else ''}{title}]({link})")
            if not lines:
                continue
            msg = _ul(lang, "evening_title") + "\n".join(lines)
            queue_send(uid, msg, parse_mode="Markdown", disable_web_page_preview=True)
            _evening_recap_sent[str(uid)] = today
        except Exception:
            continue




def send_daily_report():
    if bot_paused: return
    today = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    total_users_count = len(users)
    new_today = sum(1 for u in users.values() if u.get("join_date", "").startswith(today))
    premium_count = len(stats.get("premium_users", []))
    channels_count = len(channels_groups)
    total_ch_news = sum(ch.get("news_sent_count", 0) for ch in channels_groups)
    read_today = read_stats.get("daily", {}).get(today, 0)
    read_yest = read_stats.get("daily", {}).get(yesterday, 0)
    total_reads = read_stats.get("total_opens", 0)
    active_users = sum(1 for u in users.values() if u.get("notifications", True))
    quiet_users   = sum(1 for u in users.values() if u.get("quiet_mode_enabled", True))
    breaking_only = sum(1 for u in users.values() if u.get("alert_level") == "breaking")
    interests_set = sum(1 for u in users.values() if u.get("interests"))
    # ── ساعات الذروة ──
    hourly = _broadcast_stats.get("hourly_activity", {})
    if hourly:
        sorted_hours = sorted(hourly.items(), key=lambda x: int(x[0]))
        peak_hour, peak_val = max(hourly.items(), key=lambda x: x[1])
        bar_max = max(hourly.values()) or 1
        peak_chart = ""
        for h, v in sorted_hours:
            bar = "█" * max(1, round(v / bar_max * 8))
            peak_mark = " ⬅ ذروة" if h == peak_hour else ""
            peak_chart += f"`{int(h):02d}:00` {bar}{peak_mark}\n"
    else:
        peak_chart = "_لا بيانات بعد_"
    report = (
        f"📊 *التقرير اليومي — {today}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"👥 إجمالي المستخدمين: `{total_users_count}`\n"
        f"🆕 جدد اليوم: `{new_today}`\n"
        f"🔔 نشطون (إشعارات مفعّلة): `{active_users}`\n"
        f"⭐ مميزون: `{premium_count}`\n"
        f"🌙 وضع صامت: `{quiet_users}`\n"
        f"🚨 عاجلة فقط: `{breaking_only}`\n"
        f"📌 لديهم اهتمامات: `{interests_set}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📺 القنوات/المجموعات: `{channels_count}`\n"
        f"📰 إجمالي أخبار القنوات: `{total_ch_news}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"📖 قراءات اليوم: `{read_today}`\n"
        f"📖 قراءات أمس: `{read_yest}`\n"
        f"📖 إجمالي القراءات: `{total_reads}`\n"
        f"━━━━━━━━━━━━━━\n"
        f"⏰ *ساعات الذروة:*\n{peak_chart}"
        f"━━━━━━━━━━━━━━\n"
        f"🤖 @{BOT_USERNAME}"
    )
    try:
        bot.send_message(ADMIN_ID, report, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)
    for admin_id in extra_admins:
        try:
            bot.send_message(admin_id, report, parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)


def _check_entity_alerts(title: str, source: str):
    """
    يُرسل تنبيهاً لكل مستخدم يتتبع كياناً ظهر في هذا الخبر.
    يعمل في الخلفية بعد كل بثّ.
    """
    def _do():
        title_lower = title.lower()
        for uid_str, entities in list(_entity_tracks.items()):
            try:
                uid = int(uid_str)
                if uid in banned: continue
                for ent_obj in entities:
                    ent = ent_obj.get("entity", "").lower()
                    if ent and ent in title_lower:
                        bot.send_message(uid,
                            f"📡 *تنبيه التتبع:* ذُكر *{ent_obj['entity']}*\n\n"
                            f"📰 _{title}_\n\n_المصدر: {source}_",
                            parse_mode="Markdown")
                        break
            except Exception as _exc:
                _log_exc(_exc)
    _AI_EXECUTOR.submit(_do)


def _build_scheduled_bcast_loop():
    """يُنفّذ البث المجدول في الوقت المحدد."""
    while True:
        try:
            now = time.time()
            due = [b for b in _scheduled_bcasts if b.get("scheduled_ts", 0) <= now]
            for bcast in due:
                _scheduled_bcasts.remove(bcast)
                _save_scheduled()
                text    = bcast.get("text", "")
                target  = bcast.get("target", "all")
                if not text: continue
                uids = []
                if target == "all":
                    uids = [int(uid) for uid, u in users.items()
                            if u.get("notifications", True)]
                elif target == "premium":
                    uids = [int(uid) for uid in users
                            if is_premium(int(uid))]
                for uid in uids:
                    try:
                        bot.send_message(uid, text, parse_mode="Markdown")
                        time.sleep(0.05)
                    except Exception as _exc:
                        _log_exc(_exc)
        except Exception as _exc:
            _log_exc(_exc)
        time.sleep(30)

_start_thread_once("ScheduledBcast", _build_scheduled_bcast_loop)


def _inject_sponsored_news():
    """
    يُضيف خبراً مموّلاً واحداً كل 20 خبراً في البث.
    يُستدعى من دورة البث.
    """
    if not _sponsored_queue:
        return None
    item = _sponsored_queue[0]
    # يُرسل كل 20 دقيقة كحد أدنى
    last_sent = item.get("last_sent_ts", 0)
    if time.time() - last_sent < 1200:
        return None
    item["last_sent_ts"] = time.time()
    _save_sponsored()
    return item


def _build_segment_cache():
    """يُنشئ تصنيفات المستخدمين."""
    global _segment_cache, _segment_cache_ts
    now = time.time()
    cutoff_7  = now - 7  * 86400
    cutoff_30 = now - 30 * 86400

    active, inactive_7, inactive_30, blocked_list = [], [], [], []
    for uid_str, u in list(users.items()):
        try:
            uid = int(uid_str)
            last = u.get("last_active", 0)
            if isinstance(last, str):
                try: last = datetime.datetime.fromisoformat(last).timestamp()
                except Exception as _exc2:
                    _log_exc(_exc2)
                    last = 0
            if last >= cutoff_7:
                active.append(uid)
            elif last >= cutoff_30:
                inactive_7.append(uid)
            else:
                inactive_30.append(uid)
        except Exception as _exc:
            _log_exc(_exc)

    _segment_cache = {
        "active":      active,
        "inactive_7":  inactive_7,
        "inactive_30": inactive_30,
    }
    _segment_cache_ts = now


# ─────────────────────────────────────────────────────────────────────────
# §4  ADMIN COMMANDS — أوامر الأدمن الجديدة
# ─────────────────────────────────────────────────────────────────────────

# ── /dashboard — لوحة القيادة الحية ──────────────────────────────────────
_dashboard_msg_ids: dict = {}   # {uid: message_id}

def _ts(val) -> float:
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        try: return datetime.datetime.fromisoformat(val).timestamp()
        except Exception as _exc:
            _log_exc(_exc)
            return 0.0
    return 0.0
