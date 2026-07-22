# -*- coding: utf-8 -*-
"""
  db_backup.py — auto-backup/restore من قناة تيليغرام

  يُصدِّر دوال النسخ الاحتياطي والاسترداد التلقائي.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الأساسية
from bot_legacy import _logger, _log_exc, _db_lock, _db_conn, _now_sa, _sa_str  # noqa: F811

# FIX: _track_error قد تأتي من error_tracker — lazy fallback
def _track_error(func_name: str, exc: Exception = None, err_type: str = ""):
    import sys as _s
    _et = _s.modules.get("error_tracker")
    if _et and hasattr(_et, "_track_error"):
        _et._track_error(func_name, exc, err_type)
    else:
        _log_exc(exc, func_name)

def _auto_db_backup():
    """
    ينسخ `bot_data.db` إلى `bot_data.db.bak` دورياً.
    يُجري VACUUM لتحسين الأداء وتقليص الحجم.
    """
    try:
        import shutil
        bak = DB_FILE + ".bak"
        # VACUUM في connection منفصلة لا تحجب _db_conn الرئيسية
        try:
            import sqlite3 as _sq3_vac
            _vac_conn = _sq3_vac.connect(DB_FILE, timeout=10)
            _vac_conn.execute("PRAGMA journal_mode=WAL")
            _vac_conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            _vac_conn.close()
        except Exception as _vexc:
            _logger.debug("WAL checkpoint: %s", _vexc)
        shutil.copy2(DB_FILE, bak)
        size_kb = os.path.getsize(bak) / 1024
        _logger.info("💾 DB backup: %s — %.1f KB", bak, size_kb)
    except Exception as _dbe:
        _logger.error("_auto_db_backup: %s", _dbe)
        _track_error("_auto_db_backup", _dbe)

# ── Replit Keep-Alive: HTTP server بسيط لمنع السقوط ────────────────────────
def _build_backup_report():
    """يبني تقرير نصي مفصّل بكل بيانات البوت والمستخدمين."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💾 تقرير النسخة الاحتياطية الشاملة")
    lines.append(f"🕐 التاريخ والوقت: {now}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── إحصائيات عامة ──
    total_users = len(users)
    premium_list = stats.get("premium_users", [])
    premium_count = len(premium_list)
    banned_count = len(banned)
    lines.append(f"\n📊 إحصائيات عامة:")
    lines.append(f"  👥 إجمالي المستخدمين: {total_users}")
    lines.append(f"  ⭐ المستخدمون المميزون: {premium_count}")
    lines.append(f"  🚫 المحظورون: {banned_count}")
    lines.append(f"  💰 الإيرادات: {stats.get('revenue', 0.0)}")

    # ── أعلى اللغات ──
    top_langs = sorted(stats.get("languages_count", {}).items(), key=lambda x: x[1], reverse=True)[:5]
    if top_langs:
        lines.append(f"\n🌐 أكثر اللغات استخداماً:")
        for lang_name, count in top_langs:
            lines.append(f"  • {lang_name}: {count} مستخدم")

    # ── أكثر الأزرار ضغطاً ──
    top_buttons = sorted(stats.get("button_presses", {}).items(), key=lambda x: x[1], reverse=True)[:5]
    if top_buttons:
        lines.append(f"\n🔘 أكثر الأوامر/الأزرار استخداماً:")
        for btn, count in top_buttons:
            lines.append(f"  • {btn}: {count} مرة")

    # ── تحليل داخلي شامل (القسم 5) ──
    lines.append(f"\n{'━'*30}")
    lines.append(f"📊 تحليل داخلي شامل:")
    lines.append(f"{'━'*30}")

    # أكثر الرموز/الأسهم/العملات متابعةً عبر كل المستخدمين
    all_symbols_counter = {}
    for uid_str, td in tracked_assets.items():
        for sym in td.get("assets", []):
            all_symbols_counter[sym] = all_symbols_counter.get(sym, 0) + 1
    top_symbols = sorted(all_symbols_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_symbols:
        lines.append(f"\n📌 أكثر الرموز/الأسهم/العملات متابعةً:")
        for sym, cnt in top_symbols:
            lines.append(f"  • {sym}: {cnt} مستخدم")
    else:
        lines.append(f"\n📌 أكثر الرموز متابعةً: لا يوجد بيانات بعد")

    # أكثر المدن طلباً للطقس
    all_cities_counter = {}
    for uid_str, u in list(users.items()):
        prov = u.get("province", "")
        if prov and prov not in ("—", ""):
            all_cities_counter[prov] = all_cities_counter.get(prov, 0) + 1
        for c in u.get("extra_cities", []):
            if c:
                all_cities_counter[c] = all_cities_counter.get(c, 0) + 1
    top_cities = sorted(all_cities_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_cities:
        lines.append(f"\n🌆 أكثر المدن طلباً للطقس:")
        for city, cnt in top_cities:
            lines.append(f"  • {city}: {cnt} مستخدم")

    # توزيع أوقات الملخص اليومي
    notif_hours_counter = {}
    users_with_notif_hour = 0
    for uid_str, u in list(users.items()):
        nh = u.get("notif_hour")
        if nh and nh != "—":
            users_with_notif_hour += 1
            notif_hours_counter[str(nh)] = notif_hours_counter.get(str(nh), 0) + 1
    lines.append(f"\n⏰ المستخدمون الذين ضبطوا وقت ملخص يومي: {users_with_notif_hour}")
    if notif_hours_counter:
        top_hours = sorted(notif_hours_counter.items(), key=lambda x: x[1], reverse=True)[:5]
        lines.append(f"  أكثر الأوقات شيوعاً:")
        for hr, cnt in top_hours:
            lines.append(f"    • الساعة {hr}: {cnt} مستخدم")

    # توزيع تنبيهات العملات
    users_with_alert = sum(1 for u in users.values() if u.get("currency_alert") and u.get("currency_alert") != "—")
    lines.append(f"\n🔔 المستخدمون الذين فعّلوا تنبيه سعر العملة: {users_with_alert}")

    # المستخدمون الأكثر إحالةً (أعلى 5)
    top_referrers = sorted(
        [(uid_str, len(u.get("referrals", []))) for uid_str, u in list(users.items()) if u.get("referrals")],
        key=lambda x: x[1], reverse=True
    )[:5]
    if top_referrers:
        lines.append(f"\n🏆 أكثر المستخدمين إحالةً:")
        for uid_str, ref_cnt in top_referrers:
            u = users.get(uid_str, {})
            uname = u.get("username") or u.get("name") or uid_str
            lines.append(f"  • {uname} ({uid_str}): {ref_cnt} إحالة")

    # المستخدمون الذين استخدموا الملخص اليومي/الأسبوعي
    used_summary_count = sum(1 for u in users.values() if u.get("used_summary"))
    lines.append(f"\n📋 المستخدمون الذين استخدموا الملخص: {used_summary_count}")

    # توزيع الاهتمامات
    interests_counter = {}
    for u in users.values():
        for interest in u.get("interests", []):
            interests_counter[interest] = interests_counter.get(interest, 0) + 1
    if interests_counter:
        top_interests = sorted(interests_counter.items(), key=lambda x: x[1], reverse=True)[:8]
        lines.append(f"\n🎯 أكثر الاهتمامات شيوعاً:")
        for interest, cnt in top_interests:
            lines.append(f"  • {interest}: {cnt} مستخدم")

    # المستخدمون النشطون (آخر ظهور خلال 7 أيام)
    try:
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        active_7d = 0
        active_30d = 0
        month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        for u in users.values():
            ls = u.get("last_seen", "")
            if ls and ls != "—":
                try:
                    ls_dt = datetime.datetime.strptime(ls, "%Y-%m-%d %H:%M")
                    if ls_dt >= week_ago:
                        active_7d += 1
                    if ls_dt >= month_ago:
                        active_30d += 1
                except Exception as _exc:
                    _log_exc(_exc)
        lines.append(f"\n📅 المستخدمون النشطون خلال آخر 7 أيام: {active_7d}")
        lines.append(f"📅 المستخدمون النشطون خلال آخر 30 يوماً: {active_30d}")
    except Exception as _exc:
        _log_exc(_exc)

    # الكلمات المفتاحية (لكل مستخدم مميز)
    users_with_keywords = sum(1 for uid_str in users if user_keywords.get(uid_str))
    lines.append(f"\n🔑 المستخدمون الذين لديهم كلمات مفتاحية: {users_with_keywords}")

    # ── بيانات تقنية (القسم 6) ──
    lines.append(f"\n{'━'*30}")
    lines.append(f"🔧 بيانات تقنية:")
    lines.append(f"{'━'*30}")
    lines.append(f"  🤖 اسم البوت: @{BOT_USERNAME}")
    lines.append(f"  📦 ملف قاعدة البيانات: {DB_FILE}")
    lines.append(f"  📝 ملاحظة: عناوين IP غير محفوظة (تلغرام لا يوفرها للبوتات)")
    lines.append(f"  📝 ملاحظة: سجل أخطاء المستخدمين غير مخزّن بشكل مستقل")
    lines.append(f"  📝 ملاحظة: إصدار البوت عند المستخدم غير متاح عبر API تلغرام")

    # ── تفاصيل المستخدمين ──
    lines.append(f"\n{'━'*30}")
    lines.append(f"👤 تفاصيل المستخدمين ({total_users} مستخدم):")
    lines.append(f"{'━'*30}")

    for idx, (uid_str, user) in enumerate(users.items(), 1):
        # ── المعلومات الأساسية ──
        name = user.get("name", "غير معروف")
        username = user.get("username", "—")
        first_name = user.get("first_name", name)
        last_name = user.get("last_name", "")
        lang = user.get("lang", "—")
        country = user.get("country", "—")
        province = user.get("province", "—")
        join_date = user.get("join_date", "—")
        notifications = "✅ مفعّل" if user.get("notifications", True) else "❌ مغلق"
        is_prem = "⭐ نعم" if int(uid_str) in premium_list else "لا"
        is_ban = "🚫 نعم" if int(uid_str) in banned else "لا"
        premium_direct = "⭐ نعم" if user.get("premium") else "لا"

        # ── التفضيلات والتتبع ──
        track_data = tracked_assets.get(uid_str, {})
        tracked_symbols = track_data.get("assets", [])
        tracked_symbols_str = ", ".join(tracked_symbols) if tracked_symbols else "لا يوجد"

        extra_cities = user.get("extra_cities", [])
        all_cities = ([province] if province and province != "—" else []) + extra_cities
        cities_str = ", ".join(all_cities) if all_cities else "لا يوجد"

        currency_alert = user.get("currency_alert", "—")
        notif_hour = user.get("notif_hour", "—")
        notif_type = "رسالة نصية" if user.get("notifications", True) else "مغلق"
        interests = user.get("interests", [])
        interests_str = ", ".join(interests) if interests else "—"
        unlocked = user.get("unlocked_features", [])
        unlocked_str = ", ".join(unlocked) if unlocked else "—"
        ref_premium_expiry = user.get("ref_premium_expiry", "—")
        referrals_count = len(user.get("referrals", []))
        referred_by = user.get("referred_by", "—")
        last_alert_sent = user.get("currency_alert_last", "—")
        sent_news_count = len(user.get("sent_news", {}))
        telegram_lang = user.get("telegram_lang", "—")
        last_command = user.get("last_command", "—")
        last_seen = user.get("last_seen", "—")
        used_summary = "✅ نعم" if user.get("used_summary") else "لا"
        rewarded_milestones = user.get("rewarded_milestones", [])
        rewarded_str = ", ".join(str(m) for m in rewarded_milestones) if rewarded_milestones else "—"
        keywords = user_keywords.get(uid_str, [])
        keywords_str = ", ".join(keywords) if keywords else "—"

        lines.append(f"\n{'─'*30}")
        lines.append(f"#{idx} — {first_name} {last_name}".strip())

        lines.append(f"\n  1️⃣ معلومات الحساب:")
        lines.append(f"  🆔 user_id: {uid_str}")
        lines.append(f"  👤 username: @{username}" if username and username != "—" else f"  👤 username: —")
        lines.append(f"  📛 الاسم الأول: {first_name}")
        lines.append(f"  📛 الاسم الأخير: {last_name if last_name else '—'}")
        lines.append(f"  🌐 اللغة المختارة في البوت: {lang}")
        lines.append(f"  💬 لغة تلغرام (Language Code): {telegram_lang}")
        lines.append(f"  🌍 الدولة: {country}")
        lines.append(f"  📍 المدينة/المحافظة الرئيسية: {province}")
        lines.append(f"  📅 تاريخ الانضمام: {join_date}")
        lines.append(f"  🕐 آخر ظهور: {last_seen}")
        lines.append(f"  🚫 محظور: {is_ban}")

        lines.append(f"\n  2️⃣ الاشتراك والمميزات:")
        lines.append(f"  ⭐ مميز (قائمة الأدمن): {is_prem}")
        lines.append(f"  ⭐ مميز (حقل مباشر): {premium_direct}")
        lines.append(f"  ⏰ انتهاء المميز المجاني: {ref_premium_expiry}")
        lines.append(f"  🎖 مراحل الإحالة المكافأة: {rewarded_str}")
        lines.append(f"  🔓 الميزات المفتوحة: {unlocked_str}")

        lines.append(f"\n  3️⃣ وظائف البوت — الطقس والتنبيهات:")
        lines.append(f"  🌆 المدن المتابعة للطقس: {cities_str}")
        lines.append(f"  📌 الأسهم/العملات المتابعة (/mytrack): {tracked_symbols_str}")
        lines.append(f"  🔔 تنبيه سعر العملة (/alerts): {currency_alert}")
        lines.append(f"  💹 آخر سعر تنبيه أُرسل: {last_alert_sent}")
        lines.append(f"  ⏰ وقت الملخص اليومي: {notif_hour}")
        lines.append(f"  📢 حالة الإشعارات: {notifications}")
        lines.append(f"  📨 نوع الإشعار: {notif_type}")
        lines.append(f"  🔑 الكلمات المفتاحية (للمميزين): {keywords_str}")

        lines.append(f"\n  4️⃣ التفاعل والاهتمامات:")
        lines.append(f"  🎯 الاهتمامات: {interests_str}")
        lines.append(f"  🗞 عدد الأخبار المُرسلة له: {sent_news_count}")
        lines.append(f"  📋 استخدم الملخص اليومي/الأسبوعي: {used_summary}")
        lines.append(f"  🖱 آخر أمر استخدمه: {last_command}")
        lines.append(f"  👥 عدد الإحالات: {referrals_count}")
        lines.append(f"  🔗 مُحال من: {referred_by}")

    lines.append(f"\n{'━'*30}")
    lines.append(f"📦 ملفات JSON المحفوظة:")
    for fname in [STATS_FILE, BANNED_FILE, RSS_FILE, ADMINS_FILE,
                  KEYWORDS_FILE, TRACK_FILE, CHANNELS_FILE, BLACKLIST_FILE,
                  READ_STATS_FILE, BROADCAST_SETTINGS_FILE, NEWS_SETTINGS_FILE,
                  INBOX_FILE, RATINGS_FILE]:
        exists = "✅" if os.path.exists(fname) else "❌"
        lines.append(f"  {exists} {fname}")

    lines.append(f"\n💾 ملف قاعدة البيانات: {DB_FILE}")
    lines.append(f"🕐 وقت إنشاء التقرير: {now}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _send_sectioned_backup(chat_id, section):
    """إرسال نسخة احتياطية لقسم محدد"""
    import io, json as _json, zipfile
    now_str  = _now_sa().strftime("%Y-%m-%d %H:%M")
    file_str = _now_sa().strftime("%Y%m%d-%H%M")
    try:
        if section == "users":
            # نسخة قاعدة المستخدمين من SQLite
            with _db_lock:
                _db_conn.commit()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(DB_FILE):
                    zf.write(DB_FILE, os.path.basename(DB_FILE))
                # ملف JSON احتياطي للمستخدمين
                users_json = {uid: {k: list(v) if isinstance(v, set) else v
                                    for k, v in info.items()}
                              for uid, info in list(users.items())}
                zf.writestr("users_backup.json", _json.dumps(users_json, ensure_ascii=False, indent=2))
            buf.seek(0)
            buf.name = f"users_backup_{file_str}.zip"
            caption = (f"👥 *نسخة المستخدمين*\n🕐 {now_str}\n"
                       f"📊 إجمالي: `{len(users)}` مستخدم")
            bot.send_document(chat_id, buf, caption=caption,
                              visible_file_name=f"users_backup_{file_str}.zip",
                              parse_mode="Markdown")

        elif section == "rss":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(RSS_FILE):
                    zf.write(RSS_FILE, os.path.basename(RSS_FILE))
                if os.path.exists(CUSTOM_TG_CHANNELS_FILE):
                    zf.write(CUSTOM_TG_CHANNELS_FILE, os.path.basename(CUSTOM_TG_CHANNELS_FILE))
                # إضافة بيانات RSS من الذاكرة
                zf.writestr("rss_in_memory.json", _json.dumps(RSS, ensure_ascii=False, indent=2))
                zf.writestr("custom_tg_channels_in_memory.json", _json.dumps(_custom_tg_channels, ensure_ascii=False, indent=2))
            buf.seek(0)
            buf.name = f"rss_backup_{file_str}.zip"
            total_feeds = sum(len(v) for v in RSS.values())
            caption = (f"📡 *نسخة مصادر RSS*\n🕐 {now_str}\n"
                       f"📊 إجمالي المصادر: `{total_feeds}`")
            bot.send_document(chat_id, buf, caption=caption,
                              visible_file_name=f"rss_backup_{file_str}.zip",
                              parse_mode="Markdown")

        elif section == "channels":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                if os.path.exists(CHANNELS_FILE):
                    zf.write(CHANNELS_FILE, os.path.basename(CHANNELS_FILE))
                zf.writestr("channels_in_memory.json",
                            _json.dumps(channels_groups, ensure_ascii=False, indent=2))
            buf.seek(0)
            buf.name = f"channels_backup_{file_str}.zip"
            caption = (f"📺 *نسخة القنوات والمجموعات*\n🕐 {now_str}\n"
                       f"📊 إجمالي: `{len(channels_groups)}`")
            bot.send_document(chat_id, buf, caption=caption,
                              visible_file_name=f"channels_backup_{file_str}.zip",
                              parse_mode="Markdown")

        elif section == "settings":
            settings_files = [
                ADMINS_FILE, KEYWORDS_FILE, TRACK_FILE, BLACKLIST_FILE,
                BROADCAST_SETTINGS_FILE, NEWS_SETTINGS_FILE, INBOX_FILE,
                RATINGS_FILE, WELCOME_FILE, STATS_FILE, READ_STATS_FILE,
            ]
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for fp in settings_files:
                    if os.path.exists(fp):
                        zf.write(fp, os.path.basename(fp))
            buf.seek(0)
            buf.name = f"settings_backup_{file_str}.zip"
            caption = (f"⚙️ *نسخة الإعدادات*\n🕐 {now_str}")
            bot.send_document(chat_id, buf, caption=caption,
                              visible_file_name=f"settings_backup_{file_str}.zip",
                              parse_mode="Markdown")
    except Exception as e:
        try:
            bot.send_message(chat_id, f"❌ خطأ في النسخة الاحتياطية ({section}): {e}")
        except Exception as _exc:
            _log_exc(_exc)


def send_backup(chat_id=None):
    import io, zipfile
    target = chat_id if chat_id else ADMIN_ID
    with _db_lock:
        _db_conn.commit()
    now = _now_sa().strftime("%Y-%m-%d %H:%M")
    file_now = _now_sa().strftime("%Y%m%d-%H%M")

    # ── 1) إرسال ملف الإعدادات ZIP (آمن 100% للاستعادة بدون كراش) ──
    try:
        settings_zip = io.BytesIO()
        settings_files = [
            ADMINS_FILE, KEYWORDS_FILE, TRACK_FILE, CHANNELS_FILE,
            BLACKLIST_FILE, BROADCAST_SETTINGS_FILE, NEWS_SETTINGS_FILE,
            INBOX_FILE, RATINGS_FILE, WELCOME_FILE, STATS_FILE, READ_STATS_FILE,
        ]
        with zipfile.ZipFile(settings_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for f_path in settings_files:
                if os.path.exists(f_path):
                    zf.write(f_path, os.path.basename(f_path))
        settings_zip.seek(0)
        settings_zip.name = f"bot_settings_{file_now}.zip"
        bot.send_document(
            target,
            settings_zip,
            caption=(
                f"⚙️ *نسخة احتياطية — الإعدادات*\n"
                f"🕐 {now}\n\n"
                f"📦 يحتوي على:\n"
                f"• القنوات والمجموعات\n"
                f"• الأدمن المضافين\n"
                f"• الكلمات المفتاحية والتنبيهات\n"
                f"• تتبع الأسهم والعملات\n"
                f"• الكلمات المحظورة ({len(blacklist_words)})\n"
                f"• رسائل الصندوق ({len(inbox_messages)})\n"
                f"• إعدادات الأخبار والبث\n"
                f"• رسالة الترحيب المخصصة\n"
                f"• التقييمات والإحصائيات\n\n"
                f"↩️ *لاستعادة الإعدادات:* أرسل هذا الملف للبوت مباشرة\n"
                f"✅ آمن تماماً — لا يوقف البوت"
            ),
            visible_file_name=f"bot_settings_{file_now}.zip",
            parse_mode="Markdown"
        )
    except Exception as e:
        try:
            bot.send_message(target, f"❌ فشل إرسال ملف الإعدادات: {e}")
        except Exception as _exc:
            _log_exc(_exc)

    # ── 2) إرسال قاعدة البيانات .db (المستخدمون) ──
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "rb") as f:
                bot.send_document(
                    target,
                    f,
                    caption=(
                        f"💾 *نسخة احتياطية — قاعدة البيانات*\n"
                        f"🕐 {now}\n"
                        f"👥 المستخدمون: {len(users)}\n"
                        f"⭐ المميزون: {len(stats.get('premium_users', []))}\n"
                        f"🚫 المحظورون: {len(banned)}\n\n"
                        f"↩️ *لاستعادة البيانات:* أرسل هذا الملف للبوت مباشرة\n"
                        f"✅ آمن تماماً — لا يوقف البوت"
                    ),
                    visible_file_name=f"bot_data_{file_now}.db",
                    parse_mode="Markdown"
                )
    except Exception as e:
        try:
            bot.send_message(target, f"❌ فشل إرسال قاعدة البيانات: {e}")
        except Exception as _exc:
            _log_exc(_exc)

    # ── 3) إرسال تقرير المستخدمين .txt (مفصّل قابل للقراءة) ──
    try:
        report_text = _build_backup_report()
        report_bytes = io.BytesIO(report_text.encode("utf-8"))
        report_bytes.name = f"users_report_{file_now}.txt"
        bot.send_document(
            target,
            report_bytes,
            caption=(
                f"📋 *تقرير المستخدمين التفصيلي*\n"
                f"🕐 {now}\n"
                f"👥 إجمالي المستخدمين: {len(users)}\n\n"
                f"📄 يحتوي على:\n"
                f"• معلومات الحساب الكاملة (ID، اسم المستخدم، الأسماء)\n"
                f"• اللغة المختارة ولغة تلغرام\n"
                f"• الدولة والمدينة\n"
                f"• تاريخ الانضمام وآخر ظهور\n"
                f"• حالة الإشعارات والاشتراك المميز\n"
                f"• الرموز المتابعة وتنبيهات العملات\n"
                f"• آخر أمر واهتمامات المستخدم\n"
                f"• الإحالات والميزات المفعّلة"
            ),
            visible_file_name=f"users_report_{file_now}.txt",
            parse_mode="Markdown"
        )
    except Exception as e:
        try:
            bot.send_message(target, f"❌ فشل إرسال تقرير المستخدمين: {e}")
        except Exception as _exc:
            _log_exc(_exc)

def auto_backup():
    send_backup(ADMIN_ID)

# ======== تذكير الأدمن إذا البوت متوقف أكثر من 6 ساعات ========
def _update_backup_state(db_file_id=None, zip_file_id=None):
    """يُحدّث رسالة الحالة بأحدث file_ids للملفات الاحتياطية."""
    if not BACKUP_CHANNEL_ID or not BACKUP_STATE_MSG_ID:
        return
    import json as _jsu
    try:
        try:
            fwd = bot.forward_message(ADMIN_ID, BACKUP_CHANNEL_ID, BACKUP_STATE_MSG_ID)
            old_text  = fwd.text or fwd.caption or "{}"
            try:
                bot.delete_message(ADMIN_ID, fwd.message_id)
            except Exception:
                pass
            old_state = _jsu.loads(old_text) if old_text.strip().startswith("{") else {}
        except Exception:
            old_state = {}
        new_state = {
            "db_file_id":  db_file_id  or old_state.get("db_file_id"),
            "zip_file_id": zip_file_id or old_state.get("zip_file_id"),
            "ts":          _sa_str(),
            "users":       len(users),
        }
        bot.edit_message_text(
            text=_jsu.dumps(new_state, ensure_ascii=False),
            chat_id=BACKUP_CHANNEL_ID,
            message_id=BACKUP_STATE_MSG_ID
        )
        _logger.info("✅ تم تحديث رسالة الحالة في قناة البكاب")
    except Exception as _e:
        _logger.warning("⚠️ فشل تحديث رسالة الحالة: %s", _e)


def _send_backup_to_channel():
    """
    يُرسل النسخة الاحتياطية (DB + ZIP) إلى قناة البكاب ويُحدّث رسالة الحالة.
    يُستدعى تلقائياً كل 20 دقيقة وعند إيقاف البوت (SIGTERM).
    """
    if not BACKUP_CHANNEL_ID or not BACKUP_STATE_MSG_ID:
        return
    import io as _io2, zipfile as _zf2
    db_file_id  = None
    zip_file_id = None
    file_now = _now_sa().strftime("%Y%m%d-%H%M")
    now_str  = _sa_str()
    # ─── إرسال قاعدة البيانات ──────────────────────────────────────
    try:
        if os.path.exists(DB_FILE):
            with _db_lock:
                _db_conn.commit()
            with open(DB_FILE, "rb") as _dbf:
                sent_db = bot.send_document(
                    BACKUP_CHANNEL_ID,
                    _dbf,
                    caption=f"💾 DB | {now_str} | 👥 {len(users)}",
                    visible_file_name=f"bot_data_{file_now}.db"
                )
            db_file_id = sent_db.document.file_id
    except Exception as _e:
        _logger.warning("⚠️ فشل إرسال DB إلى قناة البكاب: %s", _e)
    # ─── إرسال ملف الإعدادات ZIP ───────────────────────────────────
    try:
        settings_zip = _io2.BytesIO()
        settings_files_list = [
            ADMINS_FILE, KEYWORDS_FILE, TRACK_FILE, CHANNELS_FILE,
            BLACKLIST_FILE, BROADCAST_SETTINGS_FILE, NEWS_SETTINGS_FILE,
            INBOX_FILE, RATINGS_FILE, WELCOME_FILE, STATS_FILE, READ_STATS_FILE,
        ]
        with _zf2.ZipFile(settings_zip, "w", _zf2.ZIP_DEFLATED) as _zff:
            for _fp in settings_files_list:
                if os.path.exists(_fp):
                    _zff.write(_fp, os.path.basename(_fp))
        settings_zip.seek(0)
        sent_zip = bot.send_document(
            BACKUP_CHANNEL_ID,
            settings_zip,
            caption=f"⚙️ Settings | {now_str}",
            visible_file_name=f"bot_settings_{file_now}.zip"
        )
        zip_file_id = sent_zip.document.file_id
    except Exception as _e:
        _logger.warning("⚠️ فشل إرسال ZIP إلى قناة البكاب: %s", _e)
    # ─── تحديث رسالة الحالة ────────────────────────────────────────
    if db_file_id or zip_file_id:
        _update_backup_state(db_file_id=db_file_id, zip_file_id=zip_file_id)
        _logger.info("🔄 تم حفظ نسخة احتياطية تلقائية في قناة التيليغرام")



# ── معالج ملفات المستخدمين (TXT / CSV / JSON / PDF) ──────────────────────
