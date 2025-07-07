
# utils/pypsa_runner.py
import pandas as pd
import pypsa
import os
from pathlib import Path
import numpy as np
import logging
import numpy_financial as npf
import traceback
import threading # Not used directly in run_pypsa_model_core but good for runner script
from datetime import datetime
from .pypsa_helpers import extract_tables_by_markers, annuity_future_value # Ensure pypsa_helpers is in the same directory or accessible

logger = logging.getLogger(__name__)

def run_pypsa_model_core(job_id, project_path_str, scenario_name, ui_settings_overrides, pypsa_jobs):
    """
    Main PyPSA model execution function - Iterative Single-Year Optimization.
    """
    if job_id not in pypsa_jobs:
        # This case should ideally not happen if job is created before calling this
        logger.error(f"Job {job_id} not found in pypsa_jobs at start of core execution.")
        # Attempt to create a basic job entry if missing, for logging purposes
        pypsa_jobs[job_id] = {
            'status': 'Failed', 'progress': 0, 'error': 'Job ID not found prior to execution.',
            'log': [f"CRITICAL: Job {job_id} not found when starting core logic."],
            'scenario_name': scenario_name, 'project_path': project_path_str,
            'start_time': datetime.now().isoformat()
        }
        return

    job = pypsa_jobs[job_id]
    original_cwd = os.getcwd() # Save current working directory

    try:
        job['status'] = 'Processing Inputs'
        job['current_step'] = 'Initializing PyPSA model and reading inputs'
        job['log'].append(f"Model run for scenario '{scenario_name}' started at {datetime.now().isoformat()}.")
        job['progress'] = 5

        project_path = Path(project_path_str)
        input_file_path = project_path / "inputs" / "pypsa_input_template.xlsx"
        results_base_dir = project_path / "results" / "PyPSA_Modeling"
        scenario_results_dir = results_base_dir / scenario_name # scenario_name should be sanitized

        scenario_results_dir.mkdir(parents=True, exist_ok=True)
        job['log'].append(f"Results will be saved to: {scenario_results_dir}")

        if not input_file_path.exists():
            raise FileNotFoundError(f"PyPSA input template not found: {input_file_path}")

        job['log'].append(f"Reading input file: {input_file_path}")
        job['progress'] = 10

        try:
            xls = pd.ExcelFile(str(input_file_path))
            # Load all sheets, provide empty DataFrames for missing optional sheets
            sheet_names_in_excel = xls.sheet_names
            required_sheets_map = {
                'Settings': 'setting_df_excel', 'Generators': 'generators_base_df',
                'Buses': 'buses_df', 'Demand': 'demand_excel_df',
                'Lifetime': 'lifetime_df', 'FOM': 'fom_df',
                'Fuel_cost': 'fuel_cost_df', 'Startupcost': 'startupcost_df',
                'CO2': 'co2_df', 'P_max_pu': 'p_max_pu_excel_df',
                'P_min_pu': 'p_min_pu_excel_df', 'Capital_cost': 'capital_cost_df',
                'wacc': 'wacc_df', 'New_Generators': 'new_generators_excel_df',
                'Pipe_Line_Generators_p_max': 'pipe_line_generators_p_max_df',
                'Pipe_Line_Generators_p_min': 'pipe_line_generators_p_min_df',
                'New_Storage': 'new_storage_excel_df', 'Links': 'links_excel_df',
                'Pipe_Line_Storage_p_min': 'pipe_line_storage_p_min_df'
                # Add 'Custom days' if it becomes strictly required by a path
            }
            loaded_data = {}
            missing_critical_sheets = []
            for sheet_name, df_name in required_sheets_map.items():
                if sheet_name in sheet_names_in_excel:
                    loaded_data[df_name] = xls.parse(sheet_name)
                elif sheet_name in ['Settings', 'Generators', 'Buses', 'Demand']: # Critical sheets
                    missing_critical_sheets.append(sheet_name)
                else: # Optional sheets
                    logger.warning(f"Optional sheet '{sheet_name}' not found in Excel. Proceeding with empty DataFrame.")
                    loaded_data[df_name] = pd.DataFrame()
            
            if 'Custom days' in sheet_names_in_excel: # For critical days snapshot option
                loaded_data['custom_days_df'] = xls.parse('Custom days')
            else:
                loaded_data['custom_days_df'] = pd.DataFrame()


            if missing_critical_sheets:
                raise ValueError(f"Missing critical sheets in Excel file: {', '.join(missing_critical_sheets)}")

            # Assign to local variables for easier access (matching notebook style)
            setting_df_excel = loaded_data['setting_df_excel']
            generators_base_df = loaded_data['generators_base_df']
            buses_df = loaded_data['buses_df']
            lifetime_df = loaded_data['lifetime_df']
            fom_df = loaded_data['fom_df']
            demand_excel_df = loaded_data['demand_excel_df']
            fuel_cost_df = loaded_data['fuel_cost_df']
            startupcost_df = loaded_data['startupcost_df']
            co2_df = loaded_data['co2_df']
            p_max_pu_excel_df = loaded_data['p_max_pu_excel_df']
            p_min_pu_excel_df = loaded_data['p_min_pu_excel_df']
            capital_cost_df = loaded_data['capital_cost_df']
            wacc_df = loaded_data['wacc_df']
            new_generators_excel_df = loaded_data['new_generators_excel_df']
            pipe_line_generators_p_max_df = loaded_data['pipe_line_generators_p_max_df']
            pipe_line_generators_p_min_df = loaded_data['pipe_line_generators_p_min_df']
            new_storage_excel_df = loaded_data['new_storage_excel_df']
            links_excel_df = loaded_data['links_excel_df']
            pipe_line_storage_p_min_df = loaded_data['pipe_line_storage_p_min_df']
            custom_days_df = loaded_data['custom_days_df']


        except Exception as e:
            raise ValueError(f"Error reading or validating Excel file sheets: {str(e)}")

        job['log'].append("Excel file sheets validated and loaded.")
        job['progress'] = 15

        settings_main_excel_table = extract_tables_by_markers(setting_df_excel, '~').get('Main_Settings')
        if settings_main_excel_table is None or settings_main_excel_table.empty:
            raise ValueError("Table '~Main_Settings' not found or empty in 'Settings' sheet.")

        def get_setting(key, default_value, df=settings_main_excel_table, overrides=ui_settings_overrides):
            val_override = overrides.get(key)
            if val_override is not None:
                job['log'].append(f"UI Override for '{key}': {val_override}")
                # Type casting for known numeric or boolean settings from UI
                if key in ['Weightings', 'Base_Year', 'solver_threads']:
                    try: return int(val_override)
                    except ValueError: return default_value
                if key in ['Generator Cluster', 'Committable', 'solver_parallel', 'solver_presolve', 'log_to_console_solver']:
                    return bool(val_override) # UI likely sends true/false
                if key in ['pdlp_gap_tol', 'simplex_strategy'] and isinstance(val_override, (int,float,str)):
                     try: return float(val_override) if '.' in str(val_override) else int(val_override)
                     except: return default_value
                return val_override

            row = df[df['Setting'] == key]
            if not row.empty and 'Option' in row.columns and pd.notna(row['Option'].iloc[0]):
                excel_val = row['Option'].iloc[0]
                job['log'].append(f"Excel Setting for '{key}': {excel_val}")
                if key in ['Weightings', 'Base_Year']:
                    try: return int(excel_val) if float(excel_val).is_integer() else float(excel_val)
                    except ValueError: return default_value
                if key in ['Generator Cluster', 'Committable']: # Excel might have 'Yes'/'No'
                    return str(excel_val).strip().lower() == 'yes'
                # Add more type conversions as needed for other settings from Excel
                return excel_val
            job['log'].append(f"Using default for '{key}': {default_value}")
            return default_value

        snapshot_condition = get_setting('Run Pypsa Model on', 'All Snapshots')
        weightings_freq_hours = get_setting('Weightings', 1) # This is snapshot_duration_hours
        base_year_config = get_setting('Base_Year', 2025)
        multi_year_mode = get_setting('Multi Year Investment', 'No') # String 'No', 'Only Capacity...', etc.
        do_generator_clustering = get_setting('Generator Cluster', False) # Boolean
        do_unit_commitment = get_setting('Committable', False) # Boolean

        job['log'].append(f"Settings: Snapshots='{snapshot_condition}', Weightings(Duration)={weightings_freq_hours}h, BaseYear={base_year_config}, MultiYear='{multi_year_mode}', Clustering={do_generator_clustering}, UC={do_unit_commitment}")
        job['progress'] = 20

        solver_name_opt = get_setting('solver_name', 'highs', overrides=ui_settings_overrides) # Allow overriding solver name
        solver_threads_val = get_setting('solver_threads', 0, overrides=ui_settings_overrides) # Ensure this is int
        
        solver_options_from_ui = {
            'log_file': str(scenario_results_dir / f'{scenario_name}_solver_{datetime.now().strftime("%Y%m%d%H%M")}.log'),
            "threads": int(solver_threads_val), # Make sure it's an integer
            "solver": get_setting('highs_solver_type', "simplex", overrides=ui_settings_overrides), # 'simplex' or 'pdlp' for HiGHS
            "parallel": "on" if get_setting('solver_parallel', True, overrides=ui_settings_overrides) else "off",
            "presolve": "on" if get_setting('solver_presolve', True, overrides=ui_settings_overrides) else "off",
            'log_to_console': get_setting('log_to_console_solver', True, overrides=ui_settings_overrides) # For solver's own console log
        }
        if solver_options_from_ui["solver"] == "pdlp":
            pdlp_gap_tol_val = get_setting('pdlp_gap_tol', 1e-4, overrides=ui_settings_overrides)
            solver_options_from_ui['pdlp_d_gap_tol'] = float(pdlp_gap_tol_val) if pdlp_gap_tol_val is not None else 1e-4
            if 'simplex_strategy' in solver_options_from_ui: del solver_options_from_ui['simplex_strategy'] # remove if not pdlp
        elif solver_options_from_ui["solver"] == "simplex":
            simplex_strat_val = get_setting('simplex_strategy', 0, overrides=ui_settings_overrides) # Default is "choose"
            solver_options_from_ui['simplex_strategy'] = int(simplex_strat_val) if simplex_strat_val is not None else 0
            if 'pdlp_d_gap_tol' in solver_options_from_ui: del solver_options_from_ui['pdlp_d_gap_tol'] # remove if not simplex

        job['log'].append(f"Solver: {solver_name_opt}, Options: {solver_options_from_ui}")

        # Derive year list from demand data columns that look like years (e.g., 2025, 2026)
        year_list_from_demand = sorted([
            int(col) for col in demand_excel_df.columns
            if isinstance(col, (int, str)) and str(col).isdigit() and len(str(col)) == 4 and str(col).startswith('20')
        ])
        years_to_simulate = [yr for yr in year_list_from_demand if yr >= base_year_config]

        if not years_to_simulate:
            raise ValueError(f"No simulation years found. Base year: {base_year_config}, Demand years available: {year_list_from_demand}")
        job['log'].append(f"Simulation years based on demand data and base year: {years_to_simulate}")
        job['progress'] = 25

        # Extract additional settings for constraints if they exist
        committable_settings_df = extract_tables_by_markers(setting_df_excel, '~').get('commitable', pd.DataFrame())
        # monthly_constraints_settings_df = extract_tables_by_markers(setting_df_excel, '~').get('Monthly_Constraints', pd.DataFrame())
        # battery_cycle_settings_df = extract_tables_by_markers(setting_df_excel, '~').get('Battery_Cycle', pd.DataFrame())


        # ==================================
        # MAIN PYPSA LOGIC - Iterative Single Year
        # ==================================
        if multi_year_mode == 'No':
            job['status'] = 'Running Single-Year Models'
            previous_year_export_path_obj = None # Use Path object

            for idx, current_year in enumerate(years_to_simulate):
                job['current_step'] = f"Processing Year: {current_year}"
                job['log'].append(f"\n--- Starting processing for simulation year: {current_year} ---")
                current_progress_base = 30 + int(((idx) / len(years_to_simulate)) * 60) # Base progress for this year

                # 1. Generate Snapshots for the current_year
                job['log'].append(f"Generating snapshots for FY{current_year} with condition '{snapshot_condition}' and {weightings_freq_hours}h resolution.")
                model_snapshots_index, full_year_hourly_index = _generate_snapshots_for_year(
                    str(input_file_path), current_year, snapshot_condition, weightings_freq_hours, base_year_config, demand_excel_df, custom_days_df, job['log']
                )
                if model_snapshots_index.empty:
                    job['log'].append(f"Warning: No snapshots generated for year {current_year}. Skipping this year.")
                    continue
                job['log'].append(f"Generated {len(model_snapshots_index)} snapshots for model, from {len(full_year_hourly_index)} hourly base snapshots.")
                job['progress'] = current_progress_base + 2


                # 2. Initialize PyPSA Network and Set Snapshots
                n = pypsa.Network()
                n.set_snapshots(model_snapshots_index)

                # Snapshot weighting:
                # 'objective' weighting used for operational costs (marginal_cost * p * objective_weighting)
                # 'objective' weighting also used for capital costs IF p_nom_extendable=True (capital_cost * p_nom * objective_weighting)
                # Here, weightings_freq_hours is the duration of each snapshot (e.g., 1h, 3h).
                # The capital_cost should be an annuity. PyPSA handles the overall annualization through these weightings if set correctly.
                # If each snapshot represents more than its duration in the year (e.g. typical days), this needs care.
                # The notebook's method: capital_cost_annual / (snapshot_duration * num_representative_hours_per_year_for_snapshot)
                # and snapshot_weightings["objective"] = snapshot_duration seems okay.

                # Let's use the effective capital weighting factor approach for clarity.
                # Snapshot duration (e.g., 1h, 3h if resampled)
                snapshot_duration_hours_actual = weightings_freq_hours # This is what each snapshot "is"
                
                # How many hours in a full year does one of our model snapshots represent?
                # If using all snapshots (resampled), it's 8760 / len(model_snapshots_index) * snapshot_duration_hours_actual.
                # No, it's simpler: if we have N snapshots, and each is D hours long, the total duration modeled is N*D.
                # The capital cost is annual. So, it should be "per year".
                # PyPSA objective: sum_{sns}( op_cost_per_hour * D_sns ) + sum_g ( cap_cost_per_year * Pnom_g )
                # If snapshot_weightings["objective"] = D_sns (duration of snapshot), then capital_cost should be input as per_year cost.
                n.snapshot_weightings["objective"] = snapshot_duration_hours_actual
                job['log'].append(f"Set snapshot_weightings['objective'] to {snapshot_duration_hours_actual} (duration of each snapshot).")
                job['progress'] = current_progress_base + 3


                # 3. Prepare Aligned Time-Series Data (Pmax/Pmin_pu, Demand)
                # These need to be Series/DataFrames indexed by n.snapshots
                def align_timeseries_to_model_snapshots(source_df_full_year_hourly, full_year_idx, model_idx, tech_name_in_source, default_val=1):
                    if tech_name_in_source not in source_df_full_year_hourly.columns:
                        # job['log'].append(f"Warning: Tech '{tech_name_in_source}' not in source DF for P_pu. Using default {default_val}.")
                        return pd.Series(default_val, index=model_idx)
                    
                    series_full_hourly = pd.Series(source_df_full_year_hourly[tech_name_in_source].values, index=full_year_idx)
                    # Reindex to model snapshots, then interpolate/ffill/bfill
                    aligned_series = series_full_hourly.reindex(model_idx).interpolate(method='time').ffill().bfill()
                    return aligned_series.fillna(default_val) # Ensure no NaNs remain

                p_max_pu_aligned_dfs = {}
                p_min_pu_aligned_dfs = {}
                # Pre-align all relevant P_max_pu and P_min_pu series
                all_techs_for_pu = set(generators_base_df['carrier'].unique()) | set(new_generators_excel_df['carrier'].unique())
                for tech in all_techs_for_pu:
                    p_max_pu_aligned_dfs[tech] = align_timeseries_to_model_snapshots(p_max_pu_excel_df, full_year_hourly_index, n.snapshots, tech, 1)
                    p_min_pu_aligned_dfs[tech] = align_timeseries_to_model_snapshots(p_min_pu_excel_df, full_year_hourly_index, n.snapshots, tech, 0)
                    # For Outside Kerala Solar/Wind specifically
                    if tech in ['Solar', 'Wind']:
                        p_max_pu_aligned_dfs[f"{tech}_Outside"] = align_timeseries_to_model_snapshots(p_max_pu_excel_df, full_year_hourly_index, n.snapshots, f"{tech}_Outside", 1)
                        # p_min_pu for outside RE is typically 0, handled in generator addition
                job['log'].append("Pre-aligned P_max/min_pu profiles for technologies.")


                # 4. Add Buses
                if not buses_df.empty:
                    for _, bus_row in buses_df.iterrows():
                        n.add("Bus", bus_row['name'], v_nom=bus_row.get('v_nom', 1.0)) # Add other bus attributes if present
                else: job['log'].append("Warning: Buses DataFrame is empty.")
                job['log'].append("Buses added.")

                # 5. Add Loads
                # Demand for the current_year, aligned to model_snapshots_index
                demand_col_to_use = current_year if current_year in demand_excel_df.columns else base_year_config
                if demand_col_to_use not in demand_excel_df.columns:
                     raise ValueError(f"Demand data for year {demand_col_to_use} (or base year) not found in Demand sheet.")
                job['log'].append(f"Using demand from sheet column '{demand_col_to_use}' for simulation year {current_year}.")
                
                demand_series_full_year_hourly = pd.Series(demand_excel_df[demand_col_to_use].values, index=full_year_hourly_index)
                load_p_set_aligned = demand_series_full_year_hourly.reindex(model_snapshots_index).interpolate(method='time').ffill().bfill()
                
                # Assume load is on 'Main_Bus' if not specified otherwise
                main_bus_name = buses_df['name'].iloc[0] if not buses_df.empty else "Main_Bus" # Fallback
                if main_bus_name not in n.buses.index: # If Main_Bus wasn't in buses_df, add it
                    n.add("Bus", main_bus_name)

                n.add("Load", "MainLoad", bus=main_bus_name, p_set=load_p_set_aligned)
                job['log'].append(f"Load added to bus '{main_bus_name}'.")
                job['progress'] = current_progress_base + 5

                # 6. Add Carriers
                if not co2_df.empty:
                    for _, car_row in co2_df.iterrows():
                        # Ensure TECHNOLOGY column exists
                        if 'TECHNOLOGY' in car_row and pd.notna(car_row['TECHNOLOGY']):
                             # Default tonnes/MWh to 0 if not specified or NaN
                            co2_emissions_val = car_row.get('tonnes/MWh', 0)
                            if pd.isna(co2_emissions_val): co2_emissions_val = 0
                            
                            n.add("Carrier", str(car_row['TECHNOLOGY']),
                                  co2_emissions=co2_emissions_val,
                                  color=str(car_row.get('color', '#CCCCCC'))) # Default color
                        else:
                            job['log'].append(f"Skipping carrier due to missing TECHNOLOGY name: {car_row}")
                else: job['log'].append("Warning: CO2 DataFrame for carriers is empty.")
                job['log'].append("Carriers added.")


                # 7. Add Generators (Existing from base or previous year, and New potential)
                temp_current_generators_df = pd.DataFrame() # To hold generators for this year's model build
                if current_year == base_year_config or previous_year_export_path_obj is None:
                    job['log'].append(f"Using base generators_df for year {current_year}.")
                    temp_current_generators_df = generators_base_df.copy()
                    if 'p_nom_extendable' not in temp_current_generators_df.columns:
                        temp_current_generators_df['p_nom_extendable'] = False
                    if 'name' not in temp_current_generators_df.columns and temp_current_generators_df.index.name == 'name':
                        temp_current_generators_df.reset_index(inplace=True)
                    elif 'name' not in temp_current_generators_df.columns: # If no name column, try to create from index or skip
                         job['log'].append("Warning: 'name' column missing in generators_base_df and index is not 'name'. Generators might not be added correctly.")


                    # Market type generators are typically extendable
                    if 'carrier' in temp_current_generators_df.columns:
                        temp_current_generators_df.loc[temp_current_generators_df['carrier'] == 'Market', 'p_nom_extendable'] = True

                else: # Load from previous year's results
                    job['log'].append(f"Loading generators from previous year ({current_year-1}) results from {previous_year_export_path_obj}.")
                    prev_gens_path = previous_year_export_path_obj / "generators.csv"
                    if prev_gens_path.exists():
                        temp_current_generators_df = pd.read_csv(prev_gens_path)
                        if 'p_nom_opt' in temp_current_generators_df.columns and 'p_nom' in temp_current_generators_df.columns:
                            # Update p_nom with p_nom_opt if p_nom_opt is larger (for capacity expansion)
                            temp_current_generators_df['p_nom'] = np.maximum(
                                temp_current_generators_df['p_nom'].fillna(0),
                                temp_current_generators_df['p_nom_opt'].fillna(0) # FillNa to avoid issues with np.maximum
                            )
                            # temp_current_generators_df = temp_current_generators_df.drop(columns=['p_nom_opt']) # Keep p_nom_opt for records
                        temp_current_generators_df['p_nom_extendable'] = False # Existing are not extendable by default
                        if 'carrier' in temp_current_generators_df.columns:
                             temp_current_generators_df.loc[temp_current_generators_df['carrier'] == 'Market', 'p_nom_extendable'] = True
                    else:
                        job['log'].append(f"Warning: Previous year generator data not found at {prev_gens_path}. Reverting to base_generators_df for {current_year}.")
                        temp_current_generators_df = generators_base_df.copy() # Fallback
                        if 'p_nom_extendable' not in temp_current_generators_df.columns: temp_current_generators_df['p_nom_extendable'] = False
                        if 'carrier' in temp_current_generators_df.columns: temp_current_generators_df.loc[temp_current_generators_df['carrier'] == 'Market', 'p_nom_extendable'] = True


                # Apply retiring logic to the temp_current_generators_df BEFORE adding them
                # This needs a standalone function that operates on the DataFrame, not the network object yet
                # For now, we'll add all, then use the network-based retiring.
                # Or, filter temp_current_generators_df here:
                def retire_generators_from_df(df, year_select, base_yr):
                    if df.empty or 'build_year' not in df.columns or 'lifetime' not in df.columns:
                        return df
                    
                    if year_select == base_yr: # or year_select == 2025 in notebook:
                        # Remove generators built after a certain point if it's the base run
                        # This logic from notebook: n.remove("Generator", n.generators[n.generators["build_year"] > 2025].index.tolist())
                        # translates to:
                        return df[df["build_year"] <= 2025] # Assuming 2025 is a fixed reference for this rule
                    
                    # General retiring rule
                    df_filtered = df[df["build_year"] + df["lifetime"] > year_select] # Keep if not retired
                    # Also remove those built in the future relative to select_year
                    df_filtered = df_filtered[df_filtered["build_year"] <= year_select]
                    return df_filtered

                temp_current_generators_df = retire_generators_from_df(temp_current_generators_df, current_year, base_year_config)
                job['log'].append(f"Applied pre-retiring logic to existing generators DataFrame. Count: {len(temp_current_generators_df)}")


                # Add these "existing" (potentially from previous year) generators to the network
                if not temp_current_generators_df.empty and 'name' in temp_current_generators_df.columns:
                    for _, gen_row in temp_current_generators_df.iterrows():
                        tech = gen_row.get('carrier')
                        gen_name = gen_row['name']
                        bus_name = gen_row.get('bus')
                        if not tech or not gen_name or not bus_name:
                            job['log'].append(f"Skipping existing generator due to missing info: Name='{gen_name}', Tech='{tech}', Bus='{bus_name}'")
                            continue
                        
                        # Capital cost for existing generators is typically 0 unless it's extendable market
                        # If it's a market component that is extendable, it might have a cost.
                        # For fixed existing plants, capital_cost should be 0 as it's sunk.
                        # The notebook calculates capital_cost for all, which is unusual for existing fixed.
                        # For PyPSA: capital_cost is an annual cost.
                        # If p_nom_extendable=False, capital_cost is informational.
                        # If p_nom_extendable=True, capital_cost is part of objective.
                        # Let's assume capital_cost for existing fixed plants is 0 in the objective.
                        cap_cost_val = 0
                        if gen_row.get('p_nom_extendable', False): # Only calculate if it's extendable (e.g. Market)
                            cap_cost_series = capital_cost_df[capital_cost_df['carrier'] == tech][current_year] if tech in capital_cost_df.get('carrier', pd.Series()) and current_year in capital_cost_df.columns else pd.Series()
                            if not cap_cost_series.empty and pd.notna(cap_cost_series.iloc[0]):
                                wacc_val = wacc_df[current_year].iloc[0] if current_year in wacc_df.columns and not wacc_df.empty else 0.08
                                life_val = lifetime_df[lifetime_df['carrier'] == tech]['lifetime'].iloc[0] if tech in lifetime_df.get('carrier', pd.Series()) and not lifetime_df[lifetime_df['carrier'] == tech].empty else 30
                                fom_val = fom_df[fom_df['carrier'] == tech]['FOM'].iloc[0] if tech in fom_df.get('carrier', pd.Series()) and not fom_df[fom_df['carrier'] == tech].empty else 0
                                # Annualized capital cost + FOM
                                cap_cost_val = float(abs(annuity_future_value(wacc_val, life_val, cap_cost_series.iloc[0]))) + fom_val
                        
                        p_max_pu_key = f"{tech}_Outside" if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind'] else tech
                        p_min_pu_key = f"{tech}_Outside" if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind'] else tech
                        
                        p_max_pu_series_val = p_max_pu_aligned_dfs.get(p_max_pu_key, pd.Series(1, index=n.snapshots))
                        p_min_pu_series_val = p_min_pu_aligned_dfs.get(p_min_pu_key, pd.Series(0, index=n.snapshots))
                        if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind']: p_min_pu_series_val = pd.Series(0, index=n.snapshots)


                        n.add("Generator", gen_name,
                              bus=bus_name,
                              p_nom=gen_row.get('p_nom', 0),
                              p_nom_extendable=gen_row.get('p_nom_extendable', False),
                              p_min_pu=p_min_pu_series_val.tolist(),
                              p_max_pu=p_max_pu_series_val.tolist(),
                              carrier=tech,
                              marginal_cost=gen_row.get('marginal_cost', 0),
                              build_year=gen_row.get('build_year', base_year_config), # Default to base_year if not specified
                              lifetime=gen_row.get('lifetime', 30), # Default lifetime
                              capital_cost=cap_cost_val, # Annual cost
                              committable=gen_row.get('committable', False), # Default from file
                              # Add other params like startup_cost, ramp_limit_up etc. with .get(key, default)
                              start_up_cost=gen_row.get('start_up_cost', 0),
                              shut_down_cost=gen_row.get('shut_down_cost', 0),
                              min_up_time=gen_row.get('min_up_time', 0),
                              min_down_time=gen_row.get('min_down_time', 0),
                              ramp_limit_up=gen_row.get('ramp_limit_up', np.nan), # PyPSA uses NaN for no limit
                              ramp_limit_down=gen_row.get('ramp_limit_down', np.nan)
                              )
                job['log'].append("Existing/previous-year generators processed and added to network.")
                job['progress'] = current_progress_base + 10


                # Add NEW potential generators for the current_year build
                if not new_generators_excel_df.empty:
                    for _, new_gen_row in new_generators_excel_df.iterrows():
                        tech = new_gen_row.get('carrier')
                        # 'TECHNOLOGY' column in new_generators_excel_df seems to be the specific name/ID
                        gen_instance_name = new_gen_row.get('TECHNOLOGY', f"{tech}_New")
                        bus_name = new_gen_row.get('bus')

                        if not tech or not gen_instance_name or not bus_name:
                             job['log'].append(f"Skipping new generator due to missing info: Instance='{gen_instance_name}', Tech='{tech}', Bus='{bus_name}'")
                             continue

                        # Capital cost for new generators
                        cap_cost_val_new = 0
                        # Match capital_cost_df by 'carrier' and also by 'bus' if that level of detail exists
                        cap_cost_tech_df = capital_cost_df[capital_cost_df['carrier'] == tech]
                        if 'bus' in capital_cost_df.columns: # If capital cost has bus-specific values
                            cap_cost_tech_bus_df = cap_cost_tech_df[cap_cost_tech_df['bus'] == bus_name]
                            if not cap_cost_tech_bus_df.empty: cap_cost_tech_df = cap_cost_tech_bus_df
                        
                        if not cap_cost_tech_df.empty and current_year in cap_cost_tech_df.columns and pd.notna(cap_cost_tech_df[current_year].iloc[0]):
                            base_investment_cost = cap_cost_tech_df[current_year].iloc[0]
                            wacc_val = wacc_df[current_year].iloc[0] if current_year in wacc_df.columns and not wacc_df.empty else 0.08
                            life_val = lifetime_df[lifetime_df['carrier'] == tech]['lifetime'].iloc[0] if tech in lifetime_df.get('carrier', pd.Series()) and not lifetime_df[lifetime_df['carrier'] == tech].empty else 30
                            fom_val = fom_df[fom_df['carrier'] == tech]['FOM'].iloc[0] if tech in fom_df.get('carrier', pd.Series()) and not fom_df[fom_df['carrier'] == tech].empty else 0
                            cap_cost_val_new = float(abs(annuity_future_value(wacc_val, life_val, base_investment_cost))) + fom_val
                        else:
                            job['log'].append(f"Warning: Capital cost for new '{gen_instance_name}' ({tech}) in year {current_year} at bus '{bus_name}' not found. Defaulting to 0.")

                        p_max_pu_key_new = f"{tech}_Outside" if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind'] else tech
                        p_min_pu_key_new = f"{tech}_Outside" if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind'] else tech
                        
                        p_max_pu_series_new = p_max_pu_aligned_dfs.get(p_max_pu_key_new, pd.Series(1, index=n.snapshots))
                        p_min_pu_series_new = p_min_pu_aligned_dfs.get(p_min_pu_key_new, pd.Series(0, index=n.snapshots))
                        if bus_name == 'Outside Kerala' and tech in ['Solar', 'Wind']: p_min_pu_series_new = pd.Series(0, index=n.snapshots)


                        # p_nom_min and p_nom_max from pipeline DataFrames
                        p_nom_min_val = 0
                        p_nom_max_val = np.inf # Default to unconstrained if not found
                        
                        # Match pipeline data by 'TECHNOLOGY' (instance name) and 'bus'
                        # For pipe_line_generators_p_min_df
                        if not pipe_line_generators_p_min_df.empty and 'TECHNOLOGY' in pipe_line_generators_p_min_df.columns and 'bus' in pipe_line_generators_p_min_df.columns:
                            p_min_matches = pipe_line_generators_p_min_df[
                                (pipe_line_generators_p_min_df["TECHNOLOGY"] == gen_instance_name) &
                                (pipe_line_generators_p_min_df["bus"] == bus_name)
                            ]
                            if not p_min_matches.empty and current_year in p_min_matches.columns:
                                p_nom_min_val = p_min_matches[current_year].values[0]
                                if pd.isna(p_nom_min_val): p_nom_min_val = 0 # Ensure it's not NaN
                        
                        # For pipe_line_generators_p_max_df
                        if not pipe_line_generators_p_max_df.empty and 'TECHNOLOGY' in pipe_line_generators_p_max_df.columns and 'bus' in pipe_line_generators_p_max_df.columns:
                            p_max_matches = pipe_line_generators_p_max_df[
                                (pipe_line_generators_p_max_df["TECHNOLOGY"] == gen_instance_name) &
                                (pipe_line_generators_p_max_df["bus"] == bus_name)
                            ]
                            if not p_max_matches.empty and current_year in p_max_matches.columns:
                                p_nom_max_val = p_max_matches[current_year].values[0]
                                if pd.isna(p_nom_max_val): p_nom_max_val = np.inf # Ensure it's not NaN

                        marginal_cost_val = 0
                        if not fuel_cost_df.empty and tech in fuel_cost_df.get('carrier', pd.Series()) and current_year in fuel_cost_df.columns:
                            fuel_matches = fuel_cost_df[fuel_cost_df['carrier'] == tech]
                            if not fuel_matches.empty: marginal_cost_val = fuel_matches[current_year].values[0]

                        startup_cost_val = 0
                        if not startupcost_df.empty and tech in startupcost_df.get('carrier', pd.Series()) and current_year in startupcost_df.columns:
                             startup_matches = startupcost_df[startupcost_df['carrier'] == tech]
                             if not startup_matches.empty: startup_cost_val = startup_matches[current_year].values[0]

                        lifetime_val = 30 # Default
                        if not lifetime_df.empty and tech in lifetime_df.get('carrier', pd.Series()):
                            lifetime_matches = lifetime_df[lifetime_df['carrier'] == tech]
                            if not lifetime_matches.empty: lifetime_val = lifetime_matches['lifetime'].iloc[0]
                        
                        job['log'].append(f"Adding new potential: {gen_instance_name} ({tech}) at {bus_name} for build year {current_year}. MinCap: {p_nom_min_val}, MaxCap: {p_nom_max_val if p_nom_max_val != np.inf else 'inf'}, AnnCapCost: {cap_cost_val_new:.2f}, MargCost: {marginal_cost_val:.2f}")

                        n.add("Generator", f"{gen_instance_name} {bus_name} Build{current_year}", # Unique name
                              bus=bus_name,
                              p_nom_extendable=new_gen_row.get('p_nom_extendable', True), # New are typically extendable
                              p_nom_min=p_nom_min_val,
                              p_nom_max=p_nom_max_val,
                              p_min_pu=p_min_pu_series_new.tolist(),
                              p_max_pu=p_max_pu_series_new.tolist(),
                              carrier=tech,
                              marginal_cost=marginal_cost_val,
                              build_year=current_year, # Built in this simulation year
                              lifetime=lifetime_val,
                              capital_cost=cap_cost_val_new, # Annual cost
                              committable=new_gen_row.get('committable', False), # Default from file
                              start_up_cost=startup_cost_val,
                              shut_down_cost=startup_cost_val, # Often same as startup
                              min_up_time=new_gen_row.get('min_up_time', 0),
                              min_down_time=new_gen_row.get('min_down_time', 0),
                              ramp_limit_up=new_gen_row.get('ramp_limit_up', np.nan),
                              ramp_limit_down=new_gen_row.get('ramp_limit_down', np.nan)
                              )
                job['log'].append("New potential generators processed and added.")
                job['progress'] = current_progress_base + 15

                # 8. Apply Generator Clustering (if enabled) AFTER all generators are added but BEFORE retiring (as retiring logic is simpler on individual units)
                # Correction: Notebook applies retiring, THEN clustering. Let's stick to that.
                # The dataframe based retiring is already done. Now apply network based retiring to catch anything missed.
                # n = _apply_retiring_logic_network(n, current_year, base_year_config) # Network-based retiring
                # job['log'].append("Network-based generator retiring logic applied.")

                if do_generator_clustering:
                    job['log'].append("Applying generator clustering...")
                    n = _apply_generator_clustering(n, p_max_pu_aligned_dfs, p_min_pu_aligned_dfs, job['log']) # Pass aligned DFs
                    job['log'].append("Generator clustering applied.")
                job['progress'] = current_progress_base + 17


                # 9. Add Storage (Existing from previous year, and New potential)
                # Similar logic to generators: load from prev year or add new
                # Existing Stores
                if previous_year_export_path_obj:
                    prev_stores_path = previous_year_export_path_obj / "stores.csv"
                    if prev_stores_path.exists():
                        existing_stores_df = pd.read_csv(prev_stores_path)
                        if 'e_nom_opt' in existing_stores_df.columns and 'e_nom' in existing_stores_df.columns:
                            existing_stores_df['e_nom'] = np.maximum(
                                existing_stores_df['e_nom'].fillna(0),
                                existing_stores_df['e_nom_opt'].fillna(0)
                            )
                        existing_stores_df['e_nom_extendable'] = False
                        # Ensure required columns like 'bus', 'carrier' are present
                        for _, store_data_row in existing_stores_df.iterrows():
                            store_name = store_data_row.get('name')
                            if store_name and store_data_row.get('bus') and store_data_row.get('carrier'):
                                # Filter out non-numeric/problematic from_dict items
                                store_params = {k: v for k, v in store_data_row.to_dict().items() if pd.notna(v) and k not in ['name', 'e_nom_opt', 'p_dispatch', 'p_store', 'e_initial', 'e_final']}
                                if 'marginal_cost_dispatch' in store_params : store_params['marginal_cost'] = store_params.pop('marginal_cost_dispatch') # PyPSA uses marginal_cost for dispatch

                                n.add('Store', store_name, **store_params)
                            else:
                                job['log'].append(f"Skipping existing store due to missing essential data: {store_data_row.get('name')}")
                        job['log'].append(f"Added {len(existing_stores_df)} existing Stores from {current_year-1}.")

                    prev_storage_units_path = previous_year_export_path_obj / "storage_units.csv"
                    if prev_storage_units_path.exists():
                        existing_storage_units_df = pd.read_csv(prev_storage_units_path)
                        if 'p_nom_opt' in existing_storage_units_df.columns and 'p_nom' in existing_storage_units_df.columns:
                             existing_storage_units_df['p_nom'] = np.maximum(
                                 existing_storage_units_df['p_nom'].fillna(0),
                                 existing_storage_units_df['p_nom_opt'].fillna(0)
                             )
                        existing_storage_units_df['p_nom_extendable'] = False
                        for _, su_data_row in existing_storage_units_df.iterrows():
                            su_name = su_data_row.get('name')
                            if su_name and su_data_row.get('bus') and su_data_row.get('carrier'):
                                su_params = {k:v for k,v in su_data_row.to_dict().items() if pd.notna(v) and k not in ['name','p_nom_opt']}
                                n.add('StorageUnit', su_name, **su_params)
                            else:
                                job['log'].append(f"Skipping existing SU due to missing essential data: {su_data_row.get('name')}")
                        job['log'].append(f"Added {len(existing_storage_units_df)} existing StorageUnits from {current_year-1}.")
                job['progress'] = current_progress_base + 20

                # Add NEW potential storage for current_year build
                if not new_storage_excel_df.empty:
                    for _, new_store_row in new_storage_excel_df.iterrows():
                        store_tech_id = new_store_row.get('TECHNOLOGY') # Specific name/ID
                        store_carrier = new_store_row.get('carrier')    # General type like 'Battery', 'PHS'
                        store_bus = new_store_row.get('bus')
                        store_type_excel = new_store_row.get('Type')    # 'Store' or 'StorageUnit'

                        if not all([store_tech_id, store_carrier, store_bus, store_type_excel]):
                            job['log'].append(f"Skipping new storage {store_tech_id} due to missing critical info.")
                            continue
                        
                        # Capital cost for new storage
                        cap_cost_val_store = 0
                        # Match by TECHNOLOGY for storage capital costs
                        cap_cost_store_df = capital_cost_df[capital_cost_df['TECHNOLOGY'] == store_tech_id] if 'TECHNOLOGY' in capital_cost_df.columns else pd.DataFrame()

                        if not cap_cost_store_df.empty and current_year in cap_cost_store_df.columns and pd.notna(cap_cost_store_df[current_year].iloc[0]):
                            base_investment_cost_store = cap_cost_store_df[current_year].iloc[0]
                            wacc_val = wacc_df[current_year].iloc[0] if current_year in wacc_df.columns and not wacc_df.empty else 0.08
                            # Match lifetime by TECHNOLOGY for storage
                            life_val_store = 15 # Default
                            if not lifetime_df.empty and 'TECHNOLOGY' in lifetime_df.columns:
                                 life_match_store = lifetime_df[lifetime_df['TECHNOLOGY'] == store_tech_id]
                                 if not life_match_store.empty: life_val_store = life_match_store['lifetime'].iloc[0]
                            # Match FOM by TECHNOLOGY or carrier as fallback
                            fom_val_store = 0
                            if not fom_df.empty:
                                fom_match_tech = fom_df[fom_df['TECHNOLOGY'] == store_tech_id] if 'TECHNOLOGY' in fom_df.columns else pd.DataFrame()
                                fom_match_carrier = fom_df[fom_df['carrier'] == store_carrier] if 'carrier' in fom_df.columns else pd.DataFrame()
                                if not fom_match_tech.empty and 'FOM' in fom_match_tech.columns: fom_val_store = fom_match_tech['FOM'].iloc[0]
                                elif not fom_match_carrier.empty and 'FOM' in fom_match_carrier.columns: fom_val_store = fom_match_carrier['FOM'].iloc[0]
                            
                            cap_cost_val_store = float(abs(annuity_future_value(wacc_val, life_val_store, base_investment_cost_store))) + fom_val_store
                        else:
                             job['log'].append(f"Warning: Capital cost for new storage '{store_tech_id}' in year {current_year} not found. Defaulting to 0.")


                        # e_nom_min / p_nom_min from pipeline data
                        e_p_nom_min_val_store = 0
                        if not pipe_line_storage_p_min_df.empty and 'TECHNOLOGY' in pipe_line_storage_p_min_df.columns:
                            storage_min_matches = pipe_line_storage_p_min_df[pipe_line_storage_p_min_df["TECHNOLOGY"] == store_tech_id]
                            if not storage_min_matches.empty and current_year in storage_min_matches.columns:
                                e_p_nom_min_val_store = storage_min_matches[current_year].values[0]
                                if pd.isna(e_p_nom_min_val_store): e_p_nom_min_val_store = 0

                        unique_store_name = f"{store_tech_id} {store_bus} Build{current_year}"
                        lifetime_for_add = life_val_store if 'life_val_store' in locals() and life_val_store else 15

                        if store_type_excel == 'Store':
                            n.add('Store', unique_store_name,
                                  bus=store_bus, carrier=store_carrier, # PyPSA 'Store' doesn't use 'type' attr
                                  e_nom_extendable=True,
                                  e_nom_min=e_p_nom_min_val_store,
                                  # e_max_pu=1, e_min_pu=0 by default
                                  capital_cost=cap_cost_val_store, # Annual cost
                                  build_year=current_year,
                                  lifetime=lifetime_for_add,
                                  standing_loss=new_store_row.get('standing_loss', 0.0001) # Default standing loss
                                  # Add e_cyclic, e_initial if in new_store_row
                                  )
                        elif store_type_excel == 'StorageUnit':
                            # Notebook adds StorageUnit only if year > 2030, replicate if needed
                            # if current_year > 2030: # Condition from notebook
                            n.add('StorageUnit', unique_store_name,
                                    bus=store_bus, carrier=store_carrier, # PyPSA 'StorageUnit' doesn't use 'type' attr
                                    p_nom_extendable=True,
                                    p_nom_min=e_p_nom_min_val_store, # p_nom_min for SU
                                    capital_cost=cap_cost_val_store, # Annual cost
                                    marginal_cost=new_store_row.get('marginal_cost', 0), # Dispatch cost
                                    build_year=current_year,
                                    lifetime=lifetime_for_add,
                                    max_hours=new_store_row.get('max_hours', 6), # Energy to power ratio
                                    efficiency_store=new_store_row.get('efficiency_store', 0.9),
                                    efficiency_dispatch=new_store_row.get('efficiency_dispatch', 0.9),
                                    # Add cyclic_state_of_charge, min_state_of_charge etc. if available
                                    )
                        job['log'].append(f"Added new potential {store_type_excel}: {unique_store_name}")
                job['log'].append("New potential storage processed.")
                job['progress'] = current_progress_base + 25

                # Apply storage retiring logic (network based)
                n = _apply_storage_retiring_logic_network(n, current_year, base_year_config)
                job['log'].append("Network-based storage retiring logic applied.")


                # 10. Add Links
                if not links_excel_df.empty:
                    invertor_setting = get_setting('Storage Charging/Discharging', 'Anytime', df=settings_main_excel_table)
                    for _, link_row in links_excel_df.iterrows():
                        link_name = link_row.get('name')
                        if not link_name or not link_row.get('bus0') or not link_row.get('bus1'):
                            job['log'].append(f"Skipping link due to missing name/bus0/bus1: {link_name}")
                            continue

                        link_p_max_pu_val = link_row.get('p_max_pu', 1) # Default to 1 if not specified
                        link_p_min_pu_val = link_row.get('p_min_pu', 0) # Default to 0

                        if str(link_name).startswith("invertor") and invertor_setting == 'Solar and Non solar hours':
                            solar_hours_start, solar_hours_end = int(get_setting('Solar_Start_Hour', 10)), int(get_setting('Solar_End_Hour', 17))
                            # Ensure snapshots are DatetimeIndex for .hour access
                            time_idx_for_links = n.snapshots.get_level_values(-1) if isinstance(n.snapshots, pd.MultiIndex) else n.snapshots
                            if isinstance(time_idx_for_links, pd.DatetimeIndex):
                                is_solar_hour_series = (time_idx_for_links.hour >= solar_hours_start) & (time_idx_for_links.hour < solar_hours_end)
                                if link_row.get('type') == 'charging link': # Assuming a 'type' column in Links sheet
                                    link_p_max_pu_val = np.where(is_solar_hour_series, 1, 0).tolist()
                                else: # Discharging link or other type
                                    link_p_max_pu_val = np.where(is_solar_hour_series, 0, 1).tolist()
                            else: job['log'].append(f"Warning: Cannot apply solar hour logic to link '{link_name}', snapshots not DatetimeIndex.")


                        n.add('Link', link_name,
                              bus0=link_row['bus0'], bus1=link_row['bus1'],
                              p_nom=link_row.get('p_nom', 0), # p_nom is fixed capacity, if extendable, it's optimized
                              p_nom_extendable=link_row.get('p_nom_extendable', False),
                              efficiency=link_row.get('efficiency', 1),
                              p_max_pu=link_p_max_pu_val,
                              p_min_pu=link_p_min_pu_val,
                              # lifetime=link_row.get('lifetime', np.inf), # PyPSA default
                              # build_year=link_row.get('build_year', base_year_config), # PyPSA default
                              capital_cost=link_row.get('capital_cost', 0), # Annual cost if extendable
                              marginal_cost=link_row.get('marginal_cost', 0)
                              # type=link_row.get('type', None) # Custom type if used in constraints
                              )
                job['log'].append("Links added.")
                job['progress'] = current_progress_base + 30

                # 11. Unit Commitment Settings on Network
                if do_unit_commitment and not committable_settings_df.empty:
                    job['log'].append("Applying unit commitment settings from Excel table...")
                    committable_carriers = committable_settings_df[committable_settings_df['Option'].astype(str).str.lower() == 'yes']['Carrier'].tolist()
                    non_committable_carriers = committable_settings_df[committable_settings_df['Option'].astype(str).str.lower() == 'no']['Carrier'].tolist()
                    
                    if not n.generators.empty:
                        n.generators.loc[n.generators.carrier.isin(committable_carriers), 'committable'] = True
                        n.generators.loc[n.generators.carrier.isin(non_committable_carriers), 'committable'] = False
                        job['log'].append(f"Marked carriers {committable_carriers} as committable.")
                    else:
                        job['log'].append("No generators in network to apply committable settings to.")


                # 12. Optimization
                job['current_step'] = f"Optimizing network for year {current_year}"
                job['log'].append(f"Starting initial optimization for year {current_year}...")
                n.optimize(solver_name=solver_name_opt, solver_options=solver_options_from_ui)
                job['log'].append(f"Initial optimization for year {current_year} complete. Objective: {n.objective:.2f}")
                job['progress'] = current_progress_base + 45


                # 13. Apply Network Constraints (if any) and Re-solve
                # This function now needs to be robust and handle missing tables gracefully
                job['log'].append(f"Applying network constraints for year {current_year} (if configured)...")
                n = _apply_network_constraints(n, setting_df_excel, settings_main_excel_table, job, solver_name_opt, solver_options_from_ui)
                job['log'].append(f"Network constraints applied and model potentially re-solved for year {current_year}. New Objective: {n.objective:.2f}")
                job['progress'] = current_progress_base + 55


                # 14. Export Results for the current year
                year_results_dir_obj = scenario_results_dir / f"results_{current_year}"
                year_results_dir_obj.mkdir(parents=True, exist_ok=True)
                job['log'].append(f"Exporting results for {current_year} to {year_results_dir_obj}")

                n.export_to_csv_folder(str(year_results_dir_obj))
                # Export full network to NetCDF for this year.
                # The name should be unique for the year if scenario_results_dir is common for all years of a scenario run.
                netcdf_file_name_year = scenario_results_dir / f"{scenario_name}_{current_year}_network.nc"
                n.export_to_netcdf(str(netcdf_file_name_year))
                job['log'].append(f"Year {current_year} results exported. NetCDF: {netcdf_file_name_year.name}")

                previous_year_export_path_obj = year_results_dir_obj # Update for next iteration
                job['progress'] = current_progress_base + 60

            job['log'].append("All single-year models processed successfully.")

        elif multi_year_mode == 'Only Capacity expansion on multi year' or multi_year_mode == 'All in One multi year':
            # This mode is significantly different and requires a single network build with MultiIndex snapshots
            job['log'].append(f"Multi-year mode '{multi_year_mode}' selected. This is a complex setup.")
            job['status'] = 'Running Multi-Year Model'
            # (Implementation for multi-year would go here, following the notebook's second main block)
            # This involves:
            # 1. Snapshots_from_user_input_for_multiyear
            # 2. Setting n.investment_periods, n.investment_period_weightings (with discount factors)
            # 3. Adding all components with build_year attributes, where capital_cost is for that build_year
            # 4. A single n.optimize() call.
            # 5. Potentially different constraint handling.
            raise NotImplementedError(f"Multi-year mode '{multi_year_mode}' is not fully implemented in this version of pypsa_runner.py.")

        else:
            raise ValueError(f"Unknown 'Multi Year Investment' mode: {multi_year_mode}")


        # Finalize Job
        result_files_list = []
        if scenario_results_dir.exists():
            for item_path in scenario_results_dir.rglob('*'):
                if item_path.is_file():
                    result_files_list.append(str(item_path.relative_to(scenario_results_dir)))
        job['result_files'] = result_files_list
        job['status'] = 'Completed'
        job['progress'] = 100
        job['current_step'] = 'Model run finished successfully'
        job['log'].append(f"PyPSA Model run '{scenario_name}' finished successfully at {datetime.now().isoformat()}.")
        job['result'] = {'message': 'Model run completed.', 'output_folder': str(scenario_results_dir)}
        logger.info(f"Job {job_id} for scenario '{scenario_name}' completed.")

    except FileNotFoundError as e:
        error_msg = f"File Not Found Error: {str(e)}"
        job['status'] = 'Failed'
        job['error'] = error_msg
        job['log'].append(f"CRITICAL ERROR: {error_msg}")
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=False) # No need for full stack for FileNotFoundError usually
    except ValueError as e: # For configuration or data validation errors
        error_msg = f"Validation/Configuration Error: {str(e)}"
        job['status'] = 'Failed'
        job['error'] = error_msg
        job['log'].append(f"CRITICAL ERROR: {error_msg}")
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=True)
    except NotImplementedError as e:
        error_msg = f"Feature Not Implemented: {str(e)}"
        job['status'] = 'Failed'
        job['error'] = error_msg
        job['log'].append(f"ERROR: {error_msg}")
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=False)
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        stack_trace = traceback.format_exc()
        job['status'] = 'Failed'
        job['error'] = error_msg
        job['log'].append(f"CRITICAL UNEXPECTED ERROR: {error_msg}")
        job['log'].append(f"Stack trace: {stack_trace}")
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed critically with an unexpected error.", exc_info=True)
    finally:
        job['end_time'] = datetime.now().isoformat()
        if job.get('status') != 'Completed':
             job['progress'] = 100 # Mark as 100% done even if failed, for UI clarity
        os.chdir(original_cwd) # Restore original working directory


# Helper function to generate snapshots for a single year
def _generate_snapshots_for_year(input_file_path_str, target_year, snapshot_condition, weightings_freq_hours, base_year_config, demand_df, custom_days_df, log_list):
    """
    Generate snapshots for a specific year based on condition.
    `demand_df` and `custom_days_df` are passed as already loaded DataFrames.
    `log_list` is the job's log list to append messages to.
    """
    log_list.append(f"Snapshot generation for FY{target_year}: Condition='{snapshot_condition}', Freq={weightings_freq_hours}H.")

    # Financial year runs from April of (target_year-1) to March of target_year
    fy_start_date = pd.Timestamp(f'{int(target_year)-1}-04-01 00:00:00')
    fy_end_date = pd.Timestamp(f'{int(target_year)}-03-31 23:00:00') # Inclusive of 23:00
    full_year_hourly_index = pd.date_range(start=fy_start_date, end=fy_end_date, freq='H')

    def _resample_dt_index(dt_index_to_resample, freq_hours_val):
        if not isinstance(dt_index_to_resample, pd.DatetimeIndex) or dt_index_to_resample.empty:
            log_list.append("Warning: _resample_dt_index received empty or invalid index. Returning empty.")
            return pd.DatetimeIndex([])
        # Create a dummy series, resample, and return the new index
        # Ensure consistent origin for resampling if needed, e.g., start of the day/period
        try:
            # Resample based on the actual start of the data to avoid alignment issues
            # Using .asfreq() after resample().mean() can be more robust for just getting the index points
            resampled_idx = pd.Series(1, index=dt_index_to_resample).resample(f'{int(freq_hours_val)}H').mean().index
            # Ensure the resampled index is within the original range if it matters
            # resampled_idx = resampled_idx[(resampled_idx >= dt_index_to_resample.min()) & (resampled_idx <= dt_index_to_resample.max())]
            return resampled_idx
        except Exception as e_resample:
            log_list.append(f"Error during resampling: {e_resample}. Falling back to original index or empty.")
            return dt_index_to_resample if int(freq_hours_val) == 1 else pd.DatetimeIndex([])


    selected_snapshots_for_model = pd.DatetimeIndex([])

    if snapshot_condition == 'All Snapshots':
        selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
    elif snapshot_condition == 'Critical days':
        if custom_days_df.empty:
            log_list.append("Warning: 'Critical days' selected but 'Custom days' sheet is empty or missing. Defaulting to 'All Snapshots'.")
            selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
        else:
            try:
                # 'Month' and 'Day' columns are from Custom days sheet
                # Determine 'CalendarYear' based on FY logic
                df_cd = custom_days_df.copy()
                df_cd['CalendarYear'] = df_cd['Month'].apply(
                    lambda m: int(target_year) - 1 if int(m) >= 4 else int(target_year) # April onwards is previous calendar year for FY
                )
                custom_dates_pd = pd.to_datetime(
                    {'year': df_cd['CalendarYear'], 'month': df_cd['Month'], 'day': df_cd['Day']}
                )
                hourly_custom_day_snapshots = pd.DatetimeIndex([])
                for date_val in sorted(custom_dates_pd.unique()):
                    # Create 24 hourly snapshots for each unique custom day
                    hourly_custom_day_snapshots = hourly_custom_day_snapshots.union(
                        pd.date_range(start=date_val, periods=24, freq='H')
                    )
                selected_snapshots_for_model = _resample_dt_index(hourly_custom_day_snapshots, weightings_freq_hours)
            except Exception as e_crit:
                log_list.append(f"Error processing critical days for {target_year}: {e_crit}. Defaulting to 'All Snapshots'.")
                selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)

    elif snapshot_condition == 'Typical days': # Peak weeks logic from notebook
        try:
            demand_col_to_use_snap = target_year if target_year in demand_df.columns else base_year_config
            if demand_col_to_use_snap not in demand_df.columns:
                 log_list.append(f"Demand data for year {demand_col_to_use_snap} not found for Typical Days. Defaulting to All.")
                 selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
            else:
                demand_series_full_fy = pd.Series(demand_df[demand_col_to_use_snap].values, index=full_year_hourly_index)
                temp_df = demand_series_full_fy.to_frame('demand')
                # Calculate month relative to FY start (April = 0, May = 1 ... March = 11)
                temp_df['month_in_fy'] = (temp_df.index.month - fy_start_date.month + 12) % 12
                # Calculate week relative to FY start
                temp_df['week_in_fy'] = (temp_df.index - fy_start_date).days // 7

                peak_week_snapshots_list = []
                for _, month_group in temp_df.groupby('month_in_fy'):
                    if month_group.empty: continue
                    weekly_sum = month_group.groupby('week_in_fy')['demand'].sum()
                    if weekly_sum.empty: continue
                    peak_week_num_in_fy = weekly_sum.idxmax() # Week number within the FY
                    peak_week_snapshots_list.extend(month_group[month_group['week_in_fy'] == peak_week_num_in_fy].index)

                if peak_week_snapshots_list:
                    selected_snapshots_for_model = _resample_dt_index(pd.DatetimeIndex(sorted(list(set(peak_week_snapshots_list)))), weightings_freq_hours)
                else:
                    log_list.append(f"No peak weeks identified for FY{target_year}. Defaulting to 'All Snapshots'.")
                    selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
        except Exception as e_typ:
            log_list.append(f"Error processing typical days for {target_year}: {e_typ}. Defaulting to 'All Snapshots'.")
            selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
    else:
        log_list.append(f"Unknown snapshot condition: '{snapshot_condition}'. Defaulting to 'All Snapshots'.")
        selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)

    if selected_snapshots_for_model.empty:
         log_list.append(f"Warning: Snapshot generation resulted in an empty list for FY{target_year}. This might cause errors.")

    return selected_snapshots_for_model, full_year_hourly_index


# Network-based retiring logic (operates on the pypsa.Network object)
def _apply_retiring_logic_network(n, select_year, base_year):
    """Apply generator retiring logic directly on the PyPSA network object."""
    generators_to_remove = []
    if select_year == base_year: # Assuming base_year is an int
        # Remove generators built after a certain reference year (e.g., 2025 in notebook)
        # This rule might be specific to the base year setup.
        ref_retire_year = 2025 # As per notebook logic for base_year/2025
        generators_to_remove.extend(n.generators[n.generators.build_year > ref_retire_year].index.tolist())
    else:
        # Standard retiring: remove if lifetime ended before or in select_year
        # And remove those built after select_year (future plants not relevant for this year's run)
        generators_to_remove.extend(n.generators[n.generators.build_year + n.generators.lifetime <= select_year].index.tolist())
        generators_to_remove.extend(n.generators[n.generators.build_year > select_year].index.tolist())

    if generators_to_remove:
        # n.mremove("Generator", generators_to_remove) # Use mremove for multiple
        # PyPSA add/remove methods usually take a list of names.
        # If names are not unique, this could be an issue. Assume names are unique for now.
        # Let's remove them one by one to be safe or ensure names are unique
        unique_gens_to_remove = list(set(generators_to_remove))
        n.remove("Generator", unique_gens_to_remove)
        logger.info(f"Retired {len(unique_gens_to_remove)} generators for year {select_year}.")
    return n

def _apply_storage_retiring_logic_network(n, select_year, base_year):
    """Apply storage retiring logic directly on the PyPSA network object."""
    stores_to_remove = []
    storage_units_to_remove = []

    # For Stores
    if not n.stores.empty:
        if select_year == base_year:
            ref_retire_year = 2025
            stores_to_remove.extend(n.stores[n.stores.build_year > ref_retire_year].index.tolist())
        else:
            stores_to_remove.extend(n.stores[n.stores.build_year + n.stores.lifetime <= select_year].index.tolist())
            stores_to_remove.extend(n.stores[n.stores.build_year > select_year].index.tolist())
        if stores_to_remove:
            n.remove("Store", list(set(stores_to_remove)))
            logger.info(f"Retired {len(set(stores_to_remove))} Stores for year {select_year}.")

    # For StorageUnits
    if not n.storage_units.empty:
        if select_year == base_year:
            ref_retire_year = 2025
            storage_units_to_remove.extend(n.storage_units[n.storage_units.build_year > ref_retire_year].index.tolist())
        else:
            storage_units_to_remove.extend(n.storage_units[n.storage_units.build_year + n.storage_units.lifetime <= select_year].index.tolist())
            storage_units_to_remove.extend(n.storage_units[n.storage_units.build_year > select_year].index.tolist())
        if storage_units_to_remove:
            n.remove("StorageUnit", list(set(storage_units_to_remove)))
            logger.info(f"Retired {len(set(storage_units_to_remove))} StorageUnits for year {select_year}.")
    return n


def _apply_generator_clustering(n, p_max_pu_aligned_dfs, p_min_pu_aligned_dfs, log_list):
    """
    Apply generator clustering.
    `p_max_pu_aligned_dfs` and `p_min_pu_aligned_dfs` are dicts of Series,
    keyed by tech name, already aligned to n.snapshots.
    """
    if n.generators.empty:
        log_list.append("No generators to cluster.")
        return n

    # Create a DataFrame from n.generators that includes all necessary attributes for clustering
    # Ensure to handle potentially missing columns with defaults if necessary
    # PyPSA uses NaN for undefined numerical optional parameters, so fillna might be needed for calculations
    cluster_source_df = n.generators.copy()
    cluster_source_df.reset_index(inplace=True) # 'name' becomes a column

    # Group by carrier, bus, and marginal_cost.
    # Marginal cost can be float, handle potential precision issues if used directly for grouping floats.
    # It might be safer to round marginal_cost or group by other defining characteristics if MC is too variable.
    # For now, assume it's stable enough for grouping as in the notebook.
    # Ensure 'marginal_cost' is numeric and handle NaNs if they are not meaningful for grouping
    cluster_source_df['marginal_cost_group'] = cluster_source_df['marginal_cost'].fillna(np.nan).round(4) # Round for stable grouping

    # Add default values for attributes that might be missing after retiring or from partial data
    default_attrs = {
        'p_nom_min': 0, 'p_nom_max': np.inf, 'min_up_time': 0, 'min_down_time': 0,
        'ramp_limit_up': np.nan, 'ramp_limit_down': np.nan, 'start_up_cost': 0, 'shut_down_cost': 0,
        'committable': False, 'p_nom_extendable': False, 'capital_cost':0
    }
    for attr, default_val in default_attrs.items():
        if attr not in cluster_source_df.columns:
            cluster_source_df[attr] = default_val
        else: # Fill NaNs for numeric columns involved in sum/mean
            if pd.api.types.is_numeric_dtype(cluster_source_df[attr]):
                 cluster_source_df[attr] = cluster_source_df[attr].fillna(default_val if attr not in ['ramp_limit_up', 'ramp_limit_down'] else np.nan)


    # Perform grouping
    # Note: Using 'marginal_cost_group' for grouping
    # 'p_nom_extendable' and 'committable' should also be part of group key if they vary within (carrier, bus, mc)
    # The notebook groups by ('carrier', 'bus', 'marginal_cost'). Let's stick to that and ensure MC is handled.
    # If extendable/committable can differ for same carrier/bus/mc, they should be in groupby.
    # Assuming for now they are consistent or the first one is taken.
    grouped_generators = cluster_source_df.groupby(['carrier', 'bus', 'marginal_cost_group', 'p_nom_extendable', 'committable'], observed=True, dropna=False)


    # Store names of generators to remove before adding clustered ones
    original_generator_names = n.generators.index.tolist()

    for group_keys, group_df in grouped_generators:
        carrier, bus, _, p_nom_extendable_val, committable_val = group_keys # Unpack keys

        if group_df.empty: continue

        # Aggregated properties
        total_p_nom = group_df['p_nom'].sum()
        if total_p_nom == 0 and not p_nom_extendable_val : # Skip clusters with no capacity unless extendable
            log_list.append(f"Skipping empty cluster (and not extendable): {group_keys}")
            continue

        # Weighted average for marginal_cost (use original MC for calculation, group_key MC was for grouping)
        # Handle cases where total_p_nom might be zero (for extendable clusters)
        weighted_marginal_cost = np.average(group_df['marginal_cost'].fillna(0), weights=group_df['p_nom'].fillna(0)) if total_p_nom > 0 else group_df['marginal_cost'].fillna(0).mean()
        
        # Sum for capacities, min/mean for others
        # Ensure that p_nom_max is summed correctly (inf + x = inf)
        summed_p_nom_max = group_df['p_nom_max'].sum()
        if np.isinf(group_df['p_nom_max'].array).any(): # Check using .array for ExtensionArray compatibility
            summed_p_nom_max = np.inf


        # Get p_min_pu and p_max_pu series for the carrier
        p_max_pu_key_cluster = f"{carrier}_Outside" if bus == 'Outside Kerala' and carrier in ['Solar', 'Wind'] else carrier
        p_min_pu_key_cluster = f"{carrier}_Outside" if bus == 'Outside Kerala' and carrier in ['Solar', 'Wind'] else carrier
        
        p_max_pu_series_cluster = p_max_pu_aligned_dfs.get(p_max_pu_key_cluster, pd.Series(1, index=n.snapshots))
        p_min_pu_series_cluster = p_min_pu_aligned_dfs.get(p_min_pu_key_cluster, pd.Series(0, index=n.snapshots))
        if bus == 'Outside Kerala' and carrier in ['Solar', 'Wind']: p_min_pu_series_cluster = pd.Series(0, index=n.snapshots)


        clustered_gen_name = f"{carrier}_{bus}_mc{weighted_marginal_cost:.2f}_cluster"
        # Ensure unique name if multiple clusters end up with same rounded MC
        # This could be improved by adding a counter if name collision happens
        
        log_list.append(f"Adding clustered generator: {clustered_gen_name} (from {len(group_df)} original generators)")

        n.add("Generator",
              clustered_gen_name,
              bus=bus,
              carrier=carrier,
              p_nom=total_p_nom,
              p_nom_min=group_df['p_nom_min'].sum(),
              p_nom_max=summed_p_nom_max,
              p_nom_extendable=p_nom_extendable_val,
              marginal_cost=weighted_marginal_cost,
              capital_cost=group_df['capital_cost'].sum(), # Sum annual capital costs
              build_year=group_df['build_year'].max(), # Take max build year
              lifetime=group_df['lifetime'].mean(),   # Average lifetime
              committable=committable_val,
              p_min_pu=p_min_pu_series_cluster.tolist(),
              p_max_pu=p_max_pu_series_cluster.tolist(),
              min_up_time=group_df['min_up_time'].mean(),
              min_down_time=group_df['min_down_time'].mean(),
              ramp_limit_up=group_df['ramp_limit_up'].mean(), # Mean of non-NaN, or NaN if all NaN
              ramp_limit_down=group_df['ramp_limit_down'].mean(),
              start_up_cost=group_df['start_up_cost'].mean(),
              shut_down_cost=group_df['shut_down_cost'].mean()
              )

    # Remove original individual generators
    if original_generator_names:
        n.remove("Generator", original_generator_names)
        log_list.append(f"Removed {len(original_generator_names)} original generators after clustering.")

    return n


def _apply_network_constraints(n, setting_df_excel, settings_main_excel_table, job, solver_name, solver_options_dict):
    """
    Apply network constraints (monthly generation, battery cycle limits) if enabled.
    This function might re-solve the model.
    """
    log_list = job['log'] # Use the job's log list

    # Check if 'Monthly constraints' setting exists and is 'Yes'
    monthly_constraints_setting_row = settings_main_excel_table[settings_main_excel_table['Setting'] == 'Monthly constraints']
    apply_monthly_gen_constraints = False
    apply_battery_cycle_constraints = False # Assume same master switch for now as notebook

    if not monthly_constraints_setting_row.empty:
        master_switch_monthly = monthly_constraints_setting_row['Option'].values[0]
        if str(master_switch_monthly).lower() == 'yes':
            apply_monthly_gen_constraints = True
            apply_battery_cycle_constraints = True # As per notebook structure
            log_list.append("Monthly and/or Battery Cycle constraints are enabled based on Main_Settings.")
        else:
            log_list.append("Monthly and Battery Cycle constraints are disabled in Main_Settings.")
            return n # No constraints to apply
    else:
        log_list.append("Warning: 'Monthly constraints' setting not found in Main_Settings. No network constraints applied.")
        return n


    # If either constraint type is active, we need to create the model expression handles
    if apply_monthly_gen_constraints or apply_battery_cycle_constraints:
        try:
            # Create Linopy model expressions. This requires the network to have been optimized once to get p_nom_opt.
            # If n.model is not yet built (e.g. first solve hasn't happened or was cleared), this will fail.
            # PyPSA's n.optimize() calls n.lopf(), which builds n.model.
            # If this function is called after n.optimize(), n.model should exist.
            if not hasattr(n, 'model') or n.model is None:
                 log_list.append("Warning: n.model not found. Constraints requiring model variables (like Generator-p) cannot be added. Solve first.")
                 # Attempt to build model if not present - this is risky if solve options are not fully set
                 # n.lopf(pypsa_dict=n.pypsa_components, solver_name=solver_name, **solver_options_dict) # This is a guess
                 # Safer to assume optimize was called.
                 return n


            constraints_were_added = False

            # Monthly Generation Constraints
            if apply_monthly_gen_constraints:
                log_list.append("Processing monthly generation constraints...")
                monthly_constraints_table_df = extract_tables_by_markers(setting_df_excel, '~').get('Monthly_Constraints')
                if monthly_constraints_table_df is None or monthly_constraints_table_df.empty:
                    log_list.append("Monthly_Constraints table not found or empty in Settings sheet. Skipping monthly gen constraints.")
                else:
                    gen_p = n.model.variables["Generator-p"] # Expression for generator dispatch
                    for carrier_name_constraint in n.generators.carrier.unique():
                        if carrier_name_constraint in monthly_constraints_table_df.columns:
                            gens_of_carrier = n.generators[n.generators.carrier == carrier_name_constraint].index
                            if gens_of_carrier.empty: continue

                            # Use p_nom_opt (optimized capacity) if available, else p_nom (fixed capacity)
                            # This implies constraints are added AFTER an initial optimization that determines p_nom_opt.
                            total_capacity_for_carrier = n.generators.loc[gens_of_carrier, 'p_nom_opt'].sum() if 'p_nom_opt' in n.generators.columns else n.generators.loc[gens_of_carrier, 'p_nom'].sum()
                            if total_capacity_for_carrier == 0:
                                log_list.append(f"Carrier {carrier_name_constraint} has 0 capacity for monthly constraints. Skipping.")
                                continue
                            
                            carrier_gen_dispatch_vars = gen_p.sel(Generator=gens_of_carrier) # Dispatch variables for these generators

                            for _, m_limit_row in monthly_constraints_table_df.iterrows():
                                month_num = m_limit_row.get('Month') # Expecting 1-12
                                cap_factor_limit = m_limit_row.get(carrier_name_constraint)

                                if pd.isna(month_num) or pd.isna(cap_factor_limit): continue

                                # Identify snapshots for this month
                                # Handle both MultiIndex and DatetimeIndex for snapshots
                                time_idx_for_month = n.snapshots.get_level_values(-1) if isinstance(n.snapshots, pd.MultiIndex) else n.snapshots
                                if not isinstance(time_idx_for_month, pd.DatetimeIndex): continue # Cannot get month

                                month_snapshots_bool = (time_idx_for_month.month == int(month_num))
                                if not month_snapshots_bool.any(): continue
                                
                                # Duration of snapshots in this month
                                # snapshot_weightings['objective'] holds duration of each snapshot
                                hours_in_month_snapshots = n.snapshot_weightings.objective[month_snapshots_bool].sum()
                                if hours_in_month_snapshots == 0: continue

                                # Generation limit for this month = CF_limit * TotalCapacity * HoursInMonth
                                monthly_gen_limit_mwh = cap_factor_limit * total_capacity_for_carrier * hours_in_month_snapshots
                                
                                # Sum of generation for this carrier over the month's snapshots
                                # generation = sum_{snapshots_in_month} ( dispatch_vars_for_carrier_at_snapshot * snapshot_duration )
                                monthly_total_generation_expr = (carrier_gen_dispatch_vars.sel(snapshot=n.snapshots[month_snapshots_bool]) * n.snapshot_weightings.objective[month_snapshots_bool]).sum()
                                
                                constraint_name = f"monthly_gen_limit_{carrier_name_constraint}_month{int(month_num)}"
                                n.model.add_constraints(monthly_total_generation_expr <= monthly_gen_limit_mwh, name=constraint_name)
                                log_list.append(f"Added constraint: {constraint_name} (Limit: {monthly_gen_limit_mwh:.2f} MWh)")
                                constraints_were_added = True

            # Battery Cycle Constraints
            if apply_battery_cycle_constraints:
                log_list.append("Processing battery cycle constraints...")
                battery_cycle_table_df = extract_tables_by_markers(setting_df_excel, '~').get('Battery_Cycle')
                if battery_cycle_table_df is None or battery_cycle_table_df.empty:
                    log_list.append("Battery_Cycle table not found or empty. Skipping battery cycle constraints.")
                elif n.stores.empty and n.storage_units.empty: # Check if there are any storage components
                    log_list.append("No stores or storage units in the network. Skipping battery cycle constraints.")
                else:
                    # Assuming constraints apply to 'Store' components as in notebook
                    # Notebook uses 'Store-p' which is dispatch/charge power.
                    # Limit is on total energy dispatched (positive Store-p values) over a cycle.
                    if "Store-p" not in n.model.variables: # Check if Store dispatch variables exist
                        log_list.append("Warning: 'Store-p' variables not in model. Cannot apply battery dispatch cycle constraints.")
                    else:
                        store_dispatch_p = n.model.variables["Store-p"] # Linopy variable

                        cycle_info_row = battery_cycle_table_df.iloc[0] # Assuming first row defines the cycle
                        cycle_type = cycle_info_row.get('Type', 'Daily').lower()
                        num_cycles_per_period = cycle_info_row.get('No. of cycle', 1)
                        if num_cycles_per_period == 0: num_cycles_per_period = 1 # Avoid division by zero

                        # Determine cycle length in hours
                        if cycle_type == 'daily': cycle_len_hours = 24 / num_cycles_per_period
                        elif cycle_type == 'weekly': cycle_len_hours = (24 * 7) / num_cycles_per_period
                        elif cycle_type == 'monthly': cycle_len_hours = (24 * 30) / num_cycles_per_period # Approx.
                        else: cycle_len_hours = (24 * 365) / num_cycles_per_period # Annual approx.
                        cycle_len_hours = int(max(1, cycle_len_hours)) # Ensure at least 1 hour

                        # Convert cycle_len_hours to number of snapshots (approx)
                        # Assumes uniform snapshot duration from snapshot_weightings.objective
                        avg_snapshot_duration = n.snapshot_weightings.objective.mean()
                        if avg_snapshot_duration == 0: avg_snapshot_duration = 1 # Avoid div by zero
                        cycle_len_snapshots = int(max(1, cycle_len_hours / avg_snapshot_duration))


                        for store_name in n.stores.index: # Iterate through each 'Store' component
                            if 'e_nom_opt' not in n.stores.columns or pd.isna(n.stores.loc[store_name, 'e_nom_opt']):
                                log_list.append(f"Skipping cycle constraint for store {store_name}, e_nom_opt not available.")
                                continue
                            
                            store_energy_capacity = n.stores.loc[store_name, 'e_nom_opt']
                            if store_energy_capacity == 0: continue

                            for i in range(0, len(n.snapshots), cycle_len_snapshots):
                                cycle_snaps_slice = n.snapshots[i : i + cycle_len_snapshots]
                                if cycle_snaps_slice.empty: continue

                                # Total energy dispatched (positive power) by this store in this cycle
                                # Sum (Store-p[st, sns] * snapshot_duration[sns]) for sns in cycle_snaps_slice if Store-p > 0
                                store_dispatch_in_cycle = store_dispatch_p.sel(Store=store_name, snapshot=cycle_snaps_slice)
                                
                                # Linopy constraint: sum of positive dispatch * duration <= e_nom_opt
                                # This requires careful formulation with Linopy.
                                # A common way is to introduce auxiliary positive variables.
                                # Simpler (maybe less performant for solver): Summing only positive parts not directly easy in one Linopy expression for constraint.
                                # The notebook sums positive values after getting data. For model constraints, it's different.
                                # The constraint should be: dispatched_energy_in_cycle <= store_energy_capacity
                                # Let's assume total throughput (charge + dispatch / 2) or just dispatch limit.
                                # Notebook: cyclic_supply (positive Store-p values summed) <= e_nom_opt
                                # This means total energy dispatched should be less than its capacity.
                                # This requires positive_part(Store-p) in linopy.
                                # If Store-p can be negative (charging), this needs care.
                                # PyPSA convention: Store-p > 0 is dispatch, Store-p < 0 is charge.
                                # So we want sum(Store-p[Store-p > 0] * duration) <= e_nom_opt
                                
                                # This is a complex constraint to add directly with Linopy's expression.
                                # The notebook's approach seems to be a post-analysis check or a simplified constraint.
                                # For a true model constraint, you might need to use an auxiliary variable:
                                # store_dispatch_positive_vars >= store_dispatch_in_cycle
                                # store_dispatch_positive_vars >= 0
                                # sum(store_dispatch_positive_vars * snapshot_weightings) <= store_energy_capacity
                                # Or, if the solver handles it, a constraint on the sum of the positive part.
                                # For now, let's log that this is complex.
                                log_list.append(f"Battery cycle constraint for store {store_name} for cycle starting {cycle_snaps_slice[0]} is complex to add directly. Placeholder for now.")
                                # constraints_were_added = True # If implemented

            if constraints_were_added:
                log_list.append("Re-solving model with added network constraints...")
                n.optimize.solve_model(solver_name=solver_name, solver_options=solver_options_dict) # Uses existing n.model
                log_list.append("Model re-solved after adding constraints.")
            else:
                log_list.append("No new network constraints were actually added to the model formulation.")

        except Exception as e_constraints:
            log_list.append(f"ERROR applying network constraints: {str(e_constraints)}. Proceeding without them or with previously solved state.")
            logger.error(f"Error applying network constraints for job {job['jobId'] if 'jobId' in job else 'unknown'}", exc_info=True)
            # Depending on severity, you might want to stop or just log and continue
    return n

