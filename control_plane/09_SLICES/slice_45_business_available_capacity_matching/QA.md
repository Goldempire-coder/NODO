# QA.md

## Pruebas backend obligatorias

- Negocio puede guardar `declared_available_capacity_usd`.
- Negocio no puede actualizar capacidad de otro negocio.
- Negocio suspendido/bloqueado no puede ponerse disponible.
- Search solo muestra negocios online que cubren `amount_usd`.
- Search no expone capacidad exacta al cliente.
- Crear orden rechaza monto mayor a capacidad efectiva.
- Crear orden reserva monto exacto.
- Dos ordenes concurrentes no duplican capacidad.
- Idempotency replay de crear orden no duplica reserva.
- Cancelar antes de pago libera reserva.
- Expirar antes de pago libera reserva.
- Completar orden consume reserva.
- Disputa mantiene reserva hasta resolucion.
- Admin puede ver declarado, reservado y efectivo.
- Admin adjustment audita actor, negocio, antes/despues y request_id.

## Pruebas frontend obligatorias

- App Negocio permite actualizar "Disponible ahora" y online/offline.
- App Negocio muestra declarado, reservado y restante.
- App Negocio avisa si restante es menor a 20.00.
- App Cliente pide monto antes de mostrar opciones o re-filtra antes de crear orden.
- App Cliente no muestra negocios que no cubren el monto.
- App Cliente maneja `BUSINESS_CAPACITY_INSUFFICIENT` con mensaje claro y permite elegir otro negocio.
- Admin muestra capacidad en detalle de negocio.

## Pruebas de seguridad

- Cliente no recibe `declared_available_capacity_usd`.
- Cliente no recibe `reserved_capacity_usd`.
- Cliente no recibe `effective_available_capacity_usd`.
- Requests manipulados no pueden forzar capacidad ni saltar online/offline.
- Logs no contienen datos privados no redactados.

## Pruebas de rendimiento

- Search filtra capacidad sin escanear toda la tabla de negocios.
- Indices propuestos para reservas activas y negocios online.
- No offset en listas grandes.

## Comandos esperados

```powershell
python -m pytest apps/api/tests/test_ads_marketplace.py apps/api/tests/test_order_creation.py -q --tb=short
python -m pytest apps/api/tests/test_business_order_ops.py apps/api/tests/test_business_access_control.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

Si se agrega concurrencia real:

```powershell
python -m pytest apps/api/tests/test_business_capacity_matching.py -q --tb=short
```

## Smoke staging futuro

Solo despues de deploy aprobado:

1. negocio aprobado se pone online con `40.00`;
2. cliente busca `30.00` y ve el negocio;
3. cliente crea orden `30.00`;
4. negocio queda con efectivo `10.00`;
5. otro cliente busca `20.00` y ya no ve ese negocio;
6. cliente cancela orden antes de pago;
7. negocio vuelve a efectivo `40.00`;
8. cliente vuelve a verlo para `20.00`.
