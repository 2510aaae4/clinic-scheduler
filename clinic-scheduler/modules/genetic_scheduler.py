import numpy as np
import random
from typing import List, Dict, Tuple, Any
import copy
from config.settings import Config
from modules.fitness_evaluator import FitnessEvaluator
from modules.schedule_requirements import DAILY_ROOM_REQUIREMENTS

class GeneticScheduler:
    def __init__(self, personnel_data: Dict, rules: Dict, population_size: int = None, generations: int = 1000):
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
        self.weeks = Config.TOTAL_WEEKS
        self.days = Config.WEEKDAYS
        self.time_slots = Config.TIME_SLOTS
        self.clinic_rooms = Config.CLINIC_ROOMS
        self.health_check_rooms = Config.HEALTH_CHECK_ROOMS
        
        # Track best solution
        self.best_fitness = float('-inf')
        self.best_solution = None
        self.no_improvement_count = 0
        
        # Create personnel list with metadata
        self.personnel_list = self._create_personnel_list()
        
    def _create_personnel_list(self) -> List[Dict]:
        """Create flat list of all personnel with their metadata"""
        personnel_list = []
        
        for level, people in self.personnel_data.items():
            for person_id, data in people.items():
                personnel_list.append({
                    'id': person_id,
                    'level': level,
                    'rotation_unit': data['rotation_unit'],
                    'health_check': data.get('health_check', False),
                    'tuesday_teaching': data.get('tuesday_teaching', False)
                })
                
        return personnel_list
    
    def calculate_population_size(self) -> int:
        """Calculate optimal population size based on personnel count"""
        base_size = 500
        complexity_factor = self.total_personnel / 21  # 21 is default total
        return int(base_size * max(1.0, complexity_factor ** 1.5))
    
    def initialize_population(self) -> List[np.ndarray]:
        """Create initial population with R1-focused strategy"""
        population = []
        
        # Generate chromosomes prioritizing R1 assignments
        for _ in range(self.population_size):
            chromosome = self.create_r1_focused_chromosome()
            population.append(chromosome)
            
        return population
    
    def create_r1_focused_chromosome(self) -> np.ndarray:
        """Create a chromosome with R1 personnel prioritized for health checks"""
        # Initialize empty schedule (weeks x days x time_slots x rooms)
        total_rooms = len(self.clinic_rooms) + len(self.health_check_rooms)
        chromosome = np.full(
            (self.weeks, len(self.days), len(self.time_slots), total_rooms),
            -1,  # -1 means no assignment
            dtype=int
        )
        
        # Get R1 personnel who can do health checks
        r1_health_check = [
            i for i, p in enumerate(self.personnel_list)
            if p['level'] == 'R1' and p['health_check']
        ]
        
        # First, assign R1 personnel to health check rooms
        for week in range(self.weeks):
            for day_idx, day in enumerate(self.days):
                for time_idx, time_slot in enumerate(self.time_slots):
                    # Skip Tuesday teaching slots for R4
                    if day == 'Tuesday' and any(
                        p['tuesday_teaching'] for p in self.personnel_list
                    ):
                        continue
                    
                    # Assign health check rooms first
                    health_room_offset = len(self.clinic_rooms)
                    for room_idx in range(len(self.health_check_rooms)):
                        if r1_health_check:
                            person_idx = random.choice(r1_health_check)
                            chromosome[week, day_idx, time_idx, health_room_offset + room_idx] = person_idx
        
        # Then assign remaining personnel to clinic rooms
        for week in range(self.weeks):
            for day_idx, day in enumerate(self.days):
                for time_idx, time_slot in enumerate(self.time_slots):
                    # Get available personnel for this slot
                    available = self._get_available_personnel(
                        chromosome, week, day_idx, time_idx
                    )
                    
                    # Assign to clinic rooms
                    room_indices = list(range(len(self.clinic_rooms)))
                    random.shuffle(room_indices)
                    
                    for room_idx in room_indices:
                        if available:
                            person_idx = random.choice(available)
                            chromosome[week, day_idx, time_idx, room_idx] = person_idx
                            available.remove(person_idx)
                            
        return chromosome
    
    def _get_available_personnel(self, chromosome: np.ndarray, week: int, 
                                day_idx: int, time_idx: int) -> List[int]:
        """Get list of personnel available for assignment"""
        # Get already assigned personnel in this time slot
        assigned = set(chromosome[week, day_idx, time_idx, :])
        assigned.discard(-1)  # Remove empty slots
        
        available = []
        for i, person in enumerate(self.personnel_list):
            # Skip if already assigned
            if i in assigned:
                continue
                
            # Skip R4 with Tuesday teaching
            if (self.days[day_idx] == 'Tuesday' and 
                person['tuesday_teaching']):
                continue
                
            available.append(i)
            
        return available
    
    def fitness(self, chromosome: np.ndarray) -> float:
        """Calculate fitness score for a chromosome"""
        score = 0.0
        penalties = 0.0
        
        # Check hard constraints
        # 1. No person in multiple rooms at same time
        for week in range(self.weeks):
            for day in range(len(self.days)):
                for time in range(len(self.time_slots)):
                    assignments = chromosome[week, day, time, :]
                    valid_assignments = assignments[assignments >= 0]
                    if len(valid_assignments) != len(set(valid_assignments)):
                        penalties += 100  # Heavy penalty for double booking
        
        # 2. Health check rooms must be filled by appropriate personnel
        health_room_offset = len(self.clinic_rooms)
        for week in range(self.weeks):
            for day in range(len(self.days)):
                for time in range(len(self.time_slots)):
                    for room_idx in range(len(self.health_check_rooms)):
                        person_idx = chromosome[week, day, time, health_room_offset + room_idx]
                        if person_idx >= 0:
                            person = self.personnel_list[person_idx]
                            if not person['health_check']:
                                penalties += 50  # Penalty for wrong assignment
                        else:
                            penalties += 20  # Penalty for empty health check room
        
        # 3. R4 Tuesday teaching constraint
        for week in range(self.weeks):
            tuesday_idx = self.days.index('Tuesday')
            for time in range(len(self.time_slots)):
                assignments = chromosome[week, tuesday_idx, time, :]
                for person_idx in assignments:
                    if person_idx >= 0:
                        person = self.personnel_list[person_idx]
                        if person['tuesday_teaching']:
                            penalties += 100  # Heavy penalty
        
        # 4. Rotation unit constraints
        for person_idx, person in enumerate(self.personnel_list):
            unit = person['rotation_unit']
            if unit in self.rules.get('unit_constraints', {}):
                constraints = self.rules['unit_constraints'][unit]
                
                # Count assignments
                person_assignments = np.sum(chromosome == person_idx)
                
                min_clinics = constraints.get('min_clinics', 0)
                max_clinics = constraints.get('max_clinics', float('inf'))
                
                if person_assignments < min_clinics:
                    penalties += 10 * (min_clinics - person_assignments)
                elif person_assignments > max_clinics:
                    penalties += 10 * (person_assignments - max_clinics)
        
        # 5. Calculate coverage score
        total_slots = self.weeks * len(self.days) * len(self.time_slots) * len(self.clinic_rooms)
        filled_slots = np.sum(chromosome[:, :, :, :len(self.clinic_rooms)] >= 0)
        coverage_score = (filled_slots / total_slots) * 100
        
        # 6. Distribution score (prefer even distribution)
        distribution_score = self._calculate_distribution_score(chromosome)
        
        # Calculate final fitness
        fitness = coverage_score + distribution_score - penalties
        
        return fitness
    
    def _calculate_distribution_score(self, chromosome: np.ndarray) -> float:
        """Calculate how evenly work is distributed"""
        assignments_per_person = []
        
        for person_idx in range(len(self.personnel_list)):
            count = np.sum(chromosome == person_idx)
            assignments_per_person.append(count)
        
        if not assignments_per_person:
            return 0.0
            
        mean_assignments = np.mean(assignments_per_person)
        std_assignments = np.std(assignments_per_person)
        
        # Lower standard deviation is better
        if mean_assignments > 0:
            distribution_score = 50 * (1 - std_assignments / mean_assignments)
        else:
            distribution_score = 0.0
            
        return max(0, distribution_score)
    
    def crossover(self, parent1: np.ndarray, parent2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Perform crossover between two parents"""
        if random.random() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        if self.weeks > 1:
            # Week-based crossover for multiple weeks
            crossover_point = random.randint(1, self.weeks - 1)
            child1[crossover_point:] = parent2[crossover_point:]
            child2[crossover_point:] = parent1[crossover_point:]
        else:
            # Day-based crossover for single week
            crossover_day = random.randint(1, len(self.days) - 1)
            child1[0, crossover_day:] = parent2[0, crossover_day:]
            child2[0, crossover_day:] = parent1[0, crossover_day:]
        
        return child1, child2
    
    def mutate(self, chromosome: np.ndarray) -> np.ndarray:
        """Perform mutation on a chromosome"""
        if random.random() > self.mutation_rate:
            return chromosome
        
        mutated = chromosome.copy()
        
        # Random swap mutation
        num_mutations = random.randint(1, 3)
        
        for _ in range(num_mutations):
            # Select random time slot
            week = random.randint(0, self.weeks - 1)
            day = random.randint(0, len(self.days) - 1)
            time = random.randint(0, len(self.time_slots) - 1)
            
            # Select two random rooms
            room1 = random.randint(0, len(self.clinic_rooms) + len(self.health_check_rooms) - 1)
            room2 = random.randint(0, len(self.clinic_rooms) + len(self.health_check_rooms) - 1)
            
            # Swap assignments
            temp = mutated[week, day, time, room1]
            mutated[week, day, time, room1] = mutated[week, day, time, room2]
            mutated[week, day, time, room2] = temp
        
        return mutated
    
    def tournament_selection(self, population: List[np.ndarray], 
                           fitness_scores: List[float]) -> np.ndarray:
        """Select individual using tournament selection"""
        tournament_indices = random.sample(range(len(population)), self.tournament_size)
        tournament_fitness = [fitness_scores[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx]
    
    def run(self) -> Dict[str, Any]:
        """Run the genetic algorithm"""
        # Initialize population
        population = self.initialize_population()
        
        for generation in range(self.generations):
            # Calculate fitness for all individuals
            fitness_scores = [self.fitness(chromosome) for chromosome in population]
            
            # Track best solution
            best_idx = np.argmax(fitness_scores)
            if fitness_scores[best_idx] > self.best_fitness:
                self.best_fitness = float(fitness_scores[best_idx])  # Convert to Python float
                self.best_solution = population[best_idx].copy()
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
            elite_indices = np.argsort(fitness_scores)[-self.elite_size:]
            for idx in elite_indices:
                new_population.append(population[idx].copy())
            
            # Generate rest of population
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
        
        # Convert best solution to schedule format
        if self.best_solution is not None:
            schedule = self._chromosome_to_schedule(self.best_solution)
            statistics = self._calculate_statistics(self.best_solution)
            
            return {
                'success': True,
                'schedule': schedule,
                'statistics': statistics,
                'fitness': float(self.best_fitness),  # Convert to Python float
                'generations': int(generation + 1)  # Convert to Python int
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
    
    def _chromosome_to_schedule(self, chromosome: np.ndarray) -> Dict[str, Any]:
        """Convert chromosome to readable schedule format"""
        schedule = {}
        
        for week in range(self.weeks):
            week_key = f"W{week + 1}"
            schedule[week_key] = {}
            
            for day_idx, day in enumerate(self.days):
                schedule[week_key][day] = {}
                
                for time_idx, time_slot in enumerate(self.time_slots):
                    schedule[week_key][day][time_slot] = {}
                    
                    # Clinic rooms
                    for room_idx, room in enumerate(self.clinic_rooms):
                        person_idx = chromosome[week, day_idx, time_idx, room_idx]
                        if person_idx >= 0:
                            person = self.personnel_list[person_idx]
                            schedule[week_key][day][time_slot][room] = person['id']
                        else:
                            schedule[week_key][day][time_slot][room] = None
                    
                    # Health check rooms
                    health_offset = len(self.clinic_rooms)
                    for room_idx, room in enumerate(self.health_check_rooms):
                        person_idx = chromosome[week, day_idx, time_idx, health_offset + room_idx]
                        if person_idx >= 0:
                            person = self.personnel_list[person_idx]
                            schedule[week_key][day][time_slot][room] = person['id']
                        else:
                            schedule[week_key][day][time_slot][room] = None
                            
        return schedule
    
    def _calculate_statistics(self, chromosome: np.ndarray) -> Dict[str, Any]:
        """Calculate schedule statistics"""
        stats = {
            'total_personnel': self.total_personnel,
            'personnel_by_level': {
                level: len(people) for level, people in self.personnel_data.items()
            },
            'total_clinic_slots': self.weeks * len(self.days) * len(self.time_slots) * len(self.clinic_rooms),
            'total_health_check_slots': self.weeks * len(self.days) * len(self.time_slots) * len(self.health_check_rooms),
            'assignments_per_person': {},
            'coverage_rate': 0,
            'health_check_coverage': 0
        }
        
        # Count assignments per person
        for person_idx, person in enumerate(self.personnel_list):
            count = np.sum(chromosome == person_idx)
            # Convert numpy int64 to Python int
            stats['assignments_per_person'][person['id']] = int(count)
        
        # Calculate coverage rates
        clinic_filled = np.sum(chromosome[:, :, :, :len(self.clinic_rooms)] >= 0)
        # Convert numpy float64 to Python float
        stats['coverage_rate'] = float((clinic_filled / stats['total_clinic_slots']) * 100)
        
        health_filled = np.sum(chromosome[:, :, :, len(self.clinic_rooms):] >= 0)
        # Convert numpy float64 to Python float
        stats['health_check_coverage'] = float((health_filled / stats['total_health_check_slots']) * 100)
        
        return stats