"""
Sightline Health - COB Agent Web Demo
Flask application for browser-based demonstration
"""

from flask import Flask, render_template, jsonify, request
import sys
import os

# Get the absolute path to the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add parent directory to path to import our modules
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from synthetic_data import SyntheticDataGenerator
from cob_agent import COBAgent
from data_models import Patient, Claim

# Initialize Flask with explicit template folder
template_dir = os.path.join(current_dir, 'templates')
app = Flask(__name__, template_folder=template_dir)

# Global variables to store demo state
demo_data = {
    'patients': [],
    'claims': [],
    'results': None,
    'agent': None
}


def initialize_demo(num_patients=100, seed=42):
    """Initialize the demo with synthetic data"""
    global demo_data
    
    # Generate data
    generator = SyntheticDataGenerator(seed=seed)
    patients_list, claims_list = generator.generate_dataset(num_patients=num_patients)
    
    # Store data
    demo_data['patients'] = patients_list
    demo_data['claims'] = claims_list
    demo_data['patients_dict'] = {p.patient_id: p for p in patients_list}
    
    # Initialize agent
    demo_data['agent'] = COBAgent()
    
    return len(patients_list), len(claims_list)


def run_analysis():
    """Run the COB agent analysis"""
    global demo_data
    
    if not demo_data['agent']:
        initialize_demo()
    
    # Process claims
    results = demo_data['agent'].process_claims_batch(
        demo_data['claims'],
        demo_data['patients_dict']
    )
    
    demo_data['results'] = results
    return results


@app.route('/')
def index():
    """Main demo page"""
    return render_template('index.html')


@app.route('/debug')
def debug():
    """Debug endpoint to check file structure"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    return jsonify({
        'current_dir': current_dir,
        'parent_dir': parent_dir,
        'template_folder': app.template_folder,
        'files_in_current': os.listdir(current_dir),
        'files_in_parent': os.listdir(parent_dir) if os.path.exists(parent_dir) else [],
        'templates_exists': os.path.exists(os.path.join(current_dir, 'templates')),
        'templates_contents': os.listdir(os.path.join(current_dir, 'templates')) if os.path.exists(os.path.join(current_dir, 'templates')) else []
    })


@app.route('/api/initialize', methods=['POST'])
def api_initialize():
    """Initialize demo with specified parameters"""
    data = request.get_json()
    num_patients = data.get('num_patients', 100)
    seed = data.get('seed', 42)
    
    num_patients_created, num_claims_created = initialize_demo(num_patients, seed)
    
    return jsonify({
        'success': True,
        'num_patients': num_patients_created,
        'num_claims': num_claims_created,
        'message': f'Generated {num_patients_created} patients with {num_claims_created} claims'
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Run the COB analysis"""
    results = run_analysis()
    
    # Convert results to JSON-serializable format
    summary = results['processing_summary']
    daily_report = results['daily_report']
    
    # Filter top alerts to only high-value (>$25K) and limit to top 50
    high_value_alerts = [
        alert for alert in results['top_priority_alerts'] 
        if (alert.estimated_recovery or 0) > 25000
    ][:50]  # Top 50 high-value alerts for pagination
    
    # Top alerts with patient and claim info
    top_alerts = []
    for alert in high_value_alerts:
        patient = demo_data['patients_dict'][alert.patient_id]
        claim = next(c for c in demo_data['claims'] if c.claim_id == alert.claim_id)
        
        top_alerts.append({
            'alert_id': alert.alert_id,
            'alert_type': alert.alert_type,
            'severity': alert.severity,
            'confidence': round(alert.confidence_score * 100, 1),
            'estimated_recovery': round(alert.estimated_recovery or 0, 2),
            'description': alert.description,
            'recommended_action': alert.recommended_action,
            'patient': {
                'id': patient.patient_id,
                'name': f"{patient.first_name} {patient.last_name}",
                'age': patient.get_age(),
                'mrn': patient.mrn
            },
            'claim': {
                'id': claim.claim_id,
                'service_date': str(claim.service_date),
                'billed_amount': round(claim.billed_amount, 2),
                'status': claim.claim_status.value,
                'carc_code': claim.carc_code,
                'rarc_code': claim.rarc_code
            }
        })
    
    return jsonify({
        'success': True,
        'summary': {
            'claims_processed': summary['claims_processed'],
            'alerts_generated': summary['alerts_generated'],
            'high_priority_alerts': summary['high_priority_alerts'],
            'high_value_alerts': len(high_value_alerts),  # Count of >$25K alerts
            'outreach_initiated': summary['outreach_initiated'],
            'workflows_created': summary['workflows_created'],
            'total_potential_recovery': round(summary['total_potential_recovery'], 2)
        },
        'alerts_by_type': daily_report['alerts_by_type'],
        'top_alerts': top_alerts,
        'total_pages': (len(top_alerts) + 9) // 10  # 10 alerts per page
    })


@app.route('/api/alert/<alert_id>')
def api_get_alert(alert_id):
    """Get detailed information about a specific alert"""
    if not demo_data['results']:
        return jsonify({'success': False, 'error': 'No analysis run yet'})
    
    # Find the alert
    alert = None
    for a in demo_data['results']['top_priority_alerts']:
        if a.alert_id == alert_id:
            alert = a
            break
    
    if not alert:
        return jsonify({'success': False, 'error': 'Alert not found'})
    
    # Get patient and claim
    patient = demo_data['patients_dict'][alert.patient_id]
    claim = next(c for c in demo_data['claims'] if c.claim_id == alert.claim_id)
    
    # Get workflow if exists
    workflow = None
    for w in demo_data['agent'].resolution_agent.workflows:
        if w.alert_id == alert_id:
            workflow = demo_data['agent'].resolution_agent.get_workflow_status(w.workflow_id)
            break
    
    # Get outreach if exists
    outreach = None
    for o in demo_data['agent'].outreach_agent.outreach_attempts:
        if o.alert_id == alert_id:
            outreach = {
                'attempt_id': o.attempt_id,
                'channel': o.channel,
                'timestamp': str(o.timestamp),
                'message': o.message_sent
            }
            break
    
    return jsonify({
        'success': True,
        'alert': {
            'id': alert.alert_id,
            'type': alert.alert_type,
            'severity': alert.severity,
            'confidence': round(alert.confidence_score * 100, 1),
            'estimated_recovery': round(alert.estimated_recovery or 0, 2),
            'description': alert.description,
            'recommended_action': alert.recommended_action,
            'data_points': alert.data_points
        },
        'patient': {
            'id': patient.patient_id,
            'mrn': patient.mrn,
            'name': f"{patient.first_name} {patient.last_name}",
            'dob': str(patient.date_of_birth),
            'age': patient.get_age(),
            'employment': patient.employment_status,
            'insurance_count': len(patient.insurance_coverage)
        },
        'claim': {
            'id': claim.claim_id,
            'service_date': str(claim.service_date),
            'billed_amount': round(claim.billed_amount, 2),
            'paid_amount': round(claim.paid_amount, 2),
            'status': claim.claim_status.value,
            'diagnosis_codes': claim.diagnosis_codes,
            'is_emergency': claim.is_emergency,
            'is_accident': claim.is_accident_related,
            'is_work_related': claim.is_work_related
        },
        'workflow': workflow,
        'outreach': outreach
    })


@app.route('/api/stats')
def api_stats():
    """Get current demo statistics"""
    if not demo_data['results']:
        return jsonify({
            'success': False,
            'initialized': len(demo_data['patients']) > 0,
            'analyzed': False
        })
    
    dashboard = demo_data['agent'].get_dashboard_metrics()
    
    return jsonify({
        'success': True,
        'initialized': True,
        'analyzed': True,
        'dashboard': dashboard
    })


if __name__ == '__main__':
    # Initialize with default data - 500 patients for realistic demo
    print("Initializing COB Agent Web Demo...")
    initialize_demo(500, 42)
    print("Demo initialized with 500 patients")
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)
