# ACCEPTANCE_CRITERIA.md

- El builder entrega Understanding Report antes de construir.
- No cambia reglas de negocio.
- No debilita endpoints sensibles.
- Marketplace read usa camino optimizado y medido.
- Cache marketplace tiene invalidacion correcta.
- Pool/worker config evita `too many clients already`.
- Stress c100/c200 se ejecuta con evidencia.
- Full validation pasa.
- Reporte final incluye resultados y riesgos residuales.
- No se declara READY_FOR_REAL_USE.
- No se declara capacidad 10,000 sin prueba cloud real.

