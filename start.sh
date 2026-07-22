#!/data/data/com.termux/files/usr/bin/bash
# ══════════════════════════════════════════════════════
# IraqNow Bot — سكريبت تشغيل Termux
# الاستخدام: bash start.sh
# ══════════════════════════════════════════════════════

# ── التحقق من متغيرات البيئة الإلزامية ─────────────────
if [ -z "$BOT_TOKEN" ] && [ ! -f ".env" ]; then
    echo "❌ خطأ: BOT_TOKEN غير مضبوط."
    echo ""
    echo "الحل:"
    echo "  أنشئ ملف .env بالمحتوى التالي:"
    echo "    BOT_TOKEN=توكن_البوت_هنا"
    echo "    ADMIN_ID=رقم_تيليغرام_الأدمن"
    echo ""
    echo "  أو اضبط متغيرات البيئة مباشرةً:"
    echo "    export BOT_TOKEN=توكن_البوت_هنا"
    echo "    export ADMIN_ID=رقم_تيليغرام_الأدمن"
    exit 1
fi

# ── تحديد مجلد البوت ────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# ── التحقق من وجود Python ───────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مثبَّت."
    echo "ثبِّته بـ: pkg install python"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)

# ── التحقق من تثبيت المتطلبات ───────────────────────────
if ! "$PYTHON" -c "import telebot" 2>/dev/null; then
    echo "⚠️  متطلبات Python غير مثبَّتة. جارٍ التثبيت..."
    "$PYTHON" -m pip install -r requirements.txt --quiet
fi

# ── إعداد اللوغ ─────────────────────────────────────────
LOG_FILE="iraqnow_bot.log"
echo "📝 ملف اللوغ: $LOG_FILE"
echo "🛑 للإيقاف: اضغط Ctrl+C"
echo ""

# ── تشغيل البوت ─────────────────────────────────────────
echo "🚀 جارٍ تشغيل IraqNow Bot..."
"$PYTHON" main.py 2>&1 | tee -a "$LOG_FILE"
