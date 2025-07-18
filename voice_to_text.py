import sounddevice as sd
import numpy as np
import whisper
import torch
import wavio
import threading
import time 
import time as time_module

class VoiceToTextConverter:
    def __init__(self):
        # 初始化参数
        self.recording = False
        self.audio_data = None
        self.samplerate = 16000  # 采样率
        self.channels = 1        # 单声道
        # 静音检测参数
        self.silence_threshold = 0.02  # 静音阈值(振幅)
        self.silence_duration = 3 # 静音持续时间(秒)
        self.last_speech_time = time.time()  # 最后语音时间
        self.recording_event = threading.Event()  # 初始化事件标志
        self.last_transcription = ""  # 存储最新转录结果
        self.lock = threading.Lock()  # 添加线程锁确保变量同步
        # 显式指定device为cpu并使用fp32精度以避免警告
        # 自动检测GPU，如果可用则使用cuda，否则使用cpu
        device = "cuda" if torch.cuda.is_available() else "cpu"
        #print(f"使用设备: {device}")
        self.model = whisper.load_model("base", device=device)  # 加载量化模型减小体积并加速推理
        self.output_file = 'recording.wav'  # 临时音频文件

        # 移除自动开始录音，改为手动调用record_and_transcribe()
        pass

    def record_and_transcribe(self):
        """开始录音并在检测到静音后返回识别结果"""
        self.start_recording()
        # 等待录音线程完成
        self.recording_thread.join()
        with self.lock:
            return self.last_transcription

    def start_recording(self):
        """开始录音"""
        self.recording = True
        self.audio_data = []
        #print("开始录音...")

        # 在新线程中录音，避免阻塞主线程
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.start()

    def record_audio(self):
        """录音函数 - 实时处理音频流并检测静音"""
        def callback(indata, frames, time, status):
            # if status:
            #     print(f"录音状态: {status}")
            self.audio_data.append(indata.copy())
            
            # 计算音频振幅(音量)
            amplitude = np.max(np.abs(indata))
            current_time = time_module.time()  # 使用重命名的time模块避免冲突
            
            # 如果振幅超过阈值，更新最后语音时间
            if amplitude > self.silence_threshold:
                self.last_speech_time = current_time
            
            # 检查是否超过静音持续时间
            if current_time - self.last_speech_time > self.silence_duration:
                self.stop_recording()

        # 创建录音流
        with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=callback):
            while self.recording and not self.recording_event.is_set():
                # 仅保持循环运行，等待静音检测触发停止
                time.sleep(0.1)
                
                # 检查静音状态
                if time.time() - self.last_speech_time > self.silence_duration:
                    self.stop_recording()
                    break

    def process_audio_fragment(self):
        """处理音频片段并实时转录"""
        if not self.audio_data:
            return

        # 提取并清空当前音频数据
        audio_array = np.concatenate(self.audio_data, axis=0)
        self.audio_data = []

        # 保存为临时文件
        temp_file = 'temp_recording.wav'
        wavio.write(temp_file, audio_array, self.samplerate, sampwidth=2)

        # 使用whisper进行实时语音识别
        try:
            # 使用更短的温度设置和单通道处理以加快速度
            result = self.model.transcribe(
                temp_file, 
                language='zh', 
                fp16=torch.cuda.is_available(),  # 根据设备自动选择精度
                initial_prompt="日常对话",
                temperature=0.0,
                condition_on_previous_text=True,  # 确定性输出
                no_speech_threshold=0.6  # 降低无语音阈值
            )
            transcribed_text = result['text'].strip()
            # 确保中文正常显示
            transcribed_text = transcribed_text.encode('utf-8').decode('utf-8')
            if transcribed_text:
                # 更新最后语音时间
                self.last_speech_time = time.time()
                return transcribed_text
        except Exception as e:
            print(f"语音识别出错: {str(e)}")
            return ""

        # 删除临时文件
        import os
        if os.path.exists(temp_file):
            os.remove(temp_file)

    def stop_recording(self):
        """停止录音并处理最后的音频片段"""
        if not self.recording:
            return

        self.recording = False
        self.recording_event.set()  # 触发事件通知线程结束
        # 确保不在当前线程中调用join


        # 处理剩余的音频数据
        final_text = self.process_audio_fragment()
        
        # 输出最终识别结果
        if final_text:
            with self.lock:
                self.last_transcription = final_text
            print(f"识别结果: {final_text}")
        
        # 仅返回识别结果，不保存到文件
        if not final_text:
            print("未检测到有效语音内容")

        print("录音已停止")
        return final_text

    def run(self):
        """运行程序 - 持续运行直到用户按Ctrl+C退出"""
        try:
            # 持续运行主循环
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_recording()
            print("程序已退出")

if __name__ == "__main__":
    # 确保中文显示正常
    
    while True:

        vtt = VoiceToTextConverter()
        transcribed_text = vtt.record_and_transcribe()
        if not transcribed_text:
            print("🔇 未检测到语音输入，请重试...")
            continue
        print(f"识别结果: {transcribed_text}")
        transcribed_text=""
        if transcribed_text == "退出":
            break

