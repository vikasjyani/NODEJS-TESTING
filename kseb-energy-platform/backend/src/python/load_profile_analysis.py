import sys
import json
import argparse
import logging
import traceback
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union

# Assuming shared utils are in a 'shared' directory sibling to this script
try:
    from shared import data_utils, validation # Assuming these exist from previous chunks
except ImportError:
    # Fallback for direct execution
    current_dir = Path(__file__).resolve().parent
    shared_dir = current_dir / "shared"
    if not shared_dir.exists(): shared_dir = current_dir.parent / "shared"
    if shared_dir.exists():
        sys.path.insert(0, str(shared_dir.parent))
        from shared import data_utils, validation
    else: # Minimal dummy for parsing
        class data_utils: load_excel_sheet=lambda:None; clean_timeseries_data=lambda:None; save_results_json=lambda:None
        class validation: validate_config_keys=lambda:[]

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Profile Analysis Engine ---
class ProfileAnalyzer:
    def __init__(self):
        logger.info("ProfileAnalyzer initialized.")

    def _load_profile_data_from_file(self, file_path: Union[str, Path]) -> Optional[Dict[int, pd.DataFrame]]:
        """Loads profile data (all years) from the saved JSON file."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Profile data file not found: {file_path}")
            return None
        try:
            with open(file_path, 'r') as f:
                profile_package = json.load(f) # This is the full package saved by generator

            yearly_dataframes = {}
            # The data is stored under "data" key, then year keys, then list of records
            for year_str, records in profile_package.get("data", {}).items():
                df = pd.DataFrame(records)
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df = df.set_index('datetime')
                if 'load' in df.columns:
                     df['load'] = pd.to_numeric(df['load'], errors='coerce')
                yearly_dataframes[int(year_str)] = df

            if not yearly_dataframes:
                logger.warning(f"No data found within the 'data' key of profile file: {file_path}")
                return None

            return yearly_dataframes
        except Exception as e:
            logger.error(f"Error loading or parsing profile data file {file_path}: {e}")
            return None

    def _calculate_single_profile_metrics(self, profile_data_all_years: Dict[int, pd.DataFrame], analysis_type: str) -> Dict[str, Any]:
        """Calculates metrics for a single profile based on analysis type."""
        metrics = {"analysis_type": analysis_type, "yearly_metrics": {}, "overall_metrics": {}}
        all_loads_combined = []

        for year, df_year in profile_data_all_years.items():
            if 'load' not in df_year.columns or df_year['load'].isnull().all():
                logger.warning(f"No valid 'load' data for year {year} in profile.")
                continue

            load_series = df_year['load'].dropna()
            all_loads_combined.extend(load_series.tolist())

            year_metrics = {
                "peak_mw": float(load_series.max()),
                "min_mw": float(load_series.min()),
                "avg_mw": float(load_series.mean()),
                "total_gwh": float(load_series.sum() / 1000), # Assuming hourly MW
                "load_factor": float(load_series.mean() / load_series.max()) if load_series.max() > 0 else 0,
                "hours_at_peak_range": float((load_series >= 0.9 * load_series.max()).sum()), # Hours >= 90% of peak
            }
            # Add more specific metrics based on analysis_type
            if analysis_type == "seasonal_decomposition": # Placeholder for actual decomposition
                year_metrics["seasonal_peak_factor"] = float(load_series.quantile(0.95) / load_series.mean()) if load_series.mean() > 0 else 0

            metrics["yearly_metrics"][year] = year_metrics

        if all_loads_combined:
            all_loads_array = np.array(all_loads_combined)
            metrics["overall_metrics"] = {
                "overall_peak_mw": float(all_loads_array.max()),
                "overall_avg_mw": float(all_loads_array.mean()),
                "overall_total_gwh": float(all_loads_array.sum() / 1000),
            }
        return metrics

    def analyze_profile(self, profile_path: str, analysis_type: str) -> Dict[str, Any]:
        """Analyzes a single load profile."""
        logger.info(f"Analyzing profile at {profile_path} for type: {analysis_type}")

        profile_data_all_years = self._load_profile_data_from_file(profile_path)
        if not profile_data_all_years:
            return {"error": f"Could not load profile data from {profile_path}."}

        # Based on analysis_type, perform different calculations
        if analysis_type == "overview":
            analysis_result = self._calculate_single_profile_metrics(profile_data_all_years, analysis_type)
        elif analysis_type == "seasonal": # Example
            # Perform seasonal decomposition or analysis
            analysis_result = self._calculate_single_profile_metrics(profile_data_all_years, "seasonal_decomposition") # Placeholder
            analysis_result["details"] = "Seasonal analysis details would go here (e.g., monthly peaks, seasonal factors)."
        else:
            logger.warning(f"Unsupported analysis type '{analysis_type}'. Performing overview.")
            analysis_result = self._calculate_single_profile_metrics(profile_data_all_years, "overview")
            analysis_result["message"] = f"Analysis type '{analysis_type}' not fully implemented, showing overview."

        return {"profile_path_analyzed": profile_path, **analysis_result}


    def compare_profiles(self, profile_paths: List[str], metrics_to_compare: Optional[List[str]] = None) -> Dict[str, Any]:
        """Compares multiple load profiles based on specified metrics."""
        logger.info(f"Comparing {len(profile_paths)} profiles. Metrics: {metrics_to_compare or 'default'}")

        comparison_results = {"profiles_compared": [], "comparison_summary": {}}
        all_profile_metrics = []

        for i, p_path_str in enumerate(profile_paths):
            profile_name = Path(p_path_str).stem # Use filename (without .json) as name
            profile_data = self._load_profile_data_from_file(p_path_str)
            if not profile_data:
                logger.warning(f"Skipping profile {p_path_str} in comparison due to load error.")
                comparison_results["profiles_compared"].append({"name": profile_name, "error": "Load error"})
                continue

            # Get basic overview metrics for comparison
            metrics = self._calculate_single_profile_metrics(profile_data, "overview")
            comparison_results["profiles_compared"].append({"name": profile_name, **metrics})
            all_profile_metrics.append({"name": profile_name, **metrics})

        if not all_profile_metrics:
            return {"error": "No profiles could be loaded for comparison."}

        # Generate a summary table or comparative stats (example)
        # This is highly dependent on what kind of comparison is useful.
        # For now, just list the key metrics for each.
        # If specific metrics_to_compare are given, select those.
        default_compare_keys = ["peak_mw", "total_gwh", "load_factor"]

        summary_table = []
        for profile_comp_data in all_profile_metrics:
            row = {"profile_name": profile_comp_data["name"]}
            # Extract overall or a specific year's data for comparison
            # For simplicity, let's use overall if available, else first year.
            data_source_for_summary = profile_comp_data.get("overall_metrics", {})
            if not data_source_for_summary and profile_comp_data.get("yearly_metrics"):
                first_year_key = next(iter(profile_comp_data["yearly_metrics"]), None)
                if first_year_key:
                    data_source_for_summary = profile_comp_data["yearly_metrics"][first_year_key]

            for key in metrics_to_compare or default_compare_keys:
                row[key] = data_source_for_summary.get(key, None)
            summary_table.append(row)

        comparison_results["comparison_summary"]["table"] = summary_table
        # Could add charts data here, e.g., comparing yearly peak demands across profiles

        return comparison_results

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="KSEB Load Profile Analysis Module")
    # Option 1: Analyze a single profile
    parser.add_argument('--profile-id', type=str, help="ID of the profile to analyze (used with --profile-path).")
    parser.add_argument('--profile-path', type=str, help="Path to the saved profile JSON file to analyze.")
    parser.add_argument('--analysis-type', type=str, default="overview", help="Type of analysis (e.g., 'overview', 'seasonal').")

    # Option 2: Compare multiple profiles
    parser.add_argument('--compare-paths', type=str, help="JSON string of a list of profile file paths to compare.")
    parser.add_argument('--metrics', type=str, help="JSON string of a list of metrics to include in comparison summary.")

    args = parser.parse_args()
    output_result = {}
    analyzer = ProfileAnalyzer()

    try:
        if args.compare_paths:
            profile_paths_to_compare = json.loads(args.compare_paths)
            if not isinstance(profile_paths_to_compare, list) or not all(isinstance(p, str) for p in profile_paths_to_compare):
                raise ValueError("--compare-paths must be a JSON list of strings.")

            metrics_list = json.loads(args.metrics) if args.metrics else None
            if metrics_list and (not isinstance(metrics_list, list) or not all(isinstance(m, str) for m in metrics_list)):
                 raise ValueError("--metrics must be a JSON list of strings.")

            output_result = analyzer.compare_profiles(profile_paths_to_compare, metrics_list)

        elif args.profile_path: # Single profile analysis
            # profile_id is mostly for context/logging if provided with path
            output_result = analyzer.analyze_profile(args.profile_path, args.analysis_type)
            if args.profile_id: output_result["profile_id_context"] = args.profile_id

        else:
            parser.print_help()
            output_result = {"error": "No valid operation specified (e.g., --profile-path or --compare-paths)."}
            sys.exit(1)

    except json.JSONDecodeError as e_json:
        logger.error(f"JSON Decode Error: {e_json.msg}", exc_info=True)
        output_result = {"success": False, "error": f"Invalid JSON argument: {e_json.msg}"}
        sys.exit(1)
    except Exception as e_main:
        logger.error(f"Unhandled Exception in Load Profile Analysis: {str(e_main)}", exc_info=True)
        output_result = {"success": False, "error": str(e_main), "traceback": traceback.format_exc()}
        sys.exit(1)
    finally:
        print(json.dumps(output_result, default=str)) # default=str for datetime, numpy types

if __name__ == "__main__":
    main()
