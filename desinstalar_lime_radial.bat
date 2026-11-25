@echo off
chcp 65001 >nul
echo ========================================================
echo       🍋 Desinstalador de Lime Radial Windows
echo ========================================================
echo.

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\LimeRadial"

echo [1/3] Cerrando procesos de Lime Radial si están activos...
taskkill /F /IM LimeRadial.exe >nul 2>&1

echo [2/3] Eliminando del inicio automático de Windows...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "LimeRadial" /f >nul 2>&1

echo [3/3] Eliminando accesos directos y carpeta de instalación...
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Lime Radial.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\Lime Radial.lnk" >nul 2>&1

if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%" >nul 2>&1
)

echo.
echo ✔ Lime Radial ha sido desinstalado completamente de tu equipo.
pause
