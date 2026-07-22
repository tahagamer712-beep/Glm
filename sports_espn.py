# -*- coding: utf-8 -*-
"""
  sports_espn.py — ESPN API + live scores + play-by-play

  يُصدِّر دوال ESPN API وبيانات النتائج المباشرة.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# ─── Module-level caches ─────────────────────────────────────────────────
_teams_cache: dict = {}
_teams_lock = threading.Lock()


def _get_live_scores(espn_slug: str) -> list:
    """جلب النتائج المباشرة من ESPN مع أحداث كاملة (أهداف، بطاقات، جزاء)"""
    try:
        sport, league = espn_slug.split('/', 1)
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        data = r.json()
        matches = []
        for event in data.get('events', []):
            comp = event.get('competitions', [{}])[0]
            status = comp.get('status', {})
            state = status.get('type', {}).get('state', '')
            desc = status.get('type', {}).get('description', '')
            clock = status.get('displayClock', '')
            period = status.get('period', 0)
            competitors = comp.get('competitors', [])
            if len(competitors) < 2:
                continue
            home = next((c for c in competitors if c.get('homeAway') == 'home'), competitors[0])
            away = next((c for c in competitors if c.get('homeAway') == 'away'), competitors[1])
            home_team_id = home.get('team', {}).get('id', '')

            # ── جلب أحداث المباراة من حقل details ──────────────────────
            match_events = []
            for detail in comp.get('details', []):
                try:
                    ev_type = detail.get('type', {}).get('text', '')
                    ev_type_lower = ev_type.lower()
                    ev_clock = detail.get('clock', {}).get('displayValue', '') or detail.get('clock', '')
                    if isinstance(ev_clock, dict):
                        ev_clock = ev_clock.get('displayValue', '')
                    team_id = str(detail.get('team', {}).get('id', ''))
                    athletes = detail.get('athletesInvolved', [])
                    player = athletes[0].get('displayName', '') if athletes else ''
                    h_score = str(detail.get('homeScore', ''))
                    a_score = str(detail.get('awayScore', ''))
                    team_abbr = (
                        home.get('team', {}).get('abbreviation', '?')
                        if team_id == home_team_id
                        else away.get('team', {}).get('abbreviation', '?')
                    )
                    # إيموجي الحدث
                    if any(k in ev_type_lower for k in ('goal', 'score', 'touchdown', 'basket')):
                        ev_emoji = '⚽'
                    elif 'red' in ev_type_lower:
                        ev_emoji = '🟥'
                    elif 'yellow' in ev_type_lower or 'card' in ev_type_lower:
                        ev_emoji = '🟨'
                    elif 'penalty' in ev_type_lower or 'pen' in ev_type_lower:
                        ev_emoji = '🎯'
                    elif 'substitut' in ev_type_lower or 'sub' in ev_type_lower:
                        ev_emoji = '🔄'
                    elif 'offside' in ev_type_lower:
                        ev_emoji = '🚩'
                    else:
                        ev_emoji = '•'
                    score_part = f" [{h_score}-{a_score}]" if h_score and a_score else ''
                    player_part = f" {player}" if player else ''
                    team_part = f" ({team_abbr})" if team_abbr and team_abbr != '?' else ''
                    clock_part = f"{ev_clock}'" if ev_clock else ''
                    display = f"{ev_emoji} {clock_part}{player_part}{team_part}{score_part}".strip()
                    match_events.append({
                        'type': ev_type,
                        'emoji': ev_emoji,
                        'clock': ev_clock,
                        'player': player,
                        'team_id': team_id,
                        'display': display,
                        'score': f"{h_score}-{a_score}" if h_score else '',
                    })
                except Exception as _exc:
                    _log_exc(_exc)

            matches.append({
                'home':       home.get('team', {}).get('displayName', '?'),
                'away':       away.get('team', {}).get('displayName', '?'),
                'home_abbr':  home.get('team', {}).get('abbreviation', '?'),
                'away_abbr':  away.get('team', {}).get('abbreviation', '?'),
                'home_id':    str(home.get('team', {}).get('id', '')),
                'away_id':    str(away.get('team', {}).get('id', '')),
                'home_score': home.get('score', '-'),
                'away_score': away.get('score', '-'),
                'state':      state,
                'desc':       desc,
                'clock':      clock,
                'period':     period,
                'date':       event.get('date', ''),
                'id':         event.get('id', ''),
                'name':       event.get('name', ''),
                'events':     match_events,
            })
        return matches
    except Exception:
        return []

def _get_league_teams(espn_slug: str) -> list:
    """جلب فرق الدوري من ESPN"""
    if espn_slug in _teams_cache:
        return _teams_cache[espn_slug]
    try:
        sport, league = espn_slug.split('/', 1)
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams?limit=50"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        sports_data = r.json().get('sports', [])
        if not sports_data:
            return []
        leagues_data = sports_data[0].get('leagues', [])
        if not leagues_data:
            return []
        teams = []
        for t in leagues_data[0].get('teams', []):
            team = t.get('team', {})
            teams.append({
                'id': str(team.get('id', '')),
                'name': team.get('displayName', team.get('name', '?')),
                'short': team.get('abbreviation', ''),
            })
        _teams_cache[espn_slug] = teams
        return teams
    except Exception:
        return []

# ─────────────────────────────────────────────────────────────────────
# نظام متابعة المباريات الكاملة — مثل 365Score
# ─────────────────────────────────────────────────────────────────────

def _get_match_play_by_play(espn_slug: str, event_id: str) -> list:
    """
    يجلب أحداث المباراة التفصيلية (play-by-play) من ESPN summary API.
    يُعيد قائمة أحداث: [{id, type, clock, period, player, home_score, away_score, text, team_id}]
    """
    try:
        sport, league = espn_slug.split('/', 1)
        url = (f"https://site.api.espn.com/apis/site/v2/sports"
               f"/{sport}/{league}/summary?event={event_id}")
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        data = r.json()
        plays = []

        # ── ملعب كرة القدم والأمريكية وباقي الرياضات ──
        for play in data.get('plays', []):
            play_type_obj = play.get('type', {})
            play_type = play_type_obj.get('text', '') or play_type_obj.get('name', '')
            clock_obj = play.get('clock', {})
            clock = clock_obj.get('displayValue', '') if isinstance(clock_obj, dict) else str(clock_obj)
            period = play.get('period', {})
            period_num = period.get('number', 0) if isinstance(period, dict) else period
            participants = play.get('participants', [])
            player = ''
            team_id = ''
            if participants:
                p0 = participants[0]
                athlete = p0.get('athlete', {})
                player = athlete.get('displayName', '')
                team_id = str(p0.get('team', {}).get('id', ''))
            plays.append({
                'id':         str(play.get('id', '')),
                'type':       play_type,
                'clock':      clock,
                'period':     period_num,
                'player':     player,
                'team_id':    team_id,
                'home_score': str(play.get('homeScore', '')),
                'away_score': str(play.get('awayScore', '')),
                'text':       play.get('text', ''),
            })

        # ── تنس وغولف: drives/holes/sets ──
        for hole in data.get('holes', []):
            plays.append({
                'id':      str(hole.get('id', hole.get('number', ''))),
                'type':    'Hole',
                'clock':   str(hole.get('number', '')),
                'period':  hole.get('number', 0),
                'player':  '',
                'team_id': '',
                'home_score': '',
                'away_score': '',
                'text':    hole.get('description', ''),
            })

        return plays
    except Exception:
        return []


def _send_live_scores(uid, chat_id, msg_id=None):
    """
    إصلاح #2: يُظهر رسالة واضحة للدوريات بلا ESPN (كالدوري العراقي)
    بدلاً من تجاهلها.
    إصلاح #11: يُمرر tz_offset حسب لغة المستخدم.
    """
    prefs       = _get_user_sports(uid)
    selected    = prefs.get('leagues', [])
    tz_offset   = _get_user_tz_offset(uid)
    lang        = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')

    if not selected:
        text = "⚽ *النتائج المباشرة*\n\nاختر دورياتك أولاً من قائمة ⚽ اختر دورياتك"
    else:
        text = "🔴 *النتائج المباشرة*\n\n"
        found_any = False
        for key in selected:
            league = SPORTS_LEAGUES.get(key)
            if not league:
                continue
            sport = league.get('sport', 'football')
            if not league.get('espn') and not league.get('scores365_id'):
                text += f"{league['flag']} *{league['name']}*\n"
                text += "  ⚠️ النتائج المباشرة غير متاحة لهذا الدوري حالياً\n\n"
                found_any = True
                continue
            matches   = _get_matches_for_league(league)
            live      = [m for m in matches if m['state'] == 'in']
            recent    = [m for m in matches if m['state'] == 'post'][:3]
            if not live and not recent:
                continue
            found_any = True
            text += f"{league['flag']} *{league['name']}*\n"
            for m in live:
                text += f"  {_format_match_line(m, sport, tz_offset)}\n"
            if not live:
                for m in recent:
                    text += f"  {_format_match_line(m, sport, tz_offset)}\n"
            text += "\n"
        if not found_any:
            text += "لا توجد مباريات مباشرة الآن في دورياتك المختارة 📭\n\nاضغط 📅 جدول المباريات لرؤية القادمة"

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("🔄 تحديث", callback_data="sp_live"),
        types.InlineKeyboardButton("📅 الجدول", callback_data="sp_schedule"),
    )
    kb.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="sp_main"))
    try:
        if msg_id:
            bot.edit_message_text(text[:4096], chat_id, msg_id, parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(chat_id, text[:4096], parse_mode="Markdown", reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, text[:4096], parse_mode="Markdown", reply_markup=kb)

def _preload_popular_teams():
    """يحمّل فرق أشهر 6 دوريات في الخلفية عند بدء البوت لتجنب التأخير"""
    _POPULAR = [
        "soccer/eng.1",       # البريميرليغ
        "soccer/esp.1",       # لاليغا
        "soccer/ger.1",       # البوندسليغا
        "soccer/ita.1",       # السيريا آ
        "soccer/fra.1",       # الدوري الفرنسي
        "soccer/ksa.1",       # الدوري السعودي
        "soccer/uefa.champions", # دوري الأبطال
    ]
    for slug in _POPULAR:
        try:
            if slug not in _teams_cache:
                _get_league_teams(slug)
                time.sleep(0.5)
        except Exception as _exc:
            _log_exc(_exc)
    _logger.info("✅ تم التحميل المسبق لفرق الدوريات الشهيرة")

_start_thread_once("TeamPreload", _preload_popular_teams)

# ======== رسالة الترحيب عند إضافة البوت للقناة/المجموعة ========
CHANNEL_WELCOME_MSG = (
   "👋 *أهلاً! تم تفعيل بوت الأخبار بنجاح في هذه القناة/المجموعة.*\n\n"
   "━━━━━━━━━━━━━━\n"
   "📋 *الأوامر المتاحة لأدمن القناة/المجموعة:*\n\n"
   "🌐 *تغيير لغة الأخبار:*\n"
   "`/setlang العربية 🇮🇶`\n"
   "`/setlang English 🇬🇧`\n"
   "`/setlang فارسی 🇮🇷`\n"
   "`/setlang Türkçe 🇹🇷`\n\n"
   "🏙 *تغيير المدينة:*\n"
   "`/setcity بغداد`\n\n"
   "📡 *مصادر الأخبار (RSS):*\n"
   "`/setsource رابط_RSS` — إضافة مصدر\n"
   "`/removesource رابط_RSS` — حذف مصدر\n"
   "`/listsources` — عرض المصادر\n\n"
   "⏸ *التحكم في البث:*\n"
   "`/pause` — إيقاف البث مؤقتاً\n"
   "`/resume` — استئناف البث\n\n"
   "⚙️ *الإعدادات:*\n"
   "`/settings` — عرض الإعدادات الحالية\n\n"
   "━━━━━━━━━━━━━━\n"
   "📰 سيبدأ إرسال الأخبار تلقائياً كل بضع دقائق.\n"
   f"🤖 @{BOT_USERNAME}"
)


# ═══════════════════════════════════════════════════════════════════
# أوامر الجيل الثاني
# ═══════════════════════════════════════════════════════════════════

