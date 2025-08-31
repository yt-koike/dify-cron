import json
import requests


class CronJobAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_job_ids(self) -> list[int]:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        result = requests.get(
            "https://api.cron-job.org/jobs",
            headers=headers,
        )
        return [job["jobId"] for job in result.json()["jobs"]]

    def register_job(self, job: dict):
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        result = requests.put("https://api.cron-job.org/jobs", headers=headers, data=json.dumps(job))
        return result.json()["jobId"]

    def register_dify_job(self, workflow_api_key: str):
        # Reference: https://docs.cron-job.org/rest-api.html
        job = {
            "job": {
                "url": "https://api.dify.ai/v1/chat-messages",
                "enabled": True,
                "saveResponses": True,
                "extendedData": {
                    "headers": {"Content-Type": "application/json", "Authorization": f"Bearer {workflow_api_key}"},
                    "body": '{"inputs": {},"query": "!cron!","response_mode": "blocking","conversation_id": "","user": "cron","files": []}',
                },
                "schedule": {
                    "timezone": "GMT",
                    "expiresAt": 0,
                    "hours": [-1],
                    "minutes": [-1],
                    "mdays": [-1],
                    "months": [-1],
                    "wdays": [-1],
                },
                "requestMethod": 1,  # PUT
            }
        }
        return self.register_job(job)


if __name__ == "__main__":
    a = CronJobAPI("Q7oBsE2142aVGhWaCAXxN96FxjJ0Xw3GbcmwEetLeWM=")
    a.register_dify_job("app-fQAB1IxCcvllL7BM0ZPybQUz")
    print(a.get_job_ids())
