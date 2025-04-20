import csv
import os
import argparse
from collections import defaultdict

def csv_to_obj(csv_file, obj_file=None):
    """
    将 RenderDoc 导出的 CSV 文件转换为 OBJ 格式
    
    参数:
        csv_file (str): 输入的CSV文件路径
        obj_file (str, optional): 输出的OBJ文件路径，如果不指定，则使用与CSV相同的名称但扩展名为.obj
    """
    if obj_file is None:
        # 使用相同的文件名但扩展名为.obj
        obj_file = os.path.splitext(csv_file)[0] + '.obj'
    
    print(f"转换 {csv_file} 到 {obj_file}")
    
    # 读取CSV文件
    with open(csv_file, 'r') as f:
        # 手动读取第一行并处理标题中的空格问题
        header_line = f.readline().strip()
        header = [col.strip() for col in header_line.split(',')]
        
        # 定位重要列
        vtx_index = header.index("VTX")
        idx_index = header.index("IDX")
        
        # 找到位置(POSITION)相关列
        position_columns = {}
        for i, col in enumerate(header):
            if col.startswith("POSITION."):
                component = col.split('.')[-1]
                if component in ['x', 'y', 'z']:
                    position_columns[component] = i
        
        # 找到法线(NORMAL)相关列
        normal_columns = {}
        for i, col in enumerate(header):
            if col.startswith("NORMAL."):
                component = col.split('.')[-1]
                if component in ['x', 'y', 'z']:
                    normal_columns[component] = i
        
        # 找到纹理坐标(TEXCOORD0)相关列
        texcoord_columns = {}
        for i, col in enumerate(header):
            if col.startswith("TEXCOORD0."):
                component = col.split('.')[-1]
                if component in ['x', 'y']:
                    texcoord_columns[component] = i
        
        print(f"位置列: {position_columns}")
        print(f"法线列: {normal_columns}")
        print(f"纹理坐标列: {texcoord_columns}")
        
        # 存储所有顶点、法线和纹理坐标数据
        all_vertices = []
        all_normals = []
        all_texcoords = []
        
        # 用于记录每个顶点索引(IDX)对应的数据位置
        idx_to_data_index = {}
        
        # 用于存储按VTX顺序组织的顶点索引
        vtx_ordered_indices = []
        
        # 处理CSV的每一行
        content = f.read()
        for row in csv.reader(content.splitlines()):
            if not row or len(row) <= max(
                max(position_columns.values(), default=0),
                max(normal_columns.values(), default=0),
                max(texcoord_columns.values(), default=0)
            ):
                continue
            
            # 清理每个单元格的空格
            row = [cell.strip() for cell in row]
            
            # 获取VTX和IDX值
            vtx = int(row[vtx_index])
            idx = int(row[idx_index])
            
            try:
                # 获取位置数据
                position = [
                    float(row[position_columns['x']]),
                    float(row[position_columns['y']]),
                    float(row[position_columns['z']])
                ]
                
                # 获取法线数据
                normal = [
                    float(row[normal_columns['x']]),
                    float(row[normal_columns['y']]),
                    float(row[normal_columns['z']])
                ]
                
                # 获取纹理坐标
                texcoord = [
                    float(row[texcoord_columns['x']]),
                    float(row[texcoord_columns['y']])
                ]
                
                # 如果这个IDX还没有对应的数据索引，就添加新数据
                if idx not in idx_to_data_index:
                    idx_to_data_index[idx] = len(all_vertices)
                    all_vertices.append(position)
                    all_normals.append(normal)
                    all_texcoords.append(texcoord)
                
                # 添加顶点到VTX顺序列表
                vtx_ordered_indices.append(idx)
                
            except (ValueError, KeyError) as e:
                print(f"处理第 {vtx} 行时出错: {e}")
                continue
    
    # 生成三角形面
    faces = []
    for i in range(0, len(vtx_ordered_indices), 3):
        if i + 2 < len(vtx_ordered_indices):
            # 获取三个顶点的IDX值
            idx1 = vtx_ordered_indices[i]
            idx2 = vtx_ordered_indices[i+1]
            idx3 = vtx_ordered_indices[i+2]
            
            # 获取这些IDX对应的数据索引
            v1_index = idx_to_data_index[idx1] + 1  # OBJ索引从1开始
            v2_index = idx_to_data_index[idx2] + 1
            v3_index = idx_to_data_index[idx3] + 1
            
            faces.append([v1_index, v2_index, v3_index])
    
    # 写入OBJ文件
    with open(obj_file, 'w') as f:
        f.write("# OBJ file created from RenderDoc CSV\n")
        
        # 写入顶点
        for v in all_vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        
        # 写入纹理坐标
        for vt in all_texcoords:
            # OBJ格式中V坐标通常需要翻转
            f.write(f"vt {vt[0]} {1.0 - vt[1]}\n")
        
        # 写入法线
        for vn in all_normals:
            f.write(f"vn {vn[0]} {vn[1]} {vn[2]}\n")
        
        # 写入面 - 包含顶点、纹理和法线索引
        for face in faces:
            # 每个索引指向相应的顶点、纹理坐标和法线
            f.write(f"f {face[0]}/{face[0]}/{face[0]} {face[1]}/{face[1]}/{face[1]} {face[2]}/{face[2]}/{face[2]}\n")
    
    print(f"转换完成:")
    print(f"- 顶点数: {len(all_vertices)}")
    print(f"- 纹理坐标数: {len(all_texcoords)}")
    print(f"- 法线数: {len(all_normals)}")
    print(f"- 面数: {len(faces)}")
    print(f"OBJ文件已写入 {obj_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='将RenderDoc CSV文件转换为OBJ格式')
    parser.add_argument('csv_file', help='从RenderDoc导出的CSV文件')
    parser.add_argument('-o', '--output', help='输出的OBJ文件 (默认: 与输入文件同名但扩展名为.obj)')
    args = parser.parse_args()
    
    csv_to_obj(args.csv_file, args.output)