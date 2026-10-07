#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post-proceso de index.html.

El workflow llama a ESTE archivo y a ninguno mas. Para agregar un paso nuevo
al build basta con sumarlo a la lista PASOS de abajo: no hay que tocar
.github/workflows/desplegar.yml nunca mas.

(El conector de GitHub no puede escribir en .github/workflows/ — ese permiso
lo declara la propia GitHub App, no se puede conceder desde la cuenta. Por eso
el workflow tiene un unico paso fijo que apunta aca.)

Los pasos corren EN ORDEN y sobre el mismo index.html que dejo construir.py.
Si alguno falla, el build se detiene: es preferible romper el deploy a
publicar la pagina con los precios o la medicion rotos.
"""
import os
import subprocess
import sys

PASOS = [
    'scripts/precios.py',   # precios reales + descuento del pack completo
    'scripts/links.py',     # links de pago de Hotmart
    'scripts/imagenes.py',  # PNG pesados -> WebP, srcset real, lazy loading
    'scripts/moneda.py',    # precios en moneda local, instantaneos
    'scripts/carrito.py',   # el TOTAL del carrito tambien en moneda local
    'scripts/meta.py',      # Meta Pixel + atribucion de anuncios
]


def main():
    if not os.path.exists('index.html'):
        sys.exit('post.py: no existe index.html — ¿corrio construir.py?')

    for paso in PASOS:
        if not os.path.exists(paso):
            print('── %s (no existe, se omite)' % paso)
            continue
        print('── %s' % paso)
        r = subprocess.run([sys.executable, paso])
        if r.returncode != 0:
            sys.exit('post.py: fallo %s (codigo %d)' % (paso, r.returncode))

    print('post-proceso completo')


if __name__ == '__main__':
    main()
