#!/usr/bin/env python3

import os
import subprocess
import shutil

class AssetExporter:
   def __init__(self, blender_path):
       self.blender_path = os.path.join(blender_path, "blender")

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
       dae_path = os.path.join(mesh_dir, f"{base_name}.dae")
       collision_path = os.path.join(mesh_dir, f"{base_name}_collision.dae")
       self._export_dae(blend_file, dae_path, collision_path)
       
       # Move textures to correct location
       print("Step 2: Moving textures to correct location...")
       for file in os.listdir(mesh_dir):
           if file.endswith(('.jpg', '.png')):
               src_path = os.path.join(mesh_dir, file)
               dst_path = os.path.join(textures_dir, file)
               shutil.move(src_path, dst_path)
               print(f"Moved texture: {file} to textures folder")
       
       # Get textures and create material
       print("Step 3: Finding textures...")
       textures = self._organize_textures(blend_file, textures_dir)
       
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
       decimate.ratio = 0.01  # Much lower ratio for collision
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
       
       subprocess.run([
           self.blender_path,
           "--background",
           "--python",
           script_path
       ], capture_output=True)
       
       if os.path.exists(output_path) and os.path.exists(collision_path):
           print(f"Successfully exported: {output_path} and {collision_path}")
       else:
           print("Failed to export DAE files")

   def _organize_textures(self, blend_file, textures_dir):
       """Simply list all textures without categorizing"""
       textures = []
       
       print(f"\nSearching for textures in: {textures_dir}")
       try:
           for file in os.listdir(textures_dir):
               if file.endswith(('.jpg', '.png')):
                   textures.append(file)
                   print(f"Found texture: {file}")
       except Exception as e:
           print(f"Error scanning textures: {str(e)}")
       
       return textures

   def _create_material_file(self, model_name, textures, materials_dir):
       """Create a simple material file with all textures"""
       print(f"\nCreating material for {model_name}")
       
       material_content = f"""material {model_name}
{{
   technique
   {{
       pass
       {{
           ambient 1.0 1.0 1.0 1.0
           diffuse 1.0 1.0 1.0 1.0
           specular 0.5 0.5 0.5 1.0 12.5
"""
       
       # Add all textures as simple texture units
       for i, texture in enumerate(textures):
           material_content += f"""
           texture_unit
           {{
               texture ../textures/{texture}
               tex_coord_set {i}
               filtering trilinear
           }}
"""
       
       material_content += """
       }
   }
}"""

       material_path = os.path.join(materials_dir, f"{model_name}.material")
       with open(material_path, 'w') as f:
           f.write(material_content)
       print(f"Created material file: {material_path}")

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
                       <uri>file://{parent_folder}/{model_name}/mesh/{model_name}_collision.dae</uri>
                   </mesh>
               </geometry>
           </collision>
           <visual name="visual">
               <geometry>
                   <mesh>
                       <uri>file://{parent_folder}/{model_name}/mesh/{model_name}.dae</uri>
                   </mesh>
               </geometry>
               <material>
                   <script>
                       <uri>file://{parent_folder}/{model_name}/materials/{model_name}.material</uri>
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
   # Paths
   blender_path = "/home/vampiro/Downloads/blender-4.2.1-linux-x64"
   blend_files_path = "/home/vampiro/Desktop/plant"
   models_base_dir = "/home/vampiro/Desktop/AI4Forest/forest_generator/models"
   
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
           "coast-land-rocks-04_2K_9d63d4e8-5064-4b62-8bfa-f7d45027fcf6.blend"
       ],
       'sand': [
           "sand-dune_2K_0a625146-f652-4724-ad1f-ff705a37da8f.blend"
       ]      
   }
   
   exporter = AssetExporter(blender_path)
   
   for category, models in model_categories.items():
       category_dir = os.path.join(models_base_dir, category)
       print(f"\nProcessing {category} category...")
       
       for model in models:
           blend_path = os.path.join(blend_files_path, model)
           exporter.process_asset(blend_path, category_dir)

if __name__ == "__main__":
   main()
