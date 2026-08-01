# Pendientes — Consola Ultimate

Lista viva de lo hecho y lo que falta. Se marca con `[x]` a medida que se cierra.

> **Ojo:** `index.html` NO se edita a mano. Lo genera `scripts/construir.py` en
> cada deploy bajándose la página de Shopify, y después lo reescriben
> `scripts/moneda.py` y `scripts/meta.py`. Cualquier edición manual del HTML se
> pierde en el siguiente build.

---

## Hecho

- [x] **Precio en moneda local instantáneo** — `scripts/moneda.py`
      País por huso horario (sin red), tasa cacheada 6 h, tabla de respaldo si la
      API cae. Antes había 0,3–2 s de dólares en pantalla por dos llamadas
      encadenadas. Cobertura LATAM + USA (20 países). Se quitó `ipapi.co`
      (tope de 1000 consultas/día en plan gratuito).

- [x] **Meta Pixel + atribución** — `scripts/meta.py`
      PageView, ViewContent, AddToCart e InitiateCheckout. Captura `utm_*`,
      `fbclid` y `gclid` al llegar y los pasa a Hotmart en sus campos `src` y `sck`.

- [x] **Id duplicado `ctaCheckoutBtn`** — el segundo botón pasó a
      `ctaCheckoutBtn2`. Antes cualquier medición por `getElementById` solo
      registraba el primero de los dos.

---

## Falta — por orden de impacto

- [ ] **Pegar el ID del píxel de Meta**
      En `scripts/meta.py`, variable `PIXEL_ID`. Mientras esté vacío se instala
      la atribución pero no el píxel.

- [ ] **Configurar el píxel también en Hotmart**
      Hotmart → Herramientas → Pixel de Facebook, con el mismo ID. El evento
      `Purchase` ocurre allá, no en la landing: sin esto Meta no recibe la
      conversión real y no puede optimizar las campañas.

- [ ] **Verificar el precio real en Hotmart**
      La página vende a **$39.99** pero el comentario del link `principal` en
      `construir.py` dice **$34.99**. Uno de los dos está desactualizado.

- [ ] **Crear ofertas por país en Hotmart y llenar `OFERTAS_PAIS`**
      Hotmart convierte a moneda local con su propia tasa más un *spread*, así
      que hoy la landing muestra un número algo menor al del checkout. Con una
      oferta por país (4 variantes cada una: principal, +gold-pc, +gold-mob,
      +ambos) el precio de la landing y el del checkout quedan idénticos.
      La tabla está en `scripts/moneda.py` con un ejemplo comentado.
      Empezar por CO, MX y BR.

- [ ] **Conectar el dominio de GoDaddy**
      4 registros A al apex + CNAME para `www`, dominio en Settings → Pages,
      y activar *Enforce HTTPS* cuando esté disponible.

- [ ] **Barra de compra fija en el scroll**
      La página tiene ~6.600 líneas y el botón de compra sale solo en 2 puntos.

- [ ] **Lazy loading en las imágenes**
      126 de 160 imágenes cargan sin `loading="lazy"`. En celular con datos
      móviles retrasa bastante la primera pintura.

- [ ] **Limpiar links muertos y unificar `checkoutMode`**
      6 de los 18 links de Hotmart son inalcanzables (los de bonos sueltos: el
      carrito ahora fuerza packs completos). `checkoutMode=10` está solo en 4 de
      los 18, así que la experiencia de checkout cambia según el combo. Además
      viajan ~120 líneas de una versión vieja del carrito que se sobrescribe.

- [ ] **Permiso de Workflows para el conector de GitHub**
      Sin él, `.github/workflows/desplegar.yml` hay que editarlo a mano cada vez
      que se agrega un paso al build.
