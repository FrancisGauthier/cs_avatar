import hashlib
import hmac

from pydantic import SecretStr


def digest_secret(secret: SecretStr, value: str) -> bytes:
    return hmac.new(
        secret.get_secret_value().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
