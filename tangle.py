from math import ceil, floor
from random import random, gauss, choice
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

import hashlib
import heapq
import simpy

NETWORK_NODES = 1000
MEAN_TX_TIME = 10
VAR_TX_TIME = 2
TPS_PER_NODE = 0.01	# Probabity that a node will initiate a transaction in a given time step

TIME_STEPS = 3000

class Tangle():

	def __init__(self):
		self.dag = nx.DiGraph()
		self.tips = []
		self.n_tips = []
		self.confirmed = Counter()
		self.txs = []
		self.log = {"tps": Counter(), "uctps": Counter(), "ctps": Counter(), 'verbose': []}
		self.make_transaction(None, None, [])

	def make_transaction(self, node_name, time_stamp, parents):
		base_tx = (node_name, time_stamp, parents)
		tx = hashlib.sha3_224(str(base_tx).encode()).hexdigest()
		self.log['verbose'].append("@{tim}, transaction: {t}\n\t{p}\n".format(tim=time_stamp, t=tx, p=parents))
		self.txs.append(tx)
		self.dag.add_node(tx)
		for parent in parents:
			self.dag.add_edge(parent, tx)
			self.confirmed[parent] += 1

		if time_stamp:
			self.log['tps'][int(time_stamp)] += 1

	def get_tips(self, mode='uniform'):
		if self.n_tips == 1:
			return [self.tips[0], self.tips[0]]
		elif self.n_tips > 1:
			if mode == 'uniform':
				return [choice(self.tips) for _ in range(2)]
			if mode == 'priority_soft':
				proportion = 0.1
				ratio = 1.0 / proportion 
				last_n = floor(self.n_tips/ratio)
				return [choice(self.tips[-last_n:]) for _ in range(2)]
			if mode == 'priority_hard':
				last_n = min(100, self.n_tips)
				return [choice(self.tips[-last_n:]) for _ in range(2)]				
			if mode == 'mcmc':
				raise NotImplementedError("MCMC Tip Selection is not yet implemented.")
		else:
			return None

	def step(self, now):
		self.tips = [x for x in self.txs if x not in self.confirmed.keys()]
		self.n_tips = len(self.tips)
		self.log['uctps'][now] += self.n_tips


def clock(env, global_tangle):
	while True:
		global_tangle.step(env.now)
		yield env.timeout(1)

def node(env, name, global_tangle):
	while True:
		if (random() < TPS_PER_NODE):	# Initate transaction
			tx_parents = global_tangle.get_tips()
			if not tx_parents:
				raise Exception("No tips left.")
			tx_time = ceil(gauss(MEAN_TX_TIME, VAR_TX_TIME))
			if (tx_time < 0):
				tx_time = 0
			
			yield env.timeout(tx_time)
			global_tangle.make_transaction(name, env.now,
				tx_parents)
		else:
			yield env.timeout(1)

tangle = Tangle()

env = simpy.Environment()
env.process(clock(env, tangle))
for i in range(NETWORK_NODES):
	env.process(node(env, i, tangle))
env.run(until=TIME_STEPS)

"""
_, tps = zip(*sorted(tangle.log['tps'].items()))
plt.plot(tps)  # arguments are passed to np.histogram
plt.title("New transactions per time step")
plt.show()
"""

#"""
_, uctps = zip(*sorted(tangle.log['uctps'].items()))
plt.plot(uctps)
plt.title("Tips per time step")
plt.show()
#"""

"""
nx.draw(tangle.dag)
plt.show()
"""
