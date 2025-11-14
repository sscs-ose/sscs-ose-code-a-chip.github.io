from typing import TypedDict, Any, Union, Iterator

class ParameterSweepDict(TypedDict):
	start: float
	end: float
	step: float

class ParameterListDict(TypedDict):
	values: list[Any]

class ConfigsIteratorEntry(TypedDict):
	values: list[Any]
	i: int

class ConfigsIterator:
	config_number: int = 0
	num_config_vars: int = 0
	configs_iterator_items: dict[str, ConfigsIteratorEntry]
	configs_iterated: bool = False

	def iterate(self) -> Iterator[tuple[dict[str, Any], int]]:
		return iter(self)

	def __init__(self, configs_iterator_items: dict[str, ConfigsIteratorEntry]):
		self.configs_iterator_items = configs_iterator_items
		self.num_config_vars = len(configs_iterator_items.keys())
		self.configs_iterated = self.num_config_vars == 0

	def __iter__(self):
		self.config_number = 0

		for parameter_name in self.configs_iterator_items:
			self.configs_iterator_items[parameter_name]['i'] = 0

		return self

	def __next__(self) -> tuple[dict[str, Any], int]:
		if self.configs_iterated and self.config_number != 0:
				raise StopIteration

		self.config_number += 1
		generated_config = {}

		change_next_param = True
		for i, parameter_name in enumerate(self.configs_iterator_items.items()):
			generated_config = self.__generate_config()

			if change_next_param:
				parameter_name[1]['i'] += 1

			change_next_param = parameter_name[1]['i'] == len(parameter_name[1]['values'])

			if change_next_param:
				parameter_name[1]['i'] = 0

			if i == self.num_config_vars - 1 and change_next_param:
				self.configs_iterated = True

		return (generated_config, self.config_number)

	def __generate_config(self):
		config = {}

		for iterator_entry in self.configs_iterator_items.items():
			config[iterator_entry[0]] = iterator_entry[1]['values'][iterator_entry[1]['i']]

		return config

def get_configs_iterator(parameters: dict[str, Union[ParameterSweepDict, ParameterListDict, Any]]) -> ConfigsIterator:
	configs_iterator_items: dict[str, ConfigsIteratorEntry] = {}

	for parameter_name in parameters.items():
		config_values: list[ConfigsIteratorEntry] = []

		if type(parameter_name[1]) is dict:
			if 'values' in parameter_name[1]:
				config_values = parameter_name[1]['values']

			elif 'start' in parameter_name[1] and 'end' in parameter_name[1]:
				value = parameter_name[1]['start']
				step = parameter_name[1]['step'] if 'step' in parameter_name[1] else 1

				while value <= parameter_name[1]['end']:
					config_values.append(value)
					value += step
		else:
			config_values = [parameter_name[1]]

		configs_iterator_items[parameter_name[0]] = {
			'values': config_values,
			'i': 0
		}

	return ConfigsIterator(configs_iterator_items)