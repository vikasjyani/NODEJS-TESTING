// static/js/load_profile_generation.js
/**
 * Load Profile Generation Frontend Controller - Enhanced Version
 * Supports both Base Profile Scaling and Advanced STL with Load Factor Improvement
 */

class LoadProfileGenerator {
    constructor() {
        this.state = {
            currentStep: 1,
            selectedMethod: null,
            selectedDemandSource: null,
            selectedScenario: null,
            templateInfo: null,
            availableBaseYears: [],
            historicalDataSummary: null,
            generationInProgress: false,
            generatedProfile: null,
            selectedProfiles: []
        };

        this.API_BASE = '/load_profile/api';
        this.charts = {};
        this.datatable = null;

        this.initialize();
    }

    async initialize() {
        console.log('Load Profile Generator: Initializing');

        // Setup event listeners
        this.setupEventListeners();

        // Initialize DataTable first
        this.initializeDataTable();

        // Load initial data
        await this.loadInitialData();

        // Update UI
        this.updateWizardProgress();
        this.updateNamePreview();
    }

    setupEventListeners() {
        // Method selection
        document.querySelectorAll('.select-method-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const method = e.currentTarget.dataset.method;
                this.selectMethod(method);
            });
        });

        // Back button
        document.getElementById('backToMethodBtn')?.addEventListener('click', () => {
            this.goToStep(1);
        });

        // Form submission
        document.getElementById('configurationForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmission();
        });

        // Base year selection
        document.getElementById('baseYear')?.addEventListener('change', (e) => {
            this.handleBaseYearChange(e.target.value);
        });

        // Preview base year
        document.getElementById('previewBaseYear')?.addEventListener('click', () => {
            this.previewBaseYear();
        });

        // Demand source selection
        document.querySelectorAll('.source-card').forEach(card => {
            card.addEventListener('click', () => {
                const source = card.dataset.source;
                this.selectDemandSource(source);
            });
        });

        // Scenario selection
        document.getElementById('scenarioSelect')?.addEventListener('change', (e) => {
            this.handleScenarioChange(e.target.value);
        });

        // Year range changes
        document.getElementById('startFY')?.addEventListener('change', () => this.updatePeriodPreview());
        document.getElementById('endFY')?.addEventListener('change', () => this.updatePeriodPreview());
        document.getElementById('frequency')?.addEventListener('change', () => this.updatePeriodPreview());

        // Custom name input
        document.getElementById('customProfileName')?.addEventListener('input', () => {
            this.updateNamePreview();
        });

        // Load factor improvement toggle
        document.getElementById('enableLoadFactorImprovement')?.addEventListener('change', (e) => {
            const params = document.getElementById('lfImprovementParams');
            if (params) {
                params.style.display = e.target.checked ? 'flex' : 'none';

                if (e.target.checked) {
                    document.getElementById('lfTargetYear')?.setAttribute('required', 'required');
                    document.getElementById('lfImprovement')?.setAttribute('required', 'required');
                    
                    // Set default target year (10 years from start year)
                    const startFY = parseInt(document.getElementById('startFY')?.value) || new Date().getFullYear() + 1;
                    const defaultTargetYear = startFY + 10;
                    if (!document.getElementById('lfTargetYear').value) {
                        document.getElementById('lfTargetYear').value = defaultTargetYear;
                    }
                } else {
                    document.getElementById('lfTargetYear')?.removeAttribute('required');
                    document.getElementById('lfImprovement')?.removeAttribute('required');
                }
            }
        });

        // Results actions
        document.getElementById('downloadGeneratedProfile')?.addEventListener('click', () => {
            this.downloadGeneratedProfile();
        });

        document.getElementById('viewDetailedAnalysis')?.addEventListener('click', () => {
            this.viewDetailedAnalysis();
        });

        document.getElementById('generateAnotherProfile')?.addEventListener('click', () => {
            this.resetForNewGeneration();
        });

        // Cancel generation
        document.getElementById('cancelGeneration')?.addEventListener('click', () => {
            this.cancelGeneration();
        });

        // Saved profiles actions
        document.getElementById('refreshProfiles')?.addEventListener('click', () => {
            this.loadSavedProfiles();
        });

        document.getElementById('compareProfiles')?.addEventListener('click', () => {
            this.compareSelectedProfiles();
        });

        document.getElementById('selectAllProfiles')?.addEventListener('change', (e) => {
            this.toggleAllProfiles(e.target.checked);
        });

        // Visualization tabs
        document.querySelectorAll('#visualizationTabs a').forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const target = e.target.getAttribute('href');
                if (target === '#heatmapTab') {
                    this.createDailyHeatmap();
                } else if (target === '#statisticsTab') {
                    this.updateStatisticsView();
                }
            });
        });
    }

    async loadInitialData() {
        try {
            // Load template info
            await this.loadTemplateInfo();

            // Load saved profiles
            await this.loadSavedProfiles();

            // Update stats
            this.updateDashboardStats();

        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadTemplateInfo() {
        try {
            const response = await fetch(`${this.API_BASE}/template_info`);
            const result = await response.json();

            if (result.status === 'success') {
                this.state.templateInfo = result.data;
                this.updateTemplateDisplay();
                this.updateConstraintStatus();
            }
        } catch (error) {
            console.error('Error loading template info:', error);
            this.showAlert('danger', 'Failed to load template information');
        }
    }

    updateDashboardStats() {
        // Update template status
        const templateStatus = document.getElementById('templateStatus');
        if (templateStatus) {
            if (this.state.templateInfo) {
                templateStatus.textContent = 'Loaded';
                templateStatus.parentElement.parentElement.classList.add('bg-success');
            } else {
                templateStatus.textContent = 'Not Found';
                templateStatus.parentElement.parentElement.classList.remove('bg-success');
                templateStatus.parentElement.parentElement.classList.add('bg-danger');
            }
        }

        // Update available years
        const availableYears = document.getElementById('availableYears');
        if (availableYears && this.state.templateInfo) {
            availableYears.textContent = this.state.templateInfo.historical_data.available_years.length;
        }
    }

    selectMethod(method) {
        this.state.selectedMethod = method;

        // Update UI
        document.querySelectorAll('.method-card-v2').forEach(card => {
            card.classList.remove('selected');
        });
        const selectedCard = document.querySelector(`[data-method="${method}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Show method-specific configuration
        if (method === 'base_profile_scaling') {
            this.showElement('baseMethodConfig');
            this.hideElement('stlMethodConfig');
            this.loadAvailableBaseYears();
        } else if (method === 'stl_decomposition') {
            this.hideElement('baseMethodConfig');
            this.showElement('stlMethodConfig');
            // Temporarily disable historical summary loading until route is fixed
            // this.loadHistoricalDataSummary();
            this.displayHistoricalSummary({
                total_years: 'Loading...',
                total_records: 'Loading...',
                avg_load_factor: 'Loading...',
                peak_demand: 'Loading...'
            });
        }

        // Go to configuration step
        this.goToStep(2);

        this.showAlert('info', `Selected method: ${method.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}`);
    }

    showElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('d-none');
        }
    }

    hideElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add('d-none');
        }
    }

    async loadAvailableBaseYears() {
        try {
            const response = await fetch(`${this.API_BASE}/available_base_years`);
            const result = await response.json();
            if (result.status === 'success') {
                this.state.availableBaseYears = result.data.available_years;
                this.state.yearAnalysis = result.data.year_analysis;
                this.updateBaseYearSelect(result.data);
            }
        } catch (error) {
            console.error('Error loading base years:', error);
            this.showAlert('danger', 'Failed to load available years');
        }
    }

    updateBaseYearSelect(data) {
        const select = document.getElementById('baseYear');
        if (!select) return;

        select.innerHTML = '<option value="">Select a year...</option>';

        data.available_years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `FY ${year} (${year - 1}-${year})`;

            // Add data quality indicator
            const yearAnalysis = data.year_analysis[year];
            if (yearAnalysis && yearAnalysis.data_quality.missing_values === 0 && yearAnalysis.data_quality.zero_values < 100) {
                option.textContent += ' ⭐';
            }

            select.appendChild(option);
        });

        // Select recommended year
        if (data.recommended_year) {
            select.value = data.recommended_year;
            this.handleBaseYearChange(data.recommended_year);
        }
    }

    async handleBaseYearChange(year) {
        const yearInfo = document.getElementById('selectedYearInfo');
        const previewBtn = document.getElementById('previewBaseYear');
        
        if (!year) {
            if (yearInfo) {
                yearInfo.innerHTML = '<p class="text-muted">Select a year to view details</p>';
            }
            if (previewBtn) {
                previewBtn.disabled = true;
            }
            return;
        }

        if (previewBtn) {
            previewBtn.disabled = false;
        }

        if (!yearInfo) return;

        yearInfo.innerHTML = `
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Loading year data...</span>
        `;

        try {
            const info = this.state.yearAnalysis[year];
            if (!info) {
                throw new Error('Year data not found');
            }

            yearInfo.innerHTML = `
                <div class="mb-2">
                    <small class="text-muted">Data Points:</small>
                    <div class="fw-bold">${info.total_records.toLocaleString()}</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Date Range:</small>
                    <div class="fw-bold">${new Date(info.date_range.start).toLocaleDateString()} - ${new Date(info.date_range.end).toLocaleDateString()}</div>
                </div>
                <div class="mb-2">
                    <small class="text-muted">Data Quality:</small>
                    <div class="fw-bold text-${info.data_quality.missing_values === 0 ? 'success' : 'warning'}">
                        ${info.data_quality.missing_values === 0 ? 'Excellent' : 'Good'}
                    </div>
                </div>
            `;

            if (info.pattern_preview) {
                this.showMiniHeatmap(info.pattern_preview);
            }
        } catch (error) {
            console.error('Error loading base year info:', error);
            yearInfo.innerHTML = `<p class="text-danger">Failed to load year data: ${error.message}</p>`;
        }
    }

    showMiniHeatmap(patternData) {
        const container = document.getElementById('baseYearHeatmap');
        if (!container) return;

        container.classList.remove('d-none');

        // Create heatmap using Plotly
        const data = [{
            z: patternData.values,
            x: patternData.hours,
            y: patternData.months,
            type: 'heatmap',
            colorscale: 'Viridis',
            showscale: true
        }];

        const layout = {
            title: 'Average Load Pattern by Month and Hour',
            xaxis: { title: 'Hour of Day' },
            yaxis: { title: 'Month' },
            height: 300
        };

        if (typeof Plotly !== 'undefined') {
            Plotly.newPlot('heatmapChart', data, layout, { responsive: true });
        }
    }

    async loadHistoricalDataSummary() {
        try {
            const response = await fetch(`${this.API_BASE}/historical_summary`);
            
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response received:', text.substring(0, 200));
                throw new Error('Server returned non-JSON response');
            }
            
            const result = await response.json();

            if (result.status === 'success') {
                this.state.historicalDataSummary = result.data;
                this.displayHistoricalSummary(result.data);
            } else if (result.error) {
                console.warn('Historical summary returned with error:', result.error);
                // Display with limited data
                this.displayHistoricalSummary(result);
            } else {
                throw new Error(result.message || 'Failed to load historical summary');
            }
        } catch (error) {
            console.error('Error loading historical summary:', error);
            // Display fallback information
            this.displayHistoricalSummary({
                total_years: 0,
                total_records: 0,
                avg_load_factor: 0,
                peak_demand: 0,
                error: error.message
            });
        }
    }

    displayHistoricalSummary(summary) {
        const container = document.getElementById('historicalDataSummary');
        if (!container) return;

        // Handle potential missing data
        const totalYears = summary.total_years || 0;
        const totalRecords = summary.total_records || 0;
        const avgLoadFactor = summary.avg_load_factor || 0;
        const peakDemand = summary.peak_demand || 0;

        container.innerHTML = `
            <div class="col-md-3">
                <div class="text-center">
                    <h4>${totalYears}</h4>
                    <small class="text-muted">Years of Data</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4>${(totalRecords / 1000).toFixed(0)}k</h4>
                    <small class="text-muted">Data Points</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4>${avgLoadFactor.toFixed(1)}%</h4>
                    <small class="text-muted">Avg Load Factor</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="text-center">
                    <h4>${peakDemand.toFixed(0)} MW</h4>
                    <small class="text-muted">Peak Demand</small>
                </div>
            </div>
            ${summary.error ? `
                <div class="col-12 mt-2">
                    <div class="alert alert-warning alert-sm">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Limited data available: ${summary.error}
                    </div>
                </div>
            ` : ''}
        `;
    }

    selectDemandSource(source) {
        this.state.selectedDemandSource = source;

        // Update UI
        document.querySelectorAll('.source-card').forEach(card => {
            card.classList.remove('selected');
        });
        const selectedCard = document.querySelector(`[data-source="${source}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Update radio
        const radio = document.querySelector(`input[value="${source}"]`);
        if (radio) {
            radio.checked = true;
        }

        // Show/hide scenario selection
        const scenarioSelect = document.getElementById('scenarioSelect');
        if (source === 'scenario') {
            if (scenarioSelect) {
                scenarioSelect.style.display = 'block';
                scenarioSelect.setAttribute('required', 'required');
            }
        } else {
            if (scenarioSelect) {
                scenarioSelect.style.display = 'none';
                scenarioSelect.removeAttribute('required');
            }
            this.updateTemplateInfoDisplay();
        }
    }

    updateTemplateDisplay() {
        const templateInfo = document.getElementById('templateInfo');
        if (!templateInfo) return;

        if (this.state.templateInfo) {
            const info = this.state.templateInfo;
            templateInfo.innerHTML = `
                <div class="mt-2">
                    <div class="d-flex justify-content-between mb-1">
                        <small>Historical Records:</small>
                        <small class="fw-bold">${info.historical_data.records.toLocaleString()}</small>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <small>Available Years:</small>
                        <small class="fw-bold">${info.historical_data.available_years.length}</small>
                    </div>
                    <div class="d-flex justify-content-between">
                        <small>Demand Scenarios:</small>
                        <small class="fw-bold">${info.total_demand.years}</small>
                    </div>
                </div>
            `;
        } else {
            templateInfo.innerHTML = `
                <div class="alert alert-warning mt-2 mb-0">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Template file not found
                </div>
            `;
        }
    }

    updateTemplateInfoDisplay() {
        this.updateTemplateDisplay();
    }

    updateConstraintStatus() {
        if (!this.state.templateInfo) return;

        const constraints = this.state.templateInfo.constraints_available;

        // Monthly peaks
        const monthlyPeaksStatus = document.getElementById('monthlyPeaksStatus');
        const applyMonthlyPeaks = document.getElementById('applyMonthlyPeaks');
        
        if (monthlyPeaksStatus) {
            if (constraints.monthly_peaks) {
                monthlyPeaksStatus.innerHTML = `
                    <span class="text-success">
                        <i class="fas fa-check-circle me-1"></i>
                        ${constraints.monthly_peaks_source === 'template' ? 'From template' : 'Calculated'}
                    </span>
                `;
                if (applyMonthlyPeaks) applyMonthlyPeaks.disabled = false;
            } else {
                monthlyPeaksStatus.innerHTML = `
                    <span class="text-warning">
                        <i class="fas fa-exclamation-circle me-1"></i>
                        Not available
                    </span>
                `;
                if (applyMonthlyPeaks) applyMonthlyPeaks.disabled = true;
            }
        }

        // Load factors
        const loadFactorsStatus = document.getElementById('loadFactorsStatus');
        const applyLoadFactors = document.getElementById('applyLoadFactors');
        
        if (loadFactorsStatus) {
            if (constraints.monthly_load_factors) {
                loadFactorsStatus.innerHTML = `
                    <span class="text-success">
                        <i class="fas fa-check-circle me-1"></i>
                        ${constraints.load_factors_source === 'template' ? 'From template' : 'Calculated'}
                    </span>
                `;
                if (applyLoadFactors) applyLoadFactors.disabled = false;
            } else {
                loadFactorsStatus.innerHTML = `
                    <span class="text-warning">
                        <i class="fas fa-exclamation-circle me-1"></i>
                        Not available
                    </span>
                `;
                if (applyLoadFactors) applyLoadFactors.disabled = true;
            }
        }
    }

    async handleScenarioChange(scenarioName) {
        if (!scenarioName) return;

        const scenarioInfo = document.getElementById('scenarioInfo');
        if (!scenarioInfo) return;

        scenarioInfo.innerHTML = `
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Loading scenario...</span>
        `;

        try {
            const response = await fetch(`${this.API_BASE}/scenario_info/${scenarioName}`);
            const result = await response.json();

            if (result.status === 'success') {
                const info = result.data;
                scenarioInfo.innerHTML = `
                    <div class="alert alert-info mb-0">
                        <div class="d-flex justify-content-between mb-1">
                            <small>Years:</small>
                            <small class="fw-bold">${info.data_summary.total_years}</small>
                        </div>
                        <div class="d-flex justify-content-between mb-1">
                            <small>Growth Rate:</small>
                            <small class="fw-bold">${info.data_summary.growth_analysis.average_growth_rate.toFixed(1)}%</small>
                        </div>
                        <div class="d-flex justify-content-between">
                            <small>Peak Demand:</small>
                            <small class="fw-bold">${(info.data_summary.demand_range.max / 1000000).toFixed(1)} TWh</small>
                        </div>
                    </div>
                `;

                this.state.selectedScenario = info;
                this.showAlert('success', `Loaded scenario: ${scenarioName}`);
            }
        } catch (error) {
            console.error('Error loading scenario:', error);
            scenarioInfo.innerHTML = '<p class="text-danger mb-0">Failed to load scenario</p>';
        }
    }

    updatePeriodPreview() {
        const startFY = parseInt(document.getElementById('startFY')?.value);
        const endFY = parseInt(document.getElementById('endFY')?.value);
        const frequency = document.getElementById('frequency')?.value;
        const preview = document.getElementById('periodPreview');

        if (startFY && endFY && startFY < endFY && preview) {
            const years = endFY - startFY + 1;
            const frequencies = {
                'hourly': '8,760 data points per year',
                '15min': '35,040 data points per year',
                '30min': '17,520 data points per year',
                'daily': '365 data points per year'
            };

            preview.textContent = `Will generate ${years} years of data (${frequencies[frequency] || 'data points per year'})`;
        }
    }

    updateNamePreview() {
        const customName = document.getElementById('customProfileName')?.value.trim();
        const preview = document.getElementById('namePreview');
        
        if (!preview) return;

        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '_');

        if (customName) {
            const safeName = customName.replace(/[^a-zA-Z0-9\s\-_]/g, '').replace(/\s+/g, '_');
            preview.innerHTML = `
                <code class="text-success">${safeName}_${timestamp}.csv</code>
            `;
        } else {
            const method = this.state.selectedMethod || 'profile';
            preview.innerHTML = `
                <code class="text-info">${method}_${timestamp}.csv</code>
                <small class="text-muted d-block mt-1">Auto-generated</small>
            `;
        }
    }

    async previewBaseYear() {
        const baseYear = document.getElementById('baseYear')?.value;
        if (!baseYear) {
            this.showAlert('warning', 'Please select a base year first');
            return;
        }

        try {
            this.showLoading(true);

            const response = await fetch(`${this.API_BASE}/preview_base_profiles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ base_year: parseInt(baseYear) })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.displayBaseYearPreview(result.data);
            }
        } catch (error) {
            console.error('Error previewing base year:', error);
            this.showAlert('danger', 'Failed to generate preview');
        } finally {
            this.showLoading(false);
        }
    }

    displayBaseYearPreview(previewData) {
        const modalElement = document.getElementById('baseYearPreviewModal');
        if (!modalElement) return;

        const modal = new bootstrap.Modal(modalElement);
        const content = document.getElementById('baseYearPreviewContent');

        if (content) {
            content.innerHTML = `
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Summary Statistics</h6>
                                <ul class="list-unstyled mb-0">
                                    <li class="mb-2">
                                        <strong>Base Year:</strong> FY ${previewData.base_year}
                                    </li>
                                    <li class="mb-2">
                                        <strong>Total Patterns:</strong> ${previewData.total_patterns}
                                    </li>
                                    <li class="mb-2">
                                        <strong>Weekday Patterns:</strong> ${previewData.patterns_by_type.weekday_patterns}
                                    </li>
                                    <li class="mb-2">
                                        <strong>Weekend/Holiday:</strong> ${previewData.patterns_by_type.weekend_holiday_patterns}
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Load Pattern Visualization</h6>
                                <canvas id="previewPatternChart" height="300"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mt-3">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-body">
                                <h6 class="card-title">Monthly Pattern Heatmap</h6>
                                <div id="monthlyPatternHeatmap"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        modalElement.removeAttribute('inert');
        modal.show();
        
        modalElement.addEventListener('shown.bs.modal', () => {
            const firstFocusable = modalElement.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        }, { once: true });
        
        modalElement.addEventListener('hidden.bs.modal', () => {
            modalElement.setAttribute('inert', '');
        }, { once: true });
        
        setTimeout(() => {
            this.createPreviewCharts(previewData);
        }, 300);
    }

    createPreviewCharts(previewData) {
        // Line chart for sample patterns
        const ctx = document.getElementById('previewPatternChart')?.getContext('2d');
        if (!ctx || typeof Chart === 'undefined') return;

        const datasets = [];
        const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];

        previewData.sample_patterns.forEach((pattern, index) => {
            if (pattern.weekday.length > 0) {
                datasets.push({
                    label: `${pattern.month_name} Weekday`,
                    data: pattern.weekday.map(p => p.fraction),
                    borderColor: colors[index % colors.length],
                    backgroundColor: 'transparent',
                    tension: 0.4
                });
            }

            if (pattern.weekend.length > 0) {
                datasets.push({
                    label: `${pattern.month_name} Weekend`,
                    data: pattern.weekend.map(p => p.fraction),
                    borderColor: colors[index % colors.length],
                    borderDash: [5, 5],
                    backgroundColor: 'transparent',
                    tension: 0.4
                });
            }
        });

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({ length: 24 }, (_, i) => i),
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Daily Load Patterns by Month'
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Hour of Day' }
                    },
                    y: {
                        title: { display: true, text: 'Load Fraction' }
                    }
                }
            }
        });

        // Create heatmap
        if (previewData.heatmap_data && typeof Plotly !== 'undefined') {
            this.createMonthlyHeatmap('monthlyPatternHeatmap', previewData.heatmap_data);
        }
    }

    createMonthlyHeatmap(elementId, heatmapData) {
        const data = [{
            z: heatmapData.values,
            x: heatmapData.hours,
            y: heatmapData.months,
            type: 'heatmap',
            colorscale: 'Viridis',
            showscale: true,
            hoverongaps: false
        }];

        const layout = {
            xaxis: {
                title: 'Hour of Day',
                tickmode: 'linear',
                tick0: 0,
                dtick: 2
            },
            yaxis: {
                title: 'Month',
                tickmode: 'array',
                tickvals: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                ticktext: ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
            },
            height: 400,
            margin: { t: 30, r: 30, b: 50, l: 50 }
        };

        Plotly.newPlot(elementId, data, layout, { responsive: true });
    }

    goToStep(step) {
        this.state.currentStep = step;

        // Hide all content
        document.querySelectorAll('.wizard-content').forEach(content => {
            content.classList.add('d-none');
        });

        // Show current step content
        const stepContent = document.getElementById(`step${step}Content`);
        if (stepContent) {
            stepContent.classList.remove('d-none');
        }

        // Update wizard progress
        this.updateWizardProgress();

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    updateWizardProgress() {
        document.querySelectorAll('.wizard-step').forEach((step, index) => {
            const stepNum = index + 1;

            if (stepNum < this.state.currentStep) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (stepNum === this.state.currentStep) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    async handleFormSubmission() {
        if (!this.validateForm()) {
            return;
        }

        const formData = new FormData(document.getElementById('configurationForm'));
        const config = Object.fromEntries(formData.entries());

        // Add method and demand source
        config.method = this.state.selectedMethod;
        config.demand_source = this.state.selectedDemandSource;
        config.start_fy = parseInt(config.start_fy, 10);
        config.end_fy = parseInt(config.end_fy, 10);

        // Handle method-specific parameters
        if (this.state.selectedMethod === 'base_profile_scaling') {
            config.base_year = parseInt(document.getElementById('baseYear')?.value, 10);

            // Remove STL-specific parameters
            delete config.stl_period;
            delete config.stl_seasonal;
            delete config.stl_robust;
            delete config.lf_target_year;
            delete config.lf_improvement_percent;
            delete config.enable_lf_improvement;

        } else if (this.state.selectedMethod === 'stl_decomposition') {
            // STL parameters
            config.stl_params = {
                period: parseInt(config.stl_period) || 8760,
                seasonal: parseInt(config.stl_seasonal) || 13,
                robust: config.stl_robust === 'true'
            };

            // Load factor improvement
            const lfEnabled = document.getElementById('enableLoadFactorImprovement')?.checked;
            if (lfEnabled) {
                const targetYear = parseInt(config.lf_target_year, 10);
                const improvementPercent = parseFloat(config.lf_improvement_percent);
                
                if (targetYear && improvementPercent) {
                    config.lf_improvement = {
                        enabled: true,
                        target_year: targetYear,
                        improvement_percent: improvementPercent
                    };
                }
            }

            // Remove non-STL parameters
            delete config.stl_period;
            delete config.stl_seasonal;
            delete config.stl_robust;
            delete config.enable_lf_improvement;
            delete config.lf_target_year;
            delete config.lf_improvement_percent;
            delete config.base_year;
        }

        // Process constraints
        config.apply_monthly_peaks = document.getElementById('applyMonthlyPeaks')?.checked || false;
        config.apply_load_factors = document.getElementById('applyLoadFactors')?.checked || false;

        // Custom name
        const customName = document.getElementById('customProfileName')?.value.trim();
        if (customName) {
            config.custom_name = customName;
        }

        console.log('Form config:', JSON.stringify(config, null, 2));

        // Generate profile
        await this.generateProfile(config);
    }

    validateForm() {
        // Method validation
        if (!this.state.selectedMethod) {
            this.showAlert('warning', 'Please select a generation method');
            return false;
        }

        // Base profile specific validation
        if (this.state.selectedMethod === 'base_profile_scaling') {
            const baseYear = document.getElementById('baseYear')?.value;
            if (!baseYear || isNaN(parseInt(baseYear))) {
                this.showAlert('warning', 'Please select a valid base year');
                return false;
            }
            const year = parseInt(baseYear);
            if (year < 2000 || year > 2030) {
                this.showAlert('warning', 'Base year must be between 2000 and 2030');
                return false;
            }
        }

        // STL specific validation
        if (this.state.selectedMethod === 'stl_decomposition') {
            const lfEnabled = document.getElementById('enableLoadFactorImprovement')?.checked;
            if (lfEnabled) {
                const targetYear = parseInt(document.getElementById('lfTargetYear')?.value);
                const improvementPercent = parseFloat(document.getElementById('lfImprovement')?.value);
                
                if (!targetYear || targetYear < 2025 || targetYear > 2050) {
                    this.showAlert('warning', 'Load factor target year must be between 2025 and 2050');
                    return false;
                }
                
                if (!improvementPercent || improvementPercent <= 0 || improvementPercent > 50) {
                    this.showAlert('warning', 'Load factor improvement must be between 0 and 50 percent');
                    return false;
                }
            }
        }

        // Demand source validation
        if (!this.state.selectedDemandSource) {
            this.showAlert('warning', 'Please select a demand data source');
            return false;
        }

        if (this.state.selectedDemandSource === 'scenario') {
            const scenario = document.getElementById('scenarioSelect')?.value;
            if (!scenario) {
                this.showAlert('warning', 'Please select a demand scenario');
                return false;
            }
        }

        // Year range validation
        const startFY = parseInt(document.getElementById('startFY')?.value);
        const endFY = parseInt(document.getElementById('endFY')?.value);
        
        if (!startFY || !endFY || isNaN(startFY) || isNaN(endFY)) {
            this.showAlert('warning', 'Please specify valid start and end years');
            return false;
        }
        
        if (startFY >= endFY) {
            this.showAlert('warning', 'End year must be greater than start year');
            return false;
        }
        
        if (endFY - startFY > 50) {
            this.showAlert('warning', 'Forecast period exceeds 50 years, which may affect accuracy');
        }

        // Frequency validation
        const frequency = document.getElementById('frequency')?.value;
        if (!['hourly', '15min', '30min', 'daily'].includes(frequency)) {
            this.showAlert('warning', 'Please select a valid output frequency');
            return false;
        }

        // Custom name validation
        const customName = document.getElementById('customProfileName')?.value.trim();
        if (customName) {
            if (customName.length < 2 || customName.length > 50) {
                this.showAlert('warning', 'Custom name must be 2–50 characters');
                return false;
            }
            const invalidChars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|'];
            if (invalidChars.some(char => customName.includes(char))) {
                this.showAlert('warning', 'Custom name contains invalid characters');
                return false;
            }
        }

        return true;
    }

    async generateProfile(config) {
        console.log('Generating profile with config:', JSON.stringify(config, null, 2));
        
        try {
            this.state.generationInProgress = true;
            this.goToStep(3);
            
            const endpoint = config.method === 'base_profile_scaling' ?
                '/generate_base_profile' : '/generate_stl_profile';
            
            this.updateGenerationProgress(0, 'Initializing...');
            
            const response = await fetch(`${this.API_BASE}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.state.generatedProfile = result.data;
                this.updateGenerationProgress(100, 'Complete!');
                setTimeout(() => {
                    this.goToStep(4);
                    this.displayResults();
                }, 1000);
            } else {
                const errorMessage = result.errors ? result.errors.join('; ') : result.message || 'Generation failed';
                throw new Error(errorMessage);
            }
        } catch (error) {
            console.error('Error generating profile:', error);
            this.showAlert('danger', `Generation failed: ${error.message}`);
            this.goToStep(2);
        } finally {
            this.state.generationInProgress = false;
        }
    }

    updateGenerationProgress(percent, message) {
        // Update circular progress
        const circle = document.getElementById('progressCircle');
        const percentText = document.getElementById('progressPercent');
        const messageEl = document.getElementById('progressMessage');

        if (circle && percentText && messageEl) {
            const circumference = 2 * Math.PI * 90;
            const offset = circumference - (percent / 100) * circumference;

            circle.style.strokeDashoffset = offset;
            percentText.textContent = `${percent}%`;
            messageEl.textContent = message;
        }

        // Update steps
        const steps = ['progressStep1', 'progressStep2', 'progressStep3', 'progressStep4'];
        const stepPercent = 100 / steps.length;

        steps.forEach((stepId, index) => {
            const step = document.getElementById(stepId);
            if (step) {
                if (percent >= (index + 1) * stepPercent) {
                    step.classList.add('completed');
                } else if (percent >= index * stepPercent) {
                    step.classList.add('active');
                } else {
                    step.classList.remove('active', 'completed');
                }
            }
        });
    }

    displayResults() {
        if (!this.state.generatedProfile) return;

        // Update summary
        this.updateResultsSummary();

        // Update validation
        this.updateValidationResults();

        // Create visualizations
        this.createProfileChart();

        // Load saved profiles
        this.loadSavedProfiles();
    }

    updateResultsSummary() {
        const profile = this.state.generatedProfile;
        const summary = document.getElementById('resultsSummary');
        
        if (!summary) return;

        let methodDisplay = 'Unknown Method';
        if (profile.generation_config?.method) {
            methodDisplay = profile.generation_config.method.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }

        summary.innerHTML = `
            <div class="result-item mb-3">
                <i class="fas fa-file text-primary me-2"></i>
                <strong>Profile ID:</strong>
                <div class="text-muted">${profile.save_info?.profile_id || 'Unknown'}</div>
            </div>
            
            <div class="result-item mb-3">
                <i class="fas fa-chart-line text-success me-2"></i>
                <strong>Method:</strong>
                <div class="text-muted">${methodDisplay}</div>
            </div>
            
            <div class="result-item mb-3">
                <i class="fas fa-calendar text-info me-2"></i>
                <strong>Period:</strong>
                <div class="text-muted">FY ${profile.summary?.start_fy || 'N/A'} - FY ${profile.summary?.end_fy || 'N/A'}</div>
            </div>
            
            <div class="result-item mb-3">
                <i class="fas fa-database text-warning me-2"></i>
                <strong>File Size:</strong>
                <div class="text-muted">${profile.save_info?.file_size?.toFixed(1) || 'N/A'} MB</div>
            </div>
            
            ${profile.validation?.general_stats ? `
                <div class="result-item">
                    <i class="fas fa-bolt text-danger me-2"></i>
                    <strong>Peak Demand:</strong>
                    <div class="text-muted">${profile.validation.general_stats.peak_demand.toFixed(1)} kW</div>
                </div>
            ` : ''}
        `;
    }

    updateValidationResults() {
        const validation = this.state.generatedProfile?.validation;
        const container = document.getElementById('validationResults');
        
        if (!container || !validation) return;

        let html = '';

        // Annual totals validation
        if (validation.annual_totals) {
            html += '<h6 class="mb-2">Annual Validation</h6>';
            html += '<div class="validation-items">';

            Object.entries(validation.annual_totals).forEach(([year, data]) => {
                const status = data.difference_percent < 1 ? 'success' :
                    data.difference_percent < 5 ? 'warning' : 'danger';

                html += `
                    <div class="d-flex justify-content-between mb-2">
                        <span>${year}:</span>
                        <span class="badge bg-${status}">${data.difference_percent.toFixed(2)}% diff</span>
                    </div>
                `;
            });

            html += '</div>';
        }

        // General stats
        if (validation.general_stats) {
            html += '<h6 class="mt-3 mb-2">Statistics</h6>';
            html += `
                <div class="small">
                    <div class="d-flex justify-content-between mb-1">
                        <span>Load Factor:</span>
                        <span class="fw-bold">${(validation.general_stats.overall_load_factor * 100).toFixed(1)}%</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span>Avg Demand:</span>
                        <span class="fw-bold">${validation.general_stats.avg_demand.toFixed(1)} kW</span>
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    createProfileChart() {
        const ctx = document.getElementById('profileChart')?.getContext('2d');
        if (!ctx || typeof Chart === 'undefined') return;

        // Destroy existing chart
        if (this.charts.profile) {
            this.charts.profile.destroy();
        }

        // Get sample data (first month)
        const forecastData = this.state.generatedProfile.forecast || [];
        const sampleSize = Math.min(24 * 30, forecastData.length);
        const sampleData = forecastData.slice(0, sampleSize);

        const labels = sampleData.map((row) => {
            return new Date(row.ds);
        });

        const data = sampleData.map(row => row.demand);

        this.charts.profile = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Load Profile',
                    data: data,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Generated Load Profile (First 30 Days)'
                    },
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: true,
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'x',
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MMM dd'
                            }
                        },
                        title: { display: true, text: 'Date' }
                    },
                    y: {
                        title: { display: true, text: 'Demand (kW)' }
                    }
                }
            }
        });
    }

    createDailyHeatmap() {
        if (!this.state.generatedProfile || typeof Plotly === 'undefined') return;

        // Process data for heatmap
        const forecastData = this.state.generatedProfile.forecast || [];
        const heatmapData = this.processDataForHeatmap(forecastData);

        const data = [{
            z: heatmapData.values,
            x: heatmapData.hours,
            y: heatmapData.days,
            type: 'heatmap',
            colorscale: 'Viridis',
            showscale: true
        }];

        const layout = {
            title: 'Daily Load Pattern Heatmap',
            xaxis: { title: 'Hour of Day' },
            yaxis: { title: 'Day of Year' },
            height: 400
        };

        Plotly.newPlot('dailyHeatmap', data, layout, { responsive: true });
    }

    processDataForHeatmap(forecastData) {
        // Group by day and hour
        const heatmapMatrix = [];
        const days = [];

        if (!forecastData.length) {
            return { values: [], hours: [], days: [] };
        }

        // Process first year only for visualization
        const firstYearData = forecastData.filter(row => row.financial_year === forecastData[0].financial_year);

        let currentDay = null;
        let dayData = [];

        firstYearData.forEach(row => {
            const date = new Date(row.ds);
            const dayStr = date.toISOString().split('T')[0];

            if (currentDay !== dayStr) {
                if (dayData.length > 0) {
                    heatmapMatrix.push(dayData);
                }
                currentDay = dayStr;
                dayData = [];
                days.push(dayStr);
            }

            dayData.push(row.demand);
        });

        // Add last day
        if (dayData.length > 0) {
            heatmapMatrix.push(dayData);
        }

        return {
            values: heatmapMatrix,
            hours: Array.from({ length: 24 }, (_, i) => i),
            days: days.map((d, i) => i + 1)
        };
    }

    updateStatisticsView() {
        if (!this.state.generatedProfile) return;

        const stats = this.state.generatedProfile.validation?.general_stats;
        const container = document.getElementById('profileStatistics');

        if (!container) return;

        if (!stats) {
            container.innerHTML = '<p class="text-muted">No statistics available</p>';
            return;
        }

        // Calculate additional statistics
        const forecastData = this.state.generatedProfile.forecast || [];
        const monthlyStats = this.calculateMonthlyStatistics(forecastData);

        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Overall Statistics</h6>
                    <table class="table table-sm">
                        <tbody>
                            <tr>
                                <td>Total Hours:</td>
                                <td class="fw-bold">${stats.total_hours?.toLocaleString() || 'N/A'}</td>
                            </tr>
                            <tr>
                                <td>Peak Demand:</td>
                                <td class="fw-bold">${stats.peak_demand?.toFixed(1) || 'N/A'} kW</td>
                            </tr>
                            <tr>
                                <td>Minimum Demand:</td>
                                <td class="fw-bold">${stats.min_demand?.toFixed(1) || 'N/A'} kW</td>
                            </tr>
                            <tr>
                                <td>Average Demand:</td>
                                <td class="fw-bold">${stats.avg_demand?.toFixed(1) || 'N/A'} kW</td>
                            </tr>
                            <tr>
                                <td>Load Factor:</td>
                                <td class="fw-bold">${((stats.overall_load_factor || 0) * 100).toFixed(1)}%</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Monthly Statistics</h6>
                    <canvas id="monthlyStatsChart" height="200"></canvas>
                </div>
            </div>
        `;

        // Create monthly stats chart
        setTimeout(() => {
            this.createMonthlyStatsChart(monthlyStats);
        }, 100);
    }

    calculateMonthlyStatistics(forecastData) {
        const monthlyData = {};

        forecastData.forEach(row => {
            const month = row.financial_month;
            if (!monthlyData[month]) {
                monthlyData[month] = {
                    demands: [],
                    total: 0,
                    count: 0
                };
            }
            monthlyData[month].demands.push(row.demand);
            monthlyData[month].total += row.demand;
            monthlyData[month].count++;
        });

        const monthNames = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
        const stats = [];

        for (let month = 1; month <= 12; month++) {
            if (monthlyData[month]) {
                const demands = monthlyData[month].demands;
                stats.push({
                    month: monthNames[month - 1],
                    avg: monthlyData[month].total / monthlyData[month].count,
                    peak: Math.max(...demands),
                    min: Math.min(...demands)
                });
            }
        }

        return stats;
    }

    createMonthlyStatsChart(monthlyStats) {
        const ctx = document.getElementById('monthlyStatsChart')?.getContext('2d');
        if (!ctx || typeof Chart === 'undefined') return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: monthlyStats.map(s => s.month),
                datasets: [
                    {
                        label: 'Peak',
                        data: monthlyStats.map(s => s.peak),
                        backgroundColor: 'rgba(239, 68, 68, 0.6)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Average',
                        data: monthlyStats.map(s => s.avg),
                        backgroundColor: 'rgba(59, 130, 246, 0.6)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Monthly Demand Statistics'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Demand (kW)' }
                    }
                }
            }
        });
    }

    async downloadGeneratedProfile() {
        if (!this.state.generatedProfile?.save_info) {
            this.showAlert('warning', 'No profile to download');
            return;
        }

        const profileId = this.state.generatedProfile.save_info.profile_id;
        window.location.href = `${this.API_BASE}/download_profile/${profileId}`;
        this.showAlert('success', 'Download started');
    }

    viewDetailedAnalysis() {
        if (!this.state.generatedProfile?.save_info) {
            this.showAlert('warning', 'No profile to analyze');
            return;
        }

        const profileId = this.state.generatedProfile.save_info.profile_id;
        window.location.href = `/load_profile_analysis/?profile=${encodeURIComponent(profileId)}`;
    }

    resetForNewGeneration() {
        // Reset state
        this.state = {
            ...this.state,
            currentStep: 1,
            selectedMethod: null,
            selectedDemandSource: null,
            selectedScenario: null,
            generatedProfile: null
        };

        // Reset form
        const form = document.getElementById('configurationForm');
        if (form) form.reset();

        // Reset UI
        document.querySelectorAll('.method-card-v2').forEach(card => {
            card.classList.remove('selected');
        });

        document.querySelectorAll('.source-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Clear custom name
        const customNameInput = document.getElementById('customProfileName');
        if (customNameInput) customNameInput.value = '';
        this.updateNamePreview();

        // Go to step 1
        this.goToStep(1);
    }

    cancelGeneration() {
        if (this.state.generationInProgress) {
            this.state.generationInProgress = false;
            this.showAlert('info', 'Generation cancelled');
            this.goToStep(2);
        }
    }

    initializeDataTable() {
        const tableElement = document.getElementById('savedProfilesTable');
        if (!tableElement) {
            console.error('Table element #savedProfilesTable not found');
            return;
        }
        
        // Check if jQuery and DataTables are available
        if (!window.jQuery) {
            console.error('jQuery library not loaded');
            return;
        }
        
        if (!$.fn.DataTable) {
            console.error('DataTables library not loaded');
            return;
        }
        
        // Destroy existing DataTable if it exists
        if ($.fn.DataTable.isDataTable('#savedProfilesTable')) {
            $('#savedProfilesTable').DataTable().destroy();
        }
        
        try {
            this.datatable = $('#savedProfilesTable').DataTable({
                pageLength: 10,
                order: [[3, 'desc']],
                columnDefs: [
                    { orderable: false, targets: [0, 6] },
                    { width: '5%', targets: 0 },
                    { width: '25%', targets: 1 },
                    { width: '15%', targets: 2 },
                    { width: '15%', targets: 3 },
                    { width: '15%', targets: 4 },
                    { width: '10%', targets: 5 },
                    { width: '15%', targets: 6 }
                ],
                language: {
                    emptyTable: "No saved profiles found. Generate your first load profile above."
                },
                searching: true,
                paging: true,
                info: true,
                autoWidth: false,
                responsive: true
            });
            
            console.log('DataTable initialized successfully');
        } catch (error) {
            console.error('Error initializing DataTable:', error);
            this.datatable = null;
        }
    }

    async loadSavedProfiles() {
        // Wait for DataTable to be ready
        let retries = 0;
        while (!this.datatable && retries < 10) {
            await new Promise(resolve => setTimeout(resolve, 100));
            retries++;
        }
        
        if (!this.datatable) {
            console.warn('DataTable not initialized after retries, attempting to initialize');
            this.initializeDataTable();
            if (!this.datatable) {
                console.error('Failed to initialize DataTable');
                return;
            }
        }
        
        try {
            const response = await fetch(`${this.API_BASE}/saved_profiles`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
            }
            const result = await response.json();
            if (result.status === 'success') {
                this.updateSavedProfilesTable(result.data.profiles);
            } else {
                throw new Error(result.message || 'Failed to load profiles');
            }
        } catch (error) {
            console.error('Error loading saved profiles:', error);
            this.showAlert('danger', `Failed to load profiles: ${error.message}`);
        }
    }

    updateSavedProfilesTable(profiles) {
        if (!this.datatable) return;

        // Clear existing data
        this.datatable.clear();

        // Add new data
        profiles.forEach(profile => {
            const isCustom = profile.profile_id &&
                !profile.profile_id.match(/^(base_profile_scaling|stl_decomposition)_\d{8}_\d{6}$/);

            const methodBadge = profile.method === 'base_profile_scaling' ?
                '<span class="badge bg-primary">Base Profile</span>' :
                '<span class="badge bg-success">STL</span>';

            const customBadge = isCustom ? '<span class="badge bg-info ms-1">Custom</span>' : '';

            const rowData = [
                `<input type="checkbox" class="profile-checkbox" value="${profile.profile_id}">`,
                `<strong>${profile.profile_id}</strong>${customBadge}<br>
                 <small class="text-muted">${profile.method || 'Unknown'}</small>`,
                methodBadge,
                profile.generated_at ? new Date(profile.generated_at).toLocaleDateString() : 'Unknown',
                `${profile.start_fy || 'N/A'} - ${profile.end_fy || 'N/A'}`,
                `${(profile.file_info?.size_mb || 0).toFixed(1)} MB`,
                `<div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="loadProfileGenerator.viewProfile('${profile.profile_id}')" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="loadProfileGenerator.downloadProfile('${profile.profile_id}')" title="Download">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="loadProfileGenerator.deleteProfile('${profile.profile_id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>`
            ];

            this.datatable.row.add(rowData);
        });

        // Draw the table
        this.datatable.draw();

        // Update checkbox listeners
        this.updateProfileCheckboxListeners();
    }

    updateProfileCheckboxListeners() {
        document.querySelectorAll('.profile-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const profileId = e.target.value;
                if (e.target.checked) {
                    this.state.selectedProfiles.push(profileId);
                } else {
                    this.state.selectedProfiles = this.state.selectedProfiles.filter(id => id !== profileId);
                }

                // Update compare button state
                const compareBtn = document.getElementById('compareProfiles');
                if (compareBtn) {
                    compareBtn.disabled = this.state.selectedProfiles.length < 2;
                }
            });
        });
    }

    toggleAllProfiles(checked) {
        document.querySelectorAll('.profile-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
            checkbox.dispatchEvent(new Event('change'));
        });
    }

    async viewProfile(profileId) {
        try {
            this.showLoading(true);

            const response = await fetch(`${this.API_BASE}/profile_data/${profileId}`);
            const result = await response.json();

            if (result.status === 'success') {
                // For now, redirect to analysis page
                window.location.href = `/load_profile_analysis/?profile=${encodeURIComponent(profileId)}`;
            }
        } catch (error) {
            console.error('Error viewing profile:', error);
            this.showAlert('danger', 'Failed to load profile');
        } finally {
            this.showLoading(false);
        }
    }

    async downloadProfile(profileId) {
        try {
            window.location.href = `${this.API_BASE}/download_profile/${profileId}`;
            this.showAlert('success', 'Download started');
        } catch (error) {
            console.error('Error downloading profile:', error);
            this.showAlert('danger', 'Download failed');
        }
    }

    async deleteProfile(profileId) {
        if (!confirm(`Are you sure you want to delete profile "${profileId}"?`)) {
            return;
        }

        try {
            const response = await fetch(`${this.API_BASE}/delete_profile/${profileId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.showAlert('success', `Profile "${profileId}" deleted successfully`);
                this.loadSavedProfiles();
            } else {
                throw new Error(result.message || 'Failed to delete profile');
            }
        } catch (error) {
            console.error('Error deleting profile:', error);
            this.showAlert('danger', `Failed to delete profile: ${error.message}`);
        }
    }

    async compareSelectedProfiles() {
        if (this.state.selectedProfiles.length < 2) {
            this.showAlert('warning', 'Please select at least 2 profiles to compare');
            return;
        }

        if (this.state.selectedProfiles.length > 4) {
            this.showAlert('warning', 'Maximum 4 profiles can be compared at once');
            return;
        }

        try {
            this.showLoading(true);

            const response = await fetch(`${this.API_BASE}/compare_profiles`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile_ids: this.state.selectedProfiles })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.displayProfileComparison(result.data);
            }
        } catch (error) {
            console.error('Error comparing profiles:', error);
            this.showAlert('danger', 'Failed to compare profiles');
        } finally {
            this.showLoading(false);
        }
    }

    displayProfileComparison(comparisonData) {
        const modalElement = document.getElementById('profileComparisonModal');
        if (!modalElement) return;

        const modal = new bootstrap.Modal(modalElement);
        const content = document.getElementById('profileComparisonContent');

        if (content) {
            content.innerHTML = `
                <div class="row">
                    <div class="col-12">
                        <h6>Profile Comparison Chart</h6>
                        <canvas id="comparisonChart" height="300"></canvas>
                    </div>
                </div>
                
                <div class="row mt-4">
                    <div class="col-12">
                        <h6>Comparison Statistics</h6>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Profile</th>
                                        <th>Peak (kW)</th>
                                        <th>Average (kW)</th>
                                        <th>Load Factor</th>
                                        <th>Method</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${comparisonData.profiles?.map(profile => `
                                        <tr>
                                            <td>${profile.profile_id}</td>
                                            <td>${profile.peak_demand?.toFixed(1) || 'N/A'}</td>
                                            <td>${profile.avg_demand?.toFixed(1) || 'N/A'}</td>
                                            <td>${((profile.load_factor || 0) * 100).toFixed(1)}%</td>
                                            <td>${profile.method || 'Unknown'}</td>
                                        </tr>
                                    `).join('') || ''}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
        }

        modal.show();

        // Create comparison chart
        setTimeout(() => {
            this.createComparisonChart(comparisonData);
        }, 300);
    }

    createComparisonChart(comparisonData) {
        const ctx = document.getElementById('comparisonChart')?.getContext('2d');
        if (!ctx || typeof Chart === 'undefined') return;

        const datasets = (comparisonData.profiles || []).map((profile, index) => {
            const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444'];
            return {
                label: profile.profile_id,
                data: profile.sample_data || [],
                borderColor: colors[index % colors.length],
                backgroundColor: 'transparent',
                tension: 0.2,
                pointRadius: 0
            };
        });

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({ length: 24 * 7 }, (_, i) => i), // One week
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Load Profile Comparison (First Week)'
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Hours' }
                    },
                    y: {
                        title: { display: true, text: 'Demand (kW)' }
                    }
                }
            }
        });
    }

    showAlert(type, message, duration = 5000) {
        const alert = document.getElementById('statusAlert');
        const messageEl = document.getElementById('statusMessage');

        if (!alert || !messageEl) return;

        // Remove all alert type classes
        alert.className = 'alert alert-dismissible fade show';

        // Add specific type class
        alert.classList.add(`alert-${type}`);

        // Set message
        messageEl.textContent = message;

        // Show alert
        alert.classList.remove('d-none');

        // Auto-hide after duration
        if (duration > 0) {
            setTimeout(() => {
                alert.classList.add('d-none');
            }, duration);
        }
    }

    showLoading(show) {
        if (show) {
            // Create loading overlay if it doesn't exist
            if (!document.getElementById('loadingOverlay')) {
                const overlay = document.createElement('div');
                overlay.id = 'loadingOverlay';
                overlay.className = 'loading-overlay';
                overlay.innerHTML = '<div class="loading-spinner"></div>';
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    z-index: 9999;
                `;
                document.body.appendChild(overlay);
            }
            document.getElementById('loadingOverlay').style.display = 'flex';
        } else {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {
                overlay.style.display = 'none';
            }
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');
    console.log('jQuery available:', typeof window.jQuery !== 'undefined');
    console.log('DataTables available:', typeof $.fn?.DataTable !== 'undefined');
    
    // Ensure jQuery and DataTables are loaded before starting the app
    if (window.jQuery && $.fn.DataTable) {
        console.log('All libraries loaded, initializing LoadProfileGenerator');
        window.loadProfileGenerator = new LoadProfileGenerator();
    } else {
        console.warn('Libraries not ready, waiting...');
        // Fallback: If libraries are slow to load, wait and try again
        let attempts = 0;
        const maxAttempts = 20; // Wait up to 2 seconds
        
        const checkLibraries = () => {
            attempts++;
            console.log(`Checking libraries attempt ${attempts}/${maxAttempts}`);
            
            if (window.jQuery && $.fn.DataTable) {
                console.log('Libraries now available, initializing LoadProfileGenerator');
                window.loadProfileGenerator = new LoadProfileGenerator();
            } else if (attempts < maxAttempts) {
                setTimeout(checkLibraries, 100);
            } else {
                console.error("Fatal Error: Required libraries (jQuery or DataTables) failed to load after waiting.");
                alert("Required components failed to load. Please refresh the page and check your internet connection.");
            }
        };
        
        setTimeout(checkLibraries, 100);
    }
});