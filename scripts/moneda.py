#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Precios en moneda local, instantaneos.

Se ejecuta DESPUES de scripts/construir.py y reescribe index.html para que:
  1. El pais se detecte por huso horario  -> sin esperar a la red.
  2. La tasa de cambio salga del cache local -> sin red en visitas repetidas.
  3. Nunca se le muestre un precio en dolares a alguien de un pais con moneda propia.
  4. Si hay una OFERTA DE HOTMART para ese pais, se muestre su precio EXACTO
     y el boton de compra apunte a esa oferta (precio de landing == precio de checkout).

Es idempotente: se puede correr varias veces sobre el mismo archivo.
"""
import re, io, sys, os

ARCHIVO = os.environ.get('CU_INDEX', 'index.html')
MARCA = 'CU-FX v4'
MARCA_VIEJA = 'CU-FX v'   # para retirar cualquier version anterior (v3, v4...)

# ══════════════════════════════════════════════════════════════════
#  BLOQUE QUE SE INYECTA EN EL <head>
# ══════════════════════════════════════════════════════════════════
HEAD = r'''<link crossorigin="" href="https://open.er-api.com" rel="preconnect"/>
<link href="https://api.country.is" rel="dns-prefetch"/>
<style id="cu-fx-guard">html.cu-fx-wait .cu-main-price,html.cu-fx-wait .cu-main-compare,html.cu-fx-wait .cu-bump-price,html.cu-fx-wait .cu-bump-compare,html.cu-fx-wait .price-item--sale,html.cu-fx-wait .price-item--regular,html.cu-fx-wait #cu-total,html.cu-fx-wait #cu-savings{visibility:hidden!important}</style>
<script>
/* ══════════════════════════════════════════════════════════════════
   CU-FX v4 — precio en moneda local, instantaneo e IDENTICO al checkout

   Orden de prioridad para el precio que ve el visitante:
     1) PRECIO FIJO DE STRIPE de su moneda -> exacto, identico al checkout
     2) OFERTA por pais (OFERTAS_PAIS)     -> exacto, con link propio
     3) Tasa de cambio cacheada            -> instantaneo, sin red
     4) Tasa de cambio en vivo             -> ~200 ms
     5) Tasa de respaldo del codigo        -> si la API esta caida

   Desde 2026-08-05 el checkout es STRIPE (Payment Links). Cada Price tiene
   currency_options con montos FIJOS en 14 monedas de LATAM; el checkout
   presenta ese monto por IP del comprador. STRIPE_PRECIOS (abajo) es una
   COPIA de esa tabla: por eso landing y checkout muestran el mismo numero,
   sin ecuaciones ni margen de error. Si se cambia un precio en Stripe hay
   que cambiarlo AQUI tambien (scripts/moneda.py) y viceversa.
   ══════════════════════════════════════════════════════════════════ */
(function(){
  "use strict";

  /* ─────────────────────────────────────────────────────────────
     ⚙️ OFERTAS POR PAIS (opcional — para un link distinto por pais;
     con Stripe normalmente NO hace falta: STRIPE_PRECIOS ya da el
     precio exacto y el link es el mismo para todos)
     Formato:
       CO: {
         moneda: "COP",
         precios: { "39.99": 129900, "117.64": 389900 },   // USD del HTML -> precio local exacto
         links:   { "principal": "https://pay.hotmart.com/....?off=xxxx",
                    "principal+gold-pc": "...",
                    "principal+gold-mob": "...",
                    "principal+gold-pc+gold-mob": "..." }
       }
     Precios USD que aparecen en la pagina y conviene mapear:
       principal 39.99 (antes 117.64) · Ultimate Leyenda 34.00 (antes 85.00)
       Pack Supremo Mobile 35.20 (antes 88.00)
     ───────────────────────────────────────────────────────────── */
  var OFERTAS_PAIS = {
    /* Ejemplo listo para copiar — descomenta y reemplaza con tus datos reales:
    CO: {
      moneda: "COP",
      precios: { "39.99": 129900, "117.64": 389900, "34.00": 110000, "85.00": 275000, "35.20": 114000, "88.00": 285000 },
      links: {
        "principal":                   "https://pay.hotmart.com/XXXXXXXXX?off=aaaaaaaa",
        "principal+gold-pc":           "https://pay.hotmart.com/XXXXXXXXX?off=bbbbbbbb",
        "principal+gold-mob":          "https://pay.hotmart.com/XXXXXXXXX?off=cccccccc",
        "principal+gold-pc+gold-mob":  "https://pay.hotmart.com/XXXXXXXXX?off=dddddddd"
      }
    }
    */
  };

  /* ─────────────────────────────────────────────────────────────
     PRECIOS FIJOS DE STRIPE — la misma tabla que currency_options
     (montos de venta; generados 2026-08-05 con tasa open.er-api.com
     x1.045 de colchon — ARS x1.12 — y redondeo comercial hacia arriba)

     Claves: el precio USD que aparece en la pagina -> monto local EXACTO.
       34.99 principal · 24.99 cada pack · 59.98 principal+un pack
       74.99 los tres juntos
     El checkout de Stripe presenta EXACTAMENTE estos montos por IP.

     ⚙️ Si se cambia un precio: actualizar currency_options en Stripe Y
     esta tabla, en el mismo commit. Prices:
       price_1U16tQCraKX72R2swkGNocWA (34.99)
       price_1U17U8CraKX72R2szMhxcarB / price_1U17UACraKX72R2sLBiHe2xV (59.98)
       price_1U17UCCraKX72R2s11blFbmZ (74.99)
     ───────────────────────────────────────────────────────────── */
  var STRIPE_PRECIOS = {
    COP: {"34.99":115900, "24.99":82900,  "59.98":198800, "74.99":247900},
    MXN: {"34.99":639,    "24.99":459,    "59.98":1098,   "74.99":1359},
    BRL: {"34.99":189,    "24.99":139,    "59.98":328,    "74.99":399},
    PEN: {"34.99":129,    "24.99":88.99,  "59.98":217.99, "74.99":269},
    CLP: {"34.99":34900,  "24.99":24900,  "59.98":59800,  "74.99":72900},
    ARS: {"34.99":58900,  "24.99":41900,  "59.98":100800, "74.99":125900},
    UYU: {"34.99":1469,   "24.99":1049,   "59.98":2518,   "74.99":3149},
    GTQ: {"34.99":279,    "24.99":199,    "59.98":478,    "74.99":599},
    HNL: {"34.99":979,    "24.99":699,    "59.98":1678,   "74.99":2099},
    NIO: {"34.99":1349,   "24.99":969,    "59.98":2318,   "74.99":2879},
    CRC: {"34.99":16900,  "24.99":11900,  "59.98":28800,  "74.99":35900},
    DOP: {"34.99":2119,   "24.99":1519,   "59.98":3638,   "74.99":4549},
    PYG: {"34.99":218900, "24.99":155900, "59.98":374800, "74.99":467900},
    BOB: {"34.99":439,    "24.99":319,    "59.98":758,    "74.99":939}
  };

  /* Factor SOLO para los numeros decorativos (precios tachados, "ahorras"):
     el mismo colchon con el que se genero la tabla, para que el descuento
     se vea coherente. Los precios de venta reales salen de STRIPE_PRECIOS.
     Tambien aplica a monedas sin precio fijo (VES, CUP): alli el checkout
     de Stripe cobra en USD y la landing muestra un aproximado local. */
  var FACTOR = {
    COP: 1.045, MXN: 1.045, BRL: 1.045, PEN: 1.045, CLP: 1.045, UYU: 1.045,
    GTQ: 1.045, HNL: 1.045, NIO: 1.045, CRC: 1.045, DOP: 1.045, PYG: 1.045,
    BOB: 1.045, ARS: 1.12
  };
  var FACTOR_DEF = 1.05;

  /* Redondeo SIEMPRE hacia arriba, nunca hacia abajo: redondear hacia
     abajo podria dejar la landing por debajo del checkout. */
  function redondearArriba(v){
    var paso = v >= 10000 ? 100 : (v >= 1000 ? 10 : (v >= 100 ? 1 : 0.1));
    return Math.ceil(v / paso) * paso;
  }

  /* huso horario -> pais (LATAM + USA) */
  var TZ2CC = {
    "America/Bogota":"CO",
    "America/Mexico_City":"MX","America/Cancun":"MX","America/Merida":"MX","America/Monterrey":"MX",
    "America/Matamoros":"MX","America/Chihuahua":"MX","America/Ciudad_Juarez":"MX","America/Ojinaga":"MX",
    "America/Hermosillo":"MX","America/Mazatlan":"MX","America/Bahia_Banderas":"MX","America/Tijuana":"MX",
    "America/Lima":"PE",
    "America/Santiago":"CL","America/Punta_Arenas":"CL","Pacific/Easter":"CL",
    "America/Guatemala":"GT","America/Tegucigalpa":"HN","America/Managua":"NI","America/Costa_Rica":"CR",
    "America/Santo_Domingo":"DO","America/Asuncion":"PY","America/Montevideo":"UY","America/La_Paz":"BO",
    "America/Caracas":"VE","America/Havana":"CU",
    /* Argentina: el navegador renombra America/Argentina/* a la forma corta,
       asi que hay que listar las dos. Sin esto los argentinos no ven pesos. */
    "America/Buenos_Aires":"AR","America/Cordoba":"AR","America/Mendoza":"AR",
    "America/Rosario":"AR","America/Catamarca":"AR","America/Jujuy":"AR",
    "America/Sao_Paulo":"BR","America/Bahia":"BR","America/Fortaleza":"BR","America/Recife":"BR",
    "America/Belem":"BR","America/Manaus":"BR","America/Cuiaba":"BR","America/Campo_Grande":"BR",
    "America/Porto_Velho":"BR","America/Boa_Vista":"BR","America/Rio_Branco":"BR","America/Maceio":"BR",
    "America/Araguaina":"BR","America/Santarem":"BR","America/Eirunepe":"BR","America/Noronha":"BR",
    "America/Sao_Luis":"BR",
    "America/Guayaquil":"EC","Pacific/Galapagos":"EC","America/Panama":"PA","America/El_Salvador":"SV",
    "America/Puerto_Rico":"PR",
    "America/New_York":"US","America/Detroit":"US","America/Chicago":"US","America/Denver":"US",
    "America/Phoenix":"US","America/Los_Angeles":"US","America/Anchorage":"US","Pacific/Honolulu":"US",
    "America/Boise":"US","America/Kentucky/Louisville":"US"
  };

  /* pais -> moneda. "USD" = ya esta en dolares, no se convierte nada */
  var MONEDAS = {
    CO:"COP", MX:"MXN", PE:"PEN", CL:"CLP", AR:"ARS", BR:"BRL", GT:"GTQ", HN:"HNL", NI:"NIO",
    CR:"CRC", DO:"DOP", PY:"PYG", UY:"UYU", BO:"BOB", VE:"VES", CU:"CUP",
    US:"USD", EC:"USD", PA:"USD", SV:"USD", PR:"USD"
  };

  var SIMBOLO = {
    COP:"$", MXN:"$", ARS:"$", CLP:"$", UYU:"$", CUP:"$", DOP:"RD$",
    PEN:"S/", BRL:"R$", GTQ:"Q", HNL:"L", NIO:"C$", CRC:"₡", PYG:"₲", BOB:"Bs", VES:"Bs"
  };
  var LOCALE = {
    COP:"es-CO", MXN:"es-MX", ARS:"es-AR", CLP:"es-CL", PEN:"es-PE", UYU:"es-UY",
    BOB:"es-BO", PYG:"es-PY", GTQ:"es-GT", HNL:"es-HN", NIO:"es-NI", CRC:"es-CR",
    DOP:"es-DO", VES:"es-VE", CUP:"es-CU", BRL:"pt-BR"
  };

  /* red de seguridad si la API de tasas no responde — open.er-api.com, 31 jul 2026 */
  var FB = {
    COP:3200.63, MXN:17.36, PEN:3.39, CLP:933.41, ARS:1490.84, BRL:5.09, GTQ:7.62,
    HNL:26.76, NIO:36.76, CRC:454.20, DOP:58.03, PYG:5992.80, UYU:40.07, BOB:11.45,
    VES:746.63, CUP:24
  };

  var LS_R="cu_fx_rates_v3", LS_P="cu_fx_pais_v3";
  var TTL_R=6*3600*1000, TTL_P=30*24*3600*1000;
  var ESPERA_RESPALDO=900, ESPERA_DURA=2500;

  function leerCache(k){
    try{
      var s=localStorage.getItem(k); if(!s) return null;
      var o=JSON.parse(s);
      if(!o||!o.t||(Date.now()-o.t)>o.ttl) return null;
      return o.v;
    }catch(e){ return null; }
  }
  function guardarCache(k,v,ttl){
    try{ localStorage.setItem(k,JSON.stringify({t:Date.now(),ttl:ttl,v:v})); }catch(e){}
  }

  function paisPorTZ(){
    var z="";
    try{ z=Intl.DateTimeFormat().resolvedOptions().timeZone||""; }catch(e){}
    if(!z) return "";
    if(z.indexOf("America/Argentina/")===0) return "AR";
    if(z.indexOf("America/Indiana/")===0||z.indexOf("America/North_Dakota/")===0) return "US";
    return TZ2CC[z]||"";
  }

  var revelado=false;
  function revelar(){
    if(revelado) return;
    revelado=true;
    var h=document.documentElement;
    if(h) h.className=h.className.replace(/\s*\bcu-fx-wait\b/g,"");
  }

  function repintar(){
    if(typeof window.CU_REPAINT==="function"){ try{ window.CU_REPAINT(); }catch(e){} }
  }

  var aplicada=null;
  function aplicar(cur, rate, origen){
    if(!cur||cur==="USD"||!rate||!isFinite(rate)||rate<=0){ revelar(); return; }
    if(aplicada&&aplicada.cur===cur&&Math.abs(aplicada.rate-rate)/rate<0.005){ revelar(); return; }

    var of  = OFERTAS_PAIS[window.CU_PAIS] || null;
    var usa = of && of.moneda===cur ? of : null;   /* la oferta solo aplica si es la misma moneda */
    var dec = rate>100 ? 0 : 2;
    var sim = SIMBOLO[cur]||"";
    var nf, nf0;
    try{
      nf  = new Intl.NumberFormat(LOCALE[cur]||"es",{minimumFractionDigits:dec,maximumFractionDigits:dec});
      nf0 = new Intl.NumberFormat(LOCALE[cur]||"es",{minimumFractionDigits:0,maximumFractionDigits:2});
    }catch(e){
      try{ nf=new Intl.NumberFormat("es",{minimumFractionDigits:dec,maximumFractionDigits:dec}); nf0=nf; }
      catch(e2){ revelar(); return; }
    }

    var fija = STRIPE_PRECIOS[cur] || null;   /* tabla fija de Stripe para esta moneda */
    aplicada={cur:cur,rate:rate};
    window.CU_FX={
      cur:cur, rate:rate, origen:origen,
      oferta: !!(usa||fija),
      /* con precio fijo de Stripe el numero es exacto; solo avisamos
         "aproximado" en monedas sin tabla (alli Stripe cobra en USD) */
      nota: (usa||fija) ? "" : ("💱 Precios aprox. en "+cur+" — el valor exacto se confirma al pagar."),
      fmt:function(usd){
        var k = (typeof usd==="number" ? usd : parseFloat(usd)).toFixed(2);
        var exacto = null;
        if(fija && fija[k]!=null) exacto = fija[k];                 /* 1) precio fijo de Stripe */
        else if(usa && usa.precios){                                /* 2) oferta por pais */
          exacto = usa.precios[k]!=null ? usa.precios[k] : usa.precios[String(usd)];
        }
        if(exacto!=null) return sim+nf0.format(exacto)+" "+cur;
        var f = FACTOR[cur] || FACTOR_DEF;                          /* 3) conversion con colchon */
        return sim+nf.format(redondearArriba(usd*rate*f))+" "+cur;
      }
    };
    repintar();
    revelar();
  }

  /* enlace de checkout del pais, si existe oferta */
  window.CU_LINK_PAIS=function(combo){
    var of=OFERTAS_PAIS[window.CU_PAIS];
    if(of&&of.links&&of.links[combo]) return of.links[combo];
    return null;
  };

  /* ── arranque sincronico ── */
  var cc = leerCache(LS_P) || paisPorTZ();
  window.CU_PAIS = (cc||"").toUpperCase();
  var cur = MONEDAS[window.CU_PAIS] || "";
  var convierte = !!cur && cur!=="USD";

  if(convierte){
    document.documentElement.className+=" cu-fx-wait";
    setTimeout(revelar, ESPERA_DURA);
  }

  var cache=leerCache(LS_R);
  if(convierte && cache && cache[cur]) aplicar(cur, cache[cur], "cache");
  else if(convierte) setTimeout(function(){ if(!aplicada) aplicar(cur, FB[cur], "respaldo"); }, ESPERA_RESPALDO);

  /* tasas en vivo (siempre, para refrescar el cache) */
  fetch("https://open.er-api.com/v6/latest/USD")
    .then(function(r){ return r.json(); })
    .then(function(fx){
      if(!fx||!fx.rates) return;
      guardarCache(LS_R, fx.rates, TTL_R);
      if(convierte) aplicar(cur, fx.rates[cur], "vivo");
    })
    .catch(function(){ if(convierte&&!aplicada) aplicar(cur, FB[cur], "respaldo"); });

  /* verificacion por IP en segundo plano (VPN, viajeros, husos raros) */
  if(!leerCache(LS_P)){
    fetch("https://api.country.is/")
      .then(function(r){ return r.json(); })
      .then(function(h){
        var ip=h&&h.country?String(h.country).toUpperCase():"";
        if(!ip) return;
        guardarCache(LS_P, ip, TTL_P);
        if(ip===window.CU_PAIS) return;
        window.CU_PAIS=ip;
        var nc=MONEDAS[ip]||"";
        cur=nc; convierte=!!nc&&nc!=="USD";
        if(!convierte){ aplicada=null; window.CU_FX=null; repintar(); revelar(); return; }
        aplicada=null;
        var c2=leerCache(LS_R);
        aplicar(nc, (c2&&c2[nc])||FB[nc], c2&&c2[nc]?"ip-cache":"ip-respaldo");
      })
      .catch(function(){});
  }
})();
</script>
'''

# ══════════════════════════════════════════════════════════════════
def main():
    if not os.path.exists(ARCHIVO):
        sys.exit('no existe ' + ARCHIVO)
    s = io.open(ARCHIVO, encoding='utf-8').read()
    n0 = len(s)

    # idempotencia: si ya se corrio (cualquier version), se quita y se reinyecta
    if MARCA_VIEJA in s:
        ini = s.find('<link crossorigin="" href="https://open.er-api.com" rel="preconnect"/>')
        fin = s.find('</script>', s.find(MARCA_VIEJA))
        if ini != -1 and fin != -1:
            s = s[:ini] + s[fin + len('</script>\n'):]
            print('bloque anterior retirado (idempotente)')

    # ── 1. inyectar el bloque en el <head>, antes del script de links de pago
    ancla = '<script>\n/* ═════'
    i = s.find(ancla)
    if i == -1:
        i = s.find('</head>')
        if i == -1:
            sys.exit('no se encontro donde inyectar en el <head>')
    s = s[:i] + HEAD + s[i:]
    print('bloque CU-FX v4 inyectado en el <head>')

    # ── 2. quitar el IIFE viejo de geo+moneda del final del body
    ini = s.find('  (function(){\n    var MONEDAS = {')
    if ini != -1:
        fin = s.find('  })();\n', ini)
        if fin == -1:
            sys.exit('no se encontro el cierre del IIFE viejo de moneda')
        fin += len('  })();\n')
        s = s[:ini] + (
            '  /* La deteccion de pais y la tasa viven en el <head> (CU-FX v4):\n'
            '     el precio sale ya convertido sin esperar a la red. */\n'
            '  window.CU_REPAINT = repintarPrecios;\n'
            '  repintarPrecios();\n'
        ) + s[fin:]
        print('IIFE viejo de moneda reemplazado por el enganche de repintado')
    else:
        print('AVISO: no se hallo el IIFE viejo (quiza construir.py cambio)')

    # ── 3. la nota "precios aprox." ahora depende de si hay oferta de pais
    vieja_nota = 'n.textContent = "\U0001F4B1 Precios aprox. en " + window.CU_FX.cur + " — el valor exacto se confirma al pagar.";'
    nueva_nota = 'n.textContent = window.CU_FX.nota || "";'
    if vieja_nota in s:
        s = s.replace(vieja_nota, nueva_nota)
        s = s.replace(
            'if(btn && !document.getElementById("cu-fx-note") && window.CU_FX){',
            'if(btn && !document.getElementById("cu-fx-note") && window.CU_FX && window.CU_FX.nota){')
        print('nota de "precio aproximado" condicionada a que no haya oferta de pais')

    # ── 4. el checkout usa la oferta del pais cuando existe
    viejo_link = '    var link = (LINKS_COMBO && LINKS_COMBO[combo]) || LINKS_DE_PAGO.principal || "";'
    nuevo_link = ('    var link = (window.CU_LINK_PAIS && window.CU_LINK_PAIS(combo))\n'
                  '            || (LINKS_COMBO && LINKS_COMBO[combo])\n'
                  '            || LINKS_DE_PAGO.principal || "";')
    if viejo_link in s:
        s = s.replace(viejo_link, nuevo_link)
        print('checkout enlazado a la oferta del pais cuando exista')
    else:
        print('AVISO: no se hallo la linea de seleccion de link en cuGoCheckout')

    io.open(ARCHIVO, 'w', encoding='utf-8').write(s)
    print('%s: %d -> %d bytes' % (ARCHIVO, n0, len(s)))

    # ── validaciones: si algo no quedo enganchado, el build DEBE fallar
    #    (mejor romper el deploy que publicar la pagina con precios rotos)
    fallos = []
    if MARCA not in s:
        fallos.append('el bloque CU-FX no quedo inyectado')
    if 'STRIPE_PRECIOS' not in s:
        fallos.append('falta la tabla STRIPE_PRECIOS (precios fijos del checkout)')
    if s.count('<style id="cu-fx-guard">') != 1:
        fallos.append('quedo mas de un bloque CU-FX en el <head> (idempotencia rota)')
    if 'window.CU_REPAINT = repintarPrecios;' not in s:
        fallos.append('el repintado de precios no quedo enganchado')
    if 'window.CU_LINK_PAIS && window.CU_LINK_PAIS(combo)' not in s:
        fallos.append('el checkout no quedo enlazado a las ofertas por pais')
    if 'LINKS_DE_PAGO' not in s:
        fallos.append('se perdieron los links de pago')
    if 'ipapi.co' in s:
        fallos.append('quedo codigo viejo de geolocalizacion (ipapi.co)')
    if fallos:
        sys.exit('ERROR moneda.py:\n  - ' + '\n  - '.join(fallos))
    print('validaciones OK')


if __name__ == '__main__':
    main()
