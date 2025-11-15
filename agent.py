from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Literal
import json
import os
from openai import OpenAI

SIGNAL_DETECTION_WINDOW = timedelta(weeks=2)
DATASET = "enterprise_sales_calls_1000_humanized.csv"

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

    def main(self):
        """
        Main function.
        """
        # 1. load data
        df = pd.read_csv(DATASET)

        # 2. get today's date
        today = datetime.now()

        # 3. get a set of open/active calls, and closed calls from the previous 2 weeks.
        open_calls, recent_closed_calls = self.__segment_calls(df, today)

        # 4. Identify opportunities / actions to take for all open calls.
        opportunities = self.surface_opportunities(open_calls)

        # 5. Get all closed calls from the previous 2 weeks, run signal detection on them.
        signals = self.detect_signals(recent_closed_calls)

        # 6. Return a) current opportunities and action items to take, and b) a list of proposed new signals to add to the dataset.
        return opportunities, signals

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

    # helpers
    def __segment_calls(self, df: pd.DataFrame, today: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Segment calls into open/active and closed.
        """
        # Define what statuses are open/active and closed
        OPEN_STATUSES = {"initial_contact", "discovery", "follow_up", "negotiation", "objection_handling", "demo_scheduled"}
        CLOSED_STATUSES = {"closed_won", "closed_lost"}

        # Ensure date column is parsed as datetime
        df["date"] = pd.to_datetime(df["date"])
        
        # Filter open/active calls as of today
        open_calls = df[df["status"].isin(OPEN_STATUSES)]

        # Filter closed calls from the previous 2 weeks
        two_weeks_ago = today - SIGNAL_DETECTION_WINDOW
        recent_closed_calls = df[
            (df["status"].isin(CLOSED_STATUSES)) &
            (df["date"] >= two_weeks_ago) &
            (df["date"] <= today)
        ]

        return open_calls, recent_closed_calls
    
    def __classify_call(self, call_id: str, call_df: pd.DataFrame) -> OpportunityClassification:
        """
        Classify a call by specific opportunity. 
        Args:
            call_id (str): The call id.
            call_df (pd.DataFrame): The call dataframe.

        Returns:
            OpportunityClassification: The opportunity classification.
        """
        return OpportunityClassification.NO_BUDGET

    def __handle_opportunity_type(self, df: pd.DataFrame, call_id: str, opportunity_type: OpportunityClassification) -> Action:
        """
        Handle the opportunity type using LLM to generate personalized action plans.

        Args:
            call_transcript (Dict[str, str]): A dictionary of the call transcript.
            call_date (datetime): The call date.
            opportunity_type (OpportunityClassification): The opportunity type.

        Returns:
            Action: An Action object dictating the action to take.
        """
        # Extract call_id from call_transcript
        call_id = call_transcript.get("id", "")
        
        # Parse the transcript text
        transcript_text = call_transcript.get("transcript", "")
        
        # Format the transcript for the LLM
        try:
            if isinstance(transcript_text, str):
                transcript_messages = json.loads(transcript_text)
                formatted_transcript = "\n".join([
                    f"{msg.get('speaker', 'unknown').upper()}: {msg.get('text', '')}"
                    for msg in transcript_messages
                ])
            else:
                formatted_transcript = str(transcript_text)
        except json.JSONDecodeError:
            formatted_transcript = str(transcript_text)
        
        # Create comprehensive system prompt
        system_prompt = """You are an AI sales assistant helping enterprise salespeople take the right actions based on sales call opportunities.

Your role is to analyze sales call transcripts and generate detailed, actionable follow-up plans for salespeople.

OPPORTUNITY TYPES AND THEIR MEANINGS:
- NO_BUDGET: Prospect has no budget allocated for the solution
- NO_BUDGET_WITH_DATE: Prospect mentioned a specific date/timeframe when budget will be available (e.g., Q4, next fiscal year)
- NEEDS_APPROVAL: Prospect needs approval from others but hasn't specified who
- NEEDS_APPROVAL_WITH_NAMED_PERSON: Prospect mentioned specific stakeholders who need to approve (e.g., CFO, VP Operations)
- NEEDS_SPECIFIC_FEATURE: Prospect requires specific features or integrations (e.g., Salesforce integration, specific capabilities)
- NEEDS_SPECIFIC_COMPLIANCE: Prospect requires compliance certifications (e.g., GDPR, SOC2, HIPAA)
- SATISFIED_WITH_CURRENT_SOLUTION: Prospect is happy with their current vendor/solution
- NOT_A_PRIORITY_FOR_LEADERSHIP: This initiative is not a current priority for the company
- OTHER: Any other situation

YOUR TASK:
1. Analyze the call transcript to extract specific details mentioned by the prospect
2. Based on the opportunity type and extracted details, generate a detailed 3-4 step action plan
3. Choose the appropriate action type:
   - "follow_up": For situations requiring nurturing, scheduling calls, or relationship building
   - "add_web_listener": For situations where monitoring for product/compliance updates would be valuable (typically NEEDS_SPECIFIC_FEATURE or NEEDS_SPECIFIC_COMPLIANCE)
4. Make the action plan SPECIFIC and PERSONALIZED based on what was said in the transcript

GUIDELINES FOR ACTION PLANS:
- Extract and reference specific details: dates (Q4, next year), stakeholder names/titles (CFO, VP), feature requirements (Salesforce), compliance needs (GDPR), competitor names
- Provide 3-4 concrete, actionable steps
- Include timing recommendations when relevant
- Make it detailed enough that a salesperson can immediately act on it
- Format as a clear header followed by numbered steps

EXAMPLE OUTPUT FORMATS:

For NO_BUDGET_WITH_DATE (if prospect mentioned "Q4"):
"BUDGET TIMING IDENTIFIED (Q4) - Strategic nurture plan:
1. Send comprehensive ROI documentation and case study NOW for their Q4 planning discussions
2. Add to calendar for follow-up in early September (2-3 weeks before Q4) to ensure inclusion in budget
3. Share industry benchmarks showing typical 3-month payback period to strengthen internal business case
4. Offer to join their Q4 planning meeting to present solution and answer stakeholder questions"

For NEEDS_APPROVAL_WITH_NAMED_PERSON (if prospect mentioned "CFO and VP of Operations"):
"KEY STAKEHOLDERS IDENTIFIED (CFO, VP of Operations) - Direct engagement plan:
1. Ask your champion to introduce you directly to CFO and VP of Operations via warm email introduction
2. Research both stakeholders on LinkedIn and prepare customized messaging (CFO: cost savings, VP Ops: efficiency)
3. Prepare individual one-pagers for each: CFO gets ROI analysis, VP Ops gets implementation timeline
4. Schedule brief 15-min introductory calls with each stakeholder separately before group demo"

Be specific, actionable, and reference details from the transcript."""

        # Create user prompt with call details
        user_prompt = f"""CALL DATE: {call_date.strftime('%Y-%m-%d')}

OPPORTUNITY TYPE: {opportunity_type.value}

CALL TRANSCRIPT:
{formatted_transcript}

Based on the opportunity type and the conversation above, generate a detailed action plan for the salesperson. Extract any specific details mentioned (dates, names, features, etc.) and incorporate them into your action plan."""

        try:
            # Call OpenAI API with structured output
            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=Action,
            )
            
            # Extract the parsed action from the response
            action_response = response.choices[0].message.parsed
            
            # Update the call_id to match the current call
            action_response.call_id = call_id
            
            return action_response
            
        except Exception as e:
            # Fallback in case of API error
            return Action(
                action="follow_up",
                call_id=call_id,
                followup_context=f"ERROR: Could not generate action plan due to API error: {str(e)}. Please review the call manually and create a follow-up plan."
            )
