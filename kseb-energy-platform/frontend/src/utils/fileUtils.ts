/**
 * Formats file size from bytes to a human-readable string.
 * @param bytes The file size in bytes.
 * @param decimals Number of decimal places to display.
 * @returns Human-readable file size string (e.g., "1.23 MB").
 */
export const formatBytes = (bytes: number, decimals: number = 2): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

/**
 * Gets a file extension from a filename.
 * @param filename The name of the file.
 * @returns The file extension (e.g., "png", "txt") or an empty string if no extension.
 */
export const getFileExtension = (filename: string): string => {
  return filename.slice(((filename.lastIndexOf(".") - 1) >>> 0) + 2).toLowerCase();
};

/**
 * Checks if a file type is an image based on its MIME type.
 * @param fileType The MIME type string (e.g., "image/jpeg").
 * @returns True if the type indicates an image, false otherwise.
 */
export const isImageFile = (fileType: string | undefined): boolean => {
  return !!fileType && fileType.startsWith('image/');
};

/**
 * Creates a data URL for previewing an image file.
 * @param file The image File object.
 * @returns A Promise that resolves with the data URL string.
 */
export const createImagePreviewUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    if (!isImageFile(file.type)) {
      reject(new Error('File is not an image.'));
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      resolve(reader.result as string);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

/**
 * Converts a Dropzone 'Accept' object to a string for display.
 * Example input: { 'image/*': ['.png', '.jpg'], 'text/csv': ['.csv'] }
 * Example output: ".png, .jpg, .csv, other image/*"
 * @param accept The react-dropzone Accept object.
 * @returns A string representation of accepted file types.
 */
export const formatAcceptObject = (accept?: Record<string, string[]>): string => {
    if (!accept || Object.keys(accept).length === 0) {
        return "any files";
    }

    const allExtensions = new Set<string>();
    const mimeTypesGeneric: string[] = [];

    Object.entries(accept).forEach(([mimeType, extensions]) => {
        if (extensions && extensions.length > 0) {
            extensions.forEach(ext => allExtensions.add(ext));
        } else {
            // Handle generic MIME types like 'image/*'
            if (mimeType.endsWith('/*')) {
                mimeTypesGeneric.push(mimeType.replace('/*', ' files')); // e.g., "image files"
            } else {
                mimeTypesGeneric.push(mimeType); // Specific MIME like 'application/pdf'
            }
        }
    });

    const parts: string[] = [];
    if (allExtensions.size > 0) {
        parts.push(Array.from(allExtensions).join(', '));
    }
    if (mimeTypesGeneric.length > 0) {
        parts.push(...mimeTypesGeneric);
    }

    return parts.join(', ') || "specified types";
};


// Example of how you might read a CSV client-side (e.g., for quick validation)
// This is a basic example and might need a more robust CSV parser for complex files.
/**
 * Reads a CSV file and returns its content as an array of objects.
 * @param file The CSV File object.
 * @returns A Promise resolving to an array of objects, where keys are headers.
 */
export const readCsvFile = <T = Record<string, string>>(file: File): Promise<T[]> => {
    return new Promise((resolve, reject) => {
        if (file.type !== 'text/csv' && !file.name.toLowerCase().endsWith('.csv')) {
            // Basic check, server-side validation is more reliable for type.
            // reject(new Error("File is not a CSV."));
            // return;
            console.warn("Attempting to read non-CSV file as CSV:", file.name, file.type);
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const csvText = event.target?.result as string;
                const lines = csvText.split(/\r\n|\n/);
                if (lines.length === 0) {
                    resolve([]);
                    return;
                }

                // Basic CSV parsing: assumes comma delimiter and no escaped commas within fields
                const headers = lines[0].split(',').map(h => h.trim());
                const data: T[] = [];

                for (let i = 1; i < lines.length; i++) {
                    const line = lines[i].trim();
                    if (line === '') continue; // Skip empty lines

                    const values = line.split(',');
                    const entry: any = {};
                    headers.forEach((header, index) => {
                        entry[header] = values[index]?.trim() || '';
                    });
                    data.push(entry as T);
                }
                resolve(data);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = (error) => reject(error);
        reader.readAsText(file);
    });
};

export default {
  formatBytes,
  getFileExtension,
  isImageFile,
  createImagePreviewUrl,
  formatAcceptObject,
  readCsvFile,
};
