# -*- coding: utf-8 -*-
"""
  handler_help.py — /help + قائمة الأوامر

  يُصدِّر معالج أمر /help وقائمة الأوامر.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _make_help_keyboard(lang):
    lbl = HELP_CMD_LABELS.get(lang, HELP_CMD_LABELS["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton(lbl["start"],    callback_data="hcmd_start"),
        types.InlineKeyboardButton(lbl["settings"], callback_data="hcmd_settings"),
        types.InlineKeyboardButton(lbl["help"],     callback_data="hcmd_help"),
    )
    markup.add(
        types.InlineKeyboardButton(lbl["mytrack"],     callback_data="hcmd_mytrack"),
        types.InlineKeyboardButton(lbl["markets"],     callback_data="hcmd_markets"),
        types.InlineKeyboardButton(lbl["alerts"],      callback_data="hcmd_alerts"),
    )
    markup.add(
        types.InlineKeyboardButton(lbl["chart"],       callback_data="hcmd_chart"),
        types.InlineKeyboardButton(lbl["addtrack"],    callback_data="hcmd_addtrack"),
        types.InlineKeyboardButton(lbl["removetrack"], callback_data="hcmd_removetrack"),
    )
    markup.add(
        types.InlineKeyboardButton(lbl["news"],     callback_data="hcmd_news"),
        types.InlineKeyboardButton(lbl["trending"], callback_data="hcmd_trending"),
        types.InlineKeyboardButton(lbl["summary"],  callback_data="hcmd_summary"),
    )
    markup.add(
        types.InlineKeyboardButton(lbl["weather"],  callback_data="hcmd_weather"),
    )
    return markup

@bot.message_handler(commands=['help'])
def help_command(message):
    uid = message.from_user.id
    if uid in banned: return
    _update_user_last_command(uid, "/help")
    user = users.get(str(uid))
    lang = user.get("lang", "English 🇬🇧") if user else "English 🇬🇧"
    text = HELP_TEXTS.get(lang, HELP_TEXTS["English 🇬🇧"])
    bot.send_message(uid, text, parse_mode="Markdown", reply_markup=_make_help_keyboard(lang))



# HEROKU FIX v2: Universal callback anti-spam guard
# Registered FIRST so it runs before all other callback handlers
from handler_callbacks import _cb_antispam  # noqa: E402  (FIX: كان اسماً تائهاً غير مربوط، يُسقِط كل الـ callbacks بـ NameError)


@bot.callback_query_handler(func=lambda c: _cb_antispam(c.from_user.id))
def help_cmd_callback(call):
    uid = call.from_user.id
    cmd = call.data.replace("hcmd_", "")
    bot.answer_callback_query(call.id)
    user = users.get(str(uid), {})
    lang = user.get("lang", "English 🇬🇧")
    if cmd == "start":
        class _FakeMsg:
            from_user = type("U", (), {"id": uid, "first_name": user.get("name",""), "username": None})()
            chat = type("C", (), {"id": uid, "type": "private"})()
            text = "/start"
        start(_FakeMsg())
    elif cmd == "help":
        text = HELP_TEXTS.get(lang, HELP_TEXTS["English 🇬🇧"])
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=_make_help_keyboard(lang))
    elif cmd == "settings":
        if str(uid) in users:
            class _FakeSettingsMsg:
                from_user = type("U", (), {"id": uid})()
                chat = type("C", (), {"id": uid, "type": "private"})()
            cmd_settings_private(_FakeSettingsMsg())
    elif cmd == "mytrack":
        start_track_asset(uid)
    elif cmd == "markets":
        class _M:
            from_user = type("U",(),{"id":uid})()
        cmd_markets(_M())
    elif cmd == "alerts":
        class _M:
            from_user = type("U",(),{"id":uid})()
        cmd_alerts(_M())
    elif cmd == "chart":
        _send_chart_categories(uid, lang)
    elif cmd == "news":
        if str(uid) in users:
            send_hourly_news(uid)
        else:
            bot.send_message(uid, _ui("send_start_first", lang))
    elif cmd == "trending":
        if str(uid) in users:
            send_trending_news(uid)
        else:
            bot.send_message(uid, _ui("send_start_first", lang))
    elif cmd == "summary":
        if str(uid) in users:
            send_daily_top3(uid)
        else:
            bot.send_message(uid, _ui("send_start_first", lang))
    elif cmd == "weather":
        if str(uid) in users:
            u = users[str(uid)]
            if u.get("province"):
                send_detailed_weather(uid)
            else:
                bot.send_message(uid, _ui("no_city_set", lang))
        else:
            bot.send_message(uid, _ui("send_start_first", lang))
    elif cmd in ("addtrack", "removetrack"):
        hint = {
            "addtrack": {
                "العربية 🇮🇶":   "أرسل رمز الأصل لإضافته، مثال: `BTC` أو `AAPL`",
                "English 🇬🇧":   "Send the asset symbol to add, e.g.: `BTC` or `AAPL`",
                "Русский 🇷🇺":   "Отправьте символ актива для добавления, напр.: `BTC` или `AAPL`",
                "فارسی 🇮🇷":     "نماد دارایی را ارسال کنید، مثلاً: `BTC` یا `AAPL`",
                "हिन्दी 🇮🇳":    "एसेट सिंबल भेजें, जैसे: `BTC` या `AAPL`",
                "Português 🇧🇷": "Envie o símbolo do ativo, ex.: `BTC` ou `AAPL`",
                "Türkçe 🇹🇷":    "Eklemek için varlık sembolünü gönderin, ör.: `BTC` veya `AAPL`",
                "اردو 🇵🇰":      "اثاثہ علامت بھیجیں، مثال: `BTC` یا `AAPL`",
                "Deutsch 🇩🇪":   "Sende das Asset-Symbol zum Hinzufügen, z.B.: `BTC` oder `AAPL`",
                "Українська 🇺🇦":"Надішліть символ активу, напр.: `BTC` або `AAPL`",
                "Italiano 🇮🇹":  "Invia il simbolo dell'asset, es.: `BTC` o `AAPL`",
                "Español 🇲🇽":   "Envía el símbolo del activo, ej.: `BTC` o `AAPL`",
                "Français 🇫🇷":  "Envoyez le symbole de l'actif, ex.: `BTC` ou `AAPL`",
            },
            "removetrack": {
                "العربية 🇮🇶":   "أرسل رمز الأصل لحذفه من قائمة التتبع",
                "English 🇬🇧":   "Send the asset symbol to remove from tracking",
                "Русский 🇷🇺":   "Отправьте символ актива для удаления из отслеживания",
                "فارسی 🇮🇷":     "نماد دارایی را برای حذف از ردیابی ارسال کنید",
                "हिन्दी 🇮🇳":    "ट्रैकिंग से हटाने के लिए एसेट सिंबल भेजें",
                "Português 🇧🇷": "Envie o símbolo do ativo para remover do rastreamento",
                "Türkçe 🇹🇷":    "Takipten kaldırmak için varlık sembolünü gönderin",
                "اردو 🇵🇰":      "ٹریکنگ سے ہٹانے کے لیے علامت بھیجیں",
                "Deutsch 🇩🇪":   "Sende das Asset-Symbol zum Entfernen aus der Verfolgung",
                "Українська 🇺🇦":"Надішліть символ для видалення зі стеження",
                "Italiano 🇮🇹":  "Invia il simbolo per rimuoverlo dal tracciamento",
                "Español 🇲🇽":   "Envía el símbolo para eliminarlo del seguimiento",
                "Français 🇫🇷":  "Envoyez le symbole pour le supprimer du suivi",
            },
        }
        msg = hint[cmd].get(lang, hint[cmd]["English 🇬🇧"])
        if cmd == "addtrack":
            bot.send_message(uid, f"➕ {msg}", parse_mode="Markdown")
            bot.register_next_step_handler_by_chat_id(uid, lambda m: _addtrack_step(m))
        else:
            bot.send_message(uid, f"➖ {msg}", parse_mode="Markdown")
            bot.register_next_step_handler_by_chat_id(uid, lambda m: _removetrack_step(m))

@bot.message_handler(commands=["stop"])
def stop_command(message):
    uid = message.from_user.id
    if uid in banned: return
    lang = (users.get(str(uid), {}) or {}).get("lang", "English 🇬🇧")
    if str(uid) in users:
        users[str(uid)]["notifications"] = False
        _db_save_all_users(users)
    bot.send_message(uid, _ui("stop_notifications", lang))

