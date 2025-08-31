import datetime
import json
import time
from collections.abc import Mapping

import requests
from dify_plugin import Endpoint
from dify_plugin.core.runtime import Session
from werkzeug import Request, Response

running_app_ids = set()


class CronManager:
    def start(self, app_id) -> None:
        global running_app_ids
        running_app_ids.add(app_id)

    def stop(self, app_id) -> None:
        global running_app_ids
        running_app_ids.remove(app_id)

    def is_running(self, app_id) -> bool:
        global running_app_ids
        return app_id in running_app_ids


STATUS_ACTIVE_HTML = "<html><head></head><body>Cron status: active <br><a href='./stop'>Stop?</a></body></html>"
STATUS_INACTIVE_HTML = "<html><head></head><body>Cron status: inactive <br><a href='./start'>Start?</a></body></html>"
STOP_HTML = '<html><head></head><body>Stop requested. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
START_HTML = (
    '<html><head></head><body>Cron started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>',
)
ALREADY_STARTED_HTML = '<html><head></head><body>Cron already started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
ALREADY_STOPPED_HTML = (
    "<html><head></head><body>Cron was not running. Returning in 5 seconds... "
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


def run_once(session: Session, app_id: str):
    session.app.chat.invoke(app_id, "!cron!", {"is_cron": "yes"}, "blocking", "")


def cron_loop(session: Session, cron_man: CronManager, app_id, cron_str: str) -> None:
    is_triggered = False
    while True:
        if not cron_man.is_running(app_id):
            break
        time.sleep(0.1)
        if is_now_to_call(cron_str):
            if not is_triggered:
                run_once(session, app_id)
                is_triggered = True
        else:
            is_triggered = False


class CronJobAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_jobs(self) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        result = requests.get(
            "https://api.cron-job.org/jobs",
            headers=headers,
        )
        return result.json()["jobs"]

    def get_job_ids(self) -> list[int]:
        jobs = self.get_jobs()
        return [job["jobId"] for job in jobs]

    def get_job_urls(self) -> list[str]:
        jobs = self.get_jobs()
        return [job["url"] for job in jobs]

    def register_job(self, job: dict):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        result = requests.put("https://api.cron-job.org/jobs", headers=headers, data=json.dumps(job))
        return result.json()["jobId"]

    def delete_job(self, job_id: int) -> None:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        result = requests.delete(f"https://api.cron-job.org/jobs/{job_id}", headers=headers)

    def delete_job_by_url(self, url: str) -> None:
        for job in self.get_jobs():
            if job["url"] == url:
                self.delete_job(job["jobId"])

    def register_dify_job(
        self,
        url: str,
        timezone: str = "UTC",
        hours: list[int] = [-1],
        minutes: list[int] = [-1],
        mdays: list[int] = [-1],
        months: list[int] = [-1],
        wdays: list[int] = [-1],
    ):
        # Reference: https://docs.cron-job.org/rest-api.html
        job = {
            "job": {
                "url": url,
                "enabled": True,
                "saveResponses": True,
                "schedule": {
                    "timezone": timezone,
                    "expiresAt": 0,
                    "hours": hours,
                    "minutes": minutes,
                    "mdays": mdays,
                    "months": months,
                    "wdays": wdays,
                },
                "requestMethod": 0,  # GET
            }
        }
        return self.register_job(job)


class CronEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        command = values["command"]
        app_id = settings.get("app")["app_id"]
        if settings.get("is_cloud"):
            return self.run_cloud(r, values, settings)
        else:
            return self.run_local(r, values, settings)

    def run_local(self, r: Request, values: Mapping, settings: Mapping) -> Request:
        command = values["command"]
        app_id = settings.get("app")["app_id"]
        cron_str = settings.get("cron_str")
        cron_man = CronManager()
        try:
            is_now_to_call(cron_str)
        except:
            raise Exception("Invalid cron setting")

        if len(command) == 0 or command == "status":
            return Response(
                (STATUS_ACTIVE_HTML if cron_man.is_running(app_id) else STATUS_INACTIVE_HTML),
                status=200,
                content_type="text/html",
            )
        elif command == "stop":
            if cron_man.is_running(app_id):
                cron_man.stop(app_id)
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
            if cron_man.is_running(app_id):
                return Response(
                    ALREADY_STARTED_HTML,
                    status=200,
                    content_type="text/html",
                )
            cron_man.start(app_id)
            # print(f"Starting cron for app {app_id} with cron string {cron_str}")
            cron_loop(self.session, cron_man, app_id, cron_str)
            # print(f"Stop cron for app {app_id}")
        else:
            return Response("Invalid Command")

    def run_cloud(self, r: Request, values: Mapping, settings: Mapping):
        if "cron_job_org_key" not in settings:
            raise Exception("Please input an API Key from https://cron-job.org")
        cron_job = CronJobAPI(settings["cron_job_org_key"])
        command = values["command"]
        app_id = settings.get("app")["app_id"]

        run_once_url = "/".join(r.base_url.split("/")[:-1]) + "/runOnce"
        if command == "start":
            if run_once_url in cron_job.get_job_urls():
                return Response(
                    ALREADY_STARTED_HTML,
                    status=200,
                    content_type="text/html",
                )
            cron_job.register_dify_job(run_once_url)
            return Response(
                START_HTML,
                status=200,
                content_type="text/html",
            )
        elif command == "stop":
            if run_once_url not in cron_job.get_job_urls():
                return Response(
                    ALREADY_STOPPED_HTML,
                    status=200,
                    content_type="text/html",
                )
            cron_job.delete_job_by_url(run_once_url)
            return Response(
                START_HTML,
                status=200,
                content_type="text/html",
            )
        elif command == "status":
            if run_once_url in cron_job.get_job_urls():
                html = STATUS_ACTIVE_HTML
            else:
                html = STATUS_INACTIVE_HTML
            return Response(
                html,
                status=200,
                content_type="text/html",
            )
        elif command == "runOnce":
            run_once(self.session, app_id)
            return Response(
                "OK",
                status=200,
                content_type="text/html",
            )
