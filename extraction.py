import kagglehub
from pathlib import Path
import sys


def descargar_dataset():
    nombre_dataset = "sobhanmoosavi/us-accidents"
    carpeta_destino = Path("./data/us_accidents")

    try:
        print("=" * 60)
        print("DESCARGA DEL DATASET US ACCIDENTS")
        print("=" * 60)

        # Crear la carpeta de destino
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        print(f"\nDataset: {nombre_dataset}")
        print(f"Carpeta de destino: {carpeta_destino.resolve()}")
        print("\nIniciando descarga...")

        # Descargar la versión más reciente
        path = kagglehub.dataset_download(
            nombre_dataset,
            output_dir=str(carpeta_destino)
        )

        ruta_dataset = Path(path)

        print("\nDescarga completada correctamente.")
        print(f"Ruta del dataset: {ruta_dataset.resolve()}")

        # Mostrar los archivos descargados
        archivos = [
            archivo
            for archivo in ruta_dataset.rglob("*")
            if archivo.is_file()
        ]

        if archivos:
            print("\nARCHIVOS DESCARGADOS")
            print("-" * 60)

            espacio_total = 0

            for archivo in archivos:
                tamano_mb = archivo.stat().st_size / (1024 ** 2)
                espacio_total += archivo.stat().st_size

                print(f"Archivo: {archivo.name}")
                print(f"Tamaño: {tamano_mb:.2f} MB")
                print(f"Ruta: {archivo.resolve()}")
                print("-" * 60)

            print(f"\nTotal de archivos: {len(archivos)}")
            print(
                f"Espacio total: "
                f"{espacio_total / (1024 ** 3):.2f} GB"
            )
        else:
            print(
                "\nNo se encontraron archivos en la ruta indicada."
            )

    except Exception as error:
        print("\nERROR DURANTE LA DESCARGA")
        print(f"Detalles: {error}")
        print(
            "\nVerifica tu conexión a Internet, "
            "la instalación de kagglehub y los permisos de Kaggle."
        )
        sys.exit(1)


if __name__ == "__main__":
    descargar_dataset()