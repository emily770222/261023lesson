# AI4I 2020 預測性維護分析

本專案分析 [AI4I 2020 Predictive Maintenance Dataset](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset)，建立可重現的資料治理、EDA、特徵工程、模型訓練、解釋性與報告流程。總規劃見 [Issue #3](https://github.com/emily770222/261023lesson/issues/3)。

## 目前進度

- [x] [#4 資料治理與資料字典](https://github.com/emily770222/261023lesson/issues/4)
- [ ] [#5 EDA 與洩漏檢查](https://github.com/emily770222/261023lesson/issues/5)
- [ ] [#6 特徵工程與前處理 Pipeline](https://github.com/emily770222/261023lesson/issues/6)
- [ ] [#7 模型訓練、不平衡處理與成本導向門檻](https://github.com/emily770222/261023lesson/issues/7)
- [ ] [#8 模型解釋性與誤判分析](https://github.com/emily770222/261023lesson/issues/8)
- [ ] [#9 圖表、小論文與靜態報告](https://github.com/emily770222/261023lesson/issues/9)
- [ ] [#10 端到端 Pipeline、CI 與發佈](https://github.com/emily770222/261023lesson/issues/10)

## 資料集

- 原始檔：`data/raw/ai4i2020.csv`（10,000 列 × 14 欄）
- 故障率：3.39%（339 筆）
- SHA-256：`dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e`
- 授權：CC BY 4.0
- 完整欄位、觀測範圍、故障模式定義與已知不一致：見 [`docs/data_dictionary.md`](docs/data_dictionary.md)

資料檔直接納入版本控管（約 510 KB），並以 `data/raw/SHA256SUMS` 驗證完整性。

## 快速開始

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m ai4i.validate_data
pytest
```

Linux/macOS：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m ai4i.validate_data
pytest
```

驗證通過時會輸出摘要，並將完整結果寫入 `reports/data_validation.json`。若資料毀損、schema 變更或 checksum 不符，程式會以非 0 結束碼失敗。

重新下載原始資料（會先驗證 SHA-256，checksum 不符時不寫入）：

```bash
python -m ai4i.download
```

若目標檔已存在但內容不符，程式會拒絕覆蓋；確認要重新下載時加上 `--force`。

## 專案結構

```text
.
├── data/raw/                # 不可變更的原始資料與 checksum
├── docs/                    # 資料字典與方法文件
├── reports/                 # 驗證報告與後續圖表
├── src/ai4i/                # 資料載入、驗證與後續分析程式
├── tests/                   # 自動化測試
├── pyproject.toml
└── README.md
```

## 已知資料特性

- 五種故障模式可同時出現；24 筆有多重模式。
- 9 筆 `Machine failure=1` 但五種模式皆為 0。
- 18 筆至少一個模式為 1，但 `Machine failure=0`。
- 原始資料保留上述不一致，不進行人工修正。
- `Product ID` 在本檔中全部唯一；資料無時間戳，不能直接做時間序列特徵。
- UCI 文字說明中的部分數字與 CSV 不一致，本專案以 CSV 為準。

## 引用

> AI4I 2020 Predictive Maintenance Dataset [Dataset]. (2020). UCI Machine Learning Repository. https://doi.org/10.24432/C5HS5C.

## 授權

資料集採用 CC BY 4.0。使用或改作時請保留上述出處與引用資訊。
