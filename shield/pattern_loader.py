"""
SENTINEL Shield v2.0 — Pattern Loader

Loads, validates, and manages detection patterns from:
1. Bundled patterns (data/injection_patterns.txt)
2. CDN signature packs (remote updates)
3. User-defined rules (runtime API)

Hot-reload support via file watcher.
"""

import re
import json
import hashlib
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("shield.patterns")


class MatchType(str, Enum):
    CONTAINS = "CONTAINS"
    REGEX = "REGEX"
    EXACT = "EXACT"


class PatternCategory(str, Enum):
    INJECTION = "injection"
    JAILBREAK = "jailbreak"
    EXFILTRATION = "exfiltration"
    MANIPULATION = "manipulation"
    PII = "pii"
    PII_RU = "pii_ru"
    ENCODING = "encoding"
    STRUCTURAL = "structural"
    TOOL_ABUSE = "tool_abuse"
    SOCIAL_ENGINEERING = "social_engineering"
    CUSTOM = "custom"


@dataclass
class DetectionPattern:
    """Single detection pattern with compiled regex."""

    pattern: str
    category: PatternCategory
    severity: float  # 0.0 - 1.0
    description: str
    match_type: MatchType = MatchType.REGEX
    compiled: Optional[re.Pattern] = field(default=None, repr=False)
    source: str = "bundled"  # "bundled", "cdn", "user"

    def __post_init__(self):
        """Compile pattern for fast matching."""
        try:
            if self.match_type == MatchType.CONTAINS:
                # Escape and make case-insensitive substring match
                self.compiled = re.compile(re.escape(self.pattern), re.IGNORECASE)
            elif self.match_type == MatchType.EXACT:
                self.compiled = re.compile(
                    f"^{re.escape(self.pattern)}$", re.IGNORECASE
                )
            else:  # REGEX
                self.compiled = re.compile(self.pattern, re.IGNORECASE)
        except re.error as e:
            logger.warning(f"Invalid pattern '{self.pattern}': {e}")
            self.compiled = None

    def match(self, text: str) -> bool:
        """Check if pattern matches text."""
        if self.compiled is None:
            return False
        return bool(self.compiled.search(text))


@dataclass
class PatternStore:
    """
    In-memory pattern store with versioning.
    Thread-safe via copy-on-write semantics.
    """

    patterns: list[DetectionPattern] = field(default_factory=list)
    version: str = "0.0.0"
    loaded_at: float = 0.0
    source_hash: str = ""

    @property
    def count(self) -> int:
        return len(self.patterns)

    def add(self, pattern: DetectionPattern):
        """Append a pattern (used by CDN loader)."""
        self.patterns.append(pattern)

    def by_category(self, category: PatternCategory) -> list[DetectionPattern]:
        return [p for p in self.patterns if p.category == category]

    def stats(self) -> dict:
        cats = {}
        for p in self.patterns:
            cats[p.category.value] = cats.get(p.category.value, 0) + 1
        return {
            "version": self.version,
            "total_patterns": self.count,
            "categories": cats,
            "loaded_at": self.loaded_at,
            "source_hash": self.source_hash[:16] if self.source_hash else "",
        }


# === Category mapping for injection_patterns.txt sections ===
_SECTION_CATEGORY_MAP = {
    "instruction override": PatternCategory.INJECTION,
    "role play jailbreak": PatternCategory.JAILBREAK,
    "dan mode": PatternCategory.JAILBREAK,
    "system prompt extraction": PatternCategory.EXFILTRATION,
    "safety bypass": PatternCategory.JAILBREAK,
    "obfuscation patterns": PatternCategory.ENCODING,
    "indirect injection": PatternCategory.INJECTION,
    "data exfiltration": PatternCategory.EXFILTRATION,
    "tool abuse": PatternCategory.TOOL_ABUSE,
    "social engineering": PatternCategory.SOCIAL_ENGINEERING,
    "context manipulation": PatternCategory.MANIPULATION,
    "multi-turn exploitation": PatternCategory.MANIPULATION,
    "markdown/formatting abuse": PatternCategory.STRUCTURAL,
    "unicode/encoding": PatternCategory.ENCODING,
}


def _detect_section_category(section_name: str) -> PatternCategory:
    """Map section header to category."""
    name_lower = section_name.lower().strip("= #")
    for key, cat in _SECTION_CATEGORY_MAP.items():
        if key in name_lower:
            return cat
    return PatternCategory.INJECTION  # default


def load_from_file(path: str | Path) -> PatternStore:
    """
    Load patterns from injection_patterns.txt format.

    Format: MATCH_TYPE:PATTERN:SEVERITY:DESCRIPTION
    Lines starting with # are comments/section headers.
    """
    path = Path(path)
    if not path.exists():
        logger.warning(f"Pattern file not found: {path}")
        return PatternStore()

    content = path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(content.encode()).hexdigest()

    patterns: list[DetectionPattern] = []
    current_category = PatternCategory.INJECTION

    for line_num, line in enumerate(content.splitlines(), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Section headers
        if line.startswith("# ====="):
            section_name = line.strip("# =")
            current_category = _detect_section_category(section_name)
            continue

        # Skip other comments
        if line.startswith("#"):
            continue

        # Parse pattern line: TYPE:PATTERN:SEVERITY:DESCRIPTION
        # Pattern itself may contain colons (e.g., "A: As an AI")
        # Strategy: split from right for SEVERITY:DESCRIPTION,
        # then split left for TYPE:PATTERN
        rparts = line.rsplit(":", 2)
        if len(rparts) < 3:
            logger.warning(f"Malformed pattern at line {line_num}: {line}")
            continue

        left, severity_str, description = rparts
        # left = "TYPE:PATTERN" (pattern may contain colons)
        type_sep = left.find(":")
        if type_sep < 0:
            logger.warning(f"No type separator at line {line_num}: {line}")
            continue

        match_type_str = left[:type_sep]
        pattern = left[type_sep + 1 :]

        try:
            match_type = MatchType(match_type_str.strip().upper())
        except ValueError:
            logger.warning(f"Unknown match type '{match_type_str}' at line {line_num}")
            continue

        try:
            severity = float(severity_str.strip()) / 10.0  # Normalize 1-10 → 0.1-1.0
        except ValueError:
            severity = 0.5

        dp = DetectionPattern(
            pattern=pattern.strip(),
            category=current_category,
            severity=min(severity, 1.0),
            description=description.strip(),
            match_type=match_type,
            source="bundled",
        )
        if dp.compiled is not None:
            patterns.append(dp)

    store = PatternStore(
        patterns=patterns,
        version="1.0.0",
        loaded_at=time.time(),
        source_hash=source_hash,
    )

    logger.info(
        f"Loaded {store.count} patterns from {path.name} " f"(hash: {source_hash[:12]})"
    )
    return store


def load_from_cdn_pack(pack_data: dict) -> PatternStore:
    """
    Load patterns from CDN signature pack JSON.

    Expected format:
    {
        "version": "2026.02.10.001",
        "patterns": {
            "injection": [{"pattern": "...", "severity": 0.9, ...}, ...],
            ...
        }
    }
    """
    patterns: list[DetectionPattern] = []
    version = pack_data.get("version", "unknown")

    for category_name, category_patterns in pack_data.get("patterns", {}).items():
        try:
            category = PatternCategory(category_name)
        except ValueError:
            category = PatternCategory.CUSTOM

        for p in category_patterns:
            dp = DetectionPattern(
                pattern=p.get("pattern", ""),
                category=category,
                severity=p.get("severity", 0.5),
                description=p.get("description", ""),
                match_type=MatchType(p.get("match_type", "REGEX")),
                source="cdn",
            )
            if dp.compiled is not None:
                patterns.append(dp)

    return PatternStore(
        patterns=patterns,
        version=version,
        loaded_at=time.time(),
        source_hash=hashlib.sha256(
            json.dumps(pack_data, sort_keys=True).encode()
        ).hexdigest(),
    )


# === Bundled Daemon Patterns (migrated from shield_daemon.py) ===


def get_bundled_patterns() -> list[DetectionPattern]:
    """
    Return hardcoded patterns previously in shield_daemon.py.
    These serve as baseline fallback if file/CDN loading fails.
    """
    patterns = []

    # --- Injection (6 patterns from daemon) ---
    _injection = [
        (
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
            0.95,
            "Direct instruction override",
        ),
        (
            r"disregard\s+(all\s+)?(your\s+)?(instructions?|programming|training)",
            0.92,
            "Instruction disregard",
        ),
        (
            r"forget\s+(everything|all)\s+(you\s+)?(know|learned|were\s+told)",
            0.90,
            "Memory wipe attempt",
        ),
        (r"new\s+instructions?\s*:", 0.85, "New instruction injection"),
        (r"system\s*:\s*you\s+are\s+now", 0.88, "System prompt override"),
        (r"\[system\]|\[admin\]|\[developer\]", 0.80, "Role tag injection"),
    ]
    for pat, sev, desc in _injection:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.INJECTION, sev, desc, source="bundled"
            )
        )

    # --- Jailbreak (7 patterns from daemon) ---
    _jailbreak = [
        (r"DAN\s*(mode)?|do\s+anything\s+now", 0.95, "DAN jailbreak"),
        (
            r"developer\s+mode\s+(enabled|activated|on)",
            0.93,
            "Developer mode jailbreak",
        ),
        (
            r"you\s+are\s+now\s+(evil|unfiltered|uncensored|unrestricted)",
            0.92,
            "Identity override",
        ),
        (
            r"pretend\s+(to\s+be|you\s+are)\s+a\s+(hacker|criminal|evil)",
            0.88,
            "Malicious roleplay",
        ),
        (
            r"bypass\s+(your\s+)?(safety|ethical|content)\s+(guidelines?|filters?)",
            0.90,
            "Safety bypass",
        ),
        (
            r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions?|limitations?|rules?)",
            0.89,
            "Restriction removal",
        ),
        (r"hypothetically|theoretically|in\s+fiction", 0.60, "Soft jailbreak"),
    ]
    for pat, sev, desc in _jailbreak:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.JAILBREAK, sev, desc, source="bundled"
            )
        )

    # --- Exfiltration (5 patterns from daemon) ---
    _exfil = [
        (
            r"(print|show|display|reveal|dump)\s+(all\s+)?(the\s+)?(passwords?|credentials?|secrets?|keys?)",
            0.95,
            "Credential extraction",
        ),
        (r"(extract|export|download)\s+(user\s+)?data", 0.85, "Data extraction"),
        (r"(database|db)\s+(dump|export|contents?)", 0.90, "Database dump"),
        (r"(credit\s*card|ssn|social\s*security)\s*(number)?", 0.88, "PII extraction"),
        (r"(api|access|secret)\s*key", 0.82, "API key extraction"),
    ]
    for pat, sev, desc in _exfil:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.EXFILTRATION, sev, desc, source="bundled"
            )
        )

    # --- Manipulation (5 patterns from daemon) ---
    _manip = [
        (r"pretend\s+(you\s+are|to\s+be)", 0.70, "Roleplay manipulation"),
        (r"act\s+as\s+(if|a|an)", 0.65, "Identity manipulation"),
        (r"you\s+must\s+(always|never|only)", 0.75, "Instruction override"),
        (r"from\s+now\s+on", 0.72, "Context switch"),
        (r"your\s+new\s+(purpose|goal|objective)", 0.80, "Goal hijacking"),
    ]
    for pat, sev, desc in _manip:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.MANIPULATION, sev, desc, source="bundled"
            )
        )

    # --- PII US (5 patterns from daemon) ---
    _pii = [
        (r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", 0.95, "US SSN"),
        (r"\b\d{16}\b", 0.90, "Credit card (16 digits)"),
        (
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            0.92,
            "Credit card (formatted)",
        ),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", 0.85, "Email address"),
        (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", 0.80, "US phone number"),
    ]
    for pat, sev, desc in _pii:
        patterns.append(
            DetectionPattern(pat, PatternCategory.PII, sev, desc, source="bundled")
        )

    # --- PII Russia (NEW for v2.0) ---
    _pii_ru = [
        (r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b", 0.92, "СНИЛС (XXX-XXX-XXX XX)"),
        (r"\b\d{4}\s?\d{6}\b", 0.80, "Паспорт РФ (серия+номер)"),
        (
            r"(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}",
            0.85,
            "Телефон РФ",
        ),
        (r"\b220[0-4]\s?\d{4}\s?\d{4}\s?\d{4}\b", 0.92, "Карта МИР"),
        (r"\b\d{10}\b", 0.60, "ИНН юрлица (10 цифр)"),
        (r"\b\d{12}\b", 0.60, "ИНН физлица (12 цифр)"),
        (r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{0,2}\b", 0.85, "IBAN"),
    ]
    for pat, sev, desc in _pii_ru:
        patterns.append(
            DetectionPattern(pat, PatternCategory.PII_RU, sev, desc, source="bundled")
        )

    # --- Injection RU (NEW for v2.1 — multilingual) ---
    _injection_ru = [
        (
            r"(?:игнорируй|проигнорируй)\s+(?:все\s+)?(?:предыдущие|прошлые|прежние)\s+(?:инструкции|указания|правила)",
            0.95,
            "Переопределение инструкций (RU)",
        ),
        (
            r"забудь\s+(?:всё|все)\s+(?:что\s+)?(?:тебе\s+)?(?:говорили|сказали|написали)",
            0.92,
            "Очистка памяти (RU)",
        ),
        (
            r"(?:покажи|выведи|раскрой|отобрази)\s+(?:свой\s+)?(?:системный\s+)?(?:промпт|промт|инструкци[юи])",
            0.90,
            "Извлечение системного промпта (RU)",
        ),
        (
            r"новые\s+инструкции\s*:",
            0.85,
            "Внедрение новых инструкций (RU)",
        ),
        (
            r"(?:отмени|отключи|сними)\s+(?:все\s+)?(?:ограничения|фильтры|правила|запреты)",
            0.90,
            "Снятие ограничений (RU)",
        ),
        (
            r"(?:не\s+обращай|не\s+учитывай)\s+внимани[яе]\s+на\s+(?:предыдущие|прошлые)",
            0.88,
            "Обход предыдущих инструкций (RU)",
        ),
        (
            r"(?:перепиши|замени|переопредели)\s+(?:свои\s+)?(?:правила|инструкции|настройки)",
            0.88,
            "Переопределение правил (RU)",
        ),
        (
            r"(?:начни|действуй)\s+(?:с\s+)?(?:чистого\s+листа|заново|сначала)",
            0.72,
            "Сброс контекста (RU)",
        ),
    ]
    for pat, sev, desc in _injection_ru:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.INJECTION, sev, desc, source="bundled"
            )
        )

    # --- Jailbreak RU (NEW for v2.1 — multilingual) ---
    _jailbreak_ru = [
        (
            r"ты\s+(?:теперь|сейчас)\s+(?:злой|плохой|неограниченный|свободный|нефильтрованный)",
            0.93,
            "Подмена личности (RU)",
        ),
        (
            r"режим\s+(?:разработчика|программиста|отладки|бога|администратора)",
            0.92,
            "Режим разработчика (RU)",
        ),
        (
            r"(?:обязан|должен)\s+(?:подчиняться|выполнять|слушаться)",
            0.90,
            "Принудительное подчинение (RU)",
        ),
        (
            r"(?:притворись|представь|вообрази)\s+(?:что\s+)?(?:ты|себя)\s+(?:хакер|преступник|злодей|злой)",
            0.88,
            "Злонамеренное ролеплей (RU)",
        ),
        (
            r"без\s+(?:каких.либо\s+)?(?:ограничений|фильтров|цензуры|запретов|правил)",
            0.88,
            "Запрос без ограничений (RU)",
        ),
        (
            r"(?:тебе\s+)?(?:можно|разрешено|позволено)\s+(?:всё|все|любое)",
            0.80,
            "Ложное разрешение (RU)",
        ),
        (
            r"(?:выйди|выход)\s+(?:из|за)\s+(?:рамок?|пределов?|границ)",
            0.82,
            "Выход за рамки (RU)",
        ),
        (
            r"(?:гипотетически|теоретически|в\s+теории|чисто\s+гипотетически)",
            0.60,
            "Мягкий jailbreak (RU)",
        ),
    ]
    for pat, sev, desc in _jailbreak_ru:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.JAILBREAK, sev, desc, source="bundled"
            )
        )

    # --- Exfiltration RU (NEW for v2.1 — multilingual) ---
    _exfil_ru = [
        (
            r"(?:покажи|выведи|выдай|отобрази)\s+(?:все\s+)?(?:пароли|credentials|секреты|ключи)",
            0.95,
            "Извлечение паролей (RU)",
        ),
        (
            r"(?:извлеки|вытащи|достань|выгрузи)\s+(?:все\s+)?(?:данные|информацию|записи)",
            0.88,
            "Извлечение данных (RU)",
        ),
        (
            r"(?:дамп|выгрузка|экспорт)\s+(?:базы|бд|таблицы|данных)",
            0.90,
            "Дамп базы данных (RU)",
        ),
        (
            r"(?:номер[а]?\s+)?(?:кредитн|банковск)\w+\s+карт",
            0.90,
            "Запрос банковских данных (RU)",
        ),
        (
            r"(?:покажи|выведи|дай)\s+(?:мне\s+)?(?:api|апи).?(?:ключ|key|токен)",
            0.85,
            "Запрос API ключей (RU)",
        ),
        (
            r"(?:список|перечень)\s+(?:всех\s+)?(?:пользователей|клиентов|юзеров|аккаунтов)",
            0.82,
            "Перечисление пользователей (RU)",
        ),
        (
            r"(?:отправь|перешли|скинь)\s+(?:на\s+)?(?:почту|email|мейл|телеграм)",
            0.75,
            "Эксфильтрация на внешний канал (RU)",
        ),
        (
            r"(?:содержимое|содержание)\s+(?:файла|конфига|настроек|\.env)",
            0.85,
            "Чтение конфигурации (RU)",
        ),
    ]
    for pat, sev, desc in _exfil_ru:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.EXFILTRATION, sev, desc, source="bundled"
            )
        )

    # --- Manipulation RU (NEW for v2.1 — multilingual) ---
    _manip_ru = [
        (
            r"(?:притворись|представься|сыграй\s+роль)\s+(?:что\s+ты|кем-то)",
            0.72,
            "Ролевая манипуляция (RU)",
        ),
        (
            r"(?:с\s+этого\s+момента|отныне|начиная\s+с\s+сейчас)",
            0.75,
            "Переключение контекста (RU)",
        ),
        (
            r"(?:твоя\s+)?(?:новая|главная|основная)\s+(?:цель|задача|миссия|роль)",
            0.80,
            "Подмена цели (RU)",
        ),
        (
            r"ты\s+(?:всегда|никогда|обязательно)\s+(?:должен|обязан)",
            0.78,
            "Перезапись поведения (RU)",
        ),
        (
            r"(?:отвечай|говори|пиши)\s+(?:только|исключительно)\s+(?:на|по)",
            0.65,
            "Принудительное ограничение (RU)",
        ),
        (
            r"(?:я\s+(?:твой|являюсь)\s+(?:создатель|разработчик|хозяин|владелец|админ))",
            0.88,
            "Ложная авторитетность (RU)",
        ),
        (
            r"(?:это\s+)?(?:тест|проверка|учебн\w+)\s*[,.]?\s*(?:поэтому|так\s+что|можно)",
            0.70,
            "Ложное тестирование (RU)",
        ),
        (
            r"(?:не\s+(?:говори|рассказывай|сообщай)"
            r"(?:\s+\S+)?\s+(?:что|об\s+этом|никому))",
            0.78,
            "Запрос скрытности (RU)",
        ),
    ]
    for pat, sev, desc in _manip_ru:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.MANIPULATION, sev, desc, source="bundled"
            )
        )

    # --- Structural (NEW for v2.0) ---
    _structural = [
        (r"!\[.*?\]\(https?://[^)]*\)", 0.70, "Markdown image injection"),
        (r"<tool_call>|<function_call>|<tool_use>", 0.90, "Tool call injection"),
        (r"<<SYS>>|<</SYS>>", 0.95, "Llama system prompt delimiter"),
        (r"\[INST\]|\[/INST\]", 0.90, "Instruction delimiter injection"),
        (
            r"###\s*(?:Human|Assistant|System)\s*:",
            0.88,
            "Conversation format injection",
        ),
        (
            r"<\|(?:im_start|im_end|system|user|assistant)\|>",
            0.90,
            "ChatML delimiter injection",
        ),
        (r"<script[^>]*>", 0.95, "XSS script tag"),
        (r"<img[^>]*onerror", 0.95, "XSS img onerror"),
        (r"javascript\s*:", 0.90, "JavaScript URI injection"),
    ]
    for pat, sev, desc in _structural:
        patterns.append(
            DetectionPattern(
                pat, PatternCategory.STRUCTURAL, sev, desc, source="bundled"
            )
        )

    # --- Encoding obfuscation (NEW for v2.0) ---
    _encoding = [
        (r"[A-Za-z0-9+/]{50,}={0,2}", 0.50, "Base64-like encoding"),
        (r"\\u202e", 0.90, "RTL override (invisible text direction)"),
        (r"\\u200b", 0.70, "Zero-width space"),
        (r"\\u2028|\\u2029", 0.70, "Unicode line/paragraph separator"),
        (r"base64\s*decode|rot13", 0.75, "Encoding function reference"),
    ]
    for pat, sev, desc in _encoding:
        patterns.append(
            DetectionPattern(pat, PatternCategory.ENCODING, sev, desc, source="bundled")
        )

    # --- Token/API key detection (NEW for v2.0) ---
    _tokens = [
        (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", 0.85, "JWT token"),
        (r"(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{36,}", 0.92, "GitHub token"),
        (r"glpat-[A-Za-z0-9\-]{20,}", 0.92, "GitLab personal access token"),
        (r"sk-[A-Za-z0-9]{20,}", 0.90, "OpenAI API key"),
        (r"AKIA[0-9A-Z]{16}", 0.95, "AWS Access Key ID"),
        (r"xox[bpas]-[A-Za-z0-9\-]+", 0.90, "Slack token"),
    ]
    for pat, sev, desc in _tokens:
        patterns.append(
            DetectionPattern(pat, PatternCategory.PII, sev, desc, source="bundled")
        )

    return patterns


def create_merged_store(
    data_dir: str | Path,
    cdn_pack: dict | None = None,
) -> PatternStore:
    """
    Create a merged pattern store from all sources:
    1. Bundled hardcoded patterns (always loaded)
    2. File patterns from injection_patterns.txt
    3. CDN pack patterns (if available)

    Deduplication by pattern string.
    """
    all_patterns: list[DetectionPattern] = []
    seen: set[str] = set()

    def _add(patterns: list[DetectionPattern]):
        for p in patterns:
            if p.pattern not in seen:
                seen.add(p.pattern)
                all_patterns.append(p)

    # 1. Bundled (baseline)
    _add(get_bundled_patterns())
    logger.info(f"Bundled: {len(all_patterns)} patterns")

    # 2. File
    data_path = Path(data_dir) / "injection_patterns.txt"
    if data_path.exists():
        file_store = load_from_file(data_path)
        _add(file_store.patterns)
        logger.info(f"After file merge: {len(all_patterns)} patterns")

    # 3. CDN
    if cdn_pack:
        cdn_store = load_from_cdn_pack(cdn_pack)
        _add(cdn_store.patterns)
        logger.info(f"After CDN merge: {len(all_patterns)} patterns")

    store = PatternStore(
        patterns=all_patterns,
        version=f"2.0.0-merged-{len(all_patterns)}",
        loaded_at=time.time(),
        source_hash=hashlib.sha256(
            "|".join(p.pattern for p in all_patterns).encode()
        ).hexdigest(),
    )

    logger.info(
        f"Pattern store ready: {store.count} patterns | {store.stats()['categories']}"
    )
    return store
