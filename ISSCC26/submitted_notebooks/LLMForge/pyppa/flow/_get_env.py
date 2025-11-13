from typing import Optional

def get_env(self, init_env: Optional[dict] = None) -> dict:
	env = {**init_env} if init_env is not None else {}

	for key in self.config:
		value = self.config[key]

		match type(value):
			case t if t in [tuple, list]: # Join list options with spaces in between
				env[key] = ' '.join(value)

			case t if t in [int, float]: # Convert numerical values to string
				env[key] = str(value)

			case t if t is bool: # Convert boolean values to integers
				env[key] = str(int(value))

			case _: # Fallback to string
				env[key] = str(value)

	return env
