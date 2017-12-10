from collections import Counter

import itertools

"""
discount: 1.0
values: [ reward, cost ]
states: list of strings
actions: adopt build
observations: list of strings

start: <name of starting state>

T: adopt : * : <name of starting state> 1.0
// for all the start-end combinations we see in the data:
	T: build : <start-state> : <end-state> : probability


// for all the state-observation combinations we see in the data:
O: * : <end-state> : <observation> %f

R: <action> : <start-state> : <end-state> : <observation> %f

R: build : * : * : * -epsilon
// for all the winning states
	R: * : * : <win-state> : * 1.0
"""

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

def data_to_pomdp(data, fname='tangle.POMDP'):
	with open(fname,'w') as pomdp_file:
		S = get_S(data)
		A = ['back', 'wait', 'build']
		T = get_T(S, A[1:], data)
		O = get_O(S, A, data)

		O_states = S

		win_states = get_R(S, A, data)

		discount = 0.9
		epsilon = -0.0001
		start = 'a-a'

		pomdp_file.write("# Tangle File \n")
		pomdp_file.write("discount: {f} \n".format(f=discount))
		pomdp_file.write("values: reward \n")
		pomdp_file.write("states: {s} \n".format(s=' '.join(S)))
		pomdp_file.write("actions: {a} \n".format(a=' '.join(A)))
		pomdp_file.write("observations: {o} \n".format(o=' '.join(O_states)))
		pomdp_file.write("\n")
		pomdp_file.write("start: {st} \n".format(st=start))
		pomdp_file.write("\n")
		pomdp_file.write("T: back : * : {st} 1.0 \n".format(st=start))
		for win_state in win_states:
			pomdp_file.write("T: * : {ws} : {st} 1.0 \n".format(ws=win_state, st=start))
		for (action, start_state, end_state, probability) in T:
			pomdp_file.write("T: {a} : {ss} : {es} {p} \n".format(a=action, ss=start_state, es=end_state, p=probability))

		for (end_state, observation, probability) in O:
			pomdp_file.write("O: * : {es} : {o} {p} \n".format(es=end_state, o=observation, p=probability))

		pomdp_file.write("R: build : * : * : * {eps} \n".format(eps=epsilon))
		for win_state in win_states:
			pomdp_file.write("R: * : * : {ws} : * 1.0 \n".format(ws=win_state))

	return pomdp_file

def get_S(data):
	#S = ['(1,0)', '(1,1)', '(1,2)']
	S = []
	for i in range(11):
		for j in range(11):
			S.append("{}-{}".format(alphabet[i], alphabet[j]))
	return S

def get_T(S, A, data):
	#T = [('wait', '(1,0)', '(1,0)', 0.50), ('wait', '(1,0)', '(1,1)', 0.50), ('build', '(1,0)', '(1,1)', 0.50), ('build', '(1,0)', '(1,2)', 0.50), ('build', '(1,1)', '(1,2)', 1.0)]
	T = []

	for action in A:
		transition_counters = {}
		for state in S:
			transition_counters[state] = Counter()

		for (start_state, end_state) in itertools.product(S, S):
			transition_counters[start_state][end_state] += 1

		for i, step in enumerate(data['global']):
			start_state = step[0]
			if step[1] is not action:
				continue

			if i == len(data['global']) - 1:
				break
			end_state = data['global'][i+1][0]
			transition_counters[start_state][end_state] += 1

		probabilities = []

		for start_state in transition_counters:
			total = 0.0
			for end_state in transition_counters[start_state]:
				total += transition_counters[start_state][end_state]
			for end_state in transition_counters[start_state]:
				T_tuple = (action, start_state, end_state, transition_counters[start_state][end_state] / total)
				probabilities.append(T_tuple)

		for p in probabilities:
			T.append(p)

	return T

def get_O(S, A, data):
	#O = [('(1,0)', '(100, 0)', 1.0), ('(1,1)', '(50, 50)', 1.0), ('(1,2)', '(33,67)', 1.0)]
	O = []

	transition_counters = {}
	for state in S:
		transition_counters[state] = Counter()

	for (event, observation) in itertools.product(S, S):
		transition_counters[event][observation] += 1

	for step, observation in zip(data['global'], data['local']):
		event = step[0]
		transition_counters[event][observation] += 1

	for state in transition_counters:
		total = 0.0
		for observation in transition_counters[state]:
			total += transition_counters[state][observation]
		for observation in transition_counters[state]:
			O_tuple = (state, observation, transition_counters[state][observation] / total)
			O.append(O_tuple)
		
	return O

def get_R(S, A, data):
	#R = ['(1,2)']
	R = []
	#for i in range(51, 100):
	#	for j in range(i+1, 100):
	#		R.append("({orig},{doub})".format(orig=i, doub=j))
	for i in range(11):
		for j in range(i+1, 11):
			R.append("{orig}-{doub}".format(orig=alphabet[i], doub=alphabet[j]))
	return R