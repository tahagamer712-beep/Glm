# -*- coding: utf-8 -*-
"""
  ai_engine.py — fallback: Gemini→Groq→OpenRouter→Mistral→Together→Cohere

  يُصدِّر محرك الذكاء الاصطناعي مع آلية الـ fallback.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX-13: ثوابت قص تاريخ AI — تمنع Context Overflow وتقلل التكلفة
_MAX_HISTORY_MESSAGES = 20
_MAX_HISTORY_CHARS    = 8000

def trim_ai_history(history: list) -> list:
    """
    FIX-13: يُبقي على آخر N رسالة فقط، ويقطع إذا تجاوز الحجم الكلي الحد.
    استخدم هذه الدالة قبل إرسال history لأي AI provider.
    """
    if not history:
        return history
    # احتفظ بآخر MAX_HISTORY_MESSAGES فقط
    history = list(history[-_MAX_HISTORY_MESSAGES:])
    # قص من البداية إذا تجاوز الحجم الكلي
    total_chars = sum(len(m.get('content', '')) for m in history)
    while total_chars > _MAX_HISTORY_CHARS and len(history) > 1:
        removed = history.pop(0)
        total_chars -= len(removed.get('content', ''))
    return history

def _smart_fallback_fact(title: str) -> dict:
    t = title.lower()
    negative = any(k in t for k in ["انفجار","هجوم","اغتيال","قتل","ضرب","صاروخ","سقط","تفجير"])
    official = any(k in t for k in ["وزير","رئيس","مجلس","محكمة","برلمان","حكومة","أمين","سفير"])
    vague = any(k in t for k in ["يُزعم","مصادر","قيل إن","تشير","يبدو"])
    if official and not vague:
        return {"verdict": "✅", "label": "موثوق", "reason": "صادر عن جهة رسمية مُسمّاة"}
    if vague or (not official and not negative):
        return {"verdict": "⚠️", "label": "يحتاج تحقق", "reason": "الخبر يفتقر لمصدر رسمي واضح — تحقق قبل المشاركة"}
    return {"verdict": "⚠️", "label": "يحتاج تحقق", "reason": "حدث حساس — تابع مصادر متعددة للتأكيد"}

def _smart_fallback_why(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["صاروخ","هجوم","انفجار","حرب","غارة","عملية"]):
        return ("💥 هذا الخبر يتعلق بحادثة أمنية أو عسكرية قد تؤثر على الاستقرار الإقليمي.\n"
                "• قد يتصاعد التوتر بين الأطراف المعنية.\n"
                "• يؤثر على المواطنين في مناطق النزاع ومسارات التجارة الإقليمية.\n"
                "• تابع البيانات الرسمية للتحقق من التفاصيل.")
    if any(k in t for k in ["اقتصاد","دولار","نفط","أسعار","تضخم","موازنة","بنك"]):
        return ("💰 هذا الخبر يؤثر مباشرة على القوة الشرائية والأسعار اليومية.\n"
                "• قد تتغير أسعار السلع الأساسية في الأسابيع القادمة.\n"
                "• يؤثر على العملة المحلية والادخار الشخصي.\n"
                "• تابع البيانات الرسمية لمعرفة التداعيات.")
    if any(k in t for k in ["حكومة","وزير","رئيس","قرار","قانون","برلمان","تشريع"]):
        return ("🏛 قرار سياسي قد ينعكس على الخدمات والحقوق اليومية للمواطنين.\n"
                "• قد يغير بعض القوانين أو الخدمات الحكومية.\n"
                "• يؤثر على من لديهم تعاملات رسمية أو مشاريع مع الدولة.")
    return (f"📰 هذا الخبر يرصد تطوراً يستحق المتابعة:\n"
            f"«{title[:100]}»\n"
            "• ابقَ على اطلاع عبر مصادر متعددة للحصول على الصورة الكاملة.")

def _smart_fallback_next(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["صاروخ","هجوم","انفجار","حرب","غارة"]):
        return ("🔮 التطورات المتوقعة:\n"
                "• 0-6 ساعات: بيانات رسمية وتحديد هوية المسؤولين عن الحادثة.\n"
                "• 24 ساعة: ردود فعل دبلوماسية وتصريحات الأطراف المعنية.\n"
                "• 48-72 ساعة: قرارات طارئة أو تحركات ميدانية محتملة.\n"
                "• تابع القنوات الرسمية للتحديثات الدقيقة.")
    if any(k in t for k in ["اقتصاد","دولار","نفط","أسعار","تضخم","بنك"]):
        return ("🔮 التطورات المتوقعة:\n"
                "• قريباً: ردود فعل الأسواق والبورصات الإقليمية.\n"
                "• خلال أسبوع: تصريحات البنك المركزي والحكومة.\n"
                "• قد تتأثر أسعار بعض السلع الأساسية تدريجياً.\n"
                "• راقب سعر الصرف الرسمي وغير الرسمي.")
    if any(k in t for k in ["حكومة","وزير","قرار","قانون","برلمان"]):
        return ("🔮 التطورات المتوقعة:\n"
                "• قريباً: تفاصيل القرار وآلية التطبيق.\n"
                "• خلال أسبوع: ردود المعارضة والمجتمع المدني.\n"
                "• خلال شهر: نتائج التطبيق وأثره الفعلي على المواطنين.")
    return ("🔮 التطورات المتوقعة:\n"
            "• تابع المصادر الرسمية للتحديثات خلال الـ 24 ساعة القادمة.\n"
            "• قد تصدر بيانات أو توضيحات رسمية بشأن هذا الملف.\n"
            "• لا تشارك الخبر قبل التحقق من مصادر متعددة.")

def _smart_fallback_context(title: str, lang: str = "العربية 🇮🇶") -> str:
    t = title.lower()
    if any(k in t for k in ["إيران","إسرائيل","صاروخ","هجوم","غزة","لبنان","حزب الله"]):
        return ("📚 السياق التاريخي:\n"
                "• العلاقة بين إيران وإسرائيل متوترة منذ الثورة الإيرانية 1979.\n"
                "• تصاعدت المواجهات المباشرة بشكل لافت منذ أكتوبر 2023.\n"
                "• المنطقة تشهد حالة من عدم الاستقرار الممتد منذ سنوات.\n"
                "• هذا الحدث جزء من سلسلة مواجهات متصاعدة في المنطقة.")
    if any(k in t for k in ["روسيا","أوكرانيا","ناتو","الغرب"]):
        return ("📚 السياق التاريخي:\n"
                "• الحرب الروسية الأوكرانية بدأت في فبراير 2022.\n"
                "• جذورها تعود لاتفاقيات مينسك الفاشلة وتوسع حلف الناتو.\n"
                "• الصراع رسم خريطة جديدة للعلاقات الدولية والطاقة العالمية.")
    if any(k in t for k in ["العراق","بغداد","الفصائل","الحشد"]):
        return ("📚 السياق التاريخي:\n"
                "• العراق يمر بمرحلة إعادة بناء مستمرة منذ 2003.\n"
                "• يتأثر بشكل مباشر بالتوازنات الإقليمية بين إيران والغرب.\n"
                "• الاستقرار الأمني والسياسي لا يزال يمثل تحدياً رئيسياً.")
    return (f"📚 السياق التاريخي:\n"
            f"هذا الحدث يندرج ضمن سياق أوسع يستحق المتابعة.\n"
            f"• ابحث عن أخبار سابقة متعلقة بـ: «{title[:60]}»\n"
            "• راجع مصادر موثوقة لفهم الخلفية الكاملة للحدث.")

# ══════════════════════════════════════════════════════════════════
# قاموس ترجمة واجهة المستخدم — جميع اللغات المدعومة
# ══════════════════════════════════════════════════════════════════
_UI_STRINGS: dict = {
    # ── رسائل التحميل ──────────────────────────────────────────
    "fc_loading": {
        "العربية 🇮🇶":   "🔍 *جاري التحقق من الخبر...*\n_قد يستغرق بضع ثوانٍ_",
        "English 🇬🇧":   "🔍 *Verifying the news...*\n_This may take a few seconds_",
        "Русский 🇷🇺":   "🔍 *Проверяем новость...*\n_Подождите несколько секунд_",
        "فارسی 🇮🇷":     "🔍 *در حال بررسی خبر...*\n_چند ثانیه صبر کنید_",
        "हिन्दी 🇮🇳":    "🔍 *समाचार सत्यापित हो रहा है...*\n_कुछ सेकंड प्रतीक्षा करें_",
        "Português 🇧🇷": "🔍 *Verificando a notícia...*\n_Aguarde alguns segundos_",
        "Türkçe 🇹🇷":    "🔍 *Haber doğrulanıyor...*\n_Birkaç saniye bekleyin_",
        "اردو 🇵🇰":      "🔍 *خبر کی تصدیق ہو رہی ہے...*\n_چند سیکنڈ انتظار کریں_",
        "Deutsch 🇩🇪":   "🔍 *Nachricht wird überprüft...*\n_Bitte einen Moment warten_",
        "Українська 🇺🇦":"🔍 *Перевіряємо новину...*\n_Зачекайте кілька секунд_",
        "Italiano 🇮🇹":  "🔍 *Verifica notizia in corso...*\n_Attendere qualche secondo_",
        "Español 🇲🇽":   "🔍 *Verificando la noticia...*\n_Espere unos segundos_",
        "Français 🇫🇷":  "🔍 *Vérification de l'actualité...*\n_Quelques secondes svp_",
    },
    "why_loading": {
        "العربية 🇮🇶":   "💡 *جاري تحليل أهمية الخبر...*\n_بضع ثوانٍ_",
        "English 🇬🇧":   "💡 *Analyzing why this matters...*\n_A few seconds_",
        "Русский 🇷🇺":   "💡 *Анализируем важность новости...*\n_Секунду_",
        "فارسی 🇮🇷":     "💡 *در حال تحلیل اهمیت خبر...*\n_چند ثانیه_",
        "हिन्दी 🇮🇳":    "💡 *समाचार का महत्व विश्लेषण...*\n_कुछ सेकंड_",
        "Português 🇧🇷": "💡 *Analisando a importância...*\n_Alguns segundos_",
        "Türkçe 🇹🇷":    "💡 *Haberin önemi analiz ediliyor...*\n_Birkaç saniye_",
        "اردو 🇵🇰":      "💡 *خبر کی اہمیت کا تجزیہ...*\n_چند سیکنڈ_",
        "Deutsch 🇩🇪":   "💡 *Bedeutung wird analysiert...*\n_Einen Moment_",
        "Українська 🇺🇦":"💡 *Аналізуємо важливість...*\n_Кілька секунд_",
        "Italiano 🇮🇹":  "💡 *Analisi importanza notizia...*\n_Alcuni secondi_",
        "Español 🇲🇽":   "💡 *Analizando la importancia...*\n_Unos segundos_",
        "Français 🇫🇷":  "💡 *Analyse de l'importance...*\n_Quelques secondes_",
    },
    "next_loading": {
        "العربية 🇮🇶":   "🔮 *جاري تحليل مسار الأحداث...*\n_بضع ثوانٍ_",
        "English 🇬🇧":   "🔮 *Analyzing what happens next...*\n_A few seconds_",
        "Русский 🇷🇺":   "🔮 *Анализируем дальнейшее развитие...*\n_Секунду_",
        "فارسی 🇮🇷":     "🔮 *در حال پیش‌بینی تحولات...*\n_چند ثانیه_",
        "हिन्दी 🇮🇳":    "🔮 *आगे क्या होगा विश्लेषण...*\n_कुछ सेकंड_",
        "Português 🇧🇷": "🔮 *Analisando próximos eventos...*\n_Alguns segundos_",
        "Türkçe 🇹🇷":    "🔮 *Sonraki gelişmeler analiz ediliyor...*\n_Birkaç saniye_",
        "اردو 🇵🇰":      "🔮 *آگے کیا ہوگا تجزیہ...*\n_چند سیکنڈ_",
        "Deutsch 🇩🇪":   "🔮 *Nächste Entwicklungen werden analysiert...*\n_Moment_",
        "Українська 🇺🇦":"🔮 *Аналізуємо подальший розвиток...*\n_Кілька секунд_",
        "Italiano 🇮🇹":  "🔮 *Analisi sviluppi futuri...*\n_Alcuni secondi_",
        "Español 🇲🇽":   "🔮 *Analizando próximos eventos...*\n_Unos segundos_",
        "Français 🇫🇷":  "🔮 *Analyse des prochains événements...*\n_Quelques secondes_",
    },
    "ctx_loading": {
        "العربية 🇮🇶":   "📚 *جاري تحليل الخلفية التاريخية...*\n_بضع ثوانٍ_",
        "English 🇬🇧":   "📚 *Analyzing historical background...*\n_A few seconds_",
        "Русский 🇷🇺":   "📚 *Анализируем исторический контекст...*\n_Секунду_",
        "فارسی 🇮🇷":     "📚 *در حال تحلیل پس‌زمینه تاریخی...*\n_چند ثانیه_",
        "हिन्दी 🇮🇳":    "📚 *ऐतिहासिक पृष्ठभूमि का विश्लेषण...*\n_कुछ सेकंड_",
        "Português 🇧🇷": "📚 *Analisando contexto histórico...*\n_Alguns segundos_",
        "Türkçe 🇹🇷":    "📚 *Tarihsel bağlam analiz ediliyor...*\n_Birkaç saniye_",
        "اردو 🇵🇰":      "📚 *تاریخی پس منظر کا تجزیہ...*\n_چند سیکنڈ_",
        "Deutsch 🇩🇪":   "📚 *Historischer Kontext wird analysiert...*\n_Moment_",
        "Українська 🇺🇦":"📚 *Аналізуємо історичний контекст...*\n_Кілька секунд_",
        "Italiano 🇮🇹":  "📚 *Analisi del contesto storico...*\n_Alcuni secondi_",
        "Español 🇲🇽":   "📚 *Analizando contexto histórico...*\n_Unos segundos_",
        "Français 🇫🇷":  "📚 *Analyse du contexte historique...*\n_Quelques secondes_",
    },
    # ── رسائل الحالة ──────────────────────────────────────────
    "expired": {
        "العربية 🇮🇶":   "🔄 أُعيد تشغيل البوت — الزر لم يعد صالحاً. اطلب الخبر من جديد.",
        "English 🇬🇧":   "🔄 Bot was restarted — this button is no longer valid. Please request the news again.",
        "Русский 🇷🇺":   "⚠️ Срок кнопки истёк. Откройте новость снова.",
        "فارسی 🇮🇷":     "⚠️ این دکمه منقضی شده. خبر را دوباره باز کنید.",
        "हिन्दी 🇮🇳":    "⚠️ यह बटन समाप्त हो गया। समाचार फिर से खोलें।",
        "Português 🇧🇷": "⚠️ Este botão expirou. Abra a notícia novamente.",
        "Türkçe 🇹🇷":    "⚠️ Bu buton süresi doldu. Haberi tekrar açın.",
        "اردو 🇵🇰":      "⚠️ یہ بٹن ختم ہو گیا۔ خبر دوبارہ کھولیں۔",
        "Deutsch 🇩🇪":   "⚠️ Diese Schaltfläche ist abgelaufen. Öffne die Nachricht erneut.",
        "Українська 🇺🇦":"⚠️ Термін дії кнопки вичерпано. Відкрийте новину знову.",
        "Italiano 🇮🇹":  "⚠️ Pulsante scaduto. Riapri la notizia.",
        "Español 🇲🇽":   "⚠️ Este botón ha expirado. Vuelve a abrir la noticia.",
        "Français 🇫🇷":  "⚠️ Ce bouton a expiré. Rouvrez l'actualité.",
    },
    "wait": {
        "العربية 🇮🇶":   "⏳ انتظر ثوانٍ قليلة.",
        "English 🇬🇧":   "⏳ Please wait a few seconds.",
        "Русский 🇷🇺":   "⏳ Подождите несколько секунд.",
        "فارسی 🇮🇷":     "⏳ چند ثانیه صبر کنید.",
        "हिन्दी 🇮🇳":    "⏳ कुछ सेकंड प्रतीक्षा करें।",
        "Português 🇧🇷": "⏳ Aguarde alguns segundos.",
        "Türkçe 🇹🇷":    "⏳ Birkaç saniye bekleyin.",
        "اردو 🇵🇰":      "⏳ چند سیکنڈ انتظار کریں۔",
        "Deutsch 🇩🇪":   "⏳ Bitte einen Moment warten.",
        "Українська 🇺🇦":"⏳ Зачекайте кілька секунд.",
        "Italiano 🇮🇹":  "⏳ Attendere qualche secondo.",
        "Español 🇲🇽":   "⏳ Espera unos segundos.",
        "Français 🇫🇷":  "⏳ Veuillez patienter quelques secondes.",
    },
    "bm_saved": {
        "العربية 🇮🇶":   "🔖 تم الحفظ! اكتب /saved لعرض محفوظاتك.",
        "English 🇬🇧":   "🔖 Saved! Type /saved to view your bookmarks.",
        "Русский 🇷🇺":   "🔖 Сохранено! Введите /saved для просмотра.",
        "فارسی 🇮🇷":     "🔖 ذخیره شد! /saved را بنویسید.",
        "हिन्दी 🇮🇳":    "🔖 सहेजा गया! /saved टाइप करें।",
        "Português 🇧🇷": "🔖 Salvo! Digite /saved para ver.",
        "Türkçe 🇹🇷":    "🔖 Kaydedildi! /saved yazın.",
        "اردو 🇵🇰":      "🔖 محفوظ! /saved لکھیں۔",
        "Deutsch 🇩🇪":   "🔖 Gespeichert! Tippe /saved zum Anzeigen.",
        "Українська 🇺🇦":"🔖 Збережено! Введіть /saved для перегляду.",
        "Italiano 🇮🇹":  "🔖 Salvato! Scrivi /saved per vedere.",
        "Español 🇲🇽":   "🔖 ¡Guardado! Escribe /saved para ver.",
        "Français 🇫🇷":  "🔖 Sauvegardé! Tapez /saved pour voir.",
    },
    "bm_already": {
        "العربية 🇮🇶":   "📌 محفوظ مسبقاً! اكتب /saved لعرض محفوظاتك.",
        "English 🇬🇧":   "📌 Already saved! Type /saved to view bookmarks.",
        "Русский 🇷🇺":   "📌 Уже сохранено! Введите /saved.",
        "فارسی 🇮🇷":     "📌 قبلاً ذخیره شده! /saved را بنویسید.",
        "हिन्दी 🇮🇳":    "📌 पहले से सहेजा! /saved टाइप करें।",
        "Português 🇧🇷": "📌 Já salvo! Digite /saved.",
        "Türkçe 🇹🇷":    "📌 Zaten kaydedildi! /saved yazın.",
        "اردو 🇵🇰":      "📌 پہلے سے محفوظ! /saved لکھیں۔",
        "Deutsch 🇩🇪":   "📌 Bereits gespeichert! Tippe /saved.",
        "Українська 🇺🇦":"📌 Вже збережено! Введіть /saved.",
        "Italiano 🇮🇹":  "📌 Già salvato! Scrivi /saved.",
        "Español 🇲🇽":   "📌 ¡Ya guardado! Escribe /saved.",
        "Français 🇫🇷":  "📌 Déjà sauvegardé! Tapez /saved.",
    },
    "bm_error": {
        "العربية 🇮🇶":   "⚠️ حدث خطأ أثناء الحفظ، حاول مجدداً.",
        "English 🇬🇧":   "⚠️ Error saving. Please try again.",
        "Русский 🇷🇺":   "⚠️ Ошибка сохранения. Попробуйте снова.",
        "فارسی 🇮🇷":     "⚠️ خطا در ذخیره‌سازی. دوباره امتحان کنید.",
        "हिन्दी 🇮🇳":    "⚠️ सहेजने में त्रुटि। पुनः प्रयास करें।",
        "Português 🇧🇷": "⚠️ Erro ao salvar. Tente novamente.",
        "Türkçe 🇹🇷":    "⚠️ Kaydetme hatası. Tekrar deneyin.",
        "اردو 🇵🇰":      "⚠️ محفوظ کرنے میں خطا۔ دوبارہ کوشش کریں۔",
        "Deutsch 🇩🇪":   "⚠️ Fehler beim Speichern. Versuche es erneut.",
        "Українська 🇺🇦":"⚠️ Помилка збереження. Спробуйте ще раз.",
        "Italiano 🇮🇹":  "⚠️ Errore nel salvataggio. Riprova.",
        "Español 🇲🇽":   "⚠️ Error al guardar. Inténtalo de nuevo.",
        "Français 🇫🇷":  "⚠️ Erreur lors de la sauvegarde. Réessayez.",
    },
    "fc_checking": {
        "العربية 🇮🇶":   "🔍 جاري التحقق...",
        "English 🇬🇧":   "🔍 Verifying...",
        "Русский 🇷🇺":   "🔍 Проверяем...",
        "فارسی 🇮🇷":     "🔍 در حال بررسی...",
        "हिन्दी 🇮🇳":    "🔍 सत्यापन जारी...",
        "Português 🇧🇷": "🔍 Verificando...",
        "Türkçe 🇹🇷":    "🔍 Doğrulanıyor...",
        "اردو 🇵🇰":      "🔍 تصدیق ہو رہی ہے...",
        "Deutsch 🇩🇪":   "🔍 Wird überprüft...",
        "Українська 🇺🇦":"🔍 Перевіряємо...",
        "Italiano 🇮🇹":  "🔍 Verifica in corso...",
        "Español 🇲🇽":   "🔍 Verificando...",
        "Français 🇫🇷":  "🔍 Vérification...",
    },
    "why_checking": {
        "العربية 🇮🇶":   "💡 جاري التحليل...",
        "English 🇬🇧":   "💡 Analyzing...",
        "Русский 🇷🇺":   "💡 Анализируем...",
        "فارسی 🇮🇷":     "💡 در حال تحلیل...",
        "हिन्दी 🇮🇳":    "💡 विश्लेषण जारी...",
        "Português 🇧🇷": "💡 Analisando...",
        "Türkçe 🇹🇷":    "💡 Analiz ediliyor...",
        "اردو 🇵🇰":      "💡 تجزیہ ہو رہا ہے...",
        "Deutsch 🇩🇪":   "💡 Analysiere...",
        "Українська 🇺🇦":"💡 Аналізуємо...",
        "Italiano 🇮🇹":  "💡 Analisi in corso...",
        "Español 🇲🇽":   "💡 Analizando...",
        "Français 🇫🇷":  "💡 Analyse en cours...",
    },
    "next_checking": {
        "العربية 🇮🇶":   "🔮 جاري التحليل...",
        "English 🇬🇧":   "🔮 Analyzing...",
        "Русский 🇷🇺":   "🔮 Анализируем...",
        "فارسی 🇮🇷":     "🔮 در حال تحلیل...",
        "हिन्दी 🇮🇳":    "🔮 विश्लेषण जारी...",
        "Português 🇧🇷": "🔮 Analisando...",
        "Türkçe 🇹🇷":    "🔮 Analiz ediliyor...",
        "اردو 🇵🇰":      "🔮 تجزیہ ہو رہا ہے...",
        "Deutsch 🇩🇪":   "🔮 Analysiere...",
        "Українська 🇺🇦":"🔮 Аналізуємо...",
        "Italiano 🇮🇹":  "🔮 Analisi in corso...",
        "Español 🇲🇽":   "🔮 Analizando...",
        "Français 🇫🇷":  "🔮 Analyse en cours...",
    },
    "ctx_checking": {
        "العربية 🇮🇶":   "📚 جاري بناء السياق التاريخي...",
        "English 🇬🇧":   "📚 Building historical context...",
        "Русский 🇷🇺":   "📚 Формируем исторический контекст...",
        "فارسی 🇮🇷":     "📚 در حال ساختن بافت تاریخی...",
        "हिन्दी 🇮🇳":    "📚 ऐतिहासिक संदर्भ बन रहा है...",
        "Português 🇧🇷": "📚 Construindo contexto histórico...",
        "Türkçe 🇹🇷":    "📚 Tarihsel bağlam oluşturuluyor...",
        "اردو 🇵🇰":      "📚 تاریخی سیاق بن رہا ہے...",
        "Deutsch 🇩🇪":   "📚 Historischer Kontext wird erstellt...",
        "Українська 🇺🇦":"📚 Формуємо історичний контекст...",
        "Italiano 🇮🇹":  "📚 Costruzione contesto storico...",
        "Español 🇲🇽":   "📚 Construyendo contexto histórico...",
        "Français 🇫🇷":  "📚 Construction du contexte historique...",
    },
    # ── عناوين الأقسام ──────────────────────────────────────────
    "fc_title": {
        "العربية 🇮🇶":   "🔍 نتيجة التحقق:",
        "English 🇬🇧":   "🔍 Fact-check result:",
        "Русский 🇷🇺":   "🔍 Результат проверки:",
        "فارسی 🇮🇷":     "🔍 نتیجه بررسی:",
        "हिन्दी 🇮🇳":    "🔍 सत्यापन परिणाम:",
        "Português 🇧🇷": "🔍 Resultado da verificação:",
        "Türkçe 🇹🇷":    "🔍 Doğrulama sonucu:",
        "اردو 🇵🇰":      "🔍 تصدیق کا نتیجہ:",
        "Deutsch 🇩🇪":   "🔍 Faktencheck-Ergebnis:",
        "Українська 🇺🇦":"🔍 Результат перевірки:",
        "Italiano 🇮🇹":  "🔍 Risultato verifica:",
        "Español 🇲🇽":   "🔍 Resultado de verificación:",
        "Français 🇫🇷":  "🔍 Résultat de vérification:",
    },
    "why_title": {
        "العربية 🇮🇶":   "💡 لماذا يهمك هذا الخبر؟",
        "English 🇬🇧":   "💡 Why does this news matter to you?",
        "Русский 🇷🇺":   "💡 Почему эта новость важна для вас?",
        "فارسی 🇮🇷":     "💡 چرا این خبر برای شما مهم است؟",
        "हिन्दी 🇮🇳":    "💡 यह समाचार आपके लिए क्यों महत्वपूर्ण है?",
        "Português 🇧🇷": "💡 Por que esta notícia importa para você?",
        "Türkçe 🇹🇷":    "💡 Bu haber neden önemli?",
        "اردو 🇵🇰":      "💡 یہ خبر آپ کے لیے کیوں اہم ہے؟",
        "Deutsch 🇩🇪":   "💡 Warum ist diese Nachricht wichtig für dich?",
        "Українська 🇺🇦":"💡 Чому ця новина важлива для вас?",
        "Italiano 🇮🇹":  "💡 Perché questa notizia ti riguarda?",
        "Español 🇲🇽":   "💡 ¿Por qué te importa esta noticia?",
        "Français 🇫🇷":  "💡 Pourquoi cette actualité vous concerne-t-elle?",
    },
    "next_title": {
        "العربية 🇮🇶":   "🔮 ماذا قد يحدث بعدها؟",
        "English 🇬🇧":   "🔮 What might happen next?",
        "Русский 🇷🇺":   "🔮 Что может произойти дальше?",
        "فارسی 🇮🇷":     "🔮 چه اتفاقی ممکن است بیفتد؟",
        "हिन्दी 🇮🇳":    "🔮 आगे क्या हो सकता है?",
        "Português 🇧🇷": "🔮 O que pode acontecer a seguir?",
        "Türkçe 🇹🇷":    "🔮 Bundan sonra ne olabilir?",
        "اردو 🇵🇰":      "🔮 آگے کیا ہو سکتا ہے؟",
        "Deutsch 🇩🇪":   "🔮 Was könnte als nächstes passieren?",
        "Українська 🇺🇦":"🔮 Що може статися далі?",
        "Italiano 🇮🇹":  "🔮 Cosa potrebbe succedere dopo?",
        "Español 🇲🇽":   "🔮 ¿Qué podría pasar después?",
        "Français 🇫🇷":  "🔮 Que pourrait-il se passer ensuite?",
    },
    "ctx_title": {
        "العربية 🇮🇶":   "📚 السياق التاريخي والخلفية",
        "English 🇬🇧":   "📚 Historical Context & Background",
        "Русский 🇷🇺":   "📚 Исторический контекст и предыстория",
        "فارسی 🇮🇷":     "📚 زمینه تاریخی و پیشینه",
        "हिन्दी 🇮🇳":    "📚 ऐतिहासिक संदर्भ और पृष्ठभूमि",
        "Português 🇧🇷": "📚 Contexto histórico e antecedentes",
        "Türkçe 🇹🇷":    "📚 Tarihsel Bağlam ve Arka Plan",
        "اردو 🇵🇰":      "📚 تاریخی تناظر اور پس منظر",
        "Deutsch 🇩🇪":   "📚 Historischer Kontext und Hintergrund",
        "Українська 🇺🇦":"📚 Історичний контекст та передісторія",
        "Italiano 🇮🇹":  "📚 Contesto storico e sfondo",
        "Español 🇲🇽":   "📚 Contexto histórico y antecedentes",
        "Français 🇫🇷":  "📚 Contexte historique et arrière-plan",
    },
    "sentiment_label": {
        "العربية 🇮🇶":   "🎭 المشاعر:",
        "English 🇬🇧":   "🎭 Sentiment:",
        "Русский 🇷🇺":   "🎭 Тональность:",
        "فارسی 🇮🇷":     "🎭 احساسات:",
        "हिन्दी 🇮🇳":    "🎭 भावना:",
        "Português 🇧🇷": "🎭 Sentimento:",
        "Türkçe 🇹🇷":    "🎭 Duygu:",
        "اردو 🇵🇰":      "🎭 جذبات:",
        "Deutsch 🇩🇪":   "🎭 Stimmung:",
        "Українська 🇺🇦":"🎭 Настрій:",
        "Italiano 🇮🇹":  "🎭 Sentimento:",
        "Español 🇲🇽":   "🎭 Sentimiento:",
        "Français 🇫🇷":  "🎭 Sentiment:",
    },
    "quality_label": {
        "العربية 🇮🇶":   "⭐ جودة المحتوى:",
        "English 🇬🇧":   "⭐ Content quality:",
        "Русский 🇷🇺":   "⭐ Качество контента:",
        "فارسی 🇮🇷":     "⭐ کیفیت محتوا:",
        "हिन्दी 🇮🇳":    "⭐ सामग्री गुणवत्ता:",
        "Português 🇧🇷": "⭐ Qualidade do conteúdo:",
        "Türkçe 🇹🇷":    "⭐ İçerik kalitesi:",
        "اردو 🇵🇰":      "⭐ مواد کا معیار:",
        "Deutsch 🇩🇪":   "⭐ Inhaltsqualität:",
        "Українська 🇺🇦":"⭐ Якість контенту:",
        "Italiano 🇮🇹":  "⭐ Qualità del contenuto:",
        "Español 🇲🇽":   "⭐ Calidad del contenido:",
        "Français 🇫🇷":  "⭐ Qualité du contenu:",
    },
    # ── رسائل Feature Flags ──────────────────────────────────────────
    "feature_disabled": {
        "العربية 🇮🇶":   "⛔ هذه الميزة متوقفة حالياً.",
        "English 🇬🇧":   "⛔ This feature is currently disabled.",
        "Русский 🇷🇺":   "⛔ Эта функция сейчас отключена.",
        "فارسی 🇮🇷":     "⛔ این ویژگی در حال حاضر غیرفعال است.",
        "हिन्दी 🇮🇳":    "⛔ यह सुविधा अभी अक्षम है।",
        "Português 🇧🇷": "⛔ Este recurso está desativado no momento.",
        "Türkçe 🇹🇷":    "⛔ Bu özellik şu anda devre dışı.",
        "اردو 🇵🇰":      "⛔ یہ فیچر ابھی بند ہے۔",
        "Deutsch 🇩🇪":   "⛔ Diese Funktion ist derzeit deaktiviert.",
        "Українська 🇺🇦":"⛔ Ця функція зараз вимкнена.",
        "Italiano 🇮🇹":  "⛔ Questa funzione è attualmente disabilitata.",
        "Español 🇲🇽":   "⛔ Esta función está desactivada actualmente.",
        "Français 🇫🇷":  "⛔ Cette fonctionnalité est actuellement désactivée.",
    },
    "premium_only_msg": {
        "العربية 🇮🇶":   "⚡ هذه الميزة حصرية للمستخدمين المميزين فقط.",
        "English 🇬🇧":   "⚡ This feature is for Premium users only.",
        "Русский 🇷🇺":   "⚡ Эта функция доступна только Premium-пользователям.",
        "فارسی 🇮🇷":     "⚡ این ویژگی فقط برای کاربران پریمیوم است.",
        "हिन्दी 🇮🇳":    "⚡ यह सुविधा केवल Premium उपयोगकर्ताओं के लिए है।",
        "Português 🇧🇷": "⚡ Este recurso é exclusivo para usuários Premium.",
        "Türkçe 🇹🇷":    "⚡ Bu özellik yalnızca Premium kullanıcılara özeldir.",
        "اردو 🇵🇰":      "⚡ یہ فیچر صرف Premium صارفین کے لیے ہے۔",
        "Deutsch 🇩🇪":   "⚡ Diese Funktion ist nur für Premium-Nutzer verfügbar.",
        "Українська 🇺🇦":"⚡ Ця функція лише для Premium-користувачів.",
        "Italiano 🇮🇹":  "⚡ Questa funzione è riservata agli utenti Premium.",
        "Español 🇲🇽":   "⚡ Esta función es exclusiva para usuarios Premium.",
        "Français 🇫🇷":  "⚡ Cette fonctionnalité est réservée aux utilisateurs Premium.",
    },
    # ── رسائل عامة للمستخدم ───────────────────────────────────────────
    "send_start_first": {
        "العربية 🇮🇶":   "⚠️ أرسل /start أولاً.",
        "English 🇬🇧":   "⚠️ Please send /start first.",
        "Русский 🇷🇺":   "⚠️ Сначала отправьте /start.",
        "فارسی 🇮🇷":     "⚠️ ابتدا /start را ارسال کنید.",
        "हिन्दी 🇮🇳":    "⚠️ पहले /start भेजें।",
        "Português 🇧🇷": "⚠️ Envie /start primeiro.",
        "Türkçe 🇹🇷":    "⚠️ Lütfen önce /start gönderin.",
        "اردو 🇵🇰":      "⚠️ پہلے /start بھیجیں۔",
        "Deutsch 🇩🇪":   "⚠️ Bitte sende zuerst /start.",
        "Українська 🇺🇦":"⚠️ Спочатку надішліть /start.",
        "Italiano 🇮🇹":  "⚠️ Invia prima /start.",
        "Español 🇲🇽":   "⚠️ Envía /start primero.",
        "Français 🇫🇷":  "⚠️ Envoyez /start d'abord.",
    },
    "no_city_set": {
        "العربية 🇮🇶":   "⚠️ لم تحدد مدينتك. أرسل /start لإعداد حسابك.",
        "English 🇬🇧":   "⚠️ You haven't set your city. Send /start to set up your account.",
        "Русский 🇷🇺":   "⚠️ Город не указан. Отправьте /start для настройки.",
        "فارسی 🇮🇷":     "⚠️ شهر شما تنظیم نشده. /start را ارسال کنید.",
        "हिन्दी 🇮🇳":    "⚠️ आपका शहर सेट नहीं है। /start भेजें।",
        "Português 🇧🇷": "⚠️ Sua cidade não foi definida. Envie /start.",
        "Türkçe 🇹🇷":    "⚠️ Şehrinizi belirlediniz. /start gönderin.",
        "اردو 🇵🇰":      "⚠️ آپ کا شہر سیٹ نہیں۔ /start بھیجیں۔",
        "Deutsch 🇩🇪":   "⚠️ Keine Stadt gesetzt. Sende /start zum Einrichten.",
        "Українська 🇺🇦":"⚠️ Місто не вказано. Надішліть /start.",
        "Italiano 🇮🇹":  "⚠️ Città non impostata. Invia /start.",
        "Español 🇲🇽":   "⚠️ Ciudad no configurada. Envía /start.",
        "Français 🇫🇷":  "⚠️ Ville non définie. Envoyez /start.",
    },
    "stop_notifications": {
        "العربية 🇮🇶":   "🔕 تم إيقاف الإشعارات. أرسل /start للرجوع.",
        "English 🇬🇧":   "🔕 Notifications stopped. Send /start to go back.",
        "Русский 🇷🇺":   "🔕 Уведомления отключены. Отправьте /start.",
        "فارسی 🇮🇷":     "🔕 اعلان‌ها متوقف شد. /start را ارسال کنید.",
        "हिन्दी 🇮🇳":    "🔕 सूचनाएं बंद। /start भेजें।",
        "Português 🇧🇷": "🔕 Notificações pausadas. Envie /start.",
        "Türkçe 🇹🇷":    "🔕 Bildirimler durduruldu. /start gönderin.",
        "اردو 🇵🇰":      "🔕 اطلاعات بند۔ /start بھیجیں۔",
        "Deutsch 🇩🇪":   "🔕 Benachrichtigungen gestoppt. Sende /start.",
        "Українська 🇺🇦":"🔕 Сповіщення вимкнено. Надішліть /start.",
        "Italiano 🇮🇹":  "🔕 Notifiche fermate. Invia /start.",
        "Español 🇲🇽":   "🔕 Notificaciones pausadas. Envía /start.",
        "Français 🇫🇷":  "🔕 Notifications arrêtées. Envoyez /start.",
    },
    "track_cancelled": {
        "العربية 🇮🇶":   "⚠️ تم إلغاء إضافة الرمز. أرسل /addtrack للمحاولة مجدداً.",
        "English 🇬🇧":   "⚠️ Symbol addition cancelled. Send /addtrack to try again.",
        "Русский 🇷🇺":   "⚠️ Добавление отменено. Отправьте /addtrack повторно.",
        "فارسی 🇮🇷":     "⚠️ افزودن نماد لغو شد. /addtrack را ارسال کنید.",
        "हिन्दी 🇮🇳":    "⚠️ जोड़ना रद्द। /addtrack भेजें।",
        "Português 🇧🇷": "⚠️ Adição cancelada. Envie /addtrack.",
        "Türkçe 🇹🇷":    "⚠️ Sembol ekleme iptal edildi. /addtrack gönderin.",
        "اردو 🇵🇰":      "⚠️ اضافہ منسوخ۔ /addtrack بھیجیں۔",
        "Deutsch 🇩🇪":   "⚠️ Hinzufügen abgebrochen. Sende /addtrack.",
        "Українська 🇺🇦":"⚠️ Додавання скасовано. Надішліть /addtrack.",
        "Italiano 🇮🇹":  "⚠️ Aggiunta annullata. Invia /addtrack.",
        "Español 🇲🇽":   "⚠️ Adición cancelada. Envía /addtrack.",
        "Français 🇫🇷":  "⚠️ Ajout annulé. Envoyez /addtrack.",
    },
    "feature_already_unlocked": {
        "العربية 🇮🇶":   "⚠️ هذه الميزة مفتوحة لديك بالفعل.",
        "English 🇬🇧":   "⚠️ This feature is already unlocked for you.",
        "Русский 🇷🇺":   "⚠️ Эта функция уже разблокирована.",
        "فارسی 🇮🇷":     "⚠️ این ویژگی قبلاً باز شده است.",
        "हिन्दी 🇮🇳":    "⚠️ यह सुविधा पहले से अनलॉक है।",
        "Português 🇧🇷": "⚠️ Este recurso já está desbloqueado.",
        "Türkçe 🇹🇷":    "⚠️ Bu özellik zaten açık.",
        "اردو 🇵🇰":      "⚠️ یہ فیچر پہلے سے کھلا ہے۔",
        "Deutsch 🇩🇪":   "⚠️ Diese Funktion ist bereits freigeschaltet.",
        "Українська 🇺🇦":"⚠️ Цю функцію вже розблоковано.",
        "Italiano 🇮🇹":  "⚠️ Questa funzione è già sbloccata.",
        "Español 🇲🇽":   "⚠️ Esta función ya está desbloqueada.",
        "Français 🇫🇷":  "⚠️ Cette fonctionnalité est déjà débloquée.",
    },
    # ── رسائل الأخبار الصوتية ─────────────────────────────────────────
    "voice_unavailable": {
        "العربية 🇮🇶":   "⚠️ خاصية الأخبار الصوتية غير متاحة حالياً.",
        "English 🇬🇧":   "⚠️ Voice news feature is unavailable right now.",
        "Русский 🇷🇺":   "⚠️ Голосовые новости недоступны.",
        "فارسی 🇮🇷":     "⚠️ اخبار صوتی در دسترس نیست.",
        "हिन्दी 🇮🇳":    "⚠️ वॉयस न्यूज़ अभी उपलब्ध नहीं।",
        "Português 🇧🇷": "⚠️ Notícias em voz não disponíveis agora.",
        "Türkçe 🇹🇷":    "⚠️ Sesli haber özelliği şu an mevcut değil.",
        "اردو 🇵🇰":      "⚠️ آواز خبریں ابھی دستیاب نہیں۔",
        "Deutsch 🇩🇪":   "⚠️ Sprachnachrichten sind derzeit nicht verfügbar.",
        "Українська 🇺🇦":"⚠️ Голосові новини недоступні.",
        "Italiano 🇮🇹":  "⚠️ Notizie vocali non disponibili.",
        "Español 🇲🇽":   "⚠️ Noticias de voz no disponibles.",
        "Français 🇫🇷":  "⚠️ Actualités vocales indisponibles.",
    },
    "voice_loading": {
        "العربية 🇮🇶":   "🎙️ جاري تحضير الأخبار الصوتية...",
        "English 🇬🇧":   "🎙️ Preparing voice news...",
        "Русский 🇷🇺":   "🎙️ Подготовка голосовых новостей...",
        "فارسی 🇮🇷":     "🎙️ در حال آماده‌سازی اخبار صوتی...",
        "हिन्दी 🇮🇳":    "🎙️ वॉयस न्यूज़ तैयार हो रहा है...",
        "Português 🇧🇷": "🎙️ Preparando notícias em voz...",
        "Türkçe 🇹🇷":    "🎙️ Sesli haberler hazırlanıyor...",
        "اردو 🇵🇰":      "🎙️ آواز خبریں تیار ہو رہی ہیں...",
        "Deutsch 🇩🇪":   "🎙️ Sprachnachrichten werden vorbereitet...",
        "Українська 🇺🇦":"🎙️ Підготовка голосових новин...",
        "Italiano 🇮🇹":  "🎙️ Preparazione notizie vocali...",
        "Español 🇲🇽":   "🎙️ Preparando noticias de voz...",
        "Français 🇫🇷":  "🎙️ Préparation des actualités vocales...",
    },
    "voice_no_news": {
        "العربية 🇮🇶":   "⚠️ لم أجد أخبار متاحة الآن. حاول لاحقاً.",
        "English 🇬🇧":   "⚠️ No news available right now. Try later.",
        "Русский 🇷🇺":   "⚠️ Нет доступных новостей. Попробуйте позже.",
        "فارسی 🇮🇷":     "⚠️ خبری یافت نشد. بعداً امتحان کنید.",
        "हिन्दी 🇮🇳":    "⚠️ कोई समाचार उपलब्ध नहीं। बाद में प्रयास करें।",
        "Português 🇧🇷": "⚠️ Nenhuma notícia disponível. Tente depois.",
        "Türkçe 🇹🇷":    "⚠️ Haber bulunamadı. Daha sonra deneyin.",
        "اردو 🇵🇰":      "⚠️ کوئی خبر دستیاب نہیں۔ بعد میں کوشش کریں۔",
        "Deutsch 🇩🇪":   "⚠️ Keine Nachrichten verfügbar. Versuche es später.",
        "Українська 🇺🇦":"⚠️ Новин немає. Спробуйте пізніше.",
        "Italiano 🇮🇹":  "⚠️ Nessuna notizia disponibile. Riprova dopo.",
        "Español 🇲🇽":   "⚠️ No hay noticias disponibles. Intenta después.",
        "Français 🇫🇷":  "⚠️ Aucune actualité disponible. Réessayez plus tard.",
    },
    "voice_fail": {
        "العربية 🇮🇶":   "⚠️ فشل توليد الصوت. حاول مرة أخرى.",
        "English 🇬🇧":   "⚠️ Voice generation failed. Please try again.",
        "Русский 🇷🇺":   "⚠️ Ошибка генерации голоса. Попробуйте ещё раз.",
        "فارسی 🇮🇷":     "⚠️ تولید صدا ناموفق بود. دوباره امتحان کنید.",
        "हिन्दी 🇮🇳":    "⚠️ आवाज़ बनाने में विफल। फिर कोशिश करें।",
        "Português 🇧🇷": "⚠️ Geração de voz falhou. Tente novamente.",
        "Türkçe 🇹🇷":    "⚠️ Ses üretimi başarısız. Tekrar deneyin.",
        "اردو 🇵🇰":      "⚠️ آواز بنانا ناکام ہوا۔ دوبارہ کوشش کریں۔",
        "Deutsch 🇩🇪":   "⚠️ Sprachgenerierung fehlgeschlagen. Erneut versuchen.",
        "Українська 🇺🇦":"⚠️ Помилка генерації голосу. Спробуйте знову.",
        "Italiano 🇮🇹":  "⚠️ Generazione voce fallita. Riprova.",
        "Español 🇲🇽":   "⚠️ Fallo en la generación de voz. Inténtalo de nuevo.",
        "Français 🇫🇷":  "⚠️ Échec de la génération vocale. Réessayez.",
    },
    "voice_caption": {
        "العربية 🇮🇶":   "🎙️ *أخبار صوتية*",
        "English 🇬🇧":   "🎙️ *Voice News*",
        "Русский 🇷🇺":   "🎙️ *Голосовые новости*",
        "فارسی 🇮🇷":     "🎙️ *اخبار صوتی*",
        "हिन्दी 🇮🇳":    "🎙️ *वॉयस न्यूज़*",
        "Português 🇧🇷": "🎙️ *Notícias em Voz*",
        "Türkçe 🇹🇷":    "🎙️ *Sesli Haberler*",
        "اردو 🇵🇰":      "🎙️ *آواز خبریں*",
        "Deutsch 🇩🇪":   "🎙️ *Sprachnachrichten*",
        "Українська 🇺🇦":"🎙️ *Голосові новини*",
        "Italiano 🇮🇹":  "🎙️ *Notizie Vocali*",
        "Español 🇲🇽":   "🎙️ *Noticias de Voz*",
        "Français 🇫🇷":  "🎙️ *Actualités Vocales*",
    },
    # ══════════════════════════════════════════════════════════
    # رسائل الأوامر متعددة اللغات — Commands UI Strings
    # ══════════════════════════════════════════════════════════

    # /search
    "cmd_search_usage": {
        "العربية 🇮🇶":   "🔍 *البحث في أرشيف الأخبار*\n\nاكتب كلمة مفتاحية:\n`/search الدولار`\n`/search بغداد`",
        "English 🇬🇧":   "🔍 *Search News Archive*\n\nType a keyword:\n`/search dollar`\n`/search Baghdad`",
        "Русский 🇷🇺":   "🔍 *Поиск в архиве новостей*\n\nВведите ключевое слово:\n`/search доллар`",
        "فارسی 🇮🇷":     "🔍 *جستجوی آرشیو اخبار*\n\nکلمه کلیدی:\n`/search دلار`",
        "हिन्दी 🇮🇳":    "🔍 *समाचार संग्रह खोज*\n\nकीवर्ड टाइप करें:\n`/search dollar`",
        "Português 🇧🇷": "🔍 *Pesquisar Arquivo*\n\nDigite uma palavra-chave:\n`/search dólar`",
        "Türkçe 🇹🇷":    "🔍 *Haber Arşivi Ara*\n\nAnahtar kelime girin:\n`/search dolar`",
        "اردو 🇵🇰":      "🔍 *خبر آرکائیو تلاش*\n\nکلیدی لفظ لکھیں:\n`/search dollar`",
        "Deutsch 🇩🇪":   "🔍 *Nachrichtenarchiv durchsuchen*\n\nStichwort eingeben:\n`/search Dollar`",
        "Українська 🇺🇦":"🔍 *Пошук в архіві новин*\n\nВведіть ключове слово:\n`/search долар`",
        "Italiano 🇮🇹":  "🔍 *Cerca nell'archivio*\n\nInserisci una parola chiave:\n`/search dollaro`",
        "Español 🇲🇽":   "🔍 *Buscar en el archivo*\n\nEscribe una palabra clave:\n`/search dólar`",
        "Français 🇫🇷":  "🔍 *Rechercher dans l'archive*\n\nEntrez un mot-clé:\n`/search dollar`",
    },
    "cmd_search_noresult": {
        "العربية 🇮🇶":   "🔍 لا توجد نتائج لـ *{q}* في أرشيف الأخبار (7 أيام).",
        "English 🇬🇧":   "🔍 No results for *{q}* in the news archive (7 days).",
        "Русский 🇷🇺":   "🔍 Нет результатов для *{q}* за 7 дней.",
        "فارسی 🇮🇷":     "🔍 نتیجه‌ای برای *{q}* یافت نشد (7 روز).",
        "हिन्दी 🇮🇳":    "🔍 *{q}* के लिए कोई परिणाम नहीं (7 दिन)।",
        "Português 🇧🇷": "🔍 Sem resultados para *{q}* (7 dias).",
        "Türkçe 🇹🇷":    "🔍 *{q}* için sonuç yok (7 gün).",
        "اردو 🇵🇰":      "🔍 *{q}* کے لیے کوئی نتیجہ نہیں (7 دن)۔",
        "Deutsch 🇩🇪":   "🔍 Keine Ergebnisse für *{q}* (7 Tage).",
        "Українська 🇺🇦":"🔍 Немає результатів для *{q}* (7 днів).",
        "Italiano 🇮🇹":  "🔍 Nessun risultato per *{q}* (7 giorni).",
        "Español 🇲🇽":   "🔍 Sin resultados para *{q}* (7 días).",
        "Français 🇫🇷":  "🔍 Aucun résultat pour *{q}* (7 jours).",
    },
    "cmd_search_result_hdr": {
        "العربية 🇮🇶":   "🔍 *نتائج البحث عن:* `{q}`\n",
        "English 🇬🇧":   "🔍 *Search results for:* `{q}`\n",
        "Русский 🇷🇺":   "🔍 *Результаты поиска:* `{q}`\n",
        "فارسی 🇮🇷":     "🔍 *نتایج جستجو:* `{q}`\n",
        "हिन्दी 🇮🇳":    "🔍 *खोज परिणाम:* `{q}`\n",
        "Português 🇧🇷": "🔍 *Resultados de busca:* `{q}`\n",
        "Türkçe 🇹🇷":    "🔍 *Arama sonuçları:* `{q}`\n",
        "اردو 🇵🇰":      "🔍 *تلاش نتائج:* `{q}`\n",
        "Deutsch 🇩🇪":   "🔍 *Suchergebnisse für:* `{q}`\n",
        "Українська 🇺🇦":"🔍 *Результати пошуку:* `{q}`\n",
        "Italiano 🇮🇹":  "🔍 *Risultati per:* `{q}`\n",
        "Español 🇲🇽":   "🔍 *Resultados de búsqueda:* `{q}`\n",
        "Français 🇫🇷":  "🔍 *Résultats pour:* `{q}`\n",
    },

    # /ask
    "cmd_ask_usage": {
        "العربية 🇮🇶":   "💬 *محادثة مع الأخبار*\n\nاسألني عن أي حدث:\n`/ask شنو صار اليوم ببغداد؟`\n`/ask ما آخر أخبار النفط؟`",
        "English 🇬🇧":   "💬 *Chat with the News*\n\nAsk me about any event:\n`/ask What happened today?`\n`/ask Latest oil news?`",
        "Русский 🇷🇺":   "💬 *Диалог с новостями*\n\nСпросите о любом событии:\n`/ask Что произошло сегодня?`",
        "فارسی 🇮🇷":     "💬 *گفتگو با اخبار*\n\nدرباره هر رویدادی بپرسید:\n`/ask امروز چه اتفاقی افتاد؟`",
        "हिन्दी 🇮🇳":    "💬 *समाचार चैट*\n\nकोई भी सवाल पूछें:\n`/ask आज क्या हुआ?`",
        "Português 🇧🇷": "💬 *Chat com as Notícias*\n\nPergunte sobre qualquer evento:\n`/ask O que aconteceu hoje?`",
        "Türkçe 🇹🇷":    "💬 *Haberlerle Sohbet*\n\nHerhangi bir olay hakkında sorun:\n`/ask Bugün ne oldu?`",
        "اردو 🇵🇰":      "💬 *خبروں سے بات*\n\nکوئی بھی سوال پوچھیں:\n`/ask آج کیا ہوا؟`",
        "Deutsch 🇩🇪":   "💬 *Mit Nachrichten chatten*\n\nFragen Sie über ein Ereignis:\n`/ask Was passierte heute?`",
        "Українська 🇺🇦":"💬 *Чат з новинами*\n\nЗапитайте про будь-яку подію:\n`/ask Що сталося сьогодні?`",
        "Italiano 🇮🇹":  "💬 *Chat con le Notizie*\n\nChiedi di qualsiasi evento:\n`/ask Cosa è successo oggi?`",
        "Español 🇲🇽":   "💬 *Chat con las Noticias*\n\nPregunta sobre cualquier evento:\n`/ask ¿Qué pasó hoy?`",
        "Français 🇫🇷":  "💬 *Discuter avec les actualités*\n\nPosez une question:\n`/ask Que s'est-il passé aujourd'hui?`",
    },
    "cmd_ask_loading": {
        "العربية 🇮🇶":   "💬 أبحث في الأخبار...",
        "English 🇬🇧":   "💬 Searching the news...",
        "Русский 🇷🇺":   "💬 Ищу в новостях...",
        "فارسی 🇮🇷":     "💬 در حال جستجو...",
        "हिन्दी 🇮🇳":    "💬 खोज रहा हूँ...",
        "Português 🇧🇷": "💬 Pesquisando...",
        "Türkçe 🇹🇷":    "💬 Haberleri arıyorum...",
        "اردو 🇵🇰":      "💬 خبروں میں تلاش...",
        "Deutsch 🇩🇪":   "💬 Suche in Nachrichten...",
        "Українська 🇺🇦":"💬 Шукаю в новинах...",
        "Italiano 🇮🇹":  "💬 Sto cercando...",
        "Español 🇲🇽":   "💬 Buscando noticias...",
        "Français 🇫🇷":  "💬 Recherche en cours...",
    },
    "cmd_ask_footer": {
        "العربية 🇮🇶":   "_مبني على آخر الأخبار المتاحة_",
        "English 🇬🇧":   "_Based on the latest available news_",
        "Русский 🇷🇺":   "_На основе последних доступных новостей_",
        "فارسی 🇮🇷":     "_بر اساس آخرین اخبار_",
        "हिन्दी 🇮🇳":    "_नवीनतम उपलब्ध समाचारों पर आधारित_",
        "Português 🇧🇷": "_Baseado nas últimas notícias disponíveis_",
        "Türkçe 🇹🇷":    "_Mevcut son haberler temel alınmıştır_",
        "اردو 🇵🇰":      "_تازہ ترین خبروں پر مبنی_",
        "Deutsch 🇩🇪":   "_Basierend auf den aktuellsten Nachrichten_",
        "Українська 🇺🇦":"_На основі останніх доступних новин_",
        "Italiano 🇮🇹":  "_Basato sulle ultime notizie disponibili_",
        "Español 🇲🇽":   "_Basado en las últimas noticias disponibles_",
        "Français 🇫🇷":  "_Basé sur les dernières actualités disponibles_",
    },

    # /verify
    "cmd_verify_usage": {
        "العربية 🇮🇶":   "🕵️ *محقق الشائعات*\n\nأرسل النص الذي تريد التحقق منه:\n`/verify انهيار الدينار العراقي خلال 24 ساعة`",
        "English 🇬🇧":   "🕵️ *Fact Checker*\n\nSend the claim you want to verify:\n`/verify Iraqi dinar collapse in 24 hours`",
        "Русский 🇷🇺":   "🕵️ *Проверка фактов*\n\nОтправьте утверждение:\n`/verify Обвал иракского динара`",
        "فارسی 🇮🇷":     "🕵️ *راستی‌آزمایی*\n\nمتن مورد نظر را ارسال کنید:\n`/verify سقوط دینار عراق`",
        "हिन्दी 🇮🇳":    "🕵️ *तथ्य जाँचकर्ता*\n\nजो दावा जांचना हो भेजें:\n`/verify Iraqi dinar collapse`",
        "Português 🇧🇷": "🕵️ *Verificador de Fatos*\n\nEnvie a afirmação:\n`/verify colapso do dinar iraquiano`",
        "Türkçe 🇹🇷":    "🕵️ *Gerçek Kontrolcü*\n\nDoğrulamak istediğiniz metni gönderin:\n`/verify Irak dinarının çöküşü`",
        "اردو 🇵🇰":      "🕵️ *حقائق جانچ*\n\nجو بات چیک کرنی ہو بھیجیں:\n`/verify عراقی دینار کا بحران`",
        "Deutsch 🇩🇪":   "🕵️ *Faktenprüfung*\n\nSenden Sie die Behauptung:\n`/verify Zusammenbruch des Irakischen Dinars`",
        "Українська 🇺🇦":"🕵️ *Перевірка фактів*\n\nНадішліть твердження:\n`/verify Обвал іракського динара`",
        "Italiano 🇮🇹":  "🕵️ *Verifica dei Fatti*\n\nInvia l'affermazione:\n`/verify crollo del dinaro iracheno`",
        "Español 🇲🇽":   "🕵️ *Verificador de Hechos*\n\nEnvía la afirmación:\n`/verify colapso del dinar iraquí`",
        "Français 🇫🇷":  "🕵️ *Vérificateur de Faits*\n\nEnvoyez l'affirmation:\n`/verify effondrement du dinar irakien`",
    },
    "cmd_verify_loading": {
        "العربية 🇮🇶":   "🕵️ جاري التحقق من: _{claim}_...",
        "English 🇬🇧":   "🕵️ Verifying: _{claim}_...",
        "Русский 🇷🇺":   "🕵️ Проверяем: _{claim}_...",
        "فارسی 🇮🇷":     "🕵️ در حال بررسی: _{claim}_...",
        "हिन्दी 🇮🇳":    "🕵️ जाँच हो रही है: _{claim}_...",
        "Português 🇧🇷": "🕵️ Verificando: _{claim}_...",
        "Türkçe 🇹🇷":    "🕵️ Doğrulanıyor: _{claim}_...",
        "اردو 🇵🇰":      "🕵️ تصدیق ہو رہی ہے: _{claim}_...",
        "Deutsch 🇩🇪":   "🕵️ Überprüfe: _{claim}_...",
        "Українська 🇺🇦":"🕵️ Перевіряємо: _{claim}_...",
        "Italiano 🇮🇹":  "🕵️ Verifica in corso: _{claim}_...",
        "Español 🇲🇽":   "🕵️ Verificando: _{claim}_...",
        "Français 🇫🇷":  "🕵️ Vérification: _{claim}_...",
    },

    # /profile
    "cmd_profile_usage": {
        "العربية 🇮🇶":   "🕵️ *محقق الشخصيات*\n\nأرسل اسم السياسي أو المسؤول:\n`/profile محمد شياع السوداني`",
        "English 🇬🇧":   "🕵️ *Profile Builder*\n\nSend the name of the politician or official:\n`/profile Mohammed Al-Sudani`",
        "Русский 🇷🇺":   "🕵️ *Профиль*\n\nОтправьте имя политика:\n`/profile Мухаммед ас-Судани`",
        "فارسی 🇮🇷":     "🕵️ *پروفایل*\n\nنام سیاستمدار را ارسال کنید:\n`/profile محمد السودانی`",
        "हिन्दी 🇮🇳":    "🕵️ *प्रोफ़ाइल बिल्डर*\n\nनाम भेजें:\n`/profile Mohammed Al-Sudani`",
        "Português 🇧🇷": "🕵️ *Perfil*\n\nEnvie o nome:\n`/profile Mohammed Al-Sudani`",
        "Türkçe 🇹🇷":    "🕵️ *Profil Oluşturucu*\n\nAdı gönderin:\n`/profile Mohammed Al-Sudani`",
        "اردو 🇵🇰":      "🕵️ *پروفائل بنانے والا*\n\nنام بھیجیں:\n`/profile محمد السودانی`",
        "Deutsch 🇩🇪":   "🕵️ *Profil*\n\nNamen senden:\n`/profile Mohammed Al-Sudani`",
        "Українська 🇺🇦":"🕵️ *Профіль*\n\nНадішліть ім'я:\n`/profile Mohammed Al-Sudani`",
        "Italiano 🇮🇹":  "🕵️ *Profilo*\n\nInvia il nome:\n`/profile Mohammed Al-Sudani`",
        "Español 🇲🇽":   "🕵️ *Constructor de Perfil*\n\nEnvía el nombre:\n`/profile Mohammed Al-Sudani`",
        "Français 🇫🇷":  "🕵️ *Constructeur de Profil*\n\nEnvoyez le nom:\n`/profile Mohammed Al-Sudani`",
    },
    "cmd_profile_loading": {
        "العربية 🇮🇶":   "🕵️ جاري بناء ملف: *{name}*...",
        "English 🇬🇧":   "🕵️ Building profile: *{name}*...",
        "Русский 🇷🇺":   "🕵️ Составляю профиль: *{name}*...",
        "فارسی 🇮🇷":     "🕵️ در حال ساخت پروفایل: *{name}*...",
        "हिन्दी 🇮🇳":    "🕵️ प्रोफ़ाइल बना रहे: *{name}*...",
        "Português 🇧🇷": "🕵️ Construindo perfil: *{name}*...",
        "Türkçe 🇹🇷":    "🕵️ Profil oluşturuluyor: *{name}*...",
        "اردو 🇵🇰":      "🕵️ پروفائل بنایا جا رہا ہے: *{name}*...",
        "Deutsch 🇩🇪":   "🕵️ Profil wird erstellt: *{name}*...",
        "Українська 🇺🇦":"🕵️ Будую профіль: *{name}*...",
        "Italiano 🇮🇹":  "🕵️ Profilo in costruzione: *{name}*...",
        "Español 🇲🇽":   "🕵️ Construyendo perfil: *{name}*...",
        "Français 🇫🇷":  "🕵️ Construction du profil: *{name}*...",
    },
    "cmd_profile_hdr": {
        "العربية 🇮🇶":   "🕵️ *ملف:*",
        "English 🇬🇧":   "🕵️ *Profile:*",
        "Русский 🇷🇺":   "🕵️ *Профиль:*",
        "فارسی 🇮🇷":     "🕵️ *پروفایل:*",
        "हिन्दी 🇮🇳":    "🕵️ *प्रोफ़ाइल:*",
        "Português 🇧🇷": "🕵️ *Perfil:*",
        "Türkçe 🇹🇷":    "🕵️ *Profil:*",
        "اردو 🇵🇰":      "🕵️ *پروفائل:*",
        "Deutsch 🇩🇪":   "🕵️ *Profil:*",
        "Українська 🇺🇦":"🕵️ *Профіль:*",
        "Italiano 🇮🇹":  "🕵️ *Profilo:*",
        "Español 🇲🇽":   "🕵️ *Perfil:*",
        "Français 🇫🇷":  "🕵️ *Profil:*",
    },

    # /analyze
    "cmd_analyze_usage": {
        "العربية 🇮🇶":   "🧠 *تحليل المزاج السياسي*\n\nأرسل الخبر بعد الأمر:\n`/analyze عنوان الخبر`",
        "English 🇬🇧":   "🧠 *Political Analysis*\n\nSend the news topic:\n`/analyze news headline`",
        "Русский 🇷🇺":   "🧠 *Политический анализ*\n\nОтправьте тему:\n`/analyze заголовок`",
        "فارسی 🇮🇷":     "🧠 *تحلیل سیاسی*\n\nموضوع را ارسال کنید:\n`/analyze عنوان خبر`",
        "हिन्दी 🇮🇳":    "🧠 *राजनीतिक विश्लेषण*\n\nविषय भेजें:\n`/analyze headline`",
        "Português 🇧🇷": "🧠 *Análise Política*\n\nEnvie o tópico:\n`/analyze manchete`",
        "Türkçe 🇹🇷":    "🧠 *Siyasi Analiz*\n\nKonuyu gönderin:\n`/analyze haber başlığı`",
        "اردو 🇵🇰":      "🧠 *سیاسی تجزیہ*\n\nموضوع بھیجیں:\n`/analyze خبر`",
        "Deutsch 🇩🇪":   "🧠 *Politische Analyse*\n\nThema senden:\n`/analyze Schlagzeile`",
        "Українська 🇺🇦":"🧠 *Політичний аналіз*\n\nНадішліть тему:\n`/analyze заголовок`",
        "Italiano 🇮🇹":  "🧠 *Analisi Politica*\n\nInvia il tema:\n`/analyze titolo`",
        "Español 🇲🇽":   "🧠 *Análisis Político*\n\nEnvía el tema:\n`/analyze titular`",
        "Français 🇫🇷":  "🧠 *Analyse Politique*\n\nEnvoyez le sujet:\n`/analyze titre`",
    },
    "cmd_analyze_loading": {
        "العربية 🇮🇶":   "🧠 جاري التحليل السياسي...",
        "English 🇬🇧":   "🧠 Political analysis in progress...",
        "Русский 🇷🇺":   "🧠 Политический анализ...",
        "فارسی 🇮🇷":     "🧠 در حال تحلیل سیاسی...",
        "हिन्दी 🇮🇳":    "🧠 राजनीतिक विश्लेषण...",
        "Português 🇧🇷": "🧠 Análise política em andamento...",
        "Türkçe 🇹🇷":    "🧠 Siyasi analiz yapılıyor...",
        "اردو 🇵🇰":      "🧠 سیاسی تجزیہ جاری...",
        "Deutsch 🇩🇪":   "🧠 Politische Analyse läuft...",
        "Українська 🇺🇦":"🧠 Політичний аналіз...",
        "Italiano 🇮🇹":  "🧠 Analisi politica in corso...",
        "Español 🇲🇽":   "🧠 Análisis político en curso...",
        "Français 🇫🇷":  "🧠 Analyse politique en cours...",
    },
    "cmd_analyze_hdr": {
        "العربية 🇮🇶":   "🧠 *تحليل سياسي*",
        "English 🇬🇧":   "🧠 *Political Analysis*",
        "Русский 🇷🇺":   "🧠 *Политический анализ*",
        "فارسی 🇮🇷":     "🧠 *تحلیل سیاسی*",
        "हिन्दी 🇮🇳":    "🧠 *राजनीतिक विश्लेषण*",
        "Português 🇧🇷": "🧠 *Análise Política*",
        "Türkçe 🇹🇷":    "🧠 *Siyasi Analiz*",
        "اردو 🇵🇰":      "🧠 *سیاسی تجزیہ*",
        "Deutsch 🇩🇪":   "🧠 *Politische Analyse*",
        "Українська 🇺🇦":"🧠 *Політичний аналіз*",
        "Italiano 🇮🇹":  "🧠 *Analisi Politica*",
        "Español 🇲🇽":   "🧠 *Análisis Político*",
        "Français 🇫🇷":  "🧠 *Analyse Politique*",
    },

    # /compare
    "cmd_compare_usage": {
        "العربية 🇮🇶":   "🌐 *مقارنة وجهات النظر*\n\nأرسل الموضوع بعد الأمر:\n`/compare الانتخابات العراقية`",
        "English 🇬🇧":   "🌐 *Compare Perspectives*\n\nSend the topic:\n`/compare Iraq elections`",
        "Русский 🇷🇺":   "🌐 *Сравнение взглядов*\n\nОтправьте тему:\n`/compare выборы в Ираке`",
        "فارسی 🇮🇷":     "🌐 *مقایسه دیدگاه‌ها*\n\nموضوع را ارسال کنید:\n`/compare انتخابات عراق`",
        "हिन्दी 🇮🇳":    "🌐 *दृष्टिकोण तुलना*\n\nविषय भेजें:\n`/compare Iraq elections`",
        "Português 🇧🇷": "🌐 *Comparar Perspectivas*\n\nEnvie o tópico:\n`/compare eleições no Iraque`",
        "Türkçe 🇹🇷":    "🌐 *Perspektif Karşılaştırma*\n\nKonuyu gönderin:\n`/compare Irak seçimleri`",
        "اردو 🇵🇰":      "🌐 *نقطہ نظر موازنہ*\n\nموضوع بھیجیں:\n`/compare عراق انتخابات`",
        "Deutsch 🇩🇪":   "🌐 *Perspektiven vergleichen*\n\nThema senden:\n`/compare Irak-Wahlen`",
        "Українська 🇺🇦":"🌐 *Порівняння поглядів*\n\nНадішліть тему:\n`/compare вибори в Іраку`",
        "Italiano 🇮🇹":  "🌐 *Confronto Prospettive*\n\nInvia il tema:\n`/compare elezioni in Iraq`",
        "Español 🇲🇽":   "🌐 *Comparar Perspectivas*\n\nEnvía el tema:\n`/compare elecciones en Iraq`",
        "Français 🇫🇷":  "🌐 *Comparer les Perspectives*\n\nEnvoyez le sujet:\n`/compare élections en Irak`",
    },
    "cmd_compare_loading": {
        "العربية 🇮🇶":   "🌐 جاري مقارنة المصادر الإعلامية...",
        "English 🇬🇧":   "🌐 Comparing media perspectives...",
        "Русский 🇷🇺":   "🌐 Сравниваю источники...",
        "فارسی 🇮🇷":     "🌐 در حال مقایسه منابع...",
        "हिन्दी 🇮🇳":    "🌐 स्रोतों की तुलना...",
        "Português 🇧🇷": "🌐 Comparando fontes...",
        "Türkçe 🇹🇷":    "🌐 Kaynaklar karşılaştırılıyor...",
        "اردو 🇵🇰":      "🌐 ذرائع کا موازنہ...",
        "Deutsch 🇩🇪":   "🌐 Quellen werden verglichen...",
        "Українська 🇺🇦":"🌐 Порівнюю джерела...",
        "Italiano 🇮🇹":  "🌐 Confronto fonti in corso...",
        "Español 🇲🇽":   "🌐 Comparando fuentes...",
        "Français 🇫🇷":  "🌐 Comparaison des sources...",
    },
    "cmd_compare_hdr": {
        "العربية 🇮🇶":   "🌐 *مقارنة وجهات النظر*\n\n🔎 الموضوع: _{topic}_",
        "English 🇬🇧":   "🌐 *Perspectives Compared*\n\n🔎 Topic: _{topic}_",
        "Русский 🇷🇺":   "🌐 *Сравнение взглядов*\n\n🔎 Тема: _{topic}_",
        "فارسی 🇮🇷":     "🌐 *مقایسه دیدگاه‌ها*\n\n🔎 موضوع: _{topic}_",
        "हिन्दी 🇮🇳":    "🌐 *दृष्टिकोण तुलना*\n\n🔎 विषय: _{topic}_",
        "Português 🇧🇷": "🌐 *Perspectivas Comparadas*\n\n🔎 Tema: _{topic}_",
        "Türkçe 🇹🇷":    "🌐 *Perspektifler Karşılaştırıldı*\n\n🔎 Konu: _{topic}_",
        "اردو 🇵🇰":      "🌐 *نقطہ نظر موازنہ*\n\n🔎 موضوع: _{topic}_",
        "Deutsch 🇩🇪":   "🌐 *Perspektiven verglichen*\n\n🔎 Thema: _{topic}_",
        "Українська 🇺🇦":"🌐 *Порівняння поглядів*\n\n🔎 Тема: _{topic}_",
        "Italiano 🇮🇹":  "🌐 *Prospettive Confrontate*\n\n🔎 Tema: _{topic}_",
        "Español 🇲🇽":   "🌐 *Perspectivas Comparadas*\n\n🔎 Tema: _{topic}_",
        "Français 🇫🇷":  "🌐 *Perspectives Comparées*\n\n🔎 Sujet: _{topic}_",
    },

    # /timeline
    "cmd_timeline_usage": {
        "العربية 🇮🇶":   "📅 *خريطة الأخبار الزمنية*\n\nأرسل الموضوع:\n`/timeline الأزمة السياسية في العراق`",
        "English 🇬🇧":   "📅 *News Timeline*\n\nSend the topic:\n`/timeline Iraq political crisis`",
        "Русский 🇷🇺":   "📅 *Хронология*\n\nОтправьте тему:\n`/timeline политический кризис в Ираке`",
        "فارسی 🇮🇷":     "📅 *جدول زمانی اخبار*\n\nموضوع را ارسال کنید:\n`/timeline بحران سیاسی عراق`",
        "हिन्दी 🇮🇳":    "📅 *समाचार समयरेखा*\n\nविषय भेजें:\n`/timeline Iraq political crisis`",
        "Português 🇧🇷": "📅 *Linha do Tempo*\n\nEnvie o tópico:\n`/timeline crise política no Iraque`",
        "Türkçe 🇹🇷":    "📅 *Haber Zaman Tüneli*\n\nKonuyu gönderin:\n`/timeline Irak siyasi krizi`",
        "اردو 🇵🇰":      "📅 *خبری سلسلہ*\n\nموضوع بھیجیں:\n`/timeline عراق سیاسی بحران`",
        "Deutsch 🇩🇪":   "📅 *Nachrichtenchronik*\n\nThema senden:\n`/timeline politische Krise im Irak`",
        "Українська 🇺🇦":"📅 *Хронологія новин*\n\nНадішліть тему:\n`/timeline політична криза в Іраку`",
        "Italiano 🇮🇹":  "📅 *Cronologia Notizie*\n\nInvia il tema:\n`/timeline crisi politica in Iraq`",
        "Español 🇲🇽":   "📅 *Línea de Tiempo*\n\nEnvía el tema:\n`/timeline crisis política en Irak`",
        "Français 🇫🇷":  "📅 *Chronologie*\n\nEnvoyez le sujet:\n`/timeline crise politique en Irak`",
    },
    "cmd_timeline_loading": {
        "العربية 🇮🇶":   "📅 جاري بناء الخريطة الزمنية...",
        "English 🇬🇧":   "📅 Building timeline...",
        "Русский 🇷🇺":   "📅 Строю хронологию...",
        "فارسی 🇮🇷":     "📅 در حال ساخت جدول زمانی...",
        "हिन्दी 🇮🇳":    "📅 समयरेखा बना रहे...",
        "Português 🇧🇷": "📅 Construindo linha do tempo...",
        "Türkçe 🇹🇷":    "📅 Zaman tüneli oluşturuluyor...",
        "اردو 🇵🇰":      "📅 سلسلہ بنایا جا رہا ہے...",
        "Deutsch 🇩🇪":   "📅 Chronologie wird erstellt...",
        "Українська 🇺🇦":"📅 Будую хронологію...",
        "Italiano 🇮🇹":  "📅 Cronologia in costruzione...",
        "Español 🇲🇽":   "📅 Construyendo línea de tiempo...",
        "Français 🇫🇷":  "📅 Construction de la chronologie...",
    },
    "cmd_timeline_hdr": {
        "العربية 🇮🇶":   "📅 *الخريطة الزمنية*\n\n🔎 الموضوع: _{topic}_",
        "English 🇬🇧":   "📅 *Timeline*\n\n🔎 Topic: _{topic}_",
        "Русский 🇷🇺":   "📅 *Хронология*\n\n🔎 Тема: _{topic}_",
        "فارسی 🇮🇷":     "📅 *جدول زمانی*\n\n🔎 موضوع: _{topic}_",
        "हिन्दी 🇮🇳":    "📅 *समयरेखा*\n\n🔎 विषय: _{topic}_",
        "Português 🇧🇷": "📅 *Linha do Tempo*\n\n🔎 Tema: _{topic}_",
        "Türkçe 🇹🇷":    "📅 *Zaman Tüneli*\n\n🔎 Konu: _{topic}_",
        "اردو 🇵🇰":      "📅 *سلسلہ وار*\n\n🔎 موضوع: _{topic}_",
        "Deutsch 🇩🇪":   "📅 *Chronik*\n\n🔎 Thema: _{topic}_",
        "Українська 🇺🇦":"📅 *Хронологія*\n\n🔎 Тема: _{topic}_",
        "Italiano 🇮🇹":  "📅 *Cronologia*\n\n🔎 Tema: _{topic}_",
        "Español 🇲🇽":   "📅 *Línea de Tiempo*\n\n🔎 Tema: _{topic}_",
        "Français 🇫🇷":  "📅 *Chronologie*\n\n🔎 Sujet: _{topic}_",
    },

    # /predict
    "cmd_predict_usage": {
        "العربية 🇮🇶":   "🔮 *التنبؤ بالأحداث*\n\nأرسل الموضوع:\n`/predict الأزمة السياسية العراقية`\n`/predict أسعار النفط`",
        "English 🇬🇧":   "🔮 *Event Prediction*\n\nSend the topic:\n`/predict Iraq political crisis`\n`/predict oil prices`",
        "Русский 🇷🇺":   "🔮 *Прогноз событий*\n\nОтправьте тему:\n`/predict политический кризис в Ираке`",
        "فارسی 🇮🇷":     "🔮 *پیش‌بینی رویدادها*\n\nموضوع را ارسال کنید:\n`/predict بحران سیاسی عراق`",
        "हिन्दी 🇮🇳":    "🔮 *घटना पूर्वानुमान*\n\nविषय भेजें:\n`/predict Iraq political crisis`",
        "Português 🇧🇷": "🔮 *Previsão de Eventos*\n\nEnvie o tópico:\n`/predict crise política no Iraque`",
        "Türkçe 🇹🇷":    "🔮 *Olay Tahmini*\n\nKonuyu gönderin:\n`/predict Irak siyasi krizi`",
        "اردو 🇵🇰":      "🔮 *واقعات کی پیش گوئی*\n\nموضوع بھیجیں:\n`/predict عراق بحران`",
        "Deutsch 🇩🇪":   "🔮 *Ereignisvorhersage*\n\nThema senden:\n`/predict politische Krise im Irak`",
        "Українська 🇺🇦":"🔮 *Прогнозування подій*\n\nНадішліть тему:\n`/predict політична криза`",
        "Italiano 🇮🇹":  "🔮 *Previsione eventi*\n\nInvia il tema:\n`/predict crisi politica in Iraq`",
        "Español 🇲🇽":   "🔮 *Predicción de Eventos*\n\nEnvía el tema:\n`/predict crisis política en Irak`",
        "Français 🇫🇷":  "🔮 *Prévision d'Événements*\n\nEnvoyez le sujet:\n`/predict crise politique en Irak`",
    },
    "cmd_predict_loading": {
        "العربية 🇮🇶":   "🔮 جاري تحليل الأنماط والتنبؤ بـ: *{topic}*...",
        "English 🇬🇧":   "🔮 Analyzing patterns and predicting: *{topic}*...",
        "Русский 🇷🇺":   "🔮 Анализирую и прогнозирую: *{topic}*...",
        "فارسی 🇮🇷":     "🔮 تحلیل و پیش‌بینی: *{topic}*...",
        "हिन्दी 🇮🇳":    "🔮 विश्लेषण और पूर्वानुमान: *{topic}*...",
        "Português 🇧🇷": "🔮 Analisando e prevendo: *{topic}*...",
        "Türkçe 🇹🇷":    "🔮 Analiz ve tahmin: *{topic}*...",
        "اردو 🇵🇰":      "🔮 تجزیہ اور پیش گوئی: *{topic}*...",
        "Deutsch 🇩🇪":   "🔮 Analyse und Vorhersage: *{topic}*...",
        "Українська 🇺🇦":"🔮 Аналіз і прогноз: *{topic}*...",
        "Italiano 🇮🇹":  "🔮 Analisi e previsione: *{topic}*...",
        "Español 🇲🇽":   "🔮 Análisis y predicción: *{topic}*...",
        "Français 🇫🇷":  "🔮 Analyse et prévision: *{topic}*...",
    },
    "cmd_predict_hdr": {
        "العربية 🇮🇶":   "🔮 *التنبؤات —* _{topic}_",
        "English 🇬🇧":   "🔮 *Predictions —* _{topic}_",
        "Русский 🇷🇺":   "🔮 *Прогнозы —* _{topic}_",
        "فارسی 🇮🇷":     "🔮 *پیش‌بینی‌ها —* _{topic}_",
        "हिन्दी 🇮🇳":    "🔮 *पूर्वानुमान —* _{topic}_",
        "Português 🇧🇷": "🔮 *Previsões —* _{topic}_",
        "Türkçe 🇹🇷":    "🔮 *Tahminler —* _{topic}_",
        "اردو 🇵🇰":      "🔮 *پیش گوئیاں —* _{topic}_",
        "Deutsch 🇩🇪":   "🔮 *Vorhersagen —* _{topic}_",
        "Українська 🇺🇦":"🔮 *Прогнози —* _{topic}_",
        "Italiano 🇮🇹":  "🔮 *Previsioni —* _{topic}_",
        "Español 🇲🇽":   "🔮 *Predicciones —* _{topic}_",
        "Français 🇫🇷":  "🔮 *Prévisions —* _{topic}_",
    },

    # /intel
    "cmd_intel_on": {
        "العربية 🇮🇶":   "🌐 *الخبر قبل الخبر*\n\nالحالة: ✅ مُفعَّل\n\nستصلك الأخبار من المصادر الأجنبية قبل غيرك.",
        "English 🇬🇧":   "🌐 *Foreign Intel Mode*\n\nStatus: ✅ Enabled\n\nYou'll receive news from foreign sources before others.",
        "Русский 🇷🇺":   "🌐 *Иностранная разведка*\n\nСтатус: ✅ Включено\n\nВы будете получать новости из зарубежных источников раньше.",
        "فارسی 🇮🇷":     "🌐 *اخبار از منابع خارجی*\n\nوضعیت: ✅ فعال\n\nاخبار خارجی زودتر دریافت می‌کنید.",
        "हिन्दी 🇮🇳":    "🌐 *विदेशी Intel मोड*\n\nस्थिति: ✅ सक्षम\n\nआप विदेशी स्रोतों से पहले समाचार पाएंगे।",
        "Português 🇧🇷": "🌐 *Modo Intel Estrangeiro*\n\nStatus: ✅ Ativado\n\nVocê receberá notícias de fontes estrangeiras primeiro.",
        "Türkçe 🇹🇷":    "🌐 *Yabancı Haber Modu*\n\nDurum: ✅ Etkin\n\nYabancı kaynaklardan haberleri önce alırsınız.",
        "اردو 🇵🇰":      "🌐 *غیر ملکی خبریں*\n\nحالت: ✅ فعال\n\nآپ پہلے غیر ملکی ذرائع سے خبریں پائیں گے۔",
        "Deutsch 🇩🇪":   "🌐 *Auslandsnachrichten-Modus*\n\nStatus: ✅ Aktiviert\n\nSie erhalten Nachrichten zuerst.",
        "Українська 🇺🇦":"🌐 *Іноземний Intel-режим*\n\nСтатус: ✅ Увімкнено\n\nВи отримуватимете новини першими.",
        "Italiano 🇮🇹":  "🌐 *Modalità Intel Estero*\n\nStato: ✅ Attivato\n\nRiceverai notizie dalle fonti estere prima degli altri.",
        "Español 🇲🇽":   "🌐 *Modo Intel Extranjero*\n\nEstado: ✅ Activado\n\nRecibirás noticias de fuentes extranjeras primero.",
        "Français 🇫🇷":  "🌐 *Mode Intel Étranger*\n\nStatut: ✅ Activé\n\nVous recevrez les actualités des sources étrangères en premier.",
    },
    "cmd_intel_off": {
        "العربية 🇮🇶":   "🌐 *الخبر قبل الخبر*\n\nالحالة: ❌ مُوقَف\n\nأُوقفت هذه الميزة.",
        "English 🇬🇧":   "🌐 *Foreign Intel Mode*\n\nStatus: ❌ Disabled\n\nThis feature has been turned off.",
        "Русский 🇷🇺":   "🌐 *Иностранная разведка*\n\nСтатус: ❌ Отключено",
        "فارسی 🇮🇷":     "🌐 *اخبار خارجی*\n\nوضعیت: ❌ غیرفعال",
        "हिन्दी 🇮🇳":    "🌐 *विदेशी Intel*\n\nस्थिति: ❌ अक्षम",
        "Português 🇧🇷": "🌐 *Intel Estrangeiro*\n\nStatus: ❌ Desativado",
        "Türkçe 🇹🇷":    "🌐 *Yabancı Haber*\n\nDurum: ❌ Devre Dışı",
        "اردو 🇵🇰":      "🌐 *غیر ملکی خبریں*\n\nحالت: ❌ بند",
        "Deutsch 🇩🇪":   "🌐 *Auslandsnachrichten*\n\nStatus: ❌ Deaktiviert",
        "Українська 🇺🇦":"🌐 *Іноземний Intel*\n\nСтатус: ❌ Вимкнено",
        "Italiano 🇮🇹":  "🌐 *Intel Estero*\n\nStato: ❌ Disattivato",
        "Español 🇲🇽":   "🌐 *Intel Extranjero*\n\nEstado: ❌ Desactivado",
        "Français 🇫🇷":  "🌐 *Intel Étranger*\n\nStatut: ❌ Désactivé",
    },

    # /history /today
    "cmd_history_loading": {
        "العربية 🇮🇶":   "📅 *جاري البحث فيما جرى في {date}...*",
        "English 🇬🇧":   "📅 *Searching what happened on {date}...*",
        "Русский 🇷🇺":   "📅 *Ищу события {date}...*",
        "فارسی 🇮🇷":     "📅 *جستجوی رویدادهای {date}...*",
        "हिन्दी 🇮🇳":    "📅 *{date} की घटनाएं खोज रहे...*",
        "Português 🇧🇷": "📅 *Buscando eventos de {date}...*",
        "Türkçe 🇹🇷":    "📅 *{date} olayları aranıyor...*",
        "اردو 🇵🇰":      "📅 *{date} کے واقعات تلاش...*",
        "Deutsch 🇩🇪":   "📅 *Suche Ereignisse von {date}...*",
        "Українська 🇺🇦":"📅 *Шукаю події {date}...*",
        "Italiano 🇮🇹":  "📅 *Ricerca eventi del {date}...*",
        "Español 🇲🇽":   "📅 *Buscando eventos del {date}...*",
        "Français 🇫🇷":  "📅 *Recherche des événements du {date}...*",
    },
    "cmd_history_hdr": {
        "العربية 🇮🇶":   "📅 *ذاكرة الأمة —* {date}",
        "English 🇬🇧":   "📅 *Nation's Memory —* {date}",
        "Русский 🇷🇺":   "📅 *Память нации —* {date}",
        "فارسی 🇮🇷":     "📅 *حافظه ملت —* {date}",
        "हिन्दी 🇮🇳":    "📅 *राष्ट्रीय स्मृति —* {date}",
        "Português 🇧🇷": "📅 *Memória da Nação —* {date}",
        "Türkçe 🇹🇷":    "📅 *Millet Belleği —* {date}",
        "اردو 🇵🇰":      "📅 *قوم کی یادداشت —* {date}",
        "Deutsch 🇩🇪":   "📅 *Gedächtnis der Nation —* {date}",
        "Українська 🇺🇦":"📅 *Пам'ять нації —* {date}",
        "Italiano 🇮🇹":  "📅 *Memoria della Nazione —* {date}",
        "Español 🇲🇽":   "📅 *Memoria de la Nación —* {date}",
        "Français 🇫🇷":  "📅 *Mémoire de la Nation —* {date}",
    },

    # /tip
    "cmd_tip_usage": {
        "العربية 🇮🇶":   "📢 *أرسل لنا خبراً*\n\nإذا شاهدت حدثاً في شارعك أرسله:\n`/tip في الكرادة انفجار صوت قوي الآن`\n\nسيتم مراجعته ونشره إذا تحقق.",
        "English 🇬🇧":   "📢 *Send Us a Tip*\n\nSend something you witnessed:\n`/tip There's a loud explosion in Baghdad now`\n\nWe'll review and publish if verified.",
        "Русский 🇷🇺":   "📢 *Отправьте нам новость*\n\nЧто-то видели? Напишите:\n`/tip Взрыв в центре Багдада`\n\nМы проверим и опубликуем.",
        "فارسی 🇮🇷":     "📢 *ارسال خبر*\n\nچیزی دیدید؟ بنویسید:\n`/tip انفجار در بغداد`",
        "हिन्दी 🇮🇳":    "📢 *टिप भेजें*\n\nकुछ देखा? लिखें:\n`/tip Baghdad में विस्फोट`",
        "Português 🇧🇷": "📢 *Envie uma Dica*\n\nViu algo? Escreva:\n`/tip Explosão em Bagdá`",
        "Türkçe 🇹🇷":    "📢 *İpucu Gönder*\n\nBir şey gördünüz mü? Yazın:\n`/tip Bağdat'ta patlama`",
        "اردو 🇵🇰":      "📢 *ٹپ بھیجیں*\n\nکچھ دیکھا؟ لکھیں:\n`/tip بغداد میں دھماکہ`",
        "Deutsch 🇩🇪":   "📢 *Tipp senden*\n\nEtwas gesehen? Schreiben:\n`/tip Explosion in Bagdad`",
        "Українська 🇺🇦":"📢 *Надіслати підказку*\n\nЩось бачили? Напишіть:\n`/tip Вибух у Багдаді`",
        "Italiano 🇮🇹":  "📢 *Invia Notizia*\n\nHai visto qualcosa? Scrivi:\n`/tip Esplosione a Baghdad`",
        "Español 🇲🇽":   "📢 *Enviar Pista*\n\n¿Viste algo? Escribe:\n`/tip Explosión en Bagdad`",
        "Français 🇫🇷":  "📢 *Envoyer un Tuyau*\n\nVu quelque chose? Écrivez:\n`/tip Explosion à Bagdad`",
    },
    "cmd_tip_success": {
        "العربية 🇮🇶":   "✅ *شكراً! تم استلام تقريرك*\n\nسيتم مراجعته من قِبَل فريقنا وإذا تحقق سيُنشر للجميع.",
        "English 🇬🇧":   "✅ *Thank you! Your report has been received.*\n\nOur team will review it and publish if verified.",
        "Русский 🇷🇺":   "✅ *Спасибо! Ваш репортаж получен.*\n\nМы проверим и опубликуем.",
        "فارسی 🇮🇷":     "✅ *ممنون! گزارش شما دریافت شد.*\n\nبررسی و در صورت تأیید منتشر می‌شود.",
        "हिन्दी 🇮🇳":    "✅ *धन्यवाद! आपकी रिपोर्ट मिल गई।*\n\nसत्यापित होने पर प्रकाशित होगी।",
        "Português 🇧🇷": "✅ *Obrigado! Seu relato foi recebido.*\n\nSerá revisado e publicado se verificado.",
        "Türkçe 🇹🇷":    "✅ *Teşekkürler! Raporunuz alındı.*\n\nDoğrulanırsa yayınlanacak.",
        "اردو 🇵🇰":      "✅ *شکریہ! آپ کی رپورٹ مل گئی۔*\n\nتصدیق ہونے پر شائع ہوگی۔",
        "Deutsch 🇩🇪":   "✅ *Danke! Ihr Bericht wurde empfangen.*\n\nWird geprüft und bei Bestätigung veröffentlicht.",
        "Українська 🇺🇦":"✅ *Дякуємо! Ваш звіт отримано.*\n\nБуде перевірено та опубліковано.",
        "Italiano 🇮🇹":  "✅ *Grazie! Il tuo report è stato ricevuto.*\n\nSarà revisionato e pubblicato se verificato.",
        "Español 🇲🇽":   "✅ *¡Gracias! Tu reporte fue recibido.*\n\nSerá revisado y publicado si se verifica.",
        "Français 🇫🇷":  "✅ *Merci! Votre rapport a été reçu.*\n\nIl sera examiné et publié si vérifié.",
    },

    # /sources
    "cmd_sources_hdr": {
        "العربية 🇮🇶":   "📊 *تصنيف المصادر الإخبارية*\n_(حسب السرعة والكمية — آخر 24 ساعة)_\n\n",
        "English 🇬🇧":   "📊 *News Sources Ranking*\n_(by speed & volume — last 24h)_\n\n",
        "Русский 🇷🇺":   "📊 *Рейтинг источников*\n_(скорость и объём — 24ч)_\n\n",
        "فارسی 🇮🇷":     "📊 *رتبه‌بندی منابع*\n_(سرعت و حجم — ۲۴ ساعت)_\n\n",
        "हिन्दी 🇮🇳":    "📊 *समाचार स्रोत रैंकिंग*\n_(गति और मात्रा — 24 घंटे)_\n\n",
        "Português 🇧🇷": "📊 *Ranking de Fontes*\n_(velocidade e volume — 24h)_\n\n",
        "Türkçe 🇹🇷":    "📊 *Kaynak Sıralaması*\n_(hız ve hacim — son 24 saat)_\n\n",
        "اردو 🇵🇰":      "📊 *خبر ذرائع کی درجہ بندی*\n_(رفتار اور تعداد — 24 گھنٹے)_\n\n",
        "Deutsch 🇩🇪":   "📊 *Quellen-Ranking*\n_(Geschwindigkeit & Volumen — 24h)_\n\n",
        "Українська 🇺🇦":"📊 *Рейтинг джерел*\n_(швидкість та обсяг — 24 год)_\n\n",
        "Italiano 🇮🇹":  "📊 *Classifica Fonti*\n_(velocità e volume — 24h)_\n\n",
        "Español 🇲🇽":   "📊 *Ranking de Fuentes*\n_(velocidad y volumen — 24h)_\n\n",
        "Français 🇫🇷":  "📊 *Classement des Sources*\n_(vitesse et volume — 24h)_\n\n",
    },
    "cmd_sources_nodata": {
        "العربية 🇮🇶":   "📊 *تصنيف المصادر*\n\nلم يتم جمع بيانات كافية بعد.\nسيظهر التصنيف بعد دورات بث عدة.",
        "English 🇬🇧":   "📊 *Source Ranking*\n\nNot enough data yet.\nRanking will appear after several broadcast cycles.",
        "Русский 🇷🇺":   "📊 *Рейтинг источников*\n\nДанных пока недостаточно.",
        "فارسی 🇮🇷":     "📊 *رتبه‌بندی منابع*\n\nداده کافی نیست.",
        "हिन्दी 🇮🇳":    "📊 *स्रोत रैंकिंग*\n\nपर्याप्त डेटा नहीं।",
        "Português 🇧🇷": "📊 *Ranking de Fontes*\n\nDados insuficientes ainda.",
        "Türkçe 🇹🇷":    "📊 *Kaynak Sıralaması*\n\nYeterli veri yok henüz.",
        "اردو 🇵🇰":      "📊 *ذرائع درجہ بندی*\n\nکافی ڈیٹا نہیں ابھی۔",
        "Deutsch 🇩🇪":   "📊 *Quellen-Ranking*\n\nNoch nicht genug Daten.",
        "Українська 🇺🇦":"📊 *Рейтинг джерел*\n\nНедостатньо даних.",
        "Italiano 🇮🇹":  "📊 *Classifica Fonti*\n\nDati insufficienti.",
        "Español 🇲🇽":   "📊 *Ranking de Fuentes*\n\nDatos insuficientes.",
        "Français 🇫🇷":  "📊 *Classement des Sources*\n\nDonnées insuffisantes.",
    },
    "cmd_sources_unit": {
        "العربية 🇮🇶":   "خبر · ⚡ كل",
        "English 🇬🇧":   "stories · ⚡ every",
        "Русский 🇷🇺":   "новостей · ⚡ каждые",
        "فارسی 🇮🇷":     "خبر · ⚡ هر",
        "हिन्दी 🇮🇳":    "समाचार · ⚡ हर",
        "Português 🇧🇷": "notícias · ⚡ a cada",
        "Türkçe 🇹🇷":    "haber · ⚡ her",
        "اردو 🇵🇰":      "خبر · ⚡ ہر",
        "Deutsch 🇩🇪":   "Nachrichten · ⚡ alle",
        "Українська 🇺🇦":"новин · ⚡ кожні",
        "Italiano 🇮🇹":  "notizie · ⚡ ogni",
        "Español 🇲🇽":   "noticias · ⚡ cada",
        "Français 🇫🇷":  "actualités · ⚡ toutes les",
    },
    "cmd_sources_min": {
        "العربية 🇮🇶":   "دقيقة",
        "English 🇬🇧":   "min",
        "Русский 🇷🇺":   "мин",
        "فارسی 🇮🇷":     "دقیقه",
        "हिन्दी 🇮🇳":    "मिनट",
        "Português 🇧🇷": "min",
        "Türkçe 🇹🇷":    "dk",
        "اردو 🇵🇰":      "منٹ",
        "Deutsch 🇩🇪":   "Min",
        "Українська 🇺🇦":"хв",
        "Italiano 🇮🇹":  "min",
        "Español 🇲🇽":   "min",
        "Français 🇫🇷":  "min",
    },

    # /connections
    "cmd_connections_loading": {
        "العربية 🇮🇶":   "🕸 *جاري تحليل الأخبار وإيجاد الروابط الخفية...*",
        "English 🇬🇧":   "🕸 *Analyzing news and finding hidden connections...*",
        "Русский 🇷🇺":   "🕸 *Анализируем новости и ищем скрытые связи...*",
        "فارسی 🇮🇷":     "🕸 *در حال تحلیل اخبار و یافتن ارتباطات پنهان...*",
        "हिन्दी 🇮🇳":    "🕸 *समाचार विश्लेषण और छिपे संबंध खोज रहे...*",
        "Português 🇧🇷": "🕸 *Analisando notícias e encontrando conexões ocultas...*",
        "Türkçe 🇹🇷":    "🕸 *Haberler analiz ediliyor ve gizli bağlantılar aranıyor...*",
        "اردو 🇵🇰":      "🕸 *خبروں کا تجزیہ اور چھپے تعلقات تلاش...*",
        "Deutsch 🇩🇪":   "🕸 *Analyse der Nachrichten und Suche nach versteckten Verbindungen...*",
        "Українська 🇺🇦":"🕸 *Аналіз новин та пошук прихованих зв'язків...*",
        "Italiano 🇮🇹":  "🕸 *Analisi delle notizie e ricerca connessioni nascoste...*",
        "Español 🇲🇽":   "🕸 *Analizando noticias y encontrando conexiones ocultas...*",
        "Français 🇫🇷":  "🕸 *Analyse des actualités et recherche de connexions cachées...*",
    },
    "cmd_connections_hdr": {
        "العربية 🇮🇶":   "🕸 *خريطة العلاقات — آخر {count} خبر*",
        "English 🇬🇧":   "🕸 *Connections Map — Last {count} News*",
        "Русский 🇷🇺":   "🕸 *Карта связей — Последние {count} новостей*",
        "فارسی 🇮🇷":     "🕸 *نقشه ارتباطات — آخرین {count} خبر*",
        "हिन्दी 🇮🇳":    "🕸 *कनेक्शन मैप — अंतिम {count} समाचार*",
        "Português 🇧🇷": "🕸 *Mapa de Conexões — Últimas {count} Notícias*",
        "Türkçe 🇹🇷":    "🕸 *Bağlantı Haritası — Son {count} Haber*",
        "اردو 🇵🇰":      "🕸 *تعلقات نقشہ — آخری {count} خبریں*",
        "Deutsch 🇩🇪":   "🕸 *Verbindungskarte — Letzte {count} Nachrichten*",
        "Українська 🇺🇦":"🕸 *Карта зв'язків — Останні {count} новин*",
        "Italiano 🇮🇹":  "🕸 *Mappa delle Connessioni — Ultime {count} Notizie*",
        "Español 🇲🇽":   "🕸 *Mapa de Conexiones — Últimas {count} Noticias*",
        "Français 🇫🇷":  "🕸 *Carte des Connexions — Dernières {count} Actualités*",
    },

    # /follow
    "cmd_follow_usage": {
        "العربية 🇮🇶":   "🔔 *متابعة قصة إخبارية*\n\nأرسل الكلمة أو الموضوع:\n`/follow العراق`\n`/follow أسعار النفط`\n\nسيُرسل لك البوت فوراً عند ظهور أخبار جديدة.",
        "English 🇬🇧":   "🔔 *Follow a Story*\n\nSend the keyword or topic:\n`/follow Iraq`\n`/follow oil prices`\n\nYou'll be notified instantly of new news.",
        "Русский 🇷🇺":   "🔔 *Следить за темой*\n\nОтправьте ключевое слово:\n`/follow Ирак`\n\nВы получите уведомление о новостях.",
        "فارسی 🇮🇷":     "🔔 *دنبال کردن خبر*\n\nکلمه کلیدی ارسال کنید:\n`/follow عراق`\n\nاخبار جدید فوری دریافت می‌کنید.",
        "हिन्दी 🇮🇳":    "🔔 *कहानी फॉलो करें*\n\nकीवर्ड भेजें:\n`/follow Iraq`\n\nनई खबरों की सूचना मिलेगी।",
        "Português 🇧🇷": "🔔 *Seguir uma História*\n\nEnvie a palavra-chave:\n`/follow Iraq`\n\nVocê receberá notificações.",
        "Türkçe 🇹🇷":    "🔔 *Konuyu Takip Et*\n\nAnahtar kelime gönderin:\n`/follow Irak`\n\nAnında bildirim alırsınız.",
        "اردو 🇵🇰":      "🔔 *خبر فالو کریں*\n\nکلیدی لفظ بھیجیں:\n`/follow عراق`\n\nنئی خبروں پر فوری اطلاع ملے گی۔",
        "Deutsch 🇩🇪":   "🔔 *Thema verfolgen*\n\nStichwort senden:\n`/follow Irak`\n\nSie erhalten sofortige Benachrichtigungen.",
        "Українська 🇺🇦":"🔔 *Стежити за темою*\n\nНадішліть ключове слово:\n`/follow Ірак`\n\nОтримуєте сповіщення.",
        "Italiano 🇮🇹":  "🔔 *Segui una Storia*\n\nInvia la parola chiave:\n`/follow Iraq`\n\nRiceverai notifiche istantanee.",
        "Español 🇲🇽":   "🔔 *Seguir una Historia*\n\nEnvía la palabra clave:\n`/follow Irak`\n\nRecibirás notificaciones.",
        "Français 🇫🇷":  "🔔 *Suivre une Histoire*\n\nEnvoyez le mot-clé:\n`/follow Irak`\n\nVous recevrez des notifications.",
    },
    "cmd_follow_list_hdr": {
        "العربية 🇮🇶":   "🔔 *القصص التي تتابعها:*",
        "English 🇬🇧":   "🔔 *Stories you're following:*",
        "Русский 🇷🇺":   "🔔 *Вы следите за:*",
        "فارسی 🇮🇷":     "🔔 *موضوعاتی که دنبال می‌کنید:*",
        "हिन्दी 🇮🇳":    "🔔 *आप जो फॉलो कर रहे हैं:*",
        "Português 🇧🇷": "🔔 *Histórias que você segue:*",
        "Türkçe 🇹🇷":    "🔔 *Takip ettiğiniz konular:*",
        "اردو 🇵🇰":      "🔔 *آپ جو فالو کر رہے ہیں:*",
        "Deutsch 🇩🇪":   "🔔 *Themen, denen Sie folgen:*",
        "Українська 🇺🇦":"🔔 *Теми, за якими ви стежите:*",
        "Italiano 🇮🇹":  "🔔 *Storie che segui:*",
        "Español 🇲🇽":   "🔔 *Historias que sigues:*",
        "Français 🇫🇷":  "🔔 *Histoires que vous suivez:*",
    },
    "cmd_follow_unfollow_btn": {
        "العربية 🇮🇶":   "❌ إلغاء متابعة: {kw}",
        "English 🇬🇧":   "❌ Unfollow: {kw}",
        "Русский 🇷🇺":   "❌ Отписаться: {kw}",
        "فارسی 🇮🇷":     "❌ لغو دنبال‌کردن: {kw}",
        "हिन्दी 🇮🇳":    "❌ अनफॉलो: {kw}",
        "Português 🇧🇷": "❌ Deixar de seguir: {kw}",
        "Türkçe 🇹🇷":    "❌ Takibi bırak: {kw}",
        "اردو 🇵🇰":      "❌ ان فالو: {kw}",
        "Deutsch 🇩🇪":   "❌ Entfolgen: {kw}",
        "Українська 🇺🇦":"❌ Відписатися: {kw}",
        "Italiano 🇮🇹":  "❌ Smetti di seguire: {kw}",
        "Español 🇲🇽":   "❌ Dejar de seguir: {kw}",
        "Français 🇫🇷":  "❌ Ne plus suivre: {kw}",
    },
    "cmd_follow_press_unfollow": {
        "العربية 🇮🇶":   "\n\nاضغط لإلغاء متابعة أي منها.",
        "English 🇬🇧":   "\n\nPress to unfollow any of them.",
        "Русский 🇷🇺":   "\n\nНажмите для отписки.",
        "فارسی 🇮🇷":     "\n\nبرای لغو دنبال‌کردن بزنید.",
        "हिन्दी 🇮🇳":    "\n\nअनफॉलो के लिए दबाएं।",
        "Português 🇧🇷": "\n\nPressione para deixar de seguir.",
        "Türkçe 🇹🇷":    "\n\nTakibi bırakmak için basın.",
        "اردو 🇵🇰":      "\n\nان فالو کرنے کیلئے دبائیں۔",
        "Deutsch 🇩🇪":   "\n\nDrücken zum Entfolgen.",
        "Українська 🇺🇦":"\n\nНатисніть для відписки.",
        "Italiano 🇮🇹":  "\n\nPremi per smettere di seguire.",
        "Español 🇲🇽":   "\n\nPresiona para dejar de seguir.",
        "Français 🇫🇷":  "\n\nAppuyez pour ne plus suivre.",
    },

    # /unfollow
    "cmd_unfollow_usage": {
        "العربية 🇮🇶":   "❌ مثال: `/unfollow العراق`",
        "English 🇬🇧":   "❌ Example: `/unfollow Iraq`",
        "Русский 🇷🇺":   "❌ Пример: `/unfollow Ирак`",
        "فارسی 🇮🇷":     "❌ مثال: `/unfollow عراق`",
        "हिन्दी 🇮🇳":    "❌ उदाहरण: `/unfollow Iraq`",
        "Português 🇧🇷": "❌ Exemplo: `/unfollow Iraq`",
        "Türkçe 🇹🇷":    "❌ Örnek: `/unfollow Irak`",
        "اردو 🇵🇰":      "❌ مثال: `/unfollow عراق`",
        "Deutsch 🇩🇪":   "❌ Beispiel: `/unfollow Irak`",
        "Українська 🇺🇦":"❌ Приклад: `/unfollow Ірак`",
        "Italiano 🇮🇹":  "❌ Esempio: `/unfollow Iraq`",
        "Español 🇲🇽":   "❌ Ejemplo: `/unfollow Irak`",
        "Français 🇫🇷":  "❌ Exemple: `/unfollow Irak`",
    },
    "cmd_unfollow_done": {
        "العربية 🇮🇶":   "✅ تم إلغاء متابعة: `{kw}`",
        "English 🇬🇧":   "✅ Unfollowed: `{kw}`",
        "Русский 🇷🇺":   "✅ Отписка от: `{kw}`",
        "فارسی 🇮🇷":     "✅ لغو شد: `{kw}`",
        "हिन्दी 🇮🇳":    "✅ अनफॉलो: `{kw}`",
        "Português 🇧🇷": "✅ Deixou de seguir: `{kw}`",
        "Türkçe 🇹🇷":    "✅ Takipten çıkıldı: `{kw}`",
        "اردو 🇵🇰":      "✅ ان فالو: `{kw}`",
        "Deutsch 🇩🇪":   "✅ Entfolgt: `{kw}`",
        "Українська 🇺🇦":"✅ Відписано від: `{kw}`",
        "Italiano 🇮🇹":  "✅ Smesso di seguire: `{kw}`",
        "Español 🇲🇽":   "✅ Dejó de seguir: `{kw}`",
        "Français 🇫🇷":  "✅ Ne suit plus: `{kw}`",
    },

    # /menu_news callback loading
    "cmd_menu_news_loading": {
        "العربية 🇮🇶":   "📰 جاري تحضير آخر الأخبار...",
        "English 🇬🇧":   "📰 Preparing the latest news...",
        "Русский 🇷🇺":   "📰 Готовлю последние новости...",
        "فارسی 🇮🇷":     "📰 در حال آماده‌سازی آخرین اخبار...",
        "हिन्दी 🇮🇳":    "📰 ताज़ा खबरें तैयार हो रहीं...",
        "Português 🇧🇷": "📰 Preparando as últimas notícias...",
        "Türkçe 🇹🇷":    "📰 Son haberler hazırlanıyor...",
        "اردو 🇵🇰":      "📰 تازہ خبریں تیار ہو رہی ہیں...",
        "Deutsch 🇩🇪":   "📰 Neueste Nachrichten werden vorbereitet...",
        "Українська 🇺🇦":"📰 Готую останні новини...",
        "Italiano 🇮🇹":  "📰 Preparazione ultime notizie...",
        "Español 🇲🇽":   "📰 Preparando las últimas noticias...",
        "Français 🇫🇷":  "📰 Préparation des dernières actualités...",
    },
    "cmd_parliament_loading": {
        "العربية 🇮🇶":   "🏛️ جاري جمع آخر أخبار البرلمان...",
        "English 🇬🇧":   "🏛️ Gathering latest parliament news...",
        "Русский 🇷🇺":   "🏛️ Сбор новостей парламента...",
        "فارسی 🇮🇷":     "🏛️ جمع‌آوری اخبار پارلمان...",
        "हिन्दी 🇮🇳":    "🏛️ संसद की ताज़ा खबर...",
        "Português 🇧🇷": "🏛️ Coletando notícias do parlamento...",
        "Türkçe 🇹🇷":    "🏛️ Parlamento haberleri toplanıyor...",
        "اردو 🇵🇰":      "🏛️ پارلیمنٹ کی تازہ خبریں...",
        "Deutsch 🇩🇪":   "🏛️ Parlamentsnachrichten werden gesammelt...",
        "Українська 🇺🇦":"🏛️ Збір новин парламенту...",
        "Italiano 🇮🇹":  "🏛️ Raccolta notizie parlamentari...",
        "Español 🇲🇽":   "🏛️ Recopilando noticias del parlamento...",
        "Français 🇫🇷":  "🏛️ Collecte des nouvelles du parlement...",
    },
    "cmd_influence_usage": {
        "العربية 🇮🇶":   "🗺️ *خريطة النفوذ السياسي*\n\nأرسل الاسم:\n`/influence نوري المالكي`",
        "English 🇬🇧":   "🗺️ *Political Influence Map*\n\nSend the name:\n`/influence Nouri al-Maliki`",
        "Русский 🇷🇺":   "🗺️ *Карта политического влияния*\n\nОтправьте имя:\n`/influence Нури аль-Малики`",
        "فارسی 🇮🇷":     "🗺️ *نقشه نفوذ سیاسی*\n\nنام را ارسال کنید:\n`/influence نوری المالکی`",
        "हिन्दी 🇮🇳":    "🗺️ *राजनीतिक प्रभाव मानचित्र*\n\nनाम भेजें:\n`/influence Nouri al-Maliki`",
        "Português 🇧🇷": "🗺️ *Mapa de Influência Política*\n\nEnvie o nome:\n`/influence Nouri al-Maliki`",
        "Türkçe 🇹🇷":    "🗺️ *Siyasi Etki Haritası*\n\nAdı gönderin:\n`/influence Nouri al-Maliki`",
        "اردو 🇵🇰":      "🗺️ *سیاسی اثر و رسوخ*\n\nنام بھیجیں:\n`/influence نوری المالکی`",
        "Deutsch 🇩🇪":   "🗺️ *Politische Einflusskarte*\n\nNamen senden:\n`/influence Nouri al-Maliki`",
        "Українська 🇺🇦":"🗺️ *Карта політичного впливу*\n\nНадішліть ім'я:\n`/influence Нурі аль-Малікі`",
        "Italiano 🇮🇹":  "🗺️ *Mappa dell'Influenza Politica*\n\nInvia il nome:\n`/influence Nouri al-Maliki`",
        "Español 🇲🇽":   "🗺️ *Mapa de Influencia Política*\n\nEnvía el nombre:\n`/influence Nouri al-Maliki`",
        "Français 🇫🇷":  "🗺️ *Carte d'Influence Politique*\n\nEnvoyez le nom:\n`/influence Nouri al-Maliki`",
    },
    "cmd_influence_loading": {
        "العربية 🇮🇶":   "🗺️ جاري رسم خريطة نفوذ: *{name}*...",
        "English 🇬🇧":   "🗺️ Mapping influence for: *{name}*...",
        "Русский 🇷🇺":   "🗺️ Карта влияния: *{name}*...",
        "فارسی 🇮🇷":     "🗺️ نقشه نفوذ: *{name}*...",
        "हिन्दी 🇮🇳":    "🗺️ *{name}* का प्रभाव मानचित्र...",
        "Português 🇧🇷": "🗺️ Mapeando influência de: *{name}*...",
        "Türkçe 🇹🇷":    "🗺️ Etki haritası: *{name}*...",
        "اردو 🇵🇰":      "🗺️ *{name}* کا اثر نقشہ...",
        "Deutsch 🇩🇪":   "🗺️ Einfluss kartiert: *{name}*...",
        "Українська 🇺🇦":"🗺️ Карта впливу: *{name}*...",
        "Italiano 🇮🇹":  "🗺️ Mappatura influenza: *{name}*...",
        "Español 🇲🇽":   "🗺️ Mapeando influencia de: *{name}*...",
        "Français 🇫🇷":  "🗺️ Cartographie: *{name}*...",
    },
    "cmd_influence_hdr": {
        "العربية 🇮🇶":   "🗺️ *خريطة النفوذ — {name}*",
        "English 🇬🇧":   "🗺️ *Influence Map — {name}*",
        "Русский 🇷🇺":   "🗺️ *Карта влияния — {name}*",
        "فارسی 🇮🇷":     "🗺️ *نقشه نفوذ — {name}*",
        "हिन्दी 🇮🇳":    "🗺️ *प्रभाव मानचित्र — {name}*",
        "Português 🇧🇷": "🗺️ *Mapa de Influência — {name}*",
        "Türkçe 🇹🇷":    "🗺️ *Etki Haritası — {name}*",
        "اردو 🇵🇰":      "🗺️ *اثر نقشہ — {name}*",
        "Deutsch 🇩🇪":   "🗺️ *Einflusskarte — {name}*",
        "Українська 🇺🇦":"🗺️ *Карта впливу — {name}*",
        "Italiano 🇮🇹":  "🗺️ *Mappa Influenza — {name}*",
        "Español 🇲🇽":   "🗺️ *Mapa de Influencia — {name}*",
        "Français 🇫🇷":  "🗺️ *Carte d'Influence — {name}*",
    },
    "cmd_econ_loading": {
        "العربية 🇮🇶":   "📉 جاري جمع المؤشرات الاقتصادية...",
        "English 🇬🇧":   "📉 Gathering economic indicators...",
        "Русский 🇷🇺":   "📉 Сбор экономических показателей...",
        "فارسی 🇮🇷":     "📉 جمع‌آوری شاخص‌های اقتصادی...",
        "हिन्दी 🇮🇳":    "📉 आर्थिक संकेतक एकत्र किए जा रहे हैं...",
        "Português 🇧🇷": "📉 Coletando indicadores econômicos...",
        "Türkçe 🇹🇷":    "📉 Ekonomik göstergeler toplanıyor...",
        "اردو 🇵🇰":      "📉 اقتصادی اشارے جمع ہو رہے ہیں...",
        "Deutsch 🇩🇪":   "📉 Wirtschaftsdaten werden gesammelt...",
        "Українська 🇺🇦":"📉 Збір економічних показників...",
        "Italiano 🇮🇹":  "📉 Raccolta indicatori economici...",
        "Español 🇲🇽":   "📉 Recopilando indicadores económicos...",
        "Français 🇫🇷":  "📉 Collecte des indicateurs économiques...",
    },
    "cmd_econ_hdr": {
        "العربية 🇮🇶":   "📊 *لوحة المؤشرات الاقتصادية*",
        "English 🇬🇧":   "📊 *Economic Indicators Dashboard*",
        "Русский 🇷🇺":   "📊 *Панель экономических показателей*",
        "فارسی 🇮🇷":     "📊 *داشبورد شاخص‌های اقتصادی*",
        "हिन्दी 🇮🇳":    "📊 *आर्थिक संकेतक डैशबोर्ड*",
        "Português 🇧🇷": "📊 *Painel de Indicadores Econômicos*",
        "Türkçe 🇹🇷":    "📊 *Ekonomik Göstergeler Paneli*",
        "اردو 🇵🇰":      "📊 *معاشی اشاریے ڈیش بورڈ*",
        "Deutsch 🇩🇪":   "📊 *Wirtschaftsindikator-Dashboard*",
        "Українська 🇺🇦":"📊 *Панель економічних показників*",
        "Italiano 🇮🇹":  "📊 *Dashboard Indicatori Economici*",
        "Español 🇲🇽":   "📊 *Panel de Indicadores Económicos*",
        "Français 🇫🇷":  "📊 *Tableau de Bord Économique*",
    },
    "cmd_econ_oil": {
        "العربية 🇮🇶":   "🛢️ *النفط الخام:*", "English 🇬🇧": "🛢️ *Crude Oil:*",
        "Русский 🇷🇺":   "🛢️ *Сырая нефть:*", "فارسی 🇮🇷": "🛢️ *نفت خام:*",
        "हिन्दी 🇮🇳":    "🛢️ *कच्चा तेल:*", "Português 🇧🇷": "🛢️ *Petróleo Bruto:*",
        "Türkçe 🇹🇷":    "🛢️ *Ham Petrol:*", "اردو 🇵🇰": "🛢️ *خام تیل:*",
        "Deutsch 🇩🇪":   "🛢️ *Rohöl:*", "Українська 🇺🇦": "🛢️ *Сира нафта:*",
        "Italiano 🇮🇹":  "🛢️ *Petrolio Greggio:*", "Español 🇲🇽": "🛢️ *Petróleo Crudo:*",
        "Français 🇫🇷":  "🛢️ *Pétrole Brut:*",
    },
    "cmd_econ_gold": {
        "العربية 🇮🇶":   "🥇 *الذهب:*", "English 🇬🇧": "🥇 *Gold:*",
        "Русский 🇷🇺":   "🥇 *Золото:*", "فارسی 🇮🇷": "🥇 *طلا:*",
        "हिन्दी 🇮🇳":    "🥇 *सोना:*", "Português 🇧🇷": "🥇 *Ouro:*",
        "Türkçe 🇹🇷":    "🥇 *Altın:*", "اردو 🇵🇰": "🥇 *سونا:*",
        "Deutsch 🇩🇪":   "🥇 *Gold:*", "Українська 🇺🇦": "🥇 *Золото:*",
        "Italiano 🇮🇹":  "🥇 *Oro:*", "Español 🇲🇽": "🥇 *Oro:*",
        "Français 🇫🇷":  "🥇 *Or:*",
    },
    "cmd_econ_dollar": {
        "العربية 🇮🇶":   "💵 *دولار/دينار:*", "English 🇬🇧": "💵 *USD/IQD:*",
        "Русский 🇷🇺":   "💵 *USD/IQD:*", "فارسی 🇮🇷": "💵 *دلار/دینار:*",
        "हिन्दी 🇮🇳":    "💵 *USD/IQD:*", "Português 🇧🇷": "💵 *USD/IQD:*",
        "Türkçe 🇹🇷":    "💵 *USD/IQD:*", "اردو 🇵🇰": "💵 *ڈالر/دینار:*",
        "Deutsch 🇩🇪":   "💵 *USD/IQD:*", "Українська 🇺🇦": "💵 *USD/IQD:*",
        "Italiano 🇮🇹":  "💵 *USD/IQD:*", "Español 🇲🇽": "💵 *USD/IQD:*",
        "Français 🇫🇷":  "💵 *USD/IQD:*",
    },
    "cmd_econ_normal": {
        "العربية 🇮🇶": "✅ طبيعي", "English 🇬🇧": "✅ Normal", "Русский 🇷🇺": "✅ Норма",
        "فارسی 🇮🇷": "✅ طبیعی", "हिन्दी 🇮🇳": "✅ सामान्य", "Português 🇧🇷": "✅ Normal",
        "Türkçe 🇹🇷": "✅ Normal", "اردو 🇵🇰": "✅ معمول", "Deutsch 🇩🇪": "✅ Normal",
        "Українська 🇺🇦": "✅ Нормальний", "Italiano 🇮🇹": "✅ Normale",
        "Español 🇲🇽": "✅ Normal", "Français 🇫🇷": "✅ Normal",
    },
    "cmd_econ_abnormal": {
        "العربية 🇮🇶": "⚠️ خارج النطاق", "English 🇬🇧": "⚠️ Out of Range",
        "Русский 🇷🇺": "⚠️ Вне диапазона", "فارسی 🇮🇷": "⚠️ خارج از محدوده",
        "हिन्दी 🇮🇳": "⚠️ सीमा से बाहर", "Português 🇧🇷": "⚠️ Fora do intervalo",
        "Türkçe 🇹🇷": "⚠️ Aralık dışı", "اردو 🇵🇰": "⚠️ حد سے باہر",
        "Deutsch 🇩🇪": "⚠️ Außerhalb", "Українська 🇺🇦": "⚠️ Поза діапазоном",
        "Italiano 🇮🇹": "⚠️ Fuori intervallo", "Español 🇲🇽": "⚠️ Fuera de rango",
        "Français 🇫🇷": "⚠️ Hors plage",
    },
    "cmd_econ_ai_analysis": {
        "العربية 🇮🇶": "🧠 *تحليل AI:*", "English 🇬🇧": "🧠 *AI Analysis:*",
        "Русский 🇷🇺": "🧠 *Анализ ИИ:*", "فارسی 🇮🇷": "🧠 *تحلیل هوش مصنوعی:*",
        "हिन्दी 🇮🇳": "🧠 *AI विश्लेषण:*", "Português 🇧🇷": "🧠 *Análise de IA:*",
        "Türkçe 🇹🇷": "🧠 *YZ Analizi:*", "اردو 🇵🇰": "🧠 *AI تجزیہ:*",
        "Deutsch 🇩🇪": "🧠 *KI-Analyse:*", "Українська 🇺🇦": "🧠 *Аналіз ШІ:*",
        "Italiano 🇮🇹": "🧠 *Analisi AI:*", "Español 🇲🇽": "🧠 *Análisis IA:*",
        "Français 🇫🇷": "🧠 *Analyse IA:*",
    },
    "cmd_live_usage": {
        "العربية 🇮🇶":   "🔴 *بث مباشر للأحداث*\n\nأرسل الحدث:\n`/live اجتماع البرلمان`\n\n⏱ تحديث كل دقيقتين لمدة 6 ساعات",
        "English 🇬🇧":   "🔴 *Live Event Tracking*\n\nSend the event to track:\n`/live Parliament session`\n\n⏱ Updates every 2 minutes for 6 hours",
        "Русский 🇷🇺":   "🔴 *Прямое отслеживание событий*\n\nОтправьте событие:\n`/live заседание парламента`\n\n⏱ Обновление каждые 2 минуты",
        "فارسی 🇮🇷":     "🔴 *رویداد زنده*\n\nرویداد را ارسال کنید:\n`/live جلسه پارلمان`\n\n⏱ هر 2 دقیقه",
        "हिन्दी 🇮🇳":    "🔴 *लाइव ट्रैकिंग*\n\nइवेंट भेजें:\n`/live संसद सत्र`\n\n⏱ हर 2 मिनट में",
        "Português 🇧🇷": "🔴 *Acompanhamento ao Vivo*\n\nEvento:\n`/live sessão parlamentar`\n\n⏱ A cada 2 minutos",
        "Türkçe 🇹🇷":    "🔴 *Canlı Etkinlik Takibi*\n\nEtkinlik:\n`/live meclis oturumu`\n\n⏱ Her 2 dakikada",
        "اردو 🇵🇰":      "🔴 *لائیو ٹریکنگ*\n\nایونٹ:\n`/live پارلیمنٹ اجلاس`\n\n⏱ ہر 2 منٹ",
        "Deutsch 🇩🇪":   "🔴 *Live-Verfolgung*\n\nEreignis:\n`/live Parlamentssitzung`\n\n⏱ Alle 2 Minuten",
        "Українська 🇺🇦":"🔴 *Живе відстеження*\n\nПодія:\n`/live засідання парламенту`\n\n⏱ Кожні 2 хвилини",
        "Italiano 🇮🇹":  "🔴 *Monitoraggio in Diretta*\n\nEvento:\n`/live sessione parlamentare`\n\n⏱ Ogni 2 minuti",
        "Español 🇲🇽":   "🔴 *Seguimiento en Vivo*\n\nEvento:\n`/live sesión parlamentaria`\n\n⏱ Cada 2 minutos",
        "Français 🇫🇷":  "🔴 *Suivi en Direct*\n\nÉvénement:\n`/live session parlementaire`\n\n⏱ Toutes les 2 minutes",
    },
    "cmd_live_active": {
        "العربية 🇮🇶":   "🔴 أنت الآن تتابع: *{event}*\n\nسيرسل لك تحديث كل دقيقتين.",
        "English 🇬🇧":   "🔴 You are now tracking: *{event}*\n\nUpdates every 2 minutes.",
        "Русский 🇷🇺":   "🔴 Вы отслеживаете: *{event}*\n\nОбновления каждые 2 минуты.",
        "فارسی 🇮🇷":     "🔴 دنبال‌کردن: *{event}*\n\nهر 2 دقیقه بروزرسانی.",
        "हिन्दी 🇮🇳":    "🔴 ट्रैक हो रहा है: *{event}*\n\nहर 2 मिनट में अपडेट।",
        "Português 🇧🇷": "🔴 Você está acompanhando: *{event}*\n\nAtualizações a cada 2 min.",
        "Türkçe 🇹🇷":    "🔴 Takip: *{event}*\n\nHer 2 dakikada güncelleme.",
        "اردو 🇵🇰":      "🔴 ٹریکنگ: *{event}*\n\nہر 2 منٹ میں اپڈیٹ۔",
        "Deutsch 🇩🇪":   "🔴 Verfolgung: *{event}*\n\nUpdates alle 2 Minuten.",
        "Українська 🇺🇦":"🔴 Відстеження: *{event}*\n\nОновлення кожні 2 хв.",
        "Italiano 🇮🇹":  "🔴 Monitoraggio: *{event}*\n\nAggiornamenti ogni 2 min.",
        "Español 🇲🇽":   "🔴 Siguiendo: *{event}*\n\nActualizaciones cada 2 min.",
        "Français 🇫🇷":  "🔴 Suivi: *{event}*\n\nMises à jour toutes les 2 min.",
    },
    "cmd_live_started": {
        "العربية 🇮🇶":   "🔴 *بدأ التتبع المباشر*\n\n📌 الحدث: *{event}*\n⏱ تحديث كل دقيقتين لمدة 6 ساعات",
        "English 🇬🇧":   "🔴 *Live Tracking Started*\n\n📌 Event: *{event}*\n⏱ Updates every 2 minutes for 6 hours",
        "Русский 🇷🇺":   "🔴 *Отслеживание начато*\n\n📌 Событие: *{event}*\n⏱ Каждые 2 минуты, 6 часов",
        "فارسی 🇮🇷":     "🔴 *ردیابی شروع شد*\n\n📌 رویداد: *{event}*\n⏱ هر 2 دقیقه، 6 ساعت",
        "हिन्दी 🇮🇳":    "🔴 *लाइव ट्रैकिंग शुरू*\n\n📌 इवेंट: *{event}*\n⏱ 6 घंटे, हर 2 मिनट",
        "Português 🇧🇷": "🔴 *Rastreamento Iniciado*\n\n📌 Evento: *{event}*\n⏱ A cada 2 min, 6 horas",
        "Türkçe 🇹🇷":    "🔴 *Canlı Takip Başladı*\n\n📌 Etkinlik: *{event}*\n⏱ Her 2 dk, 6 saat",
        "اردو 🇵🇰":      "🔴 *لائیو ٹریکنگ شروع*\n\n📌 ایونٹ: *{event}*\n⏱ ہر 2 منٹ، 6 گھنٹے",
        "Deutsch 🇩🇪":   "🔴 *Live-Verfolgung Gestartet*\n\n📌 Ereignis: *{event}*\n⏱ Alle 2 Min, 6 Std",
        "Українська 🇺🇦":"🔴 *Відстеження розпочато*\n\n📌 Подія: *{event}*\n⏱ Кожні 2 хв, 6 год",
        "Italiano 🇮🇹":  "🔴 *Monitoraggio Avviato*\n\n📌 Evento: *{event}*\n⏱ Ogni 2 min, 6 ore",
        "Español 🇲🇽":   "🔴 *Seguimiento Iniciado*\n\n📌 Evento: *{event}*\n⏱ Cada 2 min, 6 horas",
        "Français 🇫🇷":  "🔴 *Suivi Démarré*\n\n📌 Événement: *{event}*\n⏱ Toutes les 2 min, 6h",
    },
    "cmd_live_stop_btn": {
        "العربية 🇮🇶": "⏹ إيقاف التتبع", "English 🇬🇧": "⏹ Stop Tracking",
        "Русский 🇷🇺": "⏹ Остановить", "فارسی 🇮🇷": "⏹ توقف",
        "हिन्दी 🇮🇳": "⏹ ट्रैकिंग बंद", "Português 🇧🇷": "⏹ Parar",
        "Türkçe 🇹🇷": "⏹ Durdur", "اردو 🇵🇰": "⏹ بند کریں",
        "Deutsch 🇩🇪": "⏹ Stoppen", "Українська 🇺🇦": "⏹ Зупинити",
        "Italiano 🇮🇹": "⏹ Ferma", "Español 🇲🇽": "⏹ Detener",
        "Français 🇫🇷": "⏹ Arrêter",
    },
    "cmd_live_stopped": {
        "العربية 🇮🇶":   "⏹ *تم إيقاف التتبع*\n\nالحدث: *{event}*",
        "English 🇬🇧":   "⏹ *Tracking Stopped*\n\nEvent: *{event}*",
        "Русский 🇷🇺":   "⏹ *Отслеживание остановлено*\n\nСобытие: *{event}*",
        "فارسی 🇮🇷":     "⏹ *ردیابی متوقف شد*\n\nرویداد: *{event}*",
        "हिन्दी 🇮🇳":    "⏹ *ट्रैकिंग रुकी*\n\nइवेंट: *{event}*",
        "Português 🇧🇷": "⏹ *Rastreamento Parado*\n\nEvento: *{event}*",
        "Türkçe 🇹🇷":    "⏹ *Takip Durduruldu*\n\nEtkinlik: *{event}*",
        "اردو 🇵🇰":      "⏹ *ٹریکنگ بند*\n\nایونٹ: *{event}*",
        "Deutsch 🇩🇪":   "⏹ *Verfolgung gestoppt*\n\nEreignis: *{event}*",
        "Українська 🇺🇦":"⏹ *Відстеження зупинено*\n\nПодія: *{event}*",
        "Italiano 🇮🇹":  "⏹ *Monitoraggio Fermato*\n\nEvento: *{event}*",
        "Español 🇲🇽":   "⏹ *Seguimiento Detenido*\n\nEvento: *{event}*",
        "Français 🇫🇷":  "⏹ *Suivi Arrêté*\n\nÉvénement: *{event}*",
    },
    "cmd_live_no_active": {
        "العربية 🇮🇶": "❌ لا يوجد تتبع نشط", "English 🇬🇧": "❌ No active tracking",
        "Русский 🇷🇺": "❌ Нет активного отслеживания", "فارسی 🇮🇷": "❌ ردیابی فعالی نیست",
        "हिन्दी 🇮🇳": "❌ कोई सक्रिय ट्रैकिंग नहीं", "Português 🇧🇷": "❌ Nenhum rastreamento ativo",
        "Türkçe 🇹🇷": "❌ Aktif takip yok", "اردو 🇵🇰": "❌ کوئی فعال ٹریکنگ نہیں",
        "Deutsch 🇩🇪": "❌ Keine aktive Verfolgung", "Українська 🇺🇦": "❌ Немає відстеження",
        "Italiano 🇮🇹": "❌ Nessun monitoraggio", "Español 🇲🇽": "❌ Sin seguimiento activo",
        "Français 🇫🇷": "❌ Aucun suivi actif",
    },
    "cmd_submit_usage": {
        "العربية 🇮🇶":   "📰 *أرسل خبراً من الميدان*\n\nاكتب الخبر بعد الأمر:\n`/submit نص الخبر هنا`\n\n⭐ سيُقيّمه الذكاء الاصطناعي ويُبثّ للمشتركين إن كان موثوقاً.",
        "English 🇬🇧":   "📰 *Submit a field report*\n\nWrite news after the command:\n`/submit your news here`\n\n⭐ AI will rate it and broadcast to subscribers if verified.",
        "Русский 🇷🇺":   "📰 *Отправьте новость с места событий*\n\nНапишите новость после команды:\n`/submit текст новости`",
        "فارسی 🇮🇷":     "📰 *ارسال خبر میدانی*\n\nمتن خبر را بعد از دستور بنویسید:\n`/submit متن خبر`",
        "हिन्दी 🇮🇳":    "📰 *फ़ील्ड रिपोर्ट भेजें*\n\nकमांड के बाद समाचार लिखें:\n`/submit आपकी खबर यहाँ`",
        "Português 🇧🇷": "📰 *Envie uma notícia de campo*\n\nEscreva após o comando:\n`/submit sua notícia aqui`",
        "Türkçe 🇹🇷":    "📰 *Saha haberi gönderin*\n\nKomuttan sonra haberi yazın:\n`/submit haberi buraya yazın`",
        "اردو 🇵🇰":      "📰 *فیلڈ رپورٹ بھیجیں*\n\nکمانڈ کے بعد خبر لکھیں:\n`/submit آپ کی خبر یہاں`",
        "Deutsch 🇩🇪":   "📰 *Feldbericht senden*\n\nNachricht nach dem Befehl schreiben:\n`/submit Ihre Nachricht hier`",
        "Українська 🇺🇦":"📰 *Надіслати польовий репортаж*\n\nНапишіть новину після команди:\n`/submit текст новини`",
        "Italiano 🇮🇹":  "📰 *Invia una notizia sul campo*\n\nScrivi dopo il comando:\n`/submit la tua notizia qui`",
        "Español 🇲🇽":   "📰 *Envía una noticia de campo*\n\nEscribe después del comando:\n`/submit tu noticia aquí`",
        "Français 🇫🇷":  "📰 *Envoyez un rapport de terrain*\n\nÉcrivez après la commande:\n`/submit votre nouvelle ici`",
    },
    "cmd_submit_loading": {
        "العربية 🇮🇶":   "🤖 جاري التحقق من خبرك...",
        "English 🇬🇧":   "🤖 Verifying your report...",
        "Русский 🇷🇺":   "🤖 Проверка вашего репортажа...",
        "فارسی 🇮🇷":     "🤖 در حال تأیید گزارش شما...",
        "हिन्दी 🇮🇳":    "🤖 आपकी रिपोर्ट सत्यापित की जा रही है...",
        "Português 🇧🇷": "🤖 Verificando seu relatório...",
        "Türkçe 🇹🇷":    "🤖 Raporunuz doğrulanıyor...",
        "اردو 🇵🇰":      "🤖 آپ کی رپورٹ تصدیق ہو رہی ہے...",
        "Deutsch 🇩🇪":   "🤖 Ihr Bericht wird überprüft...",
        "Українська 🇺🇦":"🤖 Ваш репортаж перевіряється...",
        "Italiano 🇮🇹":  "🤖 Verifica del reportage...",
        "Español 🇲🇽":   "🤖 Verificando tu reporte...",
        "Français 🇫🇷":  "🤖 Vérification du reportage...",
    },
    "cmd_submit_accepted": {
        "العربية 🇮🇶":   "✅ *تم قبول خبرك ونشره!*\n\n📊 نسبة الموثوقية: `{score}%`\n👥 أُرسل لـ `{count}` مشترك\n\nشكراً! 🙏",
        "English 🇬🇧":   "✅ *Report Accepted and Broadcast!*\n\n📊 Credibility: `{score}%`\n👥 Sent to `{count}` subscribers\n\nThank you! 🙏",
        "Русский 🇷🇺":   "✅ *Репортаж принят и опубликован!*\n\n📊 Достоверность: `{score}%`\n👥 Отправлено `{count}` подписчикам\n\nСпасибо! 🙏",
        "فارسی 🇮🇷":     "✅ *گزارش قبول و منتشر شد!*\n\n📊 اعتبار: `{score}%`\n👥 به `{count}` مشترک ارسال\n\nممنون! 🙏",
        "हिन्दी 🇮🇳":    "✅ *रिपोर्ट स्वीकृत!*\n\n📊 विश्वसनीयता: `{score}%`\n👥 `{count}` सब्सक्राइबर को भेजी\n\nधन्यवाद! 🙏",
        "Português 🇧🇷": "✅ *Relatório Aceito!*\n\n📊 Credibilidade: `{score}%`\n👥 Enviado para `{count}` assinantes\n\nObrigado! 🙏",
        "Türkçe 🇹🇷":    "✅ *Rapor Kabul Edildi!*\n\n📊 Güvenilirlik: `{score}%`\n👥 `{count}` aboneye gönderildi\n\nTeşekkürler! 🙏",
        "اردو 🇵🇰":      "✅ *رپورٹ قبول ہوئی!*\n\n📊 اعتبار: `{score}%`\n👥 `{count}` سبسکرائبرز کو\n\nشکریہ! 🙏",
        "Deutsch 🇩🇪":   "✅ *Bericht Angenommen!*\n\n📊 Glaubwürdigkeit: `{score}%`\n👥 An `{count}` Abonnenten\n\nDanke! 🙏",
        "Українська 🇺🇦":"✅ *Репортаж прийнято!*\n\n📊 Достовірність: `{score}%`\n👥 `{count}` підписникам\n\nДякую! 🙏",
        "Italiano 🇮🇹":  "✅ *Reportage Accettato!*\n\n📊 Credibilità: `{score}%`\n👥 Inviato a `{count}` abbonati\n\nGrazie! 🙏",
        "Español 🇲🇽":   "✅ *¡Reporte Aceptado!*\n\n📊 Credibilidad: `{score}%`\n👥 Enviado a `{count}` suscriptores\n\n¡Gracias! 🙏",
        "Français 🇫🇷":  "✅ *Reportage Accepté!*\n\n📊 Crédibilité: `{score}%`\n👥 Envoyé à `{count}` abonnés\n\nMerci! 🙏",
    },
    "cmd_submit_rejected": {
        "العربية 🇮🇶":   "❌ *لم يُقبل الخبر*\n\n📊 الموثوقية: `{score}%` (يحتاج 60%+)\n📝 السبب: {reason}",
        "English 🇬🇧":   "❌ *Report Not Accepted*\n\n📊 Credibility: `{score}%` (needs 60%+)\n📝 Reason: {reason}",
        "Русский 🇷🇺":   "❌ *Репортаж не принят*\n\n📊 Достоверность: `{score}%`\n📝 Причина: {reason}",
        "فارسی 🇮🇷":     "❌ *گزارش قبول نشد*\n\n📊 اعتبار: `{score}%`\n📝 دلیل: {reason}",
        "हिन्दी 🇮🇳":    "❌ *रिपोर्ट अस्वीकृत*\n\n📊 विश्वसनीयता: `{score}%`\n📝 कारण: {reason}",
        "Português 🇧🇷": "❌ *Relatório Rejeitado*\n\n📊 Credibilidade: `{score}%`\n📝 Motivo: {reason}",
        "Türkçe 🇹🇷":    "❌ *Rapor Reddedildi*\n\n📊 Güvenilirlik: `{score}%`\n📝 Neden: {reason}",
        "اردو 🇵🇰":      "❌ *رپورٹ رد*\n\n📊 اعتبار: `{score}%`\n📝 وجہ: {reason}",
        "Deutsch 🇩🇪":   "❌ *Bericht Abgelehnt*\n\n📊 Glaubwürdigkeit: `{score}%`\n📝 Grund: {reason}",
        "Українська 🇺🇦":"❌ *Репортаж відхилено*\n\n📊 Достовірність: `{score}%`\n📝 Причина: {reason}",
        "Italiano 🇮🇹":  "❌ *Reportage Rifiutato*\n\n📊 Credibilità: `{score}%`\n📝 Motivo: {reason}",
        "Español 🇲🇽":   "❌ *Reporte Rechazado*\n\n📊 Credibilidad: `{score}%`\n📝 Razón: {reason}",
        "Français 🇫🇷":  "❌ *Reportage Rejeté*\n\n📊 Crédibilité: `{score}%`\n📝 Raison: {reason}",
    },

    "bot_paused": {
        "العربية 🇮🇶":   "🔧 البوت متوقف مؤقتاً، سيعود قريباً.",
        "English 🇬🇧":   "🔧 The bot is temporarily paused. It will be back soon.",
        "Русский 🇷🇺":   "🔧 Бот временно приостановлен. Скоро вернётся.",
        "فارسی 🇮🇷":     "🔧 ربات موقتاً متوقف شده است. به زودی برمی‌گردد.",
        "हिन्दी 🇮🇳":    "🔧 बॉट अस्थायी रूप से रुका हुआ है। जल्द वापस आएगा।",
        "Português 🇧🇷": "🔧 O bot está temporariamente pausado. Voltará em breve.",
        "Türkçe 🇹🇷":    "🔧 Bot geçici olarak duraklatıldı. Yakında geri dönecek.",
        "اردو 🇵🇰":      "🔧 بوٹ عارضی طور پر روکا گیا ہے۔ جلد واپس آئے گا۔",
        "Deutsch 🇩🇪":   "🔧 Der Bot ist vorübergehend pausiert. Er kehrt bald zurück.",
        "Українська 🇺🇦":"🔧 Бот тимчасово призупинено. Незабаром повернеться.",
        "Italiano 🇮🇹":  "🔧 Il bot è temporaneamente in pausa. Tornerà presto.",
        "Español 🇲🇽":   "🔧 El bot está temporalmente pausado. Volverá pronto.",
        "Français 🇫🇷":  "🔧 Le bot est temporairement en pause. Il reviendra bientôt.",
    },
    "rate_limited": {
        "العربية 🇮🇶":   "⏳ أنت تستخدم هذه الميزة بسرعة كبيرة. انتظر لحظة ثم حاول مجدداً.",
        "English 🇬🇧":   "⏳ You're using this feature too fast. Please wait a moment and try again.",
        "Русский 🇷🇺":   "⏳ Вы слишком быстро используете эту функцию. Подождите немного.",
        "فارسی 🇮🇷":     "⏳ از این قابلیت خیلی سریع استفاده می‌کنید. لطفاً کمی صبر کنید.",
        "हिन्दी 🇮🇳":    "⏳ आप इस सुविधा का उपयोग बहुत तेज़ कर रहे हैं। कृपया थोड़ा रुकें।",
        "Português 🇧🇷": "⏳ Você está usando este recurso rápido demais. Aguarde um momento.",
        "Türkçe 🇹🇷":    "⏳ Bu özelliği çok hızlı kullanıyorsunuz. Lütfen bekleyin.",
        "اردو 🇵🇰":      "⏳ آپ یہ فیچر بہت تیزی سے استعمال کر رہے ہیں۔ تھوڑا انتظار کریں۔",
        "Deutsch 🇩🇪":   "⏳ Sie nutzen diese Funktion zu schnell. Bitte warten Sie einen Moment.",
        "Українська 🇺🇦":"⏳ Ви занадто швидко використовуєте цю функцію. Зачекайте трохи.",
        "Italiano 🇮🇹":  "⏳ Stai usando questa funzione troppo velocemente. Attendi un momento.",
        "Español 🇲🇽":   "⏳ Estás usando esta función muy rápido. Espera un momento e inténtalo.",
        "Français 🇫🇷":  "⏳ Vous utilisez cette fonctionnalité trop vite. Veuillez patienter.",
    },
    "start_first": {
        "العربية 🇮🇶":   "👋 الرجاء إرسال /start أولاً.",
        "English 🇬🇧":   "👋 Please send /start first.",
        "Русский 🇷🇺":   "👋 Пожалуйста, сначала отправьте /start.",
        "فارسی 🇮🇷":     "👋 لطفاً ابتدا /start را ارسال کنید.",
        "हिन्दी 🇮🇳":    "👋 कृपया पहले /start भेजें।",
        "Português 🇧🇷": "👋 Por favor, envie /start primeiro.",
        "Türkçe 🇹🇷":    "👋 Lütfen önce /start gönderin.",
        "اردو 🇵🇰":      "👋 براہ کرم پہلے /start بھیجیں۔",
        "Deutsch 🇩🇪":   "👋 Bitte senden Sie zuerst /start.",
        "Українська 🇺🇦":"👋 Будь ласка, спочатку надішліть /start.",
        "Italiano 🇮🇹":  "👋 Invia prima /start.",
        "Español 🇲🇽":   "👋 Por favor envía /start primero.",
        "Français 🇫🇷":  "👋 Veuillez d'abord envoyer /start.",
    },
    "referral_join": {
        "العربية 🇮🇶":   "🎉 *انضم شخص جديد عبر رابطك!*\n👤 الاسم: {name}\n👥 إجمالي دعواتك: `{total}`",
        "English 🇬🇧":   "🎉 *Someone joined via your link!*\n👤 Name: {name}\n👥 Total referrals: `{total}`",
        "Русский 🇷🇺":   "🎉 *Новый участник по вашей ссылке!*\n👤 Имя: {name}\n👥 Всего приглашений: `{total}`",
        "فارسی 🇮🇷":     "🎉 *کسی از طریق لینک شما پیوست!*\n👤 نام: {name}\n👥 کل معرفی‌ها: `{total}`",
        "हिन्दी 🇮🇳":    "🎉 *आपके लिंक से कोई जुड़ा!*\n👤 नाम: {name}\n👥 कुल रेफरल: `{total}`",
        "Português 🇧🇷": "🎉 *Alguém entrou pelo seu link!*\n👤 Nome: {name}\n👥 Total de convites: `{total}`",
        "Türkçe 🇹🇷":    "🎉 *Bağlantınız üzerinden biri katıldı!*\n👤 Ad: {name}\n👥 Toplam davet: `{total}`",
        "اردو 🇵🇰":      "🎉 *آپ کے لنک سے کوئی شامل ہوا!*\n👤 نام: {name}\n👥 کل ریفرل: `{total}`",
        "Deutsch 🇩🇪":   "🎉 *Jemand trat über Ihren Link bei!*\n👤 Name: {name}\n👥 Einladungen: `{total}`",
        "Українська 🇺🇦":"🎉 *Хтось приєднався за вашим посиланням!*\n👤 Ім'я: {name}\n👥 Всього запрошень: `{total}`",
        "Italiano 🇮🇹":  "🎉 *Qualcuno si è unito tramite il tuo link!*\n👤 Nome: {name}\n👥 Inviti totali: `{total}`",
        "Español 🇲🇽":   "🎉 *¡Alguien se unió por tu enlace!*\n👤 Nombre: {name}\n👥 Total de invitaciones: `{total}`",
        "Français 🇫🇷":  "🎉 *Quelqu'un a rejoint via votre lien!*\n👤 Nom: {name}\n👥 Total parrainages: `{total}`",
    },
    "referral_progress": {
        "العربية 🇮🇶":   "\n🎯 تحتاج {remaining} دعوة أخرى للمكافأة القادمة!",
        "English 🇬🇧":   "\n🎯 You need {remaining} more invite(s) for the next reward!",
        "Русский 🇷🇺":   "\n🎯 Нужно ещё {remaining} приглашений до следующей награды!",
        "فارسی 🇮🇷":     "\n🎯 برای جایزه بعدی به {remaining} دعوت دیگر نیاز دارید!",
        "हिन्दी 🇮🇳":    "\n🎯 अगले इनाम के लिए {remaining} और आमंत्रण चाहिए!",
        "Português 🇧🇷": "\n🎯 Você precisa de mais {remaining} convite(s) para a próxima recompensa!",
        "Türkçe 🇹🇷":    "\n🎯 Sonraki ödül için {remaining} davet daha gerekiyor!",
        "اردو 🇵🇰":      "\n🎯 اگلے انعام کے لیے {remaining} مزید دعوت درکار!",
        "Deutsch 🇩🇪":   "\n🎯 Sie brauchen {remaining} weitere Einladung(en) für die nächste Belohnung!",
        "Українська 🇺🇦":"\n🎯 Потрібно ще {remaining} запрошень до наступної нагороди!",
        "Italiano 🇮🇹":  "\n🎯 Ti servono ancora {remaining} invito/i per il prossimo premio!",
        "Español 🇲🇽":   "\n🎯 ¡Necesitas {remaining} invitación(es) más para la próxima recompensa!",
        "Français 🇫🇷":  "\n🎯 Il vous faut encore {remaining} invitation(s) pour la prochaine récompense!",
    },
    "referral_milestone": {
        "العربية 🇮🇶":   "\n🏆 وصلت لأعلى مستوى!",
        "English 🇬🇧":   "\n🏆 You reached the highest level!",
        "Русский 🇷🇺":   "\n🏆 Вы достигли высшего уровня!",
        "فارسی 🇮🇷":     "\n🏆 به بالاترین سطح رسیدید!",
        "हिन्दी 🇮🇳":    "\n🏆 आप उच्चतम स्तर पर पहुँच गए!",
        "Português 🇧🇷": "\n🏆 Você alcançou o nível mais alto!",
        "Türkçe 🇹🇷":    "\n🏆 En yüksek seviyeye ulaştınız!",
        "اردو 🇵🇰":      "\n🏆 آپ نے اعلیٰ ترین سطح حاصل کی!",
        "Deutsch 🇩🇪":   "\n🏆 Sie haben das höchste Level erreicht!",
        "Українська 🇺🇦":"\n🏆 Ви досягли найвищого рівня!",
        "Italiano 🇮🇹":  "\n🏆 Hai raggiunto il livello più alto!",
        "Español 🇲🇽":   "\n🏆 ¡Llegaste al nivel más alto!",
        "Français 🇫🇷":  "\n🏆 Vous avez atteint le niveau le plus élevé!",
    },
    "ds_s1": {
        "العربية 🇮🇶":   "🧩 أُحلّل موضوعك وأُحدّد الكلمات المفتاحية...",
        "English 🇬🇧":   "🧩 Analysing your topic and extracting keywords...",
        "Русский 🇷🇺":   "🧩 Анализирую тему и извлекаю ключевые слова...",
        "فارسی 🇮🇷":     "🧩 موضوع را تجزیه‌وتحلیل می‌کنم...",
        "हिन्दी 🇮🇳":    "🧩 विषय का विश्लेषण हो रहा है...",
        "Português 🇧🇷": "🧩 Analisando seu tópico e extraindo palavras-chave...",
        "Türkçe 🇹🇷":    "🧩 Konunuz analiz ediliyor...",
        "اردو 🇵🇰":      "🧩 موضوع کا تجزیہ ہو رہا ہے...",
        "Deutsch 🇩🇪":   "🧩 Ihr Thema wird analysiert...",
        "Українська 🇺🇦":"🧩 Аналізую вашу тему...",
        "Italiano 🇮🇹":  "🧩 Analizzo il tuo argomento...",
        "Español 🇲🇽":   "🧩 Analizando tu tema y extrayendo palabras clave...",
        "Français 🇫🇷":  "🧩 Analyse de votre sujet en cours...",
    },
    "ds_s2": {
        "العربية 🇮🇶":   "📡 أجمع المعلومات من {n} زوايا بحث...",
        "English 🇬🇧":   "📡 Gathering information from {n} search angles...",
        "Русский 🇷🇺":   "📡 Собираю информацию из {n} углов поиска...",
        "فارسی 🇮🇷":     "📡 اطلاعات از {n} زاویه جستجو جمع‌آوری می‌شود...",
        "हिन्दी 🇮🇳":    "📡 {n} खोज कोणों से जानकारी एकत्र हो रही है...",
        "Português 🇧🇷": "📡 Coletando informações de {n} ângulos de pesquisa...",
        "Türkçe 🇹🇷":    "📡 {n} arama açısından bilgi toplanıyor...",
        "اردو 🇵🇰":      "📡 {n} زاویوں سے معلومات جمع ہو رہی ہیں...",
        "Deutsch 🇩🇪":   "📡 Informationen aus {n} Suchwinkeln werden gesammelt...",
        "Українська 🇺🇦":"📡 Збираю інформацію з {n} кутів пошуку...",
        "Italiano 🇮🇹":  "📡 Raccolta informazioni da {n} angoli di ricerca...",
        "Español 🇲🇽":   "📡 Recopilando información desde {n} ángulos de búsqueda...",
        "Français 🇫🇷":  "📡 Collecte d'informations depuis {n} angles de recherche...",
    },
    "ds_s3": {
        "العربية 🇮🇶":   "🔎 أُقيّم موثوقية المصادر وأُفلترها...",
        "English 🇬🇧":   "🔎 Evaluating source reliability and filtering...",
        "Русский 🇷🇺":   "🔎 Оцениваю надёжность источников и фильтрую...",
        "فارسی 🇮🇷":     "🔎 قابلیت اطمینان منابع بررسی می‌شود...",
        "हिन्दी 🇮🇳":    "🔎 स्रोतों की विश्वसनीयता का मूल्यांकन हो रहा है...",
        "Português 🇧🇷": "🔎 Avaliando a confiabilidade das fontes e filtrando...",
        "Türkçe 🇹🇷":    "🔎 Kaynak güvenilirliği değerlendiriliyor...",
        "اردو 🇵🇰":      "🔎 ذرائع کی قابل اعتمادی جانچی جا رہی ہے...",
        "Deutsch 🇩🇪":   "🔎 Quellenzuverlässigkeit wird bewertet...",
        "Українська 🇺🇦":"🔎 Оцінюю надійність джерел...",
        "Italiano 🇮🇹":  "🔎 Valutazione dell'affidabilità delle fonti...",
        "Español 🇲🇽":   "🔎 Evaluando la confiabilidad de las fuentes...",
        "Français 🇫🇷":  "🔎 Évaluation de la fiabilité des sources...",
    },
    "ds_s4": {
        "العربية 🇮🇶":   "🧠 الذكاء الاصطناعي يُحلّل بعمق (9 خطوات)...",
        "English 🇬🇧":   "🧠 AI is performing deep analysis (9 steps)...",
        "Русский 🇷🇺":   "🧠 ИИ выполняет глубокий анализ (9 шагов)...",
        "فارسی 🇮🇷":     "🧠 هوش مصنوعی در حال تجزیه‌وتحلیل عمیق است...",
        "हिन्दी 🇮🇳":    "🧠 AI गहन विश्लेषण कर रहा है...",
        "Português 🇧🇷": "🧠 A IA está realizando análise profunda (9 etapas)...",
        "Türkçe 🇹🇷":    "🧠 Yapay zeka derin analiz yapıyor (9 adım)...",
        "اردو 🇵🇰":      "🧠 AI گہرا تجزیہ کر رہا ہے...",
        "Deutsch 🇩🇪":   "🧠 KI führt tiefe Analyse durch (9 Schritte)...",
        "Українська 🇺🇦":"🧠 ШІ виконує глибокий аналіз (9 кроків)...",
        "Italiano 🇮🇹":  "🧠 L'IA sta eseguendo un'analisi approfondita...",
        "Español 🇲🇽":   "🧠 La IA está realizando un análisis profundo (9 pasos)...",
        "Français 🇫🇷":  "🧠 L'IA effectue une analyse approfondie (9 étapes)...",
    },
    "ds_s4_fuse": {
        "العربية 🇮🇶":   "🔗 دمج المعرفة + كشف التناقضات...",
        "English 🇬🇧":   "🔗 Fusing knowledge & detecting contradictions...",
        "Русский 🇷🇺":   "🔗 Слияние знаний + выявление противоречий...",
        "فارسی 🇮🇷":     "🔗 ادغام دانش + تشخیص تضادها...",
        "हिन्दी 🇮🇳":    "🔗 ज्ञान विलय + विरोधाभास पहचान...",
        "Português 🇧🇷": "🔗 Fundindo conhecimento + detectando contradições...",
        "Türkçe 🇹🇷":    "🔗 Bilgi birleştirme + çelişki tespiti...",
        "اردو 🇵🇰":      "🔗 علم کا انضمام + تضادات کی تلاش...",
        "Deutsch 🇩🇪":   "🔗 Wissen fusionieren + Widersprüche erkennen...",
        "Українська 🇺🇦":"🔗 Злиття знань + виявлення суперечностей...",
        "Italiano 🇮🇹":  "🔗 Fusione conoscenza + rilevamento contraddizioni...",
        "Español 🇲🇽":   "🔗 Fusionando conocimiento + detectando contradicciones...",
        "Français 🇫🇷":  "🔗 Fusion des connaissances + détection des contradictions...",
    },
    "ds_s5": {
        "العربية 🇮🇶":   "📝 أجمّع التقرير النهائي مع المصادر...",
        "English 🇬🇧":   "📝 Compiling the final report with sources...",
        "Русский 🇷🇺":   "📝 Составляю итоговый отчёт с источниками...",
        "فارسی 🇮🇷":     "📝 گزارش نهایی با منابع آماده می‌شود...",
        "हिन्दी 🇮🇳":    "📝 अंतिम रिपोर्ट तैयार हो रही है...",
        "Português 🇧🇷": "📝 Compilando o relatório final com as fontes...",
        "Türkçe 🇹🇷":    "📝 Kaynaklar ile nihai rapor hazırlanıyor...",
        "اردو 🇵🇰":      "📝 حتمی رپورٹ مصادر کے ساتھ تیار ہو رہی ہے...",
        "Deutsch 🇩🇪":   "📝 Abschlussbericht mit Quellen wird erstellt...",
        "Українська 🇺🇦":"📝 Складаю фінальний звіт із джерелами...",
        "Italiano 🇮🇹":  "📝 Compilazione del rapporto finale con le fonti...",
        "Español 🇲🇽":   "📝 Compilando el informe final con las fuentes...",
        "Français 🇫🇷":  "📝 Compilation du rapport final avec les sources...",
    },
    "ds_s6": {
        "العربية 🇮🇶":   "📤 يُرسل التقرير إليك...",
        "English 🇬🇧":   "📤 Sending the report to you...",
        "Русский 🇷🇺":   "📤 Отправляю отчёт...",
        "فارسی 🇮🇷":     "📤 در حال ارسال گزارش...",
        "हिन्दी 🇮🇳":    "📤 रिपोर्ट भेजी जा रही है...",
        "Português 🇧🇷": "📤 Enviando o relatório para você...",
        "Türkçe 🇹🇷":    "📤 Rapor gönderiliyor...",
        "اردو 🇵🇰":      "📤 رپورٹ بھیجی جا رہی ہے...",
        "Deutsch 🇩🇪":   "📤 Bericht wird gesendet...",
        "Українська 🇺🇦":"📤 Відправляю звіт...",
        "Italiano 🇮🇹":  "📤 Invio del rapporto...",
        "Español 🇲🇽":   "📤 Enviando el informe...",
        "Français 🇫🇷":  "📤 Envoi du rapport...",
    },
    "cb_antispam_text": {
        "العربية 🇮🇶": "⏳ لحظة واحدة...", "English 🇬🇧": "⏳ Please wait...",
        "Русский 🇷🇺": "⏳ Подождите...", "فارسی 🇮🇷": "⏳ لحظه‌ای...",
        "हिन्दी 🇮🇳": "⏳ एक पल...", "Português 🇧🇷": "⏳ Aguarde...",
        "Türkçe 🇹🇷": "⏳ Bekleyin...", "اردو 🇵🇰": "⏳ ایک لمحہ...",
        "Deutsch 🇩🇪": "⏳ Bitte warten...", "Українська 🇺🇦": "⏳ Зачекайте...",
        "Italiano 🇮🇹": "⏳ Un momento...", "Español 🇲🇽": "⏳ Un momento...",
        "Français 🇫🇷": "⏳ Un instant...",
    },
    "cmd_verify_hdr": {
        "العربية 🇮🇶":   "🕵️ *نتيجة التحقق*", "English 🇬🇧": "🕵️ *Verification Result*",
        "Русский 🇷🇺":   "🕵️ *Результат проверки*", "فارسی 🇮🇷": "🕵️ *نتیجه تأیید*",
        "हिन्दी 🇮🇳":    "🕵️ *सत्यापन परिणाम*", "Português 🇧🇷": "🕵️ *Resultado da Verificação*",
        "Türkçe 🇹🇷":    "🕵️ *Doğrulama Sonucu*", "اردو 🇵🇰": "🕵️ *تصدیق کا نتیجہ*",
        "Deutsch 🇩🇪":   "🕵️ *Prüfungsergebnis*", "Українська 🇺🇦": "🕵️ *Результат перевірки*",
        "Italiano 🇮🇹":  "🕵️ *Risultato Verifica*", "Español 🇲🇽": "🕵️ *Resultado de Verificación*",
        "Français 🇫🇷":  "🕵️ *Résultat de Vérification*",
    },
    "cmd_verify_verdict_lbl": {
        "العربية 🇮🇶": "الحكم", "English 🇬🇧": "Verdict", "Русский 🇷🇺": "Вердикт",
        "فارسی 🇮🇷": "حکم", "हिन्दी 🇮🇳": "निर्णय", "Português 🇧🇷": "Veredicto",
        "Türkçe 🇹🇷": "Karar", "اردو 🇵🇰": "فیصلہ", "Deutsch 🇩🇪": "Urteil",
        "Українська 🇺🇦": "Вердикт", "Italiano 🇮🇹": "Verdetto",
        "Español 🇲🇽": "Veredicto", "Français 🇫🇷": "Verdict",
    },
    "cmd_verify_confidence_lbl": {
        "العربية 🇮🇶": "الثقة", "English 🇬🇧": "Confidence", "Русский 🇷🇺": "Уверенность",
        "فارسی 🇮🇷": "اطمینان", "हिन्दी 🇮🇳": "विश्वास", "Português 🇧🇷": "Confiança",
        "Türkçe 🇹🇷": "Güven", "اردو 🇵🇰": "اعتماد", "Deutsch 🇩🇪": "Vertrauen",
        "Українська 🇺🇦": "Впевненість", "Italiano 🇮🇹": "Fiducia",
        "Español 🇲🇽": "Confianza", "Français 🇫🇷": "Confiance",
    },
    "cmd_verify_related_news": {
        "العربية 🇮🇶": "📰 أخبار مرتبطة: {count} خبر", "English 🇬🇧": "📰 Related news: {count} articles",
        "Русский 🇷🇺": "📰 Связанных новостей: {count}", "فارسی 🇮🇷": "📰 اخبار مرتبط: {count}",
        "हिन्दी 🇮🇳": "📰 संबंधित समाचार: {count}", "Português 🇧🇷": "📰 Notícias relacionadas: {count}",
        "Türkçe 🇹🇷": "📰 İlgili haberler: {count}", "اردو 🇵🇰": "📰 متعلقہ خبریں: {count}",
        "Deutsch 🇩🇪": "📰 Verwandte Nachrichten: {count}", "Українська 🇺🇦": "📰 Пов'язаних новин: {count}",
        "Italiano 🇮🇹": "📰 Notizie correlate: {count}", "Español 🇲🇽": "📰 Noticias relacionadas: {count}",
        "Français 🇫🇷": "📰 Actualités liées: {count}",
    },
    "cmd_verify_first_src": {
        "العربية 🇮🇶": "🔗 أول مصدر:", "English 🇬🇧": "🔗 First source:", "Русский 🇷🇺": "🔗 Первый источник:",
        "فارسی 🇮🇷": "🔗 اولین منبع:", "हिन्दी 🇮🇳": "🔗 पहला स्रोत:", "Português 🇧🇷": "🔗 Primeira fonte:",
        "Türkçe 🇹🇷": "🔗 İlk kaynak:", "اردو 🇵🇰": "🔗 پہلا ماخذ:", "Deutsch 🇩🇪": "🔗 Erste Quelle:",
        "Українська 🇺🇦": "🔗 Перше джерело:", "Italiano 🇮🇹": "🔗 Prima fonte:",
        "Español 🇲🇽": "🔗 Primera fuente:", "Français 🇫🇷": "🔗 Première source:",
    },
    "cmd_verify_no_sources": {
        "العربية 🇮🇶": "لا توجد أخبار مرتبطة", "English 🇬🇧": "No related news found",
        "Русский 🇷🇺": "Нет связанных новостей", "فارسی 🇮🇷": "خبر مرتبطی یافت نشد",
        "हिन्दी 🇮🇳": "कोई संबंधित समाचार नहीं", "Português 🇧🇷": "Nenhuma notícia relacionada",
        "Türkçe 🇹🇷": "İlgili haber bulunamadı", "اردو 🇵🇰": "کوئی متعلقہ خبر نہیں",
        "Deutsch 🇩🇪": "Keine verwandten Nachrichten", "Українська 🇺🇦": "Пов'язаних новин немає",
        "Italiano 🇮🇹": "Nessuna notizia correlata", "Español 🇲🇽": "No hay noticias relacionadas",
        "Français 🇫🇷": "Aucune actualité liée",
    },
    "ai_err_quota": {
        "العربية 🇮🇶":   "⚠️ *نفد رصيد الذكاء الاصطناعي لهذا اليوم.*\nيتجدد كل 24 ساعة. حاول مجدداً غداً.",
        "English 🇬🇧":   "⚠️ *AI quota exhausted for today.*\nResets every 24 hours. Try again tomorrow.",
        "Русский 🇷🇺":   "⚠️ *Лимит ИИ на сегодня исчерпан.*\nОбновляется каждые 24 часа. Попробуйте завтра.",
        "فارسی 🇮🇷":     "⚠️ *سهمیه هوش مصنوعی امروز تمام شد.*\nهر ۲۴ ساعت تمدید می‌شود.",
        "हिन्दी 🇮🇳":    "⚠️ *आज की AI सीमा समाप्त हो गई।*\n24 घंटे में रीसेट होती है।",
        "Português 🇧🇷": "⚠️ *Cota de IA esgotada hoje.*\nReinicializa em 24 horas. Tente amanhã.",
        "Türkçe 🇹🇷":    "⚠️ *Bugünkü AI kotası tükendi.*\n24 saatte sıfırlanır. Yarın deneyin.",
        "اردو 🇵🇰":      "⚠️ *آج کا AI کوٹہ ختم ہو گیا۔*\n24 گھنٹوں میں دوبارہ شروع ہوتا ہے۔",
        "Deutsch 🇩🇪":   "⚠️ *KI-Kontingent für heute erschöpft.*\nErneuerung in 24 Stunden.",
        "Українська 🇺🇦":"⚠️ *Ліміт ШІ на сьогодні вичерпано.*\nОновлюється кожні 24 години.",
        "Italiano 🇮🇹":  "⚠️ *Quota AI esaurita per oggi.*\nSi rinnova ogni 24 ore.",
        "Español 🇲🇽":   "⚠️ *Cuota de IA agotada hoy.*\nSe renueva cada 24 horas.",
        "Français 🇫🇷":  "⚠️ *Quota IA épuisé aujourd'hui.*\nSe renouvelle dans 24 heures.",
    },
    "ai_err_timeout": {
        "العربية 🇮🇶":   "⏱ *انتهت مهلة الذكاء الاصطناعي.* حاول مجدداً بعد لحظة.",
        "English 🇬🇧":   "⏱ *AI request timed out.* Please try again in a moment.",
        "Русский 🇷🇺":   "⏱ *Время запроса к ИИ истекло.* Попробуйте снова через момент.",
        "فارسی 🇮🇷":     "⏱ *درخواست هوش مصنوعی منقضی شد.* لحظه‌ای بعد دوباره امتحان کنید.",
        "हिन्दी 🇮🇳":    "⏱ *AI अनुरोध समय समाप्त।* एक क्षण बाद पुनः प्रयास करें।",
        "Português 🇧🇷": "⏱ *Tempo de IA esgotado.* Tente novamente em um momento.",
        "Türkçe 🇹🇷":    "⏱ *AI isteği zaman aşımına uğradı.* Bir an sonra tekrar deneyin.",
        "اردو 🇵🇰":      "⏱ *AI درخواست کا وقت ختم ہو گیا۔* تھوڑی دیر بعد دوبارہ کوشش کریں۔",
        "Deutsch 🇩🇪":   "⏱ *KI-Anfrage abgelaufen.* Bitte gleich nochmal versuchen.",
        "Українська 🇺🇦":"⏱ *Час запиту до ШІ вичерпано.* Спробуйте знову за мить.",
        "Italiano 🇮🇹":  "⏱ *Richiesta AI scaduta.* Riprova tra un momento.",
        "Español 🇲🇽":   "⏱ *Tiempo de solicitud de IA agotado.* Inténtalo de nuevo.",
        "Français 🇫🇷":  "⏱ *Délai de la requête IA dépassé.* Réessayez dans un moment.",
    },
    "ai_err_network": {
        "العربية 🇮🇶":   "🌐 *تعذر الاتصال بخادم الذكاء الاصطناعي.* تحقق من الاتصال وأعد المحاولة.",
        "English 🇬🇧":   "🌐 *Could not reach AI server.* Check your connection and try again.",
        "Русский 🇷🇺":   "🌐 *Не удалось подключиться к ИИ.* Проверьте соединение и повторите.",
        "فارسی 🇮🇷":     "🌐 *اتصال به سرور هوش مصنوعی ممکن نشد.* اینترنت را بررسی کنید.",
        "हिन्दी 🇮🇳":    "🌐 *AI सर्वर से कनेक्ट नहीं हो सका।* कनेक्शन जांचें।",
        "Português 🇧🇷": "🌐 *Não foi possível conectar ao servidor de IA.* Verifique a conexão.",
        "Türkçe 🇹🇷":    "🌐 *AI sunucusuna bağlanılamadı.* Bağlantınızı kontrol edin.",
        "اردو 🇵🇰":      "🌐 *AI سرور سے رابطہ نہیں ہو سکا۔* کنکشن چیک کریں۔",
        "Deutsch 🇩🇪":   "🌐 *KI-Server nicht erreichbar.* Verbindung prüfen und nochmal versuchen.",
        "Українська 🇺🇦":"🌐 *Не вдалося підключитися до ШІ.* Перевірте з'єднання.",
        "Italiano 🇮🇹":  "🌐 *Impossibile contattare il server AI.* Controlla la connessione.",
        "Español 🇲🇽":   "🌐 *No se pudo conectar al servidor de IA.* Verifica tu conexión.",
        "Français 🇫🇷":  "🌐 *Impossible de contacter le serveur IA.* Vérifiez votre connexion.",
    },
    "ai_err_unavail": {
        "العربية 🇮🇶":   "🤖 *الذكاء الاصطناعي غير متاح الآن.* قد يكون مفتاح API غير مُهيأ.",
        "English 🇬🇧":   "🤖 *AI is currently unavailable.* The API key may not be configured.",
        "Русский 🇷🇺":   "🤖 *ИИ сейчас недоступен.* Возможно, ключ API не настроен.",
        "فارسی 🇮🇷":     "🤖 *هوش مصنوعی در دسترس نیست.* احتمالاً کلید API پیکربندی نشده.",
        "हिन्दी 🇮🇳":    "🤖 *AI अभी उपलब्ध नहीं है।* API key कॉन्फ़िगर नहीं हो सकती।",
        "Português 🇧🇷": "🤖 *IA indisponível no momento.* A chave API pode não estar configurada.",
        "Türkçe 🇹🇷":    "🤖 *AI şu anda mevcut değil.* API anahtarı yapılandırılmamış olabilir.",
        "اردو 🇵🇰":      "🤖 *AI ابھی دستیاب نہیں۔* API کلید ترتیب نہ دی گئی ہو سکتی ہے۔",
        "Deutsch 🇩🇪":   "🤖 *KI derzeit nicht verfügbar.* API-Schlüssel möglicherweise nicht konfiguriert.",
        "Українська 🇺🇦":"🤖 *ШІ наразі недоступний.* Ключ API може бути не налаштований.",
        "Italiano 🇮🇹":  "🤖 *IA attualmente non disponibile.* La chiave API potrebbe non essere configurata.",
        "Español 🇲🇽":   "🤖 *IA no disponible en este momento.* La clave API puede no estar configurada.",
        "Français 🇫🇷":  "🤖 *IA actuellement indisponible.* La clé API n'est peut-être pas configurée.",
    },
    "ai_err_generic": {
        "العربية 🇮🇶":   "❌ *تعذرت العملية.* أعد المحاولة بعد قليل.",
        "English 🇬🇧":   "❌ *Operation failed.* Please try again shortly.",
        "Русский 🇷🇺":   "❌ *Операция не выполнена.* Попробуйте снова позже.",
        "فارسی 🇮🇷":     "❌ *عملیات ناموفق بود.* لحظه‌ای بعد دوباره امتحان کنید.",
        "हिन्दी 🇮🇳":    "❌ *ऑपरेशन विफल।* थोड़ी देर बाद पुनः प्रयास करें।",
        "Português 🇧🇷": "❌ *Operação falhou.* Tente novamente em breve.",
        "Türkçe 🇹🇷":    "❌ *İşlem başarısız.* Kısa süre sonra tekrar deneyin.",
        "اردو 🇵🇰":      "❌ *آپریشن ناکام ہوا۔* تھوڑی دیر بعد دوبارہ کوشش کریں۔",
        "Deutsch 🇩🇪":   "❌ *Vorgang fehlgeschlagen.* Bitte bald nochmal versuchen.",
        "Українська 🇺🇦":"❌ *Операція не вдалася.* Спробуйте ще раз пізніше.",
        "Italiano 🇮🇹":  "❌ *Operazione fallita.* Riprova tra poco.",
        "Español 🇲🇽":   "❌ *Operación fallida.* Inténtalo de nuevo en breve.",
        "Français 🇫🇷":  "❌ *Opération échouée.* Réessayez dans un moment.",
    },
    "user_banned": {
        "العربية 🇮🇶":   "🚫 أنت محظور من استخدام البوت.",
        "English 🇬🇧":   "🚫 You are banned from using this bot.",
        "Русский 🇷🇺":   "🚫 Вы заблокированы.",
        "فارسی 🇮🇷":     "🚫 شما مسدود شده‌اید.",
        "हिन्दी 🇮🇳":    "🚫 आप प्रतिबंधित हैं।",
        "Português 🇧🇷": "🚫 Você está banido.",
        "Türkçe 🇹🇷":    "🚫 Engellisiniz.",
        "اردو 🇵🇰":      "🚫 آپ پر پابندی ہے۔",
        "Deutsch 🇩🇪":   "🚫 Sie sind gesperrt.",
        "Українська 🇺🇦":"🚫 Вас заблоковано.",
        "Italiano 🇮🇹":  "🚫 Sei bannato.",
        "Español 🇲🇽":   "🚫 Estás baneado.",
        "Français 🇫🇷":  "🚫 Vous êtes banni.",
    },
}

def _init_gemini():
    global _AI_AVAILABLE, _AI_MODEL
    if not GEMINI_API_KEY:
        return

    # قائمة الموديلات بالأولوية — نجرب كل واحد حتى ينجح
    # ملاحظة: gemini-1.5-flash أولاً لأن حدّه المجاني 1500 طلب/يوم
    # بينما gemini-2.5-flash حده المجاني 20 طلب/يوم فقط
    _MODELS_TRY = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
    ]

    # ── محاولة 1: مكتبة google-genai الجديدة ──────────────────────
    try:
        from google import genai as _new_genai
        _client = _new_genai.Client(api_key=GEMINI_API_KEY)

        class _NewModelWrapper:
            def __init__(self, client, model_name, all_models):
                self._client     = client
                self._model      = model_name
                self._all_models = all_models  # قائمة الموديلات البديلة
            def generate_content(self, prompt):
                class _Resp:
                    def __init__(self, text): self.text = text
                # جرّب الموديل الحالي، فإذا نفد الحد (429) جرّب التالي
                models_to_try = [self._model] + [m for m in self._all_models if m != self._model]
                for _m in models_to_try:
                    try:
                        r = self._client.models.generate_content(
                            model=_m, contents=prompt)
                        if _m != self._model:
                            _logger.warning(f"⚠️ تبديل تلقائي لـ {_m} بسبب نفاد حد {self._model}")
                            self._model = _m  # احفظ الموديل الجديد للطلبات القادمة
                        return _Resp(r.text)
                    except Exception as _e:
                        err_str = str(_e)
                        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                            _logger.warning(f"⚠️ حد {_m} نفد (429) — أجرّب الموديل التالي...")
                            continue
                        raise  # خطأ غير متوقع — أرسله للأعلى
                raise Exception("جميع موديلات Gemini نفد حدّها اليومي")

        # جرّب الموديلات بالترتيب حتى ينجح أحدها
        for _m in _MODELS_TRY:
            try:
                _test_wrapper = _NewModelWrapper(_client, _m, _MODELS_TRY)
                _test_resp    = _test_wrapper.generate_content("test")
                if _test_resp.text is not None:
                    _AI_MODEL     = _test_wrapper
                    _AI_AVAILABLE = True
                    _logger.info(f"✅ Gemini AI جاهز — موديل: {_m}")
                    return
            except Exception:
                continue

    except ImportError:
        pass  # نتابع للمحاولة التالية
    except Exception as e:
        _logger.warning(f"⚠️ google-genai خطأ غير متوقع: {e}")

    # ── محاولة 2: مكتبة google-generativeai القديمة ───────────────
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        for _m in _MODELS_TRY:
            try:
                _mdl  = genai.GenerativeModel(_m)
                _resp = _mdl.generate_content("test")
                if _resp.text is not None:
                    _AI_MODEL     = _mdl
                    _AI_AVAILABLE = True
                    _logger.info(f"✅ Gemini AI جاهز (legacy) — موديل: {_m}")
                    return
            except Exception:
                continue

        _logger.warning("⚠️ جميع موديلات Gemini فشلت مع المفتاح الحالي")
    except ImportError:
        _logger.warning("⚠️ مكتبة Gemini غير مثبتة. أضف google-genai لـ requirements.txt")
    except Exception as e:
        _logger.warning(f"⚠️ خطأ في تهيئة Gemini AI: {e}")

_init_gemini()

# ════════════════════════════════════════════════════════════════════
# قسم محرك الذكاء الاصطناعي (AI) — نُقل فعلياً إلى ai.py
# ════════════════════════════════════════════════════════════════════
import ai as _ai_module  # noqa: F401
from ai import *  # noqa: F401, F403
_ai_module._export_all_to(globals())  # يجلب أيضاً الأسماء التي تبدأ بـ _

# =============================================================================
# HEROKU FIX v2: Global callback anti-spam — 1-second cooldown on ALL callbacks
# =============================================================================
_CB_ANTISPAM: dict = {}          # uid -> last_cb_time
_CB_ANTISPAM_LOCK = threading.Lock()
_CB_GLOBAL_COOLDOWN = 1.0        # ثانية واحدة بين أي callback

def _ai_generate(prompt: str) -> str:
    """
    FIX: هذه هي الدالة الأساسية لاستدعاء نموذج Gemini مباشرة — كانت
    مُستخدَمة من +13 ملفاً (بما فيها _ai_call_safe نفسها بالأسفل) لكنها لم
    تكن مُعرَّفة في أي مكان في المشروع كله، فكانت كل ميزات الذكاء الاصطناعي
    (تلخيص، فحص الشائعات، تحليل المشاعر، التوقعات...) تفشل بصمت.
    """
    if not _AI_AVAILABLE or not _AI_MODEL:
        return ""
    try:
        resp = _AI_MODEL.generate_content(prompt)
        text = getattr(resp, "text", "") or ""
        return text.strip()
    except Exception as _e:
        try:
            _logger.warning("⚠️ _ai_generate فشل: %s", _e)
        except Exception:
            pass
        return ""


def _ai_call_safe(prompt: str, timeout: int = 10) -> str:
    """
    استدعاء Gemini AI محمي بـ Circuit Breaker.
    إذا فشل _CB_MAX_FAILS مرات متتالية → يُغلق الدائرة لـ _CB_COOLDOWN ثانية.
    """
    global _cb_fail_count, _cb_open_until
    with _cb_lock:
        if time.time() < _cb_open_until:
            return ""   # الدائرة مفتوحة — لا تُرسل
        if not _AI_AVAILABLE or not _AI_MODEL:
            return ""

    result = [""]
    def _call():
        try:
            _r_ai = _ai_generate(prompt)
            if _r_ai:
                result[0] = _r_ai
        except Exception as _exc:
            _log_exc(_exc)

    t = threading.Thread(target=_call, daemon=True)
    t.start()
    t.join(timeout=timeout)

    with _cb_lock:
        if result[0]:
            _cb_fail_count = 0          # نجح → إعادة العداد
        else:
            _cb_fail_count += 1
            if _cb_fail_count >= _CB_MAX_FAILS:
                _cb_open_until = time.time() + _CB_COOLDOWN
                _cb_fail_count = 0
                try:
                    adm = int(os.environ.get("ADMIN_ID", 0))
                    if adm:
                        bot.send_message(adm,
                            f"⚠️ *Circuit Breaker:* Gemini AI أُوقف تلقائياً لـ {_CB_COOLDOWN//60} دقائق بعد {_CB_MAX_FAILS} فشل متتالية.",
                            parse_mode="Markdown")
                except Exception as _exc:
                    _log_exc(_exc)
    return result[0]


# ── 1b. RSS Feed Health Monitor ───────────────────────────────────────────
_rss_health: dict = {}    # {url: {"status": "ok"/"slow"/"dead", "latency": ms, "last_check": ts}}
_RSS_HEALTH_LOCK = threading.Lock()
