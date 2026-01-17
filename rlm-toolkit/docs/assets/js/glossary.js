/**
 * RLM Academy - Interactive Glossary JavaScript
 * Enables hover tooltips and expandable cards for glossary terms
 */

(function () {
  "use strict";

  // Glossary data cache
  let glossaryData = null;
  let glossaryDataRu = null;

  // Detect current language
  function getCurrentLanguage() {
    const path = window.location.pathname;
    if (path.includes("/ru/")) return "ru";
    return "en";
  }

  // Load glossary data
  async function loadGlossaryData() {
    const lang = getCurrentLanguage();
    const file =
      lang === "ru" ? "/assets/glossary_ru.json" : "/assets/glossary.json";

    try {
      const response = await fetch(file);
      const data = await response.json();
      return data.terms;
    } catch (error) {
      console.warn("Could not load glossary data:", error);
      return {};
    }
  }

  // Create tooltip HTML
  function createTooltip(termData) {
    const lang = getCurrentLanguage();
    const learnMore = lang === "ru" ? "Подробнее →" : "Learn more →";
    const related = lang === "ru" ? "Связанные:" : "Related:";

    return `
            <div class="glossary-tooltip">
                <div class="glossary-tooltip__term">${termData.term}</div>
                <div class="glossary-tooltip__full">${termData.full}</div>
                <div class="glossary-tooltip__short">${termData.short}</div>
                ${
                  termData.example
                    ? `
                    <div class="glossary-tooltip__example">${escapeHtml(
                      termData.example
                    )}</div>
                `
                    : ""
                }
                ${
                  termData.related && termData.related.length > 0
                    ? `
                    <div class="glossary-tooltip__related">
                        ${related}
                        <div class="glossary-tooltip__related-tags">
                            ${termData.related
                              .map(
                                (t) =>
                                  `<a href="#${t}" class="glossary-tooltip__related-tag">${t}</a>`
                              )
                              .join("")}
                        </div>
                    </div>
                `
                    : ""
                }
                <a href="/glossary/#${termData.term.toLowerCase()}" class="glossary-tooltip__link">${learnMore}</a>
            </div>
        `;
  }

  // Escape HTML for code examples
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Initialize glossary terms in documentation
  async function initGlossaryTerms() {
    const terms = await loadGlossaryData();
    if (!terms || Object.keys(terms).length === 0) return;

    // Find all glossary term elements
    const termElements = document.querySelectorAll(".glossary-term[data-term]");

    termElements.forEach((el) => {
      const termKey = el.getAttribute("data-term");
      const termData = terms[termKey];

      if (termData) {
        // Add tooltip
        el.innerHTML = el.textContent + createTooltip(termData);

        // Make focusable for accessibility
        el.setAttribute("tabindex", "0");
        el.setAttribute("role", "button");
        el.setAttribute("aria-describedby", `tooltip-${termKey}`);
      }
    });
  }

  // Initialize glossary page with cards
  async function initGlossaryPage() {
    const container = document.querySelector(".glossary-grid");
    if (!container) return;

    const terms = await loadGlossaryData();
    if (!terms || Object.keys(terms).length === 0) return;

    const lang = getCurrentLanguage();
    const exampleLabel = lang === "ru" ? "ПРИМЕР" : "EXAMPLE";
    const clickToExpand =
      lang === "ru" ? "Нажмите для подробностей" : "Click to expand";

    // Generate cards
    const cards = Object.entries(terms)
      .map(
        ([key, data]) => `
            <div class="glossary-card" data-term="${key}" title="${clickToExpand}">
                <div class="glossary-card__term">${data.term}</div>
                <div class="glossary-card__full">${data.full}</div>
                <div class="glossary-card__short">${data.short}</div>
                <div class="glossary-card__expand">
                    <div class="glossary-card__long">${data.long}</div>
                    ${
                      data.example
                        ? `
                        <div class="glossary-card__example-label">${exampleLabel}</div>
                        <div class="glossary-card__example">${escapeHtml(
                          data.example
                        )}</div>
                    `
                        : ""
                    }
                </div>
            </div>
        `
      )
      .join("");

    container.innerHTML = cards;

    // Add click handlers for expansion
    container.querySelectorAll(".glossary-card").forEach((card) => {
      card.addEventListener("click", () => {
        card.classList.toggle("expanded");
      });
    });

    // Initialize search
    initGlossarySearch(terms);
  }

  // Search functionality
  function initGlossarySearch(terms) {
    const searchInput = document.querySelector(".glossary-search");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase();
      const cards = document.querySelectorAll(".glossary-card");

      cards.forEach((card) => {
        const term = card.getAttribute("data-term");
        const data = terms[term];

        if (!data) return;

        const searchText = [data.term, data.full, data.short, data.long]
          .join(" ")
          .toLowerCase();

        const matches = searchText.includes(query);
        card.style.display = matches ? "block" : "none";
      });
    });
  }

  // Handle hash navigation to specific term
  function handleHashNavigation() {
    const hash = window.location.hash.slice(1);
    if (!hash) return;

    const card = document.querySelector(`.glossary-card[data-term="${hash}"]`);
    if (card) {
      card.classList.add("expanded");
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.style.animation = "pulse 0.5s ease";
    }
  }

  // Initialize on DOM ready
  function init() {
    // Initialize tooltips in docs
    initGlossaryTerms();

    // Initialize glossary page if on it
    if (document.querySelector(".glossary-grid")) {
      initGlossaryPage();
      handleHashNavigation();
      window.addEventListener("hashchange", handleHashNavigation);
    }
  }

  // Run when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Re-initialize on page navigation (for SPA behavior)
  if (typeof document$ !== "undefined") {
    document$.subscribe(() => init());
  }
})();
