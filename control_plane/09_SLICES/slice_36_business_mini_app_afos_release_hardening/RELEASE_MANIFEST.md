# RELEASE_MANIFEST

## Archivos de producto tocados por este slice

- `apps/api/app/modules/ads/service.py`
- `apps/api/app/modules/ads/management.py`
- `apps/api/app/modules/ads/memory_repository.py`
- `apps/api/app/modules/ads/postgres_repository.py`
- `apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts`
- `apps/web/src/screens/business-app/BusinessAdsScreens.tsx`
- `apps/web/src/screens/business-app/ads/BusinessAdCard.tsx`
- `apps/web/src/screens/business-app/ads/BusinessAdDetailPanel.tsx`

## Tests tocados

- `apps/api/tests/test_ads_marketplace.py`
- `apps/api/tests/test_auth_lifecycle_static.py`

## Contratos tocados

- `control_plane/06_API_CONTRACTS/ADS_API.md`
- `control_plane/03_DOMAIN_RULES/AD_LIFECYCLE_MASTER.md`
- `control_plane/03_DOMAIN_RULES/RISK_RULES.md`

## Observacion AFOS

El worktree completo contiene muchos cambios previos fuera de este slice. Este manifest solo declara el alcance agregado por `slice_36_business_mini_app_afos_release_hardening`; no certifica el resto del repo como release candidate limpio.

