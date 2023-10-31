import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, Union

from contextlib import asynccontextmanager
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
from .utils.constants import boundary_geo_json

# sys.path.append(
#     "/Users/sid/workspace/drop/"
# )  # I need to install drop and then run the webdemo as its own project to get rid of this hackery.

logger = logging.getLogger(__name__)
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # TODO: Replace once committed.
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],  # Allows requests only from "https://example.com"
    allow_credentials=True,
    allow_methods=["GET"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.add_middleware(SessionMiddleware, secret_key="my-secret-key")

templates = Jinja2Templates(directory="src/herenow_demo/templates")

app.mount("/static", StaticFiles(directory="src/herenow_demo/static"), name="static")
NOW_WINDOW_HOURS = 1  # Make this a const
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
        datetime_now = datetime.strptime("2023-09-01 10:00", "%Y-%m-%d %H:%M")
        # Pass lat long, when to the backend method to get the data.
        filtered_events = geotag_moodtag_events_helper(
            _engine,
            filename="hobokengirl_com_hoboken_jersey_city_events_september_1_2023_20230913_160012_a.txt_postprocessed",
            version="v1",
            where_lat=lat,
            where_lon=long,
            datetime_now=datetime_now,
            when=when,
            now_window_hours=1,
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
                    or ["00:00"]
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

# TODO: replace with a non hardcoded path.
SQLLITE_PATH = "sqlite:////Users/sid/workspace/drop/drop.db"
def init_db():
    print("Initating DB")


    global _engine
    _engine = create_engine(
        SQLLITE_PATH, connect_args={"check_same_thread": False}
    )  # Create new DB
    bind_engine(_engine)
    print("Initalized DB")


def run():
    # import uvicorn

    init_db()
    # NOTE that usually we can pass the app object directly to uvicorn.run
    # but
    # TODO: remove reload in production.
    # uvicorn.run("herenow_demo.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
