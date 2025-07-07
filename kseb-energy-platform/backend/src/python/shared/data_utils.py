import pandas as pd
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_excel_sheet(file_path: Union[str, Path], sheet_name: str, expected_columns: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
    """
    Loads a specific sheet from an Excel file and performs basic validation.

    Args:
        file_path (Union[str, Path]): Path to the Excel file.
        sheet_name (str): Name of the sheet to load.
        expected_columns (Optional[List[str]]): A list of column names expected to be in the sheet.
                                                If None, no column check is performed.

    Returns:
        Optional[pd.DataFrame]: DataFrame if loaded successfully, None otherwise.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return None

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        logger.info(f"Successfully loaded sheet '{sheet_name}' from '{file_path}'. Shape: {df.shape}")

        if df.empty:
            logger.warning(f"Sheet '{sheet_name}' in '{file_path}' is empty.")
            # return df # Or None, depending on how empty sheets should be handled

        if expected_columns:
            df.columns = [str(col).lower().strip() for col in df.columns] # Standardize column names
            missing_cols = [col for col in expected_columns if col.lower().strip() not in df.columns]
            if missing_cols:
                logger.warning(f"Sheet '{sheet_name}': Missing expected columns: {', '.join(missing_cols)}. Found: {', '.join(df.columns)}")
                # Depending on strictness, you might return None or the df with a warning

        return df

    except Exception as e:
        logger.error(f"Error loading sheet '{sheet_name}' from '{file_path}': {e}")
        return None

def clean_timeseries_data(
    df: pd.DataFrame,
    year_col: str = 'year',
    value_col: str = 'demand',
    other_numeric_cols: Optional[List[str]] = None,
    exclude_years: Optional[List[int]] = None
) -> pd.DataFrame:
    """
    Cleans and prepares a DataFrame for time series analysis or regression.

    Args:
        df (pd.DataFrame): Input DataFrame.
        year_col (str): Name of the column containing year information.
        value_col (str): Name of the primary value column (e.g., 'demand').
        other_numeric_cols (Optional[List[str]]): Other columns that should be numeric.
        exclude_years (Optional[List[int]]): List of years to exclude from the data.

    Returns:
        pd.DataFrame: Cleaned and sorted DataFrame.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    _df = df.copy()
    _df.columns = [str(col).lower().strip() for col in _df.columns] # Standardize column names

    required_cols = [year_col, value_col]
    for col in required_cols:
        if col not in _df.columns:
            logger.error(f"Required column '{col}' not found in DataFrame.")
            return pd.DataFrame() # Or raise error

    # Convert year and primary value column to numeric, coercing errors
    _df[year_col] = pd.to_numeric(_df[year_col], errors='coerce')
    _df[value_col] = pd.to_numeric(_df[value_col], errors='coerce')

    # Convert other specified numeric columns
    if other_numeric_cols:
        for col in other_numeric_cols:
            if col in _df.columns:
                _df[col] = pd.to_numeric(_df[col], errors='coerce')
            else:
                logger.warning(f"Specified numeric column '{col}' not found.")

    # Drop rows where essential columns (year, value_col) are NaN after conversion
    _df = _df.dropna(subset=[year_col, value_col])

    if _df.empty:
        logger.warning("DataFrame became empty after coercing essential columns and dropping NaNs.")
        return _df

    # Exclude specified years
    if exclude_years:
        _df = _df[~_df[year_col].isin(exclude_years)]
        logger.info(f"Excluded years {exclude_years}. Data shape after exclusion: {_df.shape}")

    # Sort by year
    _df = _df.sort_values(by=year_col).reset_index(drop=True)

    return _df


def extrapolate_linearly(series: pd.Series, n_periods: int) -> np.ndarray:
    """
    Simple linear extrapolation for n_periods based on the last two points or overall trend.
    """
    if len(series) < 2:
        logger.warning("Not enough data points to extrapolate linearly. Returning last value or zeros.")
        last_val = series.iloc[-1] if len(series) == 1 else 0
        return np.full(n_periods, last_val)

    # Use last two points for simple trend
    x = np.arange(len(series))
    y = series.values

    # Fit a line to the last few points (e.g., last 5 or all if less than 5)
    fit_points = min(len(x), 5)
    coeffs = np.polyfit(x[-fit_points:], y[-fit_points:], 1)
    slope, intercept = coeffs[0], coeffs[1]

    future_x = np.arange(len(series), len(series) + n_periods)
    return slope * future_x + intercept


def save_results_json(data: Dict[str, Any], output_dir: Union[str, Path], filename: str):
    """Saves dictionary data to a JSON file in the specified directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{filename}.json"

    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str) # default=str for datetime, numpy types
        logger.info(f"Results successfully saved to: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save results to {file_path}: {e}")

if __name__ == '__main__':
    # Example Usage (can be run directly for testing this module)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create a dummy Excel file for testing load_excel_sheet
    dummy_data = {'year': [2020, 2021, 2022], 'demand': [100, 110, 120], 'gdp': [1000, 1020, 1050]}
    dummy_df = pd.DataFrame(dummy_data)

    temp_excel_path = Path("temp_test_excel.xlsx")
    with pd.ExcelWriter(temp_excel_path) as writer:
        dummy_df.to_excel(writer, sheet_name="test_sheet", index=False)
        dummy_df.iloc[:, :2].to_excel(writer, sheet_name="partial_sheet", index=False) # Sheet with fewer columns
        pd.DataFrame().to_excel(writer, sheet_name="empty_sheet", index=False)

    logger.info(f"Created temporary Excel file: {temp_excel_path.resolve()}")

    # Test load_excel_sheet
    loaded_df = load_excel_sheet(temp_excel_path, "test_sheet", expected_columns=['year', 'demand', 'gdp'])
    if loaded_df is not None:
        logger.info(f"Loaded 'test_sheet' head:\n{loaded_df.head()}")

    load_excel_sheet(temp_excel_path, "partial_sheet", expected_columns=['year', 'demand', 'gdp']) # Should warn
    load_excel_sheet(temp_excel_path, "empty_sheet") # Should warn

    # Test clean_timeseries_data
    dirty_df_data = {
        'YEAR': ['2018', '2019', '2020', '2021', '2022', '2023'],
        'Demand (GWh)': [90, 95, 'error', 105, 110, 115],
        'GDP': [900, 950, 1000, 1010, 1020, 1030.0],
        'Population': [None, 100, 101, 102, 103, 104]
    }
    dirty_df = pd.DataFrame(dirty_df_data)
    cleaned_df = clean_timeseries_data(
        dirty_df,
        year_col='year', value_col='demand (gwh)', # Testing lowercase/space handling
        other_numeric_cols=['gdp', 'population'],
        exclude_years=[2020]
    )
    logger.info(f"Cleaned DataFrame head:\n{cleaned_df.head()}")
    logger.info(f"Cleaned DataFrame dtypes:\n{cleaned_df.dtypes}")


    # Test extrapolate_linearly
    s = pd.Series([10, 12, 14, 16, 18])
    extrapolated_values = extrapolate_linearly(s, 3)
    logger.info(f"Extrapolated values: {extrapolated_values}") # Expected: [20, 22, 24]

    # Test save_results_json
    test_result_data = {"scenario": "test", "data": {"years": [2025, 2026], "values": [100,110]}}
    save_results_json(test_result_data, "temp_results_dir", "my_test_scenario")

    # Cleanup dummy file
    # temp_excel_path.unlink(missing_ok=True)
    # Path("temp_results_dir/my_test_scenario.json").unlink(missing_ok=True)
    # Path("temp_results_dir").rmdir()
    logger.info("data_utils.py example run complete.")
