# Plugin

A Python tool for automatically exporting Blender assets to Gazebo-compatible models with proper file structure, optimized meshes, and material configurations.


![Forest3D Environment](https://github.com/khalidbourr/Forest3D/blob/main/Screenshot%20from%202024-11-21%2022-29-42.png)

## Prerequisites

- Python 3.x
- Blender 4.x (tested with 4.2.1)
- Required Python packages:
  - `os`
  - `subprocess`
  - `shutil`
  - `sys`
  - `time`
  - `threading`
  - `argparse`
  - `itertools`
  - `numpy`
  - `gdal` (osgeo)
  - `numpy-stl`
  - `scipy`
  - `pathlib`

## Installation

1. Clone the repository:
```bash
git clone the repository
cd .../world
export GAZEBO_MODEL_PATH=/path/Forest3D/models

# Launch forest world
cd worlds
gazebo forest_world.world
