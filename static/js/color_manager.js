/**
 * JavaScript Color Manager for Energy Platform
 * Frontend color management system that syncs with backend ColorManager
 */

class ColorManager {
    constructor() {
        this.colors = {};
        this.initialized = false;
        this.apiBase = '/api/colors';
        this.loadColors();
    }

    /**
     * Initialize color manager and load colors
     */
    async loadColors() {
        try {
            // First try to get colors from window.AppColors (set by template)
            if (window.AppColors && typeof window.AppColors === 'object') {
                this.colors = window.AppColors;
                this.initialized = true;
                console.log('✓ Colors loaded from window.AppColors');
                return;
            }

            // Fallback to API if window.AppColors not available
            const response = await fetch(`${this.apiBase}/get-all`);
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success' && result.data) {
                    this.colors = result.data;
                    this.initialized = true;
                    console.log('✓ Colors loaded from API');
                } else {
                    this.loadDefaultColors();
                    console.warn(`⚠ Using default colors - API error: ${result.message || 'Unknown error'}`);
                }
            } else {
                this.loadDefaultColors();
                console.warn('⚠ Using default colors - API not available');
            }
        } catch (error) {
            console.error('Error loading colors:', error);
            this.loadDefaultColors();
        }
    }

    /**
     * Load default colors as fallback
     */
    loadDefaultColors() {
        this.colors = {
            sectors: {
                residential: "#2563EB",
                commercial: "#059669",
                industrial: "#DC2626",
                transportation: "#7C3AED",
                agriculture: "#16A34A",
                public: "#EA580C",
                mining: "#92400E",
                construction: "#0891B2",
                services: "#BE185D",
                other: "#6B7280"
            },
            models: {
                MLR: "#3B82F6",
                SLR: "#10B981",
                WAM: "#F59E0B",
                TimeSeries: "#8B5CF6",
                ARIMA: "#EF4444",
                Linear: "#06B6D4"
            },
            carriers: {
                electricity: "#3B82F6",
                natural_gas: "#EF4444",
                coal: "#1F2937",
                oil: "#92400E",
                biomass: "#16A34A",
                solar: "#F59E0B",
                wind: "#06B6D4",
                hydro: "#0891B2",
                nuclear: "#7C3AED"
            },
            status: {
                success: "#10B981",
                warning: "#F59E0B",
                error: "#EF4444",
                info: "#3B82F6",
                pending: "#6B7280"
            },
            charts: {
                primary: "#2563EB",
                secondary: "#059669",
                tertiary: "#DC2626",
                quaternary: "#7C3AED",
                quinary: "#EA580C"
            }
        };
        this.initialized = true;
    }

    /**
     * Get color for specific category and item
     */
    getColor(category, item, defaultColor = "#6B7280") {
        if (!this.initialized) {
            console.warn('ColorManager not initialized, using default color');
            return defaultColor;
        }

        try {
            const categoryColors = this.colors[category];
            if (categoryColors && categoryColors[item]) {
                return categoryColors[item];
            }

            // Generate color if not exists
            if (categoryColors) {
                const generatedColor = this.generateColorForItem(category, item);
                categoryColors[item] = generatedColor;
                return generatedColor;
            }

            return defaultColor;
        } catch (error) {
            console.error(`Error getting color for ${category}.${item}:`, error);
            return defaultColor;
        }
    }

    /**
     * Get color palette for multiple items in a category
     */
    getColorPalette(category, items) {
        const palette = {};
        items.forEach(item => {
            palette[item] = this.getColor(category, item);
        });
        return palette;
    }

    /**
     * Get colors specifically for sectors
     */
    getSectorColors(sectors) {
        return this.getColorPalette('sectors', sectors);
    }

    /**
     * Get colors specifically for models
     */
    getModelColors(models) {
        return this.getColorPalette('models', models);
    }

    /**
     * Get colors specifically for carriers
     */
    getCarrierColors(carriers) {
        return this.getColorPalette('carriers', carriers);
    }

    /**
     * Get chart colors for specified count
     */
    getChartColors(count, category = 'charts') {
        const baseColors = [
            this.getColor(category, 'primary'),
            this.getColor(category, 'secondary'),
            this.getColor(category, 'tertiary'),
            this.getColor(category, 'quaternary'),
            this.getColor(category, 'quinary')
        ];

        if (count <= baseColors.length) {
            return baseColors.slice(0, count);
        }

        // Generate additional colors if needed
        const additionalColors = [];
        for (let i = baseColors.length; i < count; i++) {
            additionalColors.push(this.generateColorForItem('chart', `color_${i}`));
        }

        return [...baseColors, ...additionalColors];
    }

    /**
     * Generate consistent color for an item based on its name
     */
    generateColorForItem(category, item) {
        // Simple hash function for consistent color generation
        let hash = 0;
        const str = `${category}_${item}`;
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash + str.charCodeAt(i)) & 0xffffffff;
        }

        // Convert to positive number and generate RGB
        hash = Math.abs(hash);
        const r = Math.floor((hash % 256));
        const g = Math.floor(((hash >> 8) % 256));
        const b = Math.floor(((hash >> 16) % 256));

        // Ensure good contrast and visibility
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        let adjustedR = r, adjustedG = g, adjustedB = b;

        if (brightness < 100) { // Too dark
            adjustedR = Math.min(255, r + 100);
            adjustedG = Math.min(255, g + 100);
            adjustedB = Math.min(255, b + 100);
        } else if (brightness > 200) { // Too light
            adjustedR = Math.max(0, r - 100);
            adjustedG = Math.max(0, g - 100);
            adjustedB = Math.max(0, b - 100);
        }

        return `#${adjustedR.toString(16).padStart(2, '0')}${adjustedG.toString(16).padStart(2, '0')}${adjustedB.toString(16).padStart(2, '0')}`;
    }

    /**
     * Set color for specific category and item
     */
    async setColor(category, item, color) {
        try {
            if (!this.colors[category]) {
                this.colors[category] = {};
            }
            this.colors[category][item] = color;

            // Try to save to backend
            const response = await fetch(`${this.apiBase}/set`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    category: category,
                    item: item,
                    color: color
                })
            });

            if (!response.ok) {
                console.warn('Failed to save color to backend');
            }

            return true;
        } catch (error) {
            console.error('Error setting color:', error);
            return false;
        }
    }

    /**
     * Set multiple colors for a category
     */
    async setColors(category, colorDict) {
        try {
            if (!this.colors[category]) {
                this.colors[category] = {};
            }
            Object.assign(this.colors[category], colorDict);

            // Try to save to backend
            const response = await fetch(`${this.apiBase}/set-multiple`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    category: category,
                    colors: colorDict
                })
            });

            if (!response.ok) {
                console.warn('Failed to save colors to backend');
            }

            return true;
        } catch (error) {
            console.error('Error setting colors:', error);
            return false;
        }
    }

    /**
     * Add transparency to hex color
     */
    addTransparency(hexColor, alpha) {
        try {
            const hex = hexColor.replace('#', '');
            const r = parseInt(hex.substr(0, 2), 16);
            const g = parseInt(hex.substr(2, 2), 16);
            const b = parseInt(hex.substr(4, 2), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        } catch (error) {
            return `rgba(59, 130, 246, ${alpha})`;
        }
    }

    /**
     * Darken a hex color by a factor
     */
    darkenColor(hexColor, factor) {
        try {
            const hex = hexColor.replace('#', '');
            let r = parseInt(hex.substr(0, 2), 16);
            let g = parseInt(hex.substr(2, 2), 16);
            let b = parseInt(hex.substr(4, 2), 16);

            r = Math.max(0, Math.floor(r * (1 - factor)));
            g = Math.max(0, Math.floor(g * (1 - factor)));
            b = Math.max(0, Math.floor(b * (1 - factor)));

            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        } catch (error) {
            return '#1D4ED8';
        }
    }

    /**
     * Lighten a hex color by a factor
     */
    lightenColor(hexColor, factor) {
        try {
            const hex = hexColor.replace('#', '');
            let r = parseInt(hex.substr(0, 2), 16);
            let g = parseInt(hex.substr(2, 2), 16);
            let b = parseInt(hex.substr(4, 2), 16);

            r = Math.min(255, Math.floor(r + (255 - r) * factor));
            g = Math.min(255, Math.floor(g + (255 - g) * factor));
            b = Math.min(255, Math.floor(b + (255 - b) * factor));

            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        } catch (error) {
            return '#93C5FD';
        }
    }

    /**
     * Get gradient colors
     */
    getGradient(gradientName) {
        const gradients = this.colors.gradients || {};
        return gradients[gradientName] || ["#3B82F6", "#1D4ED8"];
    }

    /**
     * Create Chart.js dataset with proper colors
     */
    createDataset(label, data, options = {}) {
        const {
            category = 'charts',
            item = 'primary',
            type = 'line',
            fill = false,
            tension = 0.1
        } = options;

        const color = this.getColor(category, item);

        const dataset = {
            label: label,
            data: data,
            borderColor: color,
            backgroundColor: fill ? this.addTransparency(color, 0.3) : this.addTransparency(color, 0.1),
            fill: fill,
            tension: tension,
            borderWidth: 2,
            pointRadius: 3,
            pointHoverRadius: 5
        };

        // Type-specific styling
        if (type === 'bar') {
            dataset.backgroundColor = color;
            dataset.borderWidth = 1;
        } else if (type === 'area') {
            dataset.fill = true;
            dataset.backgroundColor = this.addTransparency(color, 0.3);
        }

        return dataset;
    }

    /**
     * Get all colors
     */
    getAllColors() {
        return { ...this.colors };
    }

    /**
     * Get category colors
     */
    getCategoryColors(category) {
        return { ...(this.colors[category] || {}) };
    }

    /**
     * Wait for initialization
     */
    async waitForInitialization() {
        if (this.initialized) return;

        let attempts = 0;
        const maxAttempts = 50;

        while (!this.initialized && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 100));
            attempts++;
        }

        if (!this.initialized) {
            console.warn('ColorManager initialization timeout, using defaults');
            this.loadDefaultColors();
        }
    }

    /**
     * Reset colors to defaults
     */
    async resetToDefaults(category = null) {
        try {
            const response = await fetch(`${this.apiBase}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ category: category })
            });

            if (response.ok) {
                await this.loadColors();
                return true;
            } else {
                console.warn('Failed to reset colors via API');
                if (category && this.colors[category]) {
                    // Reset locally
                    this.loadDefaultColors();
                    return true;
                }
            }
        } catch (error) {
            console.error('Error resetting colors:', error);
        }
        return false;
    }

    /**
     * Save all current colors to backend
     */
    async saveAllColors() {
        try {
            const response = await fetch(`${this.apiBase}/save-all`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.colors)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: `Server responded with status ${response.status}` }));
                console.error('Failed to save all colors to backend:', errorData);
                throw new Error(errorData.message || `Failed to save colors. Status: ${response.status}`);
            }

            const result = await response.json();
            if (result.status !== 'success') {
                throw new Error(result.message || 'Backend reported an error on save.');
            }

            return true;
        } catch (error) {
            console.error('Error in saveAllColors:', error);
            throw error; // Re-throw to be caught by the caller
        }
    }
}

// Create global instance
window.ColorManager = ColorManager;
window.colorManager = new window.ColorManager();

// Utility functions for global access
window.getColor = (category, item, defaultColor) => window.colorManager.getColor(category, item, defaultColor);
window.getSectorColors = (sectors) => window.colorManager.getSectorColors(sectors);
window.getModelColors = (models) => window.colorManager.getModelColors(models);
window.getChartColors = (count) => window.colorManager.getChartColors(count);

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ColorManager;
}