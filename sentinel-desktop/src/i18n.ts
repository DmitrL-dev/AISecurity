/**
 * SENTINEL Desktop - Internationalization Module
 *
 * Provides i18n support for EN/RU locales.
 * Usage: import { t, setLocale, getCurrentLocale } from './i18n';
 */

import ruLocale from "./locales/ru.json";
import enLocale from "./locales/en.json";

// Type definitions
type LocaleData = typeof ruLocale;
type LocaleKey = "ru" | "en";

// Available locales
const locales: Record<LocaleKey, LocaleData> = {
  ru: ruLocale,
  en: enLocale,
};

// Current locale (default: detect from system or use RU)
let currentLocale: LocaleKey = detectSystemLocale();

/**
 * Detect system locale from browser
 */
function detectSystemLocale(): LocaleKey {
  const systemLang = navigator.language.toLowerCase();
  if (systemLang.startsWith("en")) {
    return "en";
  }
  return "ru"; // Default to Russian
}

/**
 * Get current locale
 */
export function getCurrentLocale(): LocaleKey {
  return currentLocale;
}

/**
 * Set locale
 */
export function setLocale(locale: LocaleKey): void {
  if (locales[locale]) {
    currentLocale = locale;
    localStorage.setItem("sentinel-locale", locale);
    // Dispatch event for UI update
    window.dispatchEvent(new CustomEvent("locale-changed", { detail: locale }));
  }
}

/**
 * Initialize locale from localStorage or system
 */
export function initLocale(): LocaleKey {
  const saved = localStorage.getItem("sentinel-locale") as LocaleKey | null;
  if (saved && locales[saved]) {
    currentLocale = saved;
  } else {
    currentLocale = detectSystemLocale();
  }
  return currentLocale;
}

/**
 * Translate a key path (e.g., 'nav.home', 'settings.title')
 */
export function t(
  keyPath: string,
  replacements?: Record<string, string | number>
): string {
  const keys = keyPath.split(".");
  let result: any = locales[currentLocale];

  for (const key of keys) {
    if (result && typeof result === "object" && key in result) {
      result = result[key];
    } else {
      // Fallback to English
      result = locales["en"];
      for (const k of keys) {
        if (result && typeof result === "object" && k in result) {
          result = result[k];
        } else {
          console.warn(`i18n: Missing translation for "${keyPath}"`);
          return keyPath; // Return key as fallback
        }
      }
      break;
    }
  }

  if (typeof result !== "string") {
    console.warn(`i18n: Key "${keyPath}" is not a string`);
    return keyPath;
  }

  // Apply replacements: {{key}} -> value
  if (replacements) {
    for (const [key, value] of Object.entries(replacements)) {
      result = result.replace(new RegExp(`{{${key}}}`, "g"), String(value));
    }
  }

  return result;
}

/**
 * Get all available locales
 */
export function getAvailableLocales(): { code: LocaleKey; name: string }[] {
  return [
    { code: "ru", name: "Русский" },
    { code: "en", name: "English" },
  ];
}

/**
 * Apply translations to DOM elements with data-i18n attribute
 * Usage: <span data-i18n="nav.home">Главная</span>
 */
export function applyTranslations(): void {
  console.log("[i18n] Applying translations, locale:", currentLocale);
  const elements = document.querySelectorAll("[data-i18n]");
  console.log("[i18n] Found elements with data-i18n:", elements.length);
  elements.forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      const translated = t(key);
      console.log(`[i18n] ${key} -> "${translated}"`);
      el.textContent = translated;
    }
  });

  // Also handle placeholders
  const inputs = document.querySelectorAll("[data-i18n-placeholder]");
  inputs.forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    if (key && el instanceof HTMLInputElement) {
      el.placeholder = t(key);
    }
  });

  // Handle titles
  const titled = document.querySelectorAll("[data-i18n-title]");
  titled.forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (key && el instanceof HTMLElement) {
      el.title = t(key);
    }
  });
}

// Auto-init on load
if (typeof window !== "undefined") {
  initLocale();
}

// Export types
export type { LocaleKey, LocaleData };
