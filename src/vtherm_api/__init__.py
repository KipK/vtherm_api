"""Public package for the Versatile Thermostat API."""

from .command_receipt import (
    AppliedCommandReceipt,
    CommandAlteration,
    CommandReceiptCallback,
    CommandReceiptKind,
    InterfaceCommandReceiptScheduler,
)
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
from .inhibition import InhibitionNotStartedError
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

__version__ = "0.7.0"

__all__ = [
    "AppliedCommandReceipt",
    "CommandAlteration",
    "CommandReceiptCallback",
    "CommandReceiptKind",
    "InhibitionNotStartedError",
    "InterfaceCommandReceiptScheduler",
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
