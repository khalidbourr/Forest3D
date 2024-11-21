#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
import sys
import json
from ForestGenerator import WorldPopulator

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate a forest world for Gazebo simulation')
    
    parser.add_argument('--base-path', type=str,
                        default=str(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                        help='Base path for the project')
    
    parser.add_argument('--density', type=str,
                        help='JSON string with model densities (e.g., \'{"tree":10, "rock":5}\')')
    
    parser.add_argument('--config-file', type=str,
                        help='Path to JSON configuration file')
    
    return parser.parse_args()

def load_default_density():
    """Load default density configuration"""
    return {
        'rock': 5,     # Number of rocks
        'tree': 25,    # Number of trees
        'bush': 10,     # Number of bushes
        'grass': 500    # Number of grass patches
    }

def load_config_file(config_path):
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return None

def validate_density(density):
    """Validate density configuration"""
    valid_categories = ['sand', 'rock', 'tree', 'bush', 'grass']
    
    if not isinstance(density, dict):
        return False
        
    for category, count in density.items():
        if category not in valid_categories:
            print(f"Warning: Invalid category '{category}' in density configuration")
            return False
        if not isinstance(count, int) or count < 0:
            print(f"Warning: Invalid count for {category}: {count}")
            return False
            
    return True

def main():
    try:
        # Parse command-line arguments
        args = parse_arguments()
        
        # Determine base path
        base_path = Path(args.base_path)
        if not base_path.exists():
            print(f"Error: Base path does not exist: {base_path}")
            sys.exit(1)
            
        # Load density configuration
        if args.config_file:
            density = load_config_file(args.config_file)
            if not density:
                print("Using default density configuration")
                density = load_default_density()
        elif args.density:
            try:
                density = json.loads(args.density)
            except json.JSONDecodeError:
                print("Error: Invalid JSON string for density")
                sys.exit(1)
        else:
            density = load_default_density()
            
        # Validate density configuration
        if not validate_density(density):
            print("Error: Invalid density configuration")
            sys.exit(1)
            
        print("\nInitializing World Populator...")
        print(f"Base path: {base_path}")
        print("\nDensity configuration:")
        for category, count in density.items():
            print(f"  {category}: {count}")
            
        # Create and populate the world
        populator = WorldPopulator(base_path)
        
        print("\nGenerating forest world...")
        world_path = populator.create_forest_world(density)

        print(f"\nSuccess! Forest world created at: {world_path}")
        print(f"\nTo view in Gazebo:")
        print(f"export GAZEBO_MODEL_PATH={base_path}/models")
        print(f"gazebo {world_path}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
