#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meta Pixel + atribucion de anuncios.

Se ejecuta DESPUES de construir.py (y de moneda.py) y reescribe index.html para:
  1. Instalar el Meta Pixel con los eventos del embudo.
  2. Guardar los UTM y el fbclid con los que llego el visitante,
     y pasarlos al checkout de STRIPE (client_reference_id) para poder
     atribuir cada venta desde el Dashboard de Stripe.
  3. Arreglar el id duplicado de los botones de compra, que rompia la medicion.

⚙️ ESTEBAN: pega tu ID de pixel en PIXEL_ID aqui abajo (o define la
variable de entorno META_PIXEL_ID en el workflow). Sin ID, el script
igual arregla los ids y la atribucion, pero no instala el pixel.

El evento Purchase NO se dispara aqui: la compra ocurre en Stripe.
PENDIENTE: apuntar el after_completion de los 4 Payment Links a una
pagina /gracias en the-gamebox.com que dispare fbq('track','Purchase')
(o usar la Conversions API con el webhook de Stripe). Hasta entonces,
Meta recibe el embudo hasta InitiateCheckout.

Es idempotente.
"""
import io, os, sys

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')
MARCA = 'CU-META v1'

# ⚙️ ─────────────────────────────────────────────────────────────
PIXEL_ID = os.environ.get('META_PIXEL_ID', '').strip() or '1076125914843182'
#    Pixel "The Game Box" · cuenta publicitaria GAMEBOX (1569117264652457)
#    dentro del portafolio EL MEGA BAZAR. Creado con la API de conversiones
#    activada. El MISMO id va tambien en Hotmart (Herramientas > Mostrar
#    todas > Pixel de seguimiento > Facebook + Instagram) para que llegue
#    el evento de Compra: la venta ocurre alla, no en la landing.
# ─────────────────────────────────────────────────────────────────

HEAD_TPL = r'''<script>
/* ══════════════════════════════════════════════════════════
   CU-META v1 — Meta Pixel + atribucion de anuncios
   ══════════════════════════════════════════════════════════ */
(function(){
  "use strict";

  /* ── 1. guardar de donde llego el visitante ──────────────
     Se guarda en sessionStorage para que sobreviva a la
     navegacion interna y llegue completo al checkout.      */
  var CLAVES = ["utm_source","utm_medium","utm_campaign","utm_content","utm_term",
                "fbclid","gclid","ttclid"];
  var LS = "cu_atrib_v1";

  function guardado(){
    try{ return JSON.parse(sessionStorage.getItem(LS) || "{}") || {}; }
    catch(e){ return {}; }
  }
  function capturar(){
    var prev = guardado(), hay = false, out = {};
    var q;
    try{ q = new URLSearchParams(location.search); }
    catch(e){ return prev; }
    CLAVES.forEach(function(k){
      var v = q.get(k);
      if(v){ out[k] = v; hay = true; }
    });
    if(!hay) return prev;                 /* sin UTMs nuevos: se respeta el primer toque */
    out.ts = Date.now();
    try{ sessionStorage.setItem(LS, JSON.stringify(out)); }catch(e){}
    return out;
  }
  window.CU_ATRIB = capturar();

  /* Etiqueta de seguimiento para el checkout de STRIPE.
     Stripe solo acepta un campo en la URL del Payment Link:
     client_reference_id (alfanumerico, guion y guion bajo, max 200).
     Queda guardado en la sesion de pago y se ve en el Dashboard,
     asi cada venta dice combo + campana + anuncio + origen. */
  window.CU_TRACK = function(combo){
    var a = window.CU_ATRIB || {};
    function limpio(s){ return String(s || "").replace(/[^A-Za-z0-9_-]/g, "-"); }
    var src = limpio(a.utm_source || (a.fbclid ? "facebook" : "directo"));
    var ref = [limpio(combo),
               limpio(a.utm_campaign || "sin-campana"),
               limpio(a.utm_content  || "sin-anuncio"),
               src].join("__").slice(0, 200);
    return { src: src, ref: ref };
  };

  /* ── 2. Meta Pixel ───────────────────────────────────── */
  var PIXEL = "__PIXEL_ID__";
  if(!PIXEL) return;

  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}
  (window,document,'script','https://connect.facebook.net/en_US/fbevents.js');

  fbq('init', PIXEL);
  fbq('track', 'PageView');

  /* ViewContent: el visitante esta viendo el producto */
  fbq('track', 'ViewContent', {
    content_name: 'MULTICONSOLA ULTIMATE RETRO',
    content_type: 'product',
    content_ids: ['consola-ultimate'],
    value: 34.99,
    currency: 'USD'
  });
})();
</script>
'''

TAIL = r'''<script>
/* ══════════════════════════════════════════════════════════
   CU-META v1 — eventos del embudo + atribucion al checkout
   Va al final del body: aqui ya existen openCart y cuGoCheckout.
   ══════════════════════════════════════════════════════════ */
(function(){
  "use strict";

  /* total del carrito en USD (los data-price de los packs estan en USD) */
  function totalUSD(){
    var t = 0;
    var m = document.querySelector(".cu-main-price");
    if(m) t += parseFloat(m.dataset && m.dataset.usd ? m.dataset.usd : String(m.textContent).replace(/[^0-9.]/g,"")) || 0;
    ["gold-pc","gold-mob"].forEach(function(k){
      var cb = document.getElementById("cu-cb-" + k);
      if(cb && cb.checked) t += parseFloat(cb.getAttribute("data-price")) || 0;
    });
    return Math.round(t * 100) / 100;
  }
  function ids(){
    var out = ["consola-ultimate"];
    ["gold-pc","gold-mob"].forEach(function(k){
      var cb = document.getElementById("cu-cb-" + k);
      if(cb && cb.checked) out.push(k);
    });
    return out;
  }
  function ev(nombre, extra){
    if(typeof fbq !== "function") return;
    var d = { content_type:"product", content_ids: ids(), value: totalUSD(), currency:"USD" };
    if(extra) for(var k in extra) d[k] = extra[k];
    try{ fbq("track", nombre, d); }catch(e){}
  }

  /* AddToCart al abrir el carrito (una sola vez por sesion de pagina) */
  var abierto = false;
  var _open = window.openCart;
  if(typeof _open === "function"){
    window.openCart = function(){
      try{ if(!abierto){ abierto = true; ev("AddToCart"); } }catch(e){}
      return _open.apply(this, arguments);
    };
  }

  /* AddToCart tambien al agregar un pack */
  var _gold = window.cuToggleGold;
  if(typeof _gold === "function"){
    window.cuToggleGold = function(cb, key){
      var r = _gold.apply(this, arguments);
      try{ if(cb && cb.checked) ev("AddToCart", {content_name:key}); }catch(e){}
      return r;
    };
  }

  /* InitiateCheckout + atribucion, justo antes de saltar a Stripe */
  var _go = window.cuGoCheckout;
  if(typeof _go === "function"){
    window.cuGoCheckout = function(){
      var keys = ["principal"];
      ["gold-pc","gold-mob"].forEach(function(k){
        var cb = document.getElementById("cu-cb-" + k);
        if(cb && cb.checked) keys.push(k);
      });
      var combo = keys.join("+");

      var link = (window.CU_LINK_PAIS && window.CU_LINK_PAIS(combo))
              || (window.LINKS_COMBO && LINKS_COMBO[combo])
              || (window.LINKS_DE_PAGO && LINKS_DE_PAGO.principal) || "";
      if(!link) return _go.apply(this, arguments);

      var t = window.CU_TRACK ? window.CU_TRACK(combo) : {ref:combo.replace(/\+/g,"-")};
      var sep = link.indexOf("?") > -1 ? "&" : "?";
      link += sep + "client_reference_id=" + encodeURIComponent(t.ref);

      try{ ev("InitiateCheckout"); }catch(e){}

      /* pequena pausa para que el pixel alcance a enviar el evento */
      if(typeof fbq === "function"){
        setTimeout(function(){ window.location.href = link; }, 220);
      }else{
        window.location.href = link;
      }
    };
  }
})();
</script>
'''


def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    # idempotencia: quitar los bloques de una corrida anterior
    while MARCA in s:
        i = s.find(MARCA)
        ini = s.rfind('<script>', 0, i)
        fin = s.find('</script>', i)
        if ini == -1 or fin == -1:
            break
        s = s[:ini] + s[fin + len('</script>\n'):]
    if n0 != len(s):
        print('bloques anteriores retirados (idempotente)')

    # ── 1. id duplicado: el segundo boton pasa a ctaCheckoutBtn2
    marca_id = 'id="ctaCheckoutBtn"'
    if s.count(marca_id) > 1:
        primero = s.find(marca_id)
        segundo = s.find(marca_id, primero + 1)
        s = s[:segundo] + 'id="ctaCheckoutBtn2"' + s[segundo + len(marca_id):]
        print('id duplicado corregido: el segundo boton ahora es ctaCheckoutBtn2')

    # ── 2. bloque del <head>
    head = HEAD_TPL.replace('__PIXEL_ID__', PIXEL_ID)
    ancla = '<script>\n/* ═════'
    i = s.find(ancla)
    if i == -1:
        i = s.find('</head>')
        if i == -1:
            sys.exit('no se encontro donde inyectar en el <head>')
    s = s[:i] + head + s[i:]
    print('bloque de cabecera inyectado' + ('' if PIXEL_ID else ' (SIN pixel: falta PIXEL_ID)'))

    # ── 3. bloque final, despues de todo lo demas
    j = s.rfind('</body>')
    if j == -1:
        sys.exit('no se encontro </body>')
    s = s[:j] + TAIL + s[j:]
    print('bloque de eventos inyectado antes de </body>')

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))

    fallos = []
    if s.count(MARCA) != 2:
        fallos.append('los dos bloques CU-META no quedaron (hay %d)' % s.count(MARCA))
    if s.count('id="ctaCheckoutBtn"') != 1:
        fallos.append('sigue habiendo ids duplicados de ctaCheckoutBtn')
    if 'window.CU_TRACK' not in s:
        fallos.append('la atribucion no quedo instalada')
    if PIXEL_ID and 'fbevents.js' not in s:
        fallos.append('hay PIXEL_ID pero el pixel no quedo inyectado')
    if fallos:
        sys.exit('ERROR meta.py:\n  - ' + '\n  - '.join(fallos))

    if not PIXEL_ID:
        print('AVISO: sin PIXEL_ID. Se instalo la atribucion pero NO el pixel de Meta.')
    print('validaciones OK')


if __name__ == '__main__':
    main()
