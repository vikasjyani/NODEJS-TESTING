// This file is for client-side file validation utilities.
// More complex validation (e.g., CSV structure, Excel sheet names)
// would typically be done on the backend after upload.

export interface FileValidationOptions {
  allowedExtensions?: string[]; // e.g., ['.csv', '.xlsx']
  maxSizeMb?: number;
  minSizeKb?: number;
  expectedMimeTypes?: string[]; // e.g., ['text/csv', 'application/vnd.ms-excel']
  // Custom validation function
  customValidator?: (file: File) => Promise<{ isValid: boolean; message?: string }>;
}

export interface FileValidationResult {
  isValid: boolean;
  errors: string[]; // Array of error messages
  fileName: string;
  fileSize: number;
  fileType: string;
}

/**
 * Validates a single file based on provided options.
 * @param file The File object to validate.
 * @param options Validation options.
 * @returns A Promise resolving to FileValidationResult.
 */
export const validateFile = async (
  file: File,
  options: FileValidationOptions = {}
): Promise<FileValidationResult> => {
  const errors: string[] = [];

  // Validate extension
  if (options.allowedExtensions && options.allowedExtensions.length > 0) {
    const fileExtension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`;
    if (!options.allowedExtensions.includes(fileExtension)) {
      errors.push(`Invalid file type. Allowed extensions: ${options.allowedExtensions.join(', ')}.`);
    }
  }

  // Validate MIME type (more reliable than extension for some cases)
  if (options.expectedMimeTypes && options.expectedMimeTypes.length > 0) {
    if (!options.expectedMimeTypes.includes(file.type)) {
        // Fallback for common Excel types if browser reports them generically
        const isExcelType = file.type === 'application/vnd.ms-excel' || file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
        const expectsExcel = options.expectedMimeTypes.some(type => type.includes('excel') || type.includes('spreadsheetml'));
        if (!(isExcelType && expectsExcel)) {
             errors.push(`Invalid MIME type '${file.type}'. Expected: ${options.expectedMimeTypes.join(', ')}.`);
        }
    }
  }


  // Validate max size
  if (options.maxSizeMb && file.size > options.maxSizeMb * 1024 * 1024) {
    errors.push(`File is too large. Maximum size: ${options.maxSizeMb} MB. (File: ${(file.size / (1024*1024)).toFixed(2)} MB)`);
  }

  // Validate min size
  if (options.minSizeKb && file.size < options.minSizeKb * 1024) {
    errors.push(`File is too small. Minimum size: ${options.minSizeKb} KB.`);
  }

  // Custom validator
  if (options.customValidator) {
    try {
      const customResult = await options.customValidator(file);
      if (!customResult.isValid) {
        errors.push(customResult.message || 'Custom validation failed.');
      }
    } catch (customError: any) {
      errors.push(`Custom validation error: ${customError.message}`);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
  };
};


/**
 * Validates a list of files.
 * @param files Array of File objects.
 * @param options Validation options to apply to each file.
 * @param maxFiles Optional maximum number of files allowed.
 * @returns A Promise resolving to an array of FileValidationResult.
 */
export const validateMultipleFiles = async (
  files: File[],
  options: FileValidationOptions = {},
  maxFiles?: number
): Promise<FileValidationResult[]> => {
  const results: FileValidationResult[] = [];

  if (maxFiles && files.length > maxFiles) {
    // Add a general error for exceeding max files, or handle this in the dropzone logic directly
    // For now, we'll validate individual files and let dropzone handle maxFiles count.
    // Or, one could return a single error result for this case.
    console.warn(`Attempted to validate ${files.length} files, but maxFiles is ${maxFiles}.`)
  }

  for (const file of files) {
    results.push(await validateFile(file, options));
  }
  return results;
};


// Example custom validator (can be passed to validateFile options)
export const exampleCsvHeaderValidator = async (file: File): Promise<{ isValid: boolean; message?: string }> => {
    if (!file.type.includes('csv')) return { isValid: true }; // Skip for non-CSV

    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const text = e.target?.result as string;
            const firstLine = text.split('\n')[0].toLowerCase();
            const requiredHeaders = ['year', 'demand', 'gdp']; // Example

            let isValid = true;
            let missingHeaders: string[] = [];

            requiredHeaders.forEach(header => {
                if (!firstLine.includes(header)) {
                    isValid = false;
                    missingHeaders.push(header);
                }
            });

            if (isValid) {
                resolve({ isValid: true });
            } else {
                resolve({ isValid: false, message: `Missing required CSV headers: ${missingHeaders.join(', ')}.` });
            }
        };
        reader.onerror = () => resolve({isValid: false, message: "Could not read file for header validation."});
        reader.readAsText(file.slice(0, 2048)); // Read only first 2KB for headers
    });
};

// Utility to format file size
export const formatFileSize = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};
