# -*- coding: utf-8 -*-
"""
  users_core.py — تحميل/حفظ + تحديث + مستخدم عراقي

  يُصدِّر دوال إدارة بيانات المستخدمين الأساسية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def save_stats():
    """دالة مساعدة: حفظ الإحصائيات."""
    save_json(STATS_FILE, stats)

def _is_iraqi_user(uid) -> bool:
    """يتحقق إذا كان المستخدم من العراق (لغة عربية عراقية أو مدينة عراقية)"""
    user = users.get(str(uid), {})
    lang = user.get("lang", "")
    province = user.get("province", "")
    if lang == "العربية 🇮🇶":
        return True
    iraqi_cities = {
        "بغداد", "بصرة", "موصل", "اربيل", "كربلاء", "نجف", "كركوك",
        "سليمانية", "ديالى", "بابل", "الانبار", "الديوانية", "ميسان",
        "واسط", "ذي قار", "صلاح الدين", "نينوى", "دهوك", "المثنى",
        "Baghdad", "Basra", "Mosul", "Erbil", "Karbala", "Najaf",
    }
    if province and any(c.lower() in province.lower() for c in iraqi_cities):
        return True
    return False


def send_usage_hint(uid, lang):
    hint = USAGE_HINTS.get(lang, USAGE_HINTS["English 🇬🇧"])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 تواصل / Contact", url=CONTACT_LINK))
    bot.send_message(uid, hint, parse_mode="Markdown", reply_markup=markup)

# ======== القائمة الرئيسية ========
def _update_last_seen(uid, message=None):
    u = users.get(str(uid))
    if u:
        u["last_seen"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        u["message_count"] = u.get("message_count", 0) + 1
        # حفظ بيانات الملف الشخصي من كائن الرسالة
        if message and hasattr(message, "from_user"):
            fu = message.from_user
            if fu.first_name:
                u["first_name"] = fu.first_name
            if fu.last_name:
                u["last_name"] = fu.last_name
            if fu.username:
                u["username"] = fu.username
        _db_save_user(uid, u)

def _track_feature(uid, feature):
    """يسجّل استخدام ميزة معينة في قائمة features_used"""
    u = users.get(str(uid))
    if not u:
        return
    used = u.get("features_used", {})
    used[feature] = used.get(feature, 0) + 1
    u["features_used"] = used
    _db_save_user(uid, u)

def _update_user_last_command(uid, command):
    """يحدّث آخر أمر استخدمه المستخدم."""
    uid_str = str(uid)
    if uid_str in users:
        users[uid_str]["last_command"] = command
        users[uid_str]["last_seen"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

