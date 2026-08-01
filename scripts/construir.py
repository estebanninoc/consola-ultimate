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
  principal: "https://pay.hotmart.com/N106875864F?off=srtfx2gy&checkoutMode=10",   /* MULTICONSOLA ULTIMATE RETRO™ — $34.99 */
  b0: "https://pay.hotmart.com/X106964889D?off=c7rnch8s",   /* JUEGOS DE PS4            — $27.99 */
  b1: "https://pay.hotmart.com/O106964911H?off=0vqlev44",   /* JUEGOS DE PS5            — $29.60 */
  b2: "https://pay.hotmart.com/F106964936U?off=8fkm1imy",   /* JUEGOS DE XBOX SERIES    — $25.60 */
  "gold-pc": "https://pay.hotmart.com/L106972133T?off=9zc6fnuq",   /* ULTIMATE LEYENDA         — $34.00 */
  b3: "https://pay.hotmart.com/F106971351O?off=x0logolr",   /* RETRO GAMING MOBILE      — $16.80 */
  b4: "https://pay.hotmart.com/Q106971374Q?off=moqagwmg",   /* ULTRA RETRO MOBILE       — $19.20 */
  b5: "https://pay.hotmart.com/M106971389O?off=fdqkpr2j",   /* PS2 MOBILE               — $17.60 */
  "gold-mob": "https://pay.hotmart.com/Y106972171P?off=7l2spaxx"   /* PACK SUPREMO MOBILE      — $35.20 */
};
/* LINKS_COMBO — rutas por combinación del carrito de la landing.
   La clave se arma con "principal" + los bonos marcados, en el orden del drawer:
     0 = Juegos PS4 · 1 = Juegos PS5 · 2 = Juegos Xbox · gold-pc = Ultimate Leyenda (Pack Juegos)
     3 = Retro Gaming Mobile · 4 = Ultra Retro Mobile · 5 = PS2 Mobile · gold-mob = Pack Supremo
   Ej.: "principal+0+2": "https://pay.hotmart.com/…"
   Si la combinación no está aquí, va al checkout del principal (que muestra
   los 8 bonos para replicar la selección) etiquetado con sck=<combinación>. */
var LINKS_COMBO = {
  "principal+0":        "https://pay.hotmart.com/D106973843E?off=5smsap7b",   /* MC + Juegos PS4          — $62.98 */
  "principal+1":        "https://pay.hotmart.com/R106973896Y?off=b50zd6k6",   /* MC + Juegos PS5          — $64.59 */
  "principal+2":        "https://pay.hotmart.com/Y106973920J?off=2795atqv",   /* MC + Juegos Xbox         — $60.59 */
  "principal+gold-pc":  "https://pay.hotmart.com/G106973941A?off=464flaar",   /* MC + Pack Juegos         — $68.99 */
  "principal+3":        "https://pay.hotmart.com/P106973964I?off=lb04939l",   /* MC + AAA                 — $51.79 */
  "principal+4":        "https://pay.hotmart.com/E106973981Q?off=doflyrog",   /* MC + BBB                 — $54.19 */
  "principal+5":        "https://pay.hotmart.com/A106974004P?off=nbamy7si",   /* MC + CCC                 — $52.59 */
  "principal+gold-mob": "https://pay.hotmart.com/S106974036W?off=tgm2hq2f",   /* MC + Pack a+b+c          — $70.19 */
  "principal+gold-pc+gold-mob": "https://pay.hotmart.com/T106974063L?off=wobycom3"   /* MC TODO       — $104.19 */
};
</script>'''
html2 = html2.replace('</head>', config + '\n</head>', 1)

m = re.search(r'window\.cuGoCheckout = function\(\)\{[\s\S]*?\n\};', html2)
assert m, 'cuGoCheckout no encontrado'
nuevo = '''window.cuGoCheckout = function(){
  var keys = ['principal'];
  document.querySelectorAll('#cu-drawer .cu-bump-cb:checked').forEach(function(cb){
    keys.push(cb.id.replace('cu-cb-','').replace('cu-cb',''));
  });
  var combo = keys.join('+');
  var link = (LINKS_COMBO && LINKS_COMBO[combo]) || LINKS_DE_PAGO.principal || '';
  if(!link){
    var btn = document.getElementById('cu-btn'); var prev = btn.innerHTML;
    btn.innerHTML = '⚠️ Configura tu link de pago';
    setTimeout(function(){ btn.innerHTML = prev; }, 3000);
    return;
  }
  /* etiqueta la venta en Hotmart con lo seleccionado en la landing (sck) */
  link += (link.indexOf('?') > -1 ? '&' : '?') + 'sck=' + encodeURIComponent(combo);
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

# 9) solo se venden los packs: bundles con miniaturas + precios en moneda local
solo_packs = '''<script>
(function(){
  var GRUPOS = { "gold-pc": [0,1,2], "gold-mob": [3,4,5] };
  function cbPack(key){ return document.getElementById("cu-cb-" + key); }
  function cbNum(i){ return document.getElementById("cu-cb" + i); }

  /* ── conversion de moneda por pais ── */
  function fmtMoney(usd){
    return (window.CU_FX && window.CU_FX.fmt) ? window.CU_FX.fmt(usd) : "$" + usd.toFixed(2);
  }
  function leer(sel){
    var e = document.querySelector(sel); if(!e) return 0;
    if(e.dataset && e.dataset.usd) return parseFloat(e.dataset.usd) || 0;
    return parseFloat(e.textContent.replace(/[^0-9.]/g, "")) || 0;
  }
  function repintarPrecios(){
    var els = document.querySelectorAll(".cu-main-price,.cu-main-compare,.cu-bump-price,.cu-bump-compare,.price-item--sale,.price-item--regular");
    els.forEach(function(e){
      if(!e.dataset.usd){
        var v = parseFloat(e.textContent.replace(/[^0-9.]/g, ""));
        if(!v) return;
        e.dataset.usd = v;
      }
      e.textContent = fmtMoney(parseFloat(e.dataset.usd));
    });
    if(window.updateTotals) updateTotals();
    var btn = document.getElementById("cu-btn");
    if(btn && !document.getElementById("cu-fx-note") && window.CU_FX){
      var n = document.createElement("div");
      n.id = "cu-fx-note";
      n.style.cssText = "font-size:10.5px;opacity:.65;text-align:center;margin:6px 0 2px;";
      n.textContent = "💱 Precios aprox. en " + window.CU_FX.cur + " — el valor exacto se confirma al pagar.";
      btn.parentNode.insertBefore(n, btn);
    }
  }
  (function(){
    var MONEDAS = { CO:"COP", MX:"MXN", PE:"PEN", CL:"CLP", AR:"ARS", BR:"BRL",
                    GT:"GTQ", HN:"HNL", NI:"NIO", CR:"CRC", DO:"DOP", PY:"PYG", UY:"UYU", BO:"BOB" };
    function conRate(cur, rate){
      if(!rate) return;
      var dec = rate > 100 ? 0 : 2;
      var nf;
      try{ nf = new Intl.NumberFormat("es", {style:"currency", currency:cur, currencyDisplay:"code", maximumFractionDigits:dec, minimumFractionDigits:dec}); }
      catch(e){ return; }
      window.CU_FX = { cur: cur, rate: rate, fmt: function(usd){ return nf.format(usd * rate); } };
      repintarPrecios();
    }
    function conPais(cc){
      var cur = MONEDAS[(cc || "").toUpperCase()];
      if(!cur) return;
      fetch("https://open.er-api.com/v6/latest/USD").then(function(r){ return r.json(); })
        .then(function(fx){ conRate(cur, fx && fx.rates && fx.rates[cur]); }).catch(function(){});
    }
    fetch("https://ipapi.co/json/").then(function(r){ return r.json(); })
      .then(function(g){
        var cc = g && (g.country_code || g.country);
        if(cc) conPais(cc);
        else throw 0;
      })
      .catch(function(){
        fetch("https://api.country.is/").then(function(r){ return r.json(); })
          .then(function(h){ if(h && h.country) conPais(h.country); }).catch(function(){});
      });
  })();

  window.updateTotals = function(){
    var total = leer(".cu-main-price"), compare = leer(".cu-main-compare");
    ["gold-pc","gold-mob"].forEach(function(key){
      var cb = cbPack(key);
      if(cb && cb.checked){
        total   += parseFloat(cb.getAttribute("data-price"))   || 0;
        compare += parseFloat(cb.getAttribute("data-compare")) || 0;
      }
    });
    var t = document.getElementById("cu-total");   if(t) t.textContent = fmtMoney(total);
    var s = document.getElementById("cu-savings"); if(s) s.textContent = "-" + fmtMoney(compare - total);
  };

  function setGrupo(key, on){
    GRUPOS[key].forEach(function(i){
      var cb = cbNum(i); if(!cb) return;
      cb.checked = on;
      var card = document.getElementById("cu-b" + i);
      if(card) card.classList.toggle("selected", on);
      var txt = document.getElementById("cu-txt" + i);
      if(txt) txt.setAttribute("data-label", on ? "✓ INCLUIDO EN EL PACK" : "+ AGREGAR ESTE BONO");
    });
  }

  window.cuToggleGold = function(cb, key){
    var card = document.getElementById("cu-b-" + key);
    if(card) card.classList.toggle("selected", cb.checked);
    var txt = document.getElementById("cu-txt-" + key);
    if(txt){
      var labels = key === "gold-pc"
        ? ["+ AGREGAR ULTIMATE LEYENDA",    "✓ ULTIMATE LEYENDA AGREGADO"]
        : ["+ AGREGAR PACK SUPREMO MOBILE", "✓ PACK SUPREMO MOBILE AGREGADO"];
      txt.setAttribute("data-label", cb.checked ? labels[1] : labels[0]);
    }
    setGrupo(key, cb.checked);
    updateTotals();
  };

  window.cuToggle = function(cb, i){
    /* los bonos sueltos ya no se venden por separado: tocar uno lleva su pack completo */
    var key = i <= 2 ? "gold-pc" : "gold-mob";
    var pack = cbPack(key);
    cb.checked = false;
    if(pack){ pack.checked = !pack.checked; cuToggleGold(pack, key); }
  };

  /* ── drawer solo-bundles: bonos sueltos ocultos, contenido con miniaturas ── */
  var css = document.createElement("style");
  css.textContent =
    "#cu-b0,#cu-b1,#cu-b2,#cu-b3,#cu-b4,#cu-b5{display:none!important}" +
    ".cu-incluye{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:12px 0 4px;padding:0;list-style:none}" +
    ".cu-incluye li{position:relative;text-align:center;font-size:10px;font-weight:800;line-height:1.25;letter-spacing:.03em;text-transform:uppercase}" +
    ".cu-incluye img{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:11px;border:2px solid rgba(255,255,255,.18);display:block;margin-bottom:6px;transition:all .25s}" +
    ".cu-incluye .cu-inc-check{position:absolute;top:5px;right:5px;width:21px;height:21px;border-radius:50%;background:#1db954;color:#fff;font-size:12px;font-weight:900;display:none;align-items:center;justify-content:center;box-shadow:0 0 10px rgba(29,185,84,.9);z-index:2}" +
    ".selected .cu-incluye img{border-color:#1db954;box-shadow:0 0 14px rgba(29,185,84,.55)}" +
    ".selected .cu-incluye .cu-inc-check{display:flex}" +
    "#cu-b-gold-pc,#cu-b-gold-mob{padding:16px 14px!important}" +
    "#cu-b-gold-pc>.cu-bump-row .cu-bump-img,#cu-b-gold-mob>.cu-bump-row .cu-bump-img{display:none!important}" +
    "#cu-b-gold-pc .cu-bump-desc,#cu-b-gold-mob .cu-bump-desc{display:none!important}" +
    "#cu-b-gold-pc .cu-bump-title,#cu-b-gold-mob .cu-bump-title{font-size:18px!important;line-height:1.2}" +
    "#cu-b-gold-pc .cu-bump-price,#cu-b-gold-mob .cu-bump-price{font-size:23px!important;font-weight:900!important}" +
    "#cu-b-gold-pc .cu-bump-compare,#cu-b-gold-mob .cu-bump-compare{font-size:13px!important}" +
    "#cu-b-gold-pc .cu-bump-info,#cu-b-gold-mob .cu-bump-info{width:100%}" +
    ".cu-incluye{gap:10px;margin:12px 0 6px}" +
    ".cu-incluye li{font-size:10.5px}";
  document.head.appendChild(css);

  function datosDe(i){
    var c = document.getElementById("cu-b" + i); if(!c) return null;
    var t = c.querySelector(".cu-bump-title");
    var img = c.querySelector(".cu-bump-img");
    return { nombre: t ? t.textContent.trim() : "", src: img ? img.getAttribute("src") : "" };
  }
  [["gold-pc",[0,1,2]],["gold-mob",[3,4,5]]].forEach(function(par){
    var card = document.getElementById("cu-b-" + par[0]); if(!card) return;
    if(card.querySelector(".cu-incluye")) return;
    var ul = document.createElement("ul"); ul.className = "cu-incluye";
    par[1].forEach(function(i){
      var d = datosDe(i); if(!d) return;
      var li = document.createElement("li");
      var chk = document.createElement("span"); chk.className = "cu-inc-check"; chk.textContent = "✓";
      li.appendChild(chk);
      if(d.src){ var im = document.createElement("img"); im.src = d.src; im.alt = d.nombre; im.loading = "lazy"; li.appendChild(im); }
      var nm = document.createElement("span"); nm.textContent = d.nombre; li.appendChild(nm);
      ul.appendChild(li);
    });
    var foot = card.querySelector(".cu-bump-footer");
    card.insertBefore(ul, foot || null);
  });

  window.cuGoCheckout = function(){
    var keys = ["principal"];
    ["gold-pc","gold-mob"].forEach(function(key){
      var cb = cbPack(key); if(cb && cb.checked) keys.push(key);
    });
    var combo = keys.join("+");
    var link = (LINKS_COMBO && LINKS_COMBO[combo]) || LINKS_DE_PAGO.principal || "";
    if(!link){
      var btn = document.getElementById("cu-btn"); var prev = btn.innerHTML;
      btn.innerHTML = "⚠️ Configura tu link de pago";
      setTimeout(function(){ btn.innerHTML = prev; }, 3000);
      return;
    }
    link += (link.indexOf("?") > -1 ? "&" : "?") + "sck=" + encodeURIComponent(combo);
    window.location.href = link;
  };
})();
</script>'''
html2 = html2.replace('</body>', solo_packs + '\n</body>', 1)

# 10) tono de verde de la marca: todos los verdes al matiz 135 (verde LED de la foto)
import colorsys
HUE_VERDE = 135 / 360.0
def _verde_hex(m):
    hx = m.group(1)
    if len(hx) == 3:
        r, g, b = [int(c*2, 16) for c in hx]
    else:
        r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    if 118/360 <= h <= 172/360 and s > 0.12:
        r2, g2, b2 = [round(x*255) for x in colorsys.hls_to_rgb(HUE_VERDE, l, s)]
        return '#%02x%02x%02x' % (r2, g2, b2)
    return m.group(0)
def _verde_rgb(m):
    r, g, b = int(m.group(2)), int(m.group(4)), int(m.group(6))
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    if 118/360 <= h <= 172/360 and s > 0.12:
        r2, g2, b2 = [round(x*255) for x in colorsys.hls_to_rgb(HUE_VERDE, l, s)]
        return m.group(1) + str(r2) + m.group(3) + str(g2) + m.group(5) + str(b2)
    return m.group(0)
html2 = re.sub(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b', _verde_hex, html2)
html2 = re.sub(r'(rgba?\(\s*)(\d+)(\s*,\s*)(\d+)(\s*,\s*)(\d+)', _verde_rgb, html2)

open('index.html', 'w', encoding='utf-8').write(html2)
print('index.html generado:', len(html2), 'bytes')
assert 'assets/' in html2
assert 'LINKS_DE_PAGO' in html2
