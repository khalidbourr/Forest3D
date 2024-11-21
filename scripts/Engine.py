#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from TerrainGenerator import TerrainGenerator
from ForestGenerator import WorldPopulator
from B2GEngine import AssetExporter, LoadingAnimation

@dataclass
class ModelCategory:
    name: str
    files: List[str]
    default_density: int

class TerrainGeneratorCLI:
    # Rest of the code remains exactly the same...
    MODEL_CATEGORIES = {
        'tree': ModelCategory('tree', [
            "MT_PM_V60_Alnus_cremastogyne_01_01.blend",
            "MT_PM_V60_Acer_buergerianum_01_01.blend"
        ], 25),
        'bush': ModelCategory('bush', [
            "MT_PM_V60_Cistus_albidus_01_01.blend",
            "MT_PM_V60_Agave_sisalana_01_01.blend"
        ], 10),
        'grass': ModelCategory('grass', [
            "MT_PM_V60_Cynodon_dactylon_01_01.blend"
        ], 500),
        'rock': ModelCategory('rock', [
            "coast-land-rocks-04_2K_9d63d4e8-5064-4b62-8bfa-f7d45027fcf6.blend"
        ], 5),
        'sand': ModelCategory('sand', [
            "sand-dune_2K_0a625146-f652-4724-ad1f-ff705a37da8f.blend"
        ], 0)
    }

    def __init__(self):
        self.base_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description='Unified Terrain Generator for Gazebo')
        
        parser.add_argument('--mode', choices=['forest', 'terrain', 'assets'], 
                           required=True, help='Generation mode')
        parser.add_argument('--base-path', type=str,
                           default=str(self.base_path),
                           help='Base path for the project')
        parser.add_argument('--density', type=str,
                           help='JSON string with model densities')
        parser.add_argument('--config-file', type=str,
                           help='Path to JSON configuration file')
        parser.add_argument('--tif-file', type=str,
                           help='Name of the .tif file for terrain generation')
        parser.add_argument('--blender-path', type=str,
                           default="/usr/local/blender",
                           help='Path to Blender installation')
        
        return parser

    def validate_density(self, density: Dict[str, int]) -> bool:
        return all(
            category in self.MODEL_CATEGORIES and 
            isinstance(count, int) and 
            count >= 0
            for category, count in density.items()
        )

    def load_density_config(self, args) -> Dict[str, int]:
        if args.config_file:
            try:
                with open(args.config_file, 'r') as f:
                    density = json.load(f)
            except Exception as e:
                print(f"Error loading config file: {e}")
                return self.get_default_density()
        elif args.density:
            try:
                density = json.loads(args.density)
            except json.JSONDecodeError:
                print("Error: Invalid JSON string for density")
                return self.get_default_density()
        else:
            return self.get_default_density()

        return density if self.validate_density(density) else self.get_default_density()

    def get_default_density(self) -> Dict[str, int]:
        return {name: cat.default_density for name, cat in self.MODEL_CATEGORIES.items()}

    def generate_forest(self, args):
        density = self.load_density_config(args)
        populator = WorldPopulator(Path(args.base_path))
        world_path = populator.create_forest_world(density)
        
        print(f"\nForest world created at: {world_path}")
        self._print_gazebo_instructions(world_path)

    def generate_terrain(self, args):
        if not args.tif_file:
            raise ValueError("--tif-file required for terrain generation")
            
        generator = TerrainGenerator(args.tif_file)
        model_path = generator.process_terrain()
        
        print(f"\nTerrain generation completed at: {model_path}")
        self._print_gazebo_instructions(model_path)

    def process_assets(self, args):
        blend_files_path = self.base_path / "Blender-Assets"
        models_base_dir = self.base_path / "models"
        
        with LoadingAnimation() as loading:
            exporter = AssetExporter(args.blender_path)
            
            for category, model_cat in self.MODEL_CATEGORIES.items():
                loading.update(f"Processing {category} category")
                category_dir = models_base_dir / category
                
                for model in model_cat.files:
                    blend_path = blend_files_path / model
                    exporter.process_asset(blend_path, category_dir)

    def _print_gazebo_instructions(self, path: Path):
        print("\nTo view in Gazebo:")
        print(f"export GAZEBO_MODEL_PATH={self.base_path}/models")
        print(f"gazebo {path}")

    def run(self):
        try:
            args = self.parser.parse_args()
            
            mode_handlers = {
                'forest': self.generate_forest,
                'terrain': self.generate_terrain,
                'assets': self.process_assets
            }
            
            mode_handlers[args.mode](args)
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\nError: {str(e)}")
            self.parser.print_help()
            sys.exit(1)

if __name__ == "__main__":
    TerrainGeneratorCLI().run()

