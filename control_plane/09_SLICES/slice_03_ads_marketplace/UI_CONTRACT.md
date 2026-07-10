# UI_CONTRACT.md

Screens affected:

- R-02_HOME_SEARCH
- R-03_SEARCH_RESULTS
- R-04_BUSINESS_DETAIL
- B-08_CREATE_AD
- B-09_MY_ADS
- B-10_ARCHIVED_ADS

UI rules:

- Follow `07_UI_UX/VISUAL_REFERENCE.md` and `SCREEN_LAYOUT_MASTER.md`.
- Telegram Mini App mobile-first layout.
- Use `@telegram-apps/telegram-ui` where possible.
- Respect `themeParams`, safe areas and MainButton rules.
- Include loading, empty, error, offline, forbidden and success states.
- Use required disclaimers for marketplace, verification, credits and responsibility.
- Do not create landing/marketing pages instead of functional screens.
- Do not expose private business account values, storage paths, documents or Telegram IDs.
- Do not show fake production metrics.
- Do not show city, cash, pickup, "Mas cercano" or generic web nav.

## Endpoint mapping

- R-02 uses `GET /api/v1/ads/search` after validating amount/method.
- R-03 uses `GET /api/v1/ads/search`.
- R-04 uses `GET /api/v1/ads/{id}`.
- B-08 uses `POST /api/v1/business/ads`.
- B-09 uses `GET /api/v1/business/ads`, plus pause/archive/update endpoints.
- B-10 uses `GET /api/v1/business/ads/archived`.

Each screen file under `08_SCREENS` must stay aligned with this mapping.
