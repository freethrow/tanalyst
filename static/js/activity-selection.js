/**
 * Activity Selection Manager
 * Handles activity selection across pages using localStorage
 */
(function () {
  "use strict";

  const STORAGE_KEY = "selected_activities";
  const MAX_SELECTIONS = 100; // Prevent excessive selections

  class ActivitySelectionManager {
    constructor() {
      this.selectedActivities = this.loadFromStorage();
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
          this.selectedActivities = this.loadFromStorage();
          this.restoreCheckboxStates();
          this.updateFloatingPanel();
        }
      });
    }

    /**
     * Load selected activities from localStorage
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
     * Save selected activities to localStorage
     */
    saveToStorage() {
      try {
        localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(this.selectedActivities)
        );
      } catch (error) {
        console.error("Error saving selections to localStorage:", error);
      }
    }

    /**
     * Toggle activity selection
     */
    toggleActivity(checkbox) {
      const activityId = checkbox.dataset.activityId;
      const activityTitle = checkbox.dataset.activityTitle;

      if (!activityId) return;

      if (checkbox.checked) {
        // Add activity
        if (Object.keys(this.selectedActivities).length >= MAX_SELECTIONS) {
          checkbox.checked = false;
          this.showToast(
            `Maximum ${MAX_SELECTIONS} activities can be selected`,
            "warning"
          );
          return;
        }

        this.selectedActivities[activityId] = {
          id: activityId,
          title: activityTitle,
          selectedAt: new Date().toISOString(),
        };

        // Add visual feedback to row
        const row = checkbox.closest("tr");
        if (row) {
          row.classList.add("bg-primary/5", "ring-2", "ring-primary");
        }

        this.showToast("Activity added to selection", "success");
      } else {
        // Remove activity
        delete this.selectedActivities[activityId];

        // Remove visual feedback from row
        const row = checkbox.closest("tr");
        if (row) {
          row.classList.remove("bg-primary/5", "ring-2", "ring-primary");
        }

        this.showToast("Activity removed from selection", "info");
      }

      this.saveToStorage();
      this.updateFloatingPanel();
    }

    /**
     * Restore checkbox states from storage
     */
    restoreCheckboxStates() {
      document.querySelectorAll(".activity-selector").forEach((checkbox) => {
        const activityId = checkbox.dataset.activityId;
        const isSelected = !!this.selectedActivities[activityId];

        checkbox.checked = isSelected;

        // Add visual feedback to selected rows
        const row = checkbox.closest("tr");
        if (row && isSelected) {
          row.classList.add("bg-primary/5", "ring-2", "ring-primary");
        }
      });
    }

    /**
     * Update the floating selection panel
     */
    updateFloatingPanel() {
      const count = Object.keys(this.selectedActivities).length;
      const panel = document.getElementById("activity-selection-panel");
      const countElement = document.getElementById("activity-selection-count");

      if (!panel) return;

      if (count > 0) {
        panel.classList.remove("hidden");
        if (countElement) countElement.textContent = count;
      } else {
        panel.classList.add("hidden");
      }
    }

    /**
     * Clear all selections
     */
    clearAllSelections() {
      if (Object.keys(this.selectedActivities).length === 0) return;

      if (confirm("Are you sure you want to clear all selected activities?")) {
        this.selectedActivities = {};
        this.saveToStorage();

        // Uncheck all checkboxes
        document.querySelectorAll(".activity-selector").forEach((checkbox) => {
          checkbox.checked = false;
          const row = checkbox.closest("tr");
          if (row) {
            row.classList.remove("bg-primary/5", "ring-2", "ring-primary");
          }
        });

        this.updateFloatingPanel();
        this.showToast("All selections cleared", "info");
      }
    }

    /**
     * Get all selected activity IDs
     */
    getSelectedIds() {
      return Object.keys(this.selectedActivities);
    }

    /**
     * Get all selected activities data
     */
    getSelectedActivities() {
      return Object.values(this.selectedActivities);
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

    /**
     * Generate Excel report
     */
    generateExcelReport() {
      const ids = this.getSelectedIds();
      if (ids.length === 0) {
        this.showToast("No activities selected", "warning");
        return;
      }

      // Create form and submit
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/activities/report/excel/";

      // Add CSRF token
      const csrfMatch = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
      if (csrfMatch) {
        const csrfInput = document.createElement("input");
        csrfInput.type = "hidden";
        csrfInput.name = "csrfmiddlewaretoken";
        csrfInput.value = csrfMatch[2];
        form.appendChild(csrfInput);
      }

      // Add activity IDs
      const idsInput = document.createElement("input");
      idsInput.type = "hidden";
      idsInput.name = "activity_ids";
      idsInput.value = JSON.stringify(ids);
      form.appendChild(idsInput);

      document.body.appendChild(form);
      form.submit();
      document.body.removeChild(form);
    }

    /**
     * Generate PDF report
     */
    generatePDFReport() {
      const ids = this.getSelectedIds();
      if (ids.length === 0) {
        this.showToast("No activities selected", "warning");
        return;
      }

      // Create form and submit
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/activities/report/pdf/";

      // Add CSRF token
      const csrfMatch = document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'));
      if (csrfMatch) {
        const csrfInput = document.createElement("input");
        csrfInput.type = "hidden";
        csrfInput.name = "csrfmiddlewaretoken";
        csrfInput.value = csrfMatch[2];
        form.appendChild(csrfInput);
      }

      // Add activity IDs
      const idsInput = document.createElement("input");
      idsInput.type = "hidden";
      idsInput.name = "activity_ids";
      idsInput.value = JSON.stringify(ids);
      form.appendChild(idsInput);

      document.body.appendChild(form);
      form.submit();
      document.body.removeChild(form);
    }
  }

  // Create global instance
  window.ActivitySelection = new ActivitySelectionManager();

  // Export for use in other scripts
  if (typeof module !== "undefined" && module.exports) {
    module.exports = ActivitySelectionManager;
  }
})();
