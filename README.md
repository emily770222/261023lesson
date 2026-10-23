# 261023lesson

課程練習：Iris 資料探索、PCA 3D 視覺化、類神經網路分類與小論文（Issue #2）。

## 快速開始

參考環境為 Colab Python 3.13；完整直接依賴版本記錄於 `requirements.txt`。
全新虛擬環境驗證所使用的直接與間接依賴，另鎖定於 `requirements-lock.txt`，可用它替換下方的 requirements 安裝命令。
不需要 GPU、API key 或外部資料下載；Iris 來自 scikit-learn 隨套件附帶的修正版。

```bash
python -m venv .venv
# Linux / Colab shell
source .venv/bin/activate
# Windows PowerShell 改用：.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Debian/Ubuntu/Colab 另安裝 PDF 所需中文字型（Colab 可省略 sudo）
sudo apt-get update
sudo apt-get install -y fonts-arphic-uming
python -m pytest tests -q
python iris_study.py
python make_report.py
```

在 Colab 中執行 shell 指令時，請使用 `!python ...` 或 `%%bash` 儲存格。
Windows 使用系統微軟正黑體。其他系統請設定 `IRIS_REPORT_FONT` 指向支援繁體中文的 TrueType 字型。PDF 會嵌入字型子集，避免閱讀器替代字型造成亂碼。
若需完整隔離驗證，可直接使用 `.venv/bin/python`，避免依賴 shell 啟用狀態。
Windows sandbox 若無法使用預設暫存目錄，可在 pytest 加上 `--basetemp=.test-tmp-local`。

## 資料與方法

- `data/iris.csv`：150 筆、4 個公分單位的測量特徵；`sample_id` 為來源列編號，不輸入模型；`target`／`species` 為標籤。
- 三類別為 setosa、versicolor、virginica，各 50 筆。
- 缺失值、重複觀測及 1.5 IQR 標記見 `results/audit.json`；保留全部原始資料，不自動刪除離群點。
- 相同特徵向量作為同一群組，再固定種子 42 分層切分：訓練 96、驗證 24、測試 30 筆。
- 標準化僅 fit 訓練資料。全資料 PCA 只供描述性視覺化，不作為神經網路輸入。
- 模型為 MLP 4→16→8→3，ReLU、softmax、Adam、learning rate 0.01、L2 alpha 0.0001、batch size 16。
- 最多 500 epochs，驗證 cross-entropy 40 輪未改善即停止，恢復最佳 checkpoint。模型設定在最終測試前固定。
- 測試集只在 checkpoint 確定後評估；不以測試結果挑選種子、輪次或參數。

## 成果位置

| 路徑 | 內容 |
| --- | --- |
| `data/metadata.json` | 資料來源、取得時間、SHA256、版本、欄位及標籤對照 |
| `results/describe.csv`, `class_means.csv`, `correlation.csv` | 描述統計、各品種平均與相關矩陣 |
| `results/splits.csv` | 每筆樣本的切分歸屬 |
| `results/pca_scores.csv`, `pca_loadings.csv` | 3D 主成分分數與負荷量 |
| `results/history.csv` | 每輪訓練／驗證 loss、accuracy |
| `results/metrics.json` | 指標、混淆矩陣、選定輪次、模型設定及執行版本 |
| `results/predictions.csv`, `misclassified.csv` | 測試預測、機率與錯誤案例 |
| `figures/` | 分布與相關性、PCA 3D、訓練曲線、混淆矩陣及類別指標 PNG |
| `reports/iris-paper.md`, `iris-paper.pdf` | 可編輯小論文及 PDF |
| `results/tdd/`, `TDD_LOG.md` | 紅燈／綠燈測試證據與開發流程 |

報告只讀取已產生的實驗檔案，所有數值均由結果檔帶入。`python iris_study.py --output other-run` 可將新實驗寫到別的目錄，再以 `python make_report.py --root other-run` 產生對應報告。

## 測試與重現範圍

10 項 pytest 測試涵蓋 CSV round trip、資料品質檢查、分組分層切分、訓練專屬標準化、PCA、無效輸入、模型決定性、測試資料隔離、評估一致性及輸出產物。
固定資料、切分與依賴版本可重現數值；不同 OS／BLAS 或套件版本可能有微小浮點差異。時間戳記及 PDF 建立日期不保證逐位元相同。
測試沒有以預設高準確率作為通過條件，避免將實驗結果當作既定事實。

本實驗僅為單次小樣本教學研究，不宣稱模型最優，也未完成外部驗證或部署評估。

## 本次參考結果

- 測試 30 筆中正確 28 筆：accuracy 93.33%，macro F1 0.9333；多數類基準 33.33%。
- PCA 三成分累積解釋變異 99.48%。
- 訓練共 56 輪，驗證集選定第 16 輪；setosa 10/10 正確，另兩類各 9/10。
- Colab 與全新虛擬環境皆通過 10 項測試；重跑的混淆矩陣、最佳輪次一致，cross-entropy 差異小於 1e-10。
- 六頁繁體中文 PDF 已嵌入中文字型，完成逐頁圖像檢查與文字／數值一致性檢查。

## 參考資料

- Fisher, R. (1936), Iris, UCI：https://doi.org/10.24432/C56C76
- scikit-learn load_iris：https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_iris.html
- PCA：https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html
- MLPClassifier：https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html
