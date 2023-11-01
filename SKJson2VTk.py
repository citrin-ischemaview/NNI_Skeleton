import math
import json
import os

VERTICES_KEY = 'SurfaceMeshVertices'
FACES_KEY = 'SurfaceMeshFaces'
MATRIX_KEY = 'TransformationMatrix'
SKPOINTS_KEY = 'SkPoints'
SKEDGES_KEY = 'SkEdges'

# returns dictonary object of json
def ParseJson(json_path):
    with open(json_path) as json_file:
        return json.load(json_file)

def write_vtk_unstructured_grid_centerline(mesh_vertices, mesh_faces, filename):  
    # Open file for writing
    file = open(filename, "w")

    # Write header information
    file.write("# vtk DataFile Version 3.0\n")
    file.write("Unstructured Grid Example\n")
    file.write("ASCII\n")
    file.write("DATASET UNSTRUCTURED_GRID\n")
    
    all_points = []
    all_cells = []
    num_points = 0
    
    # mesh vertices
    for vertex in mesh_vertices:
        all_points.append([vertex[0],vertex[1],vertex[2]])
        num_points += 1
        
    # mesh faces   
    cnt = 0
    for face in mesh_faces:
        all_cells.append(face)
        cnt += 1
  
        
    # add points to vtk file 
    file.write("POINTS " + str(num_points) + " float\n")
    for vertex in all_points:
        file.write(str(vertex[0]) + " " + str(vertex[1]) + " " + str(vertex[2]) + "\n")
    
    num_cells = len(all_cells)
    num_cell_points = sum([len(cell) for cell in all_cells])
    file.write("CELLS " + str(num_cells) + " " + str(num_cell_points + num_cells) + "\n")
    
    for cell in all_cells:
        face = cell
        num_face_vertices = len(face)
        file.write(str(num_face_vertices) + " ")
        for vertex_index in face:
            file.write(str(vertex_index) + " ")
        file.write("\n")
    
    # Write cell types
    file.write("CELL_TYPES " + str(num_cells) + "\n")
    for cell in all_cells:
        face = cell
        
        num_face_vertices = len(face)
        if num_face_vertices == 4:
            # Quad
            file.write("9\n")
        elif num_face_vertices == 3:
            # Triangle
            file.write("5\n")
        elif num_face_vertices == 2:
            # Edge
            file.write("3\n")
        else:
            raise ValueError("Invalid number of vertices for face")
    
    # Close file
    file.close()


def write_vtk_unstructured_grid(mesh_vertices, mesh_faces, filename):  
    # Open file for writing
    file = open(filename, "w")

    # Write header information
    file.write("# vtk DataFile Version 3.0\n")
    file.write("Unstructured Grid Example\n")
    file.write("ASCII\n")
    file.write("DATASET UNSTRUCTURED_GRID\n")
    
    all_points = []
    all_cells = []
    num_points = 0
    
    # mesh vertices
    for vertex in mesh_vertices:
        all_points.append([vertex[0],vertex[1],vertex[2]])
        num_points += 1
        
    # mesh faces   
    cnt = 0
    for face in mesh_faces:
        all_cells.append(face)
        cnt += 1
  
        
    # add points to vtk file 
    file.write("POINTS " + str(num_points) + " float\n")
    for vertex in all_points:
        file.write(str(vertex[0]) + " " + str(vertex[1]) + " " + str(vertex[2]) + "\n")
    
    num_cells = len(all_cells)
    num_cell_points = sum([len(cell) for cell in all_cells])
    file.write("CELLS " + str(num_cells) + " " + str(num_cell_points + num_cells) + "\n")
    
    for cell in all_cells:
        face = cell
        num_face_vertices = len(face)
        file.write(str(num_face_vertices) + " ")
        for vertex_index in face:
            file.write(str(vertex_index) + " ")
        file.write("\n")
    
    # Write cell types
    file.write("CELL_TYPES " + str(num_cells) + "\n")
    for cell in all_cells:
        face = cell
        
        num_face_vertices = len(face)
        if num_face_vertices == 4:
            # Quad
            file.write("9\n")
        elif num_face_vertices == 3:
            # Triangle
            file.write("5\n")
        elif num_face_vertices == 2:
            # Edge
            file.write("3\n")
        else:
            raise ValueError("Invalid number of vertices for face")
    
    # Close file
    file.close()

def ParseDataFromJsons(skeleton_json_path):
    skeleton_data = ParseJson(skeleton_json_path)
    
    mesh_vertices = []
    raw_vertices = skeleton_data[VERTICES_KEY]
    for i in range(int(len(raw_vertices)/3)):
        mesh_vertices.append([raw_vertices[i * 3 + 0],raw_vertices[i * 3 + 1],raw_vertices[i * 3 + 2]])
        
    mesh_faces = []
    raw_faces = skeleton_data[FACES_KEY]
    for i in range(int(len(raw_faces)/3)):
        mesh_faces.append([raw_faces[i * 3 + 0],raw_faces[i * 3 + 1],raw_faces[i * 3 + 2]])
        
    sk_points = []
    raw_sk_points = skeleton_data[SKPOINTS_KEY]
    for i in range(int(len(raw_sk_points)/3)):
        sk_points.append([raw_sk_points[i * 3 + 0],raw_sk_points[i * 3 + 1],raw_sk_points[i * 3 + 2]])    
    sk_edges = []
    raw_sk_edges = skeleton_data[SKEDGES_KEY]
    for i in range(int(len(raw_sk_edges)/2)):
        sk_edges.append([raw_sk_edges[i * 2 + 0],raw_sk_edges[i * 2 + 1]])    
        
    return mesh_vertices, mesh_faces, sk_points, sk_edges
    
def WriteVesselAndCenterlineVtk(sk_json, case_name, output_path):
    
    vertices, faces, sk_points, sk_edges = ParseDataFromJsons(sk_json)
    
    vessel_vtk_path = os.path.join(output_path,case_name + "_Vessel.vtk")
    centerline_vtk_path = os.path.join(output_path,case_name + "_Centerline.vtk")

    write_vtk_unstructured_grid(vertices, faces, vessel_vtk_path)
    write_vtk_unstructured_grid(sk_points, sk_edges, centerline_vtk_path)