# QA

Comandos requeridos:

```powershell
python -m pytest apps/api/tests/test_auth_lifecycle_static.py -q --tb=short
python -m pytest apps/api/tests/test_ads_marketplace.py -q --tb=short
python -m pytest apps/api/tests/test_business_access_control.py apps/api/tests/test_business_order_ops.py apps/api/tests/test_credits_referrals.py -q --tb=short
python -m pytest apps/api/tests -q
python -m ruff check apps/api scripts
python -m compileall apps/api apps/web/src scripts
$env:PATH="C:\Users\carlo\AppData\Local\Programs\Cursor\resources\app\resources\helpers;$env:PATH"; pnpm --filter @nodo/web build
rg -n "window\.confirm|savingZelleId|deletingZelleId|isSavingZelle" apps/web/src/hooks/business-mini-app apps/web/src/screens/business-app
rg -n "api\.developer\.coinbase\.com/rpc/v1/base/[A-Za-z0-9_-]+|0x[a-fA-F0-9]{40}|PRIVATE_KEY|mnemonic|seed phrase|BEGIN [A-Z ]*PRIVATE KEY" apps/web/src apps/api/app/modules/ads apps/api/app/modules/businesses apps/api/app/modules/credits apps/api/app/modules/orders
```
