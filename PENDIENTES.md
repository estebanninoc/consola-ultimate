# Pendientes — Consola Ultimate

Lista viva de lo hecho y lo que falta. Se marca con `[x]` a medida que se cierra.

> **Ojo:** `index.html` NO se edita a mano. Lo genera `scripts/construir.py` en
> cada deploy bajándose la página de Shopify, y después lo reescribe
> `scripts/post.py` corriendo, en este orden: `precios.py`, `links.py`,
> `imagenes.py`, `moneda.py`, `carrito.py`, `meta.py`. Cualquier edición manual
> del HTML se pierde en el siguiente build.

---

## Hecho

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

- [ ] **Mergear el PR #16**
      Trae el `PIXEL_ID` en `scripts/meta.py`. Hasta que no se mergee, la landing
      sale a producción con el píxel apagado.

- [ ] **Replicar el checkout con marca a los otros tres productos**
      En el Checkout Builder de Hotmart, "Duplicar a otros productos" desde el
      principal. Hoy solo el principal y el combo con Leyenda lo tienen.

- [ ] **Banner del pie del checkout en los combos**
      Sigue diciendo "MULTI CONSOLA ULTIMATE RETRO™ · +65.000 juegos" también en
      los productos combinados. Falta una imagen por combo.

- [ ] **Conversion API en Hotmart (opcional pero vale mucho)**
      El envío quedó solo "vía WEB". La API de Conversiones manda el evento
      desde el servidor y sobrevive a los bloqueos de iOS y de los bloqueadores.
      Pide un token que se genera en el Administrador de Eventos de Meta; ese
      token lo tiene que pegar Esteban, no se maneja por aquí.

- [ ] **Crear ofertas por país en Hotmart y llenar `OFERTAS_PAIS`**
      Hoy el factor por moneda deja la landing siempre igual o más cara que el
      checkout, que es lo correcto, pero no idéntica. Con una oferta por país
      (4 variantes: principal, +leyenda, +supremo, +ambos) los dos números
      quedan clavados. Empezar por CO, MX y BR.
      La tabla está en `scripts/moneda.py` con un ejemplo comentado.

- [ ] **Barra de compra fija en el scroll**
      La página tiene ~6.600 líneas y el botón de compra sale solo en 2 puntos.

- [ ] **Limpiar links muertos y unificar `checkoutMode`**
      6 de los 18 links de Hotmart son inalcanzables (los de bonos sueltos: el
      carrito ahora fuerza packs completos). `checkoutMode=10` está solo en 4 de
      los 18, así que la experiencia de checkout cambia según el combo. Además
      viajan ~120 líneas de una versión vieja del carrito que se sobrescribe.

- [ ] **Permiso de Workflows para el conector de GitHub**
      Sin él, `.github/workflows/desplegar.yml` hay que editarlo a mano cada vez
      que se agrega un paso al build.
