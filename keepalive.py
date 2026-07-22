# -*- coding: utf-8 -*-
"""
  keepalive.py — HTTP Keep-Alive Server (اختياري)

  هذا الملف مُصمَّم أصلاً لـ Heroku/Replit لمنع سقوط الـ dyno.
  على Termux لا داعي لهذا الـ server لأن البوت يعمل كعملية محلية.

  FIX للتوافق مع Termux:
    • الـ server يبدأ فقط إذا كان متغير PORT مضبوطاً
    • أو إذا كان متغير KEEPALIVE_ENABLED=1
    • على Termux (لا PORT) يُتجاهَل بصمت

  يُصدِّر: _start_keepalive_server()
"""

import sys as _sys_legacy
import os
import threading
import time as _ka_time
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX: _sys_health قد تأتي من bot_legacy أو error_tracker — نُؤمِّن وجودها
if "_sys_health" not in dir():
    _sys_health: dict = {
        "ram_pct": 0.0, "cpu_pct": 0.0, "disk_pct": 0.0,
        "start_ts": _ka_time.time(), "recoveries": 0,
    }


def _start_keepalive_server():
    """
    يُشغّل HTTP server بسيط على PORT بيئي.
    يُجيب على /health بـ 200 OK.
    على Termux: يُتجاهَل إذا لم يُضبَط PORT أو KEEPALIVE_ENABLED.
    """
    # FIX: على Termux لا PORT → تجاهل الـ server تلقائياً
    _port_str = os.environ.get("PORT", "").strip()
    _keepalive_enabled = os.environ.get("KEEPALIVE_ENABLED", "0").strip() == "1"

    if not _port_str and not _keepalive_enabled:
        # بيئة Termux — لا داعي لـ HTTP server
        _logger.debug("KeepAlive: تم تعطيله (Termux mode — لا PORT مضبوط)")
        return

    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class _PingHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    uptime_s = int(time.time() - _sys_health.get("start_ts", time.time()))
                    uptime_h = uptime_s // 3600
                    uptime_m = (uptime_s % 3600) // 60
                    _user_count = len(users) if "users" in globals() else 0
                    body = (
                        f"OK | uptime={uptime_h}h{uptime_m}m"
                        f" | users={_user_count}"
                        f" | ram={_sys_health.get('ram_pct', 0):.0f}%"
                    ).encode("utf-8")
                except Exception:
                    body = b"OK"

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                pass  # تعطيل سجلات HTTP العادية

        port = int(_port_str) if _port_str else 8080
        srv = HTTPServer(("0.0.0.0", port), _PingHandler)
        _logger.info("🌐 Keep-Alive server يعمل على port %d", port)
        srv.serve_forever()
    except Exception as _kae:
        _logger.warning("_start_keepalive_server: %s", _kae)


# FIX: يبدأ فقط في بيئات السحابة (Heroku/Railway) — لا في Termux
_should_start = (
    os.environ.get("PORT", "").strip() != ""
    or os.environ.get("KEEPALIVE_ENABLED", "0") == "1"
)

if _should_start:
    threading.Thread(
        target=_start_keepalive_server,
        daemon=True,
        name="KeepAliveServer"
    ).start()
