from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Literal
import json
import re

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
        Handle the opportunity type.

        Args:
            call_transcript (Dict[str, str]): A dictionary of the call transcript.
            call_date (datetime): The call date.
            opportunity_type (OpportunityClassification): The opportunity type.

        Returns:
            Action: An Action object dictating the action to take.
        """
        # Extract call_id from call_transcript
        call_id = call_transcript.get("id", "")
        
        # Parse the transcript text to extract insights
        transcript_text = call_transcript.get("transcript", "")
        transcript_messages = []
        
        try:
            if isinstance(transcript_text, str):
                transcript_messages = json.loads(transcript_text)
        except json.JSONDecodeError:
            transcript_messages = []
        
        # Combine all prospect responses for analysis
        prospect_text = " ".join([
            msg.get("text", "") 
            for msg in transcript_messages 
            if msg.get("speaker") == "prospect"
        ])
        
        # Handle each opportunity type with detailed action guidance
        if opportunity_type == OpportunityClassification.NO_BUDGET:
            # Extract any budget-related mentions
            followup_context = (
                "NO BUDGET IDENTIFIED - Multi-step engagement strategy:\n"
                "1. Send ROI case study and cost-benefit analysis showing typical payback period (Q1 achievement)\n"
                "2. Share customer testimonials from similar-sized companies demonstrating value\n"
                "3. Offer flexible payment terms or pilot program to reduce upfront investment concerns\n"
                "4. Schedule follow-up call in 30-45 days to revisit once they've reviewed materials"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NO_BUDGET_WITH_DATE:
            # Extract specific timing mentions (Q1-Q4, fiscal year, quarters, months)
            timing_patterns = [
                r"Q[1-4]",
                r"[Qq]uarter\s+\d",
                r"next\s+(?:fiscal\s+)?year",
                r"in\s+\d+\s+months?",
                r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
            ]
            
            timing_info = "at their budget cycle"
            for pattern in timing_patterns:
                match = re.search(pattern, prospect_text, re.IGNORECASE)
                if match:
                    timing_info = f"in {match.group()}"
                    break
            
            followup_context = (
                f"BUDGET TIMING IDENTIFIED - Strategic nurture plan for follow-up {timing_info}:\n"
                f"1. Send comprehensive ROI documentation and case study NOW for their planning discussions\n"
                f"2. Add to calendar for follow-up 2-3 weeks before {timing_info} to ensure you're included in budget allocation\n"
                f"3. Share industry benchmarks and competitive intel to strengthen their internal business case\n"
                f"4. Offer to join their planning meeting to present solution and answer stakeholder questions"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NEEDS_APPROVAL:
            followup_context = (
                "APPROVAL PROCESS IDENTIFIED - Multi-stakeholder strategy:\n"
                "1. Request to schedule a group call with all decision-makers to present solution efficiently\n"
                "2. Prepare executive summary deck tailored to each stakeholder's concerns (CFO: ROI, Ops: implementation)\n"
                "3. Send individual one-pagers addressing each stakeholder's specific priorities\n"
                "4. Offer references from similar companies where multiple departments approved the solution"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NEEDS_APPROVAL_WITH_NAMED_PERSON:
            # Extract stakeholder titles/names (CFO, VP, Director, etc.)
            stakeholder_patterns = [
                r"(?:our\s+)?(?:CFO|CEO|CTO|COO|VP|Vice President|Director|Manager)(?:\s+of\s+\w+)?",
            ]
            
            stakeholders = []
            for pattern in stakeholder_patterns:
                matches = re.findall(pattern, prospect_text, re.IGNORECASE)
                stakeholders.extend(matches)
            
            stakeholder_info = ""
            if stakeholders:
                unique_stakeholders = list(set(stakeholders))
                stakeholder_info = f" - Identified: {', '.join(unique_stakeholders)}"
            
            followup_context = (
                f"KEY STAKEHOLDERS IDENTIFIED{stakeholder_info} - Direct engagement plan:\n"
                f"1. Ask your champion to introduce you directly to {stakeholders[0] if stakeholders else 'the decision-makers'} via email\n"
                f"2. Research each stakeholder on LinkedIn and customize your messaging to their priorities\n"
                f"3. Prepare role-specific value propositions (Finance: cost savings, Operations: efficiency gains)\n"
                f"4. Schedule individual 15-min calls with each stakeholder before group demo to build relationships"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NEEDS_SPECIFIC_FEATURE:
            # Extract feature/integration mentions
            feature_patterns = [
                r"(?:integration with |integrate with |works with )(\w+(?:\s+\w+)?)",
                r"(\w+)\s+integration",
                r"need\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            ]
            
            features = []
            for pattern in feature_patterns:
                matches = re.findall(pattern, prospect_text, re.IGNORECASE)
                features.extend(matches)
            
            feature_info = ""
            if features:
                unique_features = list(set([f for f in features if len(f) > 2]))[:3]
                feature_info = f" - Required: {', '.join(unique_features)}"
            
            followup_context = (
                f"SPECIFIC FEATURE REQUIREMENT{feature_info} - Documentation and monitoring strategy:\n"
                f"1. Send detailed technical documentation showing feature capabilities and specs immediately\n"
                f"2. Provide implementation guide and setup timeline for the required features\n"
                f"3. SET WEB LISTENER: Monitor for product updates/announcements related to this feature\n"
                f"4. Offer to schedule technical deep-dive with solutions engineer to address all questions"
            )
            return Action(action="add_web_listener", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NEEDS_SPECIFIC_COMPLIANCE:
            # Extract compliance requirements (GDPR, SOC2, HIPAA, etc.)
            compliance_patterns = [
                r"(GDPR|SOC\s*2|HIPAA|ISO\s*\d+|PCI[\s-]?DSS|CCPA)",
                r"(compliance|compliant)",
            ]
            
            compliance_reqs = []
            for pattern in compliance_patterns:
                matches = re.findall(pattern, prospect_text, re.IGNORECASE)
                compliance_reqs.extend(matches)
            
            compliance_info = ""
            if compliance_reqs:
                unique_compliance = list(set([c.upper() for c in compliance_reqs if len(c) > 3]))[:3]
                compliance_info = f" - Required: {', '.join(unique_compliance)}"
            
            followup_context = (
                f"COMPLIANCE REQUIREMENT IDENTIFIED{compliance_info} - Proof and monitoring strategy:\n"
                f"1. Send compliance certifications, audit reports, and security documentation immediately\n"
                f"2. Provide detailed compliance matrix showing how you meet all their regulatory requirements\n"
                f"3. SET WEB LISTENER: Monitor for new compliance certifications or regulatory updates you obtain\n"
                f"4. Offer call with security/compliance team to review architecture and answer technical questions"
            )
            return Action(action="add_web_listener", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.SATISFIED_WITH_CURRENT_SOLUTION:
            # Extract competitor mentions
            competitor_patterns = [
                r"(?:using|use|have|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                r"([A-Z][a-z]+)\s+(?:right now|currently)",
            ]
            
            competitors = []
            for pattern in competitor_patterns:
                matches = re.findall(pattern, prospect_text)
                competitors.extend(matches)
            
            competitor_info = ""
            if competitors:
                # Filter for likely company names (capitalize, not common words)
                likely_competitors = [c for c in competitors if len(c) > 3 and c not in ['Sure', 'Yeah', 'Okay']][:2]
                if likely_competitors:
                    competitor_info = f" - Current vendor: {', '.join(likely_competitors)}"
            
            followup_context = (
                f"SATISFIED WITH INCUMBENT{competitor_info} - Competitive displacement strategy:\n"
                f"1. Send competitive comparison sheet highlighting your unique advantages and differentiators\n"
                f"2. Share case studies of companies who switched from their current provider to you\n"
                f"3. Focus on what they're likely missing: newer features, better pricing, superior support\n"
                f"4. Set 6-month follow-up reminder (contracts often renew annually - position for next cycle)"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        elif opportunity_type == OpportunityClassification.NOT_A_PRIORITY_FOR_LEADERSHIP:
            # Extract timing or priority mentions
            timing_match = re.search(r"(next\s+(?:quarter|month|year)|Q[1-4]|\d+\s+months?)", prospect_text, re.IGNORECASE)
            timing_info = timing_match.group(1) if timing_match else "3-6 months"
            
            followup_context = (
                f"NOT CURRENT PRIORITY - Long-term nurture strategy for re-engagement in {timing_info}:\n"
                f"1. Send value-add content (industry reports, best practices) to stay top-of-mind without being pushy\n"
                f"2. Connect on LinkedIn and engage with their posts to maintain relationship warmth\n"
                f"3. Set calendar reminder to follow up in {timing_info} when priorities may have shifted\n"
                f"4. Monitor their company news (funding, expansion, leadership changes) that could reprioritize this need"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
        
        else:  # OTHER or any unhandled type
            followup_context = (
                "GENERAL FOLLOW-UP - Standard engagement strategy:\n"
                "1. Send meeting recap email summarizing discussion points and next steps within 24 hours\n"
                "2. Provide relevant resources (case studies, product information) based on conversation topics\n"
                "3. Propose specific next action with date/time options (demo, technical call, or stakeholder meeting)\n"
                "4. Set follow-up reminder for 7-10 days if no response to initial outreach"
            )
            return Action(action="follow_up", call_id=call_id, followup_context=followup_context)
