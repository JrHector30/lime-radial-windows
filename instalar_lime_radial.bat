@echo off
chcp 65001 >nul
echo ========================================================
echo       🍋 Instalador de Lime Radial para Windows
echo ========================================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\LimeRadial"

echo [1/4] Creando directorio de instalación en:
echo       %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo.
echo [2/4] Copiando archivos del programa...
if exist "dist\LimeRadial\LimeRadial.exe" (
    xcopy /E /I /Y "dist\LimeRadial\*" "%INSTALL_DIR%\" >nul
    set "EXE_TARGET=%INSTALL_DIR%\LimeRadial.exe"
) else (
    xcopy /E /I /Y "lime_radial" "%INSTALL_DIR%\lime_radial\" >nul
    copy /Y "run.py" "%INSTALL_DIR%\" >nul
    copy /Y "lime.ico" "%INSTALL_DIR%\" >nul
    copy /Y "iniciar_lime_silencioso.vbs" "%INSTALL_DIR%\" >nul
    set "EXE_TARGET=%INSTALL_DIR%\iniciar_lime_silencioso.vbs"
)

echo.
echo [3/4] Creando accesos directos en Menú Inicio y Escritorio...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s1 = $ws.CreateShortcut([Environment]::GetFolderPath('Programs') + '\Lime Radial.lnk'); " ^
    "if ('%EXE_TARGET%'.EndsWith('.exe')) { $s1.TargetPath = '%EXE_TARGET%'; } else { $s1.TargetPath = 'wscript.exe'; $s1.Arguments = '\"%EXE_TARGET%\"'; } " ^
    "$s1.IconLocation = '%INSTALL_DIR%\lime.ico,0'; " ^
    "$s1.Description = 'Lime Radial Windows'; " ^
    "$s1.Save(); " ^
    "$s2 = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Lime Radial.lnk'); " ^
    "if ('%EXE_TARGET%'.EndsWith('.exe')) { $s2.TargetPath = '%EXE_TARGET%'; } else { $s2.TargetPath = 'wscript.exe'; $s2.Arguments = '\"%EXE_TARGET%\"'; } " ^
    "$s2.IconLocation = '%INSTALL_DIR%\lime.ico,0'; " ^
    "$s2.Description = 'Lime Radial Windows'; " ^
    "$s2.Save();"

echo.
echo [4/4] Configurando inicio automático con Windows...
if "%EXE_TARGET:~-4%"==".exe" (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "LimeRadial" /t REG_SZ /d "\"%EXE_TARGET%\"" /f >nul
) else (
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "LimeRadial" /t REG_SZ /d "wscript.exe \"%EXE_TARGET%\"" /f >nul
)

echo.
echo ========================================================
echo   🎉 ¡Instalación completada con éxito!
echo   - Se ha añadido a tu Menú Inicio y Escritorio.
echo   - Se iniciará automáticamente al arrancar tu PC.
echo   - Ejecutando ahora en segundo plano...
echo ========================================================
echo.

if "%EXE_TARGET:~-4%"==".exe" (
    start "" "%EXE_TARGET%"
) else (
    wscript "%EXE_TARGET%"
)

timeout /t 3 >nul
