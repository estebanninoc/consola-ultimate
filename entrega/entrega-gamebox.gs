/**
 * ═══════════════════════════════════════════════════════════════════
 *  THE GAME BOX — Entrega automática por correo (Stripe → Gmail)
 *  ───────────────────────────────────────────────────────────────────
 *  Stripe llama a este script cada vez que alguien PAGA
 *  (evento checkout.session.completed). El script detecta qué combo
 *  compró y le manda el correo con los entregables desde esta cuenta
 *  de Gmail. Cero servidores, cero costo.
 *
 *  ⚙️ CONFIGURACIÓN (pestaña "Configuración del proyecto" → Propiedades
 *  del script — NUNCA pegar claves en el código):
 *    TOKEN       → palabra secreta larga inventada (va también en la URL
 *                  del webhook que se registra en Stripe)
 *    STRIPE_KEY  → clave restringida de Stripe (solo lectura de Checkout
 *                  Sessions) para saber con certeza qué combo compró
 *  ═══════════════════════════════════════════════════════════════════
 */

// ─────────────────────────────────────────────────────────────
// 📦 ENTREGABLES — pega aquí los PDFs/links cuando los tengas.
//   driveId: el ID del archivo en el Drive de ESTA cuenta
//            (de la URL: drive.google.com/file/d/ESTE_PEDAZO/view)
//   adjuntar: true = va adjunto al correo (máx ~20 MB en total);
//             false = va como botón/link de descarga
// ─────────────────────────────────────────────────────────────
var ENTREGABLES = {
  'principal': [
    { nombre: 'MULTICONSOLA ULTIMATE RETRO (versión completa)', url: 'https://www.mediafire.com/file/8b8ptuxvz2zt8r7/file' },
    { nombre: 'Versión LITE — computadoras gama media-baja', url: 'https://drive.google.com/drive/folders/18egvQaaJ3zNrX-gRKW65ahQTz_HlhXf_' },
    { nombre: 'Versión BASE — computadoras gama baja', url: 'https://drive.google.com/drive/folders/1uHIuv5lU16fNeKFd9lQUflHavGAR516x' },
    { nombre: 'Guía de instalación MultiConsola 2026', driveId: '1_hnl0GZYI1vw6nj3s1qv99lo20u5oNJi', adjuntar: true }
  ],
  'gold-pc': [
    { nombre: 'ULTIMATE LEYENDA — versión julio 2026', url: 'https://www.mediafire.com/file/8b8ptuxvz2zt8r7/file' },
    { nombre: 'Descarga directa alternativa', url: 'https://transfer.it/t/csJcbrplBRwL' },
    { nombre: 'Guía de instalación Leyenda — Android', driveId: '1Klf0IlfYhcyKx_Y6d8YBwDXqp1u4u2iP', adjuntar: true },
    { nombre: 'Guía de instalación Leyenda — PS4/PS5/Xbox', driveId: '1YpiQ8l6llEopJRKJk9Yef4JuA1-UWnvi', adjuntar: true }
  ],
  'gold-mob': [
    { nombre: 'RETROGAMING ANDROID MOBILE (APK)', url: 'https://www.mediafire.com/file_premium/i7e3mb4wf4iryu4/VideoJuegos-Gtboxplay.apk/file' },
    { nombre: 'ULTRA RETRO MOBILE ANDROID 30 (APK)', url: 'https://www.mediafire.com/file/4bdvjlpevywbacy/GT_BOX_PLAY_GAME_-_EMULADORES_%25281%2529_%25281%2529.apk/file' },
    { nombre: 'PS2 MOBILE (APK)', url: 'https://www.mediafire.com/file/ahhv40xlukvzbh2/Igames_ps2_%2528Premium%2529_%25281%2529.apk/file' }
  ]
};

// Copia oculta de cada entrega (para que veas que salió). Vacío = sin copia.
var BCC = '';

// price de Stripe → qué entregar (NO tocar salvo que cambien los productos)
var PRICE_A_COMBO = {
  'price_1U1cSuEIkdT1ZKlov4UV6J0Z': ['principal'],                        // $34.99
  'price_1U1cSwEIkdT1ZKlokreSSUvx': ['principal', 'gold-pc'],             // $59.98 + Leyenda
  'price_1U1cT9EIkdT1ZKlo85QCkIG9': ['principal', 'gold-mob'],            // $59.98 + Supremo
  'price_1U1cTCEIkdT1ZKlo7WVqVvnO': ['principal', 'gold-pc', 'gold-mob']  // $74.99 todo
};

var NOMBRES = {
  'principal': '&#128377;&#65039; MULTICONSOLA ULTIMATE RETRO&#8482;',
  'gold-pc': '&#127918; ULTIMATE LEYENDA',
  'gold-mob': '&#128241; PACK SUPREMO MOBILE'
};

// ═════════════════════════════════════════════════════════════
//  WEBHOOK
// ═════════════════════════════════════════════════════════════
function doPost(e) {
  var ok = ContentService.createTextOutput('ok');
  try {
    var props = PropertiesService.getScriptProperties();

    // 1. seguridad: el token de la URL debe coincidir
    if (!e || !e.parameter || e.parameter.token !== props.getProperty('TOKEN')) {
      console.warn('token inválido');
      return ok; // 200 igual: no darle pistas a nadie
    }

    var evento = JSON.parse(e.postData.contents);
    if (evento.type !== 'checkout.session.completed') return ok;

    var sesion = evento.data.object;
    var correo = (sesion.customer_details && sesion.customer_details.email) || sesion.customer_email;
    var nombre = (sesion.customer_details && sesion.customer_details.name) || '';
    if (!correo) { console.error('sesión sin correo: ' + sesion.id); return ok; }

    // 2. idempotencia: si Stripe reintenta, no mandar dos veces
    var marca = 'sent_' + sesion.id;
    if (props.getProperty(marca)) return ok;

    // 3. ¿qué compró? — por line items (certero) o por client_reference_id (respaldo)
    var combos = combosDeLaSesion(sesion, props);

    // 4. mandar el correo
    enviarEntrega(correo, nombre, combos);
    props.setProperty(marca, new Date().toISOString());
    console.log('entregado a ' + correo + ': ' + combos.join(', '));
  } catch (err) {
    console.error('ERROR: ' + err + (err.stack ? '\n' + err.stack : ''));
  }
  return ok; // siempre 200: si algo falla queda en los logs, no en reintentos infinitos
}

function combosDeLaSesion(sesion, props) {
  // certero: preguntar a Stripe los line items de la sesión
  try {
    var key = props.getProperty('STRIPE_KEY');
    if (key) {
      var r = UrlFetchApp.fetch(
        'https://api.stripe.com/v1/checkout/sessions/' + encodeURIComponent(sesion.id) + '/line_items?limit=10',
        { headers: { Authorization: 'Bearer ' + key }, muteHttpExceptions: true }
      );
      if (r.getResponseCode() === 200) {
        var items = JSON.parse(r.getContentText()).data || [];
        for (var i = 0; i < items.length; i++) {
          var pid = items[i].price && items[i].price.id;
          if (PRICE_A_COMBO[pid]) return PRICE_A_COMBO[pid];
        }
      }
    }
  } catch (e2) { console.warn('line items falló: ' + e2); }

  // respaldo: la landing manda el combo en client_reference_id ("principal-gold-pc__...")
  var ref = String(sesion.client_reference_id || '');
  if (ref.indexOf('gold-pc') > -1 && ref.indexOf('gold-mob') > -1) return ['principal', 'gold-pc', 'gold-mob'];
  if (ref.indexOf('gold-pc') > -1) return ['principal', 'gold-pc'];
  if (ref.indexOf('gold-mob') > -1) return ['principal', 'gold-mob'];
  if (ref.indexOf('principal') > -1) return ['principal'];

  // último recurso: entregar TODO (mejor de más que un cliente sin producto)
  console.warn('combo desconocido en ' + sesion.id + ' — se entrega todo');
  return ['principal', 'gold-pc', 'gold-mob'];
}

// ═════════════════════════════════════════════════════════════
//  EL CORREO
// ═════════════════════════════════════════════════════════════
function enviarEntrega(correo, nombre, combos) {
  var saludo = nombre ? nombre.split(' ')[0] : 'crack';
  var adjuntos = [];
  var filas = '';

  combos.forEach(function (c) {
    var lista = ENTREGABLES[c] || [];
    filas += '<tr><td style="padding:18px 0 6px;font-size:16px;font-weight:800;color:#0a3d22;">' + NOMBRES[c] + '</td></tr>';
    if (!lista.length) {
      filas += '<tr><td style="padding:2px 0;color:#555;font-size:14px;">Tu acceso llega en un correo aparte en los próximos minutos.</td></tr>';
    }
    lista.forEach(function (item) {
      if (item.adjuntar && item.driveId) {
        try { adjuntos.push(DriveApp.getFileById(item.driveId).getBlob()); } catch (e3) { console.error('adjunto falló: ' + item.nombre); }
        filas += '<tr><td style="padding:2px 0;font-size:14px;color:#333;">&#128206; ' + item.nombre + ' — va adjunto a este correo</td></tr>';
      } else {
        var url = item.url || ('https://drive.google.com/file/d/' + item.driveId + '/view');
        filas += '<tr><td style="padding:6px 0;">' +
          '<a href="' + url + '" style="display:inline-block;background:#1db954;color:#ffffff;font-weight:800;' +
          'padding:12px 22px;border-radius:10px;text-decoration:none;font-size:14px;">&#11015;&#65039; Descargar: ' + item.nombre + '</a></td></tr>';
      }
    });
  });

  var html =
    '<div style="background:#f4f6f4;padding:28px 12px;font-family:Arial,Helvetica,sans-serif;">' +
    '<table align="center" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;">' +
    '<tr><td style="background:#0a0f0a;padding:28px;text-align:center;">' +
    '<div style="font-size:40px;">&#128377;&#65039;</div>' +
    '<div style="color:#3cff91;font-size:24px;font-weight:900;letter-spacing:1px;">¡GRACIAS POR TU COMPRA, ' + saludo.toUpperCase() + '!</div>' +
    '<div style="color:#9aa0a6;font-size:13px;margin-top:6px;letter-spacing:2px;">THE GAME BOX™ · +65.000 JUEGOS RETRO</div>' +
    '</td></tr>' +
    '<tr><td style="padding:26px 32px 30px;">' +
    '<p style="font-size:15px;color:#333;margin:0 0 6px;">Aquí está <b>todo lo tuyo</b>. Descarga, sigue la guía y en 5 minutos estás jugando:</p>' +
    '<table width="100%" cellpadding="0" cellspacing="0">' + filas + '</table>' +
    '<p style="font-size:13px;color:#777;margin:26px 0 0;">¿Algún problema con la descarga? Responde este correo o escríbenos por ' +
    '<a href="https://wa.me/573102611023" style="color:#1db954;font-weight:700;">WhatsApp</a> y te ayudamos al instante.</p>' +
    '</td></tr></table></div>';

  var opciones = { htmlBody: html, name: 'The Game Box' };
  if (adjuntos.length) opciones.attachments = adjuntos;
  if (BCC) opciones.bcc = BCC;

  GmailApp.sendEmail(correo, 'Tu MULTICONSOLA está aquí — descarga todo', 'Tu compra está confirmada. Abre este correo para descargar todo.', opciones);
}

// ═════════════════════════════════════════════════════════════
//  PRUEBA MANUAL — Ejecutar > probarEnvio (manda una entrega
//  de ejemplo del combo completo A TU PROPIA cuenta)
// ═════════════════════════════════════════════════════════════
function probarEnvio() {
  var yo = Session.getActiveUser().getEmail();
  enviarEntrega(yo, 'Esteban', ['principal', 'gold-pc', 'gold-mob']);
  console.log('correo de prueba enviado a ' + yo);
}
