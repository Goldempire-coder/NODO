/* Local, fake-data regression checks. No browser, wallet, SDK, or network calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const Module = require("node:module");

for (const key of Object.keys(process.env)) delete process.env[key];
let blocked = 0;
const originalLoad = Module._load;
const forbidden = new Set(["net", "http", "https", "http2", "tls", "dgram", "dns", "child_process"]);
function deny() {
  blocked += 1;
  throw new Error("ISOLATED_TEST_CONNECTION_BLOCKED");
}
Module._load = function (id, ...args) {
  if (forbidden.has(id.replace(/^node:/, "").split("/")[0])) return deny();
  return originalLoad.call(this, id, ...args);
};
globalThis.fetch = deny;
const ts = require(process.argv[2] || "../apps/web/node_modules/typescript");
const root = path.resolve(__dirname, "..");
const helperPath = "apps/web/src/lib/wallet/metamaskHandoff.ts";
const envPath = "apps/web/src/lib/env.ts";
const themePath = "apps/web/src/theme/telegramTheme.ts";
const allowedFiles = new Set([helperPath, envPath, themePath, "apps/web/next.config.mjs"]);
const token = "x".repeat(43);
const stage = "https://nodo-staging.pages.dev";
const official = "https://nodo.example";
let passed = 0;

function fixture(environment = "production", allowlist, origin = official, telegramMode = "ok", nodeEnv = "production") {
  const warnings = [];
  const links = [];
  const navigations = [];
  const env = { NODE_ENV: nodeEnv, NEXT_PUBLIC_APP_ENV: environment };
  if (allowlist !== undefined) env.NEXT_PUBLIC_WALLET_ALLOWLIST = allowlist;
  const window = {
    location: { origin, assign: (url) => navigations.push(url) },
    Telegram: telegramMode === "absent" ? undefined : {
      WebApp: { openLink: (url) => {
        if (telegramMode === "throws") throw new Error("FAKE_TELEGRAM_ERROR");
        links.push(url);
      } }
    }
  };
  const context = vm.createContext({
    URL, URLSearchParams, window, process: { env },
    console: { warn: (...args) => warnings.push(args) }, fetch: deny
  });
  const cache = new Map();
  function load(relative) {
    assert.ok(allowedFiles.has(relative), "MODULE_NOT_AUTHORIZED");
    if (cache.has(relative)) return cache.get(relative).exports;
    const module = { exports: {} };
    cache.set(relative, module);
    const result = ts.transpileModule(fs.readFileSync(path.join(root, relative), "utf8"), {
      fileName: relative.replace(/\.mjs$/, ".ts"), reportDiagnostics: true,
      compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS }
    });
    assert.equal((result.diagnostics || []).filter((d) => d.category === ts.DiagnosticCategory.Error).length, 0);
    const compiled = vm.runInContext(`(function(require, module, exports) {${result.outputText}\n})`, context, { timeout: 1000 });
    compiled((id) => {
      if (id === "../env") return load(envPath);
      if (id === "../../theme/telegramTheme") return load(themePath);
      return deny();
    }, module, module.exports);
    return module.exports;
  }
  return { helper: load(helperPath), load, warnings, links, navigations, context };
}

function check(name, fn) {
  try {
    fn();
    assert.equal(blocked, 0);
    passed += 1;
    console.log(`PASS ${name}`);
  } catch {
    console.error(`FAIL ${name}; stopped; passed=${passed}; blocked=${blocked}`);
    process.exit(1);
  }
}

function accepted(f, origin) {
  const host = new URL(origin).host;
  assert.equal(f.helper.buildMetaMaskWalletProbeDeeplink(origin), `https://link.metamask.io/dapp/${host}/business/wallet-probe/`);
  assert.equal(f.helper.buildMetaMaskCreditHandoffDeeplink(origin, token), `https://link.metamask.io/dapp/${host}/business/credit-payment/handoff/${token}/`);
  assert.equal(f.warnings.length, 0);
}

function rejected(f, origin) {
  for (const [invoke, code] of [
    [() => f.helper.buildMetaMaskWalletProbeDeeplink(origin), "WALLET_PROBE_ORIGIN_INVALID"],
    [() => f.helper.buildMetaMaskCreditHandoffDeeplink(origin, token), "CREDIT_HANDOFF_ORIGIN_INVALID"]
  ]) {
    assert.throws(invoke, (error) => error.code === code && error.message === "No se puede abrir MetaMask desde este sitio. Contacta a Soporte NODO.");
    assert.equal(JSON.stringify(f.warnings.at(-1)), JSON.stringify([code]));
  }
  assert.equal(f.links.length + f.navigations.length, 0);
}

check("explicit-production-origin-both-routes", () => accepted(fixture("production", official), official));
for (const environment of ["local", "dev", "development", "staging", "test", " StAgInG "]) {
  check(`default-staging-${environment.trim()}`, () => accepted(fixture(environment), stage));
}
check("next-dev-without-app-env", () => accepted(fixture("", undefined, stage, "ok", "development"), stage));
for (const environment of ["production", " Production ", "", "unknown"]) {
  check(`deny-missing-list-${environment.trim() || "empty"}`, () => rejected(fixture(environment), stage));
}
check("blank-production-list", () => rejected(fixture("production", "  "), official));
check("explicit-list-replaces-staging-default", () => rejected(fixture("staging", official), stage));
check("csv-normalizes-case-port-and-trailing-slash", () => accepted(fixture("production", "https://other.example, HTTPS://NODO.EXAMPLE:443/ "), official));
check("exact-nondefault-port", () => accepted(fixture("production", "https://nodo.example:8443"), "https://nodo.example:8443"));
for (const origin of [
  "https://other.example", "https://sub.nodo.example", "https://nodo.example.evil.example",
  "https://nodo.example:8443", "https://nodo.example@evil.example", "https://user:private@nodo.example",
  `${official}/private`, `${official}?private=value`, `${official}#private`, `${official}?`, `${official}#`,
  "https://nodo.example\\private", "https://no\tdo.example", "javascript:private", "not-a-url", "null",
  `${official}/private/..`, `${official}/%2e`, "https:nodo.example", "https:/nodo.example"
]) {
  check(`reject-origin-${passed}`, () => rejected(fixture("production", official), origin));
}
for (const invalid of [
  "*", "https://*.example", "http://nodo.example", "https://user:private@nodo.example",
  `${official}/private`, `${official}?private=value`, `${official}#private`, `${official}?`,
  "https://nodo.example\\", "https://no\tdo.example", "not-a-url", `${official},`,
  `${official},https://other.example/private`, `${official}/private/..`, "https:nodo.example"
]) {
  check(`malformed-list-fails-closed-${passed}`, () => rejected(fixture("production", invalid), official));
}
for (const origin of [stage, "https://preview.nodo-staging.pages.dev"]) {
  check(`no-production-staging-even-explicit-${passed}`, () => rejected(fixture("production", origin), origin));
}
for (const origin of ["http://localhost:3000", "http://127.0.0.1:3000", "http://[::1]:3000"]) {
  check(`local-http-${passed}`, () => accepted(fixture("local"), origin));
  check(`no-production-http-${passed}`, () => rejected(fixture("production", origin), origin));
}
check("unknown-env-explicit-https-only", () => accepted(fixture("qa", official), official));
check("invalid-token-remains-blocked-without-private-logging", () => {
  const f = fixture("production", official);
  assert.throws(() => f.helper.buildMetaMaskCreditHandoffDeeplink(official, "private?"), /CREDIT_HANDOFF_TOKEN_INVALID/);
  assert.equal(f.warnings.length, 0);
});
for (const mode of ["ok", "absent", "throws"]) {
  check(`navigation-only-mocked-${mode}`, () => {
    const f = fixture("production", official, official, mode);
    f.helper.openMetaMaskCreditHandoff(token);
    f.helper.openMetaMaskWalletProbe();
    assert.equal(f.links.length, mode === "ok" ? 2 : 0);
    assert.equal(f.navigations.length, mode === "ok" ? 0 : 2);
    assert.equal(f.warnings.length, 0);
  });
}
check("denied-launch-never-navigates", () => {
  const f = fixture("production");
  assert.throws(() => f.helper.openMetaMaskCreditHandoff(token), (error) => error.code === "CREDIT_HANDOFF_ORIGIN_INVALID");
  assert.throws(() => f.helper.openMetaMaskWalletProbe(), (error) => error.code === "WALLET_PROBE_ORIGIN_INVALID");
  assert.equal(f.links.length + f.navigations.length, 0);
  assert.equal(JSON.stringify(f.warnings), JSON.stringify([["CREDIT_HANDOFF_ORIGIN_INVALID"], ["WALLET_PROBE_ORIGIN_INVALID"]]));
});
check("server-render-does-not-launch", () => {
  const f = fixture();
  delete f.context.window;
  f.helper.openMetaMaskCreditHandoff(token);
  f.helper.openMetaMaskWalletProbe();
  assert.equal(f.warnings.length + f.links.length + f.navigations.length, 0);
});
check("public-env-and-next-config-wire-list", () => {
  const f = fixture("production", official);
  assert.equal(f.load(envPath).getPublicEnv().NEXT_PUBLIC_WALLET_ALLOWLIST, official);
  assert.equal(f.load("apps/web/next.config.mjs").default.env.NEXT_PUBLIC_WALLET_ALLOWLIST, official);
});
console.log(`WALLET_ALLOWLIST_RESULT passed=${passed} blocked=${blocked} typescript=${ts.version}`);
