import { useState, useMemo, useCallback, useEffect } from 'react';
import { Column } from '../components/common/DataTable'; // Assuming DataTable exports Column type
import { ActiveFilter } from '../components/common/TableFilters'; // Assuming TableFilters exports ActiveFilter type

// This type would be more specific based on your actual API response structure
export type RawApiDataRow = Record<string, any>;

// Type for the hook's options
interface UseTableDataOptions<T extends RawApiDataRow> {
  initialData?: T[];
  initialColumns: Column<T>[]; // Columns are required
  // fetchFunction?: (params: { page: number, rowsPerPage: number, sortBy?: string, sortOrder?: 'asc'|'desc', filters?: ActiveFilter[], searchTerm?: string }) => Promise<{ data: T[], totalCount: number }>;
  // clientSideProcessing?: boolean; // True if all data is fetched once and then processed client-side
  defaultSortBy?: keyof T | string;
  defaultSortOrder?: 'asc' | 'desc';
  defaultRowsPerPage?: number;
}

// Type for the hook's return value
interface UseTableDataReturn<T extends RawApiDataRow> {
  processedData: T[]; // Data to be rendered in the table (sorted, paginated, filtered)
  columns: Column<T>[];
  totalDataCount: number; // Total count of items (for server-side pagination)

  // State and setters
  page: number;
  setPage: React.Dispatch<React.SetStateAction<number>>;
  rowsPerPage: number;
  setRowsPerPage: React.Dispatch<React.SetStateAction<number>>;
  sortBy: keyof T | string | undefined;
  setSortBy: React.Dispatch<React.SetStateAction<keyof T | string | undefined>>;
  sortOrder: 'asc' | 'desc';
  setSortOrder: React.Dispatch<React.SetStateAction<'asc' | 'desc'>>;
  searchTerm: string;
  setSearchTerm: React.Dispatch<React.SetStateAction<string>>;
  activeFilters: ActiveFilter[];
  setActiveFilters: React.Dispatch<React.SetStateAction<ActiveFilter[]>>;

  // Status
  isLoading: boolean;
  error: string | null;

  // Actions
  refreshData: () => void; // Function to trigger a data refetch
  // updateColumnVisibility: (columnId: keyof T | string, isVisible: boolean) => void; // Example
}


/**
 * Custom hook to manage data table state including sorting, pagination, filtering, and searching.
 * This is a conceptual hook. For server-side operations, `fetchFunction` would be essential.
 * For client-side, it would operate on `initialData`.
 */
export const useTableData = <T extends RawApiDataRow>(
  options: UseTableDataOptions<T>
): UseTableDataReturn<T> => {
  const {
    initialData = [],
    initialColumns,
    // fetchFunction,
    // clientSideProcessing = !fetchFunction, // Default to client-side if no fetchFunction
    defaultSortBy,
    defaultSortOrder = 'asc',
    defaultRowsPerPage = 10,
  } = options;

  const [sourceData, setSourceData] = useState<T[]>(initialData); // Holds raw data if client-side
  const [columns, setColumns] = useState<Column<T>[]>(initialColumns);
  const [totalDataCount, setTotalDataCount] = useState<number>(initialData.length);

  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(defaultRowsPerPage);
  const [sortBy, setSortBy] = useState<keyof T | string | undefined>(defaultSortBy);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(defaultSortOrder);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // --- Data Fetching (Conceptual for Server-Side) ---
  const fetchData = useCallback(async () => {
    // if (!fetchFunction) return; // Only run if fetchFunction is provided (server-side)

    setIsLoading(true);
    setError(null);
    try {
        // const result = await fetchFunction({
        //     page,
        //     rowsPerPage,
        //     sortBy: sortBy as string,
        //     sortOrder,
        //     filters: activeFilters,
        //     searchTerm
        // });
        // setSourceData(result.data);
        // setTotalDataCount(result.totalCount);

        // SIMULATION FOR CLIENT-SIDE (REMOVE IF USING FETCHFUNCTION)
        console.log("Simulating data fetch/processing based on state:", { page, rowsPerPage, sortBy, sortOrder, activeFilters, searchTerm });
        // Client-side processing will happen in `processedData` memo
        setTotalDataCount(initialData.length); // For client-side, total is just initial length
        setSourceData(initialData); // Reset to full initial data for client-side processing
        // END SIMULATION

    } catch (err: any) {
      setError(err.message || 'Failed to fetch table data.');
    } finally {
      setIsLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [/*fetchFunction,*/ page, rowsPerPage, sortBy, sortOrder, activeFilters, searchTerm, initialData]); // Add initialData for client-side simulation refresh

  // Initial fetch or when dependencies for fetching change
  useEffect(() => {
    // if (fetchFunction) { // Server-side
    //   fetchData();
    // } else { // Client-side (data is already in sourceData)
    //   setIsLoading(false); // No async loading for initial client-side data
    // }
    fetchData(); // For client-side simulation, this will "reset" and re-filter
  }, [fetchData]);


  // --- Client-Side Data Processing ---
  const processedData = useMemo(() => {
    // if (!clientSideProcessing) return sourceData; // If server-side, sourceData is already processed for current page

    let dataToProcess = [...sourceData];

    // 1. Filtering
    if (activeFilters.length > 0) {
      dataToProcess = dataToProcess.filter(row =>
        activeFilters.every(filter => {
          const rowValue = row[filter.id as keyof T];
          if (rowValue === undefined || rowValue === null) return false;

          switch (filter.type) {
            case 'string':
              const textFilter = filter as TextFilter;
              const valStr = String(rowValue).toLowerCase();
              const filterValStr = (textFilter.value || '').toLowerCase();
              if (filterValStr === '') return true;
              switch (textFilter.operator) {
                case 'equals': return valStr === filterValStr;
                case 'startsWith': return valStr.startsWith(filterValStr);
                case 'endsWith': return valStr.endsWith(filterValStr);
                default: return valStr.includes(filterValStr); // 'contains'
              }
            case 'number':
              const numFilter = filter as NumberRangeFilter;
              const valNum = Number(rowValue);
              if (numFilter.min !== undefined && valNum < numFilter.min) return false;
              if (numFilter.max !== undefined && valNum > numFilter.max) return false;
              return true;
            // TODO: Add 'date', 'boolean', 'custom' (CategoryFilter) cases
            default:
              return true;
          }
        })
      );
    }

    // 2. Global Search (if not handled by server)
    if (searchTerm) {
      const lowerSearchTerm = searchTerm.toLowerCase();
      dataToProcess = dataToProcess.filter(row =>
        initialColumns.some(column => { // Use initialColumns to search all, even if hidden
          const value = column.format ? column.format(row[column.id as keyof T], row) : row[column.id as keyof T];
          return value != null && String(value).toLowerCase().includes(lowerSearchTerm);
        })
      );
    }

    // Update total count after filtering and search (for client-side pagination)
    // Note: This is a bit of a hack. For true client-side, totalDataCount should be updated here.
    // However, DataTable uses `sortedData.length` for pagination count if client-side.
    // This hook's `totalDataCount` is more for server-side.
    // If purely client-side, the DataTable itself will use the length of the data passed to it.
    // Let's assume for now this hook primarily prepares data for the DataTable component,
    // and DataTable's internal pagination will use the length of `processedData` before slicing.


    // 3. Sorting
    if (sortBy) {
      const columnToSort = initialColumns.find(c => c.id === sortBy);
      dataToProcess.sort((a, b) => {
        const aVal = a[sortBy as keyof T];
        const bVal = b[sortBy as keyof T];
        if (columnToSort?.type === 'number') return sortOrder === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
        if (columnToSort?.type === 'date') return sortOrder === 'asc' ? new Date(aVal as string).getTime() - new Date(bVal as string).getTime() : new Date(bVal as string).getTime() - new Date(aVal as string).getTime();
        if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      });
    }

    // Update totalDataCount based on filtered/searched data if purely client-side
    // This is important for the TablePagination component if it uses this hook's totalDataCount
    // For true client-side, this should reflect the length *before* pagination slicing.
    // if (clientSideProcessing) {
    //    setTotalDataCount(dataToProcess.length); // This might cause re-render loop if not careful
    // }


    // 4. Pagination (slicing is done by DataTable itself if clientSideProcessing is true and all data is passed)
    // If this hook is responsible for pagination even client-side:
    // const startIndex = page * rowsPerPage;
    // return dataToProcess.slice(startIndex, startIndex + rowsPerPage);

    // For now, assume DataTable handles pagination slicing from the full `processedData` (after filter/sort)
    return dataToProcess;

  }, [sourceData, activeFilters, searchTerm, sortBy, sortOrder, initialColumns, /*clientSideProcessing, page, rowsPerPage*/]);

  // If client-side, totalDataCount should be length of processed (but not paginated) data
  const finalTotalDataCount = /*clientSideProcessing ? processedData.length :*/ totalDataCount;


  return {
    processedData: processedData, // If client-side, DataTable will paginate this. If server-side, this is already the page.
    columns,
    totalDataCount: finalTotalDataCount,
    page,
    setPage,
    rowsPerPage,
    setRowsPerPage,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    searchTerm,
    setSearchTerm,
    activeFilters,
    setActiveFilters,
    isLoading,
    error,
    refreshData: fetchData, // Expose fetchData as refreshData
  };
};

// Example Usage (Conceptual)
// const MyComponent = () => {
//   const {
//     processedData, columns, totalDataCount,
//     page, setPage, rowsPerPage, setRowsPerPage, /* ...other states and setters */
//     isLoading, error, refreshData
//   } = useTableData<MyDataType>({
//     initialColumns: MY_COLUMNS_DEFINITION,
//     // For server-side:
//     // fetchFunction: async (params) => myApiService.getTableData(params),
//     // clientSideProcessing: false,
//     // For client-side:
//     initialData: MY_STATIC_DATA,
//     clientSideProcessing: true,
//   });

//   return (
//     <DataTable
//       data={processedData} // This will be the paginated slice if server-side, or full sorted/filtered if client-side
//       columns={columns}
//       loading={isLoading}
//       error={error}
//       pagination // DataTable handles pagination display
//       page={page} // Control current page
//       rowsPerPage={rowsPerPage} // Control rows per page
//       count={totalDataCount} // Total items for pagination
//       onPageChange={(e, newPage) => setPage(newPage)}
//       onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
//       // ... other props like onSort, onFilter, onSearch to update hook's state
//     />
//   );
// };
