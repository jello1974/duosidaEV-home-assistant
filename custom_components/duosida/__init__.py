"""The Duosida D EV Charge (DS Charge APP) integration."""

from __future__ import annotations

import logging

import voluptuous as vol
import datetime as dt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_ID,
    CONF_DEVICE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    COORDINATOR,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import DeviceDataUpdateCoordinator

from .duosida import Duosida, DeviceAttribute

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

SERVICE_SET_DEVICE_CHARGING_POWER = "set_device_charging_power"
ATTR_VALUE = "value"

SET_DEVICE_CHARGING_POWER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_VALUE): vol.Coerce(float),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Set up Duosida from a config entry.
    duosida = Duosida()
    try:
        reponse = await duosida.async_connect(
            entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
        if not reponse:
            _LOGGER.error(
                "Failed to connect to Duosida with device: %s",
                entry.data[CONF_DEVICE].get(DeviceAttribute.PILE_NAME),
            )
            raise ConfigEntryAuthFailed()
    except Exception as error:
        _LOGGER.exception("")
        raise ConfigEntryNotReady() from error

    deviceid = entry.data[CONF_DEVICE].get(DeviceAttribute.ID)
    device = await duosida.async_hello(deviceid)
    if device is None:
        return False
    else:
        device.config_attributes = await duosida.api.async_get_device_config(deviceid)
        device.detail_attributes = await duosida.api.async_get_device_detail(deviceid)
        if device.detail_attributes["txStop"] != "null":
            device.consumption_sequence_last_changed_utc = dt.datetime.now(
                dt.timezone.utc
            ) - dt.timedelta(hours=1)

    scan_interval_seconds = entry.options.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
    )
    coordinator = DeviceDataUpdateCoordinator(
        hass, device, scan_interval_seconds, COORDINATOR, device.async_update_state
    )

    hass.data.setdefault(DOMAIN, {}).setdefault(entry.unique_id, {COORDINATOR: {}})

    hass.data[DOMAIN][entry.unique_id][COORDINATOR] = coordinator

    await coordinator.async_config_entry_first_refresh()

    ##hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    async def async_set_device_charging_power_service(service_call):
        """Create service for device."""
        device_id = service_call.data.get(ATTR_DEVICE_ID)
        value = service_call.data.get(ATTR_VALUE)

        device_registry = dr.async_get(hass)
        device = device_registry.devices[device_id]

        entry = hass.config_entries.async_get_entry(next(iter(device.config_entries)))
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            COORDINATOR
        ]
        await coordinator.device.set_device_max_current(value)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_DEVICE_CHARGING_POWER,
        async_set_device_charging_power_service,
        schema=SET_DEVICE_CHARGING_POWER_SCHEMA,
    )
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.unique_id)

    return unload_ok
