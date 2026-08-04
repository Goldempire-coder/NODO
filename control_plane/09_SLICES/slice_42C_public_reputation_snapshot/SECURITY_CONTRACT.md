# Security Contract

- La escritura de un rating no actualiza inmediatamente la proyeccion publica.
- El snapshot requiere al menos cinco ratings, un calculo fuente con 24h de
  antiguedad y un intervalo minimo de 24h entre publicaciones.
- Marketplace y negocio nunca consultan agregados vivos para presentar o
  ordenar reputacion.
- No se crean mensajes, attention items ni notificaciones por ratings.
- El conteo exacto del snapshot puede revelar cambios agrupados; este riesgo
  residual debe revisarse antes de reducir el umbral o intervalo.
