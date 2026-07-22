# -*- coding: utf-8 -*-
"""
  voice_news.py — أخبار صوتية + قائمة الاختيار

  يُصدِّر نظام الأخبار الصوتية.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403
# FIX: استيراد صريح للأسماء الضرورية
from bot_legacy import _orig_bot_send_message  # noqa: F811

def _bot_send_message_compat(chat_id, text, **kwargs):
    if "disable_web_page_preview" in kwargs and "link_preview_options" not in kwargs:
        _v = kwargs.pop("disable_web_page_preview")
        try:
            kwargs["link_preview_options"] = types.LinkPreviewOptions(is_disabled=bool(_v))
        except Exception:
            kwargs["disable_web_page_preview"] = _v
    return _orig_bot_send_message(chat_id, text, **kwargs)
bot.send_message = _bot_send_message_compat

