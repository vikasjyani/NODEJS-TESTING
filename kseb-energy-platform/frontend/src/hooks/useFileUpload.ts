import { useState, useCallback } from 'react';
import { FileRejection } from 'react-dropzone';
import { validateFile, FileValidationOptions, FileValidationResult } from '../components/common/FileValidator'; // Adjust path

export interface UploadableFile {
  id: string; // Unique client-side ID for the file instance
  file: File;
  status: 'pending' | 'validating' | 'ready' | 'uploading' | 'success' | 'error' | 'cancelled';
  progress?: number; // Upload progress 0-100
  error?: string; // Error message if any phase fails
  previewUrl?: string; // For image previews
  serverFilePath?: string; // Path on server after successful upload
  validationResult?: FileValidationResult; // Result of client-side validation
}

interface UseFileUploadOptions {
  initialFiles?: UploadableFile[];
  validationOptions?: FileValidationOptions;
  maxFiles?: number;
  // uploadHandler: (file: File, onProgress: (percent: number) => void, signal: AbortSignal) => Promise<{ success: boolean; filePath?: string; message?: string }>;
  // For this hook, we'll make uploadHandler optional and focus on selection/validation first.
  // If an uploadHandler is provided, the hook can manage the full upload lifecycle.
}

const generateId = () => `uploadable_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;

export const useFileUpload = (options: UseFileUploadOptions = {}) => {
  const { initialFiles = [], validationOptions = {}, maxFiles = 1 } = options;
  const [files, setFiles] = useState<UploadableFile[]>(initialFiles);
  const [isGlobalUploading, setIsGlobalUploading] = useState<boolean>(false); // Tracks if any file is currently being uploaded by the hook's own upload function
  const abortControllers = new Map<string, AbortController>();


  const addFiles = useCallback(async (acceptedDropFiles: File[], fileRejections: FileRejection[]) => {
    const newUploadables: UploadableFile[] = [];

    // Handle rejected files first
    fileRejections.forEach(rejection => {
      newUploadables.push({
        id: generateId(),
        file: rejection.file as File, // Cast to File
        status: 'error',
        error: `${rejection.errors[0].message} (Code: ${rejection.errors[0].code})`,
        previewUrl: rejection.file.type.startsWith('image/') ? URL.createObjectURL(rejection.file) : undefined,
        validationResult: {
            isValid: false,
            errors: [rejection.errors[0].message],
            fileName: rejection.file.name,
            fileSize: rejection.file.size,
            fileType: rejection.file.type
        }
      });
    });

    // Process accepted files
    for (const file of acceptedDropFiles) {
      if (files.length + newUploadables.filter(f=>f.status !== 'error').length >= maxFiles && maxFiles > 0) {
        if (!newUploadables.find(f => f.error?.includes("Maximum files exceeded"))) {
            newUploadables.push({
                id: generateId(),
                file: new File([], "limit_error.txt"),
                status: 'error',
                error: `Maximum ${maxFiles} file(s) allowed.`,
            });
        }
        break;
      }

      const id = generateId();
      const initialUploadable: UploadableFile = {
        id,
        file: file as File, // Cast to File
        status: 'validating',
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      };
      newUploadables.push(initialUploadable);
    }

    setFiles(prev => [...prev, ...newUploadables]);

    // Perform client-side validation for newly added 'validating' files
    for (const upFile of newUploadables) {
      if (upFile.status === 'validating') {
        const validationRes = await validateFile(upFile.file, validationOptions);
        setFiles(prev => prev.map(f => f.id === upFile.id ? {
          ...f,
          status: validationRes.isValid ? 'ready' : 'error', // Ready for upload or error
          error: validationRes.isValid ? undefined : validationRes.errors.join('; '),
          validationResult: validationRes,
        } : f));
      }
    }
  }, [files, maxFiles, validationOptions]);


  const removeFile = useCallback((fileId: string) => {
    setFiles(prevFiles => {
      const fileToRemove = prevFiles.find(f => f.id === fileId);
      if (fileToRemove?.previewUrl) {
        URL.revokeObjectURL(fileToRemove.previewUrl);
      }
      // Cancel any ongoing upload for this file
      const controller = abortControllers.get(fileId);
      controller?.abort();
      abortControllers.delete(fileId);
      return prevFiles.filter(f => f.id !== fileId);
    });
  }, [abortControllers]);

  const clearAllFiles = useCallback(() => {
    files.forEach(f => {
      if (f.previewUrl) URL.revokeObjectURL(f.previewUrl);
      abortControllers.get(f.id)?.abort();
    });
    abortControllers.clear();
    setFiles([]);
  }, [files, abortControllers]);

  // Placeholder for an actual upload function that would be passed or defined here
  // This function would typically use `fetch` or an RTK Query mutation
  const startUpload = useCallback(async (
    fileToUpload: UploadableFile,
    uploadHandler: (file: File, onProgress: (percent: number) => void, signal: AbortSignal) => Promise<{ success: boolean; filePath?: string; message?: string }>
    ) => {
    if (fileToUpload.status !== 'ready' && fileToUpload.status !== 'error') { // Allow retry on error
        console.warn(`File ${fileToUpload.file.name} is not ready for upload or already processed.`);
        return;
    }

    const controller = new AbortController();
    abortControllers.set(fileToUpload.id, controller);
    setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'uploading', progress: 0, error: undefined } : f));
    setIsGlobalUploading(true);

    try {
      const result = await uploadHandler(
        fileToUpload.file,
        (percent: number) => {
          setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, progress: percent } : f));
        },
        controller.signal
      );

      if (controller.signal.aborted) {
         setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'cancelled', error: 'Upload cancelled.' } : f));
      } else if (result.success) {
        setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'success', serverFilePath: result.filePath, progress: 100 } : f));
      } else {
        setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'error', error: result.message || 'Upload failed' } : f));
      }
    } catch (err: any) {
        if (err.name === 'AbortError' || controller.signal.aborted) {
             setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'cancelled', error: 'Upload cancelled by user.' } : f));
        } else {
            setFiles(prev => prev.map(f => f.id === fileToUpload.id ? { ...f, status: 'error', error: err.message || 'Network error or unhandled exception during upload' } : f));
        }
    } finally {
      abortControllers.delete(fileToUpload.id);
      // Check if any other files are uploading
      if (Array.from(abortControllers.values()).length === 0) {
          setIsGlobalUploading(false);
      }
    }
  }, [abortControllers]);

  const retryUpload = useCallback((fileId: string, uploadHandler: any) => {
    const fileToRetry = files.find(f => f.id === fileId);
    if (fileToRetry && fileToRetry.status === 'error') {
        startUpload(fileToRetry, uploadHandler);
    }
  }, [files, startUpload]);


  return {
    files,
    addFiles, // This is what react-dropzone's onDrop will call
    removeFile,
    clearAllFiles,
    startUpload, // Expose this if individual file uploads are triggered from UI
    retryUpload,
    isGlobalUploading, // To disable dropzone or show global progress
  };
};

// Example Usage (Conceptual - in a component using this hook)
// const MyUploaderComponent = () => {
//   const myCustomUploadHandler = async (file, onProgress, signal) => {
//     // ... your fetch/axios logic for uploading the file
//     // call onProgress(percentage) during the upload
//     // check signal.aborted to stop upload
//     return { success: true, filePath: '/server/path/to/file.ext' };
//   };

//   const { files, addFiles, removeFile, startUpload } = useFileUpload({
//     validationOptions: { allowedExtensions: ['.png', '.jpg'], maxSizeMb: 2 },
//     maxFiles: 3,
//   });

//   const { getRootProps, getInputProps } = useDropzone({ onDrop: addFiles });

//   return (
//     <div>
//       <div {...getRootProps()}>
//         <input {...getInputProps()} />
//         <p>Drag 'n' drop some files here, or click to select files</p>
//       </div>
//       <ul>
//         {files.map(upFile => (
//           <li key={upFile.id}>
//             {upFile.file.name} - {upFile.status} - {upFile.progress}%
//             {upFile.status === 'ready' && <button onClick={() => startUpload(upFile, myCustomUploadHandler)}>Upload</button>}
//             <button onClick={() => removeFile(upFile.id)}>Remove</button>
//           </li>
//         ))}
//       </ul>
//     </div>
//   );
// };
