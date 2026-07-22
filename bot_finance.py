# -*- coding: utf-8 -*-
# bot_finance.py — العملات والأصول المالية والرسوم البيانية

def convert_currency_msg(uid, amount, from_currency):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        r = requests.get(url, timeout=10).json()
        rates = r.get("rates", {})
        if not rates:
            bot.send_message(uid, f"⚠️ عملة غير مدعومة: {from_currency}")
            return
        targets = ["USD", "EUR", "IQD", "SAR", "AED", "GBP", "TRY", "KWD", "EGP", "RUB"]
        msg = f"🔄 *تحويل {amount:,.2f} {from_currency}*\n━━━━━━━━━━━━━━━\n\n"
        for t in targets:
            if t == from_currency:
                continue
            rate = rates.get(t)
            if rate:
                converted = amount * rate
                label = CURRENCY_SYMBOLS.get(t, t)
                msg += f"{label}: *{converted:,.2f}*\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, "⚠️ لا يمكن جلب أسعار الصرف الآن.")
        notify_admin_error(f"خطأ في محوّل العملات: {e}")

# ======== إحصائيات المستخدم الشخصية ========

def send_crypto_prices(uid):
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,binancecoin,solana,ripple,dogecoin,cardano,tron,litecoin,the-open-network,notcoin,pepe,dogwifcoin,bittensor&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(url, timeout=10).json()
        crypto_names = {
            "bitcoin":          ("₿ Bitcoin",  "BTC"),
            "ethereum":         ("⟠ Ethereum", "ETH"),
            "tether":           ("💵 Tether",   "USDT"),
            "binancecoin":      ("🟡 BNB",      "BNB"),
            "solana":           ("◎ Solana",    "SOL"),
            "ripple":           ("〇 XRP",       "XRP"),
            "dogecoin":         ("🐶 Dogecoin", "DOGE"),
            "cardano":          ("🔵 Cardano",  "ADA"),
            "tron":             ("🔴 TRON",     "TRX"),
            "litecoin":         ("🥈 Litecoin", "LTC"),
            "the-open-network": ("💎 TON",      "TON"),
            "notcoin":          ("🎮 NOT",      "NOT"),
            "pepe":             ("🐸 PEPE",     "PEPE"),
            "dogwifcoin":       ("🐕 WIF",      "WIF"),
            "bittensor":        ("🧠 TAO",      "TAO"),
        }
        msg = t(lang, "crypto_header")
        for coin_id, (name, symbol) in crypto_names.items():
            data = r.get(coin_id, {})
            price = data.get("usd", "—")
            change = data.get("usd_24h_change", None)
            if isinstance(price, (int, float)):
                price_str = f"${price:,.6f}" if price < 0.01 else (f"${price:,.4f}" if price < 1 else f"${price:,.2f}")
            else:
                price_str = "—"
            if change is not None:
                arrow = "📈" if change >= 0 else "📉"
                change_str = f"{arrow} {change:+.2f}%"
            else:
                change_str = ""
            msg += f"{name} ({symbol})\n   💲 {price_str}  {change_str}\n\n"
        msg += t(lang, "crypto_footer")
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "crypto_error"))
        notify_admin_error(f"خطأ في أسعار الكريبتو: {e}")

# ======== أوقات الصلاة ========

def get_asset_label(symbol):
    """اسم وصفي للرمز إن وُجد."""
    if symbol in YAHOO_SYMBOLS:
        return f"{symbol} ({YAHOO_SYMBOLS[symbol]})"
    return symbol

def fetch_asset_price(symbol):
    """جلب سعر أي أصل: عملة رقمية / فيات / سهم / سلعة / مؤشر."""
    if symbol in CRYPTO_IDS:
        try:
            cg_id = CRYPTO_IDS[symbol]
            r = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
                timeout=10
            ).json()
            price = r.get(cg_id, {}).get("usd")
            return float(price) if price else None
        except Exception:
            return None
    if symbol in FIAT_CURRENCIES:
        try:
            r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=10).json()
            rate = r.get("rates", {}).get(symbol)
            return float(rate) if rate else None
        except Exception:
            return None
    # أسهم وسلع ومؤشرات عبر Yahoo Finance
    try:
        encoded = requests.utils.quote(symbol, safe='')
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1d&range=1d",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10
        ).json()
        result = r.get("chart", {}).get("result")
        if result:
            closes = result[0]["indicators"]["quote"][0].get("close", [])
            price = next((p for p in reversed(closes) if p is not None), None)
            return float(price) if price else None
    except Exception as _exc:
        _log_exc(_exc)
    return None

def format_asset_price(symbol, price):
    """تنسيق عرض السعر حسب حجمه."""
    label = get_asset_label(symbol)
    if price is None:
        return f"❓ {label}: غير متوفر"
    if price >= 10000:
        return f"`{label}`: `${price:,.0f}`"
    elif price >= 1:
        return f"`{label}`: `${price:,.2f}`"
    elif price >= 0.0001:
        return f"`{label}`: `${price:.6f}`"
    else:
        return f"`{label}`: `${price:.8f}`"

def start_track_asset(uid):
    user_data = tracked_assets.get(str(uid), {})
    assets = user_data.get("assets", [])
    last_prices = user_data.get("last_prices", {})
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")

    msg = t(lang, "track_header")

    if assets:
        msg += t(lang, "track_current_list")
        for sym in assets:
            p = last_prices.get(sym)
            msg += f"  • {format_asset_price(sym, p)}\n"
        msg += t(lang, "track_count").format(count=len(assets))

    msg += (
        "➕ *لإضافة رمز:* أرسل اسمه مباشرة\n\n"
        "💎 *عملات رقمية (Cryptos):*\n"
        "`BTC` `ETH` `SOL` `BNB` `XRP` `DOGE` `ADA` `MATIC` `LINK` `UNI`\n"
        "`SHIB` `PEPE` `TRX` `TON` `WIF` `BONK` `LUNA` `AVAX` `DOT` `XLM`\n"
        "`FIL` `FTM` `SAND` `APE` `MANA` `CRO` `NEAR` `ALGO` `VET`\n\n"
        "💱 *عملات فيات (Fiat):*\n"
        "`USD` `EUR` `GBP` `IQD` `SAR` `AED` `TRY` `IRR` `KWD` `EGP` `INR` `RUB`\n\n"
        "📈 *أسهم (Stocks):*\n\n"
        "تقنية / تكنولوجيا:\n"
        "`AAPL` `MSFT` `GOOGL` `AMZN` `META` `TSLA` `NVDA` `INTEL` `AMD` `IBM` `CISCO` `ORACLE` `ADOBE` `SALESFORCE`\n\n"
        "بنوك ومالية:\n"
        "`JPM` `BAC` `C` `CFG` `GS` `MS` `WFC` `HSBC` `BARCLAYS` `DEUTSCHE` `CREDITBNP`\n\n"
        "صناعة / طاقة:\n"
        "`XOM` `CVX` `BP` `TOT` `GE` `BOEING` `CAT` `SIEMENS` `HONEYWELL` `LOCKHEED`\n\n"
        "مستهلك / خدمات:\n"
        "`KO` `PEP` `MCD` `SBUX` `WMT` `NKE` `ADS` `LVMH` `UNILEVER` `NESTLE`\n\n"
        "رعاية صحية / أدوية:\n"
        "`PFE` `JNJ` `MRNA` `ROCHE` `NOV` `NVS` `MRK` `AZN` `LLY` `SNY`\n\n"
        "🏅 *سلع ومؤشرات (Commodities & Indices):*\n"
        "`GC=F` (Gold)  `SI=F` (Silver)\n"
        "`CL=F` (WTI)  `BZ=F` (Brent)\n"
        "`^GSPC` (S&P500)  `^IXIC` (NASDAQ)\n\n"
        "🔔 ستصلك تنبيهات فورية عند تغير ±1% وقائمة بأسعارك كل ساعة.\n\n"
        "❌ لحذف رمز: `/removetrack [رمز]`\n"
        "📋 لعرض قائمتك: `/mytrack`"
    )

    user_states[uid] = "tracking_asset"
    bot.send_message(uid, msg, parse_mode="Markdown")

def check_asset_tracking():
    if bot_paused: return
    """يعمل كل ساعة: يرسل تقريراً شاملاً + تنبيهات التغيرات الكبيرة."""
    for uid_str, data in list(tracked_assets.items()):
        assets = data.get("assets", [])
        if not assets:
            continue
        last_prices = data.get("last_prices", {})
        changed = False
        report_lines = []
        alerts = []

        user = users.get(uid_str, {})
        lang = user.get("lang", "English 🇬🇧")

        for symbol in assets:
            try:
                new_price = fetch_asset_price(symbol)
                if new_price is None:
                    report_lines.append(f"❓ {get_asset_label(symbol)}: {t(lang, 'track_unavailable')}")
                    continue
                old_price = last_prices.get(symbol)
                if old_price and old_price > 0:
                    change_pct = ((new_price - old_price) / old_price) * 100
                    arrow = "📈" if change_pct >= 0 else "📉"
                    report_lines.append(
                        f"{arrow} {format_asset_price(symbol, new_price)}  `{change_pct:+.2f}%`"
                    )
                    if abs(change_pct) >= 1.0:
                        direction = t(lang, "track_rose") if change_pct > 0 else t(lang, "track_fell")
                        alerts.append(
                            f"{direction} *{get_asset_label(symbol)}* بنسبة `{change_pct:+.2f}%`\n"
                            f"   السعر: `${new_price:,.4f}` (كان `${old_price:,.4f}`)"
                        )
                else:
                    report_lines.append(f"🔹 {format_asset_price(symbol, new_price)}")
                tracked_assets[uid_str]["last_prices"][symbol] = new_price
                changed = True
            except Exception:
                continue

        if changed:
            save_tracked_assets()

        # إرسال التنبيهات الفورية للتغيرات الكبيرة
        if alerts:
            alert_msg = (
                t(lang, "track_alert_title")
                + "\n\n".join(alerts)
                + f"\n\n🤖 @{BOT_USERNAME}"
            )
            try:
                bot.send_message(int(uid_str), alert_msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

        # إرسال التقرير الساعي الشامل
        if report_lines:
            now_str = _now_sa().strftime("%H:%M — %d/%m/%Y")
            report_msg = (
                t(lang, "track_report_title")
                + f"🕐 {now_str}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                + "\n".join(report_lines)
                + f"\n\n━━━━━━━━━━━━━━━\n🤖 @{BOT_USERNAME}"
            )
            try:
                bot.send_message(int(uid_str), report_msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

def cmd_mytrack(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    _update_user_last_command(uid, "/mytrack")
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    data = tracked_assets.get(str(uid), {})
    assets = data.get("assets", [])
    if not assets:
        bot.send_message(uid, t(lang, "track_empty"), parse_mode="Markdown")
        return
    last_prices = data.get("last_prices", {})
    msg = t(lang, "track_list_header")
    for sym in assets:
        price = fetch_asset_price(sym)
        if price:
            tracked_assets[str(uid)]["last_prices"][sym] = price
            save_tracked_assets()
        msg += f"• {format_asset_price(sym, price or last_prices.get(sym))}\n"
    msg += f"━━━━━━━━━━━━━━\n🤖 @{BOT_USERNAME}"
    bot.send_message(uid, msg, parse_mode="Markdown")

@bot.message_handler(commands=["removetrack"])
def cmd_removetrack(m):
    uid = m.from_user.id
    if uid in banned: return
    if bot_paused: return
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    parts = m.text.strip().split()
    if len(parts) < 2:
        bot.send_message(uid, t(lang, "track_remove_usage"), parse_mode="Markdown")
        return
    symbol = parts[1].upper()
    data = tracked_assets.get(str(uid), {})
    assets = data.get("assets", [])
    if symbol not in assets:
        bot.send_message(uid, t(lang, "track_not_found").format(symbol=symbol), parse_mode="Markdown")
        return
    assets.remove(symbol)
    tracked_assets[str(uid)]["assets"] = assets
    tracked_assets[str(uid)]["last_prices"].pop(symbol, None)
    save_tracked_assets()
    bot.send_message(uid, t(lang, "track_removed").format(symbol=symbol), parse_mode="Markdown")


def _fetch_ohlc(symbol, yf_interval, range_):
    """جلب بيانات OHLC من Yahoo Finance."""
    try:
        encoded = requests.utils.quote(symbol, safe='')
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
            f"?interval={yf_interval}&range={range_}"
        )
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12).json()
        result = r.get("chart", {}).get("result")
        if not result:
            return None
        quotes = result[0]["indicators"]["quote"][0]
        timestamps = result[0].get("timestamp", [])
        opens  = quotes.get("open",  [])
        closes = quotes.get("close", [])
        highs  = quotes.get("high",  [])
        lows   = quotes.get("low",   [])
        bars = []
        for i in range(len(timestamps)):
            try:
                o = opens[i]; c = closes[i]; h = highs[i]; l = lows[i]
                if None in (o, c, h, l):
                    continue
                bars.append({"ts": timestamps[i], "o": o, "c": c, "h": h, "l": l})
            except Exception:
                continue
        return bars[-10:] if len(bars) > 10 else bars
    except Exception:
        return None


def _crypto_ohlc(symbol, yf_interval, range_):
    """محاولة CoinGecko للعملات الرقمية أولاً، ثم Yahoo Finance."""
    cg_id = CRYPTO_IDS.get(symbol)
    if cg_id:
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(range_, 7)
        try:
            r = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days={days}",
                timeout=12
            ).json()
            bars = []
            for row in r:
                ts, o, h, l, c = row
                bars.append({"ts": ts // 1000, "o": o, "c": c, "h": h, "l": l})
            return bars[-10:] if len(bars) > 10 else bars
        except Exception as _exc:
            _log_exc(_exc)
    return _fetch_ohlc(symbol, yf_interval, range_)


def _fmt_price(v):
    if v is None:
        return "—"
    if v >= 10000:
        return f"{v:,.0f}"
    elif v >= 1:
        return f"{v:,.2f}"
    elif v >= 0.0001:
        return f"{v:.6f}"
    else:
        return f"{v:.8f}"

def _build_text_chart(symbol, bars, interval_key):
    """رسم بياني نصي بشكل شموع ┃█┃ مع الطابع الزمني و High-Low والاتجاه."""
    if not bars:
        return None
    label = CHART_ASSET_LABELS.get(symbol, symbol)
    ivl = CHART_INTERVALS[interval_key]
    ts_fmt = ivl.get("ts_fmt", "%H:%M")

    ranges = [b["h"] - b["l"] for b in bars if b["h"] and b["l"]]
    max_range = max(ranges) if ranges else 1
    MAX_BLOCKS = 8

    header = f"📊 {label} – {ivl['label_en']}"
    divider = "─" * len(header)
    lines = [header, divider, ""]

    prev_close = None
    for bar in bars:
        ts   = bar["ts"]
        o, c, h, l = bar["o"], bar["c"], bar["h"], bar["l"]
        if None in (o, c, h, l):
            continue

        try:
            time_str = datetime.datetime.utcfromtimestamp(ts).strftime(ts_fmt)
        except Exception:
            time_str = "??:??"

        direction = "🔼" if (prev_close is None and c >= o) or (prev_close is not None and c >= prev_close) else "🔽"

        rng = h - l
        blocks = max(1, round((rng / max_range) * MAX_BLOCKS)) if max_range > 0 else 1
        bar_str = "┃" + "█" * blocks + "┃"

        lo_fmt = _fmt_price(l)
        hi_fmt = _fmt_price(h)
        range_str = f"{lo_fmt}-{hi_fmt}"

        lines.append(f"{time_str} │ {bar_str} {range_str} {direction}")
        prev_close = c

    lines.append("")
    last  = bars[-1]
    first = bars[0]
    net   = ((last["c"] - first["o"]) / first["o"]) * 100 if first["o"] else 0
    trend_icon = "📈" if net >= 0 else "📉"
    lines += [
        divider,
        f"{trend_icon}  {net:+.2f}%   🔼 {_fmt_price(max(b['h'] for b in bars))}   🔽 {_fmt_price(min(b['l'] for b in bars))}",
        f"🤖 @{BOT_USERNAME}",
    ]
    return "\n".join(lines)


def _build_chart_categories_markup(lang):
    markup = types.InlineKeyboardMarkup(row_width=2)
    cat_buttons = [
        types.InlineKeyboardButton(label, callback_data=f"chart_cat_{key}")
        for key, (label, _) in CHART_CATEGORIES.items()
    ]
    for i in range(0, len(cat_buttons), 2):
        markup.row(*cat_buttons[i:i+2])
    custom_label = "🔍 رمز مخصص" if lang == "العربية 🇮🇶" else "🔍 Custom Symbol"
    markup.row(types.InlineKeyboardButton(custom_label, callback_data="chart_cat_custom"))
    return markup

def _send_chart_categories(uid, lang, edit_msg_id=None):
    prompt = CHART_CAT_PROMPTS.get(lang, CHART_CAT_PROMPTS["English 🇬🇧"])
    markup = _build_chart_categories_markup(lang)
    if edit_msg_id:
        try:
            bot.edit_message_text(prompt, chat_id=uid, message_id=edit_msg_id,
                                  reply_markup=markup, parse_mode="Markdown")
        except Exception:
            bot.send_message(uid, prompt, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(uid, prompt, reply_markup=markup, parse_mode="Markdown")

def _chart_custom_symbol_step(message):
    uid = message.from_user.id
    if not message.text or message.text.startswith('/'):
        bot.send_message(uid, "⚠️ تم الإلغاء. أرسل /chart للبدء مجدداً.")
        return
    symbol = message.text.strip().upper()
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    prompt = INTERVAL_PROMPTS.get(lang, INTERVAL_PROMPTS["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.row(*[
        types.InlineKeyboardButton(k, callback_data=f"chart_interval_{symbol}_{k}")
        for k in CHART_INTERVALS.keys()
    ])
    label = CHART_ASSET_LABELS.get(symbol, symbol)
    bot.send_message(uid, f"✅ *{label}*\n{prompt}", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["chart"])
def cmd_chart(m):
    uid = m.from_user.id
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    _send_chart_categories(uid, lang)
