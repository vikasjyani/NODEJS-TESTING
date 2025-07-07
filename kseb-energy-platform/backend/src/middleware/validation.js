const { logger } = require('../utils/logger');

/**
 * Validates the configuration for a demand forecast.
 * @param {object} config - The forecast configuration object.
 * @returns {object} - An object { isValid: boolean, errors: string[] }.
 */
const validateForecastConfig = (config) => {
    const errors = [];
    if (!config) {
        errors.push('Configuration object is required.');
        return { isValid: false, errors };
    }

    if (!config.scenario_name || typeof config.scenario_name !== 'string' || config.scenario_name.trim() === '') {
        errors.push('Scenario name (scenario_name) is required and must be a non-empty string.');
    }

    if (!config.target_year || typeof config.target_year !== 'number' || config.target_year < new Date().getFullYear() || config.target_year > 2100) {
        errors.push('Target year (target_year) is required and must be a valid future year (number).');
    }

    if (!config.sectors || typeof config.sectors !== 'object' || Object.keys(config.sectors).length === 0) {
        errors.push('Sectors configuration (sectors) is required and must be a non-empty object.');
    } else {
        for (const sectorName in config.sectors) {
            const sectorConfig = config.sectors[sectorName];
            if (!sectorConfig.models || !Array.isArray(sectorConfig.models) || sectorConfig.models.length === 0) {
                errors.push(`Sector '${sectorName}' must have a non-empty array of models.`);
            } else {
                sectorConfig.models.forEach(model => {
                    if (typeof model !== 'string' || model.trim() === '') {
                        errors.push(`Sector '${sectorName}' has an invalid model name: '${model}'. Models must be non-empty strings.`);
                    }
                    // Add more specific model validation if needed, e.g., check against a list of known models
                });
            }
            // Example: if MLR model is used, independent_variables might be required
            if (sectorConfig.models.includes('MLR') && (!sectorConfig.independent_variables || !Array.isArray(sectorConfig.independent_variables) || sectorConfig.independent_variables.length === 0)) {
                errors.push(`Sector '${sectorName}' using MLR model requires 'independent_variables' array.`);
            }
        }
    }

    if (config.input_file && typeof config.input_file !== 'string') {
        errors.push('Input file path (input_file) if provided, must be a string.');
    }

    if (config.exclude_covid && typeof config.exclude_covid !== 'boolean') {
        errors.push('Exclude COVID flag (exclude_covid), if provided, must be a boolean.');
    }

    if (config.timeout && (typeof config.timeout !== 'number' || config.timeout <=0) ){
        errors.push('Timeout, if provided, must be a positive number.');
    }

    logger.debug(`Forecast config validation for scenario '${config.scenario_name}': ${errors.length === 0 ? 'Valid' : 'Invalid - ' + errors.join(', ')}`);
    return {
        isValid: errors.length === 0,
        errors: errors,
    };
};


/**
 * Validates the configuration for load profile generation.
 * @param {object} config - The load profile configuration object.
 * @returns {object} - An object { isValid: boolean, errors: string[] }.
 */
const validateProfileConfig = (config) => {
    const errors = [];
    if (!config) {
        errors.push('Configuration object is required.');
        return { isValid: false, errors };
    }

    if (!config.method || typeof config.method !== 'string' || !['base_scaling', 'stl_decomposition'].includes(config.method)) {
        errors.push('Generation method (method) is required and must be either "base_scaling" or "stl_decomposition".');
    }

    if (!config.start_year || typeof config.start_year !== 'number' || config.start_year < 1900 || config.start_year > 2100) {
        errors.push('Start year (start_year) is required and must be a valid year.');
    }

    if (!config.end_year || typeof config.end_year !== 'number' || config.end_year < 1900 || config.end_year > 2100) {
        errors.push('End year (end_year) is required and must be a valid year.');
    }

    if (config.start_year && config.end_year && config.start_year > config.end_year) {
        errors.push('Start year cannot be after end year.');
    }

    if (config.method === 'base_scaling') {
        if (!config.base_year || typeof config.base_year !== 'number' || config.base_year < 1900 || config.base_year > 2100) {
            errors.push('Base year (base_year) is required for base_scaling method.');
        }
        // It might also need demand_scenario or growth_rate + base_demand
        if (!config.demand_scenario && (config.growth_rate === undefined || config.base_demand === undefined)) {
            errors.push("For base_scaling, either 'demand_scenario' or both 'growth_rate' and 'base_demand' must be provided.");
        }
        if (config.growth_rate !== undefined && (typeof config.growth_rate !== 'number' || config.growth_rate < -1 || config.growth_rate > 1)) {
             errors.push("Growth rate must be a number between -1 and 1 (e.g., 0.02 for 2%).");
        }
         if (config.base_demand !== undefined && (typeof config.base_demand !== 'number' || config.base_demand <= 0)) {
             errors.push("Base demand must be a positive number.");
        }
    }

    if (config.method === 'stl_decomposition') {
        if (config.historical_years && (!Array.isArray(config.historical_years) || !config.historical_years.every(year => typeof year === 'number'))) {
            errors.push('Historical years (historical_years) for STL method must be an array of numbers.');
        }
        if (config.stl_seasonal && (typeof config.stl_seasonal !== 'number' || config.stl_seasonal <= 1)) {
             errors.push("STL seasonal parameter, if provided, must be an odd integer greater than 1.");
        }
    }

    if (config.timeout && (typeof config.timeout !== 'number' || config.timeout <=0) ){
        errors.push('Timeout, if provided, must be a positive number.');
    }

    logger.debug(`Profile config validation for method '${config.method}': ${errors.length === 0 ? 'Valid' : 'Invalid - ' + errors.join(', ')}`);
    return {
        isValid: errors.length === 0,
        errors: errors,
    };
};


/**
 * Validates the configuration for PyPSA optimization.
 * @param {object} config - The PyPSA configuration object.
 * @returns {object} - An object { isValid: boolean, errors: string[] }.
 */
const validatePyPSAConfig = (config) => {
    const errors = [];
    if (!config) {
        errors.push('Configuration object is required.');
        return { isValid: false, errors };
    }

    if (!config.scenario_name || typeof config.scenario_name !== 'string' || config.scenario_name.trim() === '') {
        errors.push('Scenario name (scenario_name) is required.');
    }

    if (!config.base_year || typeof config.base_year !== 'number' || config.base_year < 1900 || config.base_year > 2100) {
        errors.push('Base year (base_year) is required and must be a valid year.');
    }

    if (!config.investment_mode || typeof config.investment_mode !== 'string' || !['single_year', 'multi_year', 'all_in_one'].includes(config.investment_mode)) {
        errors.push('Investment mode (investment_mode) is required and must be one of "single_year", "multi_year", "all_in_one".');
    }

    if (config.input_file && typeof config.input_file !== 'string') {
        errors.push('Input file path (input_file), if provided, must be a string.');
    }

    if (config.solver_options) {
        if (typeof config.solver_options !== 'object') {
            errors.push('Solver options (solver_options), if provided, must be an object.');
        } else {
            if (config.solver_options.solver && !['highs', 'gurobi', 'cplex', 'glpk', 'cbc'].includes(config.solver_options.solver.toLowerCase())) {
                errors.push('Solver name in solver_options is invalid.');
            }
            if (config.solver_options.optimality_gap && (typeof config.solver_options.optimality_gap !== 'number' || config.solver_options.optimality_gap < 0 || config.solver_options.optimality_gap > 1)) {
                errors.push('Optimality gap must be a number between 0 and 1.');
            }
            if (config.solver_options.time_limit && (typeof config.solver_options.time_limit !== 'number' || config.solver_options.time_limit <= 0)) {
                errors.push('Time limit must be a positive number (seconds).');
            }
        }
    }

    if (config.timeout && (typeof config.timeout !== 'number' || config.timeout <=0) ){
        errors.push('Timeout, if provided, must be a positive number.');
    }

    // Add more specific PyPSA validations as needed, e.g., snapshot_selection, generator_clustering, etc.

    logger.debug(`PyPSA config validation for scenario '${config.scenario_name}': ${errors.length === 0 ? 'Valid' : 'Invalid - ' + errors.join(', ')}`);
    return {
        isValid: errors.length === 0,
        errors: errors,
    };
};


module.exports = {
    validateForecastConfig,
    validateProfileConfig,
    validatePyPSAConfig,
    // Add other specific validators as needed
};
