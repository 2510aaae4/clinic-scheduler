"""R1 Pre-scheduler - Assigns all R1 clinics before genetic algorithm starts"""
import random
from typing import Dict, List, Tuple

class R1Scheduler:
    def __init__(self, r1_personnel: List[Dict]):
        self.r1_personnel = r1_personnel
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
    def schedule_all_r1_clinics(self) -> Dict[str, Tuple[str, str]]:
        """
        Pre-schedule all R1 clinics optimally
        Returns: Dict mapping person_id to (day, room) tuple
        """
        r1_assignments = {}
        available_slots = self._get_available_slots()
        
        # Categorize R1 personnel by restrictions
        fixed_personnel = []  # 健康, 社區1
        restricted_personnel = []  # 病房, 精神1
        flexible_personnel = []  # Others
        
        for person in self.r1_personnel:
            rotation_unit = person['rotation_unit']
            if rotation_unit in ['健康', '社區1']:
                fixed_personnel.append(person)
            elif '病房' in rotation_unit or rotation_unit == '精神1':
                restricted_personnel.append(person)
            else:
                flexible_personnel.append(person)
        
        # First, handle fixed assignments
        for person in fixed_personnel:
            person_id = person['id']
            rotation_unit = person['rotation_unit']
            
            if rotation_unit == '健康':
                # Fixed: Monday afternoon 4204
                r1_assignments[person_id] = ('Monday', '4204')
                available_slots.remove(('Monday', '4204'))
            elif rotation_unit == '社區1':
                # Fixed: Tuesday afternoon 4204
                r1_assignments[person_id] = ('Tuesday', '4204')
                available_slots.remove(('Tuesday', '4204'))
        
        # Then assign restricted personnel (they have fewer options)
        for person in restricted_personnel:
            person_id = person['id']
            rotation_unit = person['rotation_unit']
            
            # Get valid slots for this person
            valid_slots = self._get_valid_slots(rotation_unit, available_slots)
            
            if valid_slots:
                selected_slot = self._select_best_slot(valid_slots, rotation_unit)
                r1_assignments[person_id] = selected_slot
                available_slots.remove(selected_slot)
            else:
                # If no valid slots, we need to be more flexible
                # For 病房 units, Tuesday-Thursday are always valid
                if '病房' in rotation_unit:
                    for day in ['Wednesday', 'Thursday', 'Tuesday']:
                        slot = (day, '4204')
                        if slot in available_slots:
                            r1_assignments[person_id] = slot
                            available_slots.remove(slot)
                            break
                else:
                    raise ValueError(f"Cannot find valid slot for {person_id} ({rotation_unit})")
        
        # Finally assign flexible personnel
        for person in flexible_personnel:
            person_id = person['id']
            
            if available_slots:
                selected_slot = available_slots[0]
                r1_assignments[person_id] = selected_slot
                available_slots.remove(selected_slot)
            else:
                raise ValueError(f"No slots left for {person_id}")
        
        return r1_assignments
    
    def _get_available_slots(self) -> List[Tuple[str, str]]:
        """Get all available afternoon 4204 slots"""
        return [
            ('Monday', '4204'),
            ('Tuesday', '4204'),
            ('Wednesday', '4204'),
            ('Thursday', '4204'),
            ('Friday', '4204')
        ]
    
    def _get_valid_slots(self, rotation_unit: str, available_slots: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Get valid slots for a rotation unit considering restrictions"""
        valid_slots = []
        
        for day, room in available_slots:
            # Check restrictions
            if self._is_slot_valid(rotation_unit, day):
                valid_slots.append((day, room))
        
        return valid_slots
    
    def _is_slot_valid(self, rotation_unit: str, day: str) -> bool:
        """Check if a day is valid for the rotation unit"""
        # 病房 units cannot work on Monday or Friday
        if '病房' in rotation_unit and day in ['Monday', 'Friday']:
            return False
        
        # 精神1 cannot work Monday afternoon or Thursday afternoon
        if rotation_unit == '精神1' and day in ['Monday', 'Thursday']:
            return False
        
        return True
    
    def _select_best_slot(self, valid_slots: List[Tuple[str, str]], rotation_unit: str) -> Tuple[str, str]:
        """Select the best slot from valid options"""
        # For now, just pick the first available
        # Can implement more sophisticated selection based on:
        # - Even distribution across days
        # - Coordination with other constraints
        # - Preference for certain days
        
        # Prefer mid-week for general assignments
        preferred_order = ['Wednesday', 'Tuesday', 'Thursday', 'Monday', 'Friday']
        
        # Sort valid slots by preference
        sorted_slots = sorted(valid_slots, 
                            key=lambda x: preferred_order.index(x[0]) if x[0] in preferred_order else 999)
        
        return sorted_slots[0]
    
    def create_fixed_r1_schedule(self, r1_assignments: Dict[str, Tuple[str, str]]) -> Dict:
        """
        Create a partial schedule with all R1 assignments fixed
        This will be used as the base for all chromosomes
        """
        fixed_schedule = {}
        
        for person_id, (day, room) in r1_assignments.items():
            if day not in fixed_schedule:
                fixed_schedule[day] = {}
            if 'Afternoon' not in fixed_schedule[day]:
                fixed_schedule[day]['Afternoon'] = {}
            
            fixed_schedule[day]['Afternoon'][room] = person_id
        
        return fixed_schedule