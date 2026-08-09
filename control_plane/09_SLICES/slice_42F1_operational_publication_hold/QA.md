# QA 42F1

## Gates funcionales

- Reporte durante pausa crea ticket y hold; fuera de pausa crea solo ticket.
- Ticket, mensaje, evento y hold son atomicos en PostgreSQL.
- Un reporte concurrente no duplica ticket ni hold.
- Cerrar o resolver ticket no libera el hold.
- Release Admin exige reason e idempotencia y solo produce un efecto durable.
- Varios holds del negocio deben liberarse individualmente.
- Hold bloquea ads, marketplace y orden directa sin mutaciones parciales.
- La carrera donde el hold gana el lock del negocio falla cerrada.
- Cliente y negocio no reciben existencia, origen ni causa del hold.

## Infra local

- Aplicar migraciones completas hasta 0052 en PostgreSQL 16 desechable.
- Probar 0052 down/up con rollback fail-closed si existen holds.
- Ejecutar `test_operational_publication_holds_postgres.py` con opt-in local.

## Fuera de este gate

- Telegram Admin 42F2.
- UI Admin para listar/liberar holds.
- Delegacion Support de release.
- Staging, produccion y `READY_FOR_REAL_USE`.
