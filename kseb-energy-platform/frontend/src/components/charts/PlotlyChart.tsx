import React, { useEffect, useRef, useState, Suspense, lazy } from 'react';
import { Box, Typography, IconButton, Menu, MenuItem, CircularProgress, Alert, useTheme, Paper, Tooltip, Button } from '@mui/material'; // Added Button
import { MoreVert, Download, Fullscreen, Refresh, BrokenImage } from '@mui/icons-material';

// Lazy load Plotly to reduce initial bundle size
const Plot = lazy(() => import('react-plotly.js'));

// If @types/plotly.js is installed, TypeScript should use those types.
// The `declare global { var Plotly: any; }` was removed as it conflicts if @types/plotly.js is present.
// We will rely on `react-plotly.js` making Plotly available and use `any` casts for Plotly specific objects
// only if precise typing from @types/plotly.js proves too difficult with react-plotly.js.

interface PlotlyChartProps {
  data: any[];
  layout?: Partial<any>;
  config?: Partial<any>;
  title?: string;
  height?: number | string;
  loading?: boolean;
  error?: string | null;
  onExport?: (format: 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf' | 'html' | 'json' | 'csv') => void;
  onRefresh?: () => void;
  onRelayout?: (eventData: any) => void;
  onClick?: (eventData: any) => void;
  revision?: number;
  useResizeHandler?: boolean;
  className?: string;
  noDataMessage?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
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
  const plotRef = useRef<any>(null);

  const defaultLayout: Partial<any> = { // Using Partial<any> for Plotly.Layout
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
      autorange: layout.yaxis?.autorange
    },
    legend: {
        font: {color: theme.palette.text.secondary},
        bgcolor: theme.palette.mode === 'dark' ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
    },
    ...(layout || {}),
    title: layout.title || (title ? {text: title, font: {color: theme.palette.text.primary}} : undefined),
  };

  const defaultConfig: Partial<any> = { // Using Partial<any> for Plotly.Config
    displaylogo: false,
    responsive: true,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'sendDataToCloud'],
    toImageButtonOptions: {
      format: 'png',
      filename: title ? title.replace(/\s+/g, '_').toLowerCase() : 'chart_export',
      scale: 2
    },
    ...(config || {}),
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget);
  const handleMenuClose = () => setAnchorEl(null);

  const handleExport = (format: 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf' | 'html' | 'json' | 'csv') => {
    if (onExport) {
      onExport(format);
    } else if (plotRef.current && plotRef.current.el && (window as any).Plotly) { // Check for global Plotly
        const Plotly = (window as any).Plotly;
        if (['png', 'jpeg', 'webp', 'svg'].includes(format)) { // PDF export via downloadImage can be problematic/differ
            Plotly.downloadImage(plotRef.current.el, {
                format: format as 'png' | 'jpeg' | 'webp' | 'svg', // Corrected type
                filename: defaultConfig.toImageButtonOptions?.filename || 'chart',
                scale: defaultConfig.toImageButtonOptions?.scale || 1
            });
        } else if (format === 'pdf') {
            // PDF export often requires more setup or a different Plotly method if available
            // For now, let's try with downloadImage but it might not be ideal or fully supported by all backends
             Plotly.downloadImage(plotRef.current.el, {
                format: 'svg', // Often PDF is generated from SVG
                filename: defaultConfig.toImageButtonOptions?.filename || 'chart',
             }).then((svgDataUrl: string) => {
                // This part would need a client-side SVG to PDF library or a server-side conversion
                // For simplicity, we'll just log a warning for now if direct PDF via downloadImage isn't standard
                console.warn("PDF export initiated (from SVG). For robust PDF, server-side conversion or a library like jsPDF might be needed.");
                // Fallback: could offer SVG instead, or just not offer PDF if too complex here.
                // For now, this is a placeholder for a more robust PDF solution.
             }).catch((err: any) => console.error("Error during PDF/SVG export step: ", err));

        } else if (format === 'csv' && data.length > 0) {
            const firstTrace = data[0];
            let csvContent = "data:text/csv;charset=utf-8,";
            if (firstTrace.x && firstTrace.y && Array.isArray(firstTrace.x) && Array.isArray(firstTrace.y)) {
                const headerX = firstTrace.name_x || (firstTrace.xaxis ? `x (${firstTrace.xaxis})` : 'x');
                const headerY = firstTrace.name || (firstTrace.yaxis ? `y (${firstTrace.yaxis})` : 'y');
                csvContent += `${headerX},${headerY}\n`;
                (firstTrace.x as any[]).forEach((val, index) => {
                    csvContent += `${String(val).replace(/"/g, '""')},${String((firstTrace.y as any[])[index]).replace(/"/g, '""')}\n`;
                });
            } else {
                console.warn("CSV export: First trace does not have expected x/y array structure.");
                csvContent += "Error_Could_not_parse_data_for_CSV\n";
            }
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `${defaultConfig.toImageButtonOptions?.filename || 'chart'}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } else if (format === 'json') {
            const jsonData = {
                data: data,
                layout: plotRef.current.el?.layout || defaultLayout // try to get current layout
            };
            const jsonString = JSON.stringify(jsonData, null, 2);
            const blob = new Blob([jsonString], {type: "application/json;charset=utf-8"});
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${defaultConfig.toImageButtonOptions?.filename || 'chart'}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }
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
            {(onExport || (plotRef.current && (window as any).Plotly) ) && (
              <>
                <Tooltip title="More Options">
                    <IconButton size="small" onClick={handleMenuOpen}><MoreVert /></IconButton>
                </Tooltip>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
                  {['png', 'svg', 'csv', 'json'].map(format => (
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
      <Box sx={{ flexGrow: 1, width: '100%', height: '100%', minHeight: 0 }}>
        <Suspense fallback={<Box sx={{display:'flex', justifyContent:'center', alignItems:'center', height:'100%'}}><CircularProgress/></Box>}>
            <Plot
                ref={plotRef}
                data={data as any[]}
                layout={defaultLayout}
                config={defaultConfig}
                style={{ width: '100%', height: '100%' }}
                onRelayout={onRelayout}
                onClick={onClick}
                revision={revision}
                useResizeHandler={useResizeHandler}
            />
        </Suspense>
      </Box>
    </Paper>
  );
};


// Specialized chart components (examples)

interface SpecificChartProps extends Omit<PlotlyChartProps, 'data'> {
    xData?: any[];
    yData?: any[] | any[][];
    names?: string | string[];
    colors?: string | string[];
}

export const LineChart: React.FC<SpecificChartProps> = ({ xData = [], yData = [], names, colors, layout, ...props }) => {
  const traces: any[] = [];
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
      line: { color: colorsArray[index] || undefined },
      marker: { size: 6 }
    });
  });

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
  colorscale?: any;
}> = ({ zData, xLabels, yLabels, colorscale = 'Viridis', layout, ...props }) => {
  const data = [{
    z: zData,
    x: xLabels,
    y: yLabels,
    type: 'heatmap' as any,
    colorscale: colorscale,
    showscale: true,
  }];
  const finalLayout = { ...(layout || {}), yaxis: { ...(layout?.yaxis || {}), autorange: 'reversed' } };

  return <PlotlyChart data={data} layout={finalLayout} {...props} />;
};

export const ScatterChart: React.FC<SpecificChartProps & { size?: number | number[], symbol?: string | string[] }> = ({ xData = [], yData = [], names, colors, size, symbol, layout, ...props }) => {
  const traces: any[] = [];
  const yDataArray = Array.isArray(yData?.[0]) ? yData as any[][] : [yData as any[]];
  const namesArray = Array.isArray(names) ? names : (names ? [names] : []);
  const colorsArray = Array.isArray(colors) ? colors : (colors ? [colors] : []);
  const sizesArray = Array.isArray(size) ? size : (size ? [size] : []);
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
        size: sizesArray[index] || 8,
        symbol: symbolsArray[index] || undefined,
      }
    });
  });

  return <PlotlyChart data={traces} layout={layout} {...props} />;
};
