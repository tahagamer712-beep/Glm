# -*- coding: utf-8 -*-
"""
  sports_fixtures.py — جدول المباريات القادمة

  يُصدِّر دوال جدول المباريات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _get_upcoming_fixtures(espn_slug: str, days: int = 2) -> list:
    """يجلب المباريات القادمة من ESPN للأيام القادمة"""
    try:
        sport, league = espn_slug.split('/', 1)
        fixtures = []
        today = datetime.date.today()
        for i in range(days + 1):
            date_str = (today + datetime.timedelta(days=i)).strftime('%Y%m%d')
            url = (f"https://site.api.espn.com/apis/site/v2/sports"
                   f"/{sport}/{league}/scoreboard?dates={date_str}")
            try:
                r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    continue
                for event in r.json().get('events', []):
                    comp = event.get('competitions', [{}])[0]
                    state = comp.get('status', {}).get('type', {}).get('state', '')
                    competitors = comp.get('competitors', [])
                    if len(competitors) < 2:
                        continue
                    home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
                    away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
                    fixtures.append({
                        'id':        event.get('id', ''),
                        'name':      event.get('name', ''),
                        'date':      event.get('date', ''),
                        'state':     state,
                        'home':      home.get('team', {}).get('displayName', '?'),
                        'away':      away.get('team', {}).get('displayName', '?'),
                        'home_id':   str(home.get('team', {}).get('id', '')),
                        'away_id':   str(away.get('team', {}).get('id', '')),
                        'home_abbr': home.get('team', {}).get('abbreviation', '?'),
                        'away_abbr': away.get('team', {}).get('abbreviation', '?'),
                        'venue':     comp.get('venue', {}).get('fullName', ''),
                    })
            except Exception as _exc:
                _log_exc(_exc)
        return fixtures
    except Exception:
        return []


def _parse_espn_date(date_str: str):
    """يحول تاريخ ESPN / 365scores إلى datetime UTC (naive بدون timezone)"""
    for fmt in ('%Y-%m-%dT%H:%MZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.datetime.strptime(date_str[:len(fmt)].replace('Z',''), fmt.replace('Z',''))
        except Exception as _exc:
            _log_exc(_exc)
    try:
        dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # إذا كان timezone-aware، نحوّله إلى UTC naive
        if dt.tzinfo is not None:
            import datetime as _dt
            dt = dt.astimezone(_dt.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _send_schedule(uid, chat_id, msg_id=None):
    """
    إصلاح #2: يُظهر رسالة للدوريات بلا ESPN بدل تجاهلها.
    إصلاح #8: يستخدم _get_upcoming_fixtures بدل _get_live_scores لجلب المباريات القادمة.
    إصلاح #11: يُمرر tz_offset حسب لغة المستخدم.
    """
    prefs     = _get_user_sports(uid)
    selected  = prefs.get('leagues', [])
    tz_offset = _get_user_tz_offset(uid)

    if not selected:
        text = "📅 *جدول المباريات*\n\nاختر دورياتك أولاً من قائمة ⚽ اختر دورياتك"
    else:
        text = "📅 *جدول المباريات القادمة*\n\n"
        found_any = False
        for key in selected:
            league = SPORTS_LEAGUES.get(key)
            if not league:
                continue
            sport = league.get('sport', 'football')
            if not league.get('espn') and not league.get('scores365_id'):
                text += f"{league['flag']} *{league['name']}*\n"
                text += "  ⚠️ الجدول غير متاح لهذا الدوري حالياً\n\n"
                found_any = True
                continue
            all_matches = _get_matches_for_league(league)
            upcoming    = [m for m in all_matches if m['state'] == 'pre'][:5]
            if not upcoming:
                continue
            found_any = True
            text += f"{league['flag']} *{league['name']}*\n"
            for m in upcoming:
                text += f"  {_format_match_line(m, sport, tz_offset)}\n"
            text += "\n"
        if not found_any:
            text += "لا توجد مباريات قادمة في دورياتك المختارة 📭"

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 تحديث", callback_data="sp_schedule"),
        types.InlineKeyboardButton("🔴 مباشر", callback_data="sp_live"),
    )
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_main"))
    try:
        if msg_id:
            bot.edit_message_text(text[:4096], chat_id, msg_id, parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(chat_id, text[:4096], parse_mode="Markdown", reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text[:4096], parse_mode="Markdown", reply_markup=kb)
