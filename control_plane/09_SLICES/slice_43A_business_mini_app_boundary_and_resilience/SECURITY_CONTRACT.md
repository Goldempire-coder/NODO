# Security Contract

## Regla principal

La Mini App Negocio puede ver datos operativos necesarios para operar su propio
negocio, pero no puede recibir senales internas de riesgo, fraude, revision o
ranking reservado para Admin.

## Campos prohibidos para superficie negocio no-admin

La respuesta de `surface/session` para negocio no debe incluir:

- `risk_level`
- senales antifraude internas
- flags de investigacion
- notas admin
- rutas internas de storage
- signed URLs privadas no solicitadas por accion autorizada
- tokens, secretos o hashes internos

## `trust_level`

El Builder debe revisar el contrato vigente antes de tocar este campo.

Si `trust_level` se usa como senal interna o fue reemplazado por
`reputation_tier`, no debe salir en la sesion de negocio. Si existe una razon
contractual para mantenerlo, el Builder debe documentar esa evidencia y dejar
el cambio fuera.

## Prueba minima

Debe existir una prueba que construya o consulte el payload de negocio no-admin
y confirme que no aparecen los campos prohibidos. La prueba debe poder fallar
si alguien vuelve a agregar `risk_level`.

## Seguridad no incluida

Este slice no cambia el modelo de tokens. El riesgo residual de tokens
accesibles a JavaScript queda para un slice de auth separado.
