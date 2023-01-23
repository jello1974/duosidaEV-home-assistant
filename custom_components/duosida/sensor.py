"""Support for Duosida sensors."""
from __future__ import annotations

import logging

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity

from .entity import DuosidaEntity
from .const import DOMAIN
from .duosida import DUOSIDA_SENSOR_TYPES, DuosidaSensorEntityDescription
from .coordinator import DeviceDataUpdateCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Duosida sensors from config entry."""
    duosida_sensors = []

    for description in DUOSIDA_SENSOR_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            description.coordinator
        ]
        duosida_sensors.append(
            DuosidaSensor(
                coordinator,
                description,
            )
        )

    async_add_entities(duosida_sensors)


class DuosidaSensor(DuosidaEntity, SensorEntity):
    """Base class for specific duosida sensors"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self):
        """Return value of sensor."""
        return getattr(self.device, self.entity_description.get_native_value.__name__)()

    @property
    def native_unit_of_measurement(self):
        """Return the nateive unit of measurement"""
        if self.entity_description.get_native_unit_of_measurement is not None:
            return getattr(
                self.device,
                self.entity_description.get_native_unit_of_measurement.__name__,
            )()

        if self.entity_description.native_unit_of_measurement is not None:
            return self.entity_description.native_unit_of_measurement

    @property
    def last_reset(self) -> datetime | None:
        if self.entity_description.get_last_reset is not None:
            return getattr(
                self.device,
                self.entity_description.get_last_reset.__name__,
            )()
