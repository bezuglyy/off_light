from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .config_flow import normalize_entry_payload
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
    DATA_CURRENT_ILLUMINANCE,
    DATA_EVENTS,
    DATA_ILLUMINANCE_ALLOWED,
    DATA_OFF_TIME_ALLOWED,
    DATA_BLOCK_REASON,
    DATA_LAST_ACTION,
    DATA_LAST_ACTION_AT,
    DATA_LAST_ERROR,
    DATA_LAST_MOTION_AT,
    DATA_OFF_BLOCK_ACTIVE,
    DATA_MOTION_ACTIVE,
    DATA_MODE,
    DATA_ON_BLOCK_ACTIVE,
    DATA_ON_TIME_ALLOWED,
    DATA_ON_TIMER_FINISH_AT,
    DATA_STATUS,
    DATA_TIMER_FINISH_AT,
    DEFAULT_DELAY_MINUTES,
    DEFAULT_ENABLED,
    DEFAULT_ENABLE_OFF_BLOCK,
    DEFAULT_ENABLE_ON_BLOCK,
    DEFAULT_LIGHTS_ONLY,
    DEFAULT_MAX_ILLUMINANCE,
    DEFAULT_MIN_ILLUMINANCE,
    DEFAULT_ENABLE_OFF_TIME_RANGE,
    DEFAULT_ENABLE_ON_TIME_RANGE,
    DEFAULT_OFF_TIME_END,
    DEFAULT_OFF_TIME_START,
    DEFAULT_ON_DELAY_SECONDS,
    DEFAULT_ON_TIME_END,
    DEFAULT_ON_TIME_START,
    DEFAULT_USE_ILLUMINANCE,
    DOMAIN,
    EVENTS_LIMIT,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)


def _cfg(entry: ConfigEntry, key: str, default=None):
    if entry.options and key in entry.options:
        return entry.options.get(key)
    return entry.data.get(key, default)


def _fmt_dt(value):
    if value is None:
        return None
    return dt_util.as_local(value).isoformat()


class Runner:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.data: dict[str, Any] = {
            DATA_STATUS: "init",
            DATA_LAST_ACTION: None,
            DATA_LAST_ACTION_AT: None,
            DATA_LAST_MOTION_AT: None,
            DATA_TIMER_FINISH_AT: None,
            DATA_ON_TIMER_FINISH_AT: None,
            DATA_LAST_ERROR: None,
            DATA_EVENTS: [],
            DATA_ON_BLOCK_ACTIVE: True,
            DATA_OFF_BLOCK_ACTIVE: True,
            DATA_CURRENT_ILLUMINANCE: None,
            DATA_ILLUMINANCE_ALLOWED: True,
            DATA_ON_TIME_ALLOWED: True,
            DATA_OFF_TIME_ALLOWED: True,
            DATA_MOTION_ACTIVE: False,
            DATA_BLOCK_REASON: "Нет",
            DATA_MODE: "Ожидание",
        }
        self._unsubs: list[Any] = []
        self._off_delay_unsub = None
        self._on_delay_unsub = None

    def _emit(self) -> None:
        self.hass.bus.async_fire(f"{DOMAIN}_update", {"entry_id": self.entry.entry_id})

    def _set_mode(self, mode: str, block_reason: str | None = None) -> None:
        self.data[DATA_MODE] = mode
        self.data[DATA_BLOCK_REASON] = block_reason or "Нет"


    def _push_event(self, etype: str, **data: Any) -> None:
        item = {"ts": dt_util.now().isoformat(), "type": etype, **data}
        events = list(self.data.get(DATA_EVENTS) or [])
        events.append(item)
        self.data[DATA_EVENTS] = events[-EVENTS_LIMIT:]
        self.hass.bus.async_fire(f"{DOMAIN}_event", {"entry_id": self.entry.entry_id, **item})
        self._emit()

    def _is_enabled(self) -> bool:
        return bool(_cfg(self.entry, CONF_ENABLED, DEFAULT_ENABLED))

    def _motion_sensors(self) -> list[str]:
        return list(_cfg(self.entry, CONF_MOTION_SENSORS, []) or [])

    def _on_targets(self) -> list[str]:
        return self._apply_target_filter(list(_cfg(self.entry, CONF_ON_TARGETS, []) or []))

    def _off_targets(self) -> list[str]:
        return self._apply_target_filter(list(_cfg(self.entry, CONF_OFF_TARGETS, []) or []))

    def _off_delay_minutes(self) -> int:
        return int(_cfg(self.entry, CONF_DELAY_MINUTES, DEFAULT_DELAY_MINUTES) or 0)

    def _on_delay_seconds(self) -> int:
        return int(_cfg(self.entry, CONF_ON_DELAY_SECONDS, DEFAULT_ON_DELAY_SECONDS) or 0)

    def _on_block_configured(self) -> bool:
        return bool(_cfg(self.entry, CONF_ENABLE_ON_BLOCK, DEFAULT_ENABLE_ON_BLOCK))

    def _off_block_configured(self) -> bool:
        return bool(_cfg(self.entry, CONF_ENABLE_OFF_BLOCK, DEFAULT_ENABLE_OFF_BLOCK))

    def _lights_only(self) -> bool:
        return bool(_cfg(self.entry, CONF_LIGHTS_ONLY, DEFAULT_LIGHTS_ONLY))

    def _use_illuminance(self) -> bool:
        return bool(_cfg(self.entry, CONF_USE_ILLUMINANCE, DEFAULT_USE_ILLUMINANCE))

    def _illuminance_sensor(self) -> str:
        return str(_cfg(self.entry, CONF_ILLUMINANCE_SENSOR, "") or "")

    def _max_illuminance(self) -> float:
        return float(_cfg(self.entry, CONF_MAX_ILLUMINANCE, DEFAULT_MAX_ILLUMINANCE) or DEFAULT_MAX_ILLUMINANCE)
    def _min_illuminance(self) -> float:
        return float(_cfg(self.entry, CONF_MIN_ILLUMINANCE, DEFAULT_MIN_ILLUMINANCE) or DEFAULT_MIN_ILLUMINANCE)

    def _enable_on_time_range(self) -> bool:
        return bool(_cfg(self.entry, CONF_ENABLE_ON_TIME_RANGE, DEFAULT_ENABLE_ON_TIME_RANGE))

    def _on_time_start(self) -> str:
        return str(_cfg(self.entry, CONF_ON_TIME_START, DEFAULT_ON_TIME_START) or "")

    def _on_time_end(self) -> str:
        return str(_cfg(self.entry, CONF_ON_TIME_END, DEFAULT_ON_TIME_END) or "")

    def _enable_off_time_range(self) -> bool:
        return bool(_cfg(self.entry, CONF_ENABLE_OFF_TIME_RANGE, DEFAULT_ENABLE_OFF_TIME_RANGE))

    def _off_time_start(self) -> str:
        return str(_cfg(self.entry, CONF_OFF_TIME_START, DEFAULT_OFF_TIME_START) or "")

    def _off_time_end(self) -> str:
        return str(_cfg(self.entry, CONF_OFF_TIME_END, DEFAULT_OFF_TIME_END) or "")

    @staticmethod
    def _parse_time_minutes(value: str) -> int | None:
        if not value:
            return None
        try:
            parts = str(value).split(":")
            hh = int(parts[0])
            mm = int(parts[1])
            return hh * 60 + mm
        except Exception:
            return None

    def _is_now_in_range(self, start: str, end: str) -> bool:
        start_m = self._parse_time_minutes(start)
        end_m = self._parse_time_minutes(end)
        if start_m is None or end_m is None:
            return True
        now = dt_util.as_local(dt_util.now())
        cur = now.hour * 60 + now.minute
        if start_m == end_m:
            return True
        if start_m < end_m:
            return start_m <= cur <= end_m
        return cur >= start_m or cur <= end_m

    def _is_on_time_allowed(self) -> bool:
        if not self._enable_on_time_range():
            self.data[DATA_ON_TIME_ALLOWED] = True
            return True
        allowed = self._is_now_in_range(self._on_time_start(), self._on_time_end())
        self.data[DATA_ON_TIME_ALLOWED] = allowed
        return allowed

    def _is_off_time_allowed(self) -> bool:
        if not self._enable_off_time_range():
            self.data[DATA_OFF_TIME_ALLOWED] = True
            return True
        allowed = self._is_now_in_range(self._off_time_start(), self._off_time_end())
        self.data[DATA_OFF_TIME_ALLOWED] = allowed
        return allowed

    def is_on_block_active(self) -> bool:
        return self._on_block_configured() and bool(self.data.get(DATA_ON_BLOCK_ACTIVE, True))

    def is_off_block_active(self) -> bool:
        return self._off_block_configured() and bool(self.data.get(DATA_OFF_BLOCK_ACTIVE, True))

    def set_on_block_active(self, value: bool) -> None:
        self.data[DATA_ON_BLOCK_ACTIVE] = bool(value)
        if not value:
            self._cancel_on_timer()
        self._push_event("on_block_toggled", active=bool(value))
        self._emit()

    def set_off_block_active(self, value: bool) -> None:
        self.data[DATA_OFF_BLOCK_ACTIVE] = bool(value)
        if not value:
            self._cancel_off_timer()
        self._push_event("off_block_toggled", active=bool(value))
        self._emit()

    def _cancel_off_timer(self) -> None:
        if self._off_delay_unsub:
            self._off_delay_unsub()
            self._off_delay_unsub = None
        self.data[DATA_TIMER_FINISH_AT] = None

    def _cancel_on_timer(self) -> None:
        if self._on_delay_unsub:
            self._on_delay_unsub()
            self._on_delay_unsub = None
        self.data[DATA_ON_TIMER_FINISH_AT] = None

    def _cancel_all_timers(self) -> None:
        self._cancel_on_timer()
        self._cancel_off_timer()

    def _any_motion_active(self) -> bool:
        active = False
        for entity_id in self._motion_sensors():
            st = self.hass.states.get(entity_id)
            if st and str(st.state).lower() == "on":
                active = True
                break
        self.data[DATA_MOTION_ACTIVE] = active
        return active

    def _apply_target_filter(self, targets: list[str]) -> list[str]:
        if not self._lights_only():
            return targets
        filtered = [entity_id for entity_id in targets if entity_id.startswith("light.")]
        return filtered

    def _read_illuminance(self) -> float | None:
        sensor = self._illuminance_sensor()
        if not sensor:
            self.data[DATA_CURRENT_ILLUMINANCE] = None
            self.data[DATA_ILLUMINANCE_ALLOWED] = True
            return None
        state = self.hass.states.get(sensor)
        if not state:
            self.data[DATA_CURRENT_ILLUMINANCE] = None
            self.data[DATA_ILLUMINANCE_ALLOWED] = False
            return None
        try:
            value = float(state.state)
        except Exception:
            self.data[DATA_CURRENT_ILLUMINANCE] = None
            self.data[DATA_ILLUMINANCE_ALLOWED] = False
            return None
        self.data[DATA_CURRENT_ILLUMINANCE] = value
        self.data[DATA_ILLUMINANCE_ALLOWED] = self._min_illuminance() <= value <= self._max_illuminance()
        return value

    def _is_illuminance_allowed(self) -> bool:
        if not self._use_illuminance():
            self.data[DATA_ILLUMINANCE_ALLOWED] = True
            return True
        value = self._read_illuminance()
        if value is None:
            return False
        return bool(self.data.get(DATA_ILLUMINANCE_ALLOWED))

    async def _turn_on_targets(self) -> None:
        targets = self._on_targets()
        if not self._is_enabled() or not self.is_on_block_active():
            return
        if not targets:
            self._set_mode("Ожидание", "Не выбраны устройства для включения")
            self._push_event("skip", reason="no_on_targets")
            return
        if not self._any_motion_active():
            self._set_mode("Ожидание", "Движение пропало до включения")
            self._push_event("cancelled", reason="motion_missing_before_on")
            return
        if not self._is_on_time_allowed():
            self.data[DATA_STATUS] = "on_time_blocked"
            self._set_mode("Блокировка", "Вне разрешённого времени включения")
            self._push_event(
                "skip",
                reason="on_time_blocked",
                start=self._on_time_start(),
                end=self._on_time_end(),
            )
            self._emit()
            return
        if not self._is_illuminance_allowed():
            self.data[DATA_STATUS] = "bright_enough"
            self._set_mode("Блокировка", "Освещённость вне диапазона")
            self._push_event(
                "skip",
                reason="illuminance_blocked",
                illuminance=self.data.get(DATA_CURRENT_ILLUMINANCE),
                min_illuminance=self._min_illuminance(),
                max_illuminance=self._max_illuminance(),
            )
            self._emit()
            return
        try:
            self.data[DATA_STATUS] = "turning_on"
            self._set_mode("Включение", None)
            self._emit()
            await self.hass.services.async_call(
                "homeassistant",
                "turn_on",
                {"entity_id": targets},
                blocking=True,
            )
            self.data[DATA_LAST_ACTION] = "turn_on"
            self.data[DATA_LAST_ACTION_AT] = dt_util.now()
            self.data[DATA_LAST_ERROR] = None
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
            self._set_mode("Движение", None)
            self._push_event("turned_on", targets=targets)
        except Exception as exc:
            self.data[DATA_LAST_ERROR] = str(exc)
            self.data[DATA_STATUS] = "error"
            self._set_mode("Ошибка", str(exc))
            _LOGGER.exception("Failed to turn on targets")
            self._push_event("error", error=str(exc), action="turn_on")
        finally:
            self._cancel_on_timer()
            self._emit()

    async def _turn_off_targets(self) -> None:
        targets = self._off_targets()
        if not self._is_enabled():
            self.data[DATA_STATUS] = "disabled"
            self._set_mode("Отключено", None)
            self._set_mode("Отключено", None)
            self._emit()
            return
        if not self.is_off_block_active():
            self.data[DATA_STATUS] = "idle"
            self._set_mode("Ожидание", None)
            self._set_mode("Ожидание", "Блок выключения отключён")
            self._cancel_off_timer()
            self._push_event("cancelled", reason="off_block_disabled")
            return
        if not targets:
            self.data[DATA_STATUS] = "idle"
            self._set_mode("Ожидание", None)
            self._set_mode("Ожидание", "Не выбраны устройства для выключения")
            self._push_event("skip", reason="no_off_targets")
            return
        if self._any_motion_active():
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
            self._set_mode("Движение", None)
            self._push_event("cancelled", reason="motion_returned")
            return
        if not self._is_off_time_allowed():
            self.data[DATA_STATUS] = "off_time_blocked"
            self._set_mode("Блокировка", "Вне разрешённого времени выключения")
            self._push_event(
                "skip",
                reason="off_time_blocked",
                start=self._off_time_start(),
                end=self._off_time_end(),
            )
            self._emit()
            return
        try:
            self.data[DATA_STATUS] = "turning_off"
            self._set_mode("Выключение", None)
            self._emit()
            await self.hass.services.async_call(
                "homeassistant",
                "turn_off",
                {"entity_id": targets},
                blocking=True,
            )
            self.data[DATA_LAST_ACTION] = "turn_off"
            self.data[DATA_LAST_ACTION_AT] = dt_util.now()
            self.data[DATA_LAST_ERROR] = None
            self.data[DATA_STATUS] = "idle"
            self._set_mode("Ожидание", None)
            self._set_mode("Ожидание", None)
            self._push_event("turned_off", targets=targets)
        except Exception as exc:
            self.data[DATA_LAST_ERROR] = str(exc)
            self.data[DATA_STATUS] = "error"
            self._set_mode("Ошибка", str(exc))
            _LOGGER.exception("Failed to turn off targets")
            self._push_event("error", error=str(exc), action="turn_off")
        finally:
            self._cancel_off_timer()
            self._emit()

    def _schedule_turn_off(self) -> None:
        if not self.is_off_block_active():
            self.data[DATA_STATUS] = "idle"
            self._set_mode("Ожидание", None)
            self._set_mode("Ожидание", "Блок выключения отключён")
            self._cancel_off_timer()
            self._emit()
            return
        self._cancel_off_timer()
        delay = self._off_delay_minutes()
        run_at = dt_util.now() + timedelta(minutes=delay)
        self.data[DATA_TIMER_FINISH_AT] = run_at
        self.data[DATA_STATUS] = "delay_running" if delay > 0 else "pending_off"
        self._set_mode("Ожидание выключения", None)
        self._push_event("timer_started", delay_minutes=delay, run_at=_fmt_dt(run_at))

        @callback
        def _run(_now):
            self.hass.async_create_task(self._turn_off_targets())

        self._off_delay_unsub = async_call_later(self.hass, max(0, delay * 60), _run)
        self._emit()

    def _schedule_turn_on(self) -> None:
        if not self.is_on_block_active():
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
            self._set_mode("Движение", "Блок включения отключён")
            self._cancel_on_timer()
            self._emit()
            return
        self._cancel_on_timer()
        delay = self._on_delay_seconds()
        run_at = dt_util.now() + timedelta(seconds=delay)
        self.data[DATA_ON_TIMER_FINISH_AT] = run_at
        self.data[DATA_STATUS] = "on_delay_running" if delay > 0 else "turning_on"
        self._set_mode("Ожидание включения", None)
        self._push_event("on_timer_started", delay_seconds=delay, run_at=_fmt_dt(run_at))

        @callback
        def _run(_now):
            self.hass.async_create_task(self._turn_on_targets())

        self._on_delay_unsub = async_call_later(self.hass, max(0, delay), _run)
        self._emit()

    @callback
    def _handle_motion_event(self, event: Event) -> None:
        if not self._is_enabled():
            self.data[DATA_STATUS] = "disabled"
            self._set_mode("Отключено", None)
            self._set_mode("Отключено", None)
            self._cancel_all_timers()
            self._emit()
            return

        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        state_value = getattr(new_state, "state", None)
        if state_value is None:
            return
        state_value = str(state_value).lower()

        self._push_event("motion_changed", entity_id=entity_id, state=state_value)

        if state_value == "on":
            self.data[DATA_LAST_MOTION_AT] = dt_util.now()
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
            self._set_mode("Движение", None)
            self._cancel_off_timer()
            self._emit()
            self._schedule_turn_on()
            return

        if state_value != "off":
            return

        self._cancel_on_timer()
        if self._any_motion_active():
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
            self._set_mode("Движение", None)
            self._cancel_off_timer()
            self._emit()
            return

        self._schedule_turn_off()

    async def async_start(self) -> None:
        self.data[DATA_STATUS] = "starting"
        self.data[DATA_ON_BLOCK_ACTIVE] = self._on_block_configured()
        self.data[DATA_OFF_BLOCK_ACTIVE] = self._off_block_configured()
        self._read_illuminance()
        self._emit()
        sensors = self._motion_sensors()
        if sensors:
            self._unsubs.append(async_track_state_change_event(self.hass, sensors, self._handle_motion_event))

        if not self._is_enabled():
            self.data[DATA_STATUS] = "disabled"
            self._set_mode("Отключено", None)
        elif self._any_motion_active():
            self.data[DATA_STATUS] = "motion_detected"
            self._set_mode("Движение", None)
        else:
            self.data[DATA_STATUS] = "idle"
            self._set_mode("Ожидание", None)
        self._push_event(
            "started",
            sensors=sensors,
            on_targets=self._on_targets(),
            off_targets=self._off_targets(),
            delay_minutes=self._off_delay_minutes(),
            on_delay_seconds=self._on_delay_seconds(),
            lights_only=self._lights_only(),
            use_illuminance=self._use_illuminance(),
            illuminance_sensor=self._illuminance_sensor(),
            min_illuminance=self._min_illuminance(),
            max_illuminance=self._max_illuminance(),
            enable_on_time_range=self._enable_on_time_range(),
            on_time_start=self._on_time_start(),
            on_time_end=self._on_time_end(),
            enable_off_time_range=self._enable_off_time_range(),
            off_time_start=self._off_time_start(),
            off_time_end=self._off_time_end(),
            on_block=self.is_on_block_active(),
            off_block=self.is_off_block_active(),
        )
        self._emit()

    async def async_stop(self) -> None:
        self._cancel_all_timers()
        for unsub in self._unsubs:
            try:
                unsub()
            except Exception:
                pass
        self._unsubs.clear()
        self.data[DATA_STATUS] = "stopped"
        self._set_mode("Остановлено", None)
        self._push_event("stopped")
        self._emit()


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        data = dict(entry.data or {})
        options = dict(entry.options or {})

        if entry.version < 2:
            if "targets" in data and CONF_OFF_TARGETS not in data:
                data[CONF_OFF_TARGETS] = data.pop("targets")
            if "targets" in options and CONF_OFF_TARGETS not in options:
                options[CONF_OFF_TARGETS] = options.pop("targets")
            data.setdefault(CONF_ENABLE_ON_BLOCK, False)
            options.setdefault(CONF_ENABLE_ON_BLOCK, False)
            data.setdefault(CONF_ENABLE_OFF_BLOCK, True)
            options.setdefault(CONF_ENABLE_OFF_BLOCK, True)
            data.setdefault(CONF_ON_TARGETS, [])
            options.setdefault(CONF_ON_TARGETS, [])

        if entry.version < 3:
            for payload in (data, options):
                payload.setdefault(CONF_ON_DELAY_SECONDS, DEFAULT_ON_DELAY_SECONDS)
                payload.setdefault(CONF_LIGHTS_ONLY, DEFAULT_LIGHTS_ONLY)
                payload.setdefault(CONF_USE_ILLUMINANCE, DEFAULT_USE_ILLUMINANCE)
                payload.setdefault(CONF_ILLUMINANCE_SENSOR, "")
                payload.setdefault(CONF_MAX_ILLUMINANCE, DEFAULT_MAX_ILLUMINANCE)

        if entry.version < 4:
            for payload in (data, options):
                payload.setdefault(CONF_MIN_ILLUMINANCE, DEFAULT_MIN_ILLUMINANCE)
                payload.setdefault(CONF_ON_TIME_START, DEFAULT_ON_TIME_START)
                payload.setdefault(CONF_ON_TIME_END, DEFAULT_ON_TIME_END)
                payload.setdefault(CONF_OFF_TIME_START, DEFAULT_OFF_TIME_START)
                payload.setdefault(CONF_OFF_TIME_END, DEFAULT_OFF_TIME_END)

        if entry.version < 5:
            for payload in (data, options):
                payload.setdefault(CONF_ENABLE_ON_TIME_RANGE, DEFAULT_ENABLE_ON_TIME_RANGE)
                payload.setdefault(CONF_ENABLE_OFF_TIME_RANGE, DEFAULT_ENABLE_OFF_TIME_RANGE)

        new_data = normalize_entry_payload(data)
        new_options = normalize_entry_payload(options) if options else {}
        changed = (new_data != (entry.data or {})) or (new_options != (entry.options or {})) or entry.version < 5
        if changed:
            hass.config_entries.async_update_entry(entry, data=new_data, options=new_options, version=5)
        return True
    except Exception:
        _LOGGER.exception("Failed to migrate config entry %s", entry.entry_id)
        return False


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    if entry.title != "Свет по движению":
        hass.config_entries.async_update_entry(entry, title="Свет по движению")
    runner = Runner(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    hass.data[DOMAIN][entry.entry_id] = runner
    await runner.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runner = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runner:
        await runner.async_stop()
    return unload_ok
