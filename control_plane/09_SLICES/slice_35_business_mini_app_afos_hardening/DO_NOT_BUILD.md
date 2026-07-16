# DO_NOT_BUILD.md

No construir ni tocar en este slice:

- app cliente;
- integracion cliente-negocio end-to-end;
- admin redesign;
- produccion;
- deploy;
- infraestructura;
- cambios de plan Railway/Cloudflare/Supabase;
- nuevas colas, Redis, workers o microservicios;
- wallet privada;
- seed phrase;
- custodia de fondos;
- cambios de pricing de paquetes;
- acreditacion automatica sin verifier backend;
- nuevas reglas financieras sin tests;
- Base USDC mainnet real como prueba destructiva;
- migraciones salvo que un bug bloqueante lo exija y quede aprobado en reporte;
- DR/restore provider;
- c100+ como product gate;
- cambios grandes de estilo visual sin bug o contrato.

Si el builder encuentra algo fuera de alcance, debe reportarlo como riesgo o slice posterior.
