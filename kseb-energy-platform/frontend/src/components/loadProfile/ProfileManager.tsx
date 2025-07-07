import React, { useState } from 'react';
import {
  Box, Typography, Paper, List, ListItem, ListItemText, ListItemAvatar, Avatar,
  IconButton, Menu, MenuItem, CircularProgress, Alert, Button, Tooltip, Chip, Divider, Badge
} from '@mui/material';
import {
    BarChart, MoreVert, Refresh, DeleteOutline, Assessment, Visibility, FileDownload, CompareArrows
} from '@mui/icons-material';
// import { useGetSavedProfilesQuery, useDeleteProfileMutation } from '../../store/api/apiSlice'; // If managing via RTK Query directly here
// import { addNotification } from '../../store/slices/notificationSlice';
// import { useAppDispatch } from '../../store';

// Matches the summary structure from backend or what's cached in LoadProfileController
export interface SavedProfileSummary {
  profile_id: string;
  method: string;
  generation_time: string; // ISO string
  years_generated: number[] | { start_year: number, end_year: number }; // Adapt as per backend
  summary?: {
    peak_demand?: number;
    total_energy?: number;
    load_factor?: number;
    // Add other key stats
  };
  // filePath?: string; // Path might be sensitive to expose directly, but useful for actions
}

interface ProfileManagerProps {
  savedProfiles: SavedProfileSummary[];
  isLoading: boolean;
  error?: any; // Error object from RTK Query
  onRefresh: () => void;
  onSelectProfile?: (profileId: string) => void; // For viewing details
  onDeleteProfile?: (profileId: string) => Promise<void>; // For deleting
  onAnalyzeProfile?: (profileId: string) => void;
  onCompareProfiles?: (profileIds: string[]) => void;
  activeGenerationJobId?: string | null; // To highlight or indicate status
}

export const ProfileManager: React.FC<ProfileManagerProps> = ({
  savedProfiles,
  isLoading,
  error,
  onRefresh,
  onSelectProfile,
  onDeleteProfile,
  onAnalyzeProfile,
  onCompareProfiles,
  activeGenerationJobId
}) => {
  // const dispatch = useAppDispatch(); // If dispatching notifications locally
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedProfileForMenu, setSelectedProfileForMenu] = useState<SavedProfileSummary | null>(null);
  const [profilesToCompare, setProfilesToCompare] = useState<Set<string>>(new Set());

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, profile: SavedProfileSummary) => {
    setAnchorEl(event.currentTarget);
    setSelectedProfileForMenu(profile);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedProfileForMenu(null);
  };

  const handleDelete = async () => {
    if (selectedProfileForMenu && onDeleteProfile) {
      try {
        await onDeleteProfile(selectedProfileForMenu.profile_id);
        // dispatch(addNotification({ type: 'success', message: `Profile ${selectedProfileForMenu.profile_id} deleted.` }));
      } catch (err) {
        // dispatch(addNotification({ type: 'error', message: `Failed to delete profile: ${(err as Error).message}` }));
      }
    }
    handleMenuClose();
  };

  const toggleCompareSelection = (profileId: string) => {
    setProfilesToCompare(prev => {
        const newSet = new Set(prev);
        if (newSet.has(profileId)) {
            newSet.delete(profileId);
        } else {
            newSet.add(profileId);
        }
        return newSet;
    });
  };

  const handleStartComparison = () => {
    if (onCompareProfiles && profilesToCompare.size >= 2) {
        onCompareProfiles(Array.from(profilesToCompare));
        setProfilesToCompare(new Set()); // Clear selection after starting comparison
    } else {
        // dispatch(addNotification({type: 'warning', message: 'Select at least two profiles to compare.'}));
        alert('Select at least two profiles to compare.');
    }
  };


  let content;
  if (isLoading) {
    content = <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>;
  } else if (error) {
    content = <Alert severity="error" sx={{m:1}}>Error loading saved profiles: {error.message || 'Unknown error'}</Alert>;
  } else if (savedProfiles.length === 0) {
    content = <Alert severity="info" sx={{m:1}}>No saved load profiles found. Generate a new profile to see it here.</Alert>;
  } else {
    content = (
      <List dense sx={{ maxHeight: 500, overflowY: 'auto', p:0 }}>
        {savedProfiles.map((profile) => {
          const isComparing = profilesToCompare.has(profile.profile_id);
          return (
            <ListItem
              key={profile.profile_id}
              secondaryAction={
                <IconButton edge="end" aria-label="actions" onClick={(e) => handleMenuOpen(e, profile)}>
                  <MoreVert />
                </IconButton>
              }
              sx={{
                borderBottom: '1px solid', borderColor: 'divider',
                backgroundColor: isComparing ? 'action.selected' : 'transparent',
                '&:last-child': { borderBottom: 'none' }
              }}
              button // Makes the whole item clickable for selection or detail view
              onClick={() => onSelectProfile ? onSelectProfile(profile.profile_id) : toggleCompareSelection(profile.profile_id)}
            >
              <ListItemAvatar>
                <Tooltip title={profile.method || 'Profile'}>
                    <Avatar sx={{bgcolor: profile.method === 'base_scaling' ? 'primary.light': 'secondary.light'}}>
                        <BarChart />
                    </Avatar>
                </Tooltip>
              </ListItemAvatar>
              <ListItemText
                primary={
                    <Box sx={{display: 'flex', alignItems: 'center'}}>
                        <Typography variant="subtitle1" component="span" noWrap sx={{maxWidth: 120, overflow:'hidden', textOverflow:'ellipsis'}}>
                            {profile.profile_id}
                        </Typography>
                        {activeGenerationJobId === profile.profile_id && (
                            <Chip label="Generating..." size="small" color="info" sx={{ml:1}}/>
                        )}
                    </Box>
                }
                secondary={
                  <>
                    Method: {profile.method || 'N/A'} | Years: {Array.isArray(profile.years_generated) ? profile.years_generated.join(', ') : `${profile.years_generated?.start_year}-${profile.years_generated?.end_year}`}
                    <br />
                    Generated: {new Date(profile.generation_time).toLocaleDateString()}
                    {profile.summary?.peak_demand && ` | Peak: ${profile.summary.peak_demand.toFixed(0)} MW`}
                  </>
                }
              />
            </ListItem>
          );
        })}
      </List>
    );
  }

  return (
    <Paper elevation={1} sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 300 }}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6">Saved Load Profiles</Typography>
        <Tooltip title="Refresh Profile List">
          <IconButton onClick={onRefresh} size="small" disabled={isLoading}>
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>
      {content}
      <Divider/>
      <Box sx={{p:1, mt:'auto', display:'flex', justifyContent:'flex-end'}}>
        <Badge badgeContent={profilesToCompare.size} color="primary" sx={{mr:1}}>
            <Button
                variant="outlined"
                size="small"
                startIcon={<CompareArrows/>}
                onClick={handleStartComparison}
                disabled={profilesToCompare.size < 2 || !onCompareProfiles}
            >
                Compare Selected
            </Button>
        </Badge>
      </Box>

      {selectedProfileForMenu && (
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={() => { onSelectProfile?.(selectedProfileForMenu.profile_id); handleMenuClose(); }}>
            <Visibility sx={{mr:1}} fontSize="small"/> View Details
          </MenuItem>
          <MenuItem onClick={() => { onAnalyzeProfile?.(selectedProfileForMenu.profile_id); handleMenuClose(); }}>
            <Assessment sx={{mr:1}} fontSize="small"/> Analyze
          </MenuItem>
          <MenuItem onClick={() => {/* TODO: Implement download */ alert('Download not implemented'); handleMenuClose();}}>
            <FileDownload sx={{mr:1}} fontSize="small"/> Download Data
          </MenuItem>
          <Divider/>
          <MenuItem onClick={handleDelete} sx={{color: 'error.main'}} disabled={!onDeleteProfile}>
            <DeleteOutline sx={{mr:1}} fontSize="small"/> Delete Profile
          </MenuItem>
        </Menu>
      )}
    </Paper>
  );
};
