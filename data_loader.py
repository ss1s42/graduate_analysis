"""
毕业生就业数据分析 - 数据加载与预处理模块
============================================
读取2020届就业信息和生源信息两个Excel文件，
进行数据探索、合并，并保存为CSV供后续分析使用。
"""

import pandas as pd
import os


# ============================================================
# 1. 读取数据
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

EMPLOYMENT_FILE = os.path.join(DATA_DIR, '2020届就业信息.xlsx')
STUDENT_FILE = os.path.join(DATA_DIR, '2020届生源信息表.xlsx')

print("=" * 60)
print("正在读取数据...")
print("=" * 60)

df_employment = pd.read_excel(EMPLOYMENT_FILE)
df_student = pd.read_excel(STUDENT_FILE)

print("[OK] 读取完成！\n")


# ============================================================
# 2. 打印数据基本信息
# ============================================================

print("=" * 60)
print("【2.1】就业信息 DataFrame (df_employment)")
print("=" * 60)
print(f"  形状 (行数, 列数): {df_employment.shape}")
print(f"  行数: {df_employment.shape[0]}")
print(f"  列数: {df_employment.shape[1]}")
print()

print("  所有列名:")
for i, col in enumerate(df_employment.columns, 1):
    print(f"    [{i}] {col}")

print()
print("  各列数据类型:")
print(df_employment.dtypes.to_string())

print()
print("  前5行数据:")
print(df_employment.head().to_string())

print("\n")

print("=" * 60)
print("【2.2】生源信息 DataFrame (df_student)")
print("=" * 60)
print(f"  形状 (行数, 列数): {df_student.shape}")
print(f"  行数: {df_student.shape[0]}")
print(f"  列数: {df_student.shape[1]}")
print()

print("  所有列名:")
for i, col in enumerate(df_student.columns, 1):
    print(f"    [{i}] {col}")

print()
print("  各列数据类型:")
print(df_student.dtypes.to_string())

print()
print("  前5行数据:")
print(df_student.head().to_string())

print("\n")


# ============================================================
# 3. 检查共同关联字段并演示合并
# ============================================================

print("=" * 60)
print("【3】关联字段检查与数据合并")
print("=" * 60)

# 找出两个 DataFrame 中共有的列
common_cols = set(df_employment.columns) & set(df_student.columns)
print(f"\n  两个表的共同列: {common_cols}")

# 将"学号"作为主关联键
JOIN_KEY = '学号'

if JOIN_KEY in common_cols:
    print(f"\n  [OK] 主关联字段: '{JOIN_KEY}'")
    print(f"    - 就业信息表中 '{JOIN_KEY}' 去重后数量: {df_employment[JOIN_KEY].nunique()}")
    print(f"    - 生源信息表中 '{JOIN_KEY}' 去重后数量: {df_student[JOIN_KEY].nunique()}")
    print(f"    - 就业信息表总行数: {len(df_employment)}")
    print(f"    - 生源信息表总行数: {len(df_student)}")

    # 检查是否有重复学号
    dup_emp = df_employment[JOIN_KEY].duplicated().sum()
    dup_stu = df_student[JOIN_KEY].duplicated().sum()
    print(f"\n  重复检查:")
    print(f"    - 就业信息表中 '{JOIN_KEY}' 重复数: {dup_emp}")
    print(f"    - 生源信息表中 '{JOIN_KEY}' 重复数: {dup_stu}")

    # 找出两个表中同时存在的学号数量
    common_ids = set(df_employment[JOIN_KEY]) & set(df_student[JOIN_KEY])
    only_emp = set(df_employment[JOIN_KEY]) - set(df_student[JOIN_KEY])
    only_stu = set(df_student[JOIN_KEY]) - set(df_employment[JOIN_KEY])
    print(f"\n  交集分析:")
    print(f"    - 两表共有学号数: {len(common_ids)}")
    print(f"    - 仅在就业信息表中的学号数: {len(only_emp)}")
    print(f"    - 仅在生源信息表中的学号数: {len(only_stu)}")

    # --- 演示合并 ---
    # 对于重复列（如"生源地"、"学历"），给生源信息表的列加后缀 _stu
    # 以就业信息表的数据为准（how='left'：保留所有就业记录）

    print(f"\n  【合并演示】以 '{JOIN_KEY}' 为键，左连接（保留就业表所有记录）:")

    df_merged = pd.merge(
        df_employment,
        df_student,
        on=JOIN_KEY,            # 以学号关联
        how='left',             # 保留就业表所有记录，补充生源信息
        suffixes=('_emp', '_stu')  # 重叠列加后缀区分来源
    )

    print(f"    合并后形状: {df_merged.shape}")
    print(f"    合并后列数: {len(df_merged.columns)}")
    print(f"    合并后列名:")
    for i, col in enumerate(df_merged.columns, 1):
        print(f"      [{i}] {col}")

    print(f"\n    合并后前3行数据:")
    print(df_merged.head(3).to_string())

    # 统计匹配情况
    matched = df_merged[[c for c in df_student.columns if c != JOIN_KEY and c in df_merged.columns]].notna().any(axis=1).sum()
    unmatched = len(df_merged) - matched
    print(f"\n    匹配统计:")
    print(f"      - 成功匹配（生源信息有数据）: {matched}")
    print(f"      - 未匹配（在生源表中无对应记录）: {unmatched}")

else:
    print(f"\n  [WARN] 未找到 '{JOIN_KEY}' 列，请检查列名。")
    # 兜底：找出所有可能的关联字段
    print("  尝试查找其他可能的关联字段...")
    for col in common_cols:
        print(f"    共同列: '{col}'")


# ============================================================
# 4. 保存合并后的数据
# ============================================================

output_path = os.path.join(DATA_DIR, 'merged_data.csv')
df_merged.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n{'=' * 60}")
print(f"【4】数据已保存")
print(f"{'=' * 60}")
print(f"  文件路径: {output_path}")
print(f"  编码格式: UTF-8 with BOM (Excel友好)")
print(f"  行数: {len(df_merged)}")
print(f"  列数: {len(df_merged.columns)}")

# 顺便输出一份简要的统计信息
print(f"\n  文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
print(f"\n[DONE] 全部完成！后续可直接用 pd.read_csv('{output_path}') 加载合并数据。")
