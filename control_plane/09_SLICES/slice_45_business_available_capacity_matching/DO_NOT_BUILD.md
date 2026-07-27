# DO_NOT_BUILD.md

Este slice no autoriza:

- pagos reales;
- cambios en Base USDC;
- cambios en creditos de publicacion;
- cambios de Zelle/USDC como metodo de pago;
- ledger financiero real;
- custodia o garantia de fondos;
- cambios en reputacion o ratings;
- cambios en intake;
- cambios en soporte;
- deploy;
- migraciones ejecutadas sin aprobacion del Owner;
- reset de DB;
- borrar datos de staging;
- declarar `READY_FOR_REAL_USE`.

No convertir `available_capacity_usd` en saldo financiero. Es solo capacidad operativa declarada por el negocio.
