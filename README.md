# CONTIX — App Web Contable

## Deploy en Railway (gratis)

### Paso 1 — Subir a GitHub
1. Creá un repositorio NUEVO en GitHub (privado o público)
   - Nombre sugerido: `contix-app`
2. Subí todos estos archivos al repositorio:
   - `app.py`
   - `parsers.py`
   - `excel_gen.py`
   - `requirements.txt`
   - `Procfile`
   - `railway.toml`
   - `static/index.html`

### Paso 2 — Deploy en Railway
1. Entrá a **railway.app** y creá una cuenta (gratis)
2. Clic en **"New Project"**
3. Elegí **"Deploy from GitHub repo"**
4. Seleccioná el repositorio `contix-app`
5. Railway detecta automáticamente que es Python y lo deploya

### Paso 3 — Obtener la URL
1. Una vez deployado, clic en el proyecto
2. Clic en **"Settings"** → **"Networking"** → **"Generate Domain"**
3. Tu URL queda lista: `contix-app.up.railway.app`

### Listo
- Abrís la URL desde cualquier dispositivo
- Los datos se guardan en la base de datos del servidor
- Funciona desde celular, tablet, cualquier computadora

## Estructura de archivos
```
contix-app/
├── app.py              ← Backend Flask (API REST)
├── parsers.py          ← Parsers bancarios (Santander, Galicia, etc.)
├── excel_gen.py        ← Generador de Excel
├── requirements.txt    ← Librerías Python
├── Procfile            ← Configuración servidor
├── railway.toml        ← Configuración Railway
└── static/
    └── index.html      ← Frontend (la app visual)
```

## Bancos soportados
- Santander Argentina ✓
- Galicia / Galicia Más ✓
- BBVA Francés ✓
- ICBC ✓
- Banco Ciudad ✓
- Bapro (Banco Provincia) ✓
- Columbia ✓
- Mercado Pago ✓
- Itaú, Credicoop, Macro, Nación (modo genérico) ✓
