#!/usr/bin/env python3

import os
import subprocess
import shutil
import sys
import time
import threading
import argparse
from itertools import cycle

class LoadingAnimation:
    def __init__(self, description="Loading"):
        self.description = description
        self.done = False
        self._thread = None

    def animate(self):
        for c in cycle(['⢿', '⣻', '⣽', '⣾', '⣷', '⣯', '⣟', '⡿']):
            if self.done:
                break
            print(f'\r{self.description} {c}', end='', flush=True)
            time.sleep(0.1)
        print('\r' + ' ' * (len(self.description) + 2), end='', flush=True)

    def start(self):
        self.done = False
        self._thread = threading.Thread(target=self.animate)
        self._thread.start()

    def stop(self):
        self.done = True
        if self._thread is not None:
            self._thread.join()
            print('\r', end='', flush=True)

class AssetExporter:
    def __init__(self, blender_path):
        self.blender_path = os.path.join(blender_path, "blender")
        self.loading_animation = LoadingAnimation()

    def process_asset(self, blend_file, category_dir):
        """Process a single asset"""
        base_name = os.path.splitext(os.path.basename(blend_file))[0]
        print(f"\nProcessing asset: {base_name}")
        
        # Create directory structure
        asset_dir = os.path.join(category_dir, base_name)
        mesh_dir = os.path.join(asset_dir, 'mesh')
        textures_dir = os.path.join(asset_dir, 'textures')
        materials_dir = os.path.join(asset_dir, 'materials')
        
        os.makedirs(mesh_dir, exist_ok=True)
        os.makedirs(textures_dir, exist_ok=True)
        os.makedirs(materials_dir, exist_ok=True)

        # Export DAE
        print("Step 1: Exporting DAE...")
        self.loading_animation.description = "Exporting DAE files"
        self.loading_animation.start()
        dae_path = os.path.join(mesh_dir, f"{base_name}.dae")
        collision_path = os.path.join(mesh_dir, f"{base_name}_collision.dae")
        self._export_dae(blend_file, dae_path, collision_path)
        self.loading_animation.stop()
        
        # Move textures to correct location
        print("Step 2: Moving textures to correct location...")
        for file in os.listdir(mesh_dir):
            if file.endswith(('.jpg', '.png', '.jpeg', '.JPG', '.PNG', '.JPEG')):
                src_path = os.path.join(mesh_dir, file)
                dst_path = os.path.join(textures_dir, file)
                shutil.move(src_path, dst_path)
                print(f"Moved texture: {file} to textures folder")
        
        # Get textures and create material
        print("Step 3: Finding textures...")
        self.loading_animation.description = "Processing textures"
        self.loading_animation.start()
        textures = self._organize_textures(blend_file, textures_dir)
        self.loading_animation.stop()
        
        if textures:
            print("Step 4: Creating material file...")
            self._create_material_file(base_name, textures, materials_dir)
        else:
            print("No textures found for material creation")

        # Generate SDF and config files
        print("Step 5: Creating SDF file...")
        self._create_sdf_file(base_name, asset_dir)
        
        print("Step 6: Creating model.config file...")
        self._create_config_file(base_name, asset_dir)

        # Create test world file
        print("Step 7: Creating test world file...")
        self._create_test_world(base_name, asset_dir)

    def _export_dae(self, blend_file, output_path, collision_path):
        """Export optimized DAE for visual and collision meshes"""
        blender_script = f'''
import bpy

# Load file
bpy.ops.wm.open_mainfile(filepath="{blend_file}")

# Export visual mesh
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = 0.1  
        bpy.ops.object.modifier_apply(modifier="Decimate")

bpy.ops.wm.collada_export(
    filepath="{output_path}",
    selected=True,
    apply_modifiers=True,
    include_children=True,
    include_armatures=True,
    include_shapekeys=False
)

# Reset and export collision mesh
bpy.ops.wm.open_mainfile(filepath="{blend_file}")
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        decimate = obj.modifiers.new(name="Decimate", type='DECIMATE')
        decimate.ratio = 0.01  
        bpy.ops.object.modifier_apply(modifier="Decimate")

bpy.ops.wm.collada_export(
    filepath="{collision_path}",
    selected=True,
    apply_modifiers=True,
    include_children=True,
    include_armatures=True,
    include_shapekeys=False
)
'''
        script_path = "/tmp/export_script.py"
        with open(script_path, 'w') as f:
            f.write(blender_script)
        
        result = subprocess.run([
            self.blender_path,
            "--background",
            "--python",
            script_path
        ], capture_output=True, text=True)
        
        if os.path.exists(output_path) and os.path.exists(collision_path):
            print(f"Successfully exported: {output_path} and {collision_path}")
        else:
            print("Failed to export DAE files")
            print("Blender output:", result.stdout)
            print("Blender errors:", result.stderr)

    def _organize_textures(self, blend_file, textures_dir):
        """Simply list all textures without categorizing"""
        textures = []
        
        print(f"\nSearching for textures in: {textures_dir}")
        try:
            for file in os.listdir(textures_dir):
                if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                    textures.append(file)
                    print(f"Found texture: {file}")
        except Exception as e:
            print(f"Error scanning textures: {str(e)}")
        
        return textures

    def _create_sdf_file(self, model_name, model_dir):
        """Create SDF file for the model with separate collision mesh"""
        parent_folder = os.path.basename(os.path.dirname(model_dir))
        sdf_content = f'''<?xml version="1.0" ?>
<sdf version="1.6">
    <model name="{model_name}">
        <static>true</static>
        <link name="link">
            <collision name="collision">
                <geometry>
                    <mesh>
                        <uri>model://{parent_folder}/{model_name}/mesh/{model_name}_collision.dae</uri>
                    </mesh>
                </geometry>
            </collision>
            <visual name="visual">
                <geometry>
                    <mesh>
                        <uri>model://{parent_folder}/{model_name}/mesh/{model_name}.dae</uri>
                    </mesh>
                </geometry>
                <material>
                    <script>
                        <uri>model://{parent_folder}/{model_name}/materials/{model_name}.material</uri>
                        <name>{model_name}</name>
                    </script>
                </material>
            </visual>
        </link>
    </model>
</sdf>'''
    
        sdf_path = os.path.join(model_dir, 'model.sdf')
        with open(sdf_path, 'w') as f:
            f.write(sdf_content)
        print(f"Created SDF file: {sdf_path}")

    # [Other methods remain the same]
    def _create_material_file(self, model_name, textures, materials_dir):
        """Create a material file with base color texture"""
        # Find the most appropriate base texture
        base_texture = None
        for texture in textures:
            if 'Leaf_01' in texture or 'Base' in texture or 'albedo' in texture:
                base_texture = texture
                break
        
        # If no specific base texture found, use the first one
        if not base_texture and textures:
            base_texture = textures[0]
        
        if not base_texture:
            print("No textures found!")
            return

        material_content = f"""material {model_name}
{{
    technique
    {{
        pass
        {{
            ambient 0.8 0.8 0.8 1.0       
            diffuse 0.7 0.7 0.7 1.0       
            specular 0.3 0.3 0.3 1.0 20.0 

            texture_unit
            {{
                texture ../textures/{base_texture}
                tex_coord_set 0
                filtering trilinear
                scale 1.0 1.0
            }}
        }}
    }}
}}"""

        material_path = os.path.join(materials_dir, f"{model_name}.material")
        with open(material_path, 'w') as f:
            f.write(material_content)
        print(f"Created material file: {material_path} using texture: {base_texture}")
    def _create_config_file(self, model_name, model_dir):
        """Create model.config file"""
        config_content = f'''<?xml version="1.0"?>
<model>
    <name>{model_name}</name>
    <version>1.0</version>
    <sdf version="1.6">model.sdf</sdf>
    
    <author>
        <name>AI4Forest</name>
        <email>your.email@example.com</email>
    </author>
    
    <description>
        {model_name} model for Gazebo simulation
    </description>
</model>'''
        
        config_path = os.path.join(model_dir, 'model.config')
        with open(config_path, 'w') as f:
            f.write(config_content)
        print(f"Created config file: {config_path}")

    def _create_test_world(self, model_name, model_dir):
        """Create test world file"""
        parent_folder = os.path.basename(os.path.dirname(model_dir))
        world_content = f'''<?xml version="1.0" ?>
<sdf version="1.6">
    <world name="default">
        <include>
            <uri>model://sun</uri>
        </include>
        <include>
            <uri>model://ground_plane</uri>
        </include>
        <include>
            <name>{model_name}</name>
            <pose>0 0 0 0 0 0</pose>
            <uri>model://{parent_folder}/{model_name}</uri>
        </include>
    </world>
</sdf>'''
    
        world_path = os.path.join(model_dir, 'test.world')
        with open(world_path, 'w') as f:
            f.write(world_content)
        print(f"Created test world file: {world_path}")

def main():
    parser = argparse.ArgumentParser(description='Export Blender assets to Gazebo models')
    parser.add_argument('--blender-path', default="/home/vampiro/Downloads/blender-4.2.1-linux-x64",
                        help='Path to Blender installation directory')
    parser.add_argument('--blend-files-path', default="/home/vampiro/Desktop/plant",
                        help='Path to directory containing Blender files')
    parser.add_argument('--models-base-dir', default="/home/vampiro/Desktop/AI4Forest/forest_generator/models",
                        help='Path to output directory for Gazebo models')

    args = parser.parse_args()
    
    # Model categories
    model_categories = {
        'tree': [
            "MT_PM_V60_Alnus_cremastogyne_01_01.blend",
            "MT_PM_V60_Acer_buergerianum_01_01.blend"
        ],
        'bush': [
            "MT_PM_V60_Cistus_albidus_01_01.blend",
            "MT_PM_V60_Agave_sisalana_01_01.blend"
        ],
        'grass': [
            "MT_PM_V60_Cynodon_dactylon_01_01.blend"
        ],
        'rock': [
            "coast-land-rocks-04_2K_9d63d4e8-5064-4b62-8bfa-f7d45027fcf6.blend",
            "photoscanned-rock-03_2K_6669afd9-de42-4d31-9b27-ec4e7f815039.blend",
            "rock_2K_bf18f3e1-4f7c-457d-b70a-56315998a211.blend"
        ],
        'sand': [
            "sand-dune_2K_0a625146-f652-4724-ad1f-ff705a37da8f.blend",
            "sand-rocks-small-01_2K_e14d6880-1c63-4176-a598-1c68a5f910bd.blend"
        ]      
    }
    
    exporter = AssetExporter(args.blender_path)
    
    for category, models in model_categories.items():
        category_dir = os.path.join(args.models_base_dir, category)
        print(f"\nProcessing {category} category...")
        
        for model in models:
            blend_path = os.path.join(args.blend_files_path, model)
            if os.path.exists(blend_path):
                exporter.process_asset(blend_path, category_dir)
            else:
                print(f"Warning: {blend_path} does not exist")

if __name__ == "__main__":
    main()
