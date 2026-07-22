# -*- coding: utf-8 -*-
"""
  sports_365.py — 365scores API + مباريات

  يُصدِّر دوال 365scores API.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _get_365scores_matches(competition_id: int, days: int = 1) -> list:
    """
    يجلب مباريات أي دوري من 365scores API.
    يُستخدم للدوريات غير المغطاة في ESPN (مثل الدوري العراقي).
    يعيد نفس فورمات _get_live_scores() للتوافق الكامل.
    """
    try:
        today  = datetime.date.today()
        start  = (today - datetime.timedelta(days=1)).strftime('%d.%m.%Y')
        end    = (today + datetime.timedelta(days=days)).strftime('%d.%m.%Y')
        url    = (
            f"https://webws.365scores.com/web/games/?appTypeId=5&langId=1"
            f"&startDate={start}&endDate={end}&competitions={competition_id}"
        )
        r = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin":     "https://www.365scores.com",
        })
        if r.status_code != 200:
            return []
        data    = r.json()
        matches = []
        for sport in data.get('sports', []):
            for game in sport.get('games', []):
                home = game.get('homeCompetitor', {})
                away = game.get('awayCompetitor', {})
                sg   = game.get('statusGroup', 0)
                # statusGroup: 1=upcoming, 2=live/1st-half, 3=HT, 4=ended, 5=cancelled
                if   sg == 1:       state = 'pre'
                elif sg in (2, 3):  state = 'in'
                elif sg == 4:       state = 'post'
                else:               state = 'unknown'

                # gameTimeDisplay من 365scores يحتوي على الفاصلة العليا (مثل "7'")
                gt_disp = game.get('gameTimeDisplay', '').strip()
                gt_num  = str(int(game.get('gameTime', 0))) if game.get('gameTime') else ''
                if state == 'in':
                    # استخدم gameTimeDisplay إذا موجود، وإلا أضف الفاصلة
                    clock = gt_disp if gt_disp else (f"{gt_num}'" if gt_num else '')
                else:
                    clock = ''

                home_score = str(int(home.get('score', 0))) if home.get('score') is not None else '-'
                away_score = str(int(away.get('score', 0))) if away.get('score') is not None else '-'

                matches.append({
                    'id':         str(game.get('id', '')),
                    'name':       f"{home.get('name','?')} vs {away.get('name','?')}",
                    'home':       home.get('name', '?'),
                    'away':       away.get('name', '?'),
                    'home_abbr':  home.get('symbolicName', home.get('name','?')[:3].upper()),
                    'away_abbr':  away.get('symbolicName', away.get('name','?')[:3].upper()),
                    'home_score': home_score,
                    'away_score': away_score,
                    'home_id':    str(home.get('id', '')),
                    'away_id':    str(away.get('id', '')),
                    'state':      state,
                    'desc':       game.get('statusText', ''),
                    'clock':      clock,
                    'period':     1 if sg in (2, 3) else 0,
                    'date':       game.get('startTime', ''),
                    'events':     [],
                })
        return matches
    except Exception:
        return []


def _get_matches_for_league(league: dict) -> list:
    """
    دالة موحّدة لجلب مباريات أي دوري.
    تستخدم ESPN للدوريات الكبرى، و365scores للدوريات الأخرى (كالعراقي).
    """
    if league.get('espn'):
        return _get_live_scores(league['espn'])
    elif league.get('scores365_id'):
        return _get_365scores_matches(league['scores365_id'])
    return []


def _format_match_line(m: dict, sport: str = 'football', tz_offset: int = 3) -> str:
    """
    تنسيق سطر حدث رياضي واحد حسب نوع الرياضة.
    إصلاح #12: tz_offset يمرَّر من الخارج حسب لغة المستخدم (افتراضي +3 بغداد).
    """
    state = m.get('state', '')
    home  = m.get('home', '?')
    away  = m.get('away', '?')
    hs    = m.get('home_score', '-')
    as_   = m.get('away_score', '-')
    _live_icon = {
        'football':'🔴','basketball':'🔴','tennis':'🎾','racing':'🏎️',
        'hockey':'🏒','baseball':'⚾','american_football':'🏈','golf':'⛳','cricket':'🏏',
    }.get(sport, '🔴')
    _end_icon = '✅'
    if state == 'in':
        clock_part = f" ⏱{m['clock']}" if m.get('clock') else ''
        score_part = f" `{hs} - {as_}`" if hs != '-' else ''
        return f"{_live_icon} *{home}*{score_part} *{away}*{clock_part}"
    elif state == 'post':
        score_part = f" `{hs} - {as_}`" if hs != '-' else ''
        return f"{_end_icon} *{home}*{score_part} *{away}* (انتهت)"
    else:
        if m.get('date'):
            try:
                dt = datetime.datetime.strptime(m['date'][:16], '%Y-%m-%dT%H:%M')
                dt_local = dt + datetime.timedelta(hours=tz_offset)
                time_str = dt_local.strftime('%d/%m %H:%M')
            except Exception:
                time_str = ''
        else:
            time_str = ''
        return f"🕐 *{home}* vs *{away}*" + (f" — `{time_str}`" if time_str else "")
