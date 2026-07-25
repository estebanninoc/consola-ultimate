#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga la página original y la convierte en landing standalone (index.html)."""
import re, os, urllib.parse, requests
from bs4 import BeautifulSoup, Comment

URL = 'https://consolaultimate.shop/products/consola-ultimate%e2%84%a2'
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'}

html = requests.get(URL, headers=UA, timeout=60).text
print('página original:', len(html), 'bytes')

nombres_assets = set()
for line in open('assets-manifest.txt', encoding='utf-8'):
    if line.strip():
        nombres_assets.add(line.split('\t')[0].strip())

soup = BeautifulSoup(html, 'html.parser')

# 1) fuera TODOS los <script src> (Shopify, analytics, apps)
for s in soup.find_all('script', src=True):
    s.decompose()

# 2) scripts inline: conservar los de la página + JSON-LD
KEEP = ('cu-drawer','MAIN_PRICE','cuPlayer','LOGOS_1','faqToggle','cu-test-vp',
        'cu-s4-track','cu-s5-track','cuFaqToggle','RESEÑAS','activeAnimations',"VID='")
for s in soup.find_all('script'):
    stype = (s.get('type') or '').lower()
    txt = s.string or s.get_text() or ''
    if 'ld+json' in stype: continue
    if any(k in txt for k in KEEP): continue
    s.decompose()

# 3) módulos Shopify irrelevantes
for sel in ('cart-notification', 'predictive-search',
            'link[rel="modulepreload"]', 'link[href*="chpmgr"]',
            'link[rel="preload"][href*="cdn/fonts"]',
            'link[rel="preload"][as="script"]', 'script[id="shopify-features"]'):
    for el in soup.select(sel):
        el.decompose()

html2 = str(soup)

# 4) URLs del CDN → assets/ locales
def localizar(m):
    name = urllib.parse.unquote(m.group('name'))
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    if safe in nombres_assets:
        return 'assets/' + safe
    return m.group(0)

html2 = re.sub(r'(?:https:)?//(?:cdn\.shopify\.com/s/files/1/0806/0207/1291/files|cdn\.shopify\.com/s/files/1/0715/1137/5955/files|consolaultimate\.shop/cdn/shop/files)/(?P<name>[^"\'\s\\),?]+)(\?[^"\'\s\\),]*)?', localizar, html2)
html2 = re.sub(r'(?:https:)?//consolaultimate\.shop/cdn/shop/t/17/assets/(?P<name>[^"\'\s\\),?]+)(\?[^"\'\s\\),]*)?', localizar, html2)

# 5) formularios del carrito neutralizados
html2 = re.sub(r'<form([^>]*)action="[^"]*/cart/add"', r'<form onsubmit="return false"\1', html2)

# 6) checkout → links de pago
config = '''<script>
/* ═════════════════════════════════════════════════════════════
   ⚙️ ESTEBAN: PEGA AQUÍ TUS LINKS DE PAGO ⚙️
   (Mercado Pago, Wompi, Bold, Hotmart, PayPal...)
   ═════════════════════════════════════════════════════════════ */
var LINKS_DE_PAGO = {
  principal: "",   /* MULTICONSOLA ULTIMATE RETRO™ — $39.99 */
  b0: "",          /* JUEGOS DE PS4            — $27.99 */
  b1: "",          /* JUEGOS DE PS5            — $29.60 */
  b2: "",          /* JUEGOS DE XBOX SERIES    — $25.60 */
  "gold-pc": "",   /* ULTIMATE LEYENDA         — $34.00 */
  b3: "",          /* RETRO GAMING MOBILE      — $16.80 */
  b4: "",          /* ULTRA RETRO MOBILE       — $19.20 */
  b5: "",          /* PS2 MOBILE               — $17.60 */
  "gold-mob": ""   /* PACK SUPREMO MOBILE      — $35.20 */
};
var LINKS_COMBO = {};  /* opcional: "principal+b0": "https://..." */
</script>'''
html2 = html2.replace('</head>', config + '\n</head>', 1)

m = re.search(r'window\.cuGoCheckout = function\(\)\{[\s\S]*?\n\};', html2)
assert m, 'cuGoCheckout no encontrado'
nuevo = '''window.cuGoCheckout = function(){
  var keys = ['principal'];
  document.querySelectorAll('#cu-drawer .cu-bump-cb:checked').forEach(function(cb){
    keys.push(cb.id.replace('cu-cb-','').replace('cu-cb',''));
  });
  var link = (LINKS_COMBO && LINKS_COMBO[keys.join('+')]) || LINKS_DE_PAGO.principal || '';
  if(!link){
    var btn = document.getElementById('cu-btn'); var prev = btn.innerHTML;
    btn.innerHTML = '⚠️ Configura tu link de pago';
    setTimeout(function(){ btn.innerHTML = prev; }, 3000);
    return;
  }
  window.location.href = link;
};'''
html2 = html2[:m.start()] + nuevo + html2[m.end():]
html2 = re.sub(r"fetch\('/cart/clear\.js'[\s\S]*?\.catch\(function\(e\)\{[^}]*\}\);", '', html2)

# 7) sessionStorage a prueba de visores restringidos
html2 = html2.replace("var end = parseInt(sessionStorage.getItem(KEY), 10);",
  "var end = 0; try{ end = parseInt(sessionStorage.getItem(KEY), 10); }catch(e){}")
html2 = html2.replace("sessionStorage.setItem(KEY, end);",
  "try{ sessionStorage.setItem(KEY, end); }catch(e){}")

# 8) respaldo de videos al abrir como archivo local (inerte en hosting)
html2 = html2.replace("""var sec = document.querySelector('.cu-vid-section');\n          if(sec) sec.style.display = 'none';""",
"""if(location.protocol==='file:'){ if(window.cuFallbackEmbed) cuFallbackEmbed(); return; }\n          var sec = document.querySelector('.cu-vid-section');\n          if(sec) sec.style.display = 'none';""")
html2 = html2.replace("var cuPlayer = null;",
"""var cuPlayer = null;\n  window.cuFallbackEmbed = function(){\n    var box=document.querySelector('.cu-vid-box');\n    if(box && !document.getElementById('cu-local-note')){\n      var n=document.createElement('div'); n.id='cu-local-note';\n      n.style.cssText='position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;background:#0a0f0a;color:#7dffb0;font-family:Inter,sans-serif;font-size:14px;text-align:center;padding:20px;cursor:pointer;z-index:5;';\n      n.innerHTML='▶️ Ver el video en YouTube<br><span style=\"font-size:11px;opacity:.6\">(el video se reproduce aquí mismo cuando la página está en internet)</span>';\n      n.onclick=function(){window.open('https://www.youtube.com/watch?v=1UXRfTPXWl8','_blank');};\n      box.appendChild(n);\n      var c=document.querySelector('.cu-controles'); if(c) c.style.display='none';\n    }\n  };""", 1)
for v in ['vps2','vps4','vps5','vxbox','vxbs']:
    html2 = re.sub(r'window\.'+v+r'Play=function\(\)\{(\s*)if\(started\)return;',
        'window.'+v+"Play=function(){\\1if(location.protocol==='file:'){window.open('https://www.youtube.com/watch?v='+VID,'_blank');return;}\\1if(started)return;", html2)

open('index.html', 'w', encoding='utf-8').write(html2)
print('index.html generado:', len(html2), 'bytes')
assert 'assets/' in html2
assert 'LINKS_DE_PAGO' in html2
