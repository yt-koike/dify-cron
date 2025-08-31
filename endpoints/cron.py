import datetime
import json
import time
from collections.abc import Mapping

import requests
from dify_plugin import Endpoint
from dify_plugin.core.runtime import Session
from werkzeug import Request, Response
from zoneinfo import ZoneInfo

running_app_ids = set()


class JobManager:
    def start(self, app_id: str) -> None:
        global running_app_ids
        running_app_ids.add(app_id)

    def stop(self, app_id: str) -> None:
        global running_app_ids
        running_app_ids.remove(app_id)

    def is_running(self, app_id: str) -> bool:
        global running_app_ids
        return app_id in running_app_ids


STATUS_ACTIVE_HTML = """
<html><head></head><body>app-id: {app-id}<br>
Now@UTC: {now_utc}<br>
Now@{timezone}: {now}<br>
seconds,minutes,hours,days,months,weekdays: {s},{m},{h},{d},{months},{w}<br>
Cron status: active <br><a href='./stop'>Stop?</a></body></html>
"""
STATUS_INACTIVE_HTML = """
<html><head></head><body>app-id: {app-id}<br>
Now@UTC: {now_utc}<br>
Now@{timezone}: {now}<br>
seconds,minutes,hours,days,months,weekdays: {s},{m},{h},{d},{months},{w}<br>
Cron status: inactive <br><a href='./start'>Start?</a></body></html>
"""

STOP_HTML = '<html><head></head><body>Stop requested. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
START_HTML = (
    '<html><head></head><body>Cron started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>',
)
ALREADY_STARTED_HTML = '<html><head></head><body>Cron already started. Returning in 5 seconds... <meta http-equiv="refresh" content="5;URL=./status"></body></html>'
ALREADY_STOPPED_HTML = (
    "<html><head></head><body>Cron was not running. Returning in 5 seconds... "
    '<meta http-equiv="refresh" content="5;URL=./status"></body></html>'
)


class Cron:
    def __init__(self, cron_str: str, timezone: str = "UTC"):
        self.cron_str = cron_str
        if len(cron_str.split(" ")) != 6:
            raise Exception("Invalid cron setting")
        self.timezone = timezone
        self.seconds, self.minutes, self.hours, self.days, self.months, self.weekdays = cron_str.split(" ")
        self.schedule = self.calc_schedule()

    def calc(self, arg: str, min: int, max: int) -> list[int]:
        # Calculate exact values for the argument in most cases.
        # For example, if arg = "*/15" and it is "minutes", then it should be min=0,max=59 and return [0,15,30,45].
        if arg == "*":
            return [-1]
        if arg.startswith("*/"):
            step = int(arg[2:])
            return [x for x in range(min, max + 1) if x % step == 0]

        li = [x for x in map(int, arg.split(",")) if min <= x and x <= max]
        return li

    def calc_schedule(self) -> dict:
        # Calculate schedule data compatible to https://docs.cron-job.org/rest-api.html#jobschedule
        return {
            "timezone": self.timezone,
            "seconds": self.calc(self.seconds, 0, 59),
            "hours": self.calc(self.hours, 0, 23),
            "minutes": self.calc(self.minutes, 0, 59),
            "mdays": self.calc(self.days, 1, 31),
            "months": self.calc(self.months, 1, 12),
            "wdays": self.calc(self.weekdays, 0, 6),
        }

    # def _match(self, field: str, current: int, allow_step: bool = False) -> bool:
    #    """Return True if the cron field matches the current value."""
    #    if field == "*":
    #        return True
    #    if field.startswith("*/"):
    #        if not allow_step:
    #            raise Exception("Invalid cron setting")
    #        try:
    #            step = int(field[2:])
    #        except ValueError as exc:
    #            raise Exception("Invalid cron setting") from exc
    #        if step <= 0:
    #            raise Exception("Invalid cron setting")
    #        return current % step == 0
    #    try:
    #        return current in map(int, field.split(","))
    #    except ValueError as exc:
    #        raise Exception("Invalid cron setting") from exc

    def is_now_to_call(self):
        # Check if it is time to make a self call
        # This cron is mostly based on UNIX cron format: https://www.ibm.com/docs/en/db2-as-a-service?topic=task-unix-cron-format
        # Sunday = 0, Monday = 1, ... and lastly Saturday = 6
        # This cron also supports seconds and step values (e.g. */5)
        now = datetime.datetime.now(tz=ZoneInfo(self.timezone))

        if not (self.seconds == "*" or now.second in self.schedule["seconds"]):
            return False
        if not (self.minutes == "*" or now.minute in self.schedule["minutes"]):
            return False
        if not (self.hours == "*" or now.hour in self.schedule["hours"]):
            return False
        if not (self.days == "*" or now.day in self.schedule["mdays"]):
            return False
        if not (self.months == "*" or now.month in self.schedule["months"]):
            return False
        if not (self.weekdays == "*" or now.weekday() in self.schedule["wdays"]):
            return False
        return True


def run_once(session: Session, app_id: str):
    session.app.chat.invoke(app_id, "!cron!", {"is_cron": "yes"}, "blocking", "")


def cron_loop(session: Session, job_man: JobManager, app_id: str, cron: Cron) -> None:
    is_triggered = False
    while True:
        if not job_man.is_running(app_id):
            break
        time.sleep(0.1)
        if cron.is_now_to_call():
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

    def register_dify_job(self, url: str, cron: Cron):
        # Reference: https://docs.cron-job.org/rest-api.html
        schedule = cron.calc_schedule()
        schedule["expiresAt"] = 0
        job = {
            "job": {
                "url": url,
                "enabled": True,
                "saveResponses": True,
                "schedule": schedule,
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
        cron = Cron(settings.get("cron_str"), timezone=settings.get("timezone", "UTC"))
        job_man = JobManager()
        try:
            cron.is_now_to_call()
        except:
            raise Exception("Invalid cron setting")

        if len(command) == 0 or command == "status":
            if job_man.is_running(app_id):
                html = STATUS_ACTIVE_HTML
            else:
                html = STATUS_INACTIVE_HTML
            html = html.replace("{app-id}", app_id)
            html = html.replace("{now_utc}", datetime.datetime.now(tz=ZoneInfo("UTC")).strftime("%d/%m/%Y, %H:%M:%S"))
            html = html.replace(
                "{now}", datetime.datetime.now(tz=ZoneInfo(cron.timezone)).strftime("%d/%m/%Y, %H:%M:%S")
            )
            html = html.replace("{timezone}", cron.timezone)
            html = html.replace("{s}", str(cron.schedule["seconds"]))
            html = html.replace("{m}", str(cron.schedule["minutes"]))
            html = html.replace("{h}", str(cron.schedule["hours"]))
            html = html.replace("{d}", str(cron.schedule["mdays"]))
            html = html.replace("{months}", str(cron.schedule["months"]))
            html = html.replace("{w}", str(cron.schedule["wdays"]))
            return Response(
                html,
                status=200,
                content_type="text/html",
            )
        elif command == "stop":
            if job_man.is_running(app_id):
                job_man.stop(app_id)
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
            if job_man.is_running(app_id):
                return Response(
                    ALREADY_STARTED_HTML,
                    status=200,
                    content_type="text/html",
                )
            job_man.start(app_id)
            # print(f"Starting cron for app {app_id} with cron string {cron_str}")
            cron_loop(self.session, job_man, app_id, cron)
            # print(f"Stop cron for app {app_id}")
        else:
            return Response("Invalid Command")

    def run_cloud(self, r: Request, values: Mapping, settings: Mapping):
        if "cron_job_org_key" not in settings:
            raise Exception("Please input an API Key from https://cron-job.org")
        api = CronJobAPI(settings["cron_job_org_key"])
        command = values["command"]
        app_id = settings.get("app")["app_id"]
        cron = Cron(settings.get("cron_str"), timezone=settings.get("timezone", "UTC"))

        run_once_url = "/".join(r.base_url.split("/")[:-1]) + "/runOnce"
        if command == "start":
            if run_once_url in api.get_job_urls():
                return Response(
                    ALREADY_STARTED_HTML,
                    status=200,
                    content_type="text/html",
                )
            api.register_dify_job(run_once_url, cron)
            return Response(
                START_HTML,
                status=200,
                content_type="text/html",
            )
        elif command == "stop":
            if run_once_url not in api.get_job_urls():
                return Response(
                    ALREADY_STOPPED_HTML,
                    status=200,
                    content_type="text/html",
                )
            api.delete_job_by_url(run_once_url)
            return Response(
                START_HTML,
                status=200,
                content_type="text/html",
            )
        elif command == "status":
            if app_id in api.get_job_ids():
                html = STATUS_ACTIVE_HTML
            else:
                html = STATUS_INACTIVE_HTML
            html = html.replace("{app-id}", app_id)
            html = html.replace("{now_utc}", datetime.datetime.now(tz=ZoneInfo("UTC")).strftime("%Y/%m/%d, %H:%M:%S"))
            html = html.replace(
                "{now}", datetime.datetime.now(tz=ZoneInfo(cron.timezone)).strftime("%Y/%m/%d, %H:%M:%S")
            )
            html = html.replace("{timezone}", cron.timezone)
            html = html.replace("{s}", str(cron.schedule["seconds"]))
            html = html.replace("{m}", str(cron.schedule["minutes"]))
            html = html.replace("{h}", str(cron.schedule["hours"]))
            html = html.replace("{d}", str(cron.schedule["mdays"]))
            html = html.replace("{months}", str(cron.schedule["months"]))
            html = html.replace("{w}", str(cron.schedule["wdays"]))
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
