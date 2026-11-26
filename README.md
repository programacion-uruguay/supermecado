# Precios Montevideo

Software de autoalimentación de precios de supermercados de Montevideo (Python + Playwright/VTEX API + SQLite) y página web comparadora en JavaScript (React + Vite).

## Supermercados incluidos
- **Tienda Inglesa** (adaptador Playwright)
- **Disco / Devoto / Géant / Tata** (adaptador VTEX API)
- **Frog / El Dorado** (adaptador Playwright)

## Estructura del proyecto
- `scraper/`: Motor de recolección de precios, adaptadores por supermercado, normalización por EAN/nombre y base SQLite (`data/precios.db`).
- `api/`: API REST en FastAPI para consultar productos, comparativas y disparar actualizaciones.
- `web/`: Aplicación web en JavaScript (React + Vite) con buscador, filtros y comparador de precios.

## Cómo ejecutarlo localmente

### 1. Instalar dependencias de Python
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Cargar datos iniciales o ejecutar el scraper
Para probar al instante con datos de ejemplo de Montevideo:
```bash
python -m scraper.run --demo
```

Para extraer precios reales desde las webs:
```bash
python -m scraper.run --queries "yerba canarias" "leche conaprole" "arroz saman"
```

Para dejar el software **autoalimentándose cada 6 horas**:
```bash
python -m scraper.run --schedule 6
```

### 3. Levantar la API en Python
```bash
uvicorn api.main:app --reload --port 8000
```

### 4. Levantar la página web en JavaScript
En otra terminal:
```bash
cd web
npm install
npm run dev
```
Abrí `http://localhost:5173` en tu navegador.

## Subir a GitHub
```bash
git init
git add .
git commit -m "Inicial: scraper Python + API FastAPI + web comparadora JS"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/precios-montevideo.git
git push -u origin main
```
