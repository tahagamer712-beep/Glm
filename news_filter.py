# -*- coding: utf-8 -*-
"""
  news_filter.py — لغة + مشاعر + أهمية + ساعات صامتة + alert level

  يُصدِّر دوال تصفية وتقييم الأخبار.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _sentiment_emoji(title):
    """يحلل العنوان ويعيد إيموجي يعبر عن طبيعة الخبر"""
    if not title:
        return ''
    words = set(_re.sub(r'[^\w\s]', ' ', title.lower()).split())
    pos = len(words & _SENTIMENT_POSITIVE)
    neg = len(words & _SENTIMENT_NEGATIVE)
    if neg > pos:
        return '📉'   # سلبي
    elif pos > neg:
        return '📈'   # إيجابي
    return ''          # محايد — لا إيموجي

# ======== فحص الوضع الصامت ذكياً ========
def _is_quiet_hours(uid):
    """HEROKU FIX v4: هل المستخدم في ساعات الهدوء (00:00-06:00 بتوقيته)؟"""
    if not _FF.get("quiet_hours", True):
        return False
    try:
        user = users.get(str(uid), {})
        # tz_offset: UTC offset للمستخدم (افتراضي +3 للعراق)
        tz_offset = int(user.get("tz_offset", 3))
        local_hour = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).hour + tz_offset) % 24
        # هادئ من 00:00 حتى 06:00 بتوقيت المستخدم
        return 0 <= local_hour < 6
    except Exception:
        return False

# ======== مستوى التنبيه لكل مستخدم ========
# 'all' = كل الأخبار, 'important' = مهم+عاجل, 'breaking' = عاجل فقط
def _passes_alert_level(title, uid):
    """هل يُسمح بإرسال هذا الخبر لهذا المستخدم حسب مستوى تنبيهه؟"""
    user = users.get(str(uid), {})
    level = user.get("alert_level", "all")
    if level == "all":
        return True
    score = _news_importance_score(title)
    if level == "important":
        return score >= 1
    if level == "breaking":
        return score >= 2
    return True

# ======== تقييم أهمية الخبر ========
_IMPORTANCE_HIGH = {
    # عربية — عاجل وأمني وكوارث
    'عاجل','عاجلة','طارئ','طارئة','انفجار','انفجارات','اغتيال','اغتيالات',
    'زلزال','فيضان','كارثة','هجوم','هجمات','اشتباك','اشتباكات','سقوط',
    'اعتقال','اعتقالات','اعدام','مجزرة','ضحايا','قتلى','جرحى','شهداء',
    'اختطاف','حريق','انتحار','حادث','تفجير','تفجيرات','قصف','غارة',
    # إنجليزية
    'breaking','urgent','explosion','attack','killed','dead','shooting',
    'earthquake','flood','crash','fire','emergency','arrested','assassination',
    'war','conflict','crisis','disaster','missile','strike','hostage',
    # روسية وتركية وفارسية
    'срочно','взрыв','убийство','катастрофа',
    'acil','patlama','saldırı','deprem',
    'فوری','انفجار','ترور','زلزله',
}
_IMPORTANCE_MEDIUM = {
    # عربية
    'مهم','هام','تحذير','إنذار','قرار','اتفاقية','صفقة','احتجاج',
    'مظاهرة','إضراب','أزمة','ارتفاع','انخفاض','توقيف','مداهمة',
    'تصريح','بيان','وزير','رئيس','برلمان','انتخاب','إلغاء','تعيين',
    # إنجليزية
    'warning','alert','sanctions','protest','summit','election','resign',
    'agreement','deal','minister','parliament','condemned','arrested',
    # تركية وروسية
    'önemli','uyarı','kritik','важно','предупреждение',
}

def _news_importance_score(title):
    """
    يُقيّم أهمية الخبر بناءً على كلماته.
    يُعيد: 2 = عالي (صورة), 1 = متوسط (صورة), 0 = عادي (بدون صورة)
    """
    if not title:
        return 0
    words = set(_re.sub(r'[^\w\s]', ' ', title.lower()).split())
    if words & _IMPORTANCE_HIGH:
        return 2
    if words & _IMPORTANCE_MEDIUM:
        return 1
    return 0

def _should_send_with_image(title):
    """هل يستحق هذا الخبر إرسال صورة معه؟ (فقط الأخبار العاجلة لتجنب تكرار الصور)"""
    return _news_importance_score(title) >= 2

# ======== استخراج صورة المقال (og:image) ========
_OG_IMAGE_CACHE = {}
_OG_IMAGE_LOCK = threading.Lock()

def is_blacklisted(title):
    if not blacklist_words:
        return False
    title_lower = title.lower()
    for word in blacklist_words:
        if word.lower() in title_lower:
            return True
    return False

# =============================================================
# فلتر محتوى قنوات تيليجرام — يمنع البروموشن والإعلانات والألعاب
# =============================================================
_TG_SPAM_PATTERNS = [
    # وصف القنوات
    "قناة متخصصة", "قناة تختص", "قناة رسمية", "قناة تهتم", "قناة تقدم",
    "منصة متخصصة", "نحن نقدم", "نقدم لكم", "تابعونا", "تابعوا قناتنا",
    "انضم إلينا", "انضم الينا", "اشترك في قناتنا", "اشترك معنا",
    "للاشتراك", "للإعلان في قناتنا", "للتعاون والإعلان",
    "للتواصل واتس", "للتواصل اتصل", "للتواصل على واتساب",
    "للتعاون الإعلاني", "تواصل معنا على", "للإعلانات تواصل",
    # ألعاب وترفيه
    "العاب تيليجرام", "telegram games", "تيليجرام قيم", "العاب بوت",
    "ربح من الالعاب", "العب واكسب", "game bot", "gamebot",
    # إعلانات وبروموشن
    "حساب موثق", "قناة موثقة", "اعلانات", "إعلانات", "عروض حصرية",
    "خدماتنا", "خدمات متميزة", "فرصة استثمارية", "استثمر معنا",
    "ربح سريع", "دخل يومي", "ربح من المنزل",
    # محتوى غير إخباري
    "وصفة طبخ", "طبخات", "اكلات", "كورسات مجانية", "كورس مجاني",
    "تحميل مجاني", "تطبيق مجاني", "برنامج مجاني",
    # روابط ترويجية
    "t.me/+", "telegram.me/+", "جروب", "قروب واتساب",
    # تحيات وكلام تافه
    "صباح الخير", "صباح النور", "مساء الخير", "مساء النور",
    "صباح الورد", "صباح الفل", "صباحكم ورد", "مساؤكم نور",
    "تصبح على خير", "تصبحون على خير", "يومكم سعيد", "يوم مبارك",
    "جمعة مباركة", "جمعة طيبة", "أسبوع سعيد", "عيد مبارك",
    "رمضان كريم", "رمضان مبارك", "ليلة مباركة",
    # آراء شخصية وكلام عادي
    "رأيي الشخصي", "شخصياً أعتقد", "على رأيي", "من وجهة نظري",
    "اللي يحبنا", "متابعينا الكرام", "أهلاً وسهلاً",
    "ههههه", "هههههه", "😂😂😂", "😂😂😂😂",
    # دعوات منفردة (ليست خبراً — لكن نتحقق من السياق أدناه)
    "دعاء اليوم", "دعاء الصباح", "دعاء المساء", "اللهم صل على النبي",
    # طلبات تفاعل
    "أعد النشر", "فوروارد", "أرسل لأصحابك",
    "تفاعلوا معنا", "لا تنسى أن تشارك", "أكبر نشر",
    "شاركوا المنشور", "نشروا الخبر",
    # خدمات ومبيعات
    "للبيع", "للإيجار", "بسعر مغري", "عرض لفترة محدودة",
    "اشترِ الآن", "احجز الآن", "سعر خاص",
    # محتوى تعليمي/دراسي (ليس أخباراً)
    "اول متوسط", "ثاني متوسط", "ثالث متوسط",
    "اول ابتدائي", "ثاني ابتدائي", "ثالث ابتدائي",
    "رابع ابتدائي", "خامس ابتدائي", "سادس ابتدائي",
    "اول اعدادي", "ثاني اعدادي", "ثالث اعدادي",
    "رياضيات شهر", "علوم شهر", "لغة عربية شهر",
    "منهج الدراسي", "كتاب مدرسي", "امتحانات وزارية",
    "اسئلة الامتحان", "حل الاسئلة", "شرح الدرس",
    "ملخص المادة", "مادة الرياضيات", "مادة العلوم",
    "مادة التاريخ", "مادة الجغرافية", "التربية الاسلامية",
    "فيزياء شهر", "كيمياء شهر", "احياء شهر",
    "الفصل الدراسي", "نتائج الطلاب", "جدول الامتحانات",
    # دعوات مشاركة/تفاعل (نهايات رسائل القنوات)
    "لا تنسى المشاركة", "لا تنسوا المشاركة",
    "لا تنسى الاشتراك", "لا تنسوا الاشتراك",
    "شارك الخبر مع", "شارك مع اصدقائك",
    "اضغط متابعة", "فعّل الاشعارات",
    # محتوى ديني غير إخباري
    "تفسير الآية", "حديث شريف", "قال رسول الله",
    "دعاء مستجاب", "ثواب عظيم",
    # ترفيه ونكت
    "نكتة اليوم", "لطيفة اليوم", "تحدي اليوم",
    "معلومة طريفة", "هل تعلم ان",
]

# أنماط تشير إلى محادثة عادية (regex)
import re as _re_spam
_TG_SPAM_REGEX = [
    _re_spam.compile(r"^[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001FFFF\s]{1,20}$"),  # إيموجي فقط
    _re_spam.compile(r"^[.،!؟?]{1,10}$"),   # ترقيم فقط
    _re_spam.compile(r"^(نعم|لا|أيوه|آه|ايوه|طيب|اوك|ok|yes|no|هم){1,3}[\s.،!؟]*$", _re_spam.IGNORECASE),
    # "لا تنسى المشاركة @قناة" أو "لا تنسوا المشاركة @قناة" — دعوة اشتراك
    _re_spam.compile(r"لا\s+تنس[ىيوو]+\s+المشاركة\s*@", _re_spam.IGNORECASE),
    # رياضيات/مواد دراسية + مستوى دراسي = محتوى تعليمي وليس خبراً
    _re_spam.compile(r"(رياضيات|علوم|فيزياء|كيمياء|احياء|جغرافية|تاريخ)\s+(شهر|اول|ثاني|ثالث|الفصل)", _re_spam.IGNORECASE),
]

def _check_breaking_news(title: str, source_url: str) -> bool:
    """Return True if this title crosses the breaking-news threshold."""
    if not _FF.get("breaking_news", True):
        return False
    if not title:
        return False
    words = [w for w in title.lower().split() if len(w) >= 4][:8]
    if len(words) < 2:
        return False
    key = hashlib.md5(" ".join(words).encode()).hexdigest()[:12]
    now = time.time()
    with _breaking_lock:
        hits = _breaking_counter.setdefault(key, [])
        # Remove stale hits
        hits[:] = [(ts, src) for ts, src in hits if now - ts < _BREAKING_WINDOW_SECS]
        # Add current source if not already in window
        sources_in_window = {src for _, src in hits}
        if source_url not in sources_in_window:
            hits.append((now, source_url))
        return len(hits) >= _BREAKING_THRESHOLD


def _feat_ok(key: str) -> bool:
    """يُعيد True إذا الميزة ليست ملغية (disabled) — لإخفاء الأزرار.

    ملاحظة: "disabled" يعني الأدمن أوقف الميزة نهائياً من لوحة إدارة الميزات،
    وهذا يجب أن يُطبَّق دائماً بغض النظر عن حالة _FEATURE_GATING_ACTIVE (نظام
    القيود العام يتحكم فقط بحدود limited/premium_only، وليس بإخفاء ميزة مُلغاة).
    """
    return _FEATURE_REGISTRY.get(key, {}).get("mode", "free") != "disabled"

def _check_disinfo(title: str, lang: str) -> bool:
    """يكتشف إذا كان الخبر عبارة عن تحقق/تفنيد لادعاء."""
    t = title.lower()
    return any(pat.lower() in t for pat in _DISINFO_PATTERNS)

