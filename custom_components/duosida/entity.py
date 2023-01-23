"""Entity object for shared properties of Duosida entities."""
from __future__ import annotations

import logging

from abc import ABC

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .duosida import DuosidaBaseEntityDescription
from .coordinator import DeviceDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class DuosidaEntity(CoordinatorEntity, ABC):
    """Generic Duosida entity (base class)"""

    def __init__(
        self,
        coordinator: DeviceDataUpdateCoordinator,
        description: DuosidaBaseEntityDescription,
        zone: int | None = None,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)

        self.device = coordinator.device
        self.entity_description: DuosidaBaseEntityDescription = description
        self.zone = zone

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.get_serial_number())},
            manufacturer=DOMAIN,
            name=self.device.get_device_name(),
            sw_version=self.device.get_firmware_version(),
            model=self.device.get_device_model(),
        )

    @property
    def unique_id(self):
        """Return the unique id."""
        return f"{self.device.id}-{self.name}"
