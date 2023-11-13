import json
import logging
import os
import pytz
from collections import defaultdict
from datetime import datetime
from typing import Optional, Union, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from shapely.geometry import Point, Polygon
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from starlette.middleware.sessions import SessionMiddleware

from drop_backend.commands.webdemo_command_helper import (
    TaggedEvent,
    geotag_moodtag_events_helper,
)
from drop_backend.model.merge_base import bind_engine
from drop_backend.types.custom_types import When
from drop_backend.utils.formatting import format_event_summary
from drop_backend.utils.ors import (
    Profile,
    TransitDirectionError,
    TransitDirectionSummary,
)
from dotenv import load_dotenv
from .utils.constants import boundary_geo_json
from drop_backend.utils.datetime_utils import (
    assert_datetime_format,
    datetime_string_processor,
)

# TODO:
## Use env vars to set the FILE_VERSION constrains
## Use them for floating time and date
## stick them in the env file and fire up the app locally in uvicorn/docker
load_dotenv()
ALLOWED_ORIGINS = os.environ.get("ALLOWD_ORIGINS", "").strip().split(",")
SQLLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH", "").strip()
NOW_WINDOW_HOURS = int(
    os.environ.get("NOW_WINDOW_HOURS", "1").strip()
)  # Make this a const
DEFAULT_START_TIME = os.environ.get("DEFAULT_START_TIME", "08:00").strip()
_FIX_NOW_DATETIME = os.environ.get("FIX_NOW_DATETIME", "").strip()
FIX_NOW_DATETIME = None
if _FIX_NOW_DATETIME:
    if assert_datetime_format(_FIX_NOW_DATETIME, "%Y-%m-%d %H:%M"):
        FIX_NOW_DATETIME = datetime.strptime(_FIX_NOW_DATETIME, "%Y-%m-%d %H:%M")
    elif assert_datetime_format(_FIX_NOW_DATETIME, "%Y-%m-%d"):
        FIX_NOW_DATETIME = datetime.strptime(_FIX_NOW_DATETIME, "%Y-%m-%d")
    else:
        raise ValueError(
            "FIX_NOW_DATETIME must be in the format %Y-%m-%d with an optional %H:%M"
        )

RELOAD_WEBAPP = os.environ.get("RELOAD_WEBAPP", "False").lower() in ["true", "1"]
SECRET_KEY = os.environ.get("SECRET_KEY")
ORS_API_ENDPOINT = os.environ.get("ORS_API_ENDPOINT", "").strip()
# in the format "file1:[version1,version2],file2:[version2]"
_FILE_VERSION_CONSTRAINTS_STR = os.environ.get("FILE_VERSION_CONSTRAINTS", "").strip()
FILE_VERSION_CONSTRAINTS_DICT: Dict[str, List[str]] = {}
if _FILE_VERSION_CONSTRAINTS_STR:
    FILE_VERSION_CONSTRAINTS_DICT: Dict[str, List[str]] = json.loads(  # type: ignore
        _FILE_VERSION_CONSTRAINTS_STR
    )
    assert FILE_VERSION_CONSTRAINTS_DICT and len(FILE_VERSION_CONSTRAINTS_DICT) > 0
    assert isinstance(FILE_VERSION_CONSTRAINTS_DICT, dict) and all(
        isinstance(vs, list) and len(vs) > 0
        for vs in FILE_VERSION_CONSTRAINTS_DICT.values()
    ), "FILE_VERSION_CONSTRAINTS must be a non empty json string with a dict of lists"
else:
    raise ValueError(
        "FILE_VERSION_CONSTRAINTS not set. Must be set to a non empty json string"
    )

assert ALLOWED_ORIGINS and isinstance(
    ALLOWED_ORIGINS, list
), "Allowed origins not set or wrong"
assert SQLLITE_DB_PATH, "SQLLITE_DB_PATH not set"
assert SECRET_KEY, "SECRET_KEY not set"
assert ORS_API_ENDPOINT, "ORS_API_ENDPOINT not set"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGINS,
    ],
    allow_credentials=True,
    allow_methods=["GET"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
FILE_PATH = os.path.dirname(__file__)
print(
    " main module FILE_PATH: ", FILE_PATH, " all static will be found relative to this"
)
templates = Jinja2Templates(directory=os.path.join(FILE_PATH, "templates"))

# Needed for serving static files for the templates like CSS, JS
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(FILE_PATH, "static")),
    name="static",
)

_engine: Engine


@app.get("/presence/where", response_class=HTMLResponse)
async def where(request: Request):
    """
    Tell us where you are on a map rendered by this route via leaflet.
    """
    request.session["lat"] = None
    request.session["lng"] = None

    boundary_geo_json_str = (
        json.dumps(boundary_geo_json)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("'", "\\u0027")
    )
    return templates.TemplateResponse(
        "where.html",
        {"request": request, "boundary_geo_json_str": boundary_geo_json_str},
    )


@app.get("/presence/are_you_really_here", response_class=HTMLResponse)
async def validate(lat: Optional[float] = None, long: Optional[float] = None):
    if _is_where_you_are_valid(lat, long):
        return "Ok"
    raise HTTPException(
        status_code=400,
        detail="The selected location is not valid or outside the allowed area.",
    )


@app.get("/presence/here/", response_class=HTMLResponse)
async def here(
    request: Request,
    lat: Optional[float] = None,
    long: Optional[float] = None,
    when: When = When.NOW,
):
    """
    Validate the location(which establishes you "here"). Here being in a certain predefined area.
    If the location is valid then return the events using swiper UI
    """
    if lat is not None and long is not None:
        print("Lat long passed by user")
        request.session["lat"] = lat
        request.session["lng"] = long

    lat = request.session.get("lat")
    long = request.session.get("lng")
    print("Lat long from session", lat, long)

    if _is_where_you_are_valid(lat, long):
        assert lat and long
        print("You are here.")
        # now lets get all the events that are going to happen close to now
        if not FIX_NOW_DATETIME:
            eastern = pytz.timezone("US/Eastern")
            datetime_now = datetime.strptime(
                datetime.now(eastern).strftime("%Y-%m-%d %H:%M"), ("%Y-%m-%d %H:%M")
            )
        else:
            datetime_now = FIX_NOW_DATETIME
        # For testing
        # datetime_now = datetime.strptime("2023-09-01 10:00", "%Y-%m-%d %H:%M")
        # Pass lat long, when to the backend method to get the data.
        filtered_events = geotag_moodtag_events_helper(
            _engine,
            ORS_API_ENDPOINT,
            FILE_VERSION_CONSTRAINTS_DICT,
            # For testing
            # filename="hobokengirl_com_hoboken_jersey_city_events_september_1_2023_20230913_160012_a.txt_postprocessed",
            # version="v1",
            where_lat=lat,
            where_lon=long,
            datetime_now=datetime_now,
            when=when,
            now_window_hours=NOW_WINDOW_HOURS,
        )
        events_by_mood = defaultdict(list)

        def get_directions_obj(
            directions: Union[TransitDirectionError, TransitDirectionSummary, None]
        ):
            if isinstance(directions, TransitDirectionError):
                return None
            return directions

        def get_closest_address_directions(tagged_event: TaggedEvent):
            (
                closest_walkable_addess_directions,
                closest_address,
            ) = tagged_event.directions[
                0
            ]  # Already sorted by time
            walking_directions = (
                closest_walkable_addess_directions[Profile.foot_walking]
                if Profile.foot_walking in closest_walkable_addess_directions
                else None
            )
            driving_directions = (
                closest_walkable_addess_directions[Profile.driving_car]
                if Profile.driving_car in closest_walkable_addess_directions
                else None
            )
            return (
                get_directions_obj(walking_directions),
                get_directions_obj(driving_directions),
                closest_address,
            )

        for tagged_event in filtered_events:
            (
                closest_walking_directions,
                closest_driving_directions,
                closest_address,
            ) = get_closest_address_directions(tagged_event)
            assert (
                tagged_event.event.event_json is not None
            ), "Something must have gone horribly wrong..."
            event_with_selected_cols = {
                "name": tagged_event.event.name,
                "description": tagged_event.event.description,
                # TODO: Fix the type on event by using the right ones from the local types module.
                "mood": tagged_event.event.mood,  # type: ignore
                "submood": tagged_event.event.submood,  # type: ignore
                "start_date": (
                    tagged_event.event.event_json.get(  # type: ignore
                        "start_date", None
                    )
                    or [datetime_now.strftime("%Y-%m-%d")]
                )[
                    0
                ],  # N2S: When start_* fields are empty the business logic assumes and asserts that events ongoing(now) else it will never be empty .
                "start_time": (
                    tagged_event.event.event_json.get(  # type: ignore
                        "start_time", None
                    )
                    or [DEFAULT_START_TIME]
                )[0],
                "addresses": list(i[-1] for i in tagged_event.directions),  # type: ignore
                "closest_address": closest_address,
                "closest_walking_distance_and_duration": closest_walking_directions,
                "closest_driving_distance_and_duration": closest_driving_directions,
                "links": tagged_event.event.event_json.get("links", []),  # type: ignore
            }
            event_with_selected_cols["mini_summary"] = format_event_summary(
                event_with_selected_cols, when, 1, datetime_now
            )
            events_by_mood[tagged_event.event.mood].append(  # type: ignore
                event_with_selected_cols
            )

        # Sort each submood group by the event time
        for mood, events in events_by_mood.items():
            events_by_mood[mood] = sorted(
                events,
                key=lambda x: (
                    x["start_date"],
                    x["start_time"],
                ),  # Assuming start_date and start_time are lists with at least one element each
            )
        template_data = {
            "request": request,
            "when": when.value,
            "events_by_mood": events_by_mood,
            "no_events": len(filtered_events)
            == 0,  # Flag to indicate whether there are events or not
        }
        return templates.TemplateResponse("here_partial.html", template_data)
    raise HTTPException(
        status_code=400,
        detail="The selected location is invalid or outside the allowed area.",
    )


def _is_where_you_are_valid(lat: Optional[float], long: Optional[float]) -> bool:
    if not lat or not long:
        return False
    point = Point(long, lat)  # Note: Shapely uses (lng, lat) order
    boundary_coords = boundary_geo_json["features"][0]["geometry"]["coordinates"][0]
    boundary = Polygon(boundary_coords)
    if boundary.contains(point):
        print("You are here.")
        return True
    return False


def init_db():
    logger.info("Initating DB")
    _engine = create_engine(SQLLITE_DB_PATH, connect_args={"check_same_thread": False})
    bind_engine(_engine)
    logger.info("Initalized DB")
    return _engine


def run():
    # Is called when we run via an entry point when testig/debugging say (typically with an entry point within poetry:
    # `poetry run herenow_demo`). There is a slight glitch here.
    # When running with `poetry run` the uvicorn with the string argument
    # it will trigger the DB initialization twice since uvicorn imports this module again using the string, which executes the else block below.
    # This is not a problem per se right now, but it is a bit of a hack.
    # Ideally just use gunicorn or uvicorn from the cli directly as shown below.
    logger.warning("In run() context, ONLY USE FOR DEBUGGING NOT PROD")
    import uvicorn

    # init_db()
    # NOTE that usually we can pass the app object directly to uvicorn.run
    # TODO: remove reload in production.
    uvicorn.run(
        "herenow_demo.main:app", host="0.0.0.0", port=8000, reload=RELOAD_WEBAPP
    )


if __name__ == "__main__":
    # For direct execution as a script; typically in a virtual env like: `python -m herenow_demo.main`.
    #
    # DON'T use this in production!
    logger.info("In context %s. ONLY USE FOR DEBUGGING NOT PROD", __name__)
    _engine = init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=RELOAD_WEBAPP)

else:
    # From Command line directly or say via docker:
    #  `uvicorn herenow_demo.main:app --host 0.0.0.0 --port 8000 --reload` # Though don't use --reload and don't use uvicorn with its --workers option since that is more limited in capabilities than using `gunicorn``.
    # Recommended way(https://fastapi.tiangolo.com/deployment/server-workers/):
    # gunicorn herenow_demo.main:app --bind 0.0.0.0:8000 --workers 1 --worker-class uvicorn.workers.UvicornWorker
    #  `poetry run herenow_demo`(which indirectly runs: "herenow_demo.main:run" i.e. run())
    logger.info("In context %s", __name__)
    _engine = init_db()
