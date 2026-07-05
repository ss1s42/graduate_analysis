"""
毕业生就业数据分析 - 可视化仪表盘
====================================
Flask Web 应用，提供数据 API 并渲染前端仪表盘页面。
侧边栏导航 · 8个分析页面 · ECharts 交互图表
"""

import os
import json
import pandas as pd
import numpy as np
from flask import Flask, render_template, jsonify, send_from_directory, request

app = Flask(__name__, static_folder='static', template_folder='templates')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'clean_data.csv')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
CHART_DIR = os.path.join(OUTPUT_DIR, 'charts')

# ============================================================
# 数据加载与预计算
# ============================================================
df = pd.read_csv(DATA_PATH, encoding='utf-8-sig')
print(f"[OK] 数据已加载: {len(df)} 行, {len(df.columns)} 列")

df_ug = df[df['education_level'] == '本科'].copy()
df_ug_emp = df_ug[df_ug['is_employed'] == True].copy()
df_pg = df[df['education_level'] == '硕士'].copy()


# ============================================================
# 工具函数：NumPy → Python 原生类型
# ============================================================
def clean_value(v):
    if isinstance(v, (np.integer,)): return int(v)
    elif isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v): return None
        return float(v)
    elif isinstance(v, (np.bool_,)): return bool(v)
    elif isinstance(v, np.ndarray): return v.tolist()
    return v


def clean_dict(d):
    if isinstance(d, dict): return {k: clean_dict(v) for k, v in d.items()}
    elif isinstance(d, list): return [clean_dict(item) for item in d]
    else: return clean_value(d)


def safe_div(a, b):
    return round(a / b * 100, 2) if b > 0 else 0.0


# ============================================================
# 页面路由
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/output/charts/<path:filename>')
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)


# ============================================================
# API 1: 项目概览
# ============================================================
@app.route('/api/overview')
def api_overview():
    total = len(df)
    employed = int(df['is_employed'].sum())
    overall_rate = safe_div(employed, total)

    # 本科
    benke_total = len(df_ug)
    benke_emp = int(df_ug['is_employed'].sum())
    benke_rate = safe_div(benke_emp, benke_total)

    # 硕士
    pg_total = len(df_pg)
    pg_emp = int(df_pg['is_employed'].sum())
    pg_rate = safe_div(pg_emp, pg_total)

    # 薪酬
    sal = df_ug_emp[df_ug_emp['薪酬'] > 0]['薪酬']
    avg_sal = round(float(sal.mean()), 0) if len(sal) > 0 else 0
    med_sal = round(float(sal.median()), 0) if len(sal) > 0 else 0
    min_sal = round(float(sal.min()), 0) if len(sal) > 0 else 0
    max_sal = round(float(sal.max()), 0) if len(sal) > 0 else 0

    # 学院/专业数
    colleges = int(df_ug['院系'].nunique())
    majors = int(df_ug['专业名称'].nunique())

    # 性别
    male = int((df_ug['性别'] == '男').sum())
    female = int((df_ug['性别'] == '女').sum())

    # 毕业去向分布
    fy_dist = df_ug['毕业去向'].value_counts().head(10).to_dict()

    # 就业状态分布（饼图用）
    emp_status = [
        {'name': '已就业', 'value': benke_emp},
        {'name': '未就业', 'value': benke_total - benke_emp},
    ]

    # 学历分布
    edu_dist = [
        {'name': '本科', 'value': benke_total},
        {'name': '硕士', 'value': pg_total},
    ]

    data = {
        'total': total,
        'employed': employed,
        'overall_rate': overall_rate,
        'benke': {'total': benke_total, 'employed': benke_emp, 'rate': benke_rate},
        'shuoshi': {'total': pg_total, 'employed': pg_emp, 'rate': pg_rate},
        'salary': {'avg': int(avg_sal), 'median': int(med_sal), 'min': int(min_sal), 'max': int(max_sal)},
        'colleges': colleges,
        'majors': majors,
        'gender': {'male': male, 'female': female},
        'emp_status': emp_status,
        'edu_dist': edu_dist,
        'fy_dist': {str(k): int(v) for k, v in fy_dist.items()},
    }
    return jsonify(clean_dict(data))


# ============================================================
# API 2: 就业率统计（全校/学院/专业/性别）
# ============================================================
@app.route('/api/employment_rate')
def api_employment_rate():
    # 全校按学历
    overall = df.groupby('education_level').agg(
        总人数=('is_employed', 'count'),
        就业人数=('is_employed', 'sum'),
    ).reset_index()
    overall['就业率'] = (overall['就业人数'] / overall['总人数'] * 100).round(2)
    overall_list = overall.to_dict('records')
    total_row = {
        'education_level': '合计',
        '总人数': int(len(df)),
        '就业人数': int(df['is_employed'].sum()),
        '就业率': safe_div(int(df['is_employed'].sum()), len(df)),
    }

    # 学院就业率
    college = df_ug.groupby('院系').agg(
        总人数=('is_employed', 'count'),
        就业人数=('is_employed', 'sum'),
    ).reset_index()
    college['就业率'] = (college['就业人数'] / college['总人数'] * 100).round(2)
    college = college.sort_values('就业率', ascending=False)
    college_list = college.to_dict('records')

    # 专业就业率
    major = df_ug.groupby(['院系', '专业名称']).agg(
        总人数=('is_employed', 'count'),
        就业人数=('is_employed', 'sum'),
    ).reset_index()
    major['就业率'] = (major['就业人数'] / major['总人数'] * 100).round(2)
    major = major.sort_values('就业率', ascending=False)
    major_list = major.to_dict('records')

    # ⭐ 分性别就业率（新增）
    gender_stats = []
    for edu in ['本科', '硕士']:
        sub = df[df['education_level'] == edu]
        for g in ['男', '女']:
            gsub = sub[sub['性别'] == g]
            tot = len(gsub)
            emp = int(gsub['is_employed'].sum())
            gender_stats.append({
                'education': edu,
                'gender': g,
                'total': tot,
                'employed': emp,
                'rate': safe_div(emp, tot),
            })

    # 学院分性别就业率
    college_gender = []
    for college_name in df_ug['院系'].unique():
        sub = df_ug[df_ug['院系'] == college_name]
        for g in ['男', '女']:
            gsub = sub[sub['性别'] == g]
            tot = len(gsub)
            emp = int(gsub['is_employed'].sum())
            college_gender.append({
                'college': college_name,
                'gender': g,
                'total': tot,
                'employed': emp,
                'rate': safe_div(emp, tot),
            })

    data = {
        'overall': overall_list,
        'overall_total': total_row,
        'college': college_list,
        'major': major_list,
        'gender_stats': gender_stats,
        'college_gender': college_gender,
    }
    return jsonify(clean_dict(data))


# ============================================================
# 单位类型归类函数（内联，避免导入副作用）
# ============================================================
def classify_employer_type(raw_type):
    if pd.isna(raw_type) or str(raw_type).strip() == "":
        return "其他/未知"
    t = str(raw_type).strip()
    if t in ("升学", "出国、出境深造", "第二学士学位", "研究生", "拟出国出境"):
        return "升学"
    if t in ("三支一扶", "西部计划", "选调生"):
        return "基层项目"
    if t in ("小学", "初中", "高中", "普通本科院校", "高职高专院校", "中专（技校）",
             "民办院校", "民办普教学校", "其他高等院校", "幼儿园", "其他普教系统"):
        return "机关事业单位"
    if any(kw in t for kw in ["国家机关", "事业单位", "党群系统", "政法系统",
                                "科研设计单位", "医疗卫生单位", "机关、部队、党群及政法系统"]):
        return "机关事业单位"
    if "国有企业" in t or "国企" in t:
        return "国有企业"
    if t in ("外商投资企业", "港、澳、台商投资企业", "三资企业"):
        return "外资企业"
    if t in ("有限责任公司", "股份有限公司", "私营企业", "股份合作企业", "联营企业", "集体企业"):
        return "民营企业"
    if t in ("其他自由职业", "自由（自雇）职业艺术工作者", "网店", "非义务教育学科类家教",
             "现代服务业", "现代农业", "传统产业", "科研助理、管理助理"):
        return "灵活就业/自由职业"
    if t == "应征义务兵":
        return "机关事业单位"
    if t == "社会团体":
        return "其他/未知"
    if t in ("其他创业类型",):
        return "灵活就业/自由职业"
    if t in ("其它", "其他", "暂不就业"):
        return "其他/未知"
    return "其他/未知"


# ============================================================
# API 3: 用人单位类型分布
# ============================================================
@app.route('/api/employer_type')
def api_employer_type():
    target = df_ug_emp.copy()
    target['大类'] = target['单位类型'].apply(classify_employer_type)

    stats = target.groupby('大类').agg(人数=('大类', 'count')).reset_index()
    stats['占比'] = (stats['人数'] / len(target) * 100).round(2)

    category_order = [
        "机关事业单位", "国有企业", "民营企业", "外资企业",
        "基层项目", "升学", "灵活就业/自由职业", "其他/未知",
    ]
    stats['排序'] = stats['大类'].apply(lambda x: category_order.index(x) if x in category_order else 99)
    stats = stats.sort_values('排序').drop(columns=['排序']).reset_index(drop=True)

    # 明细归类
    detail = target.groupby(['单位类型', '大类']).agg(人数=('大类', 'count')).reset_index()
    detail = detail.sort_values(['大类', '人数'], ascending=[True, False])

    data = {
        'total': int(len(target)),
        'categories': stats.to_dict('records'),
        'detail': detail.to_dict('records'),
    }
    return jsonify(clean_dict(data))


# ============================================================
# API 4: 薪酬分布
# ============================================================
@app.route('/api/salary')
def api_salary():
    sal = df_ug_emp[df_ug_emp['薪酬'] > 0].copy()

    # 整体统计
    overall_stats = {
        'count': int(len(sal)),
        'mean': round(float(sal['薪酬'].mean()), 1),
        'median': round(float(sal['薪酬'].median()), 1),
        'max': round(float(sal['薪酬'].max()), 1),
        'min': round(float(sal['薪酬'].min()), 1),
        'std': round(float(sal['薪酬'].std()), 1),
        'p25': round(float(sal['薪酬'].quantile(0.25)), 1),
        'p75': round(float(sal['薪酬'].quantile(0.75)), 1),
    }

    # 学院薪酬
    college_sal = sal.groupby('院系').agg(
        人数=('薪酬', 'count'), 平均薪酬=('薪酬', 'mean'),
        中位数=('薪酬', 'median'), 最高=('薪酬', 'max'), 最低=('薪酬', 'min'),
    ).reset_index()
    for col in ['平均薪酬', '中位数', '最高', '最低']:
        college_sal[col] = college_sal[col].round(0).astype(int)
    college_sal = college_sal.sort_values('平均薪酬', ascending=False)
    college_list = college_sal.to_dict('records')

    # 专业薪酬 (TOP 30)
    major_sal = sal.groupby(['院系', '专业名称']).agg(
        人数=('薪酬', 'count'), 平均薪酬=('薪酬', 'mean'), 中位数=('薪酬', 'median'),
    ).reset_index()
    major_sal['平均薪酬'] = major_sal['平均薪酬'].round(0).astype(int)
    major_sal['中位数'] = major_sal['中位数'].round(0).astype(int)
    major_sal = major_sal.sort_values('平均薪酬', ascending=False)
    major_list = major_sal.to_dict('records')

    # 薪酬区间分布
    bins = list(range(0, int(sal['薪酬'].max()) + 2000, 2000))
    hist, edges = np.histogram(sal['薪酬'], bins=bins)
    distribution = [
        {'range': f'{int(edges[i])}-{int(edges[i+1])}', 'count': int(hist[i])}
        for i in range(len(hist))
    ]

    # 箱线图数据（按学院）
    boxplot_data = []
    for college in college_sal['院系'].values:
        c_salaries = sal[sal['院系'] == college]['薪酬']
        boxplot_data.append({
            'college': college,
            'min': round(float(c_salaries.min()), 1),
            'q1': round(float(c_salaries.quantile(0.25)), 1),
            'median': round(float(c_salaries.median()), 1),
            'q3': round(float(c_salaries.quantile(0.75)), 1),
            'max': round(float(c_salaries.max()), 1),
            'count': int(len(c_salaries)),
        })

    data = {
        'overall': overall_stats,
        'college': college_list,
        'major': major_list,
        'distribution': distribution,
        'boxplot': boxplot_data,
    }
    return jsonify(clean_dict(data))


# ============================================================
# API 5: 性别与薪酬
# ============================================================
@app.route('/api/gender_salary')
def api_gender_salary():
    sal = df_ug_emp[df_ug_emp['薪酬'] > 0].copy()
    male_sal = sal[sal['性别'] == '男']['薪酬']
    female_sal = sal[sal['性别'] == '女']['薪酬']

    # 整体对比
    gender_overall = {
        'male': {
            'count': int(len(male_sal)), 'mean': round(float(male_sal.mean()), 1),
            'median': round(float(male_sal.median()), 1),
            'p25': round(float(male_sal.quantile(0.25)), 1),
            'p75': round(float(male_sal.quantile(0.75)), 1),
        },
        'female': {
            'count': int(len(female_sal)), 'mean': round(float(female_sal.mean()), 1),
            'median': round(float(female_sal.median()), 1),
            'p25': round(float(female_sal.quantile(0.25)), 1),
            'p75': round(float(female_sal.quantile(0.75)), 1),
        },
        'diff': round(float(male_sal.mean() - female_sal.mean()), 1),
    }

    # 学院 × 性别
    college_gender = []
    for college in sal['院系'].unique():
        sub = sal[sal['院系'] == college]
        m = sub[sub['性别'] == '男']['薪酬']
        f = sub[sub['性别'] == '女']['薪酬']
        entry = {
            'college': college,
            'male_mean': round(float(m.mean()), 0) if len(m) > 0 else None,
            'female_mean': round(float(f.mean()), 0) if len(f) > 0 else None,
            'male_median': round(float(m.median()), 0) if len(m) > 0 else None,
            'female_median': round(float(f.median()), 0) if len(f) > 0 else None,
            'male_count': int(len(m)), 'female_count': int(len(f)),
            'diff': round(float(m.mean() - f.mean()), 0) if len(m) > 0 and len(f) > 0 else None,
        }
        college_gender.append(entry)
    college_gender.sort(key=lambda x: abs(x['diff'] or 0), reverse=True)

    # 密度分布
    bins = list(range(0, int(sal['薪酬'].max()) + 2000, 2000))
    m_hist, _ = np.histogram(male_sal, bins=bins, density=True)
    f_hist, _ = np.histogram(female_sal, bins=bins, density=True)
    dist_data = [{
        'range': f'{int(bins[i])}-{int(bins[i+1])}',
        'center': (bins[i] + bins[i+1]) / 2,
        'male_density': round(float(m_hist[i]), 6) if i < len(m_hist) else 0,
        'female_density': round(float(f_hist[i]), 6) if i < len(f_hist) else 0,
    } for i in range(len(bins) - 1)]

    # 专业 × 性别薪酬差异（全部专业，不含样本筛选）
    major_gender = []
    # 构建专业→院系映射
    major_college_map = sal.groupby('专业名称')['院系'].first().to_dict()
    for major_name in sal['专业名称'].unique():
        sub = sal[sal['专业名称'] == major_name]
        m = sub[sub['性别'] == '男']['薪酬']
        f = sub[sub['性别'] == '女']['薪酬']
        m_mean = round(float(m.mean()), 0) if len(m) > 0 else None
        f_mean = round(float(f.mean()), 0) if len(f) > 0 else None
        major_gender.append({
            'major': major_name,
            '院系': major_college_map.get(major_name, ''),
            'male_mean': m_mean,
            'female_mean': f_mean,
            'diff': round(float(m.mean() - f.mean()), 0) if len(m) > 0 and len(f) > 0 else None,
            'male_count': int(len(m)), 'female_count': int(len(f)),
        })
    major_gender.sort(key=lambda x: abs(x['diff'] or 0), reverse=True)

    data = {
        'overall': gender_overall,
        'college': college_gender,
        'distribution': dist_data,
        'major_gender': major_gender,
    }
    return jsonify(clean_dict(data))


# ============================================================
# 地区归类函数（内联）
# ============================================================
def classify_location(region_str):
    if pd.isna(region_str) or str(region_str).strip() == '':
        return '未知'
    s = str(region_str).strip()
    for pat in ['国外及港澳台', '国外和港澳台']:
        if pat in s: return '境外'
    if '台湾' in s: return '境外'
    overseas = ['国外', '境外', '美国', '英国', '日本', '澳大利亚', '加拿大',
                '德国', '法国', '韩国', '新加坡', '新西兰', '荷兰', '瑞典',
                '瑞士', '意大利', '西班牙', '俄罗斯', '马来西亚', '泰国',
                '印度', '巴西', '爱尔兰', '挪威', '丹麦', '芬兰', '比利时',
                '奥地利', '葡萄牙', '波兰', '捷克', '南非']
    for kw in overseas:
        if kw in s: return '境外'

    gba = ['广州', '深圳', '佛山', '东莞', '珠海', '中山', '江门', '惠州', '肇庆']
    # 大湾区城市
    for city in gba:
        if city in s: return '大湾区'
    if '香港' in s or '澳门' in s: return '大湾区'

    # 广东省内
    gd_kw = ['广东省', '广东', '汕头', '湛江', '茂名', '韶关', '河源', '梅州',
             '汕尾', '阳江', '清远', '潮州', '揭阳', '云浮']
    if any(kw in s for kw in gd_kw): return '广东省内（非大湾区）'

    # 省外
    provinces = ['北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林', '黑龙江',
                 '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南', '湖北', '湖南',
                 '海南', '四川', '贵州', '云南', '陕西', '甘肃', '青海',
                 '内蒙古', '广西', '西藏', '宁夏', '新疆']
    for p in provinces:
        if p in s: return '省外'
    if '省' in s: return '省外'
    return '未知'


# ============================================================
# API 6: 就业地区分布
# ============================================================
@app.route('/api/location')
def api_location():
    COL_LOC = '单位/征兵办/项目/院校所属地区'
    if COL_LOC not in df_ug.columns:
        return jsonify({'error': '缺少地区列'}), 404

    emp_ug = df_ug[df_ug[COL_LOC].notna() & (df_ug[COL_LOC] != '')].copy()
    emp_ug['地区分类'] = emp_ug[COL_LOC].apply(classify_location)

    dist = emp_ug['地区分类'].value_counts()
    pct = (emp_ug['地区分类'].value_counts(normalize=True) * 100).round(2)

    categories = []
    for cat in ['大湾区', '广东省内（非大湾区）', '省外', '境外', '未知']:
        categories.append({
            'name': cat, 'count': int(dist.get(cat, 0)),
            'percent': round(float(pct.get(cat, 0)), 2),
        })

    # 大湾区城市
    gba_cities = []
    for city in ['广州', '深圳', '佛山', '东莞', '珠海', '中山', '江门', '惠州', '肇庆', '香港', '澳门']:
        cnt = emp_ug[emp_ug[COL_LOC].str.contains(city, na=False)].shape[0]
        if cnt > 0: gba_cities.append({'name': city, 'count': int(cnt)})
    gba_cities.sort(key=lambda x: x['count'], reverse=True)

    # 省外省份
    outside_df = emp_ug[emp_ug['地区分类'] == '省外']
    province_list = ['北京', '上海', '天津', '重庆', '江苏', '浙江', '福建', '山东',
                     '河南', '湖北', '湖南', '四川', '河北', '辽宁', '安徽', '江西',
                     '陕西', '云南', '贵州', '山西', '吉林', '黑龙江', '广西', '海南',
                     '甘肃', '内蒙古', '新疆']
    provinces = []
    for p in province_list:
        cnt = outside_df[outside_df[COL_LOC].str.contains(p, na=False)].shape[0]
        if cnt > 0: provinces.append({'name': p, 'count': int(cnt)})
    provinces.sort(key=lambda x: x['count'], reverse=True)

    # 境外国家
    overseas_df = emp_ug[emp_ug['地区分类'] == '境外']
    countries = ['英国', '澳大利亚', '日本', '美国', '加拿大', '韩国', '新加坡',
                 '德国', '法国', '荷兰', '新西兰']
    overseas_data = []
    for c in countries:
        cnt = overseas_df[overseas_df[COL_LOC].str.contains(c, na=False)].shape[0]
        if cnt > 0: overseas_data.append({'name': c, 'count': int(cnt)})
    overseas_data.sort(key=lambda x: x['count'], reverse=True)

    # 省内非大湾区城市
    gd_non_gba_df = emp_ug[emp_ug['地区分类'] == '广东省内（非大湾区）']
    gd_other_cities = ['汕头', '湛江', '茂名', '韶关', '河源', '梅州', '汕尾',
                       '阳江', '清远', '潮州', '揭阳', '云浮']
    gd_other_data = []
    for city in gd_other_cities:
        cnt = gd_non_gba_df[gd_non_gba_df[COL_LOC].str.contains(city, na=False)].shape[0]
        if cnt > 0:
            gd_other_data.append({'name': city, 'count': int(cnt)})
    gd_other_data.sort(key=lambda x: x['count'], reverse=True)

    data = {
        'categories': categories,
        'gba_cities': gba_cities,
        'gd_other_cities': gd_other_data,
        'provinces': provinces,
        'overseas': overseas_data,
        'total_with_location': int(len(emp_ug)),
    }
    return jsonify(clean_dict(data))


# ============================================================
# API 7: 考研学校 TOP3
# ============================================================
@app.route('/api/postgraduate')
def api_postgraduate():
    COL_GRAD = '毕业去向'
    COL_EMP = '就业单位名称/征兵办名称/项目名称/创业单位名称/升学院校名称/境外单位名称'

    promotion_kw = ['升学', '境内升学']
    postgrad = df_ug[df_ug[COL_GRAD].apply(
        lambda x: any(kw in str(x) for kw in promotion_kw)
    )].copy()

    # 构建专业→院系映射
    major_college_map = df_ug.groupby('专业名称')['院系'].first().to_dict()

    # 各专业升学人数（含院系）
    major_counts = postgrad.groupby('专业名称').size().reset_index(name='升学人数')
    major_counts['院系'] = major_counts['专业名称'].map(major_college_map).fillna('')
    major_counts = major_counts.sort_values('升学人数', ascending=False)

    # 每个专业 TOP3
    top3_list = []
    for major, group in postgrad.groupby('专业名称'):
        school_counts = group[COL_EMP].dropna().value_counts().head(3)
        total = len(group)
        for rank, (school, count) in enumerate(school_counts.items(), 1):
            top3_list.append({
                'major': major, 'rank': rank, 'school': school,
                'count': int(count), 'percent': safe_div(count, total),
                'major_total': int(total),
            })

    # 透视表
    pivot_list = []
    for major, group in postgrad.groupby('专业名称'):
        school_counts = group[COL_EMP].dropna().value_counts()
        total = int(len(group))
        top3 = school_counts.head(3)
        entry = {
            'major': major, 'total': total,
            'top1_school': top3.index[0] if len(top3) >= 1 else '',
            'top1_count': int(top3.iloc[0]) if len(top3) >= 1 else 0,
            'top2_school': top3.index[1] if len(top3) >= 2 else '',
            'top2_count': int(top3.iloc[1]) if len(top3) >= 2 else 0,
            'top3_school': top3.index[2] if len(top3) >= 3 else '',
            'top3_count': int(top3.iloc[2]) if len(top3) >= 3 else 0,
        }
        pivot_list.append(entry)
    pivot_list.sort(key=lambda x: x['total'], reverse=True)

    # 所有院校汇总排名
    all_schools = postgrad[COL_EMP].dropna().value_counts().head(30)
    school_ranking = [{'name': str(k), 'count': int(v)} for k, v in all_schools.items()]

    data = {
        'total_postgrad': int(len(postgrad)),
        'major_summary': major_counts.to_dict('records'),
        'top3_list': top3_list,
        'pivot': pivot_list,
        'school_ranking': school_ranking,
    }
    return jsonify(clean_dict(data))




# ============================================================
# API 8: 机器学习模型评估结果
# ============================================================
@app.route('/api/ml_results')
def api_ml_results():
    """返回 TabNet 深度学习模型的评估指标"""
    metrics_path = os.path.join(OUTPUT_DIR, 'ml_metrics.json')
    cm_path = os.path.join(CHART_DIR, 'tabnet_cm.png')
    loss_path = os.path.join(CHART_DIR, 'tabnet_loss.png')

    if os.path.exists(metrics_path):
        with open(metrics_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data['has_cm'] = os.path.exists(cm_path)
        data['has_loss'] = os.path.exists(loss_path)
        data['cm_url'] = '/output/charts/tabnet_cm.png'
        data['loss_url'] = '/output/charts/tabnet_loss.png'
        return jsonify(data)

    # 如果 JSON 不存在，返回默认结构（提示需要运行脚本）
    return jsonify({
        'model_type': 'TabNet / EmbeddingMLP',
        'device': 'cpu',
        'features': ['性别', 'education_level', '专业名称', 'province'],
        'cat_dims': [2, 2, 76, 22],
        'data_split': None,
        'metrics': None,
        'confusion_matrix': None,
        'error_analysis': None,
        'has_cm': os.path.exists(cm_path),
        'has_loss': os.path.exists(loss_path),
        'cm_url': '/output/charts/tabnet_cm.png',
        'loss_url': '/output/charts/tabnet_loss.png',
        'note': '请运行 python tabnet_classification.py 生成完整评估数据',
    })


# ============================================================
# 预测模型加载（启动时初始化）
# ============================================================
import re as _re
from sklearn.preprocessing import LabelEncoder as _LabelEncoder

_predict_model = None
_predict_encoders = {}
_predict_class_names = []
_predict_options = {}

MODEL_PATH = os.path.join(BASE_DIR, 'models', 'tabnet_employer_type.pth.zip')
METRICS_PATH = os.path.join(OUTPUT_DIR, 'ml_metrics.json')

try:
    from pytorch_tabnet.tab_model import TabNetClassifier as _TabNetClassifier
    _predict_model = _TabNetClassifier()
    _predict_model.load_model(MODEL_PATH)
    print("[OK] TabNet 预测模型已加载")
except Exception as e:
    print(f"[WARN] 预测模型加载失败: {e}")

# 加载类别名称
if os.path.exists(METRICS_PATH):
    with open(METRICS_PATH, 'r', encoding='utf-8') as f:
        _predict_class_names = json.load(f).get('class_names', [])

# 准备编码器（从训练子集拟合）
def _extract_province(addr):
    if pd.isna(addr): return '未知'
    addr = str(addr).strip()
    m = _re.match(r'^(.+?省|.+?自治区|.+?市)', addr)
    return m.group(1) if m else (addr[:3] if len(addr) >= 3 else addr)

_train_df = df_ug_emp.copy()
_train_df['province'] = _train_df['生源地_stu'].apply(_extract_province)

_feature_cols = [
    '性别', 'education_level', '专业名称', 'province',
    df.columns[12],   # 专业是否对口
    df.columns[28],   # 政治面貌
    df.columns[27],   # 民族
]
for col in _feature_cols:
    le = _LabelEncoder()
    le.fit(_train_df[col].astype(str))
    _predict_encoders[col] = le

# 预测表单可选值
_predict_options = {
    'gender': sorted(_train_df['性别'].dropna().unique().tolist()),
    'education': sorted(_train_df['education_level'].dropna().unique().tolist()),
    'major': sorted(_train_df['专业名称'].dropna().unique().tolist()),
    'province': sorted(_train_df['province'].dropna().unique().tolist()),
    'zyk': sorted(_train_df[df.columns[12]].fillna('未知').unique().tolist()),
    'zzmm': sorted(_train_df[df.columns[28]].dropna().unique().tolist()),
    'mz': sorted(_train_df[df.columns[27]].dropna().unique().tolist()),
}
print(f"[OK] 预测编码器就绪: {len(_predict_options['major'])} 专业, {len(_predict_options['province'])} 省份")


# ============================================================
# API 9: 交互式预测
# ============================================================
@app.route('/api/predict', methods=['POST'])
def api_predict():
    """接收用户输入的特征，返回 8 类用人单位性质预测概率"""
    if _predict_model is None:
        return jsonify({'error': '预测模型未加载'}), 500

    data = request.get_json() or {}
    gender   = data.get('gender', '男')
    edu      = data.get('education', '本科')
    major    = data.get('major', '')
    province = data.get('province', '广东省')
    zyk      = data.get('zyk', '未知')
    zzmm     = data.get('zzmm', '群众')
    mz       = data.get('mz', '汉族')

    def safe_encode(encoder, value, fallback=0):
        if value and value in encoder.classes_:
            return encoder.transform([value])[0]
        return fallback

    # 编码 7 个特征
    try:
        x = np.array([[
            safe_encode(_predict_encoders['性别'], gender),
            safe_encode(_predict_encoders['education_level'], edu),
            safe_encode(_predict_encoders['专业名称'], major),
            safe_encode(_predict_encoders['province'], province),
            safe_encode(_predict_encoders[df.columns[12]], zyk),
            safe_encode(_predict_encoders[df.columns[28]], zzmm),
            safe_encode(_predict_encoders[df.columns[27]], mz),
        ]], dtype=np.float32)
    except ValueError as e:
        return jsonify({'error': f'输入值不在训练范围内: {str(e)}'}), 400

    probs = _predict_model.predict_proba(x)[0]
    pred_class = int(np.argmax(probs))

    results = []
    for i, p in enumerate(probs):
        results.append({
            'class': _predict_class_names[i] if i < len(_predict_class_names) else f'类别{i}',
            'probability': round(float(p), 4),
            'percent': round(float(p) * 100, 1),
        })
    results.sort(key=lambda r: r['probability'], reverse=True)

    return jsonify({
        'prediction': _predict_class_names[pred_class] if pred_class < len(_predict_class_names) else '未知',
        'confidence': round(float(probs[pred_class]) * 100, 1),
        'results': results,
    })


@app.route('/api/model_info')
def api_model_info():
    """返回预测表单的可选值列表"""
    return jsonify(_predict_options)


# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  毕业生就业数据分析 - 可视化仪表盘")
    print("  http://127.0.0.1:5000")
    print(f"  数据: {len(df)} 行 · {df_ug['院系'].nunique()} 学院 · {df_ug['专业名称'].nunique()} 专业")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
