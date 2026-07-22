# -*- coding: utf-8 -*-
"""
  handler_ai.py — /ask /verify /factcheck /why /profile /influence

  يُصدِّر معالجات أوامر الذكاء الاصطناعي.
  """

import sys as _sys_legacy
import os
# ─── استيراد كل المتغيرات العالمية من bot_legacy ───
from bot_legacy import *
import state as gl  # noqa: F401,F403

# FIX-7: Session مشتركة لكل HTTP calls — إعادة استخدام الـ connections وتوفير الوقت
_http_session = None
def _get_http_session():
    global _http_session
    if _http_session is None:
        import requests as _rq
        _http_session = _rq.Session()
        _http_session.headers.update({"User-Agent": "NaharBot/1.0"})
    return _http_session


# ═══════════════════════════════════════════════════════════════════════════
# FIX: دوال محرك InsightX الأساسية — كانت مُستخدَمة في هذا الملف نفسه من
# عشرات المواضع (فحص الشائعات، تحليل المشاعر، الخطورة، التحيز، السياق
# التاريخي...) لكنها لم تكن مُعرَّفة إطلاقاً في أي مكان بالمشروع، فكانت كل
# أزرار InsightX (لماذا يهم / ماذا بعد / تقرير ذكي / سياق / فحص شائعة /
# ذاكرة الأمة / خريطة العلاقات) تتوقف بخطأ NameError صامت.
# كل الدوال تستدعي _ai_generate (Gemini الحقيقي) وتتراجع لرسالة صادقة
# "الذكاء الاصطناعي غير متاح الآن" عند فشل الاستدعاء — بدون بيانات مُلفَّقة.
# ═══════════════════════════════════════════════════════════════════════════
import json as _ai_json
import re as _ai_re

_AI_UNAVAILABLE_MSG = {
    "العربية 🇮🇶": "⚠️ الذكاء الاصطناعي غير متاح حالياً. حاول مرة أخرى بعد قليل.",
    "English 🇬🇧": "⚠️ AI is currently unavailable. Please try again shortly.",
}


def _ai_friendly_error(exc, feature: str = "") -> str:
    return f"⚠️ حدث خطأ في ميزة {feature or 'الذكاء الاصطناعي'}. حاول مرة أخرى بعد قليل."


def _ai_json_call(prompt: str, fallback: dict) -> dict:
    """يستدعي _ai_generate ويحاول استخراج JSON من الرد؛ يرجع fallback عند الفشل."""
    raw = _ai_generate(prompt)
    if not raw:
        return fallback
    try:
        m = _ai_re.search(r"\{.*\}", raw, _ai_re.DOTALL)
        if m:
            return {**fallback, **_ai_json.loads(m.group(0))}
    except Exception:
        pass
    return fallback


def _ai_sentiment_analysis(title: str, summary: str = "") -> dict:
    fallback = {"emoji": "😐", "label": "غير محدد", "score": 50}
    prompt = (f'حلّل مشاعر هذا الخبر العراقي وأرجع JSON فقط بالشكل '
              f'{{"emoji":"😊/😐/😠","label":"إيجابي/سلبي/محايد","score":0-100}}:\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_json_call(prompt, fallback)
    _SENTIMENT_AI_CACHE[title[:120]] = result
    return result


def _content_quality_score(title: str, summary: str = "") -> int:
    """تقييم فوري بدون AI (سرعة) يعتمد على طول النص ووجود تفاصيل محددة."""
    text = f"{title} {summary}"
    score = 40
    if len(title) > 25:
        score += 15
    if summary:
        score += 15
    if any(ch.isdigit() for ch in text):
        score += 10
    promo_words = ["اشترك", "شارك", "تابعنا", "انضم", "subscribe", "follow"]
    if any(w in text.lower() for w in promo_words):
        score -= 25
    return max(5, min(100, score))


def _ai_extract_entities(title: str, summary: str = "") -> dict:
    fallback = {"people": [], "places": [], "organizations": []}
    prompt = (f'استخرج الكيانات من هذا الخبر وأرجع JSON فقط بالشكل '
              f'{{"people":[],"places":[],"organizations":[]}} (أسماء قصيرة، حد أقصى 5 لكل قائمة):\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_json_call(prompt, fallback)
    _ENTITY_CACHE[title[:120]] = result
    return result


def _ai_risk_level(title: str, summary: str = "") -> dict:
    fallback = {"level": "غير محدد", "color": "⚪", "reason": "تحليل الخطورة غير متاح حالياً"}
    prompt = (f'قيّم مستوى خطورة/حساسية هذا الخبر وأرجع JSON فقط بالشكل '
              f'{{"level":"low/medium/high","color":"🟢/🟡/🔴","reason":"سبب قصير بالعربية"}}:\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_json_call(prompt, fallback)
    _RISK_CACHE[title[:120]] = result
    return result


def _ai_impact_and_bias(title: str, summary: str = "") -> dict:
    fallback = {"impact_score": 50, "bias": "unknown", "bias_direction": "neutral"}
    prompt = (f'قيّم تأثير هذا الخبر وتحيّزه وأرجع JSON فقط بالشكل '
              f'{{"impact_score":0-100,"bias":"low/medium/high","bias_direction":"neutral/positive/negative"}}:\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_json_call(prompt, fallback)
    _IMPACT_CACHE[title[:120]] = result
    return result


def _ai_build_context(title: str, summary: str, lang: str) -> str:
    prompt = (f'اكتب سياقاً تاريخياً/خلفية موجزة (3-4 جمل بالعربية) تساعد القارئ العراقي '
              f'على فهم هذا الخبر بشكل أعمق:\nالعنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_generate(prompt) or _smart_fallback_context(title, lang)
    _CONTEXT_CACHE[title[:120]] = result
    return result


def _ai_why_it_matters(title: str, summary: str, lang: str) -> str:
    prompt = (f'اشرح بالعربية في 3-4 جمل لماذا هذا الخبر مهم للقارئ العراقي:\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_generate(prompt) or _smart_fallback_why(title)
    _WHY_MATTERS_CACHE[title[:120]] = result
    return result


def _ai_what_next(title: str, summary: str, lang: str) -> str:
    prompt = (f'بناءً على هذا الخبر، اكتب توقعاً واقعياً وحذراً بالعربية (3-4 جمل) لما قد يحدث لاحقاً:\n'
              f'العنوان: {title}\nالملخص: {summary[:400]}')
    result = _ai_generate(prompt) or _smart_fallback_next(title)
    _WHAT_NEXT_CACHE[title[:120]] = result
    return result


def _ai_verify_rumor(claim: str, sources_text: str) -> dict:
    fallback = {"verdict": "⚠️", "confidence": 0,
                "explanation": "تحقق من المصدر الأصلي — الذكاء الاصطناعي غير متاح حالياً.",
                "first_source": ""}
    prompt = (f'أنت مدقّق أخبار. الزعم: "{claim}"\nالمصادر ذات الصلة:\n{sources_text}\n\n'
              f'أرجع JSON فقط بالشكل {{"verdict":"✅/⚠️/❌","confidence":0-100,'
              f'"explanation":"شرح قصير بالعربية","first_source":"أول مصدر إن وُجد"}}')
    return _ai_json_call(prompt, fallback)


def _ai_fact_check(title: str) -> dict:
    fallback = {"verdict": "⚠️", "label": "يحتاج تحقق", "reason": ""}
    prompt = (f'قيّم مصداقية هذا العنوان الإخباري وأرجع JSON فقط بالشكل '
              f'{{"verdict":"✅/⚠️/❌","label":"موثوق/يحتاج تحقق/غير موثوق","reason":"سبب قصير بالعربية"}}:\n'
              f'{title}')
    return _ai_json_call(prompt, fallback)


def _ai_find_connections(titles: list) -> str:
    if not titles:
        return "لا توجد أخبار كافية للتحليل حالياً."
    joined = "\n".join(f"- {t}" for t in titles[:30])
    prompt = (f'حلّل هذه العناوين الإخبارية العراقية الأخيرة واكشف الروابط والأنماط المشتركة بينها '
              f'بالعربية (فقرة أو نقاط قصيرة):\n{joined}')
    result = _ai_generate(prompt)
    return result or "تعذّر تحليل الروابط بين الأخبار حالياً (الذكاء الاصطناعي غير متاح)."


def _ai_nation_memory(lang: str) -> str:
    today_fmt = _now_sa().strftime("%d %B")
    prompt = (f'اذكر بالعربية حدثاً أو حدثين تاريخيين مهمين حصلا في العراق في مثل هذا اليوم '
              f'({today_fmt}) عبر التاريخ، بأسلوب قصير وموثّق. إذا لم تكن متأكداً من تاريخ دقيق، '
              f'قل ذلك بصراحة بدل تأليف معلومة.')
    result = _ai_generate(prompt)
    return result or "تعذّر الوصول لذاكرة الأمة حالياً (الذكاء الاصطناعي غير متاح)."


def _ai_clean_news(text: str, body: str = "", link: str = "") -> str:
    """تنظيف/تلخيص نص الخبر قبل النشر؛ يرجع النص الأصلي عند فشل AI (بدون تلفيق)."""
    if not text:
        return text
    prompt = (f'أعد كتابة هذا العنوان الإخباري بالعربية بشكل نظيف واحترافي (بدون شعارات قنوات أو '
              f'دعوات اشتراك)، بنفس المعنى وبدون تغيير الحقائق:\n{text}\n{body[:300]}')
    result = _ai_generate(prompt)
    return (result or text).strip()[:300]


def _ai_generate_summary(text: str, title: str = "", lang: str = "العربية 🇮🇶") -> str:
    if not text:
        return text
    prompt = f'لخّص هذا الخبر العراقي بالعربية في 2-3 جمل فقط:\nالعنوان: {title}\nالنص: {text[:1200]}'
    result = _ai_generate(prompt)
    return (result or text).strip()


# تتبّع نقرات المستخدمين على أزرار InsightX (تحليلات داخلية بسيطة، بدون AI)
_user_click_log: dict = {}
_user_click_lock = threading.Lock()


def _track_user_click(uid, title: str, action: str = "") -> None:
    with _user_click_lock:
        _user_click_log.setdefault(str(uid), []).append(
            {"title": title[:120], "action": action, "ts": time.time()})
        if len(_user_click_log[str(uid)]) > 200:
            _user_click_log[str(uid)] = _user_click_log[str(uid)][-200:]


def _deepsearch_worker(uid: int, topic: str, progress_msg_id: int, chat_id: int):
      """
      ══════════════════════════════════════════════════════════════════
      DeepSearch v3.0 — Perplexity-level | مثل Perplexity AI بالكامل
      ──────────────────────────────────────────────────────────────────
      1. Intent Engine  — AI يحلل النية + المجال + العمق + 5-8 أسئلة فرعية
      2. Multi-Source   — Wikipedia + Wikidata + ArXiv + NewsAPI + RSS
      3. Source Scoring — Authority + Relevance + Freshness (0-10 each)
      4. Knowledge Fusion — دمج في كائن منظم + كشف التناقضات
      5. AI Reasoning   — Gemini يكتب بـ المعلومات المجمّعة فقط (NO hallucination)
      6. Fallback Mode  — تقرير منظم بدون AI إذا فشل
      ══════════════════════════════════════════════════════════════════
      """
      import hashlib as _dh
      import urllib.parse as _dup
      import xml.etree.ElementTree as _ET
      import json as _djson

      lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
      _worker_start = time.time()
      _MAX_RUNTIME  = 720  # 12 دقيقة

      # ── Cache layer (1 hour TTL per topic) ────────────────────────
      _cache_key = _dh.md5(topic.lower().strip().encode()).hexdigest()
      if not hasattr(_deepsearch_worker, '_cache'):
          _deepsearch_worker._cache = {}
      cached = _deepsearch_worker._cache.get(_cache_key)
      if cached and (time.time() - cached['ts'] < 3600):
          try:
              bot.edit_message_text(
                  cached['msg'], chat_id, progress_msg_id,
                  parse_mode="Markdown", disable_web_page_preview=True)
          except Exception:
              try:
                  bot.send_message(uid, cached['msg'], parse_mode="Markdown",
                                   disable_web_page_preview=True)
              except Exception as _exc:
                  _log_exc(_exc)
          return

      # ── Inner helpers ──────────────────────────────────────────────
      def upd(text):
          try:
              bot.edit_message_text(text, chat_id, progress_msg_id, parse_mode="Markdown")
          except Exception as _exc:
              _log_exc(_exc)

      def _timeout():
          if time.time() - _worker_start > _MAX_RUNTIME:
              raise TimeoutError("تجاوز البحث 12 دقيقة — تم إيقافه تلقائياً لحماية الخادم.")

      def _get(url, params=None, headers=None, tout=10):
          try:
              r = requests.get(url, params=params, headers=headers, timeout=tout)
              if r.status_code == 200:
                  return r
          except Exception as _exc:
              _log_exc(_exc)
          return None

      # ── Multi-AI Generator: Gemini → Groq → OpenRouter → Together ──
      def _ds_ai_generate(prompt: str, is_intent: bool = False):
          """
          يجرب عدة providers بالترتيب حتى ينجح أحدها.
          كل provider عنده quota مستقل → أكثر طلبات يومية للمستخدم.
          يُعيد (text: str | None, provider_name: str)
          """
          import json as _j
          import os as _os2

          # ─── 1. Gemini (primary — 4 models with auto-fallback) ──────
          if _AI_AVAILABLE:
              try:
                  _resp_ai = _ai_generate(prompt)
                  if _resp_ai: return (_resp_ai or ""), "Gemini"
              except Exception as _ge:
                  _ges = str(_ge)
                  if not ("429" in _ges or "quota" in _ges.lower() or
                          "RESOURCE_EXHAUSTED" in _ges or "جميع موديلات" in _ges):
                      return None, "gemini_error"

          # ─── 2. Groq (llama-3.3-70b / gemma2-9b) ────────────────────
          _groq_key = _DS_GROQ_KEY or _os2.environ.get("GROQ_API_KEY", "")
          if _groq_key:
              _groq_models = [
                  "llama-3.3-70b-versatile",
                  "gemma2-9b-it",
                  "llama-3.1-8b-instant",
              ]
              for _gm in _groq_models:
                  try:
                      _gr = requests.post(
                          "https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": f"Bearer {_groq_key}",
                                   "Content-Type": "application/json"},
                          json={"model": _gm,
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 2000 if not is_intent else 600,
                                "temperature": 0.3},
                          timeout=60
                      )
                      if _gr.status_code == 200:
                          txt = _gr.json()["choices"][0]["message"]["content"].strip()
                          if txt:
                              return txt, f"Groq ({_gm})"
                  except Exception:
                      continue

          # ─── 3. OpenRouter (free models) ────────────────────────────
          _or_key = _DS_OPENROUTER_KEY or _os2.environ.get("OPENROUTER_KEY", "")
          if _or_key:
              _or_models = [
                  "meta-llama/llama-3.1-8b-instruct:free",
                  "google/gemma-2-9b-it:free",
                  "mistralai/mistral-7b-instruct:free",
              ]
              for _orm in _or_models:
                  try:
                      _orr = requests.post(
                          "https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": f"Bearer {_or_key}",
                                   "Content-Type": "application/json",
                                   "HTTP-Referer": "https://iraqnow.bot"},
                          json={"model": _orm,
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 2000 if not is_intent else 600},
                          timeout=60
                      )
                      if _orr.status_code == 200:
                          txt = _orr.json()["choices"][0]["message"]["content"].strip()
                          if txt:
                              return txt, f"OpenRouter ({_orm.split('/')[1].split(':')[0]})"
                  except Exception:
                      continue

          # ─── 4. Together AI ──────────────────────────────────────────
          _tog_key = _DS_TOGETHER_KEY or _os2.environ.get("TOGETHER_API_KEY", "")
          if _tog_key:
              _tog_models = [
                  "meta-llama/Llama-3-8b-chat-hf",
                  "mistralai/Mistral-7B-Instruct-v0.2",
              ]
              for _tm in _tog_models:
                  try:
                      _tr = requests.post(
                          "https://api.together.xyz/v1/chat/completions",
                          headers={"Authorization": f"Bearer {_tog_key}",
                                   "Content-Type": "application/json"},
                          json={"model": _tm,
                                "messages": [{"role": "user", "content": prompt}],
                                "max_tokens": 2000 if not is_intent else 600,
                                "temperature": 0.3},
                          timeout=60
                      )
                      if _tr.status_code == 200:
                          txt = _tr.json()["choices"][0]["message"]["content"].strip()
                          if txt:
                              return txt, f"Together ({_tm.split('/')[1]})"
                  except Exception:
                      continue

          # ─── All providers exhausted ─────────────────────────────────
          return None, "none"

      try:
          # ════════════════════════════════════════════════════════════
          # 1. INTENT ENGINE — AI تحليل النية والأسئلة الفرعية
          # ════════════════════════════════════════════════════════════
          upd(f"🔬 *DeepSearch: {topic}*\n\n`[1/6]` {_ui('ds_s1', lang)}")

          intent        = "research"
          domain        = "general"
          depth         = "deep"
          sub_questions = []
          kw_en         = []
          kw_ar         = []

          stop = {"في","من","على","إلى","أن","هذا","هذه","ذلك","التي","الذي","مع","عن",
                  "لا","ما","أو","لم","قد","كان","the","a","an","of","in","on","is","are"}

          if _AI_AVAILABLE:
              try:
                  intent_prompt = (
                      "أنت محلل بحثي متخصص. حلل الموضوع وأعد JSON فقط بدون أي نص إضافي:\n"
                      f"الموضوع: \"{topic}\"\n\n"
                      "أعد هذا JSON بالضبط:\n"
                      "{\n"
                      '  \"intent\": \"explain|analyze|compare|research|summary\",\n'
                      '  \"domain\": \"science|tech|medical|politics|general|economics|sports\",\n'
                      '  \"depth\": \"basic|deep|expert\",\n'
                      '  \"sub_questions\": [\"سؤال فرعي 1\", \"سؤال فرعي 2\", \"سؤال فرعي 3\", \"سؤال فرعي 4\", \"سؤال فرعي 5\"],\n'
                      '  \"keywords_en\": [\"kw1\", \"kw2\", \"kw3\"],\n'
                      '  \"keywords_ar\": [\"ك1\", \"ك2\", \"ك3\"]\n'
                      "}"
                  )
                  txt, _intent_prov = _ds_ai_generate(intent_prompt, is_intent=True)
                  if txt:
                      js_s = txt.find("{"); js_e = txt.rfind("}") + 1
                      if js_s >= 0 and js_e > js_s:
                          parsed        = _djson.loads(txt[js_s:js_e])
                          intent        = parsed.get("intent",        "research")
                          domain        = parsed.get("domain",        "general")
                          depth         = parsed.get("depth",         "deep")
                          sub_questions = parsed.get("sub_questions", [])[:8]
                          kw_en         = parsed.get("keywords_en",   [])[:5]
                          kw_ar         = parsed.get("keywords_ar",   [])[:5]
              except Exception as _exc:
                  _log_exc(_exc)

          # Fallback keyword extraction
          if not kw_ar:
              kw_ar = [w for w in topic.split() if len(w) > 2 and w.lower() not in stop]
          if not kw_en:
              kw_en = kw_ar[:3]
          if not sub_questions:
              sub_questions = [
                  f"ما هو {topic}؟",
                  f"ما أسباب {topic}؟",
                  f"ما تداعيات {topic}؟",
                  f"ما الموقف الدولي من {topic}؟",
                  f"ما مستقبل {topic}؟",
              ]

          intent_label = {"explain":"شرح وتعريف","analyze":"تحليل","compare":"مقارنة",
                          "research":"بحث","summary":"تلخيص"}.get(intent, intent)
          domain_label = {"science":"علوم","tech":"تقنية","medical":"طب","politics":"سياسة",
                          "general":"عام","economics":"اقتصاد","sports":"رياضة"}.get(domain, domain)
          depth_label  = {"basic":"أساسي","deep":"عميق","expert":"خبير"}.get(depth, depth)

          upd(
              f"🔬 *DeepSearch: {topic}*\n\n"
              f"✅ `[1/6]` 🧠 *{intent}* · *{domain}* · *{depth}*\n"
              f"  ↳ {len(sub_questions)} sub-q | {' · '.join((kw_ar+kw_en)[:5])}\n\n"
              f"`[2/6]` {_ui('ds_s2', lang).format(n=len(sub_questions))}"
          )
          _timeout()

          # ════════════════════════════════════════════════════════════
          # 2. MULTI-SOURCE KNOWLEDGE RETRIEVAL
          # ════════════════════════════════════════════════════════════
          all_sources = []

          # 2a. Wikipedia (EN + AR)
          def _wiki(query, lang_code="en", limit=5):
              res = []
              r = _get("https://" + lang_code + ".wikipedia.org/w/api.php",
                       params={"action":"query","list":"search","srsearch":query,
                               "srlimit":limit,"format":"json","utf8":1})
              if r:
                  for item in r.json().get("query",{}).get("search",[]):
                      t = item.get("title","")
                      s = _re.sub('<[^>]+>', '', item.get("snippet",""))[:400]
                      l = "https://" + lang_code + ".wikipedia.org/wiki/" + _dup.quote(t)
                      if t and s:
                          res.append({"title":t,"summary":s,"link":l,
                                      "source":"Wikipedia ("+lang_code.upper()+")","authority":9,"freshness":5,"type":"encyclopedia"})
              return res

          # 2b. Wikidata entity search
          def _wikidata(query):
              res = []
              r = _get("https://www.wikidata.org/w/api.php",
                       params={"action":"wbsearchentities","search":query,
                               "language":"ar","limit":3,"format":"json"})
              if r:
                  for item in r.json().get("search",[]):
                      desc  = item.get("description","")
                      label = item.get("label","")
                      if desc and len(desc) > 10:
                          res.append({"title":label,"summary":label+": "+desc,
                                      "link":"https://www.wikidata.org/wiki/"+item.get("id",""),
                                      "source":"Wikidata","authority":8,"freshness":6,"type":"knowledge_graph"})
              return res

          # 2c. ArXiv (science/tech/medical only)
          def _arxiv(query):
              res = []
              if domain not in ("science","tech","medical"):
                  return res
              r = _get("http://export.arxiv.org/api/query",
                       params={"search_query":"all:"+query,"max_results":5,"sortBy":"relevance"}, tout=15)
              if r:
                  try:
                      root = _ET.fromstring(r.text if hasattr(r, 'text') else r)
                      ns   = {"a":"http://www.w3.org/2005/Atom"}
                      for e in root.findall("a:entry", ns)[:5]:
                          t = (e.findtext("a:title","",ns) or "").strip()
                          s = (e.findtext("a:summary","",ns) or "").strip()[:400]
                          l = (e.findtext("a:id","",ns) or "").strip()
                          if t:
                              res.append({"title":t,"summary":s,"link":l,
                                          "source":"ArXiv","authority":9,"freshness":8,"type":"academic"})
                  except Exception as _exc:
                      _log_exc(_exc)
              return res

          # 2d. NewsAPI
          def _newsapi(query, lang_code="ar"):
              res = []
              if not NEWS_KEY:
                  return res
              r = _get("https://newsapi.org/v2/everything",
                       params={"q":query,"pageSize":10,"sortBy":"publishedAt","language":lang_code},
                       headers={"X-Api-Key": NEWS_KEY}, tout=10)
              if r:
                  for art in r.json().get("articles",[]):
                      url_ = art.get("url","")
                      t    = art.get("title","") or ""
                      s    = (art.get("description","") or "")[:400]
                      src  = art.get("source",{}).get("name","NewsAPI")
                      if t:
                          res.append({"title":t,"summary":s,"link":url_,
                                      "source":src,"authority":7,"freshness":9,"type":"news"})
              return res

          # 2e. RSS feeds (existing bot infrastructure)
          def _rss(query):
              res = []
              qwords = [w for w in query.split() if len(w) > 2]
              tried  = 0
              for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", [])))[:25]:
                  if tried >= 15:
                      break
                  tried += 1
                  try:
                      feed = _parse_feed(feed_url)
                      if not feed:
                          continue
                      for entry in feed.entries[:10]:
                          t_ = getattr(entry,'title','') or ''
                          s_ = getattr(entry,'summary','') or ''
                          l_ = getattr(entry,'link','') or ''
                          text_ = (t_ + " " + s_).lower()
                          matched = sum(1 for w in qwords if w.lower() in text_) >= max(1, len(qwords)*0.4)
                          if matched:
                              res.append({"title":t_,"summary":s_[:400],"link":l_,
                                          "source":feed_url,"authority":7,"freshness":8,"type":"news"})
                  except Exception as _exc:
                      _log_exc(_exc)
              return res

          # ── Run all retrievals for main topic ──────────────────────
          all_sources += _wiki(topic, "en")
          all_sources += _wiki(topic, "ar")
          _timeout()
          all_sources += _wikidata(topic)
          all_sources += _arxiv(" ".join(kw_en[:3]))
          _timeout()
          all_sources += _newsapi(topic, "ar")
          all_sources += _newsapi(" ".join(kw_en[:3]), "en")
          all_sources += _rss(topic)
          _timeout()

          # ── Also retrieve for top sub-questions ───────────────────
          for sq in sub_questions[:3]:
              _timeout()
              all_sources += _wiki(sq, "en", limit=3)
              all_sources += _newsapi(sq, "ar")[:3]

          upd(
              f"🔬 *DeepSearch: {topic}*\n\n"
              f"✅ `[1/6]` 🧠 {intent} · {domain}\n"
              f"✅ `[2/6]` 🌐 {len(all_sources)} sources\n"
              f"  ↳ Wikipedia + Wikidata + ArXiv + News + RSS\n\n"
              f"`[3/6]` {_ui('ds_s3', lang)}"
          )
          _timeout()

          # ════════════════════════════════════════════════════════════
          # 3. SOURCE PROCESSING ENGINE (score + deduplicate + rank)
          # ════════════════════════════════════════════════════════════
          def _score(src):
              text = (src.get("title","") + " " + src.get("summary","")).lower()
              all_kw = kw_ar + kw_en
              relevance  = min(10, int(sum(1 for k in all_kw if k.lower() in text) / max(1,len(all_kw)) * 10) + 2)
              freshness  = src.get("freshness", 5)
              authority  = src.get("authority", 5)
              total      = round(authority * 0.40 + relevance * 0.40 + freshness * 0.20, 2)
              return {**src, "relevance": relevance, "score": total}

          scored = [_score(s) for s in all_sources if s.get("title") and (s.get("summary") or s.get("link"))]

          # Deduplicate by title prefix
          seen_t = set()
          deduped = []
          for s in scored:
              key = s["title"][:40].lower().strip()
              if key not in seen_t and s["score"] >= 2.5:
                  seen_t.add(key)
                  deduped.append(s)

          deduped.sort(key=lambda x: x["score"], reverse=True)
          top_sources = deduped[:30]
          trusted     = [s for s in top_sources if s["score"] >= 6.0]
          acceptable  = [s for s in top_sources if 4.0 <= s["score"] < 6.0]
          quality     = trusted + acceptable

          upd(
              f"🔬 *DeepSearch: {topic}*\n\n"
              f"✅ `[1/6]` 🧠 {intent} · {domain}\n"
              f"✅ `[2/6]` 🌐 {len(all_sources)} sources\n"
              f"✅ `[3/6]` 📊 {len(trusted)} trusted | {len(acceptable)} ok\n\n"
              f"`[4/6]` {_ui('ds_s4_fuse', lang)}"
          )
          _timeout()

          # ════════════════════════════════════════════════════════════
          # 4. KNOWLEDGE FUSION ENGINE + CONTRADICTION DETECTION
          # ════════════════════════════════════════════════════════════
          fused = {
              "topic":          topic,
              "intent":         intent,
              "domain":         domain,
              "depth":          depth,
              "sub_questions":  sub_questions,
              "definitions":    [],
              "facts":          [],
              "key_points":     [],
              "perspectives":   [],
              "contradictions": [],
              "sources_used":   [],
          }

          for s in quality[:20]:
              t = s.get("title","").strip()
              sm = s.get("summary","").strip()
              if not t:
                  continue
              chunk = f"• [{s.get('source','')}] *{t}*: {sm[:220]}" if sm else f"• [{s.get('source','')}] *{t}*"
              typ = s.get("type","")
              if typ in ("encyclopedia","knowledge_graph"):
                  fused["definitions"].append(chunk)
              elif typ == "academic":
                  fused["facts"].append(chunk)
              else:
                  fused["key_points"].append(chunk)
              fused["sources_used"].append({"title":t,"link":s.get("link",""),"score":s.get("score",0),"src":s.get("source","")})

          # Contradiction Detection
          confirms = [s["title"][:80] for s in quality
                      if any(w in (s["title"]+" "+s.get("summary","")).lower()
                             for w in ("أكد","يؤكد","أثبت","confirmed","approved","affirmed","صحيح","نعم"))]
          denials  = [s["title"][:80] for s in quality
                      if any(w in (s["title"]+" "+s.get("summary","")).lower()
                             for w in ("نفى","ينفي","رفض","denied","refuted","false","خطأ","مزيف","incorrect"))]
          if confirms and denials:
              for c, d in zip(confirms[:3], denials[:3]):
                  fused["contradictions"].append(
                      f"⚠️ تعارض محتمل:\n  ✅ '{c[:70]}'\n  ❌ '{d[:70]}'")

          upd(
              f"🔬 *DeepSearch: {topic}*\n\n"
              f"✅ `[1/6]` 🧠 {intent} · {domain}\n"
              f"✅ `[2/6]` 🌐 {len(all_sources)} sources\n"
              f"✅ `[3/6]` 📊 {len(quality)} quality\n"
              f"✅ `[4/6]` 🔗 {len(fused['definitions'])+len(fused['facts'])+len(fused['key_points'])} points"
              f" | {len(fused['contradictions'])} {'⚠️' if fused['contradictions'] else '✓'}\n\n"
              f"`[5/6]` {_ui('ds_s4', lang)}"
          )
          _timeout()

          # ════════════════════════════════════════════════════════════
          # 5. AI REASONING ENGINE (Gemini — NO hallucination)
          # ════════════════════════════════════════════════════════════
          write_lang = ("العربية"    if "عرب"  in lang else
                        "English"    if "Engl" in lang else
                        "فارسی"      if "فارس" in lang else
                        "Русский"    if "Рус"  in lang else
                        "हिन्दी"     if "हिन्" in lang else
                        "Português"  if "Port" in lang else
                        "Türkçe"     if "Türk" in lang else
                        "اردو"       if "اردو" in lang else
                        "Deutsch"    if "Deut" in lang else
                        "Українська" if "Укра" in lang else
                        "Italiano"   if "Ital" in lang else
                        "Español"    if "Espa" in lang else
                        "Français"   if "Fran" in lang else "English")

          ai_report = None
          ai_mode   = "ai"

          _any_ai = _AI_AVAILABLE or bool(_DS_GROQ_KEY) or bool(_DS_OPENROUTER_KEY) or bool(_DS_TOGETHER_KEY)
          if _any_ai and quality:
              # Build structured knowledge text
              parts = []
              if fused["definitions"]:
                  parts.append("=== معلومات موسوعية ===\n" + "\n".join(fused["definitions"][:6]))
              if fused["facts"]:
                  parts.append("=== حقائق أكاديمية ===\n" + "\n".join(fused["facts"][:5]))
              if fused["key_points"]:
                  parts.append("=== نقاط إخبارية ===\n" + "\n".join(fused["key_points"][:10]))
              if fused["contradictions"]:
                  parts.append("=== تناقضات بين المصادر ===\n" + "\n".join(fused["contradictions"]))
              knowledge_txt = "\n\n".join(parts)

              sub_q_txt = "\n".join(f"{i+1}. {q}" for i,q in enumerate(fused["sub_questions"][:6]))

              contradiction_section = (
                  "\n\n**6. التناقضات بين المصادر**\n"
                  "[اشرح التعارضات التي رصدتها في المصادر المقدمة وأيها أكثر موثوقية]"
                  if fused["contradictions"] else ""
              )
              last_section_num = 7 if fused["contradictions"] else 6

              ai_prompt = (
                  f"أنت محلل بحثي خبير.\n\n"
                  f"⚠️ قواعد صارمة جداً:\n"
                  f"- استخدم فقط المعلومات المقدمة أدناه\n"
                  f"- لا تستخدم معلومات خارج المصادر المقدمة\n"
                  f"- إذا كانت المعلومات ناقصة لأي قسم، اكتب: _(لا تتوفر بيانات كافية لهذا القسم)_\n"
                  f"- اكتب بلغة: {write_lang}\n"
                  f"- الحجم: تقرير مفصّل (600-900 كلمة)\n\n"
                  f"=== الموضوع ===\n{topic}\n\n"
                  f"=== النية والمجال ===\n{intent_label} في مجال {domain_label} (مستوى {depth_label})\n\n"
                  f"=== الأسئلة الفرعية المطلوب تغطيتها ===\n{sub_q_txt}\n\n"
                  f"=== المعلومات المجمّعة من المصادر ===\n{knowledge_txt}\n\n"
                  f"=== التقرير البحثي المطلوب ===\n"
                  f"**1. الخلفية والتعريف**\n[ما هذا الموضوع؟ ما السياق التاريخي؟]\n\n"
                  f"**2. التحليل العميق**\n[ما أهم الجوانب والأبعاد؟ تحليل شامل بناءً على المصادر]\n\n"
                  f"**3. الأسباب والعوامل**\n[لماذا يحدث هذا؟ ما الأسباب الجذرية؟]\n\n"
                  f"**4. التداعيات والآثار**\n[ما النتائج والتأثيرات قصيرة وطويلة المدى؟]\n\n"
                  f"**5. السيناريوهات المستقبلية**\n"
                  f"• السيناريو الأول (متفائل): ...\n"
                  f"• السيناريو الثاني (واقعي): ...\n"
                  f"• السيناريو الثالث (متشائم): ..."
                  f"{contradiction_section}\n\n"
                  f"**{last_section_num}. الخلاصة والاستنتاجات**\n[أبرز ما تعلمناه وأهم التوصيات]"
              )

              try:
                  ai_report, _report_prov = _ds_ai_generate(ai_prompt, is_intent=False)
                  if not ai_report:
                      ai_mode = "fallback_quota"
                  else:
                      ai_mode = f"ai:{_report_prov}"
              except Exception as _ae:
                  ai_report = None
                  ai_mode   = "fallback_error"
          elif not quality:
              ai_mode = "fallback_nosources"
          else:
              ai_mode = "fallback_noai"

          # ════════════════════════════════════════════════════════════
          # 5b. FALLBACK MODE — تقرير منظم بدون AI
          # ════════════════════════════════════════════════════════════
          if not ai_report:
              fallback_parts = [f"📋 *تقرير بحثي احتياطي — {topic}*\n"]
              if fused["definitions"]:
                  fallback_parts.append("*📖 المعلومات الأساسية:*\n" + "\n".join(fused["definitions"][:5]))
              if fused["facts"]:
                  fallback_parts.append("*🔬 الحقائق والبيانات:*\n" + "\n".join(fused["facts"][:5]))
              if fused["key_points"]:
                  fallback_parts.append("*📰 النقاط الرئيسية:*\n" + "\n".join(fused["key_points"][:10]))
              if fused["contradictions"]:
                  fallback_parts.append("*⚠️ تناقضات رُصدت:*\n" + "\n".join(fused["contradictions"]))
              if ai_mode == "fallback_quota":
                  fallback_parts.append("_⚠️ ملاحظة: نفد رصيد AI — يُعرض تقرير المصادر المباشر_")
              elif ai_mode == "fallback_nosources":
                  fallback_parts.append("_⚠️ لم يُعثر على مصادر كافية. جرّب إعادة صياغة الموضوع._")
              elif ai_mode == "fallback_error":
                  fallback_parts.append("_⚠️ تعذّر الاتصال بـ AI — يُعرض تقرير المصادر_")
              ai_report = "\n\n".join(fallback_parts)

          upd(
              f"🔬 *DeepSearch: {topic}*\n\n"
              f"✅ `[1/6]` 🧠 {intent} · {domain}\n"
              f"✅ `[2/6]` 🌐 {len(all_sources)} sources\n"
              f"✅ `[3/6]` 📊 {len(quality)} quality\n"
              f"✅ `[4/6]` 🔗 knowledge fusion\n"
              f"✅ `[5/6]` {'🤖 ' + ai_mode[3:] if ai_mode.startswith('ai:') else '⚠️ fallback'}\n\n"
              f"`[6/6]` {_ui('ds_s6', lang)}"
          )
          time.sleep(0.5)
          _timeout()

          # ════════════════════════════════════════════════════════════
          # 6. OUTPUT FORMATTER & DELIVERY
          # ════════════════════════════════════════════════════════════
          # Sources block
          sources_lines = []
          shown_links   = set()
          for s in fused["sources_used"][:10]:
              lnk = s.get("link","")
              t   = s.get("title","")[:65]
              sc  = s.get("src","")
              if lnk and lnk not in shown_links:
                  shown_links.add(lnk)
                  sources_lines.append(f"• [{t}]({lnk}) _({sc})_")

          sources_block = ""
          if sources_lines:
              sources_block = "\n\n---\n📚 *المصادر:*\n" + "\n".join(sources_lines)

          # Contradiction alert
          contradiction_alert = ""
          if fused["contradictions"]:
              contradiction_alert = "\n\n⚠️ *تنبيه: رُصدت تناقضات بين المصادر — راجع القسم المخصص في التقرير*"

          # Footer
          elapsed = int(time.time() - _worker_start)
          if ai_mode.startswith("ai:"):
              _prov_name = ai_mode[3:]  # e.g. "Gemini" / "Groq (llama-3.3-70b-versatile)"
              mode_lbl = f"🤖 {_prov_name}"
          else:
              mode_lbl = {
                  "fallback_quota":    "📋 احتياطي — نفد جميع الـ AI",
                  "fallback_noai":     "📋 احتياطي — لا AI متاح",
                  "fallback_error":    "📋 احتياطي — خطأ AI",
                  "fallback_nosources":"📋 لا مصادر كافية",
              }.get(ai_mode, "📋 احتياطي")
          footer = (
              f"\n\n---\n"
              f"⏱ {elapsed}ث | 📡 {len(quality)} مصدر | {mode_lbl}"
          )

          final_msg = (
              f"🔬 *DeepSearch — {topic}*\n\n"
              f"{ai_report}"
              f"{contradiction_alert}"
              f"{sources_block}"
              f"{footer}"
          )

          # Cache result
          _deepsearch_worker._cache[_cache_key] = {"ts": time.time(), "msg": final_msg}
          if len(_deepsearch_worker._cache) > 60:
              oldest = sorted(_deepsearch_worker._cache.items(), key=lambda x: x[1]["ts"])
              for k, _ in oldest[:15]:
                  del _deepsearch_worker._cache[k]

          # Send (split if > 3800 chars)
          MAX_TG = 3800
          if len(final_msg) <= MAX_TG:
              try:
                  bot.edit_message_text(final_msg, chat_id, progress_msg_id,
                                        parse_mode="Markdown", disable_web_page_preview=True)
              except Exception:
                  try:
                      bot.send_message(uid, final_msg, parse_mode="Markdown",
                                       disable_web_page_preview=True)
                  except Exception:
                      bot.send_message(uid, final_msg[:MAX_TG])
          else:
              # First chunk via edit
              intro = final_msg[:MAX_TG] + "\n\n_(يتبع...)_"
              try:
                  bot.edit_message_text(intro, chat_id, progress_msg_id,
                                        parse_mode="Markdown", disable_web_page_preview=True)
              except Exception as _exc:
                  _log_exc(_exc)
              remaining = final_msg[MAX_TG:]
              while remaining:
                  chunk     = remaining[:MAX_TG]
                  remaining = remaining[MAX_TG:]
                  try:
                      bot.send_message(uid, chunk, parse_mode="Markdown",
                                       disable_web_page_preview=True)
                  except Exception:
                      try:
                          bot.send_message(uid, chunk)
                      except Exception as _exc:
                          _log_exc(_exc)
                  time.sleep(0.4)

      except TimeoutError as e:
          try:
              bot.edit_message_text(
                  f"🔬 *DeepSearch — توقف بسبب الوقت*\n\n⏰ {str(e)}\n\n"
                  f"💡 جرّب موضوعاً أكثر تحديداً أو استخدم كلمات مفتاحية أقل.",
                  chat_id, progress_msg_id, parse_mode="Markdown"
              )
          except Exception as _exc:
              _log_exc(_exc)
      except Exception as e:
          try:
              err_msg = _ai_friendly_error(e, "deepsearch")
              bot.edit_message_text(
                  f"🔬 *DeepSearch — انتهى بخطأ*\n\n{err_msg}\n\n"
                  f"💡 جرّب مرة أخرى أو بموضوع مختلف.",
                  chat_id, progress_msg_id, parse_mode="Markdown"
              )
          except Exception as _exc:
              _log_exc(_exc)
      finally:
          _deepsearch_active.pop(str(uid), None)

  
def handle_submit_news_cmd(message):
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get("lang", "العربية 🇮🇶")
    text = message.text.replace('/submit', '').strip()
    if not text:
        bot.send_message(message.chat.id, _ui("cmd_submit_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id, _ui("cmd_submit_loading", lang))
    result = _ai_verify_user_news(text)
    score = result.get("score", 0)
    valid = result.get("valid", False)
    reason = result.get("reason", "")
    cleaned = result.get("cleaned", text)
    if valid and score >= 60:
        # نشر للمشتركين
        user_name = message.from_user.first_name or "مستخدم"
        broadcast_text = (
            f"📢 *خبر من الميدان*\n\n"
            f"{cleaned}\n\n"
            f"📍 بلّغ: مستخدم من المجتمع\n"
            f"✅ تحقق الذكاء الاصطناعي: {score}%"
        )
        sent_count = 0
        for uid_s, info in list(users.items()):
            try:
                if info.get("notifications", True):
                    bot.send_message(int(uid_s), broadcast_text, parse_mode="Markdown")
                    sent_count += 1
            except Exception as _exc:
                _log_exc(_exc)
        reply = _ui("cmd_submit_accepted", lang).format(score=score, count=sent_count)
        _verified_user_news_log.append({"uid": uid, "text": cleaned, "score": score, "time": time.time()})
    else:
        reply = _ui("cmd_submit_rejected", lang).format(score=score, reason=reason)
    try:
        bot.edit_message_text(reply, message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply, parse_mode="Markdown")

@bot.message_handler(commands=['sources'])
def handle_sources_ranking_cmd(message):
    uid = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    rankings = _get_source_rankings()
    if not rankings:
        bot.send_message(message.chat.id, _ui("cmd_sources_nodata", lang), parse_mode="Markdown")
        return
    text = _ui("cmd_sources_hdr", lang)
    medals = ["🥇", "🥈", "🥉"] + ["🔹"] * 20
    unit = _ui("cmd_sources_unit", lang)
    mn   = _ui("cmd_sources_min",  lang)
    for i, src in enumerate(rankings[:15]):
        medal = medals[i]
        text += (
            f"{medal} *{src['source']}*\n"
            f"   📰 {src['count_24h']} {unit} {src['avg_gap_min']} {mn}\n\n"
        )
    bot.send_message(message.chat.id, text[:4096], parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("verify_news_"))
def cb_verify_news(call):
    # إصلاح #3: لا نستبدل _ بمسافة — نأخذ الـkey كما هو ونجلب العنوان الأصلي من الكاش
    key = call.data[len("verify_news_"):]
    title = _factcheck_key_cache.get(key) or _news_summary_cache.get(key, {}).get("title", "") or key.replace("_", " ")
    title = title[:100]
    bot.answer_callback_query(call.id, "🔍 جاري التحقق...")
    msg = bot.send_message(call.message.chat.id, "🔍 جاري التحقق من الخبر...")
    result = _ai_verify_news(title)
    reply = _format_verify_result(result, title)
    try:
        bot.edit_message_text(reply, call.message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)


# ─── /deepsearch command handler ────────────────────────────────
@bot.message_handler(commands=['deepsearch'])
def handle_deepsearch_cmd(message):
    uid = message.from_user.id
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')

    # فحص 1: Feature flag
    if not _FF.get("search", True):
        bot.send_message(message.chat.id, _ui("feature_disabled", lang))
        return

    # فحص 2: المستخدم مسجّل
    if str(uid) not in users:
        welcome_user(uid)
        return

    topic = message.text.replace('/deepsearch', '').strip()
    if not topic:
        prompts = {
            "العربية 🇮🇶": "🔍 *DeepSearch — بحث عميق*\n\nأرسل الموضوع بعد الأمر:\n`/deepsearch الأزمة السياسية في العراق`\n\n⏱ البحث يستغرق 5-15 دقيقة ويفحص عشرات المصادر\n\n📊 المجانيون: 2 بحث/يوم | ⭐ المميزون: 8 بحث/يوم",
            "English 🇬🇧": "🔍 *DeepSearch*\n\nSend topic after command:\n`/deepsearch Iraq political crisis`\n\n⏱ Search takes 5-15 minutes scanning dozens of sources\n\n📊 Free: 2 searches/day | ⭐ Premium: 8 searches/day",
        }
        bot.send_message(message.chat.id,
            prompts.get(lang, prompts["English 🇬🇧"]), parse_mode="Markdown")
        return

    # فحص 3: بحث جارٍ بالفعل
    if _deepsearch_active.get(str(uid)):
        wait_msgs = {
            "العربية 🇮🇶": "⏳ بحث سابق لا يزال جارياً، انتظر حتى يكتمل",
            "English 🇬🇧":  "⏳ A previous search is still running, please wait.",
        }
        bot.send_message(message.chat.id, wait_msgs.get(lang, wait_msgs["English 🇬🇧"]))
        return

    # فحص 4: كولداون (5 دقائق بين كل بحثين)
    if _is_rate_limited(uid, "deepsearch") and not is_admin(uid):
        bot.send_message(message.chat.id, _ui("rate_limited", lang))
        return

    # فحص 5: الحصة اليومية
    allowed, used, limit = _check_daily_ai_limit(uid, "deepsearch")
    if not allowed:
        prem = is_premium(uid)
        quota_msg = {
            "العربية 🇮🇶": f"📊 استنفدت حصتك اليومية من البحث العميق ({used}/{limit}).\n{'يتجدد الرصيد غداً.' if prem else '⭐ ترقية للمميز تُعطيك 8 بحث/يوم.'}",
            "English 🇬🇧": f"📊 Daily DeepSearch quota reached ({used}/{limit}).\n{'Resets tomorrow.' if prem else '⭐ Upgrade to Premium for 8 searches/day.'}",
        }
        bot.send_message(message.chat.id, quota_msg.get(lang, quota_msg["English 🇬🇧"]), parse_mode="Markdown")
        return

    _deepsearch_active[str(uid)] = True
    start_msgs = {
        "العربية 🇮🇶": (
            f"🔍 *DeepSearch بدأ*\n\n"
            f"📌 الموضوع: *{topic}*\n\n"
            f"⏳ جاري فحص:\n"
            f"• مصادر RSS العربية والدولية\n"
            f"• مواقع إخبارية بالسكرابنق\n"
            f"• المصادر الرسمية والحكومية\n"
            f"• قاعدة بيانات NewsAPI العالمية\n"
            f"• تحليل عميق بالذكاء الاصطناعي\n\n"
            f"_قد يستغرق 5-15 دقيقة..._"
        ),
        "English 🇬🇧": (
            f"🔍 *DeepSearch Started*\n\n"
            f"📌 Topic: *{topic}*\n\n"
            f"⏳ Scanning:\n"
            f"• Arabic & international RSS feeds\n"
            f"• News sites via scraping\n"
            f"• Official & government sources\n"
            f"• NewsAPI global database\n"
            f"• Deep AI analysis\n\n"
            f"_May take 5-15 minutes..._"
        ),
    }
    progress_msg = bot.send_message(
        message.chat.id,
        start_msgs.get(lang, start_msgs["English 🇬🇧"]),
        parse_mode="Markdown"
    )
    t = threading.Thread(
        target=_deepsearch_worker,
        args=(uid, topic, progress_msg.message_id, message.chat.id),
        daemon=True,
        name=f"DeepSearch-{uid}"
    )
    t.start()


@bot.callback_query_handler(func=lambda c: c.data.startswith("analyze_news_"))
def cb_analyze_news(call):
    # إصلاح #4: جلب العنوان الأصلي من الكاش بدلاً من استبدال _ بمسافة
    key   = call.data[len("analyze_news_"):]
    title = (_news_summary_cache.get(key, {}).get("title", "")
             or _factcheck_key_cache.get(key, "")
             or key.replace("_", " "))[:100]
    bot.answer_callback_query(call.id, "🧠 جاري التحليل...")
    msg = bot.send_message(call.message.chat.id, "🧠 جاري التحليل السياسي...")
    lang = users.get(str(call.from_user.id), {}).get('lang', 'العربية 🇮🇶')
    result = _ai_political_analysis(title, lang=lang)
    reply = f"🧠 *تحليل سياسي*\n\n📰 _{title[:60]}_\n\n{result}"
    try:
        bot.edit_message_text(reply[:4096], call.message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception as _exc:
        _log_exc(_exc)



# ═══════════════════════════════════════════════════════════════════
# القائمة الرئيسية الجديدة — أبسط وأجمل
# ═══════════════════════════════════════════════════════════════════

_MENU_LABELS = {
    "العربية 🇮🇶": {
        "news":"📰 الأخبار","deep":"🔍 DeepSearch","ai":"🧠 تحليل AI",
        "sports":"🏅 الرياضة","weather":"🌤 الطقس","markets":"💰 الأسواق",
        "settings":"⚙️ الإعدادات","help":"❓ المساعدة",
        "ai_verify":"✅ تحقق من خبر","ai_analyze":"🧠 تحليل سياسي",
        "ai_compare":"🌐 مقارنة مصادر","ai_timeline":"📅 خط زمني",
        "ai_predict":"🔮 توقعات","ai_influence":"🗺 خريطة نفوذ",
        "ai_profile":"🕵️ محقق شخصية","ai_parliament":"🏛 البرلمان",
        "ai_econ":"📉 مؤشرات اقتصادية","ai_ask":"💬 اسألني",
        "back":"🔙 رجوع","title":"🏠 القائمة الرئيسية",
        "live":"🔴 بث مباشر","submit":"📢 شارك خبراً",
    },
    "English 🇬🇧": {
        "news":"📰 News","deep":"🔍 DeepSearch","ai":"🧠 AI Analysis",
        "sports":"🏅 Sports","weather":"🌤 Weather","markets":"💰 Markets",
        "settings":"⚙️ Settings","help":"❓ Help",
        "ai_verify":"✅ Verify News","ai_analyze":"🧠 Political Analysis",
        "ai_compare":"🌐 Compare Sources","ai_timeline":"📅 Timeline",
        "ai_predict":"🔮 Predictions","ai_influence":"🗺 Influence Map",
        "ai_profile":"🕵️ Investigate","ai_parliament":"🏛 Parliament",
        "ai_econ":"📉 Economy","ai_ask":"💬 Ask Me",
        "back":"🔙 Back","title":"🏠 Main Menu",
        "live":"🔴 Live Event","submit":"📢 Submit News",
    },
    "Русский 🇷🇺": {
        "news":"📰 Новости","deep":"🔍 DeepSearch","ai":"🧠 ИИ Анализ",
        "sports":"🏅 Спорт","weather":"🌤 Погода","markets":"💰 Рынки",
        "settings":"⚙️ Настройки","help":"❓ Помощь",
        "ai_verify":"✅ Проверка новости","ai_analyze":"🧠 Политический анализ",
        "ai_compare":"🌐 Сравнение источников","ai_timeline":"📅 Хронология",
        "ai_predict":"🔮 Прогноз","ai_influence":"🗺 Карта влияния",
        "ai_profile":"🕵️ Профиль личности","ai_parliament":"🏛 Парламент",
        "ai_econ":"📉 Экономика","ai_ask":"💬 Задать вопрос",
        "back":"🔙 Назад","title":"🏠 Главное меню",
        "live":"🔴 Прямой эфир","submit":"📢 Поделиться новостью",
    },
    "فارسی 🇮🇷": {
        "news":"📰 اخبار","deep":"🔍 جستجوی عمیق","ai":"🧠 تحلیل هوش مصنوعی",
        "sports":"🏅 ورزش","weather":"🌤 آبوهوا","markets":"💰 بازارها",
        "settings":"⚙️ تنظیمات","help":"❓ راهنما",
        "ai_verify":"✅ تأیید خبر","ai_analyze":"🧠 تحلیل سیاسی",
        "ai_compare":"🌐 مقایسه منابع","ai_timeline":"📅 خط زمانی",
        "ai_predict":"🔮 پیشبینی","ai_influence":"🗺 نقشه نفوذ",
        "ai_profile":"🕵️ پروفایل شخص","ai_parliament":"🏛 پارلمان",
        "ai_econ":"📉 اقتصاد","ai_ask":"💬 بپرس",
        "back":"🔙 بازگشت","title":"🏠 منوی اصلی",
        "live":"🔴 رویداد زنده","submit":"📢 ارسال خبر",
    },
    "हिन्दी 🇮🇳": {
        "news":"📰 समाचार","deep":"🔍 DeepSearch","ai":"🧠 AI विश्लेषण",
        "sports":"🏅 खेल","weather":"🌤 मौसम","markets":"💰 बाज़ार",
        "settings":"⚙️ सेटिंग्स","help":"❓ सहायता",
        "ai_verify":"✅ समाचार जांच","ai_analyze":"🧠 राजनीतिक विश्लेषण",
        "ai_compare":"🌐 स्रोत तुलना","ai_timeline":"📅 समयरेखा",
        "ai_predict":"🔮 भविष्यवाणी","ai_influence":"🗺 प्रभाव मानचित्र",
        "ai_profile":"🕵️ व्यक्ति प्रोफ़ाइल","ai_parliament":"🏛 संसद",
        "ai_econ":"📉 अर्थव्यवस्था","ai_ask":"💬 मुझसे पूछें",
        "back":"🔙 वापस","title":"🏠 मुख्य मेनू",
        "live":"🔴 लाइव इवेंट","submit":"📢 समाचार भेजें",
    },
    "Português 🇧🇷": {
        "news":"📰 Notícias","deep":"🔍 DeepSearch","ai":"🧠 Análise IA",
        "sports":"🏅 Esportes","weather":"🌤 Clima","markets":"💰 Mercados",
        "settings":"⚙️ Configurações","help":"❓ Ajuda",
        "ai_verify":"✅ Verificar Notícia","ai_analyze":"🧠 Análise Política",
        "ai_compare":"🌐 Comparar Fontes","ai_timeline":"📅 Linha do Tempo",
        "ai_predict":"🔮 Previsões","ai_influence":"🗺 Mapa de Influência",
        "ai_profile":"🕵️ Perfil de Pessoa","ai_parliament":"🏛 Parlamento",
        "ai_econ":"📉 Economia","ai_ask":"💬 Pergunte-me",
        "back":"🔙 Voltar","title":"🏠 Menu Principal",
        "live":"🔴 Evento ao Vivo","submit":"📢 Enviar Notícia",
    },
    "Türkçe 🇹🇷": {
        "news":"📰 Haberler","deep":"🔍 DeepSearch","ai":"🧠 AI Analiz",
        "sports":"🏅 Spor","weather":"🌤 Hava Durumu","markets":"💰 Piyasalar",
        "settings":"⚙️ Ayarlar","help":"❓ Yardım",
        "ai_verify":"✅ Haber Doğrula","ai_analyze":"🧠 Siyasi Analiz",
        "ai_compare":"🌐 Kaynak Karşılaştır","ai_timeline":"📅 Zaman Çizelgesi",
        "ai_predict":"🔮 Tahminler","ai_influence":"🗺 Nüfuz Haritası",
        "ai_profile":"🕵️ Kişi Profili","ai_parliament":"🏛 Parlamento",
        "ai_econ":"📉 Ekonomi","ai_ask":"💬 Bana Sor",
        "back":"🔙 Geri","title":"🏠 Ana Menü",
        "live":"🔴 Canlı Etkinlik","submit":"📢 Haber Gönder",
    },
    "اردو 🇵🇰": {
        "news":"📰 خبریں","deep":"🔍 DeepSearch","ai":"🧠 AI تجزیہ",
        "sports":"🏅 کھیل","weather":"🌤 موسم","markets":"💰 منڈیاں",
        "settings":"⚙️ ترتیبات","help":"❓ مدد",
        "ai_verify":"✅ خبر کی تصدیق","ai_analyze":"🧠 سیاسی تجزیہ",
        "ai_compare":"🌐 ذرائع کا موازنہ","ai_timeline":"📅 وقت کی لکیر",
        "ai_predict":"🔮 پیشن گوئیاں","ai_influence":"🗺 اثر کا نقشہ",
        "ai_profile":"🕵️ شخصیت پروفائل","ai_parliament":"🏛 پارلیمنٹ",
        "ai_econ":"📉 معیشت","ai_ask":"💬 مجھ سے پوچھیں",
        "back":"🔙 واپس","title":"🏠 مرکزی مینو",
        "live":"🔴 براہ راست","submit":"📢 خبر بھیجیں",
    },
    "Deutsch 🇩🇪": {
        "news":"📰 Nachrichten","deep":"🔍 DeepSearch","ai":"🧠 KI-Analyse",
        "sports":"🏅 Sport","weather":"🌤 Wetter","markets":"💰 Märkte",
        "settings":"⚙️ Einstellungen","help":"❓ Hilfe",
        "ai_verify":"✅ Nachricht prüfen","ai_analyze":"🧠 Politische Analyse",
        "ai_compare":"🌐 Quellen vergleichen","ai_timeline":"📅 Zeitlinie",
        "ai_predict":"🔮 Vorhersagen","ai_influence":"🗺 Einfluss-Karte",
        "ai_profile":"🕵️ Personen-Profil","ai_parliament":"🏛 Parlament",
        "ai_econ":"📉 Wirtschaft","ai_ask":"💬 Frag mich",
        "back":"🔙 Zurück","title":"🏠 Hauptmenü",
        "live":"🔴 Live-Event","submit":"📢 Nachricht einreichen",
    },
    "Українська 🇺🇦": {
        "news":"📰 Новини","deep":"🔍 DeepSearch","ai":"🧠 ШІ Аналіз",
        "sports":"🏅 Спорт","weather":"🌤 Погода","markets":"💰 Ринки",
        "settings":"⚙️ Налаштування","help":"❓ Допомога",
        "ai_verify":"✅ Перевірка новини","ai_analyze":"🧠 Політичний аналіз",
        "ai_compare":"🌐 Порівняння джерел","ai_timeline":"📅 Хронологія",
        "ai_predict":"🔮 Прогнози","ai_influence":"🗺 Карта впливу",
        "ai_profile":"🕵️ Профіль особи","ai_parliament":"🏛 Парламент",
        "ai_econ":"📉 Економіка","ai_ask":"💬 Запитай мене",
        "back":"🔙 Назад","title":"🏠 Головне меню",
        "live":"🔴 Пряма трансляція","submit":"📢 Надіслати новину",
    },
    "Italiano 🇮🇹": {
        "news":"📰 Notizie","deep":"🔍 DeepSearch","ai":"🧠 Analisi AI",
        "sports":"🏅 Sport","weather":"🌤 Meteo","markets":"💰 Mercati",
        "settings":"⚙️ Impostazioni","help":"❓ Aiuto",
        "ai_verify":"✅ Verifica Notizia","ai_analyze":"🧠 Analisi Politica",
        "ai_compare":"🌐 Confronta Fonti","ai_timeline":"📅 Linea del Tempo",
        "ai_predict":"🔮 Previsioni","ai_influence":"🗺 Mappa Influenza",
        "ai_profile":"🕵️ Profilo Persona","ai_parliament":"🏛 Parlamento",
        "ai_econ":"📉 Economia","ai_ask":"💬 Chiedimi",
        "back":"🔙 Indietro","title":"🏠 Menu Principale",
        "live":"🔴 Evento Live","submit":"📢 Invia Notizia",
    },
    "Español 🇲🇽": {
        "news":"📰 Noticias","deep":"🔍 DeepSearch","ai":"🧠 Análisis IA",
        "sports":"🏅 Deportes","weather":"🌤 Clima","markets":"💰 Mercados",
        "settings":"⚙️ Configuración","help":"❓ Ayuda",
        "ai_verify":"✅ Verificar Noticia","ai_analyze":"🧠 Análisis Político",
        "ai_compare":"🌐 Comparar Fuentes","ai_timeline":"📅 Línea de Tiempo",
        "ai_predict":"🔮 Predicciones","ai_influence":"🗺 Mapa de Influencia",
        "ai_profile":"🕵️ Perfil de Persona","ai_parliament":"🏛 Parlamento",
        "ai_econ":"📉 Economía","ai_ask":"💬 Pregúntame",
        "back":"🔙 Volver","title":"🏠 Menú Principal",
        "live":"🔴 Evento en Vivo","submit":"📢 Enviar Noticia",
    },
}
# سائر اللغات تستخدم الإنجليزية افتراضياً
@bot.callback_query_handler(func=lambda c: c.data == "menu_deep")
def cb_menu_deep(call):
    uid = call.from_user.id
    lang = users.get(str(uid), {}).get('lang', 'العربية 🇮🇶')
    bot.answer_callback_query(call.id)
    _deep_ask = {
        "العربية 🇮🇶": "🔍 *DeepSearch — بحث عميق*\n\n✏️ *أرسل الموضوع الذي تريد البحث عنه الآن:*\n\n_مثال: الأزمة السياسية في العراق — نتائج الانتخابات — سعر النفط_\n\n⏱ يستغرق البحث 5-15 دقيقة ويفحص عشرات المصادر",
        "English 🇬🇧": "🔍 *DeepSearch*\n\n✏️ *Type your topic now:*\n\n_Example: Iraq political crisis — Oil prices — Elections_\n\n⏱ Takes 5-15 minutes scanning dozens of sources",
        "Русский 🇷🇺": "🔍 *DeepSearch*\n\n✏️ *Напишите тему сейчас:*\n\n_Пример: политический кризис в Ираке_\n\n⏱ Занимает 5-15 минут",
        "فارسی 🇮🇷": "🔍 *DeepSearch*\n\n✏️ *موضوع را اکنون ارسال کنید:*\n\n⏱ ۵ تا ۱۵ دقیقه",
        "हिन्दी 🇮🇳": "🔍 *DeepSearch*\n\n✏️ *अभी विषय टाइप करें:*\n\n⏱ 5-15 मिनट लगते हैं",
        "Português 🇧🇷": "🔍 *DeepSearch*\n\n✏️ *Digite o tópico agora:*\n\n⏱ Demora 5-15 minutos",
        "Türkçe 🇹🇷": "🔍 *DeepSearch*\n\n✏️ *Şimdi konuyu yazın:*\n\n⏱ 5-15 dakika sürer",
        "اردو 🇵🇰": "🔍 *DeepSearch*\n\n✏️ *ابھی موضوع ٹائپ کریں:*\n\n⏱ 5-15 منٹ لگتے ہیں",
        "Deutsch 🇩🇪": "🔍 *DeepSearch*\n\n✏️ *Geben Sie das Thema jetzt ein:*\n\n⏱ Dauert 5-15 Minuten",
        "Українська 🇺🇦": "🔍 *DeepSearch*\n\n✏️ *Введіть тему зараз:*\n\n⏱ Займає 5-15 хвилин",
        "Italiano 🇮🇹": "🔍 *DeepSearch*\n\n✏️ *Scrivi l'argomento ora:*\n\n⏱ Richiede 5-15 minuti",
        "Español 🇲🇽": "🔍 *DeepSearch*\n\n✏️ *Escribe el tema ahora:*\n\n⏱ Tarda 5-15 minutos",
    }
    prompt_text = _deep_ask.get(lang, _deep_ask["English 🇬🇧"])
    sent = bot.send_message(call.message.chat.id, prompt_text, parse_mode="Markdown")

    def _wait_for_deep_topic(msg):
        topic = msg.text.strip() if msg.text else ''
        if not topic or topic.startswith('/'):
            bot.send_message(msg.chat.id, "⚠️ الموضوع فارغ. جرّب مرة أخرى عبر /deepsearch" if lang == "العربية 🇮🇶" else "⚠️ Empty topic. Try /deepsearch again")
            return
        if _deepsearch_active.get(str(uid)):
            bot.send_message(msg.chat.id, "⏳ بحث سابق لا يزال جارياً" if lang == "العربية 🇮🇶" else "⏳ Previous search still running")
            return
        _deepsearch_active[str(uid)] = True
        start_msgs = {
            "العربية 🇮🇶": (
                f"🔍 *DeepSearch بدأ*\n\n📌 الموضوع: *{topic}*\n\n"
                f"⏳ جاري فحص:\n• مصادر RSS العربية والدولية\n"
                f"• مواقع إخبارية بالسكرابنق\n• المصادر الرسمية والحكومية\n"
                f"• قاعدة بيانات NewsAPI العالمية\n• تحليل عميق بالذكاء الاصطناعي\n\n_قد يستغرق 5-15 دقيقة..._"
            ),
            "English 🇬🇧": (
                f"🔍 *DeepSearch Started*\n\n📌 Topic: *{topic}*\n\n"
                f"⏳ Scanning:\n• Arabic & international RSS feeds\n"
                f"• News sites via scraping\n• Official & government sources\n"
                f"• NewsAPI global database\n• Deep AI analysis\n\n_May take 5-15 minutes..._"
            ),
        }
        progress_msg = bot.send_message(
            msg.chat.id,
            start_msgs.get(lang, start_msgs["English 🇬🇧"]),
            parse_mode="Markdown"
        )
        import threading as _thr
        _thr.Thread(
            target=_deepsearch_worker,
            args=(uid, topic, progress_msg.message_id, msg.chat.id),
            daemon=True
        ).start()

    bot.register_next_step_handler(sent, _wait_for_deep_topic)

@bot.callback_query_handler(func=lambda c: c.data == "menu_ai")
def cb_menu_ai(call):
    lang = users.get(str(call.from_user.id), {}).get('lang', 'العربية 🇮🇶')
    bot.answer_callback_query(call.id)
    titles = {"العربية 🇮🇶": "🧠 *تحليل الذكاء الاصطناعي*\nاختر ما تريد:", "English 🇬🇧": "🧠 *AI Analysis*\nChoose:"}
    kb = _build_ai_menu(lang)
    try:
        bot.edit_message_text(titles.get(lang, titles["English 🇬🇧"]),
            call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        bot.send_message(call.message.chat.id, titles.get(lang, titles["English 🇬🇧"]),
            parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("aimenu_"))
def cb_aimenu_item(call):
    lang = users.get(str(call.from_user.id), {}).get('lang', 'العربية 🇮🇶')
    prompts = _aimenu_prompts.get(call.data, {})
    text = prompts.get(lang) or prompts.get("English 🇬🇧", "")
    bot.answer_callback_query(call.id)
    if text:
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════
# ميزات الجيل المتقدم
# ═══════════════════════════════════════════════════════════════════

# ─── 1. أرشيف الأخبار ────────────────────────────────────────────
@bot.message_handler(commands=["search"])
def handle_search_cmd(message):
    """بحث في أرشيف أخبار آخر 7 أيام"""
    if not _FF.get("search", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid  = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    query = message.text.replace('/search', '').strip()
    if not query:
        bot.send_message(message.chat.id, _ui("cmd_search_usage", lang), parse_mode="Markdown")
        return
    results = search_news_archive(query, lang_filter=lang)
    if not results:
        results = search_news_archive(query)
    if not results:
        bot.send_message(message.chat.id,
            _ui("cmd_search_noresult", lang).format(q=query),
            parse_mode="Markdown")
        return
    lines = [_ui("cmd_search_result_hdr", lang).format(q=query)]
    for i, item in enumerate(results[:10], 1):
        ts_str = datetime.datetime.fromtimestamp(item["ts"]).strftime("%d/%m %H:%M")
        fact   = item.get("fact", {})
        v_icon = fact.get("verdict", "") if fact else ""
        link   = item.get("url", "")
        title  = item["title"][:100]
        lines.append(f"{i}. {v_icon} *{title}*\n   _{item.get('source','')[:30]}_ | `{ts_str}`" +
                     (f"\n   🔗 {link}" if link else ""))
    bot.send_message(message.chat.id, "\n\n".join(lines)[:4096], parse_mode="Markdown",
                     disable_web_page_preview=True)


@bot.message_handler(commands=['verify'])
def handle_verify_cmd(message):
    """محقق الشائعات — يتحقق من أي خبر أو ادعاء"""
    if not _FF.get("verify", True):
        bot.send_message(message.chat.id, "⚙️ هذه الميزة موقوفة مؤقتاً.")
        return
    uid_int = message.from_user.id
    uid  = str(uid_int)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid_int, "verify"):
        bot.send_message(message.chat.id, "⏳ استخدمت التحقق مؤخراً. انتظر دقيقة قبل المحاولة.")
        return
    allowed, used, limit = _check_daily_ai_limit(uid_int, "verify")
    if not allowed:
        bot.send_message(message.chat.id, f"📊 وصلت الحد اليومي للتحقق ({limit}/يوم). يتجدد الرصيد غداً.")
        return
    claim = message.text.replace('/verify', '').strip()
    if not claim:
        bot.send_message(message.chat.id, _ui("cmd_verify_usage", lang), parse_mode="Markdown")
        return
    msg = bot.send_message(message.chat.id,
        _ui("cmd_verify_loading", lang).format(claim=claim[:80]), parse_mode="Markdown")
    # جمع أخبار ذات صلة للمقارنة
    keywords = [w for w in claim.split() if len(w) > 3]
    sources_lines = []
    for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", [])))[:8]:
        try:
            feed = _parse_feed(feed_url)
            if not feed:
                continue
            for entry in feed.entries[:8]:
                title = getattr(entry, 'title', '') or ''
                if any(kw.lower() in title.lower() for kw in keywords):
                    sources_lines.append(f"• {title}")
        except Exception as _exc:
            _log_exc(_exc)
    sources_text = "\n".join(sources_lines[:20]) if sources_lines else _ui("cmd_verify_no_sources", lang)
    result = _ai_verify_rumor(claim, sources_text)
    verdict   = result.get("verdict", "⚠️")
    conf      = result.get("confidence", 0)
    explain   = result.get("explanation", "")
    first_src = result.get("first_source", "")
    conf_bar  = "█" * (conf // 10) + "░" * (10 - conf // 10)
    reply = (
        f"{_ui('cmd_verify_hdr', lang)}\n\n"
        f"📌 _{claim[:120]}_\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"{_ui('cmd_verify_verdict_lbl', lang)}: *{verdict}*\n"
        f"{_ui('cmd_verify_confidence_lbl', lang)}: `{conf_bar}` {conf}%\n\n"
        f"📝 {explain}"
    )
    if first_src:
        reply += f"\n\n{_ui('cmd_verify_first_src', lang)} _{first_src}_"
    if sources_lines:
        reply += f"\n\n{_ui('cmd_verify_related_news', lang).format(count=len(sources_lines))}"
    try:
        bot.edit_message_text(reply[:4096], message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")


@bot.message_handler(commands=['connections'])
def handle_connections_cmd(message):
    """خريطة العلاقات — يكشف الروابط بين الأخبار الأخيرة"""
    uid  = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    msg = bot.send_message(message.chat.id, _ui("cmd_connections_loading", lang), parse_mode="Markdown")
    # جمع عناوين آخر الأخبار من الأرشيف
    with _news_archive_lock:
        recent = list(reversed(_news_archive))[:40]
    titles = [it["title"] for it in recent if it.get("lang") == lang or not it.get("lang")]
    if len(titles) < 5:
        # fallback: جمع من RSS
        for feed_url in list(RSS.get(lang, RSS.get("العربية 🇮🇶", [])))[:6]:
            try:
                feed = _parse_feed(feed_url)
                if feed:
                    for e in feed.entries[:5]:
                        t = getattr(e, 'title', '')
                        if t:
                            titles.append(t)
            except Exception as _exc:
                _log_exc(_exc)
    analysis = _ai_find_connections(titles[:30])
    reply = (
        f"{_ui('cmd_connections_hdr', lang).format(count=len(titles))}\n\n"
        f"{analysis[:3800]}"
    )
    try:
        bot.edit_message_text(reply, message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")


@bot.message_handler(commands=['history', 'today'])
def handle_history_cmd(message):
    """ذاكرة الأمة — ماذا جرى في العراق في مثل هذا اليوم"""
    uid  = str(message.from_user.id)
    lang = users.get(uid, {}).get("lang", "العربية 🇮🇶")
    today_fmt = _now_sa().strftime("%d %B")
    msg = bot.send_message(message.chat.id,
        _ui("cmd_history_loading", lang).format(date=today_fmt), parse_mode="Markdown")
    memory = _ai_nation_memory(lang)
    reply = (
        f"{_ui('cmd_history_hdr', lang).format(date=today_fmt)}\n\n"
        f"{memory[:3800]}"
    )
    try:
        bot.edit_message_text(reply, message.chat.id, msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, reply[:4096], parse_mode="Markdown")


@bot.callback_query_handler(func=lambda c: c.data.startswith("fc_"))
def cb_factcheck(call):
    uid  = call.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "العربية 🇮🇶")
    # ── فحص Feature Flag ──
    if not _is_feature_enabled("ai_factcheck", uid):
        bot.answer_callback_query(call.id, _feature_blocked_msg(uid, "ai_factcheck"), show_alert=True)
        return
    bot.answer_callback_query(call.id, _ui("fc_checking", lang))
    fc_key = call.data[3:]
    title = _factcheck_key_cache.get(fc_key, "")
    if title:
        _track_user_click(uid, title, action="factcheck")
    if not title:
        try:
            bot.send_message(call.message.chat.id, _ui("expired", lang))
        except Exception as _exc:
            _log_exc(_exc)
        return
    chat_id = call.message.chat.id
    try:
        wait_msg = bot.send_message(chat_id, _ui("fc_loading", lang), parse_mode="Markdown")
    except Exception:
        wait_msg = None

    def _do_factcheck():
        result  = _ai_fact_check(title)
        verdict = result.get("verdict", "⚠️")
        label   = result.get("label", "يحتاج تحقق")
        reason  = result.get("reason", "")
        if not _AI_AVAILABLE and not reason:
            _tl = title.lower()
            promo_words = ["شارك", "اشترك", "لا تنسى", "تابعنا", "قناتنا",
                           "انضم", "subscribe", "follow", "join", "forward"]
            if any(w in _tl for w in promo_words):
                verdict, label, reason = "❌", "محتوى ترويجي", "النص يحتوي على دعوة للمشاركة أو الاشتراك"
            elif len(title.strip()) < 20:
                verdict, label, reason = "⚠️", "خبر قصير", "العنوان قصير جداً للتحقق"
            elif any(c.isdigit() for c in title) and any(
                    w in _tl for w in ["مليون","مليار","ألف","ميليار","كيلومتر","%"]):
                verdict, label, reason = "✅", "يبدو موثوقاً", "يحتوي على أرقام وتفاصيل محددة"
            else:
                verdict, label, reason = "⚠️", "يحتاج مراجعة", "تحقق من المصدر الأصلي"

        sent    = _ai_sentiment_analysis(title)
        quality = _content_quality_score(title)
        sep = "━━━━━━━━━━━━━━"
        reply = (
            f"{_ui('fc_title', lang)}\n{sep}\n"
            f"📰 _{title[:80]}_\n{sep}\n\n"
            f"{verdict} *{label}*"
            + (f"\n📝 {reason}" if reason else "")
            + f"\n\n{sep}\n"
            f"{_ui('sentiment_label', lang)} {sent['emoji']} {sent['label']}\n"
            f"{_ui('quality_label', lang)} {quality}/100"
        )
        try:
            if wait_msg:
                bot.edit_message_text(reply, chat_id, wait_msg.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do_factcheck)


# ======== معالج زر "لماذا يهمك؟" 💡 (InsightX) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("why_"))
def cb_why_it_matters(call):
    uid  = call.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "العربية 🇮🇶")
    # ── فحص Feature Flag ──
    if not _is_feature_enabled("ai_why", uid):
        bot.answer_callback_query(call.id, _feature_blocked_msg(uid, "ai_why"), show_alert=True)
        return
    if _is_rate_limited(uid, "why_matters"):
        bot.answer_callback_query(call.id, _ui("wait", lang), show_alert=False)
        return
    bot.answer_callback_query(call.id, _ui("why_checking", lang))
    why_key = call.data[4:]
    cached_entry = _why_key_cache.get(why_key)
    if not cached_entry:
        bot.answer_callback_query(call.id, _ui("expired", lang), show_alert=True)
        return
    title   = cached_entry.get("title", "")
    summary = cached_entry.get("summary", "")
    chat_id = call.message.chat.id
    _track_user_click(uid, title, action="why_matters")
    try:
        wait_msg = bot.send_message(chat_id, _ui("why_loading", lang), parse_mode="Markdown")
    except Exception:
        wait_msg = None

    def _do():
        explanation = _ai_why_it_matters(title, summary, lang)
        sep = "━━━━━━━━━━━━━━"
        reply = (
            f"*{_ui('why_title', lang)}*\n{sep}\n"
            f"📰 _{title[:80]}_\n{sep}\n\n"
            f"{explanation}\n{sep}"
        )
        try:
            if wait_msg:
                bot.edit_message_text(reply, chat_id, wait_msg.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== معالج زر "ماذا بعد؟" 🔮 (InsightX) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("next_"))
def cb_what_next(call):
    uid  = call.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid, "what_next"):
        bot.answer_callback_query(call.id, _ui("wait", lang), show_alert=False)
        return
    bot.answer_callback_query(call.id, _ui("next_checking", lang))
    next_key = call.data[5:]
    cached_entry = _next_key_cache.get(next_key)
    if not cached_entry:
        bot.answer_callback_query(call.id, _ui("expired", lang), show_alert=True)
        return
    title   = cached_entry.get("title", "")
    summary = cached_entry.get("summary", "")
    chat_id = call.message.chat.id
    _track_user_click(uid, title, action="what_next")
    try:
        wait_msg = bot.send_message(chat_id, _ui("next_loading", lang), parse_mode="Markdown")
    except Exception:
        wait_msg = None

    def _do():
        prediction = _ai_what_next(title, summary, lang)
        sep = "━━━━━━━━━━━━━━"
        reply = (
            f"*{_ui('next_title', lang)}*\n{sep}\n"
            f"📰 _{title[:80]}_\n{sep}\n\n"
            f"{prediction}\n{sep}"
        )
        try:
            if wait_msg:
                bot.edit_message_text(reply, chat_id, wait_msg.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== معالج زر "🧠 تقرير ذكي شامل" (InsightX Full Intelligence Report) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("intel_"))
def cb_intel_report(call):
    uid = call.from_user.id
    if _is_rate_limited(uid, "intel_report"):
        bot.answer_callback_query(call.id, "⏳ انتظر ثوانٍ قليلة.", show_alert=False)
        return
    bot.answer_callback_query(call.id, "🧠 جاري تحليل الخبر بالكامل...")
    intel_key = call.data[6:]
    cached_entry = _intel_key_cache.get(intel_key)
    if not cached_entry:
        bot.answer_callback_query(call.id,
            "🔄 أُعيد تشغيل البوت — الزر لم يعد صالحاً. اطلب الخبر من جديد.",
            show_alert=True)
        return
    user    = users.get(str(uid), {})
    lang    = user.get("lang", "العربية 🇮🇶")

    # Feature Gating
    if not _check_and_consume_feature(uid, "intel_report"):
        bot.answer_callback_query(call.id, _get_limit_msg(lang, "intel_report"), show_alert=True)
        return

    title   = cached_entry.get("title", "")
    summary = cached_entry.get("summary", "")
    chat_id = call.message.chat.id

    _track_user_click(uid, title, action="intel_report")

    try:
        wait_msg = bot.send_message(chat_id,
            "🧠 *جاري تشغيل محركات InsightX...*\n"
            "_تحليل المشاعر • استخراج الكيانات • تقييم الخطورة • Impact Score_",
            parse_mode="Markdown")
    except Exception:
        wait_msg = None

    def _do():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:  # FIX: كان 4
            f_sentiment = pool.submit(_ai_sentiment_analysis, title, summary)
            f_entities  = pool.submit(_ai_extract_entities,   title, summary)
            f_risk      = pool.submit(_ai_risk_level,          title, summary)
            f_impact    = pool.submit(_ai_impact_and_bias,     title, summary)

        sentiment = f_sentiment.result()
        entities  = f_entities.result()
        risk      = f_risk.result()
        impact    = f_impact.result()

        # جودة المحتوى (بدون AI — فوري)
        quality = _content_quality_score(title, summary)

        sep = "━━━━━━━━━━━━━━"
        # ── بناء التقرير ──────────────────────────────────────────────
        lines = [
            f"🧠 *التقرير الذكي الشامل*\n{sep}",
            f"📰 _{title[:90]}_\n{sep}",
            "",
            f"🎭 *المشاعر:* {sentiment['emoji']} {sentiment['label']} ({sentiment['score']}%)",
            f"🌡️ *الخطورة:* {risk['color']} {risk['level'].upper()}  — {risk['reason'][:60]}",
            f"📊 *Impact Score:* {'█' * (impact['impact_score'] // 10)}{'░' * (10 - impact['impact_score'] // 10)} {impact['impact_score']}/100",
            f"🔍 *التحيز:* {impact.get('bias','unknown')} ({impact.get('bias_direction','neutral')})",
            f"⭐ *جودة المصدر:* {'█' * (quality // 10)}{'░' * (10 - quality // 10)} {quality}/100",
        ]

        # الكيانات
        ppl   = entities.get("people", [])
        plcs  = entities.get("places", [])
        orgs  = entities.get("organizations", [])
        if ppl or plcs or orgs:
            lines.append("")
            lines.append(f"👥 *الكيانات الرئيسية:*")
            if ppl:
                lines.append(f"  👤 الأشخاص: {' • '.join(ppl[:4])}")
            if plcs:
                lines.append(f"  📍 الأماكن: {' • '.join(plcs[:4])}")
            if orgs:
                lines.append(f"  🏛️ المنظمات: {' • '.join(orgs[:3])}")

        lines.append(sep)
        reply = "\n".join(lines)

        try:
            if wait_msg:
                bot.edit_message_text(reply, chat_id, wait_msg.message_id,
                                      parse_mode="Markdown")
            else:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


# ======== معالج زر "📚 السياق التاريخي" (InsightX Context Builder) ========
@bot.callback_query_handler(func=lambda c: c.data.startswith("ctx_"))
def cb_context(call):
    uid  = call.from_user.id
    lang = (users.get(str(uid), {}) or {}).get("lang", "العربية 🇮🇶")
    if _is_rate_limited(uid, "context"):
        bot.answer_callback_query(call.id, _ui("wait", lang), show_alert=False)
        return
    bot.answer_callback_query(call.id, _ui("ctx_checking", lang))
    ctx_key = call.data[4:]
    cached_entry = _ctx_key_cache.get(ctx_key)
    if not cached_entry:
        bot.answer_callback_query(call.id, _ui("expired", lang), show_alert=True)
        return

    # Feature Gating
    if not _check_and_consume_feature(uid, "context"):
        bot.answer_callback_query(call.id, _get_limit_msg(lang, "context"), show_alert=True)
        return

    title   = cached_entry.get("title", "")
    summary = cached_entry.get("summary", "")
    chat_id = call.message.chat.id

    _track_user_click(uid, title, action="context")

    try:
        wait_msg = bot.send_message(chat_id, _ui("ctx_loading", lang), parse_mode="Markdown")
    except Exception:
        wait_msg = None

    def _do():
        context_text = _ai_build_context(title, summary, lang)
        sep = "━━━━━━━━━━━━━━"
        reply = (
            f"*{_ui('ctx_title', lang)}*\n{sep}\n"
            f"📰 _{title[:80]}_\n{sep}\n\n"
            f"{context_text}\n{sep}"
        )
        try:
            if wait_msg:
                bot.edit_message_text(reply, chat_id, wait_msg.message_id, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
        except Exception:
            try:
                bot.send_message(chat_id, reply, parse_mode="Markdown")
            except Exception as _exc:
                _log_exc(_exc)

    _AI_EXECUTOR.submit(_do)


@bot.callback_query_handler(func=lambda c: c.data.startswith("duel_"))
def cb_ai_duel(call):
    uid  = call.from_user.id
    if uid in banned: return
    bot.answer_callback_query(call.id, "⚔️ جاري تحضير الجدال...")
    key  = call.data[5:]
    data = _duel_key_cache.get(key, {})
    title   = data.get("title", "")
    summary = data.get("summary", "")
    if not title:
        bot.send_message(uid, "🔄 أُعيد تشغيل البوت — الزر لم يعد صالحاً. اطلب الخبر من جديد."); return
    if not _AI_AVAILABLE:
        bot.send_message(uid, _ai_friendly_error(Exception("AI غير متاح"), "duel")); return
    wait = bot.send_message(uid, "⚔️ *جاري تجهيز الجدال الذكي...*\n_الذكاء الاصطناعي يدرس الموقفين..._", parse_mode="Markdown")
    def _run():
        prompt = f"""أنت محلل إخباري محايد. الخبر: "{title}"
{"السياق: " + summary[:300] if summary else ""}

قدّم جدالاً ذكياً من جانبين متضادين بهذا الشكل EXACTLY:

⚔️ **الجدال الذكي**

🔵 **الموقف الأول — المؤيد:**
[3 حجج قوية ومقنعة تدعم هذا الخبر أو الحدث]

🔴 **الموقف الثاني — المعارض:**
[3 حجج قوية ومقنعة ترفض أو تشكك في هذا الخبر أو الحدث]

⚖️ **حكم الذكاء الاصطناعي:**
[جملة واحدة تقييمية محايدة]

اكتب بنفس لغة الخبر. كن دقيقاً وموضوعياً."""
        result = _ai_call_safe(prompt, timeout=20)
        try:
            bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        if result:
            bot.send_message(uid, result, parse_mode="Markdown")
        else:
            bot.send_message(uid, "⚠️ تعذّر إنشاء الجدال. حاول مجدداً.")
    _start_thread_once("AIDuel", _run)


# ══════════════════════════════════════════════════════════════════════════════
#  🧬  NEWS DNA — بصمة الخبر: تحليل عميق متعدد الأبعاد
# ══════════════════════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data.startswith("dna_"))
def cb_news_dna(call):
    uid  = call.from_user.id
    if uid in banned: return
    bot.answer_callback_query(call.id, "🧬 جاري تحليل بصمة الخبر...")
    key  = call.data[4:]
    data = _dna_key_cache.get(key, {})
    title   = data.get("title", "")
    summary = data.get("summary", "")
    if not title:
        bot.send_message(uid, "🔄 أُعيد تشغيل البوت — الزر لم يعد صالحاً. اطلب الخبر من جديد."); return
    if not _AI_AVAILABLE:
        bot.send_message(uid, _ai_friendly_error(Exception("AI غير متاح"), "dna")); return
    wait = bot.send_message(uid, "🧬 *جاري فك شفرة الخبر...*\n_تحليل متعدد الأبعاد..._", parse_mode="Markdown")
    def _run():
        prompt = f"""أنت خبير في تحليل الأخبار. الخبر: "{title}"
{"السياق: " + summary[:300] if summary else ""}

قدّم بصمة ذكية للخبر بهذا الشكل EXACTLY:

🧬 **بصمة الخبر**

👤 **من يستفيد؟**
[الجهة أو الأطراف المستفيدة من نشر هذا الخبر]

💔 **من يتضرر؟**
[الجهة أو الأطراف المتضررة من هذا الخبر]

🔍 **الزاوية الخفية:**
[ما لم يقله الخبر صراحةً — السياق المخفي]

📊 **مستوى التحيز:** [من 1 إلى 10] — [محايد / منحاز قليلاً / منحاز كثيراً]

⚡ **مدى التأثير:** [محلي / إقليمي / عالمي]

🔮 **توقع التطور:** [جملة واحدة]

اكتب بنفس لغة الخبر. كن موضوعياً وجريئاً."""
        result = _ai_call_safe(prompt, timeout=20)
        try:
            bot.delete_message(uid, wait.message_id)
        except Exception as _exc:
            _log_exc(_exc)
        if result:
            bot.send_message(uid, result, parse_mode="Markdown")
        else:
            bot.send_message(uid, "⚠️ تعذّر التحليل. حاول مجدداً.")
    _start_thread_once("NewsDNA", _run)


# ملاحظة: تعريف/تحميل _radar_data و _RADAR_FILE و _radar_lock انتقل إلى
# bot_legacy.py لأن ميزة الرادار الفعلية (cmd_radar وغيرها) موجودة هناك،
# وكانت منفصلة عن تعريفها هنا بسبب تقسيم الملف الأصلي (كود ميت هنا سابقاً).
