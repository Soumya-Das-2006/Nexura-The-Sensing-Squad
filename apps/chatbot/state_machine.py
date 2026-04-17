"""
apps/chatbot/state_machine.py

Finite State Machine (FSM) for conversation flow management.

States and valid transitions:

    IDLE ──greet──► GREETED ──intent──► COLLECTING ──slots_filled──► PROCESSING
                        │                                                    │
                        └──────────────────────────────────────────► RESOLVED
                                                                           │
                                                                    ──escalate──►ESCALATED

    Any state ──error──► IDLE (reset)
    Any state ──timeout──► IDLE (reset after 30 min)

The FSM is stored as JSON in ChatSession.context so it survives
process restarts and horizontal scaling.
"""

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class State(str, Enum):
    IDLE        = 'idle'
    GREETED     = 'greeted'
    COLLECTING  = 'collecting'
    PROCESSING  = 'processing'
    RESOLVED    = 'resolved'
    ESCALATED   = 'escalated'


class Event(str, Enum):
    GREET       = 'greet'
    INTENT_FOUND = 'intent_found'
    SLOTS_READY  = 'slots_ready'
    RESOLVED     = 'resolved'
    ESCALATE     = 'escalate'
    RESET        = 'reset'
    NEW_INTENT   = 'new_intent'


# Transition table: (current_state, event) → next_state
TRANSITIONS: dict[tuple, State] = {
    (State.IDLE,       Event.GREET):        State.GREETED,
    (State.IDLE,       Event.INTENT_FOUND): State.COLLECTING,
    (State.IDLE,       Event.RESOLVED):     State.RESOLVED,

    (State.GREETED,    Event.INTENT_FOUND): State.COLLECTING,
    (State.GREETED,    Event.RESOLVED):     State.RESOLVED,
    (State.GREETED,    Event.ESCALATE):     State.ESCALATED,

    (State.COLLECTING, Event.SLOTS_READY):  State.PROCESSING,
    (State.COLLECTING, Event.NEW_INTENT):   State.COLLECTING,  # user changed topic
    (State.COLLECTING, Event.ESCALATE):     State.ESCALATED,

    (State.PROCESSING, Event.RESOLVED):     State.RESOLVED,
    (State.PROCESSING, Event.ESCALATE):     State.ESCALATED,
    (State.PROCESSING, Event.NEW_INTENT):   State.COLLECTING,

    (State.RESOLVED,   Event.GREET):        State.GREETED,
    (State.RESOLVED,   Event.INTENT_FOUND): State.COLLECTING,
    (State.RESOLVED,   Event.NEW_INTENT):   State.COLLECTING,

    # Reset from any state
    (State.IDLE,       Event.RESET):        State.IDLE,
    (State.GREETED,    Event.RESET):        State.IDLE,
    (State.COLLECTING, Event.RESET):        State.IDLE,
    (State.PROCESSING, Event.RESET):        State.IDLE,
    (State.RESOLVED,   Event.RESET):        State.IDLE,
    (State.ESCALATED,  Event.RESET):        State.IDLE,
}

# Intents that require no slot collection → jump straight to PROCESSING
INSTANT_RESOLVE_INTENTS = {
    'check_balance', 'get_statement', 'check_policy',
    'check_payout', 'check_claim_status', 'payment_history',
    'loan_status', 'get_help', 'greet', 'farewell', 'thanks',
}

# Intents that need additional info from the user
SLOT_REQUIRED_INTENTS = {
    'file_claim':    ['incident_description', 'incident_date'],
    'make_payment':  ['amount'],
    'loan_enquiry':  ['loan_amount', 'loan_purpose'],
    'renew_policy':  ['policy_number'],
    'report_problem': ['problem_description'],
}


class ConversationFSM:
    """
    Manages conversation state for a single ChatSession.
    State is persisted in session.context['fsm'].
    """

    def __init__(self, session):
        """
        Parameters
        ----------
        session : ChatSession model instance
        """
        self.session = session
        self._state  = State(session.state) if session.state in State._value2member_map_ else State.IDLE

    @property
    def state(self) -> State:
        return self._state

    def transition(self, event: Event) -> State:
        """
        Apply event and move to next state.
        Returns the new state. If no transition defined, stays in current state.
        """
        key = (self._state, event)
        next_state = TRANSITIONS.get(key)

        if next_state is None:
            logger.debug("FSM: No transition for (%s, %s) — staying in %s", self._state, event, self._state)
            return self._state

        logger.info("FSM: %s --%s--> %s", self._state, event, next_state)
        self._state = next_state
        self._save()
        return self._state

    def process_intent(self, intent_name: str) -> tuple[State, list[str]]:
        """
        Given a detected intent, determine next state and required slots.

        Returns
        -------
        (new_state, required_slots)
            required_slots is [] if none needed.
        """
        required_slots = SLOT_REQUIRED_INTENTS.get(intent_name, [])
        # Check which slots are already collected
        collected = self.session.context.get('slots', {})
        missing   = [s for s in required_slots if s not in collected]

        if intent_name == 'greet':
            self.transition(Event.GREET)
        elif intent_name == 'escalate_agent':
            self.transition(Event.ESCALATE)
        elif missing:
            self.transition(Event.INTENT_FOUND)
        else:
            # All slots ready or intent needs none
            if self._state in (State.IDLE, State.GREETED):
                self.transition(Event.INTENT_FOUND)
            self.transition(Event.SLOTS_READY)

        return self._state, missing

    def record_slot(self, slot_name: str, value: str) -> list[str]:
        """Store a collected slot value. Returns remaining missing slots."""
        context = self.session.context or {}
        slots   = context.get('slots', {})
        slots[slot_name] = value
        context['slots'] = slots
        self.session.context = context

        intent   = context.get('current_intent', '')
        required = SLOT_REQUIRED_INTENTS.get(intent, [])
        missing  = [s for s in required if s not in slots]

        if not missing:
            self.transition(Event.SLOTS_READY)

        self._save()
        return missing

    def resolve(self):
        """Mark current intent as resolved."""
        self.transition(Event.RESOLVED)

    def reset(self):
        """Reset FSM to IDLE (clear slots, intent)."""
        self.transition(Event.RESET)
        ctx = self.session.context or {}
        ctx.pop('slots', None)
        ctx.pop('current_intent', None)
        self.session.context = ctx
        self._save()

    def set_current_intent(self, intent_name: str):
        ctx = self.session.context or {}
        ctx['current_intent'] = intent_name
        self.session.context = ctx
        self._save()

    def get_current_intent(self) -> Optional[str]:
        return (self.session.context or {}).get('current_intent')

    def _save(self):
        """Persist state to DB."""
        self.session.state = self._state.value
        self.session.save(update_fields=['state', 'context', 'updated_at'])
