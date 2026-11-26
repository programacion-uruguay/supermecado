@echo off
title Actualizar Precios Montevideo y Subir a GitHub
cd /d "%~dp0"

echo ==================================================
echo 1/4 - Extrayendo precios actualizados (9 supermercados)...
echo ==================================================
.\.venv\Scripts\python.exe -m scraper.run
if errorlevel 1 (
    echo [ERROR] Fallo el scraper.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo 2/4 - Compilando pagina web (web/dist)...
echo ==================================================
cd web
call npm run build
if errorlevel 1 (
    echo [ERROR] Fallo la compilacion de la web.
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo ==================================================
echo 3/4 - Guardando nuevos datos en Git...
echo ==================================================
git add web/public/data/catalog.json
git diff --cached --quiet
if %errorlevel%==0 (
    echo No hay cambios nuevos en los precios para subir.
) else (
    for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set FECHA=%%c-%%b-%%a
    git commit -m "Actualizacion automatica de precios %date% %time:~0,5%"
    echo.
    echo ==================================================
    echo 4/4 - Subiendo a GitHub (origin/main)...
    echo ==================================================
    git push origin main
    if errorlevel 1 (
        echo [ERROR] No se pudo subir a GitHub.
        pause
        exit /b 1
    )
)

echo.
echo Listo! Precios actualizados y subidos a GitHub.
pause
