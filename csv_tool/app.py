"""
COB Agent - Web-Based CSV Analysis Tool
Upload CSV, analyze, and export report
"""

from flask import Flask, render_template, request, jsonify, send_file
import csv
from datetime import datetime
from collections import defaultdict
import io
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Store results in memory for download
analysis_results = {}


class COBAnalyzer:
    """Analyzes CSV data for COB issues"""
    
    def __init__(self):
        self.results = {
            'total_records': 0,
            'total_flagged': 0,
            'reactive_count': 0,
            'proactive_count': 0,
            'by_issue_type': defaultdict(int),
            'by_payer': defaultdict(int),
            'by_facility': defaultdict(int),
            'total_recovery': 0,
            'high_priority_count': 0,
            'medium_priority_count': 0,
            'low_priority_count': 0,
            'flagged_records': []
        }
    
    def analyze_csv(self, file_content):
        """Main analysis function"""
        # Read CSV using built-in csv module
        csv_reader = csv.DictReader(io.StringIO(file_content))
        rows = list(csv_reader)
        self.results['total_records'] = len(rows)
        
        # Analyze each record
        for idx, row in enumerate(rows):
            self._analyze_record(row, idx)
        
        return self.results
    
    def _analyze_record(self, row, idx):
        """Analyze single record"""
        # Safe get with default empty string
        def safe_get(key, default=''):
            val = row.get(key, default)
            return val if val and str(val).strip() else default
        
        carc = safe_get('Denial Code (CARC)')
        has_carc = bool(carc)
        
        if has_carc:
            # REACTIVE
            self.results['reactive_count'] += 1
            issue_type = self._map_carc_to_issue(carc)
            
            denial_amt = safe_get('Denial Amount')
            ins_bal = safe_get('Insurance Balance')
            pat_bal = safe_get('Patient Balance')
            
            flagged_record = {
                'row_number': idx + 2,
                'name': safe_get('Name'),
                'dob': safe_get('DOB'),
                'age': self._calculate_age(safe_get('DOB')),
                'insurance': safe_get('Insurance'),
                'insurance_id': safe_get('Insurance ID'),
                'account_id': safe_get('Account ID'),
                'detection_method': 'Reactive (835 Remittance)',
                'issue_type': issue_type,
                'carc_code': carc,
                'rarc_code': safe_get('Remark Code (RARC)'),
                'denial_amount': float(denial_amt) if denial_amt else 0,
                'insurance_balance': float(ins_bal) if ins_bal else 0,
                'patient_balance': float(pat_bal) if pat_bal else 0,
                'facility': safe_get('Facility Location'),
                'recovery_potential': self._calculate_recovery(row, True),
                'recommended_action': self._get_action_for_carc(carc),
                'priority': self._calculate_priority(row, True)
            }
        else:
            # PROACTIVE
            issue_type = self._detect_proactive_issue(row)
            if not issue_type:
                return
            
            self.results['proactive_count'] += 1
            
            ins_bal = safe_get('Insurance Balance')
            pat_bal = safe_get('Patient Balance')
            
            flagged_record = {
                'row_number': idx + 2,
                'name': safe_get('Name'),
                'dob': safe_get('DOB'),
                'age': self._calculate_age(safe_get('DOB')),
                'insurance': safe_get('Insurance'),
                'insurance_id': safe_get('Insurance ID'),
                'account_id': safe_get('Account ID'),
                'detection_method': 'Proactive (Pre-Submission)',
                'issue_type': issue_type,
                'carc_code': '',
                'rarc_code': '',
                'denial_amount': 0,
                'insurance_balance': float(ins_bal) if ins_bal else 0,
                'patient_balance': float(pat_bal) if pat_bal else 0,
                'facility': safe_get('Facility Location'),
                'recovery_potential': self._calculate_recovery(row, False),
                'recommended_action': self._get_proactive_action(issue_type, row),
                'priority': self._calculate_priority(row, False)
            }
        
        # Track priority counts
        if flagged_record['priority'] == 'HIGH':
            self.results['high_priority_count'] += 1
        elif flagged_record['priority'] == 'MEDIUM':
            self.results['medium_priority_count'] += 1
        else:
            self.results['low_priority_count'] += 1
        
        # Add to results
        self.results['total_flagged'] += 1
        self.results['by_issue_type'][issue_type] += 1
        self.results['by_payer'][row.get('Insurance', 'Unknown')] += 1
        self.results['by_facility'][row.get('Facility Location', 'Unknown')] += 1
        self.results['total_recovery'] += flagged_record['recovery_potential']
        self.results['flagged_records'].append(flagged_record)
    
    def _map_carc_to_issue(self, carc_code):
        """Map CARC code to issue type"""
        mapping = {
            '109': 'Wrong Payer / Not Covered',
            '119': 'COB - Other Coverage Exists',
            '197': 'Authorization Missing',
            'B7': 'Service Not Covered',
            '16': 'Missing Information',
            '97': 'Duplicate/Prior Adjudication',
            '204': 'Service Not Covered',
            '22': 'COB - Coordination Required',
            '26': 'Coverage Terminated'
        }
        return mapping.get(carc_code, f'Other Issue (CARC {carc_code})')
    
    def _detect_proactive_issue(self, row):
        """Detect proactive COB issues"""
        insurance = str(row.get('Insurance', '')).lower()
        age = self._calculate_age(row.get('DOB', ''))
        
        patient_balance = row.get('Patient Balance', '')
        insurance_balance = row.get('Insurance Balance', '')
        
        patient_balance = float(patient_balance) if patient_balance else 0
        insurance_balance = float(insurance_balance) if insurance_balance else 0
        total_charges = patient_balance + insurance_balance
        
        facility = str(row.get('Facility Location', '')).lower()
        
        # MSP VIOLATION
        if 'medicare' in insurance and 65 <= age <= 70:
            return 'MSP Violation - Working Senior'
        
        # MISSING SECONDARY
        if total_charges > 0 and (patient_balance / total_charges) > 0.30:
            return 'Missing Secondary Insurance'
        
        # AUTO/LIABILITY
        if 'urgent care' in facility and total_charges > 15000:
            return 'Potential Auto/Liability'
        
        return None
    
    def _calculate_age(self, dob_str):
        """Calculate age from DOB"""
        try:
            dob = datetime.strptime(str(dob_str), '%Y-%m-%d')
            today = datetime.now()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age
        except:
            return 0
    
    def _calculate_recovery(self, row, is_reactive):
        """Estimate recovery potential"""
        if is_reactive:
            denial_amount = row.get('Denial Amount', '')
            denial_amount = float(denial_amount) if denial_amount else 0
            return denial_amount * 0.75
        else:
            insurance_balance = row.get('Insurance Balance', '')
            insurance_balance = float(insurance_balance) if insurance_balance else 0
            return insurance_balance * 0.65
    
    def _calculate_priority(self, row, is_reactive):
        """Calculate priority level"""
        recovery = self._calculate_recovery(row, is_reactive)
        if recovery > 25000:
            return 'HIGH'
        elif recovery > 10000:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_action_for_carc(self, carc_code):
        """Get recommended action for CARC code"""
        actions = {
            '109': 'Verify correct payer and rebill',
            '119': 'Request COB info from patient and rebill with correct primary',
            '197': 'Obtain prior authorization and resubmit',
            'B7': 'Review coverage policy and rebill to appropriate payer',
            '16': 'Complete missing information and resubmit',
            '97': 'Check for duplicate billing and adjust',
            '204': 'Review medical necessity and coverage criteria',
            '22': 'Update COB information and rebill',
            '26': 'Verify active coverage dates'
        }
        return actions.get(carc_code, 'Review denial and take corrective action')
    
    def _get_proactive_action(self, issue_type, row):
        """Get action for proactive detection"""
        if 'MSP' in issue_type:
            return 'Contact patient to verify employment and employer coverage before submission'
        elif 'Missing Secondary' in issue_type:
            return 'Contact patient to verify spouse/dependent coverage'
        elif 'Auto/Liability' in issue_type:
            return 'Contact patient to verify if accident-related and obtain auto insurance'
        else:
            return 'Review claim for COB issues'


@app.route('/')
def index():
    """Main upload page"""
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle CSV upload and analysis"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Please upload a CSV file'})
    
    try:
        # Read file content
        file_content = file.read().decode('utf-8')
        
        # Analyze
        analyzer = COBAnalyzer()
        results = analyzer.analyze_csv(file_content)
        
        # Store results for download
        analysis_results['latest'] = results
        
        # Format response
        summary = {
            'total_records': results['total_records'],
            'total_flagged': results['total_flagged'],
            'reactive_count': results['reactive_count'],
            'proactive_count': results['proactive_count'],
            'total_recovery': round(results['total_recovery'], 2),
            'avg_recovery': round(results['total_recovery'] / max(results['total_flagged'], 1), 2),
            'high_priority': results['high_priority_count'],
            'medium_priority': results['medium_priority_count'],
            'low_priority': results['low_priority_count'],
            'by_issue_type': dict(sorted(results['by_issue_type'].items(), key=lambda x: x[1], reverse=True)),
            'top_payers': dict(sorted(results['by_payer'].items(), key=lambda x: x[1], reverse=True)[:10])
        }
        
        return jsonify({'success': True, 'summary': summary})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/download')
def download_report():
    """Download detailed analysis report"""
    if 'latest' not in analysis_results:
        return "No analysis results available", 400
    
    results = analysis_results['latest']
    
    if not results['flagged_records']:
        return "No flagged records to export", 400
    
    # Sort by priority and recovery
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    sorted_records = sorted(
        results['flagged_records'],
        key=lambda x: (priority_order.get(x['priority'], 3), -x['recovery_potential'])
    )
    
    # Create CSV in memory using csv.DictWriter
    output = io.StringIO()
    if sorted_records:
        fieldnames = sorted_records[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_records)
    
    output.seek(0)
    
    # Convert to bytes for download
    mem = io.BytesIO()
    mem.write(output.getvalue().encode())
    mem.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'COB_Analysis_Report_{timestamp}.csv'
    
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    print("="*80)
    print("COB AGENT - WEB ANALYSIS TOOL")
    print("="*80)
    print("\nStarting server...")
    print("\nReady to analyze CSV files!")
    print("="*80 + "\n")
    
    # Use PORT from environment variable for Render, default to 5001 for local
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
