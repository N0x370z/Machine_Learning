# Unreal ejecuta este archivo al abrir el proyecto.
#  - Normal: arranca el receptor en vivo (receptor_handmotion.py). Al quedar
#    importado como módulo, el socket y el tick viven mientras el editor
#    esté abierto.
#  - HM_CAPTURA=1 (docs/imagenes_unreal.py, editor sin ventana): renderiza
#    las imágenes de la documentación y cierra el editor
#    (capturar_imagenes.py).
import os

if os.environ.get("HM_CAPTURA") == "1":
    import capturar_imagenes  # noqa: F401
else:
    import receptor_handmotion  # noqa: F401
