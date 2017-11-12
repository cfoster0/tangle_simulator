from math import ceil
from random import random, gauss
import matplotlib.pyplot as plt
import simpy
from tangle import Tangle

NETWORK_NODES = 1000
MEAN_TX_TIME = 10
VAR_TX_TIME = 2
TPS_PER_NODE = 0.01	# Probabity that a node will initiate a transaction in a given time step

TIME_STEPS = 3000

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