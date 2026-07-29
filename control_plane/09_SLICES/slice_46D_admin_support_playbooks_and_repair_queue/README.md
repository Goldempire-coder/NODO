# Slice 46D - Admin Support Playbooks And Repair Queue

Estado: IMPLEMENTATION_46D1_46D2_READY_FOR_OWNER_REVIEW

## Objetivo

Crear el contrato para mapear como Admin y Soporte deben resolver problemas
operativos reales despues de encontrar el caso con 46A, 46B o 46C.

46A encuentra pistas rapidas. 46B abre una ficha de investigacion. 46C busca
ordenes candidatas cuando las pistas son incompletas. 46D no debe agregar otra
busqueda primero: debe ordenar que casos existen, que evidencia necesita cada
caso, que puede resolver el Dashboard hoy y que reparaciones faltan.

El resultado inicial de este slice fue un reporte de brechas y una cola de
reparaciones priorizada. El Owner autorizo despues dos reparaciones acotadas:

- 46D1: panel read-only de revision guiada dentro de la ficha 46B;
- 46D2: UI de asignacion de tickets activos mediante endpoints existentes.

Ninguna de las dos cambia estados de orden, decide culpa o valida pagos.

## Implementacion Autorizada

### 46D1 Case Playbook Panel

- Compone checks neutrales desde la respuesta allowlist de 46B.
- Puede abrir rutas internas ya autorizadas.
- No consulta cuerpos, no descarga adjuntos y no ejecuta mutaciones.

### 46D2 Support Assignment UI

- Reutiliza `GET /api/v1/admin/staff?status=active` para candidatos.
- Excluye perfiles `operations_readonly` de la seleccion.
- Reutiliza `POST /api/v1/admin/support/tickets/{ticket_id}/assign`.
- Exige motivo e idempotencia.
- La lista Staff permanece limitada a Admin y Super Admin; no se amplian
  permisos de Support.

## Problemas Que Cubre

- Cliente dice que pago, pero no recuerda a que negocio.
- Cliente cerro la app y no sabe volver a la orden, ticket o conversacion.
- Cliente reporta que la orden expiro despues de pagar.
- Negocio dice que no reconoce un pago o que el cliente nunca pago.
- Negocio entro con codigo de recomendacion y Admin necesita ver de donde salio.
- Hay varios tickets activos o archivados sobre el mismo problema.
- Soporte cerro un ticket y el usuario pregunta donde quedo.
- Hay adjuntos o comprobantes, pero Admin no sabe donde abrirlos de forma segura.
- Una alerta de chat fuera de plataforma necesita seguimiento operativo.
- El Dashboard muestra la entidad correcta, pero falta una accion clara para
  continuar la investigacion.

## Resultado Esperado

El Builder debe entregar primero:

- mapa de capacidades actuales del Dashboard;
- taxonomia de casos de soporte;
- para cada caso, evidencia minima, pantalla actual, accion esperada y brecha;
- lista de reparaciones separadas por mini-slice;
- riesgos de privacidad, costo y operacion;
- pruebas manuales y automaticas que probarian cada reparacion.

## Que No Construye Esta Autorizacion

- No crea endpoints.
- No crea migraciones.
- No crea `repair_queue`.
- No relaciona tickets entre si ni tickets con ordenes.
- No cambia estados de orden, ticket, negocio, cliente o intake.
- No valida pagos ni afirma que un pago es correcto.
- No resuelve disputas.
- No fusiona tickets.
- No descarga adjuntos automaticamente.
- No exporta expedientes.
- No crea score de fraude ni declara culpables.
- No toca pagos, creditos, USDC, Zelle, reputacion, capacidad ni bots.
- No hace deploy.
- No hace commit ni deploy.

## Relacion Con Otros Slices

- Usa 46A para ubicar pistas rapidas.
- Usa 46B como ficha principal de investigacion.
- Usa 46C para encontrar ordenes candidatas con pistas incompletas.
- Usa 44B solo cuando Admin abre evidencia de chat de orden explicitamente.
- Usa 20B para soporte activo/archivado, cierre y mensajes.
- No reemplaza disputa formal ni soporte; solo define playbooks operativos.

## Criterios De Aceptacion

- Existe una lista amplia de casos reales de cliente, negocio y soporte.
- Cada caso indica como se resuelve hoy, si se puede resolver.
- Cada caso indica que falta en Dashboard o backend si no se puede resolver.
- Las reparaciones quedan separadas en paquetes pequenos.
- No hay recomendaciones que dependan de leer cuerpos privados sin accion
  explicita y auditada.
- No hay conclusiones automaticas de culpa, fraude, pago valido o recuperacion.
- El reporte final permite decidir que mini-slice construir primero.
