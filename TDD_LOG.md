# TDD 開發記錄

本工作採先建立測試、觀察失敗、實作、驗證通過的順序，不是實作完成後才補寫測試。

| 階段 | 紅燈 | 綠燈 |
| --- | --- | --- |
| 資料層 | `test_data.py` 因 `iris_study` 尚不存在而 collection failure | 實作載入、audit、group split、scaler、PCA，6 passed |
| 模型層 | `test_model.py` 因 `fit_model` 尚不存在而 collection failure | 實作固定架構、validation checkpoint 與評估，9 passed |
| 輸出層 | `test_outputs.py` 因 `run_experiment` 尚不存在而 collection failure | 實作 CSV／JSON 與 5 張圖，10 passed |

本機首次綠燈執行遇到 sandbox 暫存資料夾權限錯誤，改用工作目錄內的 pytest `--basetemp` 後完成，未修改測試期望以掩蓋錯誤。

Colab 的專案分支另保留測試先行的獨立 commit：在沒有實作模組時執行全部測試，exit code 2，三個測試模組均因缺少 `iris_study` 而失敗。隨後加入實作，再執行同一測試套件。原始證據見 `results/tdd/colab-red.txt` 與 `colab-green.txt`。

## 有意義的行為驗證

- 修改驗證及測試特徵，不得改變訓練 scaler 的平均值。
- 大幅修改測試特徵與標籤，不得改變模型權重、訓練歷程或選定 epoch。
- 相同特徵向量不得跨 train／validation／test。
- 同一種子重訓的機率必須一致，每列機率和為 1。
- 混淆矩陣及 accuracy 必須與獨立計算及已保存的預測相符。
- 產物測試實際執行流程、讀回 CSV／JSON，檢查 PNG 檔頭及大小。

## Refactor 與驗證

Colab 第一次綠燈嘗試得到 2 failed、8 passed：Pandas 資料複製後的記憶體排列使浮點加總產生約 1e-15 差異，嚴格的隔離不變性測試因此失敗。實作統一 C-order float64 特徵陣列後重跑；未放寬測試容忍度。失敗紀錄保存在 `results/tdd/colab-layout-failure.txt`。

將 JSON 輸出及繪圖集中於共用函式；資料分割、標準化、模型選擇、最終評估保持獨立。文件產生器只讀取實驗產物，避免在論文中手動抄寫不同步的指標。PDF 另經逐頁渲染與視覺檢查。

全新虛擬環境首次重現時，Colab 繼承的 MPLBACKEND 指向該環境未安裝的 inline backend，造成 1 failed、9 passed。繪圖入口在 import matplotlib 前明確設定 Agg，並在產物測試注入不存在的 notebook backend，確保可於無介面環境產圖。原始失敗證據見 `results/tdd/clean-backend-failure.txt`。

PDF 視覺檢查另發現未嵌入的 CID 字型顯示亂碼，改用嵌入的 AR PL UMing TrueType 子集後重新產生與逐頁檢查。

全新隔離虛擬環境的最終重現已完成：10 passed；完整訓練、輸出與 PDF 產生成功，混淆矩陣、最佳 epoch 一致，log loss 差異小於 1e-10。完整套件鎖定在 `requirements-lock.txt`。
