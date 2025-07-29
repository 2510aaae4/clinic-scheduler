"""Fitness evaluation for genetic algorithm based on strict rules"""
import numpy as np
from typing import Dict, List, Tuple, Any
from modules.schedule_requirements import (
    DAILY_ROOM_REQUIREMENTS, R1_RULES, R2_RULES, R3_RULES, R4_RULES
)

class FitnessEvaluator:
    def __init__(self, personnel_list: List[Dict], days: List[str], time_slots: List[str]):
        self.personnel_list = personnel_list
        self.days = days
        self.time_slots = time_slots
        self.level_rules = {
            'R1': R1_RULES,
            'R2': R2_RULES,
            'R3': R3_RULES,
            'R4': R4_RULES
        }
    
    def evaluate(self, schedule: Dict) -> Tuple[float, Dict[str, Any]]:
        """Evaluate a schedule and return fitness score and violation details"""
        violations = {
            'hard_violations': [],
            'soft_violations': [],
            'total_penalty': 0
        }
        
        # Check all hard constraints
        self._check_no_double_booking(schedule, violations)
        self._check_all_required_rooms_filled(schedule, violations)  # New check
        self._check_health_check_coverage(schedule, violations)
        self._check_no_full_day_assignment(schedule, violations)
        self._check_4201_restriction(schedule, violations)  # New check for 4201
        self._check_level_specific_rules(schedule, violations)
        self._check_r4_fixed_schedules(schedule, violations)  # New check for R4 fixed times
        
        # Calculate positive scores
        coverage_score = self._calculate_coverage_score(schedule)
        distribution_score = self._calculate_distribution_score(schedule)
        
        # Final fitness score
        fitness = coverage_score + distribution_score - violations['total_penalty']
        
        return fitness, violations
    
    def _check_no_double_booking(self, schedule: Dict, violations: Dict):
        """Rule 1: Same person cannot be in multiple rooms at same time"""
        for day in self.days:
            for time_slot in self.time_slots:
                assigned_persons = []
                
                if day in schedule and time_slot in schedule[day]:
                    for room, person_id in schedule[day][time_slot].items():
                        if person_id and person_id in assigned_persons:
                            violations['hard_violations'].append(
                                f"{person_id} double-booked on {day} {time_slot}"
                            )
                            violations['total_penalty'] += 1000
                        elif person_id:
                            assigned_persons.append(person_id)
    
    def _check_all_required_rooms_filled(self, schedule: Dict, violations: Dict):
        """Check that all required rooms in 規則.txt are filled"""
        for day in self.days:
            if day in DAILY_ROOM_REQUIREMENTS:
                for time_slot in self.time_slots:
                    if time_slot in DAILY_ROOM_REQUIREMENTS[day]:
                        required_rooms = DAILY_ROOM_REQUIREMENTS[day][time_slot]
                        
                        for room in required_rooms:
                            # Check if room is assigned and has someone
                            if (not schedule.get(day, {}).get(time_slot, {}).get(room)):
                                violations['hard_violations'].append(
                                    f"Required room {room} is empty on {day} {time_slot}"
                                )
                                violations['total_penalty'] += 1000
    
    def _check_health_check_coverage(self, schedule: Dict, violations: Dict):
        """Rule 2: Health check rooms must always have someone"""
        for day in self.days:
            for time_slot in self.time_slots:
                if day in DAILY_ROOM_REQUIREMENTS and time_slot in DAILY_ROOM_REQUIREMENTS[day]:
                    required_rooms = DAILY_ROOM_REQUIREMENTS[day][time_slot]
                    
                    for room in ['體檢1', '體檢2']:
                        if room in required_rooms:
                            if (not schedule.get(day, {}).get(time_slot, {}).get(room)):
                                violations['hard_violations'].append(
                                    f"{room} is empty on {day} {time_slot}"
                                )
                                violations['total_penalty'] += 500
    
    def _check_no_full_day_assignment(self, schedule: Dict, violations: Dict):
        """Rule 3: Same person cannot work both morning and afternoon (except R1 健康)"""
        for day in self.days:
            morning_workers = set()
            afternoon_workers = set()
            
            if day in schedule:
                if 'Morning' in schedule[day]:
                    for room, person_id in schedule[day]['Morning'].items():
                        if person_id:
                            morning_workers.add(person_id)
                
                if 'Afternoon' in schedule[day]:
                    for room, person_id in schedule[day]['Afternoon'].items():
                        if person_id:
                            afternoon_workers.add(person_id)
            
            # Check for violations
            full_day_workers = morning_workers.intersection(afternoon_workers)
            for person_id in full_day_workers:
                # Check if this is R1 with 健康 rotation unit
                person_info = self._get_person_info(person_id)
                if person_info and person_info['level'] == 'R1' and person_info['rotation_unit'] == '健康':
                    # Skip penalty for R1 健康 personnel
                    continue
                
                violations['hard_violations'].append(
                    f"{person_id} assigned both morning and afternoon on {day}"
                )
                violations['total_penalty'] += 800
    
    def _check_4201_restriction(self, schedule: Dict, violations: Dict):
        """Check that 4201 can only be assigned to R2 or R3"""
        for day in self.days:
            if day in schedule:
                for time_slot in self.time_slots:
                    if time_slot in schedule[day]:
                        # Check if 4201 is assigned
                        if '4201' in schedule[day][time_slot]:
                            person_id = schedule[day][time_slot]['4201']
                            if person_id:
                                # Get person info
                                person_info = self._get_person_info(person_id)
                                if person_info and person_info['level'] not in ['R2', 'R3']:
                                    violations['hard_violations'].append(
                                        f"4201 on {day} {time_slot} assigned to {person_id} ({person_info['level']}), must be R2 or R3"
                                    )
                                    violations['total_penalty'] += 600
    
    def _check_level_specific_rules(self, schedule: Dict, violations: Dict):
        """Check all level-specific rules for R1, R2, R3, R4"""
        person_assignments = self._get_person_assignments(schedule)
        
        for person_id, assignments in person_assignments.items():
            person_info = self._get_person_info(person_id)
            if not person_info:
                continue
            
            level = person_info['level']
            rotation_unit = person_info['rotation_unit']
            rules = self.level_rules.get(level)
            
            if not rules:
                continue
            
            # Check fixed assignments
            if 'fixed_assignments' in rules and rotation_unit in rules['fixed_assignments']:
                self._check_fixed_assignments(
                    person_id, assignments, rotation_unit, 
                    rules['fixed_assignments'][rotation_unit], violations
                )
            
            # Check restrictions
            if 'restrictions' in rules and rotation_unit in rules['restrictions']:
                self._check_restrictions(
                    person_id, assignments, rotation_unit,
                    rules['restrictions'][rotation_unit], violations
                )
            
            # Check clinic count limits
            self._check_clinic_counts(person_id, person_info, assignments, rules, violations)
            
            # Check special requirements
            self._check_special_requirements(person_id, person_info, assignments, rules, violations)
    
    def _check_fixed_assignments(self, person_id: str, assignments: List[Tuple], 
                                rotation_unit: str, fixed_rules: Dict, violations: Dict):
        """Check if person follows fixed assignment rules"""
        for day, time_rules in fixed_rules.items():
            for time_slot, required_rooms in time_rules.items():
                if required_rooms:
                    person_in_slot = any(
                        a for a in assignments 
                        if a[0] == day and a[1] == time_slot
                    )
                    
                    if isinstance(required_rooms, list):
                        # Specific rooms required
                        correct_room = any(
                            a for a in assignments 
                            if a[0] == day and a[1] == time_slot and a[2] in required_rooms
                        )
                        if not correct_room and person_in_slot:
                            violations['hard_violations'].append(
                                f"{person_id} ({rotation_unit}) not in required room on {day} {time_slot}"
                            )
                            violations['total_penalty'] += 300
                    elif required_rooms is True:
                        # Must work this slot (any room)
                        if not person_in_slot:
                            violations['soft_violations'].append(
                                f"{person_id} ({rotation_unit}) should work on {day} {time_slot}"
                            )
                            violations['total_penalty'] += 100
    
    def _check_restrictions(self, person_id: str, assignments: List[Tuple], 
                           rotation_unit: str, restrictions: Any, violations: Dict):
        """Check if person violates any restrictions"""
        if isinstance(restrictions, list):
            # List of restricted slots
            for restriction in restrictions:
                if isinstance(restriction, str):
                    # Full day restriction
                    day_assignments = [a for a in assignments if a[0] == restriction]
                    if day_assignments:
                        violations['hard_violations'].append(
                            f"{person_id} ({rotation_unit}) cannot work on {restriction}"
                        )
                        violations['total_penalty'] += 400
                elif isinstance(restriction, tuple) and len(restriction) == 2:
                    # Specific time slot restriction
                    day, time_slot = restriction
                    slot_assignments = [
                        a for a in assignments 
                        if a[0] == day and a[1] == time_slot
                    ]
                    if slot_assignments:
                        violations['hard_violations'].append(
                            f"{person_id} ({rotation_unit}) cannot work on {day} {time_slot}"
                        )
                        violations['total_penalty'] += 400
        elif isinstance(restrictions, dict) and 'required' in restrictions:
            # Special requirement (e.g., must have health check on specific slot)
            day, time_slot, required_rooms = restrictions['required']
            has_required = any(
                a for a in assignments 
                if a[0] == day and a[1] == time_slot and a[2] in required_rooms
            )
            if not has_required:
                # Check if person has any health check assignment
                has_health_check = any(a for a in assignments if a[2] in ['體檢1', '體檢2'])
                if has_health_check:
                    violations['soft_violations'].append(
                        f"{person_id} ({rotation_unit}) should have health check on {day} {time_slot}"
                    )
                    violations['total_penalty'] += 50
    
    def _check_clinic_counts(self, person_id: str, person_info: Dict, 
                            assignments: List[Tuple], rules: Dict, violations: Dict):
        """Check if person has correct number of clinics"""
        non_health_assignments = [
            a for a in assignments 
            if a[2] not in ['體檢1', '體檢2']
        ]
        health_assignments = [
            a for a in assignments 
            if a[2] in ['體檢1', '體檢2']
        ]
        
        # Check max non-health clinics
        max_clinics = rules.get('max_non_health_clinics', float('inf'))
        
        # Check special cases
        if 'special_cases' in rules and person_info['rotation_unit'] in rules['special_cases']:
            max_clinics = rules['special_cases'][person_info['rotation_unit']]
        
        if len(non_health_assignments) > max_clinics:
            violations['hard_violations'].append(
                f"{person_id} has {len(non_health_assignments)} clinics, max is {max_clinics}"
            )
            violations['total_penalty'] += 200 * (len(non_health_assignments) - max_clinics)
        
        # R1 specific rule: non-health clinics must be in afternoon 4204
        if person_info['level'] == 'R1' and non_health_assignments:
            for assignment in non_health_assignments:
                day, time_slot, room = assignment
                if time_slot != 'Afternoon' or room != '4204':
                    violations['hard_violations'].append(
                        f"{person_id} (R1) non-health clinic must be in afternoon 4204, but assigned to {room} on {day} {time_slot}"
                    )
                    violations['total_penalty'] += 400
        
        # Check health check requirement
        if person_info.get('health_check', False) and not health_assignments:
            violations['hard_violations'].append(
                f"{person_id} needs health check assignment"
            )
            violations['total_penalty'] += 300
        
        # R1 "健康" rotation unit must have exactly 8 health check assignments
        if person_info['level'] == 'R1' and person_info['rotation_unit'] == '健康':
            if len(health_assignments) != 8:
                violations['hard_violations'].append(
                    f"{person_id} (健康) must have exactly 8 health check assignments, has {len(health_assignments)}"
                )
                violations['total_penalty'] += 800
            
            # Also check if they have the required non-health clinic on Monday afternoon 4204
            monday_afternoon_4204 = any(
                a for a in non_health_assignments 
                if a[0] == 'Monday' and a[1] == 'Afternoon' and a[2] == '4204'
            )
            if not monday_afternoon_4204:
                violations['hard_violations'].append(
                    f"{person_id} (健康) must work Monday afternoon 4204"
                )
                violations['total_penalty'] += 400
    
    def _check_special_requirements(self, person_id: str, person_info: Dict, 
                                   assignments: List[Tuple], rules: Dict, violations: Dict):
        """Check special requirements like morning clinic, 4201 requirement, etc."""
        level = person_info['level']
        
        # R2, R3 must have exactly one 4201
        if level in ['R2', 'R3'] and rules.get('require_4201', False):
            room_4201_count = sum(1 for a in assignments if a[2] == '4201')
            if room_4201_count != 1:
                violations['hard_violations'].append(
                    f"{person_id} must have exactly one 4201 clinic, has {room_4201_count}"
                )
                violations['total_penalty'] += 300
        
        # R3, R4 must have at least one morning clinic
        if level in ['R3', 'R4'] and rules.get('require_morning', False):
            morning_clinics = [
                a for a in assignments 
                if a[1] == 'Morning' and a[2] not in ['體檢1', '體檢2']
            ]
            if not morning_clinics:
                violations['hard_violations'].append(
                    f"{person_id} must have at least one morning clinic"
                )
                violations['total_penalty'] += 200
        
        # R2 must have different time slots
        if level == 'R2' and rules.get('require_different_times', False):
            non_health = [a for a in assignments if a[2] not in ['體檢1', '體檢2']]
            if len(non_health) == 2:
                if non_health[0][1] == non_health[1][1]:
                    violations['hard_violations'].append(
                        f"{person_id} must have clinics at different times"
                    )
                    violations['total_penalty'] += 200
        
        # R4 Tuesday teaching restriction
        if level == 'R4' and person_info.get('tuesday_teaching', False):
            tuesday_assignments = [a for a in assignments if a[0] == 'Tuesday']
            if tuesday_assignments:
                violations['hard_violations'].append(
                    f"{person_id} has teaching on Tuesday, cannot have clinics"
                )
                violations['total_penalty'] += 500
    
    def _get_person_assignments(self, schedule: Dict) -> Dict[str, List[Tuple]]:
        """Get all assignments for each person"""
        person_assignments = {}
        
        for day in schedule:
            for time_slot in schedule[day]:
                for room, person_id in schedule[day][time_slot].items():
                    if person_id:
                        if person_id not in person_assignments:
                            person_assignments[person_id] = []
                        person_assignments[person_id].append((day, time_slot, room))
        
        return person_assignments
    
    def _get_person_info(self, person_id: str) -> Dict:
        """Get person information by ID"""
        for person in self.personnel_list:
            if person['id'] == person_id:
                return person
        return None
    
    def _calculate_coverage_score(self, schedule: Dict) -> float:
        """Calculate how well the schedule covers required rooms"""
        total_required = 0
        total_filled = 0
        
        for day in self.days:
            if day in DAILY_ROOM_REQUIREMENTS:
                for time_slot in self.time_slots:
                    if time_slot in DAILY_ROOM_REQUIREMENTS[day]:
                        required_rooms = DAILY_ROOM_REQUIREMENTS[day][time_slot]
                        total_required += len(required_rooms)
                        
                        if day in schedule and time_slot in schedule[day]:
                            for room in required_rooms:
                                if schedule[day][time_slot].get(room):
                                    total_filled += 1
        
        return (total_filled / total_required * 100) if total_required > 0 else 0
    
    def _calculate_distribution_score(self, schedule: Dict) -> float:
        """Calculate how evenly work is distributed"""
        person_counts = {}
        
        for day in schedule:
            for time_slot in schedule[day]:
                for room, person_id in schedule[day][time_slot].items():
                    if person_id:
                        person_counts[person_id] = person_counts.get(person_id, 0) + 1
        
        if not person_counts:
            return 0
        
        counts = list(person_counts.values())
        avg_count = sum(counts) / len(counts)
        variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
        
        # Lower variance is better
        return max(0, 20 - variance)
    
    def _check_r4_fixed_schedules(self, schedule: Dict, violations: Dict):
        """Check if R4 personnel with fixed schedules are assigned correctly"""
        for person in self.personnel_list:
            if person['level'] == 'R4' and person.get('fixed_schedule'):
                person_id = person['id']
                fixed = person['fixed_schedule']
                fixed_day = fixed['day']
                fixed_time = fixed['time_slot']
                
                # Check if person is scheduled at the fixed time
                person_found_at_fixed_time = False
                if fixed_day in schedule and fixed_time in schedule[fixed_day]:
                    for room, assigned_person in schedule[fixed_day][fixed_time].items():
                        if assigned_person == person_id:
                            person_found_at_fixed_time = True
                            break
                
                if not person_found_at_fixed_time:
                    violations['hard_violations'].append(
                        f"{person_id} (R4) must work on {fixed_day} {fixed_time} as specified"
                    )
                    violations['total_penalty'] += 1000
                
                # Check if person is scheduled at any other time (should only have one clinic)
                total_assignments = 0
                for day in schedule:
                    for time_slot in schedule[day]:
                        for room, assigned_person in schedule[day][time_slot].items():
                            if assigned_person == person_id:
                                total_assignments += 1
                                if (day != fixed_day or time_slot != fixed_time) and room not in ['體檢1', '體檢2']:
                                    violations['hard_violations'].append(
                                        f"{person_id} (R4) with fixed schedule should only work at {fixed_day} {fixed_time}"
                                    )
                                    violations['total_penalty'] += 800