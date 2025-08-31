from collections.abc import Mapping

from dify_plugin import Endpoint
from werkzeug import Request, Response


class EntryEndpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        return Response(
            '<html><head></head><body>Redirecting to main menu... <meta http-equiv="refresh" content="1;URL=./cron/status"></body></html>',
            status=200,
            content_type="text/html",
        )
