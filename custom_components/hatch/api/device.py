from __future__ import annotations

import logging

from awscrt import mqtt
from awsiot import iotshadow
from awsiot.iotshadow import (
    IotShadowClient,
    GetShadowResponse,
    UpdateShadowResponse,
    UpdateShadowRequest,
    ShadowState,
)

from .const import (
    DEFAULT_SAVE_ENABLED,
    PRODUCT_MODEL_MAP,
)

_LOGGER = logging.getLogger(__name__)


class Info:

    def __init__(self, state: dict):
        self.create_date = state.get("createDate")
        self.email = state.get("email")
        self.hardware_version = state.get("hardwareVersion")
        self.id = state.get("id")
        self.mac_address = state.get("macAddress")
        self.member_id = state.get("memberId")
        self.name = state.get("name")
        self.owner = state.get("owner")
        self.product = state.get("product")
        self.thing_name = state.get("thingName")
        self.update_date = state.get("updateDate")
        self.model = PRODUCT_MODEL_MAP.get(self.product, self.product)


class Device:

    def __init__(
            self,
            info: dict,
            shadow_client: IotShadowClient,
            save_response_enabled: bool = DEFAULT_SAVE_ENABLED,
    ):
        self.document_version = -1
        self.info = Info(info)
        self.previous_state = None
        self.save_response_enabled = save_response_enabled
        self.shadow_client = shadow_client
        self.state = {}

        def update_shadow_accepted(response: UpdateShadowResponse):
            self._on_update_shadow_accepted(response)

        (
            update_accepted_subscribed_future,
            _,
        ) = shadow_client.subscribe_to_update_shadow_accepted(
            request=iotshadow.UpdateShadowSubscriptionRequest(
                thing_name=self.info.thing_name
            ),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=update_shadow_accepted,
        )
        update_accepted_subscribed_future.result()

        def on_get_shadow_accepted(response: GetShadowResponse):
            self._on_get_shadow_accepted(response)

        (
            get_accepted_subscribed_future,
            _,
        ) = shadow_client.subscribe_to_get_shadow_accepted(
            request=iotshadow.GetShadowSubscriptionRequest(thing_name=self.info.thing_name),
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_get_shadow_accepted,
        )
        get_accepted_subscribed_future.result()
        self.refresh()

    def _setup_callbacks(self):
        self._callbacks = set()

    def register_callback(self, callback) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        self._callbacks.add(callback)

    def remove_callback(self, callback) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        self._callbacks.discard(callback)

    def publish_updates(self) -> None:
        if not hasattr(self, "_callbacks"):
            self._setup_callbacks()
        _LOGGER.debug(f"[{self.info.name}] Publishing updates")
        for callback in self._callbacks:
            callback()

    def refresh(self):
        _LOGGER.debug("Requesting current shadow state...")
        result = self.shadow_client.publish_get_shadow(
            request=iotshadow.GetShadowRequest(
                thing_name=self.info.thing_name, client_token=None
            ),
            qos=mqtt.QoS.AT_LEAST_ONCE,
        ).result()
        _LOGGER.debug(f"result: {result}")

    def _merge_state(self, current: dict, update: dict):
        for key, value in update.items():
            if isinstance(value, dict):
                current[key] = self._merge_state(current.get(key, {}), value)
            else:
                current[key] = value
        return current

    def _on_update_shadow_accepted(self, response: UpdateShadowResponse):
        if response.version < self.document_version:
            return
        if response.state:
            if response.state.reported:
                self.document_version = response.version
                self._update_local_state(response.state.reported)

    def _on_get_shadow_accepted(self, response: GetShadowResponse):
        if response.version < self.document_version:
            return
        if response.state:
            if response.state.delta:
                pass

            if response.state.reported:
                self.document_version = response.version
                self._update_local_state(response.state.reported)

    def _update(self, desired_state):
        request: UpdateShadowRequest = UpdateShadowRequest(
            thing_name=self.info.thing_name,
            state=ShadowState(
                desired=desired_state,
            ),
        )
        self.shadow_client.publish_update_shadow(
            request, mqtt.QoS.AT_LEAST_ONCE
        ).result()

    @property
    def firmware_version(self) -> str | None:
        return self.state.get("deviceInfo", {}).get("f")

    @property
    def is_connected(self) -> bool:
        return bool(self.state.get("connected"))
