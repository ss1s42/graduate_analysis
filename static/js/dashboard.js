/**
 * 毕业生就业数据分析 - 仪表盘前端逻辑
 * 侧边栏导航 · 7个分析页面 · ECharts · 学院筛选
 */

// ============================================================
// 工具函数
// ============================================================
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);
const api = (p) => fetch(p).then(r => r.json());
const COLORS = ['#5470C6','#91CC75','#FAC858','#EE6666','#73C0DE','#3BA272','#FC8452','#9A60B4','#EA7CCC','#48C9B0'];

function initChart(domId) {
    const dom = document.getElementById(domId);
    if (!dom) return null;
    const existing = echarts.getInstanceByDom(dom);
    if (existing) existing.dispose();
    const chart = echarts.init(dom);
    new ResizeObserver(() => chart.resize()).observe(dom);
    return chart;
}

// ============================================================
// 全局数据缓存（用于学院筛选）
// ============================================================
const DATA = {};

// ============================================================
// 页面切换
// ============================================================
const loadedPages = new Set(['overview']);

function switchPage(pageName) {
    $$('.nav-item').forEach(el => el.classList.remove('active'));
    const navItem = $(`.nav-item[data-page="${pageName}"]`);
    if (navItem) navItem.classList.add('active');

    $$('.page').forEach(el => el.classList.remove('active'));
    const pageEl = document.getElementById('page-' + pageName);
    if (pageEl) pageEl.classList.add('active');

    if (!loadedPages.has(pageName)) {
        loadedPages.add(pageName);
        loadPageData(pageName);
    } else {
        // 页面已加载过，切换到该页面时 resize 所有图表
        setTimeout(() => {
            const pageEl = document.getElementById('page-' + pageName);
            if (pageEl) {
                pageEl.querySelectorAll('.chart').forEach(dom => {
                    const chart = echarts.getInstanceByDom(dom);
                    if (chart) chart.resize();
                });
            }
        }, 100);
    }
}

function loadPageData(pageName) {
    const loaders = {
        'overview':    loadOverview,
        'employment':  loadEmploymentRate,
        'employer':    loadEmployerType,
        'salary':      loadSalary,
        'gender':      loadGenderSalary,
        'location':    loadLocation,
        'postgraduate':loadPostgraduate,
        'ml':          loadMLResults,
    };
    const fn = loaders[pageName];
    if (fn) { console.log('[加载] ' + pageName); fn().catch(err => console.error(err)); }
}

// ============================================================
// 学院筛选器初始化 & 专业图表重绘
// ============================================================
function initCollegeFilter(filterId, colleges) {
    const sel = document.getElementById(filterId);
    if (!sel) return;
    sel.innerHTML = '<option value="all">全部学院</option>' +
        colleges.map(c => `<option value="${c}">${c}</option>`).join('');
}

function filterMajorChart(page) {
    if (page === 'employment')   renderMajorEmployment();
    if (page === 'salary')       renderMajorSalary();
    if (page === 'gender')       renderMajorGenderDiff();
    if (page === 'postgraduate') renderMajorPostgrad();
}

function getFilteredMajors(dataList, filterId) {
    const sel = document.getElementById(filterId);
    if (!sel || sel.value === 'all') return dataList;
    return dataList.filter(d => d.院系 === sel.value || d.college === sel.value);
}

function getFilteredList(dataList, filterId) {
    const sel = document.getElementById(filterId);
    if (!sel || sel.value === 'all') return dataList;
    return dataList.filter(d => {
        const col = d.院系 || d.college || d.major_college || '';
        return col === sel.value;
    });
}

// ============================================================
// 初始化
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    loadOverview().catch(err => console.error(err));
});

// ============================================================
// 1. 项目概览
// ============================================================
async function loadOverview() {
    const d = await api('/api/overview');

    const cards = [
        {icon:'📋',cls:'blue',  value:`${d.total} 人`,    label:'纳入分析总人数',  detail:`本科 ${d.benke.total} · 硕士 ${d.shuoshi.total}`},
        {icon:'✅',cls:'green', value:`${d.overall_rate}%`, label:'整体就业率',      detail:`本科 ${d.benke.rate}% · 硕士 ${d.shuoshi.rate}%`},
        {icon:'💰',cls:'amber', value:`¥${d.salary.avg.toLocaleString()}`, label:'本科平均月薪', detail:`中位数 ¥${d.salary.median.toLocaleString()}`},
        {icon:'🏫',cls:'purple',value:`${d.colleges} 个`,  label:'覆盖学院',        detail:`${d.majors} 个专业方向`},
        {icon:'👥',cls:'teal',  value:`${d.gender.male}/${d.gender.female}`, label:'男女比例 (本科)', detail:`♂${(d.gender.male/(d.gender.male+d.gender.female)*100).toFixed(1)}% ♀${(d.gender.female/(d.gender.male+d.gender.female)*100).toFixed(1)}%`},
        {icon:'💼',cls:'red',   value:`${d.employed} 人`,  label:'已就业总人数',    detail:`覆盖率 ${d.overall_rate}%`},
    ];
    document.getElementById('overview-cards').innerHTML = cards.map(c => `
        <div class="stat-card"><div class="stat-icon ${c.cls}">${c.icon}</div><div class="stat-info"><div class="stat-value">${c.value}</div><div class="stat-label">${c.label}</div><div class="stat-detail">${c.detail}</div></div></div>
    `).join('');

    // 学历分布
    const eduChart = initChart('chart-edu-pie');
    if (eduChart) eduChart.setOption({
        title:{text:'学历层次分布',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'item',formatter:'{b}: {c} 人 ({d}%)'},
        legend:{bottom:10},
        series:[{type:'pie',radius:['45%','72%'],center:['50%','48%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:3},label:{formatter:'{b}\n{c}人 ({d}%)'},data:d.edu_dist,color:['#5470C6','#91CC75']}],
    });

    // 就业状态
    const empChart = initChart('chart-emp-status');
    if (empChart) empChart.setOption({
        title:{text:'本科生就业状态',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'item',formatter:'{b}: {c} 人 ({d}%)'},
        legend:{bottom:10},
        series:[{type:'pie',radius:['45%','72%'],center:['50%','48%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:3},label:{formatter:'{b}\n{c}人 ({d}%)'},data:d.emp_status,color:['#10B981','#EF4444']}],
    });

    // 毕业去向
    const fyChart = initChart('chart-fy-dist');
    if (fyChart) {
        const fy = Object.entries(d.fy_dist).sort((a,b)=>b[1]-a[1]);
        fyChart.setOption({
            title:{text:'毕业去向分布（本科生）',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
            grid:{left:5,right:'15%',top:'18%',bottom:'5%',containLabel:true},
            xAxis:{type:'value',name:'人数'},
            yAxis:{type:'category',data:fy.map(e=>e[0]),axisLabel:{fontSize:11},inverse:true},
            series:[{type:'bar',data:fy.map(e=>e[1]),barMaxWidth:26,
                itemStyle:{borderRadius:[0,4,4,0],color:new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#5470C6'},{offset:1,color:'#73C0DE'}])},
                label:{show:true,position:'right',fontSize:11}}],
        });
    }
}

// ============================================================
// 2. 就业率分析
// ============================================================
function renderMajorEmployment() {
    // 重绘专业就业率图表（根据学院筛选）
    if (!DATA.employment) return;
    const d = DATA.employment;
    const majors = getFilteredList(d.major, 'filter-er-college');

    const c4 = initChart('chart-er-major');
    if (!c4) return;
    c4.setOption({
        title:{text:`各专业本科就业率（${majors.length} 个专业）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
            formatter:p=>{const r=majors[p[0].dataIndex];return`<b>${r.院系} - ${r.专业名称}</b><br/>就业率: ${r.就业率}%<br/>就业: ${r.就业人数}/${r.总人数}`;}},
        grid:{left:'8%',right:'5%',top:'18%',bottom:'18%',containLabel:true},
        dataZoom:[{type:'slider',bottom:10,start:0,end: majors.length > 25 ? 25 : 100}],
        xAxis:{type:'category',data:majors.map(r=>r.专业名称),axisLabel:{rotate:45,fontSize:10,interval:0}},
        yAxis:{type:'value',name:'就业率 (%)',max:100,axisLabel:{formatter:'{value}%'}},
        series:[{type:'bar',
            data:majors.map(r=>({value:r.就业率,itemStyle:{color:r.就业率>=90?'#91CC75':r.就业率>=80?'#FAC858':'#EE6666'}})),
            barMaxWidth:28,itemStyle:{borderRadius:[4,4,0,0]},
            label:{show:true,position:'top',formatter:'{c}%',fontSize:9}}],
    });
}

async function loadEmploymentRate() {
    const d = await api('/api/employment_rate');
    DATA.employment = d;

    // 初始化学院筛选
    const colleges = [...new Set(d.major.map(r=>r.院系))].sort();
    initCollegeFilter('filter-er-college', colleges);

    // 全校就业率
    const c1 = initChart('chart-er-overall');
    if (c1) {
        const levels = d.overall.filter(r=>r.education_level!=='合计');
        c1.setOption({
            title:{text:'按学历层次就业率',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>就业率: <b>${p[0].value}%</b><br/>就业: ${p[0].dataExt}`},
            grid:{left:'15%',right:'15%',top:'20%',bottom:'12%',containLabel:true},
            xAxis:{type:'category',data:levels.map(r=>r.education_level==='本科'?'本科生':'硕士研究生'),axisLabel:{fontSize:14,fontWeight:'bold'}},
            yAxis:{type:'value',name:'就业率 (%)',max:100,axisLabel:{formatter:'{value}%'}},
            series:[{type:'bar',
                data:levels.map(r=>({value:r.就业率,dataExt:`${r.就业人数}/${r.总人数}`})),
                barWidth:'50%',
                itemStyle:{borderRadius:[8,8,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#5470C6'},{offset:1,color:'#91CC75'}])},
                label:{show:true,position:'top',formatter:'{c}%',fontSize:20,fontWeight:'bold',color:'#333'},
                markLine:{silent:true,data:[{yAxis:d.overall_total.就业率,name:'合计',label:{formatter:`合计: ${d.overall_total.就业率}%`}}],lineStyle:{color:'#EE6666',type:'dashed'}}}],
        });
    }

    // 分性别就业率
    const c2 = initChart('chart-er-gender');
    if (c2) {
        const gd = d.gender_stats;
        c2.setOption({
            title:{text:'分性别/学历就业率对比',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis'},
            legend:{data:['男','女'],top:38,right:'10%'},
            grid:{left:'15%',right:'10%',top:'22%',bottom:'10%',containLabel:true},
            xAxis:{type:'category',data:['本科生','硕士研究生'],axisLabel:{fontSize:13,fontWeight:'bold'}},
            yAxis:{type:'value',name:'就业率 (%)',max:100,axisLabel:{formatter:'{value}%'}},
            series:[
                {name:'男',type:'bar',data:gd.filter(r=>r.gender==='男').map(r=>r.rate),barGap:'10%',barWidth:'35%',itemStyle:{color:'#4A90D9',borderRadius:[4,4,0,0]},label:{show:true,position:'top',formatter:'{c}%',fontSize:12}},
                {name:'女',type:'bar',data:gd.filter(r=>r.gender==='女').map(r=>r.rate),barWidth:'35%',itemStyle:{color:'#E85D75',borderRadius:[4,4,0,0]},label:{show:true,position:'top',formatter:'{c}%',fontSize:12}}],
        });
    }

    // 各学院就业率
    const c3 = initChart('chart-er-college');
    if (c3) {
        c3.setOption({
            title:{text:'各学院本科就业率排名',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
                formatter:p=>{const r=d.college.find(c=>c.院系===p[0].name);return r?`<b>${r.院系}</b><br/>就业率: ${r.就业率}%<br/>就业: ${r.就业人数}/${r.总人数}`:'';}},
            grid:{left:5,right:'15%',top:'15%',bottom:'5%',containLabel:true},
            xAxis:{type:'value',name:'就业率 (%)',axisLabel:{formatter:'{value}%'}},
            yAxis:{type:'category',data:d.college.map(c=>c.院系).reverse(),axisLabel:{fontSize:11},inverse:true},
            series:[{type:'bar',data:d.college.map(c=>c.就业率).reverse(),barMaxWidth:24,
                itemStyle:{borderRadius:[0,4,4,0],color:new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#5470C6'},{offset:1,color:'#73C0DE'}])},
                label:{show:true,position:'right',formatter:'{c}%',fontSize:10}}],
        });
    }

    // 专业就业率（全部）
    renderMajorEmployment();

    // 各学院分性别就业率
    const c5 = initChart('chart-er-college-gender');
    if (c5) {
        const colList = [...new Set(d.college_gender.map(r=>r.college))];
        const mR = colList.map(c=>{const r=d.college_gender.find(r=>r.college===c&&r.gender==='男');return r?r.rate:0;});
        const fR = colList.map(c=>{const r=d.college_gender.find(r=>r.college===c&&r.gender==='女');return r?r.rate:0;});
        c5.setOption({
            title:{text:'各学院分性别本科就业率',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis'},
            legend:{data:['男','女'],top:38,right:'10%'},
            grid:{left:'8%',right:'8%',top:'22%',bottom:'10%',containLabel:true},
            xAxis:{type:'category',data:colList,axisLabel:{rotate:30,fontSize:10,interval:0}},
            yAxis:{type:'value',name:'就业率 (%)',max:100,axisLabel:{formatter:'{value}%'}},
            series:[
                {name:'男',type:'bar',data:mR,barGap:'10%',barWidth:'40%',itemStyle:{color:'#4A90D9',borderRadius:[4,4,0,0]}},
                {name:'女',type:'bar',data:fR,barWidth:'40%',itemStyle:{color:'#E85D75',borderRadius:[4,4,0,0]}}],
        });
    }
}

// ============================================================
// 3. 单位性质分布
// ============================================================
async function loadEmployerType() {
    const d = await api('/api/employer_type');

    const pie = initChart('chart-et-pie');
    if (pie) pie.setOption({
        title:{text:'单位性质占比',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'item',formatter:'{b}<br/>人数: {c} 人<br/>占比: {d}%'},
        legend:{orient:'vertical',right:'5%',top:'middle',formatter:n=>{const i=d.categories.find(r=>r.大类===n);return i?`${n} (${i.人数}人, ${i.占比}%)`:n;},textStyle:{fontSize:11}},
        series:[{type:'pie',radius:['42%','72%'],center:['40%','52%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:3},label:{formatter:'{b}\n{d}%',fontSize:11},emphasis:{label:{fontSize:16,fontWeight:'bold'}},data:d.categories.map(r=>({name:r.大类,value:r.人数})),color:COLORS}],
    });

    const bar = initChart('chart-et-bar');
    if (bar) bar.setOption({
        title:{text:'单位性质分布',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>人数: <b>${p[0].value} 人</b><br/>占比: <b>${p[0].dataExt}%</b>`},
        grid:{left:'10%',right:'8%',top:'15%',bottom:'12%',containLabel:true},
        xAxis:{type:'category',data:d.categories.map(r=>r.大类),axisLabel:{rotate:15,fontSize:10}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.categories.map(r=>({value:r.人数,dataExt:r.占比})),barWidth:'55%',
            itemStyle:{borderRadius:[6,6,0,0],color:p=>COLORS[p.dataIndex%COLORS.length]},
            label:{show:true,position:'top',formatter:p=>`${p.value}人\n(${p.data.dataExt}%)`,fontSize:10}}],
    });

    // 明细表（全部）
    const tbody = document.querySelector('#table-et-detail tbody');
    if (tbody) tbody.innerHTML = d.detail.map(r=>`<tr><td>${r.单位类型}</td><td>${r.大类}</td><td>${r.人数}</td></tr>`).join('');
}

// ============================================================
// 4. 薪酬分布
// ============================================================
function renderMajorSalary() {
    if (!DATA.salary) return;
    const d = DATA.salary;
    const majors = getFilteredList(d.major, 'filter-sal-college');

    const c4 = initChart('chart-sal-major');
    if (!c4) return;
    c4.setOption({
        title:{text:`各专业平均薪酬排名（${majors.length} 个专业）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
            formatter:p=>{const r=majors[p[0].dataIndex];return r?`<b>${r.院系} - ${r.专业名称}</b><br/>平均: ¥${r.平均薪酬.toLocaleString()}<br/>中位: ¥${r.中位数.toLocaleString()}<br/>人数: ${r.人数}`:'';}},
        grid:{left:'8%',right:'5%',top:'18%',bottom:'18%',containLabel:true},
        dataZoom:[{type:'slider',bottom:10,start:0,end: majors.length > 25 ? 25 : 100}],
        xAxis:{type:'category',data:majors.map(r=>r.专业名称),axisLabel:{rotate:45,fontSize:10,interval:0}},
        yAxis:{type:'value',name:'平均薪酬 (元/月)'},
        series:[{type:'bar',data:majors.map(r=>r.平均薪酬),barMaxWidth:28,
            itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#FAC858'},{offset:1,color:'#FC8452'}])},
            label:{show:true,position:'top',formatter:p=>'¥'+p.value.toLocaleString(),fontSize:9}}],
    });
}

async function loadSalary() {
    const d = await api('/api/salary');
    DATA.salary = d;

    const colleges = [...new Set(d.major.map(r=>r.院系))].sort();
    initCollegeFilter('filter-sal-college', colleges);

    // 概览卡片
    const cardsEl = document.getElementById('salary-cards');
    if (cardsEl) {
        const sc = [
            {icon:'💵',cls:'green', value:`¥${d.overall.mean.toLocaleString()}`, label:'平均薪酬 (月)'},
            {icon:'📐',cls:'blue',  value:`¥${d.overall.median.toLocaleString()}`, label:'中位数', detail:`P25: ¥${d.overall.p25.toLocaleString()} · P75: ¥${d.overall.p75.toLocaleString()}`},
            {icon:'📏',cls:'purple',value:`¥${d.overall.min.toLocaleString()} ~ ¥${d.overall.max.toLocaleString()}`, label:'薪酬范围', detail:`标准差: ¥${d.overall.std.toLocaleString()}`},
            {icon:'👥',cls:'teal',  value:`${d.overall.count} 人`, label:'有效样本量'},
        ];
        cardsEl.innerHTML = sc.map(c=>`
            <div class="stat-card"><div class="stat-icon ${c.cls}">${c.icon}</div><div class="stat-info"><div class="stat-value">${c.value}</div><div class="stat-label">${c.label}</div>${c.detail?`<div class="stat-detail">${c.detail}</div>`:''}</div></div>
        `).join('');
    }

    // 学院平均薪酬（横柱图：高薪在上）
    const c1 = initChart('chart-sal-college');
    if (c1) {
        const list = d.college;  // API 已按平均薪酬降序排列
        c1.setOption({
            title:{text:'各学院本科平均薪酬',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis',axisPointer:{type:'shadow'},
                formatter:p=>{const r=list[p[0].dataIndex];return r?`<b>${r.院系}</b><br/>平均: ¥${r.平均薪酬.toLocaleString()}<br/>中位: ¥${r.中位数.toLocaleString()}<br/>人数: ${r.人数}`:'';}},
            grid:{left:5,right:'15%',top:'15%',bottom:'5%',containLabel:true},
            xAxis:{type:'value',name:'薪酬 (元/月)',axisLabel:{formatter:v=>'¥'+(v/1000).toFixed(1)+'k'}},
            yAxis:{type:'category',data:list.map(r=>r.院系),axisLabel:{fontSize:11},inverse:true},
            series:[{type:'bar',data:list.map(r=>r.平均薪酬),barMaxWidth:24,
                itemStyle:{borderRadius:[0,4,4,0],color:new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#FAC858'},{offset:1,color:'#EE6666'}])},
                label:{show:true,position:'right',formatter:p=>'¥'+p.value.toLocaleString(),fontSize:10}}],
        });
    }

    // 薪酬区间分布
    const c2 = initChart('chart-sal-dist');
    if (c2) c2.setOption({
        title:{text:'薪酬区间分布',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>人数: <b>${p[0].value} 人</b>`},
        grid:{left:'10%',right:'8%',top:'15%',bottom:'10%',containLabel:true},
        xAxis:{type:'category',data:d.distribution.map(r=>r.range),axisLabel:{rotate:30,fontSize:10}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.distribution.map(r=>r.count),barWidth:'65%',
            itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#91CC75'},{offset:1,color:'#3BA272'}])},
            label:{show:true,position:'top',fontSize:10}}],
    });

    // 箱线图 — 按学院分组展示薪酬分布
    const c3 = initChart('chart-sal-boxplot');
    if (c3 && d.boxplot && d.boxplot.length > 0) {
        // 按学院平均薪酬从高到低排序
        const sorted = [...d.boxplot].sort((a,b)=>b.median-a.median);
        c3.setOption({
            title:{text:'各学院薪酬箱线图',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'item',formatter:p=>{const r=sorted[p.dataIndex];return r?`<b>${r.college}</b><br/>最高: ¥${r.max}<br/>Q3: ¥${r.q3}<br/>中位数: ¥${r.median}<br/>Q1: ¥${r.q1}<br/>最低: ¥${r.min}<br/>样本: ${r.count}人`:'';}},
            grid:{left:'10%',right:'8%',top:'15%',bottom:'10%',containLabel:true},
            xAxis:{type:'category',data:sorted.map(r=>r.college),axisLabel:{rotate:30,fontSize:10,interval:0},boundaryGap:true},
            yAxis:{type:'value',name:'薪酬 (元/月)',min:0},
            series:[{type:'boxplot',data:sorted.map(r=>[r.min,r.q1,r.median,r.q3,r.max]),
                itemStyle:{color:'#5470C6',borderColor:'#3B5BA5'},
                boxWidth:[18,28]}],
        });
    }

    // 专业薪酬（全部）
    renderMajorSalary();
}

// ============================================================
// 5. 性别薪酬差异
// ============================================================
function renderMajorGenderDiff() {
    if (!DATA.gender) return;
    const d = DATA.gender;
    const majors = getFilteredList(d.major_gender, 'filter-gs-college');

    const c3 = initChart('chart-gs-major');
    if (!c3) return;
    c3.setOption({
        title:{text:`各专业男女薪酬差异（${majors.length} 个专业）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis'},
        legend:{data:['男性平均','女性平均'],top:38,right:'10%'},
        grid:{left:'8%',right:'5%',top:'22%',bottom:'18%',containLabel:true},
        dataZoom:[{type:'slider',bottom:10,start:0,end: majors.length > 25 ? 25 : 100}],
        xAxis:{type:'category',data:majors.map(r=>r.major),axisLabel:{rotate:35,fontSize:10,interval:0}},
        yAxis:{type:'value',name:'薪酬 (元/月)'},
        series:[
            {name:'男性平均',type:'bar',data:majors.map(r=>r.male_mean),barGap:'10%',barWidth:'40%',itemStyle:{color:'#4A90D9',borderRadius:[4,4,0,0]}},
            {name:'女性平均',type:'bar',data:majors.map(r=>r.female_mean),barWidth:'40%',itemStyle:{color:'#E85D75',borderRadius:[4,4,0,0]}},
        ],
    });
}

async function loadGenderSalary() {
    const d = await api('/api/gender_salary');
    DATA.gender = d;

    const majorColleges = [...new Set(d.major_gender.map(r=>{
        // 从专业名称推断院系 — 我们从 salary API 获取院系映射
        return '';
    }).filter(Boolean))];

    // 从 API 数据（已含院系字段）初始化学院筛选器
    const colleges = [...new Set(d.major_gender.map(r=>r.院系).filter(Boolean))].sort();
    initCollegeFilter('filter-gs-college', colleges);

    // 概览卡片
    const cardsEl = document.getElementById('gender-cards');
    if (cardsEl) {
        const gc = [
            {icon:'👨',cls:'blue',  value:`¥${d.overall.male.mean.toLocaleString()}`, label:'男性平均薪酬', detail:`中位数 ¥${d.overall.male.median.toLocaleString()} · ${d.overall.male.count}人`},
            {icon:'👩',cls:'red',   value:`¥${d.overall.female.mean.toLocaleString()}`, label:'女性平均薪酬', detail:`中位数 ¥${d.overall.female.median.toLocaleString()} · ${d.overall.female.count}人`},
            {icon:'📊',cls:'amber', value:`¥${Math.abs(d.overall.diff).toLocaleString()}`, label:'男女薪酬差', detail:`男性${d.overall.diff>0?'高':'低'}${Math.abs(d.overall.diff)}元`},
            {icon:'📉',cls:'purple',value:`${(d.overall.diff/d.overall.female.mean*100).toFixed(1)}%`, label:'差异比例', detail:'相对女性均值'},
        ];
        cardsEl.innerHTML = gc.map(c=>`
            <div class="stat-card"><div class="stat-icon ${c.cls}">${c.icon}</div><div class="stat-info"><div class="stat-value">${c.value}</div><div class="stat-label">${c.label}</div><div class="stat-detail">${c.detail}</div></div></div>
        `).join('');
    }

    // 学院男女薪酬对比
    const c1 = initChart('chart-gs-bar');
    if (c1) {
        const list = d.college.filter(r=>r.male_mean&&r.female_mean);
        c1.setOption({
            title:{text:'各学院男女平均薪酬对比',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis'},
            legend:{data:['男','女'],top:38,right:'10%'},
            grid:{left:'8%',right:'8%',top:'22%',bottom:'8%',containLabel:true},
            xAxis:{type:'category',data:list.map(r=>r.college),axisLabel:{rotate:25,fontSize:10}},
            yAxis:{type:'value',name:'平均薪酬 (元/月)'},
            series:[
                {name:'男',type:'bar',data:list.map(r=>r.male_mean),barGap:'10%',barWidth:'38%',itemStyle:{color:'#4A90D9',borderRadius:[4,4,0,0]}},
                {name:'女',type:'bar',data:list.map(r=>r.female_mean),barWidth:'38%',itemStyle:{color:'#E85D75',borderRadius:[4,4,0,0]}}],
        });
    }

    // 密度分布
    const c2 = initChart('chart-gs-density');
    if (c2) c2.setOption({
        title:{text:'男女薪酬分布密度对比',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis'},
        legend:{data:['男','女'],top:38,right:'10%'},
        grid:{left:'8%',right:'5%',top:'20%',bottom:'8%',containLabel:true},
        xAxis:{type:'category',data:d.distribution.map(r=>r.range),axisLabel:{rotate:30,fontSize:10}},
        yAxis:{type:'value',name:'概率密度'},
        series:[
            {name:'男',type:'line',data:d.distribution.map(r=>r.male_density),smooth:true,lineStyle:{color:'#4A90D9',width:3},areaStyle:{color:'rgba(74,144,217,0.12)'},symbol:'none'},
            {name:'女',type:'line',data:d.distribution.map(r=>r.female_density),smooth:true,lineStyle:{color:'#E85D75',width:3},areaStyle:{color:'rgba(232,93,117,0.12)'},symbol:'none'}],
    });

    // 专业男女薪酬差异（全部）
    renderMajorGenderDiff();
}

// ============================================================
// 6. 地区分布
// ============================================================
async function loadLocation() {
    const d = await api('/api/location');
    const locColors = ['#FF6B6B','#4ECDC4','#45B7D1','#96CEB4','#D4D4D4'];

    const pie = initChart('chart-loc-pie');
    if (pie) pie.setOption({
        title:{text:`就业地区分类（N=${d.total_with_location}）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'item',formatter:'{b}<br/>人数: {c} 人<br/>占比: {d}%'},
        legend:{orient:'vertical',right:'5%',top:'middle',textStyle:{fontSize:11},formatter:n=>{const i=d.categories.find(r=>r.name===n);return i?`${n} (${i.count}人, ${i.percent}%)`:n;}},
        series:[{type:'pie',radius:['40%','68%'],center:['40%','52%'],itemStyle:{borderRadius:4,borderColor:'#fff',borderWidth:3},label:{formatter:'{b}\n{d}%',fontSize:11},data:d.categories.filter(r=>r.count>0).map(r=>({name:r.name,value:r.count})),color:locColors}],
    });

    const gba = initChart('chart-loc-gba');
    if (gba) gba.setOption({
        title:{text:'大湾区各城市就业人数',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>人数: <b>${p[0].value} 人</b>`},
        grid:{left:'10%',right:'10%',top:'15%',bottom:'8%',containLabel:true},
        xAxis:{type:'category',data:d.gba_cities.map(r=>r.name),axisLabel:{fontSize:11}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.gba_cities.map(r=>r.count),barWidth:'50%',
            itemStyle:{borderRadius:[6,6,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#FF6B6B'},{offset:1,color:'#D94A4A'}])},
            label:{show:true,position:'top',fontSize:11}}],
    });

    const prov = initChart('chart-loc-province');
    if (prov) prov.setOption({
        title:{text:'省外就业省份分布',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
        grid:{left:'8%',right:'5%',top:'15%',bottom:'15%',containLabel:true},
        xAxis:{type:'category',data:d.provinces.map(r=>r.name),axisLabel:{rotate:35,fontSize:10,interval:0}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.provinces.map(r=>r.count),barWidth:'55%',
            itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#45B7D1'},{offset:1,color:'#96CEB4'}])},
            label:{show:true,position:'top',fontSize:10}}],
    });

    // 省内非大湾区城市
    const gdOther = initChart('chart-loc-gd-other');
    if (gdOther && d.gd_other_cities && d.gd_other_cities.length > 0) gdOther.setOption({
        title:{text:'省内非大湾区城市就业分布',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>人数: <b>${p[0].value} 人</b>`},
        grid:{left:'10%',right:'8%',top:'15%',bottom:'12%',containLabel:true},
        xAxis:{type:'category',data:d.gd_other_cities.map(r=>r.name),axisLabel:{fontSize:11}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.gd_other_cities.map(r=>r.count),barWidth:'50%',
            itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#4ECDC4'},{offset:1,color:'#2BA89A'}])},
            label:{show:true,position:'top',fontSize:11}}],
    });

    const ovs = initChart('chart-loc-overseas');
    if (ovs && d.overseas.length>0) ovs.setOption({
        title:{text:'境外就业主要国家',left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',formatter:p=>`${p[0].name}<br/>人数: <b>${p[0].value} 人</b>`},
        grid:{left:'15%',right:'15%',top:'15%',bottom:'8%',containLabel:true},
        xAxis:{type:'category',data:d.overseas.map(r=>r.name),axisLabel:{fontSize:12}},
        yAxis:{type:'value',name:'人数'},
        series:[{type:'bar',data:d.overseas.map(r=>r.count),barWidth:'45%',itemStyle:{borderRadius:[6,6,0,0],color:'#96CEB4'},label:{show:true,position:'top',fontSize:11}}],
    });
    else if (ovs) ovs.setOption({title:{text:'境外就业主要国家',left:'center',top:8},graphic:{type:'text',left:'center',top:'center',style:{text:'暂无数据',fontSize:14,fill:'#999'}}});
}

// ============================================================
// 7. 考研升学
// ============================================================
function renderMajorPostgrad() {
    if (!DATA.postgraduate) return;
    const d = DATA.postgraduate;
    const majors = getFilteredList(d.major_summary, 'filter-pg-college');

    const c1 = initChart('chart-pg-major');
    if (!c1) return;
    c1.setOption({
        title:{text:`各专业升学人数（${majors.length} 个专业）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
        tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
        grid:{left:'8%',right:'5%',top:'15%',bottom:'18%',containLabel:true},
        dataZoom:[{type:'slider',bottom:10,start:0,end: majors.length > 25 ? 25 : 100}],
        xAxis:{type:'category',data:majors.map(r=>r.专业名称),axisLabel:{rotate:35,fontSize:10,interval:0}},
        yAxis:{type:'value',name:'升学人数'},
        series:[{type:'bar',data:majors.map(r=>r.升学人数),barMaxWidth:28,
            itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#9A60B4'},{offset:1,color:'#EA7CCC'}])},
            label:{show:true,position:'top',fontSize:10}}],
    });
}

async function loadPostgraduate() {
    const d = await api('/api/postgraduate');
    DATA.postgraduate = d;

    // API 已含院系字段，直接初始化学院筛选器
    const colleges = [...new Set(d.major_summary.map(r=>r.院系).filter(Boolean))].sort();
    initCollegeFilter('filter-pg-college', colleges);

    // 各专业升学人数
    renderMajorPostgrad();

    // 热门院校
    const c2 = initChart('chart-pg-school');
    if (c2) {
        const list = d.school_ranking;
        c2.setOption({
            title:{text:`升学热门院校（${list.length} 所）`,left:'center',top:8,textStyle:{fontSize:15,fontWeight:'bold'}},
            tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},
            grid:{left:'8%',right:'5%',top:'15%',bottom:'18%',containLabel:true},
            dataZoom:[{type:'slider',bottom:10,start:0,end: list.length > 15 ? 15 : 100}],
            xAxis:{type:'category',data:list.map(r=>r.name),axisLabel:{rotate:35,fontSize:10,interval:0}},
            yAxis:{type:'value',name:'升学人数'},
            series:[{type:'bar',data:list.map(r=>r.count),barMaxWidth:28,
                itemStyle:{borderRadius:[4,4,0,0],color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#3BA272'},{offset:1,color:'#73C0DE'}])},
                label:{show:true,position:'top',fontSize:9}}],
        });
    }

    // TOP3 表格（全部）
    const tbody = document.querySelector('#table-pg-pivot tbody');
    if (tbody) {
        tbody.innerHTML = d.pivot.map(r=>`<tr>
            <td>${r.major}</td><td><b>${r.total}</b></td>
            <td>${r.top1_school}</td><td>${r.top1_count}</td>
            <td>${r.top2_school}</td><td>${r.top2_count}</td>
            <td>${r.top3_school}</td><td>${r.top3_count}</td>
        </tr>`).join('');
    }
}

// ============================================================
// ============================================================
// 8. 用人单位性质预测模型
// ============================================================
async function loadMLResults() {
    const d = await api('/api/ml_results');

    // 模型架构说明
    const infoGrid = document.getElementById('ml-info-grid');
    if (infoGrid) {
        const items = [
            ['🧠 框架', 'PyTorch + TabNet（深度表格学习模型）'],
            ['📋 任务', '8 分类 — 预测毕业生就业单位类型'],
            ['🏷️ 类别', '8 类：' + (d.class_names||[]).join('、')],
            ['📊 特征', '7个分类特征：' + (d.features||[]).join('、')],
            ['📐 类别数', '各特征类别：' + (d.cat_dims||[]).join('、')],
            ['📦 数据划分', d.data_split ? '训练集 ' + d.data_split.train + ' · 验证集 ' + d.data_split.val + ' · 测试集 ' + d.data_split.test + '（分层抽样 70/15/15）' : '—'],
            ['⚖️ 类别平衡', d.class_weights ? '各类别权重：' + JSON.stringify(d.class_weights) : '—'],
            ['⚙️ 优化器', 'Adam + ReduceLROnPlateau 学习率调度'],
            ['📉 损失函数', 'CrossEntropyLoss（带类别权重）'],
            ['⏹️ 早停', 'Patience=15 epochs，监控验证损失'],
            ['🔢 参数', 'TabNet: n_d=32, n_a=32, n_steps=5, gamma=1.5, cat_emb_dim=8'],
        ];
        infoGrid.innerHTML = items.map(function(item) {
            return '<div class="ml-item"><span class="ml-label">' + item[0] + '</span><span class="ml-value">' + item[1] + '</span></div>';
        }).join('');
    }

    // 评估指标
    const metricsContainer = document.getElementById('ml-metrics-container');
    if (metricsContainer && d.metrics) {
        const m = d.metrics;
        metricsContainer.innerHTML = '<div class="metrics-grid">' +
            '<div class="metric-card"><div class="metric-value" style="color:#3B82F6;">' + (m.accuracy*100).toFixed(2) + '%</div><div class="metric-label">准确率 Accuracy</div></div>' +
            '<div class="metric-card"><div class="metric-value" style="color:#10B981;">' + (m.precision_weighted*100).toFixed(2) + '%</div><div class="metric-label">加权精确率 Precision</div></div>' +
            '<div class="metric-card"><div class="metric-value" style="color:#F59E0B;">' + (m.recall_weighted*100).toFixed(2) + '%</div><div class="metric-label">加权召回率 Recall</div></div>' +
            '<div class="metric-card"><div class="metric-value" style="color:#8B5CF6;">' + (m.f1_weighted*100).toFixed(2) + '%</div><div class="metric-label">加权 F1-Score</div></div>' +
            '</div><p style="margin-top:12px;font-size:12px;color:#64748B;">注：数据严重不均衡（民营企业占 57%），7 个小类别样本极少（0.9%~10%），模型倾向于预测为多数类。</p>';
    } else if (metricsContainer) {
        metricsContainer.innerHTML = '<div class="placeholder">⚠️ 请运行 <code>python tabnet_classification.py</code> 训练模型并生成评估指标</div>';
    }

    // 混淆矩阵图片
    const cmContainer = document.getElementById('ml-cm-container');
    if (cmContainer) {
        if (d.has_cm) cmContainer.innerHTML = '<img src="' + d.cm_url + '" alt="混淆矩阵 (8×8)" style="max-width:100%;border-radius:8px;">';
        else cmContainer.innerHTML = '<div class="placeholder">⚠️ 混淆矩阵尚未生成</div>';
    }

    // 损失曲线图片
    const lossContainer = document.getElementById('ml-loss-container');
    if (lossContainer) {
        if (d.has_loss) lossContainer.innerHTML = '<img src="' + d.loss_url + '" alt="训练损失曲线" style="max-width:100%;border-radius:8px;">';
        else lossContainer.innerHTML = '<div class="placeholder">⚠️ 损失曲线尚未生成</div>';
    }

    // 错误分类分析
    const errorContainer = document.getElementById('ml-error-container');
    if (errorContainer && d.error_analysis) {
        const err = d.error_analysis;
        let html = '<div class="metrics-grid" style="margin-bottom:20px;">' +
            '<div class="metric-card"><div class="metric-value" style="color:#EF4444;">' + err.total_errors + ' / ' + err.total_test + '</div><div class="metric-label">错误分类总数 (错误率 ' + (err.error_rate*100).toFixed(2) + '%)</div></div>' +
            '<div class="metric-card"><div class="metric-value">' + (d.num_classes||8) + '</div><div class="metric-label">目标类别数</div></div>' +
            '</div>';

        if (err.error_by_class) {
            html += '<h4 style="margin-bottom:8px;">各类别误判分析</h4><div style="overflow-x:auto;"><table class="data-table" style="margin-bottom:20px;"><thead><tr><th>类别</th><th>测试样本</th><th>误判数</th><th>误判率</th><th>主要被误判为</th></tr></thead><tbody>';
            Object.entries(err.error_by_class).forEach(function(entry) {
                var cls = entry[0], info = entry[1];
                var confused = (info.most_confused_with||[]).map(function(c){return c.class+'('+c.count+')';}).join('、');
                html += '<tr><td><b>' + cls + '</b></td><td>' + info.total + '</td><td style="color:' + (info.rate>0.9?'#EF4444':'#F59E0B') + ';">' + info.wrong + '</td><td>' + (info.rate*100).toFixed(0) + '%</td><td>' + confused + '</td></tr>';
            });
            html += '</tbody></table></div>';
        }

        if (err.error_samples && err.error_samples.length > 0) {
            html += '<h4 style="margin-bottom:8px;">错误分类样本（前15条）</h4><div style="overflow-x:auto;"><table class="data-table"><thead><tr><th>#</th><th>性别</th><th>学历</th><th>专业</th><th>生源地</th><th>真实标签</th><th>预测标签</th></tr></thead><tbody>';
            err.error_samples.slice(0,15).forEach(function(s, i) {
                html += '<tr><td>' + (i+1) + '</td><td>' + s.gender + '</td><td>' + s.education + '</td><td>' + s.major + '</td><td>' + s.province + '</td><td>' + s.true_label + '</td><td style="color:#EF4444;">' + s.pred_label + '</td></tr>';
            });
            html += '</tbody></table></div>';
        }
        errorContainer.innerHTML = html;
    } else if (errorContainer) {
        errorContainer.innerHTML = '<div class="placeholder">请运行 <code>python tabnet_classification.py</code> 生成错误分类数据</div>';
    }

    // 初始化预测表单
    initPredictForm();
}

// ============================================================
// 9. 交互式预测
// ============================================================
async function initPredictForm() {
    try {
        const info = await api('/api/model_info');
        function fill(id, values) {
            const sel = document.getElementById(id);
            if (!sel) return;
            sel.innerHTML = values.map(v => '<option value="' + v + '">' + v + '</option>').join('');
        }
        fill('pred-gender', info.gender || []);
        fill('pred-edu', info.education || []);
        fill('pred-major', info.major || []);
        fill('pred-province', info.province || []);
        fill('pred-zyk', info.zyk || []);
        fill('pred-zzmm', info.zzmm || []);
        fill('pred-mz', info.mz || []);
    } catch(e) { console.error('Failed to load model info:', e); }
}

async function doPredict() {
    const resultDiv = document.getElementById('predict-result');
    if (!resultDiv) return;
    resultDiv.innerHTML = '<div class="placeholder">预测中...</div>';

    const payload = {
        gender:   document.getElementById('pred-gender')?.value || '男',
        education:document.getElementById('pred-edu')?.value || '本科',
        major:    document.getElementById('pred-major')?.value || '',
        province: document.getElementById('pred-province')?.value || '广东省',
        zyk:      document.getElementById('pred-zyk')?.value || '未知',
        zzmm:     document.getElementById('pred-zzmm')?.value || '群众',
        mz:       document.getElementById('pred-mz')?.value || '汉族',
    };

    try {
        const resp = await fetch('/api/predict', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (data.error) {
            resultDiv.innerHTML = '<div class="placeholder" style="color:#EF4444;">' + data.error + '</div>';
            return;
        }

        const colors = ['#3B82F6','#10B981','#F59E0B','#8B5CF6','#EF4444','#EC4899','#06B6D4','#84CC16'];
        let html = '<div class="predict-top"><div class="top-label">最可能</div><div class="top-value">' + data.prediction + '（' + data.confidence + '%）</div></div>';
        data.results.forEach(function(r, i) {
            var pct = r.percent.toFixed(1);
            html += '<div class="predict-result-bar">' +
                '<span class="bar-label">' + r.class + '</span>' +
                '<div class="bar-track"><div class="bar-fill" style="width:' + Math.max(pct, 2) + '%;background:' + (colors[i] || '#999') + ';">' + pct + '%</div></div>' +
                '</div>';
        });
        resultDiv.innerHTML = html;
    } catch(e) {
        resultDiv.innerHTML = '<div class="placeholder" style="color:#EF4444;">预测失败: ' + e.message + '</div>';
    }
}