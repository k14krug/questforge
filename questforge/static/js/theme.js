/**
 * Theme management for QuestForge
 * Handles light/dark mode switching and persistence
 */

class ThemeManager {
  constructor() {
    this.themeToggle = document.getElementById('theme-toggle');
    this.init();
  }

  init() {
    // Set initial theme based on preference or stored value
    const storedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (storedTheme) {
      this.setTheme(storedTheme);
    } else if (prefersDark) {
      this.setTheme('dark');
    }

    // Setup event listeners
    if (this.themeToggle) {
      this.themeToggle.addEventListener('click', () => this.toggleTheme());
    }

    // Watch for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
      if (!localStorage.getItem('theme')) {
        this.setTheme(e.matches ? 'dark' : 'light');
      }
    });
  }

  setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem('theme', theme);
    
    // Update toggle button if exists
    if (this.themeToggle) {
      const icon = this.themeToggle.querySelector('i');
      if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
      }
    }
  }

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    this.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new ThemeManager();
});
