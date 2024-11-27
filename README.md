# Forest Generator for Gazebo Simulation 

A comprehensive toolkit for generating realistic forest environments in Gazebo simulation, including terrain generation from DEM data and procedural placement of various natural elements like trees, rocks, bushes, and grass.

![Forest3D Environment](https://github.com/khalidbourr/Forest3D/blob/main/Screenshot%20from%202024-11-21%2022-29-42.png)


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

##  Features

- **Terrain Generation**
  - DEM (Digital Elevation Model) processing
  - Resolution enhancement with cubic spline interpolation
  - Gaussian smoothing for natural-looking terrain
  - STL mesh generation with configurable scaling

- **Asset Processing**
  - Automatic processing of Blender files (.blend)
  - Optimized mesh export with decimation
  - Separate collision mesh generation
  - Texture and material organization
  - SDF and configuration file generation

- **Forest Population**
  - Procedural placement of natural elements
  - Configurable density for different asset types
  - Support for multiple asset categories

##  Installation

### Prerequisites

- Python 3.7+
- Blender 4.2+ (for asset processing)
- GDAL
- NumPy
- SciPy
- Gazebo Simulator

### Dependencies Installation

# Install system dependencies

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-numpy python3-gdal python3-scipy
```

# Install Python packages

```bash
pip3 install numpy-stl
```
##  Project Setup & Usage

### Project Setup

# Clone the repository

```bash
git clone https://github.com/khalidbourr/Forest3D.git
cd Forest3D
pip install -r requirements.txt
```


# Set up Gazebo model path
```bash
echo "export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:$(pwd)/models" >> ~/.bashrc
source ~/.bashrc
```


### Usage Guide

#### . For testing the environment already existing

```bash
cd world
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:$(pwd)/models
gazebo forest_world.world
```


#### 1. Terrain Generation

```bash
python3 TerrainGenerator.py --tif-file terrain.tif
```

**Options:**
- `--tif-file`: Name of the DEM file (must be in `models/ground/dem` directory)


#### 2. Asset Generation

The B2GEngine supports the following categories:
- `tree`: Large vegetation models
- `bush`: Small vegetation and shrubs
- `grass`: Ground cover vegetation
- `rock`: Rock formations
- `sand`: Ground textures

### Adding New Assets

1. Place your .blend files in the `Blender-Assets` directory
2. Add the filename to the appropriate category in `B2GEngine.py`:

```python
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
```

```bash
python3 B2GEngine.py --blender-path /path/to/blender \
                        --blend-files-path /path/to/blend/files \
                        --models-base-dir /path/to/output
```

**Options:**
- `--blender-path`: Path to Blender installation
- `--blend-files-path`: Directory containing Blender files
- `--models-base-dir`: Output directory for processed models

#### 3. Forest Generation

```bash
python3 main.py --density '{"tree":25,"rock":5,"bush":10,"grass":500}'
```

#### 4. Gazebo Forest World Launch

```bash
cd world
export GAZEBO_MODEL_PATH=$GAZEBO_MODEL_PATH:$(pwd)/models
gazebo forest_world.world
```

**Options:**
- `--base-path`: Project base path
- `--density`: JSON string with model densities
- `--config-file`: Path to JSON configuration file

##  Project Structure
```bash

forest-generator/
├── scripts/
│   ├── B2GEngine.py
│   ├── TerrainGenerator.py
│   └── ForestGenerator.py
├── models/
│   ├── ground/
│   │   ├── dem/
│   │   ├── mesh/
│   │   ├── material/
│   │   └── texture/
│   ├── tree/
│   ├── rock/
│   ├── bush/
│   └── grass/
└── worlds/
    └── forest.world

```

## ⚙️ Configuration

### Asset Categories
The system supports the following asset categories:
- `tree`: Large vegetation
- `rock`: Rock formations
- `bush`: Small vegetation
- `grass`: Ground cover
- `sand`: Ground textures

### Density Configuration
Create a JSON file with the following structure:

{
  "tree": 25,
  "rock": 5,
  "bush": 10,
  "grass": 500
}

##  Advanced Configuration

### Terrain Generation Parameters
- `scale_factor`: Resolution enhancement factor (default: 6.0)
- `scale_xy`: Horizontal scaling of terrain (default: 0.25)
- `scale_z`: Vertical scaling of terrain (default: 5.0)
- `z_offset`: Height offset (default: 0)

### Asset Processing Parameters
- Visual mesh decimation ratio: 0.1 (90% reduction)
- Collision mesh decimation ratio: 0.01 (99% reduction)
- Supported texture formats: JPG, PNG, JPEG


##  License

This project is licensed under the MIT License - see the LICENSE file for details.


## 💡 Usage Examples

### Basic Terrain Generation

1. Place your DEM file in models/ground/dem
2. Run terrain generation
3. Check output in models/ground/mesh

### Custom Forest Configuration

1. Create custom density file
2. Modify asset parameters
3. Run forest generation
4. Verify in Gazebo

##  Troubleshooting

### Common Issues

1. **Gazebo Model Path**
   - Verify environment variables
   - Check directory permissions

2. **Blender Export**
   - Confirm Blender version
   - Check Python dependencies

3. **Terrain Generation**
   - Validate DEM format
   - Check GDAL installation

## ROS Melodic Python Dependencies

### Overview
When using ROS Melodic (Python 2.7), you'll need a separate Python 3.8 environment for Forest3D dependencies while maintaining ROS functionality.

### Setup Python 3.8 Environment

1. Install Python 3.8
```bash
# Install required tools
apt update
apt install software-properties-common

# Add Python repository
add-apt-repository ppa:deadsnakes/ppa
apt update

# Install Python 3.8
apt install python3.8 python3.8-venv python3.8-dev
# Create Python 3.8 environment
python3.8 -m venv ~/forest3d_env

# Activate environment
source ~/forest3d_env/bin/activate

# Update pip
pip install --upgrade pip
# Install GDAL system packages
apt update
apt install python3-gdal gdal-bin libgdal-dev

# Set GDAL environment variables
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal

# Install matching GDAL Python bindings
pip install "pygdal==`gdal-config --version`.*"

# Modify requirements.txt:
numpy>=1.21.0
scipy>=1.7.0
numpy-stl>=2.16.0
pathlib>=1.0.1
black>=22.3.0
pylint>=2.12.0
pytest>=7.0.0
pytest-cov>=3.0.0

# Install requirements:
pip install -r requirements.txt
