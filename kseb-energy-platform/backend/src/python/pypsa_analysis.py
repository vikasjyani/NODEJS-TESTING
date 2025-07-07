import sys
import json
import argparse
import logging
import traceback
from pathlib import Path
import pandas as pd
# import numpy as np # If needed for specific calculations
from typing import Dict, Any, List, Optional, Union

# Assuming shared utils are in a 'shared' directory sibling to this script
try:
    from shared import data_utils, validation, pypsa_utils # pypsa_utils will be created
except ImportError:
    # Fallback for direct execution
    current_dir = Path(__file__).resolve().parent
    shared_dir = current_dir / "shared"
    if not shared_dir.exists(): shared_dir = current_dir.parent / "shared" # Try parent's sibling
    if shared_dir.exists():
        sys.path.insert(0, str(shared_dir.parent))
        from shared import data_utils, validation, pypsa_utils
    else: # Minimal dummy for parsing
        class data_utils: pass
        class validation: pass
        class pypsa_utils: load_pypsa_network = lambda x: None # Dummy
        logging.warning("Could not import shared_utils for pypsa_analysis.py. Using dummies.")


# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# --- PyPSA Network Analyzer ---
class PyPSANetworkAnalyzer:
    def __init__(self, network_path: Union[str, Path]):
        self.network_path = Path(network_path)
        self.network = None # Loaded PyPSA Network object

        # Import PyPSA dynamically
        try:
            global pypsa
            import pypsa
        except ImportError:
            logger.error("CRITICAL: PyPSA library not found. This module requires PyPSA.")
            raise # Stop if PyPSA is missing

        if not self.network_path.exists():
            err_msg = f"Network file not found: {self.network_path}"
            logger.error(err_msg)
            raise FileNotFoundError(err_msg)

        logger.info(f"PyPSANetworkAnalyzer initialized for network: {self.network_path}")

    def _load_network_if_needed(self):
        """Loads the PyPSA network if not already loaded."""
        if self.network is None:
            self.network = pypsa_utils.load_pypsa_network(self.network_path)
            if self.network is None: # load_pypsa_network should log its own errors
                raise ConnectionError(f"Failed to load PyPSA network from {self.network_path}")
            logger.info(f"Successfully loaded network from {self.network_path}")

    def get_dispatch_data(self, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None, resolution: str = 'H') -> Dict[str, Any]:
        """Extracts generation dispatch data by carrier."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Network not loaded."}

        dispatch_data = {}
        if not self.network.generators_t.p.empty:
            gen_dispatch_df = self.network.generators_t.p.copy()

            # Filter by date range if provided
            if start_date_str: gen_dispatch_df = gen_dispatch_df[gen_dispatch_df.index >= pd.to_datetime(start_date_str)]
            if end_date_str: gen_dispatch_df = gen_dispatch_df[gen_dispatch_df.index <= pd.to_datetime(end_date_str)]

            # Resample if resolution is not hourly (e.g., 'D' for daily, 'M' for monthly sum)
            if resolution.upper() != 'H' and resolution.upper() != 'HOURLY':
                try:
                    gen_dispatch_df = gen_dispatch_df.resample(resolution).sum() # Sum for energy
                except Exception as e_resample:
                    logger.warning(f"Could not resample dispatch data to '{resolution}': {e_resample}. Returning hourly.")

            # Aggregate by carrier
            dispatch_by_carrier = {}
            for gen_name in gen_dispatch_df.columns:
                if gen_name not in self.network.generators.index: continue # Skip if generator somehow not in static data
                carrier = self.network.generators.loc[gen_name, 'carrier']
                if carrier not in dispatch_by_carrier:
                    dispatch_by_carrier[carrier] = gen_dispatch_df[gen_name]
                else:
                    dispatch_by_carrier[carrier] += gen_dispatch_df[gen_name]

            dispatch_data["generation_by_carrier_mwh"] = {
                # Convert Timestamps to ISO strings for JSON
                carrier: series.map(lambda x: round(x,3)).reset_index().rename(columns={'index':'timestamp', carrier:'value'}).to_dict(orient='records')
                for carrier, series in dispatch_by_carrier.items()
            }
            dispatch_data["total_generation_mwh"] = gen_dispatch_df.sum(axis=1).map(lambda x: round(x,3)).reset_index().rename(columns={'index':'timestamp', 0:'value'}).to_dict(orient='records')
        else:
            dispatch_data["generation_by_carrier_mwh"] = {}
            dispatch_data["total_generation_mwh"] = []
            logger.warning("No generator dispatch data (network.generators_t.p) found in the network.")

        return dispatch_data

    def get_capacity_data(self) -> Dict[str, Any]:
        """Extracts installed/optimal capacities by carrier."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Network not loaded."}

        capacity_data = {}
        # Generator capacities (p_nom_opt if available, else p_nom)
        cap_col = 'p_nom_opt' if 'p_nom_opt' in self.network.generators.columns else 'p_nom'
        if not self.network.generators.empty and cap_col in self.network.generators.columns:
            gen_capacity = self.network.generators.groupby('carrier')[cap_col].sum().map(lambda x: round(x,2))
            capacity_data["generation_capacity_mw"] = gen_capacity.to_dict()
        else:
            capacity_data["generation_capacity_mw"] = {}
            logger.warning("No generator capacity data found.")

        # Storage capacities (energy capacity: store_nom_opt or store_nom)
        store_cap_col = 'e_nom_opt' if 'e_nom_opt' in self.network.storage_units.columns else 'e_nom'
        if not self.network.storage_units.empty and store_cap_col in self.network.storage_units.columns:
            storage_energy_capacity = self.network.storage_units.groupby('carrier')[store_cap_col].sum().map(lambda x: round(x,2))
            capacity_data["storage_energy_capacity_mwh"] = storage_energy_capacity.to_dict()
        else:
            capacity_data["storage_energy_capacity_mwh"] = {}

        # Storage power capacities
        store_power_cap_col = 'p_nom_opt' if 'p_nom_opt' in self.network.storage_units.columns else 'p_nom'
        if not self.network.storage_units.empty and store_power_cap_col in self.network.storage_units.columns:
            storage_power_capacity = self.network.storage_units.groupby('carrier')[store_power_cap_col].sum().map(lambda x: round(x,2))
            capacity_data["storage_power_capacity_mw"] = storage_power_capacity.to_dict()
        else:
            capacity_data["storage_power_capacity_mw"] = {}


        return capacity_data

    def get_storage_data(self, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, Any]:
        """Extracts storage unit state of charge and dispatch."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Network not loaded."}

        storage_results = {}
        if not self.network.storage_units.empty and hasattr(self.network, 'storage_units_t'):
            soc_df = self.network.storage_units_t.state_of_charge.copy()
            dispatch_df = self.network.storage_units_t.p.copy()

            if start_date_str:
                soc_df = soc_df[soc_df.index >= pd.to_datetime(start_date_str)]
                dispatch_df = dispatch_df[dispatch_df.index >= pd.to_datetime(start_date_str)]
            if end_date_str:
                soc_df = soc_df[soc_df.index <= pd.to_datetime(end_date_str)]
                dispatch_df = dispatch_df[dispatch_df.index <= pd.to_datetime(end_date_str)]

            storage_results["state_of_charge_mwh"] = {
                # Convert Timestamps to ISO strings for JSON
                name: series.map(lambda x: round(x,3)).reset_index().rename(columns={'index':'timestamp', name:'value'}).to_dict(orient='records')
                for name, series in soc_df.items()
            }
            storage_results["dispatch_mw"] = {
                name: series.map(lambda x: round(x,3)).reset_index().rename(columns={'index':'timestamp', name:'value'}).to_dict(orient='records')
                for name, series in dispatch_df.items()
            }
        else:
            storage_results["state_of_charge_mwh"] = {}
            storage_results["dispatch_mw"] = {}
            logger.warning("No storage unit time series data found.")
        return storage_results

    def get_emissions_data(self) -> Dict[str, Any]:
        """Calculates CO2 emissions by carrier and total."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Network not loaded."}

        emissions_by_carrier = {}
        total_emissions = 0

        if not self.network.generators.empty and 'co2_emissions' in self.network.generators.columns and \
           hasattr(self.network, 'generators_t') and not self.network.generators_t.p.empty:

            for gen_name, gen_props in self.network.generators.iterrows():
                carrier = gen_props['carrier']
                # Use specific CO2 emission factor (e.g., tCO2/MWh_thermal) or general one
                # This assumes co2_emissions is a per-MWh_electric factor.
                # If it's per-MWh_thermal, efficiency needs to be used.
                # PyPSA-Eur often defines `co2_intensity` on carriers or uses `environmental_impact` component.
                # For simplicity, assuming `co2_emissions` attribute on generator is tCO2/MWh_el
                emission_factor = gen_props.get('co2_emissions', 0) # tCO2/MWh_el

                if emission_factor > 0 and gen_name in self.network.generators_t.p.columns:
                    generation_mwh = self.network.generators_t.p[gen_name].sum()
                    gen_emissions = generation_mwh * emission_factor

                    emissions_by_carrier[carrier] = emissions_by_carrier.get(carrier, 0) + gen_emissions
                    total_emissions += gen_emissions
        else:
            logger.warning("Cannot calculate emissions: Missing generator data, 'co2_emissions' column, or dispatch results.")

        return {
            "emissions_by_carrier_tonnes_co2": {k:round(v,2) for k,v in emissions_by_carrier.items()},
            "total_emissions_tonnes_co2": round(total_emissions,2)
        }

    def get_network_info(self) -> Dict[str, Any]:
        """Provides general information about the network."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Network not loaded."}

        info = {
            "name": self.network.name or Path(self.network_path).stem,
            "snapshots": {
                "count": len(self.network.snapshots),
                "first": self.network.snapshots[0].isoformat() if len(self.network.snapshots) > 0 else None,
                "last": self.network.snapshots[-1].isoformat() if len(self.network.snapshots) > 0 else None,
                "freq": pd.infer_freq(self.network.snapshots) if len(self.network.snapshots) > 1 else None,
            },
            "components": {
                "buses": len(self.network.buses),
                "generators": len(self.network.generators),
                "loads": len(self.network.loads),
                "lines": len(self.network.lines),
                "transformers": len(self.network.transformers),
                "storage_units": len(self.network.storage_units),
                "links": len(self.network.links),
            },
            "objective_value": float(self.network.objective) if hasattr(self.network, 'objective') and pd.notnull(self.network.objective) else None,
            "investment_periods": self.network.investment_periods.tolist() if hasattr(self.network, 'investment_periods') else None,
        }
        return info

    def compare_networks_summary(self, other_network_paths: List[str], metrics: List[str]) -> Dict[str, Any]:
        """Compares this network with other networks based on specified metrics."""
        self._load_network_if_needed()
        if self.network is None: return {"error": "Base network for comparison not loaded."}

        comparison_data = []

        # Add current network to list for comparison
        all_paths_to_compare = [str(self.network_path)] + other_network_paths

        for net_path_str in all_paths_to_compare:
            net_path = Path(net_path_str)
            analyzer_other = PyPSANetworkAnalyzer(net_path) # Create new analyzer for each
            try:
                analyzer_other._load_network_if_needed() # Load it
                if analyzer_other.network is None:
                    comparison_data.append({"network": net_path.stem, "error": "Failed to load"})
                    continue

                current_net_summary = {"network": net_path.stem}
                # Extract requested metrics
                if "cost" in metrics: current_net_summary["total_cost"] = float(analyzer_other.network.objective) if hasattr(analyzer_other.network, 'objective') else None
                if "emissions" in metrics: current_net_summary["total_emissions_tco2"] = analyzer_other.get_emissions_data().get("total_emissions_tonnes_co2")

                if "renewable_share" in metrics and not analyzer_other.network.generators.empty and \
                   hasattr(analyzer_other.network, 'generators_t') and not analyzer_other.network.generators_t.p.empty:
                    total_gen = analyzer_other.network.generators_t.p.sum().sum()
                    renewable_carriers = ['solar', 'wind', 'hydro'] # Define or get from config
                    renewable_gen = analyzer_other.network.generators_t.p[
                        analyzer_other.network.generators[analyzer_other.network.generators.carrier.isin(renewable_carriers)].index
                    ].sum().sum()
                    current_net_summary["renewable_share_percent"] = (renewable_gen / total_gen * 100) if total_gen > 0 else 0

                # Add more metrics as needed from other get_... methods
                comparison_data.append(current_net_summary)

            except Exception as e_comp:
                logger.error(f"Error processing network {net_path} for comparison: {e_comp}")
                comparison_data.append({"network": net_path.stem, "error": str(e_comp)})

        return {"comparison_results": comparison_data}


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="KSEB PyPSA Network Analysis Module")
    parser.add_argument('--network', type=str, required=True, help="Path to the PyPSA network NetCDF file (.nc).")
    parser.add_argument('--analysis', type=str, required=True,
                        choices=['dispatch', 'capacity', 'storage', 'emissions', 'info', 'compare'],
                        help="Type of analysis to perform.")

    # Optional arguments for specific analyses
    parser.add_argument('--start-date', type=str, help="Start date for time-series data (YYYY-MM-DD).")
    parser.add_argument('--end-date', type=str, help="End date for time-series data (YYYY-MM-DD).")
    parser.add_argument('--resolution', type=str, default='H', help="Time resolution for dispatch/storage (e.g., H, D, M).")

    # For 'compare' analysis type
    parser.add_argument('--compare-paths', type=str, help="JSON string of a list of other network file paths to compare against the main --network.")
    parser.add_argument('--metrics', type=str, default='["cost", "emissions", "renewable_share"]',
                        help="JSON string of a list of metrics for comparison (e.g., ['cost', 'emissions']).")

    args = parser.parse_args()
    output_result = {}

    try:
        analyzer = PyPSANetworkAnalyzer(args.network)

        if args.analysis == 'dispatch':
            output_result = analyzer.get_dispatch_data(args.start_date, args.end_date, args.resolution)
        elif args.analysis == 'capacity':
            output_result = analyzer.get_capacity_data()
        elif args.analysis == 'storage':
            output_result = analyzer.get_storage_data(args.start_date, args.end_date)
        elif args.analysis == 'emissions':
            output_result = analyzer.get_emissions_data()
        elif args.analysis == 'info':
            output_result = analyzer.get_network_info()
        elif args.analysis == 'compare':
            if not args.compare_paths:
                raise ValueError("--compare-paths (JSON list of network paths) is required for 'compare' analysis.")
            other_network_paths_list = json.loads(args.compare_paths)
            metrics_list = json.loads(args.metrics)
            if not isinstance(other_network_paths_list, list) or not isinstance(metrics_list, list):
                raise ValueError("--compare-paths and --metrics must be JSON lists.")
            output_result = analyzer.compare_networks_summary(other_network_paths_list, metrics_list)
        else:
            # Should not happen due to choices in argparse
            raise ValueError(f"Unknown analysis type: {args.analysis}")

    except FileNotFoundError as e_fnf:
        logger.error(f"File Not Found Error: {str(e_fnf)}")
        output_result = {"success": False, "error": str(e_fnf)}
        sys.exit(1)
    except ImportError as e_imp:
        logger.critical(f"Import Error (likely PyPSA): {str(e_imp)}", exc_info=True)
        output_result = {"success": False, "error": f"Python environment error: {str(e_imp)}"}
        sys.exit(1)
    except json.JSONDecodeError as e_json: # For --compare-paths or --metrics
        logger.error(f"JSON Decode Error for arguments: {e_json.msg}", exc_info=True)
        output_result = {"success": False, "error": f"Invalid JSON in arguments: {e_json.msg}"}
        sys.exit(1)
    except Exception as e_main:
        logger.error(f"Unhandled Exception in PyPSA Analysis: {str(e_main)}", exc_info=True)
        output_result = {"success": False, "error": str(e_main), "traceback": traceback.format_exc()}
        sys.exit(1)
    finally:
        # Add success flag to result before printing
        if "error" not in output_result:
            output_result["success"] = True
        print(json.dumps(output_result, default=str))

if __name__ == "__main__":
    main()
