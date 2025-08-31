import datetime
import threading
import time
from collections.abc import Mapping
import asyncio
from dify_plugin import Endpoint
from dify_plugin.core.runtime import Session
from werkzeug import Request, Response
from endpoints.common import is_now_to_call, CronJob


class CronManager:
    def __init__(self, session: Session):
        # This class uses a global variable "started_app_ids" for trans-session management of cron jobs.
        self.jobs: set[CronJob] = set()
        self.session = session
        self.is_loop_running: bool = False

    def start(self, app_id: int, cron_str: str) -> None:
        self.jobs.add(CronJob(app_id, cron_str))
        self.start_loop()

    def stop(self, app_id: int) -> bool:
        for job in self.jobs:
            if job.app_id == app_id:
                self.jobs.remove(job)
                return True
        return False

    def is_running(self, app_id: int) -> bool:
        return app_id in self.jobs

    def get_running_jobs(self) -> list[CronJob]:
        return self.jobs

    def start_loop(self) -> None:
        if self.is_loop_running:
            return
        self.is_loop_running = True
        self.main_loop()

    def main_loop(self) -> None:
        while True:
            for job in self.jobs:
                if is_now_to_call(job.cron_str):
                    if not job.is_triggered:
                        self.session.app.chat.invoke(job.app_id, "!cron!", {"is_cron": "yes"}, "blocking", "")
                        job.is_triggered = True
                else:
                    job.is_triggered = False
            time.sleep(0.1)


def get_cron_man(session: Session) -> CronManager:
    # Singleton Design Pattern
    global global_cron_man
    if "global_cron_man" not in globals():
        global_cron_man = CronManager(session)
    return global_cron_man


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
