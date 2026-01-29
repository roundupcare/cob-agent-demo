"""
Synthetic Data Generator for COB Agent
Generates realistic patient, insurance, and claims data with embedded COB issues
"""

import random
from datetime import date, timedelta, datetime
from typing import List, Tuple, Optional
import uuid

from data_models import (
    Patient, Insurance, Claim, InsuranceType, ClaimStatus, 
    DenialReason, COBAlert
)


class SyntheticDataGenerator:
    """Generates synthetic healthcare data with COB red flags"""
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        
        # Sample data pools
        self.first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", 
            "Michael", "Linda", "William", "Elizabeth", "David", "Barbara",
            "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah",
            "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
            "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez",
            "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson",
            "Martin", "Lee", "Thompson", "White", "Harris", "Clark"
        ]
        
        self.payers = {
            InsuranceType.COMMERCIAL: [
                "Blue Cross Blue Shield", "Aetna", "UnitedHealthcare",
                "Cigna", "Humana", "Anthem"
            ],
            InsuranceType.MEDICARE: ["Medicare"],
            InsuranceType.MEDICAID: ["Medicaid"],
            InsuranceType.MEDICARE_ADVANTAGE: [
                "Humana Medicare Advantage", "UHC Medicare Advantage",
                "Aetna Medicare Advantage"
            ],
            InsuranceType.AUTO_INSURANCE: [
                "State Farm Auto", "Geico Auto", "Progressive Auto", "Allstate Auto"
            ],
            InsuranceType.WORKERS_COMP: [
                "State Workers Comp Fund", "Liberty Mutual WC", "Hartford WC"
            ]
        }
        
        self.diagnosis_codes = {
            "routine": ["Z00.00", "Z23", "I10", "E11.9", "J45.909"],
            "accident": ["S06.0X0A", "S82.001A", "V43.52XA", "W01.0XXA"],
            "work_injury": ["S61.001A", "M54.5", "S93.401A"],
            "emergency": ["I21.9", "J18.9", "K35.80", "S06.5X0A"]
        }
        
    def generate_patient(self, patient_num: int, scenario: str = "normal") -> Patient:
        """Generate a single patient with insurance coverage"""
        
        patient_id = f"PAT{patient_num:06d}"
        mrn = f"MRN{patient_num:08d}"
        
        first_name = random.choice(self.first_names)
        last_name = random.choice(self.last_names)
        
        # Age distribution
        if scenario == "medicare_age":
            age = random.randint(65, 85)
        elif scenario == "dependent_aging_out":
            age = 26  # Critical age for dependent coverage
        else:
            age = random.randint(18, 75)
            
        dob = date.today() - timedelta(days=age*365 + random.randint(0, 364))
        
        patient = Patient(
            patient_id=patient_id,
            mrn=mrn,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob,
            ssn_last_4=f"{random.randint(0, 9999):04d}",
            address=f"{random.randint(100, 9999)} Main St, City, ST {random.randint(10000, 99999)}",
            phone=f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            email=f"{first_name.lower()}.{last_name.lower()}@email.com",
            employment_status="Employed" if age < 65 and random.random() > 0.2 else "Retired"
        )
        
        # Generate insurance based on scenario
        patient.insurance_coverage = self._generate_insurance_for_scenario(
            patient, scenario
        )
        
        return patient
    
    def _generate_insurance_for_scenario(
        self, patient: Patient, scenario: str
    ) -> List[Insurance]:
        """Generate insurance coverage based on scenario type"""
        
        insurances = []
        base_date = date.today() - timedelta(days=365)  # Coverage started a year ago
        
        if scenario == "normal":
            # Single commercial insurance
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1
            ))
            
        elif scenario == "missing_secondary":
            # Has primary, missing secondary (spouse employment)
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1
            ))
            # Secondary exists but not in system (RED FLAG)
            
        elif scenario == "wrong_primary_order":
            # Two insurances with incorrect priority (RED FLAG)
            # Medicare should be secondary if patient is working
            insurances.append(self._create_insurance(
                InsuranceType.MEDICARE, base_date, None, True, 1  # WRONG
            ))
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, False, 2  # Should be primary
            ))
            
        elif scenario == "msp_violation":
            # Medicare billed as primary when it should be secondary
            insurances.append(self._create_insurance(
                InsuranceType.MEDICARE, base_date, None, True, 1  # WRONG - MSP violation
            ))
            
        elif scenario == "dependent_aging_out":
            # Dependent turned 26, coverage terminated but claim filed after
            term_date = date.today() - timedelta(days=60)  # Terminated 2 months ago
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, term_date, True, 1
            ))
            
        elif scenario == "dual_coverage":
            # Correct dual coverage
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1
            ))
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, False, 2
            ))
            
        elif scenario == "auto_accident":
            # Auto insurance should be primary for accident claims
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1  # WRONG
            ))
            insurances.append(self._create_insurance(
                InsuranceType.AUTO_INSURANCE, base_date, None, False, 2  # Should be primary
            ))
            
        elif scenario == "workers_comp":
            # Workers comp should be primary for work injuries
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1  # WRONG
            ))
            
        else:  # normal
            insurances.append(self._create_insurance(
                InsuranceType.COMMERCIAL, base_date, None, True, 1
            ))
            
        return insurances
    
    def _create_insurance(
        self, 
        ins_type: InsuranceType, 
        eff_date: date, 
        term_date: Optional[date],
        is_primary: bool,
        priority: int
    ) -> Insurance:
        """Create an insurance record"""
        
        payer = random.choice(self.payers[ins_type])
        
        return Insurance(
            insurance_id=f"INS{uuid.uuid4().hex[:8].upper()}",
            payer_name=payer,
            insurance_type=ins_type,
            policy_number=f"POL{random.randint(100000, 999999)}",
            group_number=f"GRP{random.randint(1000, 9999)}" if ins_type == InsuranceType.COMMERCIAL else None,
            subscriber_id=f"SUB{random.randint(100000000, 999999999)}",
            effective_date=eff_date,
            termination_date=term_date,
            is_primary=is_primary,
            priority_order=priority
        )
    
    def generate_claim(
        self, 
        patient: Patient, 
        claim_num: int,
        scenario: str = "normal"
    ) -> Claim:
        """Generate a claim with potential COB issues"""
        
        claim_id = f"CLM{claim_num:09d}"
        
        # Service date - recent
        service_date = date.today() - timedelta(days=random.randint(1, 90))
        
        # Determine claim characteristics based on scenario
        is_emergency = scenario in ["emergency", "auto_accident"]
        is_accident = scenario in ["auto_accident"]
        is_work_related = scenario == "workers_comp"
        
        # Select diagnosis codes
        if is_accident:
            dx_codes = random.sample(self.diagnosis_codes["accident"], 2)
        elif is_work_related:
            dx_codes = random.sample(self.diagnosis_codes["work_injury"], 2)
        elif is_emergency:
            dx_codes = random.sample(self.diagnosis_codes["emergency"], 2)
        else:
            dx_codes = random.sample(self.diagnosis_codes["routine"], 2)
        
        # Billed amount - VARIED to ensure mix in top 10 alerts (not just auto accidents)
        if is_emergency:
            billed_amount = random.uniform(25000, 85000)
        elif is_accident or is_work_related:
            # Auto/WC: high but not dominant
            billed_amount = random.uniform(15000, 50000)
        elif scenario == "msp_violation":
            # MSP: Increase significantly - often expensive procedures
            billed_amount = random.uniform(20000, 70000)
        elif scenario == "wrong_primary_order":
            # Wrong primary: Can be expensive specialty care
            billed_amount = random.uniform(15000, 55000)
        elif scenario == "dependent_aging_out":
            # Age-out: Often urgent care or procedures
            billed_amount = random.uniform(18000, 60000)
        elif scenario == "missing_secondary":
            # Missing secondary: Wide range
            billed_amount = random.uniform(5000, 35000)
        elif scenario == "dual_coverage":
            # Dual coverage: Medium to high
            billed_amount = random.uniform(10000, 40000)
        else:
            billed_amount = random.uniform(500, 5000)
        
        # Get insurance info
        active_insurance = patient.get_active_insurance(service_date)
        
        if scenario == "dependent_aging_out":
            # Claim filed after coverage terminated
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.DENIED
            denial_reason = DenialReason.DEPENDENT_ELIGIBILITY
        elif scenario == "msp_violation":
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.DENIED
            denial_reason = DenialReason.MSP_VIOLATION
        elif scenario == "wrong_primary_order":
            # Billed Medicare first when commercial should be primary
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.DENIED
            denial_reason = DenialReason.WRONG_PRIMARY
        elif scenario == "missing_secondary":
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.PAID
            denial_reason = None
            # But missing potential secondary recovery
        elif scenario in ["auto_accident", "workers_comp"]:
            # Wrong payer billed as primary
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.DENIED
            denial_reason = DenialReason.AUTO_LIABILITY if is_accident else DenialReason.WRONG_PRIMARY
        else:
            primary_ins_id = patient.insurance_coverage[0].insurance_id if patient.insurance_coverage else None
            status = ClaimStatus.PAID if random.random() > 0.3 else ClaimStatus.DENIED
            denial_reason = None if status == ClaimStatus.PAID else DenialReason.OTHER
        
        secondary_ins_id = None
        if len(patient.insurance_coverage) > 1:
            secondary_ins_id = patient.insurance_coverage[1].insurance_id
        
        submission_date = service_date + timedelta(days=random.randint(1, 14))
        denial_date = submission_date + timedelta(days=random.randint(7, 30)) if status == ClaimStatus.DENIED else None
        
        return Claim(
            claim_id=claim_id,
            patient_id=patient.patient_id,
            service_date=service_date,
            admission_date=service_date if is_emergency else None,
            discharge_date=service_date + timedelta(days=random.randint(1, 7)) if is_emergency else None,
            diagnosis_codes=dx_codes,
            procedure_codes=[f"CPT{random.randint(10000, 99999)}" for _ in range(random.randint(1, 4))],
            billed_amount=round(billed_amount, 2),
            primary_insurance_id=primary_ins_id,
            secondary_insurance_id=secondary_ins_id,
            claim_status=status,
            denial_reason=denial_reason,
            denial_date=denial_date,
            submission_date=submission_date,
            paid_amount=round(billed_amount * 0.7, 2) if status == ClaimStatus.PAID else 0.0,
            is_emergency=is_emergency,
            is_accident_related=is_accident,
            is_work_related=is_work_related,
            has_third_party_liability=is_accident or is_work_related
        )
    
    def generate_dataset(self, num_patients: int = 100) -> Tuple[List[Patient], List[Claim]]:
        """Generate a complete dataset with various COB scenarios"""
        
        patients = []
        claims = []
        
        # Scenario distribution - realistic 20% flag rate with VARIETY across all 8 types
        # Auto/WC reduced to prevent dominance in top 10 alerts
        scenarios = [
            ("normal", int(num_patients * 0.80)),           # 80% normal (no flags)
            ("missing_secondary", int(num_patients * 0.06)), # 6% - most common issue
            ("msp_violation", int(num_patients * 0.05)),     # 5% - common in Medicare
            ("wrong_primary_order", int(num_patients * 0.04)), # 4% - coordination errors
            ("dependent_aging_out", int(num_patients * 0.02)), # 2% - age 26 transitions
            ("dual_coverage", int(num_patients * 0.015)),     # 1.5% - secondary not billed
            ("auto_accident", int(num_patients * 0.005)),     # 0.5% - rare but high value
            ("workers_comp", int(num_patients * 0.005))       # 0.5% - rare but high value
        ]
        
        claim_counter = 1
        patient_counter = 1
        
        for scenario, count in scenarios:
            for _ in range(count):
                if patient_counter > num_patients:
                    break
                    
                patient = self.generate_patient(patient_counter, scenario)
                patients.append(patient)
                
                # Generate 1-3 claims per patient
                num_claims = random.randint(1, 3)
                for _ in range(num_claims):
                    claim = self.generate_claim(patient, claim_counter, scenario)
                    claims.append(claim)
                    claim_counter += 1
                
                patient_counter += 1
        
        return patients, claims
