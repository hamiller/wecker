import logging
from Transition import Transition
from State import State
from ActionButton import ActionButton
from Request import Request

class StateMachine:

	transitions = []
	request = {}

	def __init__(self, config, request):
		logging.info("Initialisiere Statemachine")
		self.transitions = config
		self.request = request

	def apply(self, action):
		for (transition) in self.transitions:
			currentStateMatches = transition.from_State is self.request.state
			conditionsMatch = transition.action is action
			if currentStateMatches and conditionsMatch:
				self.request.state = transition.to_State
				logging.info("Setze neuen state " + str(self.request.state))
                                if (transition.callback != None):
                                        logging.info("Callback")
					transition.callback()
				return self

		return self
