import streamlit as st
import random
from num2words import num2words
import re
from rapidfuzz import fuzz

st.set_page_config(page_title="闖關自動測試", layout="centered")

st.markdown("<h1 style='text-align:center'>🏁 自動闖關測試</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>模擬小朋友都唸正確英文</p>", unsafe_allow_html=True)

# ------------------------
# Session State
# ------------------------
if "challenge_numbers" not in st.session_state:
    st.session_state.challenge_numbers = random.sample(range(1, 21), 10)
    st.session_state.challenge_index = 0
    st.session_state.challenge_correct = 0
    st.session_state.challenge_finished = False

# ------------------------
# Utils
# ------------------------
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

# ------------------------
# Current Question
# ------------------------
if not st.session_state.challenge_finished:
    number = st.session_state.challenge_numbers[st.session_state.challenge_index]
    target_word = num2words(number).replace("-", " ")
    
    st.markdown(f"### 第 {st.session_state.challenge_index+1} / 10 題")
    st.markdown(f"**數字：{number}**")
    
    # 模擬小朋友回答（都正確）
    answer = target_word
    score = smart_score(target_word, answer)
    
    if score >= 85:
        st.success(f"✅ 發音正確！分數：{score}%")
        st.session_state.challenge_correct += 1
    else:
        st.warning(f"⚠️ 發音不完全正確！分數：{score}%")
    
    if st.button("下一題"):
        st.session_state.challenge_index += 1
        if st.session_state.challenge_index >= 10:
            st.session_state.challenge_finished = True
        st.experimental_rerun()

# ------------------------
# Challenge Finished
# ------------------------
if st.session_state.challenge_finished:
    st.markdown("<h2 style='text-align:center'>🎉 闖關完成！</h2>", unsafe_allow_html=True)
    st.markdown(f"### 成功題數：{st.session_state.challenge_correct}/10")
    
    if st.session_state.challenge_correct >= 8:
        st.markdown("🏆 超厲害！小朋友英文數字高手！")
    elif st.session_state.challenge_correct >= 5:
        st.markdown("⭐ 很棒！繼續加油！")
    else:
        st.markdown("💪 再玩一關一定更好！")
    
    if st.button("重新開始一關"):
        st.session_state.challenge_numbers = random.sample(range(1, 21), 10)
        st.session_state.challenge_index = 0
        st.session_state.challenge_correct = 0
        st.session_state.challenge_finished = False
        st.experimental_rerun()
