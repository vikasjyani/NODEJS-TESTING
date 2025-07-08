import React, { useState, useMemo, useCallback, ChangeEvent, MouseEvent, useEffect } from 'react'; // Added useEffect
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, TablePagination, TextField, InputAdornment, IconButton,
  Toolbar, Typography, Checkbox, Button, Menu, MenuItem,
  Chip, Box, TableSortLabel, Tooltip, CircularProgress, Alert, useTheme, lighten, ListItemText // Added ListItemText
} from '@mui/material';
import {
  Search, FilterList, Download as DownloadIcon, Visibility, VisibilityOff,
  MoreVert, Refresh, Clear, UnfoldMore, ArrowUpward, ArrowDownward
} from '@mui/icons-material';
import { visuallyHidden } from '@mui/utils'; // For accessibility with sorting

export interface Column<T = any> { // Generic type T for row data
  id: keyof T | string; // Allow string for custom/computed columns
  label: string;
  minWidth?: number | string;
  maxWidth?: number | string;
  align?: 'right' | 'left' | 'center';
  format?: (value: any, row: T) => React.ReactNode | string | number; // Allow ReactNode for custom rendering
  sortable?: boolean;
  filterable?: boolean; // General flag, specific filter UIs can be added
  type?: 'string' | 'number' | 'date' | 'boolean' | 'custom'; // For default filtering/sorting logic
  disablePadding?: boolean;
  sticky?: boolean; // For sticky columns
  stickyPosition?: 'left' | 'right'; // For sticky columns
  renderCell?: (row: T, column: Column<T>) => React.ReactNode; // Custom cell rendering
}

export interface DataTableProps<T = any> {
  columns: Column<T>[];
  data: T[];
  title?: string;
  loading?: boolean;
  error?: string | null;
  selectable?: boolean;
  onRowSelect?: (selectedRows: T[]) => void; // Callback with actual data of selected rows
  onExport?: (format: 'csv' | 'excel' | 'json', selectedOnly: boolean) => void;
  onRefresh?: () => void;
  maxHeight?: number | string;
  searchable?: boolean; // Enable global search
  // filterable?: boolean; // General flag for column filters (more complex to implement generally here)
  pagination?: boolean;
  rowsPerPageOptions?: number[];
  defaultRowsPerPage?: number;
  dense?: boolean;
  rowKey?: keyof T | ((row: T) => string); // For unique row identification, defaults to index
  initialSortBy?: keyof T | string;
  initialSortOrder?: 'asc' | 'desc';
  noDataMessage?: string;
  toolbarActions?: React.ReactNode; // Custom actions for the toolbar
  onRowClick?: (row: T, event: MouseEvent<HTMLTableRowElement>) => void;
}

type Order = 'asc' | 'desc';

export const DataTable = <T extends Record<string, any>>(
  {
    columns,
    data,
    title,
    loading = false,
    error,
    selectable = false,
    onRowSelect,
    onExport,
    onRefresh,
    maxHeight = 450,
    searchable = true,
    pagination = true,
    rowsPerPageOptions = [5, 10, 25, 50, 100],
    defaultRowsPerPage = 10,
    dense = false,
    rowKey,
    initialSortBy,
    initialSortOrder = 'asc',
    noDataMessage = "No data available.",
    toolbarActions,
    onRowClick,
  }: DataTableProps<T>
) => {
  const theme = useTheme();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(defaultRowsPerPage);
  const [orderBy, setOrderBy] = useState<keyof T | string | undefined>(initialSortBy);
  const [order, setOrder] = useState<Order>(initialSortOrder);
  const [searchTerm, setSearchTerm] = useState('');
  const [hiddenColumns, setHiddenColumns] = useState<Set<keyof T | string>>(new Set());
  const [selectedRowKeys, setSelectedRowKeys] = useState<Set<string | number>>(new Set());

  const [actionMenuAnchorEl, setActionMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [columnMenuAnchorEl, setColumnMenuAnchorEl] = useState<null | HTMLElement>(null);

  const getRowKey = useCallback((row: T, index: number): string | number => {
    if (rowKey) {
      return typeof rowKey === 'function' ? rowKey(row) : row[rowKey];
    }
    return index; // Fallback to index if no rowKey provided
  }, [rowKey]);


  const filteredData = useMemo(() => {
    let filtered = [...data];
    if (searchTerm && searchable) {
      const lowerSearchTerm = searchTerm.toLowerCase();
      filtered = filtered.filter(row =>
        columns.some(column => {
          if (hiddenColumns.has(column.id)) return false;
          const value = column.format ? column.format(row[column.id as keyof T], row) : row[column.id as keyof T];
          return value != null && String(value).toLowerCase().includes(lowerSearchTerm);
        })
      );
    }
    // Column-specific filtering could be added here if `filterable` prop is true
    return filtered;
  }, [data, searchTerm, columns, searchable, hiddenColumns]);

  const sortedData = useMemo(() => {
    if (!orderBy) return filteredData;
    const columnToSort = columns.find(c => c.id === orderBy);

    return [...filteredData].sort((a, b) => {
      const aVal = a[orderBy as keyof T];
      const bVal = b[orderBy as keyof T];

      if (columnToSort?.type === 'number') {
        return order === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
      }
      if (columnToSort?.type === 'date') {
        return order === 'asc' ? new Date(aVal as string).getTime() - new Date(bVal as string).getTime() : new Date(bVal as string).getTime() - new Date(aVal as string).getTime();
      }
      // Default string/boolean comparison
      if (aVal < bVal) return order === 'asc' ? -1 : 1;
      if (aVal > bVal) return order === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filteredData, orderBy, order, columns]);

  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    const startIndex = page * rowsPerPage;
    return sortedData.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedData, page, rowsPerPage, pagination]);


  const handleSort = (columnId: keyof T | string) => {
    const column = columns.find(c => c.id === columnId);
    if (!column?.sortable) return;
    const isAsc = orderBy === columnId && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(columnId);
  };

  const handleChangePage = (event: unknown, newPage: number) => setPage(newPage);
  const handleChangeRowsPerPage = (event: ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSelectAllClick = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelectedKeys = new Set(paginatedData.map((row, index) => getRowKey(row, page * rowsPerPage + index)));
      setSelectedRowKeys(newSelectedKeys);
    } else {
      setSelectedRowKeys(new Set());
    }
  };

  const handleRowCheckboxClick = (row: T, index: number) => {
    const key = getRowKey(row, page * rowsPerPage + index);
    const newSelected = new Set(selectedRowKeys);
    if (newSelected.has(key)) newSelected.delete(key);
    else newSelected.add(key);
    setSelectedRowKeys(newSelected);
  };

  useEffect(() => {
    if (onRowSelect) {
      const selectedData = data.filter((row, index) => selectedRowKeys.has(getRowKey(row, index)));
      onRowSelect(selectedData);
    }
  }, [selectedRowKeys, data, onRowSelect, getRowKey]);


  const toggleColumnVisibility = (columnId: keyof T | string) => {
    const newHidden = new Set(hiddenColumns);
    if (newHidden.has(columnId)) newHidden.delete(columnId);
    else newHidden.add(columnId);
    setHiddenColumns(newHidden);
  };

  const visibleColumns = useMemo(() => columns.filter(column => !hiddenColumns.has(column.id)), [columns, hiddenColumns]);
  const numSelected = selectedRowKeys.size;
  const rowCountInPage = paginatedData.length;

  const handleActionMenuOpen = (event: MouseEvent<HTMLElement>) => setActionMenuAnchorEl(event.currentTarget);
  const handleActionMenuClose = () => setActionMenuAnchorEl(null);
  const handleColumnMenuOpen = (event: MouseEvent<HTMLElement>) => setColumnMenuAnchorEl(event.currentTarget);
  const handleColumnMenuClose = () => setColumnMenuAnchorEl(null);

  const handleExportClick = (format: 'csv' | 'excel' | 'json') => {
    onExport?.(format, numSelected > 0);
    handleActionMenuClose();
  }

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden', borderRadius: 2, display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ pl: { sm: 2 }, pr: { xs: 1, sm: 1 },
        ...(numSelected > 0 && { bgcolor: (theme) => lighten(theme.palette.primary.light, 0.85) })
      }}>
        {numSelected > 0 ? (
          <Typography sx={{ flex: '1 1 100%' }} color="inherit" variant="subtitle1" component="div">
            {numSelected} selected
          </Typography>
        ) : (
          <Typography sx={{ flex: '1 1 100%' }} variant="h6" id="tableTitle" component="div">
            {title}
          </Typography>
        )}

        {searchable && numSelected === 0 && (
          <TextField
            size="small"
            variant="outlined"
            placeholder="Search table..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (<InputAdornment position="start"><Search fontSize="small"/></InputAdornment>),
              endAdornment: searchTerm ? (<InputAdornment position="end"><IconButton size="small" onClick={() => setSearchTerm('')}><Clear fontSize="small"/></IconButton></InputAdornment>) : null,
            }}
            sx={{ mx: 1, minWidth: {xs: 150, sm:200, md: 250}, transition: 'width 0.3s ease-in-out', '& .MuiOutlinedInput-root': {borderRadius: '20px'} }}
          />
        )}

        {numSelected > 0 ? (
            <Tooltip title="Actions for selected rows">
                <IconButton><MoreVert/></IconButton>
                {/* TODO: Add menu for bulk actions: delete selected, export selected etc. */}
            </Tooltip>
        ) : (
            <>
                {onRefresh && <Tooltip title="Refresh Data"><IconButton onClick={onRefresh}><Refresh /></IconButton></Tooltip>}
                <Tooltip title="Manage Columns"><IconButton onClick={handleColumnMenuOpen}><Visibility /></IconButton></Tooltip>
                {onExport && <Tooltip title="Export Data"><IconButton onClick={handleActionMenuOpen}><DownloadIcon /></IconButton></Tooltip>}
                {toolbarActions}
            </>
        )}
      </Toolbar>

      <Menu anchorEl={actionMenuAnchorEl} open={Boolean(actionMenuAnchorEl)} onClose={handleActionMenuClose}>
        <MenuItem onClick={() => handleExportClick('csv')}>Export CSV</MenuItem>
        <MenuItem onClick={() => handleExportClick('excel')}>Export Excel</MenuItem>
        <MenuItem onClick={() => handleExportClick('json')}>Export JSON</MenuItem>
      </Menu>

      <Menu anchorEl={columnMenuAnchorEl} open={Boolean(columnMenuAnchorEl)} onClose={handleColumnMenuClose}>
        {columns.map((column) => (
          <MenuItem key={String(column.id)} onClick={() => toggleColumnVisibility(column.id)}>
            <Checkbox checked={!hiddenColumns.has(column.id)} size="small" sx={{mr:1}}/>
            <ListItemText primary={column.label} />
          </MenuItem>
        ))}
      </Menu>

      <TableContainer sx={{ maxHeight, flexGrow: 1 }}>
        <Table stickyHeader aria-labelledby="tableTitle" size={dense ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox" sx={{ ...(visibleColumns.find(c=>c.sticky && c.stickyPosition === 'left') && {position:'sticky', left:0, zIndex:5, bgcolor:'background.paper'})}}>
                  <Checkbox
                    color="primary"
                    indeterminate={numSelected > 0 && numSelected < rowCountInPage} // In current page
                    checked={rowCountInPage > 0 && numSelected === rowCountInPage} // All in current page selected
                    onChange={handleSelectAllClick}
                    inputProps={{ 'aria-label': 'select all desserts' }}
                  />
                </TableCell>
              )}
              {visibleColumns.map((column, index) => (
                <TableCell
                  key={String(column.id)}
                  align={column.align}
                  padding={column.disablePadding ? 'none' : 'normal'}
                  sortDirection={orderBy === column.id ? order : false}
                  sx={{
                    minWidth: column.minWidth,
                    maxWidth: column.maxWidth,
                    fontWeight: 'medium',
                    ...(column.sticky && {
                        position: 'sticky',
                        left: column.stickyPosition === 'left' ? (selectable ? 60 : 0) + (index * (typeof column.minWidth === 'number' ? column.minWidth : 150) ) : undefined, // Basic left offset calculation
                        right: column.stickyPosition === 'right' ? 0 : undefined, // Basic right offset calculation
                        zIndex: 4, // Ensure sticky header cells are above body but below checkbox potentially
                        bgcolor: 'background.paper',
                        borderRight: column.stickyPosition === 'left' ? `1px solid ${theme.palette.divider}` : undefined,
                        borderLeft: column.stickyPosition === 'right' ? `1px solid ${theme.palette.divider}` : undefined,
                    })
                  }}
                >
                  {column.sortable ? (
                    <TableSortLabel
                      active={orderBy === column.id}
                      direction={orderBy === column.id ? order : 'asc'}
                      onClick={() => handleSort(column.id)}
                      IconComponent={orderBy === column.id ? (order === 'desc' ? ArrowDownward : ArrowUpward) : UnfoldMore}
                    >
                      {column.label}
                      {orderBy === column.id ? <Box component="span" sx={visuallyHidden}>{order === 'desc' ? 'sorted descending' : 'sorted ascending'}</Box> : null}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center" sx={{p:3}}><CircularProgress /></TableCell></TableRow>
            ) : error ? (
              <TableRow><TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center" sx={{p:2}}><Alert severity="error" sx={{width:'100%', justifyContent:'center'}}>Error: {error}</Alert></TableCell></TableRow>
            ) : paginatedData.length === 0 ? (
              <TableRow><TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center" sx={{p:3}}><Typography color="textSecondary">{noDataMessage}</Typography></TableCell></TableRow>
            ) : (
              paginatedData.map((row, rowIndexInPage) => {
                const originalRowIndex = page * rowsPerPage + rowIndexInPage;
                const key = getRowKey(row, originalRowIndex);
                const isSelected = selectedRowKeys.has(key);

                return (
                  <TableRow
                    hover
                    role={selectable ? "checkbox" : "row"}
                    aria-checked={selectable ? isSelected : undefined}
                    tabIndex={-1}
                    key={String(key)}
                    selected={selectable ? isSelected : undefined}
                    onClick={(event) => onRowClick ? onRowClick(row, event) : (selectable && handleRowCheckboxClick(row, rowIndexInPage))}
                    sx={{ cursor: (onRowClick || selectable) ? 'pointer' : 'default' }}
                  >
                    {selectable && (
                      <TableCell padding="checkbox" sx={{ ...(visibleColumns.find(c=>c.sticky && c.stickyPosition === 'left') && {position:'sticky', left:0, zIndex:3, bgcolor:'background.paper'})}}>
                        <Checkbox color="primary" checked={isSelected} inputProps={{ 'aria-labelledby': `enhanced-table-checkbox-${originalRowIndex}` }}/>
                      </TableCell>
                    )}
                    {visibleColumns.map((column, colIndex) => {
                      const value = row[column.id as keyof T];
                      return (
                        <TableCell
                            key={`${String(key)}-${String(column.id)}`}
                            align={column.align}
                            sx={{
                                ...(column.sticky && {
                                    position: 'sticky',
                                    left: column.stickyPosition === 'left' ? (selectable ? 60 : 0) + (colIndex * (typeof column.minWidth === 'number' ? column.minWidth : 150) ) : undefined,
                                    right: column.stickyPosition === 'right' ? 0 : undefined,
                                    zIndex: 2,
                                    bgcolor: 'background.paper',
                                    borderRight: column.stickyPosition === 'left' ? `1px solid ${theme.palette.divider}` : undefined,
                                    borderLeft: column.stickyPosition === 'right' ? `1px solid ${theme.palette.divider}` : undefined,

                                })
                            }}
                        >
                          {column.renderCell ? column.renderCell(row, column) :
                           column.format ? column.format(value, row) :
                           String(value ?? '')}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {pagination && data.length > 0 && (
        <TablePagination
          rowsPerPageOptions={rowsPerPageOptions.filter(rpp => rpp <= data.length || rpp === rowsPerPageOptions[0])} // Ensure options make sense for data size
          component="div"
          count={sortedData.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          showFirstButton
          showLastButton
        />
      )}
    </Paper>
  );
};
