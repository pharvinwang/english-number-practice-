import streamlit as st
from gtts import gTTS
import os
import tempfile
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import numpy as np
import speech_recognition as sr
from num2words import num2words
import random
from rapidfuzz import fuzz
import re

st.set_page_config(page_title="英文數字跟讀練習", layout="wide")

# =========================
# CSS 樣式
# =========================
st.markdown("""
<style>
.big-number {
    font-size: 120px;
    text-align: center;
    font-weight: bold;
    color: #2e7d32;
    margin: 30px 0;
}
.progress-text {
    text-align: center;
    font-size: 20px;
    color: #666;
    margin: 20px 0;
}
.feedback-box {
    padding: 20px;
    border-radius: 10px;
    margin: 20px 0;
    text-align: center;
    font-size: 24px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# Session State 初始化
# =========================
if "mic_enabled" not in st.session_state:
    st.session_state.mic_enabled = False
if "numbers_list" not in st.session_state:
    st.session_state.numbers_list = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "feedback" not in st.session_state:
    st.session_state.feedback = ""
if "last_score" not in st.session_state:
    st.session_state.last_score = None
if "mode" not in st.session_state:
    st.session_state.mode = "跟讀模式"
if "challenge_correct" not in st.session_state:
    st.session_state.challenge_correct = 0
if "tts_cache" not in st.session_state:
    st.session_state.tts_cache = {}

# =========================
# 工具函數
# =========================
def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[-]", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

def calculate_score(target, result):
    target = normalize_text(target)
    result = normalize_text(result)
    
    # 檢查數字是否出現在結果中
    target_words = target.split()
    matches = sum(1 for word in target_words if word in result)
    
    # 計算相似度分數
    base_score = fuzz.ratio(target, result)
    bonus = matches * 10
    
    return min(100, base_score + bonus)

def get_number_word(number):
    return num2words(number).replace("-", " ")

def generate_tts(number):
    if number not in st.session_state.tts_cache:
        word = get_number_word(number)
        tts = gTTS(text=word, lang="en")
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp_file.name)
        st.session_state.tts_cache[number] = tmp_file.name
    return st.session_state.tts_cache[number]

# =========================
# 音頻處理器
# =========================
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []
        self.is_recording = False
    
    def recv(self, frame):
        if self.is_recording:
            audio = frame.to_ndarray()
            self.frames.append(audio)
        return frame

# =========================
# 側邊欄設定
# =========================
st.sidebar.title("⚙️ 教師設定")

start_n = st.sidebar.number_input("起始數字 N", min_value=1, max_value=100, value=1)
end_n = st.sidebar.number_input("結束數字 S", min_value=1, max_value=100, value=20)

if start_n > end_n:
    st.sidebar.error("起始數字不能大於結束數字！")

score_good = st.sidebar.slider("🌟 很棒門檻 (%)", 70, 95, 85)
score_ok = st.sidebar.slider("🙂 接近門檻 (%)", 50, 90, 70)

mode = st.sidebar.radio("選擇模式", ["跟讀模式", "闖關模式"])

st.sidebar.markdown("---")

# 初始化按鈕
if st.sidebar.button("🚀 開始練習", type="primary"):
    if mode == "跟讀模式":
        st.session_state.numbers_list = list(range(start_n, end_n + 1))
    else:  # 闖關模式
        st.session_state.numbers_list = random.sample(
            range(start_n, end_n + 1), 
            min(10, end_n - start_n + 1)
        )
    st.session_state.current_index = 0
    st.session_state.feedback = ""
    st.session_state.last_score = None
    st.session_state.mode = mode
    st.session_state.challenge_correct = 0
    st.session_state.mic_enabled = False

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎤 錄音狀態")
if st.session_state.mic_enabled:
    st.sidebar.success("✅ 錄音已啟用")
else:
    st.sidebar.info("請先允許麥克風權限")

# =========================
# 主要區域
# =========================
st.title("👧 英文數字跟讀練習 v5.0")

# 檢查是否已開始
if not st.session_state.numbers_list:
    st.info("👈 請先在左側設定參數,然後按「開始練習」")
    st.stop()

# 檢查是否完成
if st.session_state.current_index >= len(st.session_state.numbers_list):
    st.balloons()
    st.success("🎉 恭喜完成！")
    
    if st.session_state.mode == "闖關模式":
        st.markdown(f"### 成績: {st.session_state.challenge_correct} / {len(st.session_state.numbers_list)} 題正確")
        
        percentage = (st.session_state.challenge_correct / len(st.session_state.numbers_list)) * 100
        if percentage >= 80:
            st.markdown("🏆 **超級棒！你是英文數字高手！**")
        elif percentage >= 60:
            st.markdown("⭐ **很好！繼續加油！**")
        else:
            st.markdown("💪 **不錯！多練習就會更好！**")
    else:
        st.markdown(f"### 完成 {len(st.session_state.numbers_list)} 個數字的跟讀練習！")
    
    if st.button("🔄 重新開始"):
        st.session_state.numbers_list = []
        st.session_state.current_index = 0
        st.session_state.feedback = ""
        st.session_state.challenge_correct = 0
        st.rerun()
    
    st.stop()

# 當前數字
current_number = st.session_state.numbers_list[st.session_state.current_index]
target_word = get_number_word(current_number)

# 顯示進度
if st.session_state.mode == "跟讀模式":
    progress_text = f"數字 {st.session_state.current_index + 1} / {len(st.session_state.numbers_list)}"
else:
    progress_text = f"題目 {st.session_state.current_index + 1} / {len(st.session_state.numbers_list)}"

st.markdown(f"<div class='progress-text'>{progress_text}</div>", unsafe_allow_html=True)

# 顯示數字
st.markdown(f"<div class='big-number'>{current_number}</div>", unsafe_allow_html=True)

# 播放老師發音
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔊 播放老師發音", use_container_width=True):
        audio_file = generate_tts(current_number)
        st.audio(audio_file)

st.markdown("---")

# WebRTC 音頻流
st.markdown("### 🎤 開始錄音")
st.info("點擊下方的 START 按鈕開始錄音，點擊 STOP 結束錄音")

webrtc_ctx = webrtc_streamer(
    key="speech-recording",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True,
)

# 更新錄音狀態
if webrtc_ctx.state.playing:
    st.session_state.mic_enabled = True
    if webrtc_ctx.audio_processor:
        webrtc_ctx.audio_processor.is_recording = True
else:
    if webrtc_ctx.audio_processor:
        webrtc_ctx.audio_processor.is_recording = False

# 提交錄音按鈕
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("✅ 提交錄音", type="primary", use_container_width=True):
        if webrtc_ctx.audio_processor and len(webrtc_ctx.audio_processor.frames) > 0:
            # 合併音頻數據
            audio_data = np.concatenate(webrtc_ctx.audio_processor.frames, axis=0)
            
            # 轉換為單聲道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # 儲存為 WAV 文件
            import soundfile as sf
            tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            sf.write(tmp_wav.name, audio_data, 48000)
            tmp_wav.close()
            
            # 語音辨識
            recognizer = sr.Recognizer()
            try:
                with sr.AudioFile(tmp_wav.name) as source:
                    audio = recognizer.record(source)
                    result = recognizer.recognize_google(audio, language="en-US")
                    
                    # 計算分數
                    score = calculate_score(target_word, result)
                    st.session_state.last_score = score
                    
                    # 判斷結果
                    if score >= score_good:
                        st.session_state.feedback = "correct"
                        st.session_state.challenge_correct += 1
                        st.session_state.current_index += 1
                    elif score >= score_ok:
                        st.session_state.feedback = "close"
                    else:
                        st.session_state.feedback = "retry"
                    
            except sr.UnknownValueError:
                st.session_state.feedback = "unclear"
            except sr.RequestError:
                st.session_state.feedback = "error"
            finally:
                os.unlink(tmp_wav.name)
            
            # 清空錄音緩存
            webrtc_ctx.audio_processor.frames = []
            st.rerun()
        else:
            st.warning("⚠️ 請先錄音再提交！")

# 顯示回饋
if st.session_state.feedback:
    st.markdown("---")
    
    feedback_map = {
        "correct": ("🌟 太棒了！發音正確！", "#d4edda", "✅"),
        "close": ("🙂 很接近了！再試一次看看～", "#fff3cd", "🔄"),
        "retry": ("💪 沒關係，再聽一次老師的發音試試！", "#cce5ff", "🔄"),
        "unclear": ("❓ 聽不清楚，請靠近麥克風再試一次", "#f8d7da", "🎤"),
        "error": ("⚠️ 語音辨識服務暫時無法使用", "#f8d7da", "🔄")
    }
    
    if st.session_state.feedback in feedback_map:
        msg, color, icon = feedback_map[st.session_state.feedback]
        st.markdown(
            f"<div class='feedback-box' style='background-color: {color};'>"
            f"{icon} {msg}"
            f"</div>",
            unsafe_allow_html=True
        )
        
        if st.session_state.last_score is not None:
            st.markdown(f"**發音相似度: {st.session_state.last_score}%**")

# 跳過按鈕（只在跟讀模式顯示）
if st.session_state.mode == "跟讀模式" and st.session_state.feedback != "correct":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⏭️ 跳過這題", use_container_width=True):
            st.session_state.current_index += 1
            st.session_state.feedback = ""
            st.session_state.last_score = None
            st.rerun()
