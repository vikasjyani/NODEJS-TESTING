import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Paper, Alert, AlertTitle } from '@mui/material';
import { ErrorOutline } from '@mui/icons-material';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(_: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ error, errorInfo });
    // You can also log the error to an error reporting service here
    // Example: logErrorToMyService(error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/'; // Or use react-router-dom navigate if available in this context
  }

  public render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            p: 3,
            textAlign: 'center',
            backgroundColor: (theme) => theme.palette.background.default,
          }}
        >
          <Paper elevation={3} sx={{ p: 4, maxWidth: 600, width: '100%' }}>
            <ErrorOutline color="error" sx={{ fontSize: 60, mb: 2 }} />
            <Typography variant="h4" component="h1" gutterBottom color="error">
              Oops! Something went wrong.
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              We're sorry for the inconvenience. An unexpected error occurred.
              Please try reloading the page or navigating back to the homepage.
            </Typography>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <Alert severity="error" sx={{ textAlign: 'left', mb: 3 }}>
                <AlertTitle>Error Details (Development Mode)</AlertTitle>
                <Typography variant="subtitle2" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {this.state.error.toString()}
                </Typography>
                {this.state.errorInfo && (
                  <Typography variant="caption" component="details" sx={{ mt: 1 }}>
                    <summary>Component Stack</summary>
                    <Box component="pre" sx={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflowY: 'auto', mt:1, p:1, bgcolor: 'grey.100', borderRadius:1 }}>
                        {this.state.errorInfo.componentStack}
                    </Box>
                  </Typography>
                )}
              </Alert>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt:2 }}>
              <Button variant="outlined" onClick={this.handleReload}>
                Reload Page
              </Button>
              <Button variant="contained" color="primary" onClick={this.handleGoHome}>
                Go to Homepage
              </Button>
            </Box>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}
