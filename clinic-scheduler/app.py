from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import traceback
from datetime import datetime
import uuid

from config.settings import Config
from modules.genetic_scheduler_v2 import GeneticSchedulerV2 as GeneticScheduler
from modules.validators import InputValidator
from modules.data_handler import DataHandler
from modules.export_handler import ExportHandler
from modules.r1_scheduler import R1Scheduler

app = Flask(__name__)
app.config.from_object(Config)

# Create necessary directories
os.makedirs('data/temp', exist_ok=True)

# Store running tasks
running_tasks = {}

@app.route('/')
def index():
    """Main scheduling interface"""
    return render_template('index.html')

@app.route('/api/schedule', methods=['POST'])
def generate_schedule():
    """Generate schedule using genetic algorithm"""
    try:
        data = request.json
        
        # Validate input
        validator = InputValidator()
        validation_result = validator.validate_input(data)
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['errors']
            }), 400
        
        # Parse personnel data
        personnel_data = DataHandler.parse_personnel_data(data)
        
        # Load rules
        with open('data/rules.json', 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        # Initialize genetic scheduler
        scheduler = GeneticScheduler(
            personnel_data=personnel_data,
            rules=rules
        )
        
        # Generate task ID for progress tracking
        task_id = str(uuid.uuid4())
        running_tasks[task_id] = {'status': 'running', 'progress': 0}
        
        # Run genetic algorithm
        result = scheduler.run()
        
        if result['success']:
            # Generate export files
            exporter = ExportHandler(result['schedule'], personnel_data)
            
            # Generate all CSV formats
            basic_csv = exporter.generate_basic_csv()
            personal_csv = exporter.generate_personal_csv()
            statistics_csv = exporter.generate_statistics_csv()
            
            # Save files temporarily
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            basic_path = f"data/temp/basic_schedule_{timestamp}.csv"
            personal_path = f"data/temp/personal_schedule_{timestamp}.csv"
            statistics_path = f"data/temp/statistics_{timestamp}.csv"
            
            with open(basic_path, 'w', encoding='utf-8-sig') as f:
                f.write(basic_csv)
            with open(personal_path, 'w', encoding='utf-8-sig') as f:
                f.write(personal_csv)
            with open(statistics_path, 'w', encoding='utf-8-sig') as f:
                f.write(statistics_csv)
            
            running_tasks[task_id] = {
                'status': 'completed',
                'progress': 100,
                'files': {
                    'basic': basic_path,
                    'personal': personal_path,
                    'statistics': statistics_path
                }
            }
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'schedule': result['schedule'],
                'statistics': result['statistics'],
                'files': {
                    'basic': f"basic_schedule_{timestamp}.csv",
                    'personal': f"personal_schedule_{timestamp}.csv",
                    'statistics': f"statistics_{timestamp}.csv"
                }
            })
        else:
            running_tasks[task_id] = {
                'status': 'failed',
                'error': result['error']
            }
            
            return jsonify({
                'success': False,
                'task_id': task_id,
                'error': result['error'],
                'details': result.get('details', {})
            }), 400
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        }), 500

@app.route('/api/download/<format>/<filename>')
def download_file(format, filename):
    """Download specific CSV format"""
    try:
        file_path = f"data/temp/{filename}"
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/zip/<task_id>')
def download_zip(task_id):
    """Download all files as ZIP"""
    try:
        if task_id not in running_tasks or running_tasks[task_id]['status'] != 'completed':
            return jsonify({'error': 'Task not found or not completed'}), 404
        
        files = running_tasks[task_id]['files']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create ZIP file
        exporter = ExportHandler(None, None)
        zip_path = exporter.create_zip_bundle(files, timestamp)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"clinic_schedule_{timestamp}.zip",
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate', methods=['POST'])
def validate_input():
    """Real-time validation endpoint"""
    try:
        data = request.json
        validator = InputValidator()
        result = validator.validate_partial(data)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/progress/<task_id>')
def check_progress(task_id):
    """Check genetic algorithm progress"""
    if task_id not in running_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(running_tasks[task_id])

@app.route('/api/personnel/update', methods=['POST'])
def update_personnel():
    """Update personnel count dynamically"""
    try:
        data = request.json
        level = data.get('level')
        count = data.get('count')
        
        if level not in ['R1', 'R2', 'R3', 'R4']:
            return jsonify({'error': 'Invalid level'}), 400
        
        if not isinstance(count, int) or count < 1 or count > 10:
            return jsonify({'error': 'Invalid count'}), 400
        
        return jsonify({
            'success': True,
            'level': level,
            'count': count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview-r1', methods=['POST'])
def preview_r1_schedule():
    """Generate R1 and R4 pre-schedule for preview and modification"""
    try:
        data = request.json
        
        # Validate input
        validator = InputValidator()
        validation_result = validator.validate_input(data)
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['errors']
            }), 400
        
        # Parse personnel data
        personnel_data = DataHandler.parse_personnel_data(data)
        
        # Get R1 personnel only
        r1_personnel = []
        for person_id, person_data in personnel_data.get('R1', {}).items():
            r1_personnel.append({
                'id': person_id,
                'name': person_data.get('name', ''),
                'level': 'R1',
                'rotation_unit': person_data['rotation_unit'],
                'health_check': person_data.get('health_check', False)
            })
        
        # Generate R1 pre-schedule
        r1_scheduler = R1Scheduler(r1_personnel)
        r1_assignments = r1_scheduler.schedule_all_r1_clinics()
        r1_fixed_schedule = r1_scheduler.create_fixed_r1_schedule(r1_assignments)
        
        # Also generate health check assignments for 健康 unit
        health_check_assignments = {}
        for person in r1_personnel:
            if person['rotation_unit'] == '健康':
                # Fixed health check schedule for 健康 R1
                health_check_assignments[person['id']] = [
                    {'day': 'Monday', 'time': 'Morning', 'room': '體檢1'},
                    {'day': 'Tuesday', 'time': 'Morning', 'room': '體檢1'},
                    {'day': 'Tuesday', 'time': 'Afternoon', 'room': '體檢1'},
                    {'day': 'Wednesday', 'time': 'Afternoon', 'room': '體檢1'},
                    {'day': 'Thursday', 'time': 'Morning', 'room': '體檢1'},
                    {'day': 'Thursday', 'time': 'Afternoon', 'room': '體檢1'},
                    {'day': 'Friday', 'time': 'Morning', 'room': '體檢1'},
                    {'day': 'Friday', 'time': 'Afternoon', 'room': '體檢1'}
                ]
        
        # Convert to frontend-friendly format
        r1_schedule = {
            'clinic_assignments': {},
            'health_check_assignments': health_check_assignments
        }
        
        for person_id, (day, room) in r1_assignments.items():
            r1_schedule['clinic_assignments'][person_id] = {
                'day': day,
                'time': 'Afternoon',
                'room': room,
                'person_info': next((p for p in r1_personnel if p['id'] == person_id), None)
            }
        
        # Get R4 fixed schedules
        r4_fixed_schedules = {}
        for person_id, person_data in personnel_data.get('R4', {}).items():
            if 'fixed_schedule' in person_data:
                fixed = person_data['fixed_schedule']
                r4_fixed_schedules[person_id] = {
                    'day': fixed['day'],
                    'time': fixed['time_slot'],
                    'room': fixed.get('room', None),  # Use specified room if available
                    'person_info': {
                        'id': person_id,
                        'name': person_data.get('name', ''),
                        'level': 'R4',
                        'rotation_unit': person_data['rotation_unit']
                    }
                }
        
        return jsonify({
            'success': True,
            'r1_schedule': r1_schedule,
            'r1_personnel': r1_personnel,
            'r4_fixed_schedules': r4_fixed_schedules
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Error generating R1/R4 preview: {str(e)}'
        }), 500

@app.route('/api/schedule-with-r1', methods=['POST'])
def generate_schedule_with_r1():
    """Generate schedule with modified R1 assignments"""
    try:
        data = request.json
        r1_schedule = data.get('r1_schedule', {})
        r4_fixed_schedules = data.get('r4_fixed_schedules', {})
        
        # Validate input
        validator = InputValidator()
        validation_result = validator.validate_input(data)
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['errors']
            }), 400
        
        # Parse personnel data
        personnel_data = DataHandler.parse_personnel_data(data)
        
        # Load rules
        with open('data/rules.json', 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        # Initialize genetic scheduler
        scheduler = GeneticScheduler(
            personnel_data=personnel_data,
            rules=rules
        )
        
        # Override R1 assignments with user modifications
        if r1_schedule and 'clinic_assignments' in r1_schedule:
            # Convert user-modified R1 assignments back to scheduler format
            modified_r1_assignments = {}
            for person_id, assignment in r1_schedule['clinic_assignments'].items():
                day = assignment['day']
                room = assignment['room']
                modified_r1_assignments[person_id] = (day, room)
            
            # Update scheduler with modified assignments
            scheduler.r1_assignments = modified_r1_assignments
            r1_scheduler = R1Scheduler(scheduler.personnel_list)
            scheduler.r1_fixed_schedule = r1_scheduler.create_fixed_r1_schedule(modified_r1_assignments)
        
        # Override R4 fixed schedules if any modifications were made
        if r4_fixed_schedules:
            # R4 fixed schedules are already in the correct format from frontend
            # Just need to ensure they are properly set in the scheduler
            scheduler.r4_fixed_schedule = scheduler._create_r4_fixed_schedule()
        
        # Generate task ID for progress tracking
        task_id = str(uuid.uuid4())
        running_tasks[task_id] = {'status': 'running', 'progress': 0}
        
        # Run genetic algorithm with modified R1 assignments
        result = scheduler.run()
        
        if result['success']:
            # Generate export files
            exporter = ExportHandler(result['schedule'], personnel_data)
            
            # Generate all CSV formats
            basic_csv = exporter.generate_basic_csv()
            personal_csv = exporter.generate_personal_csv()
            statistics_csv = exporter.generate_statistics_csv()
            
            # Save files temporarily
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            basic_path = f"data/temp/basic_schedule_{timestamp}.csv"
            personal_path = f"data/temp/personal_schedule_{timestamp}.csv"
            statistics_path = f"data/temp/statistics_{timestamp}.csv"
            
            with open(basic_path, 'w', encoding='utf-8-sig') as f:
                f.write(basic_csv)
            with open(personal_path, 'w', encoding='utf-8-sig') as f:
                f.write(personal_csv)
            with open(statistics_path, 'w', encoding='utf-8-sig') as f:
                f.write(statistics_csv)
            
            running_tasks[task_id] = {
                'status': 'completed',
                'progress': 100,
                'files': {
                    'basic': basic_path,
                    'personal': personal_path,
                    'statistics': statistics_path
                }
            }
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'schedule': result['schedule'],
                'statistics': result['statistics'],
                'files': {
                    'basic': f"basic_schedule_{timestamp}.csv",
                    'personal': f"personal_schedule_{timestamp}.csv",
                    'statistics': f"statistics_{timestamp}.csv"
                }
            })
        else:
            running_tasks[task_id] = {
                'status': 'failed',
                'error': result['error']
            }
            
            return jsonify({
                'success': False,
                'task_id': task_id,
                'error': result['error'],
                'details': result.get('details', {})
            }), 400
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)