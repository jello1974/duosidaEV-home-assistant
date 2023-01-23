"""Duosida module"""
import asyncio
import logging
from abc import ABC
from typing import Any, Optional, Final
from enum import IntFlag, unique
from collections.abc import Callable
from dataclasses import dataclass
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.helpers.entity import EntityCategory, EntityDescription
from homeassistant.components.binary_sensor import BinarySensorEntityDescription

from .duosida_api import DuosidaAPI, ConnectionException
from .const import NAME, COORDINATOR

_LOGGER = logging.getLogger(__name__)

_api = DuosidaAPI


class DuosidaDevice(ABC):
    """Class representing a physical device, it's state and properties."""

    def __init__(
        self,
        api: DuosidaAPI,
        attributes: dict[str, Any],
    ) -> None:
        self.api = api
        self.attributes = attributes
        self.detail_attributes: dict[str, Any] = dict()
        self.config_attributes: dict[str, Any] = dict()
        self.data: dict[str, Any] = dict()
        self.id: str = self.attributes.get(DeviceAttribute.ID, "")

    # @property

    def set_level_detection(self, val: int):
        """Set device level detection"""
        self.config_attributes[DeviceConfig.LEVEL_DETECTION] = str(val)
        return self.api.async_set_property(self.id, "CheckCpN12V", val)

    def set_direct_work_mode(self, val: int):
        """Set device direct work mode"""
        self.config_attributes[DeviceConfig.DIRECT_WORK_MODE] = str(val)
        return self.api.async_set_property(self.id, "VendorDirectWorkMode", val)

    def set_device_max_current(self, val: int):
        """Set device max operating power"""
        self.detail_attributes[DeviceDetail.MAX_CURRENT] = val
        return self.api.async_set_property(self.id, "VendorMaxWorkCurrent", val)

    def start_charging(self):
        """Device start charging"""
        return self.api.async_device_start_charge(self.id)

    def stop_charging(self):
        """Device stop charging"""
        return self.api.async_device_stop_charge(self.id)

    def get_button_status(self) -> bool:
        """Return charging state"""
        status = Status(
            self.detail_attributes.get(DeviceDetail.CONNECTION_STATUS, None)
        )
        if status is not None:
            if status in [0, 4, 5]:
                DeviceConfig.START_STOP_CHARGING = False
                return False
            else:
                DeviceConfig.START_STOP_CHARGING = True
                return True
        return None

    def get_device_name(self) -> Optional[str]:
        """Get device name"""
        return self.attributes.get(DeviceAttribute.PILE_NAME, None)

    def get_device_picture(self) -> Optional[str]:
        """Get device picture"""
        return self.attributes.get(DeviceAttribute.DEVICE_PICTURE_URL, None)

    def get_device_model(self) -> Optional[str]:
        """Get device model"""
        return self.attributes.get(DeviceAttribute.MODEL, None)

    def get_serial_number(self) -> Optional[str]:
        """Get device serial number"""
        return self.attributes.get(DeviceAttribute.SN, None)

    def get_firmware_version(self) -> Optional[str]:
        """Get device firmware version"""
        return self.attributes.get(DeviceAttribute.FW, None)

    def get_device_temperature(self) -> Optional[str]:
        """Get device temperature"""
        return self.detail_attributes.get(DeviceDetail.TEMPERATURE, None)

    def get_device_status(self) -> Optional[str]:
        """Get device connection status"""
        return Status(self.detail_attributes.get(DeviceDetail.CONNECTION_STATUS, None))

    def get_device_current(self) -> Optional[str]:
        """Get device current"""
        return self.detail_attributes.get(DeviceDetail.CURRENT, None)

    def get_device_current2(self) -> Optional[str]:
        """Get device current phase 2"""
        return self.detail_attributes.get(DeviceDetail.CURRENT2, None)

    def get_device_current3(self) -> Optional[str]:
        """Get device current phase 3"""
        return self.detail_attributes.get(DeviceDetail.CURRENT3, None)

    def get_device_voltage(self) -> Optional[str]:
        """Get device voltage"""
        return self.detail_attributes.get(DeviceDetail.VOLTAGE, None)

    def get_device_voltage2(self) -> Optional[str]:
        """Get device voltage phase 2"""
        return self.detail_attributes.get(DeviceDetail.VOLTAGE2, None)

    def get_device_voltage3(self) -> Optional[str]:
        """Get device voltage phase 3"""
        return self.detail_attributes.get(DeviceDetail.VOLTAGE3, None)

    def get_device_accenergy(self) -> Optional[str]:
        """Get device accenergy"""
        return self.detail_attributes.get(DeviceDetail.ACCENERGY, None)

    def get_device_accenergy2(self) -> Optional[str]:
        """Get device accenergy2"""
        return self.detail_attributes.get(DeviceDetail.ACCENERGY2, None)

    def get_device_max_current(self) -> Optional[str]:
        """Get device firmware version"""
        return self.detail_attributes.get(DeviceDetail.MAX_CURRENT, None)

    def get_device_power(self) -> Optional[str]:
        """Get device power"""
        return self.detail_attributes.get(DeviceDetail.POWER, None)

    def get_direct_work_mode(self) -> Optional[str]:
        """Get device direct work mode status"""
        return self.config_attributes.get(DeviceConfig.DIRECT_WORK_MODE, None)

    def get_level_detection(self) -> Optional[str]:
        """Get device level detection status"""
        return self.config_attributes.get(DeviceConfig.LEVEL_DETECTION, None)

    def get_stop_on_disconnect(self) -> Optional[str]:
        """Get device stop on disconnect status"""
        return self.config_attributes.get(DeviceConfig.STOP_ON_DISCONNECT, None)

    # @abstractmethod
    async def async_update_state(self) -> None:
        """Async update the device states from the cloud"""
        self.config_attributes = await self.api.async_get_device_config(self.id)
        self.detail_attributes = await self.api.async_get_device_detail(self.id)
        self.get_button_status()


class Duosida:
    """Duosida class"""

    def __init__(self) -> None:
        self.api = None
        self.cloud_devices: list[dict[str, Any]] = []

    async def async_connect(self, username: str, password: str) -> bool:
        """Connect to the duosida cloud"""
        self.api = DuosidaAPI(username, password)
        return await self.api.async_connect()

    async def async_discover(self) -> Optional[list[dict[str, Any]]]:
        """Retreive duosida devices from the cloud"""
        if self.api is None:
            _LOGGER.exception("Call async_connect first")
            return None
        cloud_devices = await _async_discover(self.api)
        self.cloud_devices = cloud_devices
        return cloud_devices

    async def async_hello(self, gateway: str) -> Optional[DuosidaDevice]:
        """Get duosida device"""
        if self.api is None:
            _LOGGER.exception("Call async_connect() first")
            return None

        if len(self.cloud_devices) == 0:
            await self.async_discover()

        return await _get_device(self.cloud_devices, self.api, gateway)


@unique
class Status(IntFlag):
    """Status mode enum"""

    UNDEFINED = -1
    Available = 0
    Preparing = 1
    Charging = 2
    COOLING = 3
    SuspendedEV = 4
    Finished = 5
    HOLIDAY = 6


class DeviceAttribute(DuosidaDevice):
    """Constants for device attributes"""

    MODEL: Final[str] = "chargePointModel"
    SN: Final[str] = "chargePointSerialNumber"
    VENDOR: Final[str] = "chargePointVendor"
    STATUS: Final[int] = "connStatus"
    CURRENT_TIME: Final[int] = "curTime"
    ENERGY: Final[str] = "energy"
    FW: Final[str] = "firmwareVersion"
    ID: Final[int] = "id"
    IS_ONLINE: Final[int] = "isOnline"
    PILE_NAME: Final[str] = "pileName"
    TYPE: Final[str] = "type"
    UPDATE_TIME: Final[int] = "updateTime"
    DEVICE_PICTURE_URL: Final[str] = "url"


class DeviceConfig(DuosidaDevice):
    """Constants for device configuration"""

    DEVICE_ID: Final[int] = "cpId"
    CREATE_TIME: Final[int] = "createTime"
    DIRECT_WORK_MODE: Final[bool] = "directWorkMode"
    LED_STRENGHT: Final[int] = "ledStrength"
    LEVEL_DETECTION: Final[bool] = "levelDetection"
    MAX_CURRENT: Final[int] = "maxCurrent"
    STOP_ON_DISCONNECT: Final[bool] = "stopTranOnEVSideDiscon"
    START_STOP_CHARGING: Final[bool] = "StartStopCharging"


class DeviceDetail(DuosidaDevice):
    """Constants for device detail"""

    ACCENERGY: Final[float] = "accEnergy"
    ACCENERGY2: Final[float] = "accEnergy2"
    CONNECTION_STATUS: Final[IntFlag] = "connStatus"
    CURRENT: Final[float] = "current"
    CURRENT2: Final[float] = "current2"
    CURRENT3: Final[float] = "current3"
    ERRORCODE: Final[int] = "errorCode"
    MAX_CURRENT: Final[int] = "maxCurrent"
    POWER: Final[float] = "power"
    TEMPERATURE: Final[float] = "temperature"
    VOLTAGE: Final[float] = "voltage"
    VOLTAGE2: Final[float] = "voltage2"
    VOLTAGE3: Final[float] = "voltage3"


async def _get_device(
    cloud_devices: list[dict[str, Any]],
    api: DuosidaAPI,
    gateway: str,
) -> Optional[DuosidaDevice]:
    """Get duosida device"""
    device = next(
        (dev for dev in cloud_devices if dev.get(DeviceAttribute.ID) == gateway),
        None,
    )
    if device is None:
        _LOGGER.exception(f'No device "{gateway}" found.')
        return None
    else:
        device[DeviceAttribute] = await api.async_get_device_config(gateway)
        device[DeviceDetail] = await api.async_get_device_detail(gateway)
    return DuosidaDevice(api, device)


async def _async_connect(username: str, password: str) -> DuosidaAPI:
    """Async connect to duosida api"""
    api = DuosidaAPI(username, password)
    if not await api.async_connect():
        raise ConnectionException
    return api


async def _async_discover(api: DuosidaAPI) -> list[dict[str, Any]]:
    """Async retreive duosida devices from the cloud"""
    cloud_devices: list[dict[str, Any]] = []
    cloud_devices_tuple: tuple[
        list[dict[str, Any]], list[dict[str, Any]]
    ] = await asyncio.gather(
        api.async_get_devices(),
    )

    for devices in cloud_devices_tuple:
        cloud_devices.extend(devices)
    return cloud_devices


async def async_discover(username: str, password: str) -> list[dict[str, Any]]:
    """Retreive duosida devices from the cloud"""
    api = await _async_connect(username, password)
    return await _async_discover(api)


async def async_hello(
    username: str,
    password: str,
    gateway: str,
    is_metric: bool = True,
    language_tag: str = "en-US",
) -> Optional[DuosidaDevice]:
    """Get duosida device"""
    api = await _async_connect(username, password)
    cloud_devices = await _async_discover(api)
    return _get_device(cloud_devices, api, gateway)


@dataclass
class DuosidaBaseEntityDescription(EntityDescription, ABC):
    """An abstract class that describes Duosida entites"""

    device_detail: list[DeviceDetail] = None
    device_config: list[DeviceConfig] = None
    device_atribute: list[DeviceAttribute] = None
    coordinator: str = COORDINATOR
    zone: bool = False


@dataclass
class DuosidaSwitchEntityDescription(
    SwitchEntityDescription, DuosidaBaseEntityDescription
):
    """A class that describes switch entities."""

    setter: Callable = None
    getter: Callable = None


@dataclass
class DuosidaNumberEntityDescription(
    NumberEntityDescription, DuosidaBaseEntityDescription
):
    """A class that describes numbers entities."""

    setter: Callable = None
    getter: Callable = None
    min: Callable = None
    max: Callable = None
    getstep: Callable = None


@dataclass
class DuosidaSensorEntityDescription(
    SensorEntityDescription, DuosidaBaseEntityDescription
):
    """A class that describes sensor entities."""

    get_native_value: Callable = None
    get_native_unit_of_measurement: Callable = None
    get_last_reset: Callable = None


@dataclass
class DuosidaBinarySensorEntityDescription(
    BinarySensorEntityDescription, DuosidaBaseEntityDescription
):
    """A class that describes binary sensor entities."""

    get_is_on: Callable = None


@dataclass
class DuosidaButtonEntityDescription(
    ButtonEntityDescription, DuosidaBaseEntityDescription
):
    """A class that describes button entities."""

    start_action: Callable = None
    stop_action: Callable = None
    button_status: Callable = None


DUOSIDA_SENSOR_TYPES: tuple[DuosidaSensorEntityDescription, ...] = (
    DuosidaSensorEntityDescription(
        key=DeviceAttribute.PILE_NAME,
        name=f"{NAME} station name",
        get_native_value=DuosidaDevice.get_device_name,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceAttribute.MODEL,
        name=f"{NAME} charge point model",
        get_native_value=DuosidaDevice.get_device_model,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceAttribute.SN,
        name=f"{NAME} charge point serial number",
        get_native_value=DuosidaDevice.get_serial_number,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceAttribute.FW,
        name=f"{NAME} charge point firmware version",
        get_native_value=DuosidaDevice.get_firmware_version,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.TEMPERATURE,
        name=f"{NAME} station temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_temperature,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceAttribute.STATUS,
        name=f"{NAME} status",
        device_class=SensorDeviceClass.ENUM,
        get_native_value=DuosidaDevice.get_device_status,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.CURRENT,
        name=f"{NAME} current",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_current,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.CURRENT2,
        name=f"{NAME} current2",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_current2,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.CURRENT3,
        name=f"{NAME} current3",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_current3,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.VOLTAGE,
        name=f"{NAME} Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_voltage,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.VOLTAGE2,
        name=f"{NAME} Voltage2",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_voltage2,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.VOLTAGE3,
        name=f"{NAME} Voltage3",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_voltage3,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.ACCENERGY,
        name=f"{NAME} accEnergy",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_accenergy,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.ACCENERGY2,
        name=f"{NAME} accEnergy2",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_accenergy2,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.MAX_CURRENT,
        name=f"{NAME} maxCurrent",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_max_current,
    ),
    DuosidaSensorEntityDescription(
        key=DeviceDetail.POWER,
        name=f"{NAME} Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        get_native_value=DuosidaDevice.get_device_power,
    ),
)

DUOSIDA_SWITCH_TYPES: tuple[DuosidaSwitchEntityDescription, ...] = (
    DuosidaSwitchEntityDescription(
        key=DeviceConfig.DIRECT_WORK_MODE,
        name=f"{NAME} directWorkMode",
        icon="mdi:current-dc",
        setter=DuosidaDevice.set_direct_work_mode,
        getter=DuosidaDevice.get_direct_work_mode,
    ),
    DuosidaSwitchEntityDescription(
        key=DeviceConfig.LEVEL_DETECTION,
        name=f"{NAME} levelDetection",
        icon="mdi:car-brake-fluid-level",
        setter=DuosidaDevice.set_level_detection,
        getter=DuosidaDevice.get_level_detection,
    ),
)

DUOSIDA_NUMBER_TYPES: tuple[DuosidaNumberEntityDescription, ...] = (
    DuosidaNumberEntityDescription(
        key=DeviceConfig.MAX_CURRENT,
        name=f"{NAME} set maximal current",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.CONFIG,
        native_min_value=6,
        native_max_value=32,
        native_step=1,
        getter=DuosidaDevice.get_device_max_current,
        setter=DuosidaDevice.set_device_max_current,
    ),
)

DUOSIDA_BINARY_SENSOR_TYPES: tuple[DuosidaBinarySensorEntityDescription, ...] = (
    DuosidaBinarySensorEntityDescription(
        key=DeviceConfig.STOP_ON_DISCONNECT,
        name=f"{NAME} stopTranOnEVSideDiscon",
        icon="mdi:pipe-disconnected",
        get_is_on=DuosidaDevice.get_stop_on_disconnect,
    ),
)

DUOSIDA_BUTTON_TYPES: tuple[DuosidaButtonEntityDescription, ...] = (
    DuosidaButtonEntityDescription(
        key=DeviceConfig.START_STOP_CHARGING,
        name=f"{NAME} start_stop_charging",
        icon="mdi:play-pause",
        start_action=DuosidaDevice.start_charging,
        stop_action=DuosidaDevice.stop_charging,
        button_status=DuosidaDevice.get_button_status,
    ),
)


class ChargingRecord(DuosidaDevice):
    """Constants for charging record"""

    ENERGY: Final[float] = "energy"
    TIME_STAMP_STOP: Final[int] = "timestampStop"
    TIME_STAMP_START: Final[int] = "timestampStart"
    DURATION: Final[str] = "duration"
