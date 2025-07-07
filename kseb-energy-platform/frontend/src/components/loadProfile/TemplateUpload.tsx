import React, { useState, useCallback } from 'react';
import { Box, Typography, Button, Alert, List, ListItem, ListItemText, ListItemIcon, Paper, CircularProgress } from '@mui/material';
import { CloudUpload, CheckCircleOutline, ErrorOutline, Description } from '@mui/icons-material';
import { useDropzone, FileRejection, Accept } from 'react-dropzone';
import { GenerationMethod } from './MethodSelection'; // Assuming this defines method details
// import { useUploadFileMutation } from '../../store/api/apiSlice'; // If using RTK Query for actual upload

interface TemplateUploadProps {
  method?: GenerationMethod | null; // To determine if upload is needed/what types
  onDataUploaded: (fileUploaded: boolean, filePath?: string, validationResult?: any) => void; // Callback with status and optional path/validation
  // uploadFunction?: ReturnType<typeof useUploadFileMutation>[0]; // Pass the mutation trigger
  maxFileSize?: number; // in bytes, e.g., 5 * 1024 * 1024 for 5MB
}

const DEFAULT_MAX_SIZE = 10 * 1024 * 1024; // 10MB

export const TemplateUpload: React.FC<TemplateUploadProps> = ({
  method,
  onDataUploaded,
  // uploadFunction,
  maxFileSize = DEFAULT_MAX_SIZE,
}) => {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false); // For async upload simulation/actual

  // Define accepted file types based on method or globally
  const acceptedFileTypes: Accept = method?.id === 'custom_template_method'
    ? {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'application/vnd.ms-excel': ['.xls'],
        'text/csv': ['.csv'],
      }
    : { /* More generic if needed, or empty if no upload for this step */ };

  const onDrop = useCallback(async (acceptedFiles: File[], fileRejections: FileRejection[]) => {
    setUploadError(null);
    setUploadedFile(null);

    if (fileRejections.length > 0) {
      const rejectionError = fileRejections[0].errors[0];
      setUploadError(`File Error: ${rejectionError.message} (Code: ${rejectionError.code})`);
      onDataUploaded(false, undefined, { error: rejectionError.message });
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setUploadedFile(file);
      setIsUploading(true); // Simulate or start actual upload

      // Simulate backend validation/upload or call actual upload function
      // if (uploadFunction) {
      //   try {
      //     const formData = new FormData();
      //     formData.append('file', file);
      //     formData.append('type', `loadprofile_template_${method?.id || 'generic'}`);
      //     const result = await uploadFunction(formData).unwrap();
      //     setIsUploading(false);
      //     if (result.success && result.filePath) {
      //       onDataUploaded(true, result.filePath, result.validation);
      //       setUploadError(null); // Clear previous errors
      //     } else {
      //       setUploadError(result.message || 'Upload failed or validation issues.');
      //       onDataUploaded(false, undefined, { error: result.message });
      //     }
      //   } catch (err: any) {
      //     setIsUploading(false);
      //     setUploadError(err.data?.message || err.message || 'Upload request failed.');
      //     onDataUploaded(false, undefined, { error: err.data?.message || err.message });
      //   }
      // } else {
        // Simulate local "upload" and validation for now
        setTimeout(() => {
          setIsUploading(false);
          // Mock validation success
          onDataUploaded(true, file.name, { valid: true, message: "File appears valid." });
          setUploadError(null);
        }, 1500);
      // }
    }
  }, [onDataUploaded, maxFileSize, method/*, uploadFunction*/]);

  const { getRootProps, getInputProps, isDragActive, isFocused, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: acceptedFileTypes,
    maxFiles: 1,
    maxSize: maxFileSize,
    multiple: false,
    disabled: isUploading,
  });

  const borderColor = isDragAccept ? '#00e676' // green
                    : isDragReject ? '#ff1744' // red
                    : isFocused ? '#2196f3' // blue
                    : 'grey.400';

  if (!method || !method.requiresTemplateUpload) {
    return (
      <Alert severity="info" sx={{mt:1}}>
        No specific data upload required for the '{method?.name || 'selected'}' method using default inputs. You can proceed to the next step.
        {/* Optionally, still allow upload for overriding defaults */}
        <Button onClick={() => onDataUploaded(false)} sx={{ml:2}}>Skip Upload</Button>
      </Alert>
    );
  }

  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Upload Load Profile Template (for {method.name})
      </Typography>
      <Paper
        {...getRootProps()}
        variant="outlined"
        sx={{
          p: 3,
          textAlign: 'center',
          cursor: isUploading ? 'default' : 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          borderColor: borderColor,
          borderWidth: 2,
          borderStyle: 'dashed',
          opacity: isUploading ? 0.7 : 1,
          transition: 'border .24s ease-in-out, background-color .24s ease-in-out',
          '&:hover': { borderColor: isUploading ? borderColor : 'primary.main' }
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
        {isDragActive ? (
          <Typography>Drop the template file here...</Typography>
        ) : (
          <Typography>Drag 'n' drop a template file here, or click to select.
            <br/>
            <Typography variant="caption" color="textSecondary">
                (Accepted: .xlsx, .xls, .csv; Max size: {maxFileSize / (1024*1024)}MB)
            </Typography>
          </Typography>
        )}
      </Paper>

      {isUploading && <CircularProgress sx={{mt:2}}/>}

      {uploadError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {uploadError}
        </Alert>
      )}

      {uploadedFile && !isUploading && !uploadError && (
        <Alert severity="success" sx={{ mt: 2 }} icon={<CheckCircleOutline fontSize="inherit" />}>
          File '{uploadedFile.name}' selected and appears valid.
        </Alert>
      )}

      {uploadedFile && (
         <List dense sx={{mt:1, bgcolor: 'background.paper', borderRadius:1, border: '1px solid', borderColor: 'divider'}}>
            <ListItem>
                <ListItemIcon><Description /></ListItemIcon>
                <ListItemText
                    primary={uploadedFile.name}
                    secondary={`${(uploadedFile.size / 1024).toFixed(2)} KB`}
                />
            </ListItem>
         </List>
      )}

      <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
            onClick={() => onDataUploaded(!!uploadedFile && !uploadError, uploadedFile?.name)}
            disabled={isUploading || (!uploadedFile && method.requiresTemplateUpload) || !!uploadError}
            variant="contained"
        >
          Confirm Data & Proceed
        </Button>
      </Box>
    </Box>
  );
};
