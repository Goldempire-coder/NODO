# Telegram Bot Welcome Webhook - 2026-07-07

## Estado

`READY_FOR_OWNER_REVIEW`

## Objetivo

Configurar el bot de Telegram para que al recibir `/start` envie una bienvenida visual de NODO y un boton nativo `Abrir NODO` que abre la Mini App.

## Cambios realizados

- Se publico `apps/web/public/telegram-welcome.jpg`.
- Se agrego ruta backend protegida:
  - `POST /api/v1/telegram/webhook/{secret}`
- Se agrego modulo:
  - `apps/api/app/routes/telegram_bot.py`
- Se agregaron settings:
  - `TELEGRAM_WEB_APP_URL`
  - `TELEGRAM_WELCOME_IMAGE_URL`
- Se agregaron errores seguros:
  - `TELEGRAM_BOT_NOT_CONFIGURED`
  - `TELEGRAM_BOT_SEND_FAILED`
- Se agregaron tests:
  - `apps/api/tests/test_telegram_bot_webhook.py`

## Comportamiento

- `/start` envia `sendPhoto` con `https://nodo-staging.pages.dev/telegram-welcome.jpg`.
- El mensaje incluye boton inline:
  - texto: `Abrir NODO`
  - tipo: `web_app`
  - URL: `https://nodo-staging.pages.dev`
- Si Telegram no puede enviar la foto, el backend intenta fallback con `sendMessage` y el mismo boton.
- Cualquier texto distinto a `/start` responde con un mensaje corto y el boton `Abrir NODO`.

## Seguridad

- El webhook no queda abierto publicamente; usa un secreto de ruta derivado del `BOT_TOKEN`.
- El `BOT_TOKEN` no se imprime ni se expone en frontend.
- El webhook rechaza secretos incorrectos con `FORBIDDEN`.
- La URL de webhook fue redactada en evidencia.

## Validacion

- `python -m pytest apps\api\tests\test_telegram_bot_webhook.py -q`: `3 passed, 1 warning`
- `python -m pytest apps\api\tests -q`: `103 passed, 1 warning`
- `python -m ruff check apps\api scripts`: OK
- `python -m compileall apps\api\app\routes\telegram_bot.py apps\api\app\core\config.py apps\api\app\main.py`: OK
- `corepack pnpm --filter @nodo/web build`: OK
- Asset publico:
  - `https://nodo-staging.pages.dev/telegram-welcome.jpg`: `200 image/jpeg`, `191806` bytes
- Backend deploy Railway:
  - ruta nueva verificada con secreto falso: `403`
- Telegram:
  - `setWebhook`: `Webhook was set`
  - `getWebhookInfo`: `pending_update_count = 0`, sin `last_error_message`
  - `setChatMenuButton`: OK

## Ajuste posterior de imagen y descripcion

- Se reemplazo la imagen por una composicion vertical mas centrada y limpia generada desde `scripts/build_telegram_welcome_image.py`.
- Imagen publica versionada:
  - `https://nodo-staging.pages.dev/telegram-welcome.jpg?v=20260707164140`: `200 image/jpeg`, `189403` bytes
- Se reemplazo la descripcion generica de Telegram por copy en espanol:
  - descripcion: `Conecta con negocios verificados para cambiar de forma simple, rápida y confiable en NODO.`
  - short description: `Cambios con negocios verificados.`
- Se redesplego frontend en Cloudflare Pages.
- Se redesplego backend en Railway para usar URL versionada y evitar cache viejo de Telegram.
- Validacion posterior:
  - `python -m pytest apps\api\tests\test_telegram_bot_webhook.py -q`: `3 passed, 1 warning`
  - `python -m ruff check apps\api\app\routes\telegram_bot.py apps\api\app\core\config.py apps\api\tests\test_telegram_bot_webhook.py`: OK
  - webhook Railway con secreto falso: `403`
  - `getWebhookInfo`: `pending_update_count = 0`, sin `last_error_message`

## Ajuste de boton nativo

- Telegram no permite imagen dentro de `What can this bot do?`; esa zona es solo texto de descripcion.
- Se removio el boton inline `Abrir NODO` del mensaje `/start`.
- Se mantiene el boton nativo de Telegram `Abrir NODO` mediante `setChatMenuButton`.
- `/start` ahora envia solo imagen + caption corto.
- Mensajes no `/start` envian solo una indicacion corta para usar el boton nativo.
- Validacion:
  - `python -m pytest apps\api\tests\test_telegram_bot_webhook.py -q`: `3 passed, 1 warning`
  - `python -m ruff check apps\api\app\routes\telegram_bot.py apps\api\tests\test_telegram_bot_webhook.py`: OK
  - Railway deploy: OK
  - webhook con secreto falso: `403`
  - `getWebhookInfo`: `pending_update_count = 0`, sin `last_error_message`

## Ajuste visual de `Como funciona`

- Se corrigio la composicion de `telegram-welcome.jpg` porque el titulo `Como funciona` quedaba montado sobre el borde de la tarjeta al verse comprimido en Telegram.
- El titulo ahora queda dentro de la tarjeta, con espacio arriba y abajo.
- Se redujo ligeramente el alto de las filas para evitar solapes visuales.
- Nueva imagen generada:
  - `apps/web/public/telegram-welcome.jpg`: `187738` bytes
- Validacion publica:
  - `https://nodo-staging.pages.dev/telegram-welcome.jpg?v=20260707165820`: `200 image/jpeg`, `187738` bytes
  - `https://main.nodo-staging.pages.dev/telegram-welcome.jpg`: `200 image/jpeg`, `187738` bytes
- Validacion tecnica:
  - `corepack pnpm --filter @nodo/web build`: OK
  - `python -m pytest apps\api\tests\test_telegram_bot_webhook.py -q`: `3 passed, 1 warning`
  - `python -m ruff check apps\api\app\core\config.py apps\api\app\routes\telegram_bot.py apps\api\tests\test_telegram_bot_webhook.py`: OK
  - Cloudflare Pages deploy: OK
  - Railway deploy: OK
  - `getWebhookInfo`: `pending_update_count = 0`, sin `last_error_message`

## Ajuste de peso tipografico en pasos

- Se corrigio el paso `Elige un negocio verificado` porque estaba en negrita y no coincidia con el resto de los pasos.
- Todos los pasos ahora usan el mismo peso tipografico.
- Nueva imagen generada:
  - `apps/web/public/telegram-welcome.jpg`: `186898` bytes
- Se uso temporalmente `https://main.nodo-staging.pages.dev/telegram-welcome.jpg?v=20260707170427` como URL de imagen para el bot porque `nodo-staging.pages.dev` seguia sirviendo cache anterior durante la verificacion.
- Validacion publica:
  - `https://main.nodo-staging.pages.dev/telegram-welcome.jpg?v=20260707170427`: `200 image/jpeg`, `186898` bytes
- Validacion tecnica:
  - `corepack pnpm --filter @nodo/web build`: OK
  - `python -m pytest apps\api\tests\test_telegram_bot_webhook.py -q`: `3 passed, 1 warning`
  - `python -m ruff check apps\api\app\core\config.py apps\api\app\routes\telegram_bot.py apps\api\tests\test_telegram_bot_webhook.py`: OK
  - Cloudflare Pages deploy: OK
  - Railway deploy: OK
  - webhook con secreto falso: `403`
  - `getWebhookInfo`: `pending_update_count = 0`, sin `last_error_message`

## No realizado

- No se cambio flujo de ordenes.
- No se cambio auth de Mini App.
- No se cambio copy interno de pantallas.
- No se tocaron reglas de negocio, pagos, creditos, disputas ni admin.
- No se imprimieron secretos.
