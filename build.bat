@echo off
title 🚀 Building WhatsApp Automation by CoderzWeb
color 0A

echo ============================================
echo   💬 WhatsApp Automation EXE Builder
echo   Powered by CoderzWeb
echo ============================================
echo.

REM Check Python installation
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Python not found! Please install Python 3.10+ and add it to PATH.
    pause
    exit /b
)

REM Install required dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt >nul

REM Clean previous builds
echo 🧹 Cleaning old build files...
rmdir /s /q build >nul 2>&1
rmdir /s /q dist >nul 2>&1
del app_ui.spec >nul 2>&1

REM Build EXE using PyInstaller
echo ⚙️ Building EXE (this may take a few minutes)...
pyinstaller --onefile --noconsole --icon=assets\icon.ico --add-data "whatsapp_auto.py;." app_ui.py

IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Build failed. Check for errors above.
    pause
    exit /b
)

REM Move and rename output
echo 📂 Moving executable to /dist folder...
mkdir dist >nul 2>&1
move /Y "dist\app_ui.exe" "dist\WhatsAppAutomation.exe" >nul 2>&1

echo.
echo ✅ Build complete!
echo --------------------------------------------
echo   📁 EXE location: dist\WhatsAppAutomation.exe
echo   🕹  Double-click to run your app
echo --------------------------------------------
echo.

pause
exit /b
