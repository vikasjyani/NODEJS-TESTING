import { MutableRefObject } from 'react';
// Plotly type, assuming it's available globally or via import type PlotlyType from 'plotly.js';
// For this example, we'll assume a Plotly object with downloadImage and react methods.
declare var Plotly: any;

export interface PlotlyHTMLElement extends HTMLElement {
  // If you have a more specific type for the Plotly graph div element
  // For example, if it's a specific component instance:
  // plotlyInstance?: PlotlyType.PlotlyHTMLElement; // This is more accurate if using @types/plotly.js
}


export const exportChart = async (
    plotRef: MutableRefObject<PlotlyHTMLElement | null | {el: PlotlyHTMLElement}>, // Ref to the Plotly chart component or its DOM element
    format: 'png' | 'jpeg' | 'webp' | 'svg' | 'pdf' | 'csv' | 'json' | 'html' = 'png',
    filename: string = 'chart_export',
    plotData?: Partial<Plotly.PlotData>[] // Required for CSV/JSON if not extracting from ref
) => {
    let graphDiv: PlotlyHTMLElement | null = null;

    if (plotRef.current) {
        if ('el' in plotRef.current) { // Handles cases where ref points to react-plotly.js component instance
            graphDiv = plotRef.current.el as PlotlyHTMLElement;
        } else {
            graphDiv = plotRef.current as PlotlyHTMLElement;
        }
    }

    if (!graphDiv && !['csv', 'json'].includes(format)) {
        console.error('ChartExporter: Plotly graph element reference is not available for image/PDF/HTML export.');
        throw new Error('Graph element not found for export.');
    }

    try {
        switch (format) {
            case 'png':
            case 'jpeg':
            case 'webp':
            case 'svg':
            case 'pdf':
                if (graphDiv) {
                    await Plotly.downloadImage(graphDiv, {
                        format: format,
                        filename: `${filename}.${format}`,
                        // width: graphDiv.offsetWidth, // Or specify desired width/height
                        // height: graphDiv.offsetHeight,
                        scale: 2 // For better resolution on raster formats
                    });
                }
                break;
            case 'html':
                if (graphDiv) {
                    // This requires more setup for full interactivity (Plotly.toImage is static)
                    // A more robust way is to serialize the data and layout and reconstruct
                    // For a simple static HTML, one might try to get the outerHTML or use a library
                    console.warn('ChartExporter: HTML export is complex and might be static. Consider Plotly.toReact or full page save.');

                    // Basic attempt: export current view as image within HTML
                    const dataUrl = await Plotly.toImage(graphDiv, { format: 'png', scale: 1 });
                    const htmlContent = `
                        <html>
                            <head><title>${filename}</title></head>
                            <body>
                                <h1>${filename}</h1>
                                <img src="${dataUrl}" alt="${filename}" />
                                <p>Exported on: ${new Date().toLocaleString()}</p>
                            </body>
                        </html>`;
                    const blob = new Blob([htmlContent], { type: 'text/html' });
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = `${filename}.html`;
                    link.click();
                    URL.revokeObjectURL(link.href);
                }
                break;
            case 'csv':
            case 'json':
                if (!plotData || plotData.length === 0) {
                    // Try to get data from the plot itself if not provided
                    // This is tricky as plotRef.current.data might not be the direct Plotly data array.
                    // If using react-plotly.js, the component instance might have a 'data' prop.
                    // For now, we'll rely on plotData being passed for CSV/JSON.
                    console.error('ChartExporter: Plot data is required for CSV/JSON export and was not provided.');
                    throw new Error('Plot data not available for CSV/JSON export.');
                }
                if (format === 'csv') {
                    // Simplified CSV export: assumes first trace, x and y arrays
                    const trace = plotData[0];
                    if (!trace.x || !trace.y || !Array.isArray(trace.x) || !Array.isArray(trace.y)) {
                        throw new Error('CSV export requires x and y array data in the first trace.');
                    }
                    let csvContent = `${trace.name || 'X-Axis'},${trace.name || 'Y-Axis'}\n`; // Crude header
                    trace.x.forEach((val: any, index: number) => {
                        csvContent += `${val},${(trace.y as any[])[index]}\n`;
                    });
                    const encodedUri = encodeURI(`data:text/csv;charset=utf-8,${csvContent}`);
                    const csvLink = document.createElement("a");
                    csvLink.setAttribute("href", encodedUri);
                    csvLink.setAttribute("download", `${filename}.csv`);
                    document.body.appendChild(csvLink);
                    csvLink.click();
                    document.body.removeChild(csvLink);
                } else { // JSON
                    const jsonContent = JSON.stringify({ data: plotData, layout: graphDiv ? (graphDiv as any).layout : {} }, null, 2);
                    const encodedUriJson = encodeURI(`data:application/json;charset=utf-8,${jsonContent}`);
                    const jsonLink = document.createElement("a");
                    jsonLink.setAttribute("href", encodedUriJson);
                    jsonLink.setAttribute("download", `${filename}.json`);
                    document.body.appendChild(jsonLink);
                    jsonLink.click();
                    document.body.removeChild(jsonLink);
                }
                break;
            default:
                console.warn(`ChartExporter: Unsupported export format: ${format}`);
                throw new Error(`Unsupported format: ${format}`);
        }
    } catch (error) {
        console.error(`ChartExporter: Failed to export chart as ${format}.`, error);
        throw error; // Re-throw for the caller to handle
    }
};

// Example usage (would be inside a component that has a PlotlyChart):
// const MyChartComponent = () => {
//   const chartRef = useRef<PlotlyHTMLElement | null>(null);
//   const chartData = [{ x: [1,2,3], y: [2,4,3], type: 'scatter' }];
//
//   const handleExportClick = (format) => {
//     exportChart(chartRef, format, 'my-cool-chart', chartData)
//       .then(() => console.log('Export successful'))
//       .catch(err => console.error('Export failed:', err));
//   };
//
//   return (
//     <>
//       <PlotlyChart data={chartData} ref={chartRef} />
//       <Button onClick={() => handleExportClick('png')}>Export PNG</Button>
//       <Button onClick={() => handleExportClick('csv')}>Export CSV</Button>
//     </>
//   );
// };
