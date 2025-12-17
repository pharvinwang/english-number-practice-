import streamlit as st
import numpy as np
import tempfile
import os

from gtts import gTTS
from num2words import num2words
from rapidfuzz import fuzz
import speech_recognition as sr

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode

# =========================
# 頁面設定
# =========================
st.set_page_config(page_title="英文數字發音練習", layout="centered")

st.title("👧 英文數字發音練習")
st.caption("聽老師唸，再換你唸看看！")

# =========================
# 側邊欄（家長設定）
# =========================
st.sidebar.header("⚙ 教師設定")

start_n = st.sidebar.number_input("起始數字", 1, 100, 1)
end_n = st.sidebar.number_input("結束數字", 1, 100, 20)

score_good = st.sidebar.slider("判定為『很棒』門檻 (%)", 70, 95, 85)
score_ok = st.sidebar.slider("判定為『接近』門檻 (%)", 50, 84, 70)

# =========================
# Session State
# =========================
if "number" not in st.session_state:
    st.session_state.number = np.random.randint(start_n, end_n + 1)

if "feedback" not in st.session_state:
    st.session_state.feedback = ""

if "last_score" not in st.session_state:
    st.session_state.last_score = None

# =========================
# 顯示數字（超大）
# =========================
st.markdown(
    f"""
    <div style="font-size:120px;
                text-align:center;
                font-weight:bold;
                margin:30px 0;">
        {st.session_state.number}
    </div>
    """,
    unsafe_allow_html=True
)

target_word = num2words(st.session_state.number).replace("-", " ")

# =========================
# TTS：老師發音
# =========================
st.subheader("🔊 聽老師唸")

if st.button("播放老師發音 🔊"):
    tts = gTTS(text=target_word, lang="en")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        tts.save(f.name)
        st.audio(f.name)
        os.unlink(f.name)

# =========================
# 錄音處理器
# =========================
class AudioRecorder(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv(self, frame):
        audio = frame.to_ndarray()
        self.frames.append(audio)
        return frame

# =========================
# 錄音 UI
# =========================
st.subheader("🎤 輪到你唸囉！")

ctx = webrtc_streamer(
    key="speech",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioRecorder,
    media_stream_constraints={"audio": True, "video": False},
)

# =========================
# 停止後處理語音
# =========================
if ctx.audio_processor and not ctx.state.playing:
    frames = ctx.audio_processor.frames

    if frames:
        audio = np.concatenate(frames, axis=0)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            import soundfile as sf
            sf.write(f.name, audio, 48000)
            wav_path = f.name

        # Speech to Text
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        try:
            result = recognizer.recognize_google(audio_data, language="en-US").lower()
        except:
            result = ""

        os.unlink(wav_path)

        # =========================
        # 發音評分
        # =========================
        score = fuzz.ratio(target_word, result)
        st.session_state.last_score = score

        if score >= score_good:
            st.session_state.feedback = "🌟 太棒了！你唸得很清楚！"
        elif score >= score_ok:
            st.session_state.feedback = "🙂 很接近了！再試一次看看～"
        else:
            st.session_state.feedback = "💪 沒關係，聽一次老師的發音再試試！"

# =========================
# 老師回饋
# =========================
st.subheader("🌟 老師回饋")

if st.session_state.feedback:
    st.success(st.session_state.feedback)

    if st.session_state.last_score is not None:
        st.caption(f"（發音接近程度：約 {st.session_state.last_score}%）")
else:
    st.info("說完之後，老師會給你鼓勵唷！")

# =========================
# 下一題
# =========================
if st.button("下一個數字 ➡️"):
    st.session_state.number = np.random.randint(start_n, end_n + 1)
    st.session_state.feedback = ""
    st.session_state.last_score = None
