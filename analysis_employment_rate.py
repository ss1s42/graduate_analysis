# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 任务1：就业率统计
==============================================
统计维度：
  1. 全校整体就业率（本科 + 硕士分别计算）
  2. 每个学院的本科就业率
  3. 每个专业的本科就业率
输出：
  - 控制台打印
  - Excel 文件 output/employment_rate.xlsx（多个sheet）
  - 柱状图 output/charts/employment_rate_by_college.png
"""

import os
import pandas as pd
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
EXCEL_PATH = os.path.join(OUTPUT_DIR, "employment_rate.xlsx")

os.makedirs(CHART_DIR, exist_ok=True)

# ============================================================
# 1. 中文字体设置
# ============================================================
def setup_chinese_font():
    """自动探测系统中可用的中文字体并设置 matplotlib 全局字体"""
    # 常见 Windows 中文字体（按优先级）
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
# 2. 读取数据
# ============================================================
print("=" * 60)
print("读取清洗后数据:", DATA_PATH)
df = pd.read_csv(DATA_PATH)
print(f"总记录数: {len(df)}")

# 确认关键列存在
required_cols = ["education_level", "院系", "专业名称", "is_employed"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(f"缺少必要列: {missing}")

print(f"学历分布:\n{df['education_level'].value_counts()}\n")
print(f"就业状态分布:\n{df['is_employed'].value_counts()}\n")

# ============================================================
# 3. 全校整体就业率（本科 + 硕士分别计算）
# ============================================================
def calc_rate(employed: int, total: int) -> float:
    """计算就业率（百分比，保留2位小数）"""
    if total == 0:
        return 0.0
    return round(employed / total * 100, 2)


# 按学历分组统计
overall_stats = (
    df.groupby("education_level")
      .agg(总人数=("is_employed", "count"),
           就业人数=("is_employed", "sum"))
      .reset_index()
)
overall_stats["就业率(%)"] = overall_stats.apply(
    lambda r: calc_rate(r["就业人数"], r["总人数"]), axis=1
)
# 追加合计行
total_row = {
    "education_level": "合计",
    "总人数": df.shape[0],
    "就业人数": int(df["is_employed"].sum()),
    "就业率(%)": calc_rate(int(df["is_employed"].sum()), df.shape[0]),
}
overall_with_total = pd.concat(
    [overall_stats, pd.DataFrame([total_row])], ignore_index=True
)

print("=" * 60)
print("【1】全校整体就业率（按学历）")
print("-" * 40)
print(overall_with_total.to_string(index=False))
print()

# ============================================================
# 4. 按学院统计本科就业率
# ============================================================
df_ug = df[df["education_level"] == "本科"].copy()
print(f"本科生记录数: {len(df_ug)}\n")

college_stats = (
    df_ug.groupby("院系")
        .agg(总人数=("is_employed", "count"),
             就业人数=("is_employed", "sum"))
        .reset_index()
)
college_stats["就业率(%)"] = college_stats.apply(
    lambda r: calc_rate(r["就业人数"], r["总人数"]), axis=1
)
college_stats = college_stats.sort_values("就业率(%)", ascending=False).reset_index(drop=True)

print("=" * 60)
print("【2】各学院本科就业率（从高到低）")
print("-" * 40)
print(college_stats.to_string(index=True))
print()

# ============================================================
# 5. 按专业统计本科就业率
# ============================================================
major_stats = (
    df_ug.groupby(["院系", "专业名称"])
        .agg(总人数=("is_employed", "count"),
             就业人数=("is_employed", "sum"))
        .reset_index()
)
major_stats["就业率(%)"] = major_stats.apply(
    lambda r: calc_rate(r["就业人数"], r["总人数"]), axis=1
)
major_stats = major_stats.sort_values("就业率(%)", ascending=False).reset_index(drop=True)

print("=" * 60)
print("【3】各专业本科就业率（从高到低）")
print("-" * 40)
print(major_stats.to_string(index=True))
print()

# ============================================================
# 6. 保存为 Excel（多 Sheet）
# ============================================================
print("=" * 60)
with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    overall_with_total.to_excel(writer, sheet_name="全校就业率", index=False)
    college_stats.to_excel(writer, sheet_name="学院本科就业率", index=False)
    major_stats.to_excel(writer, sheet_name="专业本科就业率", index=False)
print(f"[Excel] 已保存至: {EXCEL_PATH}")

# ============================================================
# 7. 可视化：学院就业率水平柱状图
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

# 按就业率从高到低排序（水平柱状图需反过来画）
plot_data = college_stats.sort_values("就业率(%)", ascending=True)  # plt.barh 从下往上画
colleges = plot_data["院系"].tolist()
rates = plot_data["就业率(%)"].tolist()

# 颜色映射：用渐变表示高低
norm = plt.Normalize(min(rates), max(rates))
colors = plt.cm.Blues(0.4 + 0.6 * norm(rates))

bars = ax.barh(range(len(colleges)), rates, color=colors, edgecolor="#333333", linewidth=0.5)

# 在柱形末端标注就业率
for i, (college, rate) in enumerate(zip(colleges, rates)):
    ax.text(rate + 0.5, i, f"{rate}%", va="center", fontsize=9, color="#333333")

# 标题与标签
ax.set_yticks(range(len(colleges)))
ax.set_yticklabels(colleges, fontsize=10)
ax.set_xlabel("就业率 (%)", fontsize=12)
ax.set_title("各学院本科就业率", fontsize=14, fontweight="bold")
ax.set_xlim(0, max(rates) * 1.12)  # 右侧留空标注文字
ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))

# 网格线
ax.xaxis.grid(True, linestyle="--", alpha=0.4)
ax.set_axisbelow(True)

# 去掉上右边框
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

chart_path = os.path.join(CHART_DIR, "employment_rate_by_college.png")
fig.savefig(chart_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表] 已保存至: {chart_path}")

# ============================================================
# 8. 分性别就业率统计(补充)
# ============================================================
print("\n" + "=" * 60)
print("分性别就业率统计")
print("-" * 40)

# 8a. 按学历 + 性别
print("\n  [8a] 按学历层次和性别统计就业率:")
for edu in ['本科', '硕士']:
    sub_edu = df[df['education_level'] == edu]
    for gender in ['男', '女']:
        sub = sub_edu[sub_edu['性别'] == gender]
        tot = len(sub)
        emp = sub['is_employed'].sum()
        rate = calc_rate(int(emp), tot)
        print(f"    {edu} · {gender}: {emp}/{tot} = {rate}%")

# 8b. 按学院 + 性别
print("\n  [8b] 各学院分性别本科就业率:")
for college in df_ug['院系'].unique():
    sub_college = df_ug[df_ug['院系'] == college]
    for gender in ['男', '女']:
        sub = sub_college[sub_college['性别'] == gender]
        tot = len(sub)
        emp = sub['is_employed'].sum()
        rate = calc_rate(int(emp), tot)
        if tot > 0:
            print(f"    {college:<16} · {gender}: {emp}/{tot} = {rate}%")

# 8c. 保存分性别就业率到 Excel
gender_stats = []
for edu in ['本科', '硕士']:
    sub_edu = df[df['education_level'] == edu]
    for gender in ['男', '女']:
        sub = sub_edu[sub_edu['性别'] == gender]
        tot = len(sub)
        emp = int(sub['is_employed'].sum())
        gender_stats.append({
            '学历层次': edu,
            '性别': gender,
            '总人数': tot,
            '就业人数': emp,
            '就业率(%)': calc_rate(emp, tot),
        })

college_gender_stats = []
for college in df_ug['院系'].unique():
    sub_college = df_ug[df_ug['院系'] == college]
    for gender in ['男', '女']:
        sub = sub_college[sub_college['性别'] == gender]
        tot = len(sub)
        emp = int(sub['is_employed'].sum())
        college_gender_stats.append({
            '院系': college,
            '性别': gender,
            '总人数': tot,
            '就业人数': emp,
            '就业率(%)': calc_rate(emp, tot),
        })

gender_df = pd.DataFrame(gender_stats)
college_gender_df = pd.DataFrame(college_gender_stats)
college_gender_df = college_gender_df.sort_values(['院系', '性别']).reset_index(drop=True)

# 追加到已有 Excel
with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl", mode='a', if_sheet_exists='replace') as writer:
    gender_df.to_excel(writer, sheet_name="分性别学历就业率", index=False)
    college_gender_df.to_excel(writer, sheet_name="学院分性别就业率", index=False)

print(f"\n[Excel] 分性别就业率已追加到: {EXCEL_PATH}")

print()
print("=" * 60)
print("任务1「就业率统计」完成！")
print(f"  Excel:  {EXCEL_PATH}")
print(f"  图表:   {chart_path}")
print("=" * 60)
