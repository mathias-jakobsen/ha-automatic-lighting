#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_BRIGHTNESS_PCT, ATTR_KELVIN, ATTR_RGB_COLOR, VALID_BRIGHTNESS, VALID_BRIGHTNESS_PCT
from homeassistant.const import CONF_DELAY, CONF_ID
from homeassistant.helpers import config_validation as cv
import voluptuous as vol


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

# ------ Configuration ---------------
CONF_BLOCK_DURATION = "block_duration"
CONF_DURATION = "duration"
CONF_LIGHT_GROUPS = "light_groups"
CONF_LIGHTS = "lights"
CONF_STATUS = "status"

# --- Attributes ----------
ATTR_BLOCKED_UNTIL = "blocked_until"
ATTR_STATUS = "status"
ATTR_UNTIL = "until"

# ------ Defaults ---------------
DEFAULT_BLOCK_DURATION = 300

# ------ Events ---------------
EVENT_DATA_TYPE_REQUEST = "request"
EVENT_DATA_TYPE_RESET = "reset"
EVENT_TYPE_AUTOMATIC_LIGHTING = "automatic_lighting_event"

# ------ Services ---------------
SERVICE_BLOCK = "block"
SERVICE_TRACK_LIGHTS = "track_lights"

# ------ States ---------------
STATUS_ACTIVE = "active"
STATUS_BLOCKED = "blocked"
STATUS_IDLE = "idle"

# ------ Validators ---------------
VALID_COLOR_NAME = cv.string
VALID_COLOR_TEMP = vol.All(vol.Coerce(int), vol.Range(min=1))
VALID_HS_COLOR = vol.All(vol.ExactSequence((vol.All(vol.Coerce(float), vol.Range(min=0, max=360)), vol.All(vol.Coerce(float), vol.Range(min=0, max=100)))),vol.Coerce(tuple))
VALID_KELVIN = cv.positive_int
VALID_RGB_COLOR = vol.All(vol.ExactSequence((cv.byte, cv.byte, cv.byte)), vol.Coerce(tuple))
VALID_XY_COLOR = vol.All(vol.ExactSequence((cv.small_float, cv.small_float)), vol.Coerce(tuple))
VALID_WHITE_VALUE = vol.All(vol.Coerce(int), vol.Range(min=0, max=255))


#-----------------------------------------------------------#
#       Schemas
#-----------------------------------------------------------#

SERVICE_SCHEMA_BLOCK = {
    vol.Optional(CONF_DURATION): cv.positive_int
}

SERVICE_SCHEMA_TRACK_LIGHTS = {
    vol.Required(CONF_LIGHTS): vol.Any(dict, list, str)
}

SERVICE_SCHEMA_TURN_OFF = {
    vol.Optional(CONF_DELAY): cv.positive_int
}

SERVICE_SCHEMA_TURN_ON = {
    vol.Required(CONF_ID): vol.Any(str, int),
    vol.Required(CONF_STATUS): vol.In([STATUS_ACTIVE, STATUS_IDLE]),
    vol.Required(CONF_LIGHTS): vol.Any(dict, list, str),
    vol.Optional(ATTR_BRIGHTNESS): VALID_BRIGHTNESS,
    vol.Optional(ATTR_BRIGHTNESS_PCT): VALID_BRIGHTNESS_PCT,
    vol.Optional(ATTR_KELVIN): VALID_KELVIN,
    vol.Optional(ATTR_RGB_COLOR): VALID_RGB_COLOR,
}