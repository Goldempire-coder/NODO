# 52C2B-DEP Wallet Connection Dependency Gate

Estado: `BLOCKED_PENDING_AUDIT`

Fecha de evaluacion: 2026-08-24

## Alcance

Este gate evalua dependencias para una futura conexion de wallet en App Negocio.
No implementa UI, provider, conexion, firma, approve, pago, watcher ni polling. No
configura project IDs, wallets, treasury, staging o produccion.

## Stack Evaluado

Se evaluaron con pins exactos:

- `@reown/appkit@1.8.23`
- `@reown/appkit-adapter-wagmi@1.8.23`
- `wagmi@2.19.5`
- `wagmi@3.7.6`, solo como comparacion de resolucion
- `viem@2.55.19`
- `@tanstack/react-query@5.101.4`

`@tanstack/react-query@5.101.4` fue preferido frente a una publicacion mas
reciente para cumplir la politica de edad de releases del lockfile sin crear una
excepcion automatica.

La documentacion oficial actual de Reown instala AppKit con Wagmi, Viem y React
Query, pero tambien declara que AppKit solo es compatible con Wagmi 2.x. Aunque
la prueba exploratoria con Wagmi 3 resolvio los peers y redujo duplicacion, no se
considera un stack aprobado mientras la documentacion oficial mantenga esa
restriccion.

Fuente oficial:

- https://docs.reown.com/appkit/react/core/installation

## Scripts De Instalacion

Los tarballs publicados fueron inspeccionados antes de decidir permisos:

| Paquete | Script | Hallazgo | Decision propuesta |
| --- | --- | --- | --- |
| `@reown/appkit@1.8.23` | `postinstall: node scripts/appkit-version-check.js` | Lee manifests locales y compara versiones Reown. No se encontro acceso de red ni telemetria en el script. | Permitir solo si el gate de vulnerabilidades pasa. |
| `bufferutil@4.1.0` | `install: node-gyp-build` | Acelerador nativo opcional para Node; dispone de fallback JavaScript. No es necesario para el frontend browser. | Denegar. |
| `utf-8-validate@5.0.10` | `install: node-gyp-build` | Acelerador nativo opcional para Node; dispone de fallback JavaScript. No es necesario para el frontend browser. | Denegar. |
| `keccak@3.0.4` | `install: node-gyp-build || exit 0` | La entrada browser usa implementacion JavaScript; el build nativo no es necesario para el bundle web. | Denegar. |

No se conserva ninguna aprobacion nueva en `pnpm-workspace.yaml` porque el stack
completo no paso este gate.

## Instalacion Y Dependencias

La instalacion candidata fue reproducible con lockfile generado y scripts
decididos explicitamente. La variante Wagmi 2 produjo duplicacion de ramas
Wagmi/Reown y un problema de peer opcional. La variante Wagmi 3 dejo el peer
check limpio y redujo el grafo, pero contradice la compatibilidad publicada por
Reown y por eso no es una salida aprobada.

Persisten dependencias transitivas deprecated en el grafo de WalletConnect,
incluyendo paquetes `@walletconnect/*` y Safe Gateway. No se propone reemplazo
manual dentro de este slice.

## Bloqueos De Seguridad

`pnpm audit --prod --audit-level high` sobre el candidato reporto 12 hallazgos:
10 moderados y 2 altos.

1. `ws` vulnerable a agotamiento de memoria por fragmentos pequenos. El grafo
   fija una version vulnerable mediante dependencias WalletConnect/Reown/Viem.
   Referencia publica: GitHub Advisory `GHSA-96hv-2xvq-fx4p`.
2. `axios` vulnerable en el adaptador HTTP Node por herencia de proxy. El grafo
   llega por AppKit Pay/Base Account/Coinbase CDP SDK y fija una version
   vulnerable. Referencia publica: GitHub Advisory
   `GHSA-gcfj-64vw-6mp9`.

Los paquetes ascendentes fijan las versiones afectadas. Este slice no autoriza
overrides transitivos ni forks, y no se debe esconder el resultado del audit
forzando una resolucion no soportada.

## Decision

Clasificacion: `BLOCKED_PENDING_AUDIT`.

No se agregan dependencias wallet a `apps/web/package.json`, no se modifica el
lockfile y no se aprueban scripts nuevos. La arquitectura Reown puede volver a
evaluarse cuando se cumplan todas estas condiciones:

1. Reown y sus transitivas publiquen un grafo sin vulnerabilidades `high`, o el
   Owner autorice un slice separado para evaluar overrides con pruebas.
2. La version Wagmi elegida coincida con la compatibilidad oficial de Reown.
3. `pnpm install --frozen-lockfile` y `pnpm peers check` pasen.
4. `pnpm audit --prod --audit-level high` pase sin vulnerabilidades altas.
5. Los scripts nativos opcionales permanezcan denegados salvo evidencia nueva.

Este resultado no significa `DO_NOT_INSTALL_PRIMARY`: el bloqueo puede cerrarse
con actualizaciones upstream y una nueva auditoria. Tampoco autoriza una
implementacion manual de wallet como sustituto.

## No Acciones

- No se implemento wallet connect.
- No se modifico runtime frontend o backend.
- No se tocaron contratos Solidity, migraciones o watcher.
- No se instalaron claves ni configuracion cloud.
- No hubo deploy, commit, push, staging o produccion.
- No se configuraron wallets ni se movieron fondos.
- No se declara `READY_FOR_REAL_USE` ni `READY_FOR_PRODUCTION`.
