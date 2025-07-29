# 安裝與設定說明

## Python 版本相容性

本專案支援 Python 3.8 以上版本。已測試並確認可在以下版本運行：
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

## 安裝步驟

1. **建立虛擬環境**（建議）：
   ```bash
   python -m venv venv
   ```

2. **啟動虛擬環境**：
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. **安裝相依套件**：
   ```bash
   pip install -r requirements.txt
   ```

## 可能的問題與解決方案

### 問題：AttributeError: module 'pkgutil' has no attribute 'ImpImporter'

**原因**：使用 Python 3.12+ 版本時，某些舊套件不相容。

**解決方案**：
- 已更新 requirements.txt，移除不相容的 zipfile36 套件
- 使用內建的 zipfile 模組替代

### 問題：numpy 或 pandas 安裝失敗

**解決方案**：
1. 確保 pip 是最新版本：
   ```bash
   pip install --upgrade pip
   ```

2. 如果仍有問題，可個別安裝：
   ```bash
   pip install numpy
   pip install pandas
   pip install Flask
   ```

### 問題：在 M1/M2 Mac 上安裝問題

**解決方案**：
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 驗證安裝

安裝完成後，可執行以下命令驗證：

```bash
python -c "import flask; import pandas; import numpy; print('所有套件安裝成功！')"
```

## 執行應用程式

```bash
python app.py
```

應用程式將在 http://localhost:5000 啟動。