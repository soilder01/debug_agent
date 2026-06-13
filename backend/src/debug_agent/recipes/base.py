from typing import Protocol

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentStep


class DebugRecipe(Protocol):
    task_type: str

    def plan_steps(self, *, case: DebugCase, baseline_trials: int) -> list[ExperimentStep]:
        """Build experiment steps for one task type."""

    def build_step_prompt(self, *, case: DebugCase, step_name: str) -> str:
        """Build the prompt for one experiment step."""
