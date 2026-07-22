# -*- coding: utf-8 -*-
"""
  sports_keyboards.py — قوائم وأزرار الرياضة

  يُصدِّر دوال بناء قوائم وأزرار واجهة الرياضة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _sports_main_keyboard(uid):
    prefs       = _get_user_sports(uid)
    alerts_icon = "🔔" if prefs.get('live_alerts') else "🔕"
    sel_leagues = prefs.get('leagues', [])
    sel_teams   = sum(len(v) for v in prefs.get('teams', {}).values())
    n_leagues   = len(sel_leagues)
    n_teams     = sel_teams
    # ملخص الرياضات المختارة
    sport_summary = {}
    for lk in sel_leagues:
        sp = SPORTS_LEAGUES.get(lk, {}).get('sport', '')
        if sp:
            sport_summary[sp] = sport_summary.get(sp, 0) + 1
    sports_line = " • ".join(
        f"{SPORT_CATEGORIES.get(sp,{}).get('flag','')}{cnt}"
        for sp, cnt in list(sport_summary.items())[:5]
    )
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔴 نتائج مباشرة", callback_data="sp_live"),
        types.InlineKeyboardButton("📅 جدول المباريات", callback_data="sp_schedule"),
    )
    sel_label = f"🏅 دورياتي ({n_leagues})" if n_leagues else "🏅 اختر رياضتك"
    if sports_line:
        sel_label += f"  {sports_line}"
    kb.add(types.InlineKeyboardButton(sel_label, callback_data="sp_sports"))
    if n_teams > 0:
        kb.add(types.InlineKeyboardButton(f"👕 فرقي المتابَعة ({n_teams})", callback_data="sp_myteams"))
    kb.add(
        types.InlineKeyboardButton("📰 أخبار رياضية", callback_data="sp_news"),
        types.InlineKeyboardButton(f"{alerts_icon} تنبيهات مباشرة", callback_data="sp_toggle_alerts"),
    )
    kb.add(
        types.InlineKeyboardButton("🏟 ملعب مباشر" if _LIVE_FIELD_ENABLED else "🏟 ملعب (معطّل)", callback_data="sp_toggle_field"),
        types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"),
    )
    return kb

def _sport_categories_keyboard(uid=None):
    """قائمة تصنيفات الرياضة مع عدد الدوريات والمختارة"""
    kb = types.InlineKeyboardMarkup(row_width=2)
    selected = set()
    if uid:
        prefs = _get_user_sports(uid)
        selected = set(prefs.get('leagues', []))
    row = []
    for cat_key, cat in SPORT_CATEGORIES.items():
        total, sel_cnt = _get_sport_league_count(cat_key, selected)
        if total == 0:
            continue
        sel_badge = f" ✅{sel_cnt}" if sel_cnt > 0 else ""
        label = f"{cat['flag']} {cat['name']}{sel_badge}"
        btn = types.InlineKeyboardButton(label, callback_data=f"sp_sport_{cat_key}")
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    # زر "اختر الكل" لكل رياضة
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_main"))
    return kb

def _leagues_by_sport_keyboard(uid, sport_key: str, page=0):
    """دوريات مفلترة حسب الرياضة — محسّنة مع دعم كامل لكل الرياضات"""
    prefs       = _get_user_sports(uid)
    sel_leagues = set(prefs.get('leagues', []))
    keys        = [k for k, v in SPORTS_LEAGUES.items() if v.get('sport') == sport_key]
    per_page    = 8
    start       = page * per_page
    chunk       = keys[start:start + per_page]
    total       = len(keys)
    cat         = SPORT_CATEGORIES.get(sport_key, {})
    kb          = types.InlineKeyboardMarkup(row_width=1)

    if not chunk:
        kb.add(types.InlineKeyboardButton("⚠️ لا توجد دوريات لهذه الرياضة", callback_data="noop"))
        kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_sports"))
        return kb

    # زر "✅ اختر الكل / ❌ أزل الكل" لهذه الرياضة
    all_selected = all(k in sel_leagues for k in keys)
    select_all_label = "❌ أزل جميع دوريات " + cat.get("flag","") if all_selected else "✅ اختر جميع دوريات " + cat.get("flag","")
    kb.add(types.InlineKeyboardButton(select_all_label, callback_data=f"sp_allsport_{sport_key}"))
    kb.add(types.InlineKeyboardButton("─────────────", callback_data="noop"))

    for key in chunk:
        league        = SPORTS_LEAGUES[key]
        is_selected   = key in sel_leagues
        icon          = "✅" if is_selected else "○"
        has_espn      = bool(league.get('espn'))
        has_365       = bool(league.get('scores365_id'))
        live_badge    = " 🔴" if has_espn or has_365 else " 📋"
        league_name   = league['name']
        # أضف زر الدوري نفسه
        kb.add(types.InlineKeyboardButton(
            f"{icon} {league['flag']} {league_name}{live_badge}",
            callback_data=f"sp_tog_{key}_s{sport_key}_p{page}"
        ))
        # زر اختيار فريق (فقط للدوريات التي عندها ESPN)
        if is_selected and has_espn and sport_key not in ('racing', 'golf', 'esports', 'cricket'):
            kb.add(types.InlineKeyboardButton(
                f"   👕 اختر فريق محدد",
                callback_data=f"sp_tms_{key}_p0"
            ))

    # شريط التنقل مع عداد الصفحة
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton(f"◀️ السابق", callback_data=f"sp_sport_{sport_key}_p{page-1}"))
    page_info = f"  {page+1}/{(total-1)//per_page+1}  "
    nav.append(types.InlineKeyboardButton(page_info, callback_data="noop"))
    if start + per_page < total:
        nav.append(types.InlineKeyboardButton(f"التالي ▶️", callback_data=f"sp_sport_{sport_key}_p{page+1}"))
    if len(nav) > 1:
        kb.row(*nav)

    kb.add(types.InlineKeyboardButton("🔙 رجوع للرياضات", callback_data="sp_sports"))
    return kb

def _teams_keyboard(uid, league_key: str, page=0):
    """قائمة فرق الدوري مع اختيار المستخدم"""
    prefs = _get_user_sports(uid)
    user_teams = prefs.get('teams', {})
    sel_teams = set(user_teams.get(league_key, []))
    league = SPORTS_LEAGUES.get(league_key, {})
    espn = league.get('espn')
    if not espn:
        return None
    teams = _get_league_teams(espn)
    if not teams:
        return None
    per_page = 8
    start = page * per_page
    chunk = teams[start:start + per_page]
    league_display = league.get('name','').replace('⚽ ','').replace('🏀 ','').replace('🏎️ ','')
    kb = types.InlineKeyboardMarkup(row_width=2)
    row = []
    for team in chunk:
        icon = "✅" if team['id'] in sel_teams else "○"
        btn = types.InlineKeyboardButton(f"{icon} {team['name']}", callback_data=f"sp_tm_{league_key}_{team['id']}")
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀️", callback_data=f"sp_tms_{league_key}_p{page-1}"))
    if start + per_page < len(teams):
        nav.append(types.InlineKeyboardButton("▶️", callback_data=f"sp_tms_{league_key}_p{page+1}"))
    if nav:
        kb.row(*nav)
    sport_key = league.get('sport', 'football')
    kb.add(types.InlineKeyboardButton(f"🔙 رجوع للدوريات", callback_data=f"sp_sport_{sport_key}"))
    return kb

def _sports_leagues_keyboard(uid, page=0):
    """قائمة كل الدوريات (للتوافق القديم)"""
    prefs = _get_user_sports(uid)
    selected = set(prefs.get('leagues', []))
    keys = list(SPORTS_LEAGUES.keys())
    per_page = 8
    start = page * per_page
    chunk = keys[start:start + per_page]
    kb = types.InlineKeyboardMarkup(row_width=1)
    for key in chunk:
        league = SPORTS_LEAGUES[key]
        icon = "✅ " if key in selected else ""
        kb.add(types.InlineKeyboardButton(f"{icon}{league['flag']} {league['name'].replace('⚽ ','').replace('🏀 ','').replace('🏎️ ','')}", callback_data=f"sp_tog_{key}_s{league.get('sport','')}"))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"sp_leagues_p{page-1}"))
    if start + per_page < len(keys):
        nav.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"sp_leagues_p{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_sports"))
    return kb
