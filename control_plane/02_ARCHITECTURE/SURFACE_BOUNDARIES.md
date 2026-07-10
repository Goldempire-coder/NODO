# SURFACE_BOUNDARIES.md

## Superficies

```txt
apps/
  client-miniapp/      # futuro: Mini App Cliente
  business-miniapp/    # futuro: Mini App Negocio
  admin-web/           # futuro: Panel Admin Web Desktop
  bot/                 # futuro: Bot Registro Negocios
  api/                 # backend unico compartido
```

La estructura exacta puede implementarse en el repo actual como apps separadas o rutas/shells separadas dentro de `apps/web`, pero el contrato funcional exige boundaries claros.

## Reglas

- Cliente no importa pantallas negocio/admin.
- Negocio no importa pantallas cliente/admin salvo componentes compartidos.
- Admin web no usa shell mobile de Telegram ni bottom nav cliente.
- Bot no depende de componentes web.
- `api/` es compartido y valida permisos por backend.
- Componentes compartidos viven en una capa comun sin reglas de negocio.

## Build

Cada superficie debe tener build/test verificable:

- client mini app build
- business mini app build
- admin web build
- bot tests
- backend tests

## CORS/origins

Admin web, client mini app y business mini app pueden tener origenes distintos. Backend debe validar CORS por env y no asumir un solo frontend.
