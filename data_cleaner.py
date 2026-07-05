"""
毕业生就业数据分析 - 数据清洗模块
==================================
读取合并后的数据，执行去重、缺失值处理、学历统一、
派生列生成等清洗操作，输出清洗后数据和质量报告。

优化点（v2）：
  - 学号去重改为保留最新签约时间记录
  - 学历映射改为字符串提取，自动兼容未知学历
"""

import pandas as pd
import numpy as np
import os


# ============================================================
# 0. 路径设置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

INPUT_FILE = os.path.join(DATA_DIR, 'merged_data.csv')
OUTPUT_FILE = os.path.join(DATA_DIR, 'clean_data.csv')


# ============================================================
# 1. 读取数据
# ============================================================

print("=" * 60)
print("【1】读取合并数据")
print("=" * 60)

df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
rows_before = len(df)
print(f"  文件: {INPUT_FILE}")
print(f"  原始行数: {rows_before}")
print(f"  原始列数: {len(df.columns)}")
print()


# ============================================================
# 2. 处理重复学号 — 按签约时间保留最新记录
# ============================================================

print("=" * 60)
print("【2】学号去重（保留最新签约时间）")
print("=" * 60)

dup_count = df['学号'].duplicated().sum()
print(f"  重复学号数: {dup_count}")

if dup_count > 0:
    dup_ids = df[df['学号'].duplicated(keep=False)]['学号'].unique()
    print(f"  涉及学号: {len(dup_ids)} 个，共 {dup_count} 条重复")

    # 尝试按时间列排序，保留最新记录
    TIME_COL = '签约时间/入学时间/毕业时间/录用时间/升学离职时间'

    if TIME_COL in df.columns:
        # 转为日期时间类型（无法解析的置 NaT，排在最后）
        df['_time_parsed'] = pd.to_datetime(df[TIME_COL], errors='coerce')
        # 按学号分组，取时间最新的那条
        df = df.sort_values(['学号', '_time_parsed'], ascending=[True, False]) \
               .drop_duplicates(subset='学号', keep='first') \
               .drop(columns=['_time_parsed']) \
               .copy()
        print(f"  去重策略: 按「{TIME_COL}」保留最新记录")
    else:
        # 兜底：保留首条
        df = df.drop_duplicates(subset='学号', keep='first').copy()
        print(f"  去重策略: 时间列不存在，保留首条（兜底）")
else:
    print(f"  无重复学号，跳过")

rows_after_dedup = len(df)
print(f"  去重后行数: {rows_after_dedup}")
print()


# ============================================================
# 3. 处理缺失值
# ============================================================

print("=" * 60)
print("【3】缺失值处理")
print("=" * 60)

# --- 3.1 "毕业去向"为空 → 标记为"待就业" ---
print("\n  [3.1] 毕业去向缺失处理")
bt_null_before = df['毕业去向'].isna().sum()
print(f"    毕业去向为空数量: {bt_null_before}")
df['毕业去向'] = df['毕业去向'].fillna('待就业')
print(f"    已将 {bt_null_before} 条毕业去向缺失记录标记为'待就业'")

# --- 3.2 "薪酬"为空或0 → 标记为 NaN ---
print("\n  [3.2] 薪酬缺失/无效值处理")
df['薪酬'] = pd.to_numeric(df['薪酬'], errors='coerce')

salary_null_before = df['薪酬'].isna().sum()
salary_zero_count = (df['薪酬'] == 0).sum()
print(f"    薪酬为 NaN 数量: {salary_null_before}")
print(f"    薪酬为 0 数量: {salary_zero_count}")

df.loc[df['薪酬'] == 0, '薪酬'] = np.nan
print(f"    处理后薪酬为 NaN 总数: {df['薪酬'].isna().sum()}")
print()


# ============================================================
# 4. 统一"学历"列
# ============================================================

print("=" * 60)
print("【4】学历列统一")
print("=" * 60)

EDU_COL = '学历状况'

print(f"\n  原始学历分布（{EDU_COL} 列）:")
edu_counts_before = df[EDU_COL].value_counts(dropna=False)
for edu, cnt in edu_counts_before.items():
    print(f"    {edu}: {cnt} 人")

# 统计结业人数（不纳入分析）
jieye_mask = df[EDU_COL].str.contains('结业', na=False)
jieye_count = jieye_mask.sum()
print(f"\n  [注意] 结业人数: {jieye_count}（不纳入就业率分析）")

# 筛选：排除结业
df = df[~jieye_mask].copy()
print(f"  排除结业后行数: {len(df)}")
print()


# ============================================================
# 5. 添加派生列
# ============================================================

print("=" * 60)
print("【5】派生列生成")
print("=" * 60)

# --- 5.1 is_employed（黑名单关键词匹配） ---
# 未就业的状态类型少且稳定（4类），已就业的类型多且多变（11类）
# 黑名单策略：匹配到未就业关键词 → False，其余 → True

UNEMPLOYED_KEYWORDS = [
    '待就业',    # 待就业
    '求职中',    # 求职中
    '拟升学',    # 拟升学、不就业拟升学
    '暂不就业',  # 暂不就业、其他暂不就业
    '不派遣',    # 不派遣（档案未派遣 = 无确定就业去向）
]

print("\n  [5.1] 就业状态判定（黑名单关键词匹配）")
print(f"    未就业判定关键词: {UNEMPLOYED_KEYWORDS}")
print(f"    策略: 毕业去向中包含任一未就业关键词 → 未就业，其余 → 已就业")

# 匹配到未就业关键词 → 未就业，其余 → 已就业
df['is_employed'] = ~df['毕业去向'].apply(
    lambda x: any(kw in str(x) for kw in UNEMPLOYED_KEYWORDS)
)

employed_count = df['is_employed'].sum()
unemployed_count = (~df['is_employed']).sum()

# 诊断：列出所有被判定为未就业的状态，确认无遗漏
unemployed_statuses = df[~df['is_employed']]['毕业去向'].value_counts()
print(f"\n    未就业状态明细：")
for status, cnt in unemployed_statuses.items():
    print(f"      [未就业] {status}: {cnt} 人")
print(f"    共 {len(unemployed_statuses)} 种未就业状态，{int(unemployed_statuses.sum())} 人")

print(f"    已就业 (True):  {employed_count} 人")
print(f"    未就业 (False): {unemployed_count} 人")
print(f"    就业率: {employed_count / len(df) * 100:.2f}%")

# --- 5.2 education_level（字符串提取，自动兼容） ---
print("\n  [5.2] 学历层级映射（从学历状况提取前两字）")
df['education_level'] = df[EDU_COL].str.extract(r'^(..)')[0]

print(f"    提取规则: 取「{EDU_COL}」列前两个字符")
print(f"    分布:")
for level, cnt in df['education_level'].value_counts().items():
    print(f"      {level}: {cnt} 人")
print()


# ============================================================
# 6. 保存清洗后数据
# ============================================================

print("=" * 60)
print("【6】保存清洗数据")
print("=" * 60)

df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print(f"  输出文件: {OUTPUT_FILE}")
print(f"  编码格式: UTF-8 with BOM (Excel 友好)")
print(f"  行数: {len(df)}")
print(f"  列数: {len(df.columns)}")
print(f"  文件大小: {os.path.getsize(OUTPUT_FILE) / 1024:.1f} KB")
print(f"\n  新增列:")
print(f"    - is_employed (bool): 是否就业")
print(f"    - education_level (str): 学历层级")
print()


# ============================================================
# 7. 数据质量报告
# ============================================================

print("=" * 60)
print("【7】数据质量报告")
print("=" * 60)

print(f"""
  ┌─────────────────────────────────────────┐
  │            清洗前后行数对比              │
  ├─────────────────────────────────────────┤
  │  原始数据行数            : {rows_before:>6}          │
  │  学号去重后行数          : {rows_after_dedup:>6}          │
  │  剔除结业后行数          : {len(df):>6}          │
  │  综合保留率              : {len(df) / rows_before * 100:>5.1f}%          │
  └─────────────────────────────────────────┘
""")

# 分学历就业统计
for edu_level in df['education_level'].unique():
    sub = df[df['education_level'] == edu_level]
    total = len(sub)
    emp = sub['is_employed'].sum()
    rate = emp / total * 100 if total > 0 else 0
    print(f"  {edu_level}: {total} 人, 就业 {int(emp)} 人, 就业率 {rate:.1f}%")

print()

# 毕业去向分布
print("  ┌─ 毕业去向分布 ───────────────────────┐")
for dest, cnt in df['毕业去向'].value_counts().items():
    marker = "[已就业]" if df[df['毕业去向'] == dest]['is_employed'].iloc[0] else "[未就业]"
    print(f"  │  {marker} {dest:<14} {cnt:>6}          │")
print("  └──────────────────────────────────────┘")

print(f"\n[DONE] 数据清洗完成！清洗后数据保存于: {OUTPUT_FILE}")
