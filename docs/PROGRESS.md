# ImageProcessor 开发进度

_文档版本：v1.0_  
_最后更新：2026-07-02_

---

## 已完成功能

### 1. 环境与依赖

- [x] 创建 `requirements.txt`，包含项目所有依赖
  - Pillow, rembg[cpu], opencv-python, numpy, PySide6
- [x] 创建本地 Python 虚拟环境 `.venv` 并安装依赖
- [x] 验证 rembg CPU 后端可正常加载模型

### 2. 项目结构

- [x] 按 README 设计建立 `image_processor/` 模块化包结构
  - `core/`：图像处理引擎、批量处理
  - `gui/`：主窗口、画布、工具栏、属性面板
  - `models/`：ImageItem 数据模型
  - `utils/`：通用工具函数
- [x] 新增程序入口 `main.py` 和 `image_processor/app.py`

### 3. 核心图像引擎 (`image_processor/core/image_engine.py`)

- [x] 智能抠图（rembg）支持模型选择、Alpha Matting、裁剪透明边缘
- [x] 多图层合并
- [x] 等比缩放，支持按宽度/高度/百分比缩放，可选插值算法
- [x] 裁剪、旋转、翻转
- [x] 多格式导出（PNG/JPEG/WebP/BMP/TIFF），JPEG/WebP 支持质量调节
- [x] 内容感知擦除（OpenCV inpainting），支持 NS 和 TELEA 算法
- [x] 棋盘格背景生成（可自定义格子大小和颜色）
- [x] 精灵图生成：支持自定义/自动列数、间距、内边距、JSON 元数据导出

### 4. 批量处理 (`image_processor/core/batch_processor.py`)

- [x] 批量抠图（线程池，不阻塞 UI）
- [x] 批量缩放导出
- [x] 支持取消操作和进度回调

### 5. CLI 工具（已重构为使用核心模块）

- [x] `img_matting.py`：单图抠图，支持所有 rembg 参数
- [x] `img_merge.py`：多图层合并
- [x] `img_sprite.py`：按文件夹生成精灵图，自动生成 JSON 配置
- [x] `img_inpaint.py`：内容感知擦除，支持 NS/TELEA 算法

### 6. GUI 骨架

- [x] 主窗口（`main_window.py`）支持菜单、状态栏、拖拽上传、撤销/重做
- [x] 工具栏（`toolbar.py`）切换工具：抠图 / 缩放 / 裁剪 / 精灵图 / 调色
- [x] 画布（`canvas.py`）使用棋盘格背景，支持滚轮缩放
- [x] 属性面板：
  - 抠图面板（`matting_panel.py`）
  - 缩放面板（`resize_panel.py`）
  - 裁剪/旋转/翻转面板（`crop_panel.py`）
  - 内容感知擦除面板（`inpaint_panel.py`）
  - 橡皮擦/画笔面板（`brush_panel.py`），支持在画布上涂抹擦除或恢复
  - 精灵图面板（`sprite_panel.py`）
  - 调色面板（`adjust_panel.py`）
- [x] 批量处理对话框（`batch_dialog.py`），支持批量抠图和批量缩放，带进度条和日志
- [x] 线程安全的抠图后台任务（`matting_worker.py`），进度信号更新到主线程 UI
- [x] 最近文件菜单（`recent_files.py`），持久化到 `~/.image_processor/recent_files.json`
- [x] 原图/处理后对比对话框（`compare_dialog.py`）
- [x] 滑动对比组件（`slider_compare.py`）
- [x] 项目保存/打开（`project_manager.py`、`project.py`），保存图片和历史栈
- [x] 深色/浅色主题切换（`themes.py`）

### 7. 测试

- [x] 使用 `@images` 测试 CLI 脚本（抠图、合并、精灵图、内容感知擦除），结果正常输出到 `output/`
- [x] 使用核心引擎进行加载、缩放、合并、精灵图、批量缩放、批量抠图、裁剪/旋转、内容感知擦除测试
- [x] 橡皮擦/画笔逻辑测试（涂抹预览、应用、撤销/重做）
- [x] 滑动对比组件实例化测试
- [x] 项目保存/加载测试（含真实图片和历史栈）
- [x] PyInstaller 本地打包成功，生成 `ImageProcessor-macOS.zip`（约 317 MB）
- [x] GitHub Release `v1.0.0` 发布成功
- [x] 所有 GUI 模块均可成功导入，无语法错误
- [x] 通过 ReadLints 检查，无 lint 错误

---

## 未完成/待开发功能

### 高优先级（P0/P1）

- [x] 历史记录与撤销/重做（`HistoryManager`）
- [x] 批量处理对话框，带进度条和取消按钮
- [x] 图片导航（上一张/下一张、缩略图列表）
- [x] 画布缩放比例显示和重置按钮
- [x] 非阻塞 Toast 错误提示
- [x] 抠图模型首次下载时的加载提示

### 中优先级（P2）

- [x] 橡皮擦与画笔手动修复
- [x] 图片对比（分屏，已支持原图/处理后对比）
- [x] 图片对比（滑动对比）
- [x] 项目保存（保存当前编辑状态）

### 低优先级（P3）

- [x] 性能优化（历史栈已限制为 20 条、大图片处理依赖核心引擎）
- [x] 使用 PyInstaller 打包为独立应用
- [x] 发布 GitHub Release：[`v1.0.0`](https://github.com/Cary123/ImageProcessor/releases/tag/v1.0.0)

---

## 发布说明

- GitHub 仓库：`https://github.com/Cary123/ImageProcessor`
- Release 页面：`https://github.com/Cary123/ImageProcessor/releases/tag/v1.0.0`
- 下载资产：`ImageProcessor-macOS.zip`（macOS arm64 应用包）

---

## 测试文件位置

- 测试图片：`/Users/josephgao/Documents/ImageProcessor/images/`
- 测试输出：`/Users/josephgao/Documents/ImageProcessor/output/`
- 虚拟环境：`/Users/josephgao/Documents/ImageProcessor/.venv/`
