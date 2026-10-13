"""Public package for the Versatile Thermostat API."""

from .interfaces import (
    InterfaceCycleScheduler,
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostat,
    InterfaceThermostatRuntime,
    ValveDiagnosticState,
)
from .log_collector import (
    VThermLogEntry,
    VThermLogHandler,
    VThermLogger,
    async_export_logs,
    get_vtherm_logger,
    write_event_log,
)
from .plugin_climate import PluginClimate
from .vtherm_api import VThermAPI

__version__ = "0.6.1"

__all__ = [
    "InterfaceCycleScheduler",
    "InterfaceFeatureManager",
    "InterfaceFeatureManagerFactory",
    "InterfacePropAlgorithmFactory",
    "InterfacePropAlgorithmHandler",
    "InterfaceThermostat",
    "InterfaceThermostatRuntime",
    "ValveDiagnosticState",
    "PluginClimate",
    "VThermAPI",
    "VThermLogEntry",
    "VThermLogHandler",
    "VThermLogger",
    "async_export_logs",
    "get_vtherm_logger",
    "write_event_log",
    "__version__",
]
