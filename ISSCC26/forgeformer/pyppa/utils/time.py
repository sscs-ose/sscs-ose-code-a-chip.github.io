import time

class TimeElapsed():
	days: int
	hours: int
	minutes: int
	seconds: int
	total_seconds: int

	def __init__(self, total_seconds: int) -> None:
		days, remaining_seconds = divmod(total_seconds, 24 * 60 * 60)
		hours, remaining_seconds = divmod(remaining_seconds, 60 * 60)
		minutes, seconds = divmod(remaining_seconds, 60)

		self.days = days
		self.hours = hours
		self.minutes = minutes
		self.seconds = seconds
		self.total_seconds = total_seconds

	def combined(*elapsed_times: list["TimeElapsed"]) -> "TimeElapsed":
		total_seconds = 0
		for elapsed_time in elapsed_times:
			total_seconds += elapsed_time.total_seconds

		return TimeElapsed(total_seconds)

	def format(self) -> str:
		formatted_time_segments = []

		show_next_segment = False
		for key in ['days', 'hours', 'minutes', 'seconds']:
			value = self.__getattribute__(key)

			if value > 0 or show_next_segment:
				formatted_time_segments.append(f"{value}{key[0]}")
				show_next_segment = True

		return ' '.join(formatted_time_segments)

def start_time_count() -> int:
	return int(time.time())

def get_elapsed_time(start_time: int) -> TimeElapsed:
	num_seconds = int(time.time()) - start_time

	return TimeElapsed(num_seconds)