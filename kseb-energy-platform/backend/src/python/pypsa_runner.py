import sys
import json
import argparse
import logging
import traceback
import uuid
from pathlib import Path
import pandas as pd
# Ensure numpy is imported if used, e.g. for specific data manipulations
# import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

# Assuming shared utils are in a 'shared' directory sibling to this script
try:
    from shared import data_utils, validation # If these exist and are relevant
except ImportError:
    # Fallback for direct execution or if shared utils are not directly applicable here
    # Minimal dummy for parsing, actual shared utils might be needed for real operations
    class data_utils: save_results_json=lambda:None
    class validation: validate_config_keys=lambda:[]
    logging.warning("Could not import shared_utils for pypsa_runner.py. Using dummies.")


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- PyPSA Progress Reporter ---
class PyPSAProgressReporter:
    def __init__(self, job_id_nodejs: str, pypsa_job_id_python: str):
        self.job_id_nodejs = job_id_nodejs
        self.pypsa_job_id_python = pypsa_job_id_python
        self.current_progress = 0

    def report(self, progress: float, current_step: str, status_message: str, details: Optional[Dict[str, Any]] = None):
        payload = {
            "jobId": self.job_id_nodejs,
            "pythonJobId": self.pypsa_job_id_python, # Python's internal ID for this PyPSA job
            "progress": round(min(100, max(0, progress)), 2),
            "step": current_step, # Consistent with frontend: 'step' for current phase name
            "status": status_message, # More detailed human-readable status
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        print(f"PROGRESS:{json.dumps(payload)}", flush=True)
        logger.debug(f"Reported PyPSA progress: {progress:.2f}% - Step: {current_step} - Status: {status_message}")

# --- PyPSA Runner ---
class PyPSARunner:
    def __init__(self, config: Dict[str, Any], job_id_nodejs: Optional[str] = None):
        self.config = config
        self.pypsa_job_id_python = config.get("scenario_name", f"pypsa_run_{str(uuid.uuid4())[:8]}")
        self.reporter = PyPSAProgressReporter(job_id_nodejs or f"job_{self.pypsa_job_id_python}", self.pypsa_job_id_python)

        self.base_input_dir = Path("inputs") # e.g., for PyPSA network templates
        self.base_results_dir = Path("results") / "pypsa" # Main output dir for PyPSA results
        self.scenario_results_dir = self.base_results_dir / self.pypsa_job_id_python # Specific dir for this run
        self.scenario_results_dir.mkdir(parents=True, exist_ok=True)

        self.network = None # Will hold the PyPSA Network object

        # Import PyPSA dynamically to catch ImportError early if not installed
        try:
            global pypsa
            import pypsa
            logger.info(f"PyPSA version {pypsa.__version__} loaded.")
        except ImportError:
            logger.error("CRITICAL: PyPSA library not found. Please install PyPSA.")
            # This error should ideally be caught by test_environment.py,
            # but good to have a check here too.
            raise # Re-raise to stop execution if PyPSA is missing

        logger.info(f"PyPSARunner initialized for scenario: {self.pypsa_job_id_python}")

    def _validate_config(self) -> List[str]:
        required = ["scenario_name", "base_year", "investment_mode"]
        optional = [
            "input_file", "snapshot_selection", "generator_clustering",
            "unit_commitment", "monthly_constraints", "battery_constraints",
            "solver_options", "target_year", "timeout" # target_year for multi-horizon
        ]
        errors = validation.validate_config_keys(self.config, required, optional)

        # Add more PyPSA specific validations
        solver_opts = self.config.get("solver_options", {})
        if solver_opts.get("solver") and not isinstance(solver_opts["solver"], str):
            errors.append("solver_options.solver must be a string.")
        # ... other solver option checks

        return errors

    def _build_network_from_template(self):
        """Builds or loads a PyPSA network, e.g., from an Excel template or existing NetCDF."""
        self.reporter.report(5, "Network Building", "Loading network components.")
        # This is where you'd implement logic to:
        # 1. Create an empty pypsa.Network()
        # 2. Populate it from an Excel template (e.g., buses, lines, generators, loads, storage)
        #    - self.network.import_components_from_dataframe(...)
        #    - self.network.import_series_from_dataframe(...)
        # 3. Or load from an existing NetCDF file if provided as a base.

        # For this placeholder, we create a very simple network.
        # In a real scenario, this would parse self.config.get("input_file", "default_template.xlsx")
        self.network = pypsa.Network()
        self.network.set_snapshots(pd.date_range(f"{self.config['base_year']}-01-01", f"{self.config['base_year']}-01-02", freq="H", inclusive="left")) # 24 hours

        self.network.add("Bus", "Bus1", v_nom=220)
        self.network.add("Load", "Load1", bus="Bus1", p_set=pd.Series([10,12,11,13,15,20,22,25,23,20,18,16,15,14,15,17,19,23,24,22,20,18,15,12], index=self.network.snapshots))
        self.network.add("Generator", "Gen1_Gas", bus="Bus1", carrier="gas", p_nom=50, marginal_cost=50, capital_cost=10000)
        self.network.add("Generator", "Gen2_Solar", bus="Bus1", carrier="solar", p_nom_extendable=True, capital_cost=80000,
                         p_max_pu=pd.Series([0,0,0,0,0,0.1,0.3,0.5,0.6,0.7,0.75,0.8,0.75,0.7,0.6,0.4,0.1,0,0,0,0,0,0,0], index=self.network.snapshots))

        logger.info("Placeholder network built.")
        self.reporter.report(15, "Network Building", "Basic network components added.")


    def _configure_optimization_problem(self):
        """Configures LOPF/OPF specific settings based on self.config."""
        self.reporter.report(20, "Optimization Setup", "Applying optimization settings.")
        # Example: Set global CO2 limits, enable unit commitment if specified, etc.
        # self.network.add("GlobalConstraint", "co2_limit", sense="<=", constant=1e6, type="co2_emissions")

        if self.config.get("unit_commitment"):
            logger.info("Unit commitment constraints would be applied here (if PyPSA-Linopy supports it directly or via extensions).")
            # PyPSA-Eur often handles this with specific component definitions or custom constraints.
            # For basic PyPSA, this might involve setting min_up_time, min_down_time, start_up_cost etc. on generators.

        logger.info("Optimization problem configured (placeholder).")
        self.reporter.report(25, "Optimization Setup", "Settings applied.")


    def _run_pypsa_lopf(self) -> Dict[str, Any]:
        """Executes the Linear Optimal Power Flow (LOPF)."""
        self.reporter.report(30, "Solver Execution", "Starting LOPF solver.")
        solver_options = self.config.get("solver_options", {})
        solver_name = solver_options.get("solver", "glpk") # Default to GLPK or HiGHS if available

        # PyPSA's solve_opts for the solver
        pypsa_solve_opts = {}
        if "time_limit" in solver_options: pypsa_solve_opts['solver_options'] = {'timelimit': str(solver_options['time_limit'])} # Example for CBC/GLPK
        if "optimality_gap" in solver_options:
            if 'solver_options' not in pypsa_solve_opts: pypsa_solve_opts['solver_options'] = {}
            pypsa_solve_opts['solver_options']['mipgap'] = str(solver_options['optimality_gap']) # Example

        logger.info(f"Running LOPF with solver: {solver_name}, options: {pypsa_solve_opts}")

        try:
            # The progress_reporter inside PyPSA's LOPF is for solver iterations,
            # which is hard to pipe to our reporter directly without modifying PyPSA.
            # We report broader steps.
            self.network.lopf(solver_name=solver_name, **pypsa_solve_opts)

            status = self.network.objective_status
            condition = self.network.termination_condition
            objective_value = self.network.objective

            logger.info(f"LOPF completed. Status: {status}, Condition: {condition}, Objective: {objective_value:.2f}")
            self.reporter.report(80, "Solver Execution", f"Solver finished. Status: {status}", {"objective": objective_value})

            return {
                "status": status,
                "termination_condition": condition,
                "objective_value": objective_value
            }
        except Exception as e:
            logger.error(f"Error during PyPSA LOPF execution: {e}", exc_info=True)
            self.reporter.report(80, "Solver Execution", "Solver failed.", {"error": str(e)})
            raise # Re-raise to be caught by the main execution block

    def _extract_and_save_results(self, lopf_result: Dict[str,Any]) -> Dict[str, Any]:
        """Extracts key results and saves the network and summary."""
        self.reporter.report(85, "Results Processing", "Extracting key results.")

        # --- Result Extraction (examples) ---
        summary_results = {
            "objective_value": lopf_result.get("objective_value"),
            "solver_status": lopf_result.get("status"),
            "termination_condition": lopf_result.get("termination_condition"),
            "total_generation_mwh": {}, # by carrier
            "total_capacity_mw": {}, # by carrier (p_nom_opt)
            "total_cost": float(lopf_result.get("objective_value", 0)), # Assuming objective is cost
        }

        # Generator capacities and generation
        if not self.network.generators.empty:
            for carrier in self.network.generators.carrier.unique():
                gens_carrier = self.network.generators[self.network.generators.carrier == carrier]
                summary_results["total_capacity_mw"][carrier] = float(gens_carrier.p_nom_opt.sum()) if 'p_nom_opt' in gens_carrier else float(gens_carrier.p_nom.sum())
                if not self.network.generators_t.p.empty:
                     summary_results["total_generation_mwh"][carrier] = float(self.network.generators_t.p[gens_carrier.index].sum().sum())

        # Save network to NetCDF
        network_filename = f"{self.pypsa_job_id_python}_network.nc"
        network_path = self.scenario_results_dir / network_filename
        try:
            self.network.export_to_netcdf(network_path)
            logger.info(f"Network saved to: {network_path}")
        except Exception as e:
            logger.error(f"Failed to save network NetCDF: {e}")
            # This might not be a fatal error for returning summary.

        # Save summary results to JSON
        summary_filename = f"{self.pypsa_job_id_python}_summary.json"
        summary_path = self.scenario_results_dir / summary_filename
        data_utils.save_results_json(summary_results, self.scenario_results_dir, summary_filename.replace(".json",""))

        self.reporter.report(95, "Results Processing", "Results extracted and saved.")

        # Return information needed by Node.js (including paths to files)
        return {
            "scenario_name": self.pypsa_job_id_python,
            "objective_value": summary_results["total_cost"],
            "solver_status": summary_results["solver_status"],
            "network_path": str(network_path.resolve()),
            "summary_path": str(summary_path.resolve()),
            "summary_data": summary_results # Send summary back directly
        }

    def run_optimization_workflow(self) -> Dict[str, Any]:
        """Main workflow for a PyPSA optimization run."""
        self.reporter.report(0, "Initialization", "Validating PyPSA configuration.")
        config_errors = self._validate_config()
        if config_errors:
            self.reporter.report(100, "Error", "Configuration validation failed.", {"errors": config_errors})
            return {"success": False, "error": "Configuration errors.", "details": config_errors}

        self._build_network_from_template()
        self._configure_optimization_problem()

        lopf_solve_result = self._run_pypsa_lopf() # This can raise an exception

        final_results_summary = self._extract_and_save_results(lopf_solve_result)

        self.reporter.report(100, "Completed", "PyPSA optimization workflow finished.")
        return {"success": True, **final_results_summary}


def extract_results_from_netcdf(network_file_path: str) -> Dict[str, Any]:
    """Loads a PyPSA network from NetCDF and extracts a summary of results."""
    logger.info(f"Extracting results from NetCDF: {network_file_path}")
    try:
        global pypsa # Ensure pypsa is available
        import pypsa
    except ImportError:
        return {"success": False, "error": "PyPSA library not found for extraction."}

    if not Path(network_file_path).exists():
        return {"success": False, "error": f"Network file not found: {network_file_path}"}

    try:
        network = pypsa.Network(network_file_path)

        # Re-use parts of _extract_and_save_results logic or a dedicated extraction function
        # For simplicity, a brief extraction:
        results = {
            "objective_value": float(network.objective) if hasattr(network, 'objective') else None,
            "snapshot_count": len(network.snapshots),
            "bus_count": len(network.buses),
            "generator_count": len(network.generators),
            "generator_capacity_by_carrier_mw": {},
            "generator_dispatch_by_carrier_mwh": {},
            # Add more as needed by frontend for display without re-running LOPF
        }
        if not network.generators.empty:
            results["generator_capacity_by_carrier_mw"] = network.generators.groupby('carrier')['p_nom_opt' if 'p_nom_opt' in network.generators else 'p_nom'].sum().to_dict()
            if hasattr(network, 'generators_t') and 'p' in network.generators_t.p.columns:
                 results["generator_dispatch_by_carrier_mwh"] = network.generators_t.p.sum().groupby(network.generators.carrier).sum().to_dict()


        logger.info("Results extracted successfully from NetCDF.")
        return {"success": True, "data": results}

    except Exception as e:
        logger.error(f"Error extracting results from {network_file_path}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="KSEB PyPSA Optimization Runner Module")
    parser.add_argument('--config', type=str, help="JSON string of the PyPSA optimization configuration.")
    parser.add_argument('--extract', type=str, help="Path to a PyPSA network NetCDF file to extract results from.")
    parser.add_argument('--job-id', type=str, help="Optional Node.js Job ID for progress tracking.")

    args = parser.parse_args()
    output_result = {}

    try:
        if args.config:
            config_data = json.loads(args.config)
            runner = PyPSARunner(config_data, job_id_nodejs=args.job_id)
            output_result = runner.run_optimization_workflow()
        elif args.extract:
            output_result = extract_results_from_netcdf(args.extract)
        else:
            parser.print_help()
            output_result = {"success": False, "error": "No valid arguments (--config or --extract) provided."}
            sys.exit(1)

    except ImportError as e_imp: # Specifically catch PyPSA import error if it happens late
        logger.critical(f"Import Error (likely PyPSA or a dependency): {str(e_imp)}", exc_info=True)
        output_result = {"success": False, "error": f"Python environment error: {str(e_imp)}"}
        sys.exit(1)
    except json.JSONDecodeError as e_json:
        logger.error(f"JSON Decode Error: {e_json.msg}", exc_info=True)
        output_result = {"success": False, "error": f"Invalid JSON in --config: {e_json.msg}"}
        sys.exit(1)
    except Exception as e_main:
        logger.error(f"Unhandled Exception in PyPSA Runner: {str(e_main)}", exc_info=True)
        output_result = {"success": False, "error": str(e_main), "traceback": traceback.format_exc()}
        sys.exit(1)
    finally:
        print(json.dumps(output_result, default=str)) # default=str for Path objects, datetime, etc.

if __name__ == "__main__":
    main()
