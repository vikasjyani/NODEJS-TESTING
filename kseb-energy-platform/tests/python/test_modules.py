import unittest
import json
import tempfile
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# --- Setup sys.path to find Python modules ---
# This assumes the tests/python directory is sibling to backend/src/python
# Adjust if your structure is different or if using a proper package install for modules
# Get the absolute path to the directory containing this test file
TEST_DIR = Path(__file__).resolve().parent
# Get the root project directory (e.g., 'kseb-energy-platform')
PROJECT_ROOT = TEST_DIR.parent.parent
# Path to the directory containing the Python modules to be tested
MODULES_DIR = PROJECT_ROOT / "backend" / "src" / "python"
SHARED_MODULES_DIR = MODULES_DIR / "shared"

if str(MODULES_DIR) not in sys.path:
    sys.path.insert(0, str(MODULES_DIR))
if str(SHARED_MODULES_DIR.parent) not in sys.path: # Add parent of shared if shared is a package
    sys.path.insert(0, str(SHARED_MODULES_DIR.parent))


# --- Import an
# --- Import and test modules ---
# It's good practice to wrap imports in try-except if they might fail due to dependencies
# not being set up in every test environment, though test_environment.py should catch this.
try:
    from demand_projection import ForecastingEngine as DemandForecastingEngine, DataValidator as DemandDataValidator, ProgressReporter as DemandProgressReporter
    from load_profile_generation import LoadProfileGenerator
    from pypsa_runner import PyPSARunner, extract_results_from_netcdf as extract_pypsa_results
    from pypsa_analysis import PyPSANetworkAnalyzer
    from shared import data_utils, validation as shared_validation, pypsa_utils
except ImportError as e:
    print(f"ERROR: Could not import one or more Python modules for testing: {e}")
    print("Ensure backend/src/python and backend/src/python/shared are in PYTHONPATH or accessible.")
    # Depending on test runner, might want to sys.exit(1) or raise to fail tests hard
    # For unittest, tests will fail individually if modules aren't found when classes are defined.


# --- Test Demand Projection Module ---
class TestDemandProjection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir_manager = tempfile.TemporaryDirectory()
        cls.temp_dir = Path(cls.temp_dir_manager.name)

        # Create a dummy input Excel file for demand projection
        cls.dummy_excel_path = cls.temp_dir / "inputs" / "default_demand_data.xlsx"
        (cls.temp_dir / "inputs").mkdir(parents=True, exist_ok=True)

        writer = pd.ExcelWriter(cls.dummy_excel_path, engine='openpyxl')
        pd.DataFrame({
            'year': [2019, 2020, 2021, 2022, 2023],
            'demand': [100, 102, 95, 105, 108], # 2020, 2021 are potential COVID years
            'gdp': [1000, 1010, 980, 1030, 1050],
            'population': [50, 51, 52, 53, 54]
        }).to_excel(writer, sheet_name='residential', index=False)
        pd.DataFrame({
            'year': [2019, 2020, 2021, 2022, 2023],
            'demand': [200, 205, 190, 210, 215]
        }).to_excel(writer, sheet_name='commercial', index=False)
        writer.close() # pd.ExcelWriter needs close() with openpyxl >=3.1.0, or save() with older

        cls.base_config = {
            "scenario_name": "test_demand_scenario",
            "target_year": 2025,
            "input_file": str(cls.dummy_excel_path.relative_to(MODULES_DIR)), # Path relative to where script runs
            "exclude_covid": True,
            "exclude_covid_years": [2020, 2021], # Default in script, explicit here
            "sectors": {
                "residential": {"models": ["SLR", "MLR"], "independent_variables": ["gdp", "population"]},
                "commercial": {"models": ["WAM"], "wam_window": 3}
            }
        }
        cls.reporter = DemandProgressReporter(job_id="test_demand_job")


    @classmethod
    def tearDownClass(cls):
        cls.temp_dir_manager.cleanup()

    def test_01_data_validator(self):
        validator = DemandDataValidator() # Assuming it's a class with static methods or can be instantiated
        validation_result = validator.validate_input_excel_file(self.dummy_excel_path)
        self.assertTrue(validation_result["is_valid"])
        self.assertIn("residential", validation_result["summary"]["sheets_found"])

    def test_02_slr_model(self):
        engine = DemandForecastingEngine(self.base_config, self.reporter)
        df_res = engine._load_and_prepare_data("residential")
        self.assertIsNotNone(df_res)
        # After excluding COVID years [2020, 2021], data for [2019, 2022, 2023] should remain
        self.assertEqual(len(df_res), 3)

        slr_results = engine._run_slr_model(df_res)
        self.assertNotIn("error", slr_results)
        self.assertIn("projections", slr_results)
        self.assertIn(2024, slr_results["projections"])
        self.assertIn(2025, slr_results["projections"])

    def test_03_mlr_model(self):
        engine = DemandForecastingEngine(self.base_config, self.reporter)
        df_res = engine._load_and_prepare_data("residential")
        mlr_results = engine._run_mlr_model(df_res, ["gdp", "population"])
        self.assertNotIn("error", mlr_results)
        self.assertIn("projections", mlr_results)

    def test_04_full_forecast_execution(self):
        engine = DemandForecastingEngine(self.base_config, self.reporter)
        full_results = engine.execute_full_forecast()
        self.assertNotIn("error", full_results)
        self.assertIn("residential", full_results["sectors"])
        self.assertIn("commercial", full_results["sectors"])
        self.assertIn("SLR", full_results["sectors"]["residential"]["models"])


# --- Test Load Profile Module ---
class TestLoadProfileGeneration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_manager = tempfile.TemporaryDirectory()
        cls.temp_dir = Path(cls.temp_dir_manager.name)

        # Create dummy input Excel for load profile
        cls.dummy_load_template_path = cls.temp_dir / "inputs" / "load_curve_template.xlsx"
        (cls.temp_dir / "inputs").mkdir(parents=True, exist_ok=True)
        (cls.temp_dir / "results" / "load_profiles").mkdir(parents=True, exist_ok=True) # For output

        writer = pd.ExcelWriter(cls.dummy_load_template_path, engine='openpyxl')
        hourly_data = []
        for i in range(8760): # Full year
            dt = datetime(2022, 1, 1) + timedelta(hours=i)
            load_val = 50 + 20 * np.sin(i * 2 * np.pi / 24) + 10 * np.sin(i * 2 * np.pi / 8760)
            hourly_data.append({"datetime": dt, "load": load_val})
        pd.DataFrame(hourly_data).to_excel(writer, sheet_name="2022", index=False)
        writer.close()

        cls.base_config = {
            "profile_name": "test_lp_scenario",
            "method": "base_scaling",
            "start_year": 2023,
            "end_year": 2024,
            "base_year": 2022,
            "input_template_file": str(cls.dummy_load_template_path.relative_to(MODULES_DIR/"inputs").parent), # Path relative to script's CWD (python dir)
            "growth_rate": 0.03
        }
        # Set CWD for the test to where Python scripts would run from
        cls.original_cwd = Path.cwd()
        os.chdir(MODULES_DIR) # Python scripts assume CWD is their location for relative paths like "inputs/"

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.original_cwd) # Restore CWD
        cls.temp_dir_manager.cleanup()

    def test_01_base_scaling_generation(self):
        generator = LoadProfileGenerator(self.base_config, job_id_nodejs="test_lp_job")
        results = generator.generate()

        self.assertTrue(results.get("success"))
        self.assertNotIn("error", results)
        self.assertIn("saved_path", results)
        self.assertTrue(Path(results["saved_path"]).exists())
        self.assertIn(2023, results["statistics"]["yearly"])
        self.assertIn(2024, results["statistics"]["yearly"])

        # Verify saved JSON structure (basic check)
        with open(results["saved_path"], 'r') as f:
            saved_data_package = json.load(f)
        self.assertEqual(saved_data_package["profile_id"], self.base_config["profile_name"])
        self.assertIn("2023", saved_data_package["data"])
        self.assertEqual(len(saved_data_package["data"]["2023"]), 8760) # Hourly data for a year


# --- Test PyPSA Modules (Basic Placeholders - PyPSA itself is complex) ---
class TestPyPSA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir_manager = tempfile.TemporaryDirectory()
        cls.temp_dir = Path(cls.temp_dir_manager.name)
        (cls.temp_dir / "results" / "pypsa" / "test_pypsa_scenario").mkdir(parents=True, exist_ok=True) # For output

        # Check if PyPSA is importable, skip tests if not
        cls.pypsa_available = False
        try:
            import pypsa
            cls.pypsa_available = True
        except ImportError:
            print("PyPSA library not found, skipping PyPSA tests.")

        cls.base_config = {
            "scenario_name": "test_pypsa_scenario",
            "base_year": 2023,
            "investment_mode": "single_year",
            # "input_file": "path/to/dummy_pypsa_template.xlsx", # Needs a minimal valid template
            "solver_options": {"solver": "cbc"}, # CBC or GLPK often available
            "timeout": 10000 # Short timeout for test
        }
        cls.original_cwd = Path.cwd()
        os.chdir(MODULES_DIR)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.original_cwd)
        cls.temp_dir_manager.cleanup()

    @unittest.skipIf(not pypsa_available, "PyPSA library not available")
    def test_01_pypsa_runner_placeholder_network(self):
        runner = PyPSARunner(self.base_config, job_id_nodejs="test_pypsa_job")
        results = runner.run_optimization_workflow() # Uses simple internal network

        self.assertTrue(results.get("success"))
        self.assertNotIn("error", results)
        self.assertIn("network_path", results)
        self.assertTrue(Path(results["network_path"]).exists())
        self.assertIn("summary_data", results)
        self.assertIsNotNone(results["summary_data"].get("objective_value"))

    @unittest.skipIf(not pypsa_available, "PyPSA library not available")
    def test_02_pypsa_analysis_on_generated_network(self):
        # First, run a scenario to generate a network file
        runner = PyPSARunner(self.base_config, job_id_nodejs="test_pypsa_job_for_analysis")
        run_results = runner.run_optimization_workflow()
        self.assertTrue(run_results.get("success"))
        network_file_to_analyze = run_results.get("network_path")
        self.assertTrue(network_file_to_analyze and Path(network_file_to_analyze).exists())

        # Now, analyze it
        analyzer = PyPSANetworkAnalyzer(network_file_to_analyze)
        info_results = analyzer.get_network_info() # Test one analysis type
        self.assertNotIn("error", info_results)
        self.assertEqual(info_results["name"], self.base_config["scenario_name"])
        self.assertGreater(info_results["components"]["generators"], 0)


# --- Test Shared Utilities ---
class TestSharedUtilities(unittest.TestCase):
    def test_data_utils_clean_timeseries(self):
        df = pd.DataFrame({
            'year': ['2020', '2021', 'bad_year', '2022'],
            'demand': [100, '110', 120, 115.5]
        })
        cleaned = data_utils.clean_timeseries_data(df, year_col='year', value_col='demand')
        self.assertEqual(len(cleaned), 3) # bad_year row and 'error' in demand should be handled
        self.assertTrue(pd.api.types.is_integer_dtype(cleaned['year']))
        self.assertTrue(pd.api.types.is_float_dtype(cleaned['demand']))

    def test_validation_config_keys(self):
        config = {"a":1, "b":2, "d":4}
        required = ["a", "c"]
        optional = ["b"]
        errors = shared_validation.validate_config_keys(config, required, optional)
        self.assertIn("Missing required configuration key: 'c'.", errors)
        self.assertIn("Unknown configuration keys found: d.", errors)


if __name__ == '__main__':
    # This allows running the tests directly using `python tests/python/test_modules.py`
    # Ensure PYTHONPATH is set correctly if modules are not found.

    # Example: Set PYTHONPATH temporarily if needed for direct run
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # project_root = os.path.abspath(os.path.join(script_dir, '../../..'))
    # backend_python_src = os.path.join(project_root, 'backend', 'src', 'python')
    # if backend_python_src not in sys.path:
    // PGPAGE_WELCOME
// License page (optional - if you have a license.txt in build resources)
// !define MUI_LICENSEPAGE_CHECKBOX
// !insertmacro MUI_PAGE_LICENSE "path\to\license.txt"
// Components page (if you have optional components)
// !insertmacro MUI_PAGE_COMPONENTS
// Directory page (installation path)
!insertmacro MUI_PAGE_DIRECTORY

// Custom Page for Python Path Configuration (Optional - advanced)
// Page custom nsPythonPage nsPythonPageLeave "Python Configuration"

// InstFiles page (shows installation progress)
!insertmacro MUI_PAGE_INSTFILES
// Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_PRODUCT_FILENAME}.exe" ; APP_PRODUCT_FILENAME is set by electron-builder
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md" ; If you want to show a README
!define MUI_FINISHPAGE_LINK "KSEB Energy Futures Platform Website"
!define MUI_FINISHPAGE_LINK_LOCATION "https://www.kseb.in/" ; Placeholder
!insertmacro MUI_PAGE_FINISH

// Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

//--------------------------------
// Language

!insertmacro MUI_LANGUAGE "English"

//--------------------------------
// Installer Sections & Functions

Function .onInit
  ; Set the installation scope (per-user or per-machine)
  ; electron-builder typically handles this with nsis.perMachine option
  ; If perMachine is true: SetShellVarContext all
  ; Else: SetShellVarContext current

  ; Check for existing Python (example - this is complex and might be better handled post-install by the app)
  ; Call CheckPython
FunctionEnd

// Custom Page function example (if used)
// Function nsPythonPage
//   !insertmacro MUI_HEADER_TEXT "Python Configuration" "Configure Python settings for the application."
//   ; Add custom UI elements here using nsDialogs or InstallOptions
//   nsDialogs::Create 1018
//   Pop $0 ; HWND
//   ; ...
//   nsDialogs::Show
// FunctionEnd
// Function nsPythonPageLeave
//   ; Read values from custom page
// FunctionEnd


Section "InstallApplication" SecCore
  SectionIn RO ; Required section

  SetOutPath "$INSTDIR"
  ; Files are automatically copied by electron-builder based on "files" and "extraResources" in package.json
  ; This section is mainly for custom NSIS logic like shortcuts, registry entries.

  ; Create Desktop Shortcut (electron-builder nsis.createDesktopShortcut handles this by default)
  ; If custom logic needed: CreateShortCut "$DESKTOP\${APP_PRODUCT_NAME}.lnk" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe"

  ; Create Start Menu Shortcut (electron-builder nsis.createStartMenuShortcut and nsis.menuCategory handle this)
  ; If custom logic needed:
  ; CreateDirectory "$SMPROGRAMS\${MUI_STARTMENUPAGE_FOLDER}"
  ; CreateShortCut "$SMPROGRAMS\${MUI_STARTMENUPAGE_FOLDER}\${APP_PRODUCT_NAME}.lnk" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe"

  ; Write the uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Register application for Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayName" "${APP_PRODUCT_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayIcon" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe,0"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "Publisher" "${APP_AUTHOR_NAME}" ; APP_AUTHOR_NAME set if author is object
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoRepair" 1

  ; File Associations (Example for .ksep project files)
  ; Ensure APP_ID is unique and suitable for use as a ProgID base
  WriteRegStr HKCR ".ksep" "" "${APP_ID}.ksepfile"
  WriteRegStr HKCR "${APP_ID}.ksepfile" "" "KSEB Energy Project File"
  WriteRegStr HKCR "${APP_ID}.ksepfile\DefaultIcon" "" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe,0" ; Use app icon
  WriteRegStr HKCR "${APP_ID}.ksepfile\shell\open\command" "" '"$INSTDIR\${APP_PRODUCT_FILENAME}.exe" "%1"'

  ; Notify Shell of changes for file associations
  System::Call 'shell32::SHChangeNotify(i 0x8000000, i 0, i 0, i 0)'

SectionEnd


; Optional Section for Bundled Python Runtime (if not handled by simply copying via extraResources)
; This section assumes Python runtime is copied to $INSTDIR\python by electron-builder
Section "Python Runtime Configuration" SecPython
    SetOutPath "$INSTDIR\python" ; This path should match where Python is bundled
    ; If specific PATH modifications are needed system-wide (requires admin, generally not recommended for user-specific installs)
    ; Or, the application itself should be configured to find this Python version.

    ; Example: Add Python to user's PATH (if user selected this option on a custom page)
    ; ${If} $AddToPathUserChoice == 1
    ;   EnVar::SetUserVar "PATH" "$INSTDIR\python;$INSTDIR\python\Scripts;%PATH%"
    ; ${EndIf}

    ; Create a batch file or script that sets up the environment for the app if needed
    ; FileOpen $0 "$INSTDIR\launch-with-python-env.bat" w
    //           token: ${{ secrets.CODECOV_TOKEN }} # If using Codecov
      #   directory: ./coverage/ # Path to coverage results

  build-and-release:
    name: Build & Release Electron App
    if: startsWith(github.ref, 'refs/tags/v') # Only run on version tags
    needs: lint-test # Ensure linting and tests pass before building
    runs-on: ${{ matrix.os }} # Build on multiple OS

    strategy:
      matrix:
        os: [macos-latest, ubuntu-latest, windows-latest]
        node-version: [18.x]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies (root and workspaces)
        run: npm install --workspaces --if-present && npm install

      # For macOS and Linux, ensure Python is available for potential native module builds or scripts
      # Windows runners usually have Python.
      - name: Setup Python (macOS & Linux)
        if: runner.os == 'macOS' || runner.os == 'Linux'
        uses: actions/setup-python@v4
        with:
          python-version: '3.9' # Or your target Python version for scripts

      - name: Build all packages (frontend, backend, electron main/preload)
        run: npm run build # This should trigger workspace builds as defined in root package.json

      - name: Package Electron application
        run: npm run dist # This should use electron-builder to create installers/packages
        env:
          # For code signing (macOS and Windows) - set these as encrypted secrets in GitHub repo settings
          CSC_LINK: ${{ secrets.CSC_LINK }} # Certificate link or base64 encoded cert
          CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }} # Certificate password
          # For notarization on macOS (if needed)
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          # For GitHub releases
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} # Automatically available

      - name: Upload Artifacts (Installers/Packages)
        uses: actions/upload-artifact@v3
        with:
          name: KSEB-Energy-Platform-${{ matrix.os }}
          path: | # Paths to the distributable files
            dist/packages/*.dmg
            dist/packages/*.exe
            dist/packages/*.AppImage
            dist/packages/*.deb
            dist/packages/*.rpm
            dist/packages/*.zip
            dist/packages/*.tar.gz
            dist/packages/latest*.yml # For auto-updater
            !dist/packages/*-unpacked/ # Exclude unpacked directories

      # Optional: Create a GitHub Release
      - name: Create GitHub Release
        if: success() && startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v1
        with:
          # tag_name: ${{ github.ref_name }} # Use the tag that triggered the workflow
          # name: Release ${{ github.ref_name }}
          body: |
            Release of version ${{ github.ref_name }}.
            See CHANGELOG.md for details.

            **Artifacts:**
            (Links will be automatically added by uploading to the release)
          draft: true # Create as a draft, manually publish later
          prerelease: contains(github.ref, '-beta') || contains(github.ref, '-alpha') # Mark as pre-release if tag contains -beta or -alpha
          files: | # Attach all built packages to the release
            dist/packages/*.dmg
            dist/packages/*.exe
            dist/packages/*.AppImage
            dist/packages/*.deb
            dist/packages/*.rpm
            dist/packages/*.zip
            dist/packages/*.tar.gz
            dist/packages/latest*.yml
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
//     FileWrite $0 "@echo off$\r$\n"
//     FileWrite $0 "set PATH=$INSTDIR\python;$INSTDIR\python\Scripts;%PATH%$\r$\n"
//     FileWrite $0 'start "" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe"$\r$\n'
//     FileClose $0
SectionEnd


;--------------------------------
; Uninstaller Section

Section "Uninstall"
  ; Remove files and directories
  RMDir /r "$INSTDIR" ; This removes everything including the uninstaller itself if it's in $INSTDIR

  ; Remove shortcuts
  Delete "$DESKTOP\${APP_PRODUCT_NAME}.lnk"
  Delete "$SMPROGRAMS\${MUI_STARTMENUPAGE_FOLDER}\${APP_PRODUCT_NAME}.lnk"
  RMDir "$SMPROGRAMS\${MUI_STARTMENUPAGE_FOLDER}" ; Remove folder if empty

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
  DeleteRegKey HKCR ".ksep"
  DeleteRegKey HKCR "${APP_ID}.ksepfile"

  ; Notify Shell of changes
  System::Call 'shell32::SHChangeNotify(i 0x8000000, i 0, i 0, i 0)'
SectionEnd

;--------------------------------
; Helper Functions (Examples)

; Function CheckPython
;   ; This is a complex task. A simple check:
;   ClearErrors
;   ExecWait '"python" --version' $0
;   IfErrors PathNotFound NoPython
;   StrCpy $PythonExe "python"
;   Goto PythonFound
; PathNotFound:
;   ClearErrors
;   ExecWait '"python3" --version' $0
;   IfErrors NoPython
;   StrCpy $PythonExe "python3"
;   Goto PythonFound
; NoPython:
//           token: ${{ secrets.CODECOV_TOKEN }} # If using Codecov
      #   directory: ./coverage/ # Path to coverage results

  build-and-release:
    name: Build & Release Electron App
    if: startsWith(github.ref, 'refs/tags/v') # Only run on version tags
    needs: lint-test # Ensure linting and tests pass before building
    runs-on: ${{ matrix.os }} # Build on multiple OS

    strategy:
      matrix:
        os: [macos-latest, ubuntu-latest, windows-latest]
        node-version: [18.x]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies (root and workspaces)
        run: npm install --workspaces --if-present && npm install

      # For macOS and Linux, ensure Python is available for potential native module builds or scripts
      # Windows runners usually have Python.
      - name: Setup Python (macOS & Linux)
        if: runner.os == 'macOS' || runner.os == 'Linux'
        uses: actions/setup-python@v4
        with:
          python-version: '3.9' # Or your target Python version for scripts

      - name: Build all packages (frontend, backend, electron main/preload)
        run: npm run build # This should trigger workspace builds as defined in root package.json

      - name: Package Electron application
        run: npm run dist # This should use electron-builder to create installers/packages
        env:
          # For code signing (macOS and Windows) - set these as encrypted secrets in GitHub repo settings
          CSC_LINK: ${{ secrets.CSC_LINK }} # Certificate link or base64 encoded cert
          CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }} # Certificate password
          # For notarization on macOS (if needed)
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_ID_PASSWORD: ${{ secrets.APPLE_ID_PASSWORD }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          # For GitHub releases
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} # Automatically available

      - name: Upload Artifacts (Installers/Packages)
        uses: actions/upload-artifact@v3
        with:
          name: KSEB-Energy-Platform-${{ matrix.os }}
          path: | # Paths to the distributable files
            dist/packages/*.dmg
            dist/packages/*.exe
            dist/packages/*.AppImage
            dist/packages/*.deb
            dist/packages/*.rpm
            dist/packages/*.zip
            dist/packages/*.tar.gz
            dist/packages/latest*.yml # For auto-updater
            !dist/packages/*-unpacked/ # Exclude unpacked directories

      # Optional: Create a GitHub Release
      - name: Create GitHub Release
        if: success() && startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v1
        with:
          # tag_name: ${{ github.ref_name }} # Use the tag that triggered the workflow
          # name: Release ${{ github.ref_name }}
          body: |
            Release of version ${{ github.ref_name }}.
            See CHANGELOG.md for details.

            **Artifacts:**
            (Links will be automatically added by uploading to the release)
          draft: true # Create as a draft, manually publish later
          prerelease: contains(github.ref, '-beta') || contains(github.ref, '-alpha') # Mark as pre-release if tag contains -beta or -alpha
          files: | # Attach all built packages to the release
            dist/packages/*.dmg
            dist/packages/*.exe
            dist/packages/*.AppImage
            dist/packages/*.deb
            dist/packages/*.rpm
            dist/packages/*.zip
            dist/packages/*.tar.gz
            dist/packages/latest*.yml
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
//   MessageBox MB_OK|MB_ICONINFORMATION "Python does not seem to be installed or not in PATH. The application might bundle its own Python or prompt you later."
//   StrCpy $PythonExe ""
// PythonFound:
//   ; $PythonExe now holds 'python' or 'python3' if found in PATH
//   ; The application should ideally use its bundled Python.
// FunctionEnd

// Function AddToPath
//   Push $0
//   Push $1
//   Push $2
//   ; $R0: Path to add
//   ; $R1: Current User (1) or All Users (0)
//   ClearErrors
//   ${If} $R1 == 1 ; Current User
//     ReadRegStr $0 HKCU "Environment" "Path"
//     StrCpy $1 "$R0;$0"
//     WriteRegExpandStr HKCU "Environment" "Path" $1
//   ${Else} ; All Users (requires Admin)
//     ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
//     StrCpy $1 "$R0;$0"
//     WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" $1
//   ${EndIf}
//   SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
//   Pop $2
//   Pop $1
//   Pop $0
// FunctionEnd

// Descriptions for sections (if using components page)
// !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
//  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Installs the main application files."
//  !insertmacro MUI_DESCRIPTION_TEXT ${SecPython} "Configures the bundled Python runtime environment (if applicable)."
// !insertmacro MUI_FUNCTION_DESCRIPTION_END
    #     sys.path.insert(0, backend_python_src)
    #     # Also add the parent of 'shared' if 'shared' is a package-like directory
    #     shared_parent = os.path.abspath(os.path.join(backend_python_src, '..'))
    #     if shared_parent not in sys.path:
    #         sys.path.insert(0, shared_parent)

    unittest.main(verbosity=2)
