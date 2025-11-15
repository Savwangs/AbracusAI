from datetime import datetime
import pandas as pd
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Literal

class Action(BaseModel):
    action: Literal["follow_up", "add_web_listener", "no_action"]
    call_id: str
    followup_context: Optional[str] = None

class OpportunityClassification(str, Enum):
    NO_BUDGET = "no_budget"
    NO_BUDGET_WITH_DATE = "no_budget_with_date"
    NEEDS_APPROVAL = "needs_approval"
    NEEDS_APPROVAL_WITH_NAMED_PERSON = "needs_approval_with_named_person"
    NEEDS_SPECIFIC_FEATURE = "needs_specific_feature"
    NEEDS_SPECIFIC_COMPLIANCE = "needs_specific_compliance"
    SATISFIED_WITH_CURRENT_SOLUTION = "satisfied_with_current_solution"
    NOT_A_PRIORITY_FOR_LEADERSHIP = "not_a_priority_for_leadership"
    OTHER = "other"

class Agent:

    def __init__(self, dataset: pd.DataFrame):
        self.dataset = dataset

    def detect_signals(self, start_date: datetime, end_date: datetime) -> list[str]:
        """
        Detect signals from the script.
        """
        return []

    def surface_opportunities(self, day: datetime) -> list[str]:
        """
        Surface opportunities for the day.
        """
        return []

    # Search helpers
    def __cluster_calls(self, end_date: datetime) -> Dict[OpportunityClassification, List[str]]:
        """
        Cluster phone calls by specific opportunity. 
        Args:
            end_date (datetime): The end date to cluster calls by.

        Returns:
            Dict[OpportunityClassification, List[str]]: A dictionary of opportunity classifications and the calls that belong to them.
        """
        return {}

    def __handle_opportunity_type(self, call_transcript: Dict[str, str], call_date: datetime, opportunity_type: OpportunityClassification) -> Action:
        """
        Handle the opportunity type.

        Args:
            call_transcript (Dict[str, str]): A dictionary of the call transcript.
            call_date (datetime): The call date.
            opportunity_type (OpportunityClassification): The opportunity type.

        Returns:
            str: A string dictating the action to take.
        """
        return Action(action="no_action", call_id="")
