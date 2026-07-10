# DESIGN_TOKENS.md

NODO visual tokens are based on the approved dark fintech mockups.

## Color tokens

```txt
background.app.dark      #020B16
background.depth.dark    #061426
surface.card.dark        #071A2D
surface.card.elevated    #0B2138
surface.input.dark       #06182B
border.subtle.dark       #1D344B
border.active.blue       #1C9CEB

brand.navy               #0A2540
brand.green              #00C853
brand.blue               #1C9CEB
brand.zelle              #8A3FFC
brand.usdt               #26A17B

text.primary.dark        #FFFFFF
text.secondary.dark      #B8C4D6
text.muted.dark          #7F8CA3

success                  #00C853
warning                  #FF9800
danger                   #F44336
info                     #1C9CEB
```

Light mode must respect Telegram themeParams but keep NODO identity.

## Gradients

Primary CTA:

```txt
linear-gradient(90deg, #00C853 0%, #1C9CEB 100%)
```

Cards may use subtle dark depth only. Do not use decorative blobs/orbs.

## Radius

```txt
screen.card.radius       16px
input.radius             14px
button.radius            14px
metric.tile.radius       12px
badge.radius             8px
```

## Spacing

```txt
page.padding.x           16px
section.gap              16px
card.padding             16px
element.gap              12px
compact.gap              8px
safe.top                 use Telegram/iOS safe area
safe.bottom              use Telegram/iOS safe area
```

## Typography

Use system fonts:

```txt
font.family.ui           system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
font.family.amount       ui-monospace, SFMono-Regular, "Roboto Mono", monospace
```

Sizes:

```txt
title.large              24px / 32px semibold
title.section            18px / 24px semibold
body                     16px / 22px regular
body.small               14px / 20px regular
caption                  12px / 16px medium
amount.hero              42px / 52px regular
rate                     18px / 24px semibold
```

Do not scale font size with viewport width.

## Logo

Logo must stay identical across all screens:

- NODO wordmark
- N mark
- green verification/check accent
- no alternative logos
- no crypto/web3 treatment

Logo may animate only according to `MOTION_AND_INTERACTION.md`. Animation cannot change proportions, colors, mark shape or verification accent.

## Motion tokens

```txt
motion.duration.fast          120ms
motion.duration.base          200ms
motion.duration.screen        240ms
motion.duration.logoIntro     900ms-1400ms
motion.ease.standard          cubic-bezier(0.2, 0.0, 0, 1)
motion.ease.out               cubic-bezier(0, 0, 0.2, 1)
motion.press.scale            0.98
motion.card.enter.y           8px-12px
motion.reduced.maxDuration    150ms
```

Animate transform and opacity first. Avoid layout-affecting animation.
