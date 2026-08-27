import { network } from "hardhat";

import {
  BASE_SEPOLIA_VAULT_PROFILE,
  assertOwnerDeployApproval,
  assertVaultInspectionMatchesPlan,
  buildBaseSepoliaVaultPlan,
  formatBaseSepoliaVaultPlan,
  readBaseSepoliaPublicInputs,
  safeDeploymentToolError,
} from "../deployment/baseSepoliaVault.ts";

async function deploy(): Promise<void> {
  const plan = buildBaseSepoliaVaultPlan(
    readBaseSepoliaPublicInputs(process.env),
  );
  assertOwnerDeployApproval(process.env);

  const { viem, networkName } = await network.create();
  if (networkName !== BASE_SEPOLIA_VAULT_PROFILE.networkName) {
    throw new Error("DEPLOY_NETWORK_NAME_MISMATCH");
  }

  const publicClient = await viem.getPublicClient();
  if ((await publicClient.getChainId()) !== plan.chainId) {
    throw new Error("DEPLOY_CHAIN_ID_MISMATCH");
  }

  const [walletClient, ...unexpectedWalletClients] =
    await viem.getWalletClients();
  if (!walletClient || unexpectedWalletClients.length > 0) {
    throw new Error("DEPLOYER_ACCOUNT_CONFIGURATION_INVALID");
  }

  process.stdout.write(`${formatBaseSepoliaVaultPlan(plan, "deploy")}\n`);
  process.stdout.write("ownerApproval: CONFIRMED\n");
  process.stdout.write("deploymentStatus: SUBMITTING_BASE_SEPOLIA_TRANSACTION\n");

  const vault = await viem.deployContract(
    "NODOCreditPaymentVaultSigned",
    [plan.acceptedToken, plan.treasury, plan.owner, plan.authorizedSigner],
    {
      confirmations: 2,
      client: {
        public: publicClient,
        wallet: walletClient,
      },
    },
  );

  process.stdout.write("deploymentStatus: MINED_PENDING_VERIFICATION\n");
  process.stdout.write(`vaultAddress: ${vault.address}\n`);

  assertVaultInspectionMatchesPlan(plan, {
    address: vault.address,
    chainId: await publicClient.getChainId(),
    bytecode: await publicClient.getBytecode({ address: vault.address }),
    contractVersion: await vault.read.CONTRACT_VERSION(),
    acceptedToken: await vault.read.acceptedToken(),
    treasury: await vault.read.treasury(),
    owner: await vault.read.owner(),
    authorizedSigner: await vault.read.authorizedSigner(),
    paused: await vault.read.paused(),
  });

  process.stdout.write("deploymentStatus: VERIFIED\n");
}

deploy().catch((error: unknown) => {
  process.stderr.write(`${safeDeploymentToolError(error)}\n`);
  process.exitCode = 1;
});
