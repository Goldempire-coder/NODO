type DecimalOptions = {
  maxDecimals?: number;
  maxIntegerDigits?: number;
};

export function sanitizeDecimalInput(value: string, options: DecimalOptions = {}): string {
  const maxDecimals = options.maxDecimals ?? 2;
  const maxIntegerDigits = options.maxIntegerDigits ?? 8;
  const normalized = value.replace(/,/g, ".");
  const digitsAndDots = normalized.replace(/[^\d.]/g, "");
  const [integerPart = "", ...decimalParts] = digitsAndDots.split(".");
  const integer = integerPart.slice(0, maxIntegerDigits);
  const decimals = decimalParts.join("").slice(0, maxDecimals);

  if (digitsAndDots.includes(".") && maxDecimals > 0) {
    return `${integer}.${decimals}`;
  }

  return integer;
}

export function sanitizeIntegerInput(value: string, maxDigits = 6): string {
  return value.replace(/\D/g, "").slice(0, maxDigits);
}

export function sanitizePhoneInput(value: string): string {
  const cleaned = value.replace(/[^\d+ ()-]/g, "").replace(/(?!^)\+/g, "");
  return cleaned.slice(0, 24);
}
