"""Support for Duosida numbers."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .entity import DuosidaEntity
from .const import DOMAIN
from .duosida import DUOSIDA_NUMBER_TYPES, DuosidaNumberEntityDescription
from .coordinator import DeviceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Duosida numbers from config entry."""
    duosida_numbers: list[NumberEntity] = []

    for description in DUOSIDA_NUMBER_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            description.coordinator
        ]
        duosida_numbers.append(DuosidaNumber(coordinator, description))

    async_add_entities(duosida_numbers)


class DuosidaNumber(DuosidaEntity, NumberEntity):
    """Base class for specific duosida numbers"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)

    @property
    def name(self):
        """Return the name of the entity"""
        if self.entity_description.zone:
            return f"{self.entity_description.name} {self.zone}"
        return self.entity_description.name

    @property
    def native_value(self):
        """Return the current value"""
        if self.entity_description.zone:
            return getattr(self.device, self.entity_description.getter.__name__)(
                self.zone
            )
        return getattr(self.device, self.entity_description.getter.__name__)()

    async def async_set_native_value(self, value: float):
        """Update the current value."""
        await getattr(self.device, self.entity_description.setter.__name__)(value)
        self.async_write_ha_state()
