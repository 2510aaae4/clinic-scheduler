"""Define daily schedule requirements based on rules"""

# Daily room requirements
DAILY_ROOM_REQUIREMENTS = {
    'Monday': {
        'Morning': ['4201', '4203', '4209', '4218', '體檢1', '體檢2'],
        'Afternoon': ['4201', '4202', '4203', '4207', '4208', '4204', '體檢1']
    },
    'Tuesday': {
        'Morning': ['4201', '4207', '4209', '體檢1', '體檢2'],
        'Afternoon': ['4201', '4204', '4205', '4208', '體檢1']
    },
    'Wednesday': {
        'Morning': ['4201', '4208', '4213', '4218', '體檢1', '體檢2'],
        'Afternoon': ['4201', '4203', '4204', '4207', '4208', '4209', '4213', '體檢1']
    },
    'Thursday': {
        'Morning': ['4201', '4213', '4218', '體檢1', '體檢2'],
        'Afternoon': ['4201', '4202', '4204', '4205', '4207', '4208', '體檢1']
    },
    'Friday': {
        'Morning': ['4201', '4205', '4218', '體檢1', '體檢2'],
        'Afternoon': ['4201', '4202', '4204', '4205', '4207', '4208', '體檢1']
    }
}

# R1 specific rules
R1_RULES = {
    'fixed_assignments': {
        '健康': {
            'Monday': {'Morning': ['體檢1'], 'Afternoon': ['4204']},  # 必須上4204診
            'Tuesday': {'Morning': ['體檢1'], 'Afternoon': ['體檢1']},
            'Wednesday': {'Morning': [], 'Afternoon': ['體檢1']},
            'Thursday': {'Morning': ['體檢1'], 'Afternoon': ['體檢1']},
            'Friday': {'Morning': ['體檢1'], 'Afternoon': ['體檢1']}
        },
        '社區1': {
            'Tuesday': {'Afternoon': ['4204']}
        }
    },
    'restrictions': {
        '病房': ['Monday', 'Friday'],  # Cannot work on these days
        '精神1': [('Monday', 'Afternoon'), ('Thursday', 'Afternoon')],  # Cannot work these slots
        '兒科病房': {'required': ('Wednesday', 'Morning', ['體檢1', '體檢2'])},
        '婦產病房': {'required': ('Wednesday', 'Morning', ['體檢1', '體檢2'])}
    },
    'max_non_health_clinics': 1,
    'default_clinic_slot': ('Afternoon', '4204')  # R1 defaults to afternoon 4204
}

# R2 specific rules
R2_RULES = {
    'fixed_assignments': {
        '社區2': {
            'Wednesday': {'Afternoon': True},  # Any available room
            'Friday': {'Morning': True}
        }
    },
    'restrictions': {
        '皮膚門診': [('Wednesday', 'Morning'), ('Wednesday', 'Afternoon')],
        '復健門診': [('Wednesday', 'Morning')]
    },
    'max_non_health_clinics': 2,
    'require_4201': True,
    'require_different_times': True  # One morning, one afternoon
}

# R3 specific rules
R3_RULES = {
    'fixed_assignments': {
        '斗六1': {
            'Tuesday': {'Morning': ['4201']}
        },
        'CR': {
            'Monday': {'Morning': True},
            'Tuesday': {'Afternoon': True},
            'Thursday': {'Afternoon': True}
        },
        '安寧2': {
            'Tuesday': {'Morning': True},
            'Wednesday': {'Afternoon': True},
            'Friday': {'Afternoon': True}
        }
    },
    'restrictions': {
        '安寧1': [('Monday', 'Morning')]
    },
    'max_non_health_clinics': 3,
    'special_cases': {
        '斗六1': 1  # Only 1 clinic for 斗六1
    },
    'require_4201': True,
    'require_morning': True  # At least one morning clinic
}

# R4 specific rules
R4_RULES = {
    'fixed_assignments': {
        '斗六2': {
            'Thursday': {'Afternoon': True}
        }
    },
    'restrictions': {
        '睡眠門診': [('Tuesday', 'Afternoon'), ('Thursday', 'Morning'), ('Thursday', 'Afternoon')],
        '旅遊門診': [('Monday', 'Afternoon'), ('Friday', 'Afternoon')],
        '骨鬆門診': [('Tuesday', 'Afternoon'), ('Thursday', 'Morning')],
        '減重門診': [('Tuesday', 'Morning'), ('Wednesday', 'Afternoon')],
        '疼痛科': [('Tuesday', 'Afternoon'), ('Friday', 'Afternoon'), ('Wednesday', 'Morning')]
    },
    'max_non_health_clinics': 3,
    'special_cases': {
        '斗六2': 1,  # Only 1 clinic for 斗六2
        '旅遊門診': 2  # Only 2 clinics for 旅遊門診
    },
    'require_morning': True,  # At least one morning clinic
    'tuesday_teaching_restriction': True  # If teaching, no clinics on Tuesday
}