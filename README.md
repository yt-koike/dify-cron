# Cron

**Author:** yt-koike
**Version:** 0.1.0
**Type:** extension

## Description

Cron can automatically trigger workflows at a certain time or frequency.
This plugin also works on https://cloud.dify.ai/ with a help of https://cron-job.org

If you want to use this plugin on the cloud, please get an API Key on https://cron-job.org in advance. Reference: https://blog.cron-job.org/service/news/2021/12/23/cron-job-org-api.html

## How to Start and Stop Cron

Here are the instructions how to use this Cron plugin.

### 1. Install Cron

![alt text](_assets/installed.png)

### 2. Add an endpoint

- Endpoint Name: Name of this endpoint. You can input a custom name here.
- App: Workflow or Chatflow to trigger regularly
- Cron: When this plugin will trigger the workflow. Please see the Cron Format section to make a valid setting.
- Timezone: Supports identifiers(e.g. Asia/Tokyo) of Python Zoneinfo and PHP TimeZone.
- Is this cloud version?: Set to True if you use this plugin on https://cloud.dify.ai
- API key for cron-job.org: You can get it on https://console.cron-job.org/settings after logging in.

![alt text](_assets/endpoint.png)

### 3. [Important] Start Cron

You need to access the endpoint URL.
You will see this message on the page so click "Start?" link ONCE. Do not click it for multiple times. After clicking it once, please reload the page. If the message changed to "Cron status: active", Cron is now turned on.
![alt text](_assets/cron.png)

Caution: Endpoint switch(below) will not start or stop Cron! Please switch on or off it via endpoint URLs.
![alt text](_assets/switch.png)

### 4. Stop Cron

If you want to stop Cron, access to the page of the previous section and click "Stop?" link.

## How to Use

After you start Cron, it will automatically trigger workflows.

If you want to know a certain query came from Cron or not, you can use an optional input variable "is_cron".
If Cron made that query, is_cron is set to "yes", otherwise is_cron is empty.
You can make a branch with an if block like the workflow below.
![alt text](_assets/is_cron.png)

## Required APIs and Credentials

For self-hosted servers, no external APIs or credentials are required.

For cloud.dify.ai, access to https://cron-job.org/ is required.
For further details regarding this access, please refer to [PRIVACY.md](https://github.com/yt-koike/dify-cron/blob/main/PRIVACY.md).

## Connection requirements

On self-hosted servers, this plugin operates independently without external connections.

On cloud.dify.ai, this plugin must establish a connection to https://cron-job.org .
Additional information on this requirement is available in [PRIVACY.md](https://github.com/yt-koike/dify-cron/blob/main/PRIVACY.md).

## Cron Format

The order is "seconds minutes hours days months weekdays".
Wildcards and lists are supported. Step values like `*/5` are allowed for the
seconds, minutes and hours fields only.
For example, `0,15,30,45 * * * * *` will trigger the workflow every fifteen seconds.
`0 */5 * * * *` runs every five minutes.

Note: to apply changes to the Cron string, you must disable the service and then re-enable it.
Caution: Cloud version does NOT support "seconds" and the first argument will be ignored.

## Reference

- Repository: https://github.com/yt-koike/dify-cron
- Cron Logo: https://iconduck.com/icons/154528/cronjob
