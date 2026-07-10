# SCOPE.md

## Objective

Crear anuncios, mostrar marketplace y aplicar costo/vida del anuncio por rango.

## Included

- ads
- credit_wallets read/write for hold at publish
- credits_ledger
- audit_logs
- GET /api/v1/ads/search
- GET /api/v1/ads/{id}
- POST /api/v1/business/ads
- GET /api/v1/business/ads
- GET /api/v1/business/ads/archived
- PUT /api/v1/business/ads/{id}
- POST /api/v1/business/ads/{id}/pause
- POST /api/v1/business/ads/{id}/archive

## Affected screens

- R-02_HOME_SEARCH
- R-03_SEARCH_RESULTS
- R-04_BUSINESS_DETAIL
- B-08_CREATE_AD
- B-09_MY_ADS
- B-10_ARCHIVED_ADS

## Explicitly excluded

- order creation
- payment report
- chat/dispute

If a requested change falls outside this scope, stop and report BLOCKED_BY_MISSING_CONTRACT or request owner approval.
