# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 任务2：本科生就业单位性质占比
==============================================
统计维度：
  1. 按单位类型归类为 8 大类，统计人数与占比
  2. 饼图（百分比 + 人数标注）
  3. 柱状图（各类人数）
  4. Excel 统计表

输出：
  - 控制台打印
  - 饼图   output/charts/employer_type_pie.png
  - 柱状图 output/charts/employer_type_bar.png
  - Excel  output/employer_type_stats.xlsx
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
EXCEL_PATH = os.path.join(OUTPUT_DIR, "employer_type_stats.xlsx")

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
# 2. 读取数据 & 筛选本科生已就业
# ============================================================
print("=" * 60)
print("读取清洗后数据:", DATA_PATH)
df = pd.read_csv(DATA_PATH)
print(f"总记录数: {len(df)}")

# 筛选：本科生 + 已就业
df_ug = df[(df["education_level"] == "本科") & (df["is_employed"] == True)].copy()
total_employed = len(df_ug)
print(f"本科已就业人数: {total_employed}")
print()

# ============================================================
# 3. 定义单位类型归类规则
# ============================================================
# 每一条规则是一个 (关键词列表, 大类名称) 的映射
# 匹配逻辑：单位类型字符串包含任一关键词即归入该大类
# 优先级：从具体到宽泛，先匹配更具体的规则

def classify_employer_type(raw_type):
    """
    将原始单位类型字符串归类为 8 个大类之一。
    返回 (大类名称, 详细说明)。
    """
    if pd.isna(raw_type) or str(raw_type).strip() == "":
        return "其他/未知"

    t = str(raw_type).strip()

    # ---- 升学 ----
    if t in ("升学", "出国、出境深造", "第二学士学位", "研究生", "拟出国出境"):
        return "升学"

    # ---- 基层项目 ----
    if t in ("三支一扶", "西部计划", "选调生"):
        return "基层项目"

    # ---- 机关事业单位 ----
    # 学校（各类教育机构）
    if t in ("小学", "初中", "高中",
             "普通本科院校", "高职高专院校", "中专（技校）",
             "民办院校", "民办普教学校", "其他高等院校",
             "幼儿园", "其他普教系统"):
        return "机关事业单位"

    # 国家机关
    if "国家机关" in t:
        return "机关事业单位"

    # 事业单位
    if "事业单位" in t:
        return "机关事业单位"

    # 党群系统
    if "党群系统" in t:
        return "机关事业单位"

    # 政法系统
    if "政法系统" in t:
        return "机关事业单位"

    # 科研设计单位
    if "科研设计单位" in t:
        return "机关事业单位"

    # 医疗卫生单位
    if "医疗卫生单位" in t:
        return "机关事业单位"

    # 其他机关、部队相关
    if "机关、部队、党群及政法系统" in t:
        return "机关事业单位"

    # ---- 国有企业 ----
    if "国有企业" in t or "国企" in t:
        return "国有企业"

    # ---- 外资企业 ----
    if t in ("外商投资企业", "港、澳、台商投资企业", "三资企业"):
        return "外资企业"

    # ---- 民营企业 ----
    if t in ("有限责任公司", "股份有限公司", "私营企业",
             "股份合作企业", "联营企业", "集体企业"):
        return "民营企业"

    # ---- 灵活就业/自由职业 ----
    if t in ("其他自由职业", "自由（自雇）职业艺术工作者",
             "网店", "非义务教育学科类家教",
             "现代服务业", "现代农业", "传统产业"):
        return "灵活就业/自由职业"

    # ---- 其他 ----
    # 应征义务兵、科研助理、社会团体、其他创业类型、暂不就业、其它 等
    if t == "应征义务兵":
        return "机关事业单位"   # 军队属国家机器

    if t == "科研助理、管理助理":
        return "灵活就业/自由职业"  # 属于短期/合同性质的科研助理岗位

    if t == "社会团体":
        return "其他/未知"  # 社会团体/NGO，不便于归类

    if t in ("其他创业类型", "其它", "其他", "暂不就业"):
        return "其他/未知"

    # 兜底：未匹配到的
    return "其他/未知"


# ============================================================
# 4. 执行归类 & 统计
# ============================================================
df_ug["大类"] = df_ug["单位类型"].apply(classify_employer_type)

# 统计各类人数
stats = (
    df_ug.groupby("大类")
         .agg(人数=("大类", "count"))
         .reset_index()
)
stats["占比(%)"] = stats["人数"].apply(
    lambda x: round(x / total_employed * 100, 2)
)

# 固定排序
category_order = [
    "机关事业单位",
    "国有企业",
    "民营企业",
    "外资企业",
    "基层项目",
    "升学",
    "灵活就业/自由职业",
    "其他/未知",
]

# 只保留实际有数据的类
stats["排序"] = stats["大类"].apply(
    lambda x: category_order.index(x) if x in category_order else 99
)
stats = stats.sort_values("排序").drop(columns=["排序"]).reset_index(drop=True)

print("=" * 60)
print("【任务2】本科生就业单位性质占比")
print("-" * 40)
print(f"本科已就业总人数: {total_employed}")
print()
print(stats.to_string(index=False))
print()

# 同时输出详细对照表（每个原始类型 → 归类）
detail = (
    df_ug.groupby(["单位类型", "大类"])
         .agg(人数=("大类", "count"))
         .reset_index()
         .sort_values(["大类", "人数"], ascending=[True, False])
)
print("-" * 40)
print("【明细】原始单位类型 → 大类归类")
print(detail.to_string(index=False))
print()

# ============================================================
# 5. 保存为 Excel
# ============================================================
with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
    stats.to_excel(writer, sheet_name="大类统计", index=False)
    detail.to_excel(writer, sheet_name="明细归类", index=False)
print(f"[Excel] 已保存至: {EXCEL_PATH}")

# ============================================================
# 6. 可视化：饼图
# ============================================================
# 颜色方案（8种颜色，视觉清晰可辨）
pie_colors = [
    "#5470c6",  # 机关事业单位 - 蓝
    "#fac858",  # 国有企业     - 金
    "#91cc75",  # 民营企业     - 绿
    "#ee6666",  # 外资企业     - 红
    "#73c0de",  # 基层项目     - 浅蓝
    "#3ba272",  # 升学         - 深绿
    "#fc8452",  # 灵活就业     - 橙
    "#9a60b4",  # 其他/未知   - 紫
]

fig, ax = plt.subplots(figsize=(10, 7))

labels = stats["大类"].tolist()
sizes = stats["人数"].tolist()
percents = stats["占比(%)"].tolist()

# 构造图例标签（含人数和百分比）
legend_labels = [
    f"{label}  ({count}人, {pct}%)"
    for label, count, pct in zip(labels, sizes, percents)
]

# 突出显示较小的扇区（explode 所有扇区轻微分离）
explode = [0.02] * len(labels)

wedges, texts, autotexts = ax.pie(
    sizes,
    labels=None,            # 不在饼图上直接写标签
    autopct="%1.1f%%",      # 显示百分比
    startangle=90,          # 从12点方向开始
    colors=pie_colors[:len(labels)],
    explode=explode,
    pctdistance=0.75,
    textprops={"fontsize": 10},
)

# 美化百分比文字
for at in autotexts:
    at.set_fontweight("bold")
    at.set_fontsize(11)

# 图例放在右侧
ax.legend(
    wedges,
    legend_labels,
    title="单位性质（人数, 占比）",
    loc="center left",
    bbox_to_anchor=(1, 0, 0.5, 1),
    fontsize=10,
    title_fontsize=12,
)

ax.set_title("本科生就业单位性质占比", fontsize=16, fontweight="bold", pad=20)

# 确保饼图为正圆
ax.set_aspect("equal")

plt.tight_layout()

pie_path = os.path.join(CHART_DIR, "employer_type_pie.png")
fig.savefig(pie_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表-饼图] 已保存至: {pie_path}")

# ============================================================
# 7. 可视化：柱状图
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

# 柱形颜色
bar_colors = pie_colors[:len(labels)]

bars = ax.bar(
    range(len(labels)),
    sizes,
    color=bar_colors,
    edgecolor="#333333",
    linewidth=0.8,
    width=0.65,
)

# 在柱形顶部标注人数和百分比
for i, (bar, count, pct) in enumerate(zip(bars, sizes, percents)):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(sizes) * 0.01,
        f"{count}人\n({pct}%)",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        color="#333333",
    )

ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
ax.set_ylabel("人数", fontsize=13)
ax.set_title("本科生就业单位性质分布", fontsize=16, fontweight="bold")
ax.set_ylim(0, max(sizes) * 1.18)  # 顶部留空白放标注

# 网格线
ax.yaxis.grid(True, linestyle="--", alpha=0.4)
ax.set_axisbelow(True)

# 去掉上右边框
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

# y轴刻度
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

plt.tight_layout()

bar_path = os.path.join(CHART_DIR, "employer_type_bar.png")
fig.savefig(bar_path, dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"[图表-柱状图] 已保存至: {bar_path}")

print()
print("=" * 60)
print("任务2「本科生就业单位性质占比」完成！")
print(f"  Excel:      {EXCEL_PATH}")
print(f"  饼图:       {pie_path}")
print(f"  柱状图:     {bar_path}")
print("=" * 60)
