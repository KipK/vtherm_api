from email.parser import Parser
from importlib.metadata import distribution
from pathlib import Path

from src import vtherm_api


def _package_metadata_version() -> str:
    package_root = Path(vtherm_api.__file__).resolve().parent
    local_pkg_info = package_root.parent / "vtherm_api.egg-info" / "PKG-INFO"

    if local_pkg_info.exists():
        return Parser().parsestr(local_pkg_info.read_text(encoding="utf-8"))["Version"]

    return distribution("vtherm_api").version


def test_package_version_is_0_7_0() -> None:
    assert vtherm_api.__version__ == "0.7.0"


def test_package_exports_algorithm_plugin_api() -> None:
    assert vtherm_api.VThermAPI is not None
    assert vtherm_api.PluginClimate is not None
    assert vtherm_api.InterfaceThermostat is not None
    assert vtherm_api.InterfaceThermostatRuntime is not None
    assert vtherm_api.InterfaceCycleScheduler is not None
    assert vtherm_api.InterfacePropAlgorithmHandler is not None
    assert vtherm_api.InterfacePropAlgorithmFactory is not None
    assert vtherm_api.InterfaceFeatureManager is not None
    assert vtherm_api.InterfaceFeatureManagerFactory is not None
    assert vtherm_api.InterfaceCommandReceiptScheduler is not None
    assert vtherm_api.AppliedCommandReceipt is not None
    assert vtherm_api.CommandReceiptKind is not None
    assert vtherm_api.CommandAlteration is not None
    assert vtherm_api.CommandReceiptCallback is not None
    assert vtherm_api.VThermLogger is not None
    assert vtherm_api.VThermLogHandler is not None
    assert vtherm_api.VThermLogEntry is not None
    assert vtherm_api.get_vtherm_logger is not None
    assert vtherm_api.write_event_log is not None
    assert vtherm_api.async_export_logs is not None
    assert vtherm_api.__version__ == _package_metadata_version()
