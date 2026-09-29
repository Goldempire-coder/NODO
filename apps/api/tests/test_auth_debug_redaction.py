import json
from copy import deepcopy

import pytest
from app.modules.users.auth_helpers import safe_debug_payload
from app.shared.logging_redaction import redact_mapping


@pytest.mark.parametrize(
    "key", ["password", "secret", "code", "init_data", "custom_token", "CustomToken"]
)
def test_auth_debug_hides_sensitive_keys(key):
    payload = {key: "fictitious-sensitive-value", "status": "ok"}
    assert json.loads(safe_debug_payload(payload)) == {
        key: "[REDACTED]",
        "status": "ok",
    }


def test_auth_debug_redacts_nested_values_without_mutation():
    payload = {
        "items": [{"code": "123456", "custom_token": "fake"}],
        "nested": ({"PASSWORD": "fake", "init_data": "fake"},),
        "message": "Bearer fictitious-token",
        "count": 3,
    }
    original = deepcopy(payload)
    result = json.loads(safe_debug_payload(payload))
    assert result["items"] == [{"code": "[REDACTED]", "custom_token": "[REDACTED]"}]
    assert result["nested"] == [{"PASSWORD": "[REDACTED]", "init_data": "[REDACTED]"}]
    assert result["message"] == "Bearer [REDACTED]"
    assert result["count"] == 3
    assert payload == original


def test_auth_debug_does_not_change_global_error_code_redaction():
    assert redact_mapping({"code": "AUTH_INVALID"}) == {"code": "AUTH_INVALID"}
    assert safe_debug_payload({"z": 1, "a": True}) == '{"a": true, "z": 1}'
