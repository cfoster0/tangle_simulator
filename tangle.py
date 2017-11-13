from math import floor, exp
from random import choice, randint
from collections import Counter
from functools import lru_cache

import numpy as np
import networkx as nx

import hashlib

class Tangle():

	def __init__(self, verbose=False):
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
		if (self.verbose):
			self.log['verbose'].append("@{tim}, transaction: {t}\n\t{p}\n".format(tim=time_stamp, t=tx, p=parents))
		self.txs.append(tx)
		self.dag.add_node(tx)
		for parent in parents:
			self.dag.add_edge(parent, tx)
			if not self.confirmed[parent]:
				self.log['ctps'][time_stamp] += 1
			self.confirmed[parent] += 1

		if time_stamp:
			self.log['tps'][int(time_stamp)] += 1
			nx.set_node_attributes(self.dag, 'time_stamp', {tx: time_stamp})

	@lru_cache(maxsize=4096)
	def walk_back(self, start, depth):
		if depth > 0:
			parents = list(self.dag.predecessors(start))
			if parents:
				return self.walk_back(choice(parents), depth - 1)
		return start

	@lru_cache(maxsize=1024)
	def walk_forward(self, start, depth, alpha):
		if depth > 0:
			children = list(self.dag.successors(start))
			if children:
				transition_probabilities = [exp(-alpha * ((self.confirmed[start]+1) - (self.confirmed[child]+1))) for child in children]
				total_probability = sum(transition_probabilities)
				transition_probabilities = [tp / total_probability for tp in transition_probabilities]
				return self.walk_forward(np.random.choice(a=children, p=transition_probabilities), depth - 1, alpha)
		return start

	def mcmc_select(self, n=2, n_sites=10, w=100, alpha=0.005):
		if n_sites < n:
			raise Exception("Not enough sites specified for MCMC")
		walkers = [self.walk_back(start=self.txs[-1], depth=randint(w, w*2)) for _ in range(n_sites)]

		selected_tips = []
		while len(selected_tips) < n:
			walkers = [self.walk_forward(start=walker, depth=1, alpha=alpha) for walker in walkers]
			for walker in walkers:
				if walker is None:
					walkers.remove(None)
					continue
				if walker not in self.confirmed:
					selected_tips.append(walker)
		return selected_tips

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
				return self.mcmc_select(n=2, n_sites=10, w=10)
		return None

	def step(self, now):
		self.tips = [x for x in self.txs if x not in self.confirmed.keys()]
		self.n_tips = len(self.tips)
		self.log['uctps'][now] += self.n_tips

	def last_common_tx(self, t1, t2):
		preds_1 = nx.bfs_predecessors(self.dag, t1)
		#_, p = zip(*preds_1)
		if t2 in preds_1:
			return t2
		preds_2 = nx.bfs_predecessors(self.dag, t2)
		if t1 in preds_2:
			return t1
		common_preds = set([n for n in preds_1]).intersection(set([n for n in preds_2]))

	def prune(self, mode='snapshot', txs=[], interval=[]):
		if mode == 'snapshot':
			if len(txs) > 1:
				self.prune(txs=txs.remove(self.last_common_tx(txs[0], txs[1])))
			elif len(txs) == 1:
				self.dag = self.snapshot(txs[0])
			else:
				raise IndexError("Cannot snapshot without reference transactions")
		if mode == 'interval':
			raise NotImplementedError()

		

