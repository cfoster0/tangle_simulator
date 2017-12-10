import sys

import numpy as np

from data_to_pomdp import data_to_pomdp

def main(arguments):
	trials = arguments[1:]
	trial_data = []
	for trial in trials:
		trial_data.append(np.load(trial).item())

	data = {}
	data['global'] = []
	data['local'] = []
	for trial in trial_data:
		data['global'].extend(trial['global'])
		data['local'].extend(trial['local'])

	data_to_pomdp(data)

if __name__ == '__main__':
	main(sys.argv)