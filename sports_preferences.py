# -*- coding: utf-8 -*-
"""
  sports_preferences.py — تفضيلات المستخدم (دوري/فريق/توقيت)

  يُصدِّر دوال تفضيلات الرياضة للمستخدم.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _get_user_sports(uid) -> dict:
    prefs = users.get(str(uid), {}).get('sports', {})
    if not prefs:
        prefs = {'leagues': [], 'teams': {}, 'live_alerts': False}
    # ترقية: إذا teams كانت list قديمة → حوّلها لـ dict
    if isinstance(prefs.get('teams'), list):
        prefs['teams'] = {}
    if 'teams' not in prefs:
        prefs['teams'] = {}
    if 'leagues' not in prefs:
        prefs['leagues'] = []
    return prefs

def _set_user_sports(uid, prefs: dict):
    uid_s = str(uid)
    if uid_s not in users:
        users[uid_s] = {}
    users[uid_s]['sports'] = prefs
    save_users()

# تصنيفات الرياضة
SPORT_CATEGORIES = {
    "football":          {"name": "⚽ كرة القدم",               "flag": "⚽",  "count": 0},
    "basketball":        {"name": "🏀 كرة السلة",               "flag": "🏀",  "count": 0},
    "tennis":            {"name": "🎾 التنس",                   "flag": "🎾",  "count": 0},
    "racing":            {"name": "🏎️ سباقات السيارات",         "flag": "🏎️", "count": 0},
    "hockey":            {"name": "🏒 هوكي الجليد",             "flag": "🏒",  "count": 0},
    "baseball":          {"name": "⚾ البيسبول",                "flag": "⚾",  "count": 0},
    "american_football": {"name": "🏈 كرة القدم الأمريكية",     "flag": "🏈",  "count": 0},
    "golf":              {"name": "⛳ الغولف",                   "flag": "⛳",  "count": 0},
    "cricket":           {"name": "🏏 الكريكيت",                "flag": "🏏",  "count": 0},
    "handball":          {"name": "🤾 كرة اليد",                "flag": "🤾",  "count": 0},
    "esports":           {"name": "🎮 رياضات إلكترونية",        "flag": "🎮",  "count": 0},
}

def _get_sport_league_count(sport_key: str, selected: set) -> tuple:
    """يُعيد (إجمالي الدوريات، المختارة) لرياضة معينة."""
    all_leagues = [k for k,v in SPORTS_LEAGUES.items() if v.get('sport') == sport_key]
    sel_count   = sum(1 for k in all_leagues if k in selected)
    return len(all_leagues), sel_count

# كاش الفرق (league_key → list of teams)
_teams_cache = {}

def _get_user_tz_offset(uid) -> int:
    """إصلاح #11: يُعيد offset المنطقة الزمنية بالساعات حسب لغة المستخدم"""
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶') or 'العربية 🇮🇶'
    return {
        'العربية 🇮🇶': 3, 'العربية السعودية 🇸🇦': 3, 'العربية الكويتية 🇰🇼': 3,
        'العربية السورية 🇸🇾': 3, 'العربية اليمنية 🇾🇪': 3, 'العربية الأردنية 🇯🇴': 3,
        'العربية المصرية 🇪🇬': 2, 'العربية الليبية 🇱🇾': 2, 'العربية التونسية 🇹🇳': 1,
        'العربية الجزائرية 🇩🇿': 1, 'العربية المغربية 🇲🇦': 1,
        'العربية الإماراتية 🇦🇪': 4, 'العربية البحرينية 🇧🇭': 3, 'العربية القطرية 🇶🇦': 3,
        'English 🇬🇧': 0, 'Français 🇫🇷': 1, 'Deutsch 🇩🇪': 1,
        'Español 🇪🇸': 1, 'Türkçe 🇹🇷': 3, 'فارسی 🇮🇷': 3,
    }.get(lang, 3)
