# -*- coding: utf-8 -*-
"""
  admin_users_mgmt.py — إدارة المستخدمين + بحث + رسالة لمستخدم

  يُصدِّر دوال إدارة المستخدمين من لوحة الأدمن.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _admin_reply_step(message, target_uid):
    if not is_admin(message.from_user.id):
        return
    try:
        bot.send_message(int(target_uid),
            f"💬 *رد من إدارة البوت:*\n\n{message.text}",
            parse_mode="Markdown")
        bot.send_message(message.from_user.id, "✅ تم إرسال الرد بنجاح.")
    except Exception as e:
        bot.send_message(message.from_user.id, f"⚠️ فشل الإرسال: {e}")

# ======== إدارة القنوات والمجموعات ========
def search_user_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    query = message.text.strip().lower()
    results = []
    for u_id, u_info in list(users.items()):
        name = u_info.get("name", "").lower()
        if query == u_id or query in name:
            results.append((u_id, u_info))
    if not results:
        bot.send_message(uid, "❌ لم يُعثَر على مستخدم بهذا ID أو الاسم.")
        return
    for u_id, u_info in results[:5]:
        notif = "✅" if u_info.get("notifications", True) else "❌"
        is_pr = int(u_id) in stats.get("premium_users", [])
        msg = (
            f"👤 *نتيجة البحث*\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{u_id}`\n"
            f"👤 الاسم: *{u_info.get('name', '—')}*\n"
            f"🗣 اللغة: {u_info.get('lang', '-')}\n"
            f"🌍 الدولة: {u_info.get('country', '-')}\n"
            f"📅 الانضمام: `{u_info.get('join_date', '-')}`\n"
            f"🔔 إشعارات: {notif} | ⭐ مميز: {'نعم' if is_pr else 'لا'}"
        )
        view_markup = types.InlineKeyboardMarkup(row_width=2)
        view_markup.add(
            types.InlineKeyboardButton("🚫 حظر", callback_data=f"quick_ban_{u_id}"),
            types.InlineKeyboardButton("⭐ ترقية", callback_data=f"quick_premium_{u_id}"),
            types.InlineKeyboardButton("📢 راسله", url=f"tg://user?id={u_id}"),
        )
        bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=view_markup)

def msg_user_step(message):
    if not is_admin(message.from_user.id):
        return
    uid = message.from_user.id
    lines = message.text.strip().split("\n")
    if len(lines) < 2:
        bot.send_message(uid, "❌ أرسل في سطرين: السطر 1 ID المستخدم، السطر 2 الرسالة.")
        return
    try:
        target_id = int(lines[0].strip())
        msg_text = "\n".join(lines[1:]).strip()
        bot.send_message(target_id, f"📩 *رسالة من الإدارة:*\n\n{msg_text}", parse_mode="Markdown")
        bot.send_message(uid, f"✅ تم إرسال الرسالة للمستخدم `{target_id}` بنجاح.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(uid, "❌ ID غير صحيح.")
    except Exception as e:
        bot.send_message(uid, f"❌ فشل الإرسال: {e}")

# ======== خطوة إضافة أدمن (تُستدعى عبر bot.register_next_step_handler من admin_panel.py) ========
def add_admin_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id == ADMIN_ID:
            bot.send_message(ADMIN_ID, "⚠️ هذا هو الأدمن الرئيسي بالفعل.")
            return
        if new_admin_id in extra_admins:
            bot.send_message(ADMIN_ID, "⚠️ هذا المستخدم أدمن بالفعل.")
            return
        extra_admins.append(new_admin_id)
        save_extra_admins()
        bot.send_message(ADMIN_ID, f"✅ تم تعيين المستخدم `{new_admin_id}` كأدمن.", parse_mode="Markdown")
        try:
            bot.send_message(new_admin_id, "👑 تم تعيينك كأدمن في البوت.\nاستخدم /admin للوصول للوحة التحكم.")
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ خطأ: {e}")

def remove_admin_step(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.strip())
        if target_id not in extra_admins:
            bot.send_message(ADMIN_ID, "⚠️ هذا المستخدم ليس أدمن إضافياً.")
            return
        extra_admins.remove(target_id)
        save_extra_admins()
        bot.send_message(ADMIN_ID, f"✅ تم إزالة الأدمن `{target_id}`.", parse_mode="Markdown")
        try:
            bot.send_message(target_id, "⚠️ تم إلغاء صلاحيات الأدمن الخاصة بك.")
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ خطأ: {e}")

# ======== خطوات الأدمن ========
def get_user_info(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = str(message.text.strip())
        user = users.get(target_id)
        if not user:
            bot.send_message(message.from_user.id, "❌ المستخدم غير موجود.")
            return
        is_banned_user = int(target_id) in banned
        is_premium_user = int(target_id) in stats.get("premium_users", [])
        is_admin_user = is_admin(int(target_id))
        referrals = user.get("referrals", [])
        referred_by = user.get("referred_by", None)
        join_date = user.get("join_date", "غير معروف")
        interests = user.get("interests", [])
        notif = "✅ مفعّل" if user.get("notifications", True) else "❌ موقوف"
        track_data = tracked_assets.get(target_id, {})
        tracked = track_data.get("assets", [])
        msg = (
            f"👤 *ملف المستخدم الكامل*\n"
            f"━━━━━━━━━━━━━━\n"
            f"🆔 ID: `{target_id}`\n"
            f"👤 الاسم: *{user.get('name', 'غير معروف')}*\n"
            f"🗣 اللغة: {user.get('lang', '-')}\n"
            f"🌍 الدولة: {user.get('country', '-')}\n"
            f"📍 المحافظة: {user.get('province', '-')}\n"
            f"📅 تاريخ الانضمام: `{join_date}`\n"
            f"━━━━━━━━━━━━━━\n"
            f"🚫 محظور: {'✅ نعم' if is_banned_user else '❌ لا'}\n"
            f"⭐ مميز: {'✅ نعم' if is_premium_user else '❌ لا'}\n"
            f"👑 أدمن: {'✅ نعم' if is_admin_user else '❌ لا'}\n"
            f"🔔 الإشعارات: {notif}\n"
            f"━━━━━━━━━━━━━━\n"
            f"🎁 دعواته: `{len(referrals)}` شخص\n"
            f"👈 جاء عبر: `{referred_by if referred_by else 'مباشر'}`\n"
            f"📌 أصوله المتتبعة: `{', '.join(tracked) if tracked else 'لا يوجد'}`\n"
            f"📰 اهتماماته: `{', '.join(interests) if interests else 'لم يختر'}`\n"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🚫 حظر", callback_data=f"quick_ban_{target_id}"),
            types.InlineKeyboardButton("⭐ ترقية مميز", callback_data=f"quick_premium_{target_id}"),
            types.InlineKeyboardButton("📢 راسله", url=f"tg://user?id={target_id}"),
        )
        bot.send_message(message.from_user.id, msg, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")

def ban_user_step(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        if target_id not in banned:
            banned.append(target_id)
            save_json(BANNED_FILE, banned)
        bot.send_message(message.from_user.id, f"✅ تم حظر المستخدم `{target_id}`", parse_mode="Markdown")
        try:
            bot.send_message(target_id, "🚫 تم حظرك من استخدام البوت.")
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")

def unban_user_step(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        if target_id in banned:
            banned.remove(target_id)
            save_json(BANNED_FILE, banned)
            bot.send_message(message.from_user.id, f"✅ تم رفع حظر المستخدم `{target_id}`", parse_mode="Markdown")
        else:
            bot.send_message(message.from_user.id, "⚠️ المستخدم غير محظور.")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")

def promote_premium_step(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        if "premium_users" not in stats:
            stats["premium_users"] = []
        if target_id not in stats["premium_users"]:
            stats["premium_users"].append(target_id)
            save_json(STATS_FILE, stats)
        bot.send_message(message.from_user.id, f"⭐ تم ترقية المستخدم `{target_id}` للمميز.", parse_mode="Markdown")
        try:
            bot.send_message(target_id, "⭐ تهانينا! تمت ترقيتك لحساب مميز.")
        except Exception as _exc:
            _log_exc(_exc)
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")

def demote_premium_step(message):
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
        if target_id in stats.get("premium_users", []):
            stats["premium_users"].remove(target_id)
            save_json(STATS_FILE, stats)
            bot.send_message(message.from_user.id, f"✅ تم إلغاء الاشتراك المميز للمستخدم `{target_id}`", parse_mode="Markdown")
        else:
            bot.send_message(message.from_user.id, "⚠️ المستخدم ليس مميزاً.")
    except Exception as e:
        bot.send_message(message.from_user.id, f"❌ خطأ: {e}")
