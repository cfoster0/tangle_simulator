from math import ceil
from random import random, gauss

import networkx as nx

import simpy

from tangle import Tangle

N_NODES = 1000
MEAN_TX_TIME = 10
VAR_TX_TIME = 2
TPS_PER_NODE = 0.01	# Probabity that a node will initiate a transaction in a given time step
CONNECTIONS_PER_NODE = 8

N_TRANSACTIONS_TO_BROADCAST = 5

TIME_STEPS = 500

def clock(env):
	while True:
		print("Executing step #{t}...".format(t=env.now))
		yield env.timeout(1)

def step(env, tangle):
	while True:
		tangle.step(env.now)
		yield env.timeout(1)

def node(env, name, gt, lt, inc, out, communications):
	broadcast_queue = []
	while True:
		for connection in inc:
			incoming_tx = communications[connection]
			lt.txs.extend(incoming_tx)
			broadcast_queue.extend(incoming_tx)
			communications[connection] = []

		if (random() < TPS_PER_NODE):	# Initate transaction
			tx_parents = lt.get_tips()
			if not tx_parents:
				raise Exception("No tips left.")
			tx_time = ceil(gauss(MEAN_TX_TIME, VAR_TX_TIME))
			if (tx_time < 0):
				tx_time = 0
			
			yield env.timeout(tx_time)
			lt.make_transaction(name, env.now,
				tx_parents)
			gt.make_transaction(name, env.now,
				tx_parents)
		else:
			yield env.timeout(1)

		for connection in out:
			bq = list(broadcast_queue)
			for i in range(min(N_TRANSACTIONS_TO_BROADCAST, len(bq))):
				outgoing_tx = bq.pop()
				communications[connection].append(outgoing_tx)

global_tangle = Tangle()

topology = nx.random_regular_graph(CONNECTIONS_PER_NODE, N_NODES)
connections = list(topology.edges()) + [tuple(reversed(x)) for x in list(topology.edges)]
communications = {}
for connection in connections:
	communications[connection] = []

env = simpy.Environment()
env.process(clock(env))
env.process(step(env, global_tangle))
local_tangles = []
for i in range(N_NODES):
	local_tangle = Tangle()
	env.process(step(env, local_tangle))
	income = [(x, y) for (x, y) in connections if y == i]
	outgo = [(x, y) for (x, y) in connections if x == i]
	env.process(node(env, i, global_tangle, local_tangle, income, outgo, communications))
env.run(until=TIME_STEPS)

"""
import matplotlib.pyplot as plt
_, uctps = zip(*sorted(global_tangle.log['uctps'].items()))
plt.plot(uctps)
plt.title("Tips per time step")
plt.show()
"""
