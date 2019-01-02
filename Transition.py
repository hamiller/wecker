class Transition:
	from_State = {}
	action = {}
	to_State = {}
	callback = {}

	def __init__(self, from_State, action, to_State, callback = None):
		self.from_State = from_State
		self.action = action
		self.to_State = to_State
		self.callback = callback
