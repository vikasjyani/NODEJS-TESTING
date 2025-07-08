import React, { useState, useCallback } from 'react';
import { Box, Button, Typography, Alert, CircularProgress, Tooltip, Paper, IconButton } from '@mui/material'; // Added Paper, IconButton
import { FileUpload as FileUploadIcon, SettingsApplications, HelpOutline } from '@mui/icons-material';
import { useDropzone, FileRejection, Accept } from 'react-dropzone';
// import * as XLSX from 'xlsx'; // Consider adding xlsx library if parsing is done client-side

import { PyPSAModelConfiguration } from '../../pages/PyPSAModeling'; // Adjust path as needed

interface ExcelSettingsLoaderProps {
  onSettingsLoaded: (settings: Partial<PyPSAModelConfiguration>) => void; // Callback with parsed settings
  // If upload to backend for parsing:
  // onUploadForParsing?: (file: File) => Promise<Partial<PyPSAModelConfiguration>>;
}

const acceptedFileTypes: Accept = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
};
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB limit for settings file

export const ExcelSettingsLoader: React.FC<ExcelSettingsLoaderProps> = ({
    onSettingsLoaded,
    // onUploadForParsing
}) => {
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Placeholder for client-side parsing logic (complex)
  // For a robust solution, backend parsing is often preferred for Excel.
  const parseExcelClientSide = (file: File): Promise<Partial<PyPSAModelConfiguration>> => {
    return new Promise((resolve, reject) => {
      // This is a very simplified placeholder. Real Excel parsing is complex.
      // Using a library like 'xlsx' or 'exceljs' would be necessary.
      // Example:
      // const reader = new FileReader();
      // reader.onload = (e) => {
      //   try {
      //     const data = e.target?.result;
      //     const workbook = XLSX.read(data, { type: 'binary' });
      //     const sheetName = workbook.SheetNames[0]; // Assume settings are on the first sheet
      //     const worksheet = workbook.Sheets[sheetName];
      //     const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
            //     // Now, map jsonData (array of arrays) to PyPSAModelConfiguration structure
            //     // This mapping logic would be highly specific to the Excel template format.
            //     const parsedSettings: Partial<PyPSAModelConfiguration> = {};
            //     // ... parsing logic ...
            //     resolve(parsedSettings);
      //   } catch (parseError) {
      //     reject(new Error('Failed to parse Excel file. Ensure it follows the expected format.'));
      //   }
      // };
      // reader.onerror = () => reject(new Error('Failed to read file.'));
      // reader.readAsBinaryString(file);

      // --- SIMULATED PARSING ---
      console.warn("Client-side Excel parsing is complex and only simulated here.");
      if (file.name.toLowerCase().includes("error")) {
        reject(new Error("Simulated parsing error: Invalid Excel format."));
        return;
      }
      const mockSettings: Partial<PyPSAModelConfiguration> = {
        scenario_name: `FromExcel_${file.name.split('.')[0]}`,
        base_year: 2025,
        investment_mode: 'multi_year',
        solver_options: { solver: 'gurobi', optimality_gap: 0.005 },
        input_file: "data/network_template_from_excel.xlsx" // Example path specified in Excel
      };
      resolve(mockSettings);
      // --- END SIMULATION ---
    });
  };


  const onDrop = useCallback(async (acceptedFiles: File[], fileRejections: FileRejection[]) => {
    setError(null);
    setFileName(null);

    if (fileRejections.length > 0) {
      setError(`File error: ${fileRejections[0].errors[0].message}`);
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setFileName(file.name);
      setIsLoading(true);

      try {
        // Option 1: Client-side parsing (complex, placeholder used)
        const settings = await parseExcelClientSide(file);
        onSettingsLoaded(settings);
        setError(null); // Clear previous error

        // Option 2: Upload to backend for parsing (if onUploadForParsing is provided)
        // if (onUploadForParsing) {
        //   const settings = await onUploadForParsing(file);
        //   onSettingsLoaded(settings);
        // } else {
        //   // Fallback or error if no parsing mechanism
        //   throw new Error("No parsing mechanism provided for Excel settings.");
        // }
      } catch (err: any) {
        setError(err.message || 'Failed to load settings from Excel.');
      } finally {
        setIsLoading(false);
      }
    }
  }, [onSettingsLoaded /*, onUploadForParsing*/]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxFiles: 1,
    maxSize: MAX_FILE_SIZE,
    multiple: false,
    disabled: isLoading,
  });

  return (
    <Box sx={{ my: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', mb:1 }}>
        Load Configuration from Excel File
        <Tooltip title="Upload an Excel file (.xlsx, .xls) containing pre-defined PyPSA model settings. This can quickly populate common configuration fields.">
          <IconButton size="small" sx={{ml:0.5}}><HelpOutline fontSize="small"/></IconButton>
        </Tooltip>
      </Typography>
      <Paper
        {...getRootProps()}
        variant="outlined"
        sx={{
          p: 1.5,
          textAlign: 'center',
          cursor: isLoading ? 'default' : 'pointer',
          backgroundColor: isDragActive ? 'action.selected' : 'transparent',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          borderStyle: 'dashed',
          opacity: isLoading ? 0.7 : 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 60,
          transition: 'border .2s, background-color .2s',
          '&:hover': { borderColor: isLoading ? 'divider' : 'primary.light' }
        }}
      >
        <input {...getInputProps()} />
        {isLoading ? (
          <CircularProgress size={24} sx={{mr:1}}/>
        ) : (
          <SettingsApplications color="action" sx={{ mr: 1 }} />
        )}
        <Typography variant="body2" color={isDragActive ? "primary" : "text.secondary"}>
          {isDragActive ? 'Drop Excel settings file here...' :
           fileName ? `File: ${fileName}` : 'Click or Drag & Drop Excel Settings File'}
        </Typography>
      </Paper>
      {error && <Alert severity="error" sx={{ mt: 1, fontSize: '0.8rem' }}>{error}</Alert>}
    </Box>
  );
};
