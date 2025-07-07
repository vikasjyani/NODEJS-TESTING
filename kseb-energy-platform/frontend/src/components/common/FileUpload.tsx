import React, { useState, useCallback, useRef, useMemo } from 'react';
import {
  Box, Typography, Button, LinearProgress, Alert, Chip,
  IconButton, List, ListItem, ListItemText, ListItemAvatar, Avatar,
  Dialog, DialogTitle, DialogContent, DialogActions, Paper, Tooltip, Link, CircularProgress
} from '@mui/material';
import {
  CloudUpload, Delete, CheckCircle, ErrorOutline as ErrorIcon, WarningAmber, // Changed from Warning due to potential name clash
  InsertDriveFile, Description, Image as ImageIcon, BrokenImage, Cancel
} from '@mui/icons-material';
import { useDropzone, FileRejection, Accept as DropzoneAccept } from 'react-dropzone'; // Accept type from react-dropzone
// import { useUploadFileMutation } from '../../store/api/apiSlice'; // If using RTK for upload

export interface UploadedFileMeta {
  file: File;
  id: string; // Unique ID for this upload instance
  status: 'pending' | 'validating' | 'uploading' | 'success' | 'error' | 'cancelled';
  progress?: number; // 0-100 for uploading
  error?: string; // Error message
  previewUrl?: string; // For image previews
  serverFilePath?: string; // Path after successful upload to server
  validationResult?: any; // Result from server-side validation
}

// Props for the component
interface FileUploadProps {
  accept?: DropzoneAccept; // Uses react-dropzone's Accept type e.g. {'image/*': ['.png', '.jpg']}
  maxSize?: number; // in bytes
  maxFiles?: number;
  multiple?: boolean;
  onFilesProcess: (processedFiles: UploadedFileMeta[]) => void; // Callback when files are selected and initially processed (validated client-side)
  onUploadComplete?: (successfulUploads: UploadedFileMeta[], failedUploads: UploadedFileMeta[]) => void; // Callback after all attempts
  // If using a specific upload function (e.g., RTK Query mutation hook)
  // uploadFunction?: (file: File, fileType: string) => Promise<{success: boolean, filePath?: string, message?: string, validation?: any}>;
  // fileTypeForUpload?: string; // To pass to uploadFunction
  title?: string;
  description?: string;
  disabled?: boolean;
  showPreview?: boolean; // For image files
  dropzoneHeight?: number | string;
  compact?: boolean; // For a smaller version
}

const DEFAULT_MAX_SIZE_BYTES = 16 * 1024 * 1024; // 16MB

export const FileUpload: React.FC<FileUploadProps> = ({
  accept = { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'], 'application/vnd.ms-excel': ['.xls'], 'text/csv': ['.csv'] },
  maxSize = DEFAULT_MAX_SIZE_BYTES,
  maxFiles = 5, // Allow multiple files by default, can be set to 1
  multiple = true, // Corresponds to maxFiles > 1
  onFilesProcess,
  onUploadComplete,
  // uploadFunction,
  // fileTypeForUpload = 'generic_upload',
  title = 'Upload Files',
  description, // Default description handled dynamically
  disabled = false,
  showPreview = true,
  dropzoneHeight = 150,
  compact = false,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileMeta[]>([]);
  const [isGloballyUploading, setIsGloballyUploading] = useState<boolean>(false); // If one button uploads all
  const [previewFile, setPreviewFile] = useState<UploadedFileMeta | null>(null);

  const activeUploadControllers = useRef<Map<string, AbortController>>(new Map());


  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const getFileIcon = (fileType?: string): React.ReactElement => {
    const type = fileType?.toLowerCase() || '';
    if (type.startsWith('image/')) return <ImageIcon color="primary" />;
    if (type.includes('excel') || type.includes('spreadsheetml')) return <Description sx={{color: 'success.main'}} />;
    if (type.includes('csv')) return <Description sx={{color: 'info.main'}} />;
    if (type.includes('pdf')) return <Description color="error" />; // Example
    return <InsertDriveFile color="action" />;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const defaultDescription = useMemo(() => {
      const acceptedExtensions = Object.values(accept || {}).flat().join(', ');
      return description || `Drag & drop files here, or click. Accepted: ${acceptedExtensions || 'any type'}. Max ${maxFiles} file(s), ${formatFileSize(maxSize)}/file.`;
  }, [accept, description, maxFiles, maxSize]);


  const processDroppedFiles = useCallback(async (acceptedDropFiles: File[], fileRejections: FileRejection[]) => {
    const currentFileIds = new Set(uploadedFiles.map(f => f.id));
    let newProcessedFiles: UploadedFileMeta[] = [];

    fileRejections.forEach(rejection => {
      const id = generateFileId();
      // Check if we already have an error entry for this conceptual file (e.g. from previous drop attempt)
      // This part is tricky without stable file IDs from browser before selection.
      // For simplicity, we'll add a new error entry.
      newProcessedFiles.push({
        file: rejection.file, // File object is available
        id,
        status: 'error',
        error: `${rejection.errors[0].message} (Code: ${rejection.errors[0].code})`,
        previewUrl: (showPreview && rejection.file.type.startsWith('image/')) ? URL.createObjectURL(rejection.file) : undefined,
      });
    });

    acceptedDropFiles.forEach(file => {
      const id = generateFileId();
      newProcessedFiles.push({
        file,
        id,
        status: 'pending', // Pending client-side validation or direct upload
        previewUrl: (showPreview && file.type.startsWith('image/')) ? URL.createObjectURL(file) : undefined,
      });
    });

    // Filter out if maxFiles would be exceeded by new additions
    const totalAfterAdd = uploadedFiles.length + newProcessedFiles.filter(f=>f.status !== 'error').length;
    if (totalAfterAdd > maxFiles && maxFiles > 0) {
        const limitErrorFile: UploadedFileMeta = {
            file: new File([], "limit_error.txt"), // Dummy file
            id: generateFileId(),
            status: 'error',
            error: `Cannot add more files. Maximum ${maxFiles} allowed. Already have ${uploadedFiles.length}.`,
        };
        // Add one error message for the batch that exceeded limit
        newProcessedFiles = [limitErrorFile, ...newProcessedFiles.filter(f => f.status === 'error')];
    } else {
        // If within limits, update the main list
        setUploadedFiles(prev => [...prev, ...newProcessedFiles]);
    }
    onFilesProcess([...uploadedFiles, ...newProcessedFiles]); // Notify parent about all files

  }, [uploadedFiles, maxFiles, onFilesProcess, showPreview]);

  const { getRootProps, getInputProps, isDragActive, isFocused, isDragAccept, isDragReject } = useDropzone({
    onDrop: processDroppedFiles,
    accept,
    maxSize,
    maxFiles: multiple ? maxFiles : 1, // react-dropzone maxFiles applies to a single drop operation
    multiple,
    disabled: disabled || isGloballyUploading,
  });

  const borderColor = isDragAccept ? 'success.main'
                    : isDragReject ? 'error.main'
                    : isFocused ? 'primary.main'
                    : 'divider';

  const removeFile = (fileId: string) => {
    const fileToRemove = uploadedFiles.find(f => f.id === fileId);
    if (fileToRemove?.previewUrl) {
      URL.revokeObjectURL(fileToRemove.previewUrl);
    }
    // Cancel ongoing upload if any for this file
    activeUploadControllers.current.get(fileId)?.abort();
    activeUploadControllers.current.delete(fileId);

    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const cancelUpload = (fileId: string) => {
    activeUploadControllers.current.get(fileId)?.abort();
    setUploadedFiles(prev => prev.map(f => f.id === fileId && f.status === 'uploading' ? {...f, status: 'cancelled', progress: 0} : f));
  };


  // SIMULATED UPLOAD ALL FUNCTION - Replace with actual backend calls
  const handleUploadAllPending = async () => {
    setIsGloballyUploading(true);
    const pendingFiles = uploadedFiles.filter(f => f.status === 'pending' || f.status === 'validating');
    let successful: UploadedFileMeta[] = [];
    let failed: UploadedFileMeta[] = [];

    for (const currentFile of pendingFiles) {
      const controller = new AbortController();
      activeUploadControllers.current.set(currentFile.id, controller);

      setUploadedFiles(prev => prev.map(f => f.id === currentFile.id ? { ...f, status: 'uploading', progress: 0, error: undefined } : f));

      try {
        // Simulate upload progress
        for (let p = 0; p <= 100; p += 20) {
          if (controller.signal.aborted) throw new Error('Upload cancelled by user.');
          await new Promise(res => setTimeout(res, 200)); // Simulate network latency
          setUploadedFiles(prev => prev.map(f => f.id === currentFile.id ? { ...f, progress: p } : f));
        }

        // Simulate server response
        const serverResponse = { success: Math.random() > 0.2, filePath: `/uploads/${currentFile.file.name}`, message: "Uploaded successfully (simulated)" };

        if (controller.signal.aborted) throw new Error('Upload cancelled by user.');

        if (serverResponse.success) {
          const updatedFile: UploadedFileMeta = {...currentFile, status: 'success', serverFilePath: serverResponse.filePath, progress: 100};
          setUploadedFiles(prev => prev.map(f => f.id === currentFile.id ? updatedFile : f));
          successful.push(updatedFile);
        } else {
          throw new Error(serverResponse.message || "Simulated server upload error.");
        }
      } catch (err: any) {
        const errorMsg = err.message === 'Upload cancelled by user.' ? err.message : `Upload failed: ${err.message}`;
        const finalStatus = err.message === 'Upload cancelled by user.' ? 'cancelled' : 'error';
        const updatedFile: UploadedFileMeta = {...currentFile, status: finalStatus, error: errorMsg, progress: 0};
        setUploadedFiles(prev => prev.map(f => f.id === currentFile.id ? updatedFile : f));
        failed.push(updatedFile);
      } finally {
         activeUploadControllers.current.delete(currentFile.id);
      }
    }
    setIsGloballyUploading(false);
    onUploadComplete?.(successful, failed);
  };

  const pendingFileCount = uploadedFiles.filter(f => f.status === 'pending' || f.status === 'validating').length;

  return (
    <Box>
      {!compact && <Typography variant="h6" gutterBottom>{title}</Typography>}
      <Paper
        {...getRootProps()}
        variant="outlined"
        sx={{
          p: compact ? 1.5 : 3,
          minHeight: compact? 'auto' : dropzoneHeight,
          textAlign: 'center',
          cursor: disabled || isGloballyUploading ? 'default' : 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'transparent',
          borderColor: borderColor,
          borderWidth: 2,
          borderStyle: 'dashed',
          borderRadius: 1,
          opacity: disabled || isGloballyUploading ? 0.6 : 1,
          transition: 'border .2s ease-in-out, background-color .2s ease-in-out',
          display: 'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
          '&:hover': { borderColor: disabled || isGloballyUploading ? borderColor : 'primary.light' }
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: compact ? 32 : 48, color: 'primary.main', mb: compact ? 0.5 : 1 }} />
        <Typography variant={compact ? "body2" : "h6"} gutterBottom={!compact}>
          {isDragActive ? 'Drop files here...' : (compact ? "Select or Drop" : "Select or Drop Files")}
        </Typography>
        {!compact && <Typography variant="caption" color="textSecondary">{defaultDescription}</Typography>}
      </Paper>

      {uploadedFiles.length > 0 && (
        <Box sx={{ mt: compact ? 1 : 2 }}>
          {!compact && <Typography variant="subtitle1" gutterBottom>Selected Files ({uploadedFiles.length}/{maxFiles})</Typography>}
          <List dense={compact}>
            {uploadedFiles.map((upFile) => (
              <ListItem
                key={upFile.id}
                divider
                sx={{bgcolor: 'background.paper', mb:0.5, borderRadius:1,
                     borderLeft: 5,
                     borderColor: upFile.status === 'success' ? 'success.main' : upFile.status === 'error' ? 'error.main' : upFile.status === 'cancelled' ? 'warning.main' : 'divider'
                }}
                secondaryAction={
                  <IconButton edge="end" onClick={() => removeFile(upFile.id)} size="small" disabled={upFile.status === 'uploading'}>
                    <Delete fontSize="small"/>
                  </IconButton>
                }
              >
                <ListItemAvatar sx={{minWidth: 32}}>
                  <Avatar sx={{width: 28, height: 28, bgcolor: 'transparent'}}>
                    {upFile.previewUrl && showPreview ? (
                      <Tooltip title="Preview image">
                        <img src={upFile.previewUrl} alt="preview" style={{ width: '100%', height: '100%', objectFit: 'cover', cursor:'pointer' }} onClick={() => setPreviewFile(upFile)} />
                      </Tooltip>
                    ) : getFileIcon(upFile.file.type)}
                  </Avatar>
                </ListItemAvatar>
                <ListItemText
                  primary={<Tooltip title={upFile.file.name}><Typography variant="body2" noWrap sx={{maxWidth: compact ? 100: 200}}>{upFile.file.name}</Typography></Tooltip>}
                  secondary={
                    <Box>
                        <Typography variant="caption" color="textSecondary">
                            {formatFileSize(upFile.file.size)} - Status: <Chip label={upFile.status} size="small" color={
                                upFile.status === 'success' ? 'success' : upFile.status === 'error' ? 'error' : upFile.status === 'uploading' ? 'info' : upFile.status === 'cancelled' ? 'warning' : 'default'
                            } sx={{height:18, fontSize:'0.7rem'}}/>
                        </Typography>
                        {upFile.status === 'uploading' && upFile.progress !== undefined && (
                            <Box sx={{display:'flex', alignItems:'center'}}>
                                <LinearProgress variant="determinate" value={upFile.progress} sx={{ width: 'calc(100% - 40px)', mr: 1, height:6, borderRadius:1 }} />
                                <Typography variant="caption">{`${upFile.progress}%`}</Typography>
                                <Tooltip title="Cancel Upload">
                                    <IconButton onClick={() => cancelUpload(upFile.id)} size="small" sx={{ml:0.5, p:0.2}}><Cancel fontSize="small"/></IconButton>
                                </Tooltip>
                            </Box>
                        )}
                        {upFile.error && <Typography variant="caption" color="error.main" display="block">{upFile.error}</Typography>}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {pendingFileCount > 0 && (
        <Box sx={{mt:2, display:'flex', justifyContent:'flex-end'}}>
            <Button
                variant="contained"
                onClick={handleUploadAllPending}
                disabled={isGloballyUploading}
                startIcon={isGloballyUploading ? <CircularProgress size={20} color="inherit"/> : <CloudUpload/>}
            >
                {isGloballyUploading ? 'Uploading...' : `Upload ${pendingFileCount} Pending File(s)`}
            </Button>
        </Box>
      )}

      <Dialog open={Boolean(previewFile)} onClose={() => setPreviewFile(null)} maxWidth="md" fullWidth>
        <DialogTitle>Preview: {previewFile?.file.name}</DialogTitle>
        <DialogContent sx={{display:'flex', justifyContent:'center', alignItems:'center'}}>
          {previewFile?.previewUrl ? (
            <img src={previewFile.previewUrl} alt={previewFile.file.name} style={{ maxWidth: '100%', maxHeight: '70vh', objectFit: 'contain' }} />
          ) : (
            <Box sx={{textAlign:'center', p:3}}><BrokenImage sx={{fontSize:60, color:'text.disabled'}}/></Box>
          )}
        </DialogContent>
        <DialogActions><Button onClick={() => setPreviewFile(null)}>Close</Button></DialogActions>
      </Dialog>
    </Box>
  );
};
