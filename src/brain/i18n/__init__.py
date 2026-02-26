"""
SENTINEL Brain - Internationalization (i18n)

Multi-language support for error messages, API responses, and UI strings.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache


# Supported languages
SUPPORTED_LANGUAGES = ["en", "ru", "zh"]
DEFAULT_LANGUAGE = "en"


class I18n:
    """
    Internationalization manager.
    
    Loads and manages translations for multiple languages.
    """
    
    def __init__(self, locale_dir: Optional[Path] = None):
        self.locale_dir = locale_dir or Path(__file__).parent / "locales"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all translation files."""
        for lang in SUPPORTED_LANGUAGES:
            self._translations[lang] = self._load_language(lang)
    
    def _load_language(self, lang: str) -> Dict[str, str]:
        """Load translations for a specific language."""
        file_path = self.locale_dir / f"{lang}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    
    def t(
        self,
        key: str,
        lang: str = DEFAULT_LANGUAGE,
        **kwargs,
    ) -> str:
        """
        Translate a key to the specified language.
        
        Args:
            key: Translation key (e.g., "error.injection_detected")
            lang: Target language code
            **kwargs: Format arguments for the string
            
        Returns:
            Translated string, or key if not found
        """
        if lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE
        
        translations = self._translations.get(lang, {})
        text = translations.get(key)
        
        # Fallback to English if not found
        if text is None and lang != "en":
            text = self._translations.get("en", {}).get(key)
        
        # Return key if still not found
        if text is None:
            return key
        
        # Format with kwargs if provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def get_language(self, accept_language: Optional[str] = None) -> str:
        """
        Detect language from Accept-Language header.
        
        Args:
            accept_language: HTTP Accept-Language header value
            
        Returns:
            Best matching language code
        """
        if not accept_language:
            return DEFAULT_LANGUAGE
        
        # Parse Accept-Language header
        for part in accept_language.split(","):
            lang = part.split(";")[0].strip().lower()
            lang_code = lang.split("-")[0]
            
            if lang_code in SUPPORTED_LANGUAGES:
                return lang_code
        
        return DEFAULT_LANGUAGE


# Global instance
_i18n: Optional[I18n] = None


def get_i18n() -> I18n:
    """Get global i18n instance."""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Shortcut for translation."""
    return get_i18n().t(key, lang, **kwargs)


__all__ = [
    "I18n",
    "get_i18n",
    "t",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
]
