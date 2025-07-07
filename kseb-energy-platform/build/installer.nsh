; KSEB Energy Futures Platform - Custom NSIS Installer Script
; This script enhances the default electron-builder NSIS installer.

!include "MUI2.nsh"
!include "FileFunc.nsh" ; For GetParent
!include "LogicLib.nsh" ; For If/Else logic
!include "x64.nsh"      ; For 64-bit system checks

;--------------------------------
; Variables

Var PythonDir
Var PythonExe
Var AddToPathCurrentSetting
Var AddToPathUserChoice

;--------------------------------
; Interface Configuration

!define MUI_ABORTWARNING ; Warns user if they abort setup
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico" ; Default, electron-builder overrides with assets/icon.ico
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico" ; Default

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page (optional - if you have a license.txt in build resources)
; !define MUI_LICENSEPAGE_CHECKBOX
; !insertmacro MUI_PAGE_LICENSE "path\to\license.txt"
; Components page (if you have optional components)
; !insertmacro MUI_PAGE_COMPONENTS
; Directory page (installation path)
!insertmacro MUI_PAGE_DIRECTORY

; Custom Page for Python Path Configuration (Optional - advanced)
; Page custom nsPythonPage nsPythonPageLeave "Python Configuration"

; InstFiles page (shows installation progress)
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_PRODUCT_FILENAME}.exe" ; APP_PRODUCT_FILENAME is set by electron-builder
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.md" ; If you want to show a README
!define MUI_FINISHPAGE_LINK "KSEB Energy Futures Platform Website"
!define MUI_FINISHPAGE_LINK_LOCATION "https://www.kseb.in/" ; Placeholder
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Language

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections & Functions

Function .onInit
  ; Set the installation scope (per-user or per-machine)
  ; electron-builder typically handles this with nsis.perMachine option
  ; If perMachine is true: SetShellVarContext all
  ; Else: SetShellVarContext current

  ; Check for existing Python (example - this is complex and might be better handled post-install by the app)
  ; Call CheckPython
FunctionEnd

; Custom Page function example (if used)
; Function nsPythonPage
;   !insertmacro MUI_HEADER_TEXT "Python Configuration" "Configure Python settings for the application."
;   ; Add custom UI elements here using nsDialogs or InstallOptions
;   nsDialogs::Create 1018
;   Pop $0 ; HWND
;   ; ...
;   nsDialogs::Show
; FunctionEnd
; Function nsPythonPageLeave
;   ; Read values from custom page
; FunctionEnd


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
;   SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
;   Pop $2
;   Pop $1
;   Pop $0
; FunctionEnd

; Descriptions for sections (if using components page)
; !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
;  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Installs the main application files."
;  !insertmacro MUI_DESCRIPTION_TEXT ${SecPython} "Configures the bundled Python runtime environment (if applicable)."
; !insertmacro MUI_FUNCTION_DESCRIPTION_END
