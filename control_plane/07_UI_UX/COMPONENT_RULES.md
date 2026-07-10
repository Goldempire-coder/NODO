# COMPONENT_RULES.md

## Base components

- AmountInput
- PaymentMethodSegmentedControl
- BusinessCard
- VerifiedBadge
- RateDisplay
- LimitDisplay
- OrderStepper
- OrderTimer
- EmptyState
- ErrorRetry
- SkeletonBlock
- SensitiveValueReveal

## Required app shell components

- AppShell
- HeaderIdentity
- AnimatedLogo
- EntryMotionShell
- UserGreeting
- BottomTabNav
- MainActionButtonBridge
- TrustDisclaimerCard

## Required marketplace components

- SearchContextBar
- FilterChipGroup
- BusinessResultCard
- AvailabilityBadge
- RatingSummary
- BusinessAvatar

## Required order components

- ReceiverDataForm
- FrozenRatePreview
- CalculatedBolivaresPreview
- PaymentInstructionCard
- PaymentProofForm
- ConfirmReceivedWarning
- DisputeEntryAction

## Required business components

- CreditBalanceCard
- BusinessStatusCard
- CreateAdForm
- IncomingOrderCard
- PaymentMethodCard

## Required admin components

- AdminMetricTile
- PendingReviewTable
- CreditPaymentReviewPanel
- DisputeResolutionPanel
- AuditLogTable
- ManualAdjustmentDialog

## Component rules

- Components do not own business rules.
- Components do not call DB.
- Components do not decide permissions.
- Components with motion must respect MOTION_AND_INTERACTION.md.
- Components with motion must support reduced motion.
- Components can receive disabled/error/loading props.
- Components must support loading, empty, error and offline states where applicable.
- Components that display sensitive values must support masked and revealed states.
