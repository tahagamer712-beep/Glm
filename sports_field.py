# -*- coding: utf-8 -*-
"""
  sports_field.py — رسم ملاعب نصية (كرة قدم/سلة/تنس/هوكي/بيسبول/أمريكية/كريكت)

  يُصدِّر دوال رسم الملاعب النصية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _event_to_emoji(ev_type: str, sport: str) -> str:
    """إيموجي مناسب لكل نوع حدث حسب الرياضة"""
    et = ev_type.lower()
    if sport == 'football':
        if any(k in et for k in ('goal', 'score')): return '⚽'
        if 'red card' in et or 'red' in et:         return '🟥'
        if 'yellow' in et or 'card' in et:          return '🟨'
        if 'penalty' in et or 'pen' in et:          return '🎯'
        if 'substitut' in et or 'sub' in et:        return '🔄'
        if 'offside' in et:                          return '🚩'
        if 'var' in et:                              return '📺'
        if 'half' in et or 'break' in et:           return '⏸'
        if 'corner' in et:                           return '🔵'
        if 'foul' in et:                             return '⚠️'
        if 'miss' in et or 'attempt' in et:         return '💨'
        if 'save' in et:                             return '🧤'
        if 'injury' in et:                           return '🏥'
    elif sport == 'basketball':
        if any(k in et for k in ('made', 'basket', '3pt', 'free throw')): return '🏀'
        if 'foul' in et:                             return '⚠️'
        if 'timeout' in et:                          return '⏸'
        if 'steal' in et:                            return '🤚'
        if 'block' in et:                            return '🛡'
    elif sport == 'tennis':
        if 'ace' in et:                              return '🎯'
        if 'set' in et:                              return '🎾'
        if 'double fault' in et:                    return '❌'
        if 'break' in et:                            return '💥'
    elif sport == 'racing':
        if 'pit' in et:                              return '🔧'
        if 'lead' in et or 'overtake' in et:        return '🏎️'
        if 'crash' in et or 'retire' in et:         return '💥'
        if 'safety car' in et:                      return '🚗'
        if 'podium' in et or 'finish' in et:        return '🏆'
    elif sport == 'hockey':
        if any(k in et for k in ('goal', 'score')): return '🏒'
        if 'penalty' in et:                          return '⏸'
    elif sport == 'baseball':
        if 'home run' in et:                         return '💣'
        if 'hit' in et:                              return '⚾'
        if 'strikeout' in et:                        return '❌'
    elif sport == 'american_football':
        if 'touchdown' in et:                        return '🏈'
        if 'field goal' in et:                       return '🎯'
        if 'interception' in et:                     return '🤚'
        if 'sack' in et:                             return '💥'
    return '•'



# ═══════════════════════════════════════════════════════════════════════════
# LIVE MATCH TEXT FIELD — عرض المباراة كملعب نصي تفاعلي
# يدعم كل الرياضات: كرة قدم / سلة / تنس / هوكي / بيسبول / كريكيت / أمريكي
# ═══════════════════════════════════════════════════════════════════════════

# ── إعدادات الميزة ──────────────────────────────────────────────────────
_LIVE_FIELD_ENABLED = True   # يمكن تعطيلها من /admin

# ── حالة الملعب لكل مباراة ──────────────────────────────────────────────
# match_id → {ball_x, ball_y, last_event, home_score, away_score,
#              clock, period, msg_ids: {uid: msg_id}, home, away,
#              sport, league_flag, league_name, last_event_id, anim_step}
_field_states: dict = {}
_field_lock = threading.Lock()

# ── أبعاد الملعب ─────────────────────────────────────────────────────────
_FIELD_W = 17   # عرض داخلي (أعمدة)
_FIELD_H = 7    # ارتفاع داخلي (صفوف)

# الموقع الابتدائي للكرة (وسط الملعب)
_BALL_START_X = _FIELD_W // 2
_BALL_START_Y = _FIELD_H // 2


def _build_football_field(bx: int, by: int, event_label: str = "") -> str:
    """يبني ملعب كرة قدم نصي مع الكرة في الموقع (bx, by)."""
    W, H = _FIELD_W, _FIELD_H
    rows = []
    # خط الهجوم/دفاع
    atk_col = W - 3
    def_col = 2

    for y in range(H):
        row = []
        for x in range(W):
            if x == bx and y == by:
                row.append("⚽")
            elif y == H // 2 and x == W // 2:
                row.append("·")   # وسط الملعب
            elif x == def_col and H // 4 <= y <= 3 * H // 4:
                row.append("|")   # منطقة جزاء يسار
            elif x == atk_col and H // 4 <= y <= 3 * H // 4:
                row.append("|")   # منطقة جزاء يمين
            else:
                row.append(" ")
        rows.append("│" + "".join(row) + "│")

    top    = "🥅" + "─" * W + "🥅"
    bottom = "🥅" + "─" * W + "🥅"
    mid_line = "├" + "─" * (W // 2) + "┼" + "─" * (W - W // 2 - 1) + "┤"
    # أدرج خط المنتصف في المنتصف
    half = H // 2
    rows.insert(half, mid_line)
    field = top + "\n" + "\n".join(rows) + "\n" + bottom
    if event_label:
        field += "\n" + event_label
    return field


def _build_basketball_court(bx: int, by: int, event_label: str = "") -> str:
    """ملعب سلة."""
    W, H = _FIELD_W, 5
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            if x == bx and y == by:
                row.append("🏀")
            elif y == H // 2 and (x == 1 or x == W - 2):
                row.append("O")   # سلة
            else:
                row.append(" ")
        rows.append("│" + "".join(row) + "│")
    top    = "╔" + "═" * W + "╗"
    bottom = "╚" + "═" * W + "╝"
    field = top + "\n" + "\n".join(rows) + "\n" + bottom
    if event_label:
        field += "\n" + event_label
    return field


def _build_tennis_court(bx: int, by: int, event_label: str = "") -> str:
    """ملعب تنس."""
    W, H = _FIELD_W, 5
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            if x == bx and y == by:
                row.append("🎾")
            elif x == W // 2:
                row.append("│")   # الشبكة
            else:
                row.append(" ")
        rows.append("[" + "".join(row) + "]")
    top    = "┌" + "─" * W + "┐"
    bottom = "└" + "─" * W + "┘"
    field = top + "\n" + "\n".join(rows) + "\n" + bottom
    if event_label:
        field += "\n" + event_label
    return field


def _build_hockey_rink(bx: int, by: int, event_label: str = "") -> str:
    """حلبة هوكي."""
    W, H = _FIELD_W, 5
    rows = []
    for y in range(H):
        row = []
        for x in range(W):
            if x == bx and y == by:
                row.append("🏒")
            elif y == H // 2 and x == W // 2:
                row.append("·")
            else:
                row.append(" ")
        rows.append("│" + "".join(row) + "│")
    top    = "🥅" + "─" * W + "🥅"
    bottom = "🥅" + "─" * W + "🥅"
    field = top + "\n" + "\n".join(rows) + "\n" + bottom
    if event_label:
        field += "\n" + event_label
    return field


def _build_baseball_diamond(score_txt: str = "", event_label: str = "") -> str:
    """ملعب بيسبول (diamond)."""
    lines_d = [
        "      2B",
        "    /    \\",
        "  3B      1B",
        "    \\    /",
        "      HP ⚾",
    ]
    diamond = "\n".join(lines_d)
    if score_txt:
        diamond += "\n" + score_txt
    if event_label:
        diamond += "\n" + event_label
    return diamond


def _build_american_football_field(bx: int, event_label: str = "") -> str:
    """ملعب كرة قدم أمريكي (شريط أفقي)."""
    W = _FIELD_W
    row = [" "] * W
    bx = max(0, min(W - 1, bx))
    row[bx] = "🏈"
    yard_line = "".join(row)
    field = "\n".join([
        "🏈───────────────🏈",
        "│" + yard_line + "│",
        "🏈───────────────🏈",
    ])
    if event_label:
        field += "\n" + event_label
    return field


def _build_cricket_field(event_label: str = "") -> str:
    """ملعب كريكيت دائري."""
    field = "\n".join([
        "    ╭───────────╮",
        "   /   OUTFIELD  \\",
        "  │   ┌───────┐   │",
        "  │   │  🏏   │   │",
        "  │   └───────┘   │",
        "   \\             /",
        "    ╰───────────╯",
    ])
    if event_label:
        field += "\n" + event_label
    return field


def _build_generic_field(sport: str, bx: int, by: int, event_label: str = "") -> str:
    """ملعب عام لأي رياضة."""
    emoji_map = {
        'football': '⚽', 'basketball': '🏀', 'tennis': '🎾',
        'hockey': '🏒', 'baseball': '⚾', 'american_football': '🏈',
        'cricket': '🏏', 'golf': '⛳', 'esports': '🎮', 'handball': '🤾',
    }
    ball = emoji_map.get(sport, '●')
    W, H = _FIELD_W, 5
    rows = []
    for y in range(H):
        row = [ball if (x == bx and y == by) else " " for x in range(W)]
        rows.append("│" + "".join(row) + "│")
    top    = "┌" + "─" * W + "┐"
    bottom = "└" + "─" * W + "┘"
    field = top + "\n" + "\n".join(rows) + "\n" + bottom
    if event_label:
        field += "\n" + event_label
    return field


def _build_sport_field(sport: str, bx: int, by: int, event_label: str = "",
                        score_txt: str = "") -> str:
    """يختار الدالة المناسبة لكل رياضة."""
    if sport == 'football':
        return _build_football_field(bx, by, event_label)
    elif sport == 'basketball':
        return _build_basketball_court(bx, by, event_label)
    elif sport == 'tennis':
        return _build_tennis_court(bx, by, event_label)
    elif sport == 'hockey':
        return _build_hockey_rink(bx, by, event_label)
    elif sport == 'baseball':
        return _build_baseball_diamond(score_txt, event_label)
    elif sport == 'american_football':
        return _build_american_football_field(bx, event_label)
    elif sport == 'cricket':
        return _build_cricket_field(event_label)
    else:
        return _build_generic_field(sport, bx, by, event_label)


def _event_to_ball_pos(ev_type: str, sport: str, current_x: int, current_y: int,
                        is_home: bool) -> tuple:
    """
    يُعيد (new_x, new_y, event_label) بناءً على نوع الحدث.
    is_home = True إذا الحدث للفريق المضيف (يهجم من اليسار).
    """
    W, H = _FIELD_W, _FIELD_H
    et = ev_type.lower()
    mid_x, mid_y = W // 2, H // 2

    # اتجاه الهجوم: المضيف يهجم يميناً، الضيف يساراً
    atk_x  = W - 2 if is_home else 1
    def_x  = 1     if is_home else W - 2
    goal_x = W - 1 if is_home else 0

    if sport == 'football':
        if any(k in et for k in ('goal', 'score')):
            return goal_x, H // 2, "⚽ *GOAL!* 🔥"
        if any(k in et for k in ('shot', 'attempt', 'save')):
            return atk_x, H // 2, "🎯 *Shot!*"
        if any(k in et for k in ('dangerous attack', 'attack')):
            return atk_x - (1 if is_home else -1), H // 2, "⚡ *Attack!*"
        if 'corner' in et:
            return atk_x, 0 if current_y > H // 2 else H - 1, "🔵 Corner"
        if 'penalty' in et:
            return atk_x, H // 2, "🎯 *Penalty!*"
        if any(k in et for k in ('free kick', 'foul')):
            return current_x, current_y, "⚠️ Foul"
        if 'offside' in et:
            return current_x, current_y, "🚩 Offside"
        if any(k in et for k in ('red card',)):
            return current_x, current_y, "🟥 Red Card!"
        if any(k in et for k in ('yellow card', 'card')):
            return current_x, current_y, "🟨 Yellow"
        if any(k in et for k in ('substitut', 'sub')):
            return current_x, current_y, "🔄 Sub"
        if any(k in et for k in ('half', 'break', 'end')):
            return mid_x, mid_y, "⏸ Half Time"
        if 'possession' in et or 'clearanc' in et:
            return def_x + (2 if is_home else -2), mid_y, ""
        return current_x, current_y, ""

    elif sport == 'basketball':
        if any(k in et for k in ('made', 'basket', '3pt', 'free throw', 'score')):
            return atk_x, H // 2, "🏀 *Score!*"
        if 'miss' in et:
            return atk_x, H // 2, "💨 Miss"
        if 'steal' in et:
            return mid_x, mid_y, "🤚 Steal!"
        if 'foul' in et:
            return current_x, current_y, "⚠️ Foul"
        if 'timeout' in et:
            return current_x, current_y, "⏸ Timeout"
        return current_x, current_y, ""

    elif sport == 'tennis':
        if 'ace' in et:
            return atk_x, mid_y, "🎯 *Ace!*"
        if 'set' in et:
            return mid_x, mid_y, "🎾 *Set!*"
        if 'double fault' in et:
            return current_x, current_y, "❌ D.Fault"
        if 'break' in et:
            return atk_x, mid_y, "💥 *Break!*"
        if 'game' in et:
            return atk_x, mid_y, "✅ Game"
        return mid_x if current_x > W // 2 else W // 2 + 1, mid_y, ""

    elif sport == 'hockey':
        if any(k in et for k in ('goal', 'score')):
            return goal_x, H // 2, "🏒 *GOAL!* 🔥"
        if 'shot' in et:
            return atk_x, H // 2, "🏒 Shot!"
        if 'penalty' in et:
            return current_x, current_y, "⏸ Penalty"
        return current_x, current_y, ""

    elif sport == 'american_football':
        if 'touchdown' in et:
            return goal_x, 0, "🏈 *TOUCHDOWN!* 🔥"
        if 'field goal' in et:
            return atk_x, 0, "🎯 Field Goal!"
        if 'interception' in et:
            return mid_x, 0, "🤚 Interception!"
        if 'sack' in et:
            return current_x - (2 if is_home else -2), 0, "💥 Sack!"
        if 'first down' in et:
            step = 3 if is_home else -3
            return min(W - 1, max(0, current_x + step)), 0, "➡️ 1st Down"
        return current_x, 0, ""

    else:
        return current_x, current_y, ""

