# SECURITY_CONTRACT.md

## Riesgos principales

- Un cliente abre una orden mayor a la capacidad real declarada.
- Dos clientes reservan la misma capacidad al mismo tiempo.
- El cliente ve informacion operativa sensible del negocio.
- El negocio declara disponibilidad que el backend no valida.
- Admin ajusta limites sin trazabilidad.
- Una orden cancelada o expirada deja capacidad bloqueada para siempre.

## Controles obligatorios

- Backend calcula y valida capacidad efectiva.
- Frontend no puede declarar `reserved_capacity_usd` ni `effective_available_capacity_usd`.
- Crear orden usa transaccion o bloqueo equivalente.
- Reservas tienen `order_id` unico.
- Liberar/consumir reserva es idempotente.
- Admin y negocio ven montos exactos; cliente solo ve compatibilidad salvo aprobacion del Owner.
- Audit log para update admin, update negocio, reserva, liberacion y consumo.
- No usar float para USD.
- No escribir montos sensibles en logs de error sin redaccion.

## Privacidad publica

El marketplace no debe revelar al cliente:

- capacidad declarada exacta;
- capacidad reservada;
- capacidad efectiva;
- ordenes abiertas de otros clientes;
- limites internos ajustados por riesgo;
- senales antifraude o `risk_level`.

Permitido para cliente:

- online/offline;
- rango publico del anuncio;
- si cubre el monto solicitado;
- reputacion publica ya aprobada por contratos previos.

## Concurrencia

El caso critico:

```txt
Negocio efectivo: 40.00
Cliente A intenta 30.00
Cliente B intenta 30.00 al mismo tiempo
```

Resultado esperado:

- una orden puede reservar;
- la otra recibe `BUSINESS_CAPACITY_INSUFFICIENT` o equivalente seguro;
- no quedan reservas negativas;
- no se crean dos ordenes validas contra los mismos 40.00.

## No custodia

No usar lenguaje de "saldo custodiado", "deposito", "fondos en NODO" o "garantia". La capacidad es declarativa y operativa.
