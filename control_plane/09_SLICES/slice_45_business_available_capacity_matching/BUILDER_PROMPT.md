# Builder Prompt

SKILLS A USAR

- spec-driven-development
- codebase-recon
- api-and-interface-design
- security-and-hardening
- code-review-and-quality
- supabase-postgres-best-practices
- performance-optimization
- test-driven-development
- frontend-ui-engineering
- observability-and-instrumentation
- git-workflow-and-versioning

AFOS es la autoridad principal. Este slice gobierna el alcance.

ESTADO ESPERADO

`INSPECTION_COMPLETE_READY_FOR_OWNER_REVIEW` o `BLOCKED_BY_EXPLICIT_EVIDENCE`.

MODO

Solo inspeccion y plan. No modifiques archivos. No escribas migraciones. No hagas deploy.

OBJETIVO

Mapea como NODO maneja hoy:

1. online/offline del negocio;
2. limites por operacion;
3. limite diario;
4. anuncios activos;
5. `ad.status = in_order`;
6. creacion de ordenes;
7. cancelacion/expiracion/completado;
8. marketplace search por monto;
9. admin detail de negocio;
10. capacidad/ordenes abiertas si ya existe algo parecido.

Luego propone el plan minimo para implementar `slice_45_business_available_capacity_matching`.

ANTES DE TOCAR ARCHIVOS

1. Confirma:
   - `Get-Location`
   - `git status --short --branch`
   - rama actual
   - archivos modificados/no rastreados
2. Lee:
   - `control_plane/09_SLICES/slice_45_business_available_capacity_matching/`
   - `control_plane/06_API_CONTRACTS/ADS_API.md`
   - `control_plane/06_API_CONTRACTS/ORDERS_API.md`
   - `control_plane/06_API_CONTRACTS/BUSINESS_ORDERS_API.md`
   - contrato de pantalla B-04 Business Dashboard
   - contrato de pantalla B-09 My Ads
   - contrato de pantalla R-04 Business Detail
3. Revisa codigo runtime relevante antes de opinar.

PREGUNTAS QUE DEBES RESPONDER

- Donde vive hoy online/offline del negocio?
- Que campos existen hoy para min/max/daily limit?
- Search filtra por monto antes o despues de cargar anuncios?
- Crear orden bloquea el anuncio completo?
- Que pasa si una orden de 30 usa un anuncio de 100?
- Hay forma actual de reservar capacidad parcial?
- Que transiciones de orden deben liberar o consumir reserva?
- Que tabla/migracion minima propones?
- Que endpoints nuevos o cambios de endpoints propones?
- Que partes frontend hay que tocar en negocio, cliente y admin?
- Que pruebas negativas y de concurrencia son obligatorias?

PROPUESTA ESPERADA

Entrega:

1. Estado.
2. Mapa actual con archivos exactos.
3. Conflictos contra el contrato del slice.
4. Plan recomendado en paquetes pequenos.
5. Migracion propuesta, sin crearla.
6. Endpoints propuestos.
7. Tests propuestos.
8. Riesgos y decisiones que requieren Owner.
9. Que NO tocarias.

NO TOCAR

- No modificar archivos.
- No commit.
- No deploy.
- No migraciones.
- No pagos.
- No creditos.
- No Base USDC.
- No Zelle.
- No soporte.
- No reputacion.
- No intake.
- No reset DB.
- No borrar datos.
- No declarar `READY_FOR_REAL_USE`.

VALIDACION DE INSPECCION

Puedes ejecutar solo comandos read-only:

```powershell
git status --short --branch
rg -n "availability|online|offline|min_order|max_order|daily_limit|in_order|amount_max|amount_min|create_order|ads/search|ORDER_STATUS" apps control_plane database
```

Si necesitas ejecutar tests para entender comportamiento actual, pide aprobacion antes.
