import assert from "node:assert/strict";
import { describe, it } from "node:test";
import hre from "hardhat";
import { encodeFunctionData, getAddress, keccak256, parseUnits, stringToHex } from "viem";

const { viem, networkHelpers } = await hre.network.create();

const AUTHORIZATION_TYPES = {
  PaymentAuthorization: [
    { name: "purchaseRef", type: "bytes32" },
    { name: "payer", type: "address" },
    { name: "amount", type: "uint256" },
    { name: "validUntil", type: "uint256" },
    { name: "chainId", type: "uint256" },
    { name: "verifyingContract", type: "address" },
    { name: "contractVersion", type: "uint256" },
  ],
} as const;

const PAYMENT_RECEIVED_EVENT_TOPIC = keccak256(
  stringToHex(
    "NodoCreditPaymentReceived(bytes32,address,address,address,uint256,uint256,uint256,uint256)",
  ),
);

type Address = `0x${string}`;

type PaymentAuthorization = {
  purchaseRef: `0x${string}`;
  payer: Address;
  amount: bigint;
  validUntil: bigint;
  chainId: bigint;
  verifyingContract: Address;
  contractVersion: bigint;
};

function purchaseRef(label: string): `0x${string}` {
  return keccak256(stringToHex(`nodo-52a1-${label}`));
}

async function deployVault(label = "default") {
  const [owner, authorizedSigner, payer, treasury, other, newSigner] = await viem.getWalletClients();
  const publicClient = await viem.getPublicClient();
  const chainId = BigInt(await publicClient.getChainId());

  const token = await viem.deployContract("MockUSDC");
  const amount = parseUnits("100", 6);
  await token.write.mint([payer.account.address, amount * 10n]);

  const vault = await viem.deployContract("NODOCreditPaymentVaultSigned", [
    token.address,
    treasury.account.address,
    owner.account.address,
    authorizedSigner.account.address,
  ]);
  await token.write.approve([vault.address, amount * 10n], { account: payer.account });

  const validUntil = BigInt(await networkHelpers.time.latest()) + 3600n;
  const authorization: PaymentAuthorization = {
    purchaseRef: purchaseRef(label),
    payer: payer.account.address,
    amount,
    validUntil,
    chainId,
    verifyingContract: vault.address,
    contractVersion: 2n,
  };

  async function signAuthorization(
    override: Partial<PaymentAuthorization> = {},
    signer = authorizedSigner,
  ) {
    const message = { ...authorization, ...override };
    return signer.signTypedData({
      account: signer.account,
      domain: {
        name: "NODOCreditPaymentVaultSigned",
        version: "2",
        chainId: Number(message.chainId),
        verifyingContract: message.verifyingContract,
      },
      types: AUTHORIZATION_TYPES,
      primaryType: "PaymentAuthorization",
      message,
    });
  }

  return {
    amount,
    authorization,
    authorizedSigner,
    chainId,
    newSigner,
    other,
    owner,
    payer,
    publicClient,
    signAuthorization,
    token,
    treasury,
    vault,
  };
}

async function expectRevert(action: Promise<unknown>, expected: string) {
  await assert.rejects(action, (error: unknown) => {
    assert.match(String(error), new RegExp(expected));
    return true;
  });
}

async function expectConstructorRevert(action: Promise<unknown>) {
  await assert.rejects(action);
}

describe("NODOCreditPaymentVaultSigned", function () {
  it("rejects zero constructor addresses", async function () {
    const [owner, authorizedSigner, , treasury] = await viem.getWalletClients();
    const token = await viem.deployContract("MockUSDC");
    const zeroAddress = "0x0000000000000000000000000000000000000000";

    await expectConstructorRevert(
      viem.deployContract("NODOCreditPaymentVaultSigned", [
        zeroAddress,
        treasury.account.address,
        owner.account.address,
        authorizedSigner.account.address,
      ]),
    );
    await expectConstructorRevert(
      viem.deployContract("NODOCreditPaymentVaultSigned", [
        token.address,
        zeroAddress,
        owner.account.address,
        authorizedSigner.account.address,
      ]),
    );
    await expectConstructorRevert(
      viem.deployContract("NODOCreditPaymentVaultSigned", [
        token.address,
        treasury.account.address,
        zeroAddress,
        authorizedSigner.account.address,
      ]),
    );
    await expectConstructorRevert(
      viem.deployContract("NODOCreditPaymentVaultSigned", [
        token.address,
        treasury.account.address,
        owner.account.address,
        zeroAddress,
      ]),
    );
  });

  it("accepts an exact NODO-signed authorization and sends USDC to treasury", async function () {
    const { amount, authorization, payer, signAuthorization, token, treasury, vault } =
      await deployVault("valid-payment");
    const signature = await signAuthorization();

    await viem.assertions.emitWithArgs(
      vault.write.pay([authorization, signature], { account: payer.account }),
      vault,
      "NodoCreditPaymentReceived",
      [
        authorization.purchaseRef,
        payer.account.address,
        token.address,
        treasury.account.address,
        amount,
        authorization.chainId,
        2n,
        authorization.validUntil,
      ],
    );

    assert.equal(await token.read.balanceOf([treasury.account.address]), amount);
    assert.equal(await vault.read.usedPurchaseRefs([authorization.purchaseRef]), true);
  });

  it("rejects tampered amount, wrong payer, wrong chain, wrong contract, wrong version, expired auth, and replay", async function () {
    const { amount, authorization, other, payer, signAuthorization, vault } =
      await deployVault("negative-guards");

    await expectRevert(
      vault.write.pay([{ ...authorization, amount: amount - 1n }, await signAuthorization()], {
        account: payer.account,
      }),
      "InvalidAuthorizationSignature",
    );

    await expectRevert(
      vault.write.pay([authorization, await signAuthorization()], { account: other.account }),
      "PayerMismatch",
    );

    await expectRevert(
      vault.write.pay(
        [
          { ...authorization, chainId: authorization.chainId + 1n },
          await signAuthorization({ chainId: authorization.chainId + 1n }),
        ],
        { account: payer.account },
      ),
      "ChainMismatch",
    );

    await expectRevert(
      vault.write.pay(
        [
          { ...authorization, verifyingContract: other.account.address },
          await signAuthorization({ verifyingContract: other.account.address }),
        ],
        { account: payer.account },
      ),
      "ContractMismatch",
    );

    await expectRevert(
      vault.write.pay(
        [
          { ...authorization, contractVersion: 3n },
          await signAuthorization({ contractVersion: 3n }),
        ],
        { account: payer.account },
      ),
      "VersionMismatch",
    );

    const expiredUntil = BigInt(await networkHelpers.time.latest()) - 1n;
    await expectRevert(
      vault.write.pay(
        [
          { ...authorization, validUntil: expiredUntil },
          await signAuthorization({ validUntil: expiredUntil }),
        ],
        { account: payer.account },
      ),
      "AuthorizationExpired",
    );

    const validSignature = await signAuthorization();
    await vault.write.pay([authorization, validSignature], { account: payer.account });
    await expectRevert(
      vault.write.pay([authorization, validSignature], { account: payer.account }),
      "PurchaseRefAlreadyUsed",
    );
  });

  it("accepts before validUntil and rejects at or after the exclusive boundary", async function () {
    const before = await deployVault("before-expiry");
    await networkHelpers.time.setNextBlockTimestamp(Number(before.authorization.validUntil - 1n));
    await before.vault.write.pay(
      [before.authorization, await before.signAuthorization()],
      { account: before.payer.account },
    );
    assert.equal(
      await before.vault.read.usedPurchaseRefs([before.authorization.purchaseRef]),
      true,
    );

    const atBoundary = await deployVault("at-expiry");
    await networkHelpers.time.setNextBlockTimestamp(Number(atBoundary.authorization.validUntil));
    await expectRevert(
      atBoundary.vault.write.pay(
        [atBoundary.authorization, await atBoundary.signAuthorization()],
        { account: atBoundary.payer.account },
      ),
      "AuthorizationExpired",
    );

    const afterBoundary = await deployVault("after-expiry");
    await networkHelpers.time.setNextBlockTimestamp(
      Number(afterBoundary.authorization.validUntil + 1n),
    );
    await expectRevert(
      afterBoundary.vault.write.pay(
        [afterBoundary.authorization, await afterBoundary.signAuthorization()],
        { account: afterBoundary.payer.account },
      ),
      "AuthorizationExpired",
    );
  });

  it("rejects empty purchase refs, zero amount, bad signatures, and wrong signer", async function () {
    const { authorization, newSigner, payer, signAuthorization, vault } =
      await deployVault("signature-guards");

    await expectRevert(
      vault.write.pay(
        [
          { ...authorization, purchaseRef: "0x0000000000000000000000000000000000000000000000000000000000000000" },
          await signAuthorization({
            purchaseRef: "0x0000000000000000000000000000000000000000000000000000000000000000",
          }),
        ],
        { account: payer.account },
      ),
      "ZeroPurchaseRef",
    );

    await expectRevert(
      vault.write.pay(
        [{ ...authorization, amount: 0n }, await signAuthorization({ amount: 0n })],
        { account: payer.account },
      ),
      "ZeroAmount",
    );

    await expectRevert(
      vault.write.pay([authorization, "0x1234"], { account: payer.account }),
      "InvalidAuthorizationSignature",
    );

    await expectRevert(
      vault.write.pay([authorization, await signAuthorization({}, newSigner)], {
        account: payer.account,
      }),
      "InvalidAuthorizationSignature",
    );
  });

  it("pauses, unpauses, rotates signer, and disables ownership renounce", async function () {
    const {
      authorization,
      newSigner,
      owner,
      payer,
      signAuthorization,
      vault,
    } = await deployVault("admin-controls");

    const originalSignature = await signAuthorization();
    await vault.write.pause({ account: owner.account });
    await expectRevert(
      vault.write.pay([authorization, originalSignature], { account: payer.account }),
      "EnforcedPause",
    );

    await vault.write.unpause({ account: owner.account });
    await expectRevert(
      vault.write.setAuthorizedSigner([newSigner.account.address], { account: payer.account }),
      "OwnableUnauthorizedAccount",
    );
    await vault.write.setAuthorizedSigner([newSigner.account.address], { account: owner.account });

    await expectRevert(
      vault.write.pay([authorization, originalSignature], { account: payer.account }),
      "InvalidAuthorizationSignature",
    );

    const rotatedSignature = await signAuthorization({}, newSigner);
    await vault.write.pay([authorization, rotatedSignature], { account: payer.account });

    await expectRevert(vault.write.renounceOwnership({ account: owner.account }), "OwnershipRenounceDisabled");
  });

  it("requires two-step ownership transfer", async function () {
    const { other, owner, vault } = await deployVault("ownership-transfer");

    await vault.write.transferOwnership([other.account.address], { account: owner.account });
    assert.equal(getAddress(await vault.read.owner()), getAddress(owner.account.address));
    assert.equal(getAddress(await vault.read.pendingOwner()), getAddress(other.account.address));

    await vault.write.acceptOwnership({ account: other.account });
    assert.equal(getAddress(await vault.read.owner()), getAddress(other.account.address));
  });

  it("sweeps trapped ERC20 tokens only to treasury and never consumes a purchase ref", async function () {
    const { amount, authorization, owner, publicClient, token, treasury, vault } =
      await deployVault("sweep");

    await token.write.mint([vault.address, amount]);
    const sweepTransaction = vault.write.sweepToTreasury([token.address], {
      account: owner.account,
    });
    await viem.assertions.emitWithArgs(
      sweepTransaction,
      vault,
      "NodoVaultSweep",
      [token.address, treasury.account.address, amount],
    );
    const receipt = await publicClient.waitForTransactionReceipt({
      hash: await sweepTransaction,
    });

    assert.equal(await token.read.balanceOf([vault.address]), 0n);
    assert.equal(await token.read.balanceOf([treasury.account.address]), amount);
    assert.equal(await vault.read.usedPurchaseRefs([authorization.purchaseRef]), false);
    assert.equal(
      receipt.logs.some((log) => log.topics[0] === PAYMENT_RECEIVED_EVENT_TOPIC),
      false,
    );
  });

  it("restricts sweep to owner and rejects an empty token balance", async function () {
    const { other, owner, token, vault } = await deployVault("sweep-guards");

    await expectRevert(
      vault.write.sweepToTreasury([token.address], { account: other.account }),
      "OwnableUnauthorizedAccount",
    );
    await expectRevert(
      vault.write.sweepToTreasury([token.address], { account: owner.account }),
      "ZeroAmount",
    );
  });

  it("does not consume purchaseRef when allowance is insufficient", async function () {
    const { amount, authorization, payer, signAuthorization, token, treasury, vault } =
      await deployVault("insufficient-allowance");

    await token.write.approve([vault.address, amount - 1n], { account: payer.account });
    await expectRevert(
      vault.write.pay([authorization, await signAuthorization()], { account: payer.account }),
      "ERC20InsufficientAllowance",
    );

    assert.equal(await vault.read.usedPurchaseRefs([authorization.purchaseRef]), false);
    assert.equal(await token.read.balanceOf([treasury.account.address]), 0n);
  });

  it("does not consume purchaseRef when payer balance is insufficient", async function () {
    const { amount, authorization, payer, signAuthorization, token, treasury, vault } =
      await deployVault("insufficient-balance");
    const amountAboveBalance = amount * 11n;
    const oversizedAuthorization = {
      ...authorization,
      amount: amountAboveBalance,
    };

    await token.write.approve([vault.address, amountAboveBalance], { account: payer.account });
    await expectRevert(
      vault.write.pay(
        [oversizedAuthorization, await signAuthorization({ amount: amountAboveBalance })],
        { account: payer.account },
      ),
      "ERC20InsufficientBalance",
    );

    assert.equal(await vault.read.usedPurchaseRefs([authorization.purchaseRef]), false);
    assert.equal(await token.read.balanceOf([treasury.account.address]), 0n);
  });

  it("reverts failed transfers without consuming the purchase ref", async function () {
    const [owner, authorizedSigner, payer, treasury] = await viem.getWalletClients();
    const publicClient = await viem.getPublicClient();
    const chainId = BigInt(await publicClient.getChainId());
    const token = await viem.deployContract("FalseReturnToken");
    const amount = parseUnits("100", 6);
    await token.write.mint([payer.account.address, amount]);

    const vault = await viem.deployContract("NODOCreditPaymentVaultSigned", [
      token.address,
      treasury.account.address,
      owner.account.address,
      authorizedSigner.account.address,
    ]);
    await token.write.approve([vault.address, amount], { account: payer.account });

    const authorization: PaymentAuthorization = {
      purchaseRef: purchaseRef("failed-transfer"),
      payer: payer.account.address,
      amount,
      validUntil: BigInt(await networkHelpers.time.latest()) + 3600n,
      chainId,
      verifyingContract: vault.address,
      contractVersion: 2n,
    };

    const signature = await authorizedSigner.signTypedData({
      account: authorizedSigner.account,
      domain: {
        name: "NODOCreditPaymentVaultSigned",
        version: "2",
        chainId: Number(chainId),
        verifyingContract: vault.address,
      },
      types: AUTHORIZATION_TYPES,
      primaryType: "PaymentAuthorization",
      message: authorization,
    });

    await expectRevert(
      vault.write.pay([authorization, signature], { account: payer.account }),
      "SafeERC20FailedOperation",
    );
    assert.equal(await vault.read.usedPurchaseRefs([authorization.purchaseRef]), false);
  });

  it("rejects native ETH transfers and unknown calldata with value", async function () {
    const { owner, publicClient, vault } = await deployVault("native-reject");

    await expectRevert(
      owner.sendTransaction({ to: vault.address, value: 1n }),
      "NativePaymentNotAccepted",
    );

    await expectRevert(
      owner.sendTransaction({
        data: encodeFunctionData({
          abi: [
            {
              inputs: [],
              name: "missingFunction",
              outputs: [],
              stateMutability: "payable",
              type: "function",
            },
          ],
          functionName: "missingFunction",
        }),
        to: vault.address,
        value: 1n,
      }),
      "NativePaymentNotAccepted",
    );

    assert.equal(await publicClient.getBalance({ address: vault.address }), 0n);
  });
});
