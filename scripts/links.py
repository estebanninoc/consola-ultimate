#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Links de pago de Hotmart, en un solo lugar.

construir.py trae los links embebidos en el HTML. Cuando cambia una oferta en
Hotmart hay que actualizarlos, y meterse a construir.py (17 KB, hace muchas
otras cosas) es incomodo y arriesgado. Este script los reescribe sobre el
HTML ya generado: para cambiar un link basta con editar la tabla de abajo.

Cada clave es la combinacion que arma el carrito:
    principal                      solo el producto
    principal+gold-pc              + Ultimate Leyenda
    principal+gold-mob             + Pack Supremo Mobile
    principal+gold-pc+gold-mob     los tres

⚙️ Se usa el formato con `off=` a proposito: fija la oferta concreta, asi el
precio no cambia aunque mañana se toque el precio base del producto. Y el
`checkoutMode=10` activa el checkout tematizado (el negro con tu marca);
sin el, el comprador ve el checkout clasico de Hotmart.

Solo se reescriben las claves que aparezcan aqui. Lo que no este, se queda
como lo dejo construir.py.

Es idempotente.
"""
import io
import os
import re
import sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')

LINKS = {
    # principal + Ultimate Leyenda — $59.98
    # producto 8238333 · oferta "Base price" (zes3wsqi) · checkout con marca publicado
    'principal+gold-pc': 'https://pay.hotmart.com/P106988065E?off=zes3wsqi&checkoutMode=10',
}


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    cambiados, faltantes = [], []
    for clave, url in LINKS.items():
        patron = re.compile(r'("%s":\s*)"[^"]*"' % re.escape(clave))
        nuevo, n = patron.subn(lambda m: m.group(1) + '"' + url + '"', s)
        if n == 0:
            faltantes.append(clave)
            continue
        s = nuevo
        cambiados.append('%s  ->  %s  (x%d)' % (clave, url, n))

    for c in cambiados:
        print('   ' + c)
    if faltantes:
        sys.exit('ERROR links.py: no se encontraron en el HTML: ' + ', '.join(faltantes))

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))

    for clave, url in LINKS.items():
        if url not in s:
            sys.exit('ERROR links.py: %s no quedo aplicado' % clave)
    print('validaciones OK')


if __name__ == '__main__':
    main()
