# SCOPE.md

## Construir

1. Matriz AFOS de la Mini App Negocio.
   - control
   - estado
   - evidencia
   - archivo
   - test
   - riesgo residual

2. Refactor dirigido de responsabilidades frontend.
   - separar logica de metodos de cobro si `useBusinessAccessModel.ts` sigue concentrando formulario, mutacion, PIN y perfil;
   - separar logica de anuncios si `useBusinessAdsModel.ts` sigue concentrando formulario, mutacion, refresh y telemetria;
   - separar compra Base USDC si `useBusinessCreditsModel.ts` sigue concentrando dashboard, compra, pendiente y referidos.

3. Matriz de acciones sensibles.
   - accion
   - requiere PIN
   - endpoint
   - idempotency key
   - audit event
   - test
   - razon

4. Observabilidad segura de Mini App Negocio.
   - breadcrumbs de accion y pantalla;
   - duracion de acciones criticas;
   - errores de API por route template;
   - sin Zelle completo, wallet completa, tx hash completo, PIN, token, correo completo, storage path ni URL firmada.

5. Medicion de fluidez de pantalla.
   - transicion entre Inicio, Anuncios, Ordenes, Creditos, Perfil;
   - deteccion de loading innecesario;
   - evidencia local automatizada o Playwright si aplica.

6. Correcciones pequenas demostradas.
   - bugs reales encontrados durante la auditoria;
   - solo si tienen reproduccion y prueba.

7. Manifest final.
   - archivos tocados;
   - pruebas ejecutadas;
   - controles AFOS PASS/PARTIAL/FAIL;
   - riesgos pendientes.

## No construir

Ver `DO_NOT_BUILD.md`.

## Modulos esperados

Frontend:

- `apps/web/src/hooks/business-mini-app/*`
- `apps/web/src/screens/business-app/*`
- `apps/web/src/observability/clientTelemetry.ts`
- tests estaticos o UI relacionados.

Backend:

- solo si una regla sensible esta mal ubicada o falta evidencia;
- preferir tests primero;
- no cambiar comportamiento financiero sin contrato explicito.

Governance:

- reporte builder en `governance/builder_reports/`;
- evidencia en `evidence/slice_runs/`;
- matriz AFOS o auditoria en `governance/owner_reviews/`.
