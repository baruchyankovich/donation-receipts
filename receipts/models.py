"""Domain models: a single :class:`Receipt` and the :class:`OrganizationSettings`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any

from .assets import DEFAULT_LOGO_PNG_BASE64
from .constants import (
    DEFAULT_ADDRESS_LINE,
    DEFAULT_ORG_NAME,
    DEFAULT_SERVICES_LINE,
    DEFAULT_STARTING_RECEIPT_NUMBER,
)
from .formatting import parse_amount


@dataclass
class Receipt:
    """A single donation receipt.

    All text fields default to empty strings so the model can be built
    incrementally from UI form values.
    """

    receipt_no: int
    date: str = ""
    donor_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    purpose: str = ""
    product: str = ""
    value_num: str = ""
    value_words: str = ""
    notes: str = ""

    #: Persisted column order, reused by the database and Excel export layers.
    COLUMNS = (
        "receipt_no",
        "date",
        "donor_name",
        "address",
        "phone",
        "email",
        "purpose",
        "product",
        "value_num",
        "value_words",
        "notes",
    )

    @property
    def amount(self) -> float:
        """The numeric donation value parsed from :attr:`value_num`."""
        return parse_amount(self.value_num)

    def as_dict(self) -> dict[str, Any]:
        """Return the receipt as a plain ``{column: value}`` mapping."""
        return {name: getattr(self, name) for name in self.COLUMNS}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Receipt:
        """Build a receipt from a mapping, ignoring unknown/missing keys."""
        known = {f.name for f in fields(cls)}
        values = {k: v for k, v in data.items() if k in known and v is not None}
        values.setdefault("receipt_no", int(data.get("receipt_no", 0) or 0))
        return cls(**values)


@dataclass
class OrganizationSettings:
    """Configurable, per-organization presentation and behaviour."""

    org_name: str = DEFAULT_ORG_NAME
    address_line: str = DEFAULT_ADDRESS_LINE
    services_line: str = DEFAULT_SERVICES_LINE
    starting_receipt_number: int = DEFAULT_STARTING_RECEIPT_NUMBER
    backup_dir: str = ""
    custom_logo_base64: str = ""
    custom_logo_mime: str = ""

    #: Keys persisted in the settings table (excludes derived/logo data, which
    #: is handled separately to keep the mapping small).
    TEXT_KEYS = (
        "org_name",
        "address_line",
        "services_line",
        "starting_receipt_number",
        "backup_dir",
    )

    def logo_data_uri(self) -> str:
        """Return a ``data:`` URI for the logo (custom if set, else default)."""
        if self.custom_logo_base64:
            mime = self.custom_logo_mime or "image/png"
            return f"data:{mime};base64,{self.custom_logo_base64}"
        return f"data:image/png;base64,{DEFAULT_LOGO_PNG_BASE64}"

    def has_custom_logo(self) -> bool:
        return bool(self.custom_logo_base64)
