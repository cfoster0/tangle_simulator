import os, time, json, gzip
from math import floor
from random import sample

import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

from iota import Tangle, Node, Adversary

N_NODES = 100
NEIGHBORS_PER_NODE = 8
TPS = 20
BANDWIDTH_LIMIT = 10

TIME_STEPS = 1000
LOG_PERIOD = 1000

MAKE_ORIGINAL_AT = 200
START_ATTACK_AT = 400

SAMPLE_SIZE = 10

def initialize_simulation(n, npn, tps, bw):
	global_tangle = Tangle()
	global_tangle.dag.add_node(global_tangle.genesis)
	global_tangle.tips.append(global_tangle.genesis)

	topology = nx.random_regular_graph(npn, n)
	while not nx.is_connected(topology):
		topology = nx.random_regular_graph(npn, n)

	connections = list(topology.edges()) + [tuple(reversed(x)) for x in list(topology.edges)]
	communications = {}
	for connection in connections:
		communications[connection] = []

	nodes = []
	local_tangles = []
	for i in range(N_NODES):
		local_tangle = Tangle()
		local_tangles.append(local_tangle)
		income = [(x, y) for (x, y) in connections if y == i]
		outgo = [(x, y) for (x, y) in connections if x == i]
		if i == 0:
			node = Adversary(i, global_tangle, local_tangle, tps/n, bw, income, outgo, communications)
		else:
			node = Node(i, global_tangle, local_tangle, tps/n, bw, income, outgo, communications)
		nodes.append(node)

	return global_tangle, nodes


def main():
	tangle, nodes = initialize_simulation(n=N_NODES, npn=NEIGHBORS_PER_NODE, tps=TPS, bw=BANDWIDTH_LIMIT)

	adversary_tangle = nodes[0].lt

	data = {}
	data['global'] = []
	data['local'] = []

	uctps = []

	tx_original = None
	tx_double_spend = None

	original_weights = []
	double_spend_weights = []

	observed_original_weights = []
	observed_double_spend_weights = []

	for time_step in range(TIME_STEPS):
		print("Executing step #{t}...".format(t=time_step))
		for node in nodes:
			if time_step is MAKE_ORIGINAL_AT and type(node) is Adversary:
				node.transact_single_spend()
				tx_original = node.original
			
			if time_step == START_ATTACK_AT and type(node) is Adversary:
				node.double_spend_step()
				tx_double_spend = node.double_spend
			else:
				node.step()
		tangle.step(time_step)

		weight_original = 0
		weight_double_spend = 0

		observed_weight_original = 0
		observed_weight_double_spend = 0

		action = None

		if tx_original:
			action = 'wait'

			sample_tips = []
			if len(tangle.tips) > SAMPLE_SIZE:
				sample_tips = sample(tangle.tips, SAMPLE_SIZE)
			else:
				sample_tips = tangle.tips

			adversary_tips = []
			if len(adversary_tangle.tips) > SAMPLE_SIZE:
				adversary_tips = sample(adversary_tangle.tips, SAMPLE_SIZE)
			else:
				adversary_tips = adversary_tangle.tips


			for tip in sample_tips:
				if nx.has_path(tangle.dag, tx_original, tip):
					weight_original += 1 * (SAMPLE_SIZE / len(sample_tips))
			for tip in adversary_tips:
				if nx.has_path(tangle.dag, tx_original, tip):
					observed_weight_original += 1 * (SAMPLE_SIZE / len(adversary_tips))
		
		if tx_double_spend:
			action = 'build'

			sample_tips = []
			if len(tangle.tips) > SAMPLE_SIZE:
				sample_tips = sample(tangle.tips, SAMPLE_SIZE)
			else:
				sample_tips = tangle.tips

			adversary_tips = []
			if len(adversary_tangle.tips) > SAMPLE_SIZE:
				adversary_tips = sample(adversary_tangle.tips, SAMPLE_SIZE)
			else:
				adversary_tips = adversary_tangle.tips

			for tip in sample_tips:
				if nx.has_path(tangle.dag, tx_double_spend, tip):
					weight_double_spend += 1 * (SAMPLE_SIZE / len(sample_tips))
			for tip in adversary_tips:
				if nx.has_path(tangle.dag, tx_double_spend, tip):
					observed_weight_double_spend += 1 * (SAMPLE_SIZE / len(adversary_tips))

		weight_original = floor(weight_original)
		weight_double_spend = floor(weight_double_spend)
		observed_weight_original = floor(observed_weight_original)
		observed_weight_double_spend = floor(observed_weight_double_spend)

		original_weights.append(weight_original)
		double_spend_weights.append(weight_double_spend)

		observed_original_weights.append(observed_weight_original)
		observed_double_spend_weights.append(observed_weight_double_spend)

		alphabet = {}
		alphabet[0] = 'a'
		alphabet[1] = 'b'
		alphabet[2] = 'c'
		alphabet[3] = 'd'
		alphabet[4] = 'e'
		alphabet[5] = 'f'
		alphabet[6] = 'g'
		alphabet[7] = 'h'
		alphabet[8] = 'i'
		alphabet[9] = 'j'
		alphabet[10] = 'k'

		global_state = '{to}-{td}'.format(to=alphabet[weight_original], td=alphabet[weight_double_spend])
		local_state = '{oo}-{od}'.format(oo=alphabet[observed_weight_original], od=alphabet[observed_weight_double_spend])

		print('S={g} and O={l}'.format(g=global_state, l=local_state))

		if action:
			data['global'].append([global_state, action])
			data['local'].append(local_state)

	np.save("N{nn}NPN{npn}TPS{tps}BW{bw}".format(nn=N_NODES, npn=NEIGHBORS_PER_NODE, tps=TPS, bw=BANDWIDTH_LIMIT) + '.npy', data) 

if __name__ == '__main__':
	main()
