import { Theme } from '@mui/material/styles';

// Standard qualitative color palette (e.g., for categories)
// Using common distinguishable colors. More can be added.
export const QUALITATIVE_COLORS = [
  '#1f77b4', // Muted Blue
  '#ff7f0e', // Safety Orange
  '#2ca02c', // Cooked Asparagus Green
  '#d62728', // Brick Red
  '#9467bd', // Muted Purple
  '#8c564b', // Chestnut Brown
  '#e377c2', // Raspberry Sorbet Pink
  '#7f7f7f', // Middle Gray
  '#bcbd22', // Curry Yellow-Green
  '#17becf', // Dark Cyan
  '#aec7e8', // Light Blue
  '#ffbb78', // Light Orange
  '#98df8a', // Light Green
  '#ff9896', // Light Red
  '#c5b0d5', // Light Purple
];

// Sequential color palette (e.g., for gradients, heatmaps if single hue)
// Example: Shades of blue
export const SEQUENTIAL_BLUE = [
  '#eff3ff',
  '#c6dbef',
  '#9ecae1',
  '#6baed6',
  '#4292c6',
  '#2171b5',
  '#084594',
];

// Diverging color palette (e.g., for heatmaps showing positive/negative)
// Example: Red-Yellow-Blue
export const DIVERGING_RdYlBu = [
  '#d73027', // Red
  '#fc8d59',
  '#fee090',
  '#ffffbf', // Center (Yellow)
  '#e0f3f8',
  '#91bfdb',
  '#4575b4', // Blue
];

/**
 * Get a color from the qualitative palette by index.
 * Cycles through colors if index is out of bounds.
 * @param index The index of the color.
 * @returns A hex color string.
 */
export const getColorByIndex = (index: number): string => {
  return QUALITATIVE_COLORS[index % QUALITATIVE_COLORS.length];
};

/**
 * Get chart colors based on the MUI theme.
 * This allows charts to adapt to light/dark mode.
 * @param theme The MUI theme object.
 * @returns An object containing theme-aware color properties.
 */
export const getThemeAwareChartColors = (theme: Theme) => {
  return {
    // Primary and secondary colors from theme
    primary: theme.palette.primary.main,
    secondary: theme.palette.secondary.main,

    // Text and grid colors
    textColor: theme.palette.text.primary,
    textSecondaryColor: theme.palette.text.secondary,
    gridColor: theme.palette.divider,

    // Background colors
    paperBackgroundColor: theme.palette.background.paper,
    plotBackgroundColor: theme.palette.background.default,

    // Specific chart elements
    axisLineColor: theme.palette.text.secondary,
    tooltipBackgroundColor: theme.palette.mode === 'dark' ? 'rgba(40, 40, 40, 0.9)' : 'rgba(250, 250, 250, 0.9)',
    tooltipTextColor: theme.palette.text.primary,

    // Series colors (can use QUALITATIVE_COLORS or derive from theme)
    seriesColors: QUALITATIVE_COLORS, // Default to predefined qualitative palette
    // Example: derive from theme if needed:
    // seriesColors: [
    //   theme.palette.primary.main,
    //   theme.palette.secondary.main,
    //   theme.palette.success.main,
    //   theme.palette.warning.main,
    //   theme.palette.info.main,
    //   // ... add more if needed
    // ],
  };
};

// Function to generate a Plotly colorscale from an array of colors
// Plotly.ColorScale is typically Array<[number, string] | string>
// We are generating the [number, string] array format.
export const generatePlotlyColorscale = (colors: string[]): Array<[number, string]> => {
    if (colors.length === 0) return [];
    if (colors.length === 1) return [[0, colors[0]], [1, colors[0]]]; // Single color spans whole scale

    const scale: Array<[number, string]> = [];
    const step = 1.0 / (colors.length - 1);
    colors.forEach((color, i) => {
        scale.push([i * step, color]);
    });
    // The calculation of step should ensure scale[0][0] is 0 and scale[last][0] is 1.
    return scale;
};

export const DEFAULT_PLOTLY_COLORS = QUALITATIVE_COLORS;

// Example Plotly colorscales that can be used directly
export const PLOTLY_COLORSCALES = {
    Viridis: 'Viridis',
    Cividis: 'Cividis',
    Plasma: 'Plasma',
    RdBu: 'RdBu', // Red-Blue diverging
    Blues: 'Blues', // Sequential Blue
    Greens: 'Greens',
    YlOrRd: 'YlOrRd', // Yellow-Orange-Red sequential
    Portland: 'Portland',
    Jet: 'Jet',
    Electric: 'Electric',
};

export default {
  QUALITATIVE_COLORS,
  SEQUENTIAL_BLUE,
  DIVERGING_RdYlBu,
  getColorByIndex,
  getThemeAwareChartColors,
  generatePlotlyColorscale,
  PLOTLY_COLORSCALES,
  DEFAULT_PLOTLY_COLORS,
};
