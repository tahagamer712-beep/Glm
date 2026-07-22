# -*- coding: utf-8 -*-
"""
  admin_features_panel.py — لوحة الميزات البصرية (تفعيل/تعطيل)

  يُصدِّر لوحة إدارة الميزات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _build_features_panel(uid):
    """يبني ويرسل لوحة إدارة الميزات البصرية."""
    gating_status = "✅ مفعّل" if _FEATURE_GATING_ACTIVE else "❌ معطّل"
    gating_btn    = "🔴 تعطيل النظام" if _FEATURE_GATING_ACTIVE else "🟢 تفعيل النظام"

    lines = [
        "⚙️ *لوحة إدارة الميزات*",
        "━━━━━━━━━━━━━━",
        f"نظام القيود: {gating_status}",
        "",
        "اضغط على أي ميزة للتنقل بين الأوضاع:",
        "  🟢 مجاني  →  🔢 محدود  →  ⭐ مميز فقط  →  🚫 ملغية",
        "",
        "🚫 *ملغية* = لا يظهر الزر لأحد ولا يشتغل الأمر",
    ]
    if not _FEATURE_GATING_ACTIVE:
        lines.append("\n⚠️ _النظام معطّل — إعدادات الأوضاع لا تُطبَّق (ماعدا 🚫 الملغية)._")

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(
        f"{gating_btn}  (النظام {gating_status})",
        callback_data="feat_toggle_gating"
    ))
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━", callback_data="noop"))

    for key, fname in _FEATURE_FRIENDLY_NAMES.items():
        reg   = _FEATURE_REGISTRY.get(key, {})
        mode  = reg.get("mode", "free")
        icon  = _MODE_ICONS.get(mode, "🟢")
        fd    = reg.get("free_daily", -1)
        pd_   = reg.get("prem_daily", -1)
        limit_txt = ""
        if mode == "limited":
            fd_s  = str(fd)  if fd  != -1 else "∞"
            pd_s  = str(pd_) if pd_ != -1 else "∞"
            limit_txt = f"  [{fd_s}/يوم → {pd_s}/مميز]"
        markup.add(types.InlineKeyboardButton(
            f"{icon} {fname}{limit_txt}",
            callback_data=f"feat_mode_{key}"
        ))

    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━", callback_data="noop"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="admin_back"))

    bot.send_message(uid, "\n".join(lines), parse_mode="Markdown", reply_markup=markup)

def _features_panel_edit(call):
    """يُحدّث رسالة لوحة الميزات بدل إرسال رسالة جديدة."""
    uid = call.from_user.id
    gating_status = "✅ مفعّل" if _FEATURE_GATING_ACTIVE else "❌ معطّل"
    gating_btn    = "🔴 تعطيل النظام" if _FEATURE_GATING_ACTIVE else "🟢 تفعيل النظام"
    lines = [
        "⚙️ *لوحة إدارة الميزات*",
        "━━━━━━━━━━━━━━",
        f"نظام القيود: {gating_status}",
        "",
        "اضغط على أي ميزة للتنقل بين الأوضاع:",
        "  🟢 مجاني  →  🔢 محدود  →  ⭐ مميز فقط  →  🚫 ملغية",
        "",
        "🚫 *ملغية* = لا يظهر الزر لأحد ولا يشتغل الأمر",
    ]
    if not _FEATURE_GATING_ACTIVE:
        lines.append("\n⚠️ _النظام معطّل — إعدادات الأوضاع لا تُطبَّق (ماعدا 🚫 الملغية)._")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(
        f"{gating_btn}  (النظام {gating_status})",
        callback_data="feat_toggle_gating"
    ))
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━", callback_data="noop"))
    for key, fname in _FEATURE_FRIENDLY_NAMES.items():
        reg   = _FEATURE_REGISTRY.get(key, {})
        mode  = reg.get("mode", "free")
        icon  = _MODE_ICONS.get(mode, "🟢")
        fd    = reg.get("free_daily", -1)
        pd_   = reg.get("prem_daily", -1)
        limit_txt = ""
        if mode == "limited":
            fd_s  = str(fd)  if fd  != -1 else "∞"
            pd_s  = str(pd_) if pd_ != -1 else "∞"
            limit_txt = f"  [{fd_s}/يوم → {pd_s}/مميز]"
        markup.add(types.InlineKeyboardButton(
            f"{icon} {fname}{limit_txt}",
            callback_data=f"feat_mode_{key}"
        ))
    markup.add(types.InlineKeyboardButton("━━━━━━━━━━━━━━━━", callback_data="noop"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع للوحة الرئيسية", callback_data="admin_back"))
    try:
        bot.edit_message_text(
            "\n".join(lines),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception:
        _build_features_panel(uid)

# ─── Callback handlers للميزات ───
@bot.callback_query_handler(func=lambda c: c.data in ("admin_features", "feat_toggle_gating") or
                             c.data.startswith("feat_mode_") or c.data.startswith("feat_set_") or
                             c.data == "feat_back")
def cb_admin_features(call):
    global _FEATURE_GATING_ACTIVE
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ للأدمن فقط")
        return
    uid  = call.from_user.id
    data = call.data

    # ── فتح اللوحة ──
    if data == "admin_features":
        bot.answer_callback_query(call.id)
        _build_features_panel(uid)
        return

    # ── تفعيل/تعطيل النظام كله ──
    if data == "feat_toggle_gating":
        _FEATURE_GATING_ACTIVE = not _FEATURE_GATING_ACTIVE
        stats["feature_gating_active"] = _FEATURE_GATING_ACTIVE
        save_stats()
        status = "✅ تم تفعيل نظام القيود" if _FEATURE_GATING_ACTIVE else "❌ تم تعطيل نظام القيود — كل الميزات مجانية الآن"
        bot.answer_callback_query(call.id, status, show_alert=True)
        _features_panel_edit(call)
        return

    # ── الضغط على ميزة → يدور الوضع ──
    if data.startswith("feat_mode_"):
        key = data[len("feat_mode_"):]
        if key not in _FEATURE_REGISTRY:
            bot.answer_callback_query(call.id, "❌ ميزة غير موجودة")
            return
        current_mode = _FEATURE_REGISTRY[key]["mode"]
        next_mode    = _MODE_CYCLE[(_MODE_CYCLE.index(current_mode) + 1) % len(_MODE_CYCLE)]
        _FEATURE_REGISTRY[key]["mode"] = next_mode
        # إذا صار limited و الحدود لا تزال -1 → اضبط حدوداً افتراضية معقولة
        if next_mode == "limited":
            if _FEATURE_REGISTRY[key]["free_daily"] == -1:
                _FEATURE_REGISTRY[key]["free_daily"] = 5
            if _FEATURE_REGISTRY[key]["prem_daily"] == -1:
                _FEATURE_REGISTRY[key]["prem_daily"] = -1
        _save_feature_registry()
        icon = _MODE_ICONS.get(next_mode, "🟢")
        fname = _FEATURE_FRIENDLY_NAMES.get(key, key)
        bot.answer_callback_query(call.id, f"{icon} {fname} → {next_mode}", show_alert=False)
        # إذا الوضع الجديد limited → اسأل عن الحدود
        if next_mode == "limited":
            msg = bot.send_message(
                uid,
                f"🔢 *ضبط حدود: {fname}*\n\n"
                f"أرسل رقمين مفصولين بمسافة:\n"
                f"`<حد_المجاني> <حد_المميز>`\n\n"
                f"مثال: `3 -1`  (المجاني 3 مرات/يوم، المميز غير محدود)\n"
                f"مثال: `5 20`  (المجاني 5، المميز 20)\n"
                f"مثال: `0 -1`  (يعني المميز فقط عملياً)\n\n"
                f"اضغط /skip لتخطي وإبقاء الحدود الحالية.",
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, lambda m, k=key: _feat_set_limits_step(m, k))
        else:
            _features_panel_edit(call)
        return

    # ── رجوع ──
    if data == "feat_back":
        bot.answer_callback_query(call.id)
        _build_features_panel(uid)

def _feat_set_limits_step(message, key):
    """يقرأ الحدود الجديدة ويحفظها."""
    uid  = message.from_user.id
    text = message.text.strip()
    fname = _FEATURE_FRIENDLY_NAMES.get(key, key)
    if text == "/skip":
        bot.send_message(uid, f"✅ تم تخطي الحدود — {fname} محدود بالأرقام السابقة.")
        _build_features_panel(uid)
        return
    parts = text.split()
    if len(parts) != 2:
        bot.send_message(uid, "⚠️ أرسل رقمين فقط مفصولين بمسافة. مثال: `3 -1`", parse_mode="Markdown")
        msg = bot.send_message(uid, "حاول مجدداً أو أرسل /skip للتخطي:")
        bot.register_next_step_handler(msg, lambda m, k=key: _feat_set_limits_step(m, k))
        return
    try:
        fd  = int(parts[0])
        pd_ = int(parts[1])
    except ValueError:
        bot.send_message(uid, "⚠️ الأرقام غير صحيحة. مثال: `3 -1`", parse_mode="Markdown")
        msg = bot.send_message(uid, "حاول مجدداً:")
        bot.register_next_step_handler(msg, lambda m, k=key: _feat_set_limits_step(m, k))
        return
    _FEATURE_REGISTRY[key]["free_daily"] = fd
    _FEATURE_REGISTRY[key]["prem_daily"] = pd_
    _save_feature_registry()
    fd_s  = str(fd)  if fd  != -1 else "∞"
    pd_s  = str(pd_) if pd_ != -1 else "∞"
    bot.send_message(
        uid,
        f"✅ *تم حفظ الحدود لـ {fname}:*\n"
        f"  👤 المجاني: {fd_s} مرة/يوم\n"
        f"  ⭐ المميز: {pd_s} مرة/يوم",
        parse_mode="Markdown"
    )
    _build_features_panel(uid)

@bot.message_handler(commands=["featuregate"])
def cmd_featuregate(m):
    """
    يُتيح للأدمن تفعيل أو تعطيل نظام Feature Gating:
    /featuregate on  ← تفعيل الحدود (المستخدمون المجانيون لديهم حد يومي)
    /featuregate off ← تعطيل الحدود (كل شيء مجاني)
    /featuregate set <feature> <free_limit> <premium_limit>
    """
    global _FEATURE_GATING_ACTIVE
    uid = m.from_user.id
    if not is_admin(uid):
        return

    parts = m.text.strip().split()
    if len(parts) < 2:
        status = "مُفعّل 🔴" if _FEATURE_GATING_ACTIVE else "مُعطّل 🟢"
        limits_txt = "\n".join(
            f"  • {feat}: مجاني={v['free']}/يوم | مميز={v['premium']} (-1=∞)"
            for feat, v in _FEATURE_DAILY_LIMITS.items()
        )
        bot.send_message(uid,
            f"🔐 *نظام Feature Gating*\n"
            f"الحالة الحالية: *{status}*\n\n"
            f"*الحدود المُعرَّفة:*\n{limits_txt}\n\n"
            f"_الأوامر:_\n"
            f"`/featuregate on` — تفعيل الحدود\n"
            f"`/featuregate off` — تعطيل الحدود\n"
            f"`/featuregate set intel_report 3 -1` — تعديل حد ميزة",
            parse_mode="Markdown"
        )
        return

    action = parts[1].lower()
    if action == "on":
        _FEATURE_GATING_ACTIVE = True
        bot.send_message(uid, "🔴 Feature Gating *مُفعّل* — الحدود اليومية مُطبَّقة.", parse_mode="Markdown")
    elif action == "off":
        _FEATURE_GATING_ACTIVE = False
        bot.send_message(uid, "🟢 Feature Gating *مُعطّل* — كل الميزات مجانية.", parse_mode="Markdown")
    elif action == "set" and len(parts) == 5:
        feat = parts[2]
        try:
            free_lim    = int(parts[3])
            premium_lim = int(parts[4])
            _FEATURE_DAILY_LIMITS[feat] = {"free": free_lim, "premium": premium_lim}
            bot.send_message(uid,
                f"✅ تم تعديل حدود `{feat}`:\n"
                f"مجاني: {free_lim}/يوم | مميز: {premium_lim}/يوم",
                parse_mode="Markdown"
            )
        except ValueError:
            bot.send_message(uid, "⚠️ الأرقام غير صحيحة. مثال: `/featuregate set intel_report 3 -1`")
    else:
        bot.send_message(uid, "⚠️ أمر غير معروف. أرسل `/featuregate` لعرض المساعدة.")


# ======== /health — صحة البوت الكاملة (أدمن فقط) ========
def _build_featurepanel_markup(page: int = 0) -> types.InlineKeyboardMarkup:
    """يبني لوحة التحكم التفاعلية لكل الميزات."""
    keys  = list(_FEATURE_REGISTRY.keys())
    per_page = 6
    start = page * per_page
    end   = min(start + per_page, len(keys))
    chunk = keys[start:end]

    markup = types.InlineKeyboardMarkup(row_width=2)
    for fkey in chunk:
        reg   = _FEATURE_REGISTRY[fkey]
        label = reg["label"]
        mode  = reg["mode"]
        mode_display = {"free": "🟢", "limited": "🔢", "premium_only": "⭐"}[mode]
        markup.add(
            types.InlineKeyboardButton(
                f"{label}  {mode_display}",
                callback_data=f"fp_toggle_{fkey}_{page}"
            )
        )

    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"fp_page_{page-1}"))
    if end < len(keys):
        nav_row.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"fp_page_{page+1}"))
    if nav_row:
        markup.row(*nav_row)

    markup.row(
        types.InlineKeyboardButton(
            "🔒 تفعيل التحكم" if not _FEATURE_GATING_ACTIVE else "🔓 إيقاف التحكم",
            callback_data="fp_toggle_gating"
        ),
        types.InlineKeyboardButton("🔄 تحديث", callback_data=f"fp_page_{page}")
    )
    return markup


def _featurepanel_text(page: int = 0) -> str:
    keys    = list(_FEATURE_REGISTRY.keys())
    per_page = 6
    total_pages = (len(keys) + per_page - 1) // per_page
    gating_status = "✅ مُفعَّل" if _FEATURE_GATING_ACTIVE else "⏸ موقوف (كل شيء مجاني)"
    return (
        f"⚙️ *لوحة التحكم بالميزات*\n"
        f"━━━━━━━━━━━━━━\n"
        f"🔧 التحكم: {gating_status}\n"
        f"📄 صفحة {page+1}/{total_pages}\n\n"
        f"*الأوضاع:*\n"
        f"🟢 مجاني — متاح للجميع\n"
        f"🔢 محدود — متاح بحد يومي\n"
        f"⭐ مميز فقط — مستخدمو المميز فقط\n"
        f"━━━━━━━━━━━━━━\n"
        f"_اضغط على أي ميزة لتغيير وضعها_"
    )


@bot.message_handler(commands=["featurepanel"])
def cmd_featurepanel(m):
    uid = m.from_user.id
    if not is_admin(uid):
        return
    bot.send_message(uid, _featurepanel_text(0),
                     parse_mode="Markdown",
                     reply_markup=_build_featurepanel_markup(0))


@bot.callback_query_handler(func=lambda c: c.data.startswith("fp_"))
def cb_featurepanel(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "⛔ أدمن فقط.")
        return

    data = call.data

    # ── تغيير صفحة ──
    if data.startswith("fp_page_"):
        page = int(data.split("_")[-1])
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(_featurepanel_text(page), uid, call.message.message_id,
                                  parse_mode="Markdown",
                                  reply_markup=_build_featurepanel_markup(page))
        except Exception as _exc:
            _log_exc(_exc)
        return

    # ── تفعيل / إيقاف التحكم العام ──
    if data == "fp_toggle_gating":
        global _FEATURE_GATING_ACTIVE
        _FEATURE_GATING_ACTIVE = not _FEATURE_GATING_ACTIVE
        stats["feature_gating_active"] = _FEATURE_GATING_ACTIVE
        save_stats()
        status = "✅ مُفعَّل" if _FEATURE_GATING_ACTIVE else "⏸ موقوف"
        bot.answer_callback_query(call.id, f"التحكم بالميزات: {status}", show_alert=True)
        try:
            bot.edit_message_text(_featurepanel_text(0), uid, call.message.message_id,
                                  parse_mode="Markdown",
                                  reply_markup=_build_featurepanel_markup(0))
        except Exception as _exc:
            _log_exc(_exc)
        return

    # ── تبديل وضع ميزة معينة ──
    if data.startswith("fp_toggle_"):
        # data = "fp_toggle_why_matters_2"
        # نزيل البادئة ثم نأخذ رقم الصفحة من آخر _
        remainder = data[len("fp_toggle_"):]   # "why_matters_2"
        last_sep  = remainder.rfind("_")
        if last_sep == -1:
            bot.answer_callback_query(call.id, "⚠️ بيانات غير صحيحة.")
            return
        fkey      = remainder[:last_sep]        # "why_matters"
        page_str  = remainder[last_sep+1:]      # "2"
        page      = int(page_str) if page_str.isdigit() else 0

        if fkey not in _FEATURE_REGISTRY:
            bot.answer_callback_query(call.id, f"⚠️ الميزة '{fkey}' غير موجودة.")
            return

        # دوران بين الأوضاع الثلاثة
        cur_mode  = _FEATURE_REGISTRY[fkey]["mode"]
        cur_idx   = _MODE_CYCLE.index(cur_mode) if cur_mode in _MODE_CYCLE else 0
        new_mode  = _MODE_CYCLE[(cur_idx + 1) % len(_MODE_CYCLE)]
        _FEATURE_REGISTRY[fkey]["mode"] = new_mode
        _save_feature_registry()

        label      = _FEATURE_REGISTRY[fkey]["label"]
        mode_label = _MODE_LABELS[new_mode]
        bot.answer_callback_query(call.id,
            f"{label}\n→ {mode_label}", show_alert=False)

        # إذا أصبحت محدودة وحدودها -1 → ضع حدوداً افتراضية معقولة
        if new_mode == "limited":
            if _FEATURE_REGISTRY[fkey]["free_daily"] == -1:
                _FEATURE_REGISTRY[fkey]["free_daily"] = 5
            if _FEATURE_REGISTRY[fkey]["prem_daily"] == -1:
                _FEATURE_REGISTRY[fkey]["prem_daily"] = -1  # مميز = غير محدود
            _save_feature_registry()

        try:
            bot.edit_message_text(_featurepanel_text(page), uid, call.message.message_id,
                                  parse_mode="Markdown",
                                  reply_markup=_build_featurepanel_markup(page))
        except Exception as _exc:
            _log_exc(_exc)
        return

    bot.answer_callback_query(call.id)


# ======== /grantpremium و /revokepremium — منح/سحب الاشتراك المميز ========
