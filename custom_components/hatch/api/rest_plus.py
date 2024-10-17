from __future__ import annotations

import logging

from .const import (
    CLOCK_FORMAT_24H,
    CLOCK_FORMAT_ON,
    CLOCK_FORMAT_OFF_12H,
    CLOCK_FORMAT_OFF_24H,
    CLOCK_FORMAT_ON_12H,
    CLOCK_FORMAT_ON_24H,
    NO_ACTIVE_PROGRAM,
    REST_PLUS_TRACKS,
)
from .device import Device
from .util import (
    api_to_color,
    api_to_pct,
    color_to_api,
    pct_to_api,
    save_response,
)

_LOGGER = logging.getLogger(__name__)


class Audio:

    def __init__(self, state: dict):
        self.track = state.get("t")
        self._volume = state.get("v")
        self.volume = api_to_pct(self._volume)
        self.name = str(REST_PLUS_TRACKS[self.track]) if self.track else None
        self.image = f"rest_plus/{self.track}" if self.name else None
        self.list = list(REST_PLUS_TRACKS.values())[1:]


class Clock:

    def __init__(self, state: dict):
        self._brightness = state.get("b")
        self.brightness = api_to_pct(self._brightness)
        self.format = state.get("f")


class Color:

    def __init__(self, state: dict):
        self._red = state.get("r")
        self._green = state.get("g")
        self._blue = state.get("b")
        self._intensity = state.get("i")
        self.red = api_to_color(self._red)
        self.green = api_to_color(self._green)
        self.blue = api_to_color(self._blue)
        self.intensity = api_to_color(self._intensity)
        self.white = bool(state.get("W"))
        self.rainbow = bool(state.get("R"))


class Preset:

    def __init__(self, index: str, state: dict):
        self.index = int(index)
        self.audio = Audio(state.get("a"))
        self.color = Color(state.get("c"))
        self.favorite = state.get("f")
        self.is_favorite = bool(self.favorite in [128, 192])
        self.is_enabled = bool(self.favorite == 192)


class Program:

    def __init__(self, index: str, state: dict):
        self.index = int(index)
        self.audio = Audio(state.get("a", {}))
        self.color = Color(state.get("c", {}))
        self.name = state.get("n")
        self.favorite = state.get("f")
        self.is_favorite = bool(self.favorite)
        self.is_enabled = bool(self.favorite == 192)


class State:

    def __init__(self, state: dict):
        self.audio = Audio(state.get("a", {}))
        self.clock = Clock(state.get("clock", {}))
        self.color = Color(state.get("c", {}))


class RestPlus(Device):

    def _update_local_state(self, state) -> None:
        _LOGGER.debug(f"[{self.info.name}] Updating API state: {state}")
        self.previous_state = State(state=self.state)
        self.state = self._merge_state(current=self.state, update=state)
        save_response(self.state, self.info.name, self.save_response_enabled)
        self.publish_updates()

    @property
    def is_device_on(self) -> bool:
        return bool(self.state.get("isPowered"))

    @is_device_on.setter
    def is_device_on(self, power: bool) -> None:
        self._update(
            {
                "isPowered": bool(power),
            }
        )

    @property
    def clock(self) -> Clock:
        return Clock(self.state.get("clock", {}))

    def _set_clock(self, brightness: int = None, format: int = None) -> None:
        data = {}
        if brightness is not None:
            data["b"] = pct_to_api(brightness)
        if format is not None:
            data["f"] = format
        if not data:
            data = {
                "b": pct_to_api(self.previous_state.clock.brightness),
                "f": self.previous_state.clock.format,
            }

        self._update(
            {
                "clock": data,
            }
        )
        _LOGGER.debug(f"[{self.info.name}] Set clock state: {data}")

    def _get_clock_format(self, clock_enabled: bool = None, clock_24hr_time: bool = None) -> int:
        format = self.clock.format
        if clock_enabled is None:
            clock_enabled = self.clock_enabled
        if clock_24hr_time is None:
            clock_24hr_time = self.clock_24hr_time
        if clock_enabled:
            if clock_24hr_time:
                format = CLOCK_FORMAT_ON_24H
            format = CLOCK_FORMAT_ON_12H
        else:
            if clock_24hr_time:
                format = CLOCK_FORMAT_OFF_24H
            format = CLOCK_FORMAT_OFF_12H
        if format == self.clock.format:
            _LOGGER.debug(f"[{self.info.name}] Clock format was not changed from current state: {format}")
        return format

    @property
    def clock_brightness(self) -> int:
        return self.clock.brightness

    @clock_brightness.setter
    def clock_brightness(self, value: int) -> None:
        self._set_clock(brightness=value)

    @property
    def clock_enabled(self) -> bool:
        return bool(self.clock.format in CLOCK_FORMAT_ON)

    @clock_enabled.setter
    def clock_enabled(self, value: bool) -> None:
        self._set_clock(format=self._get_clock_format(clock_enabled=value))

    @property
    def clock_24hr_time(self) -> bool:
        return bool(self.clock.format in CLOCK_FORMAT_24H)

    @clock_24hr_time.setter
    def clock_24hr_time(self, value: bool) -> None:
        self._set_clock(format=self._get_clock_format(clock_24hr_time=value))

    @property
    def sound_machine(self) -> bool:
        return True

    @property
    def audio(self) -> Audio:
        return Audio(self.state.get("a", {}))

    @property
    def is_audio_on(self) -> bool:
        return all(
            [
                self.is_device_on,
                self.audio.track,
                self.audio.volume,
            ]
        )

    def set_audio(self, track: str = None, volume: int = None) -> None:
        data = {}
        if track is not None:
            data["t"] = list(REST_PLUS_TRACKS.keys())[list(REST_PLUS_TRACKS.values()).index(track)]
        if volume is not None:
            data["v"] = pct_to_api(volume)
        if not data:
            data = {
                "t": self.previous_state.audio.track,
                "v": pct_to_api(self.previous_state.audio.volume),
            }

        self._update(
            {
                "isPowered": True,
                "activePresetIndex": 0,
                "a": data,
            }
        )
        _LOGGER.debug(f"[{self.info.name}] Set audio state: {data}")

    def set_audio_volume(self, volume: int) -> None:
        self.set_audio(volume=volume)

    def set_audio_track(self, track: str) -> None:
        self.set_audio(track=track)

    def turn_on_audio(self) -> None:
        self.set_audio()

    def turn_off_audio(self) -> None:
        self.set_audio_track("None")

    @property
    def battery_level(self) -> str | None:
        return self.state.get("deviceInfo", {}).get("b")

    @property
    def nightlight(self) -> bool:
        return True

    @property
    def color(self) -> Color:
        return Color(self.state.get("c", {}))

    @property
    def is_light_on(self) -> bool:
        return all(
            [
                bool(self.color.intensity),
                any(
                    [
                        bool(self.color.red),
                        bool(self.color.green),
                        bool(self.color.blue),
                        self.color.white,
                        self.color.rainbow,
                    ]
                ),
            ]
        )

    def set_color(self, red: int=None, green: int=None, blue: int=None, intensity: int=None, white: bool=None, rainbow: bool=None):
        data = {}
        if red is not None:
            data["r"] = color_to_api(red)
        if green is not None:
            data["g"] = color_to_api(green)
        if blue is not None:
            data["b"] = color_to_api(blue)
        if intensity is not None:
            data["i"] = color_to_api(intensity)
        if white is not None:
            data["W"] = bool(white)
        if rainbow is not None:
            data["R"] = bool(rainbow)
        if not data:
            data = {
                "r": color_to_api(self.previous_state.color.red),
                "g": color_to_api(self.previous_state.color.green),
                "b": color_to_api(self.previous_state.color.blue),
                "i": color_to_api(self.previous_state.color.intensity),
                "W": self.previous_state.color.white,
                "R": self.previous_state.color.rainbow,
            }
        self._update(
            {
                "isPowered": True,
                "activePresetIndex": 0,
                "c": data,
            }
        )

    def turn_on_light(self, red, green, blue, intensity, white, rainbow):
        self.set_color(
            red=red,
            green=green,
            blue=blue,
            intensity=intensity,
            white=white,
            rainbow=rainbow,
        )

    def turn_off_light(self):
        self.set_color(
            red=0,
            green=0,
            blue=0,
            white=False,
            rainbow=False,
        )

    @property
    def presets(self) -> list[Preset]:
        return [Preset(index, state) for index, state in self.state.get("presets", {}).items()]

    @property
    def active_preset_index(self) -> int:
        return self.state.get("activePresetIndex")
    
    def is_preset_active(self, index: int) -> bool:
        return bool(self.active_preset_index == index)

    def enable_preset(self, preset: Preset, enabled: bool) -> None:
        format = 192 if enabled else 128
        self._update(
            {
                "presets": {
                    str(preset.index): {
                        "f": format,
                    }
                }
            }
        )

    def set_preset(self, preset: Preset) -> None:
        self._update(
            {
                "isPowered": True,
                "activePresetIndex": preset.index,
                "a": {
                    "t": preset.audio.track,
                    "v": preset.audio._volume,
                },
                "c": {
                    "r": preset.color._red,
                    "g": preset.color._green,
                    "b": preset.color._blue,
                    "i": preset.color._intensity,
                    "W": preset.color.white,
                    "R": preset.color.rainbow,
                }
            }
        )

    @property
    def programs(self) -> list[Program]:
        return [Program(index, state) for index, state in self.state.get("programs", {}).items()]

    @property
    def active_program_index(self) -> int:
        return self.state.get("activeProgramIndex")

    def is_program_active(self, index: int) -> bool:
        return bool(self.active_program_index == index)

    @property
    def active_program_name(self) -> str:
        for program in self.programs:
            if self.is_program_active(program.index):
                return program.name
        return "none"

    def enable_program(self, program: Program, enabled: bool) -> None:
        format = 192 if enabled else 128
        self._update(
            {
                "programs": {
                    str(program.index): {
                        "f": format,
                    }
                }
            }
        )
