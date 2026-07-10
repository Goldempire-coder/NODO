# TELEGRAM_MINI_APP_RULES.md

## Required Telegram behavior

- Use MainButton native.
- Use themeParams.
- Use haptic feedback.
- Use ClosingConfirmation in payment flows.
- Respect safe areas.
- The app must feel native inside Telegram.

## MainButton rules

- MainButton is only for the primary screen CTA.
- Use loading state during async actions.
- Disable when form is invalid.
- Separate setParams from click handler registration.
- Remove click handler on screen unmount.
- Never register duplicate handlers on state changes.

## Haptic feedback

Use only on critical actions:

- create order
- report payment
- confirm payment received by business
- mark delivered
- confirm received
- open dispute
- approve/reject admin action

## ClosingConfirmation

Required during:

- active payment timer
- payment instructions
- report payment form with unsaved proof
- admin critical action dialogs

## themeParams

Use Telegram themeParams as environmental input, but preserve NODO tokens from DESIGN_TOKENS.md.

## Native-feeling constraints

- No landing page hero as first screen.
- No generic web navbar.
- No desktop-first table on remitter/business Mini App screens.
- No modal-heavy flow unless Telegram-native behavior is used.
