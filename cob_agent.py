"""
COB Agent - Main Architecture
Implements 4-component agent system: Predictive, Outreach, Resolution, Learning
"""

from datetime import datetime, date
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import json

from data_models import Patient, Claim, COBAlert, ClaimStatus
from detection_engine import COBDetectionEngine


@dataclass
class OutreachAttempt:
    """Records patient outreach attempt"""
    attempt_id: str
    alert_id: str
    patient_id: str
    channel: str  # EMAIL, SMS, PHONE, PORTAL
    timestamp: datetime
    message_sent: str
    response_received: Optional[str] = None
    response_timestamp: Optional[datetime] = None
    outcome: Optional[str] = None  # RESPONDED, NO_RESPONSE, RESOLVED, ESCALATED


@dataclass
class ResolutionWorkflow:
    """Guided resolution workflow for staff"""
    workflow_id: str
    alert_id: str
    claim_id: str
    workflow_type: str
    steps: List[Dict[str, str]]
    current_step: int = 0
    completed: bool = False
    resolution_notes: str = ""
    estimated_time_minutes: int = 30
    

@dataclass
class LearningInsight:
    """Insights learned from resolved cases"""
    insight_id: str
    pattern_type: str
    description: str
    occurrence_count: int
    success_rate: float
    avg_recovery_amount: float
    avg_resolution_time_days: float
    confidence_improvement: float = 0.0


class PredictiveAgent:
    """
    Predictive Agent: Flags at-risk claims before they become denials
    Uses detection rules and ML patterns to identify COB issues proactively
    """
    
    def __init__(self):
        self.detection_engine = COBDetectionEngine()
        self.processed_claims: List[str] = []
        
    def scan_claims(
        self, 
        claims: List[Claim], 
        patients: Dict[str, Patient]
    ) -> List[COBAlert]:
        """Scan all claims and generate alerts"""
        
        all_alerts = []
        
        for claim in claims:
            patient = patients.get(claim.patient_id)
            if not patient:
                continue
            
            # Run detection engine
            alerts = self.detection_engine.analyze_claim(claim, patient)
            
            # Add to results
            all_alerts.extend(alerts)
            self.processed_claims.append(claim.claim_id)
        
        return all_alerts
    
    def prioritize_alerts(self, alerts: List[COBAlert]) -> List[COBAlert]:
        """Prioritize alerts by potential recovery value and urgency"""
        
        def priority_score(alert: COBAlert) -> float:
            severity_weight = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
            recovery = alert.estimated_recovery or 0
            
            # Score = (severity * confidence * recovery)
            score = (
                severity_weight[alert.severity] * 
                alert.confidence_score * 
                (recovery / 1000)  # Normalize recovery
            )
            return score
        
        return sorted(alerts, key=priority_score, reverse=True)
    
    def generate_daily_report(
        self, 
        alerts: List[COBAlert],
        claims: List[Claim]
    ) -> Dict:
        """Generate daily summary report"""
        
        total_potential_recovery = sum(
            alert.estimated_recovery or 0 for alert in alerts
        )
        
        alerts_by_type = {}
        for alert in alerts:
            if alert.alert_type not in alerts_by_type:
                alerts_by_type[alert.alert_type] = []
            alerts_by_type[alert.alert_type].append(alert)
        
        return {
            "date": str(date.today()),
            "total_claims_scanned": len(claims),
            "total_alerts_generated": len(alerts),
            "high_priority_alerts": len([a for a in alerts if a.severity == "HIGH"]),
            "total_potential_recovery": round(total_potential_recovery, 2),
            "alerts_by_type": {
                alert_type: len(alert_list) 
                for alert_type, alert_list in alerts_by_type.items()
            },
            "top_10_alerts": [
                {
                    "alert_id": a.alert_id,
                    "claim_id": a.claim_id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "potential_recovery": a.estimated_recovery
                }
                for a in self.prioritize_alerts(alerts)[:10]
            ]
        }


class OutreachAgent:
    """
    Outreach Agent: Automated patient engagement via multiple channels
    Sends personalized messages to collect missing COB information
    """
    
    def __init__(self):
        self.outreach_attempts: List[OutreachAttempt] = []
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """Load message templates for different alert types"""
        
        return {
            "MISSING_SECONDARY": {
                "EMAIL": """
Subject: Update Your Insurance Information - Potential Coverage Available

Dear {patient_name},

Our records show you may have additional insurance coverage that could help reduce your out-of-pocket costs.

Claim Details:
- Service Date: {service_date}
- Amount You Owe: ${patient_responsibility}

If you or your spouse have other insurance coverage (through employment, retirement, or other sources), please update your information in our patient portal or call us at 555-0100.

This could significantly reduce your medical bills.

Thank you,
Sightline Health Revenue Team
                """,
                "SMS": "Your recent medical bill may be covered by additional insurance. Please update your insurance info at [portal_link] or call 555-0100. Could save you ${patient_responsibility}!"
            },
            
            "MSP_VIOLATION": {
                "EMAIL": """
Subject: Action Required - Update Your Insurance Information

Dear {patient_name},

We need to verify your current insurance coverage to ensure your claim is processed correctly.

Claim Details:
- Service Date: {service_date}
- Current Status: Requires review

Please confirm:
1. Are you currently employed or covered by an employer's insurance?
2. Do you have any insurance besides Medicare?

Update your information at our patient portal or call 555-0100.

Thank you,
Sightline Health Revenue Team
                """
            },
            
            "AUTO_LIABILITY_PRIMARY": {
                "EMAIL": """
Subject: Auto Insurance Information Needed

Dear {patient_name},

Your recent visit appears to be related to an accident. Your auto insurance may cover these medical expenses.

Claim Details:
- Service Date: {service_date}
- Billed Amount: ${billed_amount}

Please provide:
1. Auto insurance company name and policy number
2. Date of accident
3. Claim number (if already filed with auto insurance)

Contact us at 555-0100 or update via our patient portal.

Thank you,
Sightline Health Revenue Team
                """
            },
            
            "DEPENDENT_AGE_OUT": {
                "EMAIL": """
Subject: Important - Insurance Coverage Update Needed

Dear {patient_name},

Our records show your previous insurance coverage has ended. To ensure your medical bills are covered, we need your current insurance information.

Please provide your new insurance details as soon as possible:
- Update online at [portal_link]
- Call us at 555-0100
- Visit our billing office

Having current insurance on file will prevent delays in claim processing.

Thank you,
Sightline Health Revenue Team
                """
            }
        }
    
    def generate_outreach(
        self, 
        alert: COBAlert, 
        patient: Patient,
        claim: Claim,
        channel: str = "EMAIL"
    ) -> OutreachAttempt:
        """Generate personalized outreach message"""
        
        template_type = alert.alert_type
        if template_type not in self.templates:
            template_type = "MISSING_SECONDARY"  # Default
        
        template = self.templates[template_type].get(channel, "")
        
        # Personalize message
        message = template.format(
            patient_name=f"{patient.first_name} {patient.last_name}",
            service_date=claim.service_date.strftime("%B %d, %Y"),
            patient_responsibility=round(claim.billed_amount - claim.paid_amount, 2),
            billed_amount=round(claim.billed_amount, 2),
            portal_link="https://portal.sightlinehealth.com/update-insurance"
        )
        
        attempt = OutreachAttempt(
            attempt_id=f"OUT{len(self.outreach_attempts) + 1:06d}",
            alert_id=alert.alert_id,
            patient_id=patient.patient_id,
            channel=channel,
            timestamp=datetime.now(),
            message_sent=message
        )
        
        self.outreach_attempts.append(attempt)
        return attempt
    
    def track_response(
        self, 
        attempt_id: str, 
        response: str, 
        outcome: str
    ) -> bool:
        """Track patient response to outreach"""
        
        attempt = next(
            (a for a in self.outreach_attempts if a.attempt_id == attempt_id),
            None
        )
        
        if attempt:
            attempt.response_received = response
            attempt.response_timestamp = datetime.now()
            attempt.outcome = outcome
            return True
        
        return False
    
    def get_outreach_metrics(self) -> Dict:
        """Calculate outreach effectiveness metrics"""
        
        total_attempts = len(self.outreach_attempts)
        if total_attempts == 0:
            return {}
        
        responded = len([a for a in self.outreach_attempts if a.response_received])
        resolved = len([a for a in self.outreach_attempts if a.outcome == "RESOLVED"])
        
        response_rate = responded / total_attempts if total_attempts > 0 else 0
        resolution_rate = resolved / total_attempts if total_attempts > 0 else 0
        
        return {
            "total_outreach_attempts": total_attempts,
            "total_responses": responded,
            "total_resolved": resolved,
            "response_rate": round(response_rate * 100, 1),
            "resolution_rate": round(resolution_rate * 100, 1),
            "by_channel": self._metrics_by_channel()
        }
    
    def _metrics_by_channel(self) -> Dict:
        """Calculate metrics by communication channel"""
        
        channels = {}
        for attempt in self.outreach_attempts:
            if attempt.channel not in channels:
                channels[attempt.channel] = {
                    "sent": 0, "responded": 0, "resolved": 0
                }
            
            channels[attempt.channel]["sent"] += 1
            if attempt.response_received:
                channels[attempt.channel]["responded"] += 1
            if attempt.outcome == "RESOLVED":
                channels[attempt.channel]["resolved"] += 1
        
        return channels


class ResolutionAgent:
    """
    Resolution Agent: Provides guided workflows for revenue cycle staff
    Step-by-step pathways to resolve each type of COB issue
    """
    
    def __init__(self):
        self.workflows: List[ResolutionWorkflow] = []
        self.workflow_templates = self._load_workflow_templates()
        
    def _load_workflow_templates(self) -> Dict[str, List[Dict[str, str]]]:
        """Load workflow templates for each alert type"""
        
        return {
            "MSP_VIOLATION": [
                {
                    "step": 1,
                    "title": "Verify Patient Employment Status",
                    "description": "Check patient demographics for current employment or group health coverage",
                    "action": "Review patient record in EHR for employment/insurance updates"
                },
                {
                    "step": 2,
                    "title": "Request COB Information",
                    "description": "Contact patient for employer group health insurance details",
                    "action": "Use automated outreach or manual phone call"
                },
                {
                    "step": 3,
                    "title": "Update Insurance Priority",
                    "description": "Enter employer insurance as primary, Medicare as secondary",
                    "action": "Update payer priority in billing system"
                },
                {
                    "step": 4,
                    "title": "Rebill Claim",
                    "description": "Submit corrected claim to employer insurance as primary payer",
                    "action": "Generate and submit new claim"
                },
                {
                    "step": 5,
                    "title": "Bill Medicare Secondary",
                    "description": "After primary payment, bill Medicare for secondary coverage",
                    "action": "Submit crossover claim to Medicare"
                }
            ],
            
            "WRONG_PRIMARY_ORDER": [
                {
                    "step": 1,
                    "title": "Review Denial Reason",
                    "description": "Confirm payer denied due to COB/other insurance liability",
                    "action": "Check denial code and explanation of benefits"
                },
                {
                    "step": 2,
                    "title": "Identify Correct Primary",
                    "description": "Determine which insurance should be billed first based on COB rules",
                    "action": "Apply birthday rule, employment status, or other COB guidelines"
                },
                {
                    "step": 3,
                    "title": "Update Payer Priority",
                    "description": "Correct insurance priority in patient account",
                    "action": "Update billing system with correct primary/secondary order"
                },
                {
                    "step": 4,
                    "title": "Rebill to Correct Primary",
                    "description": "Submit claim to newly identified primary payer",
                    "action": "Generate and submit corrected claim"
                }
            ],
            
            "AUTO_LIABILITY_PRIMARY": [
                {
                    "step": 1,
                    "title": "Verify Accident Details",
                    "description": "Confirm injury is accident-related from medical records",
                    "action": "Review diagnosis codes and provider notes"
                },
                {
                    "step": 2,
                    "title": "Obtain Auto Insurance Info",
                    "description": "Contact patient for auto insurance policy details",
                    "action": "Use automated outreach or phone call"
                },
                {
                    "step": 3,
                    "title": "File Auto Insurance Claim",
                    "description": "Submit medical claim to auto insurance carrier",
                    "action": "Complete auto insurance claim form and submit"
                },
                {
                    "step": 4,
                    "title": "Monitor Auto Claim",
                    "description": "Track auto insurance claim status and payment",
                    "action": "Follow up on pending auto claim"
                },
                {
                    "step": 5,
                    "title": "Bill Health Insurance Secondary",
                    "description": "If auto coverage insufficient, bill health insurance for balance",
                    "action": "Submit coordination of benefits to health insurance"
                }
            ],
            
            "MISSING_SECONDARY": [
                {
                    "step": 1,
                    "title": "Send Patient Inquiry",
                    "description": "Ask patient about additional insurance coverage",
                    "action": "Use automated outreach via email/SMS/portal"
                },
                {
                    "step": 2,
                    "title": "Collect Secondary Insurance Info",
                    "description": "Obtain secondary insurance policy details from patient",
                    "action": "Receive and verify insurance card information"
                },
                {
                    "step": 3,
                    "title": "Verify Secondary Coverage",
                    "description": "Confirm active coverage and benefits with secondary payer",
                    "action": "Electronic eligibility check or payer phone verification"
                },
                {
                    "step": 4,
                    "title": "Bill Secondary Insurance",
                    "description": "Submit claim to secondary payer for remaining balance",
                    "action": "Generate and submit secondary claim with primary EOB"
                }
            ],
            
            "DEPENDENT_AGE_OUT": [
                {
                    "step": 1,
                    "title": "Confirm Coverage Termination",
                    "description": "Verify dependent coverage ended due to age",
                    "action": "Check insurance eligibility and termination date"
                },
                {
                    "step": 2,
                    "title": "Request Current Coverage",
                    "description": "Contact patient for new insurance information",
                    "action": "Automated outreach emphasizing urgency"
                },
                {
                    "step": 3,
                    "title": "Update Patient Account",
                    "description": "Enter new insurance information into system",
                    "action": "Update demographics and insurance in EHR/billing system"
                },
                {
                    "step": 4,
                    "title": "Rebill Claim",
                    "description": "Submit claim to patient's current insurance",
                    "action": "Generate new claim with correct coverage information"
                }
            ]
        }
    
    def create_workflow(self, alert: COBAlert) -> ResolutionWorkflow:
        """Create a guided workflow for an alert"""
        
        workflow_type = alert.alert_type
        steps = self.workflow_templates.get(
            workflow_type, 
            self.workflow_templates["MISSING_SECONDARY"]  # Default
        )
        
        workflow = ResolutionWorkflow(
            workflow_id=f"WF{len(self.workflows) + 1:06d}",
            alert_id=alert.alert_id,
            claim_id=alert.claim_id,
            workflow_type=workflow_type,
            steps=steps,
            estimated_time_minutes=len(steps) * 5  # Estimate 5 min per step
        )
        
        self.workflows.append(workflow)
        return workflow
    
    def advance_workflow(self, workflow_id: str, notes: str = "") -> bool:
        """Advance workflow to next step"""
        
        workflow = next(
            (w for w in self.workflows if w.workflow_id == workflow_id),
            None
        )
        
        if not workflow:
            return False
        
        if workflow.current_step < len(workflow.steps) - 1:
            workflow.current_step += 1
            workflow.resolution_notes += f"\nStep {workflow.current_step}: {notes}"
        else:
            workflow.completed = True
            workflow.resolution_notes += f"\nCompleted: {notes}"
        
        return True
    
    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get current status of a workflow"""
        
        workflow = next(
            (w for w in self.workflows if w.workflow_id == workflow_id),
            None
        )
        
        if not workflow:
            return {}
        
        current_step_info = workflow.steps[workflow.current_step]
        
        return {
            "workflow_id": workflow.workflow_id,
            "alert_id": workflow.alert_id,
            "claim_id": workflow.claim_id,
            "type": workflow.workflow_type,
            "total_steps": len(workflow.steps),
            "current_step": workflow.current_step + 1,
            "completed": workflow.completed,
            "progress_percentage": round(
                (workflow.current_step + 1) / len(workflow.steps) * 100, 1
            ),
            "current_step_details": current_step_info,
            "next_action": current_step_info["action"]
        }


class LearningAgent:
    """
    Learning Agent: Continuously improves detection and resolution
    Tracks outcomes and refines confidence scores
    """
    
    def __init__(self):
        self.insights: List[LearningInsight] = []
        self.case_history: List[Dict] = []
        
    def record_outcome(
        self, 
        alert: COBAlert,
        workflow: ResolutionWorkflow,
        actual_recovery: float,
        resolution_time_days: int,
        was_accurate: bool
    ):
        """Record the outcome of a resolved case"""
        
        self.case_history.append({
            "alert_id": alert.alert_id,
            "alert_type": alert.alert_type,
            "predicted_recovery": alert.estimated_recovery or 0,
            "actual_recovery": actual_recovery,
            "predicted_confidence": alert.confidence_score,
            "was_accurate": was_accurate,
            "resolution_time_days": resolution_time_days,
            "workflow_steps": len(workflow.steps),
            "timestamp": datetime.now()
        })
    
    def generate_insights(self) -> List[LearningInsight]:
        """Analyze case history and generate insights"""
        
        if len(self.case_history) < 10:
            return []  # Need minimum data
        
        insights = []
        
        # Group by alert type
        by_type = {}
        for case in self.case_history:
            alert_type = case["alert_type"]
            if alert_type not in by_type:
                by_type[alert_type] = []
            by_type[alert_type].append(case)
        
        # Generate insights per type
        for alert_type, cases in by_type.items():
            if len(cases) < 3:
                continue
            
            accurate_count = sum(1 for c in cases if c["was_accurate"])
            total_recovery = sum(c["actual_recovery"] for c in cases)
            avg_resolution_time = sum(c["resolution_time_days"] for c in cases) / len(cases)
            
            insight = LearningInsight(
                insight_id=f"INS{len(self.insights) + 1:04d}",
                pattern_type=alert_type,
                description=f"Pattern analysis for {alert_type} alerts",
                occurrence_count=len(cases),
                success_rate=round(accurate_count / len(cases), 3),
                avg_recovery_amount=round(total_recovery / len(cases), 2),
                avg_resolution_time_days=round(avg_resolution_time, 1)
            )
            
            insights.append(insight)
            self.insights.append(insight)
        
        return insights
    
    def get_learning_metrics(self) -> Dict:
        """Calculate overall learning metrics"""
        
        if not self.case_history:
            return {}
        
        total_cases = len(self.case_history)
        accurate_predictions = sum(1 for c in self.case_history if c["was_accurate"])
        total_predicted = sum(c["predicted_recovery"] for c in self.case_history)
        total_actual = sum(c["actual_recovery"] for c in self.case_history)
        
        return {
            "total_resolved_cases": total_cases,
            "prediction_accuracy": round(accurate_predictions / total_cases * 100, 1),
            "total_recovery_achieved": round(total_actual, 2),
            "prediction_accuracy_amount": round(total_actual / total_predicted * 100, 1) if total_predicted > 0 else 0,
            "insights_generated": len(self.insights),
            "avg_resolution_time_days": round(
                sum(c["resolution_time_days"] for c in self.case_history) / total_cases, 1
            )
        }


class COBAgent:
    """
    Main COB Agent orchestrator
    Coordinates all 4 component agents
    """
    
    def __init__(self):
        self.predictive_agent = PredictiveAgent()
        self.outreach_agent = OutreachAgent()
        self.resolution_agent = ResolutionAgent()
        self.learning_agent = LearningAgent()
        
    def process_claims_batch(
        self, 
        claims: List[Claim],
        patients: Dict[str, Patient]
    ) -> Dict:
        """Process a batch of claims through the complete agent workflow"""
        
        # Step 1: Predictive Agent - Detect issues
        alerts = self.predictive_agent.scan_claims(claims, patients)
        prioritized_alerts = self.predictive_agent.prioritize_alerts(alerts)
        
        # Step 2: Outreach Agent - Generate patient outreach for top alerts
        outreach_generated = []
        for alert in prioritized_alerts[:20]:  # Top 20 for outreach
            patient = patients.get(alert.patient_id)
            claim = next((c for c in claims if c.claim_id == alert.claim_id), None)
            
            if patient and claim:
                outreach = self.outreach_agent.generate_outreach(alert, patient, claim)
                outreach_generated.append(outreach.attempt_id)
        
        # Step 3: Resolution Agent - Create workflows for high-priority alerts
        workflows_created = []
        for alert in prioritized_alerts[:10]:  # Top 10 for immediate workflow
            workflow = self.resolution_agent.create_workflow(alert)
            workflows_created.append(workflow.workflow_id)
        
        # Step 4: Generate daily report
        daily_report = self.predictive_agent.generate_daily_report(alerts, claims)
        
        return {
            "processing_summary": {
                "claims_processed": len(claims),
                "alerts_generated": len(alerts),
                "high_priority_alerts": len([a for a in alerts if a.severity == "HIGH"]),
                "outreach_initiated": len(outreach_generated),
                "workflows_created": len(workflows_created),
                "total_potential_recovery": daily_report["total_potential_recovery"]
            },
            "daily_report": daily_report,
            "top_priority_alerts": prioritized_alerts[:10],
            "outreach_attempts": outreach_generated,
            "workflows": workflows_created
        }
    
    def get_dashboard_metrics(self) -> Dict:
        """Generate comprehensive dashboard metrics"""
        
        return {
            "predictive_metrics": {
                "claims_scanned": len(self.predictive_agent.processed_claims)
            },
            "outreach_metrics": self.outreach_agent.get_outreach_metrics(),
            "resolution_metrics": {
                "active_workflows": len([w for w in self.resolution_agent.workflows if not w.completed]),
                "completed_workflows": len([w for w in self.resolution_agent.workflows if w.completed])
            },
            "learning_metrics": self.learning_agent.get_learning_metrics()
        }
