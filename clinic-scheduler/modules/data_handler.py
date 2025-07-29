import pandas as pd
import json
import csv
from typing import Dict, List, Any
from io import StringIO
from config.settings import Config

class DataHandler:
    """Handle data parsing and CSV operations"""
    
    @staticmethod
    def parse_personnel_data(raw_data: Dict[str, Any]) -> Dict[str, Dict]:
        """Parse raw input data into structured personnel data"""
        personnel_data = {}
        
        # Extract personnel information
        raw_personnel = raw_data.get('personnel', {})
        
        for level, people in raw_personnel.items():
            if level not in personnel_data:
                personnel_data[level] = {}
                
            for person_id, person_info in people.items():
                personnel_data[level][person_id] = {
                    'name': person_info.get('name', ''),
                    'rotation_unit': person_info.get('rotation_unit', ''),
                    'health_check': person_info.get('health_check', False),
                    'tuesday_teaching': person_info.get('tuesday_teaching', False),
                    'fixed_schedule': person_info.get('fixed_schedule', None)
                }
        
        return personnel_data
    
    @staticmethod
    def load_rules_from_json(file_path: str) -> Dict[str, Any]:
        """Load scheduling rules from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return default rules if file not found
            return DataHandler.get_default_rules()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rules file: {str(e)}")
    
    @staticmethod
    def get_default_rules() -> Dict[str, Any]:
        """Get default scheduling rules"""
        return {
            "unit_constraints": {
                "健康": {
                    "min_clinics": 0,
                    "max_clinics": 2,
                    "health_check_required": True,
                    "description": "主要負責體檢，門診數量有限"
                },
                "急診": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "preferred_time": "Morning",
                    "description": "急診輪訓，需保留時間處理急診業務"
                },
                "內科病房": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "一般門診負擔"
                },
                "兒科病房": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "一般門診負擔"
                },
                "精神1": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "精神科訓練"
                },
                "精神2": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "精神科訓練"
                },
                "社區1": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "社區醫學訓練"
                },
                "社區2": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "社區醫學訓練"
                },
                "婦產病房": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "一般門診負擔"
                },
                "婦產門診": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "婦產科門診"
                },
                "放射": {
                    "min_clinics": 0,
                    "max_clinics": 2,
                    "description": "放射科訓練，門診時間有限"
                },
                "CR": {
                    "min_clinics": 2,
                    "max_clinics": 4,
                    "description": "心臟復健"
                },
                "斗六1": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "斗六分院支援"
                },
                "斗六2": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "斗六分院支援"
                },
                "安寧1": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "安寧療護訓練"
                },
                "安寧2": {
                    "min_clinics": 1,
                    "max_clinics": 3,
                    "description": "安寧療護訓練"
                },
                "其他": {
                    "min_clinics": 2,
                    "max_clinics": 5,
                    "description": "彈性安排"
                }
            },
            "general_rules": {
                "max_clinics_per_day": 2,
                "max_clinics_per_week": 8,
                "min_rest_between_clinics": 0,
                "health_check_priority": ["R1", "R2", "R3", "R4"],
                "tuesday_teaching_exemption": True
            },
            "room_preferences": {
                "內科門診": ["4201", "4202", "4203"],
                "外科病房": ["4204", "4205"],
                "兒科門診": ["4207", "4208"],
                "婦產門診": ["4209", "4213"],
                "其他": ["4218"]
            }
        }
    
    @staticmethod
    def validate_csv_format(csv_content: str) -> Dict[str, Any]:
        """Validate CSV file format"""
        try:
            df = pd.read_csv(StringIO(csv_content))
            
            # Check required columns
            required_columns = ['Person', 'Level', 'Rotation_Unit']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {
                    'valid': False,
                    'error': f"Missing required columns: {', '.join(missing_columns)}"
                }
            
            # Validate data
            errors = []
            
            # Check levels
            valid_levels = ['R1', 'R2', 'R3', 'R4']
            invalid_levels = df[~df['Level'].isin(valid_levels)]['Level'].unique()
            if len(invalid_levels) > 0:
                errors.append(f"Invalid levels found: {', '.join(invalid_levels)}")
            
            # Check rotation units
            for idx, row in df.iterrows():
                level = row['Level']
                unit = row['Rotation_Unit']
                if level in Config.ROTATION_UNITS:
                    if unit not in Config.ROTATION_UNITS[level]:
                        errors.append(f"Row {idx+1}: Invalid rotation unit '{unit}' for {level}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'row_count': len(df),
                'data': df.to_dict('records') if len(errors) == 0 else None
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f"Failed to parse CSV: {str(e)}"
            }
    
    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], columns: List[str]) -> str:
        """Export data to CSV format"""
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    @staticmethod
    def parse_schedule_for_display(schedule: Dict[str, Any]) -> pd.DataFrame:
        """Parse schedule data for display in UI"""
        rows = []
        
        for week, week_data in schedule.items():
            for day, day_data in week_data.items():
                for time_slot, assignments in day_data.items():
                    row = {
                        'Week': week,
                        'Day': day,
                        'Time': time_slot
                    }
                    row.update(assignments)
                    rows.append(row)
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def aggregate_statistics(schedule: Dict[str, Any], personnel_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Aggregate schedule statistics"""
        stats = {
            'assignments_by_person': {},
            'assignments_by_room': {},
            'coverage_by_day': {},
            'health_check_coverage': 0,
            'clinic_coverage': 0
        }
        
        total_clinic_slots = 0
        filled_clinic_slots = 0
        total_health_slots = 0
        filled_health_slots = 0
        
        # Initialize counters
        for level, people in personnel_data.items():
            for person_id in people:
                stats['assignments_by_person'][person_id] = {
                    'clinic': 0,
                    'health_check': 0,
                    'total': 0
                }
        
        # Count assignments
        for week, week_data in schedule.items():
            for day, day_data in week_data.items():
                if day not in stats['coverage_by_day']:
                    stats['coverage_by_day'][day] = {'total': 0, 'filled': 0}
                    
                for time_slot, assignments in day_data.items():
                    for room, person in assignments.items():
                        if room in Config.CLINIC_ROOMS:
                            total_clinic_slots += 1
                            if person:
                                filled_clinic_slots += 1
                                stats['assignments_by_person'][person]['clinic'] += 1
                                stats['assignments_by_person'][person]['total'] += 1
                        elif room in Config.HEALTH_CHECK_ROOMS:
                            total_health_slots += 1
                            if person:
                                filled_health_slots += 1
                                stats['assignments_by_person'][person]['health_check'] += 1
                                stats['assignments_by_person'][person]['total'] += 1
                        
                        if room not in stats['assignments_by_room']:
                            stats['assignments_by_room'][room] = 0
                        if person:
                            stats['assignments_by_room'][room] += 1
                            
                        stats['coverage_by_day'][day]['total'] += 1
                        if person:
                            stats['coverage_by_day'][day]['filled'] += 1
        
        # Calculate coverage rates
        if total_clinic_slots > 0:
            stats['clinic_coverage'] = (filled_clinic_slots / total_clinic_slots) * 100
        if total_health_slots > 0:
            stats['health_check_coverage'] = (filled_health_slots / total_health_slots) * 100
            
        return stats