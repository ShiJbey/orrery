"""
time.py

Neighborly uses a custom date/time implementation that represents years as 12 months
with 4, 7-day weeks per month. The smallest unit of time is one day. This module
contains the implementation of simulation datetime along with associated constants,
enums, and helper classes.
"""

from __future__ import annotations

from dataclasses import dataclass

DAYS_PER_MONTH = 28
WEEKS_PER_MONTH = 4
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = DAYS_PER_MONTH * MONTHS_PER_YEAR


@dataclass(frozen=True)
class TimeDelta:
    """Represents a difference in time from one SimDateTime to Another"""

    years: int = 0
    months: int = 0
    days: int = 0

    @property
    def total_days(self) -> int:
        """get the total number of days that this delta represents"""
        return (
            self.days
            + (self.months * DAYS_PER_MONTH)
            + (self.years * MONTHS_PER_YEAR * DAYS_PER_MONTH)
        )


class SimDateTime:
    """
    Implementation of time in the simulated town
    using 7-day weeks, 4-week months, and 12-month years
    """

    __slots__ = (
        "_day",
        "_month",
        "_year",
    )

    def __init__(
        self,
        year: int = 0,
        month: int = 0,
        day: int = 0,
    ) -> None:

        if 0 <= day < DAYS_PER_MONTH:
            self._day: int = day
        else:
            raise ValueError(
                f"Parameter 'day' must be between 0 and {DAYS_PER_MONTH - 1}"
            )

        if 0 <= month < MONTHS_PER_YEAR:
            self._month: int = month
        else:
            raise ValueError(
                f"Parameter 'month' must be between 0 and {MONTHS_PER_YEAR - 1}"
            )

        self._year: int = year

    def increment(self, days: int = 0, months: int = 0, years: int = 0) -> None:
        """Advance time by a given amount"""
        if days < 0:
            raise ValueError("Parameter 'days' may not be negative")
        if months < 0:
            raise ValueError("Parameter 'months' may not be negative")
        if years < 0:
            raise ValueError("Parameter 'years' may not be negative")

        total_days: int = self.day + days
        carry_months: int = int(total_days / 28)  # 28 days per month
        self._day = total_days % 28

        total_months: int = self._month + months + carry_months
        carry_years: int = int(total_months / 12)
        self._month = total_months % 12

        self._year = self._year + years + carry_years

    @property
    def day(self) -> int:
        return self._day

    @property
    def month(self) -> int:
        return self._month

    @property
    def year(self) -> int:
        return self._year

    def copy(self) -> SimDateTime:
        return SimDateTime(
            day=self._day,
            month=self._month,
            year=self._year,
        )

    def __repr__(self) -> str:
        return "{}(day={}, month={}, year={})".format(
            self.__class__.__name__,
            self.day,
            self.month,
            self.year,
        )

    def __str__(self) -> str:
        return self.to_date_str()

    def __sub__(self, other: SimDateTime) -> TimeDelta:
        """Subtract a SimDateTime from another and return the difference"""
        diff = self.to_ordinal() - other.to_ordinal()

        # Convert hours back to date components
        years = diff // (MONTHS_PER_YEAR * DAYS_PER_MONTH)
        remainder = diff % (MONTHS_PER_YEAR * DAYS_PER_MONTH)
        months = remainder // DAYS_PER_MONTH
        remainder = remainder % DAYS_PER_MONTH
        days = remainder

        return TimeDelta(years=years, months=months, days=days)

    def __add__(self, other: TimeDelta) -> SimDateTime:
        """Add a TimeDelta to this data"""
        date_copy = self.copy()
        date_copy.increment(days=other.days, months=other.months, years=other.years)
        return date_copy

    def __iadd__(self, other: TimeDelta) -> SimDateTime:
        self.increment(days=other.days, months=other.months, years=other.years)
        return self

    def __le__(self, other: SimDateTime) -> bool:
        return self.to_ordinal() <= other.to_ordinal()

    def __lt__(self, other: SimDateTime) -> bool:
        return self.to_ordinal() < other.to_ordinal()

    def __ge__(self, other: SimDateTime) -> bool:
        return self.to_ordinal() >= other.to_ordinal()

    def __gt__(self, other: SimDateTime) -> bool:
        return self.to_ordinal() > other.to_ordinal()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SimDateTime):
            raise TypeError(f"expected TimeDelta object but was {type(other)}")
        return self.to_ordinal() == other.to_ordinal()

    def to_date_str(self) -> str:
        return "{:02d}/{:02d}/{:04d}".format(self.day, self.month, self.year)

    def to_iso_str(self) -> str:
        """Return ISO string format"""
        return "{:04d}-{:02d}-{:02d}T00:00.000z".format(self.year, self.month, self.day)

    def to_ordinal(self) -> int:
        """Returns the number of elapsed days since 00-00-0000"""
        return (
            +self.day
            + (self.month * DAYS_PER_MONTH)
            + (self.year * MONTHS_PER_YEAR * DAYS_PER_MONTH)
        )

    @classmethod
    def from_ordinal(cls, ordinal_date: int) -> SimDateTime:
        date = cls()
        date.increment(days=ordinal_date)
        return date

    @classmethod
    def from_iso_str(cls, iso_date: str) -> SimDateTime:
        """Return a SimDateTime object given an ISO format string"""
        date_time = iso_date.strip().split("T")
        date = date_time[0]
        year, month, day = tuple(map(lambda s: int(s.strip()), date.split("-")))
        return cls(year=year, month=month, day=day)

    @classmethod
    def from_str(cls, time_str: str) -> SimDateTime:
        time = cls()
        items = tuple(time_str.split("/"))

        if len(items) == 4:
            year, month, day = items
            time._year = int(year)
            time._month = int(month)
            time._day = int(day)
            return time

        elif len(items) == 3:
            year, month, day = items
            time._year = int(year)
            time._month = int(month)
            time._day = int(day)
            return time

        else:
            raise ValueError(f"Invalid date string: {time_str}")
