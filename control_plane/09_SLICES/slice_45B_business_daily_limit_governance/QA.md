# QA.md

## Pruebas minimas

### Negocio llega al limite diario

```txt
daily_limit_usd = 1000.00
daily_consumed_usd = 900.00
daily_reserved_usd = 100.00
cliente pide = 20.00
resultado = rechazo por limite diario
```

### Reserva abierta cruza de dia

Una reserva abierta creada ayer debe seguir sumando en `daily_reserved_usd`
hasta quedar `released` o `consumed`.

### Consumo cruza de dia

Una reserva creada ayer y consumida hoy debe sumar en `daily_consumed_usd`
porque la autoridad temporal es `consumed_at`, no `created_at`.

### Negocio aun tiene cupo

```txt
daily_limit_usd = 1000.00
daily_consumed_usd = 400.00
daily_reserved_usd = 300.00
cliente pide = 100.00
resultado = permite si tambien hay capacidad efectiva
```

### Cancelacion antes de pago

Crear orden de `100.00`, cancelar antes de pago y verificar:

- reserva queda `released`;
- `daily_remaining_usd` vuelve a subir;
- replay de cancelacion no duplica liberacion.

### Orden completada

Crear orden de `100.00`, completarla y verificar:

- reserva queda `consumed`;
- `daily_remaining_usd` baja durante el dia;
- recargar o replay no consume dos veces.

### Disputa

Abrir disputa y verificar:

- cupo sigue retenido;
- no aparece como disponible;
- resolucion define `released` o `consumed`.

### Carrera

Dos clientes intentan reservar al mismo tiempo cuando queda cupo para uno solo.

Resultado:

- una orden gana;
- una orden falla;
- no hay cupo negativo;
- no hay doble reserva.

### Privacidad cliente

Buscar negocios desde Cliente y verificar que la respuesta no contiene:

- `daily_limit_usd`;
- `daily_reserved_usd`;
- `daily_consumed_usd`;
- `daily_remaining_usd`;
- `declared_available_capacity_usd`;
- `effective_available_capacity_usd`;
- `risk_level`;
- `trust_level`.

### Visibilidad negocio

Mini App Negocio debe mostrar:

- limite diario;
- usado/reservado hoy;
- restante hoy;
- reinicio diario;
- bloqueo claro si no puede aceptar mas ordenes.

### Visibilidad admin

Admin debe ver:

- limite diario;
- reservado;
- consumido;
- restante;
- ordenes que explican el calculo;
- actor de cambios manuales.

## Comandos esperados

Builder debe proponer comandos exactos despues del mapeo. Base esperada:

```powershell
python -m pytest apps/api/tests/test_business_capacity_matching.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
pnpm --filter @nodo/web build
git diff --check
```

## Evidencia insuficiente

- La pantalla se ve bien.
- El endpoint respondio `200`.
- El cliente no vio el negocio una sola vez.
- Se probo solo con un monto.
- No se probo carrera.
- No se probo cancelacion, completion y disputa.
