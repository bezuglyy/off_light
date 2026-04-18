from __future__ import annotations

DOMAIN = "off_light"
PLATFORMS: list[str] = ["sensor", "switch"]

CONF_ENABLED = "enabled"
CONF_MOTION_SENSORS = "motion_sensors"
CONF_ON_TARGETS = "on_targets"
CONF_OFF_TARGETS = "off_targets"
CONF_DELAY_MINUTES = "delay_minutes"
CONF_ON_DELAY_SECONDS = "on_delay_seconds"
CONF_ENABLE_ON_BLOCK = "enable_on_block"
CONF_ENABLE_OFF_BLOCK = "enable_off_block"
CONF_LIGHTS_ONLY = "lights_only"
CONF_USE_ILLUMINANCE = "use_illuminance"
CONF_ILLUMINANCE_SENSOR = "illuminance_sensor"
CONF_MIN_ILLUMINANCE = "min_illuminance"
CONF_MAX_ILLUMINANCE = "max_illuminance"
CONF_ENABLE_ON_TIME_RANGE = "enable_on_time_range"
CONF_ON_TIME_START = "on_time_start"
CONF_ON_TIME_END = "on_time_end"
CONF_ENABLE_OFF_TIME_RANGE = "enable_off_time_range"
CONF_OFF_TIME_START = "off_time_start"
CONF_OFF_TIME_END = "off_time_end"
CONF_RESET_OPTIONS = "reset_options"

DATA_STATUS = "status"
DATA_LAST_ACTION = "last_action"
DATA_LAST_ACTION_AT = "last_action_at"
DATA_LAST_MOTION_AT = "last_motion_at"
DATA_TIMER_FINISH_AT = "timer_finish_at"
DATA_ON_TIMER_FINISH_AT = "on_timer_finish_at"
DATA_EVENTS = "events"
DATA_LAST_ERROR = "last_error"
DATA_ON_BLOCK_ACTIVE = "on_block_active"
DATA_OFF_BLOCK_ACTIVE = "off_block_active"
DATA_CURRENT_ILLUMINANCE = "current_illuminance"
DATA_ILLUMINANCE_ALLOWED = "illuminance_allowed"
DATA_ON_TIME_ALLOWED = "on_time_allowed"
DATA_OFF_TIME_ALLOWED = "off_time_allowed"

DATA_MOTION_ACTIVE = "motion_active"
DATA_BLOCK_REASON = "block_reason"
DATA_MODE = "mode"

DEFAULT_ENABLED = True
DEFAULT_DELAY_MINUTES = 0
DEFAULT_ON_DELAY_SECONDS = 0
DEFAULT_ENABLE_ON_BLOCK = True
DEFAULT_ENABLE_OFF_BLOCK = True
DEFAULT_LIGHTS_ONLY = False
DEFAULT_USE_ILLUMINANCE = False
DEFAULT_MIN_ILLUMINANCE = 0.0
DEFAULT_MAX_ILLUMINANCE = 50.0
DEFAULT_ENABLE_ON_TIME_RANGE = False
DEFAULT_ON_TIME_START = ""
DEFAULT_ON_TIME_END = ""
DEFAULT_ENABLE_OFF_TIME_RANGE = False
DEFAULT_OFF_TIME_START = ""
DEFAULT_OFF_TIME_END = ""
EVENTS_LIMIT = 50
