import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from endpoints.cron import Cron


def test_step_allowed_seconds_minutes_hours():
    try:
        Cron("*/5 */10 */2 * * *").is_now_to_call()
    except Exception as exc:
        pytest.fail(f"Unexpected error: {exc}")


@pytest.mark.parametrize(
    "cron",
    [
        "* * * */5 * *",
        "* * * * */5 *",
        "* * * * * */5",
    ],
)
def test_step_not_allowed_on_day_month_weekday(cron):
    with pytest.raises(Exception):
        Cron(cron).is_now_to_call()


def test_step_zero_invalid():
    with pytest.raises(Exception):
        Cron("*/0 * * * * *").is_now_to_call()
