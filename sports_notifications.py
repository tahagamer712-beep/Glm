# -*- coding: utf-8 -*-
"""
  sports_notifications.py — إشعارات ما قبل المباراة + watchdog

  يُصدِّر نظام إشعارات المباريات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _prematch_watchdog():
    while True:
        time.sleep(60)
        try:
            if _prematch_lock.is_set() and time.time() - _prematch_lock_ts[0] > 120:
                _prematch_lock.clear()
        except Exception as _exc:
            _log_exc(_exc)
_start_thread_once("prematch_watchdog", _prematch_watchdog)


def _prematch_notifier():
    """
    يرسل إشعارات مسبقة للمستخدمين:
    • قبل يوم كامل (20-28 ساعة)
    • قبل 45 دقيقة (30-65 دقيقة)
    يعمل كل 15 دقيقة بواسطة المجدول.
    """
    if _prematch_lock.is_set():
        return
    _prematch_lock.set()
    _prematch_lock_ts[0] = time.time()
    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # ── جمع اشتراكات المستخدمين ─────────────────────────────────
        # league_key → {team_id → [(uid_s, lang)]}
        league_team_users = {}
        for uid_s, info in list(users.items()):
            prefs = info.get('sports', {})
            if not prefs.get('live_alerts'):
                continue
            lang = info.get('lang', 'العربية 🇮🇶')
            for lk in prefs.get('leagues', []):
                team_ids = list(prefs.get('teams', {}).get(lk, []))
                entry = league_team_users.setdefault(lk, {})
                if team_ids:
                    for tid in team_ids:
                        entry.setdefault(tid, []).append((uid_s, lang))
                else:
                    entry.setdefault('__all__', []).append((uid_s, lang))

        if not league_team_users:
            return

        # ── جلب المباريات وإرسال الإشعارات ──────────────────────────
        for league_key, team_users in league_team_users.items():
            league = SPORTS_LEAGUES.get(league_key)
            if not league or (not league.get('espn') and not league.get('scores365_id')):
                continue
            flag      = league.get('flag', '🏅')
            lname     = league.get('name', league_key)
            sport     = league.get('sport', 'football')

            try:
                if league.get('espn'):
                    fixtures = _get_upcoming_fixtures(league['espn'], days=2)
                else:
                    # 365scores: نجلب المباريات القادمة من الـ match data مباشرة
                    all_m    = _get_365scores_matches(league['scores365_id'], days=2)
                    fixtures = [m for m in all_m if m['state'] == 'pre']
            except Exception:
                continue

            for fix in fixtures:
                if fix['state'] not in ('pre',):
                    continue
                match_id  = fix['id']
                if not match_id:
                    continue
                match_dt  = _parse_espn_date(fix['date'])
                if not match_dt:
                    continue
                delta_sec = (match_dt - now_utc).total_seconds()

                is_day_before = 20 * 3600 <= delta_sec <= 28 * 3600
                is_pre45      = 25 * 60   <= delta_sec <= 65 * 60

                if not (is_day_before or is_pre45):
                    continue

                # وقت المباراة بالتوقيت المحلي (+3 بغداد)
                local_dt     = match_dt + datetime.timedelta(hours=3)
                time_str_utc = match_dt.strftime('%H:%M')
                time_str_loc = local_dt.strftime('%H:%M')
                date_str     = local_dt.strftime('%d/%m/%Y')

                home_id = fix['home_id']
                away_id = fix['away_id']

                # تحديد المستخدمين المعنيين
                interested: list[tuple[str, str]] = []
                for tid, ulist in team_users.items():
                    if tid == '__all__' or tid in (home_id, away_id):
                        interested.extend(ulist)
                seen_uids = set()
                unique_interested = []
                for uid_s, lang in interested:
                    if uid_s not in seen_uids:
                        seen_uids.add(uid_s)
                        unique_interested.append((uid_s, lang))

                for uid_s, lang in unique_interested:
                    info      = users.get(uid_s, {})
                    notified  = info.setdefault('notified_matches', {})
                    nm        = notified.setdefault(match_id, {})

                    if is_day_before and not nm.get('day'):
                        sport_emoji = {'football':'⚽','basketball':'🏀','tennis':'🎾',
                            'racing':'🏎️','hockey':'🏒','baseball':'⚾',
                            'american_football':'🏈','golf':'⛳','cricket':'🏏'}.get(sport,'🏅')
                        msg = (
                            f"📅 *مباراة غداً!*\n"
                            f"{flag} *{lname}*\n\n"
                            f"{sport_emoji} *{fix['home']}*\n"
                            f"🆚\n"
                            f"{sport_emoji} *{fix['away']}*\n\n"
                            f"⏰ الموعد: `{time_str_loc}` (بغداد) — {date_str}\n"
                            f"🔔 ستصلك تنبيهات تلقائية لكل أحداث المباراة"
                        )
                        try:
                            bot.send_message(int(uid_s), msg, parse_mode="Markdown")
                            # إصلاح #9: حفظ timestamp مع الإشعار لتنظيف صحيح لاحقاً
                            nm['day'] = True
                            nm['ts']  = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).timestamp()
                        except Exception as _exc:
                            _log_exc(_exc)

                    elif is_pre45 and not nm.get('pre45'):
                        venue = f"\n🏟 {fix['venue']}" if fix.get('venue') else ''
                        # إصلاح #11: توقيت المنطقة حسب لغة المستخدم
                        tz_offsets = {
                            'العربية 🇮🇶': 3, 'العربية السعودية 🇸🇦': 3,
                            'العربية المصرية 🇪🇬': 2, 'العربية السورية 🇸🇾': 3,
                            'العربية الكويتية 🇰🇼': 3, 'العربية الإماراتية 🇦🇪': 4,
                            'English 🇬🇧': 0, 'Français 🇫🇷': 1,
                        }
                        tz_off    = tz_offsets.get(lang, 3)
                        local_dt_ = match_dt + datetime.timedelta(hours=tz_off)
                        time_str_user = local_dt_.strftime('%H:%M')
                        msg = (
                            f"⏳ *بعد أقل من ساعة!*\n"
                            f"{flag} *{lname}*\n\n"
                            f"🏠 *{fix['home']}*\n"
                            f"🆚\n"
                            f"✈️ *{fix['away']}*\n\n"
                            f"⏰ `{time_str_user}` (توقيتك){venue}\n"
                            f"🔴 يبدأ التتبع المباشر فور الانطلاق"
                        )
                        try:
                            bot.send_message(int(uid_s), msg, parse_mode="Markdown")
                            nm['pre45'] = True
                            nm['ts']    = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).timestamp()
                        except Exception as _exc:
                            _log_exc(_exc)

        # إصلاح #7: تنظيف الإشعارات القديمة (+48h) بحذف الإدخالات الفردية لا الكل
        now_utc_ts = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).timestamp()
        for uid_s, info in list(users.items()):
            nm_dict = info.get('notified_matches', {})
            if len(nm_dict) > 100:
                # احذف المباريات التي مضى عليها أكثر من 48 ساعة
                old_keys = [
                    mid for mid, v in nm_dict.items()
                    if isinstance(v, dict) and v.get('ts', now_utc_ts) < now_utc_ts - 172800
                ]
                if old_keys:
                    for k in old_keys:
                        nm_dict.pop(k, None)
                elif len(nm_dict) > 300:
                    # fallback: إذا لم تحمل timestamps احذف الأقدم نصف
                    old_keys = list(nm_dict.keys())[:len(nm_dict)//2]
                    for k in old_keys:
                        nm_dict.pop(k, None)

    except Exception as _exc:
        _log_exc(_exc)
    finally:
        _prematch_lock.clear()

