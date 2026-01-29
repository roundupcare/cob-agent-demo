"""
COB Detection Engine
Implements detection rules for various COB issues
"""

from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from data_models import (
    Patient, Insurance, Claim, InsuranceType, ClaimStatus,
    DenialReason, COBAlert
)


@dataclass
class DetectionRule:
    """Represents a COB detection rule"""
    rule_id: str
    rule_name: str
    description: str
    severity: str  # HIGH, MEDIUM, LOW
    
    
class COBDetectionEngine:
    """Detects COB issues in claims data"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        
    def _initialize_rules(self) -> List[DetectionRule]:
        """Initialize detection rules"""
        return [
            DetectionRule(
                rule_id="R001",
                rule_name="Medicare Secondary Payer (MSP) Violation",
                description="Medicare billed as primary when patient has other coverage",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R002",
                rule_name="Wrong Primary Payer Order",
                description="Incorrect insurance priority resulting in denial",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R003",
                rule_name="Missing Secondary Coverage",
                description="Patient likely has unreported secondary insurance",
                severity="MEDIUM"
            ),
            DetectionRule(
                rule_id="R004",
                rule_name="Dependent Age-Out",
                description="Dependent coverage terminated due to age, new coverage needed",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R005",
                rule_name="Auto/Liability Should Be Primary",
                description="Accident-related claim with auto/liability insurance available",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R006",
                rule_name="Workers Comp Should Be Primary",
                description="Work-related injury billed to health insurance instead of WC",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R007",
                rule_name="Coordination Period Mismatch",
                description="Claim filed outside of coverage period",
                severity="HIGH"
            ),
            DetectionRule(
                rule_id="R008",
                rule_name="Dual Coverage Not Utilized",
                description="Secondary insurance not billed for remaining balance",
                severity="MEDIUM"
            )
        ]
    
    def analyze_claim(
        self, 
        claim: Claim, 
        patient: Patient,
        all_patients: Optional[List[Patient]] = None
    ) -> List[COBAlert]:
        """Analyze a single claim for COB issues"""
        
        alerts = []
        
        # R001: MSP Violation Check
        msp_alert = self._check_msp_violation(claim, patient)
        if msp_alert:
            alerts.append(msp_alert)
        
        # R002: Wrong Primary Payer Order
        wrong_order_alert = self._check_wrong_primary_order(claim, patient)
        if wrong_order_alert:
            alerts.append(wrong_order_alert)
        
        # R003: Missing Secondary Coverage
        missing_secondary_alert = self._check_missing_secondary(claim, patient)
        if missing_secondary_alert:
            alerts.append(missing_secondary_alert)
        
        # R004: Dependent Age-Out
        age_out_alert = self._check_dependent_age_out(claim, patient)
        if age_out_alert:
            alerts.append(age_out_alert)
        
        # R005: Auto/Liability Primary
        auto_alert = self._check_auto_liability(claim, patient)
        if auto_alert:
            alerts.append(auto_alert)
        
        # R006: Workers Comp Primary
        wc_alert = self._check_workers_comp(claim, patient)
        if wc_alert:
            alerts.append(wc_alert)
        
        # R007: Coordination Period Mismatch
        period_alert = self._check_coordination_period(claim, patient)
        if period_alert:
            alerts.append(period_alert)
        
        # R008: Dual Coverage Not Utilized
        dual_coverage_alert = self._check_dual_coverage_utilization(claim, patient)
        if dual_coverage_alert:
            alerts.append(dual_coverage_alert)
        
        return alerts
    
    def _check_msp_violation(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check for Medicare Secondary Payer violations
        
        MSP Rules:
        - If patient has group health plan through current employment → That's primary, Medicare secondary
        - If patient is 65+ and working with employer coverage → Employer primary if 20+ employees
        - If patient is under 65 with Medicare (disability/ESRD) and working → Employer primary
        """
        
        # Get primary insurance from claim
        if not claim.primary_insurance_id:
            return None
        
        primary_ins = next(
            (ins for ins in patient.insurance_coverage 
             if ins.insurance_id == claim.primary_insurance_id),
            None
        )
        
        # Only flag if Medicare was actually billed as primary
        if not primary_ins or primary_ins.insurance_type != InsuranceType.MEDICARE:
            return None
        
        # Get patient age and employment
        patient_age = patient.get_age(claim.service_date)
        is_employed = patient.employment_status == "Employed"
        
        # Check if patient has other active coverage
        active_insurance = patient.get_active_insurance(claim.service_date)
        has_commercial = any(
            ins.insurance_type in [InsuranceType.COMMERCIAL, InsuranceType.MEDICARE_ADVANTAGE]
            for ins in active_insurance
        )
        
        # MSP VIOLATION CONDITIONS:
        # 1. Patient has both Medicare AND commercial insurance → Commercial should be primary
        # 2. Patient is under 65 with Medicare (disability) AND employed → Should have employer coverage
        # 3. Patient is 65-70 and employed → If employer has 20+ employees, employer coverage is primary
        
        should_flag = False
        reason = ""
        confidence = 0.0
        
        if has_commercial and is_employed:
            # Has both coverages - commercial should definitely be primary
            should_flag = True
            reason = f"Patient has active commercial insurance (employer) that should be primary. Age: {patient_age}, Employed."
            confidence = 0.95
        elif has_commercial:
            # Has commercial but not employed - still should be primary (spouse, retiree, etc)
            should_flag = True  
            reason = f"Patient has active commercial insurance that should be primary. Age: {patient_age}."
            confidence = 0.90
        elif patient_age < 65 and is_employed:
            # Under 65 with Medicare (disability) and working - should have employer coverage
            should_flag = True
            reason = f"Patient under 65 with Medicare (likely disabled) is employed. Employer coverage should be primary. Age: {patient_age}."
            confidence = 0.80
        elif patient_age >= 65 and patient_age <= 70 and is_employed:
            # Working senior - likely has employer coverage that should be primary
            should_flag = True
            reason = f"Working senior (age {patient_age}) likely has employer coverage that should be primary."
            confidence = 0.75
        
        if should_flag:
            # Build description with CARC code if claim was denied
            description = reason
            if claim.carc_code:
                description += f" Payer denial code: {claim.carc_code}."
            
            return COBAlert(
                alert_id=None,
                claim_id=claim.claim_id,
                patient_id=patient.patient_id,
                alert_type="MSP_VIOLATION",
                severity="HIGH",
                confidence_score=confidence,
                detected_date=date.today(),
                description=description,
                recommended_action="Verify employer/commercial insurance coverage and rebill with Medicare as secondary",
                data_points={
                    "patient_age": patient_age,
                    "employment_status": patient.employment_status,
                    "has_commercial_insurance": has_commercial,
                    "commercial_count": len([i for i in active_insurance if i.insurance_type in [InsuranceType.COMMERCIAL, InsuranceType.MEDICARE_ADVANTAGE]]),
                    "carc_code": claim.carc_code,
                    "claim_status": claim.claim_status.value,
                    "detection_method": "835 Remittance Analysis" if claim.carc_code else "Proactive Pre-Submission"
                },
                estimated_recovery=claim.billed_amount * 0.8  # Typically recover most of claim
            )
        
        return None
    
    def _check_wrong_primary_order(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check if claim was denied due to wrong primary payer"""
        
        if claim.denial_reason != DenialReason.WRONG_PRIMARY:
            return None
        
        active_insurance = patient.get_active_insurance(claim.service_date)
        
        if len(active_insurance) < 2:
            return None
        
        # Find which insurance should actually be primary
        correct_primary = None
        for ins in active_insurance:
            if ins.priority_order == 2:  # Currently marked as secondary
                # Check if this should be primary based on type
                if ins.insurance_type == InsuranceType.COMMERCIAL:
                    correct_primary = ins
                    break
        
        if correct_primary:
            return COBAlert(
                alert_id=None,
                claim_id=claim.claim_id,
                patient_id=patient.patient_id,
                alert_type="WRONG_PRIMARY_ORDER",
                severity="HIGH",
                confidence_score=0.90,
                detected_date=date.today(),
                description=f"Claim denied due to wrong primary payer. "
                           f"Should bill {correct_primary.payer_name} as primary",
                recommended_action=f"Rebill claim with {correct_primary.payer_name} as primary payer",
                data_points={
                    "denied_payer": patient.insurance_coverage[0].payer_name,
                    "correct_primary": correct_primary.payer_name,
                    "denial_date": str(claim.denial_date)
                },
                estimated_recovery=claim.billed_amount * 0.75
            )
        
        return None
    
    def _check_missing_secondary(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check for likely missing secondary coverage"""
        
        # Indicators of missing secondary:
        # 1. Spouse employed but no secondary insurance
        # 2. Paid claim with significant patient responsibility
        # 3. Pattern of single coverage in dual-income household
        
        if claim.claim_status != ClaimStatus.PAID:
            return None
        
        if len(patient.insurance_coverage) > 1:
            return None  # Already has secondary
        
        # Check for spouse employment indicator
        has_spouse_employment = patient.spouse_employment == "Employed"
        
        # Check patient responsibility
        patient_responsibility = claim.billed_amount - claim.paid_amount
        high_patient_responsibility = patient_responsibility > claim.billed_amount * 0.2
        
        if has_spouse_employment or high_patient_responsibility:
            confidence = 0.70 if has_spouse_employment else 0.50
            
            return COBAlert(
                alert_id=None,
                claim_id=claim.claim_id,
                patient_id=patient.patient_id,
                alert_type="MISSING_SECONDARY",
                severity="MEDIUM",
                confidence_score=confidence,
                detected_date=date.today(),
                description=f"Patient likely has unreported secondary coverage. "
                           f"Patient responsibility: ${patient_responsibility:,.2f}",
                recommended_action="Contact patient to verify if they have other insurance coverage",
                data_points={
                    "spouse_employed": has_spouse_employment,
                    "patient_responsibility": patient_responsibility,
                    "responsibility_percentage": round(patient_responsibility / claim.billed_amount * 100, 1)
                },
                estimated_recovery=patient_responsibility * 0.5  # Conservative estimate
            )
        
        return None
    
    def _check_dependent_age_out(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check for dependent aging out of coverage"""
        
        patient_age = patient.get_age(claim.service_date)
        
        # Check if patient is near or past age 26 (dependent cutoff)
        if patient_age < 25 or patient_age > 27:
            return None
        
        # Check if coverage was terminated
        if not patient.insurance_coverage:
            return None
        
        primary_ins = patient.insurance_coverage[0]
        
        # Check if coverage ended near patient's 26th birthday
        if primary_ins.termination_date:
            # Calculate age at termination
            age_at_term = patient.get_age(primary_ins.termination_date)
            
            if age_at_term == 26 or age_at_term == 25:
                # Check if claim was filed after termination
                claim_after_term = claim.service_date > primary_ins.termination_date
                
                if claim_after_term:
                    return COBAlert(
                        alert_id=None,
                        claim_id=claim.claim_id,
                        patient_id=patient.patient_id,
                        alert_type="DEPENDENT_AGE_OUT",
                        severity="HIGH",
                        confidence_score=0.95,
                        detected_date=date.today(),
                        description=f"Dependent coverage terminated at age 26. "
                                   f"Claim service date after termination.",
                        recommended_action="Verify patient has obtained new coverage. "
                                         "Contact patient for current insurance information.",
                        data_points={
                            "patient_age": patient_age,
                            "termination_date": str(primary_ins.termination_date),
                            "service_date": str(claim.service_date),
                            "days_after_termination": (claim.service_date - primary_ins.termination_date).days
                        },
                        estimated_recovery=claim.billed_amount * 0.8
                    )
        
        return None
    
    def _check_auto_liability(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check if auto/liability insurance should be primary"""
        
        if not claim.is_accident_related:
            return None
        
        # Check if claim has accident diagnosis codes
        has_auto_insurance = any(
            ins.insurance_type == InsuranceType.AUTO_INSURANCE 
            for ins in patient.insurance_coverage
        )
        
        # Check if health insurance was billed as primary
        if claim.primary_insurance_id:
            primary_ins = next(
                (ins for ins in patient.insurance_coverage 
                 if ins.insurance_id == claim.primary_insurance_id),
                None
            )
            
            if primary_ins and primary_ins.insurance_type in [
                InsuranceType.COMMERCIAL, InsuranceType.MEDICARE, InsuranceType.MEDICAID
            ]:
                confidence = 0.85 if has_auto_insurance else 0.70
                
                return COBAlert(
                    alert_id=None,
                    claim_id=claim.claim_id,
                    patient_id=patient.patient_id,
                    alert_type="AUTO_LIABILITY_PRIMARY",
                    severity="HIGH",
                    confidence_score=confidence,
                    detected_date=date.today(),
                    description="Accident-related claim billed to health insurance. "
                               "Auto/liability insurance should be primary.",
                    recommended_action="Contact patient to obtain auto insurance information. "
                                     "Rebill to auto insurance as primary.",
                    data_points={
                        "has_auto_insurance_on_file": has_auto_insurance,
                        "diagnosis_codes": claim.diagnosis_codes,
                        "current_primary": primary_ins.payer_name
                    },
                    estimated_recovery=claim.billed_amount  # Often 100% recovery
                )
        
        return None
    
    def _check_workers_comp(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check if workers compensation should be primary"""
        
        if not claim.is_work_related:
            return None
        
        # Check if health insurance was billed
        if claim.primary_insurance_id:
            primary_ins = next(
                (ins for ins in patient.insurance_coverage 
                 if ins.insurance_id == claim.primary_insurance_id),
                None
            )
            
            if primary_ins and primary_ins.insurance_type != InsuranceType.WORKERS_COMP:
                return COBAlert(
                    alert_id=None,
                    claim_id=claim.claim_id,
                    patient_id=patient.patient_id,
                    alert_type="WORKERS_COMP_PRIMARY",
                    severity="HIGH",
                    confidence_score=0.90,
                    detected_date=date.today(),
                    description="Work-related injury billed to health insurance. "
                               "Workers compensation should be primary.",
                    recommended_action="Contact patient/employer for workers comp information. "
                                     "File workers comp claim.",
                    data_points={
                        "diagnosis_codes": claim.diagnosis_codes,
                        "current_primary": primary_ins.payer_name,
                        "employment_status": patient.employment_status
                    },
                    estimated_recovery=claim.billed_amount  # Often 100% recovery
                )
        
        return None
    
    def _check_coordination_period(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check if claim falls outside coverage period"""
        
        if not claim.primary_insurance_id:
            return None
        
        primary_ins = next(
            (ins for ins in patient.insurance_coverage 
             if ins.insurance_id == claim.primary_insurance_id),
            None
        )
        
        if not primary_ins:
            return None
        
        # Check if service date is outside coverage period
        if not primary_ins.is_active(claim.service_date):
            days_outside = 0
            if claim.service_date < primary_ins.effective_date:
                days_outside = (primary_ins.effective_date - claim.service_date).days
                period_type = "before coverage start"
            else:
                days_outside = (claim.service_date - primary_ins.termination_date).days
                period_type = "after coverage end"
            
            return COBAlert(
                alert_id=None,
                claim_id=claim.claim_id,
                patient_id=patient.patient_id,
                alert_type="COORDINATION_PERIOD_MISMATCH",
                severity="HIGH",
                confidence_score=0.95,
                detected_date=date.today(),
                description=f"Claim service date {period_type}. "
                           f"Days outside coverage: {days_outside}",
                recommended_action="Verify patient had other active coverage during service date. "
                                 "Update claim with correct insurance information.",
                data_points={
                    "service_date": str(claim.service_date),
                    "coverage_start": str(primary_ins.effective_date),
                    "coverage_end": str(primary_ins.termination_date) if primary_ins.termination_date else "Active",
                    "days_outside_coverage": days_outside
                },
                estimated_recovery=claim.billed_amount * 0.75
            )
        
        return None
    
    def _check_dual_coverage_utilization(self, claim: Claim, patient: Patient) -> Optional[COBAlert]:
        """Check if secondary insurance was utilized for dual coverage"""
        
        if claim.claim_status != ClaimStatus.PAID:
            return None
        
        # Check if patient has secondary insurance
        active_insurance = patient.get_active_insurance(claim.service_date)
        if len(active_insurance) < 2:
            return None
        
        # Check if secondary insurance was billed
        if not claim.secondary_insurance_id:
            patient_responsibility = claim.billed_amount - claim.paid_amount
            
            if patient_responsibility > 100:  # Meaningful balance
                return COBAlert(
                    alert_id=None,
                    claim_id=claim.claim_id,
                    patient_id=patient.patient_id,
                    alert_type="SECONDARY_NOT_BILLED",
                    severity="MEDIUM",
                    confidence_score=0.80,
                    detected_date=date.today(),
                    description=f"Patient has active secondary coverage but it was not billed. "
                               f"Potential recovery: ${patient_responsibility:,.2f}",
                    recommended_action="Bill secondary insurance for remaining patient responsibility.",
                    data_points={
                        "patient_responsibility": patient_responsibility,
                        "secondary_insurance": active_insurance[1].payer_name,
                        "primary_paid": claim.paid_amount
                    },
                    estimated_recovery=patient_responsibility * 0.6  # Conservative estimate
                )
        
        return None
    
    def generate_risk_score(self, alerts: List[COBAlert]) -> float:
        """Generate an overall risk score for a claim based on alerts"""
        
        if not alerts:
            return 0.0
        
        severity_weights = {
            "HIGH": 10,
            "MEDIUM": 5,
            "LOW": 2
        }
        
        total_score = sum(
            severity_weights[alert.severity] * alert.confidence_score 
            for alert in alerts
        )
        
        # Normalize to 0-100 scale
        max_possible = len(alerts) * 10  # All HIGH severity at 1.0 confidence
        risk_score = min(100, (total_score / max_possible) * 100)
        
        return round(risk_score, 2)
