"""Tests for the minimal inhibition facade (issue #2087)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src import vtherm_api
from src.vtherm_api.const import DOMAIN
from src.vtherm_api.vtherm_api import VThermAPI


class FakeInhibitionThermostat:
    """Minimal core target implementing the two inhibition operations."""

    def __init__(self, entity_id: str = "climate.office") -> None:
        self.entity_id = entity_id
        self.async_set_inhibition = AsyncMock()
        self.async_unset_inhibition = AsyncMock()


def _build_hass(*entities: object) -> SimpleNamespace:
    """Create the minimal Home Assistant shape needed by the facade."""
    return SimpleNamespace(
        data={
            DOMAIN: {},
            "climate": SimpleNamespace(entities=list(entities)),
        },
        config=SimpleNamespace(time_zone="UTC"),
    )


@pytest.fixture
def api() -> VThermAPI:
    """Create an isolated API singleton."""
    VThermAPI.reset_vtherm_api()
    yield VThermAPI.get_vtherm_api(_build_hass())
    VThermAPI.reset_vtherm_api()


@pytest.mark.asyncio
async def test_set_inhibition_delegates_to_target_core(api: VThermAPI) -> None:
    """The facade sends only the entry-stop authorization to the core."""
    thermostat = FakeInhibitionThermostat()
    api.hass.data["climate"].entities.append(thermostat)

    await api.set_inhibition("climate.office", stop_underlyings=True)

    thermostat.async_set_inhibition.assert_awaited_once_with(True)
    thermostat.async_unset_inhibition.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_without_entry_stop_delegates_false(api: VThermAPI) -> None:
    """A disabled entry stop remains a core decision, not plugin state."""
    thermostat = FakeInhibitionThermostat()
    api.hass.data["climate"].entities.append(thermostat)

    await api.set_inhibition("climate.office", stop_underlyings=False)

    thermostat.async_set_inhibition.assert_awaited_once_with(False)


@pytest.mark.asyncio
async def test_unset_inhibition_delegates_to_target_core(api: VThermAPI) -> None:
    """The facade lets the core perform its own exit reconciliation."""
    thermostat = FakeInhibitionThermostat()
    api.hass.data["climate"].entities.append(thermostat)

    await api.unset_inhibition("climate.office")

    thermostat.async_unset_inhibition.assert_awaited_once_with()
    thermostat.async_set_inhibition.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_target_raises_explicit_lookup_error(api: VThermAPI) -> None:
    """An absent target must not silently turn an API call into a no-op."""
    with pytest.raises(LookupError, match="climate.missing"):
        await api.set_inhibition("climate.missing", stop_underlyings=True)


@pytest.mark.asyncio
async def test_target_without_core_contract_is_rejected(api: VThermAPI) -> None:
    """The facade requires the updated core instead of calling HA services."""
    api.hass.data["climate"].entities.append(
        SimpleNamespace(entity_id="climate.legacy"))

    with pytest.raises(TypeError, match="does not support inhibition"):
        await api.unset_inhibition("climate.legacy")


@pytest.mark.asyncio
async def test_set_inhibition_requires_a_bool(api: VThermAPI) -> None:
    """The entry-stop authorization has a strict boolean contract."""
    with pytest.raises(TypeError, match="stop_underlyings"):
        await api.set_inhibition("climate.office", stop_underlyings=1)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_inhibition_entity_id_must_not_be_empty(api: VThermAPI) -> None:
    """A plugin must target a concrete VTherm entity."""
    with pytest.raises(ValueError, match="vtherm_entity_id"):
        await api.unset_inhibition("  ")


def test_legacy_provider_surface_is_not_exported() -> None:
    """The API must not expose provider, factory, callback, or status types."""
    legacy_symbols = (
        "DEFAULT_INHIBITION_STOP_POLICY",
        "InhibitionStatus",
        "InhibitionStopPolicy",
        "InhibitionThermostatView",
        "InhibitionTransition",
        "InterfaceInhibitionProvider",
        "InterfaceInhibitionProviderFactory",
    )

    for symbol in legacy_symbols:
        assert symbol not in vtherm_api.__all__
        assert not hasattr(vtherm_api, symbol)

    for method in (
        "register_inhibition_provider_factory",
        "unregister_inhibition_provider_factory",
        "get_inhibition_provider_factory",
        "list_inhibition_provider_factories",
        "get_inhibition_provider_factories",
    ):
        assert not hasattr(VThermAPI, method)