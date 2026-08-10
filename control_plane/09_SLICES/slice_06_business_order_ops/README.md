# slice_06_business_order_ops

Objective: Permitir al negocio revisar ordenes, confirmar pago, reportar
problemas mediante disputa y marcar entrega. La decision C0 sustituye el
rechazo directo del contrato original; `payment_rejected` queda legacy.

Depends on: slice_05_payment_instructions_reports

Read before building:

- 00_GOVERNANCE/SOURCE_OF_TRUTH.md
- 00_GOVERNANCE/BUILDER_RULES.md
- 00_GOVERNANCE/CODE_ARCHITECTURE_MASTER.md
- 09_SLICES/SLICE_EXECUTION_MATRIX.md
- 09_SLICES/SLICE_CONTRACTS_MASTER.md
- this slice folder

Builder must submit an understanding report before edits and a final BUILDER_REPORT with files, line ranges, tests and residual risks.
