import pendulum

class TimeAPI:
    def __init__(self, timezone="Asia/Kolkata"):
        """
        Initialize the TimeAPI object with a default timezone.
        """
        self.timezone = timezone
        self.now = pendulum.now(self.timezone)

    def is_today(self, date):
        """
        Check if the given date is today.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date.is_today()

    def current_time(self):
        """
        Get the current date and time in MySQL format (YYYY-MM-DD HH:mm:ss).
        """
        return self.now.to_datetime_string()

    def current_date(self):
        """
        Get the current date in YYYY-MM-DD format.
        """
        return self.now.to_date_string()

    def is_date_in_current_week(self, date):
        """
        Check if the given date is in the current week.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return self.now.start_of('week') <= parsed_date <= self.now.end_of('week')
    
    def get_yesterday(self):
        """
        Get yesterday's date.
        """
        return self.now.subtract(days=1).to_date_string()

    def get_tomorrow(self):
        """
        Get tomorrow's date.
        """
        return self.now.add(days=1).to_date_string()

    def was_yesterday(self, date):
        """
        Check if the given date was yesterday.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date == self.now.subtract(days=1).start_of('day')

    def is_tomorrow(self, date):
        """
        Check if the given date is tomorrow.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date == self.now.add(days=1).start_of('day')

    def is_past(self, date):
        """
        Check if the given date is in the past.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date < self.now

    def is_future(self, date):
        """
        Check if the given date is in the future.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date > self.now

    def add_days(self, date, days):
        """
        Add days to a given date.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date.add(days=days).to_date_string()

    def subtract_days(self, date, days):
        """
        Subtract days from a given date.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date.subtract(days=days).to_date_string()

    def time_difference(self, date1, date2):
        """
        Return the difference between two dates in days, hours, minutes, and seconds.
        """
        parsed_date1 = pendulum.parse(date1, tz=self.timezone)
        parsed_date2 = pendulum.parse(date2, tz=self.timezone)
        diff = parsed_date1.diff(parsed_date2)
        return {
            "days": diff.in_days(),
            "hours": diff.in_hours(),
            "minutes": diff.in_minutes(),
            "seconds": diff.in_seconds()
        }

    def is_weekend(self, date):
        """
        Check if the given date is a weekend.
        """
        parsed_date = pendulum.parse(date, tz=self.timezone)
        return parsed_date.day_of_week in [pendulum.SATURDAY, pendulum.SUNDAY]

    def start_of_week(self):
        """
        Return the start of the current week.
        """
        return self.now.start_of('week').to_datetime_string()

    def get_all_dates_between(self, start_date, end_date):
        """
        Return all dates between the start and end date, inclusive.
        """
        start = pendulum.parse(start_date, tz=self.timezone)
        end = pendulum.parse(end_date, tz=self.timezone)
        dates = []
        current_date = start

        while current_date <= end:
            dates.append(current_date.to_date_string())
            current_date = current_date.add(days=1)
        return dates

time_api = TimeAPI()
# previousWeakEndDate = time_api.subtract_days(time_api.start_of_week()[0:10], 2)
# previousWeakStartDate = time_api.subtract_days(previousWeakEndDate, 5)
# print(time_api.get_all_dates_between(previousWeakStartDate, previousWeakEndDate))
#allPreviousDates = time_api.get_all_dates_between(previousWeakStartDate, previousWeakEndDate)