# API Reference

## VThermAPI

**Module**: `vtherm_api.vtherm_api`

Singleton stored in `hass.data[DOMAIN][VTHERM_API_NAME]`.

### Class methods

#### `VThermAPI.get_vtherm_api(hass=None) -> VThermAPI | None`

Get or create the singleton instance.

- If `hass` is provided, the singleton is created on first call and stored in `hass.data`.
- If `hass` is omitted, the existing singleton is returned if already created.

#### `VThermAPI.reset_vtherm_api() -> None`

Reset the singleton and clear both the proportional algorithm registry and the feature manager factory registry.
Mainly useful in tests.

### Properties

| Property | Type            | Description                                           |
| -------- | --------------- | ----------------------------------------------------- |
| `hass`   | `HomeAssistant` | Home Assistant instance associated with the singleton |
| `name`   | `str`           | Always `"VThermAPI"`                                  |
| `now`    | `datetime`      | Timezone-aware datetime from Home Assistant           |

### Instance methods

#### `register_prop_algorithm(factory: InterfacePropAlgorithmFactory) -> None`

Register or replace a proportional algorithm factory by name.

#### `unregister_prop_algorithm(name: str) -> None`

Remove a proportional algorithm factory by name.

#### `get_prop_algorithm(name: str) -> InterfacePropAlgorithmFactory | None`

Return the factory registered for `name`, or `None`.

#### `list_prop_algorithms() -> list[str]`

Return registered factory names in sorted order.

#### `register_feature_manager(factory: InterfaceFeatureManagerFactory) -> None`

Register or replace a feature manager factory by name.

Unlike `register_manager(...)`, which attaches a single manager instance to the thermostats that already exist, this registry lets the core instantiate **one manager per thermostat** by calling `factory.create(runtime)` for every eligible thermostat (including thermostats built later).

Raises `ValueError` if `factory.name` is empty.

#### `unregister_feature_manager(name: str) -> None`

Remove a feature manager factory by name.

#### `get_feature_manager(name: str) -> InterfaceFeatureManagerFactory | None`

Return the feature manager factory registered for `name`, or `None`.

#### `list_feature_managers() -> list[str]`

Return registered feature manager factory names in sorted order.

#### `get_feature_manager_factories() -> list[InterfaceFeatureManagerFactory]`

Return the registered feature manager factories, sorted by name.
The core iterates over these factories when building a thermostat to instantiate one feature manager per eligible thermostat.

#### `register_inhibition_provider_factory(factory: InterfaceInhibitionProviderFactory) -> None`

Registers an inhibition provider factory (issue #2087). Unlike the other registries:

- a name already registered by **another** factory raises `ValueError` (no silent replacement);
- registering the same factory object again is a no-op;
- registration order is kept, because the core attaches the **first** eligible factory to a VTherm and reports later eligible ones as a conflict.

#### `unregister_inhibition_provider_factory(name: str) -> None`

Removes a factory; unknown names are ignored. Already-attached providers are stopped by their plugin (`stop_listening()` reports `UNKNOWN` first).

#### `get_inhibition_provider_factory(name: str) -> InterfaceInhibitionProviderFactory | None`

#### `list_inhibition_provider_factories() -> list[str]`

Names in registration order.

#### `get_inhibition_provider_factories() -> list[InterfaceInhibitionProviderFactory]`

Factories in registration order; the core iterates over them for each VTherm.

#### `link_to_vtherm(vtherm, plugin_vtherm_entity_id: str) -> None`

Search the Home Assistant climate component for a plugin climate entity matching `plugin_vtherm_entity_id`, then call `plugin.link_to_vtherm(vtherm)`.

This helper is only useful when your plugin climate is itself an HA climate entity.
For many integrations, direct linking through `PluginClimate.link_to_vtherm(...)` is simpler.

#### `register_manager(manager: InterfaceFeatureManager) -> None`

Register a feature manager across VTherm thermostat entities found in the Home Assistant climate component.

Only entities implementing `InterfaceThermostat` and exposing `device_info["model"] == DOMAIN` receive the manager.

#### `_set_now(now: datetime) -> None`

Testing helper that overrides the value returned by `api.now`.

---

## PluginClimate

**Module**: `vtherm_api.plugin_climate`

Helper bound to exactly one linked VTherm thermostat.
It can subscribe to VTherm events, cache the latest payload for each event type, and forward HA service calls to the linked thermostat.

### Constructor

```python
plugin = PluginClimate(hass)
```

### Linking methods

#### `link_to_vtherm(vtherm: Any) -> None`

Link the helper to a VTherm object.

- removes previous listeners
- stores the VTherm reference in `linked_vtherm`
- registers one HA listener for every `EventType`

Only events whose payload `entity_id` matches `linked_vtherm.entity_id` are processed.

#### `remove_listeners() -> None`

Remove all registered HA listeners.

### Properties

#### `linked_vtherm`

Return the currently linked VTherm object, or `None`.

#### `last_event_type`

Return the last handled `EventType`, or `None`.

### Event data helpers

#### `get_event_data(event_type: EventType) -> dict[str, Any]`

Return the most recent payload received for the given event type.
Returns `{}` if no event of that type has been seen yet.

### Event entrypoint

#### `handle_vtherm_event(event: Event) -> None`

Public wrapper around the internal event handling path.
Useful in tests or when invoking the dispatcher manually.

### Event handlers

Override only the handlers you need in a subclass:

| Method                                | Triggered by                      |
| ------------------------------------- | --------------------------------- |
| `handle_safety_event(event)`          | `EventType.SAFETY_EVENT`          |
| `handle_power_event(event)`           | `EventType.POWER_EVENT`           |
| `handle_temperature_event(event)`     | `EventType.TEMPERATURE_EVENT`     |
| `handle_hvac_mode_event(event)`       | `EventType.HVAC_MODE_EVENT`       |
| `handle_central_boiler_event(event)`  | `EventType.CENTRAL_BOILER_EVENT`  |
| `handle_preset_event(event)`          | `EventType.PRESET_EVENT`          |
| `handle_window_auto_event(event)`     | `EventType.WINDOW_AUTO_EVENT`     |
| `handle_auto_start_stop_event(event)` | `EventType.AUTO_START_STOP_EVENT` |
| `handle_timed_preset_event(event)`    | `EventType.TIMED_PRESET_EVENT`    |
| `handle_heating_failure_event(event)` | `EventType.HEATING_FAILURE_EVENT` |

### Action forwarding

#### `await call_linked_vtherm_action(action_name, action_data=None, blocking=False, context=None, return_response=False) -> Any`

Forward a service call to the linked VTherm thermostat.

Internally this becomes:

```python
await hass.services.async_call(
    domain=DOMAIN,
    service=action_name,
    service_data=action_data,
    blocking=blocking,
    context=context,
    target={"entity_id": linked_vtherm.entity_id},
    return_response=return_response,
)
```

Raises `RuntimeError` if no thermostat is linked.

---

## Interfaces

All interfaces are defined as runtime-checkable `Protocol` classes in `vtherm_api.interfaces`.

### InterfaceThermostat

Minimal contract expected of a VTherm thermostat entity.

| Member                      | Type           | Description               |
| --------------------------- | -------------- | ------------------------- |
| `name`                      | `str` property | Human-readable name       |
| `unique_id`                 | `str` property | Unique identifier         |
| `device_info`               | `DeviceInfo    | None` property            | HA device info |
| `register_manager(manager)` | method         | Accepts a feature manager |

### InterfaceFeatureManager

Contract for a feature manager registered through `VThermAPI.register_manager(...)`.

| Member                     | Signature                 | Description                                 |
| -------------------------- | ------------------------- | ------------------------------------------- |
| `name`                     | `str` property            | Logical manager name                        |
| `hass`                     | `HomeAssistant` property  | Home Assistant instance                     |
| `is_configured`            | `bool` property           | Whether the manager is configured           |
| `is_detected`              | `bool` property           | Whether the condition is currently detected |
| `post_init(entry_infos)`   | `(dict) -> None`          | Receive merged config                       |
| `start_listening(force)`   | `async (bool) -> None`    | Start subscriptions                         |
| `stop_listening()`         | `() -> bool               | None`                                       | Stop subscriptions |
| `refresh_state()`          | `async () -> bool`        | Refresh internal state                      |
| `restore_state(old_state)` | `(Any) -> None`           | Restore old state                           |
| `add_listener(func)`       | `(CALLBACK_TYPE) -> None` | Register cleanup callbacks                  |

### InterfaceThermostatRuntime

Runtime view exposed to proportional algorithm handlers.

#### Writable attributes

| Attribute                    | Type  | Description                |
| ---------------------------- | ----- | -------------------------- |
| `prop_algorithm`             | `Any` | Current algorithm object   |
| `minimal_activation_delay`   | `int` | Minimum activation delay   |
| `minimal_deactivation_delay` | `int` | Minimum deactivation delay |

#### Read-only properties

| Property                       | Type                     | Description                         |
| ------------------------------ | ------------------------ | ----------------------------------- |
| `hass`                         | `HomeAssistant`          | Home Assistant instance             |
| `entity_id`                    | `str`                    | Entity id                           |
| `name`                         | `str`                    | Thermostat name                     |
| `unique_id`                    | `str`                    | Unique id                           |
| `entry_infos`                  | `ConfigData              | dict`                               | Merged thermostat config                                  |
| `current_temperature`          | `float                   | None`                               | Room temperature                                          |
| `current_outdoor_temperature`  | `float                   | None`                               | Outdoor temperature                                       |
| `target_temperature`           | `float                   | None`                               | Target temperature                                        |
| `regulated_target_temperature` | `float                   | None`                               | Regulated target temperature used to drive the underlying |
| `last_temperature_slope`       | `float                   | None`                               | Latest temperature slope                                  |
| `vtherm_hvac_mode`             | `str                     | None`                               | VTherm HVAC mode                                          |
| `hvac_action`                  | `str                     | None`                               | HVAC action                                               |
| `hvac_off_reason`              | `str                     | None`                               | HVAC off reason                                           |
| `cycle_min`                    | `int`                    | Cycle length in minutes             |
| `cycle_scheduler`              | `InterfaceCycleScheduler | None`                               | Cycle scheduler                                           |
| `is_device_active`             | `bool`                   | Whether the underlying device is on |
| `is_overpowering_detected`     | `bool`                   | Whether power shedding is active    |
| `underlying_fan_modes`         | `list[str]               | None`                               | Fan modes exposed by the underlying climate(s)            |

#### Methods

| Method                                    | Signature             | Description                                  |
| ----------------------------------------- | --------------------- | -------------------------------------------- |
| `async_set_underlying_fan_mode(fan_mode)` | `async (str) -> None` | Send a fan mode to the underlying climate(s) |
| `async_underlying_entity_turn_off()`      | `async () -> None`    | Turn off the underlying entities             |
| `async_control_heating(timestamp, force)` | `async (datetime      | None, bool) -> bool`                         | Trigger VTherm control |
| `update_custom_attributes()`              | `() -> None`          | Refresh custom state attributes              |
| `async_write_ha_state()`                  | `() -> None`          | Publish state to Home Assistant              |

### InterfacePropAlgorithmHandler

Lifecycle contract for one proportional algorithm handler instance.

| Method                              | Signature                           | Description                                           |
| ----------------------------------- | ----------------------------------- | ----------------------------------------------------- |
| `init_algorithm()`                  | `() -> None`                        | Initialize algorithm state                            |
| `async_added_to_hass()`             | `async () -> None`                  | Called when entity is added to HA                     |
| `async_startup()`                   | `async () -> None`                  | Called after VTherm startup                           |
| `remove()`                          | `() -> None`                        | Cleanup resources                                     |
| `control_heating(timestamp, force)` | `async (datetime                    | None, bool) -> None`                                  | Run one control iteration |
| `on_state_changed(changed)`         | `async (bool) -> None`              | React to thermostat state refreshes and state changes |
| `on_scheduler_ready(scheduler)`     | `(InterfaceCycleScheduler) -> None` | Receive scheduler                                     |
| `should_publish_intermediate()`     | `() -> bool`                        | Allow intermediate state publication                  |

### InterfacePropAlgorithmFactory

Factory registered in `VThermAPI`.

| Member               | Signature                                                       | Description                 |
| -------------------- | --------------------------------------------------------------- | --------------------------- |
| `name`               | `str` property                                                  | Unique algorithm identifier |
| `create(thermostat)` | `(InterfaceThermostatRuntime) -> InterfacePropAlgorithmHandler` | Create a handler            |

### InterfaceFeatureManagerFactory

Factory used by external integrations to register a feature manager instantiated **once per thermostat**. Registered through `VThermAPI.register_feature_manager(...)`.

| Member                 | Signature                                                 | Description                                                                                                                                                                  |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                 | `str` property                                            | Feature manager identifier (e.g. `"auto_fan"`)                                                                                                                               |
| `supports(thermostat)` | `(InterfaceThermostatRuntime) -> bool`                    | Return `True` when the manager is eligible for the thermostat, letting the core skip incompatible thermostats (for example a manager restricted to the `over_climate` scope) |
| `create(thermostat)`   | `(InterfaceThermostatRuntime) -> InterfaceFeatureManager` | Create a feature manager bound to the runtime thermostat                                                                                                                     |

### InterfaceCycleScheduler

Contract exposed by the VTherm cycle scheduler.

| Member                                      | Signature                          | Description                   |
| ------------------------------------------- | ---------------------------------- | ----------------------------- |
| `is_cycle_running`                          | `bool` property                    | Whether a cycle is active     |
| `register_cycle_start_callback(callback)`   | `(Callable) -> None`               | Register cycle start callback |
| `register_cycle_end_callback(callback)`     | `(Callable) -> None`               | Register cycle end callback   |
| `start_cycle(hvac_mode, on_percent, force)` | `async (Any, float, bool) -> None` | Start or update a cycle       |
| `cancel_cycle()`                            | `async () -> None`                 | Cancel the current cycle      |

---

## Constants and EventType

**Module**: `vtherm_api.const`

### Domain constants

| Constant          | Value                    | Description                          |
| ----------------- | ------------------------ | ------------------------------------ |
| `DOMAIN`          | `"versatile_thermostat"` | VTherm service domain                |
| `VTHERM_API_NAME` | `"vtherm_api"`           | Singleton key in `hass.data[DOMAIN]` |

### EventType enum

```python
from vtherm_api.const import EventType

EventType.SAFETY_EVENT
EventType.POWER_EVENT
EventType.TEMPERATURE_EVENT
EventType.HVAC_MODE_EVENT
EventType.CENTRAL_BOILER_EVENT
EventType.PRESET_EVENT
EventType.WINDOW_AUTO_EVENT
EventType.AUTO_START_STOP_EVENT
EventType.TIMED_PRESET_EVENT
EventType.HEATING_FAILURE_EVENT
```

---

## Logging helpers

**Module**: `vtherm_api.log_collector`

#### `get_vtherm_logger(name: str) -> VThermLogger`

Return a `VThermLogger` whose records are also captured by the in-memory ring buffer used by VTherm.

#### `write_event_log(logger: logging.Logger, vtherm: object, message: str) -> None`

Write a highlighted `NEW EVENT` entry for a thermostat into the logs.
This mirrors the historical `write_event_log` helper of the Versatile Thermostat core so that plugins can emit the same recognizable event lines captured by the in-memory collector.

```python
import logging

from vtherm_api.log_collector import get_vtherm_logger, write_event_log

_LOGGER = get_vtherm_logger(__name__)

write_event_log(_LOGGER, thermostat, "auto_fan set to high")
```


### Inhibition (issue #2087)

Module `vtherm_api.inhibition`, all names re-exported from `vtherm_api`.

A plugin detects an external condition and reports a **confirmed** status per VTherm. While the status is `ACTIVE`, or an attached provider is `UNKNOWN`, the VTherm core withdraws control of its underlyings: effective HVAC `OFF` (reason `hvac_off_inhibition`), no regulation, TPI or repair, and at most one physical stop on entry, only with policy `TURN_OFF`. On a confirmed `INACTIVE`, the core reconciles once from the current requested state. The provider never commands the VTherm or its underlyings.

| Name | Kind | Values / members |
|---|---|---|
| `InhibitionStatus` | `StrEnum` | `ACTIVE="active"`, `INACTIVE="inactive"`, `UNKNOWN="unknown"` |
| `InhibitionStopPolicy` | `StrEnum` | `TURN_OFF="turn_off"` (default, safe fallback), `DO_NOT_TURN_OFF="do_not_turn_off"` |
| `DEFAULT_INHIBITION_STOP_POLICY` | constant | `InhibitionStopPolicy.TURN_OFF` |
| `InhibitionTransition` | frozen dataclass | `provider_name`, `new_status`, `old_status`, `stop_policy`, `timestamp`, `sequence` |
| `InhibitionTransitionCallback` | type | `Callable[[InhibitionTransition], Awaitable[None]]` |

#### InterfaceInhibitionProviderFactory

- `name -> str`: stable, non-empty.
- `supports(thermostat: InterfaceThermostatRuntime) -> bool`: pure and synchronous. An exception is a failing candidate (logged, VTherm `UNKNOWN`), never a silent `False`.
- `create(thermostat) -> InterfaceInhibitionProvider`: one provider bound to one VTherm.

#### InterfaceInhibitionProvider

- `name`, `status`, `physical_stop_policy` (properties).
- `post_init(entry_infos)`, `async_start_listening()`, `stop_listening()`, `restore_state(old_state)`.
- `async_refresh_state() -> InhibitionStatus`: re-evaluate and return the confirmed status.
- `register_transition_callback(callback) -> CALLBACK_TYPE`: returns the remover.

Rules for providers:

- publish only confirmed states, after the plugin's own delays; never a raw value or a running debounce;
- never convert `UNKNOWN` into `ACTIVE` or `INACTIVE`;
- `stop_listening()` reports `UNKNOWN` to the callbacks before detaching them;
- `physical_stop_policy` returns `TURN_OFF` when the option is unset or invalid.
