"""Shared test configuration to ensure core dependencies are loaded."""

import sys
import types
from pathlib import Path

if "jose" not in sys.modules:
    fake_jwt = types.SimpleNamespace(
        encode=lambda *args, **kwargs: "token",
        decode=lambda *args, **kwargs: {},
    )
    fake_exceptions = types.SimpleNamespace(ExpiredSignatureError=Exception)
    fake_jose = types.SimpleNamespace(JWTError=Exception, jwt=fake_jwt, exceptions=fake_exceptions)
    sys.modules["jose"] = fake_jose
    sys.modules["jose.jwt"] = fake_jwt
    sys.modules["jose.exceptions"] = fake_exceptions

if "passlib" not in sys.modules:
    class _FakeCryptContext:
        def hash(self, value: str) -> str:  # pragma: no cover - deterministic stub
            return f"hashed:{value}"

        def verify(self, plain: str, hashed: str) -> bool:  # pragma: no cover
            return hashed.endswith(plain)

    fake_passlib = types.ModuleType("passlib")
    fake_passlib_context = types.SimpleNamespace(CryptContext=lambda **_kwargs: _FakeCryptContext())
    sys.modules["passlib"] = fake_passlib
    sys.modules["passlib.context"] = fake_passlib_context

if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import core security early so that optional dependencies like `jose`
# are loaded (or stubbed) before any tests interact with them.
from app.core import security  # noqa: F401
