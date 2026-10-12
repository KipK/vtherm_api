"""Tests for the inhibition provider contract and registry (issue #2087)."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from src import vtherm_api
from src.vtherm_api.const import DOMAIN
from src.vtherm_api.inhibition import (
    DEFAULT_INHIBITION_STOP_POLICY,
    InhibitionThermostatView,
    InhibitionStatus,
    InhibitionStopPolicy,
    InhibitionTransition,
    InterfaceInhibitionProvider,
    InterfaceInhibitionProviderFactory,
    InterfaceInhibitionThermostatView,
)
from src.vtherm_api.vtherm_api import VThermAPI


class FakeInhibitionProvider:
    """Minimal provider implementing the protocol."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._status = InhibitionStatus.UNKNOWN
        self._callbacks: list = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> InhibitionStatus:
        return self._status

    @property
    def physical_stop_policy(self) -> InhibitionStopPolicy:
        return InhibitionStopPolicy.TURN_OFF

    def post_init(self, entry_infos) -> None:
        del entry_infos

    async def async_start_listening(self) -> None:
        return None

    async def async_stop_listening(self) -> None:
        old_status = self._status
        self._status = InhibitionStatus.UNKNOWN
        transition = InhibitionTransition(
            provider_name=self._name,
            new_status=InhibitionStatus.UNKNOWN,
            old_status=old_status,
            stop_policy=self.physical_stop_policy,
            timestamp=datetime.now(timezone.utc),
            sequence=1,
        )
        for callback in tuple(self._callbacks):
            await callback(transition)
        self._callbacks.clear()

    def restore_state(self, old_state: Any) -> None:
        del old_state

    async def async_refresh_state(self) -> InhibitionStatus:
        return self._status

    def register_transition_callback(self, callback):
        self._callbacks.append(callback)
        return lambda: self._callbacks.remove(callback)


class FakeInhibitionProviderFactory:
    """Minimal factory implementing the protocol."""

    def __init__(self, name: str, supported: bool = True) -> None:
        self._name = name
        self._supported = supported

    @property
    def name(self) -> str:
        return self._name

    def supports(self, thermostat: InterfaceInhibitionThermostatView) -> bool:
        del thermostat
        return self._supported

    def create(self, thermostat: InterfaceInhibitionThermostatView) -> FakeInhibitionProvider:
        del thermostat
        return FakeInhibitionProvider(self._name)


def _build_hass() -> SimpleNamespace:
    return SimpleNamespace(data={DOMAIN: {}}, config=SimpleNamespace(time_zone="UTC"))


@pytest.fixture
def api():
    VThermAPI.reset_vtherm_api()
    yield VThermAPI.get_vtherm_api(_build_hass())
    VThermAPI.reset_vtherm_api()


def test_status_and_policy_values() -> None:
    """Serialized values are stable: they are persisted by the core."""
    assert [s.value for s in InhibitionStatus] == [
        "active", "inactive", "unknown"]
    assert [p.value for p in InhibitionStopPolicy] == [
        "turn_off", "do_not_turn_off"]
    assert DEFAULT_INHIBITION_STOP_POLICY is InhibitionStopPolicy.TURN_OFF
    assert InhibitionStatus("unknown") is InhibitionStatus.UNKNOWN


def test_protocols_are_runtime_checkable() -> None:
    factory = FakeInhibitionProviderFactory("inhibit")
    thermostat = InhibitionThermostatView(
        entity_id="climate.office",
        name="Office",
        unique_id="office",
    )
    assert isinstance(thermostat, InterfaceInhibitionThermostatView)
    assert InhibitionThermostatView.from_thermostat(thermostat) == thermostat
    assert not hasattr(thermostat, "async_underlying_entity_turn_off")
    with pytest.raises(AttributeError):
        thermostat.name = "Changed"  # type: ignore[misc]
    assert isinstance(factory, InterfaceInhibitionProviderFactory)
    assert isinstance(factory.create(thermostat), InterfaceInhibitionProvider)


@pytest.mark.asyncio
async def test_provider_stop_waits_for_unknown_callback_before_detaching() -> None:
    provider = FakeInhibitionProvider("inhibit")
    received: list[InhibitionTransition] = []

    async def receive_transition(transition: InhibitionTransition) -> None:
        received.append(transition)

    provider.register_transition_callback(receive_transition)
    await provider.async_stop_listening()

    assert provider.status is InhibitionStatus.UNKNOWN
    assert [transition.new_status for transition in received] == [
        InhibitionStatus.UNKNOWN]
    assert provider._callbacks == []  # pylint: disable=protected-access


def test_transition_is_immutable() -> None:
    transition = InhibitionTransition(
        provider_name="inhibit",
        new_status=InhibitionStatus.ACTIVE,
        old_status=InhibitionStatus.INACTIVE,
        stop_policy=InhibitionStopPolicy.DO_NOT_TURN_OFF,
        timestamp=datetime(2026, 10, 11, tzinfo=timezone.utc),
        sequence=3,
    )
    with pytest.raises(AttributeError):
        transition.new_status = InhibitionStatus.INACTIVE  # type: ignore[misc]


def test_registry_keeps_registration_order(api: VThermAPI) -> None:
    """The first eligible factory wins in the core, so order must not be sorted."""
    zeta = FakeInhibitionProviderFactory("zeta")
    alpha = FakeInhibitionProviderFactory("alpha")
    api.register_inhibition_provider_factory(zeta)
    api.register_inhibition_provider_factory(alpha)

    assert api.list_inhibition_provider_factories() == ["zeta", "alpha"]
    assert api.get_inhibition_provider_factories() == [zeta, alpha]
    assert api.get_inhibition_provider_factory("alpha") is alpha


def test_duplicate_name_is_refused(api: VThermAPI) -> None:
    first = FakeInhibitionProviderFactory("inhibit")
    api.register_inhibition_provider_factory(first)

    with pytest.raises(ValueError, match="already registered"):
        api.register_inhibition_provider_factory(
            FakeInhibitionProviderFactory("inhibit"))
    assert api.get_inhibition_provider_factory("inhibit") is first


def test_same_factory_twice_is_a_noop(api: VThermAPI) -> None:
    factory = FakeInhibitionProviderFactory("inhibit")
    api.register_inhibition_provider_factory(factory)
    api.register_inhibition_provider_factory(factory)
    assert api.list_inhibition_provider_factories() == ["inhibit"]


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_is_refused(api: VThermAPI, name: str) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        api.register_inhibition_provider_factory(
            FakeInhibitionProviderFactory(name))


def test_none_factory_is_refused(api: VThermAPI) -> None:
    with pytest.raises(ValueError, match="cannot be None"):
        api.register_inhibition_provider_factory(
            None)  # type: ignore[arg-type]


def test_unregister_is_idempotent(api: VThermAPI) -> None:
    factory = FakeInhibitionProviderFactory("inhibit")
    api.register_inhibition_provider_factory(factory)

    api.unregister_inhibition_provider_factory("inhibit")
    api.unregister_inhibition_provider_factory("inhibit")
    api.unregister_inhibition_provider_factory("never_registered")

    assert api.list_inhibition_provider_factories() == []
    # The name is free again after unregistering.
    api.register_inhibition_provider_factory(
        FakeInhibitionProviderFactory("inhibit"))


def test_reset_clears_inhibition_registry() -> None:
    VThermAPI.reset_vtherm_api()
    api = VThermAPI.get_vtherm_api(_build_hass())
    api.register_inhibition_provider_factory(
        FakeInhibitionProviderFactory("inhibit"))

    VThermAPI.reset_vtherm_api()
    # The old instance may still be referenced by a plugin: it must be empty too.
    assert api.list_inhibition_provider_factories() == []
    assert VThermAPI.get_vtherm_api(
        _build_hass()).list_inhibition_provider_factories() == []
    VThermAPI.reset_vtherm_api()


def test_registry_is_separate_from_feature_managers(api: VThermAPI) -> None:
    api.register_inhibition_provider_factory(
        FakeInhibitionProviderFactory("inhibit"))
    assert api.list_feature_managers() == []
    assert api.list_prop_algorithms() == []


def test_package_exports_inhibition_api() -> None:
    for symbol in (
        "InhibitionStatus",
        "InhibitionStopPolicy",
        "InhibitionThermostatView",
        "InhibitionTransition",
        "InterfaceInhibitionProvider",
        "InterfaceInhibitionProviderFactory",
        "InterfaceInhibitionThermostatView",
        "DEFAULT_INHIBITION_STOP_POLICY",
    ):
        assert getattr(vtherm_api, symbol) is not None
        assert symbol in vtherm_api.__all__
