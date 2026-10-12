""" The API of Versatile Thermostat"""
from datetime import datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.climate import ClimateEntity, DOMAIN as CLIMATE_DOMAIN

from .const import DOMAIN, VTHERM_API_NAME, NowClass
from .log_collector import get_vtherm_logger
from .plugin_climate import PluginClimate
from .interfaces import (
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfaceThermostat,
)
from .inhibition import InterfaceInhibitionProviderFactory

_LOGGER = get_vtherm_logger(__name__)


class VThermAPI:
    """The VThermAPI
    This class is a singleton that provides access to the VTherm API instance through HA hass mecanism.
    It also provides a reference to the HA instance for use in the API implementation.
    """

    _hass: HomeAssistant = None

    def __init__(self) -> None:
        """Initialize the VThermAPI instance."""
        self._now: datetime = None
        self._prop_algorithm_registry: dict[str,
                                            InterfacePropAlgorithmFactory] = {}
        self._feature_manager_registry: dict[str,
                                             InterfaceFeatureManagerFactory] = {}
        # Registration order matters (first eligible factory wins), so this
        # registry is never sorted, unlike the other ones.
        self._inhibition_provider_registry: dict[str,
                                                 InterfaceInhibitionProviderFactory] = {}

    @classmethod
    def get_vtherm_api(cls, hass=None):
        """Get the eventual VTherm API class instance or
        instantiate it if it doesn't exists"""
        if hass is not None:
            cls._hass = hass

        if cls._hass is None:
            return None

        domain = cls._hass.data.get(DOMAIN)
        if not domain:
            cls._hass.data.setdefault(DOMAIN, {})

        ret = cls._hass.data.get(
            DOMAIN).get(VTHERM_API_NAME)
        if ret is None:
            ret = cls()
            cls._hass.data[DOMAIN][VTHERM_API_NAME] = ret
        return ret

    @classmethod
    def reset_vtherm_api(cls):
        """Reset the VTherm API instance and related data."""
        if cls._hass is None:
            return

        api = cls._hass.data.get(DOMAIN, {}).get(VTHERM_API_NAME)
        if api is not None:
            api._prop_algorithm_registry.clear()  # pylint: disable=protected-access
            api._feature_manager_registry.clear()  # pylint: disable=protected-access
            api._inhibition_provider_registry.clear()  # pylint: disable=protected-access

        # Remove the API instance from hass.data
        if DOMAIN in cls._hass.data:
            cls._hass.data[DOMAIN].pop(
                VTHERM_API_NAME, None)
        cls._hass = None

    @property
    def hass(self):
        """Get the HomeAssistant object"""
        return type(self)._hass

    @property
    def name(self) -> str:
        """Get the name of the API"""
        return "VThermAPI"

    # For testing purpose
    def _set_now(self, now: datetime):
        """Set the now timestamp. This is only for tests purpose"""
        self._now = now

    @property
    def now(self) -> datetime:
        """Get now. The local datetime or the overloaded _set_now date"""
        return self._now if self._now is not None else NowClass.get_now(self._hass)

    def register_prop_algorithm(self, factory: InterfacePropAlgorithmFactory) -> None:
        """Register or replace a proportional algorithm factory."""
        name = factory.name.strip()
        if not name:
            raise ValueError(
                "The proportional algorithm factory name cannot be empty")

        self._prop_algorithm_registry[name] = factory

    def unregister_prop_algorithm(self, name: str) -> None:
        """Remove a proportional algorithm factory from the registry."""
        self._prop_algorithm_registry.pop(name, None)

    def get_prop_algorithm(self, name: str) -> InterfacePropAlgorithmFactory | None:
        """Return the registered proportional algorithm factory for a name."""
        return self._prop_algorithm_registry.get(name)

    def list_prop_algorithms(self) -> list[str]:
        """Return the registered proportional algorithm names in sorted order."""
        return sorted(self._prop_algorithm_registry)

    def register_feature_manager(self, factory: InterfaceFeatureManagerFactory) -> None:
        """Register or replace a feature manager factory."""
        name = factory.name.strip()
        if not name:
            raise ValueError(
                "The feature manager factory name cannot be empty")

        self._feature_manager_registry[name] = factory

    def unregister_feature_manager(self, name: str) -> None:
        """Remove a feature manager factory from the registry."""
        self._feature_manager_registry.pop(name, None)

    def get_feature_manager(self, name: str) -> InterfaceFeatureManagerFactory | None:
        """Return the registered feature manager factory for a name."""
        return self._feature_manager_registry.get(name)

    def list_feature_managers(self) -> list[str]:
        """Return the registered feature manager names in sorted order."""
        return sorted(self._feature_manager_registry)

    def get_feature_manager_factories(self) -> list[InterfaceFeatureManagerFactory]:
        """Return the registered feature manager factories.

        The core iterates over these factories when building a thermostat to
        instantiate one feature manager per eligible thermostat.
        """
        return [
            self._feature_manager_registry[name]
            for name in sorted(self._feature_manager_registry)
        ]

    def register_inhibition_provider_factory(self, factory: InterfaceInhibitionProviderFactory) -> None:
        """Register an inhibition provider factory (issue #2087).

        Unlike the other registries, a name already registered by another
        factory is refused instead of silently replaced. Registering the same
        factory object again is a no-op.
        """
        if factory is None:
            raise ValueError("The inhibition provider factory cannot be None")
        name = (factory.name or "").strip()
        if not name:
            raise ValueError("The inhibition provider factory name cannot be empty")

        existing = self._inhibition_provider_registry.get(name)
        if existing is factory:
            return
        if existing is not None:
            raise ValueError(f"An inhibition provider factory named '{name}' is already registered")

        self._inhibition_provider_registry[name] = factory
        _LOGGER.info("%s - inhibition provider factory '%s' registered", self.name, name)

    def unregister_inhibition_provider_factory(self, name: str) -> None:
        """Remove an inhibition provider factory. Unknown names are ignored.

        Providers already attached to a VTherm are not touched here: the
        plugin stops them (``stop_listening`` reports ``UNKNOWN`` first).
        """
        if self._inhibition_provider_registry.pop((name or "").strip(), None) is not None:
            _LOGGER.info("%s - inhibition provider factory '%s' unregistered", self.name, name)

    def get_inhibition_provider_factory(self, name: str) -> InterfaceInhibitionProviderFactory | None:
        """Return the inhibition provider factory registered under a name."""
        return self._inhibition_provider_registry.get(name)

    def list_inhibition_provider_factories(self) -> list[str]:
        """Return the registered inhibition provider names, in registration order."""
        return list(self._inhibition_provider_registry)

    def get_inhibition_provider_factories(self) -> list[InterfaceInhibitionProviderFactory]:
        """Return the inhibition provider factories in registration order.

        The core keeps the first eligible factory for a VTherm and reports the
        later eligible ones as a conflict.
        """
        return list(self._inhibition_provider_registry.values())

    def link_to_vtherm(self, vtherm, plugin_vtherm_entity_id: str):
        """Link the VTherm API to a specific VTherm entity."""
        # Implementation for linking to a VTherm entity
        # Find a vtherm instance of type PluginClimate in hass
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None)
        if component:
            for entity in list(component.entities):
                try:
                    if entity.device_info and entity.device_info.get("model", None) == DOMAIN:
                        if plugin_vtherm_entity_id == entity.entity_id and isinstance(entity, InterfaceThermostat):
                            plugin_climate: PluginClimate = entity
                            _LOGGER.info(
                                "%s - We have found the linked PluginVTherm", self)
                            plugin_climate.link_to_vtherm(vtherm)
                            return
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error searching/initializing entity %s: %s", entity.entity_id, e)

    def register_manager(self, manager: InterfaceFeatureManager):
        """Register a feature manager to the API."""
        # Implementation for registering a feature manager
        # Find all vtherm instance of type PluginClimate in hass and register the manager to them
        component: EntityComponent[ClimateEntity] = self._hass.data.get(
            CLIMATE_DOMAIN, None)
        if component:
            for entity in list(component.entities):
                try:
                    if entity.device_info and entity.device_info.get("model", None) == DOMAIN:
                        if isinstance(entity, InterfaceThermostat):
                            plugin_climate: PluginClimate = entity
                            plugin_climate.register_manager(manager)
                except Exception as e:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "Error searching/initializing entity %s: %s", entity.entity_id, e)
