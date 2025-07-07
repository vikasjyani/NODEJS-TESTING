import { Column } from '../components/common/DataTable'; // Assuming DataTable defines Column type

/**
 * Converts an array of objects to a CSV string.
 * @param data Array of data objects.
 * @param columns Array of Column definitions to determine order and headers.
 * @returns A string in CSV format.
 */
export const convertToCSV = <T extends Record<string, any>>(data: T[], columns: Column<T>[]): string => {
  if (!data || data.length === 0 || !columns || columns.length === 0) {
    return '';
  }

  const headers = columns.map(col => col.label || String(col.id));
  const rows = data.map(row =>
    columns.map(col => {
      const value = row[col.id as keyof T];
      let formattedValue = '';
      if (col.format) {
        // Try to get a string representation if format returns ReactNode
        const formatted = col.format(value, row);
        if (typeof formatted === 'string' || typeof formatted === 'number' || typeof formatted === 'boolean') {
          formattedValue = String(formatted);
        } else {
          // Fallback for ReactNode - might just take the raw value or a placeholder
          formattedValue = String(value ?? '');
        }
      } else {
        formattedValue = String(value ?? '');
      }
      // Escape commas and newlines within a cell value
      return `"${formattedValue.replace(/"/g, '""')}"`;
    }).join(',')
  );

  return [headers.join(','), ...rows].join('\n');
};

/**
 * Triggers a download of the provided content.
 * @param content The string content to download.
 * @param filename The desired filename for the download.
 * @param contentType The MIME type of the content.
 */
export const triggerDownload = (content: string, filename: string, contentType: string): void => {
  const blob = new Blob([content], { type: contentType });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
};


/**
 * Exports data to CSV and triggers download.
 * @param data Array of data objects.
 * @param columns Array of Column definitions.
 * @param filename Desired filename without extension.
 */
export const exportDataToCSV = <T extends Record<string, any>>(data: T[], columns: Column<T>[], filename: string): void => {
  const csvString = convertToCSV(data, columns);
  triggerDownload(csvString, `${filename}.csv`, 'text/csv;charset=utf-8;');
};

/**
 * Exports data to JSON and triggers download.
 * @param data Array of data objects.
 * @param filename Desired filename without extension.
 */
export const exportDataToJSON = <T extends Record<string, any>>(data: T[], filename: string): void => {
  const jsonString = JSON.stringify(data, null, 2); // Pretty print JSON
  triggerDownload(jsonString, `${filename}.json`, 'application/json;charset=utf-8;');
};


// Placeholder for Excel export - usually requires a library like 'xlsx' or 'exceljs'
/**
 * Exports data to Excel (XLSX) format.
 * This is a placeholder and would require an Excel library.
 * @param data Array of data objects.
 * @param columns Array of Column definitions.
 * @param filename Desired filename without extension.
 */
export const exportDataToExcel = async <T extends Record<string, any>>(data: T[], columns: Column<T>[], filename: string): Promise<void> => {
  console.warn("Excel export functionality requires an external library like 'xlsx' or 'exceljs'. This is a placeholder.");

  // Dynamically import xlsx library if you want to keep it optional
  try {
    const XLSX = await import('xlsx'); // npm install xlsx --save

    const headers = columns.map(col => col.label || String(col.id));
    const dataForSheet = data.map(row =>
      columns.map(col => {
        const value = row[col.id as keyof T];
        if (col.format) {
          const formatted = col.format(value, row);
          return (typeof formatted === 'string' || typeof formatted === 'number' || typeof formatted === 'boolean') ? formatted : value;
        }
        return value;
      })
    );

    const ws = XLSX.utils.aoa_to_sheet([headers, ...dataForSheet]);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, `${filename}.xlsx`);

  } catch (error) {
    console.error("Failed to load or use XLSX library for Excel export:", error);
    alert("Excel export functionality is not fully available. Please try CSV or JSON.");
    // Fallback or simple alert
    const csvString = convertToCSV(data, columns);
    alert("Excel library not found. Here's the data as CSV instead:\n\n" + csvString.substring(0, 500) + (csvString.length > 500 ? "..." : ""));
  }
};

// Main export handler that can be called from DataTable
export const handleTableExport = <T extends Record<string, any>>(
    format: 'csv' | 'excel' | 'json',
    data: T[],
    columns: Column<T>[],
    filename: string = 'table_export'
) => {
    switch(format) {
        case 'csv':
            exportDataToCSV(data, columns, filename);
            break;
        case 'json':
            exportDataToJSON(data, filename);
            break;
        case 'excel':
            exportDataToExcel(data, columns, filename);
            break;
        default:
            console.warn(`Unsupported export format: ${format}`);
    }
};
