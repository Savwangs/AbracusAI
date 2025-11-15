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

class Action(BaseModel):
    opportunity_type: OpportunityClassification
    action: Literal["follow_up", "add_event_listener", "no_action"]
    call_id: str
    followup_context: Optional[str] = None

class Agent:

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        signals = self.detect_signals(today, recent_closed_calls)

        # 6. Return a) current opportunities and action items to take, and b) a list of proposed new signals to add to the dataset.
        return opportunities, signals

    def detect_signals(self, today: datetime, recent_closed_calls: pd.DataFrame) -> list[str]:
        """
        Detect signals from the script.
        
        1. Extract user purchase reasoning
        2. Extract ICP details
        
        """
        return []

    def surface_opportunities(self, open_calls: pd.DataFrame) -> list[Action]:
        """
        Surface opportunities for the open calls.
        Returns a list of Action objects containing both 
        the opportunity classification and recommended actions for each call.
        """
        opportunities = []
        
        for call_id in open_calls["id"]:
            # Call the combined classification and action planning function
            action = self.__handle_opportunity_type(open_calls, call_id)
            opportunities.append(action)
        
        return opportunities

    # helpers
    def __segment_calls(self, df: pd.DataFrame, today: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Segment calls into open/active and closed.
        """
        # Define what statuses are open/active and closed
        OPEN_STATUSES = {"initial_contact", "discovery", "follow_up", "negotiation", "objection_handling", "demo_scheduled"}
        CLOSED_STATUSES = {"closed_won", "closed_lost"}

        # Ensure date column is parsed as datetime
        df["call_date"] = pd.to_datetime(df["call_date"])
        
        # Filter open/active calls as of today
        open_calls = df[df["call_stage"].isin(OPEN_STATUSES)]

        # Filter closed calls from the previous 2 weeks
        two_weeks_ago = today - SIGNAL_DETECTION_WINDOW
        recent_closed_calls = df[
            (df["call_stage"].isin(CLOSED_STATUSES)) &
            (df["call_date"] >= two_weeks_ago) &
            (df["call_date"] <= today)
        ]

        return open_calls, recent_closed_calls

    def __handle_opportunity_type(self, df: pd.DataFrame, call_id: str) -> Action:
        """
        Classify the opportunity and generate personalized action plans using LLM.

        Args:
            df (pd.DataFrame): The dataframe containing all calls.
            call_id (str): The ID of the specific call to handle.

        Returns:
            Action: An Action object containing the opportunity type classification and action to take.
        """
        # Query the dataframe to get the specific call row
        call_row = df[df['id'] == call_id]
        
        if call_row.empty:
            return Action(
                opportunity_type=OpportunityClassification.OTHER,
                action="follow_up",
                call_id=call_id,
                followup_context="ERROR: Call ID not found in database. Please verify the call exists."
            )
        
        # Extract call data from the row
        call_row = call_row.iloc[0]
        transcript_text = call_row.get('transcript', '')
        call_date = pd.to_datetime(call_row.get('call_date', datetime.now()))
        
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
        
        # Create comprehensive system prompt with today's date for context
        today = datetime.now()
        system_prompt = f"""You are an AI sales assistant helping enterprise salespeople take the right actions based on sales call opportunities.

TODAY'S DATE: {today.strftime('%Y-%m-%d')} ({today.strftime('%B %d, %Y')})

Your role is to:
1. CLASSIFY the sales call into an opportunity type based on the transcript
2. GENERATE detailed, actionable follow-up plans for salespeople

OPPORTUNITY TYPES AND THEIR MEANINGS (classify based on prospect's key objection/situation):
- NO_BUDGET: Prospect has no budget allocated for the solution (and didn't mention when budget might be available)
- NO_BUDGET_WITH_DATE: Prospect mentioned a specific date/timeframe when budget will be available (e.g., "Q4", "next fiscal year", "annual planning")
- NEEDS_APPROVAL: Prospect needs approval from others but hasn't specified who
- NEEDS_APPROVAL_WITH_NAMED_PERSON: Prospect mentioned specific stakeholders who need to approve (e.g., "CFO", "VP of Operations", "our director")
- NEEDS_SPECIFIC_FEATURE: Prospect requires specific features or integrations they're not sure you have (e.g., "Salesforce integration", "API access")
- NEEDS_SPECIFIC_COMPLIANCE: Prospect requires compliance certifications (e.g., "GDPR", "SOC2", "HIPAA", "ISO")
- SATISFIED_WITH_CURRENT_SOLUTION: Prospect is happy with their current vendor/solution and sees no reason to switch
- NOT_A_PRIORITY_FOR_LEADERSHIP: This initiative is not a current priority for the company (timing issue)
- OTHER: Any other situation that doesn't clearly fit the above

YOUR TASK:
1. FIRST: Read the entire transcript and classify it into the most appropriate opportunity type based on the prospect's main objection or situation
2. THEN: Extract specific details mentioned by the prospect (dates, names, requirements, competitors)
3. FINALLY: Generate a detailed 3-4 step action plan tailored to that opportunity type
4. Choose the appropriate action type:
   - "follow_up": For situations requiring nurturing, scheduling calls, or relationship building
   - "add_event_listener": For situations where monitoring for product/compliance updates would be valuable (typically NEEDS_SPECIFIC_FEATURE or NEEDS_SPECIFIC_COMPLIANCE)
   - "no_action": Only if the call is clearly lost with no recovery path
5. Make the action plan SPECIFIC and PERSONALIZED based on what was said in the transcript

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

CALL TRANSCRIPT:
{formatted_transcript}

Analyze the transcript above and:
1. Classify this call into the most appropriate opportunity type based on the prospect's main objection or situation
2. Extract any specific details mentioned (dates, stakeholder names, features, compliance requirements, competitors)
3. Generate a detailed action plan for the salesperson that incorporates these extracted details"""

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
                opportunity_type=OpportunityClassification.OTHER,
                action="follow_up",
                call_id=call_id,
                followup_context=f"ERROR: Could not generate action plan due to API error: {str(e)}. Please review the call manually and create a follow-up plan."
            )
