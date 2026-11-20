# Página web · Análisis de accidentes de tránsito (Proyecto 3)

Abrir `index.html` con doble clic. No necesita internet ni instalar nada.

- `index.html`: estructura y textos de las 10 secciones.
- `css/estilos.css`: diseño (tema claro y oscuro).
- `js/datos.js`: cifras agregadas del modelo de Power BI (las mismas de `generar_graficas_accidentes.py` y del informe).
- `js/mapa-datos.js`: contorno de los estados de EE. UU. (us-atlas, proyección Albers).
- `js/graficas.js`: gráficas en SVG hechas a mano (barras, columnas, líneas, mapa).
- `js/app.js`: arma las gráficas, la vista de tabla, el menú y el modo exposición.

Para la exposición: botón **Exponer** o tecla **P** (pantalla completa), **→ / ←** para cambiar de sección y **Esc** para salir.

## Desplegar en Vercel

La página es estática: no requiere Node.js, compilación, base de datos ni variables de entorno. Las gráficas muestran datos agregados incluidos en `js/datos.js`; no consultan PostgreSQL ni actualizan automáticamente sus cifras.

1. Sube el repositorio `AnalisisAccidentesTransito` a GitHub (si aún no está publicado).
2. En Vercel, elige **Add New → Project** e importa ese repositorio.
3. En **Configure Project**, configura **Root Directory** como `pagina_web` (no la raíz del repositorio).
4. Selecciona **Framework Preset: Other**. Deja **Build Command** y **Output Directory** sin configurar; el archivo `index.html` está directamente en la carpeta raíz del sitio.
5. Pulsa **Deploy**. En futuras actualizaciones del repositorio, Vercel volverá a desplegar la página.

Alternativa con Vercel CLI: desde la raíz del repositorio ejecuta `vercel pagina_web` (o `vercel pagina_web --prod` para producción). La primera vez, sigue las preguntas de inicio de sesión y vinculación del proyecto. No configures el directorio raíz como toda la carpeta del repositorio: contiene scripts y documentos que no forman parte de la web.

Para comprobar el sitio antes de subirlo, ejecuta `python -m http.server 8000 --directory pagina_web` desde la raíz del repositorio y abre `http://localhost:8000/`. También puedes abrir `pagina_web/index.html` directamente.
