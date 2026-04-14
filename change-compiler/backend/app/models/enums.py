from enum import Enum


class ChangeStatus(str, Enum):
    received = "received"
    evaluated = "evaluated"
    executing = "executing"
    paused = "paused"
    halted = "halted"
    completed = "completed"
    blocked = "blocked"


class DecisionType(str, Enum):
    allow = "allow"
    allow_with_constraints = "allow_with_constraints"
    block = "block"


class EnforcementType(str, Enum):
    hard_stop = "hard_stop"
    manual_approval = "manual_approval"
    advisory = "advisory"
