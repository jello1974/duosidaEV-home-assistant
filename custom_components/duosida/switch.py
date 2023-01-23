"""Support for Duosida switches."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity

from .entity import DuosidaEntity
from .const import DOMAIN
from .duosida import DUOSIDA_SWITCH_TYPES, DuosidaSwitchEntityDescription
from .coordinator import DeviceDataUpdateCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the Duosida switches from config entry."""
    duosida_switches: list[DuosidaSwitch] = []
    for description in DUOSIDA_SWITCH_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][entry.unique_id][
            description.coordinator
        ]
        duosida_switches.append(
            DuosidaSwitch(
                coordinator,
                description,
            )
        )

    async_add_entities(duosida_switches)


class DuosidaSwitch(DuosidaEntity, SwitchEntity):
    """Base class for specific duosida switches"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description)

    @property
    def is_on(self):
        """Return true if switch is on."""
        return getattr(self.device, self.entity_description.getter.__name__)()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await getattr(self.device, self.entity_description.setter.__name__)(1)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        await getattr(self.device, self.entity_description.setter.__name__)(0)
        self.async_write_ha_state()
