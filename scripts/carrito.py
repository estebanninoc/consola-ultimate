#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arregla el TOTAL del carrito, que se quedaba en dolares.

El index.html trae DOS versiones del carrito. La vieja define su propio
updateTotals() que formatea en dolares ('$' + n.toFixed(2)). La nueva lo
reemplaza en window... pero NO reemplaza openCart, y ese openCart viejo
quedo capturando por clausura el updateTotals viejo:

    window.openCart = function(){
      ...
      updateTotals();      <- el de dolares, no el convertido
    };

Resultado visible: los precios de los productos salian en pesos, pero al
abrir el carrito el TOTAL y el "Ahorras" se sobrescribian en dolares.
Se notaba porque al marcar y desmarcar un pack el total se corregia solo.

La solucion no es tocar el carrito viejo (lo regenera construir.py en cada
build), sino envolver openCart para repintar justo despues de abrirlo.

Es idempotente.
"""
import io
import os
import sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')
MARCA = 'CU-CARRITO v1'

BLOQUE = r'''<script>
/* ══════════════════════════════════════════════════════════
   CU-CARRITO v1 — el TOTAL tambien en moneda local

   openCart viene de la version vieja del carrito y llama a su propio
   updateTotals (en dolares), pisando el total ya convertido. Lo
   envolvemos para repintar despues de abrir el drawer.
   ══════════════════════════════════════════════════════════ */
(function(){
  "use strict";
  var _open = window.openCart;
  if(typeof _open !== "function") return;
  window.openCart = function(){
    var r = _open.apply(this, arguments);
    try{ if(typeof window.CU_REPAINT === "function") window.CU_REPAINT(); }catch(e){}
    return r;
  };
})();
</script>
'''


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    if MARCA in s:
        i = s.find(MARCA)
        ini = s.rfind('<script>', 0, i)
        fin = s.find('</script>', i)
        if ini != -1 and fin != -1:
            s = s[:ini] + s[fin + len('</script>\n'):]
            print('bloque anterior retirado (idempotente)')

    j = s.rfind('</body>')
    if j == -1:
        sys.exit('no se encontro </body>')
    s = s[:j] + BLOQUE + s[j:]

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))

    if s.count(MARCA) != 1:
        sys.exit('ERROR carrito.py: el bloque no quedo bien inyectado')
    if 'window.CU_REPAINT' not in s:
        sys.exit('ERROR carrito.py: falta CU_REPAINT — ¿corrio moneda.py antes?')
    print('validaciones OK')


if __name__ == '__main__':
    main()
