# IraqNow Bot v4.1 — دليل التشغيل على Termux

## الهيكل المُصلَح

| الملف | السطور | المحتوى |
|------|--------|---------|
| `main.py` | 110 | ✅ نقطة الدخول + Long Polling + SIGTERM handling |
| `config.py` | 145 | المفاتيح من env + Feature Flags + الثوابت |
| `bot_legacy.py` | 6,650+ | النواة الرئيسية (جميع الدوال) |
| `db.py` | **جديد** | ✅ stub لـ db module المفقود + `_export_all_to` |
| `ai.py` | **جديد** | ✅ stub لـ ai module المفقود + `_export_all_to` |
| `bot_core.py` | **جديد** | ✅ stub كان مفقوداً من main.py |
| `handlers.py` | **جديد** | ✅ stub لتحميل كل معالجات الأوامر |
| `features_news.py` | **جديد** | ✅ stub لوحدات الأخبار |
| `features_sports.py` | **جديد** | ✅ stub لوحدات الرياضة |
| `features_users.py` | **جديد** | ✅ stub لوحدات المستخدمين |

---

## التشغيل على Termux

### 1. تثبيت المتطلبات الأساسية

```bash
pkg update && pkg upgrade
pkg install python git
```

### 2. تثبيت متطلبات Python

```bash
pip install -r requirements.txt
```

> **ملاحظة**: إذا واجهت مشاكل مع `google-genai` يمكن تعطيله:
> ```bash
> pip install -r requirements.txt --ignore-requires-python
> ```

### 3. إعداد متغيرات البيئة

```bash
cp .env.example .env
nano .env  # أو vim .env
```

أضف القيم الإلزامية على الأقل:
```
BOT_TOKEN=توكن_البوت_من_BotFather
ADMIN_ID=رقم_تيليغرام_الأدمن
```

### 4. تشغيل البوت

```bash
bash start.sh
```

أو مباشرةً:
```bash
python main.py
```

### التشغيل في الخلفية (Termux)

```bash
# تشغيل في الخلفية مع حفظ اللوغ
nohup python main.py > iraqnow_bot.log 2>&1 &
echo $! > bot.pid

# إيقاف البوت
kill $(cat bot.pid)
```

---

## متغيرات البيئة

### إلزامية
| المتغير | الوصف |
|---------|-------|
| `BOT_TOKEN` | توكن البوت من @BotFather |
| `ADMIN_ID` | رقم تيليغرام المشرف الرئيسي |

### اختيارية (AI)
| المتغير | الوصف |
|---------|-------|
| `GEMINI_API_KEY` | Google Gemini (مجاني) |
| `GROQ_API_KEY` | Groq (مجاني، سريع جداً) |
| `OPENROUTER_KEY` | OpenRouter (نماذج متعددة) |
| `TOGETHER_API_KEY` | Together AI |
| `MISTRAL_API_KEY` | Mistral AI |
| `COHERE_API_KEY` | Cohere |

### اختيارية (أخرى)
| المتغير | الوصف |
|---------|-------|
| `WEATHER_KEY` | مفتاح OpenWeatherMap |
| `NEWS_KEY` | مفتاح NewsAPI |
| `IMGBB_API_KEY` | رفع الصور لـ ImgBB |
| `BACKUP_CHANNEL_ID` | قناة النسخ الاحتياطي |

---

## قائمة الأخطاء المُصلَحة

### أخطاء حرجة (كانت تمنع التشغيل)

| # | الخطأ | السبب | الحل |
|---|-------|-------|------|
| 1 | `ModuleNotFoundError: No module named 'db'` | `db.py` كان مفقوداً | إنشاء `db.py` stub |
| 2 | `ModuleNotFoundError: No module named 'ai'` | `ai.py` كان مفقوداً | إنشاء `ai.py` stub |
| 3 | `ModuleNotFoundError: No module named 'bot_core'` | `bot_core.py` كان مفقوداً | إنشاء `bot_core.py` stub |
| 4 | `ModuleNotFoundError: No module named 'handlers'` | `handlers.py` كان مفقوداً | إنشاء `handlers.py` stub |
| 5 | `ModuleNotFoundError: No module named 'features_*'` | ثلاثة ملفات features مفقودة | إنشاء الثلاثة stubs |
| 6 | `NameError: name '_re' is not defined` | `safe_send.py` يستخدم `_re` لكن bot_legacy يُعرِّفه كـ `_re_san` | إضافة `import re as _re` في `safe_send.py` + `_re = _re_san` في `bot_legacy.py` |
| 7 | `NameError: name '_SIGTERM_RECEIVED' is not defined` | `utils.py/_safe_job` يستخدمه لكنه لم يُعرَّف | إضافة `_SIGTERM_RECEIVED = False` في `bot_legacy.py` |
| 8 | `NameError: name 'notify_admin_error' is not defined` | تُستخدَم في bot_legacy لكنها مُعرَّفة في error_tracker.py | إضافة استيراد في أسفل `bot_legacy.py` + fallback محلي |
| 9 | `_job_save_all_users` مجهول في `db_channels.py` | تعريفه في `db_users.py` لا في bot_legacy | `db_channels.py` يُسجِّل المهام الآن بعد تأخير 2 ثانية |

### أخطاء منطقية / بيئة

| # | الخطأ | السبب | الحل |
|---|-------|-------|------|
| 10 | Keep-Alive server يبدأ دائماً | مُصمَّم لـ Heroku | يبدأ الآن فقط إذا كان `PORT` مضبوطاً |
| 11 | لا معالجة لـ SIGTERM | `main.py` لم يُسجِّل معالجاً | إضافة `signal.signal(SIGTERM, ...)` |
| 12 | `Procfile` و `runtime.txt` خاصان بـ Heroku | بيئة مختلفة | تُجاهَل على Termux (في `.gitignore`) |
| 13 | `_export_all_to` غير موجودة | تُستدعى في rss_cache.py و ai_engine.py | مُضافة في `db.py` و `ai.py` |

---

## ملاحظات معمارية

- **النمط المتبع**: "Legacy Hub" — `bot_legacy.py` هو النواة المركزية
- **جميع الملفات** تعتمد على `from bot_legacy import *` للوصول للمتغيرات العالمية
- **التحسين المستقبلي المقترح**: استخراج كل وحدة فعلياً من bot_legacy إلى ملف منفصل

---

## ملاحظات Termux خاصة

1. **اللغة العربية**: يعمل بشكل صحيح (UTF-8 مُعدَّل في أعلى bot_legacy.py)
2. **psutil**: اختياري — مُعالَج بـ try/except داخل الكود
3. **edge-tts**: يعمل ممتاز على Termux (بدون حزم نظام إضافية)
4. **google-genai**: قد يحتاج: `pip install --no-build-isolation google-genai`
5. **الـ Long Polling**: مُهيَّأ بالكامل — لا webhook، لا heroku
