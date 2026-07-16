# ACCEPTANCE_CRITERIA.md

El slice pasa solo si:

- Existe matriz AFOS de Mini App Negocio con PASS/PARTIAL/FAIL y evidencia.
- Existe matriz de acciones sensibles.
- El hook principal sigue siendo ensamblador.
- Hooks grandes quedan reducidos o con excepcion justificada.
- Acciones de metodos de cobro, anuncios y creditos tienen estados por accion.
- Transiciones principales tienen evidencia de fluidez o medicion.
- Observabilidad no captura datos sensibles.
- Tests obligatorios pasan.
- Build web pasa.
- Scan de secretos pasa.
- No hay cambios de produccion ni deploy no autorizado.
- No se toca wallet privada ni se agrega secreto al repo.
- Riesgos pendientes quedan ordenados por severidad.

Bloquea si:

- Se mueve una regla financiera al frontend.
- Se elimina una validacion backend.
- Se registra PIN, token, Zelle completo, wallet USDT completa, wallet privada o tx hash completo.
- Se rompe ownership.
- Se acredita credito sin verifier backend.
- Se cambia contrato API sin pruebas.
- Se introduce un global busy que congele botones independientes.
- Se declara production-ready.
