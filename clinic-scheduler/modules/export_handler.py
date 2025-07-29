import pandas as pd
import zipfile  # Using Python's built-in zipfile module
from datetime import datetime
from typing import Dict, Any, List
import os
from io import StringIO
from config.settings import Config

class ExportHandler:
    """Handle multiple CSV export formats"""
    
    def __init__(self, schedule_data: Dict[str, Any], personnel_data: Dict[str, Dict]):
        self.schedule = schedule_data
        self.personnel = personnel_data
        
    def generate_basic_csv(self) -> str:
        """Generate traditional week-based schedule view (原始排班表)"""
        rows = []
        
        # Create header
        header = ['Week', 'Day', 'Time'] + Config.CLINIC_ROOMS + Config.HEALTH_CHECK_ROOMS
        
        # Process schedule data
        for week_num in range(1, Config.TOTAL_WEEKS + 1):
            week_key = f"W{week_num}"
            if week_key not in self.schedule:
                continue
                
            week_data = self.schedule[week_key]
            
            for day in Config.WEEKDAYS:
                if day not in week_data:
                    continue
                    
                day_data = week_data[day]
                
                for time_slot in Config.TIME_SLOTS:
                    if time_slot not in day_data:
                        continue
                        
                    row = {
                        'Week': week_key,
                        'Day': day,
                        'Time': time_slot
                    }
                    
                    # Add room assignments
                    assignments = day_data[time_slot]
                    for room in Config.CLINIC_ROOMS + Config.HEALTH_CHECK_ROOMS:
                        assigned_person = assignments.get(room, '')
                        if assigned_person:
                            # Try to get person's name
                            person_name = self._get_person_name(assigned_person)
                            if person_name:
                                row[room] = f"{assigned_person}\n{person_name}"
                            else:
                                row[room] = assigned_person
                        else:
                            row[room] = ''
                    
                    rows.append(row)
        
        # Convert to CSV
        df = pd.DataFrame(rows, columns=header)
        return df.to_csv(index=False, encoding='utf-8-sig')
    
    def generate_personal_csv(self) -> str:
        """Generate person-centric schedule view (個人排班表)"""
        rows = []
        
        # Process each person
        for level, people in self.personnel.items():
            for person_id, person_data in people.items():
                person_name = person_data.get('name', '')
                row = {
                    '人員': f"{person_id} ({person_name})" if person_name else person_id,
                    '級別': level,
                    '輪訓單位': person_data['rotation_unit']
                }
                
                # Initialize counts
                clinic_count = 0
                health_check_count = 0
                
                # Add weekly assignments
                for week_num in range(1, Config.TOTAL_WEEKS + 1):
                    week_key = f"W{week_num}"
                    
                    for time_slot in ['上午', '下午']:
                        slot_key = f"{week_key}{time_slot}"
                        assignment = self._find_person_assignment(
                            person_id, week_num, time_slot
                        )
                        
                        if assignment:
                            row[slot_key] = assignment['room']
                            if assignment['room'] in Config.HEALTH_CHECK_ROOMS:
                                health_check_count += 1
                            else:
                                clinic_count += 1
                        else:
                            row[slot_key] = '-'
                
                # Add statistics
                row['門診總數'] = clinic_count
                row['體檢總數'] = health_check_count
                
                rows.append(row)
        
        # Create column order
        columns = ['人員', '級別', '輪訓單位']
        for week_num in range(1, Config.TOTAL_WEEKS + 1):
            columns.extend([f"W{week_num}上午", f"W{week_num}下午"])
        columns.extend(['門診總數', '體檢總數'])
        
        # Convert to CSV
        df = pd.DataFrame(rows, columns=columns)
        return df.to_csv(index=False, encoding='utf-8-sig')
    
    def _get_person_name(self, person_id: str) -> str:
        """Get person's name from personnel data"""
        for level, people in self.personnel.items():
            if person_id in people:
                return people[person_id].get('name', '')
        return ''
    
    def generate_statistics_csv(self) -> str:
        """Generate statistics and summary report (統計報表)"""
        rows = []
        
        # Basic statistics
        total_personnel = sum(len(people) for people in self.personnel.values())
        rows.append({'統計項目': '總人員數', '數值': total_personnel})
        
        # Personnel by level
        for level in ['R1', 'R2', 'R3', 'R4']:
            count = len(self.personnel.get(level, {}))
            rows.append({'統計項目': f"{level}人員數", '數值': count})
        
        # Calculate slot statistics
        total_clinic_slots = Config.TOTAL_WEEKS * len(Config.WEEKDAYS) * len(Config.TIME_SLOTS) * len(Config.CLINIC_ROOMS)
        total_health_slots = Config.TOTAL_WEEKS * len(Config.WEEKDAYS) * len(Config.TIME_SLOTS) * len(Config.HEALTH_CHECK_ROOMS)
        
        rows.append({'統計項目': '總門診時段', '數值': total_clinic_slots})
        rows.append({'統計項目': '總體檢時段', '數值': total_health_slots})
        
        # Count filled slots
        filled_clinic_slots = 0
        filled_health_slots = 0
        person_assignments = {}
        
        for week_key, week_data in self.schedule.items():
            for day, day_data in week_data.items():
                for time_slot, assignments in day_data.items():
                    for room, person in assignments.items():
                        if person:
                            if room in Config.CLINIC_ROOMS:
                                filled_clinic_slots += 1
                            elif room in Config.HEALTH_CHECK_ROOMS:
                                filled_health_slots += 1
                            
                            if person not in person_assignments:
                                person_assignments[person] = 0
                            person_assignments[person] += 1
        
        rows.append({'統計項目': '已分配門診時段', '數值': filled_clinic_slots})
        rows.append({'統計項目': '已分配體檢時段', '數值': filled_health_slots})
        
        # Coverage rates
        clinic_coverage = (filled_clinic_slots / total_clinic_slots * 100) if total_clinic_slots > 0 else 0
        health_coverage = (filled_health_slots / total_health_slots * 100) if total_health_slots > 0 else 0
        
        rows.append({'統計項目': '門診覆蓋率', '數值': f"{clinic_coverage:.1f}%"})
        rows.append({'統計項目': '體檢覆蓋率', '數值': f"{health_coverage:.1f}%"})
        
        # Average assignments
        if person_assignments:
            avg_assignments = sum(person_assignments.values()) / len(person_assignments)
            rows.append({'統計項目': '平均每人門診數', '數值': f"{avg_assignments:.1f}"})
            
            # Find min/max
            max_person = max(person_assignments.items(), key=lambda x: x[1])
            min_person = min(person_assignments.items(), key=lambda x: x[1])
            
            rows.append({'統計項目': '最多門診人員', '數值': f"{max_person[0]} ({max_person[1]})"})
            rows.append({'統計項目': '最少門診人員', '數值': f"{min_person[0]} ({min_person[1]})"})
        
        # Rotation unit distribution
        unit_counts = {}
        for level, people in self.personnel.items():
            for person_id, person_data in people.items():
                unit = person_data['rotation_unit']
                if unit not in unit_counts:
                    unit_counts[unit] = 0
                unit_counts[unit] += 1
        
        rows.append({'統計項目': '', '數值': ''})  # Empty row
        rows.append({'統計項目': '輪訓單位分布', '數值': ''})
        
        for unit, count in sorted(unit_counts.items(), key=lambda x: x[1], reverse=True):
            rows.append({'統計項目': f"  {unit}", '數值': count})
        
        # Convert to CSV
        df = pd.DataFrame(rows)
        return df.to_csv(index=False, encoding='utf-8-sig')
    
    def _find_person_assignment(self, person_id: str, week_num: int, 
                               time_slot: str) -> Dict[str, str]:
        """Find where a person is assigned in a specific time slot"""
        week_key = f"W{week_num}"
        
        # Convert Chinese time slot to English
        english_time = 'Morning' if time_slot == '上午' else 'Afternoon'
        
        if week_key not in self.schedule:
            return None
            
        week_data = self.schedule[week_key]
        
        for day in Config.WEEKDAYS:
            if day not in week_data:
                continue
                
            if english_time not in week_data[day]:
                continue
                
            assignments = week_data[day][english_time]
            
            for room, assigned_person in assignments.items():
                if assigned_person == person_id:
                    return {
                        'day': day,
                        'room': room,
                        'time': english_time
                    }
        
        return None
    
    def create_zip_bundle(self, files: Dict[str, str], timestamp: str) -> str:
        """Create ZIP file with all formats"""
        zip_filename = f"data/temp/clinic_schedule_{timestamp}.zip"
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_type, file_path in files.items():
                if os.path.exists(file_path):
                    # Add file to zip with a friendly name
                    if file_type == 'basic':
                        arcname = '原始排班表.csv'
                    elif file_type == 'personal':
                        arcname = '個人排班表.csv'
                    elif file_type == 'statistics':
                        arcname = '統計報表.csv'
                    else:
                        arcname = os.path.basename(file_path)
                    
                    zipf.write(file_path, arcname)
        
        return zip_filename
    
    def generate_summary_report(self) -> str:
        """Generate a summary report for display"""
        summary = []
        
        # Total coverage
        total_slots = 0
        filled_slots = 0
        
        for week_key, week_data in self.schedule.items():
            for day, day_data in week_data.items():
                for time_slot, assignments in day_data.items():
                    for room, person in assignments.items():
                        total_slots += 1
                        if person:
                            filled_slots += 1
        
        coverage = (filled_slots / total_slots * 100) if total_slots > 0 else 0
        
        summary.append(f"總覆蓋率: {coverage:.1f}%")
        summary.append(f"已分配時段: {filled_slots}/{total_slots}")
        
        # Personnel summary
        total_personnel = sum(len(people) for people in self.personnel.values())
        summary.append(f"總人員數: {total_personnel}")
        
        # Level breakdown
        for level in ['R1', 'R2', 'R3', 'R4']:
            count = len(self.personnel.get(level, {}))
            summary.append(f"{level}: {count}人")
        
        return '\n'.join(summary)