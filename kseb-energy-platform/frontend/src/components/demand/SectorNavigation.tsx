import React from 'react';
import { Tabs, Tab, Box, Chip, Tooltip, Typography, Icon } from '@mui/material';
import { SvgIconComponent } from '@mui/icons-material'; // For type definition

export type QualityColor = 'success' | 'warning' | 'error' | 'default';

export interface SectorQualityData {
    score: number; // 0.0 to 1.0
    issues: string[];
}

interface SectorInfo {
    id: string;
    label: string;
    icon?: React.ReactElement<SvgIconComponent>; // MUI Icon component
}

interface SectorNavigationProps {
  sectors: SectorInfo[];
  selectedSector: string;
  onSectorChange: (sectorId: string) => void;
  getSectorQuality: (sectorId: string) => SectorQualityData;
  getQualityColor: (score: number) => QualityColor;
}

export const SectorNavigation: React.FC<SectorNavigationProps> = ({
  sectors,
  selectedSector,
  onSectorChange,
  getSectorQuality,
  getQualityColor,
}) => {
  const handleChange = (event: React.SyntheticEvent, newValue: string) => {
    onSectorChange(newValue);
  };

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
      <Tabs
        value={selectedSector}
        onChange={handleChange}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="Demand sectors navigation"
      >
        {sectors.map((sector) => {
          const quality = getSectorQuality(sector.id);
          const qualityColor = getQualityColor(quality.score);
          const tooltipTitle = (
            <React.Fragment>
              <Typography color="inherit" variant="subtitle2">{`Data Quality: ${(quality.score * 100).toFixed(0)}%`}</Typography>
              {quality.issues.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {quality.issues.map((issue, index) => (
                    <li key={index}><Typography variant="caption">{issue}</Typography></li>
                  ))}
                </ul>
              )}
            </React.Fragment>
          );

          return (
            <Tab
              key={sector.id}
              value={sector.id}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  {sector.icon && React.cloneElement(sector.icon as React.ReactElement<any>, { sx: { mr: 1 } })}
                  {sector.label}
                  <Tooltip title={tooltipTitle} placement="top" arrow>
                    <Chip
                      size="small"
                      label={`${(quality.score * 100).toFixed(0)}%`}
                      color={qualityColor}
                      sx={{ ml: 1.5, cursor: 'help', opacity: 0.8 }}
                    />
                  </Tooltip>
                </Box>
              }
              sx={{ textTransform: 'none', fontWeight: 'medium' }}
            />
          );
        })}
      </Tabs>
    </Box>
  );
};
