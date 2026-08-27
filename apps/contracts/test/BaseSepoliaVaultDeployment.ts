import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";

import {
  BASE_SEPOLIA_VAULT_PROFILE,
  OWNER_DEPLOY_APPROVAL_VALUE,
  assertOwnerDeployApproval,
  assertVaultInspectionMatchesPlan,
  buildBaseSepoliaVaultPlan,
  formatBaseSepoliaVaultPlan,
  readBaseSepoliaPublicInputs,
  safeDeploymentToolError,
} from "../deployment/baseSepoliaVault.ts";

const TREASURY = "0x1111111111111111111111111111111111111111";
const OWNER = "0x2222222222222222222222222222222222222222";
const AUTHORIZED_SIGNER = "0x3333333333333333333333333333333333333333";
const VAULT = "0x4444444444444444444444444444444444444444";
const { viem } = await hre.network.create();

function validEnvironment(): NodeJS.ProcessEnv {
  return {
    NODO_BASE_SEPOLIA_VAULT_TREASURY: TREASURY,
    NODO_BASE_SEPOLIA_VAULT_OWNER: OWNER,
    NODO_BASE_SEPOLIA_VAULT_AUTHORIZED_SIGNER: AUTHORIZED_SIGNER,
  };
}

describe("Base Sepolia vault deployment tooling", function () {
  it("pins the official testnet profile and V2 contract shape", function () {
    assert.equal(BASE_SEPOLIA_VAULT_PROFILE.chainId, 84532);
    assert.equal(BASE_SEPOLIA_VAULT_PROFILE.networkName, "baseSepolia");
    assert.equal(
      BASE_SEPOLIA_VAULT_PROFILE.acceptedToken,
      "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    );
    assert.equal(BASE_SEPOLIA_VAULT_PROFILE.contractVersion, 2n);
    assert.equal(BASE_SEPOLIA_VAULT_PROFILE.expectedPaused, false);
  });

  it("reads and validates only the three public deployment inputs", function () {
    const inputs = readBaseSepoliaPublicInputs(validEnvironment());

    assert.deepEqual(inputs, {
      treasury: TREASURY,
      owner: OWNER,
      authorizedSigner: AUTHORIZED_SIGNER,
    });
  });

  it("rejects missing, invalid, and zero public addresses", function () {
    assert.throws(
      () => readBaseSepoliaPublicInputs({}),
      /MISSING_PUBLIC_DEPLOYMENT_ADDRESS/,
    );
    assert.throws(
      () =>
        readBaseSepoliaPublicInputs({
          ...validEnvironment(),
          NODO_BASE_SEPOLIA_VAULT_TREASURY: "not-an-address",
        }),
      /INVALID_PUBLIC_DEPLOYMENT_ADDRESS/,
    );
    assert.throws(
      () =>
        readBaseSepoliaPublicInputs({
          ...validEnvironment(),
          NODO_BASE_SEPOLIA_VAULT_OWNER:
            "0x0000000000000000000000000000000000000000",
        }),
      /ZERO_PUBLIC_DEPLOYMENT_ADDRESS/,
    );
  });

  it("keeps the offline plan masked and free of secret input fields", function () {
    const plan = buildBaseSepoliaVaultPlan(
      readBaseSepoliaPublicInputs(validEnvironment()),
    );
    const output = formatBaseSepoliaVaultPlan(plan);

    assert.match(output, /DRY_RUN_ONLY_NO_TRANSACTION/);
    assert.match(output, /0x1111\.\.\.1111/);
    assert.doesNotMatch(output, new RegExp(TREASURY, "i"));
    assert.doesNotMatch(output, /private.?key|mnemonic|seed|rpc.?url/i);
  });

  it("never labels an approved deploy as an offline dry run", function () {
    const plan = buildBaseSepoliaVaultPlan(
      readBaseSepoliaPublicInputs(validEnvironment()),
    );
    const output = formatBaseSepoliaVaultPlan(plan, "deploy");

    assert.match(output, /OWNER_APPROVED_DEPLOY_TRANSACTION_PENDING/);
    assert.doesNotMatch(output, /DRY_RUN_ONLY_NO_TRANSACTION/);
  });

  it("requires an exact Owner approval phrase before deployment", function () {
    assert.throws(() => assertOwnerDeployApproval({}), /OWNER_DEPLOY_APPROVAL_REQUIRED/);
    assert.throws(
      () =>
        assertOwnerDeployApproval({
          NODO_BASE_SEPOLIA_VAULT_DEPLOY_APPROVAL: "yes",
        }),
      /OWNER_DEPLOY_APPROVAL_REQUIRED/,
    );
    assert.doesNotThrow(() =>
      assertOwnerDeployApproval({
        NODO_BASE_SEPOLIA_VAULT_DEPLOY_APPROVAL: OWNER_DEPLOY_APPROVAL_VALUE,
      }),
    );
  });

  it("keeps unexpected deployment errors neutral", function () {
    assert.equal(
      safeDeploymentToolError(new Error("DEPLOY_CHAIN_ID_MISMATCH")),
      "DEPLOY_CHAIN_ID_MISMATCH",
    );
    assert.equal(
      safeDeploymentToolError(new Error("provider failed at a private endpoint")),
      "BASE_SEPOLIA_VAULT_TOOL_FAILED",
    );
  });

  it("accepts a complete post-deploy inspection", function () {
    const plan = buildBaseSepoliaVaultPlan(
      readBaseSepoliaPublicInputs(validEnvironment()),
    );

    assert.doesNotThrow(() =>
      assertVaultInspectionMatchesPlan(plan, {
        address: VAULT,
        chainId: 84532,
        bytecode: "0x6001600055",
        contractVersion: 2n,
        acceptedToken: BASE_SEPOLIA_VAULT_PROFILE.acceptedToken,
        treasury: TREASURY,
        owner: OWNER,
        authorizedSigner: AUTHORIZED_SIGNER,
        paused: false,
      }),
    );
  });

  it("verifies all required fields on a locally deployed V2 vault", async function () {
    const [owner, authorizedSigner, treasury] = await viem.getWalletClients();
    const publicClient = await viem.getPublicClient();
    const plan = {
      ...buildBaseSepoliaVaultPlan({
        treasury: treasury.account.address,
        owner: owner.account.address,
        authorizedSigner: authorizedSigner.account.address,
      }),
      chainId: await publicClient.getChainId(),
    };
    const vault = await viem.deployContract("NODOCreditPaymentVaultSigned", [
      plan.acceptedToken,
      plan.treasury,
      plan.owner,
      plan.authorizedSigner,
    ]);
    const inspection = {
      address: vault.address,
      chainId: plan.chainId,
      bytecode: await publicClient.getBytecode({ address: vault.address }),
      contractVersion: await vault.read.CONTRACT_VERSION(),
      acceptedToken: await vault.read.acceptedToken(),
      treasury: await vault.read.treasury(),
      owner: await vault.read.owner(),
      authorizedSigner: await vault.read.authorizedSigner(),
      paused: await vault.read.paused(),
    };

    assert.doesNotThrow(() =>
      assertVaultInspectionMatchesPlan(plan, inspection),
    );
  });

  it("fails closed on missing bytecode or any deployment mismatch", function () {
    const plan = buildBaseSepoliaVaultPlan(
      readBaseSepoliaPublicInputs(validEnvironment()),
    );
    const inspection = {
      address: VAULT,
      chainId: 84532,
      bytecode: "0x6001600055" as const,
      contractVersion: 2n,
      acceptedToken: BASE_SEPOLIA_VAULT_PROFILE.acceptedToken,
      treasury: TREASURY,
      owner: OWNER,
      authorizedSigner: AUTHORIZED_SIGNER,
      paused: false,
    };

    assert.throws(
      () => assertVaultInspectionMatchesPlan(plan, { ...inspection, bytecode: "0x" }),
      /DEPLOYED_BYTECODE_NOT_FOUND/,
    );
    assert.throws(
      () => assertVaultInspectionMatchesPlan(plan, { ...inspection, chainId: 8453 }),
      /DEPLOYED_CHAIN_MISMATCH/,
    );
    assert.throws(
      () =>
        assertVaultInspectionMatchesPlan(plan, {
          ...inspection,
          contractVersion: 1n,
        }),
      /DEPLOYED_CONTRACT_VERSION_MISMATCH/,
    );
    assert.throws(
      () =>
        assertVaultInspectionMatchesPlan(plan, {
          ...inspection,
          acceptedToken: TREASURY,
        }),
      /DEPLOYED_ACCEPTED_TOKEN_MISMATCH/,
    );
    assert.throws(
      () =>
        assertVaultInspectionMatchesPlan(plan, {
          ...inspection,
          treasury: OWNER,
        }),
      /DEPLOYED_TREASURY_MISMATCH/,
    );
    assert.throws(
      () =>
        assertVaultInspectionMatchesPlan(plan, {
          ...inspection,
          owner: TREASURY,
        }),
      /DEPLOYED_OWNER_MISMATCH/,
    );
    assert.throws(
      () =>
        assertVaultInspectionMatchesPlan(plan, {
          ...inspection,
          authorizedSigner: TREASURY,
        }),
      /DEPLOYED_AUTHORIZED_SIGNER_MISMATCH/,
    );
    assert.throws(
      () => assertVaultInspectionMatchesPlan(plan, { ...inspection, paused: true }),
      /DEPLOYED_PAUSED_STATE_MISMATCH/,
    );
  });
});
