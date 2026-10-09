# ETL de Airbnb Bogotá

Proyecto académico para extraer Listings, Reviews y Calendar desde MongoDB,
explorar su calidad, transformarlos y cargarlos en SQLite y archivos Excel.
MongoDB es la fuente obligatoria del proceso; los CSV no se leen directamente
por el ETL.

## Requisitos previos

- Python 3.10 o superior.
- MongoDB local en ejecución.
- Las colecciones `Listings`, `Reviews` y `Calendar` importadas en una misma
  base de datos MongoDB.

## Instalación

Desde la carpeta raíz del proyecto, en PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y establece `AIRBNB_MONGODB_DATABASE` con el nombre real de la base
que contiene las tres colecciones. Si MongoDB no está en la URI local por
defecto, configura también `AIRBNB_MONGODB_URI`.

## Ejecución del ETL

```powershell
python -m src.main
```

También se pueden proporcionar los parámetros sin modificar `.env`:

```powershell
python -m src.main --mongo-uri mongodb://localhost:27017 --database airbnb_bogota
```

El proceso crea un log por ejecución en `logs/`, la base
`output/airbnb.sqlite` y un archivo XLSX por colección en `output/excel/`.
Cada tabla SQLite se verifica comparando el número de filas cargadas con el
DataFrame de origen.

## Exploración

Abre `notebooks/exploracion_airbnb.ipynb` desde la raíz del proyecto, selecciona
el entorno donde instalaste `requirements.txt` y ejecuta las celdas en orden. El
Notebook se conecta a la misma base configurada en `.env`; incluye perfilado,
calidad, distribuciones, valores atípicos, calendario mensual y hallazgos
generados desde los datos reales.

## Estructura

```text
src/          Extracción, transformación, carga y punto de entrada
notebooks/    Análisis exploratorio reproducible
tests/        Pruebas de transformación
logs/         Logs de ejecución
output/       SQLite y exportaciones XLSX (generados, no versionados)
```

## Transformaciones

- Elimina filas totalmente vacías y duplicados exactos; elimina columnas
  totalmente nulas y conserva nulos parciales para no descartar datos útiles.
- Aplana documentos anidados (por ejemplo, campos de host), serializa listas
  como JSON y deriva `amenities_count`.
- Convierte `price` a número quitando `$` y comas; los valores ilegibles se
  registran como advertencias y quedan nulos.
- Normaliza columnas `date` y `*_date` a `YYYY-MM-DD`. Para `date` deriva año,
  mes, día y trimestre.
- Categoriza los precios válidos en rangos bajo/medio/alto con terciles
  calculados sobre cada colección; si hay pocos precios distintos, reduce el
  número de rangos.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

## Informe e integrantes

El PDF final debe completarse después de ejecutar el EDA para incluir cifras,
gráficas y conclusiones verificables del dataset, además de la portada,
integrantes y responsabilidades del grupo. No se incluyen resultados de ejemplo
como si fueran hallazgos reales.
