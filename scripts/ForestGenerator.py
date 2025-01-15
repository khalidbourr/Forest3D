#!/usr/bin/env python3

import os
import numpy as np
from stl import mesh
from xml.etree import ElementTree as ET
from pathlib import Path
import sys

class WorldPopulator:
    SCALE_RANGES = {
        'tree': (0.8, 1.5),
        'rock': (0.5, 2.0),
        'bush': (0.3, 1.0),
        'grass': (0.2, 0.6),
        'sand': (1.0, 2.5)
    }

    MIN_DISTANCES = {
        'tree': 3.0,
        'bush': 2.0,
        'rock': 4.0,
        'grass': 0.5,
        'sand': 3.0
    }
    
    ZONE_WEIGHTS = {
        'tree': {'edge': 0.2, 'center': 0.8},
        'rock': {'edge': 0.8, 'center': 0.2},
        'bush': {'edge': 0.4, 'center': 0.6},
        'grass': {'edge': 0.5, 'center': 0.5},
        'sand': {'edge': 0.7, 'center': 0.3}
    }
    
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.models_path = self.base_path / "models"
        self.worlds_path = self.base_path / "worlds"
        self.placed_models = {
            'tree': [],
            'bush': [],
            'rock': [],
            'grass': [],
            'sand': []
        }
        self.model_variants = self._get_model_variants()
        self._verify_paths()

    def _verify_paths(self):
        """Verify all required paths exist"""
        required_paths = [
            self.models_path / "tree",
            self.models_path / "rock",
            self.models_path / "bush",
            self.models_path / "grass",
            self.models_path / "sand",
            self.models_path / "ground",
            self.worlds_path
        ]
        
        missing_paths = []
        for path in required_paths:
            if not path.exists():
                missing_paths.append(str(path))
        
        if missing_paths:
            print("Error: Required paths not found:")
            for path in missing_paths:
                print(f"  - {path}")
            sys.exit(1)

    def _get_model_variants(self):
        """Get available variants for each model category"""
        variants = {}
        categories = ['tree', 'bush', 'rock', 'grass', 'sand']
        
        for category in categories:
            category_path = self.models_path / category
            if category_path.exists():
                variants[category] = []
                for d in category_path.iterdir():
                    if d.is_dir() and not d.name.startswith('.'):
                        variants[category].append(d.name)
                print(f"Found {len(variants[category])} variants for {category}")
                
        return variants

    def _get_terrain_mesh(self):
        """Get terrain mesh for height sampling"""
        try:
            mesh_path = self.models_path / "ground/mesh/terrain.stl"
            if not mesh_path.exists():
                raise FileNotFoundError(f"Terrain mesh not found at: {mesh_path}")
            return mesh.Mesh.from_file(str(mesh_path))
        except Exception as e:
            print(f"Error loading terrain mesh: {e}")
            sys.exit(1)

    def _get_random_variant(self, category):
        """Get random variant with weighted probabilities"""
        variants = self.model_variants.get(category, [])
        if not variants:
            return None
            
        weights = [1.0] * len(variants)  # Equal weights by default
        return np.random.choice(variants, p=np.array(weights)/sum(weights))

    def _check_distance_to_placed(self, x, y, category):
        """Check if position is far enough from placed models"""
        min_distance = self.MIN_DISTANCES.get(category, 1.0)
        
        # Check distance to same category
        for px, py, _ in self.placed_models[category]:
            if np.sqrt((x - px)**2 + (y - py)**2) < min_distance:
                return False
        
        # Special checks for certain categories
        if category == 'tree':
            # Trees should be far from rocks and sand
            for other_category in ['rock', 'sand']:
                for px, py, _ in self.placed_models[other_category]:
                    if np.sqrt((x - px)**2 + (y - py)**2) < self.MIN_DISTANCES[other_category]:
                        return False
        
        elif category == 'bush':
            # Bushes should maintain some distance from sand
            for px, py, _ in self.placed_models['sand']:
                if np.sqrt((x - px)**2 + (y - py)**2) < self.MIN_DISTANCES['sand']:
                    return False
                    
        return True

    def _is_edge_position(self, x, y, min_x, max_x, min_y, max_y, edge_width=5.0):
        """Determine if a position is in the edge zone"""
        return (x < min_x + edge_width or x > max_x - edge_width or
                y < min_y + edge_width or y > max_y - edge_width)

    def _get_random_position(self, terrain_mesh, category, margin=2.0):
        """Get random position with improved variant distribution including sand"""
        bounds = terrain_mesh.vectors.reshape(-1, 3)
        min_x, max_x = np.min(bounds[:, 0]) + margin, np.max(bounds[:, 0]) - margin
        min_y, max_y = np.min(bounds[:, 1]) + margin, np.max(bounds[:, 1]) - margin

        max_attempts = 50
        edge_width = 5.0
        
        for _ in range(max_attempts):
            is_edge = np.random.random() < self.ZONE_WEIGHTS[category]['edge']
            
            if category == 'sand':
                if is_edge:
                    edge = np.random.choice(['top', 'bottom', 'left', 'right'])
                    if edge in ['top', 'bottom']:
                        x = np.random.uniform(min_x + margin, max_x - margin)
                        y = max_y - margin if edge == 'top' else min_y + margin
                        y += np.random.uniform(-1, 1)
                    else:
                        x = max_x - margin if edge == 'right' else min_x + margin
                        x += np.random.uniform(-1, 1)
                        y = np.random.uniform(min_y + margin, max_y - margin)
                else:
                    x = np.random.uniform(min_x + margin, max_x - margin)
                    y = np.random.uniform(min_y + margin, max_y - margin)
                
            elif category == 'tree':
                if self.placed_models['tree'] and np.random.random() < 0.7:
                    base_tree = np.random.choice(self.placed_models['tree'])
                    radius = np.random.uniform(self.MIN_DISTANCES['tree'], 
                                            self.MIN_DISTANCES['tree'] * 2)
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = base_tree[0] + radius * np.cos(angle)
                    y = base_tree[1] + radius * np.sin(angle)
                else:
                    valid_position = False
                    for _ in range(10):
                        x = np.random.uniform(min_x + margin, max_x - margin)
                        y = np.random.uniform(min_y + margin, max_y - margin)
                        if all(np.sqrt((x - sx)**2 + (y - sy)**2) > self.MIN_DISTANCES['sand'] * 2 
                              for sx, sy, _ in self.placed_models['sand']):
                            valid_position = True
                            break
                    if not valid_position:
                        continue
                    
            elif category == 'rock':
                if is_edge:
                    edge = np.random.choice(['top', 'bottom', 'left', 'right'])
                    if edge in ['top', 'bottom']:
                        x = np.random.uniform(min_x + margin, max_x - margin)
                        y = max_y - margin if edge == 'top' else min_y + margin
                    else:
                        x = max_x - margin if edge == 'right' else min_x + margin
                        y = np.random.uniform(min_y + margin, max_y - margin)
                else:
                    x = np.random.uniform(min_x + margin, max_x - margin)
                    y = np.random.uniform(min_y + margin, max_y - margin)
                    
            elif category == 'bush':
                if np.random.random() < 0.6 and self.placed_models['tree']:
                    base_tree = np.random.choice(self.placed_models['tree'])
                    radius = np.random.uniform(2.0, 4.0)
                    angle = np.random.uniform(0, 2 * np.pi)
                    x = base_tree[0] + radius * np.cos(angle)
                    y = base_tree[1] + radius * np.sin(angle)
                else:
                    x = np.random.uniform(min_x + margin, max_x - margin)
                    y = np.random.uniform(min_y + margin, max_y - margin)
            
            else:  # grass
                x = np.random.uniform(min_x + margin, max_x - margin)
                y = np.random.uniform(min_y + margin, max_y - margin)

            if (min_x <= x <= max_x and min_y <= y <= max_y and 
                self._check_distance_to_placed(x, y, category)):
                
                point = np.array([x, y])
                vectors = terrain_mesh.vectors
                distances = np.linalg.norm(vectors[:, :, :2] - point, axis=2)
                closest_tri = vectors[np.argmin(distances.min(axis=1))]
                z = np.mean(closest_tri[:, 2])

                if category == 'sand':
                    z += np.random.uniform(-0.2, 0)
                elif category == 'grass':
                    z += np.random.uniform(-0.05, 0.05)
                elif category == 'rock':
                    z += np.random.uniform(-0.1, 0.1)
                else:
                    z += np.random.uniform(-0.08, 0.08)

                self.placed_models[category].append((x, y, z))
                return x, y, z

        # Fallback position
        x = np.random.uniform(min_x + margin, max_x - margin)
        y = np.random.uniform(min_y + margin, max_y - margin)
        z = 0
        return x, y, z

    def _add_lighting(self, world):
            """Add optimized lighting to the world"""
            # Add sun with optimized settings
            sun = ET.SubElement(world, 'include')
            ET.SubElement(sun, 'uri').text = 'model://sun'
            
            # Add single ambient light with optimized settings
            ambient = ET.SubElement(world, 'light', {'name': 'ambient', 'type': 'directional'})
            ET.SubElement(ambient, 'cast_shadows').text = 'false'  # Disable shadow casting for performance
            ET.SubElement(ambient, 'pose').text = '0 0 10 0 0 0'
            ET.SubElement(ambient, 'diffuse').text = '0.8 0.8 0.8 1'
            ET.SubElement(ambient, 'specular').text = '0.1 0.1 0.1 1'
            ET.SubElement(ambient, 'direction').text = '0.1 0.1 -0.9'
            
            # Add single point light for additional illumination
            point = ET.SubElement(world, 'light', {
                'name': 'point_light',
                'type': 'point'
            })
            ET.SubElement(point, 'cast_shadows').text = 'false'
            ET.SubElement(point, 'pose').text = '0 0 10 0 0 0'
            ET.SubElement(point, 'diffuse').text = '0.3 0.3 0.3 1'
            ET.SubElement(point, 'specular').text = '0.05 0.05 0.05 1'
            ET.SubElement(point, 'attenuation')
            ET.SubElement(point, 'range').text = '30'

    def create_forest_world(self, density_config):
        """Create forest world with all variants including sand"""
        for category in self.placed_models:
            self.placed_models[category] = []
            
        world_elem = ET.Element('sdf', version="1.7")
        world = ET.SubElement(world_elem, 'world', name='forest_world')
        
        self._add_lighting(world)
        
        # Add terrain
        terrain = ET.SubElement(world, 'include')
        ET.SubElement(terrain, 'uri').text = 'model://ground'
        ET.SubElement(terrain, 'name').text = 'terrain'
        ET.SubElement(terrain, 'pose').text = '0 0 0 0 0 0'

        # Add physics
        physics = ET.SubElement(world, 'physics')
        physics.set('type', 'ode')
        ET.SubElement(physics, 'real_time_update_rate').text = '1000.0'
        ET.SubElement(physics, 'max_step_size').text = '0.001'
        ET.SubElement(physics, 'real_time_factor').text = '1'
        ET.SubElement(physics, 'gravity').text = '0 0 -9.8'

        terrain_mesh = self._get_terrain_mesh()

        # Process categories in specific order
        category_order = ['sand', 'rock', 'tree', 'bush', 'grass']
        
        for category in category_order:
            if category in density_config and category in self.model_variants:
                count = density_config[category]
                print(f"\nAdding {count} {category} models...")
                
                for i in range(count):
                    try:
                        variant = self._get_random_variant(category)
                        if not variant:
                            continue
                            
                        x, y, z = self._get_random_position(terrain_mesh, category)
                        
                        # Scale and rotation based on category
                        scale = np.random.uniform(*self.SCALE_RANGES[category])
                        
                        # Category-specific rotations
                        if category == 'sand':
                            # Sand dunes should be mostly level
                            roll = pitch = 0
                            yaw = np.random.uniform(0, 2 * np.pi)
                        elif category == 'tree':
                            # Slight random tilt for trees
                            roll = pitch = np.random.uniform(-0.05, 0.05)
                            yaw = np.random.uniform(0, 2 * np.pi)
                        elif category == 'rock':
                            # More varied rotation for rocks
                            roll = pitch = np.random.uniform(-0.15, 0.15)
                            yaw = np.random.uniform(0, 2 * np.pi)
                        else:  # bush and grass
                            roll = pitch = 0
                            yaw = np.random.uniform(0, 2 * np.pi)
                        
                        # Add model to world
                        include = ET.SubElement(world, 'include')
                        ET.SubElement(include, 'uri').text = f'model://{category}/{variant}'
                        ET.SubElement(include, 'name').text = f'{category}_{i}'
                        ET.SubElement(include, 'pose').text = f'{x} {y} {z} {roll} {pitch} {yaw}'
                        ET.SubElement(include, 'scale').text = f'{scale} {scale} {scale}'
                        
                    except Exception as e:
                        print(f"Warning: Failed to add {category} model: {e}")
                        continue

        # Save the world file
        output_path = self.worlds_path / "forest_world.world"
        tree = ET.ElementTree(world_elem)
        
        # Pretty print XML if available (Python 3.9+)
        try:
            ET.indent(tree, space="  ")
        except AttributeError:
            pass
            
        tree.write(str(output_path), encoding='utf-8', xml_declaration=True)
        
        print(f"\nWorld file created successfully at: {output_path}")
        print(f"Models placed:")
        for category in category_order:
            if category in self.placed_models:
                print(f"  - {category}: {len(self.placed_models[category])}")
        
        return output_path

    def get_model_statistics(self):
        """Get statistics about placed models"""
        stats = {
            'total_models': sum(len(models) for models in self.placed_models.values()),
            'by_category': {
                category: len(models) 
                for category, models in self.placed_models.items()
            },
            'variants_used': {
                category: len(set(v.name for v in self.model_variants.get(category, [])))
                for category in self.placed_models.keys()
            }
        }
        return stats
