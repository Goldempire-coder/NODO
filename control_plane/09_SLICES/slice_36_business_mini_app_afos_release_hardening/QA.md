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
rg -n "iI1Tr84|0x3934Be999744340338964C1dF0dB0AD146c75D47|api\.developer\.coinbase|PRIVATE_KEY|mnemonic|seed phrase" apps/web/src apps/api/app/modules/ads apps/api/app/modules/businesses apps/api/app/modules/credits apps/api/app/modules/orders
```

