from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import redis
from eth_account import Account
from eth_account.messages import encode_defunct
from redis.exceptions import RedisError, WatchError

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.models import BASE_MAINNET_CHAIN_ID, CREDIT_PACKAGES, utc_now
from app.modules.credits.payment_authorizations import normalize_payment_address
from app.modules.credits.schemas import ContractBaseUsdcPaymentRequest
from app.modules.users.models import UserRecord

HANDOFF_TTL_SECONDS = 5 * 60
HANDOFF_STORAGE_GRACE_SECONDS = 60
HANDOFF_TOKEN_BYTES = 32
HANDOFF_TOKEN_PATTERN_LENGTH = 43


class CreditHandoffStoreUnavailable(RuntimeError):
    pass


class CreditHandoffClaimConflict(RuntimeError):
    pass


@dataclass
class CreditHandoffRecord:
    id: str
    token_hash: str
    user_id: str
    business_id: str
    package_code: str
    challenge: str
    status: str
    created_at: str
    expires_at: str
    claim_wallet_address: str | None = None
    claim_signature_hash: str | None = None
    purchase_id: str | None = None


def handoff_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _record_from_json(raw: str) -> CreditHandoffRecord:
    return CreditHandoffRecord(**json.loads(raw))


def _record_json(record: CreditHandoffRecord) -> str:
    return json.dumps(asdict(record), sort_keys=True, separators=(",", ":"))


class InMemoryCreditHandoffStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, CreditHandoffRecord] = {}
        self._token_hash_by_id: dict[str, str] = {}

    def create(self, record: CreditHandoffRecord) -> None:
        with self._lock:
            if record.token_hash in self._records or record.id in self._token_hash_by_id:
                raise CreditHandoffClaimConflict("handoff collision")
            self._records[record.token_hash] = record
            self._token_hash_by_id[record.id] = record.token_hash

    def get_by_token(self, token: str) -> CreditHandoffRecord | None:
        with self._lock:
            return self._records.get(handoff_token_hash(token))

    def get_by_id(self, handoff_id: str) -> CreditHandoffRecord | None:
        with self._lock:
            token_hash = self._token_hash_by_id.get(handoff_id)
            return self._records.get(token_hash) if token_hash else None

    def begin_claim(
        self,
        *,
        token: str,
        wallet_address: str,
        signature_hash: str,
    ) -> CreditHandoffRecord:
        with self._lock:
            record = self._records.get(handoff_token_hash(token))
            if record is None:
                raise CreditHandoffClaimConflict("handoff missing")
            if record.status == "active":
                record.status = "claiming"
                record.claim_wallet_address = wallet_address
                record.claim_signature_hash = signature_hash
                return record
            if (
                record.status in {"claiming", "prepared"}
                and record.claim_wallet_address == wallet_address
                and record.claim_signature_hash == signature_hash
            ):
                return record
            raise CreditHandoffClaimConflict("handoff already claimed")

    def complete_claim(self, *, token: str, purchase_id: str) -> CreditHandoffRecord:
        with self._lock:
            record = self._records.get(handoff_token_hash(token))
            if record is None or record.status not in {"claiming", "prepared"}:
                raise CreditHandoffClaimConflict("handoff cannot be completed")
            if record.purchase_id not in {None, purchase_id}:
                raise CreditHandoffClaimConflict("handoff purchase mismatch")
            record.status = "prepared"
            record.purchase_id = purchase_id
            return record


class RedisCreditHandoffStore:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _token_key(token_hash: str) -> str:
        return f"credits:handoff:token:{token_hash}"

    @staticmethod
    def _id_key(handoff_id: str) -> str:
        return f"credits:handoff:id:{handoff_id}"

    def create(self, record: CreditHandoffRecord) -> None:
        ttl = HANDOFF_TTL_SECONDS + HANDOFF_STORAGE_GRACE_SECONDS
        token_key = self._token_key(record.token_hash)
        id_key = self._id_key(record.id)
        try:
            with self._client.pipeline(transaction=True) as pipe:
                pipe.set(token_key, _record_json(record), nx=True, ex=ttl)
                pipe.set(id_key, record.token_hash, nx=True, ex=ttl)
                token_created, id_created = pipe.execute()
            if not token_created or not id_created:
                if token_created:
                    self._client.delete(token_key)
                if id_created:
                    self._client.delete(id_key)
                raise CreditHandoffClaimConflict("handoff collision")
        except RedisError as exc:
            raise CreditHandoffStoreUnavailable("handoff store unavailable") from exc

    def get_by_token(self, token: str) -> CreditHandoffRecord | None:
        try:
            raw = self._client.get(self._token_key(handoff_token_hash(token)))
        except RedisError as exc:
            raise CreditHandoffStoreUnavailable("handoff store unavailable") from exc
        return _record_from_json(raw) if raw else None

    def get_by_id(self, handoff_id: str) -> CreditHandoffRecord | None:
        try:
            token_hash = self._client.get(self._id_key(handoff_id))
            raw = self._client.get(self._token_key(token_hash)) if token_hash else None
        except RedisError as exc:
            raise CreditHandoffStoreUnavailable("handoff store unavailable") from exc
        return _record_from_json(raw) if raw else None

    def begin_claim(
        self,
        *,
        token: str,
        wallet_address: str,
        signature_hash: str,
    ) -> CreditHandoffRecord:
        key = self._token_key(handoff_token_hash(token))
        for _ in range(4):
            try:
                with self._client.pipeline() as pipe:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if not raw:
                        raise CreditHandoffClaimConflict("handoff missing")
                    record = _record_from_json(raw)
                    if record.status == "active":
                        record.status = "claiming"
                        record.claim_wallet_address = wallet_address
                        record.claim_signature_hash = signature_hash
                        pipe.multi()
                        pipe.set(key, _record_json(record), keepttl=True)
                        pipe.execute()
                        return record
                    if (
                        record.status in {"claiming", "prepared"}
                        and record.claim_wallet_address == wallet_address
                        and record.claim_signature_hash == signature_hash
                    ):
                        return record
                    raise CreditHandoffClaimConflict("handoff already claimed")
            except WatchError:
                continue
            except RedisError as exc:
                raise CreditHandoffStoreUnavailable("handoff store unavailable") from exc
        raise CreditHandoffStoreUnavailable("handoff claim contention")

    def complete_claim(self, *, token: str, purchase_id: str) -> CreditHandoffRecord:
        key = self._token_key(handoff_token_hash(token))
        for _ in range(4):
            try:
                with self._client.pipeline() as pipe:
                    pipe.watch(key)
                    raw = pipe.get(key)
                    if not raw:
                        raise CreditHandoffClaimConflict("handoff missing")
                    record = _record_from_json(raw)
                    if record.status not in {"claiming", "prepared"}:
                        raise CreditHandoffClaimConflict("handoff cannot be completed")
                    if record.purchase_id not in {None, purchase_id}:
                        raise CreditHandoffClaimConflict("handoff purchase mismatch")
                    record.status = "prepared"
                    record.purchase_id = purchase_id
                    pipe.multi()
                    pipe.set(key, _record_json(record), keepttl=True)
                    pipe.execute()
                    return record
            except WatchError:
                continue
            except RedisError as exc:
                raise CreditHandoffStoreUnavailable("handoff store unavailable") from exc
        raise CreditHandoffStoreUnavailable("handoff completion contention")


class CreditPaymentHandoffs:
    def __init__(
        self,
        *,
        settings,
        store,
        user_repository,
        business_purchases,
        owner_business: Callable[[UserRecord], BusinessRecord],
        require_business_pin: Callable[[UserRecord], None],
        rate_limit: Callable[[str, str | None, str | None, str | None], None],
        audit_writer,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._store = store
        self._users = user_repository
        self._business_purchases = business_purchases
        self._owner_business = owner_business
        self._require_business_pin = require_business_pin
        self._rate_limit = rate_limit
        self._audit = audit_writer

    def create(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        package_code: str,
        request_id: str,
    ) -> dict[str, Any]:
        self._rate_limit("create", user.id, business.id, None)
        if package_code not in CREDIT_PACKAGES:
            raise ApiError("INVALID_PACKAGE", status_code=400)
        self._business_purchases.ensure_contract_payment_available()
        now = utc_now()
        expires_at = now + timedelta(seconds=HANDOFF_TTL_SECONDS)
        token = secrets.token_urlsafe(HANDOFF_TOKEN_BYTES)
        if len(token) != HANDOFF_TOKEN_PATTERN_LENGTH:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503)
        handoff_id = str(uuid4())
        challenge = self._build_challenge(
            handoff_id=handoff_id,
            nonce=secrets.token_hex(16),
            expires_at=expires_at,
        )
        record = CreditHandoffRecord(
            id=handoff_id,
            token_hash=handoff_token_hash(token),
            user_id=user.id,
            business_id=business.id,
            package_code=package_code,
            challenge=challenge,
            status="active",
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        try:
            self._store.create(record)
        except (CreditHandoffClaimConflict, CreditHandoffStoreUnavailable) as exc:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503) from exc
        self._audit.write(
            event_type="credit_wallet_handoff_created",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="credit_wallet_handoff",
            resource_id=record.id,
            request_id=request_id,
            metadata_json={"package_code": package_code, "expires_at": record.expires_at},
        )
        return {
            "handoff": {
                "id": record.id,
                "token": token,
                "status": record.status,
                "expires_at": record.expires_at,
            }
        }

    def challenge(self, *, token: str) -> dict[str, Any]:
        token_hash = handoff_token_hash(token)
        self._rate_limit("challenge", None, None, token_hash)
        record = self._record_by_token(token)
        self._require_active(record)
        return {
            "challenge": record.challenge,
            "chain_id": BASE_MAINNET_CHAIN_ID,
            "expires_at": record.expires_at,
        }

    def claim(
        self,
        *,
        token: str,
        wallet_address: str,
        chain_id: int,
        signature: str,
        request_id: str,
    ) -> dict[str, Any]:
        token_hash = handoff_token_hash(token)
        self._rate_limit("claim", None, None, token_hash)
        record = self._record_by_token(token)
        self._require_not_expired(record)
        if chain_id != BASE_MAINNET_CHAIN_ID:
            raise ApiError("CREDIT_HANDOFF_NETWORK_INVALID", status_code=409)
        wallet = normalize_payment_address(wallet_address)
        try:
            recovered = Account.recover_message(
                encode_defunct(text=record.challenge),
                signature=signature,
            ).lower()
        except (ValueError, TypeError) as exc:
            raise ApiError("CREDIT_HANDOFF_SIGNATURE_INVALID", status_code=409) from exc
        if recovered != wallet:
            raise ApiError("CREDIT_HANDOFF_SIGNATURE_INVALID", status_code=409)
        user = self._users.get_user_by_id(record.user_id)
        if user is None:
            raise ApiError("CREDIT_HANDOFF_NOT_FOUND", status_code=404)
        business = self._owner_business(user)
        if business.id != record.business_id:
            raise ApiError("CREDIT_HANDOFF_NOT_FOUND", status_code=404)
        self._require_business_pin(user)
        signature_hash = hashlib.sha256(signature.lower().encode("ascii")).hexdigest()
        try:
            claimed = self._store.begin_claim(
                token=token,
                wallet_address=wallet,
                signature_hash=signature_hash,
            )
        except CreditHandoffClaimConflict as exc:
            raise ApiError("CREDIT_HANDOFF_ALREADY_USED", status_code=409) from exc
        except CreditHandoffStoreUnavailable as exc:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503) from exc
        if claimed.status == "prepared" and claimed.purchase_id:
            return self._claim_response(claimed)
        payment = self._business_purchases.create_base_usdc_payment(
            user=user,
            business=business,
            payload=ContractBaseUsdcPaymentRequest(
                package_code=record.package_code,
                payer_wallet_address=wallet,
            ),
            request_id=request_id,
            idempotency_key=f"credit-handoff:{record.id}",
        )
        purchase = payment.get("purchase")
        purchase_id = purchase.get("id") if isinstance(purchase, dict) else None
        if not isinstance(purchase_id, str):
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503)
        try:
            completed = self._store.complete_claim(token=token, purchase_id=purchase_id)
        except CreditHandoffClaimConflict as exc:
            raise ApiError("CREDIT_HANDOFF_ALREADY_USED", status_code=409) from exc
        except CreditHandoffStoreUnavailable as exc:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503) from exc
        self._audit.write(
            event_type="credit_wallet_handoff_prepared",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="credit_wallet_handoff",
            resource_id=completed.id,
            request_id=request_id,
            metadata_json={
                "purchase_id": purchase_id,
                "wallet_address_masked": _mask_wallet(wallet),
            },
        )
        return self._claim_response(completed)

    def status(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        handoff_id: str,
    ) -> dict[str, Any]:
        self._rate_limit("status", user.id, business.id, handoff_id)
        try:
            record = self._store.get_by_id(handoff_id)
        except CreditHandoffStoreUnavailable as exc:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503) from exc
        if record is None or record.user_id != user.id or record.business_id != business.id:
            raise ApiError("CREDIT_HANDOFF_NOT_FOUND", status_code=404)
        status = "expired" if self._expired(record) and record.status != "prepared" else record.status
        response: dict[str, Any] = {
            "handoff": {
                "id": record.id,
                "status": status,
                "expires_at": record.expires_at,
                "wallet_address_masked": _mask_wallet(record.claim_wallet_address),
            }
        }
        if record.status == "prepared" and record.purchase_id:
            detail = self._business_purchases.contract_purchase_detail_for_id(
                record.purchase_id,
                business_id=record.business_id,
            )
            response.update(detail)
        return response

    def _claim_response(self, record: CreditHandoffRecord) -> dict[str, Any]:
        return {
            "handoff": {
                "id": record.id,
                "status": "prepared",
                "expires_at": record.expires_at,
                "wallet_address_masked": _mask_wallet(record.claim_wallet_address),
            }
        }

    def _record_by_token(self, token: str) -> CreditHandoffRecord:
        try:
            record = self._store.get_by_token(token)
        except CreditHandoffStoreUnavailable as exc:
            raise ApiError("CREDIT_HANDOFF_UNAVAILABLE", status_code=503) from exc
        if record is None:
            raise ApiError("CREDIT_HANDOFF_NOT_FOUND", status_code=404)
        return record

    def _require_active(self, record: CreditHandoffRecord) -> None:
        self._require_not_expired(record)
        if record.status != "active":
            raise ApiError("CREDIT_HANDOFF_ALREADY_USED", status_code=409)

    @staticmethod
    def _expires_at(record: CreditHandoffRecord) -> datetime:
        return datetime.fromisoformat(record.expires_at).astimezone(timezone.utc)

    def _expired(self, record: CreditHandoffRecord) -> bool:
        return utc_now() >= self._expires_at(record)

    def _require_not_expired(self, record: CreditHandoffRecord) -> None:
        if self._expired(record):
            raise ApiError("CREDIT_HANDOFF_EXPIRED", status_code=410)

    def _build_challenge(
        self,
        *,
        handoff_id: str,
        nonce: str,
        expires_at: datetime,
    ) -> str:
        configured = urlsplit(self._settings.telegram_web_app_url)
        origin = f"{configured.scheme}://{configured.netloc}"
        return "\n".join(
            (
                "NODO Wallet Handoff",
                f"Origin: {origin}",
                "Confirmo que esta wallet sera usada para preparar la compra de creditos NODO.",
                "Esto no cobra ni mueve fondos.",
                f"Handoff: {handoff_id}",
                f"Nonce: {nonce}",
                f"Chain ID: {BASE_MAINNET_CHAIN_ID}",
                f"Expires at: {expires_at.isoformat()}",
            )
        )


def _mask_wallet(value: str | None) -> str | None:
    return f"{value[:6]}...{value[-4:]}" if value else None
