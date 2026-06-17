"""Schema-provider loading and validation helpers for SHMC DB initialization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any


SchemaProvider = Callable[[], dict[str, Any]]


@dataclass(frozen=True)
class LoadedSchemaProvider:
    """Validated schema provider and its import reference."""

    ref: str
    provider: SchemaProvider


def load_schema_provider(ref: str) -> LoadedSchemaProvider:
    """Load a schema provider from a 'module:attribute' import string."""
    if ":" not in ref:
        raise ValueError(f"Schema provider ref must use 'module:attribute' format: {ref!r}")

    module_name, attr_name = ref.split(":", 1)
    if not module_name or not attr_name:
        raise ValueError(f"Schema provider ref must use 'module:attribute' format: {ref!r}")

    module = import_module(module_name)
    provider = getattr(module, attr_name)
    if not callable(provider):
        raise TypeError(f"Schema provider {ref!r} is not callable.")

    validate_schema_provider(provider)
    return LoadedSchemaProvider(ref=ref, provider=provider)


def validate_schema_provider(provider: SchemaProvider) -> None:
    """Validate provider output shape without mutating external state."""
    data = provider()
    if not isinstance(data, dict):
        raise TypeError("Schema provider must return a dict.")

    metadata = data.get("metadata")
    bases = data.get("bases")
    if metadata is None and bases is None:
        raise ValueError("Schema provider must return at least 'metadata' or 'bases'.")

    if metadata is not None and not isinstance(metadata, list):
        raise TypeError("Schema provider 'metadata' must be a list when provided.")

    if bases is not None and not isinstance(bases, list):
        raise TypeError("Schema provider 'bases' must be a list when provided.")


def load_schema_providers(refs: list[str]) -> list[LoadedSchemaProvider]:
    """Load and validate schema providers from import strings."""
    return [load_schema_provider(ref) for ref in refs]
