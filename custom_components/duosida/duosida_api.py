"""Duosida API"""
from __future__ import annotations

import logging

# import requests
import aiohttp
import json

from typing import Final, Any, Optional

DUOSIDA_API_URL: Final[str] = "https://cpam3.x-cheng.com/cpAm2/"
DUOSIDA_LOGIN: Final[str] = "login"
DUOSIDA_USER: Final[str] = "users/current"
DUOSIDA_GETDEVICELIST: Final[str] = "cp/deviceList"
DUOSIDA_GETDEVICEDETAIL: Final[str] = "cp/deviceDetail/"  # + deviceid
DUOSIDA_GETDEVICECONFIG: Final[str] = "cp/getCpConfig/"  # + deviceid
DUOSIDA_CHANGEDEVICECONFIG: Final[str] = "cp/changeCpConfig/"  # + deviceid
DUOSIDA_STARTCHARGE: Final[str] = "cp/startCharge/"  # + deviceid POST
DUOSIDA_STOPCHARGE: Final[str] = "cp/stopCharge/"  # + deviceid GET
DUOSIDA_CHARGERECORD: Final[str] = "tran/chargeRecordList/"  # + deviceid?showType=0


_LOGGER = logging.getLogger(__name__)


class ConnectionException(Exception):
    """When can not connect to Duosida cloud"""


class DuosidaAPI:
    """Duosida API class"""

    def __init__(self, username: str, password: str) -> None:
        """Constructor for Duosida API."""
        self.__username = username
        self.__password = password
        self.token = ""

    async def async_connect(self) -> bool:
        """Login to duosida cloud and get token"""
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.request(
                    "POST",
                    f"{DUOSIDA_API_URL}{DUOSIDA_LOGIN}",
                    params=None,
                    data={
                        "username": self.__username,
                        "password": self.__password,
                        "language": "en_us",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    verify_ssl=False,
                )

            if response is None:
                return False

            resp_x = await response.content.read()
            resp_y = resp_x.decode("utf8")
            resp_json = json.loads(resp_y)
            self.token = resp_json["token"]
            return True

        except Exception as error:
            raise ConnectionException() from error

    async def async_get_devices(self) -> list[Any]:
        """Async get duosida devices"""
        response = await DuosidaAPI._async_get(
            self, f"{DUOSIDA_API_URL}{DUOSIDA_GETDEVICELIST}"
        )
        if response is not None:
            devices = response["deviceList"]
            return list(devices)
        return list()

    async def async_get_device_config(self, gw_id: str) -> dict[str, Any]:
        """Async get device configuration"""
        features = await self._async_get(
            f"{DUOSIDA_API_URL}{DUOSIDA_GETDEVICECONFIG}{gw_id}"
        )
        if features is not None:
            return features
        return dict()

    async def async_get_device_detail(self, gw_id: str) -> dict[str, Any]:
        """Async get features for the device"""
        features = await self._async_get(
            f"{DUOSIDA_API_URL}{DUOSIDA_GETDEVICEDETAIL}{gw_id}"
        )
        if features is not None:
            return features
        return dict()

    async def async_get_features_for_device(
        self, gw_id: str
    ) -> Optional[dict[str, Any]]:
        """Async get features for the device"""
        return await self._async_get(
            f"{DUOSIDA_API_URL}{DUOSIDA_GETDEVICEDETAIL}{gw_id}"
        )

    async def async_set_property(
        self,
        gw_id: str,
        key: str,
        value: int,
    ) -> None:
        """Set device properties"""
        await self._async_post(
            f"{DUOSIDA_API_URL}{DUOSIDA_CHANGEDEVICECONFIG}{gw_id}",
            {
                "key": key,
                "value": value,
            },
        )

    async def async_device_start_charge(self, gw_id: str) -> bool:
        """Async start device charging"""
        features = await self._async_post(
            f"{DUOSIDA_API_URL}{DUOSIDA_STARTCHARGE}{gw_id}", None
        )
        if features is not None:
            return True
        return False

    async def async_device_stop_charge(self, gw_id: str) -> bool:
        """Async stop device charging"""
        features = await self._async_get(
            f"{DUOSIDA_API_URL}{DUOSIDA_STOPCHARGE}{gw_id}", None
        )
        if features is not None:
            return True
        return False

    async def async_get_charging_record(self, gw_id: str) -> dict[str, Any]:
        """Async get device charging record"""
        features = await self._async_post(
            f"{DUOSIDA_API_URL}{DUOSIDA_CHARGERECORD}{gw_id}?showType=0", None
        )
        if features is not None:
            return features
        return dict()

    async def __async_request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        body: Any = None,
        is_retry: bool = False,
    ) -> Optional[dict[str, Any]]:
        """Async request with aiohttp"""
        headers = {"token": self.token}
        _LOGGER.debug(
            "Request method %s, path: %s, params: %s, body: %s",
            method,
            path,
            params,
            body,
        )
        async with aiohttp.ClientSession() as session:
            response = await session.request(
                method,
                path,
                params=params,
                json=body,
                headers=headers,
                verify_ssl=False,
            )

            if not response.ok:
                if response.status == 405:
                    if not is_retry:
                        if await self.async_connect():
                            return await self.__async_request(
                                method, path, params, body, True
                            )
                        raise Exception("Login failed (password changed?)")
                    raise Exception("Invalid token")
                if response.status == 404:
                    return None
                raise Exception(response.status)

            if response.content and response.content.total_bytes > 0:
                _json = await response.json()
                _LOGGER.debug("Response %s", json)
                json_x = _json["bizData"]
                return json_x

            return None

    async def _async_post(self, path: str, body: Any) -> Optional[dict[str, Any]]:
        """Async POST request"""
        return await self.__async_request("POST", path, None, body)

    async def _async_get(
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """Async GET request"""
        return await DuosidaAPI.__async_request(self, "GET", path, params, None)

    async def async_set_level_detection(self, gw_id: str, level_detection: bool):
        """Async set automatic thermoregulation"""
        await self.async_set_property(
            gw_id, "CheckCpN12V", 1.0 if level_detection else 0.0
        )

    async def async_set_plug_play_mode(self, gw_id: str, plugplay_mode: bool):
        """Async set automatic thermoregulation"""
        await self.async_set_property(
            gw_id, "VendorDirectWorkMode", 1.0 if plugplay_mode else 0.0
        )

    async def async_set_max_current(self, gw_id: str, max_current: int):
        """Async set automatic thermoregulation"""
        await self.async_set_property(gw_id, "VendorMaxWorkCurrent", max_current)
