# LEGAL_REGULATORY_RISK_MAP.md

Estado: `DRAFT LEGAL_REVIEW_REQUIRED`

Fecha: 2026-09-03

Este documento es un mapa operativo de riesgo legal y regulatorio para NODO. No es asesoria legal, no autoriza produccion real y debe ser revisado por abogado antes de usarlo como base de lanzamiento.

## 1. Postura oficial de producto

NODO es una plataforma tecnologica que conecta clientes con negocios registrados, publica anuncios, organiza ordenes, chat, evidencia, reputacion, creditos internos y soporte operativo.

NODO no recibe, custodia, retiene, administra, controla, mueve, transmite, envia ni libera fondos entre cliente y negocio.

El pago entre cliente y negocio ocurre directamente entre esas partes. NODO puede registrar evidencia, estados y disputas, pero no garantiza pago, entrega, tasa, recuperacion, solvencia ni resultado.

NODO puede cobrar a negocios por creditos internos usados para publicar u operar anuncios. Ese pago es negocio-NODO por un servicio propio de plataforma. Los creditos NODO no son dinero, deposito, saldo custodiado, inversion, retiro disponible ni valor transferible.

## 2. Separacion de superficies

### 2.1 Compra de creditos NODO

Riesgo practico: menor, si se mantiene como venta de servicio propio.

NODO recibe USDC u otro metodo habilitado para vender creditos internos al negocio. La clave legal aqui es que NODO no mueve fondos de un cliente a un negocio ni crea saldos retirables.

Controles minimos:

- creditos no retirables, no transferibles y no convertibles a efectivo;
- checkout claro de paquete, monto, red y token;
- treasury de NODO separada de wallets de usuarios;
- ledger interno exact-once;
- soporte para pagos incorrectos, duplicados o fuera de red;
- contabilidad e impuestos sobre ingresos de NODO;
- screening basico de sanciones y listas de riesgo antes de produccion real.

Lenguaje permitido:

- `NODO vende creditos internos para usar servicios propios de la plataforma.`
- `El pago de creditos se acredita despues de confirmacion y validacion.`
- `Los creditos NODO no son dinero ni saldo retirable.`

Lenguaje prohibido:

- `saldo en NODO`;
- `deposito`;
- `retiro disponible`;
- `fondos protegidos`;
- `pago garantizado`;
- `NODO guarda tus fondos`.

### 2.2 Orden cliente-negocio

Riesgo practico: mayor, aunque NODO no tenga custodia.

NODO facilita que cliente y negocio se encuentren, creen una orden, compartan instrucciones, reporten pago, confirmen recepcion, conversen y abran disputas. Aunque el dinero no pasa por NODO, la plataforma puede ser vista como facilitadora de operaciones entre terceros. Esto exige lenguaje cuidadoso, limites, auditoria, monitoreo de abuso y revision legal por jurisdiccion.

Controles minimos:

- negocios registrados y revisados antes de publicar;
- limites por negocio, usuario, metodo, monto y riesgo;
- reputacion y estados sin prometer garantia;
- evidencia y chat conservados con minimizacion;
- bloqueo de instrucciones fuera de flujo cuando aumenten riesgo;
- reporte de pago y confirmacion con estados claros;
- soporte/disputas como revision operativa, no arbitraje financiero;
- sanciones, fraude, actividad prohibida y restricciones territoriales.

Lenguaje permitido:

- `NODO facilita la conexion entre cliente y negocio.`
- `El pago se realiza directamente entre cliente y negocio.`
- `NODO registra evidencia y estados para soporte y auditoria.`
- `Perfil registrado en NODO.`

Lenguaje prohibido:

- `NODO procesa remesas`;
- `NODO es casa de cambio`;
- `NODO asegura el pago`;
- `NODO garantiza la entrega`;
- `NODO libera fondos`;
- `operacion sin riesgo`;
- `negocio seguro` sin explicar el alcance real de la revision.

### 2.3 Admin, soporte y disputas

Riesgo practico: medio.

El panel admin puede revisar ordenes, mensajes, evidencia, negocios, clientes, alertas, creditos y estados. Debe operar como control interno de plataforma, no como juez, banco, asegurador o escrow.

Controles minimos:

- RBAC por rol;
- masking de datos sensibles;
- acceso justificado a evidencia;
- audit logs;
- acciones sensibles con PIN o reason cuando aplique;
- notificaciones de emergencia;
- capacidad de pausar funciones;
- soporte con lenguaje neutral.

Lenguaje permitido:

- `NODO revisa evidencia disponible para tomar medidas operativas.`
- `NODO puede limitar, pausar o cerrar acceso por riesgo.`

Lenguaje prohibido:

- `NODO decide quien tiene la razon financiera`;
- `NODO recupera tu dinero`;
- `NODO garantiza reembolso`;
- `NODO libera fondos`.

## 3. Fuentes regulatorias a revisar

### 3.1 Estados Unidos - FinCEN / BSA

FinCEN distingue entre usuarios de moneda virtual convertible, exchangers y administrators. Usar moneda virtual para comprar bienes o servicios no convierte por si solo al usuario en MSB. Pero aceptar y transmitir valor que sustituye moneda para otra persona puede entrar en money transmission.

Aplicacion practica a NODO:

- vender creditos propios a negocios se parece mas a recibir pago por servicio propio;
- aceptar fondos de una parte y transmitirlos a otra seria una linea roja;
- facilitar un mercado P2P con cripto/fiat requiere revision legal especifica, aunque NODO no custodie.

Fuentes:

- FinCEN 2013 CVC guidance: https://www.fincen.gov/resources/statutes-regulations/guidance/application-fincens-regulations-persons-administering
- 31 CFR 1010.100 money transmitter definition: https://www.ecfr.gov/current/title-31/subtitle-B/chapter-X/part-1010

### 3.2 Estados Unidos - estados y licencias

El analisis federal no sustituye leyes estatales. Si NODO opera hacia usuarios de Estados Unidos o desde una entidad estadounidense, abogado debe revisar si algun estado considera que el modelo requiere licencia, registro, exencion o restricciones.

Aplicacion practica a NODO:

- no lanzar como money transmitter, exchange, remittance provider, escrow o wallet custodiada;
- documentar jurisdicciones permitidas y bloqueadas;
- validar terminos, entidad operadora, ubicacion de usuarios y alcance territorial.

### 3.3 OFAC y sanciones

OFAC recomienda programas de cumplimiento basados en riesgo para empresas con exposicion a virtual currency, incluyendo screening y controles apropiados segun el negocio.

Aplicacion practica a NODO:

- bloquear personas, entidades, wallets o jurisdicciones sancionadas cuando se detecten;
- conservar evidencia de revisiones;
- no prometer que screening elimina todo riesgo;
- definir proceso de hit, false positive y escalamiento.

Fuentes:

- OFAC virtual currency guidance: https://ofac.treasury.gov/media/913571/download?inline=
- OFAC virtual currency FAQs: https://ofac.treasury.gov/faqs/topic/1626

### 3.4 IRS e impuestos

El IRS trata activos digitales como propiedad para impuestos federales de EE. UU. y los pagos recibidos por servicios pueden generar ingreso ordinario medido en USD al momento de recibirlos.

Aplicacion practica a NODO:

- contabilidad clara de pagos recibidos por creditos;
- valor USD del ingreso al momento del pago;
- reportes fiscales segun entidad y jurisdiccion;
- reconciliacion entre wallet, contrato, ledger y facturacion.

Fuentes:

- IRS Digital Assets: https://www.irs.gov/filing/digital-assets
- IRS Digital Asset FAQs: https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-digital-asset-transactions

### 3.5 Union Europea - MiCA

MiCA regula crypto-asset service providers y servicios relacionados con crypto-assets en la Union Europea. Si NODO ofrece servicios a usuarios de la UE o permite actividad que pueda parecer plataforma de trading, intercambio, recepcion/transmision de ordenes o transferencia de criptoactivos, se requiere revision legal antes de servir esa region.

Aplicacion practica a NODO:

- no abrir UE sin revision legal;
- no usar lenguaje de trading platform, exchange o broker;
- documentar bloqueo o restriccion territorial si aplica.

Fuente:

- Regulation (EU) 2023/1114: https://eur-lex.europa.eu/eli/reg/2023/1114/oj/eng

### 3.6 Venezuela y jurisdicciones locales

NODO usa referencias operativas como Pago Movil, Zelle, USDT TRC20, negocios venezolanos y entregas en Bs. Este mapa no confirma la regulacion venezolana vigente. Antes de produccion real se requiere abogado local para revisar normativa cambiaria, criptoactivos, datos personales, consumidor, publicidad, comercio y reportes aplicables.

Aplicacion practica a NODO:

- no prometer cumplimiento regulatorio venezolano sin abogado;
- mantener limites, registro de negocios, evidencia y soporte;
- definir entidad operadora y jurisdicciones permitidas antes de lanzamiento real.

## 4. Semaforo de riesgo

### Verde condicionado

- Venta de creditos internos no retirables a negocios.
- Pago negocio-NODO por servicio propio.
- Directorio de negocios registrados con anuncios y reputacion.
- Evidencia, soporte y auditoria sin custodiar fondos.

Condicion: lenguaje correcto, terminos aceptados, contabilidad, screening y abogado revisando jurisdicciones.

### Amarillo

- Ordenes P2P con Zelle, USDT TRC20, tasas, chat y evidencia.
- Disputas donde NODO limita cuentas o afecta reputacion.
- Ratings, badges o palabras como `verificado`.
- Uso de stablecoins, wallets y proveedores externos.

Condicion: limites, monitoreo, KYB de negocios, sanciones, politicas de uso prohibido y soporte entrenado.

### Rojo

- Recibir dinero del cliente para pasarlo al negocio.
- Mantener saldos de clientes o negocios.
- Permitir retiros, conversion, cash-out o transferencia de creditos.
- Hacer escrow, liberar fondos, prometer recuperacion o garantia.
- Operar como exchange, casa de cambio, broker, remesadora o money transmitter.
- Permitir operaciones fuera de jurisdicciones revisadas.

Condicion: no construir sin opinion legal, licencias y programa de cumplimiento formal.

## 5. Cambios de lenguaje requeridos

Mantener:

- `NODO no recibe, retiene, transfiere ni garantiza fondos entre cliente y negocio.`
- `El pago y la entrega ocurren directamente entre las partes.`
- `NODO vende creditos internos para servicios propios de la plataforma.`
- `Los creditos no son dinero, deposito, saldo custodiado, retiro disponible ni valor transferible.`

Evitar:

- `NODO procesa pagos entre cliente y negocio.`
- `NODO procesa remesas.`
- `NODO garantiza pago o entrega.`
- `Pago seguro` cuando pueda sugerir garantia financiera.
- `Negocio seguro` o `negocio confiable` sin explicar el alcance.
- `Exchange`, `casa de cambio`, `broker`, `escrow`, `custodia` como descripcion de NODO.

Corregir documentos viejos donde Stripe o pagos manuales aparezcan como flujo principal si el flujo vigente de creditos es Base USDC contractual.

## 6. Gates antes de produccion real

### Creditos NODO

- Terminos de negocio aceptados y versionados.
- Treasury real aprobada.
- Contrato y watcher en red real validados.
- Alertas operativas activas.
- Reconciliacion contable de ingresos.
- Politica de pagos duplicados, incorrectos y reembolsos.
- Screening de sanciones definido.
- Soporte entrenado con lenguaje no custodial.

### Marketplace cliente-negocio

- Opinion legal por jurisdiccion objetivo.
- Entidad operadora definida.
- KYB minimo para negocios.
- Politica de actividad prohibida.
- Limites por riesgo.
- Proceso de disputas no arbitral.
- Logs y evidencia con retencion definida.
- Bloqueo territorial donde aplique.
- Copy sin promesas de garantia.

## 7. Conclusion operativa

La posicion mas defendible para NODO es:

`NODO es una plataforma tecnologica de anuncios, ordenes, evidencia, reputacion y creditos internos. NODO cobra por servicios propios y no mueve fondos entre cliente y negocio.`

Esto reduce riesgo frente a un modelo custodial o de remesas, pero no elimina la necesidad de revision legal porque el marketplace P2P con metodos de pago externos puede ser analizado por reguladores segun hechos, jurisdiccion, volumen, marketing, controles, actividad de usuarios y rol real de NODO.
