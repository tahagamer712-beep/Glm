# -*- coding: utf-8 -*-
"""
  news_dedup.py — Jaccard + cosine similarity + كشف التكرار

  يُصدِّر دوال كشف التكرار في الأخبار.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

def _title_words(title):
    """استخرج الكلمات المهمة من العنوان للمقارنة"""
    words = _re.sub(r'[^\w\s]', ' ', title.lower()).split()
    stop = {'the','a','an','of','in','on','at','to','for','is','are','was','were',
            'و','في','من','على','إلى','أن','هذا','هذه','ذلك','التي','الذي',
            'مع','عن','لا','ما','أو','لم','قد','كان','كانت','يكون','تكون'}
    return set(w for w in words if w not in stop and len(w) > 2)

def _bigram_set(text):
    """تحويل النص لمجموعة bigrams (زوجين من الحروف) لكشف أدق"""
    words = list(_title_words(text))
    return {f"{words[i]}_{words[i+1]}" for i in range(len(words)-1)}

def _cosine_similarity_titles(t1, t2):
    """تشابه Cosine مبسّط عبر تردد الكلمات"""
    w1 = list(_title_words(t1))
    w2 = list(_title_words(t2))
    if not w1 or not w2:
        return 0.0
    all_words = set(w1) | set(w2)
    v1 = {w: w1.count(w) for w in all_words}
    v2 = {w: w2.count(w) for w in all_words}
    dot   = sum(v1[w] * v2[w] for w in all_words)
    norm1 = sum(x**2 for x in v1.values()) ** 0.5
    norm2 = sum(x**2 for x in v2.values()) ** 0.5
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

def _is_similar_title(t1, t2, threshold=0.72):
    """
    هل العنوانان يتحدثان عن نفس الخبر؟
    يستخدم Jaccard + Cosine + Bigram معاً لكشف أشمل.
    """
    w1, w2 = _title_words(t1), _title_words(t2)
    if not w1 or not w2:
        return False
    # Jaccard
    intersection = len(w1 & w2)
    union = len(w1 | w2)
    jaccard = (intersection / union) if union else 0.0
    if jaccard >= threshold:
        return True
    # Cosine
    cosine = _cosine_similarity_titles(t1, t2)
    if cosine >= threshold:
        return True
    # Bigram (للعناوين القصيرة — أكثر دقة)
    b1, b2 = _bigram_set(t1), _bigram_set(t2)
    if b1 and b2:
        b_inter = len(b1 & b2)
        b_union = len(b1 | b2)
        bigram_j = (b_inter / b_union) if b_union else 0.0
        if bigram_j >= threshold:
            return True
    return False

def _dedup_news_list(items):
    """
    إزالة الأخبار المكررة من قائمة (link, title, source, img).
    يحتفظ بأول نسخة ويحذف المشابهة.
    نستخدم مجموعة من bigrams لتحسين الأداء:
    - التحقق السريع بـ bigram overlap قبل الحساب الكامل
    - حد أقصى 200 خبر في القائمة لمنع البطء الشديد
    """
    seen_titles = []
    seen_bigrams = []
    result = []
    for item in items[:500]:  # حد أقصى 500 خبر
        title = item[1]
        bg_t = _bigram_set(title)
        duplicate = False
        for i, seen in enumerate(seen_titles):
            # فحص سريع بـ Jaccard قبل cosine كامل
            bg_s = seen_bigrams[i]
            if bg_t and bg_s:
                inter = len(bg_t & bg_s)
                union = len(bg_t | bg_s)
                if union > 0 and inter / union > 0.3:
                    if _is_similar_title(title, seen):
                        duplicate = True
                        break
            elif not bg_t and not bg_s and _is_similar_title(title, seen):
                duplicate = True
                break
        if not duplicate:
            seen_titles.append(title)
            seen_bigrams.append(bg_t)
            result.append(item)
    return result

# ======== كشف لغة العنوان (لمنع تسرب أخبار بلغة أخرى) ========
_LANG_SCRIPT = {
    "العربية 🇮🇶": _re.compile(r'[\u0600-\u06FF]'),
    "فارسی 🇮🇷":   _re.compile(r'[\u0600-\u06FF]'),
    "اردو 🇵🇰":    _re.compile(r'[\u0600-\u06FF\u0750-\u077F]'),
    "हिन्दी 🇮🇳":   _re.compile(r'[\u0900-\u097F]'),
    "Русский 🇷🇺":  _re.compile(r'[\u0400-\u04FF]'),
    "Українська 🇺🇦":_re.compile(r'[\u0400-\u04FF]'),
    "Deutsch 🇩🇪":  _re.compile(r'[a-zA-ZäöüÄÖÜß]'),
    "Türkçe 🇹🇷":  _re.compile(r'[a-zA-ZçğıöşüÇĞİÖŞÜ]'),
    "Português 🇧🇷":_re.compile(r'[a-zA-ZáàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ]'),
    "Italiano 🇮🇹": _re.compile(r'[a-zA-ZàèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ]'),
    "Español 🇲🇽":  _re.compile(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]'),
    "English 🇬🇧":  _re.compile(r'[a-zA-Z]'),
}
# لغات تستخدم حروف لاتينية متشابهة — لا نفلترها بالنص
_LATIN_LANGS = {"Deutsch 🇩🇪","Türkçe 🇹🇷","Português 🇧🇷","Italiano 🇮🇹","Español 🇲🇽","English 🇬🇧"}

def _title_in_lang(title, lang):
    """
    هل عنوان الخبر بالفعل بلغة المستخدم؟
    يُستخدم لمنع وصول أخبار إنجليزية لمستخدمي العربية/الفارسية/الهندية/الروسية.
    اللغات اللاتينية (إنجليزي/فرنسي/ألماني...) لا تُفلتر لأنها تتشارك الحروف.
    """
    if lang in _LATIN_LANGS:
        return True   # لا نستطيع التمييز بين اللاتينيات بدقة
    pat = _LANG_SCRIPT.get(lang)
    if not pat:
        return True   # لغة غير معروفة — نقبلها
    non_space = [c for c in title if not c.isspace()]
    if not non_space:
        return True
    matched = len(pat.findall(title))
    ratio = matched / len(non_space)
    return ratio >= 0.25   # 25% من الحروف يجب أن تكون بالنص الصحيح

# ======== تحليل مشاعر الخبر (Sentiment Analysis) ========
_SENTIMENT_POSITIVE = {
    'اتفاقية','توقيع','نجاح','إنجاز','تطور','انتعاش','ازدهار','سلام','تعاون',
    'مساعدة','دعم','تنمية','استثمار','بناء','إعادة إعمار','انفراج','حل','تقدم',
    'success','agreement','peace','growth','recovery','development','aid',
    'cooperation','progress','victory','positive','improvement','deal','boost',
    'انتصار','تحرير','عودة','أمل','فرصة','إنقاذ',
}
_SENTIMENT_NEGATIVE = {
    'انفجار','هجوم','قتل','اغتيال','حريق','كارثة','أزمة','انهيار','خسارة',
    'تدمير','دمار','ضحايا','قتلى','جرحى','احتجاج','غضب','مظاهرة','فشل',
    'سقوط','اعتقال','حظر','عقوبات','مجاعة','وفاة','مرض','وباء','تلوث',
    'explosion','attack','killed','crisis','collapse','disaster','violence',
    'war','conflict','death','disease','flood','earthquake','murder','protest',
    'تضخم','ارتفاع أسعار','ركود','بطالة',
}

def _is_tg_spam(raw_text: str, tg_link: str = "") -> bool:
    """يكتشف إذا كان المنشور إعلان/بروموشن/محتوى غير إخباري أو كلام تافه"""
    if not raw_text:
        return True
    stripped = raw_text.strip()
    text_lower = stripped.lower()

    # النص قصير جداً ولا يشبه خبراً (< 15 حرف)
    # ملاحظة: أخبار عاجلة كثيرة قصيرة مثل "عاجل: انفجار في بغداد" = ~30 حرف
    if len(stripped) < 15:
        return True

    # فحص الأنماط بالـ regex (إيموجي فقط، ترقيم فقط، إجابات أحادية)
    for pat in _TG_SPAM_REGEX:
        if pat.match(stripped):
            return True

    # فحص كلمات السبام
    for pat in _TG_SPAM_PATTERNS:
        if pat.lower() in text_lower:
            return True

    # رابط t.me/ لقناة مباشرة (بدون رقم رسالة) = إعادة توجيه وليس خبراً
    if tg_link:
        import re as _re
        if _re.match(r"https://t\.me/[A-Za-z0-9_]+$", tg_link):
            return True

    # نص مكوّن من إيموجي ومسافات بنسبة > 60%
    try:
        import unicodedata as _ud
        emoji_chars = sum(
            1 for ch in stripped
            if _ud.category(ch) in ('So', 'Sm') or ord(ch) > 0x1F300
        )
        if len(stripped) > 0 and emoji_chars / len(stripped) > 0.6:
            return True
    except Exception as _exc:
        _log_exc(_exc)

    # نص لا يحتوي على أي كلمة عربية أو إنجليزية حقيقية (> 3 أحرف)
    import re as _re2
    words = _re2.findall(r'[a-zA-Z\u0600-\u06FF]{4,}', stripped)
    if not words:
        return True

    # محتوى لا يشبه الخبر: أسئلة فقط بدون تفاصيل
    question_only = _re2.match(r'^[^؟?]*[؟?]\s*$', stripped)
    if question_only and len(stripped) < 80:
        return True

    # نص مكرر بشكل واضح (نفس الكلمة > 4 مرات)
    word_counts = {}
    for w in words:
        word_counts[w] = word_counts.get(w, 0) + 1
    if word_counts and max(word_counts.values()) > 4:
        return True

    return False



def _is_duplicate_title(title: str) -> bool:
    """True if a near-identical title was seen in the last 24 hours."""
    if not _FF.get("title_dedup", True):
        return False
    if not title:
        return False
    # Normalize: lowercase, keep only words ≥3 chars, first 12 words
    words = [w for w in title.lower().split() if len(w) >= 3][:12]
    if len(words) < 3:
        return False
    key = hashlib.md5(" ".join(words).encode("utf-8")).hexdigest()[:16]
    now = time.time()
    with _title_seen_lock:
        if key in _title_seen_cache:
            ts, _ = _title_seen_cache[key]
            if now - ts < _TITLE_DEDUP_TTL:
                return True
            # Expired — overwrite below
        _title_seen_cache[key] = (now, title[:120])
        # Prune old entries (keep max 20000)
        if len(_title_seen_cache) > 20000:
            cutoff = now - _TITLE_DEDUP_TTL
            stale = [k for k, (t, _) in list(_title_seen_cache.items()) if t < cutoff]
            for k in stale:
                _title_seen_cache.pop(k, None)
    return False

