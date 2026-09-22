from pathlib import Path
import vtracer

# Rutas de carpetas
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Crear la carpeta static si no existe
STATIC_DIR.mkdir(exist_ok=True)

# Extensiones a procesar
imagenes_png = list(BASE_DIR.glob("*.png")) + list(STATIC_DIR.glob("*.png"))

if not imagenes_png:
    print("No se encontraron archivos .png para convertir.")
else:
    for img_path in imagenes_png:
        # Excluir los logos institucionales complejos si prefieres dejarlos en PNG
        if "logo" in img_path.name.lower():
            continue

        archivo_svg_salida = STATIC_DIR / f"{img_path.stem}.svg"

        print(f"Vectorizando: {img_path.name} -> {archivo_svg_salida.name}...")

        vtracer.convert_image_to_svg_py(
            image_path=str(img_path),
            out_path=str(archivo_svg_salida),
            colormode="color",        # Mantener colores originales
            hierarchical="stacked",   # Curvas apiladas y limpias
            mode="spline",            # Curvas Bézier suaves
            filter_speckle=4,         # Eliminar ruido o píxeles sueltos
            color_precision=6,        # Precisión de color
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=10,
            splice_threshold=45,
            path_precision=3          # Redondear decimales para reducir peso
        )

    print("\n¡Conversión terminada! Los archivos .svg se guardaron en la carpeta /static.")