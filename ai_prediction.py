# -*- coding: utf-8 -*-
"""
  ai_prediction.py — التنبؤ بالأحداث + تنبيه اقتصادي + ملخص برلمان

  يُصدِّر دوال التنبؤ والتنبيهات الاقتصادية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _ai_predict_events(topic: str) -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "predict")
    related = []
    for feed_url in list(RSS.get("العربية 🇮🇶", []))[:8]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:10]:
                title = getattr(entry, 'title', '')
                if any(w.lower() in title.lower() for w in topic.split() if len(w) > 3):
                    related.append(title)
        except Exception as _exc:
            _log_exc(_exc)
    context = "\n".join(related[:10]) if related else ""
    _ctx_predict = ('أخبار حديثة ذات صلة:\n' + '\n'.join(related[:10])) if related else ''
    prompt = f"""أنت خبير تحليلي استراتيجي. بناءً على الأنماط الحالية، توقع ما سيحدث بخصوص: {topic}

{_ctx_predict}

قدم تنبؤات واضحة ومحددة:
🔮 **خلال 48 ساعة:**
📅 **خلال أسبوع:**
🗓️ **خلال شهر:**
⚡ **أعلى سيناريو خطورة:**
✅ **أفضل سيناريو:**

نسبة الثقة لكل تنبؤ (%)."""
    try:
        _response_ai = _ai_generate(prompt)
        return (_response_ai or "")[:1200]
    except Exception as e:
        return _ai_friendly_error(e, "predict")

# ─── 5. إنذار اقتصادي ذكي ──────────────────────────────────────
def _check_economic_alerts():
    """يراقب مؤشرات اقتصادية ويرسل إنذارات ذكية"""
    try:
        now = time.time()
        alerts = []
        # أسعار النفط
        try:
            r = requests.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1d&range=2d",
                timeout=8, headers={"User-Agent": "Mozilla/5.0"}
            )
            if r.status_code == 200:
                data = r.json()
                closes = data["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
                closes = [c for c in closes if c]
                if len(closes) >= 2:
                    change_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
                    if abs(change_pct) >= 3:
                        direction = "📉 هبط" if change_pct < 0 else "📈 ارتفع"
                        last_alert = _econ_last_alert.get("oil", 0)
                        if now - last_alert > 3600:
                            _econ_last_alert["oil"] = now
                            alerts.append(
                                f"🛢️ *تحذير نفطي*\n"
                                f"سعر خام النفط {direction} `{change_pct:+.1f}%`\n"
                                f"السعر الحالي: `${closes[-1]:.1f}`\n\n"
                                f"⚠️ قد يؤثر على الموازنة العراقية"
                            )
        except Exception as _exc:
            _log_exc(_exc)
        # الدولار مقابل الدينار (من البنك المركزي أو مصدر بديل)
        try:
            r = requests.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=8
            )
            if r.status_code == 200:
                rates = r.json().get("rates", {})
                iqd = rates.get("IQD", 0)
                if iqd and (iqd < 1290 or iqd > 1330):
                    last_alert = _econ_last_alert.get("usd_iqd", 0)
                    if now - last_alert > 7200:
                        _econ_last_alert["usd_iqd"] = now
                        status = "منخفض ⬇️" if iqd < 1290 else "مرتفع ⬆️"
                        alerts.append(
                            f"💵 *تحذير صرف*\n"
                            f"الدولار مقابل الدينار: `{iqd:,.0f}` — {status}\n"
                            f"⚠️ خارج النطاق الرسمي (1290-1330)"
                        )
        except Exception as _exc:
            _log_exc(_exc)
        # إرسال التحذيرات للمشتركين
        if alerts:
            for uid_s, info in list(users.items()):
                try:
                    if info.get("notifications", True) and info.get("alert_level", "medium") in ("high", "critical"):
                        for alert in alerts:
                            bot.send_message(int(uid_s), alert, parse_mode="Markdown")
                except Exception as _exc:
                    _log_exc(_exc)
            try:
                for alert in alerts:
                    bot.send_message(ADMIN_ID, alert, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)
    except Exception as _exc:
        _log_exc(_exc)

# ─── 6. تلخيص جلسات البرلمان ───────────────────────────────────
def _get_parliament_summary() -> str:
    if not _AI_MODEL:
        return _ai_friendly_error(Exception("AI غير متاح"), "")
    cached = _parliament_cache
    if time.time() - cached.get("timestamp", 0) < 1800:
        return cached.get("text", "")
    news_items = []
    parliament_feeds = [
        "https://www.parliament.iq/feed/",
        "https://www.ina.iq/rss.php",
    ]
    for url in parliament_feeds:
        try:
            feed = _parse_feed(url)
            if feed:
                for entry in feed.entries[:10]:
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '') or ''
                    if title:
                        news_items.append(f"• {title}: {summary[:100]}")
        except Exception as _exc:
            _log_exc(_exc)
    # جرّب السكرابنق
    if not news_items and _BS4_AVAILABLE:
        try:
            items = _scrape_news_site("https://www.parliament.iq/", "https://www.parliament.iq", max_items=8)
            news_items = [f"• {t}" for t, _ in items]
        except Exception as _exc:
            _log_exc(_exc)
    if not news_items:
        news_items = ["لا تتوفر بيانات مباشرة من موقع البرلمان"]
    prompt = f"""لخّص آخر أخبار البرلمان العراقي في 5 نقاط مختصرة وواضحة:

المعلومات المتاحة:
{chr(10).join(news_items[:15])}

الشكل المطلوب:
🏛️ **ملخص جلسة البرلمان**
1. ...
2. ...
3. ...
4. ...
5. ..."""
    try:
        _response_ai = _ai_generate(prompt)
        result = (_response_ai or "")[:1000]
        _parliament_cache["text"] = result
        _parliament_cache["timestamp"] = time.time()
        return result
    except Exception as e:
        return _ai_friendly_error(e, "parliament")

# ─── 7. خريطة النفوذ السياسي ───────────────────────────────────
def handle_predict_cmd(message):
    uid = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    topic = message.text.replace('/predict', '').strip()
    if not topic:
        bot.send_message(message.chat.id, _ui("cmd_predict_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id,
        _ui("cmd_predict_loading", lang).format(topic=topic), parse_mode="Markdown")
    result = _ai_predict_events(topic)
    reply = f"{_ui('cmd_predict_hdr', lang).format(topic=topic)}\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")

@bot.message_handler(commands=['parliament'])
def handle_parliament_cmd(message):
    uid = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    msg = bot.send_message(message.chat.id, _ui("cmd_parliament_loading", lang))
    result = _get_parliament_summary()
    try:
        bot.edit_message_text(result[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, result[:4096], parse_mode="Markdown")

@bot.message_handler(commands=["econ"])
def handle_econ_cmd(message):
    if not _FF.get("economy", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    msg = bot.send_message(message.chat.id, _ui("cmd_econ_loading", lang))
    lines = [_ui("cmd_econ_hdr", lang) + "\n"]
    # النفط
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1d&range=2d",
                         timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes = [c for c in closes if c]
            if len(closes) >= 2:
                chg = (closes[-1] - closes[-2]) / closes[-2] * 100
                icon = "📈" if chg > 0 else "📉"
                lines.append(f"{_ui('cmd_econ_oil', lang)} `${closes[-1]:.1f}` {icon} `{chg:+.1f}%`")
    except Exception:
        lines.append("🛢️ النفط: غير متاح")
    # الذهب
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=2d",
                         timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes = [c for c in closes if c]
            if len(closes) >= 2:
                chg = (closes[-1] - closes[-2]) / closes[-2] * 100
                icon = "📈" if chg > 0 else "📉"
                lines.append(f"{_ui('cmd_econ_gold', lang)} `${closes[-1]:.0f}` {icon} `{chg:+.1f}%`")
    except Exception as _exc:
        _log_exc(_exc)
    # الدولار
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=8)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            iqd = rates.get("IQD", 0)
            if iqd:
                status = _ui("cmd_econ_normal", lang) if 1290 <= iqd <= 1330 else _ui("cmd_econ_abnormal", lang)
                lines.append(f"{_ui('cmd_econ_dollar', lang)} `{iqd:,.0f}` {status}")
    except Exception as _exc:
        _log_exc(_exc)
    if _AI_MODEL and len(lines) > 1:
        try:
            econ_text = "\n".join(lines[1:])
            prompt = f"""بناءً على هذه المؤشرات الاقتصادية، قدم تحليلاً مختصراً لأثرها على العراق:
{econ_text}
جملتان فقط، مباشرة."""
            _resp_ai = _ai_generate(prompt)
            lines.append(f"\n{_ui('cmd_econ_ai_analysis', lang)} {(_resp_ai or '')[:200]}")
        except Exception as _exc:
            _log_exc(_exc)
    reply = "\n".join(lines)
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")


