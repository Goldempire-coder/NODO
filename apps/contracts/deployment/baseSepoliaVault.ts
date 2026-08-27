import { getAddress, zeroAddress, type Address, type Hex } from "viem";

export const BASE_SEPOLIA_VAULT_PROFILE = Object.freeze({
  networkName: "baseSepolia",
  networkLabel: "Base Sepolia",
  chainId: 84532,
  acceptedToken: getAddress("0x036CbD53842c5426634e7929541eC2318f3dCF7e"),
  contractVersion: 2n,
  expectedPaused: false,
});

export const OWNER_DEPLOY_APPROVAL_VALUE =
  "OWNER_APPROVED_BASE_SEPOLIA_VAULT_DEPLOY";

const PUBLIC_INPUT_ENV = Object.freeze({
  treasury: "NODO_BASE_SEPOLIA_VAULT_TREASURY",
  owner: "NODO_BASE_SEPOLIA_VAULT_OWNER",
  authorizedSigner: "NODO_BASE_SEPOLIA_VAULT_AUTHORIZED_SIGNER",
});

const OWNER_DEPLOY_APPROVAL_ENV = "NODO_BASE_SEPOLIA_VAULT_DEPLOY_APPROVAL";

type Environment = Readonly<Record<string, string | undefined>>;

export type BaseSepoliaPublicInputs = Readonly<{
  treasury: Address;
  owner: Address;
  authorizedSigner: Address;
}>;

export type BaseSepoliaVaultPlan = BaseSepoliaPublicInputs &
  Readonly<{
    networkName: string;
    networkLabel: string;
    chainId: number;
    acceptedToken: Address;
    contractVersion: bigint;
    expectedPaused: boolean;
  }>;

export type BaseSepoliaVaultInspection = Readonly<{
  address: Address | string;
  chainId: number;
  bytecode: Hex | undefined;
  contractVersion: bigint;
  acceptedToken: Address | string;
  treasury: Address | string;
  owner: Address | string;
  authorizedSigner: Address | string;
  paused: boolean;
}>;

function requirePublicAddress(environment: Environment, envName: string): Address {
  const rawValue = environment[envName]?.trim();
  if (!rawValue) {
    throw new Error(`MISSING_PUBLIC_DEPLOYMENT_ADDRESS:${envName}`);
  }

  let address: Address;
  try {
    address = getAddress(rawValue);
  } catch {
    throw new Error(`INVALID_PUBLIC_DEPLOYMENT_ADDRESS:${envName}`);
  }

  if (address === zeroAddress) {
    throw new Error(`ZERO_PUBLIC_DEPLOYMENT_ADDRESS:${envName}`);
  }
  return address;
}

export function readBaseSepoliaPublicInputs(
  environment: Environment,
): BaseSepoliaPublicInputs {
  return Object.freeze({
    treasury: requirePublicAddress(environment, PUBLIC_INPUT_ENV.treasury),
    owner: requirePublicAddress(environment, PUBLIC_INPUT_ENV.owner),
    authorizedSigner: requirePublicAddress(
      environment,
      PUBLIC_INPUT_ENV.authorizedSigner,
    ),
  });
}

export function buildBaseSepoliaVaultPlan(
  inputs: BaseSepoliaPublicInputs,
): BaseSepoliaVaultPlan {
  return Object.freeze({
    ...BASE_SEPOLIA_VAULT_PROFILE,
    ...inputs,
  });
}

export function assertOwnerDeployApproval(environment: Environment): void {
  if (
    environment[OWNER_DEPLOY_APPROVAL_ENV]?.trim() !==
    OWNER_DEPLOY_APPROVAL_VALUE
  ) {
    throw new Error("OWNER_DEPLOY_APPROVAL_REQUIRED");
  }
}

export function maskPublicAddress(value: Address | string): string {
  const address = getAddress(value);
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function formatBaseSepoliaVaultPlan(
  plan: BaseSepoliaVaultPlan,
  mode: "dry-run" | "deploy" = "dry-run",
): string {
  return [
    "52C2G-S0 Base Sepolia vault deployment plan",
    `mode: ${
      mode === "dry-run"
        ? "DRY_RUN_ONLY_NO_TRANSACTION"
        : "OWNER_APPROVED_DEPLOY_TRANSACTION_PENDING"
    }`,
    `network: ${plan.networkLabel}`,
    `chainId: ${plan.chainId}`,
    `acceptedToken: ${maskPublicAddress(plan.acceptedToken)}`,
    `contractVersion: ${plan.contractVersion}`,
    `treasury: ${maskPublicAddress(plan.treasury)}`,
    `owner: ${maskPublicAddress(plan.owner)}`,
    `authorizedSigner: ${maskPublicAddress(plan.authorizedSigner)}`,
    `expectedPaused: ${plan.expectedPaused}`,
    `ownerApprovalRequiredBeforeDeploy: ${mode === "dry-run"}`,
  ].join("\n");
}

function assertAddressMatch(
  actual: Address | string,
  expected: Address | string,
  errorCode: string,
): void {
  let normalizedActual: Address;
  try {
    normalizedActual = getAddress(actual);
  } catch {
    throw new Error(errorCode);
  }
  if (normalizedActual !== getAddress(expected)) {
    throw new Error(errorCode);
  }
}

export function assertVaultInspectionMatchesPlan(
  plan: BaseSepoliaVaultPlan,
  inspection: BaseSepoliaVaultInspection,
): void {
  if (!inspection.bytecode || inspection.bytecode === "0x") {
    throw new Error("DEPLOYED_BYTECODE_NOT_FOUND");
  }
  if (inspection.chainId !== plan.chainId) {
    throw new Error("DEPLOYED_CHAIN_MISMATCH");
  }
  if (inspection.contractVersion !== plan.contractVersion) {
    throw new Error("DEPLOYED_CONTRACT_VERSION_MISMATCH");
  }
  assertAddressMatch(
    inspection.acceptedToken,
    plan.acceptedToken,
    "DEPLOYED_ACCEPTED_TOKEN_MISMATCH",
  );
  assertAddressMatch(
    inspection.treasury,
    plan.treasury,
    "DEPLOYED_TREASURY_MISMATCH",
  );
  assertAddressMatch(inspection.owner, plan.owner, "DEPLOYED_OWNER_MISMATCH");
  assertAddressMatch(
    inspection.authorizedSigner,
    plan.authorizedSigner,
    "DEPLOYED_AUTHORIZED_SIGNER_MISMATCH",
  );
  if (inspection.paused !== plan.expectedPaused) {
    throw new Error("DEPLOYED_PAUSED_STATE_MISMATCH");
  }
}

export function safeDeploymentToolError(error: unknown): string {
  if (
    error instanceof Error &&
    /^[A-Z0-9_]+(?::[A-Z0-9_]+)?$/.test(error.message)
  ) {
    return error.message;
  }
  return "BASE_SEPOLIA_VAULT_TOOL_FAILED";
}
