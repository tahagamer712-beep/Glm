# -*- coding: utf-8 -*-
"""
  handler_voice.py — /voice /podcast + callbacks صوتية

  يُصدِّر معالجات أوامر الصوت والبودكاست.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def send_voice_news(uid, count=3):
    """جلب آخر الأخبار وإرسالها كرسالة صوتية"""
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")
    if not _TTS_AVAILABLE:
        bot.send_message(uid, _ui("voice_unavailable", lang))
        return
    voice = TTS_VOICES.get(lang, "ar-IQ-BasselNeural")

    bot.send_message(uid, _ui("voice_loading", lang))

    # جلب آخر الأخبار من RSS
    feeds = RSS.get(lang, [])
    news_titles = []
    for feed_url in feeds[:5]:
        try:
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries[:8]:
                title = getattr(entry, 'title', '').strip()
                if title and len(title) > 15:
                    news_titles.append(title)
                if len(news_titles) >= count * 3:
                    break
        except Exception as _exc:
            _log_exc(_exc)
        if len(news_titles) >= count * 3:
            break

    # إزالة المكررة وأخذ العدد المطلوب
    unique = []
    for t in news_titles:
        dup = any(_is_similar_title(t, u) for u in unique)
        if not dup:
            unique.append(t)
        if len(unique) >= count:
            break

    if not unique:
        bot.send_message(uid, _ui("voice_no_news", lang))
        return

    # تجميع النص الصوتي
    intro_map = {
        "العربية 🇮🇶": "مرحباً، إليك آخر الأخبار.",
        "English 🇬🇧": "Hello, here are the latest news.",
        "Русский 🇷🇺": "Привет, вот последние новости.",
        "فارسی 🇮🇷": "سلام، آخرین اخبار را بشنوید.",
        "Türkçe 🇹🇷": "Merhaba, işte son haberler.",
        "Deutsch 🇩🇪": "Hallo, hier sind die neuesten Nachrichten.",
        "Español 🇲🇽": "Hola, aquí están las últimas noticias.",
        "Italiano 🇮🇹": "Ciao, ecco le ultime notizie.",
    }
    separator_map = {
        "العربية 🇮🇶": ". الخبر التالي: ",
        "English 🇬🇧": ". Next: ",
        "Русский 🇷🇺": ". Следующее: ",
        "فارسی 🇮🇷": ". خبر بعدی: ",
        "Türkçe 🇹🇷": ". Sonraki: ",
        "Deutsch 🇩🇪": ". Als nächstes: ",
        "Español 🇲🇽": ". A continuación: ",
        "Italiano 🇮🇹": ". Prossimo: ",
    }
    intro = intro_map.get(lang, "Here are the latest news.")
    sep = separator_map.get(lang, ". Next: ")
    full_text = intro + " " + sep.join(unique)

    # توليد الصوت وإرساله
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        success, err = _tts_generate(full_text, voice, tmp_path)
        if not success or not os.path.exists(tmp_path):
            err_detail = f"\n\n`{err[:120]}`" if err else ""
            bot.send_message(uid, f"{_ui('voice_fail', lang)}{err_detail}", parse_mode="Markdown")
            return
        with open(tmp_path, 'rb') as audio:
            news_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(unique)])
            caption = f"{_ui('voice_caption', lang)} — {count}\n\n{news_text[:800]}"
            bot.send_voice(uid, audio, caption=caption, parse_mode="Markdown")
        try:
            os.unlink(tmp_path)
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        bot.send_message(uid, f"{_ui('voice_fail', lang)}\n\n`{str(e)[:120]}`", parse_mode="Markdown")

# ======== قائمة الأخبار الصوتية ========
def _send_voice_news_menu(uid):
    """يعرض قائمة لاختيار عدد الأخبار الصوتية"""
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    labels = {
        "العربية 🇮🇶":   ("🎙️ *أخبار صوتية*\n\nاختر عدد الأخبار:", "خبر", "أخبار"),
        "English 🇬🇧":   ("🎙️ *Voice News*\n\nChoose number of stories:", "story", "stories"),
        "Русский 🇷🇺":   ("🎙️ *Голосовые новости*\n\nВыберите количество:", "новость", "новостей"),
        "فارسی 🇮🇷":     ("🎙️ *اخبار صوتی*\n\nتعداد خبر:", "خبر", "خبر"),
        "हिन्दी 🇮🇳":    ("🎙️ *आवाज़ समाचार*\n\nसमाचार की संख्या चुनें:", "समाचार", "समाचार"),
        "Türkçe 🇹🇷":    ("🎙️ *Sesli Haberler*\n\nHaber sayısını seçin:", "haber", "haber"),
        "Deutsch 🇩🇪":   ("🎙️ *Sprachnachrichten*\n\nAnzahl wählen:", "Nachricht", "Nachrichten"),
        "Español 🇲🇽":   ("🎙️ *Noticias de Voz*\n\nElige la cantidad:", "noticia", "noticias"),
        "Français 🇫🇷":  ("🎙️ *Actualités Vocales*\n\nChoisissez le nombre:", "actualité", "actualités"),
    }
    hdr, s1, s3 = labels.get(lang, labels["English 🇬🇧"])
    kb = types.InlineKeyboardMarkup(row_width=3)
    kb.add(
        types.InlineKeyboardButton(f"3 {s3}",  callback_data="voice_count_3"),
        types.InlineKeyboardButton(f"5 {s3}",  callback_data="voice_count_5"),
        types.InlineKeyboardButton(f"10 {s3}", callback_data="voice_count_10"),
    )
    bot.send_message(uid, hdr, parse_mode="Markdown", reply_markup=kb)


# ======== مفاتيح البوت ========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEATHER_KEY = os.environ.get("WEATHER_KEY", "")
NEWS_KEY = os.environ.get("NEWS_KEY", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ======== Heroku Auto-Backup / Auto-Restore Config ========
# أنشئ قناة تيليغرام خاصة واجعل البوت أدمناً فيها، ثم ضع ID القناة هنا
BACKUP_CHANNEL_ID   = int(os.environ.get("BACKUP_CHANNEL_ID",   "0"))
# BACKUP_STATE_MSG_ID يُملأ تلقائياً عند تشغيل /setup_backup لأول مرة
BACKUP_STATE_MSG_ID = int(os.environ.get("BACKUP_STATE_MSG_ID", "0"))

# ======== Social Media Config ========
FB_PAGE_TOKEN  = os.environ.get("FB_PAGE_TOKEN", "")
FB_PAGE_ID     = os.environ.get("FB_PAGE_ID", "")
IG_USER_ID     = os.environ.get("IG_USER_ID", "")
IMGBB_API_KEY  = os.environ.get("IMGBB_API_KEY", "")

# bot is shared from bot_legacy via 'from bot_legacy import *' — no duplicate instance

# ════════════════════════════════════════════════════════════════════════
# Monkey-patch bot.send_message: حوّل disable_web_page_preview→link_preview_options
# يلغي تحذيرات DEPRECATION من pyTelegramBotAPI الجديد دون لمس 30+ موضع نداء.
# ════════════════════════════════════════════════════════════════════════
_orig_bot_send_message = bot.send_message

@bot.callback_query_handler(func=lambda c: c.data.startswith("voice_count_"))
def cb_voice_count(call):
    bot.answer_callback_query(call.id)
    uid   = call.from_user.id
    count = int(call.data.split("_")[-1])
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception as _exc:
        _log_exc(_exc)
    _AI_EXECUTOR.submit(send_voice_news, uid, count)


# ======== البودكاست اليومي ========
def send_podcast(uid):
    """يُنشئ حلقة بودكاست يومية كاملة (AI script + TTS)"""
    lang  = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    voice = TTS_VOICES.get(lang, "ar-IQ-BasselNeural")

    if not _TTS_AVAILABLE:
        bot.send_message(uid, _ui("voice_unavailable", lang))
        return

    wait_labels = {
        "العربية 🇮🇶":   "🎧 *جاري تجهيز حلقة البودكاست...*\n\n_قد يستغرق 30-60 ثانية_",
        "English 🇬🇧":   "🎧 *Preparing your podcast episode...*\n\n_This may take 30-60 seconds_",
        "Русский 🇷🇺":   "🎧 *Подготовка подкаста...*\n\n_Подождите 30-60 секунд_",
        "فارسی 🇮🇷":     "🎧 *آماده‌سازی پادکست...*\n\n_ممکن است ۳۰-۶۰ ثانیه طول بکشد_",
        "Türkçe 🇹🇷":    "🎧 *Podcast hazırlanıyor...*\n\n_30-60 saniye sürebilir_",
        "Deutsch 🇩🇪":   "🎧 *Podcast wird vorbereitet...*\n\n_Kann 30-60 Sekunden dauern_",
        "Español 🇲🇽":   "🎧 *Preparando episodio de podcast...*\n\n_Puede tardar 30-60 segundos_",
        "Français 🇫🇷":  "🎧 *Préparation du podcast...*\n\n_Peut prendre 30-60 secondes_",
    }
    wait_msg = bot.send_message(uid,
        wait_labels.get(lang, wait_labels["English 🇬🇧"]), parse_mode="Markdown")

    # ─── جمع الأخبار ───
    feeds = RSS.get(lang, RSS.get("العربية 🇮🇶", []))
    headlines = []
    for feed_url in feeds[:6]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:5]:
                title = getattr(entry, 'title', '').strip()
                if title and len(title) > 15:
                    headlines.append(title)
            if len(headlines) >= 12:
                break
        except Exception as _exc:
            _log_exc(_exc)

    # إزالة المكررة
    unique = []
    for h in headlines:
        if not any(_is_similar_title(h, u) for u in unique):
            unique.append(h)
        if len(unique) >= 8:
            break

    if not unique:
        try:
            bot.edit_message_text(_ui("voice_no_news", lang), uid, wait_msg.message_id)
        except Exception:
            bot.send_message(uid, _ui("voice_no_news", lang))
        return

    # ─── توليد السكريبت بالذكاء الاصطناعي ───
    script = ""
    if _AI_AVAILABLE and _AI_MODEL:
        lang_names = {
            "العربية 🇮🇶": "Arabic", "English 🇬🇧": "English", "Русский 🇷🇺": "Russian",
            "فارسی 🇮🇷": "Persian", "हिन्दी 🇮🇳": "Hindi", "Türkçe 🇹🇷": "Turkish",
            "Deutsch 🇩🇪": "German", "Español 🇲🇽": "Spanish", "Français 🇫🇷": "French",
            "Português 🇧🇷": "Portuguese", "Italiano 🇮🇹": "Italian",
            "اردو 🇵🇰": "Urdu", "Українська 🇺🇦": "Ukrainian",
        }
        wlang = lang_names.get(lang, "Arabic")
        headlines_txt = "\n".join(f"- {h}" for h in unique[:8])
        prompt = (
            f"You are a professional news podcast host. Write a 2-minute podcast episode script "
            f"in {wlang} language, based on these headlines:\n\n{headlines_txt}\n\n"
            f"Rules:\n"
            f"- Start with a warm greeting and today's date\n"
            f"- Cover each headline in 2-3 sentences with context\n"
            f"- Use natural spoken language, NOT formal writing style\n"
            f"- NO markdown, NO asterisks, NO bullet points — plain speech only\n"
            f"- End with a sign-off like 'Thank you for listening' in {wlang}\n"
            f"- Total length: 200-350 words"
        )
        try:
            result_holder = [""]
            def _gen():
                try:
                    _r_ai = _ai_generate(prompt)
                    if _r_ai:
                        result_holder[0] = _r_ai
                except Exception as _exc:
                    _log_exc(_exc)
            _AI_EXECUTOR.submit(_gen).result(timeout=20)
            script = result_holder[0]
        except Exception as _exc:
            _log_exc(_exc)

    # fallback: بدون AI نقرأ العناوين مباشرة
    if not script:
        intros = {
            "العربية 🇮🇶":  "مرحباً بكم في بودكاست عراق ناو. إليكم أبرز أخبار اليوم.",
            "English 🇬🇧":  "Welcome to IraqNow Podcast. Here are today's top stories.",
            "Русский 🇷🇺":  "Добро пожаловать в подкаст. Главные новости дня.",
            "Türkçe 🇹🇷":   "IraqNow Podcast'a hoş geldiniz. İşte günün haberleri.",
            "Deutsch 🇩🇪":  "Willkommen beim IraqNow Podcast. Die wichtigsten Nachrichten.",
            "Español 🇲🇽":  "Bienvenido al Podcast IraqNow. Las noticias de hoy.",
            "Français 🇫🇷": "Bienvenue sur le Podcast IraqNow. Les actualités du jour.",
        }
        outros = {
            "العربية 🇮🇶":  "شكراً لاستماعكم. إلى اللقاء في الحلقة القادمة.",
            "English 🇬🇧":  "Thank you for listening. See you next time.",
            "Русский 🇷🇺":  "Спасибо за прослушивание. До следующего раза.",
            "Türkçe 🇹🇷":   "Dinlediğiniz için teşekkürler. Görüşmek üzere.",
            "Deutsch 🇩🇪":  "Vielen Dank fürs Zuhören. Bis zum nächsten Mal.",
            "Español 🇲🇽":  "Gracias por escuchar. Hasta la próxima.",
            "Français 🇫🇷": "Merci d'avoir écouté. À la prochaine.",
        }
        intro = intros.get(lang, intros["English 🇬🇧"])
        outro = outros.get(lang, outros["English 🇬🇧"])
        sep = {
            "العربية 🇮🇶": ". الخبر التالي: ", "English 🇬🇧": ". Next: ",
            "Русский 🇷🇺": ". Следующее: ", "Türkçe 🇹🇷": ". Sonraki: ",
        }.get(lang, ". Next: ")
        script = intro + " " + sep.join(unique[:6]) + ". " + outro

    # ─── تحويل السكريبت لصوت ───
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        success, err = _tts_generate(script, voice, tmp_path)
        if not success or not os.path.exists(tmp_path):
            err_detail = f"\n\n`{err[:120]}`" if err else ""
            try:
                bot.edit_message_text(
                    f"{_ui('voice_fail', lang)}{err_detail}",
                    uid, wait_msg.message_id, parse_mode="Markdown")
            except Exception:
                bot.send_message(uid, f"{_ui('voice_fail', lang)}{err_detail}", parse_mode="Markdown")
            return

        captions = {
            "العربية 🇮🇶":  f"🎧 *بودكاست عراق ناو — اليوم*\n\n📰 {len(unique)} أخبار مُغطّاة",
            "English 🇬🇧":  f"🎧 *IraqNow Podcast — Today*\n\n📰 {len(unique)} stories covered",
            "Русский 🇷🇺":  f"🎧 *Подкаст IraqNow — Сегодня*\n\n📰 {len(unique)} новостей",
            "Türkçe 🇹🇷":   f"🎧 *IraqNow Podcast — Bugün*\n\n📰 {len(unique)} haber",
            "Deutsch 🇩🇪":  f"🎧 *IraqNow Podcast — Heute*\n\n📰 {len(unique)} Nachrichten",
            "Español 🇲🇽":  f"🎧 *Podcast IraqNow — Hoy*\n\n📰 {len(unique)} noticias",
            "Français 🇫🇷": f"🎧 *Podcast IraqNow — Aujourd'hui*\n\n📰 {len(unique)} actualités",
        }
        caption = captions.get(lang, captions["English 🇬🇧"])

        try:
            bot.delete_message(uid, wait_msg.message_id)
        except Exception as _exc:
            _log_exc(_exc)

        with open(tmp_path, 'rb') as audio:
            bot.send_voice(uid, audio, caption=caption, parse_mode="Markdown")
        try:
            os.unlink(tmp_path)
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        try:
            bot.edit_message_text(
                f"{_ui('voice_fail', lang)}\n\n`{str(e)[:120]}`",
                uid, wait_msg.message_id, parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, f"{_ui('voice_fail', lang)}\n\n`{str(e)[:120]}`", parse_mode="Markdown")


# ─── كالباك زر البودكاست من القائمة الرئيسية ───
def _handle_podcast_btn(uid):
    """يُطلق حلقة البودكاست في خيط منفصل"""
    threading.Thread(target=send_podcast, args=(uid,), daemon=True, name="Podcast").start()


# ======== تتبع عالمي للأخبار المُرسلة لكل لغة ========
# بدلاً من تخزين 500 رابط لكل مستخدم (20 ألف × 500 = 10 مليون رابط)
# نخزن مجموعة واحدة لكل لغة — إذا أُرسل الخبر للغة العربية مرة واحدة لا يُرسل أبداً لأي مستخدم عربي
_GLOBAL_SENT_FILE   = "global_sent_news.json"
_SPORTS_CACHE_FILE  = "sports_match_cache.json"
_global_sent_news = {}          # lang -> {link: timestamp}  (TTL-based)
# FIX-11: _global_sent_lock مُعرَّف في state.py — لا تُعرِّفه هنا (shadow state)
# _global_sent_lock مستورد عبر: from bot_legacy import *
_GLOBAL_SENT_TTL  = 6 * 3600   # FIX: 6 ساعات = نافذة الطزاجة (كان 2h → تعارض مع _TITLE_DEDUP_TTL=24h)
_USER_SENT_TTL    = 6 * 3600   # FIX: 6 ساعات = نافذة الطزاجة (بعدها الخبر يخرج من الـ cache أصلاً)

@bot.message_handler(commands=["podcast"])
def cmd_podcast(m):
    """يُطلق حلقة بودكاست يومية كاملة بالصوت"""
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return
    if _is_rate_limited(uid, "podcast"):
        lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
        bot.send_message(uid, _ui("rate_limited", lang))
        return
    _track_feature(uid, "audio_podcast")
    _handle_podcast_btn(uid)


@bot.message_handler(commands=["audiobriefing"])
def cmd_audiobriefing(m):
    """
    يُرسل ملخص أخبار اليوم الأبرز بصيغة نص منسّق وواضح.
    قابل للتحويل لصوت مستقبلاً عبر TTS.
    """
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    if str(uid) not in users:
        bot.send_message(uid, "⚠️ أرسل /start أولاً.")
        return
    if _is_rate_limited(uid, "audio"):
        bot.send_message(uid, "⏳ انتظر دقيقة قبل طلب موجز آخر.")
        return

    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    wait_msg = bot.send_message(uid,
        "🎙 *جاري تجهيز الموجز الإخباري...*",
        parse_mode="Markdown")

    def _do():
        feeds = RSS.get(lang, [])
        headlines = []
        for feed_url in feeds[:5]:
            try:
                feed = _parse_feed(feed_url)
                if feed is None:
                    import feedparser
                    feed = feedparser.parse(feed_url)
                if not feed:
                    continue
                for item in feed.entries[:4]:
                    title = getattr(item, 'title', '').strip()
                    if title and _title_in_lang(title, lang):
                        headlines.append(title)
                if len(headlines) >= 8:
                    break
            except Exception:
                continue

        if not headlines:
            try:
                bot.edit_message_text("⚠️ لا توجد أخبار متاحة الآن.", uid, wait_msg.message_id)
            except Exception as _exc:
                _log_exc(_exc)
            return

        top = headlines[:6]
        # AI يُنشئ موجزاً صوتياً احترافياً
        script = ""
        if _AI_AVAILABLE and _AI_MODEL:
            lang_map = {"العربية 🇮🇶": "العربية الفصحى", "English 🇬🇧": "English"}
            wlang = lang_map.get(lang, "Arabic")
            try:
                headlines_txt = "\n".join(f"- {h}" for h in top)
                prompt = (
                    f"أنت مذيع أخبار محترف. اكتب موجزاً إخبارياً باللغة {wlang} "
                    "بأسلوب احترافي وواضح يُقرأ خلال دقيقتين، بناءً على هذه العناوين:\n\n"
                    f"{headlines_txt}\n\n"
                    "ابدأ بـ 'مرحباً، هذا موجزكم الإخباري.' وأنهِ بـ 'وهذا كان موجزكم الإخباري.'"
                )
                _h_result = _ai_generate(prompt, timeout=10)
                script = _h_result
            except Exception as _exc:
                _log_exc(_exc)

        if not script:
            nums = ["١","٢","٣","٤","٥","٦"]
            script = "📻 *موجزكم الإخباري:*\n\n" + "\n\n".join(
                f"{nums[i] if i < len(nums) else str(i+1)}. {h}" for i, h in enumerate(top)
            )

        sep = "━━━━━━━━━━━━━━"
        reply = f"🎙 *الموجز الإخباري*\n{sep}\n\n{script}\n\n{sep}\n_للحصول على الموجز الصوتي تابع التحديثات القادمة_"
        try:
            bot.edit_message_text(reply, uid, wait_msg.message_id, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(uid, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== /subscribe — الاشتراك المميز عبر الإحالات أو الدفع ========
