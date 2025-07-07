/**
 * Complete Demand Visualization Application
 * Enhanced version with improved performance, error handling, and modern JavaScript practices
 * 
 * Features:
 * - Comprehensive scenario management
 * - Advanced chart visualization with Chart.js
 * - Model selection and configuration
 * - T&D losses management
 * - Consolidated results generation
 * - Scenario comparison capabilities
 * - Color customization system
 * - Data export functionality
 * - Responsive design support
 */

class CompleteDemandVisualizationApp {
    constructor() {
        // Application configuration
        this.API_BASE = '/demand_visualization/api';
        this.CHART_ANIMATION_DURATION = 750;
        this.NOTIFICATION_DURATION = 5000;
        this.CHART_DESTROY_DELAY = 50;
        
        // Application state management
        this.state = {
            // Core data
            scenarios: [],
            currentScenario: null,
            currentData: null,
            currentSector: null,
            currentTab: 'sector-analysis',
            
            // Configuration
            modelConfig: {},
            tdLossesConfig: {},
            filters: {
                unit: 'GWh',
                startYear: 2020,
                endYear: 2050
            },
            
            // Comparison mode
            isComparisonMode: false,
            comparisonScenario: null,
            comparisonData: null,
            
            // Chart management
            charts: {},
            
            // UI state
            isLoading: false,
            colorModalListenersInitialized: false
        };
        
        // Enhanced color palette for better visual distribution
        this.defaultColors = [
            '#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#ea580c',
            '#be185d', '#0d9488', '#7c2d12', '#4338ca', '#be123c', '#0369a1', '#a21caf',
            '#166534', '#92400e', '#581c87', '#155e75', '#991b1b', '#6b21a8'
        ];
        
        // Unit display mapping
        this.unitDisplayMap = {
            'GWh': 'Gigawatt-hours (GWh)',
            'MWh': 'Megawatt-hours (MWh)',
            'kWh': 'Kilowatt-hours (kWh)',
            'MW': 'Megawatts (MW)',
            'GW': 'Gigawatts (GW)',
            'kW': 'Kilowatts (kW)',
            'MU': 'Million Units (MU)'
        };
        
        // Notification icons mapping
        this.notificationIcons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-triangle',
            warning: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };
        
        // Initialize application
        this.init();
    }
    
    // ========== INITIALIZATION ==========
    
    async init() {
        try {
            this.showLoading('Initializing application...');
            
            // Load initial data
            await this.loadInitialData();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Initialize UI state
            this.initializeUI();
            
            this.showNotification('success', 'Application initialized successfully');
        } catch (error) {
            console.error('Failed to initialize application:', error);
            this.showNotification('error', 'Failed to initialize application: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async loadInitialData() {
        try {
            const response = await fetch(`${this.API_BASE}/scenarios`);
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to load scenarios');
            }
            
            this.state.scenarios = result.scenarios || [];
            this.populateScenarioSelect();
        } catch (error) {
            console.error('Error loading initial data:', error);
            throw error;
        }
    }
    
    setupEventListeners() {
        // Scenario selection
        const scenarioSelect = document.getElementById('scenarioSelect');
        if (scenarioSelect) {
            scenarioSelect.addEventListener('change', (e) => this.handleScenarioChange(e.target.value));
        }
        
        // Filter controls
        this.setupFilterListeners();
        
        // Top bar actions
        this.setupTopBarListeners();
        
        // Export buttons
        this.setupExportListeners();
        
        // Analysis tabs
        this.setupAnalysisTabListeners();
        
        // Modal event listeners
        this.setupModalListeners();
        
        // Responsive design handlers
        this.setupResponsiveHandlers();
    }
    
    setupFilterListeners() {
        const filterIds = ['unitSelect', 'startYearSelect', 'endYearSelect'];
        
        filterIds.forEach(filterId => {
            const element = document.getElementById(filterId);
            if (element) {
                element.addEventListener('change', (e) => {
                    this.handleFilterChange(filterId, e.target.value);
                });
            }
        });
        
        // Advanced filters toggle
        const advancedFiltersBtn = document.getElementById('advancedFiltersBtn');
        if (advancedFiltersBtn) {
            advancedFiltersBtn.addEventListener('click', () => this.toggleAdvancedFilters());
        }
    }
    
    setupTopBarListeners() {
        const topBarButtons = [
            { id: 'modelSelectionBtn', handler: () => this.showModelSelectionModal() },
            { id: 'compareScenarioBtn', handler: () => this.toggleComparisonMode() },
            { id: 'colorSettingsBtn', handler: () => this.openColorSettingsModal() }
        ];
        
        topBarButtons.forEach(({ id, handler }) => {
            const button = document.getElementById(id);
            if (button) {
                button.addEventListener('click', handler);
            }
        });
    }
    
    setupExportListeners() {
        const exportDataBtn = document.getElementById('exportDataBtn');
        const exportChartBtn = document.getElementById('exportChartBtn');
        
        if (exportDataBtn) {
            exportDataBtn.addEventListener('click', () => this.exportCurrentData());
        }
        
        if (exportChartBtn) {
            exportChartBtn.addEventListener('click', () => this.exportCurrentChart());
        }
    }
    
    setupAnalysisTabListeners() {
        const tabButtons = document.querySelectorAll('.analysis-tab');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabId = e.target.dataset.tab;
                if (tabId) {
                    this.switchAnalysisTab(tabId);
                }
            });
        });
    }
    
    setupModalListeners() {
        // Close modal buttons
        document.querySelectorAll('[data-dismiss="modal"]').forEach(button => {
            button.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.hideModal(modal.id);
                }
            });
        });
        
        // Modal backdrop clicks
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal.id);
                }
            });
        });
        
        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    this.hideModal(openModal.id);
                }
            }
        });
    }
    
    setupResponsiveHandlers() {
        // Handle window resize for chart responsiveness
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleWindowResize();
            }, 250);
        });
    }
    
    initializeUI() {
        // Hide sections initially
        const sectionsToHide = ['sectorNavbar', 'sectorAnalysisContent', 'tdLossesContent', 'consolidatedContent', 'comparisonContent'];
        sectionsToHide.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'none';
            }
        });
        
        // Disable buttons initially
        const buttonsToDisable = ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'];
        buttonsToDisable.forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.disabled = true;
            }
        });
        
        // Show empty states
        this.showSectorEmptyState();
        this.showTdLossesEmptyState();
        this.showConsolidatedEmptyState();
    }
    
    // ========== SCENARIO MANAGEMENT ==========
    
    populateScenarioSelect() {
        const select = document.getElementById('scenarioSelect');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select a scenario...</option>';
        
        this.state.scenarios.forEach(scenario => {
            const option = document.createElement('option');
            // Handle both string and object scenarios
            if (typeof scenario === 'string') {
                option.value = scenario;
                option.textContent = scenario;
            } else {
                option.value = scenario.name;
                option.textContent = `${scenario.name} (${scenario.sectors_count} sectors)`;
                option.setAttribute('data-sectors', scenario.sectors_count);
                option.setAttribute('data-files', scenario.file_count);
                if (scenario.year_range) {
                    option.setAttribute('data-year-min', scenario.year_range.min);
                    option.setAttribute('data-year-max', scenario.year_range.max);
                }
            }
            select.appendChild(option);
        });
    }
    
    async handleScenarioChange(scenarioName) {
        if (!scenarioName) {
            this.clearScenario();
            return;
        }
        
        try {
            this.showLoading(`Loading scenario: ${scenarioName}...`);
            
            this.state.currentScenario = scenarioName;
            
            // Load scenario data
            await this.loadScenarioData();
            
            // Initialize filters and UI
            this.initializeFilters();
            this.enableTopBarActions();
            
            // Switch to sector analysis tab
            this.switchAnalysisTab('sector-analysis');
            
            this.showNotification('success', `Scenario "${scenarioName}" loaded successfully`);
        } catch (error) {
            console.error('Error loading scenario:', error);
            this.showNotification('error', 'Failed to load scenario: ' + error.message);
            this.clearScenario();
        } finally {
            this.hideLoading();
        }
    }
    
    async loadScenarioData() {
        try {
            // Validate scenario name
            if (!this.state.currentScenario || typeof this.state.currentScenario !== 'string') {
                throw new Error(`Invalid scenario name: ${this.state.currentScenario}`);
            }
            
            // Encode scenario name for URL
            const encodedScenario = encodeURIComponent(this.state.currentScenario);
            const response = await fetch(`${this.API_BASE}/scenario/${encodedScenario}`);
            
            if (!response.ok) {
                throw new Error(`Scenario '${this.state.currentScenario}' not found`);
            }
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to load scenario data');
            }
            
            this.state.currentData = result.data;
            
            // Load existing model configuration
            await this.loadModelConfiguration();
            
            // Populate sector navigation
            this.populateSectorNavigation();
            
        } catch (error) {
            console.error('Error loading scenario data:', error);
            throw error;
        }
    }
    
    async loadModelConfiguration() {
        try {
            const response = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`);
            const result = await response.json();
            
            if (result.success && result.model_selection) {
                this.state.modelConfig = result.model_selection;
                this.updateSectorTabIndicators();
            }
        } catch (error) {
            console.warn('No existing model configuration found:', error);
            this.state.modelConfig = {};
        }
    }
    
    initializeFilters() {
        if (!this.state.currentData) return;
        
        // Get available years from data
        const allYears = new Set();
        Object.values(this.state.currentData.sectors).forEach(sectorData => {
            if (sectorData.years) {
                sectorData.years.forEach(year => allYears.add(year));
            }
        });
        
        const years = Array.from(allYears).sort((a, b) => a - b);
        
        if (years.length > 0) {
            this.state.filters.startYear = Math.min(...years);
            this.state.filters.endYear = Math.max(...years);
            
            // Update filter UI
            this.updateFilterUI(years);
        }
    }
    
    updateFilterUI(years) {
        const startYearSelect = document.getElementById('startYearSelect');
        const endYearSelect = document.getElementById('endYearSelect');
        
        if (startYearSelect && endYearSelect) {
            // Clear existing options
            startYearSelect.innerHTML = '';
            endYearSelect.innerHTML = '';
            
            // Populate year options
            years.forEach(year => {
                const startOption = document.createElement('option');
                startOption.value = year;
                startOption.textContent = year;
                if (year === this.state.filters.startYear) startOption.selected = true;
                startYearSelect.appendChild(startOption);
                
                const endOption = document.createElement('option');
                endOption.value = year;
                endOption.textContent = year;
                if (year === this.state.filters.endYear) endOption.selected = true;
                endYearSelect.appendChild(endOption);
            });
        }
        
        // Update unit select
        const unitSelect = document.getElementById('unitSelect');
        if (unitSelect) {
            unitSelect.value = this.state.filters.unit;
        }
    }
    
    enableTopBarActions() {
        const buttonsToEnable = ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'];
        buttonsToEnable.forEach(buttonId => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.disabled = false;
            }
        });
    }
    
    // ========== SECTOR NAVIGATION ==========
    
    populateSectorNavigation() {
        if (!this.state.currentData || !this.state.currentData.sectors) return;
        
        const sectorNavbar = document.getElementById('sectorNavbar');
        const sectorTabs = document.getElementById('sectorTabs');
        
        if (!sectorNavbar || !sectorTabs) return;
        
        const sectors = Object.keys(this.state.currentData.sectors);
        
        if (sectors.length === 0) {
            sectorNavbar.style.display = 'none';
            return;
        }
        
        // Clear existing tabs
        sectorTabs.innerHTML = '';
        
        // Create sector tabs
        sectors.forEach((sector, index) => {
            const tab = document.createElement('button');
            tab.className = `btn btn-outline-primary sector-tab ${index === 0 ? 'active' : ''}`;
            tab.dataset.sector = sector;
            tab.innerHTML = `
                <span>${sector.charAt(0).toUpperCase() + sector.slice(1)}</span>
                <i class="fas fa-check-circle config-indicator" style="display: none;"></i>
            `;
            
            tab.addEventListener('click', () => this.switchSector(sector));
            sectorTabs.appendChild(tab);
        });
        
        // Show sector navigation and switch to first sector
        sectorNavbar.style.display = 'block';
        this.switchSector(sectors[0]);
        
        // Update indicators
        this.updateSectorTabIndicators();
    }
    
    switchSector(sectorName) {
        if (!this.state.currentData || !this.state.currentData.sectors[sectorName]) return;
        
        this.state.currentSector = sectorName;
        
        // Update active tab
        document.querySelectorAll('.sector-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.sector === sectorName);
        });
        
        // Update sector analysis content
        this.updateSectorAnalysisContent();
    }
    
    updateSectorTabIndicators() {
        document.querySelectorAll('.sector-tab').forEach(tab => {
            const sector = tab.dataset.sector;
            const indicator = tab.querySelector('.config-indicator');
            
            if (indicator) {
                if (sector && this.state.modelConfig[sector]) {
                    indicator.style.display = 'inline';
                    tab.classList.add('has-config');
                } else {
                    indicator.style.display = 'none';
                    tab.classList.remove('has-config');
                }
            }
        });
    }
    
    // ========== ANALYSIS TABS ==========
    
    switchAnalysisTab(tabId) {
        this.state.currentTab = tabId;
        
        // Update active tab button
        document.querySelectorAll('.analysis-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });
        
        // Show/hide content sections
        this.updateContentVisibility(tabId);
        
        // Update section content
        switch (tabId) {
            case 'sector-analysis':
                this.updateSectorAnalysisContent();
                break;
            case 'td-losses':
                this.updateTdLossesContent();
                break;
            case 'consolidated':
                this.updateConsolidatedContent();
                break;
            case 'comparison':
                this.updateComparisonContent();
                break;
        }
    }
    
    updateContentVisibility(activeTab) {
        const contentSections = {
            'sector-analysis': 'sectorAnalysisContent',
            'td-losses': 'tdLossesContent',
            'consolidated': 'consolidatedContent',
            'comparison': 'comparisonContent'
        };
        
        // Show/hide sector navigation
        const sectorNavbar = document.getElementById('sectorNavbar');
        if (sectorNavbar) {
            sectorNavbar.style.display = activeTab === 'sector-analysis' ? 'block' : 'none';
        }
        
        // Show/hide content sections
        Object.entries(contentSections).forEach(([tabId, sectionId]) => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = tabId === activeTab ? 'block' : 'none';
            }
        });
        
        // Update section titles
        this.updateSectionTitle(activeTab);
    }
    
    updateSectionTitle(activeTab) {
        const titleElement = document.getElementById('sectionTitle');
        if (!titleElement) return;
        
        const titles = {
            'sector-analysis': 'Sector Analysis',
            'td-losses': 'Transmission & Distribution Losses',
            'consolidated': 'Consolidated Results',
            'comparison': 'Scenario Comparison'
        };
        
        titleElement.textContent = titles[activeTab] || 'Analysis';
    }
    
    // ========== SECTOR ANALYSIS ==========
    
    updateSectorAnalysisContent() {
        if (!this.state.currentData || !this.state.currentSector) {
            this.showSectorEmptyState();
            return;
        }
        
        const sectorData = this.state.currentData.sectors[this.state.currentSector];
        if (!sectorData) {
            this.showSectorEmptyState();
            return;
        }
        
        this.renderSectorAnalysisContent(sectorData);
    }
    
    showSectorEmptyState() {
        const content = document.getElementById('sectorAnalysisContent');
        if (!content) return;
        
        content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Sector Data Available</h5>
                <p class="text-muted">Please select a scenario to view sector analysis.</p>
            </div>
        `;
    }
    
    renderSectorAnalysisContent(sectorData) {
        const content = document.getElementById('sectorAnalysisContent');
        if (!content) return;
        
        const chartId = `sector-chart-${this.state.currentSector}`;
        
        content.innerHTML = `
            <div class="chart-container">
                <div class="chart-header">
                    <div class="chart-controls">
                        <div class="btn-group btn-group-sm" role="group">
                            <button type="button" class="btn btn-outline-primary active" data-type="line">
                                <i class="fas fa-chart-line me-1"></i>Line
                            </button>
                            <button type="button" class="btn btn-outline-primary" data-type="bar">
                                <i class="fas fa-chart-bar me-1"></i>Bar
                            </button>
                            <button type="button" class="btn btn-outline-primary" data-type="area">
                                <i class="fas fa-chart-area me-1"></i>Area
                            </button>
                        </div>
                    </div>
                    <div class="chart-actions">
                        <button class="btn btn-sm btn-outline-secondary" onclick="demandVizApp.exportCurrentChart()">
                            <i class="fas fa-download me-1"></i>Export Chart
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="demandVizApp.exportCurrentData()">
                            <i class="fas fa-file-csv me-1"></i>Export Data
                        </button>
                    </div>
                </div>
                <div class="chart-wrapper">
                    <canvas id="${chartId}" width="400" height="200"></canvas>
                </div>
            </div>
            
            <div class="sector-summary-card mt-4">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-info-circle me-2"></i>
                            ${this.state.currentSector.charAt(0).toUpperCase() + this.state.currentSector.slice(1)} Sector Summary
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3">
                                <div class="summary-item">
                                    <span class="label">Available Models:</span>
                                    <span class="value">${sectorData.models ? sectorData.models.length : 0}</span>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="summary-item">
                                    <span class="label">Data Points:</span>
                                    <span class="value">${sectorData.years ? sectorData.years.length : 0}</span>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="summary-item">
                                    <span class="label">Year Range:</span>
                                    <span class="value">${sectorData.years ? `${Math.min(...sectorData.years)} - ${Math.max(...sectorData.years)}` : 'N/A'}</span>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="summary-item">
                                    <span class="label">Selected Model:</span>
                                    <span class="value">${this.state.modelConfig[this.state.currentSector] || 'None'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="data-table-container mt-4">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">
                            <i class="fas fa-table me-2"></i>
                            Data Table
                        </h6>
                    </div>
                    <div class="card-body">
                        ${this.createSectorDataTable(sectorData)}
                    </div>
                </div>
            </div>
        `;
        
        // Setup chart type controls
        this.setupChartTypeControls(chartId, sectorData);
        
        // Create initial chart
        this.createSectorChart(chartId, sectorData, 'line');
    }
    
    setupChartTypeControls(chartId, sectorData) {
        const chartControls = document.querySelectorAll('.chart-controls .btn');
        chartControls.forEach(button => {
            button.addEventListener('click', async (e) => {
                // Update active button
                chartControls.forEach(btn => btn.classList.remove('active'));
                e.target.classList.add('active');
                
                // Get chart type
                const chartType = e.target.dataset.type;
                
                // Destroy existing chart
                if (this.state.charts[chartId]) {
                    this.state.charts[chartId].destroy();
                    this.state.charts[chartId] = null;
                }
                
                // Wait for destruction
                await new Promise(resolve => setTimeout(resolve, this.CHART_DESTROY_DELAY));
                
                // Create new chart
                this.createSectorChart(chartId, sectorData, chartType);
            });
        });
    }
    
    async createSectorChart(chartId, sectorData, chartType = 'line') {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        try {
            // Try API-based chart generation first
            const response = await fetch(`${this.API_BASE}/chart/sector/${this.state.currentScenario}/${this.state.currentSector}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chart_type: chartType,
                    filters: this.state.filters
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.chart_data) {
                const ctx = canvas.getContext('2d');
                this.state.charts[chartId] = new Chart(ctx, result.chart_data);
                return;
            }
        } catch (error) {
            console.warn('API chart generation failed, using fallback:', error);
        }
        
        // Fallback to client-side chart generation
        this.createSectorChartFallback(chartId, sectorData, chartType);
    }
    
    createSectorChartFallback(chartId, sectorData, chartType = 'line') {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Prepare datasets
        const datasets = sectorData.models.map((model, index) => {
            const data = sectorData[model] || [];
            const color = this.getModelColor(model, index);
            
            const dataset = {
                label: model,
                data: data,
                borderColor: color,
                backgroundColor: this.addTransparency(color, chartType === 'area' ? 0.3 : 0.1),
                borderWidth: 3,
                tension: 0.2,
                pointBackgroundColor: color,
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: chartType === 'area'
            };
            
            if (chartType === 'bar') {
                dataset.backgroundColor = this.addTransparency(color, 0.8);
                dataset.borderRadius = 4;
            }
            
            return dataset;
        });
        
        // Determine Chart.js type
        const chartJsType = chartType === 'bar' ? 'bar' : 'line';
        
        // Create chart
        const unitDisplay = this.getUnitDisplayName(this.state.filters.unit);
        const title = `${this.state.currentSector.charAt(0).toUpperCase() + this.state.currentSector.slice(1)} Sector - ${this.state.currentScenario} (${unitDisplay})`;
        
        this.state.charts[chartId] = new Chart(ctx, {
            type: chartJsType,
            data: {
                labels: sectorData.years || [],
                datasets: datasets
            },
            options: this.getEnhancedChartConfig(chartType, title, unitDisplay)
        });
    }
    
    createSectorDataTable(sectorData) {
        if (!sectorData.years || !sectorData.models) {
            return '<p class="text-muted">No data available</p>';
        }
        
        let html = `
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Year</th>
                            ${sectorData.models.map(model => `<th>${model}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        sectorData.years.forEach((year, yearIndex) => {
            html += `<tr><td><strong>${year}</strong></td>`;
            sectorData.models.forEach(model => {
                const value = sectorData[model] && sectorData[model][yearIndex] !== undefined
                    ? sectorData[model][yearIndex].toFixed(3)
                    : '0.000';
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        return html;
    }
    
    // ========== T&D LOSSES MANAGEMENT ==========
    
    async updateTdLossesContent() {
        if (!this.state.currentScenario) {
            this.showTdLossesEmptyState();
            return;
        }
        
        try {
            this.showLoading('Loading T&D losses configuration...');
            
            // Load existing configuration
            await this.loadTdLossesConfiguration();
            
            // Render content
            this.renderTdLossesConfiguration();
            
        } catch (error) {
            console.error('Error updating T&D losses content:', error);
            this.showNotification('error', 'Failed to load T&D losses configuration');
            this.showTdLossesEmptyState();
        } finally {
            this.hideLoading();
        }
    }
    
    async loadTdLossesConfiguration() {
        try {
            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`);
            const result = await response.json();
            
            if (result.success && result.td_losses) {
                this.state.tdLossesConfig = result.td_losses;
            } else {
                this.state.tdLossesConfig = this.getDefaultTdLosses();
            }
        } catch (error) {
            console.warn('No existing T&D losses configuration found:', error);
            this.state.tdLossesConfig = this.getDefaultTdLosses();
        }
    }
    
    getDefaultTdLosses() {
        return {
            points: [
                { year: 2025, percentage: 15.0 },
                { year: 2030, percentage: 12.0 },
                { year: 2040, percentage: 10.0 },
                { year: 2050, percentage: 8.0 }
            ]
        };
    }
    
    showTdLossesEmptyState() {
        const content = document.getElementById('tdLossesContent');
        if (!content) return;
        
        content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-bolt fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No T&D Losses Configuration</h5>
                <p class="text-muted">Please select a scenario to configure transmission and distribution losses.</p>
            </div>
        `;
    }
    
    renderTdLossesConfiguration() {
        const content = document.getElementById('tdLossesContent');
        if (!content) return;
        
        content.innerHTML = `
            <div class="td-losses-container">
                <div class="row">
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas fa-cog me-2"></i>
                                    T&D Losses Configuration
                                </h6>
                            </div>
                            <div class="card-body">
                                <div id="tdLossesConfigForm">
                                    ${this.createTdLossesForm()}
                                </div>
                                <div class="mt-3">
                                    <button class="btn btn-primary me-2" onclick="demandVizApp.saveTdLossesConfiguration()">
                                        <i class="fas fa-save me-1"></i>Save Configuration
                                    </button>
                                    <button class="btn btn-outline-secondary" onclick="demandVizApp.addTdLossEntry()">
                                        <i class="fas fa-plus me-1"></i>Add Point
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas fa-chart-line me-2"></i>
                                    Preview
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="chart-wrapper">
                                    <canvas id="tdLossesPreviewChart" width="400" height="300"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Setup form event listeners
        this.setupTdLossesFormListeners();
        
        // Update preview
        this.updateTdLossesPreview();
    }
    
    createTdLossesForm() {
        let html = '<div class="td-losses-entries">';
        
        this.state.tdLossesConfig.points.forEach((point, index) => {
            html += `
                <div class="td-loss-entry mb-3" data-index="${index}">
                    <div class="row align-items-center">
                        <div class="col-4">
                            <label class="form-label">Year</label>
                            <input type="number" class="form-control td-loss-year" 
                                   value="${point.year}" min="2020" max="2100" 
                                   onchange="demandVizApp.updateTdLossValue(${index}, 'year', this.value)">
                        </div>
                        <div class="col-4">
                            <label class="form-label">Loss %</label>
                            <input type="number" class="form-control td-loss-percentage" 
                                   value="${point.percentage}" min="0" max="100" step="0.1" 
                                   onchange="demandVizApp.updateTdLossValue(${index}, 'percentage', this.value)">
                        </div>
                        <div class="col-4">
                            <label class="form-label">&nbsp;</label>
                            <div>
                                <button type="button" class="btn btn-outline-danger btn-sm" 
                                        onclick="demandVizApp.removeTdLossEntry(${index})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }
    
    setupTdLossesFormListeners() {
        // Form validation and real-time updates are handled by inline event handlers
        // This method can be extended for additional form setup if needed
    }
    
    updateTdLossValue(index, field, value) {
        if (!this.state.tdLossesConfig.points[index]) return;
        
        const numValue = parseFloat(value);
        if (isNaN(numValue)) return;
        
        this.state.tdLossesConfig.points[index][field] = numValue;
        
        // Validate and update preview
        if (this.validateTdLossEntry(index)) {
            this.updateTdLossesPreview();
        }
    }
    
    validateTdLossEntry(index) {
        const point = this.state.tdLossesConfig.points[index];
        if (!point) return false;
        
        const isValidYear = point.year >= 2020 && point.year <= 2100;
        const isValidPercentage = point.percentage >= 0 && point.percentage <= 100;
        
        return isValidYear && isValidPercentage;
    }
    
    addTdLossEntry() {
        const newYear = this.state.tdLossesConfig.points.length > 0 
            ? Math.max(...this.state.tdLossesConfig.points.map(p => p.year)) + 5
            : 2025;
        
        this.state.tdLossesConfig.points.push({
            year: newYear,
            percentage: 10.0
        });
        
        // Re-render form
        const formContainer = document.getElementById('tdLossesConfigForm');
        if (formContainer) {
            formContainer.innerHTML = this.createTdLossesForm();
            this.setupTdLossesFormListeners();
            this.updateTdLossesPreview();
        }
    }
    
    removeTdLossEntry(index) {
        if (this.state.tdLossesConfig.points.length <= 1) {
            this.showNotification('warning', 'At least one T&D loss point is required');
            return;
        }
        
        this.state.tdLossesConfig.points.splice(index, 1);
        
        // Re-render form
        const formContainer = document.getElementById('tdLossesConfigForm');
        if (formContainer) {
            formContainer.innerHTML = this.createTdLossesForm();
            this.setupTdLossesFormListeners();
            this.updateTdLossesPreview();
        }
    }
    
    async updateTdLossesPreview() {
        try {
            // Try API-based chart generation
            const response = await fetch(`${this.API_BASE}/chart/td-losses/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    td_losses: this.state.tdLossesConfig,
                    filters: this.state.filters
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.chart_data) {
                const canvas = document.getElementById('tdLossesPreviewChart');
                if (canvas) {
                    // Destroy existing chart
                    if (this.state.charts['tdLossesPreview']) {
                        this.state.charts['tdLossesPreview'].destroy();
                    }
                    
                    const ctx = canvas.getContext('2d');
                    this.state.charts['tdLossesPreview'] = new Chart(ctx, result.chart_data);
                }
                return;
            }
        } catch (error) {
            console.warn('API T&D losses chart generation failed, using fallback:', error);
        }
        
        // Fallback to client-side chart generation
        this.createTdLossesPreviewFallback();
    }
    
    createTdLossesPreviewFallback() {
        const canvas = document.getElementById('tdLossesPreviewChart');
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.state.charts['tdLossesPreview']) {
            this.state.charts['tdLossesPreview'].destroy();
        }
        
        const ctx = canvas.getContext('2d');
        
        // Sort points by year
        const sortedPoints = [...this.state.tdLossesConfig.points].sort((a, b) => a.year - b.year);
        
        const data = {
            labels: sortedPoints.map(p => p.year),
            datasets: [{
                label: 'T&D Losses (%)',
                data: sortedPoints.map(p => p.percentage),
                borderColor: '#dc2626',
                backgroundColor: this.addTransparency('#dc2626', 0.1),
                borderWidth: 3,
                tension: 0.2,
                pointBackgroundColor: '#dc2626',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                fill: true
            }]
        };
        
        this.state.charts['tdLossesPreview'] = new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'T&D Losses Configuration Preview',
                        font: { size: 16, weight: '600' }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Loss Percentage (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Year'
                        }
                    }
                }
            }
        });
    }
    
    async saveTdLossesConfiguration() {
        try {
            // Validate all entries
            const isValid = this.state.tdLossesConfig.points.every((_, index) => 
                this.validateTdLossEntry(index)
            );
            
            if (!isValid) {
                this.showNotification('warning', 'Please fix invalid entries before saving');
                return;
            }
            
            this.showLoading('Saving T&D losses configuration...');
            
            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ td_losses: this.state.tdLossesConfig })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to save T&D losses configuration');
            }
            
            this.showNotification('success', 'T&D losses configuration saved successfully');
            
        } catch (error) {
            console.error('Error saving T&D losses configuration:', error);
            this.showNotification('error', 'Failed to save T&D losses configuration: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    // ========== CONSOLIDATED RESULTS ==========
    
    async updateConsolidatedContent() {
        if (!this.state.currentScenario) {
            this.showConsolidatedEmptyState();
            return;
        }
        
        try {
            this.showLoading('Loading consolidated configuration...');
            
            // Check model selection and T&D losses status
            const modelStatus = await this.checkModelSelectionStatus();
            const tdLossesStatus = await this.checkTdLossesStatus();
            
            // Render consolidated summary
            this.renderConsolidatedSummary(modelStatus, tdLossesStatus);
            
        } catch (error) {
            console.error('Error updating consolidated content:', error);
            this.showNotification('error', 'Failed to load consolidated configuration');
            this.showConsolidatedEmptyState();
        } finally {
            this.hideLoading();
        }
    }
    
    async checkModelSelectionStatus() {
        try {
            const response = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`);
            const result = await response.json();
            
            if (result.success && result.model_selection) {
                const sectors = Object.keys(this.state.currentData?.sectors || {});
                const configuredSectors = Object.keys(result.model_selection);
                
                return {
                    configured: sectors.length > 0 && sectors.every(sector => result.model_selection[sector]),
                    total: sectors.length,
                    completed: configuredSectors.length,
                    details: result.model_selection
                };
            }
            
            return { configured: false, total: 0, completed: 0, details: {} };
        } catch (error) {
            console.warn('Error checking model selection status:', error);
            return { configured: false, total: 0, completed: 0, details: {} };
        }
    }
    
    async checkTdLossesStatus() {
        try {
            const response = await fetch(`${this.API_BASE}/td-losses/${this.state.currentScenario}`);
            const result = await response.json();
            
            return {
                configured: result.success && result.td_losses && result.td_losses.points && result.td_losses.points.length > 0,
                points: result.td_losses?.points?.length || 0
            };
        } catch (error) {
            console.warn('Error checking T&D losses status:', error);
            return { configured: false, points: 0 };
        }
    }
    
    showConsolidatedEmptyState() {
        const content = document.getElementById('consolidatedContent');
        if (!content) return;
        
        content.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-layer-group fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Consolidated Configuration</h5>
                <p class="text-muted">Please select a scenario to view consolidated results.</p>
            </div>
        `;
    }
    
    renderConsolidatedSummary(modelStatus, tdLossesStatus) {
        const content = document.getElementById('consolidatedContent');
        if (!content) return;
        
        const canGenerate = modelStatus.configured && tdLossesStatus.configured;
        
        content.innerHTML = `
            <div class="consolidated-container">
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card ${modelStatus.configured ? 'border-success' : 'border-warning'}">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas ${modelStatus.configured ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning'} me-2"></i>
                                    Model Selection
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <p class="mb-1">Status: <span class="badge ${modelStatus.configured ? 'bg-success' : 'bg-warning'}">
                                            ${modelStatus.configured ? 'Complete' : 'Incomplete'}
                                        </span></p>
                                        <small class="text-muted">${modelStatus.completed}/${modelStatus.total} sectors configured</small>
                                    </div>
                                    <button class="btn btn-outline-primary btn-sm" onclick="demandVizApp.showModelSelectionModal()">
                                        <i class="fas fa-cog me-1"></i>Configure
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card ${tdLossesStatus.configured ? 'border-success' : 'border-warning'}">
                            <div class="card-header">
                                <h6 class="mb-0">
                                    <i class="fas ${tdLossesStatus.configured ? 'fa-check-circle text-success' : 'fa-exclamation-triangle text-warning'} me-2"></i>
                                    T&D Losses
                                </h6>
                            </div>
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div>
                                        <p class="mb-1">Status: <span class="badge ${tdLossesStatus.configured ? 'bg-success' : 'bg-warning'}">
                                            ${tdLossesStatus.configured ? 'Complete' : 'Incomplete'}
                                        </span></p>
                                        <small class="text-muted">${tdLossesStatus.points} loss points configured</small>
                                    </div>
                                    <button class="btn btn-outline-primary btn-sm" onclick="demandVizApp.switchAnalysisTab('td-losses')">
                                        <i class="fas fa-cog me-1"></i>Configure
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="text-center mb-4">
                    <button class="btn ${canGenerate ? 'btn-success' : 'btn-secondary'} btn-lg" 
                            ${canGenerate ? '' : 'disabled'} 
                            onclick="demandVizApp.generateConsolidatedResults()">
                        <i class="fas fa-play me-2"></i>
                        Generate Consolidated Results
                    </button>
                    ${!canGenerate ? '<p class="text-muted mt-2">Complete model selection and T&D losses configuration to generate results</p>' : ''}
                </div>
                
                <div id="consolidatedResults" style="display: none;">
                    <!-- Results will be populated here -->
                </div>
            </div>
        `;
    }
    
    async generateConsolidatedResults() {
        try {
            this.showLoading('Generating consolidated results...');
            
            const response = await fetch(`${this.API_BASE}/consolidated/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_selection: this.state.modelConfig,
                    td_losses: this.state.tdLossesConfig,
                    filters: this.state.filters
                })
            });
            
            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to generate consolidated results');
            }
            
            // Display results
            this.displayConsolidatedResults(result.data);
            
            this.showNotification('success', 'Consolidated results generated successfully');
            
        } catch (error) {
            console.error('Error generating consolidated results:', error);
            this.showNotification('error', 'Failed to generate consolidated results: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    displayConsolidatedResults(data) {
        const resultsContainer = document.getElementById('consolidatedResults');
        if (!resultsContainer) return;
        
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">
                        <i class="fas fa-chart-bar me-2"></i>
                        Consolidated Results
                    </h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-lg-8">
                            <div class="chart-wrapper">
                                <canvas id="consolidatedSectorChart" width="400" height="300"></canvas>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="chart-wrapper">
                                <canvas id="consolidatedTotalChart" width="400" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="mb-0">Consolidated Data Table</h6>
                            <button class="btn btn-outline-primary btn-sm" onclick="demandVizApp.exportConsolidatedResults()">
                                <i class="fas fa-download me-1"></i>Export CSV
                            </button>
                        </div>
                        <div id="consolidatedDataTable">
                            ${this.createConsolidatedTable(data)}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        resultsContainer.style.display = 'block';
        
        // Create charts
        this.createConsolidatedCharts(data);
    }
    
    async createConsolidatedCharts(data) {
        // Create sector chart (stacked bar)
        await this.createConsolidatedSectorChart(data);
        
        // Create total chart (time series)
        await this.createConsolidatedTotalChart(data);
    }
    
    async createConsolidatedSectorChart(data) {
        try {
            const response = await fetch(`${this.API_BASE}/chart/consolidated/${this.state.currentScenario}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chart_type: 'stacked_bar',
                    filters: this.state.filters
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.chart_data) {
                const canvas = document.getElementById('consolidatedSectorChart');
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    this.state.charts['consolidatedSector'] = new Chart(ctx, result.chart_data);
                }
                return;
            }
        } catch (error) {
            console.warn('API consolidated sector chart generation failed, using fallback:', error);
        }
        
        // Fallback implementation
        this.createConsolidatedSectorChartFallback(data);
    }
    
    createConsolidatedSectorChartFallback(data) {
        const canvas = document.getElementById('consolidatedSectorChart');
        if (!canvas || !data) return;
        
        const ctx = canvas.getContext('2d');
        
        // Prepare data for stacked bar chart
        const sectors = Object.keys(data.sectors || {});
        const years = data.years || [];
        
        const datasets = sectors.map((sector, index) => {
            const sectorData = data.sectors[sector] || [];
            const color = this.getSectorColor(sector, index);
            
            return {
                label: sector.charAt(0).toUpperCase() + sector.slice(1),
                data: sectorData,
                backgroundColor: this.addTransparency(color, 0.8),
                borderColor: color,
                borderWidth: 1
            };
        });
        
        const unitDisplay = this.getUnitDisplayName(this.state.filters.unit);
        
        this.state.charts['consolidatedSector'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: years,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `Consolidated Demand by Sector (${unitDisplay})`,
                         font: { size: 16, weight: '600' }
                     },
                     legend: {
                         display: true,
                         position: 'top'
                     }
                 },
                 scales: {
                     x: {
                         stacked: true,
                         title: {
                             display: true,
                             text: 'Year'
                         }
                     },
                     y: {
                         stacked: true,
                         beginAtZero: true,
                         title: {
                             display: true,
                             text: `Demand (${unitDisplay})`
                         }
                     }
                 }
             }
         });
     }
     
     async createConsolidatedTotalChart(data) {
         try {
             const response = await fetch(`${this.API_BASE}/chart/consolidated/${this.state.currentScenario}`, {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({
                     chart_type: 'time_series',
                     filters: this.state.filters
                 })
             });
             
             const result = await response.json();
             
             if (result.success && result.chart_data) {
                 const canvas = document.getElementById('consolidatedTotalChart');
                 if (canvas) {
                     const ctx = canvas.getContext('2d');
                     this.state.charts['consolidatedTotal'] = new Chart(ctx, result.chart_data);
                 }
                 return;
             }
         } catch (error) {
             console.warn('API consolidated total chart generation failed, using fallback:', error);
         }
         
         // Fallback implementation
         this.createConsolidatedTotalChartFallback(data);
     }
     
     createConsolidatedTotalChartFallback(data) {
         const canvas = document.getElementById('consolidatedTotalChart');
         if (!canvas || !data) return;
         
         const ctx = canvas.getContext('2d');
         
         const years = data.years || [];
         const totalData = data.total || [];
         
         const unitDisplay = this.getUnitDisplayName(this.state.filters.unit);
         
         this.state.charts['consolidatedTotal'] = new Chart(ctx, {
             type: 'line',
             data: {
                 labels: years,
                 datasets: [{
                     label: 'Total Demand',
                     data: totalData,
                     borderColor: '#2563eb',
                     backgroundColor: this.addTransparency('#2563eb', 0.1),
                     borderWidth: 3,
                     tension: 0.2,
                     pointBackgroundColor: '#2563eb',
                     pointBorderColor: '#ffffff',
                     pointBorderWidth: 2,
                     pointRadius: 4,
                     pointHoverRadius: 6,
                     fill: true
                 }]
             },
             options: {
                 responsive: true,
                 maintainAspectRatio: false,
                 plugins: {
                     title: {
                         display: true,
                         text: `Total Consolidated Demand (${unitDisplay})`,
                         font: { size: 16, weight: '600' }
                     },
                     legend: {
                         display: false
                     }
                 },
                 scales: {
                     y: {
                         beginAtZero: true,
                         title: {
                             display: true,
                             text: `Demand (${unitDisplay})`
                         }
                     },
                     x: {
                         title: {
                             display: true,
                             text: 'Year'
                         }
                     }
                 }
             }
         });
     }
     
     createConsolidatedTable(data) {
         if (!data || !data.years) {
             return '<p class="text-muted">No consolidated data available</p>';
         }
         
         const sectors = Object.keys(data.sectors || {});
         const years = data.years;
         
         let html = `
             <div class="table-responsive">
                 <table class="table table-striped table-hover">
                     <thead class="table-dark">
                         <tr>
                             <th>Year</th>
                             ${sectors.map(sector => `<th>${sector.charAt(0).toUpperCase() + sector.slice(1)}</th>`).join('')}
                             <th>Total</th>
                         </tr>
                     </thead>
                     <tbody>
         `;
         
         years.forEach((year, yearIndex) => {
             html += `<tr><td><strong>${year}</strong></td>`;
             
             let yearTotal = 0;
             sectors.forEach(sector => {
                 const value = data.sectors[sector] && data.sectors[sector][yearIndex] !== undefined
                     ? data.sectors[sector][yearIndex]
                     : 0;
                 yearTotal += value;
                 html += `<td>${value.toFixed(3)}</td>`;
             });
             
             html += `<td><strong>${yearTotal.toFixed(3)}</strong></td></tr>`;
         });
         
         html += `
                     </tbody>
                 </table>
             </div>
         `;
         
         return html;
     }
     
     async exportConsolidatedResults() {
         try {
             const response = await fetch(`${this.API_BASE}/export/consolidated/${this.state.currentScenario}`);
             
             if (!response.ok) {
                 throw new Error('Export failed');
             }
             
             const blob = await response.blob();
             this.downloadBlob(blob, `consolidated_${this.state.currentScenario}.csv`);
             
             this.showNotification('success', 'Consolidated results exported successfully');
         } catch (error) {
             console.error('Error exporting consolidated results:', error);
             this.showNotification('error', 'Failed to export consolidated results: ' + error.message);
         }
     }
     
     // ========== COMPARISON MODE ==========
     
     toggleComparisonMode() {
         if (!this.state.currentScenario) {
             this.showNotification('warning', 'Please select a scenario first');
             return;
         }
         
         if (this.state.isComparisonMode) {
             this.exitComparisonMode();
         } else {
             this.showCompareScenarioModal();
         }
     }
     
     showCompareScenarioModal() {
         // Implementation for comparison modal
         this.showNotification('info', 'Comparison mode feature coming soon');
     }
     
     exitComparisonMode() {
         this.state.isComparisonMode = false;
         this.state.comparisonScenario = null;
         this.state.comparisonData = null;
         
         this.showNotification('info', 'Comparison mode disabled');
     }
     
     updateComparisonContent() {
         // Implementation for comparison content
         const content = document.getElementById('comparisonContent');
         if (!content) return;
         
         content.innerHTML = `
             <div class="empty-state">
                 <i class="fas fa-balance-scale fa-3x text-muted mb-3"></i>
                 <h5 class="text-muted">Comparison Mode</h5>
                 <p class="text-muted">Scenario comparison feature is coming soon.</p>
             </div>
         `;
     }
     
     // ========== MODEL SELECTION MODAL ==========
     
     showModelSelectionModal() {
         if (!this.state.currentData) {
             this.showNotification('warning', 'Please load scenario data first');
             return;
         }
         
         this.populateModelSelectionContent();
         this.showModal('modelSelectionModal');
     }
     
     populateModelSelectionContent() {
         const container = document.getElementById('modelSelectionContent');
         if (!container || !this.state.currentData) return;
         
         const sectors = Object.keys(this.state.currentData.sectors);
         let html = '';
         
         sectors.forEach(sector => {
             const sectorData = this.state.currentData.sectors[sector];
             const currentSelection = this.state.modelConfig[sector] || '';
             
             html += `
                 <div class="model-config-item mb-3">
                     <div class="d-flex justify-content-between align-items-center mb-2">
                         <h6 class="mb-0">${sector.charAt(0).toUpperCase() + sector.slice(1)}</h6>
                         <small class="text-muted">${sectorData.models.length} models available</small>
                     </div>
                     <select class="form-select" data-sector="${sector}">
                         <option value="">Select model...</option>
                         ${sectorData.models.map(model => 
                             `<option value="${model}" ${model === currentSelection ? 'selected' : ''}>${model}</option>`
                         ).join('')}
                     </select>
                 </div>
             `;
         });
         
         container.innerHTML = html;
         
         // Add event listeners for model selection
         container.querySelectorAll('select').forEach(select => {
             select.addEventListener('change', (e) => {
                 const sector = e.target.dataset.sector;
                 const model = e.target.value;
                 if (model) {
                     this.state.modelConfig[sector] = model;
                 } else {
                     delete this.state.modelConfig[sector];
                 }
                 this.updateSectorTabIndicators();
             });
         });
     }
     
     async saveModelConfiguration() {
         try {
             const sectors = Object.keys(this.state.currentData.sectors);
             const hasAllModels = sectors.every(sector => this.state.modelConfig[sector]);
             
             if (!hasAllModels) {
                 this.showNotification('warning', 'Please select models for all sectors');
                 return;
             }
             
             this.showLoading('Saving model configuration...');
             
             const response = await fetch(`${this.API_BASE}/model-selection/${this.state.currentScenario}`, {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({ model_selection: this.state.modelConfig })
             });
             
             const result = await response.json();
             if (!result.success) {
                 throw new Error(result.error || 'Failed to save model configuration');
             }
             
             this.hideModal('modelSelectionModal');
             this.showNotification('success', 'Model configuration saved successfully');
             this.updateSectorTabIndicators();
             
         } catch (error) {
             console.error('Error saving model configuration:', error);
             this.showNotification('error', 'Failed to save model configuration: ' + error.message);
         } finally {
             this.hideLoading();
         }
     }
     
     // ========== UTILITY METHODS ==========
     
     handleFilterChange(filterId, value) {
         switch (filterId) {
             case 'unitSelect':
                 this.state.filters.unit = value;
                 break;
             case 'startYearSelect':
                 this.state.filters.startYear = parseInt(value);
                 break;
             case 'endYearSelect':
                 this.state.filters.endYear = parseInt(value);
                 break;
         }
         
         // Auto-reload data if scenario is selected
         if (this.state.currentScenario) {
             this.loadScenarioData();
         }
     }
     
     getModelColor(model, index) {
         if (window.colorManager && typeof window.colorManager.getColor === 'function') {
             return window.colorManager.getColor('models', model);
         }
         return this.defaultColors[index % this.defaultColors.length];
     }
     
     getSectorColor(sector, index) {
         if (window.colorManager && typeof window.colorManager.getColor === 'function') {
             return window.colorManager.getColor('sectors', sector);
         }
         return this.defaultColors[index % this.defaultColors.length];
     }
     
     addTransparency(hexColor, alpha) {
         // Remove # if present
         const hex = hexColor.replace('#', '');
         
         // Convert hex to RGB
         const r = parseInt(hex.substr(0, 2), 16);
         const g = parseInt(hex.substr(2, 2), 16);
         const b = parseInt(hex.substr(4, 2), 16);
         
         // Return rgba string
         return `rgba(${r}, ${g}, ${b}, ${alpha})`;
     }
     
     getEnhancedChartConfig(chartType, title, unitDisplay) {
         const containerWidth = window.innerWidth;
         const isMobile = containerWidth < 768;
         const isTablet = containerWidth >= 768 && containerWidth < 1024;
         
         return {
             responsive: true,
             maintainAspectRatio: false,
             animation: {
                 duration: this.CHART_ANIMATION_DURATION,
                 easing: 'easeInOutQuart'
             },
             interaction: {
                 intersect: false,
                 mode: 'index'
             },
             plugins: {
                 title: {
                     display: true,
                     text: title,
                     font: {
                         size: isMobile ? 14 : isTablet ? 16 : 18,
                         weight: '600',
                         family: "'Inter', 'Segoe UI', 'Roboto', sans-serif"
                     },
                     color: '#1f2937',
                     padding: {
                         top: 10,
                         bottom: 20
                     }
                 },
                 legend: {
                     display: true,
                     position: isMobile ? 'bottom' : 'top',
                     labels: {
                         font: {
                             size: isMobile ? 11 : 12,
                             family: "'Inter', 'Segoe UI', 'Roboto', sans-serif"
                         },
                         color: '#374151',
                         padding: isMobile ? 15 : 20,
                         usePointStyle: true,
                         pointStyle: 'circle'
                     }
                 },
                 tooltip: {
                     backgroundColor: 'rgba(17, 24, 39, 0.95)',
                     titleColor: '#f9fafb',
                     bodyColor: '#f3f4f6',
                     borderColor: '#374151',
                     borderWidth: 1,
                     cornerRadius: 8,
                     displayColors: true,
                     mode: 'index',
                     intersect: false,
                     titleFont: {
                         size: 13,
                         weight: '600'
                     },
                     bodyFont: {
                         size: 12
                     },
                     callbacks: {
                         label: function(context) {
                             let label = context.dataset.label || '';
                             if (label) {
                                 label += ': ';
                             }
                             if (context.parsed.y !== null) {
                                 label += context.parsed.y.toFixed(3) + ' ' + unitDisplay;
                             }
                             return label;
                         }
                     }
                 }
             },
             scales: {
                 y: {
                     beginAtZero: true,
                     grace: '5%',
                     title: {
                         display: true,
                         text: `Demand (${unitDisplay})`,
                         font: {
                             size: isMobile ? 11 : 12,
                             weight: '600',
                             family: "'Inter', 'Segoe UI', 'Roboto', sans-serif"
                         },
                         color: '#374151'
                     },
                     ticks: {
                         font: {
                             size: isMobile ? 10 : 11
                         },
                         color: '#6b7280'
                     },
                     grid: {
                         color: 'rgba(156, 163, 175, 0.2)',
                         lineWidth: 1
                     }
                 },
                 x: {
                     title: {
                         display: true,
                         text: 'Year',
                         font: {
                             size: isMobile ? 11 : 12,
                             weight: '600',
                             family: "'Inter', 'Segoe UI', 'Roboto', sans-serif"
                         },
                         color: '#374151'
                     },
                     ticks: {
                         font: {
                             size: isMobile ? 10 : 11
                         },
                         color: '#6b7280'
                     },
                     grid: {
                         color: 'rgba(156, 163, 175, 0.2)',
                         lineWidth: 1
                     }
                 }
             },
             elements: {
                 point: {
                     radius: isMobile ? 3 : 4,
                     hoverRadius: isMobile ? 5 : 6,
                     borderWidth: 2,
                     hoverBorderWidth: 3
                 },
                 line: {
                     borderWidth: isMobile ? 2 : 3,
                     tension: 0.2
                 },
                 bar: {
                     borderRadius: chartType === 'bar' ? 4 : 0,
                     borderSkipped: false
                 }
             }
         };
     }
     
     getUnitDisplayName(unit) {
         return this.unitDisplayMap[unit] || unit;
     }
     
     clearScenario() {
         this.state.currentScenario = null;
         this.state.currentData = null;
         this.state.currentSector = null;
         this.exitComparisonMode();
         
         // Hide sections
         const sectorNavbar = document.getElementById('sectorNavbar');
         if (sectorNavbar) sectorNavbar.style.display = 'none';
         
         // Disable buttons
         const buttonsToDisable = ['modelSelectionBtn', 'compareScenarioBtn', 'colorSettingsBtn', 'exportDataBtn', 'exportChartBtn'];
         buttonsToDisable.forEach(buttonId => {
             const button = document.getElementById(buttonId);
             if (button) button.disabled = true;
         });
         
         // Reset content areas
         this.showSectorEmptyState();
         this.showTdLossesEmptyState();
         this.showConsolidatedEmptyState();
         
         // Destroy charts
         Object.values(this.state.charts).forEach(chart => {
             if (chart && typeof chart.destroy === 'function') {
                 chart.destroy();
             }
         });
         this.state.charts = {};
     }
     
     downloadBlob(blob, filename) {
         const url = window.URL.createObjectURL(blob);
         const a = document.createElement('a');
         a.href = url;
         a.download = filename;
         document.body.appendChild(a);
         a.click();
         document.body.removeChild(a);
         window.URL.revokeObjectURL(url);
     }
     
     exportCurrentData() {
         try {
             if (!this.state.currentData || !this.state.currentSector) {
                 this.showNotification('warning', 'No data available to export');
                 return;
             }
             
             const sectorData = this.state.currentData.sectors[this.state.currentSector];
             if (!sectorData) {
                 this.showNotification('warning', 'No sector data available to export');
                 return;
             }
             
             // Create CSV content
             let csvContent = 'Year';
             sectorData.models.forEach(model => {
                 csvContent += `,${model}`;
             });
             csvContent += '\n';
             
             sectorData.years.forEach((year, yearIndex) => {
                 csvContent += year;
                 sectorData.models.forEach(model => {
                     const value = sectorData[model] && sectorData[model][yearIndex] !== undefined
                         ? sectorData[model][yearIndex].toFixed(3)
                         : '0.000';
                     csvContent += `,${value}`;
                 });
                 csvContent += '\n';
             });
             
             // Create and download blob
             const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
             const filename = `${this.state.currentScenario}_${this.state.currentSector}_data.csv`;
             this.downloadBlob(blob, filename);
             
             this.showNotification('success', 'Data exported successfully');
         } catch (error) {
             console.error('Error exporting data:', error);
             this.showNotification('error', 'Failed to export data: ' + error.message);
         }
     }
     
     exportCurrentChart() {
         try {
             if (this.state.currentTab === 'sector-analysis' && this.state.currentSector) {
                 const chartId = `sector-chart-${this.state.currentSector}`;
                 const chart = this.state.charts[chartId];
                 
                 if (!chart) {
                     this.showNotification('warning', 'No chart available to export');
                     return;
                 }
                 
                 // Get canvas and convert to image
                 const canvas = document.getElementById(chartId);
                 if (!canvas) {
                     this.showNotification('warning', 'Chart canvas not found');
                     return;
                 }
                 
                 // Create image from canvas
                 const image = canvas.toDataURL('image/png');
                 const link = document.createElement('a');
                 link.href = image;
                 link.download = `${this.state.currentScenario}_${this.state.currentSector}_chart.png`;
                 document.body.appendChild(link);
                 link.click();
                 document.body.removeChild(link);
                 
                 this.showNotification('success', 'Chart exported successfully');
             } else {
                 this.showNotification('warning', 'No chart available to export');
             }
         } catch (error) {
             console.error('Error exporting chart:', error);
             this.showNotification('error', 'Failed to export chart: ' + error.message);
         }
     }
     
     openColorSettingsModal() {
         this.showNotification('info', 'Color settings feature coming soon');
     }
     
     toggleAdvancedFilters() {
         const advancedFilters = document.getElementById('advancedFilters');
         if (advancedFilters) {
             const isVisible = advancedFilters.style.display !== 'none';
             advancedFilters.style.display = isVisible ? 'none' : 'block';
         }
     }
     
     handleWindowResize() {
         // Resize charts if needed
         Object.values(this.state.charts).forEach(chart => {
             if (chart && typeof chart.resize === 'function') {
                 chart.resize();
             }
         });
     }
     
     // Modal Management
     showModal(modalId) {
         const modal = document.getElementById(modalId);
         if (modal) {
             modal.classList.add('show');
             modal.style.display = 'block';
             
             // Focus management
             const firstInput = modal.querySelector('input, select, button');
             if (firstInput) {
                 setTimeout(() => firstInput.focus(), 100);
             }
         }
     }
     
     hideModal(modalId) {
         const modal = document.getElementById(modalId);
         if (modal) {
             modal.classList.remove('show');
             modal.style.display = 'none';
         }
     }
     
     // Loading and Notification Management
     showLoading(message = 'Loading...') {
         const existingLoader = document.getElementById('loadingOverlay');
         if (existingLoader) return;
         
         const loader = document.createElement('div');
         loader.id = 'loadingOverlay';
         loader.className = 'loading-overlay';
         loader.innerHTML = `
             <div class="loading-spinner">
                 <i class="fas fa-spinner fa-spin"></i>
                 <div>${message}</div>
             </div>
         `;
         document.body.appendChild(loader);
     }
     
     hideLoading() {
         const loader = document.getElementById('loadingOverlay');
         if (loader) {
             loader.remove();
         }
     }
     
     showNotification(type, message, duration = this.NOTIFICATION_DURATION) {
         const notification = document.createElement('div');
         notification.className = `notification ${type}`;
         
         const icon = this.notificationIcons[type] || this.notificationIcons.info;
         
         notification.innerHTML = `
             <div style="display: flex; justify-content: space-between; align-items: center;">
                 <span><i class="fas ${icon} me-2"></i>${message}</span>
                 <button onclick="this.parentElement.parentElement.remove()" 
                         style="background: none; border: none; color: inherit; font-size: 1.2rem; cursor: pointer; margin-left: 1rem;">&times;</button>
             </div>
         `;
         
         document.body.appendChild(notification);
         
         // Show notification
         setTimeout(() => notification.classList.add('show'), 100);
         
         // Auto remove
         setTimeout(() => {
             notification.classList.remove('show');
             setTimeout(() => {
                 if (notification.parentElement) {
                     notification.parentElement.removeChild(notification);
                 }
             }, 300);
         }, duration);
     }
 }
 
 // Initialize the complete application
 window.demandVizApp = new CompleteDemandVisualizationApp();
