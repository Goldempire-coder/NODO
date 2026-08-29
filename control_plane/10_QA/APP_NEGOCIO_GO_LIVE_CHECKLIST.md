# App Negocio Go-Live Checklist

Estado: DRAFT_LOCAL_CHECKLIST
Superficie inicial: Mini App Negocio
Objetivo: confirmar que la app es clara, segura y economica antes de ampliar el gate de produccion.

Este checklist no autoriza produccion por si solo. Cada item requiere evidencia
local, staging o manual segun corresponda.

## Fronteras

- No cambiar contratos, watcher, ledger, acreditacion ni autoridad financiera por ajustes de UI.
- No ocultar errores financieros reales con copy de frontend.
- No cargar listas completas si existe paginacion, cursor o filtro.
- No guardar secretos, private keys, tokens ni hashes completos en UI, logs o docs.
- No tocar produccion sin aprobacion Owner separada.

## App Negocio

- Navegacion movil: tabs visibles, sin solaparse con contenido ni bloquear acciones.
- Scroll movil: cada pantalla larga debe permitir llegar a todas las acciones relevantes.
- Anuncios publicados: mostrar los anuncios activos visibles y permitir cargar mas con cursor.
- Anuncios publicados: cada anuncio debe conservar sus acciones propias de editar, pausar y cerrar.
- Anuncios publicados: no debe existir scroll horizontal accidental.
- Ordenes: listar con paginacion o limite; no cargar historiales completos.
- Ordenes: estados claros para pendiente, completada, cancelada y disputa.
- Creditos: un CTA principal por etapa; evitar botones duplicados que compitan.
- Creditos: estado de espera sin timer visible y con mensaje de acreditacion automatica.
- Creditos: exito claro con creditos acreditados y boton para volver a creditos.
- Creditos: salida de pago pendiente sin romper idempotencia ni watcher.
- Perfil: acceso visible a terminos de negocio y privacidad.
- Soporte: estados de carga, vacio y error sin dejar pantallas a medias.

## UX Y Contenido

- Titulos unicos y claros por pantalla.
- Mensajes de error accionables, sin lenguaje tecnico innecesario.
- Mensajes de exito que cierren el flujo y digan que paso.
- Loading/skeleton solo donde haya espera real; sin botones titilando.
- Botones deshabilitados deben explicar o mostrar estado cuando aplique.
- Iconos usados solo para reforzar estado, no como unica fuente de informacion.
- Copy de produccion: no usar "prueba", "testnet" o instrucciones de faucet en negocio real.
- Modo oscuro: contraste suficiente en texto, bordes, iconos y botones.

## Seguridad

- Autenticacion obligatoria en todas las rutas de negocio.
- Backend autoriza negocio, usuario activo y access link activo; Telegram ID no basta solo.
- Acciones sensibles protegidas por backend y PIN cuando aplique.
- Validacion de entradas en backend; frontend solo ayuda.
- Parametros, IDs y cursors tratados como no confiables.
- Sin exposicion de secretos de API, RPC privados, signer keys o wallets internas completas.
- Cookies/tokens protegidos por flags adecuados donde aplique.
- Rate limits activos para login, handoff, pagos y acciones sensibles.
- Headers de seguridad revisados antes de produccion.
- Dependencias auditadas antes de produccion.

## Costo Y Performance

- No polling global si la pantalla no esta visible.
- Polling solo en estados que lo necesitan y con intervalos acotados.
- Listas grandes con paginacion, filtros o cursores.
- Imagenes optimizadas y sin assets innecesarios en la primera carga.
- Evitar llamadas duplicadas al volver de MetaMask o Telegram.
- Reusar estado local solo para presentacion, no como autoridad financiera.
- Build web de produccion medido antes del release.

## Web Publica Y SEO

- Pagina 404 personalizada.
- `robots.txt` revisado.
- Sitemap revisado si hay rutas publicas indexables.
- Titulos y metadescripciones por pagina publica.
- Imagen social para compartir.
- Favicon custom.
- Enlaces internos y footer sin links rotos.
- Politica de privacidad y terminos visibles donde corresponda.

## Evidencia Minima Antes De Produccion

- `git diff --check`: PASS.
- Tests estaticos de App Negocio: PASS.
- Build web production: PASS.
- QA movil iPhone de Anuncios, Ordenes, Creditos, Soporte y Perfil.
- Staging frontend/backend con SHA esperado.
- Rollback documentado y probado para web/backend.
- Checklist de secretos sin hallazgos.
- Decision Owner explicita para pasar a produccion.
