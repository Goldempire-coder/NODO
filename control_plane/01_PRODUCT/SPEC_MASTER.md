# SPEC_MASTER.md

## AMENDMENT v0.4 - Surface separation, support and business intake

NODO opera con superficies separadas:
- Mini App Cliente para remitentes/clientes.
- Mini App Negocio para negocios aprobados con `business_access_links.status = active` asociado al usuario/Telegram validado.
- Panel Admin Web Desktop para admin/super_admin/support.
- Bot Registro Negocios para intake de negocios interesados.
- Backend unico compartido como autoridad.

La Mini App Cliente no incluye registro/verificacion de negocio, creditos de negocio, ordenes entrantes, admin, metricas ni aprobaciones.

La Mini App Negocio no permite autoaprobarse, saltarse verificacion, ver otros negocios, ver admin ni resolver disputas como admin.

El acceso a Mini App Negocio se decide por backend mediante `GET /api/v1/surface/session`; Telegram ID identifica persona, pero no autoriza por si solo.

El Bot Registro Negocios crea solicitudes pendientes para admin; no crea negocio activo, no publica anuncios, no autoriza acceso y no promete aprobacion.

Soporte general/ticket no cambia estados de orden. Chat operativo no es disputa formal. Disputa formal conserva el flujo gobernado existente.
# NODO â€” Directorio de Negocios Registrados
# Estado: DRAFT v0.1
# PropÃ³sito: Fuente de verdad funcional, tÃ©cnica y operativa para construir NODO con AFOS/Codex/Cursor.

---
## AMENDMENT v0.3 - Order timers, credits and escalation

This amendment overrides any older ambiguous order timing language in SPEC_MASTER.

### Order timers

```txt
waiting_payment
Cliente no reporta pago
30 min + 15 min extension once
Resultado: cancelled, cancel_reason = payment_not_reported_in_time, ad active, credits released

payment_reported
Cliente dice que pago, negocio no responde
2h warning / 6h dispute
Resultado: disputed, dispute_reason = business_no_payment_confirmation, ad.status = in_order, credits still blocked

payment_confirmed
Negocio recibio pago, pero no entrega pago movil
30 min warning / 2h dispute
Resultado: disputed, dispute_reason = business_confirmed_payment_but_not_delivered, credits consumed

delivered
Negocio marco pago movil enviado, cliente no confirma
24h
Resultado: completed, completion_reason = auto_completed_after_24h if no dispute
```

### Credit rule

```txt
Publicar anuncio = bloquea creditos
Cliente no paga = libera creditos
Negocio confirma pago recibido = consume creditos
```

### Required job

```txt
expire_and_escalate_orders
```

The job checks every few minutes which orders expired, which need reminders, and which must escalate to dispute.

### Final owner decisions

```txt
1. Anuncio in_order:
Un anuncio solo puede tener 1 orden activa en MVP.
Cuando una orden se crea, ad.status = in_order y sale del catalogo.

2. under_review:
No es business.verification_status.
Es business.risk_level.

3. Pausar anuncio:
Pausar no congela expires_at.
Los 7 dias siguen corriendo.

4. Roles MVP:
MVP usa remitter, business_owner, admin, support.
business_operator y support_readonly quedan post-MVP.

5. Riesgo:
trust_level = reputacion/comercial.
risk_level = control interno/riesgo.
```

---

## 0. Principio central

NODO es una Telegram Mini App tipo directorio de negocios registrados.

El sistema conecta:

- Remitentes fuera de Venezuela que quieren vender USD.
- Negocios registrados que reciben Zelle o USDT.
- Receptores en Venezuela que reciben bolÃ­vares por pago mÃ³vil.

NODO NO es banco.  
NODO NO hace escrow.  
NODO NO toca fondos de la operaciÃ³n.  
NODO NO procesa Zelle.  
NODO NO garantiza entrega.  
NODO registra Ã³rdenes, organiza perfiles y evidencia, muestra la reputaciÃ³n publicada y cobra crÃ©ditos a negocios por publicar anuncios.

Tagline:

> NODO â€” Directorio de negocios registrados.

---

## 1. Alcance MVP

### 1.1 Incluido en MVP

El MVP incluye:

- Telegram Bot como entrada y notificador.
- Telegram Mini App como interfaz principal.
- Registro ligero de remitentes usando Telegram ID.
- Registro fuerte de negocios.
- AprobaciÃ³n manual de negocios por admin.
- PublicaciÃ³n de anuncios por negocios.
- Sistema de crÃ©ditos por anuncios.
- BÃºsqueda de anuncios por monto y mÃ©todo de pago.
- MÃ©todos de pago del remitente:
  - Zelle
  - USDT
- MÃ©todo de entrega al receptor:
  - Pago mÃ³vil en Venezuela
- CÃ¡lculo automÃ¡tico de bolÃ­vares.
- Tasa congelada por orden.
- Orden persistente en base de datos.
- Estado de orden.
- Chat por orden.
- Reporte de pago enviado.
- Screenshot opcional para Zelle.
- TxID/hash no se exige para USDT en negociacion P2P; si el negocio lo necesita, lo pide por chat.
- ConfirmaciÃ³n de pago por negocio.
- ConfirmaciÃ³n de recepciÃ³n por remitente.
- Rating.
- Disputas simples.
- Reportes de evasiÃ³n.
- AuditorÃ­a.
- Notificaciones por bot.
- Jobs de expiraciÃ³n/limpieza.
- LÃ­mites progresivos por riesgo.

### 1.2 Excluido del MVP

Queda fuera del MVP:

- Efectivo Bs.
- USD efectivo.
- Entrega presencial.
- Ciudades/puntos de entrega.
- DirecciÃ³n del receptor.
- CÃ³digo de retiro presencial.
- Seriales de billetes.
- Cash App.
- Venmo.
- Wise.
- USDT BEP20 / ERC20 / Polygon.
- Transferencia bancaria internacional.
- Escrow.
- Smart contracts.
- Wallet interna para clientes.
- Procesamiento automÃ¡tico de Zelle.
- KYC automÃ¡tico.
- IA.
- App nativa iOS/Android.

---

## 2. Actores

### 2.1 Remitente

Persona fuera de Venezuela que quiere vender USD y que su familiar/receptor reciba Bs por pago mÃ³vil.

Puede:

- Entrar con Telegram.
- Buscar negocios.
- Crear Ã³rdenes.
- Ver datos oficiales de pago del negocio.
- Marcar â€œYa paguÃ©â€.
- Subir comprobante.
- Chatear dentro de una orden.
- Confirmar recibido.
- Calificar.
- Abrir disputa.
- Reportar evasiÃ³n.

No puede:

- Publicar anuncios.
- Ver Ã³rdenes de otros usuarios.
- Aprobar negocios.
- Editar tasa.
- Confirmar pago recibido en nombre del negocio.

### 2.2 Negocio

Negocio/cambista verificado que recibe Zelle o USDT y envÃ­a Bs por pago mÃ³vil al receptor.

Puede:

- Registrarse como negocio.
- Subir datos/documentos.
- Esperar aprobaciÃ³n.
- Publicar anuncios.
- Comprar crÃ©ditos.
- Usar mes fundador si aplica.
- Ver Ã³rdenes propias.
- Confirmar pago recibido.
- Marcar pago mÃ³vil enviado.
- Chatear dentro de Ã³rdenes.
- Ver ratings.
- Referir negocios.

No puede:

- Ver Ã³rdenes de otros negocios.
- Crear anuncios sin aprobaciÃ³n.
- Crear anuncios sin crÃ©ditos, salvo fundador activo.
- Publicar Zelle/USDT no registrado.
- Mezclar Zelle y USDT en un mismo anuncio.
- Crear duplicados del mismo anuncio.
- Saltar lÃ­mites de riesgo.

### 2.3 Admin

DueÃ±o/equipo NODO.

Puede:

- Aprobar/rechazar negocios.
- Aprobar compras de crÃ©ditos.
- Ajustar lÃ­mites.
- Suspender negocios.
- Revisar disputas.
- Revisar reportes.
- Ver audit logs.
- Ver mÃ©tricas.
- Hacer ajustes manuales auditados.

### 2.4 Soporte

Rol futuro limitado.

Puede:

- Ver casos.
- Ver disputas.
- AÃ±adir notas.
- Escalar a admin.

No puede:

- Aprobar negocios.
- Dar crÃ©ditos.
- Suspender permanentemente.
- Cambiar lÃ­mites.
- Resolver disputas crÃ­ticas sin admin.

---

## 3. Modelo de negocio

### 3.1 Fuente de ingresos

NODO cobra a negocios por crÃ©ditos.

No cobra spread.  
No cobra comisiÃ³n por transacciÃ³n en MVP.  
No toca fondos de la transacciÃ³n.

### 3.2 Paquetes de crÃ©ditos

| Paquete | CrÃ©ditos | Precio | Precio aproximado por crÃ©dito |
|---|---:|---:|---:|
| Starter | 5 | $10 | $2.00 |
| Pro | 15 | $25 | $1.67 |
| Business | 50 | $75 | $1.50 |
| Enterprise | 200 | $250 | $1.25 |

### 3.3 Costo por anuncio

El costo del anuncio depende del rango mÃ¡ximo del anuncio:

| Rango del anuncio | CrÃ©ditos requeridos |
|---|---:|
| $20 - $100 | 1 crÃ©dito |
| $100 - $500 | 2 crÃ©ditos |
| $500 - $2,000 | 3 crÃ©ditos |
| MÃ¡s de $2,000 | No disponible en MVP / revisiÃ³n manual |

### 3.4 Monto mÃ­nimo

Monto mÃ­nimo del MVP:

```txt
$20 USD
````

No se permiten anuncios ni Ã³rdenes menores a $20.

### 3.5 Fundadores

Programa inicial:

* 5 a 10 negocios fundadores.
* 1 mes gratis.
* Sin cobrar crÃ©ditos durante el mes fundador.
* Uso ilimitado dentro de sus lÃ­mites de monto/riesgo.
* Mantienen lÃ­mites progresivos.
* Pueden referir negocios.
* El mes fundador no elimina verificaciÃ³n ni controles.

### 3.6 Referidos

Regla:

```txt
5 crÃ©ditos por negocio referido aprobado.
MÃ¡ximo 20 crÃ©ditos por negocio referente.
```

Tabla:

| Referidos aprobados | CrÃ©ditos ganados |
| ------------------: | ---------------: |
|                   1 |                5 |
|                   2 |               10 |
|                   3 |               15 |
|                   4 |               20 |
|                  5+ |        20 mÃ¡ximo |

CrÃ©ditos se otorgan solo cuando el negocio referido es aprobado por admin.

---

## 4. MÃ©todos del MVP

### 4.1 Pago del remitente al negocio

Permitidos:

```txt
zelle
usdt_trc20
```

No permitidos en MVP:

```txt
cash_app
venmo
wise
usdt_bep20
usdt_erc20
usdt_polygon
bank_transfer_international
cash
```

### 4.2 Entrega del negocio al receptor

Permitido:

```txt
pago_movil_ve
```

No permitidos en MVP:

```txt
bs_cash
usd_cash
bank_transfer_bs
pickup_point
delivery_cash
```

### 4.3 Cobertura

Cobertura del MVP:

```txt
Venezuela por pago mÃ³vil
```

No se usa ciudad en MVP.
No se filtra por ciudad.
Pago mÃ³vil se considera cobertura nacional.

---

## 5. Reglas de anuncios

### 5.1 Un anuncio = un mÃ©todo

Un anuncio solo puede tener un mÃ©todo de pago.

Correcto:

```txt
Anuncio A: Recibo Zelle -> envÃ­o pago mÃ³vil Bs
Anuncio B: Recibo USDT -> envÃ­o pago mÃ³vil Bs
```

Incorrecto:

```txt
Recibo Zelle y USDT en el mismo anuncio
```

### 5.2 Datos del anuncio

Cada anuncio debe tener:

* Negocio.
* MÃ©todo de pago:

  * Zelle
  * USDT
* MÃ©todo de entrega:

  * Pago mÃ³vil
* Tasa Bs/USD.
* Monto mÃ­nimo.
* Monto mÃ¡ximo.
* Estado.
* CrÃ©ditos requeridos.
* CrÃ©ditos en hold.
* Fecha de creaciÃ³n.
* Fecha de expiraciÃ³n.
* Ãšltima actualizaciÃ³n de tasa.

### 5.3 Estados de anuncio

Estados vÃ¡lidos:

```txt
draft
active
in_order
archived
expired
paused
suspended
```

### 5.4 Hold de anuncio

Cuando un remitente crea una orden sobre un anuncio:

```txt
ad.status = in_order
```

Mientras estÃ¡ en `in_order`:

* No aparece en resultados.
* No puede duplicarse.
* No puede reactivarse.
* No puede editar mÃ©todo.
* No puede editar monto.
* No puede editar tasa para esa orden.
* El crÃ©dito queda en hold.

### 5.5 LiberaciÃ³n del anuncio

Si la orden expira o se cancela antes de pago confirmado:

```txt
order.status = cancelled
ad.status = active
credits = released
```

### 5.6 Archivado del anuncio

Si el negocio confirma pago recibido:

```txt
order.status = payment_confirmed
ad.status = archived
credits = consumed
```

El anuncio cumpliÃ³ su funciÃ³n y muere.

### 5.7 Duplicados

Un negocio no puede tener dos anuncios activos o en hold con la misma combinaciÃ³n:

* business_id
* payment_method
* delivery_method
* amount_min_usd
* amount_max_usd

---

## 6. Reglas de Ã³rdenes

### 6.1 CreaciÃ³n de orden

Para crear una orden, el remitente debe:

* Estar autenticado por Telegram.
* Tener perfil activo/no bloqueado.
* Elegir anuncio activo.
* Ingresar monto USD.
* Ingresar datos de pago mÃ³vil del receptor.
* Confirmar resumen.

El backend debe validar:

* Anuncio activo.
* Negocio aprobado.
* MÃ©todo permitido.
* Monto >= $20.
* Monto dentro del rango del anuncio.
* Monto dentro del lÃ­mite del negocio.
* Monto dentro del lÃ­mite del usuario.
* Negocio no suspendido.
* Anuncio no duplicado/in hold.
* CrÃ©ditos o perÃ­odo fundador vÃ¡lido.

### 6.2 Datos del receptor

Para pago mÃ³vil:

* Nombre del titular.
* CÃ©dula/RIF.
* Banco.
* TelÃ©fono pago mÃ³vil.

El remitente NO escribe monto Bs a recibir.

### 6.3 CÃ¡lculo automÃ¡tico

FÃ³rmula:

```txt
amount_bs_calculated = amount_usd * rate_snapshot
```

Ejemplo:

```txt
$100 * 35.50 = 3,550 Bs
```

La tasa queda congelada al crear la orden.

### 6.4 Snapshot de orden

La orden debe guardar:

* amount_usd
* rate_snapshot
* amount_bs_calculated
* payment_method_snapshot
* delivery_method_snapshot
* receiver_data_snapshot
* business_id
* ad_id
* remitter_user_id
* timestamps

### 6.5 Tiempo para pagar

Regla:

```txt
Tiempo inicial: 30 minutos
ExtensiÃ³n: 15 minutos
MÃ¡ximo total: 45 minutos
```

Si no marca â€œYa paguÃ©â€:

* Orden se cancela.
* Anuncio vuelve activo.
* CrÃ©ditos se liberan.

### 6.6 Reporte de pago enviado

El remitente marca â€œYa paguÃ©â€.

Para Zelle debe enviar:

* Titular de la cuenta Zelle.
* Email/telÃ©fono origen.
* NÃºmero de confirmaciÃ³n.
* Screenshot obligatorio.

Para USDT debe enviar:

* Debe confirmar por chat la red exacta con el negocio antes de enviar.
* TxID/hash no requerido por NODO; el negocio puede pedirlo por chat si lo necesita.
* Wallet origen opcional.
* Screenshot opcional/recomendado.

### 6.7 ConfirmaciÃ³n de pago por negocio

El negocio puede:

```txt
RecibÃ­ el pago
No recibÃ­ el pago
```

Si confirma:

* Orden pasa a `payment_confirmed`.
* Anuncio pasa a `archived`.
* CrÃ©ditos se consumen.

Si rechaza:

* Orden pasa a `payment_rejected`.
* Remitente puede corregir datos, subir otro comprobante o abrir disputa.

### 6.8 Pago mÃ³vil enviado

DespuÃ©s de confirmar pago recibido, el negocio debe enviar pago mÃ³vil al receptor y marcar:

```txt
Pago mÃ³vil enviado
```

La orden pasa a:

```txt
delivered
```

### 6.9 ConfirmaciÃ³n del remitente

El remitente confirma que el receptor recibiÃ³.

Si confirma:

```txt
order.status = completed
```

Luego se solicita rating.

### 6.10 Auto-cierre

DespuÃ©s de que el negocio marca pago mÃ³vil enviado:

```txt
El remitente tiene 24 horas para confirmar o abrir disputa.
```

Si no hace nada:

```txt
order.status = completed
completion_reason = auto_completed_after_24h
```

El bot debe enviar recordatorios antes del auto-cierre.

---

## 7. Estados de orden

Estados vÃ¡lidos:

```txt
created
waiting_payment
payment_reported
payment_rejected
payment_confirmed
delivered
completed
cancelled
disputed
```

### 7.1 Transiciones permitidas

```txt
created -> waiting_payment
waiting_payment -> payment_reported
waiting_payment -> cancelled
payment_reported -> payment_confirmed
payment_reported -> payment_rejected
payment_reported -> disputed
payment_rejected -> payment_reported
payment_rejected -> cancelled
payment_confirmed -> delivered
payment_confirmed -> disputed
delivered -> completed
delivered -> disputed
delivered -> completed
disputed -> completed
disputed -> cancelled
```

### 7.2 Transiciones prohibidas

Prohibido:

```txt
created -> completed
waiting_payment -> delivered
payment_reported -> delivered
completed -> edit_receiver_data
completed -> payment_reported
cancelled -> payment_confirmed
```

Toda transiciÃ³n debe pasar por state machine.

---

## 8. LÃ­mites de riesgo

### 8.1 Negocio nuevo

Default:

```txt
max_order_amount_usd = 100
daily_limit_usd = 1000
active_order_limit = 1
trust_level = new
```

### 8.2 Niveles de negocio

| Nivel   | Requisitos sugeridos           | MÃ¡ximo por orden | LÃ­mite diario |
| ------- | ------------------------------ | ---------------: | ------------: |
| New     | Aprobado, sin historial        |             $100 |          $300 |
| Basic   | 10 completadas, rating >= 4.7  |             $250 |        $1,000 |
| Plus    | 25 completadas, rating >= 4.8  |             $500 |        $2,500 |
| Pro     | 50 completadas, rating >= 4.85 |           $1,000 |        $5,000 |
| Premium | RevisiÃ³n manual                |          $2,000+ |        Manual |

MVP permite hasta $2,000 por anuncio, pero negocios nuevos no pueden usar ese rango hasta subir de nivel.

### 8.3 Cliente nuevo

Default:

```txt
max_order_amount_usd = 100
active_order_limit = 1
expired_orders_daily_limit = 3
trust_level = new
```

Si un cliente crea muchas Ã³rdenes y no paga, pasa a restricted.

### 8.4 Pausa automÃ¡tica

Si un negocio acumula:

```txt
3 reportes abiertos en 24h
```

Entonces:

* Anuncios pausados.
* Admin recibe alerta.
* Negocio entra en revisiÃ³n.

---

## 9. Chat

### 9.1 Chat por orden

No existe chat global en MVP.

Cada chat pertenece a una orden.

Campos mÃ­nimos:

* order_id
* sender_user_id
* sender_role
* message_type
* message_body
* file_id
* created_at
* blocked_reason

### 9.2 PaginaciÃ³n

Al abrir chat:

```txt
Cargar Ãºltimos 30 mensajes.
```

Scroll hacia arriba:

```txt
Cargar 30 mensajes anteriores.
```

### 9.3 Mensajes del sistema

El sistema debe insertar mensajes automÃ¡ticos:

* Orden creada.
* Pago reportado.
* Pago rechazado.
* Pago confirmado.
* Pago mÃ³vil enviado.
* Orden completada.
* Disputa abierta.
* Admin resolviÃ³ disputa.

### 9.4 Anti-evasiÃ³n

Datos oficiales de pago se muestran solo en mÃ³dulo oficial de la orden.

En chat:

* Si email/telÃ©fono/wallet coincide con dato oficial registrado, se permite o se reemplaza por tarjeta oficial.
* Si no coincide, se bloquea.
* Se guarda audit log.

Frases bloqueables:

```txt
escrÃ­beme por WhatsApp
hazlo directo
guarda mi nÃºmero
la prÃ³xima vez por fuera
te doy mejor tasa fuera de la app
no uses la app
```

---

## 10. Datos de pago oficiales

### 10.1 Zelle del negocio

El negocio registra:

* Email/telÃ©fono Zelle.
* Nombre del titular.
* Estado verificado.
* Activo/inactivo.

En anuncio pÃºblico:

```txt
MÃ©todo: Zelle
Cuenta: verificada
```

No se muestra dato completo antes de iniciar orden.

En orden:

```txt
Zelle enmascarado
[Mostrar completo]
```

Al revelar:

* payment_data_revealed_at
* payment_data_revealed_by
* audit_log

### 10.2 USDT del negocio

El negocio registra:

* Wallet USDT.
* Red exacta a confirmar por chat entre cliente y negocio.
* Estado verificado.
* Activo/inactivo.

En orden:

* Wallet enmascarada.
* Advertencia de red.
* ConfirmaciÃ³n de que el usuario entiende que debe confirmar la red exacta antes de enviar.

Mensaje obligatorio:

```txt
Antes de enviar USDT, confirma por chat la red exacta con el negocio. Si envÃ­as por una red distinta, el negocio podrÃ­a no recibir el pago.
```

---

## 11. Telegram Bot

### 11.1 PropÃ³sito

El bot es:

```txt
portero + mensajero
```

No reemplaza la Mini App.

### 11.2 Funciones

El bot debe:

* Responder `/start`.
* Mostrar botÃ³n â€œAbrir NODOâ€.
* Enviar notificaciones.
* Enviar recordatorios.
* Alertar admin.
* Avisar crÃ©ditos bajos.
* Avisar Ã³rdenes nuevas.
* Avisar pagos reportados.
* Avisar pagos confirmados.
* Avisar auto-cierre cercano.

### 11.3 Notificaciones principales

| Evento            | Destino   |
| ----------------- | --------- |
| order_created     | negocio   |
| payment_reported  | negocio   |
| payment_confirmed | remitente |
| payment_rejected  | remitente |
| delivered         | remitente |
| order_completed   | ambos     |
| order_expiring    | remitente |
| credits_low       | negocio   |
| business_pending  | admin     |
| dispute_opened    | admin     |
| evasion_reported  | admin     |

---

## 12. Pantallas MVP

### 12.1 Remitente

```txt
R-01 WELCOME_ENTRY
R-02 HOME_SEARCH
R-03 SEARCH_RESULTS
R-04 BUSINESS_DETAIL
R-05 CREATE_ORDER
R-06 ORDER_SUMMARY
R-07 PAYMENT_INSTRUCTIONS
R-08 REPORT_PAYMENT
R-09 ORDER_TRACKING_CHAT
R-10 CONFIRM_RECEIVED
R-11 RATING
R-12 MY_ORDERS
R-13 PROFILE
```

### 12.2 Negocio

```txt
B-01 BUSINESS_ONBOARDING
B-02 BUSINESS_VERIFICATION_FORM
B-03 VERIFICATION_PENDING
B-04 BUSINESS_DASHBOARD
B-05 BUY_CREDITS
B-06 CREDIT_PAYMENT_PENDING
B-07 MY_CREDITS_LEDGER
B-08 CREATE_AD
B-09 MY_ADS
B-10 ARCHIVED_ADS
B-11 INCOMING_ORDERS
B-12 BUSINESS_ORDER_DETAIL
B-13 BUSINESS_CHAT
B-14 BUSINESS_RATINGS
B-15 REFERRAL_PROGRAM
B-16 PAYMENT_METHODS
B-17 BUSINESS_SETTINGS
```

### 12.3 Admin

```txt
A-01 ADMIN_DASHBOARD
A-02 PENDING_BUSINESSES
A-03 BUSINESS_VERIFICATION_DETAIL
A-04 PENDING_CREDIT_PAYMENTS
A-05 CREDIT_PAYMENT_DETAIL
A-06 DISPUTES_LIST
A-07 DISPUTE_DETAIL
A-08 EVASION_REPORTS
A-09 BUSINESS_RISK_DETAIL
A-10 USERS_REMITTERS
A-11 AUDIT_LOGS
A-12 SYSTEM_METRICS
A-13 MANUAL_ADJUSTMENTS
```

---

## 13. Data model

### 13.1 users

```txt
id
telegram_id
username
first_name
last_name
role
status
trust_level
orders_created_count
orders_completed_count
orders_expired_count
created_at
last_seen_at
```

### 13.2 businesses

```txt
id
owner_user_id
business_name
rif
address
phone
verification_status
trust_level
max_order_amount_usd
daily_limit_usd
active_order_limit
rating_avg
completed_orders_count
disputes_count
evasion_reports_count
referral_code
referral_credits_earned
founder_status
founder_started_at
founder_expires_at
created_at
approved_at
```

### 13.3 business_payment_methods

```txt
id
business_id
method_type
network
account_value
account_masked
holder_name
verified_status
active
created_at
updated_at
```

### 13.4 ads

```txt
id
business_id
payment_method_id
payment_method
delivery_method
rate_bs_per_usd
amount_min_usd
amount_max_usd
required_credits
status
credit_hold_id
created_at
expires_at
rate_updated_at
```

### 13.5 orders

```txt
id
ad_id
business_id
remitter_user_id
status
amount_usd
rate_snapshot
amount_bs_calculated
receiver_data_json
payment_method_snapshot
delivery_method_snapshot
payment_data_revealed_at
payment_data_revealed_by
expires_at
extension_used
paid_reported_at
payment_confirmed_at
delivered_at
completed_at
created_at
updated_at
```

### 13.6 payment_reports

```txt
id
order_id
reported_by_user_id
payment_type
payment_sender_name
payment_sender_account_masked
payment_reference
tx_hash
network
payment_amount
proof_file_id
status
created_at
updated_at
```

### 13.7 messages

```txt
id
order_id
sender_user_id
sender_role
body
visibility
status
idempotency_key
created_at
updated_at
deleted_at
```

`chat_messages` is legacy/non-valid naming. Use `messages`.

### 13.7.1 message_attachments

```txt
id
message_id
order_id
file_asset_id
uploaded_by_user_id
file_type
mime_type
size_bytes
status
created_at
updated_at
deleted_at
```

### 13.8 credits_ledger

```txt
id
business_id
type
amount
related_ad_id
related_order_id
related_referral_id
notes
created_by
created_at
```

Types:

```txt
purchase
founder_free_use
referral_bonus
hold
release
consume
expire
admin_adjustment
```

### 13.9 referrals

```txt
id
referrer_business_id
referred_business_id
referral_code
status
credits_awarded
created_at
approved_at
rewarded_at
```

### 13.10 ratings

```txt
id
order_id
business_id
rater_user_id
stars
created_at
```

Contrato runtime vigente: una calificacion por orden, solo estrellas 1..5. Los
campos legacy `comment` y `rating_type` no forman parte del slice 42B ni de su
API publica.

Privacidad runtime: el cliente propietario puede volver a ver sus estrellas en
su orden. Negocio, marketplace, chat, Telegram, attention, Admin y Support no
reciben ratings individuales. `rating_avg` y `ratings_count` exactos se
conservan como read-models internos. `reputation_tier` tambien permanece
interno hasta que exista un snapshot durable; publico y negocio reciben la
proyeccion estable `Reputación no publicada`.

### 13.11 disputes

```txt
id
order_id
opened_by_user_id
reason
description
evidence_file_id
status
resolution
resolved_by_admin_id
created_at
resolved_at
```

### 13.12 audit_logs

```txt
id
actor_user_id
actor_role
event_type
entity_type
entity_id
old_value_json
new_value_json
ip_address
user_agent
created_at
```

### 13.13 notification_jobs

```txt
id
notification_type
recipient_user_id
recipient_role
order_id
business_id
dispute_id
status
scheduled_for
sent_at
failed_at
attempts
max_attempts
last_error_code
dedupe_key
metadata_json
created_at
updated_at
```

Regla slice 10:

- `notification_type` es canonico; `event_type`/`telegram_chat_id` son legacy
  y no son validos para nuevas migraciones de notification jobs.
- `dedupe_key` evita notificaciones duplicadas por recurso, tipo y ventana.
- `metadata_json` no guarda `storage_path`, `account_value`, instrucciones
  completas, signed URLs, tokens, secretos ni evidencia privada.

### 13.14 files

```txt
id
owner_user_id
entity_type
entity_id
file_type
storage_path
mime_type
size_bytes
created_at
deleted_at
```

---

## 14. Ãndices obligatorios

```sql
CREATE INDEX idx_ads_search
ON ads (status, payment_method, delivery_method, amount_min_usd, amount_max_usd);

CREATE INDEX idx_ads_business_status
ON ads (business_id, status, created_at DESC);

CREATE INDEX idx_orders_business_status
ON orders (business_id, status, created_at DESC);

CREATE INDEX idx_orders_remitter_status
ON orders (remitter_user_id, status, created_at DESC);

CREATE INDEX idx_chat_order_created
ON messages (order_id, created_at DESC);

CREATE INDEX idx_businesses_status_rating
ON businesses (verification_status, trust_level, rating_avg DESC);

CREATE INDEX idx_audit_entity
ON audit_logs (entity_type, entity_id, created_at DESC);

CREATE INDEX idx_notification_jobs_status
ON notification_jobs (status, scheduled_for ASC);
```

---

## 15. Seguridad

### 15.1 AutenticaciÃ³n

* Validar Telegram initData en backend.
* No confiar en Telegram ID enviado por frontend sin validaciÃ³n.
* Crear sesiÃ³n/JWT corto.
* Revisar status del usuario en cada acciÃ³n sensible.

### 15.2 Roles

RBAC obligatorio:

```txt
remitter
business
admin
support
```

### 15.3 Storage

* Buckets privados.
* URLs firmadas temporales.
* No guardar imÃ¡genes en DB.
* Screenshot mÃ¡ximo 3MB.
* Formatos permitidos: jpg, png, webp.
* Borrar uploads huÃ©rfanos.

### 15.4 Rate limits

Aplicar lÃ­mites por usuario/IP/acciÃ³n:

* Crear orden.
* Subir comprobantes.
* Enviar chat.
* Revelar datos de pago.
* Crear anuncios.
* Intentos fallidos.
* Reportes.

### 15.5 Audit logs

Eventos obligatorios:

```txt
user_created
business_registered
business_approved
business_rejected
payment_method_added
payment_data_revealed
ad_created
ad_updated
ad_paused
ad_archived
order_created
payment_reported
payment_confirmed
payment_rejected
order_delivered
order_completed
credit_held
credit_released
credit_consumed
referral_rewarded
dispute_opened
message_created
message_attachment_uploaded
dispute_message_created
admin_action
evasion_reported
user_blocked
business_suspended
```

---

## 16. Arquitectura tÃ©cnica

### 16.1 Stack aprobado

Frontend:

```txt
Next.js + Tailwind
```

Backend:

```txt
FastAPI
```

Base de datos:

```txt
Supabase PostgreSQL
```

Storage:

```txt
Supabase Storage
```

Bot:

```txt
Python Telegram Bot
```

Deploy:

```txt
Cloudflare Pages para frontend
Railway para backend/bot/jobs
Supabase Pro para DB
Upstash Redis para locks/rate limits/jobs
Cloudflare R2 o Supabase Storage para storage privado
```

### 16.2 Motivo del stack

Next.js + Tailwind:

* Buen soporte para Mini App web.
* UI rÃ¡pida.
* Deploy simple.
* Compatible con AFOS/Cursor/Codex.

FastAPI:

* Backend claro.
* ValidaciÃ³n con Pydantic.
* Buen orden para services/repositories.
* Ideal para state machines y lÃ³gica modular.

Supabase PostgreSQL:

* Relacional.
* Ideal para marketplace.
* Ãndices.
* AuditorÃ­a.
* Storage integrado.

Python Telegram Bot:

* Simple.
* Confiable como ecosistema tecnico.
* Buen ecosistema.

### 16.3 Arquitectura modular

Backend:

```txt
routes -> services -> repositories -> database
           |
           -> validators
           -> helpers
           -> state_machines
           -> audit
           -> notifications
```

Regla:

```txt
Pantallas no contienen lÃ³gica de negocio crÃ­tica.
Backend valida todo.
```

---

## 17. Guardrails de ingenierÃ­a

### 17.1 No funciones Frankenstein

Prohibido crear funciones que hagan todo.

Cada funciÃ³n debe tener responsabilidad clara.

Mal:

```txt
createOrder hace validaciÃ³n, DB, notificaciÃ³n, auditorÃ­a, cÃ¡lculo, chat, crÃ©ditos y storage todo junto.
```

Bien:

```txt
createOrder orquesta.
validateOrderInput valida.
calculateQuote calcula.
lockAdForOrder bloquea.
createOrderRecord escribe.
writeAuditLog audita.
enqueueNotification notifica.
```

### 17.2 MÃ³dulos

Backend debe organizarse por mÃ³dulos:

```txt
auth
users
businesses
payment_methods
ads
orders
payment_reports
chat
credits
referrals
ratings
disputes
notifications
admin
audit
jobs
```

Cada mÃ³dulo:

```txt
routes.py
service.py
repository.py
schemas.py
helpers.py
tests.py
```

### 17.3 State machines

Toda transiciÃ³n de orden/anuncio/crÃ©dito debe pasar por state machine.

No se permite actualizar estados directamente desde cualquier endpoint.

### 17.4 Repositories

Queries deben vivir en repositories.

No queries regadas en rutas o pantallas.

### 17.5 Validators

Todo input debe validarse con schemas.

### 17.6 Errores humanos

No mostrar errores tÃ©cnicos al usuario.

Ejemplo:

```txt
Este anuncio ya no estÃ¡ disponible. Elige otro negocio.
```

No:

```txt
unique constraint violation
```

---

## 18. Jobs

### 18.1 Worker frecuente

Corre cada 1-5 minutos:

* Cancelar Ã³rdenes vencidas.
* Reactivar anuncios liberados.
* Enviar recordatorios.
* Procesar notificaciones.
* Detectar reportes acumulados.

### 18.2 Worker diario

Corre una vez al dÃ­a:

* Expirar anuncios.
* Limpiar uploads huÃ©rfanos.
* Marcar usuarios dormant.
* Recalcular mÃ©tricas.
* Limpiar sesiones viejas.

---

## 19. MÃ©tricas

### 19.1 Negocio

Guardar mÃ©tricas resumidas:

```txt
completed_orders_count
cancelled_orders_count
disputes_count
lost_disputes_count
avg_response_time
rating_avg
monthly_volume_reported
evasion_reports_count
```

### 19.2 Admin

Mostrar:

* Negocios pendientes.
* Pagos de crÃ©ditos pendientes.
* Ã“rdenes activas.
* Disputas abiertas.
* Reportes de evasiÃ³n.
* CrÃ©ditos vendidos.
* Anuncios activos.
* Usuarios registrados.
* Usuarios activos.

---

## 20. Ranking de anuncios

Orden de resultados:

1. Compatible con monto.
2. Compatible con mÃ©todo.
3. Negocio aprobado.
4. Negocio no suspendido.
5. Mejor trust level.
6. Mejor rating.
7. Mayor tasa de completaciÃ³n.
8. Menor tiempo promedio.
9. Mejor tasa.
10. Menos reportes.

La mejor tasa no debe superar seÃ±ales de riesgo.

---

## 21. Legal / disclaimers

### 21.1 Lenguaje permitido

Usar:

```txt
negocio registrado
orden registrada
pago reportado
pago confirmado por negocio
entrega reportada
historial pÃºblico
perfil registrado
```

### 21.2 Lenguaje prohibido

No usar:

```txt
fondos garantizados
escrow
liberamos fondos
dinero protegido
somos banco
transacciÃ³n garantizada
entrega garantizada
```

### 21.3 PosiciÃ³n legal de producto

NODO es un marketplace tecnolÃ³gico de anuncios verificados.

NODO no:

* Recibe fondos de la operaciÃ³n.
* Custodia dinero.
* Procesa pagos.
* Ejecuta cambio.
* Garantiza entrega.
* Sustituye responsabilidad del negocio.
* Sustituye responsabilidad del remitente.

---

## 22. Criterios MVP listo

El MVP se considera listo cuando:

* Remitente puede entrar con Telegram y crear orden.
* Negocio puede registrarse y ser aprobado.
* Negocio puede publicar anuncio Zelle.
* Negocio puede publicar anuncio USDT.
* Remitente puede buscar por monto/mÃ©todo.
* Remitente puede crear orden con pago mÃ³vil.
* Sistema calcula Bs automÃ¡ticamente.
* Orden persiste si usuario cierra app.
* Bot notifica eventos principales.
* Remitente puede reportar pago.
* Negocio puede confirmar pago.
* Negocio puede marcar pago mÃ³vil enviado.
* Remitente puede confirmar recibido.
* Rating funciona.
* CrÃ©ditos funcionan.
* Referidos funcionan.
* Admin puede aprobar negocios y crÃ©ditos.
* Audit logs registran eventos crÃ­ticos.
* Jobs cancelan Ã³rdenes vencidas.
* No hay funciones Frankenstein.
* Permisos por rol funcionan.
* Screenshots se guardan en storage privado.

---

## 23. Prioridad de construcciÃ³n

### Fase 0 â€” FundaciÃ³n

* Repo.
* Estructura modular.
* ConfiguraciÃ³n.
* Auth Telegram.
* DB schema.
* Audit base.
* State machines base.

### Fase 1 â€” Remitente

* Home search.
* Results.
* Business detail.
* Create order.
* Payment instructions.
* Report payment.
* My orders.
* Order tracking/chat.

### Fase 2 â€” Negocio

* Business onboarding.
* Admin approval.
* Payment methods.
* Create ad.
* My ads.
* Incoming orders.
* Order detail.
* Confirm payment.
* Mark delivered.

### Fase 3 â€” CrÃ©ditos

* Packages.
* Manual credit purchase.
* Credits ledger.
* Required credits per ad.
* Founder mode.
* Referral rewards.

### Fase 4 â€” Admin

* Dashboard.
* Pending businesses.
* Credit payments.
* Disputes.
* Reports.
* Audit logs.

### Fase 5 â€” Bot/Jobs

* Bot start.
* Open Mini App.
* Notifications.
* Expire orders.
* Reactivate ads.
* Cleanup.

### Fase 6 â€” QA

* Security tests.
* State machine tests.
* Concurrent order tests.
* Credit hold/release/consume tests.
* Role permission tests.
* Upload tests.
* Notification retry tests.

---

## 24. Pruebas obligatorias

### 24.1 Orden

* Crear orden congela tasa.
* Usuario no puede crear orden menor a $20.
* Usuario no puede crear orden mayor que lÃ­mite.
* Dos usuarios no pueden tomar el mismo anuncio.
* Orden expirada reactiva anuncio.
* Orden expirada libera crÃ©ditos.
* Pago confirmado archiva anuncio.
* Pago confirmado consume crÃ©ditos.

### 24.2 Negocio

* Negocio no aprobado no puede publicar.
* Negocio nuevo no puede publicar > $100.
* Negocio no puede duplicar anuncio.
* Negocio no puede ver Ã³rdenes de otro negocio.
* Negocio puede confirmar solo sus Ã³rdenes.

### 24.3 Cliente

* Cliente no puede ver Ã³rdenes de otro cliente.
* Cliente nuevo solo puede tener orden activa limitada.
* Cliente con muchas expiradas pasa a restricted.

### 24.4 Seguridad

* Telegram initData invÃ¡lido se rechaza.
* Datos de pago solo se revelan dentro de orden.
* Revelado genera audit log.
* Mensaje con dato no oficial se bloquea.
* Admin action genera audit log.

### 24.5 CrÃ©ditos

* Publicar anuncio bloquea crÃ©ditos.
* CancelaciÃ³n antes de pago libera crÃ©ditos.
* Confirmar pago consume crÃ©ditos.
* Referido aprobado otorga 5 crÃ©ditos.
* Referente no pasa de 20 crÃ©ditos.

---

## 25. Decisiones finales actuales

```txt
Nombre: NODO
Tagline: Directorio de negocios registrados.
MVP: Telegram Mini App
MÃ©todos: Zelle + USDT
Entrega: pago mÃ³vil Venezuela
Sin efectivo
Sin ciudades
Monto mÃ­nimo: $20
CrÃ©ditos:
  $20-$100 = 1
  $100-$500 = 2
  $500-$2,000 = 3
Paquetes:
  5 = $10
  15 = $25
  50 = $75
  200 = $250
Fundadores:
  5-10 negocios
  1 mes gratis
  uso ilimitado con lÃ­mite de monto
Referidos:
  5 crÃ©ditos por negocio aprobado
  mÃ¡ximo 20 crÃ©ditos por referente
Stack:
  Next.js + Tailwind
  FastAPI
  Supabase PostgreSQL
  Supabase Storage
  Python Telegram Bot
  Cloudflare Pages + Railway
```

---

## 26. Pendientes

Pendientes fuera de este SPEC:

* Logo final exacto.
* Dominio.
* Usuario Telegram bot.
* RevisiÃ³n legal real.
* Contratos con negocios.
* Manual de verificaciÃ³n.
* DiseÃ±o visual final de pantallas.
* ImplementaciÃ³n.
* QA real.
* Piloto con negocios fundadores.

---


---

## 27. UI/UX Profesional para Telegram Mini App

NODO debe sentirse como una fintech dentro de Telegram, no como una web externa.

Reglas obligatorias:

- Usar experiencia visual nativa de Telegram Mini App.
- Usar @telegram-apps/telegram-ui como UI kit recomendado.
- Usar MainButton nativo para CTAs principales.
- Usar haptic feedback solo en acciones crÃ­ticas.
- Usar ClosingConfirmation en flujos sensibles de pago.
- Usar skeleton screens en toda pantalla con carga remota.
- Usar empty states, error states y offline states.
- Respetar themeParams, dark mode y light mode.
- Enmascarar datos sensibles.
- Mostrar badges de verificaciÃ³n.
- Mostrar timer prominente en Ã³rdenes activas.
- Mostrar stepper de progreso en Ã³rdenes.
- No mostrar lenguaje de garantÃ­a, escrow o fondos protegidos.
- No mostrar ciudad, efectivo ni â€œmÃ¡s cercanoâ€ en MVP.

Paleta oficial NODO:

- Primary: #0A2540
- Secondary: #00C853
- Accent: #1C9CEB
- Success: #00C853
- Warning: #FF9800
- Danger: #F44336
- Light Background: #F8F9FA
- Dark Background: #1A1A2E
- Light Surface: #FFFFFF
- Dark Surface: #16213E
- Light Text: #1A1A2E
- Dark Text: #EAEAEA

Logo oficial MVP:

- N fuerte.
- Flecha sutil.
- Check de verificaciÃ³n.
- Nada de hexÃ¡gonos.
- Nada de blockchain/web3.
- Nada de logos cambiantes por pantalla.

## 28. Frontend Implementation Guardrails

Valores oficiales de mÃ©todo:

- zelle
- usdt_trc20

Prohibido usar:

- usdt
- trc20
- tether
- crypto

Home debe validar:

- Monto requerido.
- Monto numÃ©rico.
- Monto mÃ­nimo: $20.
- Monto mÃ¡ximo MVP: $2,000.
- No negativos.
- No cero.
- No texto.

MainButton:

- Separar setParams de onClick.
- Limpiar handler al desmontar pantalla.
- No registrar mÃºltiples onClick por cambios de estado.
- Mostrar loading state.
- Deshabilitar si formulario es invÃ¡lido.

Home debe mostrar siempre:

â€œTu familiar recibe por pago mÃ³vil en Venezuela.â€

ProducciÃ³n no puede mostrar datos falsos hardcoded:

- Negocios activos inventados.
- Ã“rdenes hoy inventadas.
- Mejor tasa inventada.
- Ã“rdenes recientes inventadas.

Toda mÃ©trica visible debe venir del backend o esconderse.

