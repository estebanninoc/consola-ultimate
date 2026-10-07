#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL limpia en la barra de direcciones.

Corre DESPUES de meta.py. Para ese momento meta.py ya guardo los parametros
de campana en sessionStorage (window.CU_ATRIB = capturar()) y ya disparo el
pixel, asi que de ahi en adelante los parametros en la URL no sirven para
nada mas.

Este paso los borra de la barra. Se van SOLO las claves de seguimiento, las
mismas 8 que captura meta.py (la variable CLAVES ya existe en ese bloque y
aqui se reutiliza); cualquier otro parametro que la pagina necesite queda
intacto.

POR QUE: Facebook le agrega fbclid a TODO clic de anuncio y eso no se puede
apagar. El visitante aterriza y ve una URL larga y rara justo en el momento
en que esta decidiendo si confiar. Con esto ve the-gamebox.com pelado, y no
se pierde ni un dato de atribucion: ya estaban guardados un instante antes.

NO toca el pixel, NO toca el client_reference_id, NO toca los links de pago.

Es idempotente.
"""
import io
import os
import sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')
MARCA = 'CU-URL-LIMPIA v1'
ANCLA = 'window.CU_ATRIB = capturar();'

BLOQUE = '''

  /* == %s =====================================
     Los parametros ya quedaron guardados arriba, asi que se borran de la
     barra de direcciones. Se van SOLO las claves de seguimiento (CLAVES);
     cualquier otro parametro de la pagina se respeta. */
  try{
    var _u = new URL(location.href), _toco = false;
    CLAVES.forEach(function(k){
      if(_u.searchParams.has(k)){ _u.searchParams.delete(k); _toco = true; }
    });
    if(_toco && window.history && history.replaceState){
      history.replaceState(null, "", _u.pathname + (_u.search || "") + _u.hash);
    }
  }catch(e){}
''' % MARCA


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('url_limpia.py: no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    if MARCA in s:
        print('ya estaba aplicado (idempotente)')
        print('validaciones OK')
        return

    if ANCLA not in s:
        sys.exit('url_limpia.py: no se encontro el ancla "%s". '
                 'Tiene que correr DESPUES de meta.py.' % ANCLA)
    if s.count(ANCLA) != 1:
        sys.exit('url_limpia.py: el ancla aparece %d veces, se esperaba 1'
                 % s.count(ANCLA))

    s = s.replace(ANCLA, ANCLA + BLOQUE, 1)

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))

    # Si algo de esto falla, el build PARA: es preferible romper el deploy a
    # publicar la pagina con la medicion rota.
    fallos = []
    if s.count(MARCA) != 1:
        fallos.append('el bloque no quedo (hay %d)' % s.count(MARCA))
    if 'history.replaceState' not in s:
        fallos.append('falta history.replaceState')
    if 'window.CU_TRACK' not in s:
        fallos.append('se perdio la atribucion (CU_TRACK)')
    if 'fbevents.js' not in s:
        fallos.append('se perdio el pixel de Meta')
    if fallos:
        sys.exit('ERROR url_limpia.py:\n  - ' + '\n  - '.join(fallos))

    print('la barra de direcciones queda limpia; atribucion y pixel intactos')
    print('validaciones OK')


if __name__ == '__main__':
    main()
