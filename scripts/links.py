#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Links de pago, en un solo lugar. Desde 2026-08-05 el checkout es STRIPE
(Payment Links), ya no Hotmart.

construir.py trae los links embebidos en el HTML (los viejos de Hotmart).
Este script los reescribe sobre el HTML ya generado: para cambiar un link
basta con editar la tabla de abajo.

Cada clave es la combinacion que arma el carrito:
    principal                      solo el producto            $9.99
    principal+gold-pc              + Ultimate Leyenda         $19.98
    principal+gold-mob             + Pack Supremo Mobile      $19.98
    principal+gold-pc+gold-mob     los tres                   $25.99

⚙️ Los Payment Links de Stripe presentan el precio EN LA MONEDA LOCAL del
comprador (por IP): cada Price tiene currency_options con montos fijos en
14 monedas de LATAM, los MISMOS numeros que muestra la landing (ver
scripts/moneda.py). Landing y checkout son identicos por construccion.

Cuenta Stripe: acct_1U1cFpEIkdT1ZKlo ("The Gamebox" — el checkout y el
extracto bancario dicen THE GAMEBOX / THEGAMEBOX.COM, no un nombre personal).
Productos: prod_V1fo9bI44Mgs5x (principal) · prod_V1foosCz7VA9lL (+leyenda)
           prod_V1foRduqk71z6b (+supremo) · prod_V1fonN8D2qKFGk (todo)

'principal' vive en LINKS_DE_PAGO con la clave SIN comillas; las
combinaciones viven en LINKS_COMBO con la clave entre comillas. Por eso
se intentan los dos patrones.

Solo se reescriben las claves que aparezcan aqui. Lo que no este, se queda
como lo dejo construir.py (los links sueltos de bonos ya no son alcanzables:
el carrito fuerza packs completos).

Es idempotente.
"""
import io
import os
import re
import sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')

LINKS = {
    # MULTICONSOLA ULTIMATE RETRO — $9.99
    'principal': 'https://buy.stripe.com/8x2dR94zQ0AQfI031F7kc04',
    # + ULTIMATE LEYENDA — $19.98
    'principal+gold-pc': 'https://buy.stripe.com/5kQcN55DU6Ze3Zi0Tx7kc05',
    # + PACK SUPREMO MOBILE — $19.98
    'principal+gold-mob': 'https://buy.stripe.com/8x200j7M2cjygM4au77kc06',
    # LOS TRES — $25.99
    'principal+gold-pc+gold-mob': 'https://buy.stripe.com/3cI6oHaYe83i67q6dR7kc07',
}


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    cambiados, faltantes = [], []
    for clave, url in LINKS.items():
        # clave entre comillas ("principal+gold-pc": "...") o sin comillas (principal: "...")
        patrones = [
            re.compile(r'("%s":\s*)"[^"]*"' % re.escape(clave)),
            re.compile(r'(\b%s:\s*)"[^"]*"' % re.escape(clave)),
        ]
        total = 0
        for patron in patrones:
            s, n = patron.subn(lambda m: m.group(1) + '"' + url + '"', s)
            total += n
        if total == 0:
            faltantes.append(clave)
            continue
        cambiados.append('%s  ->  %s  (x%d)' % (clave, url, total))

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

# 2026-08-05: pagina /gracias agregada; los Payment Links redirigen alli tras el pago.
# 2026-08-06: migracion a la cuenta "The Gamebox" (acct_1U1cFpEIkdT1ZKlo): 4 links
#             nuevos con las mismas currency_options fijas y redirect a /gracias.
# 2026-08-07: /gracias avisa que el correo puede tardar 5-10 min (la gente es impaciente
#             y el correo real tardo un poco en la compra de prueba). Commit toca este
#             archivo solo para disparar el workflow (paths: scripts/**).
# 2026-08-07 (2): aviso de /gracias sube a 10-15 min + enfasis en revisar SPAM (un
#             cliente real lo recibio en spam). Toque para disparar el workflow.
# 2026-08-11: REBAJA GENERAL — todo a 9.99 / combos 19.98 / trio 25.99. Prices y
#             Payment Links nuevos en la misma cuenta; tabla de monedas regenerada.
