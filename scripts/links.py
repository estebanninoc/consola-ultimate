#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Links de pago, en un solo lugar. Desde 2026-08-05 el checkout es STRIPE
(Payment Links), ya no Hotmart.

construir.py trae los links embebidos en el HTML (los viejos de Hotmart).
Este script los reescribe sobre el HTML ya generado: para cambiar un link
basta con editar la tabla de abajo.

Cada clave es la combinacion que arma el carrito:
    principal                      solo el producto           $34.99
    principal+gold-pc              + Ultimate Leyenda         $59.98
    principal+gold-mob             + Pack Supremo Mobile      $59.98
    principal+gold-pc+gold-mob     los tres                   $74.99

⚙️ Los Payment Links de Stripe presentan el precio EN LA MONEDA LOCAL del
comprador (por IP): cada Price tiene currency_options con montos fijos en
14 monedas de LATAM, los MISMOS numeros que muestra la landing (ver
scripts/moneda.py). Landing y checkout son identicos por construccion.

Cuenta Stripe: acct_1RyEj5CraKX72R2s (Esteban).
Productos: prod_V19B3sZRqg3gAb (principal) · prod_V19nvh0bd93U7l (+leyenda)
           prod_V19nKER4LLNQIV (+supremo) · prod_V19n4xkjtHwXwe (todo)

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
    # MULTICONSOLA ULTIMATE RETRO — $34.99
    'principal': 'https://buy.stripe.com/5kQ9AS8nQ63ubEZ7y0fIs09',
    # + ULTIMATE LEYENDA — $59.98
    'principal+gold-pc': 'https://buy.stripe.com/5kQ8wO1ZsdvW6kFdWofIs0a',
    # + PACK SUPREMO MOBILE — $59.98
    'principal+gold-mob': 'https://buy.stripe.com/fZu9ASfQicrSbEZg4wfIs0b',
    # LOS TRES — $74.99
    'principal+gold-pc+gold-mob': 'https://buy.stripe.com/4gM4gy8nQfE4gZjaKcfIs0c',
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
