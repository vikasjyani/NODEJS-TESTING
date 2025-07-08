import React, { useState, useEffect } from 'react';
import { Box, TextField, Button, Grid, Typography, Paper, Autocomplete, Chip, Collapse, IconButton, Tooltip, Menu, MenuItem, Checkbox, ListItemText } from '@mui/material';
// import { DateRangePicker, LocalizationProvider, DateRange } from '@mui/x-date-pickers-pro'; // Commented out
// import { AdapterDateFns } from '@mui/x-date-pickers-pro/AdapterDateFns'; // Commented out
import { FilterList, FilterListOff, RotateLeft } from '@mui/icons-material';

export interface ChartFilterValues {
  // dateRange?: DateRange<Date>; // Commented out
  dateRange?: [Date | null, Date | null]; // Using simple tuple for now
  selectedCategories?: string[];
  valueRange?: { min?: number; max?: number };
  [key: string]: any;
}

interface FilterOption {
  id: string;
  label: string;
  type: 'date_range_placeholder' | 'category_select' | 'value_range' | 'custom_text'; // Changed 'date_range'
  options?: string[];
  min?: number;
  max?: number;
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
        // if (f.type === 'date_range') resetValues[f.id] = [null, null] as DateRange<Date>; // Commented out
        if (f.type === 'date_range_placeholder') resetValues[f.id] = [null, null] as [Date | null, Date | null];
        else if (f.type === 'category_select') resetValues[f.id] = [];
        else if (f.type === 'value_range') resetValues[f.id] = { min: undefined, max: undefined };
        else resetValues[f.id] = '';
    });
    setInternalFilters(resetValues);
    if (onResetFilters) {
        onResetFilters();
    } else {
        onFilterChange(resetValues);
    }
  };

  const togglePanel = () => setIsPanelOpen(prev => !prev);

  const renderFilterField = (filter: FilterOption) => {
    switch (filter.type) {
      case 'date_range_placeholder': // Was 'date_range'
        // Placeholder for DateRangePicker
        return (
            <Box sx={{display: 'flex', gap: 1}}>
                 <TextField
                    label={`${filter.label} Start (Placeholder)`}
                    type="date"
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    fullWidth
                    value={internalFilters[filter.id]?.[0] ? (internalFilters[filter.id][0] as Date).toISOString().split('T')[0] : ''}
                    onChange={(e) => {
                        const currentDateRange = (internalFilters[filter.id] as [Date | null, Date | null]) || [null, null];
                        handleInputChange(filter.id, [e.target.value ? new Date(e.target.value) : null, currentDateRange[1]]);
                    }}
                />
                 <TextField
                    label={`${filter.label} End (Placeholder)`}
                    type="date"
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    fullWidth
                    value={internalFilters[filter.id]?.[1] ? (internalFilters[filter.id][1] as Date).toISOString().split('T')[0] : ''}
                    onChange={(e) => {
                        const currentDateRange = (internalFilters[filter.id] as [Date | null, Date | null]) || [null, null];
                        handleInputChange(filter.id, [currentDateRange[0], e.target.value ? new Date(e.target.value) : null]);
                    }}
                />
            </Box>
        );
        // return ( // Original DateRangePicker code commented out
        //   <LocalizationProvider dateAdapter={AdapterDateFns}>
        //     <DateRangePicker
        //       value={internalFilters[filter.id] as DateRange<Date> || [null, null]}
        //       onChange={(newValue: DateRange<Date>) => handleInputChange(filter.id, newValue)}
        //       renderInput={(startProps: any, endProps: any) => (
        //         <>
        //           <TextField {...startProps} label={`${filter.label} Start`} size="small" fullWidth sx={{mr:1}}/>
        //           <TextField {...endProps} label={`${filter.label} End`} size="small" fullWidth />
        //         </>
        //       )}
        //     />
        //   </LocalizationProvider>
        // );
      case 'category_select':
        return (
          <Autocomplete
            multiple
            size="small"
            options={filter.options || []}
            value={internalFilters[filter.id] as string[] || []}
            onChange={(event, newValue: string[]) => handleInputChange(filter.id, newValue)} // Typed newValue
            renderTags={(value: readonly string[], getTagProps) => // Typed value
              value.map((option: string, index: number) => ( // Typed option and index
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
    return null;
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
                <Grid item xs={12} sm={6} md={filter.type === 'date_range_placeholder' ? 12 : (filter.type === 'category_select' ? 6 : 4)} key={filter.id}>
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
