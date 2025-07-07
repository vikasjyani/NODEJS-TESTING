import sys
import importlib
import logging
import platform

# Configure basic logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REQUIRED_PACKAGES = [
    "pandas",
    "numpy",
    "scikit-learn", # For SLR, MLR models
    "statsmodels"   # For TimeSeries (ARIMA) models
    # Add other critical packages as your Python modules evolve e.g., "openpyxl" for Excel
]

OPTIONAL_PACKAGES = {
    "prophet": "for advanced time series forecasting (Prophet model)",
    # "pyarrow": "for efficient Parquet/Feather file handling",
    # "matplotlib": "for server-side plot generation (if ever needed)",
    # "seaborn": "for statistical visualizations (if ever needed)"
}

def check_python_version():
    """Checks if the Python version meets a minimum requirement."""
    logger.info(f"Python Version: {sys.version}")
    min_version = (3, 7) # Example: Require Python 3.7+
    if sys.version_info < min_version:
        logger.error(f"Python version {min_version[0]}.{min_version[1]} or higher is required. You have {sys.version_info.major}.{sys.version_info.minor}.")
        return False
    logger.info("Python version check passed.")
    return True

def check_package(package_name: str, is_optional: bool = False) -> bool:
    """Tries to import a package and logs its version."""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'N/A (version not exposed)')
        logger.info(f"SUCCESS: Package '{package_name}' (version: {version}) loaded.")
        return True
    except ImportError:
        if is_optional:
            logger.warning(f"OPTIONAL: Package '{package_name}' not found. {OPTIONAL_PACKAGES.get(package_name, '')}")
        else:
            logger.error(f"FAILED: Required package '{package_name}' not found. Please install it.")
        return False
    except Exception as e:
        logger.error(f"Error loading package '{package_name}': {e}")
        return False


def check_system_info():
    logger.info("--- System Information ---")
    logger.info(f"Platform: {platform.system()} ({platform.release()})")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"Processor: {platform.processor() if platform.processor() else 'N/A'}")
    # Add more system info if relevant (e.g., memory, disk - using psutil if installed)

def main():
    logger.info("--- KSEB Energy Futures Platform Python Environment Test ---")

    all_checks_ok = True

    # 1. Check Python Version
    if not check_python_version():
        all_checks_ok = False

    # 2. Check Required Packages
    logger.info("\n--- Checking Required Python Packages ---")
    for pkg in REQUIRED_PACKAGES:
        if not check_package(pkg):
            all_checks_ok = False

    # 3. Check Optional Packages
    logger.info("\n--- Checking Optional Python Packages ---")
    for pkg in OPTIONAL_PACKAGES.keys():
        check_package(pkg, is_optional=True) # Don't fail build for optional packages

    # 4. Display System Info
    check_system_info()

    # 5. Summary
    logger.info("\n--- Test Summary ---")
    if all_checks_ok:
        logger.info("All critical environment checks passed successfully!")
        logger.info("The Python environment seems correctly configured for core functionalities.")
        sys.exit(0) # Exit with 0 for success
    else:
        logger.error("One or more critical environment checks failed. Please review the logs above and install/update missing components.")
        logger.error("The application's Python-dependent features may not work correctly.")
        sys.exit(1) # Exit with 1 for failure

if __name__ == "__main__":
    main()

# To run this script:
# python test_environment.py
#
# Consider adding this to a pre-flight check in your Node.js backend
# when it first tries to use a Python script, or during an installation/setup phase.
