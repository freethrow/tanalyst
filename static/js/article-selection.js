/**
 * Article Selection Manager
 * Handles article selection across pages using localStorage
 */
(function () {
  "use strict";

  const STORAGE_KEY = "selected_articles";
  const MAX_SELECTIONS = 50; // Prevent excessive selections

  class ArticleSelectionManager {
    constructor() {
      this.selectedArticles = this.loadFromStorage();
      this.init();
    }

    /**
     * Initialize the selection manager
     */
    init() {
      // Restore checkbox states on page load
      this.restoreCheckboxStates();

      // Update the floating panel
      this.updateFloatingPanel();

      // Listen for storage changes from other tabs
      window.addEventListener("storage", (e) => {
        if (e.key === STORAGE_KEY) {
          this.selectedArticles = this.loadFromStorage();
          this.restoreCheckboxStates();
          this.updateFloatingPanel();
        }
      });
    }

    /**
     * Load selected articles from localStorage
     */
    loadFromStorage() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : {};
      } catch (error) {
        console.error("Error loading selections from localStorage:", error);
        return {};
      }
    }

    /**
     * Save selected articles to localStorage
     */
    saveToStorage() {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(this.selectedArticles)
        );
      } catch (error) {
        console.error("Error saving selections to localStorage:", error);
      }
    }

    /**
     * Toggle article selection
     */
    toggleArticle(checkbox) {
      const articleId = checkbox.dataset.articleId;
      const articleTitle = checkbox.dataset.articleTitle;

      if (!articleId) return;

      if (checkbox.checked) {
        // Add article
        if (Object.keys(this.selectedArticles).length >= MAX_SELECTIONS) {
          checkbox.checked = false;
          this.showToast(
            `Maximum ${MAX_SELECTIONS} articles can be selected`,
            "warning"
          );
          return;
        }

        this.selectedArticles[articleId] = {
          id: articleId,
          title: articleTitle,
          selectedAt: new Date().toISOString(),
        };

        // Add visual feedback to card
        const card = checkbox.closest(".article-card");
        if (card) {
          card.classList.add("ring-2", "ring-primary", "ring-offset-2");
        }

        this.showToast("Article added to selection", "success");
      } else {
        // Remove article
        delete this.selectedArticles[articleId];

        // Remove visual feedback from card
        const card = checkbox.closest(".article-card");
        if (card) {
          card.classList.remove("ring-2", "ring-primary", "ring-offset-2");
        }

        this.showToast("Article removed from selection", "info");
      }

      this.saveToStorage();
      this.updateFloatingPanel();
    }

    /**
     * Restore checkbox states from storage
     */
    restoreCheckboxStates() {
      document.querySelectorAll(".article-selector").forEach((checkbox) => {
        const articleId = checkbox.dataset.articleId;
        const isSelected = !!this.selectedArticles[articleId];

        checkbox.checked = isSelected;

        // Add visual feedback to selected cards
        const card = checkbox.closest(".article-card");
        if (card && isSelected) {
          card.classList.add("ring-2", "ring-primary", "ring-offset-2");
        }
      });
    }

    /**
     * Update the floating selection panel
     */
    updateFloatingPanel() {
      const count = Object.keys(this.selectedArticles).length;
      const panel = document.getElementById("selection-panel");
      const countElement = document.getElementById("selection-count");
      const clearBtn = document.getElementById("clear-selections-btn");
      const viewBtn = document.getElementById("view-selections-btn");

      if (!panel) return;

      if (count > 0) {
        panel.classList.remove("hidden");
        if (countElement) countElement.textContent = count;

        // URL is already set in template via Django's url tag
        // No need to update href dynamically
      } else {
        panel.classList.add("hidden");
      }
    }

    /**
     * Clear all selections
     */
    clearAllSelections() {
      if (Object.keys(this.selectedArticles).length === 0) return;

      if (confirm("Are you sure you want to clear all selected articles?")) {
        this.selectedArticles = {};
        this.saveToStorage();

        // Uncheck all checkboxes
        document.querySelectorAll(".article-selector").forEach((checkbox) => {
          checkbox.checked = false;
          const card = checkbox.closest(".article-card");
          if (card) {
            card.classList.remove("ring-2", "ring-primary", "ring-offset-2");
          }
        });

        this.updateFloatingPanel();
        this.showToast("All selections cleared", "info");
      }
    }

    /**
     * Get all selected article IDs
     */
    getSelectedIds() {
      return Object.keys(this.selectedArticles);
    }

    /**
     * Get all selected articles data
     */
    getSelectedArticles() {
      return Object.values(this.selectedArticles);
    }

    /**
     * Show toast notification
     */
    showToast(message, type = "info") {
      // Use the existing toast system from base.html
      if (window.showToast) {
        window.showToast(message, type);
      } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
      }
    }
  }

  // Create global instance
  window.ArticleSelection = new ArticleSelectionManager();

  // Export for use in other scripts
  if (typeof module !== "undefined" && module.exports) {
    module.exports = ArticleSelectionManager;
  }
})();
