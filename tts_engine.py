# -*- coding: utf-8 -*-
"""
  tts_engine.py — Edge TTS + أصوات اللغات

  يُصدِّر محرك تحويل النص إلى صوت وقائمة الأصوات.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _tts_generate(text, voice, out_path):
    """توليد ملف صوتي باستخدام edge-tts (مزامن)"""
    async def _run():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(out_path)
    # دائماً نُنشئ event loop جديد — آمن في البيئات متعددة الخيوط
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run())
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        loop.close()
