# -*- coding: utf-8 -*-
"""
毕业生就业分析 - 深度学习分类任务（方案C）
===========================================
使用 PyTorch + TabNet 预测毕业生用人单位性质（8 分类）

任务: 根据性别、学历、专业、生源地，预测毕业生的就业单位类型
类别: 机关事业单位 / 国有企业 / 民营企业 / 外资企业 /
       基层项目 / 升学 / 灵活就业/自由职业 / 其他/未知

Author: Course Project
"""

import sys, os, re, warnings, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
)
from sklearn.utils.class_weight import compute_class_weight

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")

# ============================================================
# 0. 路径配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "clean_data.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "charts")
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 中文字体（扫描系统可用字体，选择第一个匹配的）
from matplotlib import font_manager as _fm
_fonts = {f.name for f in _fm.fontManager.ttflist}
_chosen = None
for _fn in ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC"]:
    if _fn in _fonts: _chosen = _fn; break
if _chosen:
    plt.rcParams["font.sans-serif"] = [_chosen, "DejaVu Sans"]
    print(f"  [字体] {_chosen}")
else:
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    print("  [字体] 未找到中文字体")
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 1. 用人单位归类函数
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
# 2. 数据加载与预处理
# ============================================================
print("=" * 60)
print("1. 加载数据")
print("=" * 60)
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"  原始数据: {df.shape}")

# ⭐ 筛选：本科生 + 已就业
df = df[(df["education_level"] == "本科") & (df["is_employed"] == True)].copy()
print(f"  筛选后 (本科已就业): {df.shape[0]} 条")

# ⭐ 创建目标列：用人单位性质（8 分类）
df["employer_type"] = df["单位类型"].apply(classify_employer_type)
print(f"  目标分布 (8类):")
for cat, cnt in df["employer_type"].value_counts().items():
    print(f"    {cat}: {cnt} ({cnt/len(df)*100:.1f}%)")
print(f"  使用设备: {DEVICE}")


# ============================================================
# 3. 特征工程
# ============================================================
print("\n" + "=" * 60)
print("2. 特征工程")
print("=" * 60)

# 生源地简化提取：只保留省份维度，降低特征基数
def extract_province(addr: str) -> str:
    if pd.isna(addr):
        return "未知"
    addr = str(addr).strip()
    match = re.match(r"^(.+?省|.+?自治区|.+?市)", addr)
    if match:
        return match.group(1)
    return addr[:3] if len(addr) >= 3 else addr


df["province"] = df["生源地_stu"].apply(extract_province)

# ⭐ 新增特征预处理
# 专业是否对口（col[12]）→ 填充缺失为"未知"
col_zyk = df.columns[12]      # 专业是否对口
col_zzmm = df.columns[28]     # 政治面貌
col_mz   = df.columns[27]     # 民族
df[col_zyk] = df[col_zyk].fillna("未知")

# 建模输入特征（7个）、目标标签
feature_cols = [
    "性别",           # 2 类
    "education_level",# 1 类（仅本科）
    "专业名称",       # ~53 类
    "province",       # ~17 类（生源地省份）
    col_zyk,          # 6 类
    col_zzmm,         # 4 类
    col_mz,           # ~10 类
]
target_col = "employer_type"

print(f"  特征列: {feature_cols}")
print(f"  目标列: {target_col}")

# 处理缺失值
for col in feature_cols:
    n_missing = df[col].isnull().sum()
    if n_missing > 0:
        df[col] = df[col].fillna("未知")
        print(f"  {col}: 缺失{n_missing}条 → 填充为'未知'")
# 统计每个特征唯一类别数量
for col in feature_cols:
    print(f"  {col}: {df[col].nunique()} 个唯一值")


# ============================================================
# 4. LabelEncoder 编码
# 将所有输入特征 + 预测目标标签全部转为 0 起始连续整数；
# 同时输出模型构建所需关键参数（特征索引、每类特征取值总数、多分类平衡权重），
# 为后面 TabNet / EmbeddingMLP 网络搭建提供全部前置数据。
# ============================================================
print("\n" + "=" * 60)
print("3. LabelEncoder 编码")
print("=" * 60)

encoders = {}
df_encoded = df.copy()
# 对4个输入特征做标签编码
for col in feature_cols:
    le = LabelEncoder()
    df_encoded[col + "_enc"] = le.fit_transform(df_encoded[col].astype(str))
    encoders[col] = le
    print(f"  {col}: {len(le.classes_)} 类 -> 编码 [0, {len(le.classes_) - 1}]")

# ⭐ 目标列编码（8 分类）
target_le = LabelEncoder()
df_encoded["target_enc"] = target_le.fit_transform(df_encoded[target_col].astype(str))
num_classes = len(target_le.classes_)
print(f"\n  目标 '{target_col}': {num_classes} 类")
for i, cls in enumerate(target_le.classes_):
    count = (df_encoded["target_enc"] == i).sum()
    print(f"    类别 {i}: {cls} ({count} 样本)")

# 特征矩阵 X, 目标标签 y
encoded_feat_cols = [col + "_enc" for col in feature_cols]
X = df_encoded[encoded_feat_cols].values.astype(np.float32)
y = df_encoded["target_enc"].values.astype(np.int64)

cat_idxs = list(range(len(feature_cols)))
cat_dims = [df_encoded[col].nunique() for col in encoded_feat_cols]
print(f"\n  特征维度: {X.shape}")
print(f"  分类特征索引: {cat_idxs}")
print(f"  各特征类别数: {cat_dims}")

# ⭐ 计算多分类平衡类别权重
class_weights = compute_class_weight("balanced", classes=np.unique(y), y=y)
print(f"  类别权重: {dict(zip(range(len(class_weights)), [f'{w:.4f}' for w in class_weights]))}")


# ============================================================
# 5. 数据划分: 70% 训练, 15% 验证, 15% 测试
# ============================================================
print("\n" + "=" * 60)
print("4. 数据划分 (70/15/15, 分层抽样)")
print("=" * 60)

n_total = len(df_encoded)
all_idx = np.arange(n_total)

train_idx, temp_idx = train_test_split(
    all_idx, test_size=0.30, stratify=y, random_state=42
)
y_temp = y[temp_idx]
val_idx_in_temp, test_idx_in_temp = train_test_split(
    np.arange(len(temp_idx)), test_size=0.50, stratify=y_temp, random_state=42
)

val_idx = temp_idx[val_idx_in_temp]
test_idx = temp_idx[test_idx_in_temp]

X_train, y_train = X[train_idx], y[train_idx]
X_val,   y_val   = X[val_idx],   y[val_idx]
X_test,  y_test  = X[test_idx],  y[test_idx]

print(f"  训练集: {len(X_train)}")
print(f"  验证集: {len(X_val)}")
print(f"  测试集: {len(X_test)}")

BATCH_SIZE = 256
X_train_t = torch.tensor(X_train, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.long)
X_val_t   = torch.tensor(X_val,   dtype=torch.float32)
y_val_t   = torch.tensor(y_val,   dtype=torch.long)
X_test_t  = torch.tensor(X_test,  dtype=torch.float32)
y_test_t  = torch.tensor(y_test,  dtype=torch.long)

train_loader = DataLoader(TensorDataset(X_train_t, y_train_t),
                          batch_size=BATCH_SIZE, shuffle=True)
val_loader   = DataLoader(TensorDataset(X_val_t, y_val_t),
                          batch_size=BATCH_SIZE, shuffle=False)
test_loader  = DataLoader(TensorDataset(X_test_t, y_test_t),
                          batch_size=BATCH_SIZE, shuffle=False)

class_weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)
criterion = nn.CrossEntropyLoss(weight=class_weight_tensor)


# ============================================================
# 6. 模型加载
# ============================================================
print("\n" + "=" * 60)
print("5. 模型加载")
print("=" * 60)

USE_TABNET = False
try:
    from pytorch_tabnet.tab_model import TabNetClassifier
    USE_TABNET = True
    print("  [OK] pytorch-tabnet 可用，将使用 TabNet 模型")
except ImportError:
    print("  [WARN]  pytorch-tabnet 未安装，正在安装...")
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "pytorch-tabnet", "-q",
         "--index-url", "https://pypi.tuna.tsinghua.edu.cn/simple"],
        capture_output=True, text=True
    )
    try:
        from pytorch_tabnet.tab_model import TabNetClassifier
        USE_TABNET = True
        print("  [OK] pytorch-tabnet 安装成功")
    except ImportError:
        print("  [FAIL] pytorch-tabnet 安装失败，将使用 EmbeddingMLP 作为备选方案")


# ============================================================
# 6a. EmbeddingMLP 备选模型（多分类版）
# ============================================================
class EmbeddingMLP(nn.Module):
    def __init__(self, cat_dims, embedding_dim=16, hidden_dims=None,
                 num_classes=8, dropout=0.3):
        super(EmbeddingMLP, self).__init__()
        if hidden_dims is None:
            hidden_dims = [256, 128, 64, 32]
        self.emb_dims = [min(embedding_dim, dim // 2 + 1) for dim in cat_dims]
        self.embeddings = nn.ModuleList([
            nn.Embedding(dim, emb_dim)
            for dim, emb_dim in zip(cat_dims, self.emb_dims)
        ])
        total_emb_dim = sum(self.emb_dims)
        layers = []
        prev_dim = total_emb_dim
        for hdim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hdim),
                nn.BatchNorm1d(hdim),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = hdim
        layers.append(nn.Linear(prev_dim, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        x_long = x.long()
        embs = [self.embeddings[i](x_long[:, i])
                for i in range(len(self.embeddings))]
        x_emb = torch.cat(embs, dim=1)
        return self.network(x_emb)


# ============================================================
# 7. 训练 & 评估工具
# ============================================================
def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for bx, by in loader:
        bx, by = bx.to(device), by.to(device)
        optimizer.zero_grad()
        loss = criterion(model(bx), by)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * bx.size(0)
        correct += (model(bx).argmax(1) == by).sum().item()
        total += bx.size(0)
    return total_loss / total, correct / total


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, total = 0.0, 0, 0
    all_preds, all_labels = [], []
    for bx, by in loader:
        bx, by = bx.to(device), by.to(device)
        outputs = model(bx)
        loss = criterion(outputs, by)
        total_loss += loss.item() * bx.size(0)
        preds = outputs.argmax(1)
        correct += (preds == by).sum().item()
        total += bx.size(0)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(by.cpu().numpy())
    return (total_loss / total, correct / total,
            np.array(all_preds), np.array(all_labels))


def train_mlp(model, train_loader, val_loader, criterion, optimizer, scheduler,
              device, epochs=150, patience=20):
    history = {"train_loss": [], "train_acc": [],
               "val_loss": [], "val_acc": []}
    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0

    for epoch in range(1, epochs + 1):
        train_loss, train_acc = train_epoch(
            model, train_loader, optimizer, criterion, device)
        val_loss, val_acc, _, _ = evaluate(
            model, val_loader, criterion, device)

        if scheduler:
            scheduler.step(val_loss)

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone()
                          for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if epoch % 10 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{epochs} | "
                  f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | "
                  f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")

        if patience_counter >= patience:
            print(f"  [STOP] Early stopping at epoch {epoch}")
            break

    if best_state:
        model.load_state_dict(best_state)
    return history


# ============================================================
# 8. 训练
# ============================================================
print("\n" + "=" * 60)
print("6. 开始训练")
print("=" * 60)

if USE_TABNET:
    # ---------- TabNet 方案 ----------
    tabnet = TabNetClassifier(
        cat_idxs=cat_idxs,
        cat_dims=cat_dims,
        cat_emb_dim=8,
        n_d=32,
        n_a=32,
        n_steps=5,
        gamma=1.5,
        n_independent=3,
        n_shared=2,
        optimizer_fn=torch.optim.Adam,
        optimizer_params=dict(lr=2e-3),
        scheduler_fn=torch.optim.lr_scheduler.ReduceLROnPlateau,
        scheduler_params=dict(mode="min", patience=5, factor=0.5),
        mask_type="sparsemax",
        seed=42,
        verbose=0,
    )

    print("  训练 TabNet 8分类模型...")

    tabnet.fit(
        X_train=X_train,
        y_train=y_train,
        eval_set=[(X_val, y_val)],
        eval_name=["val"],
        eval_metric=["accuracy", "logloss"],
        max_epochs=100,
        patience=15,
        batch_size=BATCH_SIZE,
        virtual_batch_size=min(128, len(X_train) // 8),
        num_workers=0,
        drop_last=False,
    )

    y_pred = tabnet.predict(X_test)
    y_true = y_test

    hist = tabnet.history.history if hasattr(tabnet.history, "history") else {}
    history = {
        "train_loss": hist.get("loss", []),
        "train_acc": [],
        "val_loss": hist.get("val_logloss", []),
        "val_acc": hist.get("val_accuracy", []),
    }

    model_path = os.path.join(MODEL_DIR, "tabnet_employer_type.pth")
    tabnet.save_model(model_path)
    model_path = model_path + ".zip"
    trained_model = tabnet
    MODEL_TYPE = "TabNet (8分类)"

else:
    # ---------- EmbeddingMLP 备选方案 ----------
    model = EmbeddingMLP(
        cat_dims=cat_dims,
        embedding_dim=16,
        hidden_dims=[256, 128, 64, 32],
        num_classes=num_classes,
        dropout=0.3,
    ).to(DEVICE)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  EmbeddingMLP 参数量: {n_params:,}")

    optimizer = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=8)

    print("  训练 EmbeddingMLP 8分类模型...")
    history = train_mlp(
        model, train_loader, val_loader, criterion, optimizer, scheduler,
        DEVICE, epochs=150, patience=20)

    test_loss, test_acc, y_pred, y_true = evaluate(
        model, test_loader, criterion, DEVICE)

    model_path = os.path.join(MODEL_DIR, "tabnet_employer_type.pth")
    torch.save({
        "model_state_dict": model.state_dict(),
        "cat_dims": cat_dims,
        "hidden_dims": [256, 128, 64, 32],
        "embedding_dim": 16,
        "num_classes": num_classes,
        "encoders": encoders,
        "target_encoder": target_le,
        "history": history,
        "class_names": [str(c) for c in target_le.classes_],
    }, model_path)
    trained_model = model
    MODEL_TYPE = "EmbeddingMLP (8分类)"

print(f"\n  [OK] 模型已保存至: {model_path}")


# ============================================================
# 9. 评估指标
# ============================================================
print("\n" + "=" * 60)
print("7. 评估指标")
print("=" * 60)

class_names = [str(c) for c in target_le.classes_]

accuracy  = accuracy_score(y_true, y_pred)
precision = precision_score(y_true, y_pred, average="weighted", zero_division=0)
recall    = recall_score(y_true, y_pred, average="weighted", zero_division=0)
f1        = f1_score(y_true, y_pred, average="weighted", zero_division=0)
cm        = confusion_matrix(y_true, y_pred)

print(f"\n  {'指标':<26} {'数值'}")
print(f"  {'-' * 38}")
print(f"  {'准确率 (Accuracy)':<26} {accuracy:.4f}  ({accuracy:.2%})")
print(f"  {'加权精确率 (Precision)':<26} {precision:.4f}")
print(f"  {'加权召回率 (Recall)':<26} {recall:.4f}")
print(f"  {'加权 F1-Score':<26} {f1:.4f}")

# 每个类别的 precision/recall/f1
per_class = classification_report(
    y_true, y_pred, target_names=class_names, digits=4, zero_division=0
)
print(f"\n  详细分类报告:")
for line in per_class.split("\n"):
    print(f"  {line}")

# 混淆矩阵
print(f"\n  混淆矩阵 (8×8):")
header = "           " + " ".join([f"{n[:4]:>6}" for n in class_names])
print(f"  {header}")
for i, cls in enumerate(class_names):
    row = " ".join([f"{cm[i,j]:>6}" for j in range(num_classes)])
    print(f"  {cls[:8]:>8}: {row}")


# ============================================================
# 10. 可视化
# ============================================================
print("\n" + "=" * 60)
print("8. 生成可视化")
print("=" * 60)


def plot_confusion_matrix(cm, class_names, save_path):
    """绘制 8×8 混淆矩阵热力图"""
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.matshow(cm, cmap="YlOrRd", alpha=0.9)

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]),
                    ha="center", va="center",
                    fontsize=10, fontweight="bold",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")

    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, fontsize=9, rotation=45, ha="left", rotation_mode="anchor")
    ax.set_yticklabels(class_names, fontsize=9)
    ax.set_xlabel("预测标签", fontsize=13, labelpad=10)
    ax.set_ylabel("真实标签", fontsize=13)
    ax.set_title(f"混淆矩阵 — {MODEL_TYPE} — 用人单位性质预测",
                 fontsize=14, fontweight="bold", pad=15)
    ax.tick_params(axis='x', which='major', pad=3)

    plt.colorbar(im, ax=ax, shrink=0.8)
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 混淆矩阵 -> {save_path}")


cm_path = os.path.join(OUTPUT_DIR, "tabnet_cm.png")
plot_confusion_matrix(cm, class_names, cm_path)


def plot_loss_curves(history, save_path):
    """绘制训练/验证损失和准确率曲线"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    epochs = range(1, len(history["train_loss"]) + 1)

    ax = axes[0]
    ax.plot(epochs, history["train_loss"], "b-", linewidth=1.5,
            alpha=0.8, label="训练损失")
    if history.get("val_loss") and len(history["val_loss"]) > 0:
        ax.plot(epochs, history["val_loss"], "r-", linewidth=1.5,
                alpha=0.8, label="验证损失")
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Loss", fontsize=12)
    ax.set_title("损失曲线", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    has_train_acc = history.get("train_acc") and len(history["train_acc"]) > 0
    has_val_acc = history.get("val_acc") and len(history["val_acc"]) > 0
    if has_train_acc:
        ax.plot(epochs, history["train_acc"], "b-", linewidth=1.5,
                alpha=0.8, label="训练准确率")
    if has_val_acc:
        ax.plot(epochs, history["val_acc"], "r-", linewidth=1.5,
                alpha=0.8, label="验证准确率")
    if not has_train_acc and not has_val_acc:
        ax.text(0.5, 0.5, "无准确率历史\n(TabNet 仅记录验证损失)",
                ha="center", va="center", transform=ax.transAxes)
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Accuracy", fontsize=12)
    ax.set_title("准确率曲线", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] 损失曲线 -> {save_path}")


loss_path = os.path.join(OUTPUT_DIR, "tabnet_loss.png")
plot_loss_curves(history, loss_path)


# ============================================================
# 11. 错误分类样本分析
# ============================================================
print("\n" + "=" * 60)
print("9. 错误分类样本分析")
print("=" * 60)

df_test = df.iloc[test_idx].copy()
df_test["true_label"] = y_true
df_test["pred_label"] = y_pred

errors = df_test[df_test["true_label"] != df_test["pred_label"]].copy()
err_rate = len(errors) / len(df_test)
print(f"  错误分类数: {len(errors)} / {len(df_test)}  (错误率: {err_rate:.2%})")

# 每个类别被误判的情况
print(f"\n  各类别误判统计:")
for i, cls in enumerate(class_names):
    total_cls = (df_test["true_label"] == i).sum()
    wrong_cls = (errors["true_label"] == i).sum()
    if total_cls > 0:
        # 被误判为什么
        wrong_to = errors[errors["true_label"] == i]["pred_label"].value_counts()
        top_wrong = ", ".join([f"{class_names[int(idx)]}({cnt})"
                              for idx, cnt in wrong_to.head(3).items()])
        print(f"    {cls}: {wrong_cls}/{total_cls} 误判, 主要误判为→ {top_wrong}")

# 打印前 15 条错误样本
print(f"\n  {'#':<4} {'性别':<6} {'学历':<6} {'专业':<14} {'生源地':<14} {'真实':<10} {'预测':<10}")
print(f"  {'-' * 78}")
for i, (_, row) in enumerate(errors.head(15).iterrows()):
    true_cls_name = class_names[int(row["true_label"])]
    pred_cls_name = class_names[int(row["pred_label"])]
    print(f"  {i+1:<4} {str(row['性别']):<6} {str(row['education_level']):<6} "
          f"{str(row['专业名称'])[:12]:<14} {str(row['province'])[:12]:<14} "
          f"{true_cls_name:<10} {pred_cls_name:<10}")


# ============================================================
# 12. 保存评估指标 JSON（供仪表盘使用）
# ============================================================
print("\n" + "=" * 60)
print("10. 保存评估指标")
print("=" * 60)

error_samples = []
for _, row in errors.head(20).iterrows():
    error_samples.append({
        "gender": str(row['性别']),
        "education": str(row['education_level']),
        "major": str(row['专业名称']),
        "province": str(row['province']),
        "true_label": class_names[int(row["true_label"])],
        "pred_label": class_names[int(row["pred_label"])],
    })

# 各类别被误判的统计
error_by_class = {}
for i, cls in enumerate(class_names):
    total_cls = int((df_test["true_label"] == i).sum())
    wrong_cls = int((errors["true_label"] == i).sum())
    if total_cls > 0:
        wrong_to = errors[errors["true_label"] == i]["pred_label"].value_counts()
        error_by_class[cls] = {
            "total": total_cls,
            "wrong": wrong_cls,
            "rate": round(wrong_cls / total_cls, 4),
            "most_confused_with": [
                {"class": class_names[int(idx)], "count": int(cnt)}
                for idx, cnt in wrong_to.head(3).items()
            ]
        }

metrics_data = {
    "model_type": MODEL_TYPE,
    "device": str(DEVICE),
    "task": "用人单位性质预测（8分类）",
    "features": feature_cols,
    "cat_dims": cat_dims,
    "num_classes": num_classes,
    "class_names": class_names,
    "data_split": {"train": int(len(X_train)), "val": int(len(X_val)), "test": int(len(X_test))},
    "class_distribution": {str(k): int(v) for k, v in df["employer_type"].value_counts().items()},
    "class_weights": {str(i): round(float(w), 4) for i, w in enumerate(class_weights)},
    "metrics": {
        "accuracy": round(float(accuracy), 4),
        "precision_weighted": round(float(precision), 4),
        "recall_weighted": round(float(recall), 4),
        "f1_weighted": round(float(f1), 4),
    },
    "confusion_matrix": cm.tolist(),
    "confusion_labels": class_names,
    "error_analysis": {
        "total_errors": int(len(errors)),
        "total_test": int(len(df_test)),
        "error_rate": round(float(err_rate), 4),
        "error_samples": error_samples,
        "error_by_class": error_by_class,
    },
}

metrics_json_path = os.path.join(BASE_DIR, "output", "ml_metrics.json")
with open(metrics_json_path, 'w', encoding='utf-8') as f:
    json.dump(metrics_data, f, ensure_ascii=False, indent=2)
print(f"  [OK] 评估指标已保存: {metrics_json_path}")


# ============================================================
# 13. 总结
# ============================================================
print("\n" + "=" * 60)
print("11. 任务总结")
print("=" * 60)
print(f"  任务:           用人单位性质预测（8分类）")
print(f"  模型类型:        {MODEL_TYPE}")
print(f"  使用设备:        {DEVICE}")
print(f"  特征列:          {feature_cols}")
print(f"  各类别数:        {cat_dims}")
print(f"  目标类别:        {num_classes} 类")
print(f"  数据划分:        训练 {len(X_train)} / 验证 {len(X_val)} / 测试 {len(X_test)}")
print(f"  测试准确率:      {accuracy:.4f}  ({accuracy:.2%})")
print(f"  加权 F1-Score:   {f1:.4f}")
print(f"  混淆矩阵保存:    {cm_path}")
print(f"  损失曲线保存:    {loss_path}")
print(f"  模型保存路径:    {model_path}")
print(f"  评估JSON保存:    {metrics_json_path}")
print(f"  错误分类样本:    {len(errors)}/{len(df_test)}")
print(f"\n  [OK] 用人单位性质预测任务完成!")
