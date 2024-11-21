#!/usr/bin/env python3
import numpy as np
from osgeo import gdal
import os
from stl import mesh
from xml.etree import ElementTree as ET
from scipy.ndimage import gaussian_filter
from pathlib import Path
import sys
import shutil
import argparse

class TerrainGenerator:
    def __init__(self, tif_filename: str):
        self.base_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.dem_path = self.base_path / "models/ground/dem"
        self.terrain_path = self.base_path / "models/ground"
        self.mesh_path = self.terrain_path / "mesh"
        self.material_path = self.terrain_path / "material" 
        self.texture_path = self.terrain_path / "texture"
        self.worlds_path = self.base_path / "worlds"
        self.tif_filename = tif_filename
        
        self._verify_paths()

    def _verify_paths(self):
        """Verify all required paths and files exist"""
        for path in [self.dem_path, self.mesh_path, self.material_path, 
                    self.texture_path, self.worlds_path]:
            path.mkdir(parents=True, exist_ok=True)
            print(f"Created/verified directory: {path}")
            
        required_files = [
            (self.dem_path / self.tif_filename, "DEM file"),
            (self.material_path / "terrain.material", "Material file"),
            (self.texture_path / "moss_basecolor.png", "Texture file")
        ]    
        
        missing_files = []
        for file_path, description in required_files:
            if not file_path.exists():
                missing_files.append(f"{description} not found at {file_path}")
                print(f"Missing: {file_path}")
        
        if missing_files:

            raise FileNotFoundError("\n".join(missing_files))

    def enhance_resolution(self, scale_factor=6.0):
        """Enhance DEM resolution"""
        input_tiff = self.dem_path / self.tif_filename
        output_tiff = self.dem_path / "terrain_enhanced.tif"
        heightmap_tiff = self.dem_path / "enhanced_heightmap.tif"
        
        try:
            ds = gdal.Open(str(input_tiff))
            if ds is None:
                raise ValueError(f"Failed to open {input_tiff}")
            
            gdal.Warp(
                str(output_tiff),
                ds,
                width=int(ds.RasterXSize * scale_factor),
                height=int(ds.RasterYSize * scale_factor),
                resampleAlg=gdal.GRA_CubicSpline,
                options=['COMPRESS=LZW']
            )
            
            heightmap_data = ds.GetRasterBand(1).ReadAsArray()
            heightmap_data = gaussian_filter(heightmap_data, sigma=1.0)
            driver = gdal.GetDriverByName('GTiff')
            heightmap_ds = driver.Create(str(heightmap_tiff), 
                                       heightmap_data.shape[1],
                                       heightmap_data.shape[0],
                                       1,
                                       gdal.GDT_Float32)
            heightmap_ds.GetRasterBand(1).WriteArray(heightmap_data)
            
            return output_tiff
        except Exception as e:
            print(f"Error enhancing resolution: {e}")
            sys.exit(1)

    def create_terrain_mesh(self, scale_xy=0.25, scale_z=5.0, z_offset=0):
        """Generate terrain mesh from heightmap"""
        try:
            heightmap = self._process_heightmap()
            vertices = self._generate_vertices(heightmap, scale_xy, scale_z, z_offset)
            faces = self._generate_faces(heightmap.shape)
            
            terrain = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
            for i, f in enumerate(faces):
                for j in range(3):
                    terrain.vectors[i][j] = vertices[f[j]]
            
            output_path = self.mesh_path / "terrain.stl"
            terrain.save(str(output_path))
            print(f"Created terrain mesh at: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error creating terrain mesh: {e}")
            sys.exit(1)

    def _process_heightmap(self, max_size=400):
        """Process heightmap from enhanced DEM"""
        enhanced_tiff = self.dem_path / "terrain_enhanced.tif"
        if not enhanced_tiff.exists():
            print("Error: Enhanced terrain file not found. Run enhance_resolution first.")
            sys.exit(1)
            
        ds = gdal.Open(str(enhanced_tiff))
        heightmap = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
        heightmap = gaussian_filter(heightmap, sigma=1.0)
        
        rows, cols = heightmap.shape
        if rows > max_size or cols > max_size:
            skip_x = max(1, cols // max_size)
            skip_y = max(1, rows // max_size)
            heightmap = heightmap[::skip_y, ::skip_x]
        
        # Normalize and enhance contrast
        p2, p98 = np.percentile(heightmap, (2, 98))
        heightmap = np.clip(heightmap, p2, p98)
        heightmap = np.power((heightmap - p2) / (p98 - p2), 0.75)
        
        return heightmap

    def _generate_vertices(self, heightmap, scale_xy, scale_z, z_offset):
        """Generate vertices from heightmap"""
        rows, cols = heightmap.shape
        vertices = []
        for y in range(rows):
            for x in range(cols):
                vertices.append([
                    (x - cols/2) * scale_xy,
                    (y - rows/2) * scale_xy,
                    heightmap[y, x] * scale_z + z_offset
                ])
        return np.array(vertices)

    def _generate_faces(self, shape):
        """Generate faces for the mesh"""
        rows, cols = shape
        faces = []
        for y in range(rows - 1):
            for x in range(cols - 1):
                v0 = y * cols + x
                v1 = v0 + 1
                v2 = (y + 1) * cols + x
                v3 = v2 + 1
                faces.extend([[v0, v1, v2], [v1, v3, v2]])
        return np.array(faces)

    def _create_sdf_file(self):
        """Create SDF file for the terrain model"""
        sdf_content = '''<?xml version="1.0" ?>
<sdf version="1.7">
    <model name="terrain">
        <static>true</static>
        <link name="link">
            <collision name="collision">
                <geometry>
                    <mesh>
                        <uri>model://ground/mesh/terrain.stl</uri>
                    </mesh>
                </geometry>
            </collision>
            <visual name="visual">
                <geometry>
                    <mesh>
                        <uri>model://ground/mesh/terrain.stl</uri>
                    </mesh>
                </geometry>
                <material>
                    <script>
                        <uri>model://ground/material/terrain.material</uri>
                        <name>Terrain/Moss</name>
                    </script>
                </material>
            </visual>
        </link>
    </model>
</sdf>'''
        
        sdf_path = self.terrain_path / 'model.sdf'
        sdf_path.write_text(sdf_content)
        print(f"Created SDF file: {sdf_path}")

    def _create_config_file(self):
        """Create model.config file"""
        config_content = '''<?xml version="1.0"?>
<model>
    <name>ground</name>
    <version>1.0</version>
    <sdf version="1.7">model.sdf</sdf>
    
    <author>
        <name>AI4Forest</name>
        <email>khalid.bourr@gmail.com</email>
    </author>
    
    <description>
        Terrain model generated from DEM data for Gazebo simulation
    </description>
</model>'''
        
        config_path = self.terrain_path / 'model.config'
        config_path.write_text(config_content)
        print(f"Created config file: {config_path}")

    def _create_test_world(self):
        """Create test world file"""
        world_content = '''<?xml version="1.0" ?>
<sdf version="1.7">
    <world name="default">
        <!-- Add a sun to the world -->
        <include>
            <uri>model://sun</uri>
        </include>
        
        <!-- Add our terrain model -->
        <include>
            <name>terrain</name>
            <uri>model://ground</uri>
            <pose>0 0 0 0 0 0</pose>
        </include>
        
        <!-- Add physics properties -->
        <physics type="ode">
            <real_time_update_rate>1000.0</real_time_update_rate>
            <max_step_size>0.001</max_step_size>
            <real_time_factor>1</real_time_factor>
            <gravity>0 0 -9.8</gravity>
        </physics>
    </world>
</sdf>'''
        
        world_path = self.terrain_path / 'test.world'
        world_path.write_text(world_content)
        print(f"Created test world file: {world_path}")

    def process_terrain(self):
        """Process complete terrain generation pipeline"""
        print("\nStarting terrain generation pipeline...")
        print("\n1. Verifying directory structure...")
        self._verify_paths()

        print("\n2. Enhancing DEM resolution...")
        self.enhance_resolution()

        print("\n3. Creating terrain mesh...")
        stl_path = self.create_terrain_mesh()
        
        print("\n4. Creating Gazebo model files...")
        self._create_sdf_file()
        self._create_config_file()
        self._create_test_world()

        return self.terrain_path

def main():
    parser = argparse.ArgumentParser(description='Terrain Generator for Gazebo')
    parser.add_argument('--tif-file', type=str, default='terrain.tif',
                       help='Name of the .tif file in models/ground/dem directory (default: terrain.tif)')
    
    args = parser.parse_args()
    print(f"\nProcessing terrain file: {args.tif_file}")
    
    try:
        generator = TerrainGenerator(args.tif_file)
        model_path = generator.process_terrain()
        
        print("\nTerrain generation completed successfully!")
        print(f"\nTo use in Gazebo:")
        print(f"export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:{model_path.parent}")
        print(f"gazebo {model_path}/test.world")
        
    except Exception as e:
        print(f"\nError in terrain generation: {str(e)}")
        print("\nUsage:")
        print("python3 TerrainGeneratorV2.py --tif-file terrain.tif")
        sys.exit(1)

if __name__ == "__main__":
    main()

