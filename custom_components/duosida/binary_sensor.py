"""Support for Duosida binary_sensors."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .entity import DuosidaEntity
from .const import DOMAIN

from .duosida import DUOSIDA_BINARY_SENSOR_TYPES, DuosidaBinarySensorEntityDescription
from .coordinator import DeviceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Duosida binary sensors from config entry."""
    duosida_binary_sensors: list[DuosidaBinarySensor] = []
    for description in DUOSIDA_BINARY_SENSOR_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            description.coordinator
        ]
        duosida_binary_sensors.append(DuosidaBinarySensor(coordinator, description))

    async_add_entities(duosida_binary_sensors)


class DuosidaBinarySensor(DuosidaEntity, BinarySensorEntity):
    """Base class for specific duosida binary sensors"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def is_on(self):
        """Return True if the binary sensor is on."""
        return getattr(self.device, self.entity_description.get_is_on.__name__)()
