"""
COB Agent Demonstration
Generates synthetic data and runs the complete agent workflow
"""

import json
from datetime import datetime, date
from typing import Dict

from data_models import Patient, Claim
from synthetic_data import SyntheticDataGenerator
from cob_agent import COBAgent


def format_currency(amount: float) -> str:
    """Format currency for display"""
    return f"${amount:,.2f}"


def print_section_header(title: str):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def print_alert_details(alert, patient: Patient, claim: Claim):
    """Print detailed alert information"""
    print(f"\nAlert ID: {alert.alert_id}")
    print(f"Type: {alert.alert_type}")
    print(f"Severity: {alert.severity} | Confidence: {alert.confidence_score:.2%}")
    print(f"\nPatient: {patient.first_name} {patient.last_name} (ID: {patient.patient_id})")
    print(f"Claim: {claim.claim_id} | Service Date: {claim.service_date}")
    print(f"Billed: {format_currency(claim.billed_amount)} | Status: {claim.claim_status.value}")
    print(f"\nIssue: {alert.description}")
    print(f"Recommended Action: {alert.recommended_action}")
    print(f"Estimated Recovery: {format_currency(alert.estimated_recovery or 0)}")
    
    if alert.data_points:
        print(f"\nSupporting Data:")
        for key, value in alert.data_points.items():
            print(f"  - {key}: {value}")


def run_demonstration():
    """Run complete COB agent demonstration"""
    
    print_section_header("SIGHTLINE HEALTH - COB AGENT PROTOTYPE DEMONSTRATION")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis prototype demonstrates Sightline's AI-powered COB detection system")
    print("with embedded red flags in synthetic patient data.\n")
    
    # Generate synthetic data
    print_section_header("STEP 1: GENERATING SYNTHETIC PATIENT DATA")
    print("Creating 100 patients with various COB scenarios...")
    
    generator = SyntheticDataGenerator(seed=42)
    patients_list, claims_list = generator.generate_dataset(num_patients=100)
    
    # Convert to dictionary for lookup
    patients_dict = {p.patient_id: p for p in patients_list}
    
    print(f"✓ Generated {len(patients_list)} patients")
    print(f"✓ Generated {len(claims_list)} claims")
    print(f"\nScenario Distribution:")
    
    scenario_counts = {
        "Normal Coverage": 0,
        "Missing Secondary Insurance": 0,
        "Wrong Primary/Secondary Order": 0,
        "Medicare Secondary Payer Violation": 0,
        "Dependent Aging Out": 0,
        "Auto Accident Liability": 0,
        "Workers Compensation": 0
    }
    
    # Count scenarios by analyzing claims
    for claim in claims_list:
        if claim.denial_reason:
            if "MSP" in str(claim.denial_reason.value):
                scenario_counts["Medicare Secondary Payer Violation"] += 1
            elif "WRONG_PRIMARY" in str(claim.denial_reason.value):
                scenario_counts["Wrong Primary/Secondary Order"] += 1
            elif "DEPENDENT" in str(claim.denial_reason.value):
                scenario_counts["Dependent Aging Out"] += 1
            elif "AUTO" in str(claim.denial_reason.value):
                scenario_counts["Auto Accident Liability"] += 1
        elif claim.claim_status.value == "Paid" and len(patients_dict[claim.patient_id].insurance_coverage) == 1:
            scenario_counts["Missing Secondary Insurance"] += 1
        elif claim.is_work_related:
            scenario_counts["Workers Compensation"] += 1
        else:
            scenario_counts["Normal Coverage"] += 1
    
    for scenario, count in scenario_counts.items():
        if count > 0:
            print(f"  • {scenario}: {count} claims")
    
    # Initialize and run COB Agent
    print_section_header("STEP 2: INITIALIZING COB AGENT")
    print("Starting 4-component agent architecture:")
    print("  1. Predictive Agent - Flags at-risk claims")
    print("  2. Outreach Agent - Automated patient engagement")
    print("  3. Resolution Agent - Guided staff workflows")
    print("  4. Learning Agent - Continuous improvement")
    
    agent = COBAgent()
    
    # Process claims
    print_section_header("STEP 3: PROCESSING CLAIMS THROUGH AGENT")
    print("Running detection engine on all claims...\n")
    
    results = agent.process_claims_batch(claims_list, patients_dict)
    
    # Display results
    print_section_header("STEP 4: PROCESSING SUMMARY")
    
    summary = results["processing_summary"]
    print(f"Claims Processed: {summary['claims_processed']}")
    print(f"Alerts Generated: {summary['alerts_generated']}")
    print(f"High Priority Alerts: {summary['high_priority_alerts']}")
    print(f"Outreach Initiated: {summary['outreach_initiated']}")
    print(f"Workflows Created: {summary['workflows_created']}")
    print(f"\nTotal Potential Recovery: {format_currency(summary['total_potential_recovery'])}")
    
    # Daily report
    print_section_header("STEP 5: DAILY REPORT")
    
    daily_report = results["daily_report"]
    print("Alerts by Type:")
    for alert_type, count in daily_report["alerts_by_type"].items():
        print(f"  • {alert_type}: {count}")
    
    # Top priority alerts
    print_section_header("STEP 6: TOP 10 HIGH-VALUE ALERTS")
    print("These alerts represent the highest potential recovery opportunities:\n")
    
    top_alerts = results["top_priority_alerts"]
    
    for i, alert in enumerate(top_alerts[:10], 1):
        patient = patients_dict[alert.patient_id]
        claim = next(c for c in claims_list if c.claim_id == alert.claim_id)
        
        print(f"\n{'─'*80}")
        print(f"RANK #{i} - {alert.alert_type}")
        print(f"{'─'*80}")
        print_alert_details(alert, patient, claim)
    
    # Sample outreach
    print_section_header("STEP 7: AUTOMATED PATIENT OUTREACH (SAMPLE)")
    
    if results["top_priority_alerts"]:
        sample_alert = results["top_priority_alerts"][0]
        sample_patient = patients_dict[sample_alert.patient_id]
        sample_claim = next(c for c in claims_list if c.claim_id == sample_alert.claim_id)
        
        # Generate sample outreach
        outreach = agent.outreach_agent.generate_outreach(
            sample_alert, sample_patient, sample_claim, "EMAIL"
        )
        
        print(f"Example outreach message for Alert {sample_alert.alert_id}:")
        print(f"\nRecipient: {sample_patient.email}")
        print(f"Channel: {outreach.channel}")
        print(f"Sent: {outreach.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n{outreach.message_sent}")
    
    # Sample workflow
    print_section_header("STEP 8: RESOLUTION WORKFLOW (SAMPLE)")
    
    if results["workflows"]:
        workflow_id = results["workflows"][0]
        workflow_status = agent.resolution_agent.get_workflow_status(workflow_id)
        
        print(f"Workflow ID: {workflow_status['workflow_id']}")
        print(f"Type: {workflow_status['type']}")
        print(f"Progress: {workflow_status['current_step']}/{workflow_status['total_steps']} "
              f"({workflow_status['progress_percentage']}%)")
        print(f"\nCurrent Step Details:")
        print(f"  Title: {workflow_status['current_step_details']['title']}")
        print(f"  Description: {workflow_status['current_step_details']['description']}")
        print(f"  Action Required: {workflow_status['current_step_details']['action']}")
    
    # Red flag accounts summary
    print_section_header("STEP 9: RED FLAG ACCOUNTS FOR REVIEW")
    print("Accounts requiring immediate attention:\n")
    
    high_priority_alerts = [a for a in top_alerts if a.severity == "HIGH"]
    
    # Group by patient
    red_flag_patients = {}
    for alert in high_priority_alerts:
        if alert.patient_id not in red_flag_patients:
            red_flag_patients[alert.patient_id] = {
                "patient": patients_dict[alert.patient_id],
                "alerts": [],
                "total_recovery": 0
            }
        red_flag_patients[alert.patient_id]["alerts"].append(alert)
        red_flag_patients[alert.patient_id]["total_recovery"] += (alert.estimated_recovery or 0)
    
    # Sort by total recovery potential
    sorted_red_flags = sorted(
        red_flag_patients.items(),
        key=lambda x: x[1]["total_recovery"],
        reverse=True
    )
    
    print(f"{'Patient ID':<15} {'Name':<25} {'# Alerts':<10} {'Total Recovery':<20} {'Top Issue'}")
    print("─" * 100)
    
    for patient_id, data in sorted_red_flags[:15]:
        patient = data["patient"]
        num_alerts = len(data["alerts"])
        total_recovery = data["total_recovery"]
        top_issue = data["alerts"][0].alert_type.replace("_", " ")
        
        name = f"{patient.first_name} {patient.last_name}"
        print(f"{patient_id:<15} {name:<25} {num_alerts:<10} {format_currency(total_recovery):<20} {top_issue}")
    
    # Export results
    print_section_header("STEP 10: EXPORTING RESULTS")
    
    export_data = {
        "generated_date": str(datetime.now()),
        "summary": summary,
        "daily_report": daily_report,
        "red_flag_accounts": [
            {
                "patient_id": pid,
                "patient_name": f"{data['patient'].first_name} {data['patient'].last_name}",
                "mrn": data['patient'].mrn,
                "alert_count": len(data['alerts']),
                "total_recovery_potential": round(data['total_recovery'], 2),
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "type": a.alert_type,
                        "severity": a.severity,
                        "confidence": a.confidence_score,
                        "estimated_recovery": a.estimated_recovery,
                        "description": a.description
                    }
                    for a in data['alerts']
                ]
            }
            for pid, data in sorted_red_flags[:20]
        ],
        "top_10_alerts": [
            {
                "alert_id": a.alert_id,
                "claim_id": a.claim_id,
                "patient_id": a.patient_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "confidence_score": a.confidence_score,
                "estimated_recovery": a.estimated_recovery,
                "description": a.description,
                "recommended_action": a.recommended_action
            }
            for a in top_alerts[:10]
        ]
    }
    
    with open('/home/claude/cob_agent_prototype/demo_results.json', 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print("✓ Results exported to demo_results.json")
    
    # Financial impact summary
    print_section_header("STEP 11: FINANCIAL IMPACT ANALYSIS")
    
    total_potential = summary['total_potential_recovery']
    high_confidence_recovery = sum(
        a.estimated_recovery or 0 
        for a in top_alerts 
        if a.confidence_score > 0.8 and a.severity == "HIGH"
    )
    
    print(f"Total Potential Recovery (All Alerts): {format_currency(total_potential)}")
    print(f"High-Confidence Recovery (>80% confidence): {format_currency(high_confidence_recovery)}")
    print(f"\nProjected 12-Month Impact:")
    print(f"  • Daily Recovery: {format_currency(total_potential)}")
    print(f"  • Monthly Recovery (30 days): {format_currency(total_potential * 30)}")
    print(f"  • Annual Recovery (365 days): {format_currency(total_potential * 365)}")
    print(f"\nAssumptions:")
    print(f"  • Based on 100 patient sample")
    print(f"  • Average {len(claims_list)/len(patients_list):.1f} claims per patient")
    print(f"  • {len(high_priority_alerts)} high-priority issues identified")
    print(f"  • Average recovery per alert: {format_currency(total_potential/len(top_alerts) if top_alerts else 0)}")
    
    print_section_header("DEMONSTRATION COMPLETE")
    print("This prototype demonstrates:")
    print("  ✓ Automated COB issue detection across 8 denial types")
    print("  ✓ Proactive patient engagement workflows")
    print("  ✓ Guided resolution pathways for revenue cycle staff")
    print("  ✓ Significant revenue recovery opportunities")
    print("\nNext Steps:")
    print("  • Review demo_results.json for detailed analysis")
    print("  • Examine top 10 alerts for specific COB patterns")
    print("  • Analyze red flag accounts requiring immediate action")
    print("  • Consider integration with hospital EHR systems")


if __name__ == "__main__":
    run_demonstration()
