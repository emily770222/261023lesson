# docs/ 與 scripts/ 程式異味檢查報告

檢查日期：2026-10-23。依 Issue #3 的 TDD 與可重現要求執行；本次檢查只讀取程式與文件，不修改既有分析程式。儲存庫目前沒有 `scripts/` 目錄，因此該範圍以 0 個檔案記錄。

## 1. 各項警告總數

| 規則/工具 | 警告總數 | 結果 |
|---|---:|---|
| ESLint（JavaScript） | 0 | `docs/` 無 JavaScript；設定檔本身無警告 |
| jscpd 重複碼 | 0 | 目標範圍沒有可分析的程式檔 |
| Knip 未使用匯出/檔案 | 未產生結果 | 專案沒有 JavaScript entry point，Knip JSON 未建立 |
| `scripts/` 目錄存在性 | 1 | 目錄不存在，無法執行腳本專屬檢查 |

## 2. 重複率與重複片段位置

在 `docs/`（1 個 Markdown 檔）與不存在的 `scripts/` 範圍內，沒有偵測到重複程式片段；重複率為 **0%（0/0 個可比較程式 token）**。因此沒有重複片段位置可列出。

## 3. 未使用的檔案與函式

`docs/` 沒有函式；`scripts/` 不存在。Knip 未能產生可用結果，故沒有工具確認的未使用檔案或函式（0 個已確認）。`src/ai4i/` 的 Python 函式不屬於本次 `docs/` 與 `scripts/` 目標範圍，未將其推定為未使用。

## 4. 「前端推論」相關程式

在 `docs/` 與 `scripts/` 內搜尋「前端」「推論」「frontend」「inference」及相關預測詞，結果為 **0 行、0 個函式**。文件中的 `Predictive Maintenance` 是資料集名稱，不屬於前端推論程式。

## 驗證紀錄

- `npm run check:all:report`：指令完成；ESLint 結果為 0 警告。jscpd/Knip 因目標範圍沒有可分析 JavaScript 而沒有產出有效結果。
- `pytest tests/test_static_page.py`：先以測試確認首頁連結與分析頁需求，初次執行按預期失敗（頁面尚未建立），建立頁面後通過。
- 全套 `pytest`：13 通過、8 個錯誤；錯誤均發生在既有測試的 `tmp_path` fixture，原因是執行環境的暫存目錄無法建立 pytest 編號目錄，並非本次頁面變更造成。

## 來源需求

- Issue #3：要求所有資料、模型推論與靜態網站轉換腳本採 TDD。
- Issue #4：要求資料治理可重現、測試先行與單一命令驗證。
