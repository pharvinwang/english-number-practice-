# app.py v4.7 完整修正版
import streamlit as st
from gtts import gTTS
import os
import tempfile
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import numpy as np
import speech_recognition as sr

st.set_page_config(page_title="英文數字跟讀", layout="wide")

# -----------------------------
# SESSION STATE INIT
# -----------------------------
if "mic_on" not in st.session_state:
    st.session_state.mic_on = False
if "current_number" not in st.session_state:
    st.session_state.current_number = 0
if "numbers_list" not in st.session_state:
    st.session_state.numbers_list = []

# -----------------------------
# SIDEBAR: TEACHER SETTINGS
# -----------------------------
st.sidebar.header("👨‍🏫 教師設定")
start_num = st.sidebar.number_input("起始數字 N", min_value=1, max_value=100, value=1)
end_num = st.sidebar.number_input("結束數字 S", min_value=1, max_value=100, value=20)
threshold_high = st.sidebar.slider("🌟 很棒門檻 (%)", 70, 95, 85)
threshold_low = st.sidebar.slider("🙂 接近門檻 (%)", 50, 90, 70)

mode = st.sidebar.radio("選擇模式", ["闖關模式", "跟讀模式"])

if "numbers_list" not in st.session_state or st.session_state.numbers_list != list(range(start_num, end_num+1)):
    st.session_state.numbers_list = list(range(start_num, end_num+1))
    st.session_state.current_number = 0

st.sidebar.header("🎤 錄音控制")
if st.sidebar.button("啟動錄音"):
    st.session_state.mic_on = True
    st.success("錄音已啟動，請允許瀏覽器使用麥克風。")

# -----------------------------
# WEBRTC INITIALIZATION
# -----------------------------
class AudioRecorder(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame):
        if st.session_state.mic_on:
            self.frames.append(frame.to_ndarray())
        return frame

ctx = webrtc_streamer(
    key="mic",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioRecorder,
    media_stream_constraints={"audio": True, "video": False},
    async_processing=True
)

# -----------------------------
# MAIN AREA
# -----------------------------
st.title("👧 英文數字跟讀 v4.7")
st.caption("左側設定 → 啟動錄音 → 播放老師發音 → 跟讀 → 提交")

if st.session_state.current_number < len(st.session_state.numbers_list):
    number = st.session_state.numbers_list[st.session_state.current_number]
    st.subheader(f"數字 {st.session_state.current_number+1} / {len(st.session_state.numbers_list)}")
    st.markdown(f"<h1 style='text-align:center;'>{number}</h1>", unsafe_allow_html=True)
else:
    st.success("🎉 本輪練習完成！")

# -----------------------------
# FUNCTIONS
# -----------------------------
def play_teacher_voice(num):
    tts = gTTS(text=str(num), lang="en")
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp_file.name)
    st.audio(tmp_file.name)
    tmp_file.close()
    os.unlink(tmp_file.name)

def submit_recording():
    if not st.session_state.mic_on or ctx.audio_receiver is None:
        st.warning("⚠️ 尚未錄音或錄音無效！")
        return
    frames = ctx.audio_processor.frames
    if len(frames) == 0:
        st.warning("⚠️ 尚未錄音或錄音無效！")
        return
    # 保存錄音
    audio_array = np.concatenate(frames, axis=0)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    from scipy.io.wavfile import write
    write(tmp_file.name, 16000, audio_array)
    # 語音辨識
    recognizer = sr.Recognizer()
    with sr.AudioFile(tmp_file.name) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            st.info(f"辨識結果：{text}")
            if str(number) in text or str(number) in text.lower():
                st.success("✅ 發音正確！")
                st.session_state.current_number += 1
            else:
                st.warning("❌ 發音可能不正確，請再試一次！")
        except:
            st.warning("⚠️ 無法辨識錄音")
    tmp_file.close()
    os.unlink(tmp_file.name)
    ctx.audio_processor.frames = []  # 清空錄音緩存

# -----------------------------
# BUTTONS
# -----------------------------
col1, col2 = st.columns([1,1])
with col1:
    if st.button("播放老師發音"):
        play_teacher_voice(number)

with col2:
    if st.button("提交錄音"):
        submit_recording()
