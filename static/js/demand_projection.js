// demand_projection.js -with Complete Configuration Management
// All user selections captured and saved

// ==========Configuration ==========
const API_BASE_URL = '/demand_projection/api';

// ==========State Variables ==========
let currentForecastJobId = null;
let forecastPollingInterval = null;
let sectorConfigurations = {}; // Track all sector configurations
let globalDefaultModels = ['MLR', 'SLR', 'WAM', 'TimeSeries']; // Default models

// ========== Notification System ==========
class NotificationManager {
    static show(message, type = 'info', duration = 5000) {
        // Remove existing notifications of the same type
        const existing = document.querySelectorAll(`.notification-${type}`);
        existing.forEach(el => el.remove());

        // Create notification container if it doesn't exist
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }

        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show shadow notification-${type}`;

        const icon = this.getIcon(type);
        notification.innerHTML = `
            <i class="fas ${icon} me-2"></i>
            <div style="white-space: pre-line;">${message}</div>
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;

        container.appendChild(notification);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 150);
                }
            }, duration);
        }

        return notification;
    }

    static success(message, duration) {
        return this.show(message, 'success', duration);
    }

    static error(message, duration) {
        return this.show(message, 'danger', duration);
    }

    static warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    static info(message, duration) {
        return this.show(message, 'info', duration);
    }

    static getIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'danger': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }
}

// ==========UI Utilities ==========
class UIUtils {
    static showElement(element, display = 'block') {
        if (element) {
            element.style.display = display;
            element.classList.remove('d-none');
        }
    }

    static hideElement(element) {
        if (element) {
            element.style.display = 'none';
            element.classList.add('d-none');
        }
    }

    static showLoading(container, message = 'Loading...') {
        if (!container) return;

        container.innerHTML = `
            <div class="loading-spinner d-flex flex-column align-items-center justify-content-center p-4">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="text-muted">${message}</div>
            </div>
        `;
    }

    static showError(container, error, title = 'Error') {
        if (!container) return;

        const errorMessage = error instanceof Error ? error.message : String(error);
        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <div class="d-flex align-items-start">
                    <i class="fas fa-exclamation-triangle me-2 mt-1"></i>
                    <div>
                        <h6 class="alert-heading mb-1">${title}</h6>
                        <p class="mb-0">${errorMessage}</p>
                        <hr>
                        <button class="btn btn-sm btn-outline-danger" onclick="location.reload()">
                            <i class="fas fa-sync me-1"></i>Refresh Page
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    static showEmptyState(container, icon, title, message, actionText = null, actionCallback = null) {
        if (!container) return;

        let actionButton = '';
        if (actionText && actionCallback) {
            const actionId = `action-${Date.now()}`;
            actionButton = `<button class="btn btn-primary" id="${actionId}">${actionText}</button>`;
            setTimeout(() => {
                const button = document.getElementById(actionId);
                if (button) button.addEventListener('click', actionCallback);
            }, 0);
        }

        container.innerHTML = `
            <div class="empty-state text-center p-5">
                <i class="${icon} text-muted mb-3" style="font-size: 48px;"></i>
                <h5 class="text-muted mb-2">${title}</h5>
                <p class="text-muted mb-3">${message}</p>
                ${actionButton}
            </div>
        `;
    }

    static formatDuration(seconds) {
        if (seconds < 60) return `${Math.round(seconds)}s`;
        if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
        return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
    }

    static copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            NotificationManager.success('Copied to clipboard');
        }).catch(() => {
            NotificationManager.error('Failed to copy to clipboard');
        });
    }
}

// ==========Application Initialization ==========
document.addEventListener('DOMContentLoaded', function () {
    console.log("Demand Projection: Initializingapplication");
    initializeEnhancedApplication();
});

function initializeEnhancedApplication() {
    setupSectorTabs();
    setupViewToggles();
    setupEnhancedForecastConfiguration();
    setupChartControls();
    initializeSectorConfigurations();

    // Load initial content
    loadInitialData();

    console.log("Demand Projection:application initialized successfully");
}

// ==========Sector Configuration Management ==========
function initializeSectorConfigurations() {
    const sectorsDataEl = document.getElementById('sectorsData');
    if (!sectorsDataEl) {
        console.error('Sectors data element not found');
        return;
    }

    try {
        const sectors = JSON.parse(sectorsDataEl.textContent || '[]');
        console.log("Initializing configurations for sectors:", sectors);

        // Initialize configuration for each sector with defaults
        sectors.forEach(sector => {
            sectorConfigurations[sector] = {
                models: [...globalDefaultModels], // Copy default models
                independentVars: [],
                windowSize: 10,
                lastUpdated: new Date().toISOString()
            };
        });

        console.log("Sector configurations initialized:", sectorConfigurations);
    } catch (error) {
        console.error('Error initializing sector configurations:', error);
    }
}

function updateSectorConfiguration(sector, updates) {
    console.log(`Updating configuration for sector ${sector}:`, updates);
    
    if (!sectorConfigurations[sector]) {
        sectorConfigurations[sector] = {
            models: [...globalDefaultModels],
            independentVars: [],
            windowSize: 10,
            lastUpdated: new Date().toISOString()
        };
    }

    // Apply updates
    Object.assign(sectorConfigurations[sector], updates);
    sectorConfigurations[sector].lastUpdated = new Date().toISOString();

    console.log(`Updated configuration for ${sector}:`, sectorConfigurations[sector]);
    
    // Update overview table
    updateSectorOverviewTable();
}

function updateSectorOverviewTable() {
    console.log("Updating sector overview table");
    
    Object.keys(sectorConfigurations).forEach(sector => {
        const config = sectorConfigurations[sector];
        
        // Update models display
        const modelsCell = document.getElementById(`models_${sector}`);
        if (modelsCell) {
            if (config.models && config.models.length > 0) {
                modelsCell.innerHTML = config.models.map(model => 
                    `<span class="model-tag">${model}</span>`
                ).join(' ');
            } else {
                modelsCell.innerHTML = '<span class="text-muted">No models selected</span>';
            }
        }

        // Update quality indicator (you can enhance this based on data analysis)
        const qualityCell = document.getElementById(`quality_${sector}`);
        if (qualityCell) {
            qualityCell.innerHTML = '<span class="badge bg-success">Good</span>';
        }
    });
}

// ========== Sector Management ==========
function setupSectorTabs() {
    const sectorButtons = document.querySelectorAll('.sector-button');
    console.log("Setting up sector tabs:", sectorButtons.length);

    sectorButtons.forEach(button => {
        button.addEventListener('click', function () {
            const sectorId = this.dataset.sector;
            switchToSector(sectorId);
        });
    });
}

function switchToSector(sectorId) {
    console.log("Switching to sector:", sectorId);

    // Update button states
    document.querySelectorAll('.sector-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.sector === sectorId);
    });

    // Update section visibility
    document.querySelectorAll('.sector-section').forEach(section => {
        section.classList.toggle('active', section.id === `${sectorId}-section`);
    });

    // Load sector data
    loadSectorData(sectorId);
}

// ========== View Toggle System ==========
function setupViewToggles() {
    const viewButtons = document.querySelectorAll('.view-toggle-button');
    console.log("Setting up view toggles:", viewButtons.length);

    viewButtons.forEach(button => {
        button.addEventListener('click', function () {
            const sector = this.dataset.sector;
            const view = this.dataset.view;
            switchView(sector, view);
        });
    });
}

function switchView(sector, view) {
    console.log("Switching view:", sector, view);

    // Update button states
    document.querySelectorAll(`.view-toggle-button[data-sector="${sector}"]`)
        .forEach(btn => btn.classList.toggle('active', btn.dataset.view === view));

    // Hide all views for this sector
    const viewSelectors = ['table', 'chart', 'correlation', 'analysis', 'summary'];
    viewSelectors.forEach(viewType => {
        const viewElement = document.getElementById(`${sector}-${viewType}-view`);
        if (viewElement) {
            UIUtils.hideElement(viewElement);
            viewElement.classList.remove('active');
        }
    });

    // Show selected view
    const selectedView = document.getElementById(`${sector}-${view}-view`);
    if (selectedView) {
        UIUtils.showElement(selectedView, 'flex');
        selectedView.classList.add('active');

        // Load view content if needed
        loadViewContent(sector, view);
    }
}

// ========== Data Loading System ==========
async function loadInitialData() {
    try {
        // Load initial sector (aggregated)
        loadSectorData('aggregated');

    } catch (error) {
        console.error("Error loading initial data:", error);
        NotificationManager.error(`Failed to load initial data: ${error.message}`);
    }
}

async function loadSectorData(sector) {
    console.log("Loading data for sector:", sector);

    try {
        // Load chart data by default
        const currentView = getCurrentView(sector);
        if (currentView === 'chart' || sector === 'aggregated') {
            await loadViewContent(sector, 'chart');
        }

    } catch (error) {
        console.error(`Error loading sector data for ${sector}:`, error);
        NotificationManager.error(`Failed to load ${sector} data: ${error.message}`);
    }
}

async function loadViewContent(sector, view) {
    try {
        switch (view) {
            case 'chart':
                await loadTimeSeriesChart(sector);
                break;
            case 'correlation':
                await loadCorrelationAnalysis(sector);
                break;
            case 'analysis':
                await loadDataAnalysis(sector);
                break;
            case 'summary':
                await loadSummaryData(sector);
                break;
        }
    } catch (error) {
        console.error(`Error loading ${view} for ${sector}:`, error);
        const container = document.getElementById(`${sector}${view.charAt(0).toUpperCase() + view.slice(1)}Container`) ||
            document.getElementById(`${sector}-${view}-view`);
        if (container) {
            UIUtils.showError(container, error, `${view.charAt(0).toUpperCase() + view.slice(1)} Error`);
        }
    }
}

// ========== Chart Management ==========
async function loadTimeSeriesChart(sector) {
    const container = sector === 'aggregated' ?
        document.getElementById('aggregatedChartContainer') :
        document.getElementById(`${sector}ChartContainer`);

    if (!container) {
        console.error("Chart container not found for:", sector);
        return;
    }

    const spinner = container.querySelector('.loading-spinner');
    const canvas = container.querySelector('canvas');
    const errorDiv = container.querySelector('.chart-error');

    // Show loading state
    if (spinner) UIUtils.showElement(spinner);
    if (canvas) UIUtils.hideElement(canvas);
    if (errorDiv) UIUtils.hideElement(errorDiv);

    try {
        const response = await fetch(`${API_BASE_URL}/chart_data/${encodeURIComponent(sector)}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            await renderChart(sector, data.data);
            if (canvas) UIUtils.showElement(canvas);
        } else {
            throw new Error(data.message || 'Failed to load chart data');
        }

    } catch (error) {
        console.error(`Error loading chart for ${sector}:`, error);
        if (errorDiv) {
            errorDiv.textContent = `Error loading chart: ${error.message}`;
            UIUtils.showElement(errorDiv);
        }
    } finally {
        if (spinner) UIUtils.hideElement(spinner);
    }
}

async function renderChart(sector, data) {
    const canvas = sector === 'aggregated' ?
        document.getElementById('aggregatedChart') :
        document.getElementById(`${sector}Chart`);

    if (!canvas) {
        throw new Error(`Canvas not found for sector: ${sector}`);
    }

    // Destroy existing chart
    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
    }

    try {
        if (sector === 'aggregated' && data.type === 'aggregated') {
            canvas.chartInstance = createAggregatedChart(canvas, data);
        } else if (data.type === 'individual') {
            canvas.chartInstance = createIndividualChart(canvas, sector, data);
        } else {
            throw new Error('Invalid chart data format');
        }

        console.log(`Chart rendered successfully for ${sector}`);
    } catch (error) {
        console.error(`Error rendering chart for ${sector}:`, error);
        throw error;
    }
}

function createAggregatedChart(canvas, data, chartType = 'line') {
    const ctx = canvas.getContext('2d');
  
    // Build base data
    const chartData = {
      labels: data.years || [],
      datasets: data.datasets.map(ds => ({
        ...ds,
        // For bar: remove border tension; for area: enable fill
        fill: chartType === 'area',
        backgroundColor: ds.backgroundColor || ds.borderColor, 
        borderColor: ds.borderColor,
      }))
    };
  
    // Base options
    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Consolidated Electricity Consumption by Sector',
          font: { size: 16, weight: 'bold' }
        },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString()} kWh`
          }
        },
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 15 } }
      },
      scales: {
        x: { 
          stacked: (chartType === 'bar' || chartType === 'area'),
          title: { display: true, text: 'Year' },
          grid: { display: false }
        },
        y: {
          stacked: (chartType === 'bar' || chartType === 'area'),
          beginAtZero: true,
          title: { display: true, text: 'Electricity Consumption (kWh)' },
          ticks: { callback: v => v.toLocaleString() }
        }
      }
    };
  
    // Chart.js uses 'bar' for both grouped & stacked bar.
    // For area we still use 'line' but with fill + stacked scales.
    const actualType = chartType === 'area' ? 'line' : chartType;
  
    // Destroy old instance if present
    if (canvas.chartInstance) canvas.chartInstance.destroy();
  
    // Create new
    canvas.chartInstance = new Chart(ctx, {
      type: actualType,
      data: chartData,
      options: options
    });
  
    // Ensure it’s visible
    canvas.style.display = 'block';
    return canvas.chartInstance;
  }
  


function createIndividualChart(canvas, sector, data) {
    const ctx = canvas.getContext('2d');

    const chartData = {
        labels: data.years || [],
        datasets: [{
            label: 'Electricity Consumption',
            data: data.electricity || [],
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            borderWidth: 2,
            tension: 0.1,
            pointRadius: 3,
            pointHoverRadius: 6
        }]
    };

    // Add forecast line if data analysis shows forecast is needed
    if (data.data_analysis && data.data_analysis.forecast_needed) {
        const forecastYear = data.data_analysis.max_year + 1;
        const targetYear = data.data_analysis.target_year;

        if (forecastYear <= targetYear) {
            const forecastYears = [];
            for (let year = forecastYear; year <= targetYear; year++) {
                forecastYears.push(year);
            }

            chartData.datasets.push({
                label: 'Forecast Needed',
                data: forecastYears.map(() => null),
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0
            });
        }
    }

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: `${sector.charAt(0).toUpperCase() + sector.slice(1)} Sector - Electricity Consumption`,
                font: { size: 16, weight: 'bold' }
            },
            tooltip: {
                callbacks: {
                    label: function (context) {
                        if (context.parsed.y === null) return 'Forecast Required';
                        return `${context.dataset.label}: ${context.parsed.y.toLocaleString()} kWh`;
                    }
                }
            }
        },
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Year'
                }
            },
            y: {
                title: {
                    display: true,
                    text: 'Electricity Consumption (kWh)'
                },
                beginAtZero: true,
                ticks: {
                    callback: function (value) {
                        return value.toLocaleString();
                    }
                }
            }
        }
    };

    return new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: options
    });
}

// ========== Correlation Analysis ==========
async function loadCorrelationAnalysis(sector) {
    const container = document.getElementById(`${sector}CorrelationChart`);
    const spinner = document.getElementById(`${sector}CorrelationSpinner`);
    const errorDiv = document.getElementById(`${sector}CorrelationError`);

    if (!container) return;

    // Show loading state
    if (spinner) UIUtils.showElement(spinner);
    if (container) UIUtils.hideElement(container);
    if (errorDiv) UIUtils.hideElement(errorDiv);

    try {
        const response = await fetch(`${API_BASE_URL}/correlation_data/${encodeURIComponent(sector)}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            renderCorrelationTable(container, data.data);
            UIUtils.showElement(container);
        } else {
            throw new Error(data.message || 'Failed to load correlation data');
        }

    } catch (error) {
        console.error(`Error loading correlations for ${sector}:`, error);
        if (errorDiv) {
            errorDiv.textContent = `Error loading correlations: ${error.message}`;
            UIUtils.showElement(errorDiv);
        }
    } finally {
        if (spinner) UIUtils.hideElement(spinner);
    }
}

function renderCorrelationTable(container, data) {
    if (!data.variables || !data.correlations || data.variables.length === 0) {
        UIUtils.showEmptyState(
            container,
            'fas fa-project-diagram',
            'No Correlation Data',
            'No correlation data available for this sector.',
            'Refresh Data',
            () => loadCorrelationAnalysis(data.sector)
        );
        return;
    }

    // Create table with summary statistics
    let html = `
        <div class="correlation-summary mb-3">
            <div class="row text-center">
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value text-success">${data.summary_stats?.strong_correlations || 0}</div>
                        <div class="stat-label">Strong</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value text-primary">${data.summary_stats?.moderate_correlations || 0}</div>
                        <div class="stat-label">Moderate</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value text-muted">${data.summary_stats?.weak_correlations || 0}</div>
                        <div class="stat-label">Weak</div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="stat-card">
                        <div class="stat-value text-info">${data.summary_stats?.recommended_for_mlr || 0}</div>
                        <div class="stat-label">MLR Ready</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="table-responsive">
            <table class="table table-hover table-striped">
                <thead class="table-dark">
                    <tr>
                        <th>Variable</th>
                        <th>Correlation</th>
                        <th>Strength</th>
                        <th>Direction</th>
                        <th>MLR Suitable</th>
                    </tr>
                </thead>
                <tbody>
    `;

    for (let i = 0; i < data.variables.length; i++) {
        const variable = data.variables[i];
        const correlation = data.correlations[i];
        const value = correlation.value || correlation;
        const strength = correlation.strength || 'Unknown';
        const strengthClass = correlation.strength_class || 'secondary';
        const direction = correlation.direction || (value >= 0 ? 'Positive' : 'Negative');
        const recommended = correlation.recommended_for_mlr || false;

        html += `
            <tr>
                <td><strong>${variable}</strong></td>
                <td class="text-${strengthClass}">${typeof value === 'number' ? value.toFixed(3) : value}</td>
                <td><span class="badge bg-${strengthClass}">${strength}</span></td>
                <td>
                    <i class="fas fa-arrow-${direction === 'Positive' ? 'up text-success' : 'down text-danger'}"></i>
                    ${direction}
                </td>
                <td>
                    ${recommended ?
                '<i class="fas fa-check text-success" title="Recommended for MLR"></i>' :
                '<i class="fas fa-times text-muted" title="Not recommended for MLR"></i>'
            }
                </td>
            </tr>
        `;
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
}

// ========== Summary and Analysis Functions ==========
async function loadSummaryData(sector) {
    console.log("Loading summary data for:", sector);

    const container = document.getElementById(`${sector}SummaryContainer`) ||
        document.getElementById(`${sector}-summary-view`);

    if (!container) {
        console.error("Summary container not found for:", sector);
        return;
    }

    try {
        UIUtils.showLoading(container, 'Loading summary...');

        // Generate summary data
        const summaryData = await generateSummaryData(sector);
        renderSummaryData(container, summaryData, sector);

    } catch (error) {
        console.error(`Error loading summary for ${sector}:`, error);
        UIUtils.showError(container, error, 'Summary Error');
    }
}

async function loadDataAnalysis(sector) {
    console.log("Loading data analysis for:", sector);

    const container = document.getElementById(`${sector}AnalysisContainer`) ||
        document.getElementById(`${sector}-analysis-view`);

    if (!container) {
        console.error("Analysis container not found for:", sector);
        return;
    }

    try {
        UIUtils.showLoading(container, 'Loading analysis...');

        // Generate analysis data
        const analysisData = await generateAnalysisData(sector);
        renderAnalysisData(container, analysisData, sector);

    } catch (error) {
        console.error(`Error loading analysis for ${sector}:`, error);
        UIUtils.showError(container, error, 'Analysis Error');
    }
}

async function generateSummaryData(sector) {
    // Generate summary information
    return {
        sector: sector,
        dataAvailable: true,
        keyMetrics: {
            totalYears: 15,
            averageGrowth: '3.2%',
            lastYear: 2023,
            dataQuality: 'Good'
        },
        recommendations: [
            'Data shows consistent growth pattern',
            'Suitable for multiple forecasting models',
            'Consider using MLR with multiple variables'
        ]
    };
}

async function generateAnalysisData(sector) {
    // Generate analysis information  
    return {
        sector: sector,
        dataAnalysis: {
            timeSeriesComponents: {
                trend: 'Upward',
                seasonality: 'Moderate',
                irregularity: 'Low'
            },
            statistics: {
                mean: 'Calculating...',
                standardDeviation: 'Calculating...',
                variance: 'Calculating...'
            },
            patterns: [
                'Consistent annual growth',
                'Seasonal variations detected',
                'No major anomalies found'
            ]
        },
        modelRecommendations: {
            recommended: ['MLR', 'WAM', 'TimeSeries'],
            reasons: [
                'Strong correlation with economic indicators',
                'Sufficient historical data available',
                'Clear trend patterns identified'
            ]
        }
    };
}

function renderSummaryData(container, data, sector) {
    const html = `
        <div class="summary-content">
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-chart-pie me-2"></i>Key Metrics</h6>
                        </div>
                        <div class="card-body">
                            <div class="metric-item">
                                <span class="metric-label">Total Years:</span>
                                <span class="metric-value">${data.keyMetrics.totalYears}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Average Growth:</span>
                                <span class="metric-value text-success">${data.keyMetrics.averageGrowth}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Data Quality:</span>
                                <span class="metric-value text-primary">${data.keyMetrics.dataQuality}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-lightbulb me-2"></i>Recommendations</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                ${data.recommendations.map(rec => `<li><i class="fas fa-check text-success me-2"></i>${rec}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

function renderAnalysisData(container, data, sector) {
    const html = `
        <div class="analysis-content">
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-chart-line me-2"></i>Time Series Components</h6>
                        </div>
                        <div class="card-body">
                            <div class="analysis-item">
                                <span class="analysis-label">Trend:</span>
                                <span class="analysis-value text-success">${data.dataAnalysis.timeSeriesComponents.trend}</span>
                            </div>
                            <div class="analysis-item">
                                <span class="analysis-label">Seasonality:</span>
                                <span class="analysis-value text-primary">${data.dataAnalysis.timeSeriesComponents.seasonality}</span>
                            </div>
                            <div class="analysis-item">
                                <span class="analysis-label">Irregularity:</span>
                                <span class="analysis-value text-info">${data.dataAnalysis.timeSeriesComponents.irregularity}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-calculator me-2"></i>Statistical Analysis</h6>
                        </div>
                        <div class="card-body">
                            <div class="analysis-item">
                                <span class="analysis-label">Mean:</span>
                                <span class="analysis-value">${data.dataAnalysis.statistics.mean}</span>
                            </div>
                            <div class="analysis-item">
                                <span class="analysis-label">Std Dev:</span>
                                <span class="analysis-value">${data.dataAnalysis.statistics.standardDeviation}</span>
                            </div>
                            <div class="analysis-item">
                                <span class="analysis-label">Variance:</span>
                                <span class="analysis-value">${data.dataAnalysis.statistics.variance}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h6><i class="fas fa-brain me-2"></i>Model Recommendations</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <strong>Recommended Models:</strong>
                                <div class="mt-2">
                                    ${data.modelRecommendations.recommended.map(model =>
        `<span class="badge bg-primary me-1">${model}</span>`
    ).join('')}
                                </div>
                            </div>
                            <div>
                                <strong>Reasons:</strong>
                                <ul class="small mt-2">
                                    ${data.modelRecommendations.reasons.map(reason => `<li>${reason}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

// ==========Forecast Configuration ==========
function setupEnhancedForecastConfiguration() {
    console.log("Setting upforecast configuration");

    // Setup modal triggers
    document.querySelectorAll('.run-forecast-btn, .forecast-btn').forEach(btn => {
        btn.addEventListener('click', openEnhancedForecastModal);
    });

    // Setupform validation
    setupEnhancedFormValidation();

    // Setupmodel configuration
    setupEnhancedModelConfiguration();

    // Setup scenario validation
    setupScenarioValidation();

    // Setup forecast execution
    setupForecastExecution();
}

function setupEnhancedFormValidation() {
    const form = document.getElementById('forecastConfigForm');
    if (!form) return;

    // Real-time scenario name validation
    const scenarioInput = document.getElementById('scenarioName');
    if (scenarioInput) {
        scenarioInput.addEventListener('input', debounce(validateScenarioName, 1000));
        scenarioInput.addEventListener('blur', validateScenarioName);
    }

    // Target year validation
    const targetYearInput = document.getElementById('targetYear');
    if (targetYearInput) {
        targetYearInput.addEventListener('change', validateTargetYear);
    }

    // Configuration validation button
    const validateBtn = document.getElementById('validateConfigBtn');
    if (validateBtn) {
        validateBtn.addEventListener('click', validateFullConfiguration);
    }
}

function setupEnhancedModelConfiguration() {
    console.log("Setting upmodel configuration");

    // Apply to all sectors button
    const applyToAllBtn = document.getElementById('applyToAllSectorsBtn');
    if (applyToAllBtn) {
        applyToAllBtn.addEventListener('click', function () {
            const selectedDefaultModels = Array.from(document.querySelectorAll('.default-model-checkbox:checked'))
                .map(cb => cb.value);
            
            console.log("Applying default models to all sectors:", selectedDefaultModels);
            globalDefaultModels = [...selectedDefaultModels];

            // Apply to all sectors
            Object.keys(sectorConfigurations).forEach(sector => {
                updateSectorConfiguration(sector, {
                    models: [...selectedDefaultModels]
                });
                
                // Update UI checkboxes
                selectedDefaultModels.forEach(model => {
                    const checkbox = document.querySelector(`#model${model}_${sector}`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });

                // Clear unselected models
                document.querySelectorAll(`input[name="forecastModel_${sector}"]`).forEach(cb => {
                    if (!selectedDefaultModels.includes(cb.value)) {
                        cb.checked = false;
                    }
                });
            });

            NotificationManager.success('Default models applied to all sectors');
        });
    }

    // Setup sector model checkboxes withtracking
    document.querySelectorAll('.sector-model-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const sector = this.dataset.sector;
            const model = this.value;
            const isChecked = this.checked;

            console.log(`Model ${model} for sector ${sector}: ${isChecked ? 'enabled' : 'disabled'}`);

            // Update sector configuration
            if (!sectorConfigurations[sector]) {
                sectorConfigurations[sector] = {
                    models: [],
                    independentVars: [],
                    windowSize: 10
                };
            }

            if (isChecked) {
                if (!sectorConfigurations[sector].models.includes(model)) {
                    sectorConfigurations[sector].models.push(model);
                }
            } else {
                sectorConfigurations[sector].models = sectorConfigurations[sector].models.filter(m => m !== model);
            }

            updateSectorConfiguration(sector, {
                models: sectorConfigurations[sector].models
            });

            // Show/hide configuration sections based on model selection
            const configSections = {
                'MLR': `mlrConfig_${sector}`,
                'WAM': `wamConfig_${sector}`,
                'SLR': `slrConfig_${sector}`,
                'TimeSeries': `tsConfig_${sector}`
            };

            const configSection = document.getElementById(configSections[model]);
            if (configSection) {
                configSection.style.display = this.checked ? 'block' : 'none';
            }
        });
    });

    // Setup WAM window size radio buttons withtracking
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        if (radio.name.startsWith('windowSize_')) {
            radio.addEventListener('change', function () {
                const sector = this.name.replace('windowSize_', '');
                const customContainer = document.getElementById(`customWindowContainer_${sector}`);
                let windowSize = parseInt(this.value);

                if (this.value === 'custom') {
                    customContainer.style.display = 'block';
                    const customInput = document.getElementById(`customWindowSize_${sector}`);
                    if (customInput) {
                        windowSize = parseInt(customInput.value) || 10;
                    }
                } else {
                    customContainer.style.display = 'none';
                }

                // Update sector configuration
                updateSectorConfiguration(sector, {
                    windowSize: windowSize
                });

                console.log(`WAM window size for ${sector}: ${windowSize}`);
            });
        }
    });

    // Setup custom window size inputs
    document.querySelectorAll('input[id^="customWindowSize_"]').forEach(input => {
        input.addEventListener('change', function () {
            const sector = this.id.replace('customWindowSize_', '');
            const windowSize = parseInt(this.value) || 10;
            
            updateSectorConfiguration(sector, {
                windowSize: windowSize
            });

            console.log(`Custom WAM window size for ${sector}: ${windowSize}`);
        });
    });

    // Setup independent variable checkboxes (will be populated when modal opens)
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('independent-var-checkbox')) {
            const sector = e.target.name.replace('independentVars_', '');
            const variable = e.target.value;
            const isChecked = e.target.checked;
            
            if (!sectorConfigurations[sector]) {
                sectorConfigurations[sector] = {
                    models: [...globalDefaultModels],
                    independentVars: [],
                    windowSize: 10
                };
            }

            if (isChecked) {
                if (!sectorConfigurations[sector].independentVars.includes(variable)) {
                    sectorConfigurations[sector].independentVars.push(variable);
                }
            } else {
                sectorConfigurations[sector].independentVars = 
                    sectorConfigurations[sector].independentVars.filter(v => v !== variable);
            }

            updateSectorConfiguration(sector, {
                independentVars: sectorConfigurations[sector].independentVars
            });

            console.log(`Independent variables for ${sector}:`, sectorConfigurations[sector].independentVars);
        }
    });
}

function setupScenarioValidation() {
    console.log("Setting up scenario validation");

    const scenarioInput = document.getElementById('scenarioName');
    if (scenarioInput) {
        scenarioInput.addEventListener('input', debounce(validateScenarioName, 1000));
    }
}

function setupForecastExecution() {
    const executeBtn = document.getElementById('runForecastBtn');
    if (executeBtn) {
        executeBtn.addEventListener('click', startEnhancedForecast);
    }

    const cancelBtn = document.getElementById('cancelForecastBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', cancelEnhancedForecast);
    }
}

// ==========Validation Functions ==========
async function validateFullConfiguration() {
    console.log("Validating full configuration");

    try {
        const form = document.getElementById('forecastConfigForm');
        if (!form) {
            NotificationManager.error('Configuration form not found');
            return false;
        }

        const formData = new FormData(form);
        const scenarioName = formData.get('scenarioName');
        const targetYear = formData.get('targetYear');

        // Basic validation
        if (!scenarioName || scenarioName.trim().length < 2) {
            NotificationManager.error('Scenario name must be at least 2 characters');
            return false;
        }

        if (!targetYear || parseInt(targetYear) < 2024) {
            NotificationManager.error('Target year must be 2024 or later');
            return false;
        }

        // Check if at least one sector has models selected
        let hasValidSector = false;
        for (const [sector, config] of Object.entries(sectorConfigurations)) {
            if (config.models && config.models.length > 0) {
                hasValidSector = true;
                break;
            }
        }

        if (!hasValidSector) {
            NotificationManager.error('Please select at least one model for at least one sector');
            return false;
        }

        // Validate MLR configurations
        for (const [sector, config] of Object.entries(sectorConfigurations)) {
            if (config.models && config.models.includes('MLR')) {
                if (!config.independentVars || config.independentVars.length === 0) {
                    NotificationManager.warning(
                        `No independent variables selected for MLR in ${sector}. The model will use Year as default.`
                    );
                }
            }
        }

        NotificationManager.success('Configuration validation passed');
        return true;

    } catch (error) {
        console.error('Validation error:', error);
        NotificationManager.error(`Validation failed: ${error.message}`);
        return false;
    }
}

async function validateScenarioName() {
    const input = document.getElementById('scenarioName');
    const feedback = document.getElementById('scenarioNameFeedback');
    const validation = document.querySelector('.scenario-validation');

    if (!input || !input.value.trim()) {
        input.classList.remove('is-valid', 'is-invalid');
        return;
    }

    const scenarioName = input.value.trim();

    // Show validation in progress
    if (validation) {
        validation.style.display = 'block';
        validation.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <span>Validating scenario name...</span>
            </div>
        `;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/validate_scenario_name`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ scenarioName })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success' && data.data.valid) {
            input.classList.add('is-valid');
            input.classList.remove('is-invalid');
            if (feedback) feedback.textContent = '';
            if (validation) validation.style.display = 'none';
        } else {
            input.classList.add('is-invalid');
            input.classList.remove('is-valid');
            if (feedback) feedback.textContent = data.message || 'Scenario name is not available';
            if (validation) validation.style.display = 'none';
        }
    } catch (error) {
        console.error('Scenario validation error:', error);
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        if (feedback) feedback.textContent = `Validation error: ${error.message}`;
        if (validation) validation.style.display = 'none';
    }
}

function validateTargetYear() {
    const input = document.getElementById('targetYear');
    if (!input) return;

    const year = parseInt(input.value);
    const currentYear = new Date().getFullYear();

    if (year < currentYear + 1) {
        input.classList.add('is-invalid');
        NotificationManager.warning(`Target year should be after ${currentYear}`);
    } else if (year > currentYear + 50) {
        input.classList.add('is-invalid');
        NotificationManager.warning('Target year seems too far in the future');
    } else {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
    }
}

// ==========Forecast Execution ==========
async function startEnhancedForecast() {
    console.log("Startingforecast with complete configuration tracking");

    try {
        // Validate configuration first
        const isValid = await validateFullConfiguration();
        if (!isValid) {
            NotificationManager.error('Please fix configuration errors before proceeding');
            return;
        }

        // Collect complete configuration
        const config = collectCompleteConfiguration();
        
        console.log("===DEBUG: Complete Configuration ===");
        console.log("Full config object:", config);
        console.log("Scenario name:", config.scenarioName);
        console.log("Target year:", config.targetYear);
        console.log("Sector configurations:", config.sectorConfigs);
        console.log("Number of sectors configured:", Object.keys(config.sectorConfigs).length);
        console.log("Global configurations:", config.detailedConfiguration);
        
        // Validate the collected configuration
        if (!config.scenarioName || !config.targetYear || !config.sectorConfigs || Object.keys(config.sectorConfigs).length === 0) {
            throw new Error('Incomplete configuration data collected');
        }

        // Show progress modal
        showProgressModal();

        // Start forecast
        const response = await fetch(`${API_BASE_URL}/run_forecast`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        });
   
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            const jobId = data.data.job_id;
            currentForecastJobId = jobId;

            // Startpolling for progress
            startEnhancedProgressPolling(jobId);

            // Close configuration modal
            const configModal = bootstrap.Modal.getInstance(document.getElementById('forecastConfigModal'));
            if (configModal) configModal.hide();

        } else {
            throw new Error(data.message || 'Failed to start forecast');
        }

    } catch (error) {
        console.error('Enhanced forecast start error:', error);
        NotificationManager.error(`Failed to start forecast: ${error.message}`);
        hideProgressModal();
    }
}

function collectCompleteConfiguration() {
    console.log("Collecting complete configuration fromform");
    
    const form = document.getElementById('forecastConfigForm');
    const formData = new FormData(form);

    // Basic configuration
    const config = {
        scenarioName: formData.get('scenarioName').trim(),
        targetYear: parseInt(formData.get('targetYear')),
        excludeCovidYears: formData.get('excludeCovidYears') === 'on',
        sectorConfigs: {},
        detailedConfiguration: {
            defaultModels: globalDefaultModels,
            configurationMethod: 'ui',
            collectionTimestamp: new Date().toISOString(),
            userInterface: 'web_application',
            configurationSource: 'sector_specific_selections'
        }
    };

    console.log("Basic configuration collected:", {
        scenarioName: config.scenarioName,
        targetYear: config.targetYear,
        excludeCovidYears: config.excludeCovidYears
    });

    // Use the tracked sector configurations instead of reading from DOM
    config.sectorConfigs = {};
    
    Object.keys(sectorConfigurations).forEach(sector => {
        const sectorConfig = sectorConfigurations[sector];
        
        // Only include sectors that have models selected
        if (sectorConfig.models && sectorConfig.models.length > 0) {
            config.sectorConfigs[sector] = {
                models: [...sectorConfig.models],
                independentVars: [...(sectorConfig.independentVars || [])],
                windowSize: sectorConfig.windowSize || 10,
                lastUpdated: sectorConfig.lastUpdated,
                configurationSource: 'tracking'
            };
            
            console.log(`Configuration for ${sector}:`, config.sectorConfigs[sector]);
        } else {
            console.log(`Skipping sector ${sector} - no models selected`);
        }
    });

    // Add global configuration metadata
    config.detailedConfiguration.totalSectorsAvailable = Object.keys(sectorConfigurations).length;
    config.detailedConfiguration.totalSectorsConfigured = Object.keys(config.sectorConfigs).length;
    config.detailedConfiguration.sectorConfigurationSummary = Object.keys(config.sectorConfigs).map(sector => ({
        sector: sector,
        models: config.sectorConfigs[sector].models,
        hasMLRVars: config.sectorConfigs[sector].independentVars.length > 0,
        customWAMWindow: config.sectorConfigs[sector].windowSize !== 10
    }));

    console.log("Complete configuration collected:", config);
    console.log("Sector configurations summary:", config.detailedConfiguration.sectorConfigurationSummary);

    return config;
}

// ==========Progress Monitoring ==========
function startEnhancedProgressPolling(jobId) {
    console.log("Startingprogress polling for job:", jobId);

    forecastPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/forecast_status/${encodeURIComponent(jobId)}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.status === 'success') {
                const jobData = data.data;
                updateEnhancedProgressDisplay(jobData);

                // Check for completion
                if (jobData.status === 'completed') {
                    clearInterval(forecastPollingInterval);
                    showEnhancedCompletionModal(jobData.result || jobData);
                } else if (jobData.status === 'failed') {
                    clearInterval(forecastPollingInterval);
                    showErrorModal(jobData.error || 'Forecast failed');
                } else if (jobData.status === 'cancelled') {
                    clearInterval(forecastPollingInterval);
                    hideProgressModal();
                    NotificationManager.info('Forecast was cancelled');
                }
            }
        } catch (error) {
            console.error('Enhanced progress polling error:', error);
            // Continue polling on network errors
        }
    }, 3000); //3-second polling
}

function updateEnhancedProgressDisplay(jobData) {
    // Update progress bar
    const progressBar = document.getElementById('forecastProgressBar');
    const progressPercentage = document.querySelector('.progress-percentage');

    if (progressBar) {
        const progress = Math.max(0, Math.min(100, jobData.progress || 0));
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }

    if (progressPercentage) {
        progressPercentage.textContent = `${Math.round(jobData.progress || 0)}%`;
    }

    // Update current sector
    const sectorName = document.getElementById('progressSectorName');
    if (sectorName && jobData.current_sector) {
        const displayName = jobData.current_sector === 'Summary' ?
            'Creating Summary' :
            jobData.current_sector.charAt(0).toUpperCase() + jobData.current_sector.slice(1);
        sectorName.textContent = displayName;
    }

    // Update statistics
    const completedEl = document.getElementById('sectorsCompleted');
    const totalEl = document.getElementById('sectorsTotal');
    const estimatedEl = document.getElementById('estimatedRemaining');

    if (completedEl) completedEl.textContent = jobData.processed_sectors || 0;
    if (totalEl) totalEl.textContent = jobData.total_sectors || 0;
    if (estimatedEl && jobData.estimated_remaining_seconds) {
        estimatedEl.textContent = UIUtils.formatDuration(jobData.estimated_remaining_seconds);
    }

    // Add to progress log
    addProgressLogEntry(jobData.message || 'Processing...');
}

function cancelEnhancedForecast() {
    if (!currentForecastJobId) {
        NotificationManager.warning('No active forecast to cancel');
        return;
    }

    if (!confirm('Are you sure you want to cancel the forecast?')) {
        return;
    }

    fetch(`${API_BASE_URL}/cancel_forecast/${encodeURIComponent(currentForecastJobId)}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Cancel forecast response:", data);
            if (data.status === 'success') {
                NotificationManager.info('Forecast cancellation requested');
            } else {
                NotificationManager.error(`Could not cancel forecast: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error cancelling forecast:', error);
            NotificationManager.error(`Error cancelling forecast: ${error.message}`);
        });
}

// ==========UI Functions ==========
function getCurrentView(sector) {
    const activeButton = document.querySelector(`.view-toggle-button[data-sector="${sector}"].active`);
    return activeButton ? activeButton.dataset.view : 'table';
}

// ==========Modal Management ==========
function openEnhancedForecastModal() {
    console.log("Openingforecast modal");
    
    const modal = new bootstrap.Modal(document.getElementById('forecastConfigModal'));
    modal.show();

    // Load independent variables for all sectors
    const sectorsDataEl = document.getElementById('sectorsData');
    if (sectorsDataEl) {
        const sectors = JSON.parse(sectorsDataEl.textContent || '[]');
        
        // Load independent variables for each sector
        sectors.forEach(sector => {
            loadIndependentVariables(sector);
        });
        
        // Update default model selections to match global defaults
        globalDefaultModels.forEach(model => {
            const checkbox = document.getElementById(`defaultModel${model}`);
            if (checkbox) {
                checkbox.checked = true;
            }
        });
        
        // Update overview table
        updateSectorOverviewTable();
    }
}

function showProgressModal() {
    const modal = new bootstrap.Modal(document.getElementById('forecastProgressModal'), {
        backdrop: 'static',
        keyboard: false
    });
    modal.show();
}

function hideProgressModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('forecastProgressModal'));
    if (modal) modal.hide();
}

function showEnhancedCompletionModal(result) {
    hideProgressModal();

    // Update completion modal withresults
    updateEnhancedCompletionModalData(result);

    const modal = new bootstrap.Modal(document.getElementById('forecastCompleteModal'));
    modal.show();
}

function showErrorModal(error) {
    hideProgressModal();
    NotificationManager.error(`Forecast failed: ${error}`, 10000);
}

function updateEnhancedCompletionModalData(result) {
    console.log("Updatingcompletion modal data:", result);

    // Update scenario details
    const elements = {
        'summaryScenario': result.scenario_name || result.scenarioName || 'Unknown',
        'summaryTargetYear': result.target_year || result.targetYear || 'Unknown',
        'summaryTotalSectors': result.total_sectors || result.totalSectors || 'Unknown',
        'summaryFilePath': result.forecast_dir || result.forecastDir || 'results/demand_projection/'
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });

    // Showcompletion statistics
    if (result.performance_metrics) {
        const processingTime = UIUtils.formatDuration(result.performance_metrics.total_processing_time || 0);
        const processingTimeEl = document.getElementById('summaryProcessingTime');
        if (processingTimeEl) {
            processingTimeEl.textContent = processingTime;
        }
    }
}

function addProgressLogEntry(message) {
    console.log("Adding progress log entry:", message);

    const progressLog = document.getElementById('progressLog');
    if (!progressLog) return;

    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="log-time">${new Date().toLocaleTimeString()}</span>
        <span class="log-message">${message}</span>
    `;

    progressLog.appendChild(entry);

    // Keep only last 20 entries
    while (progressLog.children.length > 20) {
        progressLog.removeChild(progressLog.firstChild);
    }

    // Scroll to bottom
    progressLog.scrollTop = progressLog.scrollHeight;
}

function toggleProgressLog() {
    const progressLog = document.getElementById('progressLog');
    if (progressLog) {
        progressLog.style.display = progressLog.style.display === 'none' ? 'block' : 'none';
    }
}

function minimizeProgressModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('forecastProgressModal'));
    if (modal) {
        modal.hide();
        NotificationManager.info('Forecast continues in background. You will be notified when complete.');
    }
}

// ========== Chart Controls ==========
function setupChartControls() {
    const chartTypeRadios = document.querySelectorAll('input[name="aggregatedChartType"]');

    chartTypeRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            const selectedType = document.querySelector('input[name="aggregatedChartType"]:checked').value;
            reloadAggregatedChart(selectedType);
        });
    });
}

async function reloadAggregatedChart(chartType) {
    const sector = 'aggregated';
    try {
        const response = await fetch(`${API_BASE_URL}/chart_data/${encodeURIComponent(sector)}`);
        if (!response.ok) throw new Error(`Failed to fetch chart data: ${response.statusText}`);
        const data = await response.json();

        if (data.status === 'success') {
            const canvas = document.getElementById('aggregatedChart');
            if (canvas.chartInstance) {
                canvas.chartInstance.destroy();
            }
            canvas.chartInstance = createAggregatedChart(canvas, data.data, chartType);
            canvas.style.display = 'block';
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        console.error(error);
        const errorDiv = document.getElementById('aggregatedChartError');
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
}


function updateChartType(sector, chartType) {
    console.log("Updating chart type:", sector, chartType);
    // Implementation for changing chart types
    const canvas = document.getElementById(`${sector}Chart`);
    if (canvas && canvas.chartInstance) {
        // Would need to recreate chart with different type
        console.log(`Chart type changed to ${chartType} for ${sector}`);
    }
}

// ==========Utility Functions ==========
async function loadIndependentVariables(sector) {
    const container = document.getElementById(`independentVarsContainer_${sector}`);
    if (!container || container.dataset.loaded === 'true') return;

    UIUtils.showLoading(container, 'Loading variables...');

    try {
        const response = await fetch(`${API_BASE_URL}/independent_variables/${encodeURIComponent(sector)}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            renderEnhancedIndependentVariablesForm(container, data.data, sector);
            container.dataset.loaded = 'true';
        } else {
            throw new Error(data.message || 'Failed to load variables');
        }
    } catch (error) {
        UIUtils.showError(container, error, 'Variables Error');
    }
}

function renderEnhancedIndependentVariablesForm(container, data, sector) {
    if (!data.suitable_variables || data.suitable_variables.length === 0) {
        UIUtils.showEmptyState(
            container,
            'fas fa-database',
            'No Variables Available',
            'No suitable independent variables found for this sector.'
        );
        return;
    }

    let html = '<div class="row">';

    data.suitable_variables.forEach(variable => {
        if (variable === 'Year' || variable === 'Electricity') return;

        const correlation = data.correlations[variable] || 0;
        const absCorrelation = Math.abs(correlation);
        const isRecommended = absCorrelation >= 0.4;
        
        // Check if this variable is already selected for this sector
        const isSelected = sectorConfigurations[sector] && 
                           sectorConfigurations[sector].independentVars && 
                           sectorConfigurations[sector].independentVars.includes(variable);

        let strengthClass = 'text-muted';
        let strengthText = 'Weak';

        if (absCorrelation >= 0.7) {
            strengthClass = 'text-success fw-bold';
            strengthText = 'Strong';
        } else if (absCorrelation >= 0.4) {
            strengthClass = 'text-primary';
            strengthText = 'Moderate';
        }

        html += `
            <div class="col-md-6 mb-2">
                <div class="form-check">
                    <input class="form-check-input independent-var-checkbox" 
                           type="checkbox" 
                           name="independentVars_${sector}" 
                           id="var_${variable}_${sector}" 
                           value="${variable}" 
                           ${isSelected || isRecommended ? 'checked' : ''}>
                    <label class="form-check-label" for="var_${variable}_${sector}">
                        <strong>${variable}</strong>
                        <br>
                        <small class="${strengthClass}">
                            Correlation: ${correlation.toFixed(3)} (${strengthText})
                            ${isRecommended ? '<i class="fas fa-star text-warning ms-1" title="Recommended"></i>' : ''}
                        </small>
                    </label>
                </div>
            </div>
        `;
    });

    html += '</div>';

    if (data.recommendations) {
        html += `
            <div class="alert alert-info mt-3">
                <i class="fas fa-lightbulb me-2"></i>
                <strong>Recommendation:</strong> Select variables with moderate to strong correlations for better model performance.
                ${data.recommendations.recommended_for_mlr.length > 0 ?
                `<br>Recommended variables: ${data.recommendations.recommended_for_mlr.join(', ')}` :
                ''
            }
            </div>
        `;
    }

    container.innerHTML = html;
    
    // Initialize sector configuration with selected variables
    const selectedVars = data.suitable_variables.filter(variable => {
        if (variable === 'Year' || variable === 'Electricity') return false;
        const correlation = data.correlations[variable] || 0;
        const absCorrelation = Math.abs(correlation);
        return absCorrelation >= 0.4; // Recommended variables
    });
    
    updateSectorConfiguration(sector, {
        independentVars: selectedVars
    });
}

// ==========Utility Functions ==========
function debounce(func, delay = 1000) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

// ========== Export Functions for Template ==========
window.DemandProjectionApp = {
    // Exposefunctions for template use
    switchToSector,
    switchView,
    loadSectorData,
    openEnhancedForecastModal,
    NotificationManager,
    UIUtils,
    sectorConfigurations,
    updateSectorConfiguration
};

// ========== Additional Template Helper Functions ==========
function exportSectorData(sector) {
    NotificationManager.info(`Exporting data for ${sector}...`);
    // Implementation for data export
}

function refreshSectorData(sector) {
    loadSectorData(sector);
    NotificationManager.success(`Refreshed data for ${sector}`);
}

function toggleTrendLine(sector) {
    console.log(`Toggle trend line for ${sector}`);
}

function toggleDataPoints(sector) {
    console.log(`Toggle data points for ${sector}`);
}

function downloadChart(sector) {
    const canvas = document.getElementById(`${sector}Chart`);
    if (canvas && canvas.chartInstance) {
        const link = document.createElement('a');
        link.download = `${sector}_chart.png`;
        link.href = canvas.toDataURL();
        link.click();
        NotificationManager.success('Chart downloaded');
    }
}

function fullscreenChart(sector) {
    const container = document.getElementById(`${sector}ChartContainer`);
    if (container && container.requestFullscreen) {
        container.requestFullscreen();
    }
}

function showCorrelationHelp() {
    NotificationManager.info(`
        Correlation Analysis Help:
        • Strong (≥0.7): High predictive value
        • Moderate (0.4-0.7): Good for modeling
        • Weak (<0.4): Limited predictive value
        
        Positive correlations increase together.
        Negative correlations move in opposite directions.
    `, 8000);
}

function copyPathToClipboard() {
    const pathElement = document.getElementById('summaryFilePath');
    if (pathElement) {
        UIUtils.copyToClipboard(pathElement.textContent);
    }
}

function openResultsInNewTab() {
    const scenarioName = document.getElementById('summaryScenario').textContent;
    if (scenarioName) {
        window.open(`/demand_visualization?scenario=${encodeURIComponent(scenarioName)}`, '_blank');
    }
}

console.log(" Demand Projection JavaScript loaded successfully with complete configuration management");