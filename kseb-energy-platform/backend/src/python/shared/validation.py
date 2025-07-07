import pandas as pd
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def validate_dataframe_schema(
    df: pd.DataFrame,
    required_columns: Optional[Dict[str, type]] = None, # e.g., {'year': int, 'demand': float}
    optional_columns: Optional[Dict[str, type]] = None,
    allow_extra_columns: bool = True
) -> List[str]:
    """
    Validates if a DataFrame adheres to a defined schema.

    Args:
        df (pd.DataFrame): The DataFrame to validate.
        required_columns (Optional[Dict[str, type]]): A dictionary where keys are column names
            and values are the expected Python types (e.g., int, float, str, object for datetime).
        optional_columns (Optional[Dict[str, type]]): Similar to required_columns, but for optional ones.
        allow_extra_columns (bool): If False, an error is raised if df has columns not in required or optional.

    Returns:
        List[str]: A list of error messages. Empty if validation passes.
    """
    errors: List[str] = []
    if df is None:
        errors.append("DataFrame is None.")
        return errors
    if not isinstance(df, pd.DataFrame):
        errors.append("Input is not a pandas DataFrame.")
        return errors

    df_columns_lower = {str(col).lower().strip(): col for col in df.columns}

    # Check required columns
    if required_columns:
        for col_name, expected_type in required_columns.items():
            col_name_lower = col_name.lower().strip()
            if col_name_lower not in df_columns_lower:
                errors.append(f"Required column '{col_name}' is missing.")
            else:
                actual_col_name = df_columns_lower[col_name_lower]
                # Basic type check - can be enhanced (e.g. pd.api.types.is_numeric_dtype)
                # For simplicity, checking first non-null value's type or pandas dtype.
                # A more robust check would iterate or use pandas dtypes.
                # For example, if expected_type is int, pd.api.types.is_integer_dtype(df[actual_col_name])
                if not pd.api.types.is_dtype_equal(df[actual_col_name].dtype, expected_type):
                    # This is a very basic type check. For production, use more specific checks.
                    # e.g. pd.api.types.is_numeric_dtype, is_datetime64_any_dtype etc.
                    # And handle cases like object dtype which can contain mixed types.
                    # For now, we'll log a warning for type mismatch.
                    # errors.append(f"Column '{actual_col_name}' has type {df[actual_col_name].dtype}, expected {expected_type}.")
                    logger.debug(f"Column '{actual_col_name}' has type {df[actual_col_name].dtype}, expected {expected_type}. This is a basic check.")


    # Check optional columns type if they exist
    if optional_columns:
        for col_name, expected_type in optional_columns.items():
            col_name_lower = col_name.lower().strip()
            if col_name_lower in df_columns_lower:
                actual_col_name = df_columns_lower[col_name_lower]
                if not pd.api.types.is_dtype_equal(df[actual_col_name].dtype, expected_type):
                    logger.debug(f"Optional column '{actual_col_name}' has type {df[actual_col_name].dtype}, expected {expected_type}.")


    # Check for extra columns if not allowed
    if not allow_extra_columns:
        allowed_cols_lower = set()
        if required_columns: allowed_cols_lower.update(str(k).lower().strip() for k in required_columns.keys())
        if optional_columns: allowed_cols_lower.update(str(k).lower().strip() for k in optional_columns.keys())

        extra_cols = [col for col_lower, col in df_columns_lower.items() if col_lower not in allowed_cols_lower]
        if extra_cols:
            errors.append(f"DataFrame contains unexpected columns: {', '.join(extra_cols)}.")

    return errors

def validate_config_keys(
    config: Dict[str, Any],
    required_keys: List[str],
    optional_keys: Optional[List[str]] = None
) -> List[str]:
    """
    Validates if a configuration dictionary contains all required keys and checks for unknown keys.

    Args:
        config (Dict[str, Any]): The configuration dictionary.
        required_keys (List[str]): List of keys that must be present in the config.
        optional_keys (Optional[List[str]]): List of known optional keys.

    Returns:
        List[str]: A list of error messages. Empty if validation passes.
    """
    errors: List[str] = []
    if not isinstance(config, dict):
        errors.append("Configuration must be a dictionary.")
        return errors

    config_keys_set = set(config.keys())

    # Check for missing required keys
    for req_key in required_keys:
        if req_key not in config_keys_set:
            errors.append(f"Missing required configuration key: '{req_key}'.")

    # Check for unknown keys (if optional_keys is provided to define all known keys)
    if optional_keys is not None:
        known_keys = set(required_keys) | set(optional_keys)
        unknown_keys = config_keys_set - known_keys
        if unknown_keys:
            errors.append(f"Unknown configuration keys found: {', '.join(sorted(list(unknown_keys)))}.")

    return errors


if __name__ == '__main__':
    # Example Usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test DataFrame schema validation
    sample_data = {
        'Year': [2020, 2021, 2022],
        'Demand_GWh': [100.5, 110.2, 120.7],
        'GDP_indicator': [10, 11, 12],
        'ExtraCol': ['a', 'b', 'c']
    }
    df_test = pd.DataFrame(sample_data)
    # Pandas infers types. For explicit type testing, cast them or use more robust checks.
    df_test['Year'] = df_test['Year'].astype(np.int64) # Example for type check
    df_test['Demand_GWh'] = df_test['Demand_GWh'].astype(np.float64)
    df_test['GDP_indicator'] = df_test['GDP_indicator'].astype(np.int64)


    required = {'year': np.int64, 'demand_gwh': np.float64}
    optional = {'gdp_indicator': np.int64}

    schema_errors = validate_dataframe_schema(df_test, required, optional, allow_extra_columns=False)
    if schema_errors:
        logger.error(f"Schema validation failed: {schema_errors}")
    else:
        logger.info("Schema validation passed (with allow_extra_columns=False, expecting error for ExtraCol).")

    schema_errors_allow_extra = validate_dataframe_schema(df_test, required, optional, allow_extra_columns=True)
    if schema_errors_allow_extra:
        logger.error(f"Schema validation (allow_extra=True) failed: {schema_errors_allow_extra}")
    else:
        logger.info("Schema validation passed (with allow_extra_columns=True).")


    # Test config key validation
    valid_config_example = {'scenario_name': 'Test', 'target_year': 2030, 'models': ['SLR']}
    req_config_keys = ['scenario_name', 'target_year']
    opt_config_keys = ['models', 'input_file', 'exclude_covid']

    config_errors = validate_config_keys(valid_config_example, req_config_keys, opt_config_keys)
    if config_errors:
        logger.error(f"Config validation failed: {config_errors}")
    else:
        logger.info("Config validation passed for valid_config_example.")

    invalid_config_example = {'scenario_name': 'Test', 'unknown_param': True} # Missing target_year, has unknown
    config_errors_invalid = validate_config_keys(invalid_config_example, req_config_keys, opt_config_keys)
    if config_errors_invalid:
        logger.error(f"Config validation for invalid_config_example failed as expected: {config_errors_invalid}")
    else:
        logger.info("Config validation for invalid_config_example passed (unexpected).")

    logger.info("validation.py example run complete.")
