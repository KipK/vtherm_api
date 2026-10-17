# Guide: Register a proportional algorithm

## Goal

Replace or extend VTherm's proportional control algorithm with a custom implementation.

## Concepts

- `InterfacePropAlgorithmFactory`: named factory registered once in `VThermAPI`
- `InterfacePropAlgorithmHandler`: lifecycle object created for one thermostat runtime
- `InterfaceThermostatRuntime`: runtime view exposed by VTherm to the handler

`vtherm_smartpi` is the main real-world example of this extension point.
It registers one factory, then VTherm creates one handler per thermostat using that proportional function.

## Step 1: Implement the handler

```python
from datetime import datetime, timedelta

from homeassistant.helpers.event import async_track_time_interval

from vtherm_api import InterfaceThermostatRuntime


class MyAlgorithmHandler:
    def __init__(self, thermostat: InterfaceThermostatRuntime) -> None:
        self._thermostat = thermostat
        self._remove_timer = None

    def init_algorithm(self) -> None:
        t = self._thermostat
        t.minimal_activation_delay = 30
        t.minimal_deactivation_delay = 30
        t.prop_algorithm = MyInternalAlgorithm(
            cycle_min=t.cycle_min,
            name=t.name,
        )

    async def async_added_to_hass(self) -> None:
        return None

    async def async_startup(self) -> None:
        await self.on_state_changed(True)

    def remove(self) -> None:
        self._stop_timer()

    async def control_heating(
        self,
        timestamp: datetime | None = None,
        force: bool = False,
    ) -> None:
        t = self._thermostat
        current = t.current_temperature
        target = t.target_temperature

        if current is None or target is None:
            return

        if t.vtherm_hvac_mode == "off":
            if t.is_device_active:
                await t.async_underlying_entity_turn_off()
            return

        on_percent = t.prop_algorithm.calculate(
            target_temp=target,
            current_temp=current,
            ext_current_temp=t.current_outdoor_temperature,
            slope=t.last_temperature_slope,
            hvac_mode=t.vtherm_hvac_mode,
            power_shedding=t.is_overpowering_detected,
            off_reason=t.hvac_off_reason,
        )

        if t.cycle_scheduler is not None:
            await t.cycle_scheduler.start_cycle(
                t.vtherm_hvac_mode,
                on_percent,
                force=force,
            )

        t.update_custom_attributes()
        t.async_write_ha_state()

    async def on_state_changed(self, changed: bool) -> None:
        del changed
        t = self._thermostat
        if t.vtherm_hvac_mode == "off":
            self._stop_timer()
        else:
            self._start_timer()

    def on_scheduler_ready(self, scheduler) -> None:
        algo = self._thermostat.prop_algorithm
        scheduler.register_cycle_start_callback(algo.on_cycle_started)
        scheduler.register_cycle_end_callback(algo.on_cycle_completed)

    def should_publish_intermediate(self) -> bool:
        return True

    def _start_timer(self) -> None:
        if self._remove_timer is not None:
            return

        self._remove_timer = async_track_time_interval(
            self._thermostat.hass,
            lambda now: self._thermostat.hass.async_create_task(
                self._thermostat.async_control_heating()
            ),
            timedelta(seconds=30),
        )

    def _stop_timer(self) -> None:
        if self._remove_timer is not None:
            self._remove_timer()
            self._remove_timer = None
```

## Step 2: Implement the factory

```python
from vtherm_api import InterfaceThermostatRuntime


class MyAlgorithmFactory:
    @property
    def name(self) -> str:
        return "my_algorithm"

    def create(self, thermostat: InterfaceThermostatRuntime) -> MyAlgorithmHandler:
        return MyAlgorithmHandler(thermostat)
```

## Step 3: Register the factory

```python
from vtherm_api import VThermAPI


async def async_setup_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        return False

    api.register_prop_algorithm(MyAlgorithmFactory())
    return True
```

## Step 4: Unregister on unload

```python
async def async_unload_entry(hass, entry) -> bool:
    api = VThermAPI.get_vtherm_api()
    if api is not None:
        api.unregister_prop_algorithm("my_algorithm")
    return True
```

## What SmartPI shows in practice

The `vtherm_smartpi` integration demonstrates a few important patterns that are not obvious from the bare interface definitions:

- `thermostat.prop_algorithm` can hold a rich internal algorithm object rather than the handler itself
- `on_scheduler_ready(...)` is the place to bind cycle start and cycle end callbacks
- `on_state_changed(...)` is a good place to start or stop periodic recalculation timers
- `async_underlying_entity_turn_off()` is useful when your logic decides VTherm must force the underlying device off
- `async_control_heating()` can be re-triggered by your own timer between normal cycle boundaries

## Attributing the applied command (optional)

The scheduler can apply a value that differs from the requested `on_percent` (minimal on/off delays for a switch, a valve position held back by the valve resolver). When the scheduler implements `InterfaceCommandReceiptScheduler`, the handler can tag its requests and receive the command that was really applied:

```python
from vtherm_api import AppliedCommandReceipt, InterfaceCommandReceiptScheduler


class MyAlgorithmHandler:
    def __init__(self) -> None:
        self._request_id = 0

    def on_scheduler_ready(self, scheduler) -> None:
        self._receipts = isinstance(scheduler, InterfaceCommandReceiptScheduler)
        if self._receipts:
            self._remove_receipt = scheduler.register_command_receipt_callback(self._on_receipt)

    async def _start(self, scheduler, mode, on_percent, force) -> None:
        if self._receipts:
            self._request_id += 1
            await scheduler.start_cycle(mode, on_percent, force=force, request_id=self._request_id)
        else:
            await scheduler.start_cycle(mode, on_percent, force=force)

    async def _on_receipt(self, receipt: AppliedCommandReceipt) -> None:
        if receipt.request_id is None or receipt.alterations:
            return
        # receipt.applied_on_percent is the actuator power applied for request receipt.request_id
```

The extension is optional: `InterfaceCycleScheduler` is unchanged, and a scheduler without the extension must not receive `request_id`. See [Command receipts](../api-reference.md#command-receipts) for the full contract.

## Reading thermostat runtime state

Inside your handler, these runtime values are commonly used:

```python
async def control_heating(self, timestamp=None, force: bool = False) -> None:
    t = self._thermostat

    current = t.current_temperature
    outdoor = t.current_outdoor_temperature
    target = t.target_temperature
    slope = t.last_temperature_slope
    mode = t.vtherm_hvac_mode
    cycle_min = t.cycle_min
    scheduler = t.cycle_scheduler
    active = t.is_device_active
    overpowering = t.is_overpowering_detected
    off_reason = t.hvac_off_reason
```

See [InterfaceThermostatRuntime](../api-reference.md#interfacethermostatruntime) for the full contract.
