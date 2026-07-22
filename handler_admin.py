# -*- coding: utf-8 -*-
"""
  handler_admin.py — /admin + كل callbacks الأدمن

  يُصدِّر معالجات أوامر الأدمن وأزرارها.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def cb_admin_back(call):
    if not is_admin(call.from_user.id):
        return
    bot.answer_callback_query(call.id)
    admin_panel(call.from_user.id)

# ======== دوال شكل الخبر ========
@bot.message_handler(commands=["setup_backup"])
def cmd_setup_backup(message):
    import json as _jss
    if not is_admin(message.from_user.id):
        return
    if not BACKUP_CHANNEL_ID:
        bot.send_message(
            message.chat.id,
            "❌ *BACKUP_CHANNEL_ID غير مُعيَّن*\n\n"
            "📋 *خطوات الإعداد:*\n"
            "1️⃣ أنشئ قناة تيليغرام خاصة (مثلاً: IraqNow Backup)\n"
            "2️⃣ أضف البوت كأدمن فيها (صلاحية نشر الرسائل)\n"
            "3️⃣ احصل على ID القناة (يبدأ بـ -100...)\n"
            "4️⃣ اضبط `BACKUP_CHANNEL_ID` في هيروكو Config Vars\n"
            "5️⃣ أعد تشغيل البوت ثم أرسل /setup_backup مجدداً",
            parse_mode="Markdown"
        )
        return
    bot.send_message(message.chat.id, "⏳ جاري إنشاء رسالة الحالة في قناة البكاب...")
    try:
        initial_state = _jss.dumps({
            "db_file_id":  None,
            "zip_file_id": None,
            "ts":          _sa_str(),
            "users":       len(users),
            "note":        "هذه الرسالة تُحدَّث تلقائياً كل 20 دقيقة — لا تحذفها"
        }, ensure_ascii=False, indent=2)
        sent = bot.send_message(BACKUP_CHANNEL_ID, initial_state)
        msg_id = sent.message_id
        bot.send_message(
            message.chat.id,
            f"✅ *تم إنشاء رسالة الحالة بنجاح!*\n\n"
            f"📋 *الخطوة الأخيرة:*\n"
            f"اذهب إلى: هيروكو → Settings → Config Vars\n"
            f"أضف هذا المتغير:\n\n"
            f"`BACKUP_STATE_MSG_ID` = `{msg_id}`\n\n"
            f"ثم اضغط *Restart Dyno* في هيروكو ✅\n\n"
            f"🎉 بعدها البوت يحفظ بياناته كل 20 دقيقة تلقائياً ويستعيدها عند أي إعادة تشغيل!",
            parse_mode="Markdown"
        )
        _logger.info("✅ setup_backup: رسالة الحالة أُنشئت، msg_id=%d", msg_id)
        import threading as _thr2
        _thr2.Thread(target=_safe_job(_send_backup_to_channel), daemon=True, name="FirstBackup").start()
    except Exception as _e:
        bot.send_message(
            message.chat.id,
            f"❌ *فشل إنشاء رسالة الحالة:*\n`{str(_e)[:300]}`\n\n"
            f"تأكد أن البوت أدمن في قناة `{BACKUP_CHANNEL_ID}` وله صلاحية نشر الرسائل.",
            parse_mode="Markdown"
        )


@bot.message_handler(commands=["restart"])
def cmd_restart(m):
    uid = m.from_user.id
    if uid in banned:
        _ban_lang2 = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
        bot.send_message(uid, _ui("user_banned", _ban_lang2))
        return
    if str(uid) not in users:
        send_first_time_welcome(uid, getattr(m.from_user, "first_name", ""))
        return
    user = users[str(uid)]
    old_lang = user.get("lang", "English 🇬🇧")
    kept = {
        "name": user.get("name", ""),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "username": user.get("username", ""),
        "telegram_lang": user.get("telegram_lang", ""),
        "sent_news": user.get("sent_news", {}),
        "referrals": user.get("referrals", []),
        "referred_by": user.get("referred_by"),
        "join_date": user.get("join_date", ""),
        "unlocked_features": user.get("unlocked_features", []),
        "premium": user.get("premium", False),
        "last_command": "/restart",
    }
    kept = {k: v for k, v in kept.items() if v is not None}
    users[str(uid)] = kept
    _db_save_all_users(users)
    restart_msg_map = {
        "العربية 🇮🇶":   "🔄 *تم إعادة ضبط إعداداتك!*\n\nسيتم الآن طلب اختيار لغتك ومنطقتك مجدداً.\nبياناتك ومعلوماتك محفوظة كما هي. 👇",
        "English 🇬🇧":  "🔄 *Your settings have been reset!*\n\nYou will now be asked to choose your language and region again.\nYour data and information are preserved. 👇",
        "Русский 🇷🇺":  "🔄 *Ваши настройки сброшены!*\n\nВас попросят снова выбрать язык и регион.\nВаши данные сохранены. 👇",
        "فارسی 🇮🇷":    "🔄 *تنظیمات شما ریست شد!*\n\nاکنون از شما خواسته میشود دوباره زبان و منطقه خود را انتخاب کنید.\nاطلاعات شما حفظ شده است. 👇",
        "हिन्दी 🇮🇳":   "🔄 *आपकी सेटिंग्स रीसेट हो गई हैं!*\n\nआपसे फिर से भाषा और क्षेत्र चुनने के लिए कहा जाएगा।\nआपका डटा सुरक्षित है। 👇",
        "Português 🇧🇷":"🔄 *Suas configurações foram redefinidas!*\n\nAgora você será solicitado a escolher seu idioma e região novamente.\nSeus dados estão preservados. 👇",
        "Türkçe 🇹🇷":   "🔄 *Ayarlarınız sıfırlandı!*\n\nDil ve bölgenizi tekrar seçmeniz istenecek.\nVerileriniz korunmaktadır. 👇",
        "اردو 🇵🇰":     "🔄 *آپ کی ترتیبات ری سیٹ ہو گئی ہیں!*\n\nآپ سے دوبارہ زبان اور علاقہ منتخب کرنے کو کہا جائے گا۔\nآپ کا ڈیٹا محفوظ ہے۔ 👇",
        "Deutsch 🇩🇪":  "🔄 *Ihre Einstellungen wurden zurückgesetzt!*\n\nSie werden nun aufgefordert, erneut Ihre Sprache und Region zu wählen.\nIhre Daten sind erhalten. 👇",
        "Українська 🇺🇦":"🔄 *Ваші налаштування скинуті!*\n\nВас попросять знову вибрати мову та регіон.\nВаші дані збережені. 👇",
        "Italiano 🇮🇹": "🔄 *Le tue impostazioni sono state reimpostate!*\n\nTi verrà chiesto di scegliere di nuovo la lingua e la regione.\nI tuoi dati sono conservati. 👇",
        "Español 🇲🇽":  "🔄 *¡Tu configuración ha sido restablecida!*\n\nSe te pedirá que elijas tu idioma y región nuevamente.\nTus datos están preservados. 👇",
    }
    restart_msg = restart_msg_map.get(old_lang, restart_msg_map["English 🇬🇧"])
    bot.send_message(uid, restart_msg, parse_mode="Markdown")
    welcome_user(uid)
# ======== دوال الرسائل والتقييم والنشاط ========
@bot.message_handler(commands=["debugnews"])
def cmd_debugnews(m):
    """
    تشخيص شامل ومفصّل خطوة بخطوة لنظام الإرسال.
    - يُرسل التقرير مقسّماً (لتفادي حد تيليغرام 4096 حرف)
    - يستخدم لغة الأدمن المسجّلة (fallback للعربية)
    - يكشف القفل العالق، فلاتر الأخبار، وأسباب عدم الوصول
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return

    wait_msg = bot.send_message(uid, "🔍 جاري التشخيص الشامل... (10-20 ثانية)")
    now_sa = _now_sa()

    def _send_chunks(text: str):
        """يُرسل نص طويل مُقسَّماً إلى رسائل بحد أقصى 3900 حرف"""
        lines = text.split('\n')
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > 3900:
                try:
                    bot.send_message(uid, chunk)
                except Exception as _exc:
                    _log_exc(_exc)
                chunk = line + '\n'
            else:
                chunk += line + '\n'
        if chunk.strip():
            try:
                bot.send_message(uid, chunk)
            except Exception as _exc:
                _log_exc(_exc)

    # لغة الأدمن (fallback للعربية)
    admin_lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶') or 'العربية 🇮🇶'

    # ═══ قسم 1: حالة النظام ═══
    # ── القفل العالق ──
    lock_age_txt = ""
    if _broadcast_news_lock.is_set():
        lock_age = time.time() - _broadcast_lock_ts[0] if _broadcast_lock_ts[0] else 0
        lock_age_txt = f" (عمره {lock_age/60:.1f} دقيقة)"
        if lock_age > 300:
            lock_age_txt += " ⚠️ عالق!"
    news_lock_txt = (f"🔴 مشغول{lock_age_txt}" if _broadcast_news_lock.is_set() else "🟢 حر")
    ch_lock_txt   = ("🔴 مشغول" if _broadcast_channels_lock.is_set() else "🟢 حر")

    paused_lines = []
    if bot_paused:       paused_lines.append("  ❌ bot_paused=True")
    if broadcast_paused: paused_lines.append("  ❌ broadcast_paused=True → اضغط 📡 في /admin")
    paused_txt = ("\n" + "\n".join(paused_lines)) if paused_lines else ""
    paused_icon = "🔴 متوقف" if (bot_paused or broadcast_paused) else "🟢 يعمل"

    # ── المستخدمون ──
    active_u = sum(1 for i in users.values() if i.get("notifications", True) and i.get("lang"))
    users_sample = []
    for u_id, info in list(users.items())[:8]:
        l_ = info.get("lang", "❌ بدون لغة")
        n_ = "🔔" if info.get("notifications", True) else "🔕"
        sn_count = len(info.get("sent_news", {}))
        users_sample.append(f"  {n_} {u_id} | {l_} | sent={sn_count}")
    users_info = "\n".join(users_sample) or "  ❌ لا يوجد مستخدمون — أرسل /start أولاً!"
    # إجمالي sent_news لكل المستخدمين
    _total_user_sent = sum(len(i.get("sent_news", {})) for i in users.values())

    # ── global_sent ──
    with _global_sent_lock:
        gsn_counts = {lg: len(s) for lg, s in _global_sent_news.items()}
    gsn_total = sum(gsn_counts.values())
    gsn_txt   = " | ".join([f"{lg[:12]}:{c}" for lg, c in list(gsn_counts.items())[:6]]) or "فارغ ✅"
    gsn_age   = "—"
    try:
        if os.path.exists(_GLOBAL_SENT_FILE):
            gsn_age = f"{(time.time()-os.path.getmtime(_GLOBAL_SENT_FILE))/60:.0f} دقيقة"
    except Exception as _exc:
        _log_exc(_exc)

    # ── إحصائيات البث ──
    try:
        with _broadcast_stats_lock:
            last_bcast  = _broadcast_stats.get("last_broadcast_time") or "لم يبث بعد"
            today_sent  = _broadcast_stats.get("today_news_sent", 0)
            today_usr   = _broadcast_stats.get("today_users_reached", 0)
    except Exception:
        last_bcast = today_sent = today_usr = "—"

    part1 = (
        f"🔍 تشخيص شامل — {now_sa.strftime('%H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 الأقفال:\n"
        f"  بث المستخدمين: {news_lock_txt}\n"
        f"  بث القنوات:    {ch_lock_txt}\n"
        f"🚦 البث: {paused_icon}{paused_txt}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 المستخدمون: {len(users)} إجمالي | {active_u} فعّال\n"
        f"{users_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 global_sent: {gsn_total} رابط | عمر الملف: {gsn_age}\n"
        f"  {gsn_txt}\n"
        f"📬 user_sent (ذاكرة المستخدمين): {_total_user_sent} رابط إجمالي\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 البث اليوم: {today_sent} خبر → {today_usr} مستخدم\n"
        f"  آخر بث: {last_bcast}"
    )

    # ═══ قسم 2: اختبار RSS التفصيلي ═══
    test_feeds = RSS.get(admin_lang, RSS.get("العربية 🇮🇶", []))
    rss_lines  = [f"📡 اختبار RSS | اللغة: {admin_lang} | عدد المصادر: {len(test_feeds)}"]
    total_raw = total_fresh = total_new = total_pass_lang = 0
    with _global_sent_lock:
        lang_sent = set(_global_sent_news.get(admin_lang, set()))

    for test_url in test_feeds[:5]:   # أول 5 مصادر
        try:
            entries = _fetch_one_feed(test_url)
            n_raw   = len(entries)
            n_fresh = sum(1 for e in entries if _is_fresh(e.get("published_dt")))
            n_new   = sum(1 for e in entries if _is_fresh(e.get("published_dt")) and e["link"] not in lang_sent)
            n_lang  = sum(1 for e in entries if _is_fresh(e.get("published_dt")) and e["link"] not in lang_sent and _title_in_lang(e["title"], admin_lang))
            src     = test_url.split('/')[2][:28] if '/' in test_url else test_url[:28]
            icon    = "✅" if n_fresh > 0 else "⚠️"
            rss_lines.append(f"  {icon} {src}")
            rss_lines.append(f"    raw={n_raw} | fresh={n_fresh} | new={n_new} | pass_lang={n_lang}")
            total_raw += n_raw; total_fresh += n_fresh; total_new += n_new; total_pass_lang += n_lang
            # مثال على خبر طازج
            sample_fresh = next((e for e in entries if _is_fresh(e.get("published_dt"))), None)
            if sample_fresh:
                age_m = int((datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)-sample_fresh["published_dt"]).total_seconds()/60) if sample_fresh.get("published_dt") else "؟"
                rss_lines.append(f"    مثال ({age_m}د): {sample_fresh['title'][:50]}")
        except Exception as ex:
            rss_lines.append(f"  ❌ {test_url[:35]}: {ex}")

    rss_lines.append(f"  ─ الإجمالي: raw={total_raw} | fresh={total_fresh} | new={total_new} | pass_lang={total_pass_lang}")
    part2 = "\n".join(rss_lines)

    # ═══ قسم 3: التشخيص والحل ═══
    diagnosis, fix = [], []
    if bot_paused or broadcast_paused:
        diagnosis.append("❌ البث متوقف يدوياً")
        fix.append("→ /resetbroadcast")
    if not users:
        diagnosis.append("❌ لا مستخدمون مسجلون")
        fix.append("→ /start واختر لغة")
    elif active_u == 0:
        diagnosis.append("❌ جميع المستخدمين بدون لغة محددة")
        fix.append("→ /start واختر لغة")
    if _broadcast_news_lock.is_set():
        lock_age_sec = time.time() - _broadcast_lock_ts[0] if _broadcast_lock_ts[0] else 0
        if lock_age_sec > 300:
            diagnosis.append(f"❌ قفل البث عالق منذ {lock_age_sec/60:.0f} دقيقة")
            fix.append("→ /forcenews يُفرج عنه تلقائياً")
    if total_raw == 0:
        diagnosis.append("❌ لا مقالات RSS — مشكلة شبكة أو feeds فارغة")
        fix.append("→ أعد تشغيل البوت")
    elif total_fresh == 0:
        diagnosis.append("⚠️ كل المقالات قديمة (أكثر من 120 دقيقة)")
        fix.append("→ انتظر دورة البث القادمة")
    elif total_new == 0:
        diagnosis.append("⚠️ كل المقالات الجديدة موجودة في global_sent")
        fix.append("→ /clearcache ثم /forcenews")
    elif total_pass_lang == 0:
        diagnosis.append("⚠️ المقالات محجوبة بفلتر اللغة")
        fix.append("→ تحقق إعداد اللغة أو راجع _title_in_lang")
    # ── فحص user_sent: السبب الأكثر شيوعاً لتوقف البث بصمت ──────────
    if _total_user_sent > 50 and total_fresh > 0 and today_sent == 0:
        diagnosis.append(
            f"🚨 *السبب الرئيسي*: ذاكرة المستخدمين ممتلئة ({_total_user_sent} رابط)\n"
            f"   البوت يجد {total_fresh} خبر طازج لكنها كلها سُبق إرسالها → يرسل صفر"
        )
        fix.append("→ /clearcache (يمسح الذاكرة ويعيد البث فوراً)")
    elif _total_user_sent > 50:
        diagnosis.append(f"⚠️ ذاكرة المستخدمين كبيرة ({_total_user_sent} رابط) — قد تُبطئ البث")
        fix.append("→ /clearcache إذا لاحظت توقف الأخبار")
    if not diagnosis:
        diagnosis.append("✅ كل شيء يعمل — إذا لم تصلك أخبار: /forcenews")

    channels_count = len(channels_groups) if channels_groups else 0
    active_ch = sum(1 for ch in (channels_groups or []) if not ch.get('paused'))

    part3 = (
        f"🩺 التشخيص والحل:\n"
        f"{''.join(chr(10)+d for d in diagnosis)}\n"
        f"{''.join(chr(10)+f for f in fix) if fix else ''}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 القنوات/المجموعات: {channels_count} مسجّلة | {active_ch} فعّالة\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛠 الأوامر: /forcenews | /clearcache | /resetbroadcast | /testnews"
    )

    # أرسل رسالة الانتظار كأول رسالة، ثم الأجزاء
    try:
        bot.edit_message_text(part1, uid, wait_msg.message_id)
    except Exception:
        bot.send_message(uid, part1)
    _send_chunks(part2)
    _send_chunks(part3)


@bot.message_handler(commands=["restartmod"])
def cmd_restartmod(m):
    """
    /restartmod <اسم الوحدة> — يُعيد تشغيل وحدة بعينها بدون إيقاف البوت.
    /restartmod list — لعرض كل الوحدات وحالتها.
    للأدمن فقط.
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return
    args = m.text.split(maxsplit=1)
    if len(args) < 2 or args[1].strip().lower() in ("list", "قائمة", ""):
        status = _get_module_status()
        bot.send_message(
            uid,
            f"📋 *حالة الوحدات القابلة للإعادة*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{status}\n\n"
            f"لإعادة تشغيل وحدة: `/restartmod <الاسم>`\n"
            f"مثال: `/restartmod rss_prefetcher`",
            parse_mode="Markdown"
        )
        return
    mod_name = args[1].strip()
    bot.send_message(uid, f"⏳ جاري إعادة تشغيل `{mod_name}`...", parse_mode="Markdown")
    result = _restart_module(mod_name)
    bot.send_message(uid, result, parse_mode="Markdown")
    _track_error("restartmod_admin", err_type="manual_restart")


@bot.message_handler(commands=["errlogs"])
def cmd_errlogs(m):
    """
    /errlogs — لوحة أخطاء النظام للأدمن (منفصلة عن أخبار المستخدمين).
    تعرض آخر الأخطاء مع فلاتر بالنوع + أزرار التنقل.
    للأدمن فقط.
    """
    uid = m.from_user.id
    if not is_admin(uid):
        return
    _send_alerts_panel(uid, filter_type="all", page=0)


def _send_alerts_panel(uid: int, filter_type: str = "all", page: int = 0):
    """
    يُرسل لوحة التنبيهات الذكية مع أزرار الفلترة.
    filter_type: all / rate_limit / delivery / network / telegram_api / unknown
    """
    PAGE_SIZE = 8
    with _error_timeline_lock:
        history = list(_error_timeline)

    # ── تطبيق الفلتر ──
    if filter_type != "all":
        history = [e for e in history if e.get("type") == filter_type]

    history = list(reversed(history))   # الأحدث أولاً
    total   = len(history)
    page    = max(0, min(page, (total - 1) // PAGE_SIZE))
    chunk   = history[page * PAGE_SIZE: page * PAGE_SIZE + PAGE_SIZE]

    # ── إحصاء سريع حسب النوع ──
    from collections import Counter
    all_hist = list(_error_timeline)
    type_counts = Counter(e.get("type", "unknown") for e in all_hist)

    # ── بناء الرسالة ──
    filter_labels = {
        "all":          f"كل الأخطاء ({total})",
        "rate_limit":   f"⏳ Rate Limit ({type_counts.get('rate_limit', 0)})",
        "delivery":     f"🚫 تسليم فاشل ({type_counts.get('delivery', 0)})",
        "network":      f"🌐 شبكة ({type_counts.get('network', 0)})",
        "telegram_api": f"⚙️ Telegram API ({type_counts.get('telegram_api', 0)})",
        "unknown":      f"❓ غير معروف ({type_counts.get('unknown', 0)})",
    }
    header = (
        f"🔔 *لوحة التنبيهات — فلتر: {filter_labels.get(filter_type, filter_type)}*\n"
        f"صفحة {page + 1} | إجمالي: {total}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
    )
    lines = []
    for e in chunk:
        ts    = datetime.datetime.fromtimestamp(e["ts"]).strftime("%H:%M:%S")
        fn    = e.get("func", "?")[:20]
        etype = e.get("type", "?")[:12]
        msg   = e.get("msg", "")[:60]
        lines.append(f"`{ts}` [{etype}] `{fn}`\n  ↳ {msg}")
    body = "\n".join(lines) if lines else "لا توجد أخطاء في هذا الفلتر 🎉"

    text = header + body

    # ── أزرار الفلترة ──
    type_filters = [
        ("📋 الكل",    "alerts_f:all:0"),
        ("⏳ Rate",    "alerts_f:rate_limit:0"),
        ("🚫 تسليم",  "alerts_f:delivery:0"),
        ("🌐 شبكة",   "alerts_f:network:0"),
        ("⚙️ API",    "alerts_f:telegram_api:0"),
        ("❓ غير معروف","alerts_f:unknown:0"),
    ]
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(*[types.InlineKeyboardButton(lbl, callback_data=cd)
                 for lbl, cd in type_filters])
    # ── أزرار الصفحات ──
    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton(
            "◀️ السابق", callback_data=f"alerts_f:{filter_type}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav_btns.append(types.InlineKeyboardButton(
            "التالي ▶️", callback_data=f"alerts_f:{filter_type}:{page + 1}"))
    if nav_btns:
        markup.add(*nav_btns)
    # ── زر تحديث + حالة الوحدات ──
    markup.add(
        types.InlineKeyboardButton("🔄 تحديث", callback_data=f"alerts_f:{filter_type}:{page}"),
        types.InlineKeyboardButton("⚙️ الوحدات", callback_data="alerts_modules"),
    )

    try:
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(uid, text[:3900], reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("alerts_f:") or c.data == "alerts_modules")
def cb_alerts(c):
    """معالج أزرار لوحة تنبيهات الأدمن فقط — لا يتعارض مع alerts_show_track/alerts_track."""
    if not is_admin(c.from_user.id):
        bot.answer_callback_query(c.id, "غير مصرح!")
        return
    bot.answer_callback_query(c.id)
    uid  = c.from_user.id
    data = c.data

    if data == "alerts_modules":
        status = _get_module_status()
        bot.send_message(
            uid,
            f"⚙️ *حالة الوحدات*\n━━━━━━━━━━━━━━━━━━━\n{status}\n\n"
            f"لإعادة وحدة: `/restartmod <الاسم>`",
            parse_mode="Markdown"
        )
        return

    if data.startswith("alerts_f:"):
        parts = data.split(":")
        if len(parts) == 3:
            _, f_type, pg = parts
            try:
                pg = int(pg)
            except ValueError:
                pg = 0
            try:
                bot.delete_message(c.message.chat.id, c.message.message_id)
            except Exception as _exc:
                _log_exc(_exc)
            _send_alerts_panel(uid, filter_type=f_type, page=pg)


@bot.message_handler(commands=["clearcache"])
def cmd_clearcache(m):
    """يمسح global_sent_news وsent_news لكل المستخدمين — للأدمن فقط"""
    uid = m.from_user.id
    if not is_admin(uid):
        return
    # 1. مسح global_sent_news
    with _global_sent_lock:
        old_global = sum(len(s) for s in _global_sent_news.values())
        _global_sent_news.clear()
    _save_global_sent_news()
    # 2. مسح sent_news لكل المستخدمين (حتى لا تحجبهم ذاكرة الرسائل القديمة)
    old_user_total = 0
    for u_id, info in list(users.items()):
        cnt = len(info.get("sent_news", {}))
        old_user_total += cnt
        info["sent_news"] = {}   # dict فارغ — البنية الجديدة
    threading.Thread(
        target=lambda: _db_save_all_users(users),
        daemon=True, name="SaveUsersAfterClear"
    ).start()
    bot.send_message(uid,
        f"✅ *تم المسح الكامل*\n\n"
        f"📦 global_sent_news: حُذف `{old_global:,}` رابط\n"
        f"👤 sent_news (لكل مستخدم): حُذف `{old_user_total:,}` رابط\n\n"
        f"⏳ البث يبدأ في الدورة القادمة (30-60 ثانية)",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["cleanup"])
def cmd_cleanup(m):
    uid = m.from_user.id
    if not is_admin(uid): return
    wait = bot.send_message(uid, "🧹 جاري فحص الحسابات المحظورة...")

    def _do():
        removed = 0
        for uid_str in list(users.keys()):
            u_id = int(uid_str)
            if u_id in banned:
                continue
            try:
                bot.send_chat_action(u_id, "typing")
            except Exception as e:
                err = str(e).lower()
                if "blocked" in err or "deactivated" in err or "not found" in err:
                    users.pop(uid_str, None)
                    removed += 1
                time.sleep(0.05)
        save_json(USERS_FILE, users)
        try:
            bot.edit_message_text(
                f"✅ *تنظيف مكتمل*\n🗑 حذف {removed} حساب محظور أو غير نشط.",
                uid, wait.message_id, parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ── /killswitch + /resume_all — قاطع الطوارئ ─────────────────────────────
@bot.message_handler(commands=["killswitch"])
def cmd_killswitch(m):
    uid = m.from_user.id
    if not is_admin(uid): return
    global bot_paused, broadcast_paused
    bot_paused = True
    broadcast_paused = True
    bot.send_message(uid,
        "🔴 *Kill Switch مُفعَّل*\n\n"
        "⏹ البث: موقوف\n"
        "⏹ الإشعارات: موقوفة\n\n"
        "_أرسل /resume\\_all لإعادة التشغيل الكامل_",
        parse_mode="Markdown")


@bot.message_handler(commands=["resume_all"])
def cmd_resume_all(m):
    uid = m.from_user.id
    if not is_admin(uid): return
    global bot_paused, broadcast_paused
    bot_paused = False
    broadcast_paused = False
    bot.send_message(uid,
        "🟢 *استئناف كامل*\n\n"
        "▶️ البث: نشط\n"
        "▶️ الإشعارات: نشطة",
        parse_mode="Markdown")


# ── /sponsored — أخبار مموّلة ─────────────────────────────────────────────
@bot.message_handler(commands=["sponsored"])
def cmd_sponsored(m):
    """
    /sponsored — عرض القائمة
    /sponsored add <عنوان> | <نص> | <رابط> — إضافة
    /sponsored del <رقم> — حذف
    /sponsored list — القائمة
    """
    uid = m.from_user.id
    if not is_admin(uid): return
    sep   = "━━━━━━━━━━━━━━"
    parts = m.text.strip().split(None, 1)
    sub   = parts[1].strip() if len(parts) > 1 else ""

    if not sub:
        bot.send_message(uid,
            f"📣 *الأخبار المموّلة*\n{sep}\n\n"
            "أوامر:\n"
            "`/sponsored add عنوان | نص | رابط`\n"
            "`/sponsored list`\n"
            "`/sponsored del 1`\n\n"
            "_ستظهر كل خبر مموّل بعلامة 📣 محتوى مموّل_",
            parse_mode="Markdown")
        return

    if sub.lower() == "list":
        if not _sponsored_queue:
            bot.send_message(uid, "📋 لا يوجد محتوى مموّل حالياً."); return
        lines = [f"📣 *قائمة المموّل ({len(_sponsored_queue)}):*\n{sep}"]
        for i, s in enumerate(_sponsored_queue):
            lines.append(f"{i+1}. {s['title'][:60]}")
        bot.send_message(uid, "\n".join(lines), parse_mode="Markdown")
        return

    if sub.lower().startswith("del "):
        try:
            idx = int(sub[4:].strip()) - 1
            removed = _sponsored_queue.pop(idx)
            _save_sponsored()
            bot.send_message(uid, f"✅ حذف: _{removed['title']}_", parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, "⚠️ رقم غير صحيح.")
        return

    if sub.lower().startswith("add "):
        raw = sub[4:].strip()
        parts3 = [p.strip() for p in raw.split("|")]
        if len(parts3) < 2:
            bot.send_message(uid, "⚠️ الصيغة: `/sponsored add عنوان | نص | رابط`"); return
        title = parts3[0]
        text  = parts3[1] if len(parts3) > 1 else title
        link  = parts3[2] if len(parts3) > 2 else ""
        _sponsored_queue.append({
            "title": title, "text": text, "url": link,
            "label": "📣 محتوى مموّل", "added_ts": time.time(), "last_sent_ts": 0
        })
        _save_sponsored()
        bot.send_message(uid,
            f"✅ *تم إضافة المحتوى المموّل:*\n📰 _{title}_", parse_mode="Markdown")
        return

    bot.send_message(uid, "⚠️ أمر غير صحيح. أرسل `/sponsored` للمساعدة.")


# ─────────────────────────────────────────────────────────────────────────
# §5  USER COMMANDS — أوامر ومميزات المستخدم العادي
# ─────────────────────────────────────────────────────────────────────────

# ── 🔖 Bookmark — حفظ الأخبار ─────────────────────────────────────────────
# زر الحفظ يُضاف في make_news_share_markup — سنربطه بـ bm_<key>
