import pytest

from orrery.core.time import SimDateTime, TimeDelta


def test_copy():
    original_date = SimDateTime(1, 1, 1)
    copy_date = original_date.copy()

    assert id(original_date) != id(copy_date)
    assert original_date.day == copy_date.day
    assert original_date.month == copy_date.month
    assert original_date.year == copy_date.year


def test__sub__():
    date_2 = SimDateTime(year=1, month=3, day=23)
    date_1 = SimDateTime(year=1, month=2, day=23)

    diff = date_2 - date_1

    assert diff.years == 0
    assert diff.months == 1
    assert diff.total_days == 28


def test__add__():
    date = SimDateTime(1, 1, 1)
    new_date = date + TimeDelta(months=5, days=27)
    assert new_date.month == 6
    assert new_date.day == 28
    assert date.month == 1
    assert date.day == 1


def test__iadd__():
    date = SimDateTime(1, 1, 1)
    date += TimeDelta(months=5, days=27)
    assert date.month == 6
    assert date.day == 28


def test__le__():
    assert (SimDateTime(1, 1, 1) <= SimDateTime(1, 1, 1)) is True
    assert (SimDateTime(1, 1, 1) <= SimDateTime(2000, 1, 1)) is True
    assert (SimDateTime(3000, 1, 1) <= SimDateTime(1, 1, 1)) is False


def test__lt__():
    assert (SimDateTime(1, 1, 1) < SimDateTime(1, 1, 1)) is False
    assert (SimDateTime(1, 1, 1) < SimDateTime(2000, 1, 1)) is True
    assert (SimDateTime(3000, 1, 1) < SimDateTime(1, 1, 1)) is False


def test__ge__():
    assert (SimDateTime(1, 1, 1) >= SimDateTime(1, 1, 1)) is True
    assert (SimDateTime(1, 1, 1) >= SimDateTime(2000, 1, 1)) is False
    assert (SimDateTime(3000, 1, 1) >= SimDateTime(1, 1, 1)) is True


def test__gt__():
    assert (SimDateTime(1, 1, 1) > SimDateTime(1, 1, 1)) is False
    assert (SimDateTime(1, 1, 1) > SimDateTime(2000, 1, 1)) is False
    assert (SimDateTime(3000, 1, 1) > SimDateTime(1, 1, 1)) is True


def test__eq__():
    assert (SimDateTime(1, 1, 1) == SimDateTime(1, 1, 1)) is True
    assert (SimDateTime(1, 1, 1) == SimDateTime(2000, 1, 1)) is False
    assert (SimDateTime(3000, 1, 1) == SimDateTime(1, 1, 1)) is False
    assert (SimDateTime(3000, 1, 1) == SimDateTime(3000, 1, 1)) is True


def test_to_date_str():
    date = SimDateTime(2022, 6, 27)
    assert date.to_date_str() == "27/06/2022"

    date = SimDateTime(2022, 9, 3)
    assert date.to_date_str() == "03/09/2022"


def test_to_iso_str():
    date = SimDateTime(2022, 6, 27)
    assert date.to_iso_str() == "2022-06-27T00:00:00"

    date = SimDateTime(2022, 9, 3)
    assert date.to_iso_str() == "2022-09-03T00:00:00"


def test_to_ordinal():
    date = SimDateTime(2022, 6, 27)
    assert date.to_ordinal() == 679223

    date = SimDateTime(1005, 9, 3)
    assert date.to_ordinal() == 337571


def test_from_ordinal():
    d0 = SimDateTime.from_ordinal(679710)
    assert d0.day == 10
    assert d0.month == 12
    assert d0.year == 2023

    d1 = SimDateTime.from_ordinal(1)
    assert d1.day == 1
    assert d1.month == 1
    assert d1.year == 1

    d1 = SimDateTime.from_ordinal(12)
    assert d1.day == 12
    assert d1.month == 1
    assert d1.year == 1

    d1 = SimDateTime.from_ordinal(29)
    assert d1.day == 1
    assert d1.month == 2
    assert d1.year == 1

    d1 = SimDateTime.from_ordinal(336)
    assert d1.day == 28
    assert d1.month == 12
    assert d1.year == 1


def test_from_iso_str():
    d0 = SimDateTime.from_iso_str("2022-11-10T00:00:00.000Z")
    assert d0.day == 10
    assert d0.month == 11
    assert d0.year == 2022

    d0 = SimDateTime.from_iso_str("2021-07-28")
    assert d0.day == 28
    assert d0.month == 7
    assert d0.year == 2021


def test_from_str():
    date = SimDateTime.from_str("03/10/0002")
    assert date.day == 3
    assert date.month == 10
    assert date.year == 2


def test_increment():
    d0 = SimDateTime(1, 1, 1)

    d0.increment(days=26)
    assert d0.day == 27
    assert d0.month == 1
    assert d0.year == 1
    assert d0.weekday() == 5

    # Check that the last day of the month is not skipped
    d0.increment(days=1)
    assert d0.day == 28
    assert d0.month == 1
    assert d0.year == 1

    d0.increment(days=4)
    assert d0.day == 4
    assert d0.month == 2
    assert d0.year == 1
    assert d0.weekday() == 3

    # Advance it by the equivalent of 1 month in days
    d0.increment(days=28)
    assert d0.day == 4
    assert d0.month == 3
    assert d0.year == 1
    assert d0.weekday() == 3

    # Advance ir by the equivalent of one year in months
    d0.increment(months=12)
    assert d0.day == 4
    assert d0.month == 3
    assert d0.year == 2
    assert d0.weekday() == 3

    d1 = SimDateTime(1, 10, 1)

    d1.increment(months=1)
    assert d1.month == 11
    assert d1.year == 1

    # Check that december is not skipped
    d1.increment(months=1)
    assert d1.month == 12
    assert d1.year == 1

    # Check that years properly roll over
    d1.increment(months=1)
    assert d1.month == 1
    assert d1.year == 2

    d1.increment(days=3, months=4, years=1)
    assert d1.day == 4
    assert d1.month == 5
    assert d1.year == 3

    d2 = SimDateTime(3, 5, 4)

    d2.increment(days=32, months=24, years=3)
    assert d2.day == 8
    assert d2.month == 6
    assert d2.year == 8

    d3 = SimDateTime(3, 5, 4)

    d3.increment(days=4, months=1, years=5)
    assert d3.day == 8
    assert d3.month == 6
    assert d3.year == 8


def test_constructor():
    t0 = SimDateTime(1, 1, 1)
    assert t0.day == 1
    assert t0.month == 1
    assert t0.year == 1
    assert t0.weekday() == 0

    t1 = SimDateTime(200, 5, 7)
    assert t1.day == 7
    assert t1.month == 5
    assert t1.year == 200
    assert t1.weekday() == 6

    t2 = SimDateTime(2023, 11, 23)
    assert t2.day == 23
    assert t2.month == 11
    assert t2.year == 2023
    assert t2.weekday() == 1

    t3 = SimDateTime(2023, 12, 28)
    assert t3.day == 28
    assert t3.month == 12
    assert t3.year == 2023
    assert t3.weekday() == 6

    with pytest.raises(ValueError):
        SimDateTime(0, 1, 1)

    with pytest.raises(ValueError):
        SimDateTime(10_000, 1, 1)

    with pytest.raises(ValueError):
        SimDateTime(1, 0, 1)

    with pytest.raises(ValueError):
        SimDateTime(1, 13, 1)

    with pytest.raises(ValueError):
        SimDateTime(1, 1, 0)

    with pytest.raises(ValueError):
        SimDateTime(1, 1, 31)
