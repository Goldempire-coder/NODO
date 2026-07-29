# Slice 47B Scope

Estado: CONTRACTS_DRAFT_READY_FOR_OWNER_REVIEW

## Dentro Del Alcance

- Mapear alertas actuales.
- Definir que eventos producen alerta.
- Definir dedupe, severidad, owner y accion.
- Definir alertas por sintomas de usuario y no solo por causas tecnicas.
- Definir reglas de anomalia iniciales basadas en tasas, latencia y caidas
  respecto al comportamiento esperado.
- Definir alertas de costo por desviacion: Redis, storage, logs, retries y
  polling.
- Definir patrones de logs que deben crear alerta agregada.
- Definir backoff y pausa en pestana oculta para no quemar Redis.
- Definir UI minima de campana y badges.
- Definir pruebas para que cada alerta abra el caso correcto.

## Fuera Del Alcance

- Reconciliacion financiera.
- Jobs nuevos.
- Proveedores externos de alerting.
- Monitoreo sintetico completo; eso vive en 47F.
- Decisiones automaticas de fraude, pago valido o culpa.
- Push a SMS/email.

## Regla AFOS

Una alerta debe ser accionable. Si no tiene dueno, severidad y siguiente paso,
es ruido.
