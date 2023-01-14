from orrery.core.time import SimDateTime, TimeDelta


def test_copy():
    original_date = SimDateTime()
    copy_date = original_date.copy()

    assert id(original_date) != id(copy_date)


def test__sub__():
    date_2 = SimDateTime(year=1, month=3, day=23)
    date_1 = SimDateTime(year=1, month=2, day=23)

    diff = date_2 - date_1

    assert diff.years == 0
    assert diff.months == 1
    assert diff.total_days == 28


def test__add__():
    date = SimDateTime()
    new_date = date + TimeDelta(months=5, days=27)
    assert new_date.month == 5
    assert new_date.day == 27
    assert date.month == 0
    assert date.day == 0


def test__iadd__():
    date = SimDateTime()
    date += TimeDelta(months=5, days=27)
    assert date.month == 5
    assert date.day == 27


def test__le__():
    assert (SimDateTime() <= SimDateTime()) is True
    assert (SimDateTime() <= SimDateTime(year=2000)) is True
    assert (SimDateTime(year=3000) <= SimDateTime()) is False


def test__lt__():
    assert (SimDateTime() < SimDateTime()) is False
    assert (SimDateTime() < SimDateTime(year=2000)) is True
    assert (SimDateTime(year=3000) < SimDateTime()) is False


def test__ge__():
    assert (SimDateTime() >= SimDateTime()) is True
    assert (SimDateTime() >= SimDateTime(year=2000)) is False
    assert (SimDateTime(year=3000) >= SimDateTime()) is True


def test__gt__():
    assert (SimDateTime() > SimDateTime()) is False
    assert (SimDateTime() > SimDateTime(year=2000)) is False
    assert (SimDateTime(year=3000) > SimDateTime()) is True


def test__eq__():
    assert (SimDateTime() == SimDateTime()) is True
    assert (SimDateTime() == SimDateTime(year=2000)) is False
    assert (SimDateTime(year=3000) == SimDateTime()) is False
    assert (SimDateTime(year=3000) == SimDateTime(year=3000)) is True


def test_to_date_str():
    date = SimDateTime(2022, 6, 27)
    assert date.to_date_str() == "27/06/2022"

    date = SimDateTime(2022, 9, 3)
    assert date.to_date_str() == "03/09/2022"


def test_to_iso_str():
    date = SimDateTime(2022, 6, 27)
    assert date.to_iso_str() == "2022-06-27T00:00.000z"

    date = SimDateTime(2022, 9, 3)
    assert date.to_iso_str() == "2022-09-03T00:00.000z"


def test_to_ordinal():
    date = SimDateTime(2022, 6, 27)
    assert date.to_ordinal() == 679587

    date = SimDateTime(2022, 9, 3)
    assert date.to_ordinal() == 679647


def test_from_ordinal():
    date = SimDateTime.from_ordinal(679710)
    assert date.day == 10
    assert date.month == 11
    assert date.year == 2022


def test_from_iso_str():
    date = SimDateTime.from_iso_str("2022-11-10T00:00:00.000Z")
    assert date.day == 10
    assert date.month == 11
    assert date.year == 2022


def test_from_str():
    date = SimDateTime.from_str("03/10/0002")
    assert date.day == 3
    assert date.month == 10
    assert date.year == 2


def test_increment():
    date = SimDateTime()
    date.increment(days=26)
    assert date.day == 26
    date.increment(days=4)
    assert date.day == 2
    date.increment(days=28)
    assert date.day == 2
    assert date.month == 2
    date.increment(months=12)
    assert date.month == 2
    assert date.year == 1


def test_constructor():
    time = SimDateTime()
    assert time.day == 0
    assert time.month == 0
    assert time.year == 0
