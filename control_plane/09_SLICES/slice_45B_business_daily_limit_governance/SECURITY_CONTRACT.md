# SECURITY_CONTRACT.md

## Principio

El limite diario evita que el negocio acepte mas de lo que el Owner autorizo para ese dia. No es custodia, no es saldo financiero y no prueba que el negocio tenga fondos reales.

## Backend como autoridad

- Cliente no puede declarar que un negocio tiene cupo.
- Negocio no puede saltarse el limite diario desde la UI.
- Admin puede ajustar limites solo mediante ruta autorizada.
- Crear orden siempre revalida cupo diario en backend.
- La busqueda del marketplace nunca sustituye la validacion final de orden.

## Privacidad

El cliente no debe recibir:

- `daily_limit_usd`;
- `daily_reserved_usd`;
- `daily_consumed_usd`;
- `daily_remaining_usd`;
- `declared_available_capacity_usd`;
- `reserved_capacity_usd`;
- `effective_available_capacity_usd`;
- `risk_level`;
- `trust_level`.

El cliente solo necesita saber si el negocio puede cubrir el monto solicitado.

## Auditoria

Debe existir evidencia para reconstruir:

- quien ajusto limite diario;
- quien ajusto capacidad disponible;
- que orden reservo cupo;
- que orden libero cupo;
- que orden consumio cupo;
- por que se rechazo una orden por limite diario.

Los logs no deben incluir:

- tokens;
- wallets completas;
- datos bancarios;
- cuerpos privados de chat;
- documentos privados.

## Riesgos bloqueantes

- Dos clientes reservan el mismo cupo diario.
- Cancelar una orden ya consumida devuelve cupo diario.
- Una disputa libera cupo sin resolucion.
- Cliente ve numeros internos del negocio.
- Frontend puede abrir orden aunque backend ya no tenga cupo.

## Rollback

Si 45B requiere codigo, el rollback debe dejar el sistema en la regla segura:

```txt
si no se puede calcular cupo diario, no aceptar nuevas ordenes
```

