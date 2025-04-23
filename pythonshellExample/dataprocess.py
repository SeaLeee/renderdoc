import pandas as pd
import numpy as np
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import glob

def clean_and_analyze_texture_density(csv_file, output_dir=None):
    """
    处理和分析从TextureViewer导出的纹理密度数据，输出为Excel表格
    
    参数:
        csv_file: CSV文件路径
        output_dir: 输出目录，如果为None则使用CSV文件所在目录
    """
    print(f"正在读取CSV文件: {csv_file}")
    
    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(csv_file))
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 从文件名提取基本名称(不含路径和扩展名)
    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    
    # 读取CSV数据
    df = pd.read_csv(csv_file)
    
    # 显示初始数据信息
    print(f"原始数据行数: {len(df)}")
    print(f"列名: {list(df.columns)}")
    
    # 确定正确的列名
    # 尝试找到像素密度、简化密度和网格密度列
    pixel_density_col = None
    simplified_density_col = None
    mesh_density_col = None
    
    # 查找像素密度列
    for col in df.columns:
        if 'Pixel Density' in col:
            pixel_density_col = col
            break
    
    # 查找简化密度列
    for col in df.columns:
        if 'Simplified Density' in col:
            simplified_density_col = col
            break
    
    # 查找网格密度列
    for col in df.columns:
        if 'Mesh Density' in col:
            mesh_density_col = col
            break
    
    if not pixel_density_col:
        raise ValueError(f"找不到像素密度列。请检查CSV文件 {csv_file} 包含'Pixel Density'列。")
    
    print(f"找到像素密度列: {pixel_density_col}")
    print(f"找到简化密度列: {simplified_density_col}")
    print(f"找到网格密度列: {mesh_density_col}")
    
    # 1. 数据清洗
    # 移除包含NaN的行
    df_cleaned = df.dropna()
    print(f"删除NaN后的行数: {len(df_cleaned)}")
    
    # 移除纹理密度为0的行
    df_cleaned = df_cleaned[df_cleaned[pixel_density_col] > 0]
    print(f"删除密度为0后的行数: {len(df_cleaned)}")
    
    # 移除包含inf的行
    df_cleaned = df_cleaned.replace([np.inf, -np.inf], np.nan).dropna()
    print(f"删除无穷值后的行数: {len(df_cleaned)}")
    
    # 2. 提取路径的第一部分进行分组
    def extract_first_path(path):
        if pd.isna(path) or path == '':
            return 'Unknown'
        parts = path.split('/')
        if len(parts) > 0:
            return parts[0]
        return 'Unknown'
    
    df_cleaned['PathGroup'] = df_cleaned['Pass Path'].apply(extract_first_path)
    
    # 显示路径组的汇总信息
    path_group_counts = df_cleaned['PathGroup'].value_counts()
    print("\n路径组分布:")
    print(path_group_counts)
    
    # 3. 生成Excel报告
    excel_file = os.path.join(output_dir, f'{base_name}_analysis.xlsx')
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        # 3.1 清洗后的数据
        df_cleaned.to_excel(writer, sheet_name='清洗后数据', index=False)
        
        # 3.2 按路径组的统计信息
        agg_dict = {
            pixel_density_col: ['count', 'mean', 'median', 'min', 'max', 'std'],
            'Triangle Count': ['sum', 'mean', 'median', 'min', 'max']
        }
        
        if simplified_density_col:
            agg_dict[simplified_density_col] = ['mean', 'median', 'min', 'max', 'std']
        
        if mesh_density_col:
            agg_dict[mesh_density_col] = ['mean', 'median', 'min', 'max', 'std']
        
        path_stats = df_cleaned.groupby('PathGroup').agg(agg_dict)
        path_stats.columns = ['_'.join(col).strip() for col in path_stats.columns.values]
        path_stats.reset_index(inplace=True)
        path_stats.to_excel(writer, sheet_name='路径组统计', index=False)
        
        # 新增: 密度平均值汇总表格
        density_avg_dict = {'路径组': []}
        metrics_labels = {}
        
        if pixel_density_col:
            density_avg_dict['空间纹理密度平均值'] = []
            metrics_labels['空间纹理密度平均值'] = pixel_density_col
            
        if simplified_density_col:
            density_avg_dict['简化纹理密度平均值'] = []
            metrics_labels['简化纹理密度平均值'] = simplified_density_col
            
        if mesh_density_col:
            density_avg_dict['空间网格密度平均值'] = []
            metrics_labels['空间网格密度平均值'] = mesh_density_col
        
        # 添加样本数列
        density_avg_dict['样本数'] = []
        
        # 计算每个分类的平均密度
        for group in path_group_counts.index:
            group_df = df_cleaned[df_cleaned['PathGroup'] == group]
            
            density_avg_dict['路径组'].append(group)
            density_avg_dict['样本数'].append(len(group_df))
            
            if pixel_density_col:
                density_avg_dict['空间纹理密度平均值'].append(group_df[pixel_density_col].mean())
                
            if simplified_density_col:
                density_avg_dict['简化纹理密度平均值'].append(group_df[simplified_density_col].mean())
                
            if mesh_density_col:
                density_avg_dict['空间网格密度平均值'].append(group_df[mesh_density_col].mean())
        
        # 创建并保存汇总表格
        density_avg_df = pd.DataFrame(density_avg_dict)
        density_avg_df.to_excel(writer, sheet_name='密度平均值汇总', index=False)
        
        # 为平均值汇总表添加条形图
        workbook = writer.book
        worksheet = writer.sheets['密度平均值汇总']
        
        # 按样本数量排序，只显示前10个最主要的组
        top_groups_df = density_avg_df.sort_values('样本数', ascending=False).head(10)
        
        # 为每个密度指标创建图表
        chart_row_position = len(density_avg_df) + 3
        
        for i, metric_name in enumerate(['空间纹理密度平均值', '简化纹理密度平均值', '空间网格密度平均值']):
            if metric_name in density_avg_dict:
                # 创建条形图
                chart = workbook.add_chart({'type': 'column'})
                
                # 添加数据
                worksheet.write_row(chart_row_position, 0, ['路径组'] + top_groups_df['路径组'].tolist())
                worksheet.write_row(chart_row_position+1, 0, [metric_name] + top_groups_df[metric_name].tolist())
                
                chart.add_series({
                    'name': metric_name,
                    'categories': ['密度平均值汇总', chart_row_position, 1, chart_row_position, len(top_groups_df)],
                    'values': ['密度平均值汇总', chart_row_position+1, 1, chart_row_position+1, len(top_groups_df)],
                })
                
                # 设置图表标题和轴标签
                chart.set_title({'name': f'各路径组{metric_name}'})
                chart.set_x_axis({'name': '路径组'})
                chart.set_y_axis({'name': f'{metrics_labels.get(metric_name, metric_name)}'})
                
                # 插入图表
                worksheet.insert_chart(chart_row_position+3+i*15, 1, chart, {'x_scale': 1.5, 'y_scale': 1.5})
                
                chart_row_position += 3
        
        # 3.3 路径组分布
        path_group_counts_df = pd.DataFrame({
            '路径组': path_group_counts.index,
            '数量': path_group_counts.values,
            '百分比': path_group_counts.values / path_group_counts.sum() * 100
        })
        path_group_counts_df.to_excel(writer, sheet_name='路径组分布', index=False)
        
        # 3.4 像素密度分布统计
        density_stats_dict = {
            '统计指标': ['均值', '中位数', '标准差', '最小值', '最大值', '25%分位数', '75%分位数'],
            f'{pixel_density_col}': [
                df_cleaned[pixel_density_col].mean(),
                df_cleaned[pixel_density_col].median(),
                df_cleaned[pixel_density_col].std(),
                df_cleaned[pixel_density_col].min(),
                df_cleaned[pixel_density_col].max(),
                df_cleaned[pixel_density_col].quantile(0.25),
                df_cleaned[pixel_density_col].quantile(0.75)
            ]
        }
        
        if simplified_density_col:
            density_stats_dict[simplified_density_col] = [
                df_cleaned[simplified_density_col].mean(),
                df_cleaned[simplified_density_col].median(),
                df_cleaned[simplified_density_col].std(),
                df_cleaned[simplified_density_col].min(),
                df_cleaned[simplified_density_col].max(),
                df_cleaned[simplified_density_col].quantile(0.25),
                df_cleaned[simplified_density_col].quantile(0.75)
            ]
        
        if mesh_density_col:
            density_stats_dict[mesh_density_col] = [
                df_cleaned[mesh_density_col].mean(),
                df_cleaned[mesh_density_col].median(),
                df_cleaned[mesh_density_col].std(),
                df_cleaned[mesh_density_col].min(),
                df_cleaned[mesh_density_col].max(),
                df_cleaned[mesh_density_col].quantile(0.25),
                df_cleaned[mesh_density_col].quantile(0.75)
            ]
        
        density_stats = pd.DataFrame(density_stats_dict)
        density_stats.to_excel(writer, sheet_name='密度统计', index=False)
        
        # 3.5 像素密度直方图数据
        # 创建直方图数据
        hist_data = {}
        metrics_to_process = [pixel_density_col]
        if simplified_density_col:
            metrics_to_process.append(simplified_density_col)
        if mesh_density_col:
            metrics_to_process.append(mesh_density_col)
        
        for metric in metrics_to_process:
            hist, bins = np.histogram(df_cleaned[metric], bins=50)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            hist_df = pd.DataFrame({
                '值区间': [f"{bins[i]:.2f} - {bins[i+1]:.2f}" for i in range(len(bins)-1)],
                '中心值': bin_centers,
                '频率': hist,
                '百分比': hist / hist.sum() * 100
            })
            hist_data[metric] = hist_df
        
        # 将直方图数据保存到Excel
        for metric, hist_df in hist_data.items():
            sheet_name = metric.replace('(', '_').replace(')', '_').replace('/', '_')[:31]  # Excel工作表名限制
            hist_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 3.6 路径组详细统计
        for group in path_group_counts.head(10).index:
            group_df = df_cleaned[df_cleaned['PathGroup'] == group]
            if len(group_df) > 0:
                sheet_name = f"{group}"[:31]  # 避免工作表名过长
                group_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 3.7 添加嵌入式图表 (可选)
        # 添加密度分布图表
        for metric in metrics_to_process:
            sheet_name = metric.replace('(', '_').replace(')', '_').replace('/', '_')[:31]
            worksheet = writer.sheets[sheet_name]
            
            # 创建临时图表
            plt.figure(figsize=(10, 6))
            sns.histplot(df_cleaned[metric], kde=True, bins=50)
            plt.title(f'{metric} 分布')
            
            # 保存图表到内存
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            
            # 插入图表到Excel
            worksheet.insert_image('F2', '', {'image_data': buf, 'x_scale': 0.8, 'y_scale': 0.8})

    print(f"\nExcel报告已保存到: {excel_file}")
    return df_cleaned, excel_file

if __name__ == "__main__":
    # 创建result文件夹，用于保存所有输出
    result_dir = os.path.join(os.getcwd(), "result")
    os.makedirs(result_dir, exist_ok=True)
    
    # 获取当前目录下所有的CSV文件
    csv_files = glob.glob('*.csv')
    
    if not csv_files:
        print("当前目录下未找到CSV文件!")
    else:
        print(f"找到 {len(csv_files)} 个CSV文件，开始处理...")
        
        # 处理每个CSV文件
        for i, csv_file in enumerate(csv_files):
            try:
                print(f"\n正在处理文件 {i+1}/{len(csv_files)}: {csv_file}")
                clean_and_analyze_texture_density(csv_file, result_dir)
            except Exception as e:
                print(f"处理文件 {csv_file} 时出错: {e}")
        
        print("\n所有CSV文件处理完成! 结果保存在 result 文件夹中。")