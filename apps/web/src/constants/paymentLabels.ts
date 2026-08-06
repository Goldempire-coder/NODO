const PAYMENT_METHOD_LABELS: Record<string, string> = {
  zelle: "Zelle",
  usdt_trc20: "USDT"
};

const PAYMENT_METHOD_CURRENCY_PRESENTATION = {
  zelle: {
    amountSymbol: "$",
    currencyLabel: "USD",
    currencyTone: "usd",
    offerLabel: "Zelle · USD"
  },
  usdt_trc20: {
    amountSymbol: "",
    currencyLabel: "USDT",
    currencyTone: "usdt",
    offerLabel: "USDT"
  }
} as const;

export type PaymentMethodCurrencyPresentation =
  (typeof PAYMENT_METHOD_CURRENCY_PRESENTATION)[keyof typeof PAYMENT_METHOD_CURRENCY_PRESENTATION];

const DELIVERY_METHOD_LABELS: Record<string, string> = {
  pago_movil_ve: "Pago Movil"
};

const DELIVERY_METHOD_CURRENCY: Record<string, string> = {
  pago_movil_ve: "Bs."
};

function normalizeMethodValue(value: unknown): string | null {
  if (!value) {
    return null;
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const candidates = [
      record.method,
      record.payment_method,
      record.receive_method,
      record.delivery_method,
      record.type,
      record.code
    ];
    const candidate = candidates.find((item) => typeof item === "string");
    return typeof candidate === "string" ? candidate : null;
  }
  return String(value);
}

function humanizeUnknown(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim();
}

export function paymentMethodCurrencyPresentation(value: unknown): PaymentMethodCurrencyPresentation {
  const normalized = normalizeMethodValue(value);
  return normalized === "usdt_trc20"
    ? PAYMENT_METHOD_CURRENCY_PRESENTATION.usdt_trc20
    : PAYMENT_METHOD_CURRENCY_PRESENTATION.zelle;
}

export function formatPaymentMethod(value: unknown): string {
  const normalized = normalizeMethodValue(value);
  if (!normalized) {
    return "Metodo no disponible";
  }
  return PAYMENT_METHOD_LABELS[normalized] ?? humanizeUnknown(normalized);
}

export function formatDeliveryMethod(value: unknown): string {
  const normalized = normalizeMethodValue(value);
  if (!normalized) {
    return "Entrega no disponible";
  }
  return DELIVERY_METHOD_LABELS[normalized] ?? humanizeUnknown(normalized);
}

export function formatDeliveryCurrency(value: unknown): string {
  const normalized = normalizeMethodValue(value);
  if (!normalized) {
    return "";
  }
  return DELIVERY_METHOD_CURRENCY[normalized] ?? "";
}

export function formatExchangeRoute(paymentMethod: unknown, deliveryMethod: unknown): string {
  const currency = formatDeliveryCurrency(deliveryMethod);
  const parts = [
    `Recibe ${formatPaymentMethod(paymentMethod)}`,
    `Tipo de pago: ${formatDeliveryMethod(deliveryMethod)}`,
    currency ? `Moneda: ${currency}` : null
  ].filter(Boolean);
  return parts.join(" - ");
}

export function formatOrderMethodLine(paymentMethod: unknown, deliveryMethod: unknown): string {
  const currency = formatDeliveryCurrency(deliveryMethod);
  const parts = [
    `Metodo: ${formatPaymentMethod(paymentMethod)}`,
    `Entrega: ${formatDeliveryMethod(deliveryMethod)}`,
    currency ? `Moneda: ${currency}` : null
  ].filter(Boolean);
  return parts.join(" - ");
}
