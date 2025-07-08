import React from 'react';
import { Box, Typography, Grid, Card, CardActionArea, CardContent, CardHeader, Avatar, Chip } from '@mui/material'; // Added Chip
import { Timeline, TrendingUp, BuildCircle, Functions } from '@mui/icons-material'; // Example icons

export interface GenerationMethod {
  id: 'base_scaling' | 'stl_decomposition' | 'custom_template_method' | 'statistical_sampling'; // Add more as they are implemented
  name: string;
  description: string;
  icon: React.ReactElement;
  tags: string[]; // e.g., "Simple", "Advanced", "Data-driven"
  requiresConfig?: boolean; // Does this method have a detailed config form?
  requiresTemplateUpload?: boolean; // Does it need a specific template?
}

const AVAILABLE_METHODS: GenerationMethod[] = [
  {
    id: 'base_scaling',
    name: 'Base Year Scaling',
    description: 'Scales a historical or typical load profile based on projected annual energy or peak demand. Simple and quick.',
    icon: <TrendingUp color="primary"/>,
    tags: ['Simple', 'Scaling', 'Annual Projections'],
    requiresConfig: true,
  },
  {
    id: 'stl_decomposition',
    name: 'STL Decomposition',
    description: 'Decomposes historical load data into trend, seasonal, and residual components, then projects them forward. Captures complex patterns.',
    icon: <Timeline color="secondary"/>,
    tags: ['Advanced', 'Time Series', 'Pattern Recognition'],
    requiresConfig: true,
  },
  {
    id: 'custom_template_method',
    name: 'Custom Template Upload',
    description: 'Upload your own hourly load profile template (e.g., Excel, CSV) to be used as a base or for direct analysis.',
    icon: <BuildCircle sx={{color: "success.main"}}/>,
    tags: ['Custom Data', 'Template-based'],
    requiresTemplateUpload: true,
  },
    {
    id: 'statistical_sampling',
    name: 'Statistical Sampling',
    description: 'Generates profiles by sampling from statistical distributions of load characteristics (e.g., Monte Carlo). Useful for uncertainty analysis.',
    icon: <Functions sx={{color: "warning.main"}}/>,
    tags: ['Probabilistic', 'Stochastic', 'Uncertainty'],
    requiresConfig: true,
  },
];

interface MethodSelectionProps {
  onMethodSelect: (method: GenerationMethod) => void;
  selectedMethodId?: string | null;
}

export const MethodSelection: React.FC<MethodSelectionProps> = ({ onMethodSelect, selectedMethodId }) => {
  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="subtitle1" gutterBottom sx={{mb:2}}>
        Choose a method to generate your load profile:
      </Typography>
      <Grid container spacing={3}>
        {AVAILABLE_METHODS.map((method) => (
          <Grid item xs={12} sm={6} md={4} key={method.id}>
            <Card
                variant="outlined"
                sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    borderColor: selectedMethodId === method.id ? 'primary.main' : undefined,
                    boxShadow: selectedMethodId === method.id ? (theme) => `0 0 0 2px ${theme.palette.primary.main}`: 'none',
                    '&:hover': {
                        boxShadow: (theme) => `0 4px 12px ${theme.palette.action.hover}`,
                    }
                }}
            >
              <CardActionArea onClick={() => onMethodSelect(method)} sx={{flexGrow:1, display: 'flex', flexDirection:'column', alignItems:'flex-start'}}>
                <CardHeader
                    avatar={<Avatar sx={{ bgcolor: 'transparent', color: 'text.primary' }}>{method.icon}</Avatar>}
                    title={<Typography variant="h6" component="div">{method.name}</Typography>}
                    sx={{width: '100%', pb:0}}
                />
                <CardContent sx={{flexGrow:1}}>
                  <Typography variant="body2" color="text.secondary">
                    {method.description}
                  </Typography>
                  <Box sx={{ mt: 1.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {method.tags.map(tag => <Chip key={tag} label={tag} size="small" variant="outlined" />)}
                  </Box>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};
