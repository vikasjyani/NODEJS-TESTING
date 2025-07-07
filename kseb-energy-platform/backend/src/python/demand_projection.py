import sys
import json
import argparse
import logging
import traceback
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

# --- Logging Configuration ---
# Configured to output JSON for easier parsing by Node.js if needed,
# but also readable in console.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Ensure logs go to stdout
)
logger = logging.getLogger(__name__)

# --- Progress Reporter ---
class ProgressReporter:
    """Reports progress back to Node.js via specially formatted print statements."""
    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id if job_id else str(uuid.uuid4())

    def report(self, progress: float, current_task: str, status_message: str, details: Optional[Dict[str, Any]] = None):
        """
        Sends a progress update.
        Args:
            progress (float): Overall progress percentage (0-100).
            current_task (str): Name/ID of the current sub-task or sector being processed.
            status_message (str): A human-readable status message for the current_task.
            details (dict, optional): Additional structured data about the progress.
        """
        payload = {
            "jobId": self.job_id, # Include job_id for better tracking if multiple jobs run
            "progress": round(min(100, max(0, progress)), 2),
            "task": current_task, # Renamed from 'sector' to be more generic
            "status": status_message, # This is the main status string
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        # IMPORTANT: Prefix with "PROGRESS:" and print to STDOUT, then flush.
        print(f"PROGRESS:{json.dumps(payload)}", flush=True)
        logger.debug(f"Reported progress: {progress:.2f}% - Task: {current_task} - Status: {status_message}")

# --- Data Validation ---
class DataValidator:
    @staticmethod
    def validate_input_excel_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Validates the structure and basic quality of the input Excel file for demand projection."""
        file_path = Path(file_path)
        validation = {"is_valid": True, "errors": [], "warnings": [], "summary": {}}

        if not file_path.exists():
            validation["is_valid"] = False
            validation["errors"].append(f"Input file not found: {file_path}")
            return validation

        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            validation["summary"]["sheets_found"] = sheet_names

            required_sheets = ['residential', 'commercial', 'industrial'] # Example required sheets
            missing_sheets = [s for s in required_sheets if s not in sheet_names]
            if missing_sheets:
                validation["warnings"].append(f"Missing expected sheets: {', '.join(missing_sheets)}")

            for sheet_name in sheet_names:
                try:
                    df = excel_file.parse(sheet_name)
                    if df.empty:
                        validation["warnings"].append(f"Sheet '{sheet_name}' is empty.")
                        continue

                    # Example checks for common columns (adapt as needed)
                    expected_cols = ['year', 'demand']
                    if 'gdp' in df.columns.str.lower(): expected_cols.append('gdp') # case-insensitive check
                    if 'population' in df.columns.str.lower(): expected_cols.append('population')

                    actual_cols_lower = [str(col).lower() for col in df.columns]
                    missing_cols = [col for col in expected_cols if col.lower() not in actual_cols_lower]

                    if missing_cols:
                         validation["warnings"].append(f"Sheet '{sheet_name}': Missing columns: {', '.join(missing_cols)}. Found: {', '.join(df.columns)}")

                    if 'demand' in actual_cols_lower:
                        demand_col_name = df.columns[actual_cols_lower.index('demand')]
                        if df[demand_col_name].isnull().any():
                            validation["warnings"].append(f"Sheet '{sheet_name}': Column '{demand_col_name}' contains missing values.")
                        if not pd.api.types.is_numeric_dtype(df[demand_col_name]):
                             validation["errors"].append(f"Sheet '{sheet_name}': Column '{demand_col_name}' is not numeric.")
                             validation["is_valid"] = False


                except Exception as e_sheet:
                    validation["errors"].append(f"Error reading sheet '{sheet_name}': {str(e_sheet)}")
                    validation["is_valid"] = False

        except Exception as e_file:
            validation["is_valid"] = False
            validation["errors"].append(f"Error reading Excel file '{file_path}': {str(e_file)}")

        return validation

# --- Forecasting Engine ---
class ForecastingEngine:
    def __init__(self, config: Dict[str, Any], progress_reporter: ProgressReporter):
        self.config = config
        self.reporter = progress_reporter
        self.input_data_path = Path(config.get("input_file", "inputs/default_demand_data.xlsx")) # Default path
        self.target_year = config.get("target_year", datetime.now().year + 10)
        self.exclude_covid_years = config.get("exclude_covid_years", [2020, 2021, 2022]) if config.get("exclude_covid", True) else []

        logger.info(f"ForecastingEngine initialized for scenario: {config.get('scenario_name', 'N/A')}")
        logger.info(f"Target year: {self.target_year}, Input data: {self.input_data_path}")
        if self.exclude_covid_years:
            logger.info(f"Excluding COVID impact years: {self.exclude_covid_years}")


    def _load_and_prepare_data(self, sector_name: str) -> Optional[pd.DataFrame]:
        """Loads data for a specific sector and performs initial preparation."""
        try:
            # In a real app, input_data_path might be relative to a project root or configurable
            # For packaged Electron app, ensure this path is accessible.
            # The pythonProcessManager sets CWD to the python scripts' directory.
            actual_path = self.input_data_path
            if not actual_path.is_absolute():
                 # Assuming inputs/ is sibling to this script's dir, or specified in PYTHONPATH
                actual_path = Path.cwd() / self.input_data_path


            if not actual_path.exists():
                logger.error(f"Input data file not found for sector {sector_name} at {actual_path}")
                return None

            df = pd.read_excel(actual_path, sheet_name=sector_name)
            logger.info(f"Loaded data for sector {sector_name} from {actual_path}. Shape: {df.shape}")

            # Basic cleaning: ensure 'year' and 'demand' columns exist and are numeric
            df.columns = [str(col).lower() for col in df.columns] # Standardize column names
            if 'year' not in df.columns or 'demand' not in df.columns:
                logger.error(f"Sector {sector_name} data missing 'year' or 'demand' column.")
                return None

            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df['demand'] = pd.to_numeric(df['demand'], errors='coerce')
            df = df.dropna(subset=['year', 'demand'])

            # Exclude COVID years if specified
            if self.exclude_covid_years:
                df = df[~df['year'].isin(self.exclude_covid_years)]

            df = df.sort_values(by='year').reset_index(drop=True)
            logger.debug(f"Prepared data for sector {sector_name}:\n{df.head()}")
            return df

        except Exception as e:
            logger.error(f"Error loading/preparing data for sector {sector_name}: {e}")
            return None

    def _run_slr_model(self, df_sector: pd.DataFrame) -> Dict[str, Any]:
        """Performs Simple Linear Regression (Time Trend)."""
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score, mean_absolute_error

        if len(df_sector) < 2: return {"error": "Insufficient data for SLR."}

        X = df_sector[['year']]
        y = df_sector['demand']

        model = LinearRegression().fit(X, y)
        y_pred_train = model.predict(X)

        future_years = np.arange(df_sector['year'].max() + 1, self.target_year + 1).reshape(-1, 1)
        projections = model.predict(future_years)

        return {
            "model_type": "SLR",
            "r2": r2_score(y, y_pred_train),
            "mae": mean_absolute_error(y, y_pred_train),
            "coefficients": {"intercept": model.intercept_, "year_coeff": model.coef_[0]},
            "projections": {int(year): float(demand) for year, demand in zip(future_years.flatten(), projections)},
        }

    def _run_mlr_model(self, df_sector: pd.DataFrame, ind_vars: List[str]) -> Dict[str, Any]:
        """Performs Multiple Linear Regression."""
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score, mean_absolute_error

        valid_ind_vars = [var for var in ind_vars if var in df_sector.columns and pd.api.types.is_numeric_dtype(df_sector[var])]
        if not valid_ind_vars: return {"error": "No valid numeric independent variables found for MLR."}
        if len(df_sector) < len(valid_ind_vars) + 1: return {"error": "Insufficient data points for MLR."}

        df_clean = df_sector[['year', 'demand'] + valid_ind_vars].dropna()
        if len(df_clean) < len(valid_ind_vars) + 1: return {"error": "Insufficient non-null data for MLR."}

        X_train = df_clean[valid_ind_vars]
        y_train = df_clean['demand']

        model = LinearRegression().fit(X_train, y_train)
        y_pred_train = model.predict(X_train)

        # Projection (simplified: assumes linear growth for ind_vars)
        projections = {}
        last_known_year = df_clean['year'].max()
        last_known_vars = df_clean[df_clean['year'] == last_known_year][valid_ind_vars].iloc[0]

        for year_val in range(int(last_known_year) + 1, self.target_year + 1):
            # Simple extrapolation: (current_val / prev_val) * current_val or linear trend
            # This is highly simplified; real scenario needs ind_var projections
            projected_vars = last_known_vars * (1 + 0.02 * (year_val - last_known_year)) # Assume 2% growth for all ind_vars
            demand_forecast = model.predict(projected_vars.values.reshape(1,-1))[0]
            projections[year_val] = float(demand_forecast)

        return {
            "model_type": "MLR",
            "r2": r2_score(y_train, y_pred_train),
            "mae": mean_absolute_error(y_train, y_pred_train),
            "coefficients": {"intercept": model.intercept_, **dict(zip(valid_ind_vars, model.coef_))},
            "independent_variables_used": valid_ind_vars,
            "projections": projections,
        }

    # Placeholder for other models (WAM, TimeSeries) - these would be more complex
    def _run_wam_model(self, df_sector: pd.DataFrame, window: int = 5) -> Dict[str, Any]:
        if len(df_sector) < window: return {"error": "Insufficient data for WAM."}
        # Simplified: average of last 'window' years' growth rate applied forward
        recent_demands = df_sector['demand'].tail(window).values
        if len(recent_demands) < 2: return {"error": "Not enough recent demands for WAM growth."}
        avg_growth = np.mean(np.diff(recent_demands) / recent_demands[:-1]) # Average percentage growth

        last_demand = recent_demands[-1]
        last_year = df_sector['year'].max()
        projections = {}
        current_demand = last_demand
        for year_val in range(int(last_year) + 1, self.target_year + 1):
            current_demand *= (1 + avg_growth)
            projections[year_val] = float(current_demand)
        return {"model_type": "WAM", "avg_growth_rate": avg_growth, "projections": projections}

    def _run_timeseries_model(self, df_sector: pd.DataFrame) -> Dict[str, Any]:
        # Placeholder for ARIMA/Prophet. Requires statsmodels/prophet library.
        # This would involve fitting, e.g., an ARIMA model and forecasting.
        try:
            from statsmodels.tsa.arima.model import ARIMA # Example
            if len(df_sector) < 10: return {"error": "Insufficient data for TimeSeries (ARIMA example)."}

            model = ARIMA(df_sector['demand'], order=(1,1,1)) # Example order
            model_fit = model.fit()
            forecast_steps = self.target_year - df_sector['year'].max()
            forecast_result = model_fit.forecast(steps=forecast_steps)

            projections = {int(df_sector['year'].max() + i + 1): float(val) for i, val in enumerate(forecast_result)}
            return {"model_type": "TimeSeries (ARIMA)", "aic": model_fit.aic, "projections": projections}
        except ImportError:
            logger.warning("statsmodels library not found. TimeSeries model cannot run.")
            return {"error": "statsmodels library not found."}
        except Exception as e_ts:
            logger.error(f"TimeSeries model error: {e_ts}")
            return {"error": f"TimeSeries model failed: {str(e_ts)}"}


    def run_forecast_for_sector(self, sector_name: str, sector_config: Dict[str, Any]) -> Dict[str, Any]:
        """Runs configured forecasts for a single sector."""
        self.reporter.report(0, sector_name, "Loading data...")
        df_sector = self._load_and_prepare_data(sector_name)
        if df_sector is None or df_sector.empty:
            self.reporter.report(100, sector_name, "Failed to load data", {"error": "No data available or load error."})
            return {"error": f"No data for sector {sector_name} or error in loading."}

        sector_results = {"sector": sector_name, "models": {}}
        models_to_run = sector_config.get("models", ["SLR"]) # Default to SLR if none specified

        num_models = len(models_to_run)
        for i, model_type in enumerate(models_to_run):
            self.reporter.report(10 + (i/num_models)*80, sector_name, f"Running model: {model_type}")
            model_result = {}
            try:
                if model_type == "SLR":
                    model_result = self._run_slr_model(df_sector.copy())
                elif model_type == "MLR":
                    ind_vars = sector_config.get("independent_variables", ['gdp', 'population'])
                    model_result = self._run_mlr_model(df_sector.copy(), ind_vars)
                elif model_type == "WAM":
                    window = sector_config.get("wam_window", 5)
                    model_result = self._run_wam_model(df_sector.copy(), window)
                elif model_type == "TimeSeries": # Could be ARIMA, Prophet, etc.
                    model_result = self._run_timeseries_model(df_sector.copy())
                else:
                    model_result = {"error": f"Unsupported model type: {model_type}"}
            except Exception as e_model:
                logger.error(f"Error running model {model_type} for {sector_name}: {e_model}", exc_info=True)
                model_result = {"error": f"Failed during {model_type} execution: {str(e_model)}"}

            sector_results["models"][model_type] = model_result

        self.reporter.report(100, sector_name, "Sector forecast complete.")
        return sector_results

    def execute_full_forecast(self) -> Dict[str, Any]:
        """Executes forecasts for all configured sectors."""
        scenario_name = self.config.get("scenario_name", f"Forecast_{self.reporter.job_id}")
        self.reporter.report(0, "Overall", f"Starting forecast: {scenario_name}")

        all_sector_configs = self.config.get("sectors", {})
        if not all_sector_configs:
            self.reporter.report(100, "Overall", "Configuration error", {"error": "No sectors configured for forecast."})
            return {"error": "No sectors configured."}

        results = {"scenario_name": scenario_name, "target_year": self.target_year, "sectors": {}}
        total_sectors = len(all_sector_configs)

        for i, (sector_name, sector_config) in enumerate(all_sector_configs.items()):
            overall_progress = 5 + (i / total_sectors) * 90 # Allocate 90% of progress to sector processing
            self.reporter.report(overall_progress, "Overall", f"Processing sector: {sector_name} ({i+1}/{total_sectors})")

            sector_result = self.run_forecast_for_sector(sector_name, sector_config)
            results["sectors"][sector_name] = sector_result

        self.reporter.report(100, "Overall", "Forecast scenario complete.")
        logger.info(f"Forecast scenario {scenario_name} finished.")
        return results


# --- Helper Functions for CLI arguments ---
def get_sector_data_action(args_cli: argparse.Namespace) -> Dict[str, Any]:
    """Handles the --sector-data CLI action."""
    logger.info(f"Fetching data for sector: {args_cli.sector_data}")
    # This is a simplified version. Real version would use ForecastingEngine._load_and_prepare_data
    # and add more stats/info. For now, let's simulate.
    engine = ForecastingEngine({"input_file": args_cli.input_file or "inputs/default_demand_data.xlsx"}, ProgressReporter())
    df = engine._load_and_prepare_data(args_cli.sector_data)
    if df is not None:
        return {
            "sector": args_cli.sector_data,
            "sample_data": df.head().to_dict(orient='records'),
            "statistics": {"rows": len(df), "columns": df.columns.tolist(), "years": df['year'].unique().tolist()},
            "data_quality": {"score": 0.85, "issues": []} # Placeholder
        }
    return {"error": f"Could not load data for sector {args_cli.sector_data}"}


def get_correlation_action(args_cli: argparse.Namespace) -> Dict[str, Any]:
    """Handles the --correlation CLI action."""
    logger.info(f"Fetching correlation for sector: {args_cli.correlation}")
    engine = ForecastingEngine({"input_file": args_cli.input_file or "inputs/default_demand_data.xlsx"}, ProgressReporter())
    df = engine._load_and_prepare_data(args_cli.correlation)
    if df is not None:
        # Calculate correlation with 'demand'
        numeric_df = df.select_dtypes(include=np.number)
        if 'demand' not in numeric_df.columns:
            return {"error": "Numeric 'demand' column not found for correlation."}

        correlations = numeric_df.corr()['demand'].drop('demand', errors='ignore').fillna(0)
        corr_data = [{"variable": idx, "correlation": val, "abs_correlation": abs(val)} for idx, val in correlations.items()]
        corr_data.sort(key=lambda x: x["abs_correlation"], reverse=True)

        return {
            "sector": args_cli.correlation,
            "correlations": corr_data,
            "recommended_variables": [item['variable'] for item in corr_data if item['abs_correlation'] > 0.5] # Example threshold
        }
    return {"error": f"Could not load data for correlation analysis of sector {args_cli.correlation}"}

def validate_file_action(args_cli: argparse.Namespace) -> Dict[str, Any]:
    """Handles the --validate CLI action."""
    logger.info(f"Validating input file: {args_cli.validate}")
    return DataValidator.validate_input_excel_file(args_cli.validate)


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="KSEB Demand Projection Module")
    parser.add_argument('--config', type=str, help="JSON string of the forecast configuration.")
    parser.add_argument('--sector-data', type=str, help="Get sample data and stats for a specific sector.")
    parser.add_argument('--correlation', type=str, help="Get correlation data for variables in a sector relative to demand.")
    parser.add_argument('--validate', type=str, help="Path to an Excel input file to validate.")
    parser.add_argument('--input-file', type=str, help="Optional common input file path for actions like sector-data or correlation.")
    parser.add_argument('--job-id', type=str, help="Optional job ID for progress reporting continuity.")

    args = parser.parse_args()
    output_result = {}

    try:
        if args.config:
            config_data = json.loads(args.config)
            reporter = ProgressReporter(job_id=args.job_id) # Pass job_id if provided
            engine = ForecastingEngine(config_data, reporter)
            output_result = engine.execute_full_forecast()
        elif args.sector_data:
            output_result = get_sector_data_action(args)
        elif args.correlation:
            output_result = get_correlation_action(args)
        elif args.validate:
            output_result = validate_file_action(args)
        else:
            parser.print_help()
            output_result = {"error": "No valid arguments provided."}
            sys.exit(1)

    except json.JSONDecodeError as e_json:
        logger.error(f"JSON Decode Error: {e_json.msg} at line {e_json.lineno} col {e_json.colno}")
        output_result = {"success": False, "error": f"Invalid JSON in --config: {e_json.msg}"}
        sys.exit(1)
    except FileNotFoundError as e_fnf:
        logger.error(f"File Not Found Error: {str(e_fnf)}")
        output_result = {"success": False, "error": str(e_fnf)}
        sys.exit(1)
    except Exception as e_main:
        logger.error(f"Unhandled Exception: {str(e_main)}", exc_info=True)
        output_result = {"success": False, "error": str(e_main), "traceback": traceback.format_exc()}
        sys.exit(1)
    finally:
        # Ensure final result is printed as a single JSON line to STDOUT
        # All PROGRESS messages should have been flushed already.
        print(json.dumps(output_result, default=str)) # default=str for datetime, etc.

if __name__ == "__main__":
    main()
