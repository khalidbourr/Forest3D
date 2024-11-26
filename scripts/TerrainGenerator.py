#!/usr/bin/env python3
import numpy as np
from osgeo import gdal
import os
from stl import mesh
from scipy.ndimage import gaussian_filter
from pathlib import Path
import sys
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

    def enhance_dem(self, scale_factor=6.0):
        """Optional DEM enhancement"""
        input_tiff = self.dem_path / self.tif_filename
        output_tiff = self.dem_path / "terrain_enhanced.tif"
        
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
            
            return output_tiff
        except Exception as e:
            print(f"Error enhancing DEM: {e}")
            sys.exit(1)

    def create_terrain_mesh(self, scale_factor=1.0, smooth_sigma=1.0, enhance=False):
        """Generate terrain mesh from DEM while maintaining proportions"""
        try:
            # Determine which DEM file to use
            if enhance:
                dem_file = self.enhance_dem()
                print("Using enhanced DEM...")
            else:
                dem_file = self.dem_path / self.tif_filename
                print("Using original DEM...")

            # Open DEM file
            ds = gdal.Open(str(dem_file))
            if ds is None:
                raise ValueError(f"Failed to open {dem_file}")

            # Get geotransform information
            geotransform = ds.GetGeoTransform()
            pixel_width = abs(geotransform[1])  # X resolution
            pixel_height = abs(geotransform[5])  # Y resolution

            # Read elevation data
            elevation = ds.GetRasterBand(1).ReadAsArray().astype(np.float32)
            
            # Apply smoothing if requested
            if smooth_sigma > 0:
                elevation = gaussian_filter(elevation, sigma=smooth_sigma)

            # Get dimensions
            rows, cols = elevation.shape
            
            # Create vertices
            vertices = []
            faces = []
            
            # Calculate real-world coordinates using geotransform
            for y in range(rows):
                for x in range(cols):
                    # Convert pixel coordinates to real-world coordinates
                    world_x = x * pixel_width * scale_factor
                    world_y = y * pixel_height * scale_factor
                    world_z = elevation[y, x] * scale_factor
                    
                    vertices.append([world_x, world_y, world_z])

            # Generate faces (triangles)
            for y in range(rows - 1):
                for x in range(cols - 1):
                    v0 = y * cols + x
                    v1 = v0 + 1
                    v2 = (y + 1) * cols + x
                    v3 = v2 + 1
                    faces.extend([[v0, v1, v2], [v1, v3, v2]])

            # Create the mesh
            vertices = np.array(vertices)
            faces = np.array(faces)
            
            # Center the mesh
            center = np.mean(vertices, axis=0)
            vertices -= center
            
            # Create the STL mesh
            terrain = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
            for i, f in enumerate(faces):
                for j in range(3):
                    terrain.vectors[i][j] = vertices[f[j]]

            # Save the mesh
            output_path = self.mesh_path / "terrain.stl"
            terrain.save(str(output_path))
            print(f"Created terrain mesh at: {output_path}")
            
            # Print terrain statistics
            x_extent = np.ptp(vertices[:, 0])
            y_extent = np.ptp(vertices[:, 1])
            z_extent = np.ptp(vertices[:, 2])
            print(f"\nTerrain dimensions:")
            print(f"X extent: {x_extent:.2f} units")
            print(f"Y extent: {y_extent:.2f} units")
            print(f"Z extent: {z_extent:.2f} units")
            print(f"Number of vertices: {len(vertices)}")
            print(f"Number of faces: {len(faces)}")
            
            return output_path

        except Exception as e:
            print(f"Error creating terrain mesh: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

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
        <include>
            <uri>model://sun</uri>
        </include>
        
        <include>
            <name>terrain</name>
            <uri>model://ground</uri>
            <pose>0 0 0 0 0 0</pose>
        </include>
        
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

    def process_terrain(self, scale_factor=1.0, smooth_sigma=1.0, enhance=False):
        """Process complete terrain generation pipeline"""
        print("\nStarting terrain generation pipeline...")
        print("\n1. Verifying directory structure...")
        self._verify_paths()

        print("\n2. Creating terrain mesh...")
        stl_path = self.create_terrain_mesh(
            scale_factor=scale_factor,
            smooth_sigma=smooth_sigma,
            enhance=enhance
        )
        
        print("\n3. Creating Gazebo model files...")
        self._create_sdf_file()
        self._create_config_file()
        self._create_test_world()

        return self.terrain_path

def main():
    parser = argparse.ArgumentParser(description='DEM to Gazebo Terrain Generator')
    parser.add_argument('--tif-file', type=str, default='terrain.tif',
                       help='Name of the .tif file in models/ground/dem directory')
    parser.add_argument('--scale', type=float, default=1.0,
                       help='Scale factor for the entire terrain (default: 1.0)')
    parser.add_argument('--smooth', type=float, default=1.0,
                       help='Smoothing factor for the terrain (default: 1.0)')
    parser.add_argument('--enhance', action='store_true',
                       help='Enable DEM enhancement (default: False)')
    
    args = parser.parse_args()
    print(f"\nProcessing terrain file: {args.tif_file}")
    
    try:
        generator = TerrainGenerator(args.tif_file)
        model_path = generator.process_terrain(
            scale_factor=args.scale,
            smooth_sigma=args.smooth,
            enhance=args.enhance
        )
        
        print("\nTerrain generation completed successfully!")
        print(f"\nTo use in Gazebo:")
        print(f"export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:{model_path.parent}")
        print(f"gazebo {model_path}/test.world")
        
    except Exception as e:
        print(f"\nError in terrain generation: {str(e)}")
        print("\nUsage:")
        print("python3 terrain_generator.py --tif-file terrain.tif [--scale 1.0] [--smooth 1.0] [--enhance]")
        sys.exit(1)

if __name__ == "__main__":
    main()
