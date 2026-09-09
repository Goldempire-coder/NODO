# SCREEN_LAYOUT_MASTER.md

This document defines screen distribution for Builder.

## Global mobile shell

Every user-facing Mini App screen uses:

```txt
Safe Area
Header
Main Content
Bottom Navigation
Home Indicator Space
```

Header:
- left: NODO logo + tagline
- right: user avatar + greeting/status when authenticated
- compact, never hero-sized
- logo/header entry may animate according to MOTION_AND_INTERACTION.md

Main Content:
- vertical rhythm 12-16px
- cards max radius 16px
- no nested cards except small metric tiles inside dashboard summaries
- no horizontal overflow

Bottom Navigation:
- Inicio
- Negocios
- Ordenes
- Mensajes
- Perfil

Admin screens may use a denser dashboard layout and do not need the remitter bottom nav if an admin-specific shell is documented.

## Home screen distribution

```txt
Header
Amount Search Card
Recent Orders
Marketplace Summary
Bottom Nav
```

Amount Search Card:
- amount input
- payment method segmented control
- delivery helper text
- primary CTA
- subtle entry/focus motion, no layout shift

Recent Orders:
- show only real backend data
- hide section or show empty state if no data

Marketplace Summary:
- show only real backend metrics
- never hardcode fake counts in production

## Search results distribution

```txt
Header
Context Search Bar
Filter Chips
Business Result List
Trust Disclaimer Card
Bottom Nav
```

Allowed filter chips:
- Mejor tasa

Compatibility note:
- `sort=trust` y `sort=speed` permanecen como aliases API de `sort=rate` hasta
  que exista snapshot publico durable.
- La UI no presenta confianza o velocidad como criterios de orden mientras no
  pueda respaldarlos sin metricas vivas.

Forbidden filters in MVP:
- Mas cercano
- Por ciudad
- Retiro fisico
- Efectivo

## Order flow distribution

Create Order:
- calculated Bs preview
- frozen rate preview
- MainButton

Payment Instructions:
- timer prominent
- published business data
- reveal/copy audit behavior
- marketplace disclaimer
- MainButton "Reportar evidencia"

Report Payment:
- method-specific form
- Zelle screenshot optional
- USDT TxID/hash optional in P2P negotiation
- USDT screenshot optional unless later approved

Confirm Received:
- warning copy
- confirm only if receiver sees the agreed delivery completed
- dispute alternative

## Business app distribution

Business Dashboard:
- verification/status card
- credits balance
- active orders
- active ads
- quick actions

Create Ad:
- payment method
- rate
- min/max range
- required credits preview
- risk limit notice

Order Detail:
- order status
- payment report evidence
- chat-first Pago Movil coordination
- state-specific actions
- chat entry

## Admin distribution

Admin panel must be functional, not only whitelist access.

Admin shell needs:
- operational dashboard
- pending businesses
- credit payments
- disputes
- evasion reports
- user/business risk
- audit logs
- system metrics
- manual adjustments

Every critical admin action requires:
- confirmation
- note
- audit event
- permission check
