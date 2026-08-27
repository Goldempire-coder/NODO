import {
  buildBaseSepoliaVaultPlan,
  formatBaseSepoliaVaultPlan,
  readBaseSepoliaPublicInputs,
  safeDeploymentToolError,
} from "../deployment/baseSepoliaVault.ts";

try {
  const plan = buildBaseSepoliaVaultPlan(
    readBaseSepoliaPublicInputs(process.env),
  );
  process.stdout.write(`${formatBaseSepoliaVaultPlan(plan)}\n`);
} catch (error) {
  process.stderr.write(`${safeDeploymentToolError(error)}\n`);
  process.exitCode = 1;
}
