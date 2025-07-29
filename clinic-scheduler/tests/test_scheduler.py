import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.genetic_scheduler import GeneticScheduler
from modules.validators import InputValidator
from modules.data_handler import DataHandler
from modules.export_handler import ExportHandler
from config.settings import Config
import numpy as np


class TestGeneticScheduler(unittest.TestCase):
    """Test cases for genetic algorithm scheduler"""
    
    def setUp(self):
        """Set up test data"""
        self.test_personnel = {
            'R1': {
                'R1_A': {'rotation_unit': 'e·', 'health_check': True},
                'R1_B': {'rotation_unit': 'gÑÅ?', 'health_check': True},
                'R1_C': {'rotation_unit': '%:', 'health_check': False}
            },
            'R2': {
                'R2_A': {'rotation_unit': 'f"€:', 'health_check': False},
                'R2_B': {'rotation_unit': 'gÑÅ?', 'health_check': True}
            },
            'R3': {
                'R3_A': {'rotation_unit': 'CR', 'health_check': False}
            },
            'R4': {
                'R4_A': {'rotation_unit': 'vÖ', 'health_check': False, 'tuesday_teaching': True},
                'R4_B': {'rotation_unit': 'a €:', 'health_check': False, 'tuesday_teaching': False}
            }
        }
        
        self.test_rules = DataHandler.get_default_rules()
        
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        scheduler = GeneticScheduler(self.test_personnel, self.test_rules)
        
        self.assertEqual(scheduler.total_personnel, 8)
        self.assertTrue(scheduler.population_size > 0)
        self.assertEqual(len(scheduler.personnel_list), 8)
        
    def test_dynamic_population_size(self):
        """Test population size adaptation"""
        # Small personnel count
        small_personnel = {
            'R1': {'R1_A': {'rotation_unit': 'e·', 'health_check': True}},
            'R2': {'R2_A': {'rotation_unit': 'gÑÅ?', 'health_check': False}},
            'R3': {},
            'R4': {}
        }
        scheduler_small = GeneticScheduler(small_personnel, self.test_rules)
        
        # Large personnel count
        large_personnel = {
            'R1': {f'R1_{chr(65+i)}': {'rotation_unit': 'e·', 'health_check': True} 
                   for i in range(8)},
            'R2': {f'R2_{chr(65+i)}': {'rotation_unit': 'gÑÅ?', 'health_check': False} 
                   for i in range(8)},
            'R3': {f'R3_{chr(65+i)}': {'rotation_unit': 'CR', 'health_check': False} 
                   for i in range(6)},
            'R4': {f'R4_{chr(65+i)}': {'rotation_unit': 'vÖ', 'health_check': False} 
                   for i in range(8)}
        }
        scheduler_large = GeneticScheduler(large_personnel, self.test_rules)
        
        # Population should scale with complexity
        self.assertTrue(scheduler_large.population_size > scheduler_small.population_size)
        
    def test_r1_focused_chromosome(self):
        """Test R1-focused initialization strategy"""
        scheduler = GeneticScheduler(self.test_personnel, self.test_rules)
        chromosome = scheduler.create_r1_focused_chromosome()
        
        # Check chromosome shape
        expected_shape = (5, 5, 2, 12)  # weeks, days, time_slots, rooms
        self.assertEqual(chromosome.shape, expected_shape)
        
        # Check that health check rooms have assignments
        health_room_start = len(Config.CLINIC_ROOMS)
        health_assignments = chromosome[:, :, :, health_room_start:]
        
        # Should have some health check assignments
        self.assertTrue(np.any(health_assignments >= 0))
        
    def test_fitness_calculation(self):
        """Test fitness function"""
        scheduler = GeneticScheduler(self.test_personnel, self.test_rules)
        
        # Create a valid chromosome
        chromosome = scheduler.create_r1_focused_chromosome()
        fitness = scheduler.fitness(chromosome)
        
        # Fitness should be a number
        self.assertIsInstance(fitness, (int, float))
        
        # Create an invalid chromosome (double booking)
        bad_chromosome = chromosome.copy()
        bad_chromosome[0, 0, 0, 0] = 0  # Person 0 in room 0
        bad_chromosome[0, 0, 0, 1] = 0  # Same person in room 1 (conflict!)
        
        bad_fitness = scheduler.fitness(bad_chromosome)
        
        # Bad chromosome should have lower fitness
        self.assertTrue(bad_fitness < fitness)
        
    def test_genetic_operations(self):
        """Test crossover and mutation"""
        scheduler = GeneticScheduler(self.test_personnel, self.test_rules)
        
        parent1 = scheduler.create_r1_focused_chromosome()
        parent2 = scheduler.create_r1_focused_chromosome()
        
        # Test crossover
        child1, child2 = scheduler.crossover(parent1, parent2)
        self.assertEqual(child1.shape, parent1.shape)
        self.assertEqual(child2.shape, parent2.shape)
        
        # Test mutation
        mutated = scheduler.mutate(parent1.copy())
        self.assertEqual(mutated.shape, parent1.shape)
        

class TestValidators(unittest.TestCase):
    """Test cases for input validators"""
    
    def setUp(self):
        """Set up validator"""
        self.validator = InputValidator()
        
    def test_valid_input(self):
        """Test validation of valid input"""
        valid_data = {
            'personnel_counts': {'R1': 5, 'R2': 6, 'R3': 4, 'R4': 6},
            'personnel': {
                'R1': {
                    'R1_A': {'rotation_unit': 'e·', 'health_check': True}
                },
                'R2': {
                    'R2_A': {'rotation_unit': 'gÑÅ?', 'health_check': False}
                }
            }
        }
        
        result = self.validator.validate_input(valid_data)
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        
    def test_invalid_rotation_unit(self):
        """Test validation of invalid rotation unit"""
        invalid_data = {
            'personnel': {
                'R1': {
                    'R1_A': {'rotation_unit': 'X(„®M', 'health_check': True}
                }
            }
        }
        
        result = self.validator.validate_input(invalid_data)
        self.assertFalse(result['valid'])
        self.assertTrue(any('Invalid rotation unit' in error for error in result['errors']))
        
    def test_personnel_count_validation(self):
        """Test personnel count limits"""
        # Test too many personnel
        invalid_data = {
            'personnel_counts': {'R1': 15}  # Exceeds max of 10
        }
        
        result = self.validator.validate_input(invalid_data)
        self.assertFalse(result['valid'])
        
        # Test too few personnel
        invalid_data = {
            'personnel_counts': {'R1': 0}  # Below min of 1
        }
        
        result = self.validator.validate_input(invalid_data)
        self.assertFalse(result['valid'])
        

class TestDataHandler(unittest.TestCase):
    """Test cases for data handling"""
    
    def test_parse_personnel_data(self):
        """Test personnel data parsing"""
        raw_data = {
            'personnel': {
                'R1': {
                    'R1_A': {
                        'rotation_unit': 'e·',
                        'health_check': True
                    }
                }
            }
        }
        
        parsed = DataHandler.parse_personnel_data(raw_data)
        
        self.assertIn('R1', parsed)
        self.assertIn('R1_A', parsed['R1'])
        self.assertEqual(parsed['R1']['R1_A']['rotation_unit'], 'e·')
        self.assertTrue(parsed['R1']['R1_A']['health_check'])
        
    def test_default_rules_loading(self):
        """Test loading default rules"""
        rules = DataHandler.get_default_rules()
        
        self.assertIn('unit_constraints', rules)
        self.assertIn('general_rules', rules)
        self.assertIn('e·', rules['unit_constraints'])
        

class TestExportHandler(unittest.TestCase):
    """Test cases for export functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.test_schedule = {
            'W1': {
                'Monday': {
                    'Morning': {
                        '4201': 'R1_A',
                        '4202': 'R2_A',
                        'Ô¢1': 'R1_B'
                    }
                }
            }
        }
        
        self.test_personnel = {
            'R1': {
                'R1_A': {'rotation_unit': 'e·'},
                'R1_B': {'rotation_unit': 'gÑÅ?'}
            },
            'R2': {
                'R2_A': {'rotation_unit': 'f"€:'}
            }
        }
        
    def test_basic_csv_generation(self):
        """Test basic CSV format generation"""
        exporter = ExportHandler(self.test_schedule, self.test_personnel)
        csv_content = exporter.generate_basic_csv()
        
        self.assertIsInstance(csv_content, str)
        self.assertIn('Week,Day,Time', csv_content)
        self.assertIn('R1_A', csv_content)
        
    def test_personal_csv_generation(self):
        """Test personal view CSV generation"""
        exporter = ExportHandler(self.test_schedule, self.test_personnel)
        csv_content = exporter.generate_personal_csv()
        
        self.assertIsInstance(csv_content, str)
        self.assertIn('ºá,%,*®M', csv_content)
        
    def test_statistics_csv_generation(self):
        """Test statistics CSV generation"""
        exporter = ExportHandler(self.test_schedule, self.test_personnel)
        csv_content = exporter.generate_statistics_csv()
        
        self.assertIsInstance(csv_content, str)
        self.assertIn('qî,x<', csv_content)
        self.assertIn('=ºáx', csv_content)
        

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_scheduling_workflow(self):
        """Test complete scheduling workflow"""
        # Prepare test data
        personnel_data = {
            'R1': {
                'R1_A': {'rotation_unit': 'e·', 'health_check': True},
                'R1_B': {'rotation_unit': 'gÑÅ?', 'health_check': True}
            },
            'R2': {
                'R2_A': {'rotation_unit': 'f"€:', 'health_check': False}
            },
            'R3': {
                'R3_A': {'rotation_unit': 'CR', 'health_check': False}
            },
            'R4': {
                'R4_A': {'rotation_unit': 'vÖ', 'health_check': False, 'tuesday_teaching': False}
            }
        }
        
        rules = DataHandler.get_default_rules()
        
        # Run scheduler with limited generations for testing
        scheduler = GeneticScheduler(personnel_data, rules, generations=10)
        result = scheduler.run()
        
        # Check result structure
        self.assertIn('success', result)
        self.assertIn('schedule', result)
        self.assertIn('statistics', result)
        
        if result['success']:
            # Verify schedule has expected structure
            schedule = result['schedule']
            self.assertIn('W1', schedule)
            
            # Check statistics
            stats = result['statistics']
            self.assertEqual(stats['total_personnel'], 5)
            

if __name__ == '__main__':
    unittest.main()