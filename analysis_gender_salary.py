# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 任务4：不同性别的学院-专业薪酬分布
====================================================
统计维度：
  1. 按性别分组，分别统计男、女在各"学院-专业"的平均薪酬、中位数、人数
  2. 按学院分组，男女并排柱状图展示平均薪酬差异
  3. 男女薪酬分布密度曲线对比

筛选条件：
  - education_level == '本科'
  - is_employed == True
  - 薪酬 > 0

输出：
  - Excel 表格 output/gender_salary_stats.xlsx
  - 柱状图   output/charts/gender_salary_by_college.png
  - 密度曲线 output/charts/gender_salary_density.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 非交互式后端，避免弹窗
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager

# ============================================================
# 0. 路径与输出目录
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "clean_data.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CHART_DIR = os.path.join(OUTPUT_DIR, "charts")
EXCEL_PATH = os.path.join(OUTPUT_DIR, "gender_salary_stats.xlsx")

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

if len(df_target) == 0:
    print("[错误] 没有符合条件的记录，无法进行分析。请检查数据。")
    import sys
    sys.exit(1)

# 确认性别分布
gender_counts = df_target["性别"].value_counts()
print(f"性别分布:\n{gender_counts}\n")

# ============================================================
# 3. 按学院-专业 × 性别分组统计薪酬
# ============================================================
# 分别按男女分组统计
def gender_salary_stats(data, gender_label, gender_value):
    """按学院-专业分组，统计该性别的薪酬指标"""
    sub = data[data["性别"] == gender_value]
    if len(sub) == 0:
        return pd.DataFrame()
    stats = (
        sub.groupby(["院系", "专业名称"])
           .agg(
               人数=("薪酬", "count"),
               平均薪酬=("薪酬", "mean"),
               中位数=("薪酬", "median"),
           )
           .reset_index()
    )
    stats = stats.rename(columns={
        "人数": f"{gender_label}样本量",
        "平均薪酬": f"{gender_label}平均薪酬",
        "中位数": f"{gender_label}中位数",
    })
    return stats


male_stats = gender_salary_stats(df_target, "男", "男")
female_stats = gender_salary_stats(df_target, "女", "女")

# 合并男女统计表
stats = pd.merge(
    male_stats,
    female_stats,
    on=["院系", "专业名称"],
    how="outer"
)

# 填充缺失值：没有该性别的专业用 0 或 NaN 标记
for col in ["男样本量", "女样本量"]:
    stats[col] = stats[col].fillna(0).astype(int)
for col in ["男平均薪酬", "男中位数", "女平均薪酬", "女中位数"]:
    stats[col] = stats[col].round(0)

# 计算总样本量，并按院系 + 总样本量排序
stats["总样本量"] = stats["男样本量"] + stats["女样本量"]
stats = stats.sort_values(["院系", "总样本量"], ascending=[True, False]).reset_index(drop=True)

# 重新排列列顺序
stats = stats[[
    "院系", "专业名称",
    "男平均薪酬", "女平均薪酬",
    "男中位数", "女中位数",
    "男样本量", "女样本量",
    "总样本量",
]]

print("=" * 60)
print("【任务4】不同性别的学院-专业薪酬分布统计")
print("-" * 40)
print(f"共 {stats['院系'].nunique()} 个学院, {len(stats)} 个专业方向")
print()

# 打印前20行和前20行
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 20)
print("=== 男女薪酬差异最大的专业（按差值绝对值降序，前20） ===")
# 计算差异（仅统计两性均有数据的专业）
stats_diff = stats[(stats["男样本量"] > 0) & (stats["女样本量"] > 0)].copy()
stats_diff["男女薪酬差"] = stats_diff["男平均薪酬"] - stats_diff["女平均薪酬"]
stats_diff = stats_diff.sort_values("男女薪酬差", key=abs, ascending=False)
print(stats_diff[["院系", "专业名称", "男平均薪酬", "女平均薪酬", "男女薪酬差", "男样本量", "女样本量"]]
      .head(20).to_string(index=False))
print()

# ============================================================
# 4. 保存为 Excel（多 Sheet）
# ============================================================
with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    # Sheet 1: 明细表
    stats.to_excel(writer, sheet_name="学院专业性别薪酬统计", index=False)

    # Sheet 2: 按学院汇总
    college_gender_summary = (
        df_target.groupby(["院系", "性别"])
                 .agg(
                     专业数=("专业名称", "nunique"),
                     人数=("薪酬", "count"),
                     平均薪酬=("薪酬", "mean"),
                     中位数=("薪酬", "median"),
                 )
                 .reset_index()
    )
    college_gender_summary["平均薪酬"] = college_gender_summary["平均薪酬"].round(0).astype(int)
    college_gender_summary["中位数"] = college_gender_summary["中位数"].round(0).astype(int)
    college_gender_summary = college_gender_summary.sort_values(["院系", "性别"]).reset_index(drop=True)
    college_gender_summary.to_excel(writer, sheet_name="学院性别薪酬汇总", index=False)

    # Sheet 3: 每个学院的男女差异汇总（pivot形式，更直观）
    college_pivot = (
        df_target.groupby(["院系", "性别"])["薪酬"]
                 .agg(["mean", "median", "count"])
                 .reset_index()
    )
    # 构建宽表
    pivot_rows = []
    for college in df_target["院系"].unique():
        row = {"学院": college}
        for gender, label in [("男", "男"), ("女", "女")]:
            sub = college_pivot[(college_pivot["院系"] == college) & (college_pivot["性别"] == gender)]
            if len(sub) > 0:
                row[f"{label}平均薪酬"] = round(sub["mean"].values[0], 0)
                row[f"{label}中位数"] = round(sub["median"].values[0], 0)
                row[f"{label}样本量"] = int(sub["count"].values[0])
            else:
                row[f"{label}平均薪酬"] = None
                row[f"{label}中位数"] = None
                row[f"{label}样本量"] = 0
        # 差值
        if row["男平均薪酬"] is not None and row["女平均薪酬"] is not None:
            row["男女平均薪酬差"] = round(row["男平均薪酬"] - row["女平均薪酬"], 0)
        else:
            row["男女平均薪酬差"] = None
        pivot_rows.append(row)

    college_pivot_df = pd.DataFrame(pivot_rows)
    college_pivot_df = college_pivot_df.sort_values("男女平均薪酬差", key=abs, ascending=False, na_position="last")
    college_pivot_df.to_excel(writer, sheet_name="学院男女薪酬差异", index=False)

print(f"[Excel] 已保存至: {EXCEL_PATH}")

# ============================================================
# 5. 可视化1：按学院分组的男女并排平均薪酬柱状图
# ============================================================
# 仅保留男女均有数据的学院，且样本量足够
MIN_SAMPLES = 5

college_data = []
for college in df_target["院系"].unique():
    sub = df_target[df_target["院系"] == college]
    male_salaries = sub[sub["性别"] == "男"]["薪酬"]
    female_salaries = sub[sub["性别"] == "女"]["薪酬"]
    male_count = len(male_salaries)
    female_count = len(female_salaries)
    # 至少一方样本量足够才纳入
    if male_count >= MIN_SAMPLES or female_count >= MIN_SAMPLES:
        college_data.append({
            "学院": college,
            "男平均薪酬": male_salaries.mean() if male_count > 0 else 0,
            "女平均薪酬": female_salaries.mean() if female_count > 0 else 0,
            "男中位数": male_salaries.median() if male_count > 0 else 0,
            "女中位数": female_salaries.median() if female_count > 0 else 0,
            "男样本量": male_count,
            "女样本量": female_count,
        })

college_df = pd.DataFrame(college_data)
# 按男+女平均薪酬排序（优先用总体均值）
college_df["综合平均"] = (
    (college_df["男平均薪酬"] * college_df["男样本量"] +
     college_df["女平均薪酬"] * college_df["女样本量"]) /
    (college_df["男样本量"] + college_df["女样本量"])
)
college_df = college_df.sort_values("综合平均", ascending=False).reset_index(drop=True)

if len(college_df) == 0:
    print("[警告] 没有学院满足样本量条件（>=5），跳过柱状图绘制。")
else:
    fig, ax = plt.subplots(figsize=(14, max(7, len(college_df) * 0.6)))

    x = np.arange(len(college_df))
    bar_width = 0.35

    bars_male = ax.bar(
        x - bar_width / 2, college_df["男平均薪酬"],
        bar_width, label="男",
        color="#4A90D9", edgecolor="#2C5F8A", linewidth=0.6, alpha=0.88,
    )
    bars_female = ax.bar(
        x + bar_width / 2, college_df["女平均薪酬"],
        bar_width, label="女",
        color="#E85D75", edgecolor="#B33F52", linewidth=0.6, alpha=0.88,
    )

    # 在柱形顶端标注数值
    def label_bars(bars, fontsize=8):
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2, height + 30,
                    f"{height:.0f}",
                    ha="center", va="bottom", fontsize=fontsize, color="#333333",
                )

    label_bars(bars_male)
    label_bars(bars_female)

    # 标注样本量
    for i, row in college_df.iterrows():
        ax.text(
            i, -80,
            f"♂{int(row['男样本量'])} ♀{int(row['女样本量'])}",
            ha="center", va="top", fontsize=7, color="#666666",
        )

    # 标题与标签
    ax.set_xticks(x)
    ax.set_xticklabels(college_df["学院"], rotation=30, ha="right", fontsize=10)
    ax.set_ylabel("平均薪酬 (元/月)", fontsize=13)
    ax.set_title("不同性别各学院平均薪酬对比（本科）", fontsize=16, fontweight="bold")
    ax.legend(fontsize=12, loc="upper right")

    # 设置 Y 轴范围，底部留空间给样本量标注
    y_max = max(college_df["男平均薪酬"].max(), college_df["女平均薪酬"].max()) * 1.15
    ax.set_ylim(-150, y_max)

    # 网格线
    ax.yaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    # 去掉上右边框
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Y 轴格式
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))

    plt.tight_layout()

    bar_path = os.path.join(CHART_DIR, "gender_salary_by_college.png")
    fig.savefig(bar_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[图表-柱状图] 已保存至: {bar_path}")

# ============================================================
# 6. 可视化2：男女薪酬分布密度曲线
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

male_salaries_all = df_target[df_target["性别"] == "男"]["薪酬"].dropna()
female_salaries_all = df_target[df_target["性别"] == "女"]["薪酬"].dropna()

print(f"\n男样本量: {len(male_salaries_all)}, 女样本量: {len(female_salaries_all)}")

# 绘制 KDE 密度曲线
from scipy import stats as scipy_stats

# 使用 seaborn 的 kdeplot 或者手动用 scipy gaussian_kde
# 这里采用 matplotlib 直方图 + 密度曲线结合的方式，更直观
# 先绘制填充的密度区域
bins = np.linspace(
    min(male_salaries_all.min(), female_salaries_all.min()),
    max(male_salaries_all.max(), female_salaries_all.max()),
    80,
)

# 绘制直方图（半透明）
ax.hist(
    male_salaries_all, bins=bins, density=True,
    alpha=0.4, color="#4A90D9", label=f"男 (n={len(male_salaries_all)})",
    edgecolor="#2C5F8A", linewidth=0.3,
)
ax.hist(
    female_salaries_all, bins=bins, density=True,
    alpha=0.4, color="#E85D75", label=f"女 (n={len(female_salaries_all)})",
    edgecolor="#B33F52", linewidth=0.3,
)

# 叠加 KDE 平滑曲线
for salaries, color, label_prefix in [
    (male_salaries_all, "#1B5FA8", "男"),
    (female_salaries_all, "#C42E4E", "女"),
]:
    if len(salaries) > 3:
        kde = scipy_stats.gaussian_kde(salaries)
        x_kde = np.linspace(salaries.min(), salaries.max(), 500)
        y_kde = kde(x_kde)
        ax.plot(x_kde, y_kde, color=color, linewidth=2.5, label=f"{label_prefix} KDE")

# 绘制均值和中位数竖线
for salaries, color, style, label_prefix in [
    (male_salaries_all, "#1B5FA8", "-", "男"),
    (female_salaries_all, "#C42E4E", "-", "女"),
]:
    mean_val = salaries.mean()
    median_val = salaries.median()
    y_lim = ax.get_ylim()
    # 均值线（实线）
    ax.axvline(mean_val, color=color, linestyle="--", linewidth=1.5, alpha=0.8,
               label=f"{label_prefix}均值 {mean_val:.0f}")
    # 中位数线（点线）
    ax.axvline(median_val, color=color, linestyle=":", linewidth=1.5, alpha=0.8,
               label=f"{label_prefix}中位数 {median_val:.0f}")

# 标注
ax.set_xlabel("薪酬 (元/月)", fontsize=13)
ax.set_ylabel("概率密度", fontsize=13)
ax.set_title("男女薪酬分布密度曲线对比（本科已就业）", fontsize=16, fontweight="bold")
ax.legend(fontsize=9, loc="upper right", ncol=2)

# 去掉上右边框
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# x 轴格式
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))

plt.tight_layout()

density_path = os.path.join(CHART_DIR, "gender_salary_density.png")
fig.savefig(density_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表-密度曲线] 已保存至: {density_path}")

# ============================================================
# 7. 完成总结
# ============================================================
print()
print("=" * 60)
print("任务4「不同性别的学院-专业薪酬分布」完成！")
print(f"  Excel:       {EXCEL_PATH}")
print(f"  柱状图:      {bar_path}")
print(f"  密度曲线:    {density_path}")
print(f"  统计范围:    education_level=本科, is_employed=True, 薪酬>0")
print(f"  有效记录数:  {len(df_target)}  (男{len(male_salaries_all)}, 女{len(female_salaries_all)})")
print(f"  学院数:      {stats['院系'].nunique()}")
print(f"  专业方向数:  {len(stats)}")
print()
print("=== 整体男女薪酬对比 ===")
print(f"  男平均薪酬: {male_salaries_all.mean():.1f}  中位数: {male_salaries_all.median():.1f}")
print(f"  女平均薪酬: {female_salaries_all.mean():.1f}  中位数: {female_salaries_all.median():.1f}")
print(f"  男女均值差: {male_salaries_all.mean() - female_salaries_all.mean():.1f}")
print("=" * 60)
