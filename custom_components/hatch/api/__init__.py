from __future__ import annotations

from aiohttp import (
    ClientSession,
    ClientResponse,
    ClientError,
    hdrs as aiohttp_headers,
    __version__ as aiohttp_version,
)
from awscrt import io
from awscrt.auth import AwsCredentialsProvider
from awsiot.mqtt_connection_builder import websockets_with_default_aws_signing
from awsiot.iotshadow import IotShadowClient
import json
import logging
from re import sub, IGNORECASE
from uuid import uuid4

from .const import (
    API_URL,
    PRODUCT_REST_MINI,
    PRODUCT_REST_PLUS,
    USER_AGENT,
)
from .rest_mini import RestMini
from .rest_plus import RestPlus
from .util import (
    request_with_logging,
    request_with_logging_and_errors,
    save_response,
)

_LOGGER = logging.getLogger(__name__)


async def get_devices(
    email: str,
    password: str,
    client_session: ClientSession = None,
    on_connection_interrupted=None,
    on_connection_resumed=None,
    save_responses: bool=False,
):
    api = Hatch(client_session=client_session)
    token = await api.login(email=email, password=password)
    iot_devices = await api.iot_devices(auth_token=token)
    if save_responses:
        save_response(iot_devices, "iot_devices")
    aws_token = await api.token(auth_token=token)
    aws_http: AwsHttp = AwsHttp(api.api_session)
    aws_credentials = await aws_http.aws_credentials(
        region=aws_token["region"],
        identityId=aws_token["identityId"],
        aws_token=aws_token["token"],
    )
    credentials_provider = AwsCredentialsProvider.new_static(
        aws_credentials["Credentials"]["AccessKeyId"],
        aws_credentials["Credentials"]["SecretKey"],
        session_token=aws_credentials["Credentials"]["SessionToken"],
    )
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
    endpoint = aws_token["endpoint"].lstrip("https://")
    safe_email = sub("[^a-z]", "", email, flags=IGNORECASE).lower()
    mqtt_connection = websockets_with_default_aws_signing(
        region="us-west-2",
        credentials_provider=credentials_provider,
        keep_alive_secs=30,
        client_bootstrap=client_bootstrap,
        endpoint=endpoint,
        client_id=f"{USER_AGENT}/{safe_email}/{str(uuid4())}",
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
    )
    mqtt_connection.connect().result()
    _LOGGER.debug(f"mqtt connection connected")

    shadow_client = IotShadowClient(mqtt_connection)

    def create_device(iot_device):
        if iot_device["product"] == PRODUCT_REST_MINI:
            return RestMini(
                info=iot_device,
                shadow_client=shadow_client,
                save_responses=save_responses,
            )
        elif iot_device["product"] == PRODUCT_REST_PLUS:
            return RestPlus(
                info=iot_device,
                shadow_client=shadow_client,
                save_responses=save_responses,
            )

    devices = map(create_device, iot_devices)
    return (
        api,
        mqtt_connection,
        list(devices),
        aws_credentials["Credentials"]["Expiration"],
    )


class AwsHttp:
    def __init__(self, client_session: ClientSession = None):
        if client_session is None:
            self.api_session = ClientSession(raise_for_status=True)
        else:
            self.api_session = client_session

    async def cleanup_client_session(self):
        await self.api_session.close()

    @request_with_logging
    async def _post_request_with_logging_and_errors_raised(
        self, url: str, json_body: dict, headers: dict = None
    ) -> ClientResponse:
        return await self.api_session.post(url=url, json=json_body, headers=headers)

    async def aws_credentials(self, region: str, identityId: str, aws_token: str):
        url = f"https://cognito-identity.{region}.amazonaws.com"
        json_body = {
            "IdentityId": identityId,
            "Logins": {
                "cognito-identity.amazonaws.com": aws_token,
            },
        }
        headers = {
            "content-type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityService.GetCredentialsForIdentity",
        }
        response: ClientResponse = (
            await self._post_request_with_logging_and_errors_raised(
                url=url, json_body=json_body, headers=headers
            )
        )
        data = await response.read()
        return json.loads(data)


class Hatch:
    def __init__(self, client_session: ClientSession = None):
        if client_session is None:
            self.api_session = ClientSession(raise_for_status=True)
        else:
            self.api_session = client_session
        _LOGGER.debug(f"api_session_version: {aiohttp_version}")

    async def cleanup_client_session(self):
        await self.api_session.close()

    @request_with_logging_and_errors
    @request_with_logging
    async def _post_request_with_logging_and_errors_raised(
        self, url: str, json_body: dict, auth_token: str = None
    ) -> ClientResponse:
        headers = {aiohttp_headers.USER_AGENT: USER_AGENT}
        if auth_token is not None:
            headers["X-HatchBaby-Auth"] = auth_token
        return await self.api_session.post(url=url, json=json_body, headers=headers)

    @request_with_logging
    @request_with_logging_and_errors
    async def _get_request_with_logging_and_errors_raised(
        self, url: str, auth_token: str = None, params: dict = None
    ) -> ClientResponse:
        headers = {aiohttp_headers.USER_AGENT: USER_AGENT}
        if auth_token is not None:
            headers["X-HatchBaby-Auth"] = auth_token
        return await self.api_session.get(url=url, headers=headers, params=params)

    async def login(self, email: str, password: str) -> str:
        url = API_URL + "public/v1/login"
        json_body = {
            "email": email,
            "password": password,
        }
        response: ClientResponse = (
            await self._post_request_with_logging_and_errors_raised(
                url=url, json_body=json_body
            )
        )
        response_json = await response.json()
        return response_json["token"]

    async def member(self, auth_token: str):
        url = API_URL + "service/app/v2/member"
        response: ClientResponse = (
            await self._get_request_with_logging_and_errors_raised(
                url=url, auth_token=auth_token
            )
        )
        response_json = await response.json()
        return response_json["payload"]

    async def iot_devices(self, auth_token: str):
        url = API_URL + "service/app/iotDevice/v2/fetch"
        params = {"iotProducts": "restPlus, restMini, restore"}
        response: ClientResponse = (
            await self._get_request_with_logging_and_errors_raised(
                url=url, auth_token=auth_token, params=params,
            )
        )
        response_json = await response.json()
        return response_json["payload"]

    async def token(self, auth_token: str):
        url = API_URL + "service/app/restPlus/token/v1/fetch"
        response: ClientResponse = (
            await self._get_request_with_logging_and_errors_raised(
                url=url, auth_token=auth_token
            )
        )
        response_json = await response.json()
        return response_json["payload"]
