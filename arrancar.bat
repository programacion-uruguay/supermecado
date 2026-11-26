@echo off
title Precios Montevideo - Iniciando...
cd /d "%~dp0"

echo Iniciando API de Python (puerto 8000)...
start "API Precios Montevideo" cmd /k ".\.venv\Scripts\uvicorn.exe api.main:app --reload --port 8000"

echo Iniciando Web JavaScript (puerto 5173)...
start "Web Super Pepito" cmd /k "cd web && npm run dev"

echo Iniciando Scraper autoalimentable (cada 6 horas)...
start "Scraper Almacen" cmd /k ".\.venv\Scripts\python.exe -m scraper.run --schedule 6"

timeout /t 4 /nobreak >nul
start http://localhost:5173

echo.
echo Todo iniciado! Se abrieron 3 ventanas (API, Web y Scraper) y el navegador en http://localhost:5173
pause
