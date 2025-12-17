import streamlit as st
import numpy as np
import tempfile
import os
import re
import random
from gtts import gTTS
from num2words import num2words
from rapidfuzz import fuzz
import speech_recognition as sr
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode

# =========================
# Page & CSS
# =========================
st.set_page_config(page_title="英文數字跟讀 v4.5", layout="centered")
st.markdown("""
<style>
.card {background:#fff;border-radius:20px;padding:24px;margin:16px 0;box-shadow:0 4px 10px rgba(0,0,0,0.08);}
.big-number {font-size:110px;text-align:center;font-weight:bold;}
.center {text-align:center;}
.full-btn button {width:100%;font-size:22px;padding:16px;border-radius:16px;}
.progress {font-size:18px;text-align:center;color:#555;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='center'>👧 英文數字跟讀 v4.5</h1>", unsafe_allow_html=True)
st.markdown("<p class='center'>左側設定 → 按 START → 每題按播放老師發音 → 跟讀 → 提交</p>", unsafe_allow_html=True)

# =========================
# Sidebar: 設定 + START
# =========================
st.sidebar.header("⚙ 教師設定")
start_n = st.sidebar.number_input("起始數字 N", 1, 100, 1)
end_n = st.sidebar.number_input("結束數字 S", 1, 100, 20)
score_good = st.sidebar.slider("🌟 很棒門檻 (%)", 70, 95, 85)
score_ok = st.sidebar.slider("🙂 接近門檻 (%)", 50, 84, 70)
mode = st.sidebar.radio("選擇模式", ["闖關模式", "跟讀模式"])

if "start_pressed" not in st.session_state:
    st.session_state.start_pressed = False
if st.sidebar.button("START"):
    st.session_state.start_pressed = True

# =========================
# Utils
# =========================
def normalize(text):
    text = text.lower()
    text = re.sub(r"[-]", " ", text)
    text = re.sub(r"[^a-z ]", "", text)
    return text.strip()

def smart_score(target, result):
    target = normalize(target)
    result = normalize(result)
    hit = sum(1 for w in target.split() if w in result)
    return min(100, fuzz.ratio(target, result) + hit * 5)

class AudioRecorder(AudioProcessorBase):
    def __init__(self):
        self.frames = []
    def recv(self, frame):
        self.frames.append(frame.to_ndarray())
        return frame

# =========================
# Init Functions
# =========================
def init_challenge():
    st.session_state.challenge_numbers = random.sample(range(start_n, end_n + 1), 10)
    st.session_state.challenge_index = 0
    st.session_state.challenge_correct = 0
    st.session_state.challenge_finished = False
    st.session_state.feedback = ""
    st.session_state.last_score = None
    if "ctx_challenge" not in st.session_state:
        st.session_state.ctx_challenge = webrtc_streamer(
            key="challenge_speech",
            mode=WebRtcMode.SENDONLY,
            audio_processor_factory=AudioRecorder,
            media_stream_constraints={"audio": True, "video": False},
            async_processing=True
        )
    if "frames_challenge" not in st.session_state:
        st.session_state.frames_challenge = []

def init_follow():
    st.session_state.follow_numbers = list(range(start_n, end_n + 1))
    st.session_state.follow_index = 0
    st.session_state.follow_finished = False
    st.session_state.feedback = ""
    st.session_state.last_score = None
    st.session_state.tts_played = False
    if "ctx_follow" not in st.session_state:
        st.session_state.ctx_follow = webrtc_streamer(
            key="follow_speech",
            mode=WebRtcMode.SENDONLY,
            audio_processor_factory=AudioRecorder,
            media_stream_constraints={"audio": True, "video": False},
            async_processing=True
        )
    if "frames_follow" not in st.session_state:
        st.session_state.frames_follow = []

# =========================
# START 控制
# =========================
if st.session_state.start_pressed:
    if mode == "闖關模式":
        if "challenge_numbers" not in st.session_state:
            init_challenge()
    elif mode == "跟讀模式":
        if "follow_numbers" not in st.session_state:
            init_follow()
else:
    st.markdown("<p class='center'>請先設定左側參數並按 START</p>", unsafe_allow_html=True)
    st.stop()

# =========================
# TTS 播放 (穩定)
# =========================
if "tts_files" not in st.session_state:
    st.session_state.tts_files = {}

def play_tts(number):
    if number not in st.session_state.tts_files:
        word = num2words(number).replace("-", " ")
        tts = gTTS(word, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tts.save(f.name)
            st.session_state.tts_files[number] = f.name
    st.audio(st.session_state.tts_files[number])

# =========================
# Mode: 跟讀模式
# =========================
if mode == "跟讀模式":
    if st.session_state.follow_finished:
        st.markdown("<div class='card center'>🎉 跟讀完成！太棒了！</div>", unsafe_allow_html=True)
        if st.button("重新開始"):
            init_follow()
        st.stop()

    current_number = st.session_state.follow_numbers[st.session_state.follow_index]
    st.markdown(f"<div class='progress'>數字 {current_number} / {st.session_state.follow_numbers[-1]}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><div class='big-number'>{current_number}</div></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1,3])
    with col1:
        if st.button("播放老師發音", key=f"play_{current_number}"):
            play_tts(current_number)

    ctx = st.session_state.ctx_follow
    if ctx.audio_processor:
        st.session_state.frames_follow += ctx.audio_processor.frames
        ctx.audio_processor.frames = []

    if st.button("提交錄音", key=f"submit_{current_number}"):
        if st.session_state.frames_follow:
            audio = np.concatenate(st.session_state.frames_follow, axis=0)
            import soundfile as sf
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, audio, 48000)
                wav_path = f.name
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as src:
                audio_data = recognizer.record(src)
            try:
                result = recognizer.recognize_google(audio_data, language="en-US")
            except:
                result = ""
            os.unlink(wav_path)
            st.session_state.frames_follow = []
            score = smart_score(num2words(current_number).replace("-", " "), result)
            st.session_state.last_score = score
            if score >= score_good:
                st.session_state.feedback = "✅ 正確！"
                st.session_state.follow_index += 1
                if st.session_state.follow_index >= len(st.session_state.follow_numbers):
                    st.session_state.follow_finished = True
            elif score >= score_ok:
                st.session_state.feedback = "🙂 再試一次就好！"
            else:
                st.session_state.feedback = "💪 再試！"
        else:
            st.session_state.feedback = "⚠️ 尚未錄音或錄音無效！"

    st.markdown("<div class='card center'>", unsafe_allow_html=True)
    if st.session_state.feedback:
        st.markdown(f"<h2 class='center'>{st.session_state.feedback}</h2>", unsafe_allow_html=True)
        if st.session_state.last_score is not None:
            st.markdown(f"<p class='center'>發音接近程度：約 {st.session_state.last_score}%</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================
# Mode: 闖關模式
# =========================
elif mode == "闖關模式":
    if st.session_state.challenge_finished:
        st.markdown(f"<div class='card center'>🎉 闖關完成！正確題數：{st.session_state.challenge_correct}/10</div>", unsafe_allow_html=True)
        if st.button("重新開始"):
            init_challenge()
        st.stop()

    current_number = st.session_state.challenge_numbers[st.session_state.challenge_index]
    st.markdown(f"<div class='progress'>題目 {st.session_state.challenge_index+1} / 10</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><div class='big-number'>{current_number}</div></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1,3])
    with col1:
        if st.button("播放老師發音", key=f"play_ch_{current_number}"):
            play_tts(current_number)

    ctx = st.session_state.ctx_challenge
    if ctx.audio_processor:
        st.session_state.frames_challenge += ctx.audio_processor.frames
        ctx.audio_processor.frames = []

    if st.button("提交錄音", key=f"submit_ch_{current_number}"):
        if st.session_state.frames_challenge:
            audio = np.concatenate(st.session_state.frames_challenge, axis=0)
            import soundfile as sf
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                sf.write(f.name, audio, 48000)
                wav_path = f.name
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as src:
                audio_data = recognizer.record(src)
            try:
                result = recognizer.recognize_google(audio_data, language="en-US")
            except:
                result = ""
            os.unlink(wav_path)
            st.session_state.frames_challenge = []
            score = smart_score(num2words(current_number).replace("-", " "), result)
            st.session_state.last_score = score
            if score >= score_good:
                st.session_state.feedback = "✅ 正確！"
                st.session_state.challenge_correct += 1
            elif score >= score_ok:
                st.session_state.feedback = "🙂 再試一次就好！"
            else:
                st.session_state.feedback = "💪 再試！"
            st.session_state.challenge_index += 1
            if st.session_state.challenge_index >= 10:
                st.session_state.challenge_finished = True
        else:
            st.session_state.feedback = "⚠️ 尚未錄音或錄音無效！"

    st.markdown("<div class='card center'>", unsafe_allow_html=True)
    if st.session_state.feedback:
        st.markdown(f"<h2 class='center'>{st.session_state.feedback}</h2>", unsafe_allow_html=True)
        if st.session_state.last_score is not None:
            st.markdown(f"<p class='center'>發音接近程度：約 {st.session_state.last_score}%</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
