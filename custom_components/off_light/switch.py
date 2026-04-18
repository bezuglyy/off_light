from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runner = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            OffLightBlockSwitch(hass, entry, runner, "on_block", "Блок включения", "mdi:lightbulb-auto", "on"),
            OffLightBlockSwitch(hass, entry, runner, "off_block", "Блок выключения", "mdi:lightbulb-off-outline", "off"),
        ]
    )


class OffLightBlockSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runner, key: str, name: str, icon: str, block_type: str) -> None:
        self.hass = hass
        self.entry = entry
        self.runner = runner
        self._block_type = block_type
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Свет по движению",
            "manufacturer": "Пользовательская интеграция",
            "model": "Off_light",
        }
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        @callback
        def _on_update(event: Event) -> None:
            if event.data.get("entry_id") == self.entry.entry_id:
                self.async_write_ha_state()
        self._unsub = self.hass.bus.async_listen(f"{DOMAIN}_update", _on_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @property
    def is_on(self) -> bool:
        if self._block_type == "on":
            return self.runner.is_on_block_active()
        return self.runner.is_off_block_active()

    async def async_turn_on(self, **kwargs) -> None:
        if self._block_type == "on":
            self.runner.set_on_block_active(True)
        else:
            self.runner.set_off_block_active(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        if self._block_type == "on":
            self.runner.set_on_block_active(False)
        else:
            self.runner.set_off_block_active(False)
        self.async_write_ha_state()
