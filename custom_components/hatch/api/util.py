from __future__ import annotations

from aiohttp import ClientError
import logging
import json
import os

from .const import (
    DEFAULT_SAVE_LOCATION,
    MAX_IOT_VALUE,
    SENSITIVE_FIELD_NAMES,
)

_LOGGER = logging.getLogger(__name__)


def clean_dictionary_for_logging(dictionary: dict[str, any]) -> dict[str, any]:
    mutable_dictionary = dictionary.copy()
    for key in dictionary.keys():
        if key.lower() in SENSITIVE_FIELD_NAMES:
            mutable_dictionary[key] = "***"
        if type(mutable_dictionary[key]) is dict:
            mutable_dictionary[key] = clean_dictionary_for_logging(
                mutable_dictionary[key].copy()
            )
        if type(mutable_dictionary[key]) is list:
            new_array = []
            for item in mutable_dictionary[key]:
                if type(item) is dict:
                    new_array.append(clean_dictionary_for_logging(item.copy()))
                else:
                    new_array.append(item)
            mutable_dictionary[key] = new_array

    return mutable_dictionary


def request_with_logging(func):
    async def request_with_logging_wrapper(*args, **kwargs):
        url = kwargs["url"]
        request_message = f"sending {url} request"
        headers = kwargs.get("headers")
        if headers is not None:
            request_message = request_message + f"headers: {headers}"
        json_body = kwargs.get("json_body")
        if json_body is not None:
            request_message = (
                request_message
                + f"sending {url} request with {clean_dictionary_for_logging(json_body)}"
            )
        _LOGGER.debug(request_message)
        response = await func(*args, **kwargs)
        _LOGGER.debug(
            f"response headers:{clean_dictionary_for_logging(response.headers)}"
        )
        try:
            response_json = await response.json()
            _LOGGER.debug(
                f"response json: {clean_dictionary_for_logging(response_json)}"
            )
        except Exception:
            response_text = await response.text()
            _LOGGER.debug(f"response raw: {response_text}")
        return response

    return request_with_logging_wrapper


def request_with_logging_and_errors(func):
    async def request_with_logging_wrapper(*args, **kwargs):
        response = await func(*args, **kwargs)
        response_json = await response.json()
        if response_json.get("status") == "success":
            return response
        if response_json.get("errorCode") == 1001:
            _LOGGER.debug(f"error: session invalid")
            raise AuthError
        raise ClientError(f"api error:{response_json}")

    return request_with_logging_wrapper


def api_to_pct(value: int):
    if value is None:
        return None
    return int((value * 100) / MAX_IOT_VALUE)


def pct_to_api(value: int):
    if value is None:
        return None
    return int((value / 100) * MAX_IOT_VALUE)


def api_to_color(value: int):
    if value is None:
        return None
    return int((value * 255) / MAX_IOT_VALUE)


def color_to_api(value: int):
    if value is None:
        return None
    return int((value / 255) * MAX_IOT_VALUE)


def save_response(response, name="response"):
    if response:
        if not os.path.isdir(DEFAULT_SAVE_LOCATION):
            os.mkdir(DEFAULT_SAVE_LOCATION)
        name = name.replace("/", "_").replace(".", "_").replace("’", "").replace(" ", "_").lower()
        with open(f"{DEFAULT_SAVE_LOCATION}/{name}.json", "w") as file:
            json.dump(response, file, default=lambda o: "not-serializable", indent=4, sort_keys=True)
        file.close()


class BaseError(ClientError):
    pass


class AuthError(BaseError):
    pass


class RateError(BaseError):
    pass
