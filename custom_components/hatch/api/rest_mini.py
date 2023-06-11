from __future__ import annotations

import logging

from .const import REST_MINI_TRACKS
from .device import Device
from .util import api_to_pct, pct_to_api, save_response

_LOGGER = logging.getLogger(__name__)


class Audio:

    def __init__(self, state: dict):
        self.playing = state.get("playing")
        self.track = state.get("sound", {}).get("id")
        self._volume = state.get("sound", {}).get("v")
        self.volume = api_to_pct(self._volume)
        self.name = str(REST_MINI_TRACKS[self.track]) if self.track else None
        self.image = f"rest_mini/{self.track}" if self.name != "Heartbeat" else None
        self.list = list(REST_MINI_TRACKS.values())[1:]


class State:

    def __init__(self, state: dict):
        self.audio = Audio(state.get("current", {}))


class RestMini(Device):

    def _update_local_state(self, state):
        _LOGGER.debug(f"[{self.info.name}] Updating API state: {state}")
        self.previous_state = State(state=self.state)
        self.state = self._merge_state(current=self.state, update=state)
        if self.save_responses:
            save_response(self.state, self.info.name)
        self.publish_updates()

    @property
    def sound_machine(self):
        return True

    @property
    def audio(self):
        return Audio(self.state.get("current", {}))

    @property
    def is_audio_on(self) -> bool:
        return bool(self.audio.playing == "remote")

    def set_audio(self, playing: bool = True, track: str = None, volume: int = None):
        data, sound = {}, {}
        if playing is not None:
            data["playing"] = "remote" if playing else "none"
        if track is not None:
            sound["id"] = list(REST_MINI_TRACKS.keys())[list(REST_MINI_TRACKS.values()).index(track)]
        if volume is not None:
            sound["v"] = pct_to_api(volume)
        if not data and not sound:
            data["playing"] = self.previous_state.audio.playing,
            sound = {
                "id": self.previous_state.audio.track,
                "v": pct_to_api(self.previous_state.audio.volume),
            }
        data["sound"] = sound

        self._update(
            {
                "current": data,
            }
        )
        _LOGGER.debug(f"[{self.info.name}] Set audio state: {data}")

    def set_audio_volume(self, volume: int):
        self.set_audio(volume=volume)

    def set_audio_track(self, track: str):
        self.set_audio(track=track)

    def turn_on_audio(self):
        self.set_audio(playing=True)

    def turn_off_audio(self):
        self.set_audio(playing=False)
