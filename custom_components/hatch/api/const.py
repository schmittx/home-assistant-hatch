SENSITIVE_FIELD_NAMES = [
    "username",
    "password",
]

MAX_IOT_VALUE = 65535

REST_MINI_TRACKS = {
    0: "None",
    10124: "Heartbeat",
    10125: "Water",
    10126: "White Noise",
    10127: "Dryer",
    10128: "Ocean",
    10129: "Wind",
    10130: "Rain",
    10131: "Birds",
}

REST_PLUS_TRACKS = {
    0: "None",
    2: "Water",
    3: "White Noise",
    4: "Dryer",
    5: "Ocean",
    6: "Wind",
    7: "Rain",
    9: "Birds",
    10: "Crickets",
    11: "Brahms' Lullaby",
    13: "Twinkle Twinkle Little Star",
    14: "Rock-a-bye Baby",
}

DEFAULT_SAVE_ENABLED = False
DEFAULT_SAVE_LOCATION = f"/config/custom_components/hatch/api/responses"

CLOCK_FORMAT_OFF_12H = 0
CLOCK_FORMAT_OFF_24H = 2048
CLOCK_FORMAT_ON_12H = 32768
CLOCK_FORMAT_ON_24H = 34816

CLOCK_FORMAT_ON = [
    CLOCK_FORMAT_ON_12H,
    CLOCK_FORMAT_ON_24H,
]

CLOCK_FORMAT_24H = [
    CLOCK_FORMAT_OFF_24H,
    CLOCK_FORMAT_ON_24H,
]

NO_ACTIVE_PROGRAM = "no_active_program"

PRODUCT_REST_MINI = "restMini"
PRODUCT_REST_PLUS = "restPlus"

PRODUCT_MODEL_MAP = {
    PRODUCT_REST_MINI: "Rest Mini",
    PRODUCT_REST_PLUS: "Rest Plus",
}

USER_AGENT = "hatch_rest_api"

API_URL: str = "https://data.hatchbaby.com/"
