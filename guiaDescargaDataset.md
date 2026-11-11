# Guia de descarga y limpieza del dataset

## 1. Descarga del dataset

Comandos a ejecutar en orden (desde la raiz del proyecto):

```powershell
python -m venv ambiente

ambiente\scripts\activate
# si no funciona:
ambiente\bin\activate

pip install kagglehub

python .\extraction.py
```

El archivo queda en `data/us_accidents/US_Accidents_March23.csv` (~2.85 GB, 7.7 millones de filas).

## 2. Limpieza con PySpark

### Requisitos

- Python 3.10 a 3.13 (probado con **3.12**).
- Java 17 o superior (probado con Java 25).
- PySpark 4.x.

```powershell
py -3.12 -m pip install -r requirements.txt
```

En Windows, Spark necesita `winutils.exe` y `hadoop.dll` para escribir en disco.
No estan incluidos en el repo. Colocalos en `tools/hadoop/bin/` o en
`%USERPROFILE%\.hadoop\bin\` (por ejemplo los de
[cdarlint/winutils](https://github.com/cdarlint/winutils), carpeta `hadoop-3.3.6`);
el script configura `HADOOP_HOME` automaticamente. Si prefieres una instalacion
propia, define `HADOOP_HOME` antes de ejecutar.

### Ejecucion

```powershell
py -3.12 clean_accidents.py
```

Salidas:

- `data/us_accidents_clean/US_Accidents_March23_clean.csv` (CSV unico limpio).
- `data/us_accidents_clean/reporte_calidad.csv` (metricas de calidad antes y despues).

### Opciones

| Opcion | Descripcion |
| --- | --- |
| `--input RUTA` | CSV de entrada (por defecto el descargado). |
| `--out RUTA` | CSV de salida. |
| `--report RUTA` | Reporte de calidad en CSV. |
| `--threads N` | Hilos locales de Spark (por defecto 4). |
| `--driver-memory 6g` | Heap del driver de Spark (por defecto 4g). |
| `--parts N` | Particiones de escritura antes de fusionar en un solo CSV (por defecto 4). |
| `--keep-duplicates` | No eliminar registros repetidos del mismo accidente. |
| `--multiline` | Solo si el CSV tuviera saltos de linea dentro de campos entre comillas. |

### Reglas de limpieza aplicadas

1. **Duplicados**: elimina el mismo accidente reportado varias veces
   (misma hora de inicio y mismas coordenadas); conserva una fila.
2. **Texto**: recorta espacios y convierte `NULL`, `N/A`, `NA`, `-`, `UNKNOWN`, etc. en nulos.
3. **Tipos**: convierte fechas a timestamp, numeros a `double`, Severity a entero y
   los indicadores a booleano.
4. **Rangos imposibles** (se convierten en nulo, sin borrar la fila):
   temperatura y sensacion termica fuera de -60..130 F, viento > 100 mph,
   presion fuera de 20..33 inHg, visibilidad > 20 mi, precipitacion > 10 in,
   distancia > 100 mi.
5. **Duraciones**: si `End_Time` es anterior a `Start_Time` o supera 24 h, se anula
   `End_Time` y las coordenadas finales.
6. **Codigos**: `State` a 2 letras mayusculas, `Zipcode` a 5 digitos,
   `Country` = US, `Wind_Direction` al catalogo de 16 rumbos.
7. **Filas inservibles**: se descartan las que no tienen ID, hora de inicio,
   coordenadas de inicio, severidad o estado.

Los nulos que ya existian en el dataset (por ejemplo `End_Lat`/`End_Lng` en ~44 %
de las filas, o columnas meteorologicas) se conservan como nulos: no se imputan.
