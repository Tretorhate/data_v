# Assignment #5: 3D Object Processing with Open3D

## Overview

This assignment demonstrates 3D object processing using the Open3D library in Python. All 7 required tasks are completed step-by-step with visualization and console output.

## 3D Model Used

- **Model**: Coffee Cup (Low Poly)
- **Format**: OBJ
- **Location**: `Assignment5/object/coffeecup/coffee_cup_obj.obj`

## Tasks Completed

### 1. Loading and Visualization

- Loads the 3D OBJ file
- Since textures aren't automatically loaded by Open3D's basic loader, applies a beautiful gradient coloring based on Y-axis (height): blue (bottom) → cyan → yellow → red (top)
- Displays the original model with colors
- Prints: number of vertices, triangles, presence of color and normals

### 2. Conversion to Point Cloud

- Converts mesh to point cloud by sampling 10,000 points uniformly
- Point cloud inherits colors from the colored mesh
- Displays the colored point cloud
- Prints: number of points, presence of color

### 3. Surface Reconstruction from Point Cloud

- Reconstructs mesh using Poisson surface reconstruction (creates entirely NEW vertices)
- Removes artifacts using bounding box crop
- **Transfers colors** from original point cloud using nearest neighbor search (KD-tree)
  - Why needed: Poisson creates new vertices with no direct mapping to original colored points
  - How it works: For each new vertex, finds closest point in original cloud and copies its color
- Displays the colored reconstructed mesh
- Prints: number of vertices, triangles, presence of color, average transfer distance

### 4. Voxelization

- Converts point cloud to voxel grid
- Uses voxel size of 0.3 units
- Voxels inherit colors from the colored point cloud
- Displays the colored voxel grid
- Prints: number of voxels, presence of color

### 5. Adding a Plane

- Creates a vertical plane that cuts THROUGH the coffee cup
- Red colored plane positioned at the exact center of the model
- Displays the coffee cup with cutting plane intersecting it

### 6. Surface Clipping

- Implements clipping by removing all points on the LEFT side of the plane
- Shows ONLY the RIGHT HALF of the coffee cup after cutting (perfect 50/50 split)
- Plane is removed from this view to show clean clipped result
- Prints: remaining vertices, triangles, color and normals presence

### 7. Working with Color and Extremes

- Applies gradient coloring along Z axis (blue to red)
- Finds minimum and maximum Z coordinates
- Highlights extremes with spheres (green for min, yellow for max)
- Shows alternative view with wireframe cubes
- Prints: coordinates of extreme points

## Installation

1. Install required packages:

```bash
pip install -r requirements.txt
```

**Required libraries:**

- `open3d` - 3D data processing and visualization
- `numpy` - numerical operations
- `trimesh` - loading quad-based OBJ files
- `scipy` - KD-tree for nearest neighbor color transfer

**Notes:**

- The coffee cup OBJ file contains quad faces (4 vertices per face) instead of triangles. The script automatically handles this by:
  1. First trying Open3D's native loading with post-processing
  2. If that fails, using Trimesh library to load and triangulate the mesh, then converting to Open3D format
- **About Colors/Textures**: Open3D's basic loader doesn't automatically apply texture files. Instead, the script applies a beautiful gradient coloring based on height (Y-axis) to the coffee cup model, making it visually appealing and easier to analyze. This gradient (blue→cyan→yellow→red) helps visualize the 3D structure better than textures would.

## Running the Script

Execute the script from the project root directory:

```bash
python assignment5_solution_coffeecup.py
```

Or from within the `assignment_5` directory:

```bash
cd assignment_5
python ../assignment5_solution_coffeecup.py
```

## Expected Behavior

The script will:

1. Print detailed information to console after each task
2. Open visualization windows sequentially (close each window to proceed to the next)
3. Display 8 visualization windows total:
   - Task 1: Original Coffee Cup Model
   - Task 2: Point Cloud
   - Task 3: Reconstructed Mesh
   - Task 4: Voxel Grid
   - Task 5: Coffee Cup with Cutting Plane (red plane cuts through center)
   - Task 6: Clipped Coffee Cup (shows right half only)
   - Task 7: Gradient and Extremes (View 1 with spheres)
   - Task 7: Gradient and Extremes (View 2 with wireframe cubes)

## Controls in Visualization Window

- **Mouse Left**: Rotate view
- **Mouse Right**: Translate view
- **Mouse Wheel**: Zoom in/out
- **Close Window**: Proceed to next task

## Understanding Each Step

The script includes detailed console output explaining:

- What operation is being performed
- Statistics about the geometry (vertices, triangles, voxels)
- Presence of colors, normals, and other attributes
- Coordinates and measurements where applicable

## Notes

- All 7 tasks are implemented as required
- Each task includes proper visualization and console output
- The script processes tasks sequentially and waits for user to close each visualization window
- Gradient coloring demonstrates understanding of coordinate manipulation
- Extreme point detection uses numpy for efficient computation
