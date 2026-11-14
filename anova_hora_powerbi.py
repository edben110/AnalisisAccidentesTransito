"""Visual de Python para la tabla ANOVA_Hora de Power BI Desktop.

Agrega Hora, Severity y Frecuencia al visual como campos sin resumir.
Pega este archivo en el editor. Power BI entrega los datos en `dataset`.
"""

from math import fsum


def calcular_anova(filas):
    """Calcula el ANOVA de un factor a partir de conteos de casos."""
    frecuencias = [[0] * 4 for _ in range(24)]
    for hora, severidad, conteo in filas:
        if (hora not in range(24) or severidad not in range(1, 5)
                or conteo < 0 or conteo != int(conteo)):
            raise ValueError("Se esperan horas de 0 a 23, niveles de 1 a 4 y conteos enteros.")
        frecuencias[int(hora)][int(severidad) - 1] += int(conteo)

    tamanos = [sum(conteos) for conteos in frecuencias]
    if any(n == 0 for n in tamanos):
        raise ValueError("Se necesitan registros de las 24 horas. Revisa los filtros del visual.")

    niveles = range(1, 5)
    medias = [
        fsum(nivel * conteo for nivel, conteo in zip(niveles, conteos)) / n
        for conteos, n in zip(frecuencias, tamanos)
    ]
    total = sum(tamanos)
    media_global = fsum(n * media for n, media in zip(tamanos, medias)) / total
    sc_entre = fsum(n * (media - media_global) ** 2 for n, media in zip(tamanos, medias))
    sc_dentro = fsum(
        conteo * (nivel - media) ** 2
        for conteos, media in zip(frecuencias, medias)
        for nivel, conteo in zip(niveles, conteos)
    )
    gl_entre = len(medias) - 1
    gl_dentro = total - len(medias)
    if gl_dentro <= 0 or sc_dentro <= 0:
        raise ValueError("El ANOVA requiere variación dentro de los grupos y grados de libertad residuales.")
    estadistico = (sc_entre / gl_entre) / (sc_dentro / gl_dentro)
    eta2 = sc_entre / (sc_entre + sc_dentro)
    return medias, total, estadistico, gl_entre, gl_dentro, eta2


def dibujar(dataset):
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from scipy.stats import f

    columnas = ["Hora", "Severity", "Frecuencia"]
    faltantes = set(columnas) - set(dataset.columns)
    if faltantes:
        raise ValueError("Agrega al visual los campos sin resumir: " + ", ".join(sorted(faltantes)))

    datos = dataset[columnas].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(datos.to_numpy(dtype=float)).all():
        raise ValueError("Hay valores vacíos o no finitos en los campos de ANOVA_Hora.")
    medias, total, estadistico, gl1, gl2, eta2 = calcular_anova(
        datos.itertuples(index=False, name=None)
    )
    p = f.sf(estadistico, gl1, gl2)
    p_texto = "p < 0,001" if p < 0.001 else f"p = {p:.3f}".replace(".", ",")
    decision = "Se rechaza H₀" if p < 0.05 else "No se rechaza H₀"

    fig, ax = plt.subplots(figsize=(11, 4.8))
    horas = np.arange(24)
    ax.plot(horas, medias, color="#17578B", marker="o", markersize=3.8, linewidth=1.8)
    ax.set_title("Severidad media por hora de inicio", loc="left", fontweight="bold")
    ax.set_xticks(horas)
    ax.set_xticklabels([f"{hora:02d}" for hora in horas])
    ax.set_xlim(-0.4, 23.4)
    ax.set_xlabel("Hora de inicio")
    ax.set_ylabel("Severidad media (códigos de 1 a 4)")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)
    resumen = f"N = {total:,}   |   F({gl1}, {gl2:,}) = {estadistico:.2f}   |   η² = {eta2:.5f}"
    resumen = resumen.translate(str.maketrans(",.", ".,"))
    fig.text(0.10, 0.085, resumen + "   |   " + p_texto, fontsize=10)
    fig.text(0.10, 0.035, decision + " con α = 0,05. Eje vertical ampliado.", fontsize=9)
    fig.subplots_adjust(left=0.10, right=0.98, top=0.89, bottom=0.25)
    plt.show()


if "dataset" in globals():
    dibujar(dataset)
