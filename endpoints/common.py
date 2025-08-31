import datetime


class CronJob:
    def __init__(self, app_id: int, cron_str: str):
        self.app_id = app_id
        self.cron_str = cron_str
        self.is_triggered: bool = False


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
