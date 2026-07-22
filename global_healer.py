# -*- coding: utf-8 -*-
"""
global_healer.py — علاج شامل لمشكلة "الأسماء العالمية التائهة" الناتجة عن
تقسيم الملف الأصلي الضخم إلى عشرات الملفات تلقائياً.

المشكلة: كثير من الدوال (خصوصاً في أوامر نادرة الاستخدام مثل /addtrack أو
/follow أو /storyline أو تبديل فريق رياضي) تشير إلى متغيرات أو دوال مُعرَّفة
فعلياً في ملف آخر، لكن بدون أي "import" يربط الملفين ببعضهما. هذا كان يبقى
مخفياً لأن هذه الدوال لا تُستدعى إلا عندما يستخدم شخص الأمر المرتبط بها —
فتنهار في تلك اللحظة فقط بـ NameError.

الحل: بعد اكتمال تحميل كل وحدات المشروع، نبني "سجل شامل" لكل الأسماء
المُعرَّفة في أي وحدة من وحدات المشروع، ثم نفحص كل دالة في كل وحدة عن أسماء
تُستخدَم (LOAD_GLOBAL) وغير موجودة في مساحة أسماء تلك الوحدة — وإن وُجدت في
السجل الشامل، نُلحقها مباشرة في قاموس __globals__ الخاص بتلك الدالة، وهو
نفس القاموس الذي تستخدمه بايثون فعلياً للبحث عن الاسم عند التنفيذ. هذا يُصلح
المشكلة فعلياً وبأثر فوري، دون الحاجة لتعديل عشرات ملفات الاستيراد يدوياً.

ما لا يُعالجه هذا الملف: الأسماء غير المُعرَّفة في أي مكان بالمشروع كله
(أي أنها لم تُكتَب فعلياً، وليست فقط "تائهة") — هذه تبقى في قائمة
"unresolved" ويجب تنفيذها يدوياً (كما حدث سابقاً مع _db_load_channels).
"""

import sys
import types
import dis
import builtins
import logging

_logger = logging.getLogger("IraqNowBot")


def _iter_code_objects(code, seen):
    """يمرّ على كل كائنات الكود المتداخلة (دوال داخلية، list/dict comprehensions)."""
    if id(code) in seen:
        return
    seen.add(id(code))
    yield code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _iter_code_objects(const, seen)


def _build_project_registry(project_dir):
    """يبني سجلاً شاملاً لكل الأسماء المُعرَّفة في وحدات المشروع (وقائمة الوحدات نفسها)."""
    registry = {}
    registry_source = {}
    project_mods = []
    for _name, mod in list(sys.modules.items()):
        mod_file = getattr(mod, "__file__", None) or ""
        if project_dir not in mod_file:
            continue
        project_mods.append(mod)
        for k, v in list(vars(mod).items()):
            if k.startswith("__") and k.endswith("__"):
                continue
            if k not in registry:
                registry[k] = v
                registry_source[k] = getattr(mod, "__name__", "?")
    return registry, registry_source, project_mods


def heal_global_namespaces(project_dir, bot=None):
    """
    project_dir: المسار المطلق لمجلد services/telegram-bot (لتمييز وحدات
    المشروع عن مكتبات بايثون الخارجية).
    يُعيد (healed, unresolved) — قوائم توضيحية للتسجيل والتشخيص.
    """
    builtin_names = set(dir(builtins))

    # ── الخطوة 1: بناء سجل شامل لكل الأسماء المُعرَّفة في وحدات المشروع ──────
    registry, registry_source, project_mods = _build_project_registry(project_dir)

    # ── الخطوة 2: فحص كل دالة في كل وحدة عن أسماء مفقودة، وإصلاحها ──────────
    healed = []
    unresolved = set()
    for mod in project_mods:
        modname = getattr(mod, "__name__", "?")
        seen_codes = set()
        for fname, obj in list(vars(mod).items()):
            if not isinstance(obj, types.FunctionType):
                continue
            try:
                top_code = obj.__code__
                globs = obj.__globals__
            except Exception:
                continue
            for code in _iter_code_objects(top_code, seen_codes):
                for instr in dis.get_instructions(code):
                    if instr.opname != "LOAD_GLOBAL":
                        continue
                    gname = instr.argval
                    if gname in globs or gname in builtin_names or hasattr(builtins, gname):
                        continue
                    if gname in registry:
                        globs[gname] = registry[gname]
                        healed.append((modname, fname, gname, registry_source[gname]))
                    else:
                        unresolved.add((modname, fname, gname))

    return healed, sorted(unresolved)


def heal_handler_filter_lambdas(bot, registry, registry_source, builtin_names):
    """
    FIX: دوال lambda الممرَّرة مباشرة كـ func= داخل @bot.message_handler أو
    @bot.callback_query_handler (مثل func=lambda c: _cb_antispam(...)) لا
    تظهر أبداً في vars(module) لأنها غير مربوطة باسم على مستوى الوحدة —
    لذا كانت heal_global_namespaces() تتجاهلها تماماً، وأي اسم تائه بداخلها
    يبقى NameError حتى لو كان مُعرَّفاً في وحدة أخرى بالمشروع.
    نفحص هنا قوائم bot.message_handlers و bot.callback_query_handlers مباشرة.
    """
    healed = []
    unresolved = set()
    if bot is None:
        return healed, unresolved
    for handler_list in (getattr(bot, "message_handlers", None), getattr(bot, "callback_query_handlers", None)):
        if not handler_list:
            continue
        for h in handler_list:
            func = (h.get("filters") or {}).get("func")
            if not isinstance(func, types.FunctionType):
                continue
            globs = func.__globals__
            modname = getattr(func, "__module__", "?")
            for code in _iter_code_objects(func.__code__, set()):
                for instr in dis.get_instructions(code):
                    if instr.opname != "LOAD_GLOBAL":
                        continue
                    gname = instr.argval
                    if gname in globs or gname in builtin_names or hasattr(builtins, gname):
                        continue
                    if gname in registry:
                        globs[gname] = registry[gname]
                        healed.append((modname, "<lambda filter>", gname, registry_source[gname]))
                    else:
                        unresolved.add((modname, "<lambda filter>", gname))
    return healed, unresolved


def dedupe_message_handlers(bot):
    """
    FIX: بعض الملفات المُضافة حديثاً (مثل users_stats.py) تُعرِّف مُعالِج أمر
    (مثل /mystats) مكرَّراً — الأمر الحقيقي المُستخدَم فعلياً مُسجَّل في ملف
    آخر (مثل handler_callbacks.py) ويعتمد على دالة من الملف الجديد، لكن
    الملف الجديد نفسه يُسجِّل أيضاً نسخته الخاصة من نفس الأمر. بدون هذا
    الفلتر، سيردّ البوت مرتين على أمر واحد.
    نُبقي أول تسجيل لكل تركيبة أوامر فقط (الأقدم/الفعلي)، ونحذف أي تكرار لاحق.
    """
    seen_commands = set()
    deduped = []
    removed = 0
    for h in bot.message_handlers:
        commands = tuple(sorted(h.get("filters", {}).get("commands") or []))
        if commands:
            if commands in seen_commands:
                removed += 1
                continue
            seen_commands.add(commands)
        deduped.append(h)
    if removed:
        bot.message_handlers[:] = deduped
        _logger.info("✅ global_healer: أُزيل %d معالج أمر مكرَّر (نفس الأمر مُسجَّل مرتين)", removed)


def run(project_dir, bot=None):
    """يُشغَّل مرة واحدة بعد تحميل كل وحدات البوت، قبل بدء Long Polling."""
    if bot is not None:
        try:
            dedupe_message_handlers(bot)
        except Exception as _e:
            _logger.warning("⚠️ global_healer: فشل حذف التكرار: %s", _e)

    try:
        healed, unresolved = heal_global_namespaces(project_dir)
    except Exception as _e:
        _logger.warning("⚠️ global_healer: فشل الفحص الشامل: %s", _e)
        return

    try:
        registry, registry_source, _mods = _build_project_registry(project_dir)
        lam_healed, lam_unresolved = heal_handler_filter_lambdas(bot, registry, registry_source, set(dir(builtins)))
        healed = healed + lam_healed
        unresolved = sorted(set(unresolved) | lam_unresolved)
    except Exception as _e:
        _logger.warning("⚠️ global_healer: فشل فحص دوال lambda الخاصة بالمعالجات: %s", _e)

    if healed:
        _logger.info(
            "✅ global_healer: أُصلِح %d اسم عالمي تائه تلقائياً (كانت ستُسبب "
            "NameError عند استخدام أوامر معيّنة)",
            len(healed),
        )
        for modname, fname, gname, src in healed:
            _logger.debug("   %s.%s(): '%s' ← %s", modname, fname, gname, src)

    if unresolved:
        _logger.warning(
            "⚠️ global_healer: %d اسم غير موجود في أي مكان بالمشروع كله "
            "(تحتاج تنفيذاً يدوياً، وليس فقط ربطاً):",
            len(unresolved),
        )
        for modname, fname, gname in unresolved:
            _logger.warning("   %s.%s(): '%s' — غير مُعرَّف إطلاقاً", modname, fname, gname)
