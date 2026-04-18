from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DELAY_MINUTES,
    CONF_ENABLED,
    CONF_ENABLE_OFF_BLOCK,
    CONF_ENABLE_OFF_TIME_RANGE,
    CONF_ENABLE_ON_BLOCK,
    CONF_ENABLE_ON_TIME_RANGE,
    CONF_ILLUMINANCE_SENSOR,
    CONF_LIGHTS_ONLY,
    CONF_MAX_ILLUMINANCE,
    CONF_MIN_ILLUMINANCE,
    CONF_MOTION_SENSORS,
    CONF_OFF_TARGETS,
    CONF_OFF_TIME_END,
    CONF_OFF_TIME_START,
    CONF_ON_DELAY_SECONDS,
    CONF_ON_TARGETS,
    CONF_ON_TIME_END,
    CONF_ON_TIME_START,
    CONF_USE_ILLUMINANCE,
    DEFAULT_DELAY_MINUTES,
    DEFAULT_ENABLED,
    DEFAULT_ENABLE_OFF_BLOCK,
    DEFAULT_ENABLE_OFF_TIME_RANGE,
    DEFAULT_ENABLE_ON_BLOCK,
    DEFAULT_ENABLE_ON_TIME_RANGE,
    DEFAULT_LIGHTS_ONLY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_ON_DELAY_SECONDS,
    DEFAULT_USE_ILLUMINANCE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
SAFE_ON_TIME_START = "00:00:00"
SAFE_ON_TIME_END = "23:59:00"
SAFE_OFF_TIME_START = "00:00:00"
SAFE_OFF_TIME_END = "23:59:00"


def _motion_selector():
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="binary_sensor", multiple=True)
    )


def _sensor_selector():
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="sensor", multiple=False)
    )


def _target_selector():
    return selector.EntitySelector(
        selector.EntitySelectorConfig(multiple=True)
    )


def _time_selector():
    return selector.TimeSelector()


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, dict):
        entity_ids = value.get("entity_id")
        if isinstance(entity_ids, list):
            return [x for x in entity_ids if isinstance(x, str) and x.strip()]
        if isinstance(entity_ids, str) and entity_ids.strip():
            return [entity_ids.strip()]
        return []
    if isinstance(value, (list, tuple)):
        return [x for x in value if isinstance(x, str) and x.strip()]
    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []
    return []


def _as_int(value, default: int) -> int:
    try:
        if value in (None, ""):
            return int(default)
        return int(float(value))
    except Exception:
        return int(default)


def _as_float(value, default: float) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _as_time_str(value, *, default: str = "") -> str:
    if value in (None, ""):
        return default
    text = str(value).strip()
    if not text:
        return default
    parts = text.split(":")
    if len(parts) == 2:
        hh, mm = parts
        ss = "00"
    elif len(parts) == 3:
        hh, mm, ss = parts
    else:
        return default
    try:
        hh_i = int(hh)
        mm_i = int(mm)
        ss_i = int(ss)
    except Exception:
        return default
    if not (0 <= hh_i <= 23 and 0 <= mm_i <= 59 and 0 <= ss_i <= 59):
        return default
    return f"{hh_i:02d}:{mm_i:02d}:{ss_i:02d}"


def normalize_entry_payload(data: dict | None) -> dict:
    data = dict(data or {})
    data[CONF_ENABLED] = bool(data.get(CONF_ENABLED, DEFAULT_ENABLED))
    data[CONF_ENABLE_ON_BLOCK] = bool(data.get(CONF_ENABLE_ON_BLOCK, DEFAULT_ENABLE_ON_BLOCK))
    data[CONF_ENABLE_OFF_BLOCK] = bool(data.get(CONF_ENABLE_OFF_BLOCK, DEFAULT_ENABLE_OFF_BLOCK))
    data[CONF_LIGHTS_ONLY] = bool(data.get(CONF_LIGHTS_ONLY, DEFAULT_LIGHTS_ONLY))
    data[CONF_USE_ILLUMINANCE] = bool(data.get(CONF_USE_ILLUMINANCE, DEFAULT_USE_ILLUMINANCE))
    data[CONF_ENABLE_ON_TIME_RANGE] = bool(data.get(CONF_ENABLE_ON_TIME_RANGE, DEFAULT_ENABLE_ON_TIME_RANGE))
    data[CONF_ENABLE_OFF_TIME_RANGE] = bool(data.get(CONF_ENABLE_OFF_TIME_RANGE, DEFAULT_ENABLE_OFF_TIME_RANGE))
    data[CONF_MOTION_SENSORS] = _as_list(data.get(CONF_MOTION_SENSORS))
    data[CONF_ON_TARGETS] = _as_list(data.get(CONF_ON_TARGETS))
    data[CONF_OFF_TARGETS] = _as_list(data.get(CONF_OFF_TARGETS))
    data[CONF_DELAY_MINUTES] = max(0, min(10, _as_int(data.get(CONF_DELAY_MINUTES), DEFAULT_DELAY_MINUTES)))
    data[CONF_ON_DELAY_SECONDS] = max(0, min(300, _as_int(data.get(CONF_ON_DELAY_SECONDS), DEFAULT_ON_DELAY_SECONDS)))
    sensor = data.get(CONF_ILLUMINANCE_SENSOR)
    data[CONF_ILLUMINANCE_SENSOR] = sensor if isinstance(sensor, str) and sensor.strip() else None
    data[CONF_MIN_ILLUMINANCE] = max(0.0, min(5000.0, _as_float(data.get(CONF_MIN_ILLUMINANCE), DEFAULT_MIN_ILLUMINANCE)))
    data[CONF_MAX_ILLUMINANCE] = max(0.0, min(5000.0, _as_float(data.get(CONF_MAX_ILLUMINANCE), DEFAULT_MAX_ILLUMINANCE)))
    if data[CONF_MIN_ILLUMINANCE] > data[CONF_MAX_ILLUMINANCE]:
        data[CONF_MIN_ILLUMINANCE], data[CONF_MAX_ILLUMINANCE] = data[CONF_MAX_ILLUMINANCE], data[CONF_MIN_ILLUMINANCE]

    data[CONF_ON_TIME_START] = _as_time_str(
        data.get(CONF_ON_TIME_START),
        default=SAFE_ON_TIME_START if data[CONF_ENABLE_ON_TIME_RANGE] else "",
    )
    data[CONF_ON_TIME_END] = _as_time_str(
        data.get(CONF_ON_TIME_END),
        default=SAFE_ON_TIME_END if data[CONF_ENABLE_ON_TIME_RANGE] else "",
    )
    data[CONF_OFF_TIME_START] = _as_time_str(
        data.get(CONF_OFF_TIME_START),
        default=SAFE_OFF_TIME_START if data[CONF_ENABLE_OFF_TIME_RANGE] else "",
    )
    data[CONF_OFF_TIME_END] = _as_time_str(
        data.get(CONF_OFF_TIME_END),
        default=SAFE_OFF_TIME_END if data[CONF_ENABLE_OFF_TIME_RANGE] else "",
    )
    return data


def _validate(data: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not data.get(CONF_ENABLED, DEFAULT_ENABLED):
        return errors

    if not data.get(CONF_MOTION_SENSORS):
        errors["base"] = "need_motion_sensors"
        return errors

    if not data.get(CONF_ENABLE_ON_BLOCK, DEFAULT_ENABLE_ON_BLOCK) and not data.get(CONF_ENABLE_OFF_BLOCK, DEFAULT_ENABLE_OFF_BLOCK):
        errors["base"] = "need_one_block"
        return errors

    if data.get(CONF_ENABLE_ON_BLOCK, DEFAULT_ENABLE_ON_BLOCK) and not data.get(CONF_ON_TARGETS):
        errors["base"] = "need_on_targets"
        return errors

    if data.get(CONF_ENABLE_OFF_BLOCK, DEFAULT_ENABLE_OFF_BLOCK) and not data.get(CONF_OFF_TARGETS):
        errors["base"] = "need_off_targets"
        return errors

    if data.get(CONF_ENABLE_ON_TIME_RANGE, DEFAULT_ENABLE_ON_TIME_RANGE):
        if not data.get(CONF_ON_TIME_START) or not data.get(CONF_ON_TIME_END):
            errors["base"] = "need_on_time_range"
            return errors

    if data.get(CONF_ENABLE_OFF_TIME_RANGE, DEFAULT_ENABLE_OFF_TIME_RANGE):
        if not data.get(CONF_OFF_TIME_START) or not data.get(CONF_OFF_TIME_END):
            errors["base"] = "need_off_time_range"
            return errors

    if data.get(CONF_USE_ILLUMINANCE, DEFAULT_USE_ILLUMINANCE) and not data.get(CONF_ILLUMINANCE_SENSOR):
        errors["base"] = "need_illuminance_sensor"
        return errors

    return errors


def build_schema(data: dict) -> vol.Schema:
    fields: dict = {
        vol.Optional(CONF_ENABLED, default=bool(data[CONF_ENABLED])): selector.BooleanSelector(),
        vol.Optional(CONF_MOTION_SENSORS, default=list(data[CONF_MOTION_SENSORS])): _motion_selector(),
        vol.Optional(CONF_ENABLE_ON_BLOCK, default=bool(data[CONF_ENABLE_ON_BLOCK])): selector.BooleanSelector(),
        vol.Optional(CONF_ON_TARGETS, default=list(data[CONF_ON_TARGETS])): _target_selector(),
        vol.Optional(CONF_ON_DELAY_SECONDS, default=int(data[CONF_ON_DELAY_SECONDS])): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=300, step=5, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(CONF_ENABLE_ON_TIME_RANGE, default=bool(data[CONF_ENABLE_ON_TIME_RANGE])): selector.BooleanSelector(),
        vol.Optional(CONF_ON_TIME_START, default=(data[CONF_ON_TIME_START] or SAFE_ON_TIME_START)): _time_selector(),
        vol.Optional(CONF_ON_TIME_END, default=(data[CONF_ON_TIME_END] or SAFE_ON_TIME_END)): _time_selector(),
        vol.Optional(CONF_ENABLE_OFF_BLOCK, default=bool(data[CONF_ENABLE_OFF_BLOCK])): selector.BooleanSelector(),
        vol.Optional(CONF_OFF_TARGETS, default=list(data[CONF_OFF_TARGETS])): _target_selector(),
        vol.Optional(CONF_DELAY_MINUTES, default=int(data[CONF_DELAY_MINUTES])): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=10, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Optional(CONF_ENABLE_OFF_TIME_RANGE, default=bool(data[CONF_ENABLE_OFF_TIME_RANGE])): selector.BooleanSelector(),
        vol.Optional(CONF_OFF_TIME_START, default=(data[CONF_OFF_TIME_START] or SAFE_OFF_TIME_START)): _time_selector(),
        vol.Optional(CONF_OFF_TIME_END, default=(data[CONF_OFF_TIME_END] or SAFE_OFF_TIME_END)): _time_selector(),
        vol.Optional(CONF_LIGHTS_ONLY, default=bool(data[CONF_LIGHTS_ONLY])): selector.BooleanSelector(),
        vol.Optional(CONF_USE_ILLUMINANCE, default=bool(data[CONF_USE_ILLUMINANCE])): selector.BooleanSelector(),
        vol.Optional(CONF_MIN_ILLUMINANCE, default=float(data[CONF_MIN_ILLUMINANCE])): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=5000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_MAX_ILLUMINANCE, default=float(data[CONF_MAX_ILLUMINANCE])): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=5000, step=1, mode=selector.NumberSelectorMode.BOX)
        ),
    }

    illuminance_sensor = data.get(CONF_ILLUMINANCE_SENSOR)
    if isinstance(illuminance_sensor, str) and illuminance_sensor.strip():
        fields[vol.Optional(CONF_ILLUMINANCE_SENSOR, default=illuminance_sensor)] = _sensor_selector()
    else:
        fields[vol.Optional(CONF_ILLUMINANCE_SENSOR)] = _sensor_selector()

    return vol.Schema(fields)

class OffLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 7

    async def async_step_user(self, user_input=None):
        errors = {}
        defaults = normalize_entry_payload(user_input or {})
        if user_input is not None:
            try:
                defaults = normalize_entry_payload(user_input)
                errors = _validate(defaults)
                if not errors:
                    return self.async_create_entry(title="Свет по движению", data=defaults)
            except Exception:
                _LOGGER.exception("Validation failed")
                errors["base"] = "internal_error"

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema(defaults),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OffLightOptionsFlowHandler(config_entry)


class OffLightOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        merged = normalize_entry_payload(self._config_entry.data)
        merged.update(normalize_entry_payload(dict(self._config_entry.options)))
        defaults = normalize_entry_payload(merged)

        if user_input is not None:
            try:
                defaults = normalize_entry_payload({**merged, **user_input})
                errors = _validate(defaults)
                if not errors:
                    return self.async_create_entry(title="", data=defaults)
            except Exception:
                _LOGGER.exception("Options validation failed")
                errors["base"] = "internal_error"

        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(defaults),
            errors=errors,
        )
