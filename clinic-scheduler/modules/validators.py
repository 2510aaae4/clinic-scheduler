from typing import Dict, List, Any, Set
from config.settings import Config

class InputValidator:
    """Validate user input for schedule generation"""
    
    def __init__(self):
        self.rotation_units = Config.ROTATION_UNITS
        self.min_count = Config.MIN_PERSONNEL_COUNT
        self.max_count = Config.MAX_PERSONNEL_COUNT
        
    def validate_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete input data"""
        errors = []
        warnings = []
        
        # Validate personnel counts
        personnel_counts = data.get('personnel_counts', {})
        for level in ['R1', 'R2', 'R3', 'R4']:
            count = personnel_counts.get(level, Config.DEFAULT_PERSONNEL_COUNTS[level])
            if not isinstance(count, int) or count < self.min_count or count > self.max_count:
                errors.append(f"Invalid {level} count: must be between {self.min_count} and {self.max_count}")
        
        # Validate personnel data
        personnel_data = data.get('personnel', {})
        
        for level, people in personnel_data.items():
            if level not in self.rotation_units:
                errors.append(f"Invalid level: {level}")
                continue
                
            valid_units = self.rotation_units[level]
            
            for person_id, person_data in people.items():
                # Check rotation unit
                rotation_unit = person_data.get('rotation_unit')
                if not rotation_unit:
                    errors.append(f"{person_id}: Missing rotation unit")
                elif rotation_unit not in valid_units:
                    errors.append(f"{person_id}: Invalid rotation unit '{rotation_unit}' for {level}")
                
                # Check boolean flags
                if 'health_check' in person_data and not isinstance(person_data['health_check'], bool):
                    errors.append(f"{person_id}: health_check must be boolean")
                    
                if level == 'R4' and 'tuesday_teaching' in person_data:
                    if not isinstance(person_data['tuesday_teaching'], bool):
                        errors.append(f"{person_id}: tuesday_teaching must be boolean")
        
        # Check for conflicts
        conflicts = self._check_conflicts(personnel_data)
        if conflicts:
            warnings.extend(conflicts)
        
        # Check for scheduling difficulty
        difficulty = self._assess_difficulty(personnel_data)
        if difficulty['warnings']:
            warnings.extend(difficulty['warnings'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'difficulty': difficulty['score']
        }
    
    def validate_partial(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate partial input (for real-time validation)"""
        errors = []
        warnings = []
        
        # Extract what we're validating
        level = data.get('level')
        person_id = data.get('person_id')
        field = data.get('field')
        value = data.get('value')
        
        if field == 'rotation_unit' and level and value:
            if level in self.rotation_units:
                if value not in self.rotation_units[level]:
                    errors.append(f"Invalid rotation unit '{value}' for {level}")
        
        elif field == 'personnel_count' and level and value is not None:
            try:
                count = int(value)
                if count < self.min_count or count > self.max_count:
                    errors.append(f"Count must be between {self.min_count} and {self.max_count}")
            except ValueError:
                errors.append("Count must be a number")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _check_conflicts(self, personnel_data: Dict[str, Dict]) -> List[str]:
        """Check for potential scheduling conflicts"""
        warnings = []
        
        # Check for multiple people with same restrictive rotation units
        unit_counts = {}
        for level, people in personnel_data.items():
            for person_id, data in people.items():
                unit = data.get('rotation_unit')
                if unit:
                    if unit not in unit_counts:
                        unit_counts[unit] = []
                    unit_counts[unit].append((person_id, level))
        
        # Identify potentially problematic assignments
        problematic_units = {
            '健康': 'Multiple R1s assigned to 健康 may limit health check coverage',
            '急診': 'Multiple personnel in 急診 may reduce clinic availability',
            '放射': 'Multiple personnel in 放射 may reduce clinic availability'
        }
        
        for unit, message in problematic_units.items():
            if unit in unit_counts and len(unit_counts[unit]) > 2:
                warnings.append(message)
        
        return warnings
    
    def _assess_difficulty(self, personnel_data: Dict[str, Dict]) -> Dict[str, Any]:
        """Assess scheduling difficulty based on constraints"""
        warnings = []
        difficulty_score = 0
        
        # Count constraints
        total_personnel = sum(len(people) for people in personnel_data.values())
        health_check_count = sum(
            1 for level, people in personnel_data.items()
            for person_id, data in people.items()
            if data.get('health_check', False)
        )
        tuesday_teaching_count = sum(
            1 for level, people in personnel_data.items()
            for person_id, data in people.items()
            if data.get('tuesday_teaching', False)
        )
        
        # Assess health check coverage
        required_health_slots = Config.TOTAL_WEEKS * len(Config.WEEKDAYS) * len(Config.TIME_SLOTS) * len(Config.HEALTH_CHECK_ROOMS)
        if health_check_count < 4:
            warnings.append(f"Only {health_check_count} personnel available for health checks - may be insufficient")
            difficulty_score += 20
        
        # Assess Tuesday teaching impact
        if tuesday_teaching_count > 2:
            warnings.append(f"{tuesday_teaching_count} R4 personnel have Tuesday teaching - may limit scheduling flexibility")
            difficulty_score += 10
        
        # Check rotation unit distribution
        restrictive_units = self._count_restrictive_units(personnel_data)
        if restrictive_units > total_personnel * 0.3:
            warnings.append("Many personnel have restrictive rotation units - scheduling may be challenging")
            difficulty_score += 15
        
        # Overall assessment
        if total_personnel < 18:
            warnings.append("Low total personnel count may make it difficult to fill all slots")
            difficulty_score += 25
        elif total_personnel > 25:
            difficulty_score -= 10  # More personnel makes it easier
        
        return {
            'score': min(100, difficulty_score),
            'warnings': warnings
        }
    
    def _count_restrictive_units(self, personnel_data: Dict[str, Dict]) -> int:
        """Count personnel with restrictive rotation units"""
        restrictive_units = {
            '健康', '急診', '放射', '精神1', '精神2', '安寧1', '安寧2', 
            '糖尿病衛教', '睡眠門診', '旅遊門診', '骨鬆門診', '減重門診'
        }
        
        count = 0
        for level, people in personnel_data.items():
            for person_id, data in people.items():
                if data.get('rotation_unit') in restrictive_units:
                    count += 1
                    
        return count