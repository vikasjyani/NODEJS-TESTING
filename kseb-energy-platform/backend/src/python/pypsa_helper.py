import json
import sys
import time

def execute_optimization(config_json_string):
    """
    Placeholder for PyPSA optimization execution.
    Receives configuration as a JSON string.
    """
    try:
        config = json.loads(config_json_string)
        # Simulate work and progress for PyPSA optimization
        optimization_phases = [
            "Network Setup",
            "Constraint Building",
            "LP File Generation",
            "Solver Execution",
            "Result Processing"
        ]
        total_phases = len(optimization_phases)

        for i, phase_name in enumerate(optimization_phases):
            time.sleep(0.5) # PyPSA tasks can be longer
            progress = (i + 1) / total_phases * 100

            progress_data = {
                "progress": progress,
                "step": phase_name, # 'step' is used in frontend, aligning with it
                "status": f"Running PyPSA: {phase_name}",
                "details": f"Completed {phase_name}, moving to next."
            }
            print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)

        # Simulate final result
        result = {
            "success": True,
            "job_id": config.get("job_id", "default_pypsa_job"),
            "message": "PyPSA optimization completed successfully (simulated).",
            "results_summary": {
                "total_cost_eur": 1.5e9,
                "co2_emissions_mt": 2.5e6,
                "renewable_share_percent": 65.5
            },
            "network_file_path": f"/results/pypsa_networks/{config.get('scenario_name', 'test_scenario')}.nc",
            "config_received": config
        }
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        config_arg = sys.argv[1]
        output = execute_optimization(config_arg)
    else:
        example_config = {
            "job_id": "test_pypsa_789",
            "scenario_name": "high_renewables_2030",
            "solver": "gurobi"
        }
        output = execute_optimization(json.dumps(example_config))

    print(json.dumps(output)) # Final JSON output for Node.js
