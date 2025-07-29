from flask import Flask, render_template, request, jsonify, send_file, Response
import os
import json
import traceback
from datetime import datetime
import uuid
import logging
import gc
import time

# Use production settings
from config.settings_production import Config
from modules.genetic_scheduler_v2 import GeneticSchedulerV2 as GeneticScheduler
from modules.validators import InputValidator
from modules.data_handler import DataHandler
from modules.export_handler import ExportHandler
from modules.r1_scheduler import R1Scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Create necessary directories
os.makedirs('data/temp', exist_ok=True)

# Store running tasks
running_tasks = {}

# Add timeout decorator for long-running operations
def timeout_handler(func):
    """Decorator to handle timeouts in production"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        max_time = Config.MAX_PROCESSING_TIME
        
        # Check if we're getting close to timeout
        if time.time() - start_time > max_time - 2:
            logger.warning(f"Operation approaching timeout limit: {func.__name__}")
            # Force garbage collection
            gc.collect()
            
        return func(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    """Main scheduling interface"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': 'production',
        'max_processing_time': Config.MAX_PROCESSING_TIME,
        'ga_population_size': Config.GA_DEFAULT_POPULATION_SIZE,
        'ga_max_generations': Config.GA_DEFAULT_GENERATIONS
    }), 200

@app.route('/api/preview-r1', methods=['POST'])
@timeout_handler
def preview_r1_schedule():
    """Generate R1 and R4 pre-schedule for preview - optimized for production"""
    try:
        # Check if request contains JSON data
        if not request.is_json:
            logger.error("Request does not contain JSON data")
            return jsonify({
                'success': False,
                'error': 'Request must contain JSON data'
            }), 400
            
        data = request.json
        logger.info(f"Received preview-r1 request")
        
        # Validate input
        validator = InputValidator()
        validation_result = validator.validate_input(data)
        
        if not validation_result['valid']:
            logger.error(f"Validation failed: {validation_result['errors']}")
            return jsonify({
                'success': False,
                'error': validation_result['errors']
            }), 400
        
        # Parse personnel data
        personnel_data = DataHandler.parse_personnel_data(data)
        logger.info(f"Personnel counts - R1: {len(personnel_data.get('R1', {}))}, R4: {len(personnel_data.get('R4', {}))}")
        
        # Quick memory cleanup before processing
        gc.collect()
        
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
        logger.info(f"Generating R1 schedule for {len(r1_personnel)} R1 personnel")
        r1_scheduler = R1Scheduler(r1_personnel)
        r1_assignments = r1_scheduler.schedule_all_r1_clinics()
        r1_fixed_schedule = r1_scheduler.create_fixed_r1_schedule(r1_assignments)
        logger.info(f"R1 schedule generated successfully")
        
        # Generate health check assignments for 健康 unit
        health_check_assignments = {}
        for person in r1_personnel:
            if person['rotation_unit'] == '健康':
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
            if 'fixed_schedule' in person_data and person_data['fixed_schedule'] is not None:
                fixed = person_data['fixed_schedule']
                if isinstance(fixed, dict) and 'day' in fixed and 'time_slot' in fixed:
                    r4_fixed_schedules[person_id] = {
                        'day': fixed['day'],
                        'time': fixed['time_slot'],
                        'room': fixed.get('room', None),
                        'person_info': {
                            'id': person_id,
                            'name': person_data.get('name', ''),
                            'level': 'R4',
                            'rotation_unit': person_data['rotation_unit']
                        }
                    }
            elif not person_data.get('teaching_exempt', False):
                # Non-exempt R4s have Tuesday teaching
                r4_fixed_schedules[person_id] = {
                    'day': 'Tuesday',
                    'time': 'Both',
                    'room': 'R4教學',
                    'person_info': {
                        'id': person_id,
                        'name': person_data.get('name', ''),
                        'level': 'R4',
                        'rotation_unit': person_data['rotation_unit']
                    }
                }
        
        # Clean up memory
        gc.collect()
        
        return jsonify({
            'success': True,
            'r1_schedule': r1_schedule,
            'r1_personnel': r1_personnel,
            'r4_fixed_schedules': r4_fixed_schedules
        })
        
    except Exception as e:
        logger.error(f"Error in preview_r1_schedule: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error generating R1/R4 preview: {str(e)}'
        }), 500

@app.route('/api/schedule-with-r1', methods=['POST'])
@timeout_handler
def generate_schedule_with_r1():
    """Generate schedule with modified R1 assignments - production optimized"""
    try:
        if not request.is_json:
            logger.error("Request does not contain JSON data")
            return jsonify({
                'success': False,
                'error': 'Request must contain JSON data'
            }), 400
            
        data = request.json
        logger.info("Received schedule-with-r1 request")
        
        # Quick memory cleanup
        gc.collect()
        
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
        total_personnel = sum(len(level_data) for level_data in personnel_data.values())
        logger.info(f"Total personnel count: {total_personnel}")
        
        # Load rules
        with open('data/rules.json', 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        # Get optimized GA config based on personnel count
        ga_config = Config.get_ga_config(total_personnel)
        logger.info(f"Using GA config: population={ga_config['population_size']}, generations={ga_config['max_generations']}")
        
        # Initialize genetic scheduler with production settings
        scheduler = GeneticScheduler(
            personnel_data=personnel_data,
            rules=rules,
            config=ga_config  # Pass the optimized config
        )
        
        # Override R1 assignments with user modifications
        if r1_schedule and 'clinic_assignments' in r1_schedule:
            modified_r1_assignments = {}
            for person_id, assignment in r1_schedule['clinic_assignments'].items():
                day = assignment['day']
                room = assignment['room']
                modified_r1_assignments[person_id] = (day, room)
            
            scheduler.r1_assignments = modified_r1_assignments
            r1_scheduler = R1Scheduler(scheduler.personnel_list)
            scheduler.r1_fixed_schedule = r1_scheduler.create_fixed_r1_schedule(modified_r1_assignments)
        
        # Override R4 fixed schedules
        if r4_fixed_schedules:
            scheduler.r4_fixed_schedule = scheduler._create_r4_fixed_schedule()
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        running_tasks[task_id] = {'status': 'running', 'progress': 0}
        
        # Run genetic algorithm with timeout monitoring
        start_time = time.time()
        result = scheduler.run()
        execution_time = time.time() - start_time
        logger.info(f"GA execution completed in {execution_time:.2f} seconds")
        
        if result['success']:
            # Generate export files
            exporter = ExportHandler(result['schedule'], personnel_data)
            
            # Generate all CSV formats
            basic_csv = exporter.generate_basic_csv()
            personal_csv = exporter.generate_personal_csv()
            statistics_csv = exporter.generate_statistics_csv()
            
            # Save files
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
            
            # Clean up memory
            gc.collect()
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'schedule': result['schedule'],
                'statistics': result['statistics'],
                'files': {
                    'basic': f"basic_schedule_{timestamp}.csv",
                    'personal': f"personal_schedule_{timestamp}.csv",
                    'statistics': f"statistics_{timestamp}.csv"
                },
                'execution_time': execution_time
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
        logger.error(f"Error in generate_schedule_with_r1: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'System error: {str(e)}'
        }), 500

# Include all other routes from the original app.py...
# (download_file, download_zip, validate_input, etc.)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # In production, use gunicorn instead of Flask's built-in server
    app.run(host='0.0.0.0', port=port, debug=False)