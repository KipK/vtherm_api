"""Inhibition provider contract (issue #2087: controlled VTherm withdrawal).

An inhibition plugin detects an external condition (another heat source,
a cooling AC, a manual takeover, ...) and tells the VTherm core when it is
confirmed active or inactive. While a provider reports ``ACTIVE`` (or an
attached provider is ``UNKNOWN``), the core withdraws control of the
underlying devices: it resolves the effective HVAC mode to ``OFF``, suspends
regulation, TPI and repair, and sends at most one physical stop, only when
the provider's policy is ``TURN_OFF``.

The provider never commands the VTherm or its underlyings and never changes
the requested state. Detection, delays, bypass and configuration stay in the
plugin; the core only consumes the confirmed status and the policy.
"""

# pylint: disable=unnecessary-ellipsis

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from homeassistant.core import CALLBACK_TYPE

from .commons_type import ConfigData


@runtime_checkable
class InterfaceInhibitionThermostatView(Protocol):
    """Read-only VTherm information available to an inhibition factory.

    The core must pass a restricted snapshot implementing this protocol, not
    the full thermostat runtime. This keeps provider selection and creation
    unable to issue HVAC, underlying-device, TPI, or repair commands.
    """

    @property
    def entity_id(self) -> str:
        """Return the thermostat entity identifier."""
        ...

    @property
    def name(self) -> str:
        """Return the thermostat name."""
        ...

    @property
    def unique_id(self) -> str:
        """Return the thermostat unique identifier."""
        ...


@dataclass(frozen=True, slots=True)
class InhibitionThermostatView:
    """Immutable identity snapshot passed from the core to an inhibition factory.

    The core creates this view from the full thermostat object and must not pass
    that full runtime to a factory. Provider-specific configuration is supplied
    later through :meth:`InterfaceInhibitionProvider.post_init`.
    """

    entity_id: str
    name: str
    unique_id: str

    @classmethod
    def from_thermostat(cls, thermostat: InterfaceInhibitionThermostatView) -> "InhibitionThermostatView":
        """Capture the factory-visible identity from a thermostat runtime."""
        return cls(
            entity_id=thermostat.entity_id,
            name=thermostat.name,
            unique_id=thermostat.unique_id,
        )


class InhibitionStatus(StrEnum):
    """Confirmed status reported by an inhibition provider.

    ``UNKNOWN`` is a status of its own: source unavailable, initialization
    not finished, read failure, stop/reload, or a delay not confirmed yet.
    It must never be silently converted into ``ACTIVE`` or ``INACTIVE``.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class InhibitionStopPolicy(StrEnum):
    """Per-VTherm policy for the single physical stop on entry.

    ``TURN_OFF`` is the default and the safe fallback. With
    ``DO_NOT_TURN_OFF`` the core still withdraws control and resolves
    ``OFF``, but sends no ``turn_off`` to the underlyings.
    """

    TURN_OFF = "turn_off"
    DO_NOT_TURN_OFF = "do_not_turn_off"


DEFAULT_INHIBITION_STOP_POLICY = InhibitionStopPolicy.TURN_OFF


@dataclass(frozen=True, slots=True)
class InhibitionTransition:
    """A confirmed status change notified by a provider to the core.

    It carries no source entity, raw value or bypass detail: those
    diagnostics stay in the plugin.
    """

    provider_name: str
    new_status: InhibitionStatus
    old_status: InhibitionStatus
    stop_policy: InhibitionStopPolicy
    timestamp: datetime
    # Monotonic per provider instance; the core ignores a replayed sequence.
    sequence: int = 0


InhibitionTransitionCallback = Callable[[
    InhibitionTransition], Awaitable[None]]


@runtime_checkable
class InterfaceInhibitionProvider(Protocol):
    """Provider bound to exactly one VTherm.

    Only confirmed states are published: a raw input or a running debounce
    timer is never reported as a transition. ``async_stop_listening`` must
    report ``UNKNOWN`` to, and await, the registered callbacks before detaching
    them. The core must await this method before removing its callback or
    unregistering the provider factory, so it never treats a vanished provider
    as ``INACTIVE``.
    """

    @property
    def name(self) -> str:
        """Stable provider name (the factory name)."""
        ...

    @property
    def status(self) -> InhibitionStatus:
        """Last confirmed status."""
        ...

    @property
    def physical_stop_policy(self) -> InhibitionStopPolicy:
        """Effective per-VTherm policy; ``TURN_OFF`` when unset or invalid."""
        ...

    def post_init(self, entry_infos: ConfigData | dict[str, Any]) -> None:
        """Initialize the provider with the merged VTherm configuration."""
        ...

    async def async_start_listening(self) -> None:
        """Subscribe to the provider sources."""
        ...

    async def async_stop_listening(self) -> None:
        """Await ``UNKNOWN`` delivery, then unsubscribe from provider sources."""
        ...

    def restore_state(self, old_state: Any) -> None:
        """Restore provider data from the previous VTherm state if needed."""
        ...

    async def async_refresh_state(self) -> InhibitionStatus:
        """Re-evaluate the sources and return the confirmed status."""
        ...

    def register_transition_callback(self, callback: InhibitionTransitionCallback) -> CALLBACK_TYPE:
        """Register a coroutine called on each confirmed transition.

        Returns a function that removes the callback.
        """
        ...


@runtime_checkable
class InterfaceInhibitionProviderFactory(Protocol):
    """Factory registered by an inhibition plugin."""

    @property
    def name(self) -> str:
        """Stable, non-empty factory name."""
        ...

    def supports(self, thermostat: InterfaceInhibitionThermostatView) -> bool:
        """Return True when this factory wants to attach a provider to the VTherm.

        Pure and synchronous, no Home Assistant side effect. An exception is
        treated by the core as a failing candidate, never silently as False.
        """
        ...

    def create(self, thermostat: InterfaceInhibitionThermostatView) -> InterfaceInhibitionProvider:
        """Create the provider bound to the VTherm."""
        ...
