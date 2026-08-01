#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imagenes livianas: PNG/JPG pesados -> WebP, y srcset de verdad.

Problema que resuelve:
  1. Cinco PNG sin comprimir pesaban 22,7 MB (el 56% de todo el sitio).
  2. Los srcset tenian once medidas distintas apuntando TODAS al mismo
     archivo, porque construir.py colapsa las variantes del CDN de Shopify
     a un unico archivo local. Un celular que necesita 246 px se bajaba
     los 5,3 MB completos.
  3. Las imagenes de los bonos viven dentro del carrito, que arranca
     oculto: al abrirlo se disparaban 18 MB de golpe, justo en el momento
     de mayor intencion de compra.

Que hace:
  - Convierte a WebP (calidad 82) todo PNG/JPG que pase de UMBRAL bytes.
  - Genera las medidas reales del srcset, para que cada dispositivo baje
    solo lo que necesita.
  - Pone loading="lazy" y decoding="async" a las imagenes de mas abajo.
  - Precarga en segundo plano las imagenes del carrito cuando el navegador
    esta libre, para que el drawer abra instantaneo.

Defensivo a proposito: si una conversion falla se conserva el archivo
original y el build sigue. Solo se reescribe el HTML de lo que si convirtio.

Es idempotente.
"""
import io
import os
import re
import sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')
ASSETS = 'assets'
MARCA = 'CU-IMG v1'

CALIDAD = 82          # WebP: equilibrio entre peso y fidelidad
UMBRAL = 200 * 1024   # solo se tocan los archivos que pasen de 200 KB
ANCHO_MAX = 1920      # nadie necesita mas que esto en una landing
MAX_VARIANTES = 6     # cuantas medidas de srcset se generan como maximo

try:
    from PIL import Image
except ImportError:
    print('AVISO: Pillow no disponible, se omite la optimizacion de imagenes')
    sys.exit(0)


def convertir(ruta):
    """PNG/JPG -> WebP. Devuelve el nombre nuevo, o None si no se pudo."""
    base, ext = os.path.splitext(ruta)
    destino = base + '.webp'
    if os.path.exists(destino) and os.path.getmtime(destino) >= os.path.getmtime(ruta):
        return os.path.basename(destino)
    try:
        im = Image.open(ruta)
        im.load()
        if im.mode in ('P', 'LA', 'PA'):
            im = im.convert('RGBA')
        elif im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGB')
        if im.width > ANCHO_MAX:
            alto = int(im.height * ANCHO_MAX / im.width)
            im = im.resize((ANCHO_MAX, alto), Image.LANCZOS)
        im.save(destino, 'WEBP', quality=CALIDAD, method=6)
        return os.path.basename(destino)
    except Exception as e:
        print('   ! no se pudo convertir %s (%s)' % (os.path.basename(ruta), e))
        return None


def variante(nombre_webp, ancho):
    """Crea una copia reducida a `ancho` px. Devuelve el nombre, o None."""
    ruta = os.path.join(ASSETS, nombre_webp)
    base, _ = os.path.splitext(nombre_webp)
    salida = '%s-%dw.webp' % (base, ancho)
    destino = os.path.join(ASSETS, salida)
    if os.path.exists(destino):
        return salida
    try:
        im = Image.open(ruta)
        im.load()
        if im.width <= ancho:
            return nombre_webp          # no tiene sentido agrandar
        alto = int(im.height * ancho / im.width)
        im.resize((ancho, alto), Image.LANCZOS).save(
            destino, 'WEBP', quality=CALIDAD, method=6)
        return salida
    except Exception as e:
        print('   ! no se pudo generar la variante %dw (%s)' % (ancho, e))
        return None


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    if not os.path.isdir(ASSETS):
        print('AVISO: no hay carpeta assets/, se omite')
        return

    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    # ── 1. convertir los pesados ────────────────────────────────────
    cambios = {}
    ahorro = 0
    for nombre in sorted(os.listdir(ASSETS)):
        if not nombre.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        ruta = os.path.join(ASSETS, nombre)
        try:
            peso = os.path.getsize(ruta)
        except OSError:
            continue
        if peso < UMBRAL:
            continue
        nuevo = convertir(ruta)
        if not nuevo:
            continue
        try:
            nuevo_peso = os.path.getsize(os.path.join(ASSETS, nuevo))
        except OSError:
            continue
        cambios[nombre] = nuevo
        ahorro += peso - nuevo_peso
        print('   %-52s %6.2f MB -> %5.2f MB' % (nombre[:52], peso / 1048576.0, nuevo_peso / 1048576.0))

    for viejo, nuevo in cambios.items():
        s = s.replace('assets/' + viejo, 'assets/' + nuevo)
    if cambios:
        print('   %d imagenes convertidas · %.2f MB menos' % (len(cambios), ahorro / 1048576.0))

    # ── 2. srcset de verdad ─────────────────────────────────────────
    arreglados = [0]

    def rehacer(m):
        cuerpo = m.group(1)
        pares = re.findall(r'(assets/[^\s,]+)\s+(\d+)w', cuerpo)
        if len(pares) < 2:
            return m.group(0)
        urls = set(u for u, _ in pares)
        if len(urls) != 1:
            return m.group(0)              # ya es un srcset real
        url = pares[0][0]
        nombre = url.split('/')[-1]
        if not os.path.exists(os.path.join(ASSETS, nombre)):
            return m.group(0)
        anchos = sorted(set(int(w) for _, w in pares))
        if len(anchos) > MAX_VARIANTES:     # repartidos, no los primeros
            paso = len(anchos) / float(MAX_VARIANTES)
            anchos = [anchos[int(i * paso)] for i in range(MAX_VARIANTES)]
        nuevas = []
        for w in anchos:
            v = variante(nombre, w)
            if v:
                nuevas.append('assets/%s %dw' % (v, w))
        if len(nuevas) < 2:
            return m.group(0)
        arreglados[0] += 1
        return 'srcset="%s"' % ', '.join(nuevas)

    s = re.sub(r'srcset="([^"]*assets/[^"]*)"', rehacer, s)
    if arreglados[0]:
        print('   %d srcset regenerados con medidas reales' % arreglados[0])

    # ── 3. lazy loading en lo que esta mas abajo ────────────────────
    tags = [m for m in re.finditer(r'<img\b[^>]*>', s)]
    puestos = 0
    for m in reversed(tags[8:]):            # las 8 primeras se dejan como estan
        tag = m.group(0)
        nuevo = tag
        if 'loading=' not in nuevo:
            nuevo = nuevo[:-1].rstrip() + ' loading="lazy">'
        if 'decoding=' not in nuevo:
            nuevo = nuevo[:-1].rstrip() + ' decoding="async">'
        if nuevo != tag:
            s = s[:m.start()] + nuevo + s[m.end():]
            puestos += 1
    if puestos:
        print('   lazy/decoding agregado a %d imagenes' % puestos)

    # ── 4. precargar las imagenes del carrito cuando el navegador este libre ──
    if MARCA in s:
        i = s.find(MARCA)
        ini = s.rfind('<script>', 0, i)
        fin = s.find('</script>', i)
        if ini != -1 and fin != -1:
            s = s[:ini] + s[fin + len('</script>\n'):]

    bump = []
    for m in re.finditer(r'<img\b[^>]*class="[^"]*cu-bump-img[^"]*"[^>]*>', s):
        src = re.search(r'src="([^"]+)"', m.group(0))
        if src and src.group(1) not in bump:
            bump.append(src.group(1))

    if bump:
        lista = ',\n    '.join('"%s"' % u for u in bump)
        bloque = ('<script>\n'
                  '/* ══════════════════════════════════════════════════════════\n'
                  '   CU-IMG v1 — precarga de las imagenes del carrito\n'
                  '   Viven dentro del drawer, que arranca oculto: sin esto se\n'
                  '   descargaban todas de golpe al abrirlo, en el peor momento.\n'
                  '   Se traen cuando el navegador esta libre, sin competir con\n'
                  '   la primera pintura.\n'
                  '   ══════════════════════════════════════════════════════════ */\n'
                  '(function(){\n'
                  '  var IMGS = [\n    ' + lista + '\n  ];\n'
                  '  function precargar(){\n'
                  '    IMGS.forEach(function(u){ var i = new Image(); i.decoding = "async"; i.src = u; });\n'
                  '  }\n'
                  '  function arrancar(){\n'
                  '    if(window.requestIdleCallback) requestIdleCallback(precargar, {timeout:4000});\n'
                  '    else setTimeout(precargar, 1500);\n'
                  '  }\n'
                  '  if(document.readyState === "complete") arrancar();\n'
                  '  else window.addEventListener("load", arrancar);\n'
                  '})();\n'
                  '</script>\n')
        j = s.rfind('</body>')
        if j == -1:
            sys.exit('no se encontro </body>')
        s = s[:j] + bloque + s[j:]
        print('   precarga en segundo plano de %d imagenes del carrito' % len(bump))

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))
    print('validaciones OK')


if __name__ == '__main__':
    main()
