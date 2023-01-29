"""
time.py

Neighborly uses a custom date/time implementation that represents years as 12 months
with 4, 7-day weeks per month. The smallest unit of time is one day. This module
contains the implementation of simulation datetime along with associated constants,
enums, and helper classes.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_YEAR = 1
MAX_YEAR = 9999
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
        """Get the total number of days that this delta represents"""
        return (
            self.days
            + (self.months * DAYS_PER_MONTH)
            + (self.years * MONTHS_PER_YEAR * DAYS_PER_MONTH)
        )


class SimDateTime:
    """Implementation of time in the simulation

    Time is simulated using 7-day weeks, 4-week months, and 12-month years.
    This allows the simulation to not need to worry about things like leap-years
    and variable numbers of days per month.
    """

    __slots__ = "_days"

    def __init__(
        self,
        year: int,
        month: int,
        day: int,
    ) -> None:
        """
        Parameters
        ----------
        year: int
            The starting year, where MIN_YEAR <= year <= MAX_YEAR
        month: int
            The starting month, where 1 <= month  <= 12
        day: int
            The starting day, where 1 <= day <= DAYS_PER_MONTH

        Raises
        ------
        ValueError
            If any of the parameters are outside their allowed ranges
        """

        if 1 <= day <= DAYS_PER_MONTH:
            self._days: int = day - 1
        else:
            raise ValueError(
                f"Parameter 'days', {day} must be between 1 and {DAYS_PER_MONTH}"
            )

        if 1 <= month <= MONTHS_PER_YEAR:
            self._days += (month - 1) * DAYS_PER_MONTH
        else:
            raise ValueError(
                f"Parameter 'months', {month} must be between 1 and {MONTHS_PER_YEAR}"
            )

        if MIN_YEAR <= year <= MAX_YEAR:
            self._days += (year - 1) * DAYS_PER_YEAR
        else:
            raise ValueError(
                f"Parameter 'years', {year} must be between {MIN_YEAR} and {MAX_YEAR}"
            )

    def increment(self, days: int = 0, months: int = 0, years: int = 0) -> None:
        """Advance time by a given amount

        Parameters
        ----------
        days: int, optional
            The number of days to increment the time by
            (defaults to 0)
        months: int, optional
            The number of years to increment the time by
            (defaults to 0)
        years: int, optional
            The number of year ti increment the time by
            (defaults to 0)
        """
        if days < 0:
            raise ValueError("Parameter 'days' may not be negative")
        if months < 0:
            raise ValueError("Parameter 'months' may not be negative")
        if years < 0:
            raise ValueError("Parameter 'years' may not be negative")

        # total_days: int = self.day + days
        # carry_months: int = total_days // (DAYS_PER_MONTH + 1)  # 28 days per month
        # self._day = total_days - (carry_months * DAYS_PER_MONTH)
        #
        # total_months: int = self._month + months + carry_months
        # carry_years: int = total_months // (MONTHS_PER_YEAR + 1)  # 12 months per year
        # self._month = total_months - (carry_years * MONTHS_PER_YEAR)
        #
        # self._year = self._year + years + carry_years

        self._days += days + (months * DAYS_PER_MONTH) + (years * DAYS_PER_YEAR)

    @property
    def day(self) -> int:
        return ((self._days % DAYS_PER_YEAR) % DAYS_PER_MONTH) + 1

    @property
    def month(self) -> int:
        return ((self._days % DAYS_PER_YEAR) // DAYS_PER_MONTH) + 1

    @property
    def year(self) -> int:
        return (self._days // DAYS_PER_YEAR) + 1

    def weekday(self) -> int:
        """Get the current weekday

        Returns
        -------
        int
            Where 0 = Monday and 6 = Sunday
        """
        return (self.day - 1) % 7

    def copy(self) -> SimDateTime:
        return SimDateTime.from_ordinal(self.to_ordinal())

    def __repr__(self) -> str:
        return "{}(day={}, month={}, year={})".format(
            self.__class__.__name__,
            self.day,
            self.month,
            self.year,
        )

    def __str__(self) -> str:
        return self.to_iso_str()

    def __int__(self) -> int:
        return self.to_ordinal()

    def __sub__(self, other: SimDateTime) -> TimeDelta:
        """Subtract a SimDateTime from another and return the difference"""
        diff = self._days - other._days

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

    def __hash__(self) -> int:
        return self._days

    def to_date_str(self) -> str:
        return "{:02d}/{:02d}/{:04d}".format(self.day, self.month, self.year)

    def to_iso_str(self) -> str:
        """Return ISO string format"""
        return "{:04d}-{:02d}-{:02d}T00:00.000z".format(self.year, self.month, self.day)

    def to_ordinal(self) -> int:
        """Returns the number of elapsed days since 01-01-0000"""
        return self._days + 1

    @classmethod
    def from_ordinal(cls, ordinal_date: int) -> SimDateTime:
        """Create a SimDateTime instance from an ordinal date

        Ordinal date 1 is 01/01/0001
        """

        if ordinal_date < 1 or ordinal_date > MAX_YEAR * DAYS_PER_YEAR:
            raise ValueError(
                f"Ordinal date must be between 1 and {MAX_YEAR * DAYS_PER_YEAR}"
            )

        total_days = ordinal_date - 1
        day = ((total_days % DAYS_PER_YEAR) % DAYS_PER_MONTH) + 1
        month = ((total_days % DAYS_PER_YEAR) // DAYS_PER_MONTH) + 1
        year = (total_days // DAYS_PER_YEAR) + 1

        return cls(year, month, day)

    @classmethod
    def from_iso_str(cls, iso_date: str) -> SimDateTime:
        """Create a SimDateTime instance using an ISO-8601 formatted string"""
        date_time = iso_date.strip().split("T")
        date = date_time[0]
        year, month, day = tuple(map(lambda s: int(s.strip()), date.split("-")))
        return cls(year=year, month=month, day=day)

    @classmethod
    def from_str(cls, time_str: str) -> SimDateTime:
        """Create SimDateTime instance using DD/MM/YYYY formatted string"""

        items = tuple(time_str.split("/"))

        if len(items) == 3:
            day, month, year = items
            return cls(year=int(year), month=int(month), day=int(day))

        else:
            raise ValueError(
                f"Invalid date string: {time_str}. Need to be form DD/MM/YYYY"
            )
