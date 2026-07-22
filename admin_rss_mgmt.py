# -*- coding: utf-8 -*-
"""
  admin_rss_mgmt.py — إضافة/حذف/تحقق RSS feeds

  يُصدِّر دوال إدارة مصادر RSS من لوحة الأدمن.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def save_rss():
    save_json(RSS_FILE, RSS)

# ======== نظام الاكتشاف التلقائي لمصادر RSS الجديدة ========
# قائمة مرشحين يتم التحقق منهم تدريجياً ثم إضافتهم إن كانوا صالحين
_RSS_CANDIDATES = {
    "العربية 🇮🇶": [
        "https://www.alqabas.com/feed/", "https://www.alraimedia.com/rss.xml",
        "https://www.alhurra.com/api/zrqomtmopp", "https://arabi21.com/rss.xml",
        "https://www.noonpost.com/feed", "https://www.zawya.com/rss/mena-news.rss",
        "https://www.alaraby.co.uk/rss.xml", "https://www.alquds.com/feed/",
        "https://www.24.ae/rss/", "https://www.khaleejionline.com/feed/",
        "https://www.aawsat.com/rss.xml", "https://www.elaph.com/rss/",
        "https://www.al-monitor.com/rss.xml", "https://www.huffpostarabi.com/feed/",
        "https://www.almanar.com.lb/rss", "https://www.presstv.ir/Arabic/rss.xml",
        "https://arabic.cnn.com/api/feed/rss", "https://www.majalla.com/feed",
        "https://www.middleeasteye.net/ar/rss", "https://www.raya.com/rss/",
        "https://www.alriyadh.com/rss.xml", "https://www.okaz.com.sa/rss",
        "https://www.aleqt.com/rss.xml", "https://www.makkahnewspaper.com/rss",
        "https://www.albayan.ae/rss.xml", "https://www.alittihad.ae/rss",
        "https://www.emaratalyoum.com/rss.xml", "https://www.khaleejionline.com/feed/",
    ],
    "English 🇬🇧": [
        "https://www.middleeasteye.net/rss", "https://www.al-monitor.com/rss.xml",
        "https://www.arabnews.com/rss.xml", "https://thenational.ae/rss.xml",
        "https://www.haaretz.com/cmlink/1.4102581", "https://www.timesofisrael.com/feed/",
        "https://www.presstv.ir/rss.xml", "https://www.iraqoil.co.uk/rss.xml",
        "https://menas.co.uk/blog/rss/", "https://www.rudaw.net/english/rss",
        "https://www.benarnews.org/english/rss", "https://carnegieendowment.org/rss",
        "https://theintercept.com/feed/rss", "https://foreignpolicy.com/rss",
        "https://www.atlanticcouncil.org/feed", "https://lobelog.com/feed/",
        "https://www.mei.edu/rss.xml", "https://www.crisisgroup.org/rss.xml",
        "https://www.juancole.com/feed", "https://www.axios.com/feeds/feed.rss",
    ],
    "Türkçe 🇹🇷": [
        "https://www.milligazete.com.tr/rss", "https://www.ensonhaber.com/rss",
        "https://www.turkiyegazetesi.com.tr/rss.aspx", "https://www.timeturk.com/rss/haber.xml",
        "https://www.haber7.com/rss", "https://www.gzt.com/rss",
        "https://www.yeniakit.com.tr/rss.xml", "https://www.aksam.com.tr/rss.xml",
    ],
    "فارسی 🇮🇷": [
        "https://www.bbc.com/persian/rss.xml", "https://www.voanews.com/api/zmpqqou_ypq",
        "https://www.dw.com/rdf/rss-per-all", "https://www.radiofarda.com/api/zpqovumymr",
        "https://www.shargh.news/rss.xml", "https://www.hamshahri.net/rss",
    ],
    "Русский 🇷🇺": [
        "https://www.novayagazeta.ru/rss/all.xml", "https://meduza.io/rss/all",
        "https://www.fontanka.ru/fontanka.rss", "https://www.ng.ru/rss/",
        "https://www.polit.ru/p/rss.xml", "https://www.echo.msk.ru/interview.rss",
    ],
    "हिन्दी 🇮🇳": [
        "https://www.bhaskar.com/rss-feed/1061/", "https://www.amarujala.com/rss/breaking-news.xml",
        "https://www.zeenews.india.com/hindi/rss/top-stories.xml",
        "https://www.tv9hindi.com/feed", "https://ndtv.in/rss/top-stories",
        "https://www.jagran.com/rss/news-national.xml",
        "https://www.livehindustan.com/rss/topnews.xml",
        "https://www.patrika.com/rss/news.xml",
        "https://www.punjabkesari.in/rss.xml",
        "https://www.jansatta.com/feed/",
        "https://hindi.news18.com/commonfeeds/v1/hin/rss/india.xml",
        "https://www.abplive.in/top/feed/",
    ],
    "Português 🇧🇷": [
        "https://g1.globo.com/rss/g1/mundo/", "https://www.uol.com.br/rss.xml",
        "https://www.folha.uol.com.br/fsp/poder/rss091.xml",
        "https://veja.abril.com.br/feed/", "https://www.correiobraziliense.com.br/rss/",
        "https://www.estadao.com.br/feed/", "https://www.gazetadopovo.com.br/feed/",
        "https://noticias.uol.com.br/rss.htm", "https://www.terra.com.br/rss/",
        "https://www.istoedinheiro.com.br/feed/",
        "https://www.jornalodia.com.br/feed/",
        "https://www.valor.com.br/rss/", "https://www.poder360.com.br/feed/",
        "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
        "https://g1.globo.com/rss/g1/", "https://www.record.pt/feed/",
        "https://www.publico.pt/api/notifications/rss/latest",
        "https://www.dn.pt/rss/", "https://www.cmjornal.pt/rss",
        "https://expresso.pt/rss", "https://www.jn.pt/rss/",
        "https://rr.sapo.pt/rss/rss.aspx", "https://www.rtp.pt/noticias/rss",
    ],
    "اردو 🇵🇰": [
        "https://www.dawn.com/feeds/home", "https://www.geo.tv/rss",
        "https://arynews.tv/feed/", "https://www.thenews.com.pk/rss/1/8",
        "https://www.express.com.pk/feed/", "https://www.jang.com.pk/rss",
        "https://www.bbc.com/urdu/rss.xml",
        "https://www.samaadigital.com/feed/", "https://www.dailypakistan.com.pk/feed/",
        "https://naiatv.com/feed/", "https://92newshd.tv/feed/",
        "https://www.pakobserver.net/feed/", "https://dunyanews.tv/rss/",
        "https://www.bolnews.com/feed/", "https://www.voiceofamerica.com/api/epiqq",
        "https://urdu.geo.tv/rss", "https://urdunews.com/feed/",
        "https://www.dw.com/rdf/rss-urd-all",
    ],
    "Deutsch 🇩🇪": [
        "https://www.spiegel.de/schlagzeilen/index.rss",
        "https://www.tagesschau.de/xml/rss2",
        "https://www.welt.de/feeds/latest.rss", "https://www.faz.net/rss/aktuell/",
        "https://www.sueddeutsche.de/rss", "https://www.stern.de/feed",
        "https://www.focus.de/rss/news/", "https://www.n-tv.de/rss",
        "https://www.zdf.de/rss/zdf/zdf-heute-100.xml",
        "https://www.handelsblatt.com/contentexport/feed/politik",
        "https://www.tagesspiegel.de/contentexport/feed/politik",
        "https://www.zeit.de/politik/index.xml",
        "https://www.bild.de/rssfeeds/rss3-20196/politik-42521432,dzbildplus=false,sort=1,teaserbildmobil=false,view=rss2.bild.xml",
        "https://www.heise.de/rss/heise-top-atom.xml",
        "https://www.br.de/nachrichten/index.rss",
        "https://www.swr.de/nachrichten/feed.rss",
        "https://www.ndr.de/nachrichten/ndr_nachrichten_aktuell.rss",
    ],
    "Українська 🇺🇦": [
        "https://www.ukrinform.ua/rss/block-lastnews",
        "https://www.unian.ua/rss", "https://www.pravda.com.ua/rss/",
        "https://interfax.com.ua/news/general/rss.xml",
        "https://ua.korrespondent.net/rss/",
        "https://www.segodnya.ua/rss/all.xml",
        "https://www.obozrevatel.com/news.rss",
        "https://www.liga.net/rss/news.rss", "https://www.nv.ua/rss/all.xml",
        "https://www.epravda.com.ua/rss/", "https://www.slovoidilo.ua/rss",
        "https://www.radiosvoboda.org/api/zpqpmkez",
        "https://www.dw.com/rdf/rss-uk-all",
        "https://www.bbc.com/ukrainian/index.xml",
        "https://www.currenttime.tv/api/zrqomtmopp",
    ],
    "Italiano 🇮🇹": [
        "https://www.corriere.it/rss/homepage.xml",
        "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
        "https://www.ilpost.it/feed/", "https://www.lastampa.it/rss",
        "https://www.sole24ore.com/rss/mondo.xml",
        "https://www.ilgiornale.it/node/feed", "https://www.tgcom24.mediaset.it/rss/",
        "https://www.agi.it/feed/", "https://www.rainews.it/dl/rainews/media/NewsRss.xml",
        "https://www.liberoquotidiano.it/rss.xml",
        "https://www.adnkronos.com/feed.rss", "https://www.huffingtonpost.it/feed/",
        "https://www.fanpage.it/feed/", "https://www.open.online/feed/",
        "https://www.ilmessaggero.it/rss/", "https://www.quotidiano.net/rss/",
    ],
    "Español 🇲🇽": [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://www.elmundo.es/rss/portada.xml",
        "https://www.lavanguardia.com/rss/home.xml",
        "https://www.20minutos.es/rss/", "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",
        "https://www.jornada.com.mx/rss", "https://www.milenio.com/rss",
        "https://www.eluniversal.com.mx/rss.xml", "https://www.proceso.com.mx/?feed=rss2",
        "https://www.excelsior.com.mx/rss.xml",
        "https://www.clarin.com/rss/lo-ultimo/", "https://www.infobae.com/feeds/rss/",
        "https://www.emol.com/rss/", "https://www.latercera.com/feed/",
        "https://www.eltiempo.com/rss/mundo.xml",
        "https://www.semana.com/rss/", "https://www.lanacion.com.ar/arcio/rss/",
        "https://www.pagina12.com.ar/rss/portada",
        "https://www.bbc.com/mundo/index.xml",
        "https://rss.dw.com/rdf/rss-spa-all",
        "https://www.france24.com/es/rss", "https://www.aa.com.tr/es/rss/default",
    ],
    "Français 🇫🇷": [
        "https://www.lemonde.fr/rss/une.xml",
        "https://www.lefigaro.fr/rss/figaro_international.xml",
        "https://www.liberation.fr/arc/outboundfeeds/rss",
        "https://www.bfmtv.com/rss/news-24-7/",
        "https://www.lapresse.ca/actualites/rss",
        "https://www.lepoint.fr/rss.xml", "https://www.lexpress.fr/rss/alaune.xml",
        "https://www.europe1.fr/rss.xml", "https://www.rfi.fr/fr/rss",
        "https://www.tv5monde.com/rss/info.xml",
        "https://www.20minutes.fr/rss/une.xml",
        "https://www.lci.fr/rss/", "https://www.mediapart.fr/articles/feed",
        "https://feeds.leparisien.fr/leparisien/rss",
        "https://www.francetvinfo.fr/titres.rss",
        "https://www.france24.com/fr/rss", "https://www.rts.ch/rss/info/",
        "https://www.rtbf.be/info/rss/feed/", "https://www.24heures.ch/rss.xml",
        "https://www.tdg.ch/rss.xml", "https://www.lapress.ca/rss.xml",
        "https://www.dw.com/rdf/rss-fra-all",
    ],
}

_RSS_DISCOVERY_STATE_FILE = "rss_discovery_state.json"
_rss_discovery_state = load_json(_RSS_DISCOVERY_STATE_FILE, {})

def rss_add_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    lines = message.text.strip().split("\n", 1)
    if len(lines) < 2:
        bot.send_message(uid, "❌ أرسل اللغة ثم الرابط في سطرين.")
        return
    lang, url = lines[0].strip(), lines[1].strip()
    # محاولة اكتشاف تلقائي إذا لم يبدُ الرابط وكأنه RSS مباشر
    bot.send_message(uid, f"🔍 يجرب الرابط ويكتشف إذا كان RSS...")
    discovered = _auto_discover_rss(url)
    if not discovered:
        bot.send_message(uid, f"❌ لم أستطع التحقق من الرابط كمصدر RSS صالح:\n`{url}`\n\nتأكد أنه يُرجع محتوى XML/RSS.", parse_mode="Markdown")
        return
    if lang not in RSS:
        RSS[lang] = []
    if discovered in RSS.get(lang, []):
        bot.send_message(uid, f"⚠️ المصدر موجود مسبقاً:\n`{discovered}`", parse_mode="Markdown")
        return
    RSS[lang].append(discovered)
    save_rss()
    diff = f"\n_(تم اكتشافه تلقائياً من: `{url}`)_" if discovered != url else ""
    bot.send_message(uid,
        f"✅ *تم إضافة المصدر بنجاح!*\n`{discovered}`{diff}\n\n📡 مصادر {lang}: *{len(RSS[lang])}*",
        parse_mode="Markdown"
    )

def rss_bulk_add_step(message):
    if not is_admin(message.from_user.id):
        return
    lines = [l.strip() for l in message.text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        bot.send_message(message.from_user.id, "❌ أرسل اللغة في السطر الأول ثم الروابط في الأسطر التالية.")
        return
    lang = lines[0]
    urls = [l for l in lines[1:] if l.startswith("http")]
    skipped = [l for l in lines[1:] if not l.startswith("http")]
    if not urls:
        bot.send_message(message.from_user.id, "❌ لم أجد روابط صحيحة (يجب أن تبدأ بـ http).")
        return
    if lang not in RSS:
        RSS[lang] = []
    added = []
    duplicates = []
    for url in urls:
        if url in RSS[lang]:
            duplicates.append(url)
        else:
            RSS[lang].append(url)
            added.append(url)
    save_rss()
    report = f"✅ *تمت إضافة {len(added)} مصدر لـ {lang}*\n\n"
    if added:
        report += "➕ *المضافة:*\n" + "\n".join(f"`{u}`" for u in added) + "\n\n"
    if duplicates:
        report += f"⚠️ *مكررة (تجاهلتها):* {len(duplicates)}\n"
    if skipped:
        report += f"❌ *أسطر غير صالحة:* {len(skipped)}\n"
    report += f"\n📡 إجمالي مصادر {lang}: *{len(RSS[lang])}*"
    bot.send_message(message.from_user.id, report, parse_mode="Markdown")

def rss_remove_step(message):
    if not is_admin(message.from_user.id):
        return
    lines = message.text.split("\n", 1)
    if len(lines) < 2:
        bot.send_message(message.from_user.id, "❌ أرسل اللغة ثم رقم المصدر في سطرين.")
        return
    lang = lines[0].strip()
    try:
        index = int(lines[1].strip()) - 1
        if lang in RSS and 0 <= index < len(RSS[lang]):
            removed = RSS[lang].pop(index)
            save_rss()
            bot.send_message(message.from_user.id, f"✅ تم حذف المصدر:\n{removed}")
        else:
            bot.send_message(message.from_user.id, "❌ رقم أو لغة غير صحيحة.")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=["addrss"])
def cmd_addrss(m):
    uid = m.from_user.id
    if uid in banned: return
    user = users.get(str(uid), {})
    lang = user.get("lang", "العربية 🇮🇶")

    if not _check_and_consume_feature(uid, "custom_rss"):
        bot.send_message(uid, _get_limit_msg(lang, "custom_rss")); return

    url = m.text.strip()[len("/addrss"):].strip()
    if not url or not url.startswith("http"):
        bot.send_message(uid,
            "📰 *إضافة مصدر RSS مخصص*\n\n"
            "أرسل: `/addrss <رابط RSS>`\n\n"
            "مثال: `/addrss https://example.com/feed.xml`",
            parse_mode="Markdown"); return

    uid_str = str(uid)
    _custom_rss_store.setdefault(uid_str, [])
    if len(_custom_rss_store[uid_str]) >= 5:
        bot.send_message(uid, "⚠️ وصلت للحد الأقصى (5 مصادر). احذف مصدراً أولاً بـ /delrss")
        return
    if any(f["url"] == url for f in _custom_rss_store[uid_str]):
        bot.send_message(uid, "⚠️ هذا المصدر موجود مسبقاً."); return

    # فحص صحة الرابط
    wait = bot.send_message(uid, "🔍 جاري فحص المصدر...")
    def _check():
        try:
            import feedparser
            fd = feedparser.parse(url)
            if fd and fd.entries:
                name = fd.feed.get("title", url[:30])
                _custom_rss_store[uid_str].append({"url": url, "name": name, "added_ts": time.time()})
                _save_custom_rss()
                bot.edit_message_text(
                    f"✅ *تم إضافة المصدر:*\n📰 _{name}_\n\n"
                    f"ستصلك أخباره مع الأخبار العادية.",
                    uid, wait.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("⚠️ الرابط لا يحتوي على محتوى RSS صالح.",
                                      uid, wait.message_id)
        except Exception:
            bot.edit_message_text("⚠️ تعذّر الاتصال بالمصدر. تحقق من الرابط.",
                                  uid, wait.message_id)
    threading.Thread(target=_check, daemon=True).start()


@bot.message_handler(commands=["myrss"])
def cmd_myrss(m):
    uid     = m.from_user.id
    uid_str = str(uid)
    feeds   = _custom_rss_store.get(uid_str, [])
    if not feeds:
        bot.send_message(uid,
            "📰 لا يوجد مصادر مخصصة.\nأضف مصدراً بـ `/addrss <رابط>`",
            parse_mode="Markdown"); return

    markup = types.InlineKeyboardMarkup(row_width=1)
    lines  = ["📰 *مصادرك المخصصة:*\n━━━━━━━━━━━━━━"]
    for i, f in enumerate(feeds):
        lines.append(f"\n{i+1}. _{f['name'][:50]}_")
        markup.add(types.InlineKeyboardButton(
            f"🗑 حذف {i+1}. {f['name'][:25]}", callback_data=f"delrss_{i}"))
    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("delrss_"))
def cb_delrss(call):
    uid     = call.from_user.id
    uid_str = str(uid)
    try:
        idx   = int(call.data[len("delrss_"):])
        feeds = _custom_rss_store.get(uid_str, [])
        if 0 <= idx < len(feeds):
            removed = feeds.pop(idx)
            _save_custom_rss()
            bot.answer_callback_query(call.id, f"✅ حذف: {removed['name']}", show_alert=True)
            try: bot.delete_message(uid, call.message.message_id)
            except Exception as _exc:
                _log_exc(_exc)
        else:
            bot.answer_callback_query(call.id, "⚠️ المصدر غير موجود.")
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ خطأ.")


@bot.message_handler(commands=["delrss"])
def cmd_delrss(m):
    uid = m.from_user.id
    bot.send_message(uid, "📰 أرسل /myrss لعرض قائمة مصادرك ثم اضغط حذف.")


# ── /track /untrack /mytracks — تتبع كيان ─────────────────────────────────
