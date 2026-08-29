# LEGAL_REVIEW_NOTES.md

Estado: `DRAFT LEGAL_REVIEW_REQUIRED`

Fecha de borrador: 2026-08-29

Estas notas son para revision de abogado. No son asesoria legal, no autorizan produccion y no declaran `READY_FOR_REAL_USE`.

## 1. Documentos creados para revision

- `TERMS_OF_SERVICE_DRAFT.md`
- `CLIENT_RISK_AGREEMENT_DRAFT.md`
- `BUSINESS_PARTICIPATION_AGREEMENT_DRAFT.md`
- `ACCEPTANCE_COPY.md`
- `LEGAL_REVIEW_NOTES.md`

`BUSINESS_PARTICIPATION_AGREEMENT_DRAFT.md` fue actualizado el 2026-08-29 para consolidar en un solo documento los Terminos de Negocio NODO, incluyendo cuenta de negocio, anuncios, creditos internos, pagos digitales, reembolsos, seguridad, datos, impuestos, soporte y aceptacion.

## 2. Postura operacional que debe validar abogado

NODO debe permanecer como plataforma tecnologica sin custodia ni transmision de fondos:

- NODO conecta clientes con negocios registrados.
- NODO publica anuncios, reputacion, limites y disponibilidad.
- NODO registra ordenes, estados, chat, evidencia y acciones administrativas.
- NODO ofrece soporte y herramientas de disputa.
- Las partes pagan y cumplen directamente entre ellas.
- NODO no recibe, retiene, transfiere, administra, controla, mueve ni libera fondos de clientes o negocios entre si.
- NODO no actua como banco, exchange, casa de cambio, money transmitter, escrow ni fiduciario.

Separacion importante para revision legal: NODO puede vender creditos internos al negocio como servicio propio de la plataforma. Ese pago negocio-NODO no debe confundirse con pagos, remesas, entregas o fondos entre cliente final y negocio. Los creditos no deben ser retirables, transferibles, revendibles, convertibles a efectivo ni presentados como saldo custodiado.

## 3. Referencias externas consideradas

Estas referencias deben ser revisadas por abogado contra la jurisdiccion final y el modelo real:

- OFAC Venezuela FAQ 519: la poblacion venezolana no esta sujeta a sanciones comprehensivas, pero no deben involucrarse personas o entidades sancionadas ni actividades prohibidas.
- OFAC Sanctions List Search: la herramienta ayuda a identificar posibles coincidencias, pero no sustituye debida diligencia ni programa de cumplimiento.
- FinCEN: money transmission se relaciona con aceptar y transmitir moneda, fondos u otro valor que sustituya moneda; el diseno de NODO debe evitar aceptar y transmitir valor entre partes.
- IRS: pagos o transacciones con activos digitales pueden generar obligaciones fiscales y de reporte para las partes responsables.
- OFAC: las obligaciones de sanciones tambien pueden aplicar a transacciones que involucren virtual currency.
- Zelle: recomienda enviar dinero solo a personas o negocios conocidos y confiables; pagos a usuarios enrolados pueden no ser cancelables.

Fuentes oficiales para refresh legal:

- https://ofac.treasury.gov/faqs/topic/1581
- https://ofac.treasury.gov/faqs/topic/1636
- https://ofac.treasury.gov/recent-actions/20211015
- https://www.irs.gov/filing/digital-assets
- https://www.fincen.gov/resources/statutes-regulations/guidance/application-fincens-regulations-persons-administering
- https://www.zellepay.com/faq/using-zelle
- https://www.zellepay.com/faq/small-business-using-zelle

## 4. Riesgos que requieren abogado

### 4.1 Clasificacion regulatoria

Validar si el modelo exacto de NODO, incluyendo Telegram Mini App, anuncios, ordenes, evidencia, chat, soporte, disputas, venta de creditos internos y metodos externos, podria activar obligaciones de money services business, money transmitter, payment processor, exchange, remittance, escrow, broker, marketplace regulado o figura similar en alguna jurisdiccion relevante.

Validar especificamente que los creditos NODO, al no ser retirables, transferibles ni convertibles a efectivo, se mantengan como creditos internos para servicios propios de la plataforma y no como saldo custodiado o valor transmisible entre terceros.

### 4.2 Jurisdiccion y ley aplicable

Definir entidad operadora, pais/estado, ley aplicable, idioma prevaleciente, tribunales/arbitraje, notificaciones legales y mecanismo de resolucion legal de disputas.

### 4.3 Sanciones y debida diligencia

Definir estandar minimo de screening y monitoreo para clientes, negocios, beneficiarios, receptores, wallets, bancos, contrapartes y documentos. Validar listas aplicables, frecuencia, evidencia, manejo de posibles matches y bloqueo de operaciones.

### 4.4 AML, fraude y KYC/KYB

Validar obligaciones de identificacion, verificacion de negocios, verificacion de usuarios, monitoreo transaccional, reportes, retencion de evidencia, umbrales, escalamiento y entrenamiento operativo.

### 4.5 Zelle, bancos y proveedores externos

Validar si los textos sobre Zelle, USDT TRC20, bancos, wallets, exchanges y redes externas requieren disclaimers especificos, restricciones de marca, terminos adicionales o prohibiciones.

### 4.6 Criptoactivos, USDT TRC20 y pagos digitales de creditos

Validar riesgos de blockchain, irreversibilidad, wallet screening, travel rule si aplica, sanciones de direcciones, uso de exchanges, propiedad de wallets, comisiones, confirmaciones, pagos incorrectos, pagos duplicados, reembolsos y restricciones por jurisdiccion.

### 4.7 Consumidor, comercio y publicidad

Validar si ratings, badges, limites, tasas, disponibilidad, tiempos estimados o palabra `verificado` pueden interpretarse como recomendacion, garantia, publicidad enganosa, scoring regulado o promesa de cumplimiento.

### 4.8 Privacidad y retencion

Validar politica de privacidad, base legal para conservar evidencia, minimizacion, retencion, acceso, eliminacion, hashes de IP/user agent, documentos del negocio, chat, comprobantes, logs y datos de Telegram.

### 4.9 Firma electronica y prueba de aceptacion

Validar si checkbox/boton dentro de Telegram Mini Apps es suficiente para consentimiento, como versionar documentos, como probar aceptacion y como manejar re-aceptacion.

### 4.10 Menores y capacidad legal

Definir edad minima, capacidad legal, usuarios prohibidos, representantes, negocios registrados y restricciones territoriales.

### 4.11 Limitacion de responsabilidad e indemnizacion

Validar enforceability de limite de responsabilidad, exclusion de danos, indemnizacion, renuncias, disclaimers y lenguaje obligatorio por jurisdiccion.

### 4.12 Operacion de disputas

Validar que NODO pueda revisar evidencia y tomar medidas operativas sin asumir rol de arbitro financiero, fiduciario, escrow, asegurador o garante.

## 5. Que NO debe decir NODO

NODO no debe decir ni sugerir:

- que custodia fondos.
- que retiene fondos.
- que libera fondos.
- que procesa remesas entre partes.
- que garantiza pagos.
- que garantiza entregas.
- que asegura solvencia.
- que recupera fondos.
- que protege dinero.
- que actua como escrow.
- que actua como banco, exchange, casa de cambio o money transmitter.
- que OFAC screening elimina todo riesgo.
- que un negocio verificado es regulatoriamente aprobado.
- que una operacion es segura por estar dentro de NODO.
- que los creditos NODO son dinero, saldo, deposito, inversion, retiro disponible o valor transferible.

## 6. Recomendacion de implementacion posterior

No implementar hasta aprobacion legal y owner review.

Cuando se apruebe, implementar en una slice separada con contrato previo:

1. Crear versionado documental: `terms_version`, `client_risk_agreement_version`, `business_participation_agreement_version`, `business_credit_terms_version` si se separa luego.
2. Crear aceptacion obligatoria por superficie antes de acciones sensibles.
3. Guardar evidencia de aceptacion con `user_id`, `business_id` si aplica, version, `accepted_at`, `ip_hash` si existe, `user_agent_hash` si existe, `surface` y `locale`.
4. Bloquear uso si la version vigente no fue aceptada.
5. Agregar re-aceptacion cuando cambie una version.
6. Agregar auditoria admin para cambios de version y activacion.
7. Agregar pruebas de contrato/API antes de tocar UI.
8. Verificar que ninguna pantalla use copy prohibido.
9. Verificar que los flujos de compra de creditos usen texto de aceptacion negocio-NODO y no textos de cliente final.

Estado recomendado de esta entrega documental: `AGREEMENT_DRAFT_READY_FOR_OWNER_REVIEW`.
