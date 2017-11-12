from math import floor
from random import choice
from collections import Counter

import numpy as np
import networkx as nx

import hashlib

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
