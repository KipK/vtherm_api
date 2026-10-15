"""Tests for the optional applied-command receipt contract."""

# pylint: disable=redefined-outer-name,too-few-public-methods,unused-argument

from __future__ import annotations

import dataclasses
import inspect
from enum import StrEnum

import pytest

from src import vtherm_api
from src.vtherm_api.command_receipt import (
    AppliedCommandReceipt,
    CommandAlteration,
    CommandReceiptCallback,
    CommandReceiptKind,
    InterfaceCommandReceiptScheduler,
)
from src.vtherm_api.interfaces import InterfaceCycleScheduler


def _receipt(**overrides) -> AppliedCommandReceipt:
    values = {
        "kind": CommandReceiptKind.CYCLE_START,
        "request_id": 7,
        "hvac_mode": "heat",
        "requested_on_percent": 0.42,
        "applied_on_percent": 0.4,
        "on_time_sec": 120,
        "off_time_sec": 180,
        "cycle_duration_sec": 300.0,
        "cycle_start_monotonic": 1000.0,
        "monotonic": 1000.001,
        "is_repeat": False,
        "alterations": frozenset(),
    }
    values.update(overrides)
    return AppliedCommandReceipt(**values)


class LegacyScheduler:
    """Scheduler implementing only the original InterfaceCycleScheduler."""

    @property
    def is_cycle_running(self) -> bool:
        return False

    def register_cycle_start_callback(self, callback) -> None:
        del callback

    def register_cycle_end_callback(self, callback) -> None:
        del callback

    async def start_cycle(self, hvac_mode, on_percent: float, force: bool = False) -> None:
        del hvac_mode, on_percent, force

    async def cancel_cycle(self) -> None:
        return None


class ReceiptScheduler(LegacyScheduler):
    """Scheduler also implementing the receipt extension."""

    is_valve_mode = False

    def register_command_receipt_callback(self, callback):
        del callback
        return lambda: None

    async def start_cycle(self, hvac_mode, on_percent: float, force: bool = False, *, request_id: int | None = None) -> None:
        del hvac_mode, on_percent, force, request_id


def test_enum_values_are_stable() -> None:
    assert issubclass(CommandReceiptKind, StrEnum)
    assert issubclass(CommandAlteration, StrEnum)
    assert {member.name: member.value for member in CommandReceiptKind} == {"CYCLE_START": "cycle_start", "UPDATE": "update"}
    assert {member.name: member.value for member in CommandAlteration} == {"MIN_ON_OFF": "min_on_off", "VALVE_RETAINED": "valve_retained"}


def test_receipt_is_frozen_slotted_dataclass() -> None:
    receipt = _receipt()

    assert dataclasses.is_dataclass(receipt)
    assert not hasattr(receipt, "__dict__")
    with pytest.raises(dataclasses.FrozenInstanceError):
        receipt.request_id = 8  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        receipt.extra = 1  # type: ignore[attr-defined]


def test_receipt_fields_are_stable() -> None:
    assert [field.name for field in dataclasses.fields(AppliedCommandReceipt)] == [
        "kind",
        "request_id",
        "hvac_mode",
        "requested_on_percent",
        "applied_on_percent",
        "on_time_sec",
        "off_time_sec",
        "cycle_duration_sec",
        "cycle_start_monotonic",
        "monotonic",
        "is_repeat",
        "alterations",
    ]


def test_receipt_accepts_untagged_request_and_no_cycle_start() -> None:
    receipt = _receipt(kind=CommandReceiptKind.UPDATE, request_id=None, cycle_start_monotonic=None, alterations=frozenset({CommandAlteration.VALVE_RETAINED}))

    assert receipt.request_id is None
    assert receipt.cycle_start_monotonic is None
    assert receipt.alterations == {CommandAlteration.VALVE_RETAINED}
    assert hash(receipt) == hash(dataclasses.replace(receipt))


def test_protocol_isinstance_with_and_without_extension() -> None:
    assert isinstance(ReceiptScheduler(), InterfaceCommandReceiptScheduler)
    assert isinstance(ReceiptScheduler(), InterfaceCycleScheduler)
    assert not isinstance(LegacyScheduler(), InterfaceCommandReceiptScheduler)
    assert not hasattr(LegacyScheduler(), "register_command_receipt_callback")


def test_extension_is_not_part_of_the_cycle_scheduler_protocol() -> None:
    assert isinstance(LegacyScheduler(), InterfaceCycleScheduler)
    members = {name for name in dir(InterfaceCycleScheduler) if not name.startswith("_")}
    assert members == {"is_cycle_running", "register_cycle_start_callback", "register_cycle_end_callback", "start_cycle", "cancel_cycle"}
    assert list(inspect.signature(InterfaceCycleScheduler.start_cycle).parameters) == ["self", "hvac_mode", "on_percent", "force"]


def test_receipt_start_cycle_request_id_is_optional_keyword_only() -> None:
    parameter = inspect.signature(InterfaceCommandReceiptScheduler.start_cycle).parameters["request_id"]

    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None


def test_callback_alias_and_package_exports() -> None:
    assert CommandReceiptCallback is not None
    for name in (
        "AppliedCommandReceipt",
        "CommandAlteration",
        "CommandReceiptCallback",
        "CommandReceiptKind",
        "InterfaceCommandReceiptScheduler",
    ):
        assert name in vtherm_api.__all__
        assert getattr(vtherm_api, name) is not None
