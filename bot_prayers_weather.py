# -*- coding: utf-8 -*-
# bot_prayers_weather.py — الطقس وأوقات الصلاة

def _get_cached_weather(city, lang_code):
    key = f"{city}_{lang_code}"
    if key in _weather_cache:
        data, ts = _weather_cache[key]
        if (datetime.datetime.now() - ts).total_seconds() < _WEATHER_CACHE_TTL:
            return data
    return None

def _set_cached_weather(city, lang_code, data):
    _weather_cache[f"{city}_{lang_code}"] = (data, datetime.datetime.now())

def _fetch_weather_cached(city, lang_code):
    d = _get_cached_weather(city, lang_code)
    if d:
        return d
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}"
    try:
        d = requests.get(url, timeout=10).json()
        if d.get("cod") == 200:
            _set_cached_weather(city, lang_code, d)
            return d
    except Exception as _exc:
        _log_exc(_exc)
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# IMMORTAL DELIVERY ENGINE — تصنيف الأخطاء + ضمان التسليم + ضبط الحمل التلقائي
# ═══════════════════════════════════════════════════════════════════════════════

# ── ثوابت تصنيف الأخطاء ─────────────────────────────────────────────────────
_ERR_TELEGRAM_API  = "telegram_api"   # خطأ من API تيليغرام
_ERR_DELIVERY      = "delivery"       # فشل التسليم (مستخدم حجب / حذف)
_ERR_PARSE         = "parse"          # خطأ Markdown/HTML
_ERR_RATE_LIMIT    = "rate_limit"     # 429 Too Many Requests
_ERR_NETWORK       = "network"        # انقطاع الشبكة
_ERR_RESOURCE      = "resource"       # CPU/RAM مرتفع
_ERR_UNKNOWN       = "unknown"        # غير معروف

# ── قائمة الـ chats المعطّلة مؤقتاً (blacklist) ─────────────────────────────
_dead_chats: dict = {}
_dead_chats_lock  = gl._dead_chats_lock    # من state
_DEAD_CHAT_TTL    = 86400

# ── إحصاءات التسليم المتقدمة ──────────────────────────────────────────────────
_delivery_stats: dict = {
    "sent_ok":        0,
    "sent_fail":      0,
    "retried":        0,
    "rate_limited":   0,
    "auto_resolved":  0,    # مشاكل حُلّت تلقائياً
    "admin_alerted":  0,    # مشاكل أُبلغ عنها للأدمن
}
_delivery_stats_lock = gl._delivery_stats_lock    # من state


def send_3day_forecast(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang = user.get("lang", "English 🇬🇧")
    lang_code = LANG_CODES.get(lang, "en")
    province = user.get("province", "")
    country  = user.get("country", "")
    if not province:
        bot.send_message(uid, t(lang, "no_city"))
        return
    owm_city = _to_owm_city(province, country)
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={owm_city}&appid={WEATHER_KEY}&units=metric&lang={lang_code}&cnt=24"
        data = requests.get(url, timeout=10).json()
        if str(data.get("cod")) != "200":
            bot.send_message(uid, t(lang, "city_not_found").format(city=province))
            return
        days = {}
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in days:
                days[date] = {"temps": [], "descs": [], "icons": []}
            days[date]["temps"].append(item["main"]["temp"])
            days[date]["descs"].append(item["weather"][0]["description"])
            days[date]["icons"].append(item["weather"][0]["id"])
        msg = t(lang, "forecast_3day_header").format(city=province)
        day_names = list(days.items())[:3]
        for date, info in day_names:
            min_t = round(min(info["temps"]))
            max_t = round(max(info["temps"]))
            desc = info["descs"][len(info["descs"])//2]
            icon = get_weather_emoji(info["icons"][len(info["icons"])//2])
            msg += f"{icon} *{date}*\n"
            msg += f"   🌡 {min_t}°C — {max_t}°C\n"
            msg += f"   ☁️ {desc.capitalize()}\n\n"
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "weather_error"))
        notify_admin_error(f"خطأ في توقعات 3 أيام لـ {uid}: {e}")

# ======== ترتيب أفضل الداعين ========

def send_prayer_times(uid):
    user = users.get(str(uid))
    if not user:
        return
    lang     = user.get("lang", "English 🇬🇧")
    province = user.get("province", "")
    lat      = user.get("location_lat")
    lon      = user.get("location_lon")
    if not province and lat is None:
        bot.send_message(uid, t(lang, "prayer_no_city"))
        return
    try:
        today = datetime.date.today()
        display_city = province
        if lat is not None and lon is not None:
            url = (f"https://api.aladhan.com/v1/timings/{today}"
                   f"?latitude={lat}&longitude={lon}&method=4")
        else:
            owm_city = _to_owm_city(province)
            url = (f"https://api.aladhan.com/v1/timingsByCity"
                   f"?city={owm_city}&country=&method=4&date={today}")
        r = requests.get(url, timeout=10).json()
        if r.get("code") != 200:
            bot.send_message(uid, t(lang, "prayer_city_error").format(city=display_city))
            return
        timings  = r["data"]["timings"]
        date_info = r["data"]["date"]["readable"]
        hijri    = r["data"]["date"]["hijri"]
        hijri_str = f"{hijri['day']} {hijri['month']['ar']} {hijri['year']} هـ"
        msg = t(lang, "prayer_header").format(
            city=display_city, date=date_info, hijri=hijri_str,
            fajr=timings['Fajr'], sunrise=timings['Sunrise'],
            dhuhr=timings['Dhuhr'], asr=timings['Asr'],
            maghrib=timings['Maghrib'], isha=timings['Isha']
        )
        bot.send_message(uid, msg, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(uid, t(lang, "prayer_error"))
        notify_admin_error(f"خطأ في أوقات الصلاة لـ {uid}: {e}")

# ======== إحصائيات الدعوات (رابط الدعوة) ========
