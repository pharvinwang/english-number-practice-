import streamlit as st
from gtts import gTTS
import os
import tempfile
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

def process_audio(audio_bytes, target_word, score_good, score_ok):
    """處理音頻並返回結果"""
    # 儲存音頻為臨時文件
    tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_audio.write(audio_bytes)
    tmp_audio.close()
    
    # 語音辨識
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(tmp_audio.name) as source:
            audio = recognizer.record(source)
            result = recognizer.recognize_google(audio, language="en-US")
            
            # 計算分數
            score = calculate_score(target_word, result)
            
            # 判斷結果
            if score >= score_good:
                feedback = "correct"
                is_correct = True
            elif score >= score_ok:
                feedback = "close"
                is_correct = False
            else:
                feedback = "retry"
                is_correct = False
                
            return feedback, score, is_correct, result
            
    except sr.UnknownValueError:
        return "unclear", None, False, None
    except sr.RequestError:
        return "error", None, False, None
    except Exception as e:
        return "error", None, False, str(e)
    finally:
        os.unlink(tmp_audio.name)

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

# =========================
# 主要區域
# =========================
st.title("👧 英文數字跟讀練習 v5.1")
st.caption("使用 Streamlit 原生錄音功能 - 更穩定可靠")

# 檢查是否已開始
if not st.session_state.numbers_list:
    st.info("👈 請先在左側設定參數，然後按「開始練習」")
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
    if st.button("🔊 播放老師發音", use_container_width=True, key="play_button"):
        audio_file = generate_tts(current_number)
        st.audio(audio_file, format="audio/mp3", autoplay=True)

st.markdown("---")

# 使用 Streamlit 原生錄音功能
st.markdown("### 🎤 錄音並提交")

col_a, col_b, col_c = st.columns([1, 3, 1])
with col_b:
    audio_bytes = st.audio_input("點擊錄音按鈕開始", key=f"audio_{current_number}")

if audio_bytes:
    st.success("✅ 已錄音完成！")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎯 提交並判斷", type="primary", use_container_width=True):
            with st.spinner("正在辨識中..."):
                feedback, score, is_correct, result = process_audio(
                    audio_bytes.getvalue(), 
                    target_word, 
                    score_good, 
                    score_ok
                )
                
                st.session_state.feedback = feedback
                st.session_state.last_score = score
                
                if is_correct:
                    st.session_state.challenge_correct += 1
                    st.session_state.current_index += 1
                
                st.rerun()

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

# 跳過按鈕（只在跟讀模式且未正確時顯示）
if st.session_state.mode == "跟讀模式" and st.session_state.feedback != "correct":
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("⏭️ 跳過這題", use_container_width=True):
            st.session_state.current_index += 1
            st.session_state.feedback = ""
            st.session_state.last_score = None
            st.rerun()

# 使用說明
with st.expander("📖 使用說明"):
    st.markdown("""
    ### 操作步驟：
    1. **設定參數**：在左側設定起始/結束數字和評分門檻
    2. **選擇模式**：
       - **跟讀模式**：依序練習 N 到 S 的所有數字
       - **闖關模式**：隨機 10 題挑戰
    3. **開始練習**：點擊「🚀 開始練習」
    4. **播放發音**：點擊「🔊 播放老師發音」聽標準發音
    5. **錄音**：點擊麥克風按鈕開始錄音，再次點擊結束
    6. **提交**：點擊「🎯 提交並判斷」進行評分
    
    ### 提示：
    - 建議使用 Chrome 或 Edge 瀏覽器
    - 首次使用需允許瀏覽器麥克風權限
    - 錄音時請靠近麥克風，清楚發音
    - 跟讀模式可使用「跳過」功能
    """)
