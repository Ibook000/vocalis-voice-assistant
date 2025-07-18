# Vocalis - 轻量化桌面语音助手 🎤

Vocalis是一款简洁高效的桌面语音助手，专为Windows 11环境设计，提供语音交互、AI对话和工具调用功能。

## ✨ 功能特点
- **语音识别**：将语音转换为文本输入
- **文本转语音**：将AI回复转换为自然语音
- **AI对话**：集成大语言模型进行智能对话
- **工具调用**：通过MCP服务器调用各类实用工具
- **模块化设计**：代码结构清晰，易于扩展和维护

## 🚀 快速开始

### 环境要求
- Windows 11
- Python 3.10+
- 虚拟环境（推荐）

### 安装步骤
1. **克隆项目**（如果适用）
   ```bash
   git clone <repository-url>
   cd Vocalis
   ```

2. **创建并激活虚拟环境**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **安装依赖**
   ```powershell
   pip install openai whisper edge-tts websockets python-dotenv
   ```

4. **配置文件**
   - 修改`config.json`设置API密钥和模型参数
   - 配置`mcp.json`添加MCP服务器信息

### 使用方法
1. **启动应用**
   ```powershell
   python main.py
   ```

2. **交互方式**
   - 文本输入：直接在控制台输入文字
   - 语音输入：按指定快捷键开始语音录制
   - 输入`quit`退出程序

## 📁 项目结构
```
Vocalis/
├── ai_chatbot.py      # AI对话和工具调用核心逻辑
├── main.py            # 程序入口
├── text_to_speech.py  # 文本转语音模块
├── voice_to_text.py   # 语音转文本模块
├── config.json        # 应用配置
├── mcp.json           # MCP服务器配置
└── venv/              # Python虚拟环境
```

## 🛠️ 代码实现详解

### 1. 程序入口 (`main.py`) 🚀
负责模块初始化和流程控制，实现语音输入→AI处理→语音输出的完整闭环。

```python:/e:/pycode/Vocalis/main.py
async def main():
    # 初始化文本转语音模块
    tts = TextToSpeech(
        default_voice="zh-TW-HsiaoChenNeural",
        rate="+5%"
    )
    await tts.initialize()
    
    # 初始化AI聊天机器人
    chatbot = MCPClient()
    for server_name in chatbot.mcp_servers.keys():
        await chatbot.connect_to_server(server_name)
    
    # 主交互循环
    while True:
        # 录音并转文本
        transcribed_text = vtt.record_and_transcribe()
        # AI处理
        ai_response = await chatbot.process_query(transcribed_text)
        # 文本转语音
        await tts.synthesize(ai_response)
```

### 2. AI对话与工具调用 (`ai_chatbot.py`) 🤖
核心类`MCPClient`实现大模型交互和MCP工具调用，支持多服务器管理和工具调用标准化。

```python:/e:/pycode/Vocalis/ai_chatbot.py
class MCPClient:
    async def process_query(self, query: str) -> str:
        # 构建工具调用参数
        available_tools = [{
            "type": "function",
            "function": {
                "name": f"{tool['server_name']}_{tool['name']}",
                "description": f"[{tool['server_name']}] {tool['description']}",
                "input_schema": tool['inputSchema']
            }
        } for tool in all_tools]
        
        # 调用大模型并处理工具返回结果
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=available_tools     
        )
```

### 3. 文本转语音模块 (`text_to_speech.py`) 🔊
基于edge-tts实现高质量语音合成，支持自定义语音、语速、音量和音调。

```python:/e:/pycode/Vocalis/text_to_speech.py
class TextToSpeech:
    async def synthesize(self, text: str, voice: Optional[str] = None) -> None:
        # 创建临时文件存储音频
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_filename = temp_file.name
        
        # 使用edge-tts合成语音
        communicate = edge_tts.Communicate(
            text, voice, rate=self.rate, volume=self.volume, pitch=self.pitch
        )
        await communicate.save(temp_filename)
        playsound(temp_filename)
```

### 4. 语音转文本模块 (`voice_to_text.py`) 🎤
基于whisper模型实现语音识别，支持静音检测自动停止录音。

```python:/e:/pycode/Vocalis/voice_to_text.py
class VoiceToTextConverter:
    def __init__(self):
        # 自动检测设备并加载whisper模型
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model("base", device=device)
        
    def record_audio(self):
        # 带静音检测的录音实现
        with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=callback):
            while self.recording:
                if time.time() - self.last_speech_time > self.silence_duration:
                    self.stop_recording()
                    break
```

## ⚙️ 配置说明
- **config.json**：包含API密钥、模型选择、语音设置等
- **mcp.json**：定义可用的MCP服务器和工具列表

## 🛠️ 依赖项
- OpenAI API客户端
- Whisper语音识别
- Edge-TTS文本转语音
- WebSockets（MCP通信）

## 📄 许可证
[MIT](LICENSE)