import React, { useState, useEffect } from 'react';
import { Box, TextField, Button, Grid, Typography, Paper, Autocomplete, Chip, Collapse, IconButton, Tooltip, Menu, MenuItem, Checkbox, ListItemText } from '@mui/material';
import { FilterList, FilterListOff, RotateLeft, Clear, Add, Remove } from '@mui/icons-material';
import { Column, DataTableProps } from './DataTable'; // Assuming DataTable exports Column and potentially other types

// Define more specific filter structures
export interface BaseFilter {
  id: string; // Corresponds to column id
  label: string;
  type: Column['type']; // 'string', 'number', 'date', 'boolean', 'custom'
}

export interface TextFilter extends BaseFilter {
  type: 'string' | 'custom'; // Custom might render a specific component
  value?: string;
  operator?: 'contains' | 'equals' | 'startsWith' | 'endsWith'; // Default to 'contains'
}

export interface NumberRangeFilter extends BaseFilter {
  type: 'number';
  min?: number;
  max?: number;
}

export interface DateRangeFilter extends BaseFilter {
  type: 'date';
  startDate?: Date | null;
  endDate?: Date | null;
}

export interface BooleanFilter extends BaseFilter {
  type: 'boolean';
  value?: boolean | null; // null for 'any'
}

export interface CategoryFilter extends BaseFilter {
    type: 'custom'; // Use 'custom' for Autocomplete/Multi-select for categories
    options: string[];
    selectedValues?: string[];
}

// Ensure ActiveFilter is also exported if it's used elsewhere, or if it's only internal to useTableData, it's fine.
// For safety, let's export it too.
export type ActiveFilter = TextFilter | NumberRangeFilter | DateRangeFilter | BooleanFilter | CategoryFilter;

interface TableFiltersProps<T> {
  columns: Column<T>[]; // Columns from DataTable to derive filterable fields
  activeFilters: ActiveFilter[];
  onApplyFilters: (filters: ActiveFilter[]) => void;
  onResetFilters?: () => void;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

// Helper to get initial filter structure from columns
const initializeFiltersFromColumns = <T,>(columns: Column<T>[]): ActiveFilter[] => {
    return columns
        .filter(col => col.filterable) // Only use columns marked as filterable
        .map(col => {
            const base = { id: String(col.id), label: col.label, type: col.type || 'string' };
            switch (col.type) {
                case 'number':
                    return { ...base, type: 'number', min: undefined, max: undefined } as NumberRangeFilter;
                case 'date':
                    return { ...base, type: 'date', startDate: null, endDate: null } as DateRangeFilter;
                case 'boolean':
                    return { ...base, type: 'boolean', value: null } as BooleanFilter;
                // Example for category if column definition has options
                // if (col.filterOptions && Array.isArray(col.filterOptions)) {
                //     return { ...base, type: 'custom', options: col.filterOptions, selectedValues: [] } as CategoryFilter;
                // }
                default: // string or custom
                    return { ...base, type: 'string', value: '', operator: 'contains' } as TextFilter;
            }
        });
};


export const TableFilters = <T extends Record<string, any>>(
  {
    columns,
    activeFilters: parentActiveFilters,
    onApplyFilters,
    onResetFilters,
    collapsible = true,
    defaultOpen = false,
  }: TableFiltersProps<T>
) => {
  // Manage which filters are currently "active" or visible in the UI
  const [visibleFilters, setVisibleFilters] = useState<ActiveFilter[]>(
    // Initialize with parentActiveFilters or derive from columns if parent is empty
    parentActiveFilters.length > 0 ? parentActiveFilters : initializeFiltersFromColumns(columns)
  );
  const [isPanelOpen, setIsPanelOpen] = useState<boolean>(defaultOpen);
  const [filterMenuAnchorEl, setFilterMenuAnchorEl] = useState<null | HTMLElement>(null);

  // Sync internal state if parentActiveFilters prop changes
  useEffect(() => {
    setVisibleFilters(parentActiveFilters.length > 0 ? parentActiveFilters : initializeFiltersFromColumns(columns));
  }, [parentActiveFilters, columns]);


  const handleFilterValueChange = (filterId: string, newValue: any, subField?: string) => {
    setVisibleFilters(prevFilters =>
      prevFilters.map(f => {
        if (f.id === filterId) {
          if (subField && typeof f === 'object' && f !== null && subField in f) {
            return { ...f, [subField]: newValue };
          }
          return { ...f, value: newValue }; // For simple value filters
        }
        return f;
      })
    );
  };

  // Specific handler for number range
  const handleNumberRangeChange = (filterId: string, part: 'min' | 'max', value: string) => {
     setVisibleFilters(prevFilters =>
      prevFilters.map(f => {
        if (f.id === filterId && f.type === 'number') {
          return { ...f, [part]: value === '' ? undefined : parseFloat(value) };
        }
        return f;
      })
    );
  };

  // Specific handler for category (multi-select)
  const handleCategoryChange = (filterId: string, newSelectedValues: string[]) => {
    setVisibleFilters(prevFilters =>
      prevFilters.map(f => {
        if (f.id === filterId && f.type === 'custom' && 'options' in f) { // Check if it's a CategoryFilter
          return { ...f, selectedValues: newSelectedValues };
        }
        return f;
      })
    );
  };


  const handleApply = () => {
    // Filter out empty/default filters before applying if desired
    const trulyActiveFilters = visibleFilters.filter(f => {
        if (f.type === 'string' && (f.value === undefined || f.value.trim() === '')) return false;
        if (f.type === 'number' && f.min === undefined && f.max === undefined) return false;
        if (f.type === 'date' && !f.startDate && !f.endDate) return false;
        if (f.type === 'boolean' && f.value === null) return false;
        if (f.type === 'custom' && 'selectedValues' in f && (!f.selectedValues || f.selectedValues.length === 0)) return false;
        return true;
    });
    onApplyFilters(trulyActiveFilters);
  };

  const handleResetAll = () => {
    const resetFilters = initializeFiltersFromColumns(columns);
    setVisibleFilters(resetFilters);
    if (onResetFilters) {
      onResetFilters();
    } else {
      onApplyFilters(resetFilters.filter(f => false)); // Apply empty set
    }
  };

  const togglePanel = () => setIsPanelOpen(prev => !prev);

  const handleAddFilterMenuOpen = (event: React.MouseEvent<HTMLElement>) => setFilterMenuAnchorEl(event.currentTarget);
  const handleAddFilterMenuClose = () => setFilterMenuAnchorEl(null);

  const addFilterToVisible = (column: Column<T>) => {
    if (!visibleFilters.find(f => f.id === String(column.id))) {
        const newFilter = initializeFiltersFromColumns([column])[0];
        if (newFilter) {
            setVisibleFilters(prev => [...prev, newFilter]);
        }
    }
    handleAddFilterMenuClose();
  };

  const removeFilterFromVisible = (filterId: string) => {
    setVisibleFilters(prev => prev.filter(f => f.id !== filterId));
  };


  const renderFilterInput = (filter: ActiveFilter) => {
    // This part needs to be significantly expanded to render appropriate inputs
    // based on filter.type. For brevity, only showing text and number range example.
    switch (filter.type) {
      case 'string':
        return (
          <TextField
            fullWidth
            size="small"
            label={filter.label}
            value={(filter as TextFilter).value || ''}
            onChange={(e) => handleFilterValueChange(filter.id, e.target.value)}
            InputProps={{
                endAdornment: <IconButton size="small" onClick={() => removeFilterFromVisible(filter.id)}><Remove fontSize="inherit"/></IconButton>
            }}
          />
        );
      case 'number':
        const numFilter = filter as NumberRangeFilter;
        return (
          <Grid container spacing={1} alignItems="center">
            <Grid item xs={12} sm={5.5}>
                <TextField fullWidth size="small" type="number" label={`${filter.label} (Min)`} value={numFilter.min ?? ''} onChange={(e) => handleNumberRangeChange(filter.id, 'min', e.target.value)} />
            </Grid>
            <Grid item xs={12} sm={1} sx={{textAlign: 'center'}}><Typography variant="caption">-</Typography></Grid>
            <Grid item xs={12} sm={5.5}>
                <TextField fullWidth size="small" type="number" label={`${filter.label} (Max)`} value={numFilter.max ?? ''} onChange={(e) => handleNumberRangeChange(filter.id, 'max', e.target.value)} />
            </Grid>
             <Grid item xs={12} sx={{textAlign:'right', pt:0, mt: -1}}>
                <IconButton size="small" onClick={() => removeFilterFromVisible(filter.id)}><Remove fontSize="inherit"/></IconButton>
            </Grid>
          </Grid>
        );
      // TODO: Add cases for 'date', 'boolean', 'custom' (CategoryFilter)
      // For CategoryFilter, use Autocomplete with multiple selection.
      default:
        return <Typography variant="caption">Unsupported filter type: {filter.type} for {filter.label}</Typography>;
    }
  };

  const filterableColumns = columns.filter(c => c.filterable && !visibleFilters.find(f => f.id === String(c.id)));


  return (
    <Paper variant="outlined" sx={{ p: collapsible ? 0 : 1, mb: 1, borderRadius: 1 }}>
      {collapsible && (
        <Box onClick={togglePanel} sx={{ p: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', borderBottom: isPanelOpen ? 1 : 0, borderColor: 'divider', '&:hover': { backgroundColor: 'action.hover' } }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'medium' }}>Advanced Filters</Typography>
          <IconButton size="small">{isPanelOpen ? <FilterListOff /> : <FilterList />}</IconButton>
        </Box>
      )}
      <Collapse in={!collapsible || isPanelOpen}>
        <Box sx={{ p: 1.5 }}>
          {visibleFilters.length === 0 && <Typography variant="body2" color="textSecondary" sx={{textAlign:'center', my:1}}>No active filters. Click 'Add Filter' to begin.</Typography>}
          <Grid container spacing={2}>
            {visibleFilters.map((filter) => (
              <Grid item xs={12} md={filter.type === 'date' ? 12 : 6} lg={filter.type === 'date' ? 8 : 4} key={filter.id}>
                {renderFilterInput(filter)}
              </Grid>
            ))}
          </Grid>
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Button startIcon={<Add/>} onClick={handleAddFilterMenuOpen} size="small" disabled={filterableColumns.length === 0}>Add Filter</Button>
            <Menu anchorEl={filterMenuAnchorEl} open={Boolean(filterMenuAnchorEl)} onClose={handleAddFilterMenuClose}>
                {filterableColumns.map(col => (
                    <MenuItem key={String(col.id)} onClick={() => addFilterToVisible(col)}>
                        {col.label}
                    </MenuItem>
                ))}
                {filterableColumns.length === 0 && <MenuItem disabled>No more filters to add</MenuItem>}
            </Menu>
            <Box sx={{display:'flex', gap:1}}>
                <Tooltip title="Reset all filters"><IconButton onClick={handleResetAll} size="small"><RotateLeft /></IconButton></Tooltip>
                <Button onClick={handleApply} variant="contained" size="small" disabled={visibleFilters.length === 0}>Apply Filters</Button>
            </Box>
          </Box>
        </Box>
      </Collapse>
    </Paper>
  );
};
