// static/js/load_profile_analysis.js
/**
 *Load Profile Analysis Frontend Controller
 * Handles visualization, comparison, and analysis of load profiles
 * All calculations done server-side with comprehensive error handling
 */

document.addEventListener('DOMContentLoaded', function () {


    const state = {
        currentProfile: null,
        selectedProfiles: new Set(),
        unit: 'kW',
        filters: { year: null, season: 'all', dayType: 'all' },
        charts: { main: null, comparison: null },
        dataTable: null
    };
    // Check if a profile was selected for analysis
    const selectedProfile = localStorage.getItem('selectedProfileForAnalysis');
    if (selectedProfile) {
        // Auto-select the profile
        selectSingleProfile(selectedProfile);

        // Clear the stored selection
        localStorage.removeItem('selectedProfileForAnalysis');

        // Show success message
        showAlert('info', `Auto-selected profile: ${selectedProfile}`, 3000);
    }
    console.log('Load Profile Analysis: InitializingSystem');

    // Application State Management
    const AppState = {
        selectedProfiles: new Set(),
        currentProfile: null,
        currentAnalysisType: 'overview',
        currentUnit: 'kWh',
        currentFilters: {
            year: null,
            season: 'all',
            dayType: 'all'
        },
        loadedData: new Map(),
        charts: {
            main: null,
            comparison: null
        },
        dataTable: null,
        isLoading: false,
        cache: new Map() // Cache for API responses
    };

    // API Configuration
    const API_CONFIG = {
        base: '/load_profile_analysis/api',
        timeout: 30000,
        retryAttempts: 3,
        retryDelay: 1000
    };

    // Analysis Type Descriptions
    const ANALYSIS_DESCRIPTIONS = {
        'overview': 'Complete time series view showing demand patterns over the entire analysis period with peak and minimum points highlighted.',
        'peak_analysis': 'Comparison between the highest and lowest demand days to understand extreme load variations.',
        'weekday_weekend': 'Analysis of demand patterns between weekdays and weekends to identify usage behavior differences.',
        'seasonal': 'Seasonal load variations analysis showing consumption patterns across Summer, Monsoon, and Winter seasons.',
        'monthly': 'Monthly load patterns and trends analysis to identify seasonal peaks and variations throughout the year.',
        'duration_curve': 'Load duration curve showing the distribution of demand levels and system utilization efficiency.',
        'heatmap': 'Weekly load pattern visualization showing demand intensity across different days of the week and hours.'
    };

    // Initialize Application
    initialize();

    function initialize() {
        try {
            setupEventListeners();
            initializeCharts();
            updateProfileCount();
            setupAnalysisTypeDescriptions();

            // Load cached data if available
            loadCachedState();

            console.log('Load Profile Analysis initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Load Profile Analysis:', error);
            showAlert('danger', 'Failed to initialize application. Please refresh the page.');
        }
    }

    function setupEventListeners() {
        // Profile selection events
        document.querySelectorAll('.profile-item').forEach(item => {
            // Single click for selection
            item.addEventListener('click', function (e) {
                e.preventDefault();
                if (e.ctrlKey || e.metaKey) {
                    toggleProfileSelection(this.dataset.profileId);
                } else {
                    selectSingleProfile(this.dataset.profileId);
                }
            });

            // Double-click for details
            item.addEventListener('dblclick', function (e) {
                e.preventDefault();
                viewProfileDetails(this.dataset.profileId);
            });

            // Hover effects
            item.addEventListener('mouseenter', function () {
                if (!this.classList.contains('selected')) {
                    this.style.transform = 'translateX(3px)';
                }
            });

            item.addEventListener('mouseleave', function () {
                if (!this.classList.contains('selected')) {
                    this.style.transform = 'translateX(0)';
                }
            });
        });

        // Analysis controls
        document.getElementById('updateAnalysis')?.addEventListener('click', debounce(updateAnalysis, 300));

        document.getElementById('analysisType')?.addEventListener('change', function () {
            AppState.currentAnalysisType = this.value;
            updateAnalysisDescription();
            if (AppState.currentProfile) {
                updateAnalysis();
            }
        });

        // Filter controls with debouncing
        document.getElementById('unitFilter')?.addEventListener('change', debounce(function () {
            AppState.currentUnit = this.value;
            updateAnalysis();
        }, 300));

        document.getElementById('yearFilter')?.addEventListener('change', debounce(function () {
            AppState.currentFilters.year = this.value || null;
            updateAnalysis();
        }, 300));

        document.getElementById('seasonFilter')?.addEventListener('change', debounce(function () {
            AppState.currentFilters.season = this.value;
            updateAnalysis();
        }, 300));

        document.getElementById('dayTypeFilter')?.addEventListener('change', debounce(function () {
            AppState.currentFilters.dayType = this.value;
            updateAnalysis();
        }, 300));

        // Comparison controls
        document.getElementById('compareButton')?.addEventListener('click', function () {
            if (AppState.selectedProfiles.size >= 2) {
                showComparisonModal();
            }
        });

        document.getElementById('clearSelection')?.addEventListener('click', clearProfileSelection);
        document.getElementById('validateSelected')?.addEventListener('click', validateSelectedProfiles);

        // Keyboard shortcuts
        document.addEventListener('keydown', function (e) {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'a':
                        e.preventDefault();
                        selectAllProfiles();
                        break;
                    case 'e':
                        e.preventDefault();
                        if (AppState.currentProfile) {
                            exportAnalysis('excel');
                        }
                        break;
                    case 'r':
                        e.preventDefault();
                        refreshAnalysis();
                        break;
                }
            }

            if (e.key === 'Escape') {
                clearProfileSelection();
            }
        });

        // Window resize handler with debouncing
        window.addEventListener('resize', debounce(function () {
            Object.values(AppState.charts).forEach(chart => {
                if (chart) {
                    chart.resize();
                }
            });
        }, 250));

        // Prevent context menu on profile items for better UX
        document.querySelectorAll('.profile-item').forEach(item => {
            item.addEventListener('contextmenu', e => e.preventDefault());
        });
    }

    function setupAnalysisTypeDescriptions() {
        const analysisSelect = document.getElementById('analysisType');
        if (analysisSelect) {
            analysisSelect.addEventListener('change', updateAnalysisDescription);
            updateAnalysisDescription(); // Set initial description
        }
    }

    function updateAnalysisDescription() {
        const analysisType = document.getElementById('analysisType')?.value;
        const descriptionContainer = document.getElementById('analysisDescription');
        const descriptionText = document.getElementById('analysisDescriptionText');

        if (analysisType && descriptionContainer && descriptionText) {
            const description = ANALYSIS_DESCRIPTIONS[analysisType];
            if (description) {
                descriptionText.textContent = description;
                descriptionContainer.classList.remove('d-none');
            } else {
                descriptionContainer.classList.add('d-none');
            }
        }
    }

    function initializeCharts() {
        try {
            const mainChartElement = document.getElementById('mainChart');
            const comparisonChartElement = document.getElementById('comparisonChart');

            if (mainChartElement) {
                AppState.charts.main = echarts.init(mainChartElement);
                AppState.charts.main.on('click', handleChartClick);
                AppState.charts.main.on('datazoom', handleChartZoom);
            }

            if (comparisonChartElement) {
                AppState.charts.comparison = echarts.init(comparisonChartElement);
            }

            console.log('Charts initialized successfully');
        } catch (error) {
            console.error('Failed to initialize charts:', error);
            showAlert('warning', 'Chart initialization failed. Some visualizations may not work properly.');
        }
    }

    function handleChartClick(params) {
        if (params.componentType === 'series') {
            const info = `Value: ${params.value} at ${params.name}`;
            showAlert('info', info, 3000);
        }
    }

    function handleChartZoom(params) {
        console.log('Chart zoom changed:', params);
        // Can implement custom zoom handling here
    }

    // Profile Selection Functions
    function selectSingleProfile(profileId) {
        if (!profileId) return;

        try {
            // Clear previous selections
            clearProfileSelection();

            // Select new profile
            AppState.selectedProfiles.add(profileId);
            AppState.currentProfile = profileId;

            // Update UI
            updateProfileSelectionUI();
            showAnalysisControls();

            // Load profile data
            loadProfileData(profileId);

            // Save state
            saveState();
        } catch (error) {
            console.error('Error selecting profile:', error);
            showAlert('danger', 'Failed to select profile');
        }
    }

    function toggleProfileSelection(profileId) {
        if (!profileId) return;

        try {
            if (AppState.selectedProfiles.has(profileId)) {
                AppState.selectedProfiles.delete(profileId);
            } else {
                if (AppState.selectedProfiles.size >= 5) {
                    showAlert('warning', 'Maximum 5 profiles can be selected for comparison');
                    return;
                }
                AppState.selectedProfiles.add(profileId);
            }

            updateProfileSelectionUI();

            // Update current profile if needed
            if (AppState.selectedProfiles.size === 1) {
                AppState.currentProfile = Array.from(AppState.selectedProfiles)[0];
                showAnalysisControls();
                loadProfileData(AppState.currentProfile);
            } else if (AppState.selectedProfiles.size === 0) {
                hideAnalysisControls();
                AppState.currentProfile = null;
            }

            saveState();
        } catch (error) {
            console.error('Error toggling profile selection:', error);
            showAlert('danger', 'Failed to update selection');
        }
    }

    function clearProfileSelection() {
        AppState.selectedProfiles.clear();
        AppState.currentProfile = null;
        updateProfileSelectionUI();
        hideAnalysisControls();
        saveState();
    }

    function selectAllProfiles() {
        const profileItems = document.querySelectorAll('.profile-item');
        const profileIds = Array.from(profileItems).map(item => item.dataset.profileId);

        if (profileIds.length > 5) {
            showAlert('warning', 'Cannot select more than 5 profiles. Selecting first 5.');
            profileIds.splice(5);
        }

        AppState.selectedProfiles.clear();
        profileIds.forEach(id => AppState.selectedProfiles.add(id));

        if (AppState.selectedProfiles.size > 0) {
            AppState.currentProfile = profileIds[0];
            showAnalysisControls();
            loadProfileData(AppState.currentProfile);
        }

        updateProfileSelectionUI();
        saveState();
    }

    function updateProfileSelectionUI() {
        // Update profile item styles
        document.querySelectorAll('.profile-item').forEach(item => {
            const profileId = item.dataset.profileId;
            if (AppState.selectedProfiles.has(profileId)) {
                item.classList.add('selected');
                item.style.transform = 'translateX(5px)';
            } else {
                item.classList.remove('selected');
                item.style.transform = 'translateX(0)';
            }
        });

        // Update selected profiles display
        const selectedContainer = document.getElementById('selectedProfiles');
        if (selectedContainer) {
            if (AppState.selectedProfiles.size === 0) {
                selectedContainer.innerHTML = '<small class="text-muted">Select profiles to compare (max 5)</small>';
            } else {
                const profileBadges = Array.from(AppState.selectedProfiles).map(id =>
                    `<span class="badge bg-primary me-1 mb-1">${id}</span>`
                ).join('');
                selectedContainer.innerHTML = `
                    <div class="small text-muted mb-2">Selected (${AppState.selectedProfiles.size}/5):</div>
                    <div>${profileBadges}</div>
                `;
            }
        }

        // Update button states
        const compareButton = document.getElementById('compareButton');
        const validateButton = document.getElementById('validateSelected');

        if (compareButton) {
            compareButton.disabled = AppState.selectedProfiles.size < 2;
        }

        if (validateButton) {
            validateButton.disabled = AppState.selectedProfiles.size === 0;
        }
    }

    // UI State Management
    function showAnalysisControls() {
        const elements = [
            'analysisControls',
            'metricsRow',
            'chartContainer',
            'exportSection',
            'dataTableContainer'
        ];

        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = element.id === 'metricsRow' ? 'flex' : 'block';
                element.classList.add('fade-in');
            }
        });
    }

    function hideAnalysisControls() {
        const elements = [
            'analysisControls',
            'metricsRow',
            'chartContainer',
            'insightsSection',
            'exportSection',
            'dataTableContainer',
            'comparisonResults'
        ];

        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
                element.classList.remove('fade-in');
            }
        });
    }

    // Data Loading Functions
    async function loadProfileData(profileId) {
        if (!profileId) return;

        const cacheKey = `profile_${profileId}_${JSON.stringify(AppState.currentFilters)}_${AppState.currentUnit}`;

        // Check cache first
        if (AppState.cache.has(cacheKey)) {
            const cachedData = AppState.cache.get(cacheKey);
            processProfileData(profileId, cachedData);
            return;
        }

        try {
            showLoading(true);

            const params = new URLSearchParams({
                unit: AppState.currentUnit,
                season: AppState.currentFilters.season || 'all'
            });

            if (AppState.currentFilters.year) {
                params.append('year', AppState.currentFilters.year);
            }

            if (AppState.currentFilters.dayType && AppState.currentFilters.dayType !== 'all') {
                params.append('day_type', AppState.currentFilters.dayType);
            }

            console.log(`Loading profile data: ${profileId}, params: ${params.toString()}`);

            const response = await fetchWithRetry(`${API_CONFIG.base}/profile_data/${profileId}?${params}`);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
                throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            if (result.status === 'success') {
                // Cache the result
                AppState.cache.set(cacheKey, result.data);
                AppState.loadedData.set(profileId, result.data);

                processProfileData(profileId, result.data);

                // Load available years for this profile
                await loadProfileYears(profileId);

            } else {
                throw new Error(result.message || 'Failed to load profile data');
            }
        } catch (error) {
            console.error('Error loading profile data:', error);

            // Provide specific error messages based on error type
            let errorMessage = 'Failed to load profile data';

            if (error.message.includes('Profile not found')) {
                errorMessage = `Profile "${profileId}" not found. The profile file may have been deleted or moved.`;
            } else if (error.message.includes('No demand column found')) {
                errorMessage = `Profile "${profileId}" has invalid data format. No demand/load column was found in the CSV file.`;
            } else if (error.message.includes('Data validation error')) {
                errorMessage = `Profile "${profileId}" has data validation issues: ${error.message}`;
            } else if (error.message.includes('No data available')) {
                errorMessage = `Profile "${profileId}" contains no valid data after applying filters.`;
            } else {
                errorMessage = `Error loading profile "${profileId}": ${error.message}`;
            }

            showAlert('danger', errorMessage, 8000);

            // Clear selection if loading failed
            clearProfileSelection();
        } finally {
            showLoading(false);
        }
    }
    function processProfileData(profileId, data) {
        try {
            // Update metrics
            updateMetricsDisplay(data.statistics);

            // Update analysis
            updateCurrentAnalysis();

            // Show insights
            showInsights(data.statistics);

            // Update chart info
            updateChartInfo(data.metadata);

        } catch (error) {
            console.error('Error processing profile data:', error);
            showAlert('warning', 'Some data processing failed. Results may be incomplete.');
        }
    }

    async function loadProfileYears(profileId) {
        try {
            const response = await fetchWithRetry(`${API_CONFIG.base}/fiscal_years/${profileId}`);
            const result = await response.json();

            if (result.status === 'success') {
                updateYearFilter(result.data.fiscal_years);
            }
        } catch (error) {
            console.warn('Failed to load profile years:', error);
        }
    }

    function updateYearFilter(fiscalYears) {
        const yearFilter = document.getElementById('yearFilter');
        if (!yearFilter) return;

        yearFilter.innerHTML = '<option value="">All Years</option>';

        fiscalYears.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = `FY ${year}`;
            yearFilter.appendChild(option);
        });
    }

    // Metrics Display
    function updateMetricsDisplay(statistics) {
        if (!statistics || !statistics.basic) return;

        const basic = statistics.basic;
        const temporal = statistics.temporal || {};

        // Update metric values with animation
        updateMetricWithAnimation('peakDemand', `${basic.peak_load?.toFixed(1) || '--'} ${basic.unit}`);
        updateMetricWithAnimation('peakTime', temporal.peak_datetime ?
            new Date(temporal.peak_datetime).toLocaleString() : '--');

        updateMetricWithAnimation('avgDemand', `${basic.average_load?.toFixed(1) || '--'} ${basic.unit}`);
        updateMetricWithAnimation('demandStd', `σ: ${basic.std_dev?.toFixed(1) || '--'} ${basic.unit}`);

        updateMetricWithAnimation('totalEnergy', `${formatLargeNumber(basic.total_energy)} ${basic.unit}h`);
        updateMetricWithAnimation('energyPeriod',
            temporal.duration_days ? `${temporal.duration_days} days` : '--');

        // Update load factor with status
        const loadFactor = basic.load_factor || 0;
        updateMetricWithAnimation('loadFactorValue', `${loadFactor.toFixed(1)}%`);

        let loadFactorStatus = '';
        if (loadFactor > 80) {
            loadFactorStatus = 'Excellent';
        } else if (loadFactor > 60) {
            loadFactorStatus = 'Good';
        } else if (loadFactor > 40) {
            loadFactorStatus = 'Fair';
        } else {
            loadFactorStatus = 'Poor';
        }
        updateMetricWithAnimation('loadFactorStatus', loadFactorStatus);
    }

    function updateMetricWithAnimation(elementId, value) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.style.transition = 'opacity 0.3s ease';
        element.style.opacity = '0.5';

        setTimeout(() => {
            element.textContent = value;
            element.style.opacity = '1';
        }, 150);
    }

    function formatLargeNumber(num) {
        if (!num) return '--';

        if (num >= 1e9) {
            return (num / 1e9).toFixed(1) + 'B';
        } else if (num >= 1e6) {
            return (num / 1e6).toFixed(1) + 'M';
        } else if (num >= 1e3) {
            return (num / 1e3).toFixed(1) + 'K';
        }
        return num.toFixed(0);
    }

    // Analysis Functions
    async function updateAnalysis() {
        if (!AppState.currentProfile) return;

        try {
            showLoading(true);

            // Reload profile data with current filters
            await loadProfileData(AppState.currentProfile);

        } catch (error) {
            console.error('Error updating analysis:', error);
            showAlert('danger', `Failed to update analysis: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    async function updateCurrentAnalysis() {
        if (!AppState.currentProfile) return;

        const cacheKey = `analysis_${AppState.currentProfile}_${AppState.currentAnalysisType}_${JSON.stringify(AppState.currentFilters)}_${AppState.currentUnit}`;

        // Check cache first
        if (AppState.cache.has(cacheKey)) {
            const cachedData = AppState.cache.get(cacheKey);
            renderAnalysisChart(cachedData);
            updateDataTable(cachedData);
            return;
        }

        try {
            const params = new URLSearchParams({
                unit: AppState.currentUnit,
                season: AppState.currentFilters.season
            });

            if (AppState.currentFilters.year) {
                params.append('year', AppState.currentFilters.year);
            }

            if (AppState.currentFilters.dayType !== 'all') {
                params.append('day_type', AppState.currentFilters.dayType);
            }

            const response = await fetchWithRetry(
                `${API_CONFIG.base}/profile_analysis/${AppState.currentProfile}/${AppState.currentAnalysisType}?${params}`
            );
            const result = await response.json();

            if (result.status === 'success') {
                // Cache the result
                AppState.cache.set(cacheKey, result.data);

                renderAnalysisChart(result.data);
                updateDataTable(result.data);
            } else {
                showAlert('warning', `Analysis failed: ${result.message}`);
            }
        } catch (error) {
            console.error('Error generating analysis:', error);
            showAlert('danger', `Error generating analysis: ${error.message}`);
        }
    }

    function refreshAnalysis() {
        // Clear cache for current profile
        const keysToDelete = Array.from(AppState.cache.keys()).filter(key =>
            key.includes(AppState.currentProfile)
        );
        keysToDelete.forEach(key => AppState.cache.delete(key));

        // Reload analysis
        updateAnalysis();
    }

    // Chart Rendering
    function renderAnalysisChart(analysisData) {
        if (!AppState.charts.main || !analysisData) return;

        const { chart_type, title, data, unit } = analysisData;

        // Update chart title and info
        const chartTitle = document.getElementById('chartTitle');
        const chartInfo = document.getElementById('chartInfo');

        if (chartTitle) {
            chartTitle.textContent = title;
        }

        if (chartInfo && analysisData.metadata) {
            chartInfo.innerHTML = `
                <i class="fas fa-info-circle me-1"></i>
                ${analysisData.metadata.data_points} data points | 
                Unit: ${unit} | 
                Generated: ${new Date().toLocaleTimeString()}
            `;
        }

        let option = {};

        try {
            switch (chart_type) {
                case 'line':
                    option = createLineChartOption(data, title, unit);
                    break;
                case 'line_comparison':
                    option = createLineComparisonOption(data, title, unit);
                    break;
                case 'bar_line_combo':
                    option = createBarLineComboOption(data, title, unit);
                    break;
                case 'heatmap':
                    option = createHeatmapOption(data, title, analysisData, unit);
                    break;
                case 'line_with_markers':
                    option = createDurationCurveOption(data, title, unit);
                    break;
                default:
                    console.warn('Unknown chart type:', chart_type);
                    return;
            }

            AppState.charts.main.setOption(option, true);

            // Show chart container
            document.getElementById('chartContainer').style.display = 'block';

        } catch (error) {
            console.error('Error rendering chart:', error);
            showAlert('warning', 'Chart rendering failed. Data is still available in the table.');
        }
    }

    function createLineChartOption(data, title, unit) {
        return {
            title: {
                text: title,
                left: 'center',
                textStyle: {
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#ccc',
                borderWidth: 1,
                textStyle: {
                    color: '#333'
                },
                formatter: function (params) {
                    if (!params || !params[0]) return '';
                    const time = params[0].axisValue;
                    const value = params[0].value;
                    return `
                        <div style="font-weight: bold;">${time}</div>
                        <div>Demand: <span style="color: #667eea;">${value.toFixed(2)} ${unit}</span></div>
                    `;
                }
            },
            legend: {
                data: ['Load Profile'],
                top: 30
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.timestamps || data.hours || [],
                axisLabel: {
                    rotate: data.timestamps ? 45 : 0,
                    fontSize: 10
                },
                name: data.timestamps ? 'Time' : 'Hour',
                nameLocation: 'middle',
                nameGap: 30
            },
            yAxis: {
                type: 'value',
                name: `Demand (${unit})`,
                nameLocation: 'middle',
                nameGap: 60,
                nameTextStyle: {
                    fontWeight: 'bold'
                }
            },
            series: [{
                name: 'Load Profile',
                type: 'line',
                data: data.demand || data.values || [],
                smooth: true,
                symbol: 'none',
                lineStyle: {
                    width: 2,
                    color: '#667eea'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
                        { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
                    ])
                },
                markPoint: {
                    data: data.peak_point && data.min_point ? [
                        {
                            name: 'Peak',
                            coord: [data.peak_point.index, data.peak_point.demand],
                            value: data.peak_point.demand,
                            itemStyle: { color: '#ff4757' }
                        },
                        {
                            name: 'Minimum',
                            coord: [data.min_point.index, data.min_point.demand],
                            value: data.min_point.demand,
                            itemStyle: { color: '#2ed573' }
                        }
                    ] : []
                },
                emphasis: {
                    focus: 'series'
                }
            }],
            dataZoom: [
                {
                    type: 'slider',
                    start: 0,
                    end: 100,
                    bottom: 10
                },
                {
                    type: 'inside',
                    start: 0,
                    end: 100
                }
            ],
            toolbox: {
                feature: {
                    saveAsImage: {
                        title: 'Save as Image'
                    },
                    restore: {
                        title: 'Restore'
                    }
                }
            }
        };
    }

    function createLineComparisonOption(data, title, unit) {
        const series = [];
        const colors = ['#667eea', '#f5576c', '#4facfe', '#7b68ee'];
        let colorIndex = 0;

        if (data.peak_day) {
            series.push({
                name: `Peak Day (${data.peak_date})`,
                type: 'line',
                data: data.peak_day,
                smooth: true,
                lineStyle: { color: colors[colorIndex++], width: 2 },
                symbol: 'circle',
                symbolSize: 4
            });
        }

        if (data.off_peak_day) {
            series.push({
                name: `Off-Peak Day (${data.off_peak_date})`,
                type: 'line',
                data: data.off_peak_day,
                smooth: true,
                lineStyle: { color: colors[colorIndex++], width: 2 },
                symbol: 'circle',
                symbolSize: 4
            });
        }

        if (data.weekday) {
            series.push({
                name: 'Weekdays',
                type: 'line',
                data: data.weekday,
                smooth: true,
                lineStyle: { color: colors[colorIndex++], width: 2 },
                symbol: 'circle',
                symbolSize: 4
            });
        }

        if (data.weekend) {
            series.push({
                name: 'Weekends',
                type: 'line',
                data: data.weekend,
                smooth: true,
                lineStyle: { color: colors[colorIndex++], width: 2, type: 'dashed' },
                symbol: 'circle',
                symbolSize: 4
            });
        }

        return {
            title: {
                text: title,
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'bold' }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#ccc',
                borderWidth: 1
            },
            legend: {
                data: series.map(s => s.name),
                top: 30,
                type: 'scroll'
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.hours || Array.from({ length: 24 }, (_, i) => `${i}:00`),
                name: 'Hour of Day',
                nameLocation: 'middle',
                nameGap: 30
            },
            yAxis: {
                type: 'value',
                name: `Demand (${unit})`,
                nameLocation: 'middle',
                nameGap: 60
            },
            series: series,
            dataZoom: [
                {
                    type: 'slider',
                    start: 0,
                    end: 100,
                    bottom: 10
                }
            ]
        };
    }

    function createBarLineComboOption(data, title, unit) {
        return {
            title: {
                text: title,
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'bold' }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)'
            },
            legend: {
                data: ['Average', 'Maximum', 'Minimum'],
                top: 30
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.seasons || data.months || []
            },
            yAxis: {
                type: 'value',
                name: `Demand (${unit})`,
                nameLocation: 'middle',
                nameGap: 60
            },
            series: [
                {
                    name: 'Average',
                    type: 'bar',
                    data: data.average || [],
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#667eea' },
                            { offset: 1, color: '#764ba2' }
                        ])
                    },
                    barWidth: '60%'
                },
                {
                    name: 'Maximum',
                    type: 'line',
                    data: data.maximum || [],
                    lineStyle: { color: '#ff4757', width: 3 },
                    symbol: 'circle',
                    symbolSize: 8
                },
                {
                    name: 'Minimum',
                    type: 'line',
                    data: data.minimum || [],
                    lineStyle: { color: '#2ed573', width: 3 },
                    symbol: 'circle',
                    symbolSize: 8
                }
            ]
        };
    }

    function createHeatmapOption(data, title, analysisData, unit) {
        return {
            title: {
                text: title,
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'bold' }
            },
            tooltip: {
                position: 'top',
                formatter: function (params) {
                    if (!params.data) return '';
                    const hour = params.data[0];
                    const day = analysisData.axis_labels.y[params.data[1]];
                    const value = params.data[2];
                    return `
                        <div style="font-weight: bold;">${day}, ${hour}:00</div>
                        <div>Load: <span style="color: #667eea;">${value.toFixed(2)} ${unit}</span></div>
                    `;
                }
            },
            grid: {
                height: '70%',
                top: '15%',
                bottom: '15%'
            },
            xAxis: {
                type: 'category',
                data: analysisData.axis_labels.x,
                splitArea: { show: true },
                name: 'Hour of Day',
                nameLocation: 'middle',
                nameGap: 30
            },
            yAxis: {
                type: 'category',
                data: analysisData.axis_labels.y,
                splitArea: { show: true },
                name: 'Day of Week',
                nameLocation: 'middle',
                nameGap: 50
            },
            visualMap: {
                min: data.min_value,
                max: data.max_value,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: '5%',
                inRange: {
                    color: [
                        '#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8',
                        '#ffffcc', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'
                    ]
                },
                text: ['High', 'Low'],
                textStyle: {
                    color: '#333'
                }
            },
            series: [{
                type: 'heatmap',
                data: data.heatmap_data,
                label: {
                    show: data.heatmap_data && data.heatmap_data.length < 200, // Show labels only for smaller datasets
                    fontSize: 8
                },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };
    }

    function createDurationCurveOption(data, title, unit) {
        const percentiles = data.percentiles || {};

        return {
            title: {
                text: title,
                left: 'center',
                textStyle: { fontSize: 16, fontWeight: 'bold' }
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                formatter: function (params) {
                    if (!params || !params[0]) return '';
                    const hour = params[0].dataIndex + 1;
                    const demand = params[0].value;
                    const percentile = ((hour / data.hours.length) * 100).toFixed(1);
                    return `
                        <div style="font-weight: bold;">Hour: ${hour}</div>
                        <div>Demand: <span style="color: #667eea;">${demand.toFixed(2)} ${unit}</span></div>
                        <div>Percentile: ${percentile}%</div>
                    `;
                }
            },
            grid: {
                left: '10%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.hours,
                name: 'Hours (Ranked by Demand)',
                nameLocation: 'middle',
                nameGap: 30
            },
            yAxis: {
                type: 'value',
                name: `Demand (${unit})`,
                nameLocation: 'middle',
                nameGap: 60
            },
            series: [{
                type: 'line',
                data: data.demands,
                smooth: false,
                symbol: 'none',
                lineStyle: {
                    color: '#667eea',
                    width: 2
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(102, 126, 234, 0.3)' },
                        { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
                    ])
                },
                markLine: {
                    silent: true,
                    lineStyle: {
                        type: 'dashed',
                        width: 2
                    },
                    data: Object.entries(percentiles).map(([key, value]) => ({
                        name: `${key.toUpperCase()}`,
                        yAxis: value,
                        lineStyle: {
                            color: key === 'p10' ? '#ff4757' :
                                key === 'p50' ? '#ffa502' : '#2ed573'
                        }
                    }))
                }
            }],
            dataZoom: [
                {
                    type: 'slider',
                    start: 0,
                    end: 100,
                    bottom: 10
                }
            ]
        };
    }

    // Data Table Functions
    function updateDataTable(analysisData) {
        // Destroy existing DataTable if it exists
        if (AppState.dataTable) {
            AppState.dataTable.destroy();
            AppState.dataTable = null;
        }

        const tableContainer = document.getElementById('dataTable');
        if (!tableContainer) return;

        const thead = tableContainer.querySelector('thead');
        const tbody = tableContainer.querySelector('tbody');

        // Clear existing content
        thead.innerHTML = '';
        tbody.innerHTML = '';

        // Generate table based on analysis type and available data
        let tableData = [];
        let columns = [];

        try {
            if (AppState.currentProfile && AppState.loadedData.has(AppState.currentProfile)) {
                const profileData = AppState.loadedData.get(AppState.currentProfile);

                switch (AppState.currentAnalysisType) {
                    case 'overview':
                        tableData = profileData.data.slice(0, 1000); // Limit for performance
                        columns = [
                            { title: 'DateTime', data: 'ds', className: 'text-nowrap' },
                            { title: `Demand (${AppState.currentUnit})`, data: 'demand', className: 'text-end' },
                            { title: 'Financial Year', data: 'financial_year', className: 'text-center' },
                            { title: 'Hour', data: 'hour', className: 'text-center' }
                        ];
                        break;

                    case 'seasonal':
                        if (profileData.statistics?.seasonal_patterns?.summary) {
                            tableData = Object.entries(profileData.statistics.seasonal_patterns.summary).map(([season, stats]) => ({
                                season: season,
                                average: stats.mean?.toFixed(2) || '--',
                                maximum: stats.max?.toFixed(2) || '--',
                                minimum: stats.min?.toFixed(2) || '--',
                                total: stats.sum?.toFixed(2) || '--',
                                std_dev: stats.std?.toFixed(2) || '--'
                            }));
                            columns = [
                                { title: 'Season', data: 'season' },
                                { title: `Average (${AppState.currentUnit})`, data: 'average', className: 'text-end' },
                                { title: `Maximum (${AppState.currentUnit})`, data: 'maximum', className: 'text-end' },
                                { title: `Minimum (${AppState.currentUnit})`, data: 'minimum', className: 'text-end' },
                                { title: `Total (${AppState.currentUnit}h)`, data: 'total', className: 'text-end' },
                                { title: `Std Dev (${AppState.currentUnit})`, data: 'std_dev', className: 'text-end' }
                            ];
                        }
                        break;

                    case 'monthly':
                        if (profileData.statistics?.monthly_patterns?.summary) {
                            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                            tableData = Object.entries(profileData.statistics.monthly_patterns.summary).map(([month, stats]) => ({
                                month: monthNames[parseInt(month) - 1] || month,
                                average: stats.mean?.toFixed(2) || '--',
                                maximum: stats.max?.toFixed(2) || '--',
                                minimum: stats.min?.toFixed(2) || '--',
                                total: stats.sum?.toFixed(2) || '--',
                                std_dev: stats.std?.toFixed(2) || '--'
                            }));
                            columns = [
                                { title: 'Month', data: 'month' },
                                { title: `Average (${AppState.currentUnit})`, data: 'average', className: 'text-end' },
                                { title: `Maximum (${AppState.currentUnit})`, data: 'maximum', className: 'text-end' },
                                { title: `Minimum (${AppState.currentUnit})`, data: 'minimum', className: 'text-end' },
                                { title: `Total (${AppState.currentUnit}h)`, data: 'total', className: 'text-end' },
                                { title: `Std Dev (${AppState.currentUnit})`, data: 'std_dev', className: 'text-end' }
                            ];
                        }
                        break;

                    default:
                        // Default to showing sample raw data
                        tableData = profileData.data.slice(0, 1000);
                        columns = [
                            { title: 'DateTime', data: 'ds', className: 'text-nowrap' },
                            { title: `Demand (${AppState.currentUnit})`, data: 'demand', className: 'text-end' }
                        ];
                }
            }

            // Initialize DataTable if we have data
            if (tableData.length > 0 && columns.length > 0) {
                // Create header
                const headerRow = document.createElement('tr');
                columns.forEach(col => {
                    const th = document.createElement('th');
                    th.textContent = col.title;
                    th.className = col.className || '';
                    headerRow.appendChild(th);
                });
                thead.appendChild(headerRow);

                AppState.dataTable = new DataTable(tableContainer, {
                    data: tableData,
                    columns: columns,
                    pageLength: 25,
                    responsive: true,
                    dom: 'Bfrtip',
                    buttons: [
                        {
                            extend: 'copy',
                            className: 'btn btn-outline-secondary btn-sm'
                        },
                        {
                            extend: 'csv',
                            className: 'btn btn-outline-success btn-sm'
                        },
                        {
                            extend: 'excel',
                            className: 'btn btn-outline-primary btn-sm'
                        }
                    ],
                    order: [[0, 'asc']],
                    language: {
                        search: 'Filter:',
                        lengthMenu: 'Show _MENU_ entries',
                        info: 'Showing _START_ to _END_ of _TOTAL_ entries',
                        paginate: {
                            first: 'First',
                            last: 'Last',
                            next: 'Next',
                            previous: 'Previous'
                        }
                    }
                });

                // Show the table container
                document.getElementById('dataTableContainer').style.display = 'block';
            } else {
                // Hide table if no data
                document.getElementById('dataTableContainer').style.display = 'none';
            }

        } catch (error) {
            console.error('Error updating data table:', error);
            document.getElementById('dataTableContainer').style.display = 'none';
        }
    }

    // Insights Functions
    function showInsights(statistics) {
        if (!statistics || !statistics.basic) {
            document.getElementById('insightsSection').style.display = 'none';
            return;
        }

        const insights = generateInsights(statistics);
        const insightsList = document.getElementById('insightsList');

        if (insights.length > 0) {
            insightsList.innerHTML = insights.map(insight =>
                `<div class="mb-2"><i class="fas fa-arrow-right me-2"></i>${insight}</div>`
            ).join('');
            document.getElementById('insightsSection').style.display = 'block';
            document.getElementById('insightsSection').classList.add('fade-in');
        } else {
            document.getElementById('insightsSection').style.display = 'none';
        }
    }

    function generateInsights(statistics) {
        const insights = [];
        const basic = statistics.basic;

        if (!basic) return insights;

        // Load factor insights
        const loadFactor = basic.load_factor || 0;
        if (loadFactor > 80) {
            insights.push('Excellent load factor indicates highly efficient system utilization and steady demand patterns.');
        } else if (loadFactor > 60) {
            insights.push('Good load factor shows effective demand management with room for minor improvements.');
        } else if (loadFactor < 40) {
            insights.push('Low load factor suggests significant opportunities for demand optimization and peak shaving strategies.');
        }

        // Peak-to-average ratio insights
        const peakToAvgRatio = basic.peak_to_average_ratio || 0;
        if (peakToAvgRatio > 3) {
            insights.push('High peak-to-average ratio indicates significant demand variability - consider implementing load shifting or energy storage solutions.');
        } else if (peakToAvgRatio < 1.5) {
            insights.push('Low peak-to-average ratio demonstrates stable demand patterns, indicating good load management.');
        }

        // Variability insights
        const cv = basic.coefficient_of_variation || 0;
        if (cv > 0.5) {
            insights.push('High demand variability detected - implementing demand response programs could help stabilize load patterns.');
        } else if (cv < 0.2) {
            insights.push('Low demand variability indicates predictable consumption patterns, suitable for efficient capacity planning.');
        }

        // Seasonal insights
        if (statistics.seasonal_patterns?.summary) {
            const seasons = Object.keys(statistics.seasonal_patterns.summary);
            const seasonalLoads = seasons.map(s => statistics.seasonal_patterns.summary[s].mean || 0);
            const maxSeason = seasons[seasonalLoads.indexOf(Math.max(...seasonalLoads))];
            const minSeason = seasons[seasonalLoads.indexOf(Math.min(...seasonalLoads))];

            if (maxSeason !== minSeason) {
                insights.push(`Peak consumption occurs during ${maxSeason} season, while ${minSeason} shows the lowest demand - plan seasonal capacity accordingly.`);
            }
        }

        // Energy efficiency insights
        const totalEnergy = basic.total_energy || 0;
        const avgLoad = basic.average_load || 0;
        if (totalEnergy > 0 && avgLoad > 0) {
            const hours = totalEnergy / avgLoad;
            if (hours > 8760) {
                insights.push('Multi-year data detected - consider analyzing annual trends for long-term capacity planning.');
            }
        }

        // Peak timing insights
        if (statistics.hourly_patterns?.peak_hour !== undefined) {
            const peakHour = statistics.hourly_patterns.peak_hour;
            if (peakHour >= 18 && peakHour <= 21) {
                insights.push('Evening peak hours (6-9 PM) detected - typical residential/commercial pattern suitable for time-of-use pricing strategies.');
            } else if (peakHour >= 10 && peakHour <= 16) {
                insights.push('Daytime peak hours (10 AM-4 PM) suggest commercial/industrial load pattern - consider solar integration opportunities.');
            }
        }

        return insights;
    }

    // Comparison Functions
    function showComparisonModal() {
        const modal = new bootstrap.Modal(document.getElementById('comparisonModal'));

        // Populate comparison year filter with available years from first profile
        const yearFilter = document.getElementById('comparisonYear');
        if (yearFilter) {
            yearFilter.innerHTML = '<option value="">All Years</option>';

            const firstProfile = Array.from(AppState.selectedProfiles)[0];
            if (firstProfile && AppState.loadedData.has(firstProfile)) {
                const data = AppState.loadedData.get(firstProfile).data;
                const years = [...new Set(data.map(d => d.financial_year))].filter(y => y).sort();
                years.forEach(year => {
                    const option = document.createElement('option');
                    option.value = year;
                    option.textContent = `FY ${year}`;
                    yearFilter.appendChild(option);
                });
            }
        }

        modal.show();
    }

    async function runComparison() {
        try {
            showLoading(true);

            const comparisonType = document.getElementById('comparisonType')?.value || 'overview';
            const unit = document.getElementById('comparisonUnit')?.value || 'kW';
            const year = document.getElementById('comparisonYear')?.value || '';
            const season = document.getElementById('comparisonSeason')?.value || 'all';

            const requestData = {
                profile_ids: Array.from(AppState.selectedProfiles),
                comparison_type: comparisonType,
                unit: unit
            };

            if (year) requestData.year = year;
            if (season !== 'all') requestData.season = season;

            const response = await fetchWithRetry(`${API_CONFIG.base}/compare_profiles`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (result.status === 'success') {
                displayComparisonResults(result.data);

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('comparisonModal'));
                if (modal) modal.hide();
            } else {
                throw new Error(result.message || 'Comparison failed');
            }
        } catch (error) {
            console.error('Error running comparison:', error);
            showAlert('danger', `Comparison error: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function displayComparisonResults(comparisonData) {
        const resultsContainer = document.getElementById('comparisonResults');
        if (!resultsContainer) return;

        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('fade-in');

        // Create comparison chart
        if (AppState.charts.comparison && comparisonData.chart_type) {
            renderComparisonChart(comparisonData);
        }

        // Update comparison statistics
        updateComparisonStats(comparisonData.statistics || {});

        // Scroll to results
        resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function renderComparisonChart(comparisonData) {
        const { data, statistics, unit } = comparisonData;

        if (comparisonData.chart_type === 'multi_bar' && data?.profiles && data?.metrics) {
            const profiles = data.profiles;
            const metrics = data.metrics;

            const series = Object.keys(metrics).map((metric, index) => ({
                name: metric.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                type: 'bar',
                data: metrics[metric],
                itemStyle: {
                    color: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'][index % 5]
                }
            }));

            const option = {
                title: {
                    text: `Profile Comparison (${unit})`,
                    left: 'center',
                    textStyle: { fontSize: 16, fontWeight: 'bold' }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    backgroundColor: 'rgba(255, 255, 255, 0.95)'
                },
                legend: {
                    data: series.map(s => s.name),
                    top: 30,
                    type: 'scroll'
                },
                grid: {
                    left: '10%',
                    right: '4%',
                    bottom: '15%',
                    containLabel: true
                },
                xAxis: {
                    type: 'category',
                    data: profiles,
                    axisLabel: { rotate: 45, fontSize: 10 }
                },
                yAxis: {
                    type: 'value',
                    name: `Value (${unit})`,
                    nameLocation: 'middle',
                    nameGap: 60
                },
                series: series
            };

            AppState.charts.comparison.setOption(option, true);
        }
    }

    function updateComparisonStats(statistics) {
        const statsContainer = document.getElementById('comparisonStats');
        if (!statsContainer || !statistics) return;

        let statsHtml = '';

        Object.entries(statistics).forEach(([profileId, stats]) => {
            const basic = stats.basic || stats;
            statsHtml += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="card-title text-truncate" title="${profileId}">${profileId}</h6>
                            <div class="row g-2">
                                <div class="col-6">
                                    <small class="text-muted">Peak Load</small>
                                    <div class="fw-bold">${basic.peak_load?.toFixed(1) || '--'} ${basic.unit || AppState.currentUnit}</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Avg Load</small>
                                    <div class="fw-bold">${basic.average_load?.toFixed(1) || '--'} ${basic.unit || AppState.currentUnit}</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Load Factor</small>
                                    <div class="fw-bold">${basic.load_factor?.toFixed(1) || '--'}%</div>
                                </div>
                                <div class="col-6">
                                    <small class="text-muted">Total Energy</small>
                                    <div class="fw-bold">${formatLargeNumber(basic.total_energy)} ${basic.unit || AppState.currentUnit}h</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        statsContainer.innerHTML = statsHtml;
    }

    // Profile Details and Validation
    async function viewProfileDetails(profileId) {
        try {
            showLoading(true);

            const response = await fetchWithRetry(`${API_CONFIG.base}/profile_data/${profileId}`);
            const result = await response.json();

            if (result.status === 'success') {
                displayProfileDetailsModal(profileId, result.data);
            } else {
                throw new Error(result.message || 'Failed to load profile details');
            }
        } catch (error) {
            console.error('Error loading profile details:', error);
            showAlert('danger', `Failed to load profile details: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function displayProfileDetailsModal(profileId, profileData) {
        const content = document.getElementById('profileDetailsContent');
        if (!content) return;

        const { statistics, metadata } = profileData;
        const basic = statistics?.basic || {};
        const temporal = statistics?.temporal || {};

        content.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6><i class="fas fa-info-circle me-2 text-primary"></i>Profile Information</h6>
                    <table class="table table-sm">
                        <tbody>
                            <tr><td class="fw-bold">Profile ID</td><td>${profileId}</td></tr>
                            <tr><td class="fw-bold">Total Records</td><td>${metadata.total_records?.toLocaleString() || '--'}</td></tr>
                            <tr><td class="fw-bold">Date Range</td><td>${temporal.date_range_start?.substring(0, 10) || '--'} to ${temporal.date_range_end?.substring(0, 10) || '--'}</td></tr>
                            <tr><td class="fw-bold">Data Frequency</td><td>${temporal.data_frequency || 'Unknown'}</td></tr>
                            <tr><td class="fw-bold">Unit</td><td>${basic.unit || metadata.unit || 'kW'}</td></tr>
                            <tr><td class="fw-bold">Data Quality</td><td>
                                <span class="badge bg-${metadata.data_quality?.completeness > 0.95 ? 'success' : metadata.data_quality?.completeness > 0.8 ? 'warning' : 'danger'}">
                                    ${((metadata.data_quality?.completeness || 0) * 100).toFixed(1)}% Complete
                                </span>
                            </td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6><i class="fas fa-chart-line me-2 text-success"></i>Load Statistics</h6>
                    <table class="table table-sm">
                        <tbody>
                            <tr><td class="fw-bold">Peak Load</td><td class="text-primary fw-bold">${basic.peak_load?.toFixed(2) || '--'} ${basic.unit || 'kW'}</td></tr>
                            <tr><td class="fw-bold">Average Load</td><td>${basic.average_load?.toFixed(2) || '--'} ${basic.unit || 'kW'}</td></tr>
                            <tr><td class="fw-bold">Minimum Load</td><td>${basic.min_load?.toFixed(2) || '--'} ${basic.unit || 'kW'}</td></tr>
                            <tr><td class="fw-bold">Load Factor</td><td class="fw-bold ${basic.load_factor > 70 ? 'text-success' : basic.load_factor > 50 ? 'text-warning' : 'text-danger'}">${basic.load_factor?.toFixed(1) || '--'}%</td></tr>
                            <tr><td class="fw-bold">Std Deviation</td><td>${basic.std_dev?.toFixed(2) || '--'} ${basic.unit || 'kW'}</td></tr>
                            <tr><td class="fw-bold">Peak Time</td><td class="small">${temporal.peak_datetime ? new Date(temporal.peak_datetime).toLocaleString() : '--'}</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
            
            ${statistics.seasonal_patterns?.summary ? `
            <div class="mt-4">
                <h6><i class="fas fa-calendar-alt me-2 text-warning"></i>Seasonal Breakdown</h6>
                <div class="table-responsive">
                    <table class="table table-sm table-striped">
                        <thead class="table-dark">
                            <tr>
                                <th>Season</th>
                                <th>Average (${basic.unit || 'kW'})</th>
                                <th>Peak (${basic.unit || 'kW'})</th>
                                <th>Minimum (${basic.unit || 'kW'})</th>
                                <th>Total (${basic.unit || 'kW'}h)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${Object.entries(statistics.seasonal_patterns.summary).map(([season, stats]) => `
                                <tr>
                                    <td class="fw-bold">${season}</td>
                                    <td>${stats.mean?.toFixed(2) || '--'}</td>
                                    <td class="text-danger">${stats.max?.toFixed(2) || '--'}</td>
                                    <td class="text-success">${stats.min?.toFixed(2) || '--'}</td>
                                    <td>${stats.sum?.toFixed(2) || '--'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>` : ''}
            
            ${metadata.data_quality ? `
            <div class="mt-4">
                <h6><i class="fas fa-check-circle me-2 text-info"></i>Data Quality Assessment</h6>
                <div class="row">
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded">
                            <div class="h4 mb-1 ${metadata.data_quality.completeness > 0.95 ? 'text-success' : 'text-warning'}">${(metadata.data_quality.completeness * 100).toFixed(1)}%</div>
                            <small class="text-muted">Completeness</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded">
                            <div class="h4 mb-1 ${metadata.data_quality.has_negatives ? 'text-danger' : 'text-success'}">${metadata.data_quality.has_negatives ? 'Yes' : 'No'}</div>
                            <small class="text-muted">Negative Values</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 border rounded">
                            <div class="h4 mb-1 ${metadata.data_quality.has_zeros ? 'text-warning' : 'text-success'}">${metadata.data_quality.has_zeros ? 'Yes' : 'No'}</div>
                            <small class="text-muted">Zero Values</small>
                        </div>
                    </div>
                </div>
            </div>` : ''}
        `;

        const modal = new bootstrap.Modal(document.getElementById('profileDetailsModal'));
        modal.show();
    }

    async function validateSelectedProfiles() {
        const selectedArray = Array.from(AppState.selectedProfiles);
        if (selectedArray.length === 0) return;

        try {
            showLoading(true);

            const validationResults = {};

            // Validate each selected profile
            for (const profileId of selectedArray) {
                try {
                    const response = await fetchWithRetry(`${API_CONFIG.base}/profile_validation/${profileId}`);
                    const result = await response.json();

                    if (result.status === 'success') {
                        validationResults[profileId] = result.data;
                    } else {
                        validationResults[profileId] = { error: result.message };
                    }
                } catch (error) {
                    validationResults[profileId] = { error: error.message };
                }
            }

            displayValidationResults(validationResults);

        } catch (error) {
            console.error('Error validating profiles:', error);
            showAlert('danger', `Validation error: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function displayValidationResults(validationResults) {
        const content = document.getElementById('validationContent');
        if (!content) return;

        let html = '';

        Object.entries(validationResults).forEach(([profileId, result]) => {
            if (result.error) {
                html += `
                    <div class="alert alert-danger">
                        <h6><i class="fas fa-exclamation-triangle me-2"></i>${profileId}</h6>
                        <p>Validation failed: ${result.error}</p>
                    </div>
                `;
                return;
            }

            const statusClass = result.status === 'excellent' ? 'success' :
                result.status === 'good' ? 'info' :
                    result.status === 'fair' ? 'warning' : 'danger';

            html += `
                <div class="card mb-3">
                    <div class="card-header bg-${statusClass} text-white">
                        <h6 class="mb-0"><i class="fas fa-chart-line me-2"></i>${profileId}</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Validation Score</h6>
                                <div class="progress mb-3">
                                    <div class="progress-bar bg-${statusClass}" style="width: ${result.overall_score}%">
                                        ${result.overall_score.toFixed(1)}%
                                    </div>
                                </div>
                                <div><strong>Status:</strong> <span class="text-${statusClass}">${result.status.toUpperCase()}</span></div>
                                <div><strong>Total Records:</strong> ${result.summary?.total_records?.toLocaleString() || '--'}</div>
                                <div><strong>Valid Demand Records:</strong> ${result.summary?.valid_demand_records?.toLocaleString() || '--'}</div>
                            </div>
                            <div class="col-md-6">
                                <h6>Issues & Warnings</h6>
                                ${result.issues?.length > 0 ? `
                                    <div class="mb-2">
                                        <strong class="text-danger">Issues:</strong>
                                        <ul class="small mb-0">
                                            ${result.issues.map(issue => `<li>${issue}</li>`).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                                ${result.warnings?.length > 0 ? `
                                    <div class="mb-2">
                                        <strong class="text-warning">Warnings:</strong>
                                        <ul class="small mb-0">
                                            ${result.warnings.map(warning => `<li>${warning}</li>`).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                                ${result.passed_checks?.length > 0 ? `
                                    <div>
                                        <strong class="text-success">Passed Checks:</strong>
                                        <ul class="small mb-0">
                                            ${result.passed_checks.map(check => `<li>${check.replace(/_/g, ' ')}</li>`).join('')}
                                        </ul>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        content.innerHTML = html;

        const modal = new bootstrap.Modal(document.getElementById('validationModal'));
        modal.show();
    }

    function analyzeSelectedProfile() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('profileDetailsModal'));
        if (modal) modal.hide();

        // The profile should already be selected, just ensure it's the current one
        if (AppState.selectedProfiles.size > 0) {
            const profileId = Array.from(AppState.selectedProfiles)[0];
            if (profileId !== AppState.currentProfile) {
                selectSingleProfile(profileId);
            }
        }
    }

    // Export Functions
    async function exportAnalysis(format) {
        if (!AppState.currentProfile) {
            showAlert('warning', 'Please select a profile to export');
            return;
        }

        try {
            showLoading(true);

            const response = await fetchWithRetry(
                `${API_CONFIG.base}/export_analysis/${AppState.currentProfile}?format=${format}&unit=${AppState.currentUnit}`
            );

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${AppState.currentProfile}_analysis.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                showAlert('success', `Analysis exported as ${format.toUpperCase()}`);
            } else {
                throw new Error(`Export failed: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            console.error('Export error:', error);
            showAlert('danger', `Export failed: ${error.message}`);
        } finally {
            showLoading(false);
        }
    }

    function exportData(format) {
        if (AppState.dataTable) {
            switch (format) {
                case 'csv':
                    AppState.dataTable.button('.buttons-csv').trigger();
                    break;
                case 'excel':
                    AppState.dataTable.button('.buttons-excel').trigger();
                    break;
                case 'json':
                    // Custom JSON export
                    const data = AppState.dataTable.data().toArray();
                    const jsonData = JSON.stringify(data, null, 2);
                    downloadAsFile(jsonData, `${AppState.currentProfile}_data.json`, 'application/json');
                    break;
            }
        } else {
            showAlert('warning', 'No data table available for export');
        }
    }

    function downloadChart() {
        if (AppState.charts.main) {
            const url = AppState.charts.main.getDataURL({
                pixelRatio: 2,
                backgroundColor: '#fff'
            });
            const a = document.createElement('a');
            a.href = url;
            a.download = `${AppState.currentProfile}_${AppState.currentAnalysisType}_chart.png`;
            a.click();

            showAlert('success', 'Chart downloaded successfully');
        } else {
            showAlert('warning', 'No chart available for download');
        }
    }

    function fullscreenChart() {
        const chartElement = document.getElementById('mainChart');
        if (chartElement) {
            if (chartElement.requestFullscreen) {
                chartElement.requestFullscreen();
            } else if (chartElement.webkitRequestFullscreen) {
                chartElement.webkitRequestFullscreen();
            } else if (chartElement.msRequestFullscreen) {
                chartElement.msRequestFullscreen();
            }
        }
    }

    function resetChart() {
        if (AppState.charts.main) {
            AppState.charts.main.dispatchAction({
                type: 'dataZoom',
                start: 0,
                end: 100
            });
        }
    }

    function toggleTableView() {
        const tableContainer = document.getElementById('dataTableContainer');
        if (tableContainer) {
            const isVisible = tableContainer.style.display !== 'none';
            tableContainer.style.display = isVisible ? 'none' : 'block';
        }
    }

    function exportTableData() {
        if (AppState.dataTable) {
            AppState.dataTable.button('.buttons-excel').trigger();
        }
    }

    function refreshTable() {
        if (AppState.dataTable) {
            AppState.dataTable.ajax.reload();
        } else {
            updateDataTable();
        }
    }

    function exportComparison() {
        if (AppState.charts.comparison) {
            const url = AppState.charts.comparison.getDataURL({
                pixelRatio: 2,
                backgroundColor: '#fff'
            });
            const a = document.createElement('a');
            a.href = url;
            a.download = `profile_comparison_${new Date().toISOString().slice(0, 10)}.png`;
            a.click();

            showAlert('success', 'Comparison chart downloaded successfully');
        }
    }

    // Utility Functions
    function updateChartInfo(metadata) {
        const chartInfo = document.getElementById('chartInfo');
        if (chartInfo && metadata) {
            chartInfo.innerHTML = `
                <i class="fas fa-info-circle me-1"></i>
                ${metadata.total_records?.toLocaleString() || '--'} total records | 
                ${metadata.sample_records?.toLocaleString() || '--'} displayed |
                Unit: ${metadata.unit || 'kW'} |
                <i class="fas fa-clock me-1"></i>Updated: ${new Date().toLocaleTimeString()}
            `;
        }
    }

    function updateProfileCount() {
        const profileItems = document.querySelectorAll('.profile-item');
        const countElement = document.getElementById('profileCount');
        if (countElement) {
            countElement.textContent = `${profileItems.length} profiles`;
        }
    }

    async function fetchWithRetry(url, options = {}, retries = API_CONFIG.retryAttempts) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(url, {
                    ...options,
                    signal: AbortSignal.timeout(API_CONFIG.timeout)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return response;
            } catch (error) {
                if (i === retries - 1) throw error;

                console.warn(`Fetch attempt ${i + 1} failed, retrying...`, error);
                await new Promise(resolve => setTimeout(resolve, API_CONFIG.retryDelay * (i + 1)));
            }
        }
    }

    function downloadAsFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }

        // Update button states
        document.body.style.cursor = show ? 'wait' : 'default';
        AppState.isLoading = show;
    }

    function showAlert(type, message, duration = 5000) {
        const alert = document.getElementById('statusAlert');
        const messageSpan = document.getElementById('statusMessage');

        if (alert && messageSpan) {
            alert.className = `alert alert-${type} alert-dismissible fade show alert-custom`;
            messageSpan.textContent = message;
            alert.classList.remove('d-none');

            if (duration > 0) {
                setTimeout(() => {
                    alert.classList.add('d-none');
                }, duration);
            }
        }

        console.log(`[LoadProfileAnalysis] ${type.toUpperCase()}: ${message}`);
    }

    // State Management
    function saveState() {
        try {
            const state = {
                selectedProfiles: Array.from(AppState.selectedProfiles),
                currentProfile: AppState.currentProfile,
                currentAnalysisType: AppState.currentAnalysisType,
                currentUnit: AppState.currentUnit,
                currentFilters: AppState.currentFilters
            };
            localStorage.setItem('loadProfileAnalysisState', JSON.stringify(state));
        } catch (error) {
            console.warn('Failed to save state:', error);
        }
    }

    function loadCachedState() {
        try {
            const savedState = localStorage.getItem('loadProfileAnalysisState');
            if (savedState) {
                const state = JSON.parse(savedState);

                // Restore selections (but don't auto-load data to avoid performance issues)
                if (state.selectedProfiles?.length > 0) {
                    state.selectedProfiles.forEach(id => {
                        if (document.querySelector(`[data-profile-id="${id}"]`)) {
                            AppState.selectedProfiles.add(id);
                        }
                    });

                    if (state.currentProfile && AppState.selectedProfiles.has(state.currentProfile)) {
                        AppState.currentProfile = state.currentProfile;
                    }

                    updateProfileSelectionUI();
                }

                // Restore filters
                if (state.currentAnalysisType) {
                    AppState.currentAnalysisType = state.currentAnalysisType;
                    const analysisSelect = document.getElementById('analysisType');
                    if (analysisSelect) analysisSelect.value = state.currentAnalysisType;
                }

                if (state.currentUnit) {
                    AppState.currentUnit = state.currentUnit;
                    const unitSelect = document.getElementById('unitFilter');
                    if (unitSelect) unitSelect.value = state.currentUnit;
                }

                if (state.currentFilters) {
                    AppState.currentFilters = { ...AppState.currentFilters, ...state.currentFilters };
                }
            }
        } catch (error) {
            console.warn('Failed to load cached state:', error);
        }
    }

    // Make functions available globally for HTML onclick handlers
    window.exportAnalysis = exportAnalysis;
    window.exportData = exportData;
    window.downloadChart = downloadChart;
    window.fullscreenChart = fullscreenChart;
    window.resetChart = resetChart;
    window.toggleTableView = toggleTableView;
    window.exportTableData = exportTableData;
    window.refreshTable = refreshTable;
    window.exportComparison = exportComparison;
    window.runComparison = runComparison;
    window.analyzeSelectedProfile = analyzeSelectedProfile;

    console.log('Load Profile Analysis:system ready');
});