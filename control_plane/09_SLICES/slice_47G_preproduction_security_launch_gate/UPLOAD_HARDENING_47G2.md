# Slice 47G2 - Upload Hardening

Estado: IMPLEMENTED_LOCAL_READY_FOR_VALIDATOR_REVIEW

## Alcance

47G2 valida contenido documental real antes de storage en:

- comprobante manual de compra de creditos;
- Business Intake por endpoint HTTP y descarga Telegram;
- verificacion documental legacy interna/test fixture.

No habilita el onboarding publico legacy y no cambia asignacion de creditos,
wallets, pagos, ordenes, marketplace ni reglas financieras.

## Regla

| Tipo | Validacion | Nombre almacenado |
|---|---|---|
| JPG | decodificacion completa y MIME coincidente | `photo.jpg` |
| PNG | decodificacion completa y MIME coincidente | `photo.png` |
| WebP | decodificacion completa y MIME coincidente | `photo.webp` |
| PDF | encabezado PDF valido y `%%EOF` final | `document.pdf` |

Todas las superficies conservan su limite de 5 MB. El backend no ejecuta,
renderiza ni interpreta PDF y rechaza marcadores activos obvios. HTML, SVG, ZIP, scripts, bytes arbitrarios,
imagenes corruptas y MIME discordante se rechazan con un error neutral.

## Atomicidad De Rechazo

La validacion ocurre antes de consultar o mutar el recurso de negocio y antes de
storage. Un archivo rechazado no crea compra, documento, `file_asset`, evento,
audit, notificacion Admin ni objeto en storage.

## Riesgo Residual

La comprobacion PDF valida su envoltura, no sustituye antivirus, CDR ni analisis
profundo de contenido activo. Los documentos permanecen en storage privado y el
backend no los ejecuta ni renderiza. Un scanner aislado es un slice futuro si el
modelo de amenaza o el volumen lo exige.
