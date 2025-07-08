import React, { useEffect, useRef, useState, Suspense, lazy } from 'react';
import { Box, Typography, IconButton, Menu, MenuItem, CircularProgress, Alert, useTheme, Paper, Tooltip } from '@mui/material'; // Added Paper, Tooltip
import { MoreVert, Download, Fullscreen, Refresh, BrokenImage } from '@mui/icons-material';

// Lazy load Plotly to reduce initial bundle size
const Plot = lazy(() => import('react-plotly.js'));

// Forward declare Plotly if @types/plotly.js is not strictly enforced or causing issues
// This helps TypeScript know Plotly exists globally when react-plotly.js loads it.
declare global {
  var Plotly: any;
}

// Define Plotly types if not globally available or to be more specific
// You might need to install @types/plotly.js if you haven't already.
// The `plotly.js` package itself doesn't export all types needed for `react-plotly.js` props easily.
// Using `any` for `Plotly` related types internally if `@types/plotly.js` causes too many issues
// with `react-plotly.js` specific event types.

interface PlotlyChartProps {
  data: any[]; // Using any[] for data for flexibility, Plotly.Data[] from @types/plotly.js is stricter
  layout?: Partial<any>; // Using Partial<any> for layout, Plotly.Layout is stricter
  config?: Partial<any>; // Using Partial<any> for config, Plotly.Config is stricter
  title?: string;
  height?: number | string;
  loading?: boolean;
  error?: string | null;
  onExport?: (format: 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf' | 'html' | 'json' | 'csv') => void;
  onRefresh?: () => void;
  onRelayout?: (eventData: any) => void; // react-plotly.js event type might be PlotRelayoutEvent
  onClick?: (eventData: any) => void;   // react-plotly.js event type might be PlotMouseEvent
  revision?: number;
  useResizeHandler?: boolean;
  className?: string;
  noDataMessage?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {}, // Default to empty object
  config = {}, // Default to empty object
  title,
  height = 400,
  loading = false,
  error,
  onExport,
  onRefresh,
  onRelayout,
  onClick,
  revision,
  useResizeHandler = true,
  className,
  noDataMessage = "No data available to display."
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const plotRef = useRef<any>(null); // Ref to access Plotly instance if needed

  const defaultLayout = { // Removed Partial<Plotly.Layout> for broader compatibility if types are an issue
    autosize: true,
    margin: { l: 60, r: 30, t: title ? 60 : 30, b: 50 },
    paper_bgcolor: theme.palette.background.paper,
    plot_bgcolor: theme.palette.background.default,
    font: {
      family: theme.typography.fontFamily,
      color: theme.palette.text.primary
    },
    xaxis: {
      gridcolor: theme.palette.divider,
      linecolor: theme.palette.text.secondary,
      zerolinecolor: theme.palette.divider,
      tickfont: { color: theme.palette.text.secondary },
      title: layout.xaxis?.title ? { text: layout.xaxis.title, font: { color: theme.palette.text.secondary } } : undefined,
    },
    yaxis: {
      gridcolor: theme.palette.divider,
      linecolor: theme.palette.text.secondary,
      zerolinecolor: theme.palette.divider,
      tickfont: { color: theme.palette.text.secondary },
      title: layout.yaxis?.title ? { text: layout.yaxis.title, font: { color: theme.palette.text.secondary } } : undefined,
      autorange: layout.yaxis?.autorange // Preserve user-defined autorange
    },
    legend: {
        font: {color: theme.palette.text.secondary},
        bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
    },
    ...(layout || {}), // User layout overrides defaults, ensure layout is not undefined
    title: layout.title || (title ? {text: title, font: {color: theme.palette.text.primary}} : undefined), // Merge title correctly
  };

  const defaultConfig: Partial<any> = { // Using Partial<any> for Plotly.Config
    displaylogo: false,
    responsive: true, // Handled by Plotly's internal responsive logic
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'sendDataToCloud'],
    toImageButtonOptions: {
      format: 'png',
      filename: title ? title.replace(/\s+/g, '_').toLowerCase() : 'chart_export',
      // height and width are taken from the plot by default
      scale: 2 // Higher scale for better resolution
    },
    ...config // User config overrides defaults
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleExport = (format: 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf' | 'html' | 'json' | 'csv') => {
    if (onExport) {
      onExport(format);
    } else if (plotRef.current && plotRef.current.el) {
        // Default Plotly export if no custom handler
        if (['png', 'jpeg', 'webp', 'svg', 'pdf'].includes(format)) {
            Plotly.downloadImage(plotRef.current.el, {
                format: format as 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf',
                filename: defaultConfig.toImageButtonOptions?.filename || 'chart'
            });
        } else if (format === 'csv' && data.length > 0) {
            // Basic CSV export for the first trace - can be enhanced
            const firstTrace = data[0];
            let csvContent = "data:text/csv;charset=utf-8,";
            if (firstTrace.x && firstTrace.y) {
                csvContent += `${firstTrace.name || 'x'},${firstTrace.name || 'y'}\n`; // Headers
                (firstTrace.x as any[]).forEach((val, index) => {
                    csvContent += `${val},${(firstTrace.y as any[])[index]}\n`;
                });
            }
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `${defaultConfig.toImageButtonOptions?.filename || 'chart'}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
         // JSON and HTML export might need more specific handling or rely on Plotly's capabilities if available
    }
    handleMenuClose();
  };

  const isEmptyData = !data || data.length === 0 || data.every(trace => !trace.x?.length && !trace.y?.length && !trace.z?.length);


  if (loading) {
    return (
      <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', border: 1, borderColor: 'divider', borderRadius:1 }} className={className}>
        <CircularProgress size={40} />
        <Typography sx={{ml:1}}>Loading chart...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" icon={<BrokenImage />} sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }} className={className}>
        <Typography variant="body2">Error loading chart: {error}</Typography>
        {onRefresh && <Button size="small" onClick={onRefresh} sx={{ml:1}}>Retry</Button>}
      </Alert>
    );
  }

  if (isEmptyData && !loading) {
    return (
         <Box sx={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', border: 1, borderColor: 'divider', borderRadius:1, p:2, textAlign:'center' }} className={className}>
            <Typography variant="body2" color="text.secondary">{noDataMessage}</Typography>
        </Box>
    );
  }


  return (
    <Paper variant="outlined" sx={{ position: 'relative', height, p: {xs:1, sm:2}, display: 'flex', flexDirection: 'column' }} className={className}>
      {(title || onExport || onRefresh) && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, px: 1 }}>
          {title && <Typography variant="h6" component="h3" sx={{fontSize: '1.1rem', fontWeight: 500}}>{title}</Typography>}
          <Box>
            {onRefresh && (
              <Tooltip title="Refresh Data">
                <IconButton size="small" onClick={onRefresh}><Refresh /></IconButton>
              </Tooltip>
            )}
            {/* Fullscreen button can be added if a modal or fullscreen API is used */}
            {/* <Tooltip title="Fullscreen"><IconButton size="small"><Fullscreen /></IconButton></Tooltip> */}
            {(onExport || plotRef.current) && ( // Enable menu if onExport provided OR if ref is available for default export
              <>
                <Tooltip title="More Options">
                    <IconButton size="small" onClick={handleMenuOpen}><MoreVert /></IconButton>
                </Tooltip>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
                  {['png', 'svg', 'csv', 'json'].map(format => ( // Common export formats
                     <MenuItem key={format} onClick={() => handleExport(format as any)}>
                        <Download sx={{ mr: 1 }} fontSize="small"/> Export {format.toUpperCase()}
                     </MenuItem>
                  ))}
                </Menu>
              </>
            )}
          </Box>
        </Box>
      )}
      <Box sx={{ flexGrow: 1, width: '100%', height: '100%', minHeight: 0 /* Important for flex item to shrink */ }}>
        <Suspense fallback={<Box sx={{display:'flex', justifyContent:'center', alignItems:'center', height:'100%'}}><CircularProgress/></Box>}>
            <Plot
                ref={plotRef}
                data={data as Plotly.Data[]} // Cast to Plotly.Data[]
                layout={defaultLayout}
                config={defaultConfig}
                style={{ width: '100%', height: '100%' }} // Ensure Plotly fills the container
                onRelayout={onRelayout}
                onClick={onClick}
                revision={revision}
                useResizeHandler={useResizeHandler} // Let Plotly handle resize
            />
        </Suspense>
      </Box>
    </Paper>
  );
};


// Specialized chart components (examples)

interface SpecificChartProps extends Omit<PlotlyChartProps, 'data'> {
    // Common props for specific charts, can be expanded
    xData?: any[];
    yData?: any[] | any[][]; // Allow array of arrays for multiple y-axes or traces
    names?: string | string[];
    colors?: string | string[];
    // Add other common specific props like xAxisTitle, yAxisTitle etc.
}

export const LineChart: React.FC<SpecificChartProps> = ({ xData = [], yData = [], names, colors, layout, ...props }) => {
  const traces: any[] = []; // Using any[] for traces
  const yDataArray = Array.isArray(yData?.[0]) ? yData as any[][] : [yData as any[]];
  const namesArray = Array.isArray(names) ? names : (names ? [names] : []);
  const colorsArray = Array.isArray(colors) ? colors : (colors ? [colors] : []);

  yDataArray.forEach((yTrace, index) => {
    traces.push({
      x: xData,
      y: yTrace,
      type: 'scatter',
      mode: 'lines+markers',
      name: namesArray[index] || `Series ${index + 1}`,
      line: { color: colorsArray[index] || undefined }, // Plotly handles undefined color
      marker: { size: 6 }
    });
  });

  // Ensure layout.yaxis exists before trying to set autorange
  const finalLayout = {
    ...(layout || {}),
    yaxis: { ...(layout?.yaxis || {}), autorange: true }
  };

  return <PlotlyChart data={traces} layout={finalLayout} {...props} />;
};

export const BarChart: React.FC<SpecificChartProps> = ({ xData = [], yData = [], names, colors, layout, ...props }) => {
  const traces: any[] = [];
  const yDataArray = Array.isArray(yData?.[0]) ? yData as any[][] : [yData as any[]];
  const namesArray = Array.isArray(names) ? names : (names ? [names] : []);
  const colorsArray = Array.isArray(colors) ? colors : (colors ? [colors] : []);

  yDataArray.forEach((yTrace, index) => {
    traces.push({
      x: xData,
      y: yTrace,
      type: 'bar',
      name: namesArray[index] || `Series ${index + 1}`,
      marker: { color: colorsArray[index] || undefined }
    });
  });
  const finalLayout = { ...(layout || {}), barmode: yDataArray.length > 1 ? 'group' : ('stack' as any) };


  return <PlotlyChart data={traces} layout={finalLayout} {...props} />;
};

export const HeatmapChart: React.FC<Omit<PlotlyChartProps, 'data'> & {
  zData: number[][];
  xLabels?: string[];
  yLabels?: string[];
  colorscale?: any; // Plotly.ColorScale is complex, using `any` for now
}> = ({ zData, xLabels, yLabels, colorscale = 'Viridis', layout, ...props }) => {
  const data = [{
    z: zData,
    x: xLabels,
    y: yLabels,
    type: 'heatmap' as any, // Using `any` for Plotly.PlotType
    colorscale: colorscale,
    showscale: true,
  }];
  const finalLayout = { yaxis: { autorange: 'reversed' }, ...layout }; // Common for heatmaps

  return <PlotlyChart data={data} layout={finalLayout} {...props} />;
};

// Add ScatterChart, MultiLineChart etc. as needed, following similar patterns.
export const ScatterChart: React.FC<SpecificChartProps & { size?: number | number[], symbol?: string | string[] }> = ({ xData = [], yData = [], names, colors, size, symbol, layout, ...props }) => {
  const traces: any[] = []; // Using any[] for traces
  const yDataArray = Array.isArray(yData[0]) ? yData as any[][] : [yData as any[]];
  const namesArray = Array.isArray(names) ? names : [names];
  const colorsArray = Array.isArray(colors) ? colors : [colors];
  const sizesArray = Array.isArray(size) ? size : (size ? [size] : []); // Ensure array or default to empty for map
  const symbolsArray = Array.isArray(symbol) ? symbol : (symbol ? [symbol] : []);


  yDataArray.forEach((yTrace, index) => {
    traces.push({
      x: xData,
      y: yTrace,
      type: 'scatter',
      mode: 'markers',
      name: namesArray[index] || `Series ${index + 1}`,
      marker: {
        color: colorsArray[index] || undefined,
        size: sizesArray[index] || 8, // Default size if not provided for this trace
        symbol: symbolsArray[index] || undefined, // Default symbol
      }
    });
  });

  return <PlotlyChart data={traces} layout={layout} {...props} />;
};
