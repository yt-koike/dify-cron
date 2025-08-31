from typing import Mapping
from requests import Session
from werkzeug import Request, Response
from dify_plugin import Endpoint

from endpoints.cron_local import CronManager, get_cron_man


class EntryEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        if settings.get("is_cloud"):
            return Response(
                "Sorry, cloud version is not supported for now. Please use this Cron plugin for self-hosted Dify."
            )
        cron_man: CronManager = get_cron_man(self.session)
        app_id = settings.get("app")["app_id"]
        cron_str = settings.get("cron_str")

        if settings.get("is_active", False) == cron_man.is_running(app_id):
            return Response(
                "<html><head></head><body>Already Initiated</body></html>",
                status=200,
                content_type="text/html",
            )

        if settings.get("is_active", False):
            cron_man.start(app_id, cron_str)
            return Response(
                "<html><head></head><body>Job Started</body></html>",
                status=200,
                content_type="text/html",
            )
        else:
            cron_man.stop(app_id)
            return Response(
                "<html><head></head><body>Job Stopped</body></html>",
                status=200,
                content_type="text/html",
            )
