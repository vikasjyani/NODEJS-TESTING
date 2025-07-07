import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd

# Attempt to import PyPSA, but don't fail if it's not available when this util module is imported.
# The actual PyPSA operations in pypsa_runner.py or pypsa_analysis.py will handle the ImportError.
try:
    import pypsa
except ImportError:
    pypsa = None # Allows type hinting and basic checks without failing import of this util file

logger = logging.getLogger(__name__)

def load_pypsa_network(network_path: Union[str, Path]) -> Optional['pypsa.Network']:
    """
    Loads a PyPSA network from a NetCDF file.

    Args:
        network_path (Union[str, Path]): The path to the .nc network file.

    Returns:
        Optional[pypsa.Network]: The loaded PyPSA Network object, or None if loading fails.
    """
    if pypsa is None:
        logger.error("PyPSA library is not installed. Cannot load network.")
        return None

    network_path = Path(network_path)
    if not network_path.exists():
        logger.error(f"PyPSA network file not found at: {network_path}")
        return None

    try:
        network = pypsa.Network(network_path)
        logger.info(f"Successfully loaded PyPSA network from: {network_path}")
        return network
    except Exception as e:
        logger.error(f"Error loading PyPSA network from {network_path}: {e}", exc_info=True)
        return None

def get_network_summary(network: 'pypsa.Network') -> Dict[str, Any]:
    """
    Generates a basic summary of a PyPSA network.

    Args:
        network (pypsa.Network): The PyPSA Network object.

    Returns:
        Dict[str, Any]: A dictionary containing summary information.
    """
    if network is None:
        return {"error": "Network object is None."}

    summary = {
        "name": network.name or "Unnamed Network",
        "snapshots": {
            "count": len(network.snapshots),
            "first": network.snapshots[0].isoformat() if len(network.snapshots) > 0 else None,
            "last": network.snapshots[-1].isoformat() if len(network.snapshots) > 0 else None,
            "freq": pd.infer_freq(network.snapshots) if len(network.snapshots) > 1 else None,
        },
        "components": {
            "buses": len(network.buses),
            "generators": len(network.generators),
            "loads": len(network.loads),
            "lines": len(network.lines),
            "transformers": len(network.transformers),
            "storage_units": len(network.storage_units),
            "links": len(network.links),
            "stores": len(network.stores),
            "carriers": network.carriers.to_dict(orient='index') if not network.carriers.empty else {},
        },
        "objective_value": float(network.objective) if hasattr(network, 'objective') and pd.notnull(network.objective) else None,
        "investment_periods": network.investment_periods.tolist() if hasattr(network, 'investment_periods') and network.investment_periods is not None else None,
    }
    return summary

def add_carrier_if_not_exists(network: 'pypsa.Network', carrier_name: str, **attributes: Any):
    """
    Adds a carrier to the network if it doesn't already exist.

    Args:
        network (pypsa.Network): The PyPSA Network object.
        carrier_name (str): The name of the carrier to add.
        **attributes: Attributes for the new carrier (e.g., co2_emissions, color).
    """
    if pypsa is None:
        logger.warning("PyPSA not imported, cannot add carrier.")
        return

    if carrier_name not in network.carriers.index:
        default_attrs = {
            'co2_emissions': 0, # Default to 0 if not specified
            'color': '#778899', # Default color (LightSlateGray)
            'nice_name': carrier_name.replace('_', ' ').title()
        }
        final_attributes = {**default_attrs, **attributes}
        network.add("Carrier", carrier_name, **final_attributes)
        logger.debug(f"Added new carrier '{carrier_name}' to network with attributes: {final_attributes}")
    else:
        logger.debug(f"Carrier '{carrier_name}' already exists.")


# Example: Helper to parse solver options from config for PyPSA's lopf function
def format_solver_options_for_pypsa(solver_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Formats solver options from a general config structure to what PyPSA's LOPF might expect.
    This is highly dependent on the chosen solver and its specific option names.
    PyPSA's `Network.lopf()` passes `solver_options` directly to the solver interface (e.g., pyomo).

    Args:
        solver_config (Optional[Dict[str, Any]]): Solver options from the main configuration.
            Example: {"solver": "cbc", "time_limit": 3600, "optimality_gap": 0.01}

    Returns:
        Dict[str, Any]: Formatted options, e.g., for CBC via Pyomo: {'timelimit': '3600', 'mipgap': '0.01'}
    """
    if not solver_config:
        return {}

    pypsa_opts: Dict[str, Any] = {}

    # Common mappings - these might need adjustment based on the specific solver
    # Pyomo often expects string values for these solver options.
    if "time_limit" in solver_config:
        pypsa_opts['timelimit'] = str(solver_config["time_limit"]) # e.g., for CBC, GLPK, Gurobi via Pyomo

    if "optimality_gap" in solver_config:
        # Name can vary: 'mipgap' (CBC, Gurobi), 'mip_gap_abs', 'ratio' (GLPK)
        # This needs to be conditional on the solver or use a more generic Pyomo option if available.
        # For now, assuming 'mipgap' is common for MIP solvers.
        pypsa_opts['mipgap'] = str(solver_config["optimality_gap"])

    if "threads" in solver_config:
        pypsa_opts['threads'] = str(solver_config["threads"]) # e.g. Gurobi, CPLEX

    # Add other specific solver option translations as needed
    # For example, if solver_config has a generic "log_level", map it to solver-specific option.
    # if solver_config.get("solver") == "gurobi" and "log_file" in solver_config:
    #    pypsa_opts['logfile'] = solver_config["log_file"]

    logger.debug(f"Formatted PyPSA solver options: {pypsa_opts} from input: {solver_config}")
    return pypsa_opts


if __name__ == '__main__':
    # Example Usage
    logging.basicConfig(level=logging.DEBUG) # Set to DEBUG for util testing

    if pypsa:
        # Create a dummy network for testing utils
        test_net = pypsa.Network()
        test_net.name = "Test Utility Network"
        test_net.set_snapshots(pd.date_range("2023-01-01", "2023-01-01 02:00:00", freq="H"))

        add_carrier_if_not_exists(test_net, "gas", co2_emissions=0.2, color="gray")
        add_carrier_if_not_exists(test_net, "solar", co2_emissions=0, color="yellow")
        add_carrier_if_not_exists(test_net, "gas") # Should log that it already exists

        logger.info(f"Carriers in test network:\n{test_net.carriers}")

        net_summary = get_network_summary(test_net)
        logger.info(f"Network Summary:\n{json.dumps(net_summary, indent=2)}")

        solver_conf_example = {"solver": "cbc", "time_limit": 1800, "optimality_gap": 0.05, "threads": 4}
        formatted_opts = format_solver_options_for_pypsa(solver_conf_example)
        logger.info(f"Formatted solver options for PyPSA: {formatted_opts}")

        # To test load_pypsa_network, you'd need a sample .nc file.
        # dummy_nc_path = Path("dummy_network_for_util_test.nc")
        # if dummy_nc_path.exists():
        #     loaded_network = load_pypsa_network(dummy_nc_path)
        #     if loaded_network:
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
    ; FileWrite $0 "@echo off$\r$\n"
    ; FileWrite $0 "set PATH=$INSTDIR\python;$INSTDIR\python\Scripts;%PATH%$\r$\n"
    ; FileWrite $0 'start "" "$INSTDIR\${APP_PRODUCT_FILENAME}.exe"$\r$\n'
    ; FileClose $0
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
;   MessageBox MB_OK|MB_ICONINFORMATION "Python does not seem to be installed or not in PATH. The application might bundle its own Python or prompt you later."
;   StrCpy $PythonExe ""
; PythonFound:
;   ; $PythonExe now holds 'python' or 'python3' if found in PATH
;   ; The application should ideally use its bundled Python.
; FunctionEnd

; Function AddToPath
;   Push $0
;   Push $1
;   Push $2
;   ; $R0: Path to add
;   ; $R1: Current User (1) or All Users (0)
;   ClearErrors
;   ${If} $R1 == 1 ; Current User
;     ReadRegStr $0 HKCU "Environment" "Path"
;     StrCpy $1 "$R0;$0"
;     WriteRegExpandStr HKCU "Environment" "Path" $1
;   ${Else} ; All Users (requires Admin)
;     ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path"
;     StrCpy $1 "$R0;$0"
;     WriteRegExpandStr HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "Path" $1
;   ${EndIf}
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
//                 logger.info(f"Summary of loaded dummy network: {get_network_summary(loaded_network)}")
        # else:
        #     logger.warning(f"Skipping load_pypsa_network test as {dummy_nc_path} does not exist.")

    else:
        logger.warning("PyPSA library not found. Skipping PyPSA utility tests.")

    logger.info("pypsa_utils.py example run complete.")
