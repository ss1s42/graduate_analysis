# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 任务5 & 任务6
任务5：就业地区分布（饼图 + Excel统计表）
任务6：考研学校TOP3（Excel统计表）
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import os

# ============================================================
# 全局配置：解决中文显示问题
# ============================================================
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============================================================
# 路径配置
# ============================================================
DATA_PATH = 'data/clean_data.csv'
OUTPUT_DIR = 'output'
CHART_DIR = os.path.join(OUTPUT_DIR, 'charts')

os.makedirs(CHART_DIR, exist_ok=True)

# ============================================================
# 读取数据
# ============================================================
df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')

print(f"总记录数: {len(df)}")
print(f"education_level 分布:\n{df['education_level'].value_counts()}")

# ============================================================
# 筛选本科生
# ============================================================
ug = df[df['education_level'] == '本科'].copy()
print(f"\n本科生记录数: {len(ug)}")

# ============================================================
# 列名映射（便于使用）
# ============================================================
COL_GRADUATION = '毕业去向'             # 毕业去向
COL_EMPLOYER = '就业单位名称/征兵办名称/项目名称/创业单位名称/升学院校名称/境外单位名称'  # 单位/院校名称
COL_LOCATION = '单位/征兵办/项目/院校所属地区'  # 所属地区
COL_MAJOR = '专业名称'                  # 专业名称

# ============================================================
# 任务5：就业地区分布
# ============================================================
print("\n" + "=" * 60)
print("任务5：就业地区分布")
print("=" * 60)

# 仅统计已就业的本科生（排除待就业、自由职业、自主创业等无明确"单位/院校所属地区"的记录）
# 筛选有就业去向且地区不为空的记录
employed_ug = ug[ug[COL_LOCATION].notna() & (ug[COL_LOCATION] != '')].copy()
print(f"有地区信息的本科生记录数: {len(employed_ug)}")

# 大湾区城市列表
GREATER_BAY_AREA_CITIES = [
    '广州', '深圳', '佛山', '东莞', '珠海', '中山',
    '江门', '惠州', '肇庆', '香港', '澳门'
]


def classify_location(region_str):
    """
    地区分类
    根据"单位/院校所属地区"字段判断所属区域。
    返回: '大湾区', '广东省内（非大湾区）', '省外', '境外'
    """
    if pd.isna(region_str) or region_str == '':
        return '未知'

    region_str = str(region_str).strip()

    # 1. 先检查明确的境外关键词（优先级最高）
    # "港澳台"整体出现时（如"广东省/国外及港澳台"），按境外处理
    # "国外及港澳台"是教育系统的特殊地区代码，表示出境
    overseas_whole_patterns = ['国外及港澳台', '国外和港澳台']
    for pat in overseas_whole_patterns:
        if pat in region_str:
            return '境外'

    # 2. 境外：台湾（港澳台中的"台"）
    if '台湾' in region_str:
        return '境外'

    # 境外关键词（国家名）
    overseas_keywords = [
        '国外', '境外',
        '美国', '英国', '日本', '澳大利亚', '加拿大',
        '德国', '法国', '韩国', '新加坡', '新西兰', '荷兰', '瑞典',
        '瑞士', '意大利', '西班牙', '俄罗斯', '马来西亚', '泰国',
        '印度', '巴西', '阿根廷', '墨西哥', '越南', '菲律宾', '印度尼西亚',
        '爱尔兰', '挪威', '丹麦', '芬兰', '比利时', '奥地利', '葡萄牙',
        '波兰', '捷克', '匈牙利', '希腊', '土耳其', '以色列', '阿联酋',
        '南非', '埃及', '尼日利亚', '肯尼亚',
    ]
    for kw in overseas_keywords:
        if kw in region_str:
            return '境外'

    # 3. 广东省内分类
    if '广东省' in region_str or any(kw in region_str for kw in ['广东', '广州', '深圳', '佛山', '东莞',
                                                                      '珠海', '中山', '江门', '惠州', '肇庆',
                                                                      '汕头', '湛江', '茂名', '韶关', '河源',
                                                                      '梅州', '汕尾', '阳江', '清远', '潮州',
                                                                      '揭阳', '云浮']):
        # 检查是否为大湾区城市（香港、澳门单独处理）
        for city in ['广州', '深圳', '佛山', '东莞', '珠海', '中山', '江门', '惠州', '肇庆']:
            if city in region_str:
                return '大湾区'
        # 广东省内非大湾区
        return '广东省内（非大湾区）'

    # 4. 香港、澳门（大湾区）
    if '香港' in region_str or '澳门' in region_str:
        return '大湾区'

    # 5. 省外：中国大陆其他省份
    province_keywords = [
        '北京', '天津', '上海', '重庆',
        '河北', '山西', '辽宁', '吉林', '黑龙江',
        '江苏', '浙江', '安徽', '福建', '江西', '山东',
        '河南', '湖北', '湖南',
        '海南', '四川', '贵州', '云南',
        '陕西', '甘肃', '青海',
        '内蒙古', '广西', '西藏', '宁夏', '新疆',
    ]
    for prov in province_keywords:
        if prov in region_str:
            return '省外'

    # 6. 包含"省"字 → 省外（排除已处理的广东省）
    if '省' in region_str:
        return '省外'

    # 7. 其他无法判断
    return '未知'


# 应用分类
employed_ug['地区分类'] = employed_ug[COL_LOCATION].apply(classify_location)

print("\n地区分布统计：")
location_dist = employed_ug['地区分类'].value_counts()
print(location_dist)

# 计算百分比
location_pct = (employed_ug['地区分类'].value_counts(normalize=True) * 100).round(2)
print("\n百分比：")
print(location_pct)

# ---- 生成饼图 ----
fig, ax = plt.subplots(figsize=(10, 8))

# 过滤掉"未知"用于饼图展示
plot_data = location_dist.drop('未知', errors='ignore')

colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
explode = [0.02] * len(plot_data)  # 轻微分离所有扇区

wedges, texts, autotexts = ax.pie(
    plot_data.values,
    labels=plot_data.index,
    autopct='%1.1f%%',
    startangle=90,
    colors=colors[:len(plot_data)],
    explode=explode,
    pctdistance=0.6,
    labeldistance=1.1,
    textprops={'fontsize': 13}
)

# 设置百分比文字样式
for autotext in autotexts:
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')

ax.set_title('本科毕业生就业地区分布', fontsize=16, fontweight='bold', pad=20)

# 添加图例（含具体人数）
legend_labels = [f'{label} ({count}人)' for label, count in plot_data.items()]
ax.legend(wedges, legend_labels, title='地区分类', loc='lower left',
          bbox_to_anchor=(0.0, -0.15), ncol=2, fontsize=11)

plt.tight_layout()
pie_path = os.path.join(CHART_DIR, 'location_distribution_pie.png')
fig.savefig(pie_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print(f"\n饼图已保存: {pie_path}")

# ---- 生成统计表 ----
# 创建详细的统计表（包含多维度）
# 表1：地区分布总览
summary_data = []
for cat in ['大湾区', '广东省内（非大湾区）', '省外', '境外', '未知']:
    count = location_dist.get(cat, 0)
    pct = location_pct.get(cat, 0)
    summary_data.append({
        '地区分类': cat,
        '人数': count,
        '占比(%)': pct
    })

summary_df = pd.DataFrame(summary_data)

# 表2：大湾区各城市分布
gba_data = []
for city in GREATER_BAY_AREA_CITIES:
    city_count = employed_ug[employed_ug[COL_LOCATION].str.contains(city, na=False)].shape[0]
    gba_data.append({'城市': city, '人数': city_count})
gba_df = pd.DataFrame(gba_data)
gba_df = gba_df.sort_values('人数', ascending=False).reset_index(drop=True)

# 表3：省内非大湾区各城市分布
gd_non_gba = employed_ug[employed_ug['地区分类'] == '广东省内（非大湾区）']
# 尝试提取城市名
province_cities_others = [
    '汕头', '湛江', '茂名', '韶关', '河源', '梅州', '汕尾',
    '阳江', '清远', '潮州', '揭阳', '云浮',
]
gd_other_data = []
for city in province_cities_others:
    city_count = gd_non_gba[gd_non_gba[COL_LOCATION].str.contains(city, na=False)].shape[0]
    if city_count > 0:
        gd_other_data.append({'城市': city, '人数': city_count})
gd_other_df = pd.DataFrame(gd_other_data)
gd_other_df = gd_other_df.sort_values('人数', ascending=False).reset_index(drop=True)

# 表4：省外TOP省份
outside_df = employed_ug[employed_ug['地区分类'] == '省外']
provinces = ['北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
             '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
             '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海',
             '内蒙古', '广西', '西藏', '宁夏', '新疆']
province_data = []
for prov in provinces:
    prov_count = outside_df[outside_df[COL_LOCATION].str.contains(prov, na=False)].shape[0]
    if prov_count > 0:
        province_data.append({'省份/直辖市': prov, '人数': prov_count})
province_df = pd.DataFrame(province_data)
province_df = province_df.sort_values('人数', ascending=False).reset_index(drop=True)

# 写入Excel
location_xlsx_path = os.path.join(OUTPUT_DIR, 'location_stats.xlsx')
with pd.ExcelWriter(location_xlsx_path, engine='openpyxl') as writer:
    summary_df.to_excel(writer, sheet_name='地区分布总览', index=False)
    gba_df.to_excel(writer, sheet_name='大湾区各城市', index=False)
    gd_other_df.to_excel(writer, sheet_name='省内非大湾区城市', index=False)
    province_df.to_excel(writer, sheet_name='省外各省份', index=False)

    # 调整列宽
    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    cell_len = len(str(cell.value)) if cell.value else 0
                    # 中文字符宽度加倍
                    cjk_count = sum(1 for c in str(cell.value) if '一' <= c <= '鿿') if cell.value else 0
                    cell_len = cell_len + cjk_count
                    max_length = max(max_length, cell_len)
                except Exception:
                    pass
            adjusted_width = min(max_length + 4, 50)
            ws.column_dimensions[col_letter].width = adjusted_width

print(f"地区分布统计表已保存: {location_xlsx_path}")

# ============================================================
# 任务6：考研学校TOP3
# ============================================================
print("\n" + "=" * 60)
print("任务6：考研学校TOP3")
print("=" * 60)

# 筛选升学记录：毕业去向包含"升学"
# 境内升学 和 境内深造 都算
promotion_keywords = ['升学', '境内升学']
postgrad = ug[ug[COL_GRADUATION].apply(
    lambda x: any(kw in str(x) for kw in promotion_keywords)
)].copy()

print(f"本科生升学记录数: {len(postgrad)}")
print(f"升学去向分布:\n{postgrad[COL_GRADUATION].value_counts()}")

# 检查升学院校列
print(f"\n升学院校名称列非空数量: {postgrad[COL_EMPLOYER].notna().sum()}")
print(f"升学院校名称列空值数: {postgrad[COL_EMPLOYER].isna().sum()}")

# 统计各专业升学学校TOP3
# 按专业分组
major_groups = postgrad.groupby(COL_MAJOR)

top3_records = []

for major, group in major_groups:
    # 统计该专业升学学校出现次数
    school_counts = group[COL_EMPLOYER].dropna().value_counts()

    if len(school_counts) == 0:
        continue

    # 取前3
    top3_schools = school_counts.head(3)

    for rank, (school, count) in enumerate(top3_schools.items(), 1):
        # 计算该专业升学总人数
        total_postgrad = len(group)
        percentage = round(count / total_postgrad * 100, 2)

        top3_records.append({
            '专业名称': major,
            '排名': rank,
            '升学院校': school,
            '升学人数': count,
            '占本专业升学比例(%)': percentage,
            '本专业升学总人数': total_postgrad
        })

top3_df = pd.DataFrame(top3_records)

if not top3_df.empty:
    top3_df = top3_df.sort_values(['专业名称', '排名']).reset_index(drop=True)

print(f"\n各专业考研学校TOP3统计：")
print(f"涉及专业数: {top3_df['专业名称'].nunique()}")
print(f"总记录数: {len(top3_df)}")
print(f"\n预览：")
print(top3_df.head(20).to_string())

# 同时生成一个汇总透视表：专业 × 升学总人数 × TOP3院校
pivot_records = []
for major, group in major_groups:
    school_counts = group[COL_EMPLOYER].dropna().value_counts()
    total = len(group)
    top3 = school_counts.head(3)
    top3_str = ' / '.join([f'{school}({cnt}人)' for school, cnt in top3.items()])

    pivot_records.append({
        '专业名称': major,
        '升学总人数': total,
        'TOP1院校': top3.index[0] if len(top3) >= 1 else '',
        'TOP1人数': int(top3.iloc[0]) if len(top3) >= 1 else 0,
        'TOP2院校': top3.index[1] if len(top3) >= 2 else '',
        'TOP2人数': int(top3.iloc[1]) if len(top3) >= 2 else 0,
        'TOP3院校': top3.index[2] if len(top3) >= 3 else '',
        'TOP3人数': int(top3.iloc[2]) if len(top3) >= 3 else 0,
    })

pivot_df = pd.DataFrame(pivot_records)
pivot_df = pivot_df.sort_values('升学总人数', ascending=False).reset_index(drop=True)

# 写入Excel
postgrad_xlsx_path = os.path.join(OUTPUT_DIR, 'postgraduate_top3.xlsx')
with pd.ExcelWriter(postgrad_xlsx_path, engine='openpyxl') as writer:
    top3_df.to_excel(writer, sheet_name='各专业考研TOP3', index=False)
    pivot_df.to_excel(writer, sheet_name='汇总表', index=False)

    # 调整列宽
    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_length = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    cell_len = len(str(cell.value)) if cell.value else 0
                    cjk_count = sum(1 for c in str(cell.value) if '一' <= c <= '鿿') if cell.value else 0
                    cell_len = cell_len + cjk_count
                    max_length = max(max_length, cell_len)
                except Exception:
                    pass
            adjusted_width = min(max_length + 4, 60)
            ws.column_dimensions[col_letter].width = adjusted_width

print(f"考研学校TOP3统计表已保存: {postgrad_xlsx_path}")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 60)
print("任务5和任务6 全部完成！")
print("=" * 60)
print(f"输出文件：")
print(f"  1. {pie_path}")
print(f"  2. {location_xlsx_path}")
print(f"  3. {postgrad_xlsx_path}")
