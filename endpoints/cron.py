import time
from typing import Mapping
from werkzeug import Request, Response
from dify_plugin import Endpoint
import datetime

from dify_plugin.core.runtime import Session

started_app_ids = set()

STATUS_ACTIVE_HTML = "<html><head></head><body>Cron status: active <br><a href='./stop'>Stop?</a></body></html>"
STATUS_INACTIVE_HTML = "<html><head></head><body>Cron status: inactive <br><a href='./start'>Start?</a></body></html>"
STOP_HTML = '<html><head></head><body>Stop requested. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
START_HTML = (
    '<html><head></head><body>Cron started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>',
)
ALREADY_STARTED_HTML = '<html><head></head><body>Cron already started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
ALREADY_STOPPED_HTML = (
    '<html><head></head><body>Cron was not running. Returning in 5 seconds... '
    '<meta http-equiv="refresh" content="5;URL=./status"></body></html>'
)


def _match(field: str, current: int, allow_step: bool = False) -> bool:
    """Return True if the cron field matches the current value."""
    if field == "*":
        return True
    if field.startswith("*/"):
        if not allow_step:
            raise Exception("Invalid cron setting")
        try:
            step = int(field[2:])
        except ValueError as exc:
            raise Exception("Invalid cron setting") from exc
        if step <= 0:
            raise Exception("Invalid cron setting")
        return current % step == 0
    try:
        return current in map(int, field.split(","))
    except ValueError as exc:
        raise Exception("Invalid cron setting") from exc


def is_now_to_call(cron_str):
    # Check if it is time to make a self call
    # This cron is mostly based on UNIX cron format: https://www.ibm.com/docs/en/db2-as-a-service?topic=task-unix-cron-format
    # Sunday = 0, Monday = 1, ... and lastly Saturday = 6
    # This cron also supports seconds and step values (e.g. */5)
    cron_str = cron_str.strip()
    if len(cron_str.split(" ")) != 6:
        raise Exception("Invalid cron setting")
    seconds, minutes, hours, days, months, weekdays = cron_str.split(" ")
    now = datetime.datetime.now()

    if not _match(seconds, now.second, allow_step=True):
        return False
    if not _match(minutes, now.minute, allow_step=True):
        return False
    if not _match(hours, now.hour, allow_step=True):
        return False
    if not _match(days, now.day):
        return False
    if not _match(months, now.month):
        return False
    if not _match(weekdays, (now.weekday() + 1) % 7):
        return False
    return True


def cron_loop(session: Session, app_id, cron_str):
    is_triggered = False
    while True:
        if not app_id in started_app_ids:
            return Response("Cron Stopped")
        time.sleep(0.1)
        if is_now_to_call(cron_str):
            if not is_triggered:
                session.app.chat.invoke(
                    app_id, "!cron!", {"is_cron": "yes"}, "blocking", ""
                )
                is_triggered = True
        else:
            is_triggered = False


class CronEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        command = values["command"]
        app_id = settings.get("app")["app_id"]
        cron_str = settings.get("cron_str")
        try:
            is_now_to_call(cron_str)
        except:
            raise Exception("Invalid cron setting")

        if len(command) == 0 or command == "status":
            return Response(
                (
                    STATUS_ACTIVE_HTML
                    if app_id in started_app_ids
                    else STATUS_INACTIVE_HTML
                ),
                status=200,
                content_type="text/html",
            )
        elif command == "stop":
            if app_id in started_app_ids:
                started_app_ids.discard(app_id)
                return Response(
                    STOP_HTML,
                    status=200,
                    content_type="text/html",
                )
            else:
                return Response(
                    ALREADY_STOPPED_HTML,
                    status=200,
                    content_type="text/html",
                )
        elif command == "start":
            if app_id in started_app_ids:
                return Response(
                    ALREADY_STARTED_HTML,
                    status=200,
                    content_type="text/html",
                )
            started_app_ids.add(app_id)
            #print(f"Starting cron for app {app_id} with cron string {cron_str}")
            res =  cron_loop(self.session, app_id, cron_str)
            #print(f"Stop cron for app {app_id}")
            return res
        else:
            return Response("Invalid Command")
