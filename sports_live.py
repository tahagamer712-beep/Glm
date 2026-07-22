# -*- coding: utf-8 -*-
"""
  sports_live.py — broadcaster المباشر كل 10 ثواني

  يُصدِّر نظام البث الرياضي المباشر.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _render_live_field(match_id: str, lang: str = "العربية 🇮🇶") -> str:
    """يُولّد الرسالة الكاملة للمباراة مع الملعب النصي."""
    with _field_lock:
        st = _field_states.get(match_id)
    if not st:
        return ""

    sport      = st.get('sport', 'football')
    home       = st.get('home', '?')
    away       = st.get('away', '?')
    h_score    = st.get('home_score', '-')
    a_score    = st.get('away_score', '-')
    clock      = st.get('clock', '')
    period     = st.get('period', '')
    flag       = st.get('league_flag', '🏅')
    lname      = st.get('league_name', '')
    last_ev    = st.get('last_event', '')
    bx         = st.get('ball_x', _BALL_START_X)
    by         = st.get('ball_y', _BALL_START_Y)

    score_str  = f"`{h_score} - {a_score}`" if h_score != '-' else "--"
    clock_str  = f"⏱ {clock}" if clock else ""
    period_str = f"  {'ش' if lang == 'العربية 🇮🇶' else 'P'}{period}" if period else ""

    # بناء الرسالة
    header = (
        flag + " *" + lname + "*\n"
        + "🏠 *" + home + "*  " + score_str + "  *" + away + "* ✈️\n"
        + clock_str + period_str + "\n"
    )

    field_art = _build_sport_field(sport, bx, by,
                                   event_label=last_ev,
                                   score_txt=score_str)

    return "```\n" + header + "```\n`" + field_art + "`"


def _update_field_state(match_id: str, m: dict, sport: str,
                         league_flag: str, league_name: str,
                         play_event: dict = None):
    """
    يُحدّث حالة الملعب بناءً على بيانات المباراة وآخر حدث.
    m = dict المباراة من ESPN
    play_event = آخر حدث من play-by-play (اختياري)
    """
    with _field_lock:
        st = _field_states.setdefault(match_id, {
            'ball_x': _BALL_START_X, 'ball_y': _BALL_START_Y,
            'last_event': '', 'home_score': '-', 'away_score': '-',
            'clock': '', 'period': '', 'home': '?', 'away': '?',
            'sport': sport, 'league_flag': league_flag,
            'league_name': league_name, 'msg_ids': {},
            'last_event_id': '', 'anim_step': 0,
        })

        st['home']       = m.get('home', st['home'])
        st['away']       = m.get('away', st['away'])
        st['home_score'] = m.get('home_score', st['home_score'])
        st['away_score'] = m.get('away_score', st['away_score'])
        st['clock']      = m.get('clock', st['clock'])
        st['period']     = m.get('period', st['period'])
        st['sport']      = sport
        st['league_flag'] = league_flag
        st['league_name'] = league_name

        if play_event and play_event.get('id') != st['last_event_id']:
            ev_type  = play_event.get('type', '')
            ev_team  = play_event.get('team_id', '')
            home_id  = str(m.get('home_id', ''))
            is_home  = (ev_team == home_id) if ev_team else True

            new_x, new_y, label = _event_to_ball_pos(
                ev_type, sport,
                st['ball_x'], st['ball_y'], is_home
            )
            st['ball_x']       = max(0, min(_FIELD_W - 1, new_x))
            st['ball_y']       = max(0, min(_FIELD_H - 1, new_y))
            st['last_event']   = label
            st['last_event_id'] = play_event.get('id', '')
        elif m.get('state') == 'pre':
            # قبل المباراة: الكرة في المنتصف
            st['ball_x'] = _BALL_START_X
            st['ball_y'] = _BALL_START_Y
            st['last_event'] = ""


def _send_or_update_field(uid_s: str, match_id: str, lang: str):
    """يُرسل أو يُعدّل رسالة الملعب لمستخدم واحد."""
    try:
        rendered = _render_live_field(match_id, lang)
        if not rendered:
            return

        with _field_lock:
            st    = _field_states.get(match_id, {})
            msg_id = st.get('msg_ids', {}).get(uid_s)

        uid_int = int(uid_s)

        if msg_id:
            # حاول تعديل الرسالة الموجودة
            try:
                bot.edit_message_text(
                    rendered[:4096], uid_int, msg_id,
                    parse_mode="Markdown"
                )
                return
            except Exception as edit_err:
                err_s = str(edit_err).lower()
                if 'message is not modified' in err_s:
                    return   # لا تغيير — لا مشكلة
                if 'message to edit not found' in err_s or 'message_id_invalid' in err_s:
                    msg_id = None  # الرسالة انحذفت — أرسل جديدة

        # أرسل رسالة جديدة
        sent = bot.send_message(uid_int, rendered[:4096], parse_mode="Markdown")
        with _field_lock:
            if match_id in _field_states:
                _field_states[match_id]['msg_ids'][uid_s] = sent.message_id

    except Exception as _exc:
        _log_exc(_exc, f"_send_or_update_field uid={uid_s}")


def _cleanup_ended_fields(match_id: str):
    """يُنهي رسائل الملعب عند انتهاء المباراة."""
    with _field_lock:
        st = _field_states.pop(match_id, None)
    if not st:
        return
    # أرسل النتيجة النهائية
    home  = st.get('home', '?')
    away  = st.get('away', '?')
    hs    = st.get('home_score', '-')
    as_   = st.get('away_score', '-')
    flag  = st.get('league_flag', '🏅')
    lname = st.get('league_name', '')
    final_msg = (
        flag + " *" + lname + "*\n"
        + "🏆 *انتهت المباراة*\n\n"
        + "🏠 *" + home + "*  `" + hs + " - " + as_ + "`  *" + away + "* ✈️\n"
        + "⚡ النتيجة النهائية"
    )
    for uid_s, msg_id in st.get('msg_ids', {}).items():
        try:
            bot.edit_message_text(
                final_msg, int(uid_s), msg_id, parse_mode="Markdown"
            )
        except Exception:
            try:
                bot.send_message(int(uid_s), final_msg, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

# ─── قفل + تتبع إشعارات ما قبل المباراة ───────────────────────────
# FIX (SSOT): كان يُنشئ Event منفصلاً بنفس الاسم بدل مشاركة كائن state.py
# الوحيد مع sports_notifications.py — يُبطل الحماية من إرسال إشعارات مكررة.
_prematch_lock = gl._prematch_lock
_prematch_lock_ts = [0.0]

def _load_sports_cache():
    """
    تحميل كاش المباريات من الملف عند بدء التشغيل.
    إصلاح: يدعم كلاً من الصيغة القديمة (known_events)
    والصيغة الجديدة (known_ev_ids + known_pbp_ids).
    """
    global _sports_match_cache
    try:
        with open(_SPORTS_CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for mid, data in raw.items():
            # دعم الصيغة القديمة: known_events → known_ev_ids
            if 'known_events' in data and 'known_ev_ids' not in data:
                data['known_ev_ids']  = set(data.pop('known_events', []))
                data['known_pbp_ids'] = set()
            else:
                data['known_ev_ids']  = set(data.get('known_ev_ids',  []))
                data['known_pbp_ids'] = set(data.get('known_pbp_ids', []))
        _sports_match_cache = raw
    except Exception:
        _sports_match_cache = {}

def _save_sports_cache():
    """
    حفظ كاش المباريات في ملف.
    إصلاح: يحفظ known_ev_ids + known_pbp_ids بدلاً من known_events.
    """
    try:
        save_data = {}
        for mid, data in _sports_match_cache.items():
            # لا نحفظ المباريات المنتهية منذ أكثر من 30 دقيقة لتوفير المساحة
            if data.get('state') == 'post':
                ts = data.get('ended_at', 0)
                if ts and (time.time() - ts) > 1800:
                    continue
            save_data[mid] = {
                'state':         data.get('state', ''),
                'home_score':    data.get('home_score', '-'),
                'away_score':    data.get('away_score', '-'),
                'home_id':       data.get('home_id', ''),
                'away_id':       data.get('away_id', ''),
                'ended_at':      data.get('ended_at', 0),
                'known_ev_ids':  list(data.get('known_ev_ids',  set())),
                'known_pbp_ids': list(data.get('known_pbp_ids', set())),
            }
        with open(_SPORTS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False)
    except Exception as _exc:
        _log_exc(_exc)

_load_sports_cache()      # تحميل عند بدء التشغيل
_sports_broadcaster_lock = threading.Event()  # Event بدلاً من Lock لدعم الـ watchdog
_sports_lock_ts = [0.0]

def _sports_watchdog():
    """
    إصلاح #3: رفع timeout من 60s → 180s لأن البث قد يستغرق أكثر من دقيقة
    عند وجود عدة دوريات ومباريات حية تتطلب play-by-play.
    """
    while True:
        time.sleep(30)
        try:
            if _sports_broadcaster_lock.is_set() and time.time() - _sports_lock_ts[0] > 180:
                _sports_broadcaster_lock.clear()
        except Exception as _exc:
            _log_exc(_exc)
_start_thread_once("sports_watchdog", _sports_watchdog)

# ── ترجمة أحداث النتيجة لكل رياضة ولغة (خارج الدالة لتجنب مشكلة parsing) ──
_SPORTS_SCORE_EVENT_I18N = {
    'football':          {'العربية 🇮🇶': 'هدف جديد!', 'English 🇬🇧': 'Goal!', 'Русский 🇷🇺': 'Гол!', 'فارسی 🇮🇷': 'گل!', 'हिन्दी 🇮🇳': 'गोल!', 'Português 🇧🇷': 'Gol!', 'Türkçe 🇹🇷': 'Gol!', 'اردو 🇵🇰': 'گول!', 'Deutsch 🇩🇪': 'Tor!', 'Українська 🇺🇦': 'Гол!', 'Italiano 🇮🇹': 'Gol!', 'Español 🇲🇽': 'Gol!', 'Français 🇫🇷': 'But!'},
    'basketball':        {'العربية 🇮🇶': 'سلة!', 'English 🇬🇧': 'Basket!', 'Русский 🇷🇺': 'Мяч!', 'فارسی 🇮🇷': 'سبد!', 'हिन्दी 🇮🇳': 'बास्केट!', 'Português 🇧🇷': 'Cesta!', 'Türkçe 🇹🇷': 'Basket!', 'اردو 🇵🇰': 'باسکٹ!', 'Deutsch 🇩🇪': 'Korb!', 'Українська 🇺🇦': 'Гол!', 'Italiano 🇮🇹': 'Canestro!', 'Español 🇲🇽': 'Canasta!', 'Français 🇫🇷': 'Panier!'},
    'tennis':            {'العربية 🇮🇶': 'نقطة!', 'English 🇬🇧': 'Point!', 'Русский 🇷🇺': 'Очко!', 'فارسی 🇮🇷': 'امتیاز!', 'हिन्दी 🇮🇳': 'पॉइंट!', 'Português 🇧🇷': 'Ponto!', 'Türkçe 🇹🇷': 'Sayı!', 'اردو 🇵🇰': 'پوائنٹ!', 'Deutsch 🇩🇪': 'Punkt!', 'Українська 🇺🇦': 'Очко!', 'Italiano 🇮🇹': 'Punto!', 'Español 🇲🇽': 'Punto!', 'Français 🇫🇷': 'Point!'},
    'american_football': {'العربية 🇮🇶': 'Touchdown!', 'English 🇬🇧': 'Touchdown!', 'Русский 🇷🇺': 'Тачдаун!', 'فارسی 🇮🇷': 'Touchdown!', 'हिन्दी 🇮🇳': 'Touchdown!', 'Português 🇧🇷': 'Touchdown!', 'Türkçe 🇹🇷': 'Touchdown!', 'اردو 🇵🇰': 'Touchdown!', 'Deutsch 🇩🇪': 'Touchdown!', 'Українська 🇺🇦': 'Тачдаун!', 'Italiano 🇮🇹': 'Touchdown!', 'Español 🇲🇽': 'Touchdown!', 'Français 🇫🇷': 'Touchdown!'},
    'hockey':            {'العربية 🇮🇶': 'هدف!', 'English 🇬🇧': 'Goal!', 'Русский 🇷🇺': 'Гол!', 'فارسی 🇮🇷': 'گل!', 'हिन्दी 🇮🇳': 'गोल!', 'Português 🇧🇷': 'Gol!', 'Türkçe 🇹🇷': 'Gol!', 'اردو 🇵🇰': 'گول!', 'Deutsch 🇩🇪': 'Tor!', 'Українська 🇺🇦': 'Гол!', 'Italiano 🇮🇹': 'Gol!', 'Español 🇲🇽': 'Gol!', 'Français 🇫🇷': 'But!'},
    'baseball':          {'العربية 🇮🇶': 'ران!', 'English 🇬🇧': 'Run!', 'Русский 🇷🇺': 'Ран!', 'فارسی 🇮🇷': 'ران!', 'हिन्दी 🇮🇳': 'रन!', 'Português 🇧🇷': 'Corrida!', 'Türkçe 🇹🇷': 'Gol!', 'اردو 🇵🇰': 'رن!', 'Deutsch 🇩🇪': 'Lauf!', 'Українська 🇺🇦': 'Ран!', 'Italiano 🇮🇹': 'Punto!', 'Español 🇲🇽': 'Carrera!', 'Français 🇫🇷': 'Point!'},
    'cricket':           {'العربية 🇮🇶': 'ران!', 'English 🇬🇧': 'Run!', 'Русский 🇷🇺': 'Ран!', 'فارسی 🇮🇷': 'ران!', 'हिन्दी 🇮🇳': 'रन!', 'Português 🇧🇷': 'Ponto!', 'Türkçe 🇹🇷': 'Sayı!', 'اردو 🇵🇰': 'رن!', 'Deutsch 🇩🇪': 'Punkt!', 'Українська 🇺🇦': 'Ран!', 'Italiano 🇮🇹': 'Punto!', 'Español 🇲🇽': 'Punto!', 'Français 🇫🇷': 'Point!'},
    'racing':            {'العربية 🇮🇶': 'تغير الترتيب!', 'English 🇬🇧': 'Position change!', 'Русский 🇷🇺': 'Смена позиции!', 'فارسی 🇮🇷': 'تغییر جایگاه!', 'हिन्दी 🇮🇳': 'स्थान बदला!', 'Português 🇧🇷': 'Mudanca de posicao!', 'Türkçe 🇹🇷': 'Sıralama!', 'اردو 🇵🇰': 'ترتیب بدلا!', 'Deutsch 🇩🇪': 'Positionswechsel!', 'Українська 🇺🇦': 'Зміна позиції!', 'Italiano 🇮🇹': 'Cambio!', 'Español 🇲🇽': 'Cambio!', 'Français 🇫🇷': 'Changement!'},
    'golf':              {'العربية 🇮🇶': 'تغير الترتيب!', 'English 🇬🇧': 'Leaderboard change!', 'Русский 🇷🇺': 'Смена лидера!', 'فارسی 🇮🇷': 'تغییر رتبه!', 'हिन्दी 🇮🇳': 'स्थान बदला!', 'Português 🇧🇷': 'Mudanca!', 'Türkçe 🇹🇷': 'Sıralama!', 'اردو 🇵🇰': 'درجہ بندی!', 'Deutsch 🇩🇪': 'Rangänderung!', 'Українська 🇺🇦': 'Зміна лідера!', 'Italiano 🇮🇹': 'Cambio!', 'Español 🇲🇽': 'Cambio!', 'Français 🇫🇷': 'Changement!'},
}

def _sports_live_broadcaster():
    """
    بث رياضي مباشر مثل 365Score:
    ─ يكشف كل أحداث المباراة فور حدوثها (أهداف، بطاقات، جزاء، استبدال، نهاية...)
    ─ يفلتر حسب فريق المستخدم (إذا اختار فريقاً) أو الدوري كله
    ─ يستخدم ESPN play-by-play للأحداث التفصيلية
    ─ يعمل كل 10 ثواني لضمان أدنى تأخير ممكن
    """
    global _sports_match_cache
    if _sports_broadcaster_lock.is_set():
        return
    _sports_broadcaster_lock.set()
    _sports_lock_ts[0] = time.time()
    try:
        # ── 1. تجميع اشتراكات المستخدمين ─────────────────────────────
        # league_key → set of team_ids (أو '__all__' إذا اشترك بالدوري كله)
        league_team_map = {}   # league_key → {team_id → [(uid_s, lang)]}
        for uid_s, info in list(users.items()):
            prefs = info.get('sports', {})
            if not prefs.get('live_alerts'):
                continue
            lang = info.get('lang', 'العربية 🇮🇶')
            for lk in prefs.get('leagues', []):
                team_ids = list(prefs.get('teams', {}).get(lk, []))
                entry = league_team_map.setdefault(lk, {})
                if team_ids:
                    for tid in team_ids:
                        entry.setdefault(tid, []).append((uid_s, lang))
                else:
                    entry.setdefault('__all__', []).append((uid_s, lang))

        if not league_team_map:
            return

        # ── 2. جلب نتائج لكل دوري مطلوب (ESPN أو 365scores) ───────────
        fresh_matches = {}   # league_key → list of matches
        for key in league_team_map:
            league = SPORTS_LEAGUES.get(key)
            if not league or (not league.get('espn') and not league.get('scores365_id')):
                continue
            try:
                matches = _get_matches_for_league(league)
                if matches:
                    fresh_matches[key] = matches
            except Exception as _exc:
                _log_exc(_exc)

        if not fresh_matches:
            return

        # ── 3. جلب play-by-play للمباريات الحية (ESPN فقط) ────────────
        # نحصل على أحداث تفصيلية من ESPN summary API
        # دوريات 365scores (كالدوري العراقي) لا تدعم play-by-play حالياً
        pbp_events = {}  # match_id → [play_events]
        for key, matches in fresh_matches.items():
            league = SPORTS_LEAGUES.get(key, {})
            espn   = league.get('espn', '')
            if not espn:
                continue
            for m in matches:
                if m.get('state') != 'in':
                    continue
                mid = m.get('id', '')
                if mid and mid not in pbp_events:
                    try:
                        plays = _get_match_play_by_play(espn, mid)
                        if plays:
                            pbp_events[mid] = plays
                    except Exception as _exc:
                        _log_exc(_exc)

        # ── 4. كشف الأحداث الجديدة لكل مباراة ─────────────────────────
        # match_id → (league_key, list of alert strings, home_id, away_id)
        match_alerts = {}

        _SPORT_START = {'football':'🟢','basketball':'🟢','tennis':'🎾','racing':'🏁',
                        'hockey':'🏒','baseball':'⚾','american_football':'🏈','golf':'⛳','cricket':'🏏'}
        _SPORT_SCORE = {'football':'⚽','basketball':'🏀','tennis':'🎾','racing':'🏎️',
                        'hockey':'🏒','baseball':'⚾','american_football':'🏈','golf':'⛳','cricket':'🏏'}

        # ترجمة نصوص الأحداث لكل لغة
        _SPORT_I18N = {
            'match_started': {
                'العربية 🇮🇶': 'انطلقت المباراة الآن!',
                'English 🇬🇧':  'Match started now!',
                'Русский 🇷🇺':  'Матч начался!',
                'فارسی 🇮🇷':    'بازی شروع شد!',
                'हिन्दी 🇮🇳':   'मैच शुरू हुआ!',
                'Português 🇧🇷': 'Partida iniciada!',
                'Türkçe 🇹🇷':   'Maç başladı!',
                'اردو 🇵🇰':     'میچ شروع ہو گیا!',
                'Deutsch 🇩🇪':  'Spiel begonnen!',
                'Українська 🇺🇦': 'Матч розпочався!',
                'Italiano 🇮🇹': 'Partita iniziata!',
                'Español 🇲🇽':  '¡El partido comenzó!',
                'Français 🇫🇷': 'Match commencé!',
            },
            'live_tracking': {
                'العربية 🇮🇶': 'التتبع المباشر بدأ — سيصلك كل حدث فور وقوعه',
                'English 🇬🇧':  'Live tracking started — you will get every event instantly',
                'Русский 🇷🇺':  'Прямое отслеживание началось',
                'فارسی 🇮🇷':    'دنبال‌کردن زنده شروع شد',
                'हिन्दी 🇮🇳':   'लाइव ट्रैकिंग शुरू',
                'Português 🇧🇷': 'Acompanhamento ao vivo iniciado',
                'Türkçe 🇹🇷':   'Canlı takip başladı',
                'اردو 🇵🇰':     'لائیو ٹریکنگ شروع',
                'Deutsch 🇩🇪':  'Live-Tracking gestartet',
                'Українська 🇺🇦': 'Живе відстеження розпочато',
                'Italiano 🇮🇹': 'Tracciamento live avviato',
                'Español 🇲🇽':  'Seguimiento en vivo iniciado',
                'Français 🇫🇷': 'Suivi en direct démarré',
            },
            'match_ended': {
                'العربية 🇮🇶': 'انتهت المباراة',
                'English 🇬🇧':  'Match ended',
                'Русский 🇷🇺':  'Матч завершён',
                'فارسی 🇮🇷':    'بازی تمام شد',
                'हिन्दी 🇮🇳':   'मैच समाप्त',
                'Português 🇧🇷': 'Partida encerrada',
                'Türkçe 🇹🇷':   'Maç bitti',
                'اردو 🇵🇰':     'میچ ختم ہو گیا',
                'Deutsch 🇩🇪':  'Spiel beendet',
                'Українська 🇺🇦': 'Матч завершено',
                'Italiano 🇮🇹': 'Partita terminata',
                'Español 🇲🇽':  'Partido terminado',
                'Français 🇫🇷': 'Match terminé',
            },
            'final_result': {
                'العربية 🇮🇶': 'النتيجة النهائية',
                'English 🇬🇧':  'Final Result',
                'Русский 🇷🇺':  'Финальный счёт',
                'فارسی 🇮🇷':    'نتیجه نهایی',
                'हिन्दी 🇮🇳':   'अंतिम परिणाम',
                'Português 🇧🇷': 'Resultado Final',
                'Türkçe 🇹🇷':   'Final Skoru',
                'اردو 🇵🇰':     'حتمی نتیجہ',
                'Deutsch 🇩🇪':  'Endergebnis',
                'Українська 🇺🇦': 'Фінальний рахунок',
                'Italiano 🇮🇹': 'Risultato Finale',
                'Español 🇲🇽':  'Resultado Final',
                'Français 🇫🇷': 'Résultat Final',
            },
            'score_event': _SPORTS_SCORE_EVENT_I18N,
        }

        def _get_sport_text(key, lang, sport=None):
            """يُعيد النص الرياضي بلغة المستخدم."""
            if key == 'score_event':
                sport_map = _SPORT_I18N['score_event'].get(sport, _SPORT_I18N['score_event']['football'])
                return sport_map.get(lang, sport_map.get('English 🇬🇧', '⚽'))
            lang_map = _SPORT_I18N.get(key, {})
            return lang_map.get(lang, lang_map.get('العربية 🇮🇶', key))

        _SPORT_END   = {'football':'انتهت المباراة','basketball':'انتهت المباراة',
                        'tennis':'انتهت المباراة','racing':'انتهى السباق ✅',
                        'hockey':'انتهت المباراة','baseball':'انتهت المباراة',
                        'american_football':'انتهت المباراة','golf':'انتهت البطولة','cricket':'انتهت المباراة'}
        _SPORT_LABEL = {'football':'هدف جديد!','basketball':'سلة!','tennis':'نقطة!',
                        'racing':'تغيّر الترتيب!','hockey':'هدف!','baseball':'ران جديد!',
                        'american_football':'Touchdown!','golf':'تغيّر الترتيب!','cricket':'ران!'}

        for key, matches in fresh_matches.items():
            league     = SPORTS_LEAGUES.get(key, {})
            lname      = league.get('name', key)
            flag       = league.get('flag', '🏅')
            sport_type = league.get('sport', 'football')
            espn       = league.get('espn', '')

            s_start = _SPORT_START.get(sport_type, '🟢')
            s_score = _SPORT_SCORE.get(sport_type, '🏅')
            s_end   = _SPORT_END.get(sport_type, 'انتهى')
            s_label = _SPORT_LABEL.get(sport_type, 'حدث جديد!')

            for m in matches:
                match_id = m.get('id') or m.get('name', '')
                if not match_id:
                    continue

                prev          = _sports_match_cache.get(match_id, {})
                prev_state    = prev.get('state', '')
                prev_home     = prev.get('home_score', '-')
                prev_away     = prev.get('away_score', '-')
                prev_ev_ids   = prev.get('known_ev_ids', set())
                prev_pbp_ids  = prev.get('known_pbp_ids', set())

                curr_state    = m.get('state', '')
                curr_home     = m.get('home_score', '-')
                curr_away     = m.get('away_score', '-')
                home_id       = str(m.get('home_id', '')) if 'home_id' in m else ''
                away_id       = str(m.get('away_id', '')) if 'away_id' in m else ''

                # جمع home/away team ids من بيانات scoreboard
                comp_teams = {}  # team_name → team_id (نملأها من الأحداث)

                clock_str = f" ⏱{m['clock']}" if m.get('clock') else ''
                alerts    = []

                # ① انطلاق المباراة
                if curr_state == 'in' and prev_state not in ('in',):
                    alerts.append({'template': 'match_started', 'params': {
                        'emoji': s_start, 'flag': flag, 'lname': lname,
                    }})
                    notif_alert = (match_id, 'start')

                # ② نهاية المباراة
                if curr_state == 'post' and prev_state == 'in':
                    sc = f"`{curr_home} - {curr_away}`" if curr_home != '-' else ''
                    alerts.append({'template': 'match_ended', 'params': {
                        'flag': flag, 'lname': lname, 'score': sc,
                    }})

                # ③ أحداث scoreboard (details) الجديدة
                sc_events_raw = m.get('events', [])
                sc_event_ids  = {ev.get('display', '') for ev in sc_events_raw if ev.get('display')}
                new_sc_ids    = sc_event_ids - prev_ev_ids
                if new_sc_ids and curr_state == 'in':
                    new_sc_evs = [ev for ev in sc_events_raw if ev.get('display','') in new_sc_ids]
                    sc_str = f"`{curr_home}-{curr_away}`" if curr_home != '-' else ''
                    evs_text = "\n".join(f"  {ev['display']}" for ev in new_sc_evs)
                    alerts.append({'template': 'score', 'params': {
                        'emoji': s_score, 'flag': flag, 'lname': lname,
                        'score': sc_str, 'events': evs_text, 'clock': clock_str,
                    }})

                # ④ أحداث play-by-play التفصيلية (أهداف، بطاقات، استبدال...)
                pbp_plays     = pbp_events.get(match_id, [])
                new_pbp_plays = [p for p in pbp_plays if p['id'] and p['id'] not in prev_pbp_ids]
                new_pbp_ids   = {p['id'] for p in new_pbp_plays}
                for play in new_pbp_plays:
                    ptype  = play.get('type', '')
                    if not ptype:
                        continue
                    # فلترة الأحداث التافهة
                    pt_low = ptype.lower()
                    trivial = ('kick off', 'throw in', 'goal kick', 'gk', 'clearance',
                               'pass', 'dribble', 'cross', 'reception', 'rush', 'tackle')
                    if any(t in pt_low for t in trivial):
                        continue
                    emoji  = _event_to_emoji(ptype, sport_type)
                    if emoji == '•':   # حدث عادي بدون إيموجي خاص — تجاهله
                        continue
                    clock  = play.get('clock', '')
                    player = play.get('player', '')
                    hs     = play.get('home_score', '')
                    as_    = play.get('away_score', '')
                    sc_part   = f" `{hs}-{as_}`" if hs and as_ else ''
                    clk_part  = f" {clock}'" if clock else ''
                    plyr_part = f" *{player}*" if player else ''
                    period_p  = play.get('period', '')
                    per_part  = f" (ش{period_p})" if period_p and sport_type in ('football','hockey','basketball','american_football') else ''
                    alerts.append({'template': 'play', 'params': {
                        'emoji': emoji, 'ptype': ptype,
                        'player_part': plyr_part, 'clk_part': clk_part,
                        'per_part': per_part, 'flag': flag, 'lname': lname,
                        'sc_part': sc_part,
                    }})

                # ⑤ تغير النتيجة بدون حدث مسجل (fallback)
                if (curr_state == 'in' and prev_state == 'in'
                        and (curr_home != prev_home or curr_away != prev_away)
                        and not new_sc_ids and not new_pbp_ids):
                    sc_str = f"`{curr_home}-{curr_away}`" if curr_home != '-' else ''
                    alerts.append({'template': 'score', 'params': {
                        'emoji': s_score, 'flag': flag, 'lname': lname,
                        'score': sc_str, 'events': '', 'clock': clock_str,
                    }})

                if alerts:
                    match_alerts[match_id] = {
                        'league_key':  key,
                        'alerts':      alerts,       # للتوافق العكسي
                        'alerts_data': alerts,       # للترجمة المتعددة
                        'home':        m.get('home', '?'),
                        'away':        m.get('away', '?'),
                        'home_id':     m.get('home_id', home_id),
                        'away_id':     m.get('away_id', away_id),
                    }

                # ── إصلاح #5: تسجيل وقت انتهاء المباراة لتنظيف صحيح ──
                ended_at_ts = _sports_match_cache.get(match_id, {}).get('ended_at', 0)
                if curr_state == 'post' and prev_state == 'in':
                    ended_at_ts = time.time()

                # تحديث الكاش — إصلاح #1: الأسماء الصحيحة known_ev_ids + known_pbp_ids
                _sports_match_cache[match_id] = {
                    'state':         curr_state,
                    'home_score':    curr_home,
                    'away_score':    curr_away,
                    'home_id':       home_id,
                    'away_id':       away_id,
                    'ended_at':      ended_at_ts,
                    'known_ev_ids':  prev_ev_ids  | sc_event_ids,
                    'known_pbp_ids': prev_pbp_ids | new_pbp_ids,
                }

        # ── إصلاح #5: تنظيف المباريات المنتهية منذ >30 دقيقة فقط ──
        now_ts   = time.time()
        seen_ids = {m.get('id') or m.get('name','') for ms in fresh_matches.values() for m in ms}
        to_delete = []
        for mid, cdata in _sports_match_cache.items():
            if cdata.get('state') == 'post':
                et = cdata.get('ended_at', 0)
                # إذا انتهت ومرت 30 دقيقة أو غير موجودة في ESPN → احذف
                if (et and now_ts - et > 1800) or mid not in seen_ids:
                    to_delete.append(mid)
        for mid in to_delete:
            _sports_match_cache.pop(mid, None)

        _save_sports_cache()

        if not match_alerts:
            return

        # ── 5. تحديث الملاعب النصية + إرسال التنبيهات ─────────────────
        _msgs_sent_this_cycle = 0

        # تحديث حالة الملاعب لكل مباراة جديدة
        if _LIVE_FIELD_ENABLED:
            for key, matches in fresh_matches.items():
                league  = SPORTS_LEAGUES.get(key, {})
                sport   = league.get('sport', 'football')
                flag    = league.get('flag', '🏅')
                lname   = league.get('name', key)
                espn    = league.get('espn', '')
                for m in matches:
                    mid = m.get('id') or m.get('name', '')
                    if not mid or m.get('state') not in ('in', 'post'):
                        continue
                    # آخر حدث من play-by-play
                    latest_play = None
                    if espn and pbp_events.get(mid):
                        plays_list = pbp_events[mid]
                        if plays_list:
                            latest_play = plays_list[-1]
                    _update_field_state(mid, m, sport, flag, lname, latest_play)
                    # إذا انتهت المباراة → نظّف
                    if m.get('state') == 'post' and _field_states.get(mid, {}).get('state_prev') == 'in':
                        _AI_EXECUTOR.submit(_cleanup_ended_fields, mid)
                    with _field_lock:
                        if mid in _field_states:
                            _field_states[mid]['state_prev'] = m.get('state', '')

        for uid_s, info in list(users.items()):
            prefs = info.get('sports', {})
            if not prefs.get('live_alerts'):
                continue
            lang        = info.get('lang', 'العربية 🇮🇶')
            sel_leagues = set(prefs.get('leagues', []))
            user_teams  = prefs.get('teams', {})

            # ── تحديث الملعب النصي لهذا المستخدم ──────────────────────
            if _LIVE_FIELD_ENABLED:
                for key, matches in fresh_matches.items():
                    if key not in sel_leagues:
                        continue
                    league = SPORTS_LEAGUES.get(key, {})
                    sport2 = league.get('sport', 'football')
                    if sport2 == 'racing':
                        continue   # السيارات بدون ملعب نصي
                    sel_teams2 = set(user_teams.get(key, []))
                    for m2 in matches:
                        if m2.get('state') != 'in':
                            continue
                        mid2 = m2.get('id') or m2.get('name', '')
                        if not mid2:
                            continue
                        if sel_teams2:
                            h_id2 = str(m2.get('home_id', ''))
                            a_id2 = str(m2.get('away_id', ''))
                            if h_id2 not in sel_teams2 and a_id2 not in sel_teams2:
                                continue
                        _AI_EXECUTOR.submit(_send_or_update_field, uid_s, mid2, lang)

            user_msgs = []
            seen_alerts = set()
            for match_id, mdata in match_alerts.items():
                lk = mdata['league_key']
                if lk not in sel_leagues:
                    continue
                sel_teams = set(user_teams.get(lk, []))
                if sel_teams:
                    match_home = str(mdata.get('home_id', ''))
                    match_away = str(mdata.get('away_id', ''))
                    if match_home not in sel_teams and match_away not in sel_teams:
                        continue
                for alert_data in mdata.get('alerts_data', mdata['alerts']):
                    if isinstance(alert_data, dict):
                        # بنية جديدة: {template, params}
                        tmpl = alert_data.get('template', '')
                        params = alert_data.get('params', {})
                        lk2 = mdata['league_key']
                        league2 = SPORTS_LEAGUES.get(lk2, {})
                        sport2 = league2.get('sport', 'football')
                        # بناء النص بلغة المستخدم
                        _nl = '\n'
                        if tmpl == 'match_started':
                            _e = params.get('emoji', '🟢')
                            _f = params.get('flag', '🏅')
                            _ln = params.get('lname', '')
                            msg_txt = (
                                _e + ' *' + _get_sport_text('match_started', lang) + '*' + _nl
                                + _f + ' *' + _ln + '*' + _nl + _nl
                                + '🏠 *' + mdata['home'] + '*  vs  *' + mdata['away'] + '* ✈️' + _nl
                                + '🔴 ' + _get_sport_text('live_tracking', lang)
                            )
                        elif tmpl == 'match_ended':
                            sc = params.get('score', '')
                            _f = params.get('flag', '🏅')
                            _ln = params.get('lname', '')
                            msg_txt = (
                                '🏆 *' + _get_sport_text('match_ended', lang) + '*' + _nl
                                + _f + ' *' + _ln + '*' + _nl + _nl
                                + '🏠 *' + mdata['home'] + '*  ' + sc + '  *' + mdata['away'] + '* ✈️' + _nl
                                + '⚡ ' + _get_sport_text('final_result', lang)
                            )
                        elif tmpl == 'score':
                            sc = params.get('score', '')
                            evs = params.get('events', '')
                            clk = params.get('clock', '')
                            s_emoji = params.get('emoji', '⚽')
                            s_label = _get_sport_text('score_event', lang, sport=sport2)
                            _f = params.get('flag', '🏅')
                            _ln = params.get('lname', '')
                            msg_txt = (
                                s_emoji + ' *' + s_label + '*' + _nl
                                + _f + ' *' + _ln + '*' + _nl
                                + '🏠 *' + mdata['home'] + '* ' + sc + ' *' + mdata['away'] + '* ✈️' + clk
                                + (_nl + evs if evs else '')
                            )
                        elif tmpl == 'play':
                            _f = params.get('flag', '🏅')
                            _ln = params.get('lname', '')
                            msg_txt = (
                                params.get('emoji', '•') + ' *' + params.get('ptype', '') + '*'
                                + params.get('player_part', '') + params.get('clk_part', '')
                                + params.get('per_part', '') + _nl
                                + _f + ' *' + _ln + '*' + _nl
                                + '🏠 *' + mdata['home'] + '*' + params.get('sc_part', '') + ' *' + mdata['away'] + '* ✈️'
                            )
                        else:
                            msg_txt = str(alert_data)
                    else:
                        msg_txt = str(alert_data)

                    key = msg_txt[:80]
                    if key not in seen_alerts:
                        seen_alerts.add(key)
                        user_msgs.append(msg_txt)

            if user_msgs:
                for msg in user_msgs:
                    try:
                        bot.send_message(int(uid_s), msg[:4096], parse_mode="Markdown",
                                         disable_web_page_preview=True)
                        _msgs_sent_this_cycle += 1
                        # إصلاح #4: تأخير 60ms بين كل رسالة (≈16 رسالة/ثانية، أمان من flood)
                        time.sleep(0.06)
                        # إضافي: استراحة أطول كل 20 رسالة
                        if _msgs_sent_this_cycle % 20 == 0:
                            time.sleep(1.0)
                    except Exception as e:
                        err_str = str(e).lower()
                        if 'retry' in err_str or '429' in err_str:
                            # Flood control — انتظر
                            try:
                                retry_sec = int(''.join(c for c in err_str if c.isdigit()) or '5')
                            except Exception:
                                retry_sec = 5
                            time.sleep(min(retry_sec + 1, 30))
                        elif 'blocked' in err_str or 'deactivated' in err_str or 'not found' in err_str:
                            pass  # مستخدم حجب البوت
                        # تجاهل بقية الأخطاء بصمت

    except Exception as _exc:
        _log_exc(_exc)
    finally:
        _sports_broadcaster_lock.clear()



# ═══════════════════════════════════════════════════════════════════
# ███████╗ ███████╗  █████╗  ████████╗██╗   ██╗██████╗ ███████╗███████╗
# ██╔════╝ ██╔════╝ ██╔══██╗ ╚══██╔══╝██║   ██║██╔══██╗██╔════╝██╔════╝
# █████╗   █████╗   ███████║    ██║   ██║   ██║██████╔╝█████╗  ███████╗
# ██╔══╝   ██╔══╝   ██╔══██║    ██║   ██║   ██║██╔══██╗██╔══╝  ╚════██║
# ██║      ███████╗ ██║  ██║    ██║   ╚██████╔╝██║  ██║███████╗███████║
# ╚═╝      ╚══════╝ ╚═╝  ╚═╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝
# الميزات الأسطورية — AI Analysis + Crisis + Community + Dark Sources
# ═══════════════════════════════════════════════════════════════════

import collections

# ─── مصادر مظلمة: مواقع حكومية ورسمية عراقية ───────────────────────
DARK_SOURCES = [
    # البرلمان والحكومة
    {"url": "https://www.parliament.iq/", "base": "https://www.parliament.iq", "name": "البرلمان العراقي"},
    {"url": "https://pmo.iq/press/", "base": "https://pmo.iq", "name": "مجلس الوزراء"},
    {"url": "https://mof.gov.iq/", "base": "https://mof.gov.iq", "name": "وزارة المالية"},
    {"url": "https://www.cbi.iq/news", "base": "https://www.cbi.iq", "name": "البنك المركزي"},
    {"url": "https://oil.gov.iq/", "base": "https://oil.gov.iq", "name": "وزارة النفط"},
    {"url": "https://www.ihec.iq/", "base": "https://www.ihec.iq", "name": "المفوضية العليا للانتخابات"},
    # وكالات أنباء رسمية
    {"url": "https://www.ina.iq/", "base": "https://www.ina.iq", "name": "وكالة الأنباء العراقية"},
]

# ─── متابعة سرعة المصادر ─────────────────────────────────────────
_source_speed_log = collections.defaultdict(list)   # source → [timestamps]
_source_accuracy_log = collections.defaultdict(int) # source → verified_count

# ─── مراقبة الأزمات ───────────────────────────────────────────────
_crisis_keyword_freq = collections.defaultdict(list) # keyword → [timestamps]
_CRISIS_KEYWORDS = [
    "انفجار", "هجوم", "اغتيال", "اعتقال", "احتجاج", "تظاهر", "عاجل",
    "كارثة", "زلزال", "فيضان", "حريق", "اعلان الطوارئ", "حظر التجول",
    "explosion", "attack", "assassination", "protest", "emergency",
]
_CRISIS_FREQ_THRESHOLD = 5  # عدد المرات خلال 30 دقيقة = أزمة محتملة
_last_crisis_alert = {}  # keyword → timestamp

# ─── الأحداث الحية ───────────────────────────────────────────────
_live_events = {}  # uid → {"event": str, "started": float, "last_update": float, "updates": []}

# ─── أخبار المستخدمين المُبلَّغ عنها ─────────────────────────────
_user_submitted_queue = []  # [{"uid": uid, "text": str, "time": float}]
_verified_user_news_log = []  # قائمة الأخبار الموثقة

# ─── أرشيف الأخبار (آخر 7 أيام، 1500 عنصر) ──────────────────────
_news_archive: list = []          # [{title, url, source, lang, ts, summary, fact}]
_news_archive_lock = threading.Lock()
_NEWS_ARCHIVE_MAX  = 1500
_NEWS_ARCHIVE_DAYS = 7

# ─── غرفة الأزمات المتقدمة ──────────────────────────────────────
_crisis_room_active   = False
_crisis_room_keyword  = ""
_crisis_room_timeline: list = []  # [{time_str, text, source}]
_crisis_room_start    = 0.0
_crisis_room_lock     = threading.Lock()
_crisis_report_sent_at = 0.0       # آخر مرة أُرسل فيها تقرير

# ─── قاعدة تصريحات السياسيين ────────────────────────────────────
_politician_statements: dict = {}   # name → [{text, date, source}]
_politician_lock = threading.Lock()
POLITICIAN_NAMES_WATCH = [
    "السوداني", "بارزاني", "الحلبوسي", "المالكي", "الصدر",
    "هادي العامري", "برهم صالح", "الفياض", "السامرائي",
    "الخزعلي", "السيستاني", "الكاظمي",
]

# ─── مخزن الذكاء الجماعي (crowd tips) ──────────────────────────
_crowd_tips: list = []              # [{uid, text, time, status: pending|approved|rejected}]
_crowd_tips_lock = threading.Lock()
_CROWD_TIP_MAX = 300

# ─── إحصاءات اليوم (للتقرير اليومي) ────────────────────────────
_daily_new_users: list = []         # [uid] من انضم اليوم
_daily_new_users_lock = threading.Lock()

# ─── وسائل الإعلام الأجنبية (الخبر قبل الخبر) ──────────────────
_FOREIGN_INTEL_FEEDS = [
    # إيران
    "https://www.tasnimnews.com/ar/rss",
    "https://www.presstv.ir/Arabic/rss",
    "https://www.mehrnews.com/rss/",
    # السعودية والخليج
    "https://feeds.alarabiya.net/alarabiya",
    "https://www.skynewsarabia.com/rss.xml",
    # دولي عن العراق
    "https://feeds.bbci.co.uk/arabic/rss.xml",
    "https://feeds.feedburner.com/aljazeera/live",
    "https://www.reuters.com/rss",
]
_IRAQ_FILTER_WORDS = [
    "العراق", "Iraq", "بغداد", "Baghdad", "بصرة", "كربلاء",
    "الموصل", "اربيل", "الحشد", "الديناري", "النفط العراقي",
    "PMF", "Kurdistan", "Basra", "Mosul",
]
_foreign_intel_sent: set = set()    # عناوين مُرسلة مسبقاً
_foreign_intel_last_run = 0.0

# ═══════════════════════════════════════════════════════════════════
# 1. كشف الأخبار الكاذبة
# ═══════════════════════════════════════════════════════════════════
def handle_live_event_cmd(message):
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    text = message.text.replace('/live', '').strip()
    if not text:
        active = _live_events.get(str(uid))
        if active:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton(_ui("cmd_live_stop_btn", lang), callback_data="live_stop"))
            bot.send_message(message.chat.id,
                _ui("cmd_live_active", lang).format(event=escape_md(active['event'])),
                parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(message.chat.id, _ui("cmd_live_usage", lang), parse_mode="Markdown")
        return
    _live_events[str(uid)] = {
        "event": text,
        "started": time.time(),
        "last_update": 0,
        "updates": []
    }
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(_ui("cmd_live_stop_btn", lang), callback_data="live_stop"))
    bot.send_message(message.chat.id,
        _ui("cmd_live_started", lang).format(event=escape_md(text)),
        parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "live_stop")
def cb_live_stop(call):
    uid_s = str(call.from_user.id)
    lang = users.get(uid_s, {}).get("lang", "العربية 🇮🇶")
    if uid_s in _live_events:
        event = _live_events.pop(uid_s)["event"]
        bot.answer_callback_query(call.id)
        try:
            bot.edit_message_text(
                _ui("cmd_live_stopped", lang).format(event=escape_md(event)),
                call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception as _exc:
            _log_exc(_exc)
    else:
        bot.answer_callback_query(call.id, _ui("cmd_live_no_active", lang))

