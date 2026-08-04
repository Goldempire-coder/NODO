# QA

- Menos de cinco ratings no publica.
- El quinto rating habilita el primer snapshot.
- Un cambio interno posterior no altera el DTO antes de 24h.
- Marketplace y negocio leen el snapshot; Admin lee agregados internos.
- Ranking ignora metricas vivas y de snapshot.
- Migracion `0045_public_reputation_snapshots` valida up/down en PostgreSQL
  desechable antes de Owner Review.
- No se afirma scheduler activo sin evidencia del ambiente.
