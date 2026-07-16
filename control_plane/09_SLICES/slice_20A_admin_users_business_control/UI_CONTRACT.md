# UI_CONTRACT.md

## Pantalla A-10 Admin Users

Admin Web desktop-first.

Debe incluir:
- sidebar y top bar admin ya existentes;
- tabla de usuarios con filtros por phone, telegram_id, username, role, status;
- cursor pagination;
- busqueda con estado loading/empty/error/forbidden;
- detalle en panel lateral/split view;
- estado visible de usuario;
- links de negocio asociados;
- acciones: suspender, reactivar, bloquear;
- modales de confirmacion con reason obligatorio;
- resultado success/error seguro;
- datos sensibles enmascarados por defecto.

Support:
- ve lista/detalle masked;
- no ve controles mutantes habilitados.

No usa Telegram Mini App shell, Telegram MainButton, bottom nav Telegram ni `themeParams` como regla activa.

No incluye soporte/tickets real, chat admin ni cambios de rol salvo contrato futuro.
