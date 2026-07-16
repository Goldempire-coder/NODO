# DO_NOT_BUILD - slice_24_observability_debuggability

Do not build:

- video/session recording;
- third-party SaaS observability;
- frontend capture of tokens or Telegram initData;
- full payload logging;
- message/document/payment-instruction capture;
- production persistent replay without owner approval;
- financial ledger behavior in observability;
- business rule changes;
- deploy;
- `READY_FOR_REAL_USE`.

Do not use observability fields as authorization input.
