import os

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Application settings
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'csv', 'json'}
    
    # Genetic Algorithm default parameters
    GA_DEFAULT_POPULATION_SIZE = 300  # Reduced for 1 week
    GA_DEFAULT_GENERATIONS = 500  # Reduced for 1 week
    GA_DEFAULT_ELITE_PERCENTAGE = 0.1
    GA_DEFAULT_MUTATION_RATE = 0.15
    GA_DEFAULT_CROSSOVER_RATE = 0.8
    GA_DEFAULT_TOURNAMENT_SIZE = 5
    GA_DEFAULT_CONVERGENCE_THRESHOLD = 30  # Reduced for faster convergence
    GA_DEFAULT_PARALLEL_POPULATIONS = 3
    GA_DEFAULT_MIGRATION_INTERVAL = 20
    GA_DEFAULT_MIGRATION_SIZE = 5
    
    # Personnel default counts
    DEFAULT_PERSONNEL_COUNTS = {
        'R1': 5,
        'R2': 6,
        'R3': 4,
        'R4': 6
    }
    
    # Personnel limits
    MIN_PERSONNEL_COUNT = 1
    MAX_PERSONNEL_COUNT = 10
    
    # Clinic rooms
    CLINIC_ROOMS = ['4201', '4202', '4203', '4204', '4205', '4207', '4208', '4209', '4213', '4218']
    HEALTH_CHECK_ROOMS = ['體檢1', '體檢2']
    
    # Time slots
    TIME_SLOTS = ['Morning', 'Afternoon']
    WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    TOTAL_WEEKS = 1
    
    # Rotation units by level
    ROTATION_UNITS = {
        'R1': ['內科病房', '健康', '急診', '兒科病房', '精神1', '社區1', '婦產病房', '放射'],
        'R2': ['婦產門診', '內科病房', '兒科門診', '外科病房', '社區2', '眼科門診', '皮膚門診', 
               '神內門診', '復健門診', 'ENT門診', '精神2', '家庭醫業'],
        'R3': ['CR', '斗六1', '神內門診', '泌尿門診', '糖尿病衛教', '安寧1', '老醫門診', 
               '安寧2', '內科門診', '放射'],
        'R4': ['睡眠門診', '旅遊門診', '骨鬆門診', '減重門診', '疼痛科', '斗六2', '其他']
    }
    
    # File paths
    TEMP_FOLDER = 'data/temp'
    RULES_FILE = 'data/rules.json'
    
    # Export settings
    CSV_ENCODING = 'utf-8-sig'  # UTF-8 with BOM for Excel compatibility
    
    # Performance settings
    MAX_PROCESSING_TIME = 180  # seconds
    CLEANUP_INTERVAL = 3600  # Clean temp files every hour
    
    @staticmethod
    def get_ga_config(personnel_count):
        """Get dynamic GA configuration based on problem size"""
        base_config = {
            "population_size": Config.GA_DEFAULT_POPULATION_SIZE,
            "max_generations": Config.GA_DEFAULT_GENERATIONS,
            "elite_percentage": Config.GA_DEFAULT_ELITE_PERCENTAGE,
            "mutation_rate": Config.GA_DEFAULT_MUTATION_RATE,
            "crossover_rate": Config.GA_DEFAULT_CROSSOVER_RATE,
            "tournament_size": Config.GA_DEFAULT_TOURNAMENT_SIZE,
            "convergence_threshold": Config.GA_DEFAULT_CONVERGENCE_THRESHOLD,
            "parallel_populations": Config.GA_DEFAULT_PARALLEL_POPULATIONS,
            "migration_interval": Config.GA_DEFAULT_MIGRATION_INTERVAL,
            "migration_size": Config.GA_DEFAULT_MIGRATION_SIZE
        }
        
        # Adjust for problem complexity (but keep it reasonable for 1 week)
        default_total = sum(Config.DEFAULT_PERSONNEL_COUNTS.values())
        if personnel_count > default_total:
            complexity_ratio = personnel_count / default_total
            base_config["population_size"] = min(500, int(Config.GA_DEFAULT_POPULATION_SIZE * complexity_ratio ** 1.2))
            base_config["max_generations"] = min(800, int(Config.GA_DEFAULT_GENERATIONS * complexity_ratio ** 0.8))
            
        return base_config