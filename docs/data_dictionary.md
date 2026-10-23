# AI4I 2020 資料字典與資料治理紀錄

本文件記錄 `data/raw/ai4i2020.csv` 的來源、欄位定義、觀測範圍、品質檢查結果與已知限制。原始檔視為不可變更資產；所有異常與不一致僅記錄，不直接修改。

## 1. 資料集概述

| 項目 | 內容 |
|---|---|
| 名稱 | AI4I 2020 Predictive Maintenance Dataset |
| 資料型態 | 合成（synthetic）預測性維護資料 |
| 筆數 × 欄數 | 10,000 × 14 |
| 目標欄位 | `Machine failure`（0/1） |
| 故障率 | 339 / 10,000 = 3.39% |
| 缺失值 | 0 |
| 重複列 | 0 |
| 時間資訊 | 無時間戳；`UDI` 僅為流水號 |
| 機器 ID | 無獨立機器 ID；`Product ID` 在本檔中全部唯一 |

## 2. 來源、授權與版本

| 項目 | 內容 |
|---|---|
| 官方頁面 | https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset |
| 原始 CSV | https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv |
| 取得日期 | 2026-10-23 |
| 授權 | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| DOI | 10.24432/C5HS5C |
| 本專案檔案 | `data/raw/ai4i2020.csv` |
| SHA-256 | `dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e` |
| checksum 檔 | `data/raw/SHA256SUMS` |

建議引用：

> AI4I 2020 Predictive Maintenance Dataset [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C.

版本控管決策：CSV 約 510 KB，直接納入 Git 版本控管，並以 SHA-256 驗證完整性；不另外使用 DVC 或 Git LFS。`.gitattributes` 將此檔標記為 `-text`，避免 Git 轉換 CRLF 造成 checksum 改變。

## 3. 欄位字典

| 欄位 | 型態 | 單位 | 說明 | 本檔觀測值 |
|---|---|---|---|---|
| `UDI` | 整數 | - | 資料列唯一識別碼 | 1–10,000，連續且唯一 |
| `Product ID` | 字串 | - | 產品品質變體與序號，例如 `M14860` | 10,000 個唯一值 |
| `Type` | 類別 | - | 產品品質變體：L（低）、M（中）、H（高） | L=6,000、M=2,997、H=1,003 |
| `Air temperature [K]` | 浮點數 | K | 環境空氣溫度 | 295.3–304.5，平均 300.005 |
| `Process temperature [K]` | 浮點數 | K | 製程溫度 | 305.7–313.8，平均 310.006 |
| `Rotational speed [rpm]` | 整數 | rpm | 轉速 | 1,168–2,886，平均 1,538.776 |
| `Torque [Nm]` | 浮點數 | N·m | 扭矩 | 3.8–76.6，平均 39.987 |
| `Tool wear [min]` | 整數 | min | 刀具累積磨耗時間 | 0–253，平均 107.951 |
| `Machine failure` | 整數 | - | 是否發生任一故障：0=正常、1=故障 | 339 筆故障（3.39%） |
| `TWF` | 整數 | - | Tool Wear Failure，刀具磨耗故障 | 46 筆 |
| `HDF` | 整數 | - | Heat Dissipation Failure，散熱不良故障 | 115 筆 |
| `PWF` | 整數 | - | Power Failure，功率異常故障 | 95 筆 |
| `OSF` | 整數 | - | Overstrain Failure，過載故障 | 98 筆 |
| `RNF` | 整數 | - | Random Failure，隨機故障 | 19 筆 |

### 故障率與型別

| Type | 筆數 | 故障筆數 | 故障率 |
|---|---:|---:|---:|
| L | 6,000 | 235 | 3.92% |
| M | 2,997 | 83 | 2.77% |
| H | 1,003 | 21 | 2.09% |

## 4. 故障模式定義

以下為 UCI 對資料生成規則的說明，用於理解欄位，不建議直接寫成硬性特徵規則，以免與實際標籤不一致。

| 模式 | 定義 |
|---|---|
| `TWF` | 刀具在隨機選定的 200–240 分鐘磨耗時間點被更換或失效。 |
| `HDF` | 製程溫度與空氣溫度差小於 8.6 K，且轉速低於 1,380 rpm。 |
| `PWF` | 功率（扭矩 × 角速度，角速度 = rpm × 2π/60）小於 3,500 W 或大於 9,000 W。 |
| `OSF` | 刀具磨耗 × 扭矩超過門檻：L 為 11,000、M 為 12,000、H 為 13,000 min·N·m。 |
| `RNF` | 每個製程約有 0.1% 的隨機故障機率。 |

`Machine failure` 理論上為五種模式的聯集（任一模式成立即為 1）。

## 5. 品質檢查結果

- 維度：10,000 列 × 14 欄。
- 欄位順序與 UCI CSV 一致。
- 缺失值：0。
- 完全重複列：0。
- `UDI`：唯一、連續、範圍 1–10,000。
- `Product ID`：10,000 個唯一值，無重複。
- `Type`：僅包含 L/M/H。
- 目標與五個模式欄位：僅包含 0/1。
- 數值欄位皆在合理物理範圍內。
- 同一列可能同時有多種故障模式：24 筆。

### 已記錄的標籤不一致

本檔存在以下情形，**保留原始資料不修改**：

- 9 筆 `Machine failure=1`，但 `TWF/HDF/PWF/OSF/RNF` 全部為 0。
- 18 筆至少一個故障模式為 1，但 `Machine failure=0`。
- 五個模式合計 373 個旗標，但因 24 筆重複計數，故障列仍為 339 筆。

此外，UCI 文字說明中的部分數字與 CSV 旗標不一致（例如文字提到 TWF 120 次、RNF 5 次，但 CSV 分別為 46 與 19 筆；Type 文字比例為 50/30/20，實際為 60/30/10）。**本專案以 CSV 欄位為唯一資料來源**，並在 EDA 階段進一步量化這些差異的影響。

## 6. 對後續分析的影響

1. 預測 `Machine failure` 時，必須排除 `UDI`、`Product ID`、`TWF`、`HDF`、`PWF`、`OSF`、`RNF`，避免直接洩漏答案。
2. `Product ID` 在本檔中唯一，因此隨機分層切分即可；若未來資料出現重複，應改用 Group 切分。
3. 資料沒有時間戳或機器 ID，無法建立 lag、rolling 或剩餘壽命特徵；此資料不是嚴格的單機時間序列。
4. 類別極度不平衡（3.39%），後續不得以 accuracy 作為主要指標。
5. 標籤不一致與合成資料特性應在誤判分析與結論限制中說明。

## 7. 重現方式

```bash
pip install -e ".[dev]"
python -m ai4i.download   # 重新下載並驗證 SHA-256
python -m ai4i.validate_data
pytest
```

驗證報告輸出於 `reports/data_validation.json`。
