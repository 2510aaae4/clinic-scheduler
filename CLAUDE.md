# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a clinic scheduling system that uses a genetic algorithm to automatically assign medical personnel (R1-R4 residents) to clinic shifts. The system is built with Flask (Python) backend and vanilla JavaScript frontend.

## Common Development Commands

### Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Application
```bash
python app.py              # Development server on http://localhost:5001
gunicorn app:app          # Production server
```

### Testing
```bash
pytest tests/                        # Run all tests
pytest tests/test_scheduler.py -v    # Run with verbose output
pytest --cov=modules tests/          # Run with coverage report
pytest -k "test_genetic_scheduler"   # Run specific test by name pattern
```

## Architecture Overview

### Core Components

1. **Genetic Algorithm Engine** (`modules/genetic_scheduler_v2.py`)
   - Implements adaptive population sizing based on problem complexity
   - Uses R1-focused initialization to handle the most constrained personnel first
   - Multi-objective fitness function balancing multiple scheduling constraints

2. **Constraint System** (`modules/fitness_evaluator.py`)
   - Enforces complex scheduling rules for each personnel level
   - Handles rotation unit requirements, health check assignments, and teaching exemptions
   - Priority system: R1 (highest), R2, R3, R4 (lowest)

3. **Data Flow**
   - Input: Personnel data uploaded via web interface
   - Processing: GA runs for up to 180 seconds
   - Output: Three CSV formats (basic, personal, statistics)

### Key Architectural Decisions

- **No Database**: Uses CSV files and temporary storage instead of a database
- **Stateless Design**: Each scheduling request is independent
- **Configuration-Driven**: Rules stored in `data/rules.json`, settings in `config/settings.py`
- **Modular Structure**: Clear separation between scheduling logic, validation, and export functionality

### Important Files to Understand

- `app.py`: REST API endpoints and request handling
- `modules/genetic_scheduler_v2.py`: Core GA implementation
- `modules/r1_scheduler.py`: R1-specific scheduling logic (most complex)
- `config/settings.py`: All configuration parameters including GA settings
- `static/js/main.js`: Frontend logic and API interaction

### Scheduling Constraints

The system handles complex medical scheduling rules:
- Personnel levels (R1-R4) have different rotation units and priorities
- R1s require specific unit assignments matching their training
- R4s are exempt from Tuesday teaching duties
- Health check assignments follow a priority system
- No double-booking allowed across all rooms and time slots