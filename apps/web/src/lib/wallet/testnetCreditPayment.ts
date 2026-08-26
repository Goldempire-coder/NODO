import type { ContractCreditPayment } from "../../types/credits";
import type { Eip1193Provider } from "./eip1193";

const BASE_SEPOLIA_CHAIN_ID = 84532;
const ERC20_ALLOWANCE_SELECTOR = "dd62ed3e";
const ERC20_APPROVE_SELECTOR = "095ea7b3";
const VAULT_PAY_SELECTOR = "a1147e9b";
const UINT256_MAX = (1n << 256n) - 1n;

type PayableTestnetCreditPayment = {
  amount: bigint;
  contractAddress: string;
  contractVersion: bigint;
  payerAddress: string;
  purchaseRef: string;
  signature: string;
  tokenAddress: string;
  validUntil: bigint;
};

function requireAddress(value: string | null | undefined, field: string): string {
  if (!value || !/^0x[a-fA-F0-9]{40}$/.test(value)) {
    throw new Error(`TESTNET_PAYMENT_${field}_INVALID`);
  }
  return value.toLowerCase();
}

function requireBytes32(value: string | null | undefined, field: string): string {
  if (!value || !/^0x[a-fA-F0-9]{64}$/.test(value)) {
    throw new Error(`TESTNET_PAYMENT_${field}_INVALID`);
  }
  return value.toLowerCase();
}

function requireSignature(value: string | undefined): string {
  if (!value || !/^0x[a-fA-F0-9]{130}$/.test(value)) {
    throw new Error("TESTNET_PAYMENT_SIGNATURE_INVALID");
  }
  return value.toLowerCase();
}

function requireUint256(value: string | number | null | undefined, field: string): bigint {
  try {
    const parsed = typeof value === "number" && Number.isSafeInteger(value)
      ? BigInt(value)
      : typeof value === "string" && /^(0|[1-9][0-9]*)$/.test(value)
        ? BigInt(value)
        : -1n;
    if (parsed < 0n || parsed > UINT256_MAX) {
      throw new Error("out of range");
    }
    return parsed;
  } catch {
    throw new Error(`TESTNET_PAYMENT_${field}_INVALID`);
  }
}

function wordFromUint(value: bigint): string {
  return value.toString(16).padStart(64, "0");
}

function wordFromAddress(value: string): string {
  return value.slice(2).padStart(64, "0");
}

function encodeDynamicBytes(value: string): string {
  const bytes = value.slice(2);
  const paddedLength = Math.ceil(bytes.length / 64) * 64;
  return `${wordFromUint(BigInt(bytes.length / 2))}${bytes.padEnd(paddedLength, "0")}`;
}

function requireAcceptedRequest(result: unknown): void {
  if (typeof result !== "string" || !/^0x[a-fA-F0-9]{64}$/.test(result)) {
    throw new Error("TESTNET_PAYMENT_REQUEST_NOT_ACCEPTED");
  }
}

export function paymentAuthorizationExpired(payment: ContractCreditPayment, nowMs = Date.now()): boolean {
  return payment.authorization_valid_until === null
    || nowMs >= payment.authorization_valid_until * 1000;
}

export function requirePayableTestnetCreditPayment(
  payment: ContractCreditPayment,
  connectedAddress: string,
  connectedChainId: number,
): PayableTestnetCreditPayment {
  if (
    payment.network !== "base_sepolia"
    || payment.chain_id !== BASE_SEPOLIA_CHAIN_ID
    || payment.is_testnet !== true
    || connectedChainId !== BASE_SEPOLIA_CHAIN_ID
  ) {
    throw new Error("TESTNET_PAYMENT_NETWORK_INVALID");
  }
  if (
    payment.authorization_status !== "valid"
    || payment.capabilities.can_pay !== true
    || paymentAuthorizationExpired(payment)
  ) {
    throw new Error("TESTNET_PAYMENT_AUTHORIZATION_EXPIRED");
  }
  const payerAddress = requireAddress(payment.payer_wallet_address, "PAYER");
  if (payerAddress !== requireAddress(connectedAddress, "CONNECTED_WALLET")) {
    throw new Error("TESTNET_PAYMENT_WALLET_MISMATCH");
  }
  const amount = requireUint256(payment.expected_amount_units, "AMOUNT");
  if (amount === 0n) {
    throw new Error("TESTNET_PAYMENT_AMOUNT_INVALID");
  }
  return {
    amount,
    contractAddress: requireAddress(payment.contract_address, "CONTRACT"),
    contractVersion: requireUint256(payment.contract_version, "VERSION"),
    payerAddress,
    purchaseRef: requireBytes32(payment.purchase_ref, "PURCHASE_REF"),
    signature: requireSignature(payment.authorization_signature),
    tokenAddress: requireAddress(payment.token_contract_address, "TOKEN"),
    validUntil: requireUint256(payment.authorization_valid_until, "EXPIRATION"),
  };
}

export async function readTestUsdcAllowance(
  provider: Eip1193Provider,
  payment: ContractCreditPayment,
  connectedAddress: string,
  connectedChainId: number,
): Promise<bigint> {
  const snapshot = requirePayableTestnetCreditPayment(payment, connectedAddress, connectedChainId);
  const result = await provider.request({
    method: "eth_call",
    params: [{
      data: `0x${ERC20_ALLOWANCE_SELECTOR}${wordFromAddress(snapshot.payerAddress)}${wordFromAddress(snapshot.contractAddress)}`,
      from: snapshot.payerAddress,
      to: snapshot.tokenAddress,
    }, "latest"],
  });
  if (typeof result !== "string" || !/^0x[a-fA-F0-9]{64}$/.test(result)) {
    throw new Error("TESTNET_PAYMENT_ALLOWANCE_UNAVAILABLE");
  }
  return BigInt(result);
}

export async function approveExactTestUsdc(
  provider: Eip1193Provider,
  payment: ContractCreditPayment,
  connectedAddress: string,
  connectedChainId: number,
): Promise<void> {
  const snapshot = requirePayableTestnetCreditPayment(payment, connectedAddress, connectedChainId);
  const result = await provider.request({
    method: "eth_sendTransaction",
    params: [{
      data: `0x${ERC20_APPROVE_SELECTOR}${wordFromAddress(snapshot.contractAddress)}${wordFromUint(snapshot.amount)}`,
      from: snapshot.payerAddress,
      to: snapshot.tokenAddress,
      value: "0x0",
    }],
  });
  requireAcceptedRequest(result);
}

export function encodeTestCreditPaymentCall(
  payment: ContractCreditPayment,
  connectedAddress: string,
  connectedChainId: number,
): string {
  const snapshot = requirePayableTestnetCreditPayment(payment, connectedAddress, connectedChainId);
  const signatureBody = encodeDynamicBytes(snapshot.signature);
  return `0x${VAULT_PAY_SELECTOR}${snapshot.purchaseRef.slice(2)}`
    + `${wordFromAddress(snapshot.payerAddress)}${wordFromUint(snapshot.amount)}`
    + `${wordFromUint(snapshot.validUntil)}${wordFromUint(BigInt(BASE_SEPOLIA_CHAIN_ID))}`
    + `${wordFromAddress(snapshot.contractAddress)}${wordFromUint(snapshot.contractVersion)}`
    + `${wordFromUint(8n * 32n)}${signatureBody}`;
}

export async function payTestCreditPurchase(
  provider: Eip1193Provider,
  payment: ContractCreditPayment,
  connectedAddress: string,
  connectedChainId: number,
): Promise<void> {
  const snapshot = requirePayableTestnetCreditPayment(payment, connectedAddress, connectedChainId);
  const data = encodeTestCreditPaymentCall(payment, connectedAddress, connectedChainId);
  const result = await provider.request({
    method: "eth_sendTransaction",
    params: [{
      data,
      from: snapshot.payerAddress,
      to: snapshot.contractAddress,
      value: "0x0",
    }],
  });
  requireAcceptedRequest(result);
}

export function testnetPaymentErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "code" in error && error.code === 4001) {
    return "Cancelaste la accion en MetaMask. Puedes intentarlo de nuevo cuando quieras.";
  }
  if (error instanceof Error) {
    if (error.message === "TESTNET_PAYMENT_NETWORK_INVALID") {
      return "Cambia tu wallet a Base Sepolia para continuar.";
    }
    if (error.message === "TESTNET_PAYMENT_WALLET_MISMATCH") {
      return "La wallet conectada no coincide con la compra preparada. Inicia de nuevo desde Telegram.";
    }
    if (error.message === "TESTNET_PAYMENT_AUTHORIZATION_EXPIRED") {
      return "La autorizacion vencio. Inicia una compra nueva desde Telegram.";
    }
  }
  return "MetaMask no pudo completar esta accion de prueba. Revisa la wallet e intenta de nuevo.";
}
