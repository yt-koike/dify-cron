import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from endpoints.cron import is_now_to_call


def test_step_allowed_seconds_minutes_hours():
    try:
        is_now_to_call("*/5 */10 */2 * * *")
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
        is_now_to_call(cron)


def test_step_zero_invalid():
    with pytest.raises(Exception):
        is_now_to_call("*/0 * * * * *")
