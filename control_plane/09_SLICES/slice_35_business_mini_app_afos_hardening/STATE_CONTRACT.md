# STATE_CONTRACT.md

## Estados relevantes

Negocio:

- aprobado;
- suspendido/restringido;
- online;
- offline.

PIN:

- no configurado;
- configurado bloqueado;
- configurado bloqueado por intentos;
- configurado desbloqueado temporalmente.

Metodos de cobro:

- Zelle activo aprobado;
- USDT TRC20 activo aprobado;
- inactivo/borrado;
- no propio;
- duplicado.

Anuncio:

- active;
- paused;
- in_order;
- archived;
- expired;
- suspended.

Orden:

- waiting_payment;
- payment_reported;
- payment_confirmed;
- delivered;
- completed;
- cancelled;
- disputed.

Compra Base USDC:

- pending_payment;
- pending_onchain_confirmation;
- under_review;
- credited;
- rejected.

## Transiciones a preservar

- offline oculta anuncios activos y bloquea orden nueva.
- online vuelve a permitir ordenes solo si el anuncio y el metodo de cobro siguen validos.
- pausar anuncio no consume credito.
- borrar/archivar anuncio consume credito si el credito estaba bloqueado y la publicacion sigue dentro de su vida util.
- republicar anuncio archivado o vencido consume un credito nuevo.
- editar precio dentro del mismo costo de credito no consume credito nuevo.
- cambiar metodo de cobro de anuncio debe requerir metodo activo y propio.
- anuncio con metodo borrado no puede reactivarse hasta elegir metodo activo.
- confirmar pago consume el credito del anuncio de forma atomica.
- marcar enviado no completa automaticamente la orden si la regla actual requiere ventana o confirmacion posterior.
- pegar tx hash no acredita creditos sin verifier backend.

## Evidencia

- tests de state machine;
- tests de retry/doble click;
- tests de acciones con PIN;
- tests de orden historica con `public_order_code`.
