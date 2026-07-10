# UI_UX_MASTER.md

## Purpose

NODO must feel like a professional fintech inside Telegram, not a generic external website.

Builder must read:

- VISUAL_REFERENCE.md
- SCREEN_LAYOUT_MASTER.md
- DESIGN_TOKENS.md
- COMPONENT_RULES.md
- TELEGRAM_MINI_APP_RULES.md
- MOTION_AND_INTERACTION.md
- COPY_MICROCOPY.md

## Non-negotiable rules

- Use @telegram-apps/telegram-ui as base UI kit where possible.
- Use Telegram themeParams.
- Use MainButton native for primary CTAs.
- Use haptic feedback only on critical actions.
- Use ClosingConfirmation in payment-sensitive flows.
- Use skeleton loading for remote data.
- Use controlled motion and microinteractions from MOTION_AND_INTERACTION.md.
- Use empty, error and offline states.
- Respect safe areas.
- Mask sensitive data.
- Show verified badges.
- Show prominent timer in active orders.
- Show order progress stepper.
- Never show guarantee, escrow or protected-funds language.
- Never show city, cash, pickup points or "Mas cercano" in MVP.
- Never hardcode fake production metrics.
- Never make the main entry/home screen feel static.
- Never use heavy decorative animation that hurts Mini App performance.

## Approved visual direction

Owner-approved reference images:

- C:\Users\carlo\Downloads\57cd0b5c-e4f0-4bbf-ac5b-120377741c2b.png
- C:\Users\carlo\Downloads\a2344961-cf9e-49fd-a0b3-bf6e85b0aa2b.png

Required visual feel:

- dark navy app shell
- dark translucent cards
- thin borders
- green trust accents
- blue action accents
- purple for Zelle only
- compact cards
- bottom tab nav
- strong amount input
- professional marketplace list

## Business logic boundary

UI recommendations cannot override:

- SOURCE_OF_TRUTH
- ENUMS_AND_STATUS_MASTER
- DATA_MODEL_MASTER
- RBAC_PERMISSION_MATRIX
- API_CONTRACTS
- TRUST_AND_DISCLAIMERS
- MVP_SCOPE

If a visual idea conflicts with these, Builder must stop and report BLOCKED_BY_CONTRACT_CONFLICT.

## Screen distribution

Screen distribution is controlled by SCREEN_LAYOUT_MASTER.md. Builder cannot invent a new navigation model without owner approval.

## Production data rule

Production cannot show invented:

- active business counts
- recent orders
- best rates
- completed order counts
- ratings
- monthly metrics

If backend data is unavailable, show empty/skeleton/error state instead of fake numbers.
