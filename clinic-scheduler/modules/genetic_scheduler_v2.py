"""Genetic Algorithm Scheduler V2 - Based on strict rules from 規則.txt"""
import random
from typing import List, Dict, Tuple, Any
import copy
from config.settings import Config
from modules.fitness_evaluator import FitnessEvaluator
from modules.schedule_requirements import (
    DAILY_ROOM_REQUIREMENTS, R1_RULES, R2_RULES, R3_RULES, R4_RULES
)
from modules.r1_scheduler import R1Scheduler

class GeneticSchedulerV2:
    def __init__(self, personnel_data: Dict, rules: Dict, 
                 population_size: int = None, generations: int = 1000):
        """Initialize genetic scheduler with personnel data and rules"""
        self.personnel_data = personnel_data
        self.rules = rules
        self.total_personnel = sum(len(level) for level in personnel_data.values())
        
        # Dynamic GA parameters
        ga_config = Config.get_ga_config(self.total_personnel)
        self.population_size = population_size or ga_config['population_size']
        self.generations = generations
        self.elite_size = int(self.population_size * ga_config['elite_percentage'])
        self.mutation_rate = ga_config['mutation_rate']
        self.crossover_rate = ga_config['crossover_rate']
        self.tournament_size = ga_config['tournament_size']
        self.convergence_threshold = ga_config['convergence_threshold']
        
        # Schedule structure
        self.days = Config.WEEKDAYS
        self.time_slots = Config.TIME_SLOTS
        
        # Track best solution
        self.best_fitness = float('-inf')
        self.best_solution = None
        self.no_improvement_count = 0
        
        # Create personnel list with metadata
        self.personnel_list = self._create_personnel_list()
        
        # Initialize fitness evaluator
        self.fitness_evaluator = FitnessEvaluator(
            self.personnel_list, self.days, self.time_slots
        )
        
        # Level rules
        self.level_rules = {
            'R1': R1_RULES,
            'R2': R2_RULES,
            'R3': R3_RULES,
            'R4': R4_RULES
        }
        
        # Pre-schedule R1 clinics
        r1_personnel = [p for p in self.personnel_list if p['level'] == 'R1']
        r1_scheduler = R1Scheduler(r1_personnel)
        self.r1_assignments = r1_scheduler.schedule_all_r1_clinics()
        self.r1_fixed_schedule = r1_scheduler.create_fixed_r1_schedule(self.r1_assignments)
        
        # Pre-schedule R4 fixed clinics
        self.r4_fixed_schedule = self._create_r4_fixed_schedule()
    
    def _create_personnel_list(self) -> List[Dict]:
        """Create flat list of all personnel with their metadata"""
        personnel_list = []
        
        for level, people in self.personnel_data.items():
            for person_id, data in people.items():
                personnel_list.append({
                    'id': person_id,
                    'name': data.get('name', ''),
                    'level': level,
                    'rotation_unit': data['rotation_unit'],
                    'health_check': data.get('health_check', False),
                    'tuesday_teaching': data.get('tuesday_teaching', False),
                    'fixed_schedule': data.get('fixed_schedule', None)
                })
                
        return personnel_list
    
    def _create_r4_fixed_schedule(self) -> Dict:
        """Create fixed schedule for R4 personnel with specified time slots"""
        fixed_schedule = {}
        
        for person in self.personnel_list:
            if person['level'] == 'R4' and person.get('fixed_schedule'):
                fixed = person['fixed_schedule']
                day = fixed['day']
                time_slot = fixed['time_slot']
                room = fixed.get('room')
                
                if day not in fixed_schedule:
                    fixed_schedule[day] = {}
                if time_slot not in fixed_schedule[day]:
                    fixed_schedule[day][time_slot] = {}
                
                # Use specified room if available
                if room:
                    fixed_schedule[day][time_slot][room] = person['id']
                else:
                    # Find an available room for this time slot if not specified
                    if day in DAILY_ROOM_REQUIREMENTS and time_slot in DAILY_ROOM_REQUIREMENTS[day]:
                        available_rooms = DAILY_ROOM_REQUIREMENTS[day][time_slot]
                        # Try to find a room that's not 4204 (reserved for R1) and not 4201 (R2/R3 only)
                        for room in available_rooms:
                            if room not in ['4204', '4201', '體檢1', '體檢2']:
                                fixed_schedule[day][time_slot][room] = person['id']
                                break
        
        return fixed_schedule
    
    def run(self) -> Dict[str, Any]:
        """Run genetic algorithm to find optimal schedule"""
        # Initialize population
        population = self.initialize_population()
        
        # Evolution loop
        for generation in range(self.generations):
            # Calculate fitness for all individuals
            fitness_scores = [self.fitness(schedule) for schedule in population]
            
            # Track best solution
            best_idx = max(range(len(fitness_scores)), key=lambda i: fitness_scores[i])
            if fitness_scores[best_idx] > self.best_fitness:
                self.best_fitness = fitness_scores[best_idx]
                self.best_solution = copy.deepcopy(population[best_idx])
                self.no_improvement_count = 0
            else:
                self.no_improvement_count += 1
            
            # Check for convergence
            if self.no_improvement_count >= self.convergence_threshold:
                print(f"Converged at generation {generation}")
                break
            
            # Create new population
            new_population = []
            
            # Elitism - keep best individuals
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i], 
                                 reverse=True)[:self.elite_size]
            for idx in elite_indices:
                new_population.append(copy.deepcopy(population[idx]))
            
            # Generate new individuals
            while len(new_population) < self.population_size:
                # Selection
                parent1 = self.tournament_selection(population, fitness_scores)
                parent2 = self.tournament_selection(population, fitness_scores)
                
                # Crossover
                child1, child2 = self.crossover(parent1, parent2)
                
                # Mutation
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                
                new_population.extend([child1, child2])
            
            # Trim to exact population size
            population = new_population[:self.population_size]
        
        # Convert best solution to required format
        if self.best_solution is not None:
            # Get detailed violations
            _, violations = self.fitness_evaluator.evaluate(self.best_solution)
            
            # Calculate statistics
            statistics = self._calculate_statistics(self.best_solution)
            
            return {
                'success': True,
                'schedule': self._convert_to_api_format(self.best_solution),
                'statistics': statistics,
                'violations': violations,
                'fitness': float(self.best_fitness),
                'generations': generation + 1
            }
        else:
            return {
                'success': False,
                'error': 'Failed to find valid schedule',
                'details': {
                    'best_fitness': self.best_fitness,
                    'generations': generation + 1
                }
            }
    
    def initialize_population(self) -> List[Dict]:
        """Initialize population with valid schedules"""
        population = []
        
        for _ in range(self.population_size):
            schedule = self._create_initial_schedule()
            population.append(schedule)
        
        return population
    
    def _create_initial_schedule(self) -> Dict:
        """Create a single initial schedule"""
        # Start with pre-scheduled R1 assignments
        schedule = copy.deepcopy(self.r1_fixed_schedule)
        
        # Add pre-scheduled R4 assignments
        for day, time_slots in self.r4_fixed_schedule.items():
            if day not in schedule:
                schedule[day] = {}
            for time_slot, rooms in time_slots.items():
                if time_slot not in schedule[day]:
                    schedule[day][time_slot] = {}
                for room, person_id in rooms.items():
                    schedule[day][time_slot][room] = person_id
        
        # Handle R1 health check assignments (健康 unit)
        self._assign_r1_health_checks(schedule)
        
        # Then assign other personnel
        for day in self.days:
            if day not in schedule:
                schedule[day] = {}
            
            for time_slot in self.time_slots:
                if time_slot not in schedule[day]:
                    schedule[day][time_slot] = {}
                
                # Get required rooms for this slot
                if day in DAILY_ROOM_REQUIREMENTS and time_slot in DAILY_ROOM_REQUIREMENTS[day]:
                    required_rooms = DAILY_ROOM_REQUIREMENTS[day][time_slot]
                    
                    for room in required_rooms:
                        if room not in schedule[day][time_slot]:
                            # Try to assign someone
                            available = self._get_available_personnel(day, time_slot, room, schedule)
                            if available:
                                selected = random.choice(available)
                                schedule[day][time_slot][room] = selected
                            else:
                                schedule[day][time_slot][room] = None
        
        return schedule
    
    def _assign_r1_health_checks(self, schedule: Dict):
        """Assign R1 health check duties (mainly for 健康 unit)"""
        r1_personnel = [p for p in self.personnel_list if p['level'] == 'R1']
        
        for person in r1_personnel:
            rotation_unit = person['rotation_unit']
            
            # Special handling for 健康 unit - must follow exact health check schedule
            if rotation_unit == '健康':
                # Fixed health check assignments for 健康 R1 (not including the clinic)
                health_check_assignments = [
                    ('Monday', 'Morning', '體檢1'),
                    ('Tuesday', 'Morning', '體檢1'),
                    ('Tuesday', 'Afternoon', '體檢1'),
                    ('Wednesday', 'Afternoon', '體檢1'),
                    ('Thursday', 'Morning', '體檢1'),
                    ('Thursday', 'Afternoon', '體檢1'),
                    ('Friday', 'Morning', '體檢1'),
                    ('Friday', 'Afternoon', '體檢1')
                ]
                
                for day, time_slot, room in health_check_assignments:
                    if day not in schedule:
                        schedule[day] = {}
                    if time_slot not in schedule[day]:
                        schedule[day][time_slot] = {}
                    schedule[day][time_slot][room] = person['id']
    
    def _restore_r1_clinics(self, schedule: Dict):
        """Restore pre-scheduled R1 clinic assignments"""
        for day, time_slots in self.r1_fixed_schedule.items():
            if day not in schedule:
                schedule[day] = {}
            for time_slot, rooms in time_slots.items():
                if time_slot not in schedule[day]:
                    schedule[day][time_slot] = {}
                for room, person_id in rooms.items():
                    schedule[day][time_slot][room] = person_id
    
    def _restore_r4_fixed_clinics(self, schedule: Dict):
        """Restore pre-scheduled R4 fixed assignments"""
        for day, time_slots in self.r4_fixed_schedule.items():
            if day not in schedule:
                schedule[day] = {}
            for time_slot, rooms in time_slots.items():
                if time_slot not in schedule[day]:
                    schedule[day][time_slot] = {}
                for room, person_id in rooms.items():
                    schedule[day][time_slot][room] = person_id
    
    def _get_available_personnel(self, day: str, time_slot: str, 
                                room: str, schedule: Dict) -> List[str]:
        """Get list of personnel available for a specific slot"""
        available = []
        
        for person in self.personnel_list:
            # Check if already assigned this slot
            already_assigned = False
            if day in schedule and time_slot in schedule[day]:
                for r, p in schedule[day][time_slot].items():
                    if p == person['id']:
                        already_assigned = True
                        break
            
            if already_assigned:
                continue
            
            # Check if worked other time slot this day
            other_slot = 'Afternoon' if time_slot == 'Morning' else 'Morning'
            if day in schedule and other_slot in schedule[day]:
                for r, p in schedule[day][other_slot].items():
                    if p == person['id']:
                        already_assigned = True
                        break
            
            if already_assigned:
                continue
            
            # Check level-specific restrictions
            if self._is_restricted(person, day, time_slot):
                continue
            
            # Check room compatibility
            if room in ['體檢1', '體檢2'] and not person['health_check']:
                continue
            
            # Check 4201 restriction - only R2 and R3 can be assigned
            if room == '4201' and person['level'] not in ['R2', 'R3']:
                continue
            
            available.append(person['id'])
        
        return available
    
    def _is_restricted(self, person: Dict, day: str, time_slot: str) -> bool:
        """Check if person is restricted from working this slot"""
        level = person['level']
        rotation_unit = person['rotation_unit']
        
        # R4 Tuesday teaching
        if level == 'R4' and person.get('tuesday_teaching', False) and day == 'Tuesday':
            return True
        
        # Level-specific restrictions
        if level in self.level_rules:
            rules = self.level_rules[level]
            if 'restrictions' in rules and rotation_unit in rules['restrictions']:
                restrictions = rules['restrictions'][rotation_unit]
                
                if isinstance(restrictions, list):
                    for restriction in restrictions:
                        if isinstance(restriction, str) and restriction == day:
                            return True
                        elif isinstance(restriction, tuple):
                            if len(restriction) == 2 and restriction == (day, time_slot):
                                return True
        
        return False
    
    def _get_person_info(self, person_id: str) -> Dict:
        """Get person information by ID"""
        for person in self.personnel_list:
            if person['id'] == person_id:
                return person
        return None
    
    def fitness(self, schedule: Dict) -> float:
        """Calculate fitness score for a schedule"""
        fitness_score, _ = self.fitness_evaluator.evaluate(schedule)
        return fitness_score
    
    def tournament_selection(self, population: List[Dict], 
                           fitness_scores: List[float]) -> Dict:
        """Select individual using tournament selection"""
        tournament_indices = random.sample(range(len(population)), 
                                         min(self.tournament_size, len(population)))
        winner_idx = max(tournament_indices, key=lambda i: fitness_scores[i])
        return copy.deepcopy(population[winner_idx])
    
    def crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """Perform crossover between two parents"""
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        child1 = copy.deepcopy(parent1)
        child2 = copy.deepcopy(parent2)
        
        # Day-based crossover
        crossover_day = random.choice(self.days[1:])
        crossover_idx = self.days.index(crossover_day)
        
        # Swap schedules after crossover day
        for i in range(crossover_idx, len(self.days)):
            day = self.days[i]
            if day in parent1 and day in parent2:
                child1[day] = copy.deepcopy(parent2[day])
                child2[day] = copy.deepcopy(parent1[day])
        
        # Restore R1 clinic assignments (they should never change)
        self._restore_r1_clinics(child1)
        self._restore_r1_clinics(child2)
        
        # Restore R4 fixed assignments
        self._restore_r4_fixed_clinics(child1)
        self._restore_r4_fixed_clinics(child2)
        
        # Re-apply health check assignments for 健康 R1
        self._assign_r1_health_checks(child1)
        self._assign_r1_health_checks(child2)
        
        return child1, child2
    
    def mutate(self, schedule: Dict) -> Dict:
        """Perform mutation on a schedule"""
        if random.random() > self.mutation_rate:
            return schedule
        
        mutated = copy.deepcopy(schedule)
        
        # Try a few mutations
        num_mutations = random.randint(1, 3)
        
        for _ in range(num_mutations):
            # Pick random slot
            day = random.choice(self.days)
            time_slot = random.choice(self.time_slots)
            
            if day in mutated and time_slot in mutated[day]:
                rooms = list(mutated[day][time_slot].keys())
                if rooms:
                    room = random.choice(rooms)
                    
                    # Check if this is a fixed assignment
                    current_person = mutated[day][time_slot][room]
                    if current_person:
                        person_info = self._get_person_info(current_person)
                        # Skip mutation for any R1 assignment (clinics and health checks)
                        if person_info and person_info['level'] == 'R1':
                            continue
                        # Skip mutation for R4 fixed assignments
                        if person_info and person_info['level'] == 'R4' and person_info.get('fixed_schedule'):
                            fixed = person_info['fixed_schedule']
                            if fixed['day'] == day and fixed['time_slot'] == time_slot:
                                continue
                    
                    # Get available personnel
                    available = self._get_available_personnel(day, time_slot, room, mutated)
                    
                    if available:
                        # Include option to unassign
                        available.append(None)
                        new_person = random.choice(available)
                        mutated[day][time_slot][room] = new_person
        
        return mutated
    
    def _convert_to_api_format(self, schedule: Dict) -> Dict:
        """Convert schedule to API format with W1 prefix"""
        api_format = {}
        
        for day_idx, day in enumerate(self.days):
            if day in schedule:
                api_format[f"W1"] = api_format.get("W1", {})
                api_format["W1"][day] = {}
                
                for time_slot in self.time_slots:
                    if time_slot in schedule[day]:
                        api_format["W1"][day][time_slot] = schedule[day][time_slot]
        
        return api_format
    
    def _calculate_statistics(self, schedule: Dict) -> Dict:
        """Calculate schedule statistics"""
        stats = {
            'total_personnel': len(self.personnel_list),
            'personnel_by_level': {},
            'assignments_per_person': {},
            'coverage_rate': 0,
            'health_check_coverage': 0
        }
        
        # Count by level
        for level in ['R1', 'R2', 'R3', 'R4']:
            stats['personnel_by_level'][level] = sum(
                1 for p in self.personnel_list if p['level'] == level
            )
        
        # Count assignments per person
        total_slots = 0
        filled_slots = 0
        health_slots = 0
        filled_health = 0
        
        for day in schedule:
            for time_slot in schedule[day]:
                for room, person_id in schedule[day][time_slot].items():
                    total_slots += 1
                    if person_id:
                        filled_slots += 1
                        stats['assignments_per_person'][person_id] = \
                            stats['assignments_per_person'].get(person_id, 0) + 1
                    
                    if room in ['體檢1', '體檢2']:
                        health_slots += 1
                        if person_id:
                            filled_health += 1
        
        # Calculate rates
        stats['coverage_rate'] = (filled_slots / total_slots * 100) if total_slots > 0 else 0
        stats['health_check_coverage'] = (filled_health / health_slots * 100) if health_slots > 0 else 0
        
        # Convert to standard Python types
        for key in stats['assignments_per_person']:
            stats['assignments_per_person'][key] = int(stats['assignments_per_person'][key])
        
        stats['coverage_rate'] = float(stats['coverage_rate'])
        stats['health_check_coverage'] = float(stats['health_check_coverage'])
        
        return stats