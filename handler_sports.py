# -*- coding: utf-8 -*-
"""
  handler_sports.py — أوامر وأزرار الرياضة

  يُصدِّر معالجات أوامر الرياضة وأزرارها.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

@bot.callback_query_handler(func=lambda c: c.data == "sp_main")
def cb_sports_main(call):
    uid = call.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    prefs = _get_user_sports(uid)
    selected = prefs.get('leagues', [])
    leagues_text = _ul(lang, "sports_leagues", n=len(selected)) if selected else _ul(lang, "sports_no_leagues")
    alerts_text = _ul(lang, "sports_alerts_on") if prefs.get('live_alerts') else _ul(lang, "sports_alerts_off")
    prefs3   = _get_user_sports(uid)
    sel3     = prefs3.get('leagues', [])
    sport_summary3 = {}
    for lk3 in sel3:
        sp3 = SPORTS_LEAGUES.get(lk3, {}).get('sport', '')
        if sp3:
            sport_summary3[sp3] = sport_summary3.get(sp3, 0) + 1
    sport_lines3 = [
        f"  {SPORT_CATEGORIES.get(sp3,{}).get('flag','')} {SPORT_CATEGORIES.get(sp3,{}).get('name','')}: {cnt3} دوري"
        for sp3, cnt3 in sport_summary3.items()
    ]
    summary3 = ("\n" + "\n".join(sport_lines3)) if sport_lines3 else ""
    text = (
        _ul(lang, "sports_title")
        + f"📊 {leagues_text}{summary3}\n"
        + f"🔔 {alerts_text}\n\n"
        + _ul(lang, "sports_choose")
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=_sports_main_keyboard(uid))
    except Exception as _exc:
        _log_exc(_exc)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "sp_live")
def cb_sports_live(call):
    bot.answer_callback_query(call.id, "⏳ جاري جلب النتائج...")
    uid = call.from_user.id
    chat_id = call.message.chat.id
    msg_id  = call.message.message_id
    _send_live_scores(uid, chat_id, msg_id)
    # سجّل المستخدم للتحديث التلقائي كل 10 ثواني
    try:
        _reg = globals().get('_register_live_viewer')
        if _reg:
            _reg(uid, chat_id, msg_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "sp_schedule")
def cb_sports_schedule(call):
    bot.answer_callback_query(call.id, "⏳ جاري جلب الجدول...")
    _send_schedule(call.from_user.id, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "sp_news")
def cb_sports_news(call):
    bot.answer_callback_query(call.id, "⏳ جاري جلب الأخبار...")
    _send_sports_news(call.from_user.id, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_leagues_p"))
def cb_sports_leagues(call):
    page = int(call.data.replace("sp_leagues_p", ""))
    uid = call.from_user.id
    prefs = _get_user_sports(uid)
    selected = prefs.get('leagues', [])
    text = f"⚽ *اختر دورياتك*\n\nالمختار: {len(selected)} دوري — اضغط لإضافة أو إزالة دوري\n\n✅ = مختار"
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown",
                              reply_markup=_sports_leagues_keyboard(uid, page))
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown",
                         reply_markup=_sports_leagues_keyboard(uid, page))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_tog_"))
def cb_sports_toggle_league(call):
    raw = call.data.replace("sp_tog_", "")
    # إصلاح #6: نستخرج رقم الصفحة (_p{N}) ثم نُحلّل sport_key
    page = 0
    if "_p" in raw:
        raw, pg_str = raw.rsplit("_p", 1)
        try:
            page = int(pg_str)
        except ValueError:
            page = 0
    # دعم الصيغتين: sp_tog_{key}_s{sport} أو sp_tog_{key}
    if "_s" in raw:
        key, sport_key = raw.rsplit("_s", 1)
    else:
        key = raw
        sport_key = SPORTS_LEAGUES.get(raw, {}).get('sport', 'football')
    uid = call.from_user.id
    prefs = _get_user_sports(uid)
    selected = prefs.get('leagues', [])
    if key in selected:
        selected.remove(key)
        action = "أُزيل"
    else:
        selected.append(key)
        action = "أُضيف"
    prefs['leagues'] = selected
    _set_user_sports(uid, prefs)
    league_name = SPORTS_LEAGUES.get(key, {}).get('name', key).replace('⚽ ','').replace('🏀 ','').replace('🏎️ ','')
    bot.answer_callback_query(call.id, f"✅ {league_name} {action}")
    prefs2 = _get_user_sports(uid)
    sel2 = prefs2.get('leagues', [])
    text = f"🏅 *اختر دورياتك — {SPORT_CATEGORIES.get(sport_key,{}).get('name','')}*\n\nالمختار: {len(sel2)} دوري\n✅ = مختار، اضغط ✅ مرة ثانية للإزالة"
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown",
                              # إصلاح #6: نُمرّر page لإبقاء المستخدم في نفس الصفحة
                              reply_markup=_leagues_by_sport_keyboard(uid, sport_key, page))
    except Exception as _exc:
        _log_exc(_exc)

@bot.callback_query_handler(func=lambda c: c.data == "sp_toggle_field")
def cb_sports_toggle_field(call):
    """تفعيل/تعطيل ميزة الملعب النصي المباشر."""
    global _LIVE_FIELD_ENABLED
    if not is_admin(call.from_user.id):
        # للمستخدمين العاديين: عرض معلومات فقط
        bot.answer_callback_query(call.id,
            "🏟 الملعب المباشر يعمل تلقائياً عند تفعيل التنبيهات",
            show_alert=True)
        return
    _LIVE_FIELD_ENABLED = not _LIVE_FIELD_ENABLED
    status = "✅ مفعّل" if _LIVE_FIELD_ENABLED else "❌ معطّل"
    bot.answer_callback_query(call.id, f"🏟 الملعب المباشر: {status}", show_alert=False)
    # تحديث القائمة
    lang = users.get(str(call.from_user.id), {}).get("lang", "العربية 🇮🇶")
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id,
            reply_markup=_sports_main_keyboard(call.from_user.id)
        )
    except Exception as _exc:
        _log_exc(_exc)


@bot.callback_query_handler(func=lambda c: c.data == "sp_myteams")
def cb_sports_myteams(call):
    """عرض الفرق المتابَعة مع إمكانية إزالتها."""
    uid   = call.from_user.id
    prefs = _get_user_sports(uid)
    teams = prefs.get('teams', {})
    kb    = types.InlineKeyboardMarkup(row_width=1)
    lines = ["👕 *فرقي المتابَعة*\n"]
    if not teams or not any(teams.values()):
        lines.append("لا توجد فرق مختارة بعد.")
    else:
        for lk, team_ids in teams.items():
            if not team_ids:
                continue
            league = SPORTS_LEAGUES.get(lk, {})
            lines.append(f"{league.get('flag','🏅')} *{league.get('name',lk)}*")
            kb.add(types.InlineKeyboardButton(
                f"❌ إزالة كل فرق {league.get('flag','')} {league.get('name',lk)[:20]}",
                callback_data=f"sp_clrteam_{lk}"
            ))
    kb.add(types.InlineKeyboardButton("🏅 اختر فرق جديدة", callback_data="sp_sports"))
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_main"))
    text = "\n".join(lines)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=kb)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_clrteam_"))
def cb_sports_clear_team(call):
    """إزالة كل فرق دوري معين."""
    league_key = call.data.replace("sp_clrteam_", "")
    uid        = call.from_user.id
    prefs      = _get_user_sports(uid)
    teams      = prefs.get('teams', {})
    teams.pop(league_key, None)
    prefs['teams'] = teams
    _set_user_sports(uid, prefs)
    bot.answer_callback_query(call.id, "✅ تم إزالة فرق هذا الدوري")
    # إعادة عرض قائمة الفرق
    cb_sports_myteams(call)


@bot.callback_query_handler(func=lambda c: c.data == "sp_toggle_alerts")
def cb_sports_toggle_alerts(call):
    uid = call.from_user.id
    prefs = _get_user_sports(uid)
    prefs['live_alerts'] = not prefs.get('live_alerts', False)
    _set_user_sports(uid, prefs)
    status = "مفعّلة 🔔" if prefs['live_alerts'] else "مغلقة 🔕"
    bot.answer_callback_query(call.id, f"تنبيهات المباريات: {status}")
    # تحديث القائمة
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    selected = prefs.get('leagues', [])
    leagues_text = _ul(lang, "sports_leagues", n=len(selected)) if selected else _ul(lang, "sports_no_leagues")
    alerts_text = _ul(lang, "sports_alerts_on") if prefs['live_alerts'] else _ul(lang, "sports_alerts_off")
    text = (
        _ul(lang, "sports_title")
        + f"📊 {leagues_text}\n"
        + f"🔔 {alerts_text}\n\n"
        + _ul(lang, "sports_choose")
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=_sports_main_keyboard(uid))
    except Exception as _exc:
        _log_exc(_exc)



@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_allsport_"))
def cb_sports_select_all(call):
    """اختيار أو إزالة كل دوريات رياضة واحدة دفعة."""
    sport_key   = call.data.replace("sp_allsport_", "")
    uid         = call.from_user.id
    prefs       = _get_user_sports(uid)
    selected    = set(prefs.get('leagues', []))
    sport_keys  = [k for k,v in SPORTS_LEAGUES.items() if v.get('sport') == sport_key]
    all_sel     = all(k in selected for k in sport_keys)
    if all_sel:
        # أزل الكل
        for k in sport_keys:
            selected.discard(k)
        msg = f"❌ تم إزالة كل دوريات {SPORT_CATEGORIES.get(sport_key,{}).get('flag','')}"
    else:
        # أضف الكل
        for k in sport_keys:
            selected.add(k)
        msg = f"✅ تم إضافة كل دوريات {SPORT_CATEGORIES.get(sport_key,{}).get('flag','')} ({len(sport_keys)})"
    prefs['leagues'] = list(selected)
    _set_user_sports(uid, prefs)
    bot.answer_callback_query(call.id, msg, show_alert=False)
    cat     = SPORT_CATEGORIES.get(sport_key, {})
    sel_new = [k for k in sport_keys if k in selected]
    text    = (
        f"{cat.get('flag','⚽')} *{cat.get('name','الدوريات')}*\n\n"
        f"المختار: {len(sel_new)} من {len(sport_keys)} دوري\n"
        "اضغط الدوري لإضافته ✅ أو إزالته"
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown",
                              reply_markup=_leagues_by_sport_keyboard(uid, sport_key, 0))
    except Exception as _exc:
        _log_exc(_exc)


@bot.callback_query_handler(func=lambda c: c.data == "sp_sports")
def cb_sports_categories(call):
    uid  = call.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    prefs = _get_user_sports(uid)
    sel   = len(prefs.get('leagues', []))
    text  = (
        "🏅 *اختر الرياضة التي تتابعها*\n\n"
        f"✅ مختار حالياً: {sel} دوري\n\n"
        "• اضغط الرياضة لعرض دورياتها\n"
        "• 🔴 = يدعم التتبع المباشر\n"
        "• 📋 = نتائج بدون تتبع مباشر"
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=_sport_categories_keyboard(uid))
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown",
                         reply_markup=_sport_categories_keyboard(uid))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_sport_"))
def cb_sports_sport_filter(call):
    raw = call.data.replace("sp_sport_", "")
    page = 0
    if "_p" in raw:
        sport_key, pg = raw.rsplit("_p", 1)
        page = int(pg)
    else:
        sport_key = raw
    uid = call.from_user.id
    cat = SPORT_CATEGORIES.get(sport_key, {})
    prefs = _get_user_sports(uid)
    sel = prefs.get('leagues', [])
    sport_sel = [k for k in sel if SPORTS_LEAGUES.get(k, {}).get('sport') == sport_key]
    text = (
        f"{cat.get('flag','⚽')} *{cat.get('name','الدوريات')}*\n\n"
        f"المختار: {len(sport_sel)} دوري\n"
        "اضغط الدوري لإضافته ✅ أو إزالته\n"
        "اضغط 👕 لاختيار فريق من الدوري"
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown",
                              reply_markup=_leagues_by_sport_keyboard(uid, sport_key, page))
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown",
                         reply_markup=_leagues_by_sport_keyboard(uid, sport_key, page))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_tms_"))
def cb_sports_teams_list(call):
    raw = call.data.replace("sp_tms_", "")
    # sp_tms_{league_key}_p{page}
    parts = raw.rsplit("_p", 1)
    league_key = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    uid = call.from_user.id
    league = SPORTS_LEAGUES.get(league_key, {})
    league_display = league.get('name','').replace('⚽ ','').replace('🏀 ','').replace('🏎️ ','')
    bot.answer_callback_query(call.id, "⏳ جاري جلب الفرق...")
    # إذا الفرق غير محمّلة في الكاش — نُحمّلها الآن مع إشعار "جاري التحميل"
    league = SPORTS_LEAGUES.get(league_key, {})
    espn = league.get('espn')
    if espn and espn not in _teams_cache:
          bot.answer_callback_query(call.id, "⏳ جاري تحميل قائمة الفرق...")
          def _load_teams_bg(_espn=espn, _lk=league_key, _pg=page,
                             _cid=call.message.chat.id,
                             _mid=call.message.message_id,
                             _uid=call.from_user.id, _ld=league_display):
              _get_league_teams(_espn)
              try:
                  kb2 = _teams_keyboard(_uid, _lk, _pg)
                  if not kb2:
                      return
                  prefs_r = _get_user_sports(_uid)
                  sel_ids = prefs_r.get('teams', {}).get(_lk, [])
                  id2name = {t['id']: t['name'] for t in _teams_cache.get(_espn, [])}
                  sel_nms = [id2name.get(i, i) for i in sel_ids]
                  sel_t   = "\n".join(f"  • {n}" for n in sel_nms[:10]) or "  لم تختر أي فريق"
                  txt2    = (f"👕 *فرق {_ld}*\n\n"
                             f"✅ فرقك المختارة ({len(sel_ids)}):\n{sel_t}\n\n"
                             "💡 اضغط على الفريق للإضافة أو الإزالة")
                  try:
                      bot.edit_message_text(txt2, _cid, _mid,
                                            parse_mode="Markdown", reply_markup=kb2)
                  except Exception as _exc:
                      _log_exc(_exc)
              except Exception as _exc:
                  _log_exc(_exc)
          threading.Thread(target=_load_teams_bg, daemon=True,
                           name="LoadTeams").start()
          return
    kb = _teams_keyboard(uid, league_key, page)
    if not kb:
        bot.answer_callback_query(call.id, "❌ لا تتوفر بيانات فرق لهذا الدوري")
        return
    prefs = _get_user_sports(uid)
    user_teams = prefs.get('teams', {})
    league_teams_sel = user_teams.get(league_key, [])
    sel_count = len(league_teams_sel)
    # أسماء الفرق المختارة من الكاش
    sel_names = []
    if espn and espn in _teams_cache:
        id_to_name = {t['id']: t['name'] for t in _teams_cache[espn]}
        sel_names = [id_to_name.get(tid, tid) for tid in league_teams_sel]
    sel_text = "\n".join(f"  • {n}" for n in sel_names[:10]) if sel_names else "  لم تختر أي فريق بعد"
    text = (
        f"👕 *فرق {league_display}*\n\n"
        f"✅ فرقك المختارة ({sel_count}):\n{sel_text}\n\n"
        "💡 يمكنك اختيار *أكثر من فريق* — اضغط على الفريق للإضافة أو الإزالة"
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=kb)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sp_tm_"))
def cb_sports_toggle_team(call):
    # sp_tm_{league_key}_{team_id}
    raw = call.data.replace("sp_tm_", "")
    # team_id قد يكون رقم — نقسم من اليمين مرة واحدة
    parts = raw.split("_", 1)
    if len(parts) < 2:
        bot.answer_callback_query(call.id)
        return
    league_key = parts[0]
    team_id = parts[1]
    # إذا league_key يحتوي _ نعيد المحاولة بأخذ كل شيء قبل آخر _
    # المنطق: league_key هي مفتاح موجود في SPORTS_LEAGUES
    # نبحث عن أطول prefix مطابق
    for possible_key in sorted(SPORTS_LEAGUES.keys(), key=len, reverse=True):
        if raw.startswith(possible_key + "_"):
            league_key = possible_key
            team_id = raw[len(possible_key)+1:]
            break
    uid = call.from_user.id
    prefs = _get_user_sports(uid)
    user_teams = prefs.setdefault('teams', {})
    sel = set(user_teams.get(league_key, []))
    league = SPORTS_LEAGUES.get(league_key, {})
    espn = league.get('espn')
    # جلب اسم الفريق من الكاش فقط — لا نستدعي ESPN هنا لتجنب التأخير
    team_name = team_id
    if espn and espn in _teams_cache:
        for t in _teams_cache[espn]:
            if t['id'] == team_id:
                team_name = t['name']
                break
    if team_id in sel:
        sel.discard(team_id)
        action = "أُزيل"
    else:
        sel.add(team_id)
        action = "أُضيف"
    user_teams[league_key] = list(sel)
    prefs['teams'] = user_teams
    _set_user_sports(uid, prefs)
    icon_a = "✅" if action == "أُضيف" else "❌"
    bot.answer_callback_query(call.id, f"{icon_a} {team_name} {action}")
    # تحديث قائمة الفرق (من الكاش — لا استدعاء HTTP جديد)
    league_display = league.get('name','').replace('⚽ ','').replace('🏀 ','').replace('🏎️ ','')
    kb = _teams_keyboard(uid, league_key, 0)
    prefs2 = _get_user_sports(uid)
    sel_count = len(prefs2.get('teams', {}).get(league_key, []))
    sel_names = []
    if espn and espn in _teams_cache:
        id_to_name = {t['id']: t['name'] for t in _teams_cache[espn]}
        sel_names = [id_to_name.get(tid, tid) for tid in prefs2.get('teams', {}).get(league_key, [])]
    sel_text = "\n".join(f"  • {n}" for n in sel_names[:10]) if sel_names else "  لم تختر أي فريق"
    text = (
        f"👕 *فرق {league_display}*\n\n"
        f"✅ فرقك المختارة ({sel_count}):\n{sel_text}\n\n"
        "💡 يمكنك اختيار *أكثر من فريق* — اضغط للإضافة أو الإزالة"
    )
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              parse_mode="Markdown", reply_markup=kb)
    except Exception as _exc:
        _log_exc(_exc)


# ═══════════════════════════════════════════════════════════════════
# أوامر وكولباكات الميزات الأسطورية
# ═══════════════════════════════════════════════════════════════════

# [إصلاح #1] النسخة الأولى من /verify حُذفت — النسخة المحسّنة موجودة في قسم الميزات الاستخباراتية

@bot.callback_query_handler(func=lambda c: c.data == "menu_sports")
def cb_menu_sports(call):
    bot.answer_callback_query(call.id)
    try:
        uid2 = call.from_user.id
        lang2 = users.get(str(uid2), {}).get("lang", "English 🇬🇧")
        prefs = _get_user_sports(uid2)
        selected = prefs.get('leagues', [])
        leagues_text = _ul(lang2, "sports_leagues", n=len(selected)) if selected else _ul(lang2, "sports_no_leagues")
        alerts_text = _ul(lang2, "sports_alerts_on") if prefs.get("live_alerts") else _ul(lang2, "sports_alerts_off")
        text = (
            _ul(lang2, "sports_title")
            + f"📊 {leagues_text}\n"
            + f"🔔 {alerts_text}\n\n"
            + _ul(lang2, "sports_choose")
        )
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown",
                         reply_markup=_sports_main_keyboard(uid2))
    except Exception:
        bot.send_message(call.message.chat.id, "أرسل /sports للرياضة")

