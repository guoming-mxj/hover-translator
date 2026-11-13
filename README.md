# 全局悬停翻译器（Hover Translator）

鼠标在屏幕**任意位置**（浏览器网页、记事本、Office、PDF、图片、软件界面…）
的英文单词/短语上悬停约 0.5 秒，自动弹出中文释义，点击 🔊 可播放英文发音。

## 工作原理

| 场景 | 取词方式 |
|---|---|
| 可选中文本（Chrome/Edge、记事本、Office、资源管理器等） | Windows UI Automation（UIA）直接取词，准确、快、离线 |
| 不可选中文本（图片、游戏、自绘界面、PDF 渲染区） | 鼠标周围截屏 + RapidOCR（PaddleOCR 模型，ONNX 推理，纯本地） |

- **翻译**：默认必应（Bing）网页接口（无需 API Key，句子质量好），
  自动失败重试 MyMemory（单词）；结果本地缓存（`cache.json`）。
  也支持 Argos Translate 完全离线神经翻译。
- **发音**：默认 pyttsx3 调用 Windows 自带 SAPI 语音（完全离线）；
  可选 edge-tts（联网，嗓音更自然）。
- **弹窗**：Python 自带 tkinter，无边框置顶，无额外 GUI 依赖。

## 安装

```powershell
pip install -r requirements.txt
```

> OCR 引擎用 RapidOCR，**不需要安装 Tesseract**。首次 OCR 时会加载模型（约 1~2 秒），之后很快。

## 运行

```powershell
python main.py
```

启动后保持窗口开着，鼠标悬停英文即可翻译。

- `Esc`：关闭当前翻译弹窗
- 鼠标点击任意处：收起弹窗
- 退出：关闭运行 main.py 的控制台窗口

## 配置（config.py）

| 配置项 | 说明 |
|---|---|
| `HOVER_DELAY` | 悬停触发时间（秒），默认 0.45 |
| `REQUIRE_MODIFIER` / `MODIFIER_KEY` | 设 True 则需按住 Ctrl 才翻译，防误触 |
| `ENABLE_OCR_FALLBACK` | 是否开启截屏 OCR 兜底 |
| `TRANSLATE_ENGINE` | `bing` / `mymemory` / `offline_argos` |
| `TTS_ENGINE` | `sapi`（离线）/ `edge`（联网自然） |

## 完全离线方案

1. 翻译：`pip install argostranslate`，配置 `TRANSLATE_ENGINE="offline_argos"`，
   首次运行会自动下载 en→zh 语言包（约 50MB，下载后断网可用）。
2. 发音：保持 `TTS_ENGINE="sapi"`（Windows 自带，无需安装）。
3. 取词：UIA + RapidOCR 本身都是本地的。

## 系统托盘

程序以托盘方式常驻（无控制台黑窗）。右键右下角托盘图标可：

- **暂停/恢复翻译**（暂停时图标变灰）
- 开关 **OCR 取词**（图片/游戏兜底）
- 开关 **显示音标**
- **退出**

## 音标

单词悬停时，原文右侧会显示 IPA 音标（美音优先，可在 config.py 的
`PHONETIC_PREFER` 改为 `"uk"`）。音标来自免费词典 API，仅对单词有效；
短语/句子或离线时自动隐藏，不影响翻译。

## 打包成 exe

已提供打包脚本（见 `build_exe.ps1`），等价于：

```powershell
python -m PyInstaller --noconfirm --clean --windowed --name HoverTranslator `
  --collect-all rapidocr_onnxruntime --collect-all pystray --collect-all PIL `
  --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 main.py
```

产物在 `dist\HoverTranslator\HoverTranslator.exe`（文件夹形式，约 670MB，
含 OCR 模型；双击即可运行，无需安装 Python）。

> 想要单个 exe 文件，在命令里加 `-F`；但每次启动需解压模型、启动较慢，
> 且部分杀软易误报，一般推荐文件夹形式。

## 已知限制

- UIA 取词在部分 Electron / Qt / 自绘程序中可能拿不到文本，此时自动走 OCR；
  OCR 只识别鼠标周围一小块区域，适合单词和短行。
- 有道免费接口仅适合个人低频使用；高频使用建议申请官方 Key 或切换离线引擎。
- 长段落悬停时会智能选取鼠标附近的一个实词；翻译整段建议先选词（本工具定位是"查词"）。
