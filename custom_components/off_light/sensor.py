from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DATA_CURRENT_ILLUMINANCE,
    DATA_EVENTS,
    DATA_BLOCK_REASON,
    DATA_ILLUMINANCE_ALLOWED,
    DATA_LAST_ACTION,
    DATA_LAST_ACTION_AT,
    DATA_LAST_ERROR,
    DATA_LAST_MOTION_AT,
    DATA_MOTION_ACTIVE,
    DATA_MODE,
    DATA_OFF_BLOCK_ACTIVE,
    DATA_OFF_TIME_ALLOWED,
    DATA_ON_BLOCK_ACTIVE,
    DATA_ON_TIME_ALLOWED,
    DATA_ON_TIMER_FINISH_AT,
    DATA_STATUS,
    DATA_TIMER_FINISH_AT,
    DOMAIN,
)


@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    data_key: str
    include_details: bool = False


SENSORS: tuple[Desc, ...] = (
    Desc(key="mode", name="Режим", icon="mdi:state-machine", data_key=DATA_MODE, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="status", name="Статус", icon="mdi:motion-sensor", data_key=DATA_STATUS, entity_category=EntityCategory.DIAGNOSTIC, include_details=True),
    Desc(key="motion_active", name="Движение сейчас", icon="mdi:walk", data_key=DATA_MOTION_ACTIVE, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="block_reason", name="Причина блокировки", icon="mdi:block-helper", data_key=DATA_BLOCK_REASON, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="last_action", name="Последнее действие", icon="mdi:flash-outline", data_key=DATA_LAST_ACTION, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="last_action_at", name="Время последнего действия", icon="mdi:clock-outline", data_key=DATA_LAST_ACTION_AT, device_class="timestamp", entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="last_motion_at", name="Последнее движение", icon="mdi:run-fast", data_key=DATA_LAST_MOTION_AT, device_class="timestamp", entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="on_timer_finish_at", name="Включение по таймеру", icon="mdi:timer-play-outline", data_key=DATA_ON_TIMER_FINISH_AT, device_class="timestamp", entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="timer_finish_at", name="Выключение по таймеру", icon="mdi:timer-stop-outline", data_key=DATA_TIMER_FINISH_AT, device_class="timestamp", entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="current_illuminance", name="Текущая освещённость", icon="mdi:brightness-6", data_key=DATA_CURRENT_ILLUMINANCE, native_unit_of_measurement="lx", entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="illuminance_allowed", name="Разрешение по освещённости", icon="mdi:theme-light-dark", data_key=DATA_ILLUMINANCE_ALLOWED, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="on_time_allowed", name="Разрешение по времени включения", icon="mdi:clock-check-outline", data_key=DATA_ON_TIME_ALLOWED, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="off_time_allowed", name="Разрешение по времени выключения", icon="mdi:clock-end", data_key=DATA_OFF_TIME_ALLOWED, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="on_block_active", name="Блок включения", icon="mdi:lightbulb-auto", data_key=DATA_ON_BLOCK_ACTIVE, entity_category=EntityCategory.DIAGNOSTIC),
    Desc(key="off_block_active", name="Блок выключения", icon="mdi:lightbulb-off-outline", data_key=DATA_OFF_BLOCK_ACTIVE, entity_category=EntityCategory.DIAGNOSTIC),
)

STATUS_TRANSLATIONS = {
    "init": "Инициализация",
    "starting": "Запуск",
    "disabled": "Отключено",
    "idle": "Ожидание",
    "motion_detected": "Обнаружено движение",
    "delay_running": "Идёт задержка выключения",
    "on_delay_running": "Идёт задержка включения",
    "pending_off": "Ожидает выключения",
    "bright_enough": "Светло, включение запрещено",
    "turning_on": "Включение устройств",
    "turning_off": "Выключение устройств",
    "error": "Ошибка",
    "stopped": "Остановлено",
}

ACTION_TRANSLATIONS = {
    None: None,
    "turn_on": "Включить",
    "turn_off": "Выключить",
}

BOOL_TRANSLATIONS = {
    True: "Да",
    False: "Нет",
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    runner = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([OffLightSensor(hass, entry, runner, desc) for desc in SENSORS])


class OffLightSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runner, desc: Desc) -> None:
        self.hass = hass
        self.entry = entry
        self.runner = runner
        self.entity_description = desc
        self._attr_unique_id = f"{entry.entry_id}_{desc.key}"
        if desc.data_key == DATA_CURRENT_ILLUMINANCE:
            self._attr_native_unit_of_measurement = "lx"
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
    def native_value(self):
        value = self.runner.data.get(self.entity_description.data_key)
        if self.entity_description.data_key == DATA_STATUS and isinstance(value, str):
            return STATUS_TRANSLATIONS.get(value, value)
        if self.entity_description.data_key == DATA_LAST_ACTION and isinstance(value, str):
            return ACTION_TRANSLATIONS.get(value, value)
        if self.entity_description.data_key in (DATA_ON_BLOCK_ACTIVE, DATA_OFF_BLOCK_ACTIVE, DATA_ILLUMINANCE_ALLOWED, DATA_ON_TIME_ALLOWED, DATA_OFF_TIME_ALLOWED, DATA_MOTION_ACTIVE):
            return BOOL_TRANSLATIONS.get(bool(value))
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not self.entity_description.include_details:
            return None
        events = list(self.runner.data.get(DATA_EVENTS) or [])
        return {
            "entry_id": self.entry.entry_id,
            "last_error": self.runner.data.get(DATA_LAST_ERROR),
            "events_count": len(events),
            "events": events,
        }
