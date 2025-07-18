import asyncio
import time
from voice_to_text import VoiceToTextConverter
from text_to_speech import TextToSpeech
import asyncio
from ai_chatbot import MCPClient


async def main():
    print("🤖 语音助手初始化中...")

    # 初始化语音转文本模块
    

    # 初始化文本转语音模块
    tts = TextToSpeech(
        default_voice="zh-TW-HsiaoChenNeural",
        rate="+5%"
    )
    await tts.initialize()
    print("🔊 语音合成引擎就绪")

    # 初始化AI聊天机器人
    try:
        chatbot = MCPClient()
        print("🔄 正在连接MCP服务器...")
        for server_name in chatbot.mcp_servers.keys():
            try:
                await chatbot.connect_to_server(server_name)
                print(f"✅ 成功连接到 {server_name}")
            except Exception as e:
                print(f"⚠️ 连接 {server_name} 失败: {str(e)}")

        if not chatbot.servers:
            print("❌ 没有成功连接到任何MCP服务器，程序退出")
            return
    except Exception as e:
        print(f"初始化聊天机器人失败: {str(e)}")
        return

    print("🎉 语音助手已准备就绪！请开始说话SS...")

    while True:
        # 开始录音并获取识别结果
        vtt = VoiceToTextConverter()
        transcribed_text = vtt.record_and_transcribe()
        if not transcribed_text:
            continue
        #transcribed_text=input('请输入:')
        print(f"👤 你: {transcribed_text}")

        # 发送给AI处理
        try:
            print("🤔 AI正在思考...")
            ai_response = await chatbot.process_query(transcribed_text)
            print(f"🤖 AI: {ai_response}")

            # 转换为语音并播放
            await tts.synthesize(ai_response)
        except Exception as e:
            error_msg = f"处理请求时出错: {str(e)}"
            print(f"⚠️ {error_msg}")
            await tts.synthesize('报错啦 请重试吧！')

if __name__ == "__main__":
    asyncio.run(main())