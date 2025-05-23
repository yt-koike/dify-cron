import time
from typing import Mapping
import requests
from werkzeug import Request, Response
from dify_plugin import Endpoint
from dify_plugin.core.runtime import Session

startedSet = set()


class CronEndpoint(Endpoint):
    def is_now_to_call(self, cron_str):
        return False

    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        api_key = settings.get("api_key")
        if api_key in startedSet:
            return Response("Cron Already Started")
        startedSet.add(api_key)
        endpoint_url = settings.get("endpoint_url")
        cron_str = settings.get("api_key")
        """
        Invokes the endpoint with the given request.
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "inputs": {},
            "query": "cron",
            "response_mode": "blocking",
            "conversation_id": "",
            "user": "cron",
            "files": [],
        }
        while True:
            time.sleep(0.5)
            if self.is_now_to_call(cron_str):
                requests.post(
                    endpoint_url + "/v1/chat-messages",
                    headers=headers,
                    json=data,
                )
