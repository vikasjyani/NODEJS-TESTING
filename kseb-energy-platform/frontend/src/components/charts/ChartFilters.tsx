import React, { useState, useEffect } from 'react';
import { Box, TextField, Button, Grid, Typography, Paper, Autocomplete, Chip, Collapse, IconButton, Tooltip } from '@mui/material';
import { DateRangePicker, LocalizationProvider, DateRange } from '@mui/x-date-pickers-pro';
import { AdapterDateFns } from '@mui/x-date-pickers-pro/AdapterDateFns';
import { FilterList, FilterListOff, RotateLeft } from '@mui/icons-material';

export interface ChartFilterValues {
  dateRange?: DateRange<Date>;
  selectedCategories?: string[]; // For categorical filtering
  valueRange?: { min?: number; max?: number }; // For numerical filtering
  // Add more specific filter types as needed
  [key: string]: any; // Allow for custom filters
}

interface FilterOption {
  id: string;
  label: string;
  type: 'date_range' | 'category_select' | 'value_range' | 'custom_text';
  options?: string[]; // For category_select
  min?: number; // For value_range
  max?: number; // For value_range
}

interface ChartFiltersProps {
  availableFilters: FilterOption[];
  currentFilters: ChartFilterValues;
  onFilterChange: (newFilters: ChartFilterValues) => void;
  onResetFilters?: () => void;
  showTitle?: boolean;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

export const ChartFilters: React.FC<ChartFiltersProps> = ({
  availableFilters,
  currentFilters,
  onFilterChange,
  onResetFilters,
  showTitle = true,
  collapsible = true,
  defaultOpen = false,
}) => {
  const [internalFilters, setInternalFilters] = useState<ChartFilterValues>(currentFilters);
  const [isPanelOpen, setIsPanelOpen] = useState<boolean>(defaultOpen);

  useEffect(() => {
    // Sync internal state if currentFilters prop changes from outside
    setInternalFilters(currentFilters);
  }, [currentFilters]);

  const handleInputChange = (filterId: string, value: any) => {
    setInternalFilters(prev => ({ ...prev, [filterId]: value }));
  };

  const handleApplyFilters = () => {
    onFilterChange(internalFilters);
  };

  const handleReset = () => {
    const resetValues: ChartFilterValues = {};
    availableFilters.forEach(f => {
        if (f.type === 'date_range') resetValues[f.id] = [null, null];
        else if (f.type === 'category_select') resetValues[f.id] = [];
        else if (f.type === 'value_range') resetValues[f.id] = { min: undefined, max: undefined };
        else resetValues[f.id] = '';
    });
    setInternalFilters(resetValues);
    if (onResetFilters) {
        onResetFilters(); // Call parent reset if provided
    } else {
        onFilterChange(resetValues); // Or just apply empty filters
    }
  };

  const togglePanel = () => setIsPanelOpen(prev => !prev);

  const renderFilterField = (filter: FilterOption) => {
    switch (filter.type) {
      case 'date_range':
        return (
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <DateRangePicker
              value={internalFilters[filter.id] as DateRange<Date> || [null, null]}
              onChange={(newValue) => handleInputChange(filter.id, newValue)}
              renderInput={(startProps, endProps) => (
                <>
                  <TextField {...startProps} label={`${filter.label} Start`} size="small" fullWidth sx={{mr:1}}/>
                  <TextField {...endProps} label={`${filter.label} End`} size="small" fullWidth />
                </>
              )}
            />
          </LocalizationProvider>
        );
      case 'category_select':
        return (
          <Autocomplete
            multiple
            size="small"
            options={filter.options || []}
            value={internalFilters[filter.id] as string[] || []}
            onChange={(event, newValue) => handleInputChange(filter.id, newValue)}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => (
                <Chip label={option} {...getTagProps({ index })} size="small"/>
              ))
            }
            renderInput={(params) => (
              <TextField {...params} label={filter.label} placeholder="Select categories" />
            )}
          />
        );
      case 'value_range':
        return (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              type="number"
              label={`${filter.label} Min`}
              size="small"
              value={(internalFilters[filter.id] as {min?:number})?.min || ''}
              onChange={(e) => handleInputChange(filter.id, { ...internalFilters[filter.id], min: e.target.value ? parseFloat(e.target.value) : undefined })}
              inputProps={{ min: filter.min, max: filter.max, step: (filter.max && filter.min) ? (filter.max - filter.min)/100 : 1 }}
              fullWidth
            />
            <TextField
              type="number"
              label={`${filter.label} Max`}
              size="small"
              value={(internalFilters[filter.id] as {max?:number})?.max || ''}
              onChange={(e) => handleInputChange(filter.id, { ...internalFilters[filter.id], max: e.target.value ? parseFloat(e.target.value) : undefined })}
              inputProps={{ min: filter.min, max: filter.max, step: (filter.max && filter.min) ? (filter.max - filter.min)/100 : 1 }}
              fullWidth
            />
          </Box>
        );
      case 'custom_text':
        return (
            <TextField
                fullWidth
                label={filter.label}
                size="small"
                value={internalFilters[filter.id] as string || ''}
                onChange={(e) => handleInputChange(filter.id, e.target.value)}
            />
        );
      default:
        return null;
    }
  };

  if (availableFilters.length === 0) {
    return null; // Don't render if no filters are defined
  }

  return (
    <Paper variant="outlined" sx={{ p: collapsible ? 0 : 2, mb: 2, borderRadius: 1 }}>
        {collapsible && (
            <Box
                onClick={togglePanel}
                sx={{
                    p:1.5, display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                    borderBottom: isPanelOpen ? 1 : 0,
                    borderColor: 'divider',
                    '&:hover': {backgroundColor: 'action.hover'}
                }}
            >
                {showTitle && <Typography variant="subtitle1" sx={{fontWeight:'medium'}}>Filters</Typography>}
                <IconButton size="small">
                    {isPanelOpen ? <FilterListOff /> : <FilterList />}
                </IconButton>
            </Box>
        )}
      <Collapse in={!collapsible || isPanelOpen}>
        <Box sx={{p:2}}>
            {!collapsible && showTitle && <Typography variant="h6" gutterBottom>Filter Options</Typography>}
            <Grid container spacing={2}>
                {availableFilters.map((filter) => (
                <Grid item xs={12} sm={6} md={filter.type === 'date_range' ? 12 : (filter.type === 'category_select' ? 6 : 4)} key={filter.id}>
                    {renderFilterField(filter)}
                </Grid>
                ))}
            </Grid>
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                <Tooltip title="Reset all filters to default">
                    <IconButton onClick={handleReset} size="small">
                        <RotateLeft />
                    </IconButton>
                </Tooltip>
                <Button onClick={handleApplyFilters} variant="contained" size="small">
                Apply Filters
                </Button>
            </Box>
        </Box>
      </Collapse>
    </Paper>
  );
};
