"""Demo platform that offers a fake button entity."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import DuosidaEntity
from .const import DOMAIN
from .duosida import DUOSIDA_BUTTON_TYPES, DuosidaButtonEntityDescription
from .coordinator import DeviceDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Duosida buttons from config entry."""
    duosida_buttons: list[DuosidaButton] = []
    for description in DUOSIDA_BUTTON_TYPES:
        coordinator: DeviceDataUpdateCoordinator = hass.data[DOMAIN][
            config_entry.unique_id
        ][description.coordinator]
        duosida_buttons.append(
            DuosidaButton(
                coordinator,
                description,
            )
        )
    async_add_entities(duosida_buttons)


class DuosidaButton(DuosidaEntity, ButtonEntity):
    """Base class for specific duosida switches"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaButtonEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description)

    @property
    def is_on(self):
        """Return true if button is on."""
        return getattr(self.device, self.entity_description.button_status.__name__)()

    async def async_turn_on(self) -> None:
        """Turn the button on."""
        await getattr(self.device, self.entity_description.start_action.__name__)()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the button off."""
        await getattr(self.device, self.entity_description.stop_action.__name__)()
        self.async_write_ha_state()

    async def async_press(self) -> None:
        """Press button action."""
        if self.is_on:
            await getattr(self.device, self.entity_description.stop_action.__name__)()
            self.async_write_ha_state()
        else:
            await getattr(self.device, self.entity_description.start_action.__name__)()
            self.async_write_ha_state()
