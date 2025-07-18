#!/usr/bin/env python3

"""文本转语音功能封装类，提供灵活的语音合成接口"""

import asyncio
from typing import Optional, Dict, List
import os
import tempfile
import edge_tts
from edge_tts import VoicesManager
from playsound import playsound


class TextToSpeech:
    """
    文本转语音合成器类
    提供灵活的语音合成接口，支持自定义语音、语速、音量等参数
    """
    def __init__(self, default_voice: str = "zh-CN-XiaoxiaoNeural", 
                rate: str = "+0%", 
                 volume: str = "+0%", pitch: str = "+0Hz"):
        """
        初始化文本转语音合成器
        :param default_voice: 默认语音模型
        :param default_output: 默认输出文件路径
        :param rate: 语速，格式为"+/-百分比"，如"+10%"或"-5%"
        :param volume: 音量，格式为"+/-百分比"
        :param pitch: 音调，格式为"+/-Hz"
        """
        self.default_voice = default_voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch
        self.voices_manager: Optional[VoicesManager] = None
        self.available_voices: List[Dict] = []

    async def initialize(self):
        """初始化语音管理器并加载可用语音列表"""
        self.voices_manager = await VoicesManager.create()
        self.available_voices = self.voices_manager.voices
        return self

    def find_voices(self, **kwargs) -> List[Dict]:
        """
        根据条件查找可用语音
        :param kwargs: 筛选条件，如Gender="Female", Language="zh"
        :return: 符合条件的语音列表
        """
        if not self.voices_manager:
            raise RuntimeError("语音管理器未初始化，请先调用initialize()")
        return self.voices_manager.find(** kwargs)

    async def synthesize(self, text: str, voice: Optional[str] = None, 
                         output_file: Optional[str] = None) -> None:
        """
        将文本合成为语音并播放
        :param text: 待合成的文本
        :param voice: 语音模型，默认为None使用default_voice
        :param output_file: 已弃用参数，不再保存文件
        :return: 无返回值
        """
        if not self.voices_manager:
            raise RuntimeError("语音管理器未初始化，请先调用initialize()")

        # 使用默认语音（如果未提供）
        voice = voice or self.default_voice
        
        # 创建临时文件存储音频
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_filename = temp_file.name

        # 创建语音合成器
        communicate = edge_tts.Communicate(
            text, voice, rate=self.rate, volume=self.volume, pitch=self.pitch
        )

        try:
            # 保存合成结果到临时文件
            await communicate.save(temp_filename)
            # 播放语音
            playsound(temp_filename)
        finally:
            # 确保临时文件被删除
            os.remove(temp_filename)

        return None

    async def list_voices(self, **kwargs) -> None:
        """打印符合条件的语音列表"""
        voices = self.find_voices(** kwargs)
        if not voices:
            print("未找到符合条件的语音")
            return

        print(f"找到{len(voices)}个符合条件的语音：")
        for idx, voice in enumerate(voices, 1):
            print(f"{idx}. {voice['Name']} - {voice['Gender']} - {voice['Locale']}")


# 便捷使用示例
async def main():
    # 创建TTS实例并初始化
    tts = TextToSpeech(
        default_voice="zh-TW-HsiaoChenNeural",
        rate="+5%"
    )
    await tts.initialize()

    # 列出所有中文女声
    await tts.list_voices(Language="zh", Gender="Female")

    # 合成语音
    output_path = await tts.synthesize("早上好，这是一个文本转语音功能演示。")
    print(f"语音合成完成，文件保存至：{output_path}")


if __name__ == "__main__":
    asyncio.run(main())