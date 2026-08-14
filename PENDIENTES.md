# Pendientes — Consola Ultimate

Lista viva de lo hecho y lo que falta. Se marca con `[x]` a medida que se cierra.

> **Ojo:** `index.html` NO se edita a mano. Lo genera `scripts/construir.py` en
> cada deploy bajándose la página de Shopify, y después lo reescribe
> `scripts/post.py` corriendo, en este orden: `precios.py`, `links.py`,
> `imagenes.py`, `moneda.py`, `carrito.py`, `meta.py`. Cualquier edición manual
> del HTML se pierde en el siguiente build.

---

## Hecho

- [x] **PR #16 mergeado (2026-08-02)** — el `PIXEL_ID` ya esta en
      `scripts/meta.py`; el pixel sale activo en cada build.

- [x] **Checkout migrado de Hotmart a STRIPE con moneda local exacta (2026-08-05)**
      Los 4 combos venden ahora por Stripe Payment Links (cuenta
      `acct_1RyEj5CraKX72R2s`, liquida en USD):
      principal $34.99 · +Leyenda $59.98 · +Supremo $59.98 · todo $74.99.
      Cada Price lleva `currency_options` con montos FIJOS en 14 monedas de
      LATAM (COP, MXN, BRL, PEN, CLP, ARS, UYU, GTQ, HNL, NIO, CRC, DOP,
      PYG, BOB) y el checkout los presenta por IP. `scripts/moneda.py`
      (CU-FX v4) tiene una COPIA de esa tabla (`STRIPE_PRECIOS`): la landing
      muestra EXACTAMENTE el numero del checkout — se acabo el factor de
      Hotmart y el riesgo de que el checkout salga mas caro. VE/CU quedan
      como aproximado (Stripe no soporta VES/CUP; alli cobra USD).
      Atribucion: `scripts/meta.py` pasa combo+campana+anuncio+origen en
      `client_reference_id` del Payment Link (visible en el Dashboard).
      ⚠️ Si se cambia un precio: actualizar Stripe y `STRIPE_PRECIOS` en el
      mismo commit.

- [x] **Precio en moneda local instantáneo** — `scripts/moneda.py`
      País por huso horario (sin red), tasa cacheada 6 h, tabla de respaldo si la
      API cae. Antes había 0,3–2 s de dólares en pantalla por dos llamadas
      encadenadas. Cobertura LATAM + USA (20 países). Se quitó `ipapi.co`
      (tope de 1000 consultas/día en plan gratuito).

- [x] **La landing nunca más barata que el checkout** — `scripts/moneda.py`
      Se midió el checkout real de Hotmart país por país: la diferencia llega a
      +25,9 % en Chile, y viene casi toda del IVA local, no del spread. Por eso
      hay un factor por moneda (`FACTOR`) en vez de un margen global, y el
      resultado siempre se redondea hacia arriba.

- [x] **Bug de Argentina** — el navegador renombra `America/Argentina/*` a la
      forma corta, así que la tabla lista las dos. Sin eso los argentinos veían
      dólares.

- [x] **Total del carrito en moneda local** — `scripts/carrito.py`
      El `openCart` viejo capturaba el `updateTotals` en dólares. Ahora se
      envuelve y repinta al abrir.

- [x] **Precios nuevos y descuento por llevar todo** — `scripts/precios.py`
      Principal 34,99 (antes 117) · Leyenda 24,99 (antes 85) · Supremo 24,99
      (antes 88) · los tres juntos 74,99 en vez de 84,97.

- [x] **Imágenes** — `scripts/imagenes.py`
      PNG pesados a WebP, `srcset` real por ancho, `lazy` + `decoding` después
      de las primeras 8. Eran 40,8 MB, de los cuales 5 PNG pesaban 22,7 MB.

- [x] **Meta Pixel + atribución en la landing** — `scripts/meta.py`
      PageView, ViewContent, AddToCart e InitiateCheckout. Captura `utm_*`,
      `fbclid` y `gclid` al llegar y los pasa a Hotmart en sus campos `src` y `sck`.

- [x] **Pixel de Meta en Hotmart** — pixel `1076125914843182` ("The Game Box")
      configurado con evento **Sales made** y envío **vía WEB** en los cuatro
      productos que vende la landing:
      `8189092` principal · `8238333` + Leyenda · `8232407` + Supremo Mobile ·
      `8232421` + Leyenda + Supremo.
      *Checkout Page Visits* se dejó apagado a propósito: la landing ya dispara
      `InitiateCheckout` y si no, el evento se contaría dos veces.

- [x] **Checkout con la marca** — producto principal publicado con
      `checkoutMode=10` y el link real del combo con Leyenda
      (`P106988065E?off=zes3wsqi`).

- [x] **Dominio de GoDaddy** — registros A al apex + CNAME de `www`,
      `CNAME` = `the-gamebox.com`.

- [x] **Id duplicado `ctaCheckoutBtn`** — el segundo botón pasó a
      `ctaCheckoutBtn2`. Antes cualquier medición por `getElementById` solo
      registraba el primero de los dos.

---

## Falta — por orden de impacto

- [ ] **Entrega digital post-pago (Stripe no entrega archivos)**
      Hotmart entregaba el producto solo; Stripe no. Hay que apuntar el
      `after_completion` de los 4 Payment Links a una pagina `/gracias` en
      the-gamebox.com (o a Helios, que ya entrega los productos del circuito
      PDFs) que de acceso a la multiconsola y los packs. HOY el comprador
      paga y ve solo la confirmacion generica de Stripe.

- [ ] **Evento Purchase de Meta con Stripe**
      Antes lo mandaba Hotmart. Ahora: dispararlo en la pagina `/gracias`
      (fbq Purchase) y/o con la Conversions API desde el webhook
      `checkout.session.completed` de Stripe. Hasta entonces el embudo de
      Meta llega solo hasta InitiateCheckout.

- [ ] **Refrescar STRIPE_PRECIOS cada tanto**
      Los montos locales son fijos (generados 2026-08-05, tasa x1.045 de
      colchon; ARS x1.12). Si una moneda se devalua fuerte (ARS...), Esteban
      cobra menos USD por venta. Revisar mensual: comparar tasa del dia vs
      la implicita en la tabla y regenerar (Stripe + moneda.py juntos).

- [ ] **Barra de compra fija en el scroll**
      La pagina tiene ~6.600 lineas y el boton de compra sale solo en 2 puntos.

- [x] **Limpiar links muertos de Hotmart** — HECHO 2026-08-13
      Purgados los 20 links de pay.hotmart.com del HTML **y de construir.py**
      (si solo se limpiaba el HTML, la proxima regeneracion los devolvia).
      Ademas: candado `CU_SOLO_STRIPE` — cualquier URL que no empiece con
      https://buy.stripe.com/ se descarta y el boton cae al principal; y
      links.py aborta el build si aparece un solo link que no sea de Stripe.

- [ ] **Permiso de Workflows para el conector de GitHub**
      Sin el, `.github/workflows/desplegar.yml` hay que editarlo a mano cada vez
      que se agrega un paso al build.

### Cerrados por la migracion a Stripe (ya no aplican)
- ~~Replicar el checkout con marca a los otros tres productos (Hotmart)~~
- ~~Banner del pie del checkout en los combos (Hotmart)~~
- ~~Conversion API en Hotmart~~ → reemplazado por el punto de Purchase con Stripe
- ~~Crear ofertas por pais en Hotmart y llenar `OFERTAS_PAIS`~~ → resuelto
  mejor con `currency_options` + `STRIPE_PRECIOS` (identico por construccion)
