# 安裝問題修復指南

## 問題說明
您遇到的錯誤是因為：
1. 使用系統層級 Python（C:\Python312）而非虛擬環境
2. Windows 權限限制導致無法寫入執行檔
3. 可能有損壞的套件安裝

## 解決方案

### 方案 1：使用虛擬環境（推薦）

1. **開啟命令提示字元（CMD）或 PowerShell**

2. **切換到專案目錄**：
   ```cmd
   cd /d D:\user\Desktop\Schedule\clinic-scheduler
   ```

3. **建立虛擬環境**：
   ```cmd
   python -m venv venv
   ```

4. **啟動虛擬環境**：
   ```cmd
   venv\Scripts\activate
   ```

5. **升級 pip**：
   ```cmd
   python -m pip install --upgrade pip
   ```

6. **安裝套件**：
   ```cmd
   pip install -r requirements.txt
   ```

### 方案 2：使用管理員權限

1. **以管理員身份開啟命令提示字元**：
   - 在開始功能表搜尋 "cmd"
   - 右鍵點擊「命令提示字元」
   - 選擇「以系統管理員身分執行」

2. **切換到專案目錄並安裝**：
   ```cmd
   cd /d D:\user\Desktop\Schedule\clinic-scheduler
   pip install -r requirements.txt
   ```

### 方案 3：使用 --user 參數（不需管理員權限）

```cmd
pip install --user -r requirements.txt
```

### 方案 4：清理並重新安裝

1. **清理損壞的套件**：
   ```cmd
   pip cache purge
   ```

2. **移除有問題的 gunicorn**：
   ```cmd
   pip uninstall -y gunicorn
   ```

3. **重新安裝**：
   ```cmd
   pip install --force-reinstall -r requirements.txt
   ```

## 驗證安裝

安裝完成後，執行以下命令確認：

```cmd
python -c "import flask; import pandas; import numpy; print('核心套件安裝成功！')"
```

## 執行應用程式

如果使用虛擬環境，確保已啟動：
```cmd
venv\Scripts\activate
python app.py
```

## 額外建議

### 如果仍有問題，可建立新的簡化版 requirements.txt：

建立 `requirements-minimal.txt`：
```
Flask>=2.3.2
pandas>=2.0.3
numpy>=1.24.3
```

然後安裝：
```cmd
pip install -r requirements-minimal.txt
```

對於部署，可以稍後再安裝 gunicorn：
```cmd
pip install gunicorn
```