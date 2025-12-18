import streamlit as st
from gtts import gTTS
import os
import tempfile
import speech_recognition as sr
from num2words import num2words
import random
from rapidfuzz import fuzz
import re
import time

st.set_page_config(page_title="英文數字跟讀練習", layout="wide", initial_sidebar_state="expanded")

# =========================
# CSS 樣式 - 增加動畫效果
# =========================
st.markdown("""
<style>
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-10px); }
    75% { transform: translateX(10px); }
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-20px); }
}

.big-number {
    font-size: 150px;
    text-align: center;
    font-weight: bold;
    color: #2e7d32;
    margin: 30px 0;
    animation: pulse 2s ease-in-out infinite;
}

.progress-text {
    text-align: center;
    font-size: 22px;
    color: #666;
    margin: 20px 0;
}

.feedback-box {
    padding: 30px;
    border-radius: 15px;
    margin: 20px 0;
    text-align: center;
    font-size: 28px;
    font-weight: bold;
}

.blink-text {
    animation: blink 1s ease-in-out infinite;
    font-size: 36px;
    color: #ff6b6b;
    text-align: center;
    font-weight: bold;
    margin: 20px 0;
}

.recording-indicator {
    background: linear-gradient(90deg, #ff6b6b, #ee5a6f);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
    font-size: 24px;
    animation: pulse 1s ease-in-out infinite;
}

.countdown {
    font-size: 60px;
    font-weight: bold;
    color: #ff6b6b;
    text-align: center;
    animation: bounce 1s ease-in-out infinite;
}

.emoji-large {
    font-size: 80px;
    text-align: center;
    animation: bounce 0.5s ease-in-out;
}

.success-box {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 20px;
    text-align: center;
    font-size: 32px;
    animation: shake 0.5s ease-in-out;
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
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "auto_mode" not in st.session_state:
    st.session_state.auto_mode = False
if "phase" not in st.session_state:
    st.session_state.phase = "ready"  # ready, playing, waiting, recording, processing

# =========================
# 工具函數
# =========================
def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[-]", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

def calculate_score(target, result, tolerance_level="中等"):
    target = normalize_text(target)
    result = normalize_text(result)
    
    child_pronunciation_map = {
        "three": ["tree", "free", "sree"],
        "thirteen": ["thirty", "thurteen", "firteen"],
        "thirty": ["thirteen", "thirsty", "turty"],
        "five": ["fibe", "fife"],
        "seven": ["seben", "sebun"],
        "eleven": ["eleben", "levin"],
        "twelve": ["twelb", "twelf"],
        "twenty": ["twenny", "twunty"],
        "fifty": ["fity", "fifthy"],
        "sixty": ["sickty", "sikty"],
        "seventy": ["sebenty", "sevunty"],
        "eighty": ["eity", "eitty"],
        "ninety": ["ninty", "ninity"],
    }
    
    if tolerance_level == "寬鬆":
        target_words = target.split()
        result_words = result.split()
        
        for target_word in target_words:
            if target_word in result_words:
                return 100
            if target_word in child_pronunciation_map:
                for similar in child_pronunciation_map[target_word]:
                    if similar in result:
                        return 95
        
        matches = sum(1 for word in target_words if word in result)
        if matches > 0:
            return 80 + (matches * 5)
        
        base_score = fuzz.ratio(target, result)
        return min(100, base_score + 15)
        
    elif tolerance_level == "中等":
        target_words = target.split()
        matches = sum(1 for word in target_words if word in result)
        
        tolerance_bonus = 0
        for target_word in target_words:
            if target_word in child_pronunciation_map:
                for similar in child_pronunciation_map[target_word]:
                    if similar in result:
                        tolerance_bonus += 10
                        break
        
        base_score = fuzz.ratio(target, result)
        bonus = matches * 10
        return min(100, base_score + bonus + tolerance_bonus)
        
    else:
        target_words = target.split()
        matches = sum(1 for word in target_words if word in result)
        base_score = fuzz.ratio(target, result)
        bonus = matches * 5
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

def get_encouragement():
    """隨機返回鼓勵語"""
    encouragements = [
        ("💪 沒關係，再接再厲！", "🌈"),
        ("🎈 很棒的嘗試！我們再來一次！", "⭐"),
        ("🌟 你可以的！再試試看！", "🎯"),
        ("🎨 很好！讓我們再練習一次！", "🚀"),
        ("🎵 加油！你會越來越好的！", "💖"),
        ("🌺 別氣餒！每次練習都是進步！", "🎪"),
        ("🎭 太棒了！讓我們繼續努力！", "🎡"),
        ("🎪 很不錯！再來挑戰一次！", "🌸"),
    ]
    return random.choice(encouragements)

def get_success_message():
    """隨機返回成功訊息"""
    messages = [
        ("🎉 太棒了！", "你真是個天才！"),
        ("⭐ 完美！", "發音超級標準！"),
        ("🏆 超級厲害！", "你是英文小高手！"),
        ("🌟 優秀！", "繼續保持！"),
        ("💯 滿分！", "你太強了！"),
        ("🎯 正中目標！", "發音非常清楚！"),
        ("👏 掌聲鼓勵！", "你做得很好！"),
        ("🌈 精彩！", "你的發音真棒！"),
    ]
    return random.choice(messages)

def process_audio(audio_bytes, target_word, score_good, score_ok, tolerance_level):
    tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_audio.write(audio_bytes)
    tmp_audio.close()
    
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(tmp_audio.name) as source:
            audio = recognizer.record(source)
            result = recognizer.recognize_google(audio, language="en-US")
            
            score = calculate_score(target_word, result, tolerance_level)
            
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

st.sidebar.markdown("---")
st.sidebar.subheader("⏱️ 錄音設定")

recording_duration = st.sidebar.slider(
    "錄音時間（秒）",
    min_value=2,
    max_value=10,
    value=4,
    help="小朋友發音的錄音時長"
)

wait_after_teacher = st.sidebar.slider(
    "老師發音後等待（秒）",
    min_value=0.5,
    max_value=3.0,
    value=1.0,
    step=0.5,
    help="老師發音結束後，等待多久提示小朋友開始"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 評分設定")

score_good = st.sidebar.slider("🌟 很棒門檻 (%)", 70, 95, 85)
score_ok = st.sidebar.slider("🙂 接近門檻 (%)", 50, 90, 70)

st.sidebar.markdown("---")
st.sidebar.subheader("👶 兒童友善設定")

tolerance_level = st.sidebar.select_slider(
    "容錯等級",
    options=["嚴格", "中等", "寬鬆"],
    value="中等",
    help="調整對發音不準確的容忍度"
)

tolerance_descriptions = {
    "寬鬆": "🟢 最適合幼兒（3-6歲）",
    "中等": "🟡 適合小學生（7-10歲）",
    "嚴格": "🔴 適合高年級（11歲以上）"
}

st.sidebar.info(tolerance_descriptions[tolerance_level])

mode = st.sidebar.radio("選擇模式", ["跟讀模式", "闖關模式"])

st.sidebar.markdown("---")

# 初始化按鈕
if st.sidebar.button("🚀 開始練習", type="primary", use_container_width=True):
    if mode == "跟讀模式":
        st.session_state.numbers_list = list(range(start_n, end_n + 1))
    else:
        st.session_state.numbers_list = random.sample(
            range(start_n, end_n + 1), 
            min(10, end_n - start_n + 1)
        )
    st.session_state.current_index = 0
    st.session_state.feedback = ""
    st.session_state.last_score = None
    st.session_state.mode = mode
    st.session_state.challenge_correct = 0
    st.session_state.phase = "ready"

# =========================
# 主要區域
# =========================
st.title("🎯 英文數字跟讀練習 v6.0")
st.caption("✨ 全自動互動版 - 讓學習更有趣！")

# 檢查是否已開始
if not st.session_state.numbers_list:
    st.markdown("""
    <div style='text-align: center; padding: 50px;'>
        <div style='font-size: 80px; margin-bottom: 20px;'>🎮</div>
        <h2>準備好開始練習了嗎？</h2>
        <p style='font-size: 20px; color: #666;'>👈 請先在左側設定參數，然後按「開始練習」</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 檢查是否完成
if st.session_state.current_index >= len(st.session_state.numbers_list):
    st.balloons()
    
    st.markdown("""
    <div class='success-box'>
        <div style='font-size: 100px; margin-bottom: 20px;'>🏆</div>
        <div>恭喜完成所有練習！</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.mode == "闖關模式":
        percentage = (st.session_state.challenge_correct / len(st.session_state.numbers_list)) * 100
        
        col1, col2, col3 = st.columns(3)
        with col2:
            st.markdown(f"""
            <div style='text-align: center; padding: 30px; background: #f0f2f6; border-radius: 15px; margin: 20px 0;'>
                <div style='font-size: 24px; color: #666; margin-bottom: 10px;'>最終成績</div>
                <div style='font-size: 60px; font-weight: bold; color: #2e7d32;'>{st.session_state.challenge_correct} / {len(st.session_state.numbers_list)}</div>
                <div style='font-size: 20px; color: #666; margin-top: 10px;'>{percentage:.0f}% 正確率</div>
            </div>
            """, unsafe_allow_html=True)
        
        if percentage >= 80:
            st.markdown("<div class='emoji-large'>🌟🌟🌟</div>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>超級棒！你是英文數字高手！</h2>", unsafe_allow_html=True)
        elif percentage >= 60:
            st.markdown("<div class='emoji-large'>⭐⭐</div>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>很好！繼續加油！</h2>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='emoji-large'>💪</div>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center;'>不錯！多練習就會更好！</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 重新開始", use_container_width=True, type="primary"):
            st.session_state.numbers_list = []
            st.session_state.current_index = 0
            st.session_state.feedback = ""
            st.session_state.challenge_correct = 0
            st.session_state.last_result = None
            st.session_state.phase = "ready"
            st.rerun()
    
    st.stop()

# 當前數字
current_number = st.session_state.numbers_list[st.session_state.current_index]
target_word = get_number_word(current_number)

# 顯示進度
if st.session_state.mode == "跟讀模式":
    progress_text = f"📚 數字 {st.session_state.current_index + 1} / {len(st.session_state.numbers_list)}"
else:
    progress_text = f"🎯 題目 {st.session_state.current_index + 1} / {len(st.session_state.numbers_list)}"

st.markdown(f"<div class='progress-text'>{progress_text}</div>", unsafe_allow_html=True)

# 顯示數字
st.markdown(f"<div class='big-number'>{current_number}</div>", unsafe_allow_html=True)

# 流程控制
if st.session_state.phase == "ready":
    # 第一步：播放老師發音
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔊 第一步：聽老師發音", use_container_width=True, type="primary", key="play_teacher"):
            audio_file = generate_tts(current_number)
            st.audio(audio_file, format="audio/mp3", autoplay=True)
            st.session_state.phase = "played"
            st.rerun()
    
    st.markdown("""
    <div style='text-align: center; margin: 30px 0; padding: 20px; background: #e3f2fd; border-radius: 10px;'>
        <div style='font-size: 24px; color: #1976d2;'>
            👆 點擊按鈕聽老師怎麼唸
        </div>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.phase == "played":
    # 顯示已播放狀態
    st.success("✅ 已播放老師發音")
    
    st.markdown("""
    <div class='blink-text' style='margin: 30px 0;'>
        🎙️ 換你練習囉！
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style='text-align: center; margin: 20px 0;'>
        <div style='font-size: 28px; color: #ff6b6b; font-weight: bold; margin-bottom: 20px;'>
            👇 點擊下方的麥克風按鈕開始錄音 👇
        </div>
        <div style='font-size: 20px; color: #666;'>
            建議錄音 {recording_duration} 秒
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 錄音介面 - 直接顯示，不需要等待
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("""
        <div style='padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 15px; margin: 20px 0;'>
            <div style='text-align: center; color: white; font-size: 24px; font-weight: bold; margin-bottom: 15px;'>
                🎤 第二步：錄下你的發音
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        audio_bytes = st.audio_input(
            "點擊麥克風開始 → 錄音 → 再點一次停止",
            key=f"audio_{current_number}_{st.session_state.current_index}"
        )
    
    # 說明文字
    st.markdown("""
    <div style='text-align: center; margin: 20px 0; padding: 15px; background: #fff9c4; border-radius: 10px;'>
        <div style='font-size: 18px; color: #f57f17;'>
            💡 <b>操作提示：</b><br>
            1️⃣ 點擊上方的麥克風圖示（瀏覽器會詢問麥克風權限，請允許）<br>
            2️⃣ 對著麥克風清楚地唸出數字<br>
            3️⃣ 錄音完成後再點一次停止<br>
            4️⃣ 系統會自動判斷你的發音
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if audio_bytes:
        st.balloons()
        st.success("🎉 錄音完成！正在判斷中...")
        
        with st.spinner("🔍 AI 正在仔細聆聽你的發音..."):
            feedback, score, is_correct, result = process_audio(
                audio_bytes.getvalue(), 
                target_word, 
                score_good, 
                score_ok,
                tolerance_level
            )
            
            st.session_state.feedback = feedback
            st.session_state.last_score = score
            st.session_state.last_result = result
            st.session_state.phase = "result"
            
            if is_correct:
                st.session_state.challenge_correct += 1
            
            st.rerun()
    
    # 重新播放按鈕
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 再聽一次老師發音", use_container_width=True):
            audio_file = generate_tts(current_number)
            st.audio(audio_file, format="audio/mp3", autoplay=True)

# 顯示結果
if st.session_state.phase == "result":
    st.markdown("---")
    
    if st.session_state.feedback == "correct":
        emoji, msg = get_success_message()
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 40px; border-radius: 20px; 
                    text-align: center; margin: 20px 0;'>
            <div style='font-size: 100px; margin-bottom: 20px;'>{emoji}</div>
            <div style='font-size: 36px; font-weight: bold; margin-bottom: 10px;'>{msg}</div>
            <div style='font-size: 24px;'>發音相似度: {st.session_state.last_score}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("➡️ 下一個數字", use_container_width=True, type="primary"):
                st.session_state.current_index += 1
                st.session_state.feedback = ""
                st.session_state.last_score = None
                st.session_state.last_result = None
                st.session_state.phase = "ready"
                st.rerun()
                
    else:
        encouragement, emoji = get_encouragement()
        
        if st.session_state.feedback == "close":
            color = "#fff3cd"
            border_color = "#ffc107"
            icon = "🙂"
        else:
            color = "#cce5ff"
            border_color = "#0066cc"
            icon = "💪"
        
        st.markdown(f"""
        <div style='background: {color}; padding: 40px; border-radius: 20px; 
                    text-align: center; margin: 20px 0; border: 3px solid {border_color};'>
            <div style='font-size: 80px; margin-bottom: 20px;'>{icon}</div>
            <div style='font-size: 32px; font-weight: bold; color: #333; margin-bottom: 15px;'>{encouragement}</div>
            <div style='font-size: 60px; margin: 20px 0;'>{emoji}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.last_score is not None:
            st.markdown(f"""
            <div style='text-align: center; font-size: 20px; color: #666; margin: 10px 0;'>
                發音相似度: {st.session_state.last_score}%
            </div>
            """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 再試一次", use_container_width=True, type="secondary"):
                st.session_state.feedback = ""
                st.session_state.last_score = None
                st.session_state.last_result = None
                st.session_state.phase = "ready"
                st.rerun()
        
        with col2:
            if st.button("⏭️ 跳過這題", use_container_width=True):
                st.session_state.current_index += 1
                st.session_state.feedback = ""
                st.session_state.last_score = None
                st.session_state.last_result = None
                st.session_state.phase = "ready"
                st.rerun()
        
        # 顯示辨識結果
        if st.session_state.last_result:
            with st.expander("🔍 查看辨識詳情"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.info(f"**目標發音:**\n\n`{target_word}`")
                with col_b:
                    st.success(f"**系統聽到:**\n\n`{st.session_state.last_result}`")

# 可愛提示區
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); 
            border-radius: 15px; margin: 20px 0;'>
    <div style='font-size: 40px; margin-bottom: 10px;'>💡</div>
    <div style='font-size: 18px; color: #333;'>
        <b>小提示：</b>錄音時請靠近麥克風，清楚地唸出數字哦！
    </div>
</div>
""", unsafe_allow_html=True)

# 使用說明
with st.expander("📖 使用說明"):
    st.markdown("""
    ### 🎮 操作流程：
    
    1. **設定參數** → 在左側調整數字範圍、錄音時間、容錯等級
    2. **開始練習** → 點擊「🚀 開始練習」
    3. **點擊練習** → 點擊「🎤 開始練習這個數字」
    4. **聽老師發音** → 系統自動播放標準發音
    5. **準備好了** → 看到「換你練習囉！」提示
    6. **開始錄音** → 點擊麥克風按鈕，清楚唸出數字
    7. **自動判斷** → 系統自動辨識並給分
    8. **看結果** → 如果正確就進入下一題，不正確可以再試
    
    ### ⚙️ 參數說明：
    
    - **錄音時間**：建議 3-5 秒，太短可能錄不完整
    - **等待時間**：老師發音後等待多久提示開始，建議 1 秒
    - **容錯等級**：
      - 🟢 寬鬆：幼兒友善，允許發音錯誤
      - 🟡 中等：小學生適用
      - 🔴 嚴格：高年級使用
    
    ### 💡 小技巧：
    
    - 練習前先測試麥克風
    - 找一個安靜的環境
    - 發音要清楚，不要太快也不要太慢
    - 看到鼓勵訊息不要灰心，繼續加油！
    """)
