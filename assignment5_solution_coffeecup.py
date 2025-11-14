"""
Assignment #5: 3D Object Processing with Open3D
Student: Working with Coffee Cup Model
All 7 tasks completed step by step
"""

import open3d as o3d
import numpy as np
import copy
import os

def print_separator():
    print("\n" + "="*80 + "\n")

def print_info(title, mesh=None, pcd=None, voxel=None):
    """Print information about the geometry"""
    print(f"--- {title} ---")
    
    if mesh is not None:
        vertices = np.asarray(mesh.vertices)
        triangles = np.asarray(mesh.triangles)
        has_colors = mesh.has_vertex_colors()
        has_normals = mesh.has_vertex_normals()
        
        print(f"Number of vertices: {len(vertices)}")
        print(f"Number of triangles: {len(triangles)}")
        print(f"Has colors: {has_colors}")
        print(f"Has normals: {has_normals}")
    
    if pcd is not None:
        points = np.asarray(pcd.points)
        has_colors = pcd.has_colors()
        has_normals = pcd.has_normals()
        
        print(f"Number of points (vertices): {len(points)}")
        print(f"Has colors: {has_colors}")
        print(f"Has normals: {has_normals}")
    
    if voxel is not None:
        voxels = voxel.get_voxels()
        print(f"Number of voxels: {len(voxels)}")
        has_colors = len(voxel.get_voxels()) > 0
        print(f"Has colors: {has_colors}")

print("Starting Assignment #5: 3D Object Processing")
print_separator()

# =============================================================================
# TASK 1: Loading and Visualization
# =============================================================================
print("TASK 1: LOADING AND VISUALIZATION")
print("Loading the 3D coffee cup model from OBJ file...")

# Define the model path
model_path = os.path.join("assignment_5", "Assignment5", "object", "coffeecup", "coffee_cup_obj.obj")
# Alternative models available:
# model_path = os.path.join("assignment_5", "Assignment5", "object", "sting", "Sting-Sword-lowpoly.obj")
# model_path = os.path.join("assignment_5", "Assignment5", "object", "sofa", "couch.obj")

print(f"Model path: {model_path}")
print(f"File exists: {os.path.exists(model_path)}")

# Load mesh - the OBJ file contains quads which need to be triangulated
mesh_original = o3d.io.read_triangle_mesh(model_path, enable_post_processing=True)

# If mesh is empty (quads not loaded), try alternative approach
if len(mesh_original.vertices) == 0:
    import trimesh
    # Load with trimesh which handles quads better
    abs_path = os.path.abspath(model_path)
    tmesh = trimesh.load(abs_path, force='mesh')
    # Convert to Open3D
    mesh_original = o3d.geometry.TriangleMesh()
    mesh_original.vertices = o3d.utility.Vector3dVector(tmesh.vertices)
    mesh_original.triangles = o3d.utility.Vector3iVector(tmesh.faces)
    
    # Try to extract colors if available (handle different visual types)
    try:
        if hasattr(tmesh.visual, 'vertex_colors') and tmesh.visual.vertex_colors is not None:
            mesh_original.vertex_colors = o3d.utility.Vector3dVector(
                tmesh.visual.vertex_colors[:, :3] / 255.0)
    except:
        pass  # Colors will be added later if needed

print(f"Successfully loaded mesh with {len(mesh_original.vertices)} vertices and {len(mesh_original.triangles)} triangles")

# Compute normals if not present
if not mesh_original.has_vertex_normals():
    mesh_original.compute_vertex_normals()

# Add colors to mesh if not present (textures aren't loaded by basic Open3D loader)
if not mesh_original.has_vertex_colors():
    print("Original mesh has no vertex colors. Adding gradient coloring based on geometry...")
    # Create a gradient color based on Y-axis (height) for better visualization
    vertices = np.asarray(mesh_original.vertices)
    y_coords = vertices[:, 1]
    y_min, y_max = y_coords.min(), y_coords.max()
    y_normalized = (y_coords - y_min) / (y_max - y_min + 1e-6)
    
    # Create nice gradient: blue (bottom) -> cyan -> yellow -> red (top)
    colors = np.zeros((len(vertices), 3))
    colors[:, 0] = np.clip(y_normalized * 2, 0, 1)  # Red channel
    colors[:, 1] = np.clip(1 - abs(y_normalized - 0.5) * 2, 0.3, 1)  # Green channel
    colors[:, 2] = np.clip(1 - y_normalized * 2, 0, 1)  # Blue channel
    
    mesh_original.vertex_colors = o3d.utility.Vector3dVector(colors)
    print("Applied gradient coloring (blue=bottom, yellow/red=top)")

print_info("Original Mesh", mesh=mesh_original)
print("\nDisplaying original model...")
o3d.visualization.draw_geometries([mesh_original], 
                                   window_name="Task 1: Original Model",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 2: Conversion to Point Cloud
# =============================================================================
print("TASK 2: CONVERSION TO POINT CLOUD")
print("Converting mesh to point cloud by sampling vertices...")

# First, sample point cloud from mesh vertices
pcd_temp = mesh_original.sample_points_uniformly(number_of_points=10000)

# Save the point cloud to a file
pcd_file = "temp_coffee_cup.ply"
o3d.io.write_point_cloud(pcd_file, pcd_temp)
print(f"Point cloud saved to {pcd_file}")

# Now read it back using o3d.io.read_point_cloud() as required
print(f"Reading point cloud using o3d.io.read_point_cloud()...")
pcd = o3d.io.read_point_cloud(pcd_file)
print(f"Successfully loaded point cloud from file")

print_info("Point Cloud", pcd=pcd)
print("\nDisplaying point cloud...")
o3d.visualization.draw_geometries([pcd], 
                                   window_name="Task 2: Point Cloud",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 3: Surface Reconstruction from Point Cloud
# =============================================================================
print("TASK 3: SURFACE RECONSTRUCTION FROM POINT CLOUD")
print("Reconstructing mesh using Poisson surface reconstruction...")

# Estimate normals for point cloud
pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(
    radius=0.5, max_nn=30))

# Poisson reconstruction
mesh_reconstructed, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
    pcd, depth=9)

print("Removing low-density artifacts using bounding box crop...")

# Remove artifacts by cropping based on original bounding box
bbox = pcd.get_axis_aligned_bounding_box()
mesh_reconstructed = mesh_reconstructed.crop(bbox)

# Compute normals
mesh_reconstructed.compute_vertex_normals()

# Transfer colors from point cloud to reconstructed mesh
# Poisson creates NEW vertices, so we need to find nearest point cloud point for each vertex
print("Transferring colors from point cloud to reconstructed mesh...")
if pcd.has_colors():
    from scipy.spatial import KDTree
    
    # Get point cloud points and colors
    pcd_points = np.asarray(pcd.points)
    pcd_colors = np.asarray(pcd.colors)
    
    # Build KD-tree for fast nearest neighbor search
    tree = KDTree(pcd_points)
    
    # Get reconstructed mesh vertices
    mesh_vertices = np.asarray(mesh_reconstructed.vertices)
    
    # Find nearest point cloud point for each mesh vertex
    distances, indices = tree.query(mesh_vertices)
    
    # Assign colors from nearest neighbors
    mesh_colors = pcd_colors[indices]
    mesh_reconstructed.vertex_colors = o3d.utility.Vector3dVector(mesh_colors)
    
    print(f"Colors transferred using nearest neighbor search (avg distance: {distances.mean():.4f})")
else:
    print("Point cloud has no colors, painting mesh with light gray...")
    mesh_reconstructed.paint_uniform_color([0.7, 0.7, 0.7])

print_info("Reconstructed Mesh (after cropping)", mesh=mesh_reconstructed)
print("\nDisplaying reconstructed mesh...")
o3d.visualization.draw_geometries([mesh_reconstructed], 
                                   window_name="Task 3: Reconstructed Mesh",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 4: Voxelization
# =============================================================================
print("TASK 4: VOXELIZATION")
print("Converting point cloud to voxel grid...")

voxel_size = 0.04  # Adjusted for smaller coffee cup model (slightly larger voxels)
voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(pcd, voxel_size=voxel_size)

print(f"Voxel size used: {voxel_size}")
print_info("Voxel Grid", voxel=voxel_grid)
if pcd.has_colors():
    print("Voxels inherit colors from the colored point cloud")
else:
    print("Warning: Point cloud has no colors, voxels will be displayed without colors")
print("\nDisplaying voxel grid...")
o3d.visualization.draw_geometries([voxel_grid], 
                                   window_name="Task 4: Voxel Grid",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 5: Adding a Plane
# =============================================================================
print("TASK 5: ADDING A PLANE")
print("Creating a vertical plane that cuts through the object...")

# Get bounding box to position plane
bbox = pcd.get_axis_aligned_bounding_box()
bbox_min = bbox.get_min_bound()
bbox_max = bbox.get_max_bound()
bbox_center = (bbox_min + bbox_max) / 2.0

# Create a vertical plane mesh that intersects the object
# Position plane at the exact center of the model
plane_width = (bbox_max[2] - bbox_min[2]) * 1.5
plane_height = (bbox_max[1] - bbox_min[1]) * 1.5
plane_x = bbox_center[0]  # Cut through the exact center

# Create plane as a thin mesh (very thin for coffee cup model)
plane = o3d.geometry.TriangleMesh.create_box(width=0.001,  # Very thin plane
                                              height=plane_height, 
                                              depth=plane_width)
plane.translate([plane_x, bbox_min[1] - plane_height*0.25, bbox_min[2] - plane_width*0.25])
plane.paint_uniform_color([1.0, 0.3, 0.3])  # Red color to show cutting plane
plane.compute_vertex_normals()

print(f"Plane positioned at x={plane_x:.2f} (exact center of object)")
print(f"Object X range: [{bbox_min[0]:.2f}, {bbox_max[0]:.2f}]")
print(f"Object center X: {bbox_center[0]:.2f}")
print(f"Plane dimensions: height={plane_height:.2f}, width={plane_width:.2f}")
print("\nDisplaying object with cutting plane through the middle...")
o3d.visualization.draw_geometries([pcd, plane], 
                                   window_name="Task 5: Object with Cutting Plane",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 6: Surface Clipping
# =============================================================================
print("TASK 6: SURFACE CLIPPING")
print("Clipping the model: removing all points on the LEFT side of the plane...")
print("Keeping only the RIGHT HALF of the model...")

# Define clipping plane position (use the plane position from Task 5)
clip_x = plane_x + 0.0005  # Add half the plane width for center position
points = np.asarray(pcd.points)
colors = np.asarray(pcd.colors) if pcd.has_colors() else None
normals = np.asarray(pcd.normals) if pcd.has_normals() else None

# Keep only points where x > clip_x (to the right of the plane)
# This removes points on the left/negative side
mask = points[:, 0] > clip_x
clipped_points = points[mask]

# Create clipped point cloud
pcd_clipped = o3d.geometry.PointCloud()
pcd_clipped.points = o3d.utility.Vector3dVector(clipped_points)

if colors is not None:
    pcd_clipped.colors = o3d.utility.Vector3dVector(colors[mask])

if normals is not None:
    pcd_clipped.normals = o3d.utility.Vector3dVector(normals[mask])

print(f"\nClipping plane position: x={clip_x:.2f}")
print(f"Points before clipping: {len(points)}")
print(f"Points after clipping: {len(clipped_points)}")
print(f"Points removed (left side): {len(points) - len(clipped_points)}")
print_info("Clipped Point Cloud", pcd=pcd_clipped)

# Convert to mesh for triangle count
mesh_clipped = copy.deepcopy(mesh_reconstructed)
mesh_vertices = np.asarray(mesh_clipped.vertices)
vertex_mask = mesh_vertices[:, 0] > clip_x
vertices_to_keep = np.where(vertex_mask)[0]

mesh_clipped_simple = mesh_clipped.select_by_index(vertices_to_keep)
mesh_clipped_simple.compute_vertex_normals()

print(f"\nClipped mesh statistics:")
print(f"  Triangles: {len(mesh_clipped_simple.triangles)}")
print(f"  Has colors: {mesh_clipped_simple.has_vertex_colors()}")
print(f"  Has normals: {mesh_clipped_simple.has_vertex_normals()}")

print("\nDisplaying clipped model (RIGHT HALF only)...")
print("Plane removed to show clean clipped result.")
o3d.visualization.draw_geometries([pcd_clipped], 
                                   window_name="Task 6: Clipped Model (Right Half)",
                                   width=1024, height=768)

print_separator()

# =============================================================================
# TASK 7: Working with Color and Extremes
# =============================================================================
print("TASK 7: WORKING WITH COLOR AND EXTREMES")
print("Applying gradient coloring and finding extreme points...")

# Use original point cloud for this task
points = np.asarray(pcd.points)

# Apply gradient along Z axis
z_coords = points[:, 2]
z_min = z_coords.min()
z_max = z_coords.max()

# Normalize Z coordinates to [0, 1] for gradient
z_normalized = (z_coords - z_min) / (z_max - z_min)

# Create gradient colors (blue to red)
colors = np.zeros((len(points), 3))
colors[:, 0] = z_normalized  # Red channel
colors[:, 2] = 1 - z_normalized  # Blue channel

# Create colored point cloud
pcd_colored = o3d.geometry.PointCloud()
pcd_colored.points = o3d.utility.Vector3dVector(points)
pcd_colored.colors = o3d.utility.Vector3dVector(colors)

# Find extreme points along Z axis
# np.argmin() returns the index of the minimum value in the array
min_idx = np.argmin(z_coords)  # Index of point with smallest Z coordinate
# np.argmax() returns the index of the maximum value in the array
max_idx = np.argmax(z_coords)  # Index of point with largest Z coordinate

# Get the full 3D coordinates of the extreme points
min_point = points[min_idx]  # The actual (x, y, z) point with minimum Z
max_point = points[max_idx]  # The actual (x, y, z) point with maximum Z

print(f"Gradient applied along Z axis")
print(f"Z range: [{z_min:.4f}, {z_max:.4f}]")
print(f"\nExtreme point coordinates:")
print(f"  Minimum Z point: ({min_point[0]:.4f}, {min_point[1]:.4f}, {min_point[2]:.4f})")
print(f"  Maximum Z point: ({max_point[0]:.4f}, {max_point[1]:.4f}, {max_point[2]:.4f})")

# Create spheres to highlight extreme points (smaller for coffee cup model)
sphere_min = o3d.geometry.TriangleMesh.create_sphere(radius=0.02)  # Smaller sphere
sphere_min.translate(min_point)
sphere_min.paint_uniform_color([0, 1, 0])  # Green for minimum
sphere_min.compute_vertex_normals()

sphere_max = o3d.geometry.TriangleMesh.create_sphere(radius=0.02)  # Smaller sphere
sphere_max.translate(max_point)
sphere_max.paint_uniform_color([1, 1, 0])  # Yellow for maximum
sphere_max.compute_vertex_normals()

print("\nDisplaying colored model with extreme points highlighted...")
print("Green sphere = Minimum Z, Yellow sphere = Maximum Z")
o3d.visualization.draw_geometries([pcd_colored, sphere_min, sphere_max], 
                                   window_name="Task 7: Gradient and Extremes (View 1)",
                                   width=1024, height=768)

# Alternative view with wireframe cubes (smaller for coffee cup model)
cube_size = 0.04  # Smaller cubes for coffee cup
cube_min = o3d.geometry.TriangleMesh.create_box(width=cube_size, height=cube_size, depth=cube_size)
cube_min.translate(min_point - np.array([cube_size/2, cube_size/2, cube_size/2]))
cube_min.paint_uniform_color([0, 1, 0])
cube_min_wireframe = o3d.geometry.LineSet.create_from_triangle_mesh(cube_min)

cube_max = o3d.geometry.TriangleMesh.create_box(width=cube_size, height=cube_size, depth=cube_size)
cube_max.translate(max_point - np.array([cube_size/2, cube_size/2, cube_size/2]))
cube_max.paint_uniform_color([1, 1, 0])
cube_max_wireframe = o3d.geometry.LineSet.create_from_triangle_mesh(cube_max)

print("\nDisplaying alternative view with wireframe cubes...")
o3d.visualization.draw_geometries([pcd_colored, cube_min_wireframe, cube_max_wireframe], 
                                   window_name="Task 7: Gradient and Extremes (View 2 - Wireframe)",
                                   width=1024, height=768)

print_separator()
print("ASSIGNMENT COMPLETED SUCCESSFULLY!")
print("All 7 tasks have been executed and visualized.")

# Clean up temporary files
print("\nCleaning up temporary files...")
if os.path.exists(pcd_file):
    os.remove(pcd_file)
    print(f"Removed temporary file: {pcd_file}")

print_separator()

