"""Automatic resume translator (Ukrainian <-> English) with PII safety and glossary."""

import asyncio
import json
import logging
import re
from copy import deepcopy
from typing import Literal

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.schemas.profile import ProfileData
from app.schemas.resume import ResumeLanguage

logger = logging.getLogger(__name__)

# Official Ukrainian -> Latin transliteration (Cabinet of Ministers of Ukraine standard)
UK_TO_LATIN_DIGRAPHS = {
    "зг": "zgh",
    "Зг": "Zgh",
    "ЗГ": "ZGH",
}
UK_TO_LATIN_INITIAL = {
    "є": "ye", "Є": "Ye",
    "ї": "yi", "Ї": "Yi",
    "й": "y", "Й": "Y",
    "ю": "yu", "Ю": "Yu",
    "я": "ya", "Я": "Ya",
}
UK_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e",
    "є": "ie", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i",
    "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "shch", "ь": "", "ю": "iu", "я": "ia", "’": "", "'": "",
}

GLOSSARY_UK_TO_EN: dict[str, str] = {
    "київ, україна": "Kyiv, Ukraine",
    "київ": "Kyiv",
    "львів, україна": "Lviv, Ukraine",
    "львів": "Lviv",
    "харків, україна": "Kharkiv, Ukraine",
    "одеса, україна": "Odesa, Ukraine",
    "дніпро, україна": "Dnipro, Ukraine",
    "україна": "Ukraine",
    "віддалено": "Remote",
    "гібрид": "Hybrid",
    "офіс": "On-site",
    "гібрид / віддалено": "Hybrid / Remote",
    "віддалено / гібрид": "Remote / Hybrid",
    "бакалавр": "Bachelor's Degree",
    "магістр": "Master's Degree",
    "молодший бакалавр": "Associate Degree",
    "інформаційні технології": "Information Technology",
    "комп'ютерні науки": "Computer Science",
    "інженерія програмного забезпечення": "Software Engineering",
    "кібербезпека": "Cybersecurity",
    "державний університет інформаційно-комунікаційних технологій": "State University of Information and Communication Technologies",
    "українська": "Ukrainian",
    "англійська": "English",
    "німецька": "German",
    "польська": "Polish",
    "французька": "French",
    "іспанська": "Spanish",
    "рідна": "Native",
    "вільно": "Fluent",
    "середній": "Intermediate",
    "вище середнього": "Upper-Intermediate",
    "початковий": "Beginner",
    "командна робота": "Teamwork",
    "комунікація": "Communication",
    "комунікабельність": "Communication",
    "критичне мислення": "Critical thinking",
    "тайм-менеджмент": "Time management",
    "адаптивність": "Adaptability",
    "вирішення проблем": "Problem solving",
    "лідерство": "Leadership",
    "відповідальність": "Responsibility",
    "швидке навчання": "Fast learner",
    "увага до деталей": "Attention to detail",
    "стресостійкість": "Stress resistance",
    "аналітичне мислення": "Analytical thinking",
}

GLOSSARY_EN_TO_UK: dict[str, str] = {v.lower(): k.capitalize() for k, v in GLOSSARY_UK_TO_EN.items()}
GLOSSARY_EN_TO_UK.update(
    {
        "kyiv, ukraine": "Київ, Україна",
        "kyiv": "Київ",
        "lviv, ukraine": "Львів, Україна",
        "remote": "Віддалено",
        "hybrid": "Гібрид",
        "on-site": "Офіс",
        "hybrid / remote": "Гібрид / Віддалено",
        "remote / hybrid": "Віддалено / Гібрид",
        "bachelor": "Бакалавр",
        "bachelor's degree": "Бакалавр",
        "master": "Магістр",
        "master's degree": "Магістр",
        "information technology": "Інформаційні технології",
        "computer science": "Комп'ютерні науки",
        "software engineering": "Інженерія програмного забезпечення",
        "ukrainian": "Українська",
        "english": "Англійська",
        "native": "Рідна",
        "fluent": "Вільно",
        "state university of information and communication technologies": "Державний університет інформаційно-комунікаційних технологій",
    }
)

_TRANSLATION_CACHE: dict[tuple[str, str, str], str] = {}
CYRILLIC_RE = re.compile(r"[А-Яа-яІіЇїЄєҐґ]")
LATIN_RE = re.compile(r"[A-Za-z]")


class TranslateResumeRequest(BaseModel):
    data: ProfileData
    source_language: ResumeLanguage = "uk"
    target_language: ResumeLanguage = "en"


class TranslateResumeResponse(BaseModel):
    data: ProfileData
    target_language: ResumeLanguage
    provider: str
    translated_fields: int


def transliterate_uk_to_latin(text: str) -> str:
    """Transliterate Ukrainian personal names cleanly into Latin characters."""
    if not text or not CYRILLIC_RE.search(text):
        return text

    words = text.split(" ")
    out_words: list[str] = []
    for word in words:
        w = word
        for k, v in UK_TO_LATIN_DIGRAPHS.items():
            w = w.replace(k, v)
        chars: list[str] = []
        for idx, ch in enumerate(w):
            if idx == 0 and ch in UK_TO_LATIN_INITIAL:
                chars.append(UK_TO_LATIN_INITIAL[ch])
                continue
            low = ch.lower()
            if low in UK_TO_LATIN:
                mapped = UK_TO_LATIN[low]
                if ch.isupper() and mapped:
                    mapped = mapped[0].upper() + mapped[1:]
                chars.append(mapped)
            else:
                chars.append(ch)
        out_words.append("".join(chars))
    return " ".join(out_words)


def _needs_translation(text: str, target_lang: Literal["uk", "en"]) -> bool:
    s = (text or "").strip()
    if len(s) < 2:
        return False
    if target_lang == "en":
        return bool(CYRILLIC_RE.search(s))
    return bool(LATIN_RE.search(s))


def _glossary_lookup(text: str, target_lang: Literal["uk", "en"]) -> str | None:
    key = text.strip().lower()
    table = GLOSSARY_UK_TO_EN if target_lang == "en" else GLOSSARY_EN_TO_UK
    return table.get(key)


async def _translate_one_mymemory(
    client: httpx.AsyncClient,
    text: str,
    source_lang: Literal["uk", "en"],
    target_lang: Literal["uk", "en"],
) -> tuple[str, bool]:
    """Translate a single string via MyMemory public REST API with caching."""
    stripped = text.strip()
    if not _needs_translation(stripped, target_lang):
        return text, False

    direct = _glossary_lookup(stripped, target_lang)
    if direct:
        return direct, True

    cache_key = (source_lang, target_lang, stripped)
    if cache_key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[cache_key], True

    # Handle salary prefix like "від $800" / "from $800" cleanly without calling API
    if target_lang == "en" and stripped.lower().startswith("від "):
        res = "from " + stripped[4:]
        _TRANSLATION_CACHE[cache_key] = res
        return res, True
    if target_lang == "uk" and stripped.lower().startswith("from "):
        res = "від " + stripped[5:]
        _TRANSLATION_CACHE[cache_key] = res
        return res, True

    try:
        resp = await client.get(
            "https://api.mymemory.translated.net/get",
            params={"q": stripped[:500], "langpair": f"{source_lang}|{target_lang}"},
        )
        if resp.status_code == 200:
            payload = resp.json()
            translated = (payload.get("responseData") or {}).get("translatedText")
            status_code = payload.get("responseStatus", 200)
            if translated and int(status_code) == 200 and "MYMEMORY WARNING" not in translated.upper():
                cleaned = translated.strip()
                _TRANSLATION_CACHE[cache_key] = cleaned
                return cleaned, True
    except Exception as exc:
        logger.warning("MyMemory translation failed: %s", exc)

    return text, False


def _translate_via_gemini(
    fields: dict[str, str],
    source_lang: Literal["uk", "en"],
    target_lang: Literal["uk", "en"],
) -> dict[str, str] | None:
    """Use Gemini API when configured for high-precision batch resume translation."""
    settings = get_settings()
    if settings.AI_MOCK_MODE or not settings.GEMINI_API_KEY or not fields:
        return None
    try:
        from google import genai
        from google.genai import types

        src = "Ukrainian" if source_lang == "uk" else "English"
        dst = "English" if target_lang == "en" else "Ukrainian"
        prompt = (
            f"Translate all string values in the JSON object below from {src} to natural, ATS-friendly {dst} for a resume.\n"
            "STRICT RULES:\n"
            "1. Keep ALL JSON keys identical.\n"
            "2. Keep numbers, metrics, dates, technologies (Python, FastAPI, Docker, etc.) and company names unchanged.\n"
            "3. Do NOT invent any new facts.\n"
            "4. Return ONLY valid JSON.\n"
            f"<user_data>{json.dumps(fields, ensure_ascii=False)}</user_data>"
        )
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json"),
        )
        parsed = json.loads((resp.text or "").strip())
        if isinstance(parsed, dict):
            return {k: str(v) for k, v in parsed.items() if k in fields}
    except Exception as exc:
        logger.warning("Gemini resume translation fallback triggered: %s", exc)
    return None


async def translate_resume_data(req: TranslateResumeRequest) -> TranslateResumeResponse:
    """Translate user resume content between Ukrainian and English without leaking PII."""
    data = deepcopy(req.data)
    src = req.source_language
    dst = req.target_language

    if src == dst:
        return TranslateResumeResponse(data=data, target_language=dst, provider="noop", translated_fields=0)

    translated_count = 0

    # Transliterate Ukrainian names to Latin when switching to English (never send email/phone/links!)
    if dst == "en":
        for attr in ("first_name", "last_name", "full_name"):
            old_val = getattr(data.contacts, attr) or ""
            new_val = transliterate_uk_to_latin(old_val)
            if new_val != old_val:
                setattr(data.contacts, attr, new_val)
                translated_count += 1

    # Collect non-PII translatable fields
    fields_to_translate: dict[str, str] = {}
    if _needs_translation(data.contacts.location, dst):
        fields_to_translate["location"] = data.contacts.location
    if _needs_translation(data.target_role, dst):
        fields_to_translate["target_role"] = data.target_role
    if _needs_translation(data.summary, dst):
        fields_to_translate["summary"] = data.summary
    if _needs_translation(data.work_format, dst):
        fields_to_translate["work_format"] = data.work_format
    if _needs_translation(data.desired_salary, dst):
        fields_to_translate["desired_salary"] = data.desired_salary

    for ei, exp in enumerate(data.experiences):
        if _needs_translation(exp.position, dst):
            fields_to_translate[f"exp_{ei}_pos"] = exp.position
        for bi, b in enumerate(exp.bullets):
            if _needs_translation(b, dst):
                fields_to_translate[f"exp_{ei}_b_{bi}"] = b

    for edi, edu in enumerate(data.education):
        if _needs_translation(edu.institution, dst):
            fields_to_translate[f"edu_{edi}_inst"] = edu.institution
        if _needs_translation(edu.degree, dst):
            fields_to_translate[f"edu_{edi}_deg"] = edu.degree
        if _needs_translation(edu.field_of_study, dst):
            fields_to_translate[f"edu_{edi}_field"] = edu.field_of_study

    for ci, course in enumerate(data.courses):
        if _needs_translation(course.title, dst):
            fields_to_translate[f"course_{ci}_title"] = course.title

    for si, skill in enumerate(data.skills):
        # Preserve ASCII technical terms (Python, FastAPI, Docker); only translate Cyrillic skills when -> en
        if dst == "en" and CYRILLIC_RE.search(skill):
            fields_to_translate[f"skill_{si}"] = skill

    for ssi, sskill in enumerate(data.soft_skills):
        if _needs_translation(sskill, dst):
            fields_to_translate[f"soft_skill_{ssi}"] = sskill

    for li, lang in enumerate(data.languages):
        if _needs_translation(lang.name, dst):
            fields_to_translate[f"lang_{li}_name"] = lang.name
        if _needs_translation(lang.level, dst):
            fields_to_translate[f"lang_{li}_level"] = lang.level

    if not fields_to_translate:
        return TranslateResumeResponse(data=data, target_language=dst, provider="local", translated_fields=translated_count)

    # Tier 1: Gemini (if API key active)
    provider = "mymemory"
    results = _translate_via_gemini(fields_to_translate, src, dst)
    if results is not None:
        provider = "gemini"
        translated_count += len(results)
    else:
        # Tier 2: Glossary + MyMemory concurrent HTTP translation
        results = {}
        async with httpx.AsyncClient(timeout=8.0) as client:
            keys = list(fields_to_translate.keys())
            tasks = [_translate_one_mymemory(client, fields_to_translate[k], src, dst) for k in keys]
            done = await asyncio.gather(*tasks)
            any_remote_or_glossary = False
            for k, (val, changed) in zip(keys, done):
                results[k] = val
                if changed:
                    translated_count += 1
                    any_remote_or_glossary = True
            if not any_remote_or_glossary:
                provider = "fallback"

    # Apply translated fields back into ProfileData
    if "location" in results:
        data.contacts.location = results["location"]
    if "target_role" in results:
        data.target_role = results["target_role"]
    if "summary" in results:
        data.summary = results["summary"]
    if "work_format" in results:
        data.work_format = results["work_format"]
    if "desired_salary" in results:
        data.desired_salary = results["desired_salary"]

    for ei, exp in enumerate(data.experiences):
        if f"exp_{ei}_pos" in results:
            exp.position = results[f"exp_{ei}_pos"]
        for bi in range(len(exp.bullets)):
            if f"exp_{ei}_b_{bi}" in results:
                exp.bullets[bi] = results[f"exp_{ei}_b_{bi}"]

    for edi, edu in enumerate(data.education):
        if f"edu_{edi}_inst" in results:
            edu.institution = results[f"edu_{edi}_inst"]
        if f"edu_{edi}_deg" in results:
            edu.degree = results[f"edu_{edi}_deg"]
        if f"edu_{edi}_field" in results:
            edu.field_of_study = results[f"edu_{edi}_field"]

    for ci, course in enumerate(data.courses):
        if f"course_{ci}_title" in results:
            course.title = results[f"course_{ci}_title"]

    for si in range(len(data.skills)):
        if f"skill_{si}" in results:
            data.skills[si] = results[f"skill_{si}"]

    for ssi in range(len(data.soft_skills)):
        if f"soft_skill_{ssi}" in results:
            data.soft_skills[ssi] = results[f"soft_skill_{ssi}"]

    for li, lang in enumerate(data.languages):
        if f"lang_{li}_name" in results:
            lang.name = results[f"lang_{li}_name"]
        if f"lang_{li}_level" in results:
            lang.level = results[f"lang_{li}_level"]

    return TranslateResumeResponse(
        data=data,
        target_language=dst,
        provider=provider,
        translated_fields=translated_count,
    )
