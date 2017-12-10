from math import floor, exp
from random import choice, randint, random, sample
from collections import Counter, deque

from functools import lru_cache

import numpy as np
import networkx as nx

import hashlib

class Tangle():

	def __init__(self, verbose=False):
		self.dag = nx.DiGraph()
		self.tips = []
		#self.tips = deque(maxlen=100)
		self.n_tips = 0
		self.cumulative_weight = Counter()
		self.verbose = verbose
		#self.log = {"tps": Counter(), "uctps": Counter(), "ctps": Counter(), 'verbose': []}
		self.genesis = self.make_transaction(None, None, [])
		self.blacklist = []

	def make_transaction(self, node_name, time_stamp, parents):
		base_tx = (node_name, time_stamp, parents)
		tx = hashlib.sha3_224(str(base_tx).encode()).hexdigest()

		#if (self.verbose):
		#	self.log['verbose'].append("@{tim}, transaction: {t}\n\t{p}\n".format(tim=time_stamp, t=tx, p=parents))
		#	print('Generated a transaction {t} with parents {p}!'.format(t=tx, p=parents))

		if time_stamp:
			#self.log['tps'][int(time_stamp)] += 1
			nx.set_node_attributes(self.dag, name='time_stamp', values={tx: time_stamp})
		return tx

	
	@lru_cache(maxsize=None)
	def walk_back(self, start, depth):
		if start not in self.dag:
			raise ValueError("Cannot walk transactions not in tangle.")
		if depth > 0:
			parents = self.get_parents(start)
			if parents:
				if len(parents) > 1:
					parent = parents[0]
				else:
					parent = choice(parents)
					self.cumulative_weight[parent] += 1
					#print("Updated weight of {t}.".format(t=parent))
				return self.walk_back(parent, depth - 1)
		return start
	

	def walk_forward(self, start, alpha):
		if start not in self.dag:
			return None
		children = list(self.dag.successors(start))
		if children:
			transition_probabilities = [exp(-alpha * ((self.cumulative_weight[start]+1) - (self.cumulative_weight[child]+1))) for child in children]
			#transition_probabilities = [exp(-alpha * ((self.confirmed[start]+1) - (self.confirmed[child]+1))) for child in children]
			total_probability = sum(transition_probabilities)
			transition_probabilities = [tp / total_probability for tp in transition_probabilities]
			if len(children) > 2: 
				return np.random.choice(a=children, p=transition_probabilities)
			elif len(children) == 2:
				if random() < transition_probabilities[0]:
					return children[0]
				else:
					return children[1]
			else:
				return children[0]
		else:
			return start

	def get_sites(self, n_sites, w):
		walkers = []
		if len(self.tips) >= w:
			walkers = sample(self.tips, n_sites)
			return [self.walk_back(walker, w) for walker in walkers]
		else:
			while len(walkers) < n_sites:
				walkers.extend(self.tips)
			return walkers[:n_sites]
		"""if len(self.cumulative_weight) > n_sites:
			print(self.cumulative_weight.most_common(n_sites))
		else:
			print('not ready, but length is {x}'.format(x=len(self.cumulative_weight)))
		print(' ')"""

		"""
		walkers = []
		txs = self.cumulative_weight.keys()
		for tx in txs:
			if self.cumulative_weight[tx] >= w and self.cumulative_weight[tx] <= w*2:
				walkers.append(tx)
			if len(walkers) == n_sites:
				break

		if len(walkers) < n_sites:
			if len(txs) >= n_sites - len(walkers):
				walkers.extend([a for (a, b) in self.cumulative_weight.most_common(n_sites-len(walkers))])
			else:
				while len(walkers) < n_sites:
					walkers.extend(txs)

		return walkers[:n_sites]
		"""

	def mcmc_select(self, n=2, n_sites=10, w=14, alpha=0.001):
		if n_sites < n:
			raise Exception("Not enough sites specified for MCMC")

		walkers = self.get_sites(n_sites, w)

		selected_tips = []
		while True:
			previous_sites = walkers[:]
			for i, old_site in enumerate(previous_sites):
				new_site = self.walk_forward(start=old_site, alpha=alpha)

				if new_site is None:
					selected_tips.append(old_site)
					walkers.remove(old_site)
				elif new_site == old_site:
					selected_tips.append(new_site)
					walkers.remove(old_site)
				else:
					walkers.remove(old_site)
					walkers.append(new_site)

				if len(selected_tips) == n:
					return selected_tips

	def step(self, now):
		self.n_tips = len(self.tips)
		#self.log['uctps'][now] = self.n_tips

	@lru_cache(maxsize=None)
	def get_parents(self, tx):
		if tx in self.dag:
			return list(self.dag.predecessors(tx))
		else:
			return []

	@lru_cache(maxsize=2048)
	def get_children(self, tx):
		if tx in self.dag:
			return list(self.dag.successors(tx))
		else:
			return []

	def remove(self, tx):
		self.blacklist.append(tx)
		#print('Removed {t}.'.format(t=tx))
		if tx in self.tips:
			self.tips.remove(tx)
		for child in self.get_children(tx):
			self.dag.remove_edge(tx, child)
			self.remove(child)
		self.dag.remove_node(tx)

	"""
	#@lru_cache(maxsize=2048)
	def weigh(self, tx):
		children = self.get_children(tx)
		if children:
			cumulative_weight = sum([self.weigh(child) for child in children]) + 1
		else:
			cumulative_weight = 1
		self.cumulative_weight[tx] = cumulative_weight
		return cumulative_weight
	"""

	"""
	def weigh(self, tx):
		self.cumulative_weight[tx] += 1
		parents = self.get_parents(tx)
		if parents:
			[self.weigh(parent) for parent in parents]
	"""

class Node():

	def __init__(self, name, gt, lt, tps, bw, inc, out, communications):
		self.name = name
		self.gt = gt
		self.lt = lt
		self.inc = inc
		self.out = out
		self.communications = communications
		self.broadcast_queue = deque(maxlen=100)
		self.tps = tps
		self.bw = bw
		self.time = 0
		self.check_conflicts = True
		self.integrate(self.lt.genesis)

	def get_tips(self, mode='mcmc'):
		if mode == 'uniform':
			return [choice(self.lt.tips) for _ in range(2)]
		if mode == 'priority_soft':
			proportion = 0.1
			ratio = 1.0 / proportion 
			last_n = floor(self.lt.n_tips/ratio)
			return [choice(self.lt.tips[-last_n:]) for _ in range(2)]
		if mode == 'priority_hard':
			last_n = min(100, self.lt.n_tips)
			return [choice(self.lt.tips[-last_n:]) for _ in range(2)]				
		if mode == 'mcmc':
			return self.lt.mcmc_select(n=2, n_sites=10, w=14)
		return None

	def make_conflict(self, tx):
		if tx[0] == '_':
			return tx[1:]
		else:
			return '_' + tx

	def has_conflict(self, tx):
		return self.make_conflict(tx) in self.lt.dag

	def resolve_conflict(self, tx1, tx2):
		weight_1 = 1
		weight_2 = 1

		for tip in self.lt.tips:
			if nx.has_path(self.lt.dag, tx1, tip):
				weight_1 += 1
			if nx.has_path(self.lt.dag, tx2, tip):
				weight_2 += 1

		if weight_2 > weight_1:
			return tx2
		else:
			return tx1

	def integrate(self, tx):
		if self.check_conflicts:
			if tx in self.lt.blacklist:
				#print("{t} has already been blacklisted by {n}.".format(t=tx, n=self.name))
				return

		self.lt.tips.append(tx)
		self.lt.dag.add_node(tx)
		parents = self.gt.get_parents(tx)
		for parent in parents:
			if parent not in self.lt.dag:
				self.integrate(parent)
			self.lt.dag.add_edge(parent, tx)
			#if self.lt.cumulative_weight[parent] == 1:
			if parent in self.lt.tips:
				self.lt.tips.remove(parent)
				#self.lt.log['ctps'][self.time] += 1
			#self.lt.cumulative_weight[parent] += self.lt.cumulative_weight[tx]
		#self.lt.weigh(tx)

		if self.check_conflicts:
			if self.has_conflict(tx):
				#print("{name} found a conflict.".format(name=self.name))
				conflict = self.make_conflict(tx)
				winner = self.resolve_conflict(conflict, tx)
				#print("Resolved a conflict in favor of {t}.".format(t=winner))
				if winner is tx:
					self.lt.remove(conflict)
				else:
					self.lt.remove(tx)
					return

	def listen(self):
		incast_queue = deque(maxlen=100)
		while len(incast_queue) <= self.bw:
			n_empty = 0
			for connection in self.inc:
				if self.communications[connection]:
					tx = self.communications[connection].pop()
					incast_queue.append(tx)
				else:
					n_empty += 1
			if n_empty == len(self.inc):
				break

		for connection in self.inc:
			self.communications[connection].clear()

		while incast_queue:
			tx = incast_queue.popleft()
			if tx not in self.lt.dag:
				if self.check_conflicts:
					if tx in self.lt.blacklist:
						continue
				self.broadcast_queue.append(tx)
				self.integrate(tx)

	def transact(self):
		for i in range(np.random.poisson(self.tps)):
			tx_parents = self.get_tips(mode='mcmc')
			if not tx_parents:
				break
			tx = self.lt.make_transaction(self.name, self.time,
				tx_parents)
			self.publish(tx, tx_parents)
			self.integrate(tx)
			self.broadcast_queue.append(tx)

	def gossip(self):
		for i in range(self.bw):
			if self.broadcast_queue:
				outgoing_tx = self.broadcast_queue.popleft()
				for connection in self.out:
					#print("{x} told {y} about {t}.".format(x=connection[0], y=connection[1], t=outgoing_tx))
					self.communications[connection].append(outgoing_tx)

	def publish(self, tx, parents):
		self.gt.dag.add_node(tx)
		self.gt.tips.append(tx)

		for parent in parents:
			self.gt.dag.add_edge(parent, tx)
			if parent in self.gt.tips:
				#print("{x} confirmed a tip.".format(x=self.name))
				self.gt.tips.remove(parent)
				#self.gt.log['ctps'][self.time] += 1
			#else:
			#	print("{x} confirmed a non-tip.".format(x=self.name))
		#print('')

	def step(self):
		self.listen()
		self.transact()
		self.gossip()
		self.lt.step(self.time)
		self.time += 1

class Adversary(Node):

	def __init__(self, name, gt, lt, tps, bw, inc, out, communications):
		Node.__init__(self, name, gt, lt, tps, bw, inc, out, communications)
		self.original = None
		self.double_spend = None
		self.check_conflicts = True

	def transact_single_spend(self):
		tx_parents = self.get_tips(mode='mcmc')
		tx = self.lt.make_transaction(self.name, self.time,
				tx_parents)
		self.original = tx
		print("Made original transaction {t}".format(t=tx))
		self.publish(tx, tx_parents)
		self.lt.blacklist.append(tx)
		#self.integrate(tx)
		self.broadcast_queue.append(tx)

	def get_double_spend_tips(self):
		tips = [tip for tip in self.lt.tips if not nx.has_path(self.gt.dag, self.original, tip)]
		if len(tips) > 1:
			return tips[:2]
		else:
			raise Exception('Could not find tips for double-spend.')

	"""
	def get_tips(self, mode='mcmc'):
		tips = []
		if self.double_spend:
			#
			candidates = [self.double_spend]
			depth = 0
			while True:
				#print("Number of {d}-child transactions of the double-spend: {n}".format(d=depth, n=len(candidates)))
				children = []
				[children.extend(self.lt.get_children(candidate)) for candidate in candidates]
				if not children:
					break
				candidates = children
				depth += 1
			while len(tips) < 2:
				tips.extend(candidates)
			#

			#
			#while len(tips) < 2:
			#	candidates = super().get_tips()
			#	tips.extend([tip for tip in candidates if not nx.has_path(self.lt, self.original, tip)])
			#
		else:
			tips = super().get_tips()

		return tips[:2]
	"""

	def transact_double_spend(self):
		if self.original is None:
			print('No original transaction to double-spend.')
			return
		tx_parents = self.get_double_spend_tips()
		tx = self.make_conflict(self.original)
		self.double_spend = tx
		print("Made double-spend transaction {t}".format(t=tx))
		
		#if (self.lt.verbose):
		#	self.lt.log['verbose'].append("@{tim}, transaction: {t}\n\t{p}\n".format(tim=time_stamp, t=tx, p=parents))
		#print('Generated a double spend {t} with parents {p}!'.format(t=tx, p=parents))

		#self.lt.log['tps'][self.time] += 1
		nx.set_node_attributes(self.lt.dag, name='time_stamp', values={tx: self.time})
		self.publish(tx, tx_parents)
		self.integrate(tx)
		self.check_conflicts = True
		self.broadcast_queue.append(tx)

	def double_spend_step(self):
		self.listen()
		self.transact_double_spend()
		self.tps *= 1
		self.gossip()
		self.lt.step(self.time)
		self.time += 1

