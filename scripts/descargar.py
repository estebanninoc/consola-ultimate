#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga los assets del CDN según assets-manifest.txt → assets/"""
import os, sys, requests

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}
os.makedirs('assets', exist_ok=True)

# Estos archivos se vuelven a descargar SIEMPRE (para restaurar los originales)
FORZAR = {
    '3ds-1-300x151_12_11zon.webp','dreamcast-300x151_9_11zon.webp','gc-1-300x151_8_11zon.webp',
    'genesis-300x151_3_11zon.webp','mame-1-300x151_10_11zon.webp','n64-300x151_13_11zon.webp',
    'pinballfx3-300x151_11_11zon.webp','ps2-4-300x151_4_11zon.webp','ps3-4-300x151_1_11zon.webp',
    'psp-300x151_6_11zon.webp','psx-300x151_5_11zon.webp','switch-7-300x151_7_11zon.webp',
    'wiiu-4-300x151_2_11zon.webp','xbox-1-300x151_14_11zon.webp',
    'hf_20260409_144831_3b1e2a92-9d05-476c-9547-430d3d0be464.png',
    'hf_20260422_135711_1842b168-0f74-4444-bd8a-afee06263b4f.png',
    'hf_20260422_134211_f1962cae-60d8-4f25-b6b0-9a97cf5986c3.png',
    'hf_20260422_130608_988292ad-ae42-45a9-a941-9041eb8c3d43.png',
    'hf_20260422_131342_cfb557df-febe-4b7d-93ed-6f76e8e1ba2f.png',
}

fallos = []
for line in open('assets-manifest.txt', encoding='utf-8'):
    line = line.strip()
    if not line: continue
    name, url = line.split('\t')
    dest = os.path.join('assets', name)
    if name not in FORZAR and os.path.exists(dest) and os.path.getsize(dest) > 0:
        continue
    try:
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        open(dest, 'wb').write(r.content)
        print('ok ', name)
    except Exception as e:
        print('FALLO', name, e)
        fallos.append(name)

# parchear url() relativos en los CSS del tema
for f in os.listdir('assets'):
    if f.endswith('.css'):
        p = os.path.join('assets', f)
        css = open(p, encoding='utf-8', errors='ignore').read()
        c2 = css.replace('url(./sparkle.gif)', 'url(sparkle.gif)')
        c2 = c2.replace('url(./', 'url(https://consolaultimate.shop/cdn/shop/t/17/assets/')
        if c2 != css:
            open(p, 'w', encoding='utf-8').write(c2)

if fallos:
    print('ADVERTENCIA: fallaron', len(fallos), 'archivos:', fallos)
    if len(fallos) > 5: sys.exit(1)
