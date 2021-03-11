# -----------------------------------------------------------#
#       Imports
# -----------------------------------------------------------#

from homeassistant.components.automation import EVENT_AUTOMATION_RELOADED
from . import DOMAIN_FRIENDLY_NAME, LOGGER_BASE_NAME
from .const import ATTR_BLOCKED_UNTIL, ATTR_STATUS, CONF_BLOCK_DURATION, CONF_LIGHT_GROUPS, CONF_STATUS, DEFAULT_BLOCK_DURATION, EVENT_DATA_TYPE_REQUEST, EVENT_DATA_TYPE_RESET, EVENT_TYPE_AUTOMATIC_LIGHTING, SERVICE_SCHEMA_TRACK_LIGHTS, SERVICE_SCHEMA_TURN_ON, SERVICE_TRACK_LIGHTS, STATUS_ACTIVE, STATUS_BLOCKED, STATUS_IDLE
from .helpers import EntityBase, Profile, async_resolve_target, list_merge_unique, track_automations_changed, track_manual_control
from datetime import datetime, timedelta
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ID, CONF_ENTITY_ID, CONF_ID, CONF_LIGHTS, CONF_NAME, EVENT_HOMEASSISTANT_START, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import RestoreEntity
from logging import getLogger
from typing import Any, Callable, Dict, List


# -----------------------------------------------------------#
#       Constants
# -----------------------------------------------------------#

BLOCK_THROTTLE_TIME = 0.2
REQUEST_DEBOUNCE_TIME = 0.2
RESET_DEBOUNCE_TIME = 0.5
START_DELAY = 0.5


# -----------------------------------------------------------#
#       Entry Setup
# -----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    async_add_entities([AL_SwitchEntity(config_entry)], update_before_add=True)
    register_services(entity_platform.current_platform.get())


# -----------------------------------------------------------#
#       Service Setup
# -----------------------------------------------------------#

def register_services(platform: EntityPlatform) -> None:
    platform.async_register_entity_service(SERVICE_TRACK_LIGHTS, SERVICE_SCHEMA_TRACK_LIGHTS, "_async_service_track_lights")
    platform.async_register_entity_service(SERVICE_TURN_OFF, {}, "_async_service_turn_off")
    platform.async_register_entity_service(SERVICE_TURN_ON, SERVICE_SCHEMA_TURN_ON, "_async_service_turn_on")


# -----------------------------------------------------------#
#       AL_SwitchEntity
# -----------------------------------------------------------#

class AL_SwitchEntity(SwitchEntity, RestoreEntity, EntityBase):
    """ Represents the switch entity of the integration. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        EntityBase.__init__(self, getLogger(f"{LOGGER_BASE_NAME}.{cv.slugify(config_entry.unique_id)}"))

        self._config_entry : ConfigEntry = config_entry
        self._is_on        : bool        = None
        self._listeners    : list        = []
        self._name         : str         = f"{DOMAIN_FRIENDLY_NAME} - {config_entry.data.get(CONF_NAME)}"

        # --- Block ----------
        self._blocked_at            : datetime = None
        self._blocked_until         : datetime = None
        self._block_config_duration : int      = config_entry.options.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)
        self._block_duration        : int      = self._block_config_duration

        # --- Lights ----------
        self._light_groups   : Dict[str, Any] = config_entry.options.get(CONF_LIGHT_GROUPS, {})
        self._tracked_lights : List[str]      = list_merge_unique(*self._light_groups.values())

        # --- Status ----------
        self._current_profile : Dict[str, Any] = None
        self._current_status  : str            = STATUS_IDLE

        # --- Timers ----------
        self._block_timer   : Callable = None
        self._request_timer : Callable = None
        self._reset_timer   : Callable = None


    #-----------------------------------------------------------------------------#
    #
    #       Entity Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dict containing the entity attributes. """
        if not self._is_on:
            return {}

        attributes = { ATTR_STATUS: self._current_status }

        if self.is_blocked:
            attributes.update({ ATTR_BLOCKED_UNTIL: self._blocked_until })

        if not self.is_blocked and self._current_profile:
            attributes.update({ ATTR_ID: self._current_profile.id, **self._current_profile.attributes })

        return attributes

    @property
    def is_on(self) -> bool:
        """ Gets a boolean indicating whether the entity is turned on. """
        return self._is_on

    @property
    def name(self) -> str:
        """ Gets the name of entity. """
        return self._name

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether Home Assistant should automatically poll the entity. """
        return True

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        async def async_initialize(*args: Any):
            self._listeners.append(async_call_later(self.hass, START_DELAY, self.async_turn_on))

        last_state = await self.async_get_last_state()

        if not last_state or last_state.state == STATE_ON:
            if self.hass.is_running:
                return await async_initialize()
            else:
                return self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, async_initialize)

        await self.async_turn_off()

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        self._remove_listeners()


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_turn_off(self, *args: Any) -> None:
        """ Turns off the entity. """
        if self._is_on is not None and not self._is_on:
            return

        self._is_on = False
        self._remove_listeners()

    async def async_turn_on(self, *args: Any) -> None:
        """ Turns on the entity. """
        if self._is_on:
            return

        self._is_on = True
        self._reset()


    #-----------------------------------------------------------------------------#
    #
    #       Logic Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_blocked(self) -> bool:
        """ Gets a boolean indicating whether the entity is blocked. """
        return self._block_timer is not None


    #--------------------------------------------#
    #       Listeners Methods
    #--------------------------------------------#

    def _remove_listeners(self, *args: Any) -> None:
        """ Removes the event listeners. """
        while self._listeners:
            self._listeners.pop()()

        self._reset_block_timer()
        self._reset_request_timer()
        self._reset_reset_timer()

    def _setup_listeners(self, *args: Any) -> None:
        """ Sets up the event listeners. """
        self._listeners.append(track_automations_changed(self.hass, self._async_on_automations_changed))
        self._listeners.append(track_manual_control(self.hass, self._tracked_lights, self._async_on_manual_control, self.is_context_internal))


    #--------------------------------------------#
    #       Timer Methods
    #--------------------------------------------#

    def _reset_block_timer(self) -> None:
        """ Resets the block timer. """
        if self._block_timer:
            self._block_timer()
            self._block_timer = None

    def _reset_request_timer(self) -> None:
        """ Resets the request timer. """
        if self._request_timer:
            self._request_timer()
            self._request_timer = None

    def _reset_reset_timer(self) -> None:
        """ Resets the request timer. """
        if self._reset_timer:
            self._reset_timer()
            self._reset_timer = None


    #--------------------------------------------#
    #       Event Methods
    #--------------------------------------------#

    def _request(self) -> None:
        """ Fires the request event, requesting the next lighting settings. """
        if self._request_timer:
            self._reset_request_timer()
        else:
            self.logger.debug(f"Firing request event.")
            self._current_profile = None
            self.fire_event(EVENT_TYPE_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_DATA_TYPE_REQUEST)

        def _on_request_finished(*args: Any) -> None:
            """ Triggered when the request event has finished. """
            self._reset_request_timer()

            if self.is_blocked:
                return

            if self._current_profile:
                self.logger.debug(f"Turning on profile {self._current_profile.id} with the following values: { {CONF_ENTITY_ID: self._current_profile.lights, **self._current_profile.attributes} }")
                self._current_status = self._current_profile.status
                self._turn_off_unused_entities(self._tracked_lights, self._current_profile.lights)
                self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self._current_profile.lights, **self._current_profile.attributes)
            else:
                self.logger.debug(f"No lighting profile was provided. Turning off all tracked lights: {self._tracked_lights}")
                self._current_status = STATUS_IDLE
                self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=self._tracked_lights)

            self.async_schedule_update_ha_state(True)

        self._request_timer = async_call_later(self.hass, REQUEST_DEBOUNCE_TIME, _on_request_finished)

    def _reset(self, *args: Any) -> None:
        """ Fires the reset event. """
        if self._reset_timer:
            self._reset_reset_timer()
        else:
            self.logger.debug(f"Firing reset event.")
            self._tracked_lights = list_merge_unique(*self._light_groups.values())
            self._remove_listeners()
            self.fire_event(EVENT_TYPE_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_DATA_TYPE_RESET)

        def _on_reset_finished(*args: Any) -> None:
            """ Triggered when the reset event has finished. """
            self.logger.debug(f"Tracking {len(self._tracked_lights)} lights for manual control.")
            self._reset_reset_timer()
            self._setup_listeners()
            self._request()

        self._reset_timer = async_call_later(self.hass, RESET_DEBOUNCE_TIME, _on_reset_finished)


    #--------------------------------------------#
    #       Block Methods
    #--------------------------------------------#

    def _block(self, duration: int) -> None:
        """ Blocks the entity. """
        if self.is_blocked and (datetime.now() - self._blocked_at).total_seconds() < BLOCK_THROTTLE_TIME and duration == self._block_duration:
            return

        self.logger.debug(f"Blocking entity for {duration} seconds.")
        self._reset_block_timer()
        self._block_duration = duration
        self._blocked_at = datetime.now()
        self._blocked_until = self._blocked_at + timedelta(seconds=self._block_duration) if self._block_duration is not None else None
        self._block_timer = async_call_later(self.hass, self._block_duration, self._unblock)
        self._current_status = STATUS_BLOCKED
        self.async_schedule_update_ha_state(True)

    def _unblock(self, *args: Any) -> None:
        """ Unblocks the entity. """
        self.logger.debug(f"Unblocking entity for after {self._block_duration} seconds of inactivity.")
        self._reset_block_timer()
        self._request()



    #--------------------------------------------#
    #       Helper Methods
    #--------------------------------------------#

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        blacklist = []
        unused_entities = []

        for i in old_entity_ids:
            if i in self._light_groups:
                blacklist = blacklist + self._light_groups[i]
                unused_entities.append(i)
                continue

        for i in old_entity_ids:
            if i in self._light_groups:
                continue

            if not i in blacklist:
                unused_entities.append(i)

        for i in new_entity_ids:
            for x in unused_entities:
                if x in self._light_groups and i in self._light_groups[x]:
                    unused_entities.remove(x)
                    unused_entities = unused_entities + [t for t in self._light_groups[x] if t not in new_entity_ids]

                if x == i:
                    unused_entities.remove(x)

        if len(unused_entities) > 0:
            self.logger.debug(f"Turning off unused entities: {unused_entities}")
            self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)


    #--------------------------------------------#
    #       Service Methods
    #--------------------------------------------#

    async def _async_service_track_lights(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.track_lights' service. """
        if not self.is_on:
            return

        lights = await async_resolve_target(self.hass, service_data.get(CONF_LIGHTS))
        for light in lights:
            if not light in self._tracked_lights:
                self._tracked_lights.append(light)

    async def _async_service_turn_off(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.turn_off' service. """
        if not self.is_on:
            return

        if self.is_blocked:
            return

        if not self._current_profile:
            return

        self._request()

    async def _async_service_turn_on(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.turn_on' service. """
        if not self.is_on:
            return

        id = service_data.pop(CONF_ID)
        status = service_data.pop(CONF_STATUS)
        lights = await async_resolve_target(self.hass, service_data.pop(CONF_LIGHTS))
        attributes = service_data

        if self._request_timer:
            if self._current_profile and self._current_profile.status == STATUS_ACTIVE and status == STATUS_IDLE:
                return

            self._current_profile = Profile(id, status, lights, attributes)
            return

        if self.is_blocked:
            return self._block(self._block_duration)

        if self._current_profile and self._current_profile.id != id:
            self._turn_off_unused_entities(self._current_profile.lights, lights)

        self.logger.debug(f"Turning on profile {id} with following values: { {CONF_ENTITY_ID: lights, **attributes} }")
        self._current_profile = Profile(id, status, lights, attributes)
        self._current_status = status
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=lights, **attributes)
        self.async_schedule_update_ha_state(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_automations_changed(self, event_type: str, entity_id: str) -> None:
        """ Triggered when an automation_reloaded event or automation state change event is detected. """
        if event_type == EVENT_AUTOMATION_RELOADED:
            self.logger.debug(f"Detected an automation_reloaded event.")
        else:
            self.logger.debug(f"Detected a state change to {entity_id}.")

        self._reset()

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        """ Triggered when manual control of the lights are detected. """
        self.logger.debug(f"Manual control was detected for the following entities: {entity_ids}")
        self._block(self._block_duration if self.is_blocked else self._block_config_duration)






