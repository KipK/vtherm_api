"""Applied-command receipt contract (command ownership).

A proportional-algorithm plugin hands a requested ``on_percent`` to the cycle
scheduler through ``start_cycle``. The scheduler may apply a value that differs
from the request (minimal on/off delays for a switch, a valve position held
back by the valve resolver). This module defines the receipt the scheduler
emits for every command it really applies, so that the plugin can attribute the
applied actuator power to the request that produced it.

The contract is optional. It lives in a dedicated protocol,
:class:`InterfaceCommandReceiptScheduler`, that extends the unchanged
:class:`InterfaceCycleScheduler`. A scheduler that does not implement it keeps
satisfying :class:`InterfaceCycleScheduler`; a plugin detects the capability
with ``isinstance(scheduler, InterfaceCommandReceiptScheduler)`` or
``hasattr(scheduler, "register_command_receipt_callback")`` before passing
``request_id`` to ``start_cycle``.

Rules of the contract:

* ``request_id`` is an opaque integer chosen by the plugin. The scheduler never
  interprets it: it stores it with the pending and the active request and echoes
  it in the receipt of the command it really applies. When the scheduler applies
  an older request than the latest one received, the receipt carries the older
  identifier.
* A ``CYCLE_START`` receipt is emitted for each master-cycle start, including an
  automatic restart at the end of a master cycle (``is_repeat=True``, same
  identifier). It is emitted right after the cycle start callbacks and before
  the actuation.
* An ``UPDATE`` receipt is emitted for each valve ``start_cycle`` that goes
  through the running-cycle path, even when the value is unchanged, and for each
  deferred valve update (``request_id=None``).
* No receipt is emitted for a switch request stored as pending during an active
  cycle; its receipt is emitted when it is applied.
* Alterations are sticky per ``request_id``: an automatic restart inherits the
  alterations of the cycle that first applied the request.
* Cancellation, HVAC OFF and power shedding are not covered by receipts; they
  remain reported by the cycle end callback.
* Callbacks are coroutines and are awaited. An exception raised by a callback is
  logged and does not break the cycle.
"""

# pylint: disable=unnecessary-ellipsis

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from homeassistant.core import CALLBACK_TYPE

from .interfaces import InterfaceCycleScheduler


class CommandReceiptKind(StrEnum):
    """Origin of an applied-command receipt."""

    CYCLE_START = "cycle_start"
    """Start of a master cycle, new or automatic restart."""

    UPDATE = "update"
    """Valve position applied or confirmed without starting a new cycle."""


class CommandAlteration(StrEnum):
    """Reason why the applied command differs from the requested one."""

    MIN_ON_OFF = "min_on_off"
    """Switch: the on/off times were forced by the minimal activation or deactivation delay."""

    VALVE_RETAINED = "valve_retained"
    """Valve: the position retained by the valve resolver differs from the rounded request."""


@dataclass(frozen=True, slots=True)
class AppliedCommandReceipt:
    """Command really applied by the cycle scheduler for one request.

    Attributes:
        kind: Origin of the receipt.
        request_id: Echo of the ``request_id`` given to ``start_cycle``. ``None``
            for an internal scheduler path or an untagged request.
        hvac_mode: HVAC mode of the applied command.
        requested_on_percent: Request received for this ``request_id``, clamped to [0, 1].
        applied_on_percent: Actuator power really applied: ``on_time / cycle_duration``
            for a switch, the retained ratio for a valve.
        on_time_sec: On time of the cycle in seconds (diagnostic for a valve).
        off_time_sec: Off time of the cycle in seconds (diagnostic for a valve).
        cycle_duration_sec: Master cycle duration in seconds.
        cycle_start_monotonic: ``time.monotonic()`` at the start of the current master
            cycle; ``None`` for an ``UPDATE`` emitted outside a cycle.
        monotonic: ``time.monotonic()`` at the emission of the receipt.
        is_repeat: True for an automatic restart at the end of a master cycle.
        alterations: Reasons why applied differs from requested; empty when only the
            normal quantization applies. Sticky per ``request_id``.
    """

    kind: CommandReceiptKind
    request_id: int | None
    hvac_mode: str
    requested_on_percent: float
    applied_on_percent: float
    on_time_sec: int
    off_time_sec: int
    cycle_duration_sec: float
    cycle_start_monotonic: float | None
    monotonic: float
    is_repeat: bool
    alterations: frozenset[CommandAlteration]


CommandReceiptCallback = Callable[[AppliedCommandReceipt], Awaitable[None]]


@runtime_checkable
class InterfaceCommandReceiptScheduler(InterfaceCycleScheduler, Protocol):
    """Optional cycle scheduler extension emitting applied-command receipts."""

    @property
    def is_valve_mode(self) -> bool:
        """Return True when the scheduler drives a valve rather than a switch."""
        ...

    def register_command_receipt_callback(self, callback: CommandReceiptCallback) -> CALLBACK_TYPE:
        """Register a coroutine callback receiving each applied-command receipt.

        Returns the function that removes the registration.
        """
        ...

    async def start_cycle(
        self,
        hvac_mode: Any,
        on_percent: float,
        force: bool = False,
        *,
        request_id: int | None = None,
    ) -> None:
        """Start or update a cycle, tagging the request with an opaque identifier."""
        ...
