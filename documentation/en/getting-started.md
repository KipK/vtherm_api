# Getting started

## Installation

### In a Home Assistant custom integration

Add `vtherm_api` as a dependency in your integration's `manifest.json`:

```json
{
  "domain": "my_vtherm_plugin",
  "name": "My VTherm Plugin",
    "requirements": ["vtherm_api>=0.6.0"],
  "dependencies": ["versatile_thermostat"]
}
```

### For local development

Clone the repository, then install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Run the test suite to verify the setup:

```bash
pytest
```

## Minimum requirements

- Python 3.14+
- Home Assistant with Versatile Thermostat installed and configured
- At least one VTherm climate entity registered in Home Assistant

## Public imports

All main classes and interfaces are exported from the package root:

```python
from vtherm_api import (
  InhibitionStatus,
  InhibitionStopPolicy,
  InhibitionThermostatView,
    InterfaceCycleScheduler,
    InterfaceFeatureManager,
    InterfaceFeatureManagerFactory,
  InterfaceInhibitionProvider,
  InterfaceInhibitionProviderFactory,
  InterfaceInhibitionThermostatView,
    InterfacePropAlgorithmFactory,
    InterfacePropAlgorithmHandler,
    InterfaceThermostat,
    InterfaceThermostatRuntime,
    PluginClimate,
    VThermAPI,
    __version__,
)
from vtherm_api.const import DOMAIN, EventType
```

## First integration: create or retrieve VThermAPI

The current API does not expose `add_entry(...)` or `remove_entry(...)`.
In practice, integrations call `VThermAPI.get_vtherm_api(hass)` during setup to create or retrieve the singleton:

```python
from vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    _ = api.hass
    _ = api.now
    return True


async def async_unload_entry(hass, entry) -> bool:
    return True
```

## What VThermAPI is mainly used for

- `api.hass`: access to the Home Assistant runtime
- `api.now`: timezone-aware datetime from Home Assistant
- `api.register_prop_algorithm(...)`: register a proportional algorithm factory
- `api.register_manager(...)`: register a single feature manager instance across existing VTherm entities
- `api.register_feature_manager(...)`: register a feature manager factory instantiated once per eligible thermostat
- `api.register_inhibition_provider_factory(...)`: register an inhibition-provider factory; the core passes it an immutable `InhibitionThermostatView` and awaits provider shutdown before unregistering it

## Real-world usage patterns

Two existing integrations in this ecosystem illustrate the intended usage:

- `vtherm_smartpi`: registers a proportional algorithm factory with `VThermAPI`
- `vtherm_climate_replication`: uses `PluginClimate` to link to one target VTherm entity and forward HVAC mode, preset, and target temperature changes

## Next steps

- [Listen to thermostat events](guides/listen-to-events.md) - subscribe to VTherm events with `PluginClimate`
- [Register a proportional algorithm](guides/proportional-algorithm.md) - plug in a custom control algorithm
- [Create a FeatureManager](guides/feature-manager.md) - extend thermostat behavior
- [Forward actions to VTherm](guides/forward-actions.md) - send commands back to a thermostat
