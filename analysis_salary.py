# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 任务3：本科生的学院-专业薪酬分布
====================================================
统计维度：
  1. 按"院系"和"专业名称"分组，计算薪酬均值、中位数、最高、最低、人数
  2. 箱线图：每个学院内各专业的薪酬分布
  3. 热力图：学院-专业薪酬均值矩阵

筛选条件：
  - education_level == '本科'
  - is_employed == True
  - 薪酬 > 0

输出：
  - Excel 表格 output/salary_stats.xlsx
  - 箱线图   output/charts/salary_by_college_profession.png
  - 热力图   output/charts/salary_heatmap.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，避免弹窗
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager
import seaborn as sns

# ============================================================
# 0. 路径与输出目录
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "clean_data.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
EXCEL_PATH = os.path.join(OUTPUT_DIR, "salary_stats.xlsx")

os.makedirs(CHART_DIR, exist_ok=True)

# ============================================================
# 1. 中文字体设置
# ============================================================
def setup_chinese_font():
    """自动探测系统中可用的中文字体并设置 matplotlib 全局字体"""
    candidate_fonts = [
        "Microsoft YaHei",      # 微软雅黑
        "SimHei",               # 黑体
        "SimSun",               # 宋体
        "KaiTi",                # 楷体
        "FangSong",             # 仿宋
        "PingFang SC",          # macOS
        "Noto Sans CJK SC",     # Linux
        "WenQuanYi Micro Hei",  # Linux
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = None
    for name in candidate_fonts:
        if name in available:
            chosen = name
            break
    if chosen:
        plt.rcParams["font.sans-serif"] = [chosen, "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        print(f"[字体] 使用字体: {chosen}")
    else:
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        print("[字体] 未找到中文字体，图表中文可能显示为方框")


setup_chinese_font()

# ============================================================
# 2. 读取数据 & 筛选目标群体
# ============================================================
print("=" * 60)
print("读取清洗后数据:", DATA_PATH)
df = pd.read_csv(DATA_PATH)
print(f"总记录数: {len(df)}")

# 确保薪酬列为数值类型
df["薪酬"] = pd.to_numeric(df["薪酬"], errors="coerce")

# 筛选条件：本科生 + 已就业 + 薪酬有效（> 0）
mask = (
    (df["education_level"] == "本科") &
    (df["is_employed"] == True) &
    (df["薪酬"] > 0)
)
df_target = df[mask].copy()
print(f"本科已就业且薪酬>0 人数: {len(df_target)}")

# 检查数据是否为空
if len(df_target) == 0:
    print("[错误] 没有符合条件的记录，无法进行分析。请检查数据。")
    import sys
    sys.exit(1)

print(f"薪酬范围: {df_target['薪酬'].min():.0f} ~ {df_target['薪酬'].max():.0f}")
print(f"薪酬均值: {df_target['薪酬'].mean():.1f},  中位数: {df_target['薪酬'].median():.1f}")
print()

# ============================================================
# 3. 按院系 × 专业分组统计薪酬
# ============================================================
stats = (
    df_target.groupby(["院系", "专业名称"])
             .agg(
                 人数=("薪酬", "count"),
                 平均薪酬=("薪酬", "mean"),
                 中位数=("薪酬", "median"),
                 最高薪酬=("薪酬", "max"),
                 最低薪酬=("薪酬", "min"),
             )
             .reset_index()
)

# 四舍五入
stats["平均薪酬"] = stats["平均薪酬"].round(0).astype(int)
stats["中位数"] = stats["中位数"].round(0).astype(int)
stats["最高薪酬"] = stats["最高薪酬"].round(0).astype(int)
stats["最低薪酬"] = stats["最低薪酬"].round(0).astype(int)

# 按院系、再按平均薪酬从高到低排序
stats = stats.sort_values(["院系", "平均薪酬"], ascending=[True, False]).reset_index(drop=True)

print("=" * 60)
print("【任务3】本科生学院-专业薪酬分布统计")
print("-" * 40)
print(f"共 {stats['院系'].nunique()} 个学院, {len(stats)} 个专业方向")
print(f"总人数: {stats['人数'].sum()}")
print()
print(stats.to_string(index=False))
print()

# ============================================================
# 4. 保存为 Excel
# ============================================================
with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    stats.to_excel(writer, sheet_name="学院专业薪酬统计", index=False)

    # 额外 Sheet：按学院汇总
    college_summary = (
        df_target.groupby("院系")
                 .agg(
                     专业数=("专业名称", "nunique"),
                     总人数=("薪酬", "count"),
                     平均薪酬=("薪酬", "mean"),
                     中位数=("薪酬", "median"),
                     最高薪酬=("薪酬", "max"),
                     最低薪酬=("薪酬", "min"),
                 )
                 .reset_index()
    )
    for col in ["平均薪酬", "中位数", "最高薪酬", "最低薪酬"]:
        college_summary[col] = college_summary[col].round(0).astype(int)
    college_summary = college_summary.sort_values("平均薪酬", ascending=False).reset_index(drop=True)
    college_summary.to_excel(writer, sheet_name="学院薪酬汇总", index=False)

print(f"[Excel] 已保存至: {EXCEL_PATH}")

# ============================================================
# 5. 可视化1：学院-专业薪酬箱线图
# ============================================================
# 按院系分组，每个院系内各专业画箱线图
# 使用 seaborn 的 FacetGrid 或在同一个图上分组绘制

# 获取院系列表（按院系平均薪酬排序，与 Excel 保持一致）
college_order = (
    df_target.groupby("院系")["薪酬"].mean()
    .sort_values(ascending=False).index.tolist()
)

# 为每个学院内的专业排序（按该专业平均薪酬从高到低）
# 构建 (院系, 专业) 复合排序键
profession_order_map = {}
for college in college_order:
    sub = df_target[df_target["院系"] == college]
    ordered_majors = (
        sub.groupby("专业名称")["薪酬"].mean()
        .sort_values(ascending=False).index.tolist()
    )
    for rank, major in enumerate(ordered_majors):
        profession_order_map[(college, major)] = rank

df_target["college_rank"] = df_target["院系"].apply(
    lambda c: college_order.index(c) if c in college_order else 999
)
df_target["profession_rank"] = df_target.apply(
    lambda r: profession_order_map.get((r["院系"], r["专业名称"]), 999), axis=1
)
df_target = df_target.sort_values(["college_rank", "profession_rank"])

# 创建箱线图
num_colleges = len(college_order)
college_sizes = df_target.groupby("院系").size().reindex(college_order)

fig, ax = plt.subplots(figsize=(max(20, num_colleges * 2.2), 10))

# 对每个学院内的专业绘制箱线图
positions = []
labels = []
college_boundaries = []  # (start_pos, end_pos, college_name)
pos = 0

# 配色：为每个学院分配一种主色调（柔和调色板）
college_palette = plt.cm.tab20(np.linspace(0, 1, max(num_colleges, 20)))
# 如果学院数超过20，循环使用
if num_colleges > 20:
    college_palette = plt.cm.tab20(np.linspace(0, 1, num_colleges))

bp_data = []
bp_positions = []
bp_colors = []

# 按学院-专业分组收集箱线图数据
grouped = df_target.groupby(["院系", "专业名称"])
college_starts = []
college_ends = []
college_names = []
college_label_pos = []

current_pos = 0
for college_idx, college in enumerate(college_order):
    college_data = df_target[df_target["院系"] == college]
    # 该学院的专业按平均薪酬降序
    major_order = (
        college_data.groupby("专业名称")["薪酬"].mean()
        .sort_values(ascending=False).index.tolist()
    )

    start_pos = current_pos
    for major in major_order:
        salaries = college_data[college_data["专业名称"] == major]["薪酬"].dropna().values
        if len(salaries) > 0:
            bp_data.append(salaries)
            bp_positions.append(current_pos)
            # 同一学院的箱体用近似色调
            base_color = college_palette[college_idx % 20]
            bp_colors.append(base_color)
            labels.append(major)
            current_pos += 1
    end_pos = current_pos

    if start_pos < end_pos:
        college_starts.append(start_pos)
        college_ends.append(end_pos)
        college_names.append(college)
        college_label_pos.append((start_pos + end_pos) / 2 - 0.5)

# 绘制箱线图
boxprops = dict(linewidth=0.8)
whiskerprops = dict(linewidth=0.7)
medianprops = dict(linewidth=1.2, color="#cc0000")
flierprops = dict(marker="o", markerfacecolor="#666666", markersize=3,
                  markerfacecoloralt="#999999", alpha=0.5)

bp = ax.boxplot(
    bp_data,
    positions=bp_positions,
    patch_artist=True,
    widths=0.7,
    boxprops=boxprops,
    whiskerprops=whiskerprops,
    medianprops=medianprops,
    flierprops=flierprops,
)

# 给每个箱体上色
for patch, color in zip(bp["boxes"], bp_colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

# 绘制学院分隔背景和标注
for i, (start, end, name) in enumerate(zip(college_starts, college_ends, college_names)):
    # 交替背景色
    if i % 2 == 0:
        ax.axvspan(start - 0.5, end - 0.5, facecolor="#f0f0f0", zorder=0)
    # 学院分界线
    if start > 0:
        ax.axvline(x=start - 0.5, color="#999999", linewidth=1.2, linestyle="--", alpha=0.6)

    # 学院标注（在箱线图上方）
    mid = (start + end) / 2 - 0.5
    ax.annotate(
        name,
        xy=(mid, 1.02),
        xycoords=("data", "axes fraction"),
        fontsize=9,
        fontweight="bold",
        ha="center",
        va="bottom",
        color="#333333",
        annotation_clip=False,
    )

# x 轴标签（专业名称，可能很长所以旋转）
ax.set_xticks(bp_positions)
ax.set_xticklabels(labels, rotation=55, ha="right", fontsize=7)

ax.set_ylabel("薪酬 (元/月)", fontsize=13)
ax.set_title("本科生学院-专业薪酬分布箱线图", fontsize=16, fontweight="bold")
ax.set_ylim(0, df_target["薪酬"].max() * 1.08)

# 网格线
ax.yaxis.grid(True, linestyle="--", alpha=0.3)
ax.set_axisbelow(True)

# 去掉上右边框
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# y轴格式
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))

plt.tight_layout()

box_path = os.path.join(CHART_DIR, "salary_by_college_profession.png")
fig.savefig(box_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表-箱线图] 已保存至: {box_path}")

# ============================================================
# 6. 可视化2：学院-专业薪酬均值热力图
# ============================================================
# 构建 学院 × 专业 矩阵
pivot = stats.pivot_table(
    index="院系",
    columns="专业名称",
    values="平均薪酬",
    aggfunc="first",  # 取值（不会冲突，因为已分组）
)

# 行列排序：按每个学院的平均薪酬排序
row_order = (
    pivot.mean(axis=1)
    .sort_values(ascending=False).index.tolist()
)
# 列排序：按每个专业的平均薪酬排序（全局）
col_order = (
    pivot.mean(axis=0)
    .sort_values(ascending=False).index.tolist()
)

pivot = pivot.reindex(index=row_order, columns=col_order)

# 绘制热力图
fig_width = max(16, len(col_order) * 0.55)
fig_height = max(8, len(row_order) * 0.55)

fig, ax = plt.subplots(figsize=(fig_width, fig_height))

# 自定义色阶：浅色→深蓝（代表低→高）
cmap = sns.color_palette("YlOrRd", as_cmap=True)

# 绘制热力图
heatmap = sns.heatmap(
    pivot,
    annot=True,
    fmt=".0f",
    cmap=cmap,
    linewidths=0.6,
    linecolor="#ffffff",
    ax=ax,
    cbar_kws={
        "label": "平均薪酬 (元/月)",
        "shrink": 0.8,
    },
    annot_kws={"fontsize": 8},
    square=False,
    vmin=df_target["薪酬"].min(),
    vmax=df_target["薪酬"].max(),
)

# 样式调整
ax.set_title("本科生学院-专业平均薪酬热力图", fontsize=16, fontweight="bold", pad=20)
ax.set_xlabel("专业名称", fontsize=13)
ax.set_ylabel("院系", fontsize=13)

# x 轴标签旋转
ax.set_xticklabels(
    ax.get_xticklabels(),
    rotation=50,
    ha="right",
    fontsize=8,
)
ax.set_yticklabels(
    ax.get_yticklabels(),
    rotation=0,
    fontsize=9,
)

plt.tight_layout()

heatmap_path = os.path.join(CHART_DIR, "salary_heatmap.png")
fig.savefig(heatmap_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表-热力图] 已保存至: {heatmap_path}")

# ============================================================
# 7. 完成总结
# ============================================================
print()
print("=" * 60)
print("任务3「本科生的学院-专业薪酬分布」完成！")
print(f"  Excel:      {EXCEL_PATH}")
print(f"  箱线图:     {box_path}")
print(f"  热力图:     {heatmap_path}")
print(f"  统计范围:   education_level=本科, is_employed=True, 薪酬>0")
print(f"  有效记录数: {len(df_target)}")
print(f"  学院数:     {stats['院系'].nunique()}")
print(f"  专业方向数: {len(stats)}")
print("=" * 60)
