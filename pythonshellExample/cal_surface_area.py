import numpy as np
import argparse

def parse_obj(file_path):
    """解析 .obj 文件，提取顶点和面数据"""
    vertices = []
    faces = []

    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('v '):  # 顶点
                vertex = list(map(float, line.strip().split()[1:]))
                vertices.append(vertex)
            elif line.startswith('f '):  # 面
                face = line.strip().split()[1:]
                # 只提取顶点索引（忽略纹理坐标和法线）
                face = [int(vertex.split('/')[0]) - 1 for vertex in face]
                faces.append(face)

    return np.array(vertices), faces

def calculate_face_area(vertices, face):
    """计算一个面的面积"""
    # 获取面的顶点
    face_vertices = [vertices[i] for i in face]
    # 计算向量
    v0 = np.array(face_vertices[0])
    v1 = np.array(face_vertices[1])
    v2 = np.array(face_vertices[2])
    # 计算叉积
    cross_product = np.cross(v1 - v0, v2 - v0)
    # 计算面积
    area = 0.5 * np.linalg.norm(cross_product)
    return area

def calculate_surface_area(file_path):
    """计算几何体的表面积"""
    vertices, faces = parse_obj(file_path)
    total_area = 0.0

    for face in faces:
        if len(face) >= 3:  # 只处理三角形或多边形面
            total_area += calculate_face_area(vertices, face)

    return total_area

# 示例使用
if __name__ == "__main__":
    # 使用 argparse 模块从命令行读取文件路径
    parser = argparse.ArgumentParser(description="计算 .obj 文件中几何体的表面积")
    parser.add_argument("--file_path", type=str, help="输入 .obj 文件的路径")
    args = parser.parse_args()

    file_path = args.file_path
    surface_area = calculate_surface_area(file_path)
    print(f"几何体的表面积为: {surface_area:.4f}")