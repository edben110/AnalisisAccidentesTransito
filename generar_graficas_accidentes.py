"""Reproduce las gráficas del informe de accidentes con los datos de Power BI.

Uso:
    python generar_graficas_accidentes.py
    python generar_graficas_accidentes.py --salida figuras --originales informe.docx

Genera SVG sin dependencias externas. Con --originales también exporta los
PNG originales, incluidas las capturas, desde el Word indicado.
"""

import argparse
from html import escape
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import ZipFile

# Conteos del modelo de Power BI. Las filas de ANOVA_Hora están ordenadas
# de 00:00 a 23:00 y sus cuatro columnas corresponden a Severity 1, 2, 3 y 4.
FRECUENCIAS = (
    (341, 81686, 10568, 6194),
    (236, 71433, 8819, 4097),
    (452, 67444, 9671, 4218),
    (413, 59450, 9788, 4228),
    (2588, 113144, 28177, 5158),
    (2988, 165767, 38167, 6490),
    (5386, 300879, 72308, 7650),
    (8763, 445735, 99841, 8752),
    (8959, 437825, 99072, 8690),
    (2661, 268758, 65941, 8088),
    (2370, 254779, 60022, 7675),
    (2202, 263916, 60562, 7652),
    (1650, 257416, 59026, 8362),
    (2124, 286834, 63879, 8871),
    (2342, 328372, 70480, 9218),
    (3056, 384691, 85534, 9927),
    (4796, 422758, 100394, 10135),
    (4942, 416987, 102677, 9925),
    (3664, 308972, 80551, 9291),
    (2164, 210763, 54160, 7630),
    (826, 159986, 40038, 6967),
    (664, 135450, 31353, 6587),
    (457, 118599, 26316, 6093),
    (347, 93052, 12779, 5683),
)
MENSUALES = (
    1, 983, 6298, 18042, 17481, 30408, 45527, 56218, 54495, 55488, 64865, 59471,
    55582, 51542, 56701, 47427, 40752, 46042, 42973, 80637, 76646, 74757, 69887, 71289,
    74688, 71138, 74055, 72343, 76203, 67585, 65492, 76044, 73011, 86798, 81773, 69850,
    78976, 74112, 69043, 72653, 73567, 65246, 67933, 74898, 87282, 106351, 81525, 97640,
    91286, 84956, 82535, 81147, 82323, 95440, 35079, 37136, 72738, 109018, 139227, 143107,
    136736, 139413, 84544, 83887, 94115, 120533, 104169, 110990, 122764, 119197, 138211, 154402,
    116222, 139116, 119898, 161948, 131764, 115756, 127695, 138810, 125718, 76612, 117951, 169980,
    143507, 50097, 27046,
)
PUNTOS = (
    (-81.47, 28.45, 3026), (-73.93, 40.85, 2953),
    (-118.10, 33.94, 2941), (-118.25, 34.06, 2841), (-118.47, 34.16, 2826),
)
CATEGORIAS = (
    ("03", "estados", "Accidentes por estado · 7 principales",
     ("California", "Florida", "Texas", "Carolina del Sur", "Nueva York",
      "Carolina del Norte", "Virginia"),
     (1629140, 780896, 563542, 371783, 314278, 310600, 274114)),
    ("04", "ciudades", "Accidentes por ciudad · 7 principales",
     ("Houston", "Miami", "Los Angeles", "Charlotte", "Dallas", "Austin", "Orlando"),
     (163308, 152837, 147740, 130787, 126061, 94254, 91888)),
    ("07", "dia_semana", "Accidentes por día de la semana",
     ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"),
     (1132197, 1207313, 1224942, 1228130, 1273461, 606933, 513815)),
    ("08", "severidad", "Accidentes por nivel de severidad",
     ("Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4"), (64391, 5654696, 1290123, 177581)),
    ("09", "clima", "Accidentes por condición climática · categorías seleccionadas",
     ("Fair", "Mostly Cloudy", "Clear", "Cloudy", "Partly Cloudy", "Overcast", "Light Rain"),
     (2308827, 948789, 804782, 740845, 653811, 381008, 330472)),
    ("10", "via", "Accidentes por tipo de vía",
     ("Otra vía / sin clasificar", "Interestatal", "Ruta federal", "Ruta estatal"),
     (5175345, 1809680, 197339, 4427)),
    ("11", "vehiculos", "Menciones identificadas por tipo de vehículo",
     ("Autobús", "Camión", "Automóvil", "Motocicleta", "Bicicleta"),
     (22348, 8108, 3510, 775, 289)),
    ("12", "anios", "Accidentes por año",
     ("2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023 (ene–mar)"),
     (409277, 714235, 888980, 949226, 1053992, 1408961, 1541470, 220650)),
    ("14", "duracion", "Duración promedio por severidad (minutos)",
     ("Nivel 1", "Nivel 2", "Nivel 3", "Nivel 4", "Promedio general"),
     (45.90, 108.13, 67.69, 188.39, 102.24)),
)
AZUL = "#2773a7"
VERDE = "#00665d"
TINTA = "#253346"
REJILLA = "#d9e1e9"


def numero(value, decimals=0):
    return f"{value:,.{decimals}f}".translate(str.maketrans(",.", ".,"))


def etiqueta(x, y, contenido, size=17, anchor="start", bold=False):
    peso = "bold" if bold else "normal"
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
            f'text-anchor="{anchor}" font-weight="{peso}">{escape(str(contenido))}</text>')


def linea(x1, y1, x2, y2):
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{REJILLA}"/>'


def punto(x, y, color=AZUL):
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{color}"/>'


def guardar(path, titulo, alto, contenido):
    header = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="{alto}" '
              f'viewBox="0 0 1080 {alto}" role="img"><title>{escape(titulo)}</title>'
              '<rect width="100%" height="100%" fill="white"/>'
              f'<g font-family="Segoe UI, Arial, sans-serif" fill="{TINTA}">')
    path.write_text("\n".join([header, etiqueta(16, 31, titulo, 25, bold=True),
                               *contenido, "</g></svg>"]), encoding="utf-8")


def barras(path, titulo, categorias, valores, decimales=0, nota=""):
    maximo = max(valores)
    alto = 62 + 34 * len(valores)
    partes = [linea(250, 48, 250, alto-12)]
    for i, (nombre, valor) in enumerate(zip(categorias, valores)):
        y = 51 + 34*i
        ancho = 658 * valor / maximo
        color = VERDE if valor == maximo else AZUL
        partes.extend((etiqueta(16, y+18, nombre),
                       f'<rect x="250" y="{y}" width="{ancho:.3f}" height="24" fill="{color}"/>',
                       etiqueta(260+ancho, y+18, numero(valor, decimales))))
    if nota:
        alto += 25
        partes.append(etiqueta(16, alto-9, nota, 15))
    guardar(path, titulo, alto, partes)


def serie(path, titulo, valores, marcas, ticks, nota, columnas=False, decimales=0):
    x0, x1, y0, y1 = 85, 1040, 330, 57
    menor, mayor = ticks[0], ticks[-1]

    def escala_y(valor):
        return y0 - (y0-y1)*(valor-menor)/(mayor-menor)

    paso = (x1-x0) / len(valores)
    xs = [x0 + paso*(i+0.5) for i in range(len(valores))]
    ys = [escala_y(valor) for valor in valores]
    partes = []
    for tick in ticks:
        y = escala_y(tick)
        partes.extend((linea(x0, y, x1, y), etiqueta(74, y+6, numero(tick, decimales), 15, "end")))
    if columnas:
        ancho = paso * 0.65
        for x, y, v in zip(xs, ys, valores):
            color = VERDE if v == max(valores) else AZUL
            partes.append(f'<rect x="{x-ancho/2:.2f}" y="{y:.2f}" width="{ancho:.2f}" '
                          f'height="{y0-y:.2f}" fill="{color}"/>')
    else:
        pares = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(xs, ys))
        partes.append(f'<polyline points="{pares}" fill="none" stroke="{AZUL}" stroke-width="3"/>')
        if len(valores) <= 24:
            partes.extend(punto(x, y) for x, y in zip(xs, ys))
    partes.extend(etiqueta(xs[i], 355, marca, 15, "middle") for i, marca in marcas.items())
    partes.append(etiqueta(x0, 392, nota, 17))
    guardar(path, titulo, 413, partes)


def mapa(path):
    def x(lon):
        return 75 + (lon+125)*17

    def y(lat):
        return 324 - (lat-25)*13.5

    partes = []
    for lon in range(-120, -69, 10):
        partes.extend((linea(x(lon), 54, x(lon), 325), etiqueta(x(lon), 350, f"{-lon}° O", 16, "middle")))
    for lat in range(25, 46, 5):
        partes.extend((linea(74, y(lat), 1010, y(lat)), etiqueta(64, y(lat)+5, f"{lat}° N", 16, "end")))
    partes.extend(punto(x(lon), y(lat), VERDE) for lon, lat, _ in PUNTOS)
    partes.extend((
        etiqueta(x(-81.47)+13, y(28.45)+24, "Orlando  3.026"),
        etiqueta(x(-73.93)-14, y(40.85)+20, "Nueva York  2.953", anchor="end"),
        etiqueta(x(-118.10)+23, y(33.94)+8, "Los Angeles  2.941 / 2.841 / 2.826"),
        etiqueta(75, 390, "Las tres celdas de Los Angeles se superponen a esta escala.", 17),
    ))
    guardar(path, "Ubicación de las cinco celdas con más registros", 414, partes)


def reproducir(destino):
    for figura, archivo, titulo, nombres, valores in CATEGORIAS:
        nota = "Se excluyen 7.151.761 registros sin vehículo especificado (99,51 %)." if figura == "11" else ""
        barras(destino / f"{figura}_{archivo}.svg", titulo, nombres, valores,
               decimales=2 if figura == "14" else 0, nota=nota)

    totales = [sum(fila) for fila in FRECUENCIAS]
    medias = [sum(s*n for s, n in enumerate(fila, 1))/total
              for fila, total in zip(FRECUENCIAS, totales)]
    if sum(totales) != 7_186_791 or sum(MENSUALES) != sum(totales):
        raise ValueError("Los totales del ANOVA y la serie mensual deben coincidir.")
    horas = {i: f"{i:02d}" for i in range(24)}
    serie(destino / "06_horas.svg", "Total de accidentes por hora de inicio", totales,
          horas, [0, 150000, 300000, 450000, 600000], "Hora de inicio", columnas=True)
    anios = {i: str(2016+i//12) for i in range(0, len(MENSUALES), 12)}
    serie(destino / "13_meses.svg", "Accidentes por mes de inicio", MENSUALES, anios,
          [0, 45000, 90000, 135000, 180000], "Enero de 2016 a marzo de 2023")
    mapa(destino / "15_puntos_criticos.svg")
    serie(destino / "16_anova_severidad_hora.svg", "Severidad media por hora de inicio",
          medias, horas, [2.18, 2.20, 2.22, 2.24, 2.26],
          "Hora de inicio · Escala de 1 a 4 · Eje vertical ampliado", decimales=2)


def extraer_originales(docx, destino):
    destino.mkdir(parents=True, exist_ok=True)
    ns = {
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    with ZipFile(docx) as z:
        documento = ElementTree.fromstring(z.read("word/document.xml"))
        relaciones = ElementTree.fromstring(z.read("word/_rels/document.xml.rels"))
        rutas = {rel.get("Id"): rel.get("Target") for rel in relaciones}
        n = 0
        for objeto in documento.findall(".//wp:inline", ns) + documento.findall(".//wp:anchor", ns):
            propiedad = objeto.find("wp:docPr", ns)
            imagen = objeto.find(".//a:blip", ns)
            if propiedad is None or imagen is None:
                continue
            descripcion = propiedad.get("descr", "")
            if not descripcion.startswith("Figura "):
                continue
            figura = int(descripcion.split(".", 1)[0].split()[1])
            ruta = PurePosixPath(rutas[imagen.get(f"{{{ns['r']}}}embed")])
            nom = PurePosixPath(propiedad.get("name", ruta.name)).stem
            (destino / f"{figura:02d}_{nom}{ruta.suffix}").write_bytes(z.read(f"word/{ruta}"))
            n += 1
    return n


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("graficas_accidentes"))
    parser.add_argument("--originales", type=Path, metavar="INFORME.DOCX",
                        help="Exportar también las imágenes originales del Word.")
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    reproducir(args.salida)
    print(f"13 gráficas SVG en {args.salida.resolve()}")
    if args.originales:
        n = extraer_originales(args.originales, args.salida / "originales")
        print(f"{n} imágenes del Word exportadas en originales/")


if __name__ == "__main__":
    main()
