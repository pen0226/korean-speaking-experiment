"""
utils.py
시각적 하이라이팅, UI 컴포넌트 및 유틸리티 함수 모듈 (나이트 모드 최적화) - vs 방식 어휘 팁으로 업데이트
"""

import streamlit as st
from streamlit_mic_recorder import mic_recorder
import difflib
import re
from config import EXPERIMENT_STEPS, SUPPORTED_AUDIO_FORMATS, UI_COLORS, EXPERIMENT_QUESTION, AUDIO_QUALITY


def convert_student_to_you(text):
    """
    텍스트에서 'the student' → 'you', 'The student' → 'You', 'their' → 'your'로 변환
    
    Args:
        text: 변환할 텍스트
        
    Returns:
        str: 변환된 텍스트
    """
    if not text:
        return text
    
    # 순서가 중요: 대문자부터 먼저 처리
    text = text.replace('The student', 'You')
    text = text.replace('the student', 'you')
    text = text.replace('their', 'your')
    text = text.replace('Their', 'Your')
    
    return text


def highlight_differences_for_feedback(original, fixed):
    """
    Detailed Feedback용 하이라이트 (나이트 모드 최적화)
    
    Args:
        original: 원본 문장 (학생 답안)
        fixed: 수정된 문장 (모델 답안)
        
    Returns:
        tuple: (highlighted_original, highlighted_fixed)
               - highlighted_original: 삭제된 부분에 빨간 밑줄 (다크모드 대응)
               - highlighted_fixed: 추가/수정된 부분에 굵은 글씨 (다크모드 대응)
    """
    if not original or not fixed:
        return original, fixed
    
    try:
        # 문자 단위로 직접 비교
        matcher = difflib.SequenceMatcher(None, original, fixed)
        
        highlighted_original = []
        highlighted_fixed = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            original_segment = original[i1:i2]
            fixed_segment = fixed[j1:j2]
            
            if tag == 'equal':
                # 동일 부분은 그대로
                highlighted_original.append(original_segment)
                highlighted_fixed.append(fixed_segment)
            elif tag == 'delete':
                # 원본에서 삭제된 부분 - 다크모드 대응 빨간 물결무늬 밑줄
                highlighted_original.append(f'<span style="color: inherit; text-decoration: underline; text-decoration-style: wavy; text-decoration-color: #ef4444; opacity: 0.9;">{original_segment}</span>')
                # fixed에는 해당 부분이 없음
            elif tag == 'insert':
                # fixed에 추가된 부분 - 다크모드 대응 굵은 글씨
                highlighted_fixed.append(f'<strong style="color: inherit; font-weight: bold; opacity: 1;">{fixed_segment}</strong>')
                # original에는 해당 부분이 없음
            elif tag == 'replace':
                # 교체된 부분
                # 원본: 다크모드 대응 빨간 물결무늬 밑줄
                highlighted_original.append(f'<span style="color: inherit; text-decoration: underline; text-decoration-style: wavy; text-decoration-color: #ef4444; opacity: 0.9;">{original_segment}</span>')
                # 수정: 다크모드 대응 굵은 글씨
                highlighted_fixed.append(f'<strong style="color: inherit; font-weight: bold; opacity: 1;">{fixed_segment}</strong>')
        
        return ''.join(highlighted_original), ''.join(highlighted_fixed)
        
    except Exception as e:
        # 오류 시 원본 그대로 반환
        return original, fixed


def highlight_differences(original, fixed):
    """
    두 문장을 비교해서 다른 부분을 하이라이트 (나이트 모드 최적화)
    
    Args:
        original: 원본 문장 (학생 답안)
        fixed: 수정된 문장 (모델 답안)
        
    Returns:
        tuple: (highlighted_original, highlighted_fixed)
               - highlighted_original: 삭제된 부분에 빨간 물결무늬 밑줄 (다크모드 대응)
               - highlighted_fixed: 추가/수정된 부분에 굵은 글씨 (다크모드 대응)
    """
    if not original or not fixed:
        return original, fixed
    
    try:
        # 문자 단위로 직접 비교
        matcher = difflib.SequenceMatcher(None, original, fixed)
        
        highlighted_original = []
        highlighted_fixed = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            original_segment = original[i1:i2]
            fixed_segment = fixed[j1:j2]
            
            if tag == 'equal':
                # 동일 부분은 그대로
                highlighted_original.append(original_segment)
                highlighted_fixed.append(fixed_segment)
            elif tag == 'delete':
                # 원본에서 삭제된 부분 - 다크모드 대응 빨간 물결무늬 밑줄
                highlighted_original.append(f'<span style="color: inherit; text-decoration: underline; text-decoration-style: wavy; text-decoration-color: #ef4444; opacity: 0.9;">{original_segment}</span>')
                # fixed에는 해당 부분이 없음
            elif tag == 'insert':
                # fixed에 추가된 부분 - 다크모드 대응 굵은 글씨
                highlighted_fixed.append(f'<strong style="color: inherit; font-weight: bold; opacity: 1;">{fixed_segment}</strong>')
                # original에는 해당 부분이 없음
            elif tag == 'replace':
                # 교체된 부분
                # 원본: 다크모드 대응 빨간 물결무늬 밑줄
                highlighted_original.append(f'<span style="color: inherit; text-decoration: underline; text-decoration-style: wavy; text-decoration-color: #ef4444; opacity: 0.9;">{original_segment}</span>')
                # 수정: 다크모드 대응 굵은 글씨
                highlighted_fixed.append(f'<strong style="color: inherit; font-weight: bold; opacity: 1;">{fixed_segment}</strong>')
        
        return ''.join(highlighted_original), ''.join(highlighted_fixed)
        
    except Exception as e:
        # 오류 시 원본 그대로 반환
        return original, fixed


def parse_grammar_issue(issue_text):
    """
    문법 이슈 텍스트를 파싱하여 구성요소 추출
    
    Args:
        issue_text: "error_type|original|fix|explanation" 형태의 문자열
        
    Returns:
        dict: 파싱된 구성요소
    """
    if '|' in issue_text:
        parts = issue_text.split('|')
        if len(parts) >= 4:
            return {
                'error_type': parts[0].strip(),
                'original': parts[1].strip(),
                'fix': parts[2].strip(),
                'explanation': parts[3].strip()
            }
    
    # 기존 형식 처리 (fallback)
    if "❗️" in issue_text and "Original:" in issue_text and "→" in issue_text:
        try:
            error_type = issue_text.split("❗️")[1].split("\\n")[0].strip()
            original = issue_text.split("Original:")[1].split("→")[0].strip().strip("'\"")
            fix_part = issue_text.split("→ Fix:")[1] if "→ Fix:" in issue_text else issue_text.split("→")[1]
            fix = fix_part.split("\\n🧠")[0].strip().strip("'\"")
            
            explanation = "Review this grammar point"
            if "🧠" in fix_part:
                explanation = fix_part.split("🧠")[1].strip()
                # "Simple explanation:" 제거
                explanation = explanation.replace("Simple explanation: ", "")
                explanation = explanation.replace("Simple explanation:", "")
            
            return {
                'error_type': error_type,
                'original': original,
                'fix': fix,
                'explanation': explanation
            }
        except:
            pass
    
    # 기본값 반환
    return {
        'error_type': 'Grammar',
        'original': 'Example text',
        'fix': 'Corrected text',
        'explanation': 'Review this grammar point'
    }


def parse_vocabulary_suggestion(suggestion):
    """
    어휘 제안을 파싱해서 구성요소 추출 (vs 방식으로 업데이트)
    
    Args:
        suggestion: 어휘 제안 텍스트 (❓ **A vs B** 형태)
        
    Returns:
        dict: 파싱된 구성요소들
    """
    result = {
        'title': "Word vs Word",
        'word_a': "Word A",
        'explanation_a': "Explanation for word A",
        'word_b': "Word B", 
        'explanation_b': "Explanation for word B",
        'examples': "Example sentences",
        'key_point': "Key difference"
    }
    
    try:
        # vs 방식 포맷 파싱
        lines = suggestion.replace('\\n', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('❓ **') and ' vs ' in line:
                # 제목 추출: ❓ **공부하다 vs 배우다**
                title_text = line.replace('❓ **', '').replace('**', '')
                result['title'] = title_text
                
                # 개별 단어 추출
                if ' vs ' in title_text:
                    words = title_text.split(' vs ')
                    if len(words) >= 2:
                        result['word_a'] = words[0].strip()
                        result['word_b'] = words[1].strip()
            
            elif line.startswith('💡 ') and result['word_a'] != "Word A":
                # 첫 번째 💡 = word_a 설명, 두 번째 💡 = word_b 설명
                explanation = line.replace('💡 ', '').strip()
                
                if result['word_a'] in line:
                    # word_a에 대한 설명
                    result['explanation_a'] = explanation.replace(f"{result['word_a']}: ", "")
                elif result['word_b'] in line:
                    # word_b에 대한 설명  
                    result['explanation_b'] = explanation.replace(f"{result['word_b']}: ", "")
                elif result['explanation_a'] == "Explanation for word A":
                    # 첫 번째 💡
                    result['explanation_a'] = explanation
                elif result['explanation_b'] == "Explanation for word B":
                    # 두 번째 💡
                    result['explanation_b'] = explanation
            
            elif line.startswith('🟢 '):
                result['examples'] = line.replace('🟢 ', '').strip()
            
            elif line.startswith('📝 '):
                result['key_point'] = line.replace('📝 ', '').strip()
        
        # 기본값 처리
        for key, value in result.items():
            if not value or value in ['❓', '💡', '🟢', '📝']:
                if key == 'title':
                    result[key] = "Word vs Word"
                elif key == 'word_a':
                    result[key] = "Word A"
                elif key == 'word_b':
                    result[key] = "Word B"
                elif key in ['explanation_a', 'explanation_b']:
                    result[key] = "Explanation needed"
                elif key == 'examples':
                    result[key] = "Examples needed"
                elif key == 'key_point':
                    result[key] = "Key difference"
                    
    except Exception:
        pass
    
    return result


def parse_sentence_connection_tip(tip_text):
    """
    문장 연결 팁을 파싱하여 구성요소 추출
    
    Args:
        tip_text: 문장 연결 팁 텍스트
        
    Returns:
        dict: 파싱된 구성요소들
    """
    result = {
        'title': "Tip for Longer Sentences",
        'before_sentences': "Short sentences",
        'after_sentence': "Combined sentence", 
        'explanation': "Use connectives to sound more natural"
    }
    
    try:
        # 줄바꿈 처리
        lines = tip_text.replace('\\n', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('🎯') and 'Tip for Longer Sentences' in line:
                # 제목 추출
                result['title'] = "Tip for Longer Sentences"
            
            elif line.startswith('❌'):
                # Before 문장들 추출
                result['before_sentences'] = line.replace('❌ ', '').strip()
            
            elif line.startswith('✅'):
                # After 문장 추출
                result['after_sentence'] = line.replace('✅ ', '').strip()
            
            elif line.startswith('💡'):
                # 설명 추출
                result['explanation'] = line.replace('💡 ', '').strip()
    
    except Exception:
        pass
    
    return result


def display_vocabulary_tips_simplified(feedback):
    """
    어휘 팁을 간단한 텍스트 형태로 표시 (박스 제거, 텍스트 간소화)
    
    Args:
        feedback: 피드백 딕셔너리
    """
    vocab_suggestions = feedback.get('vocabulary_suggestions', [])
    
    if not vocab_suggestions:
        return
    
    for i, suggestion in enumerate(vocab_suggestions[:3], 1):  # 최대 3개
        parsed = parse_vocabulary_suggestion(suggestion)
        
        # 간단한 텍스트 형태로 변경
        st.markdown(f"**{parsed['title']}**")
        st.markdown(f"• **{parsed['word_a']}**: {parsed['explanation_a']}")
        st.markdown(f"• **{parsed['word_b']}**: {parsed['explanation_b']}")
        
        # 예문 표시
        if parsed['examples']:
            st.markdown(f"🟢 **Examples:** {parsed['examples']}")
        
        # 핵심 포인트 표시
        if parsed['key_point']:
            st.markdown(f"📝 **Key Point:** {parsed['key_point']}")
        
        st.markdown("")  # 간격 추가


def show_progress_indicator(current_step):
    """
    현재 단계를 표시하는 진행 상황 인디케이터 (나이트 모드 최적화)
    
    Args:
        current_step: 현재 단계 키
    """
    current_info = EXPERIMENT_STEPS.get(current_step, ('Step ?', 'Unknown'))
    
    # 🔥 completion 단계 특별 처리 (나이트 모드 최적화)
    if current_step == 'completion':
        st.markdown(
            f"""
            <div style='
                margin-bottom: 20px; 
                padding: 15px; 
                background: rgba(34, 197, 94, 0.1); 
                border-radius: 10px; 
                border-left: 4px solid #22c55e;
                color: inherit;
            '>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <strong style='color: #22c55e; font-size: 16px;'>{current_info[0]}: {current_info[1]}</strong>
                    </div>
                    <div style='color: inherit; opacity: 0.7; font-size: 14px;'>
                        Progress: Complete ✅
                    </div>
                </div>
                <div style='margin-top: 10px; background-color: #22c55e; height: 6px; border-radius: 3px; width: 100%;'>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return
    
    # 일반 단계 처리 (나이트 모드 최적화)
    try:
        step_num = int(current_info[0].split()[1])
    except:
        step_num = 1
    
    progress_percentage = (step_num / 6) * 100
    
    st.markdown(
        f"""
        <div style='
            margin-bottom: 20px; 
            padding: 15px; 
            background: rgba(59, 130, 246, 0.1); 
            border-radius: 10px; 
            border-left: 4px solid #3b82f6;
            color: inherit;
        '>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <strong style='color: #3b82f6; font-size: 16px;'>{current_info[0]} of 6: {current_info[1]}</strong>
                </div>
                <div style='color: inherit; opacity: 0.7; font-size: 14px;'>
                    Progress: {step_num}/6
                </div>
            </div>
            <div style='margin-top: 10px; background: rgba(255, 255, 255, 0.2); height: 6px; border-radius: 3px;'>
                <div style='background-color: #3b82f6; height: 6px; border-radius: 3px; width: {progress_percentage}%;'></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def display_question(step_context=""):
    """
    통일된 질문 표시 함수 (나이트 모드 최적화)
    
    Args:
        step_context: 단계 맥락 설명
    """
    if step_context:
        st.markdown(f"#### {step_context}")
    
    st.markdown(
        f"""<div style='
            padding: 20px; 
            background: rgba(0, 0, 0, 0.05); 
            border: 1px solid rgba(128, 128, 128, 0.3); 
            border-radius: 8px; 
            margin: 15px 0; 
            text-align: center;
            color: inherit;
        '>
        <h3 style='color: inherit; margin: 0; font-size: 20px; opacity: 0.9;'>{EXPERIMENT_QUESTION}</h3>
        </div>""",
        unsafe_allow_html=True
    )


def record_audio(key, label):
    """
    간소화된 녹음 인터페이스 (실시간 타이머 - 독립 버튼 방식)
    - 타이머는 iframe 내부 JS로 동작
    - 사용자 절차: Start Timer → Start Recording → Stop Recording → Stop Timer
    """
    import streamlit.components.v1 as components
    
    # 안내 메시지
    st.warning("🎙️ **Step 1:** Start Timer → **Step 2:** Start Recording → **Step 3:** Stop Recording → **Step 4:** Stop Timer")
    
    # 좌우 배치: 타이머 / 녹음 버튼
    col_timer, col_rec = st.columns([1, 2])
    
    with col_timer:
        timer_html = """
        <div style="font-family: system-ui, -apple-system, sans-serif;">
            <div id="timer" style="
                display:none; 
                margin-bottom:10px; 
                padding:12px; 
                text-align:center; 
                font-size:20px;
                font-weight:700; 
                border-radius:8px; 
                background:#eef2ff; 
                color:#3730a3;
                transition: all 0.3s;">
                ⏱️ <span id="t">0:00</span>
            </div>
            <div style="display:flex; gap:8px;">
                <button id="startBtn" style="
                    flex:1; 
                    padding:10px; 
                    border-radius:8px; 
                    border:1px solid #10b981; 
                    background:#d1fae5;
                    font-weight:600;
                    cursor:pointer;">
                    ▶️ Start Timer
                </button>
                <button id="stopBtn" style="
                    flex:1; 
                    padding:10px; 
                    border-radius:8px; 
                    border:1px solid #ef4444; 
                    background:#fee2e2;
                    font-weight:600;
                    cursor:pointer;">
                    ⏸️ Stop Timer
                </button>
            </div>
        </div>
        
        <script>
        let s=0, h=null;
        const timerDiv = document.getElementById('timer');
        const timeSpan = document.getElementById('t');
        
        const view = () => {
            const m = Math.floor(s/60);
            const sec = String(s%60).padStart(2,'0');
            timeSpan.textContent = m + ":" + sec;
            
            // 시간별 색상 변경 (1-2분 목표)
            if(s < 60) {
                timerDiv.style.background = '#fee2e2';  // 빨강 (1분 미만)
                timerDiv.style.color = '#dc2626';
            } else if(s < 90) {
                timerDiv.style.background = '#fed7aa';  // 주황 (1-1.5분)
                timerDiv.style.color = '#ea580c';
            } else {
                timerDiv.style.background = '#bbf7d0';  // 초록 (1.5분+)
                timerDiv.style.color = '#059669';
            }
        };
        
        const start = () => {
            if(h) return;  // 이미 실행중이면 무시
            s = 0;
            view();
            timerDiv.style.display = 'block';
            h = setInterval(() => {
                s++;
                view();
            }, 1000);
        };
        
        const stop = () => {
            if(h) {
                clearInterval(h);
                h = null;
            }
            // 타이머는 계속 표시 (시간 확인용)
        };
        
        document.getElementById('startBtn').onclick = start;
        document.getElementById('stopBtn').onclick = stop;
        </script>
        """
        components.html(timer_html, height=130)
    
    with col_rec:
        # 마이크 녹음
        audio = mic_recorder(
            start_prompt="🎙️ Start Recording",
            stop_prompt="⏹️ Stop Recording",
            format="wav",
            just_once=True,
            use_container_width=True,
            key=key
        )
    
    # 결과 처리
    if audio:
        st.success("✅ Recording captured successfully.")
        st.audio(audio["bytes"])
        return audio, "recording"
    
    # 파일 업로드 옵션
    uploaded_file = st.file_uploader(
        "Or upload an audio file:", 
        type=SUPPORTED_AUDIO_FORMATS, 
        key=f"{key}_upload"
    )
    
    if uploaded_file:
        st.success("✅ Audio file uploaded successfully.")
        st.audio(uploaded_file.read())
        uploaded_file.seek(0)
        return uploaded_file, "upload"
    
    return None, None

def display_transcription_with_highlights(transcription, feedback, title="What You Said", audio_data=None):
    """
    전사 텍스트를 하이라이트와 함께 표시 (나이트 모드 최적화)
    
    Args:
        transcription: 전사된 텍스트
        feedback: 피드백 딕셔너리
        title: 섹션 제목
        audio_data: 오디오 데이터 (선택사항)
    """
    st.markdown(f"#### {title}")
    st.markdown("*Here's what you said — compare it with the model answer in the green box below.*")
    
    # 음성 재생 부분
    if audio_data:
        st.markdown("**🎤 Listen to your recording**")
        st.markdown("")  # 오디오 플레이어 위쪽 여백
        if hasattr(audio_data, 'read'):
            # 업로드된 파일인 경우
            audio_data.seek(0)
            st.audio(audio_data.read())
            audio_data.seek(0)
        else:
            # 녹음된 파일인 경우
            st.audio(audio_data['bytes'])
        st.markdown("")  # 오디오 플레이어 아래쪽 여백
    
    # 하이라이트된 학생 답안 표시 (나이트 모드 최적화)
    st.markdown("**💬 Your Answer**")
    
    # 모델 문장과 비교해서 하이라이트 생성
    model_sentence = feedback.get('suggested_model_sentence', '')
    if model_sentence:
        highlighted_student, _ = highlight_differences(transcription, model_sentence)
        
        st.markdown(
            f"""
            <div style='
                background: rgba(252, 165, 165, 0.15);
                border: 2px solid #fca5a5;
                border-radius: 8px;
                padding: 20px;
                margin: 3px 0 15px 0;
                color: inherit;
            '>
                <div style='font-size: 16px; line-height: 1.6; color: inherit;'>
                    {highlighted_student}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # 피드백이 없는 경우 기본 표시 (나이트 모드 최적화)
        st.markdown(
            f"""<div style='
                padding: 20px; 
                border: 1px solid rgba(128, 128, 128, 0.3); 
                border-radius: 8px; 
                background: rgba(0, 0, 0, 0.05); 
                margin: 15px 0;
                color: inherit;
            '>
            <div style='font-size: 18px; line-height: 1.8; color: inherit;'>
            {transcription}
            </div>
            </div>""",
            unsafe_allow_html=True
        )


def display_model_sentence_with_highlights(model_sentence, feedback, title="Suggested Model Sentence"):
    """
    모델 문장을 하나의 박스에 한국어와 영어를 함께 표시 (나이트 모드 최적화)
    
    Args:
        model_sentence: 모델 문장
        feedback: 피드백 딕셔너리
        title: 섹션 제목
    """
    st.markdown(f"#### {title}")
    st.markdown("*This is how you could say it better in an interview:*")
    
    # 영어 번역 가져오기
    english_translation = feedback.get('suggested_model_sentence_english', '')
    
    # 하나의 통합된 박스에 한국어와 영어 모두 표시 (나이트 모드 최적화)
    with st.container():
        if english_translation:
            # 한국어와 영어를 하나의 박스에 통합 (나이트 모드 최적화)
            st.markdown(
                f"""<div style='
                    padding: 20px; 
                    border: 2px solid #10b981; 
                    border-radius: 8px; 
                    background: rgba(16, 185, 129, 0.1); 
                    margin: 15px 0;
                    color: inherit;
                '>
                <div style='font-size: 18px; line-height: 1.6; color: inherit; margin-bottom: 12px;'>
                {model_sentence}
                </div>
                <div style='font-size: 14px; color: #10b981; font-style: italic; padding-top: 8px; border-top: 1px solid #10b981;'>
                "{english_translation}"
                </div>
                </div>""",
                unsafe_allow_html=True
            )
        else:
            # 영어 번역이 없으면 한국어만 표시 (나이트 모드 최적화)
            st.markdown(
                f"""<div style='
                    padding: 20px; 
                    border: 2px solid #10b981; 
                    border-radius: 8px; 
                    background: rgba(16, 185, 129, 0.1); 
                    margin: 15px 0;
                    color: inherit;
                '>
                <div style='font-size: 18px; line-height: 1.6; color: inherit; margin-bottom: 0;'>
                {model_sentence}
                </div>
                </div>""",
                unsafe_allow_html=True
            )


def format_feedback_content(content):
    """
    피드백 내용을 깔끔하게 포맷팅 (개선된 줄바꿈 처리)
    
    Args:
        content: 원본 피드백 내용
        
    Returns:
        str: HTML로 포맷팅된 내용
    """
    if not content:
        return ""
    
    # 줄바꿈 처리 개선 (\\n과 \n 모두 처리)
    formatted = content.replace('\\n', '<br>')  # 이스케이프된 줄바꿈
    formatted = formatted.replace('\n', '<br>')   # 실제 줄바꿈
    
    # "Simple explanation:" 문구 제거
    formatted = formatted.replace('Simple explanation: ', '')
    formatted = formatted.replace('💡 Simple explanation: ', '💡 ')
    
    # 이모지와 강조 표시 기본 처리
    formatted = formatted.replace('💡', '<span style="color: #f59e0b;">💡</span>')
    formatted = formatted.replace('📝', '<span style="color: #3b82f6;">📝</span>')
    formatted = formatted.replace('🎯', '<span style="color: #10b981;">🎯</span>')
    formatted = formatted.replace('⚠️', '<span style="color: #ef4444;">⚠️</span>')
    formatted = formatted.replace('✅', '<span style="color: #10b981;">✅</span>')
    formatted = formatted.replace('💬', '<span style="color: #8b5cf6;">💬</span>')
    formatted = formatted.replace('🧠', '<span style="color: #6366f1;">🧠</span>')
    formatted = formatted.replace('❗️', '<span style="color: #ef4444;">❗️</span>')
    formatted = formatted.replace('💭', '<span style="color: #ec4899;">💭</span>')
    formatted = formatted.replace('🚀', '<span style="color: #3b82f6;">🚀</span>')
    
    # **굵은 글씨** 처리 (나이트 모드 최적화)
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: inherit; font-weight: bold;">\1</strong>', formatted)
    
    # 중복 줄바꿈 정리
    formatted = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted)
    
    return formatted


def format_detailed_feedback(content):
    """
    🔥 Detailed Feedback 전용 포맷팅 함수 (구조화된 박스 스타일, 나이트 모드 최적화)
    
    Args:
        content: 원본 detailed feedback 텍스트
        
    Returns:
        str: 구조화된 HTML 형태로 포맷팅된 내용
    """
    if not content:
        return ""
    
    # 기본 줄바꿈 처리
    formatted = content.replace('\\n', '\n')
    
    # 🚩, 🌟, 🎯, 📝 섹션별로 분리
    sections = {
        'task_check': '',
        'what_you_did_well': '',
        'key_improvements': '',
        'improved_examples': ''
    }
    
    # 섹션 구분자로 텍스트 분리
    current_section = None
    lines = formatted.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 섹션 헤더 감지 - 헤더는 건너뛰기
        if '🚩' in line or 'Task Completion Check' in line:
            current_section = 'task_check'
            continue  # 헤더는 건너뛰기
        elif '🌟' in line or 'What You Did Well' in line:
            current_section = 'what_you_did_well'
            continue  # 헤더는 건너뛰기
        elif '🎯' in line or 'Key Improvements' in line or 'Things to Improve' in line:
            current_section = 'key_improvements'
            continue  # 헤더는 건너뛰기
        elif '📝' in line or 'Try This Next Time' in line:
            current_section = 'improved_examples'
            continue  # 헤더는 건너뛰기
        else:
            # 현재 섹션에 내용 추가
            if current_section:
                sections[current_section] += line + '\n'
    
    # 섹션별로 HTML 구조화 (나이트 모드 최적화)
    html_parts = []
    
    # 🚩 Task Completion Check 섹션 (새로 추가)
    if sections['task_check'].strip():
        task_content = format_task_check_items(sections['task_check'].strip())
        html_parts.append(f"""
        <div style="margin-bottom: 15px; padding: 12px; background: rgba(251, 191, 36, 0.1); border-left: 3px solid #fbbf24; border-radius: 5px;">
            <div style="font-weight: bold; color: #f59e0b; margin-bottom: 8px; font-size: 15px;">
                🚩 Task Completion Check:
            </div>
            <div style="color: inherit; line-height: 1.5; font-size: 15px;">
                {task_content}
            </div>
        </div>
        """)
    
    # 🌟 What You Did Well 섹션
    if sections['what_you_did_well'].strip():
        well_content = format_bullet_points(sections['what_you_did_well'].strip())
        html_parts.append(f"""
        <div style="margin-bottom: 15px;">
            <div style="font-weight: bold; color: #059669; margin-bottom: 8px; font-size: 15px;">
                🌟 What You Did Well:
            </div>
            <div style="color: inherit; line-height: 1.5; font-size: 16px;">
                {well_content}
            </div>
        </div>
        """)
    
    # 🎯 Key Improvements 섹션
    if sections['key_improvements'].strip():
        improvements_content = format_bullet_points(sections['key_improvements'].strip())
        html_parts.append(f"""
        <div style="margin-bottom: 15px;">
            <div style="font-weight: bold; color: #0369a1; margin-bottom: 8px; font-size: 15px;">
                🎯 Key Improvements:
            </div>
            <div style="color: inherit; line-height: 1.5; font-size: 16px;">
                {improvements_content}
            </div>
        </div>
        """)
    
    # 📝 Improved Examples 섹션
    if sections['improved_examples'].strip():
        examples_content = format_bullet_points(sections['improved_examples'].strip())
        html_parts.append(f"""
        <div style="margin-bottom: 10px;">
            <div style="font-weight: bold; color: #7c3aed; margin-bottom: 8px; font-size: 15px;">
                📝 Try This Next Time:
            </div>
            <div style="color: inherit; line-height: 1.5; font-size: 16px;">
                {examples_content}
            </div>
        </div>
        """)
    
    # 모든 섹션이 비어있으면 원본 텍스트 반환 (나이트 모드 최적화)
    if not any(sections.values()):
        return f'<div style="color: inherit; line-height: 1.5; font-size: 16px;">{format_bullet_points(formatted)}</div>'
    
    return ''.join(html_parts)


def format_task_check_items(text):
    """
    Task Completion Check 항목 포맷팅 (✅/❌ 체크마크 강조)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 포맷팅된 HTML
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line or line == '-':
            continue
        
        # - 제거
        if line.startswith('- '):
            line = line[2:]
        
        # ✅와 ❌ 스타일 적용
        if '✅' in line:
            line = line.replace('✅', '<span style="color: #22c55e; font-weight: bold;">✅</span>')
        if '❌' in line:
            line = line.replace('❌', '<span style="color: #ef4444; font-weight: bold;">❌</span>')
        if '⚠️' in line:
            line = line.replace('⚠️', '<span style="color: #f59e0b; font-weight: bold;">⚠️</span>')
        
        # Past vacation, Future plans 등 키워드 강조
        line = line.replace('Past vacation:', '<strong>Past vacation:</strong>')
        line = line.replace('Future plans:', '<strong>Future plans:</strong>')
        line = line.replace('Tense usage:', '<strong>Tense usage:</strong>')
        
        formatted_lines.append(line)
    
    return '<br>'.join(formatted_lines)


def format_bullet_points(text):
    """
    • 기호를 기준으로 리스트 형태로 포맷팅
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 포맷팅된 HTML
    """
    if not text:
        return ""
    
    # • 기호를 기준으로 분리
    if '•' in text:
        parts = text.split('•')
        formatted_parts = []
        
        # 첫 번째 부분 (• 앞의 텍스트)
        if parts[0].strip():
            formatted_parts.append(parts[0].strip())
        
        # • 기호가 있는 부분들
        for part in parts[1:]:
            if part.strip():
                formatted_parts.append(f"• {part.strip()}")
        
        return '<br>'.join(formatted_parts)
    else:
        # • 기호가 없으면 그대로 반환
        return text.replace('\n', '<br>')


def format_content_ideas(content):
    """
    Content Ideas와 Advanced Grammar Pattern의 줄바꿈 처리 개선 (새로운 포맷 적용, 나이트 모드 최적화)
    
    Args:
        content: 원본 content 텍스트
        
    Returns:
        str: 새로운 포맷으로 처리된 텍스트
    """
    if not content:
        return ""
    
    # 기본 줄바꿈 처리
    formatted = content.replace('\\n', '<br>')
    formatted = formatted.replace('\n', '<br>')
    
    # === Content Ideas 포맷 처리 ===
    # 패턴: 💬 Topic: [토픽명] 📝 Example: [한국어] '[영어]'
    # 결과: 💬 **[토픽명]** 📝 [한국어] *'[영어]'*
    
    # Content Ideas 패턴 매칭 및 변환
    content_pattern = r'💬\s*Topic:\s*(.*?)<br>📝\s*Example:\s*(.*?)<br>\s*\'(.*?)\''
    
    def replace_content_format(match):
        topic = match.group(1).strip()
        korean_example = match.group(2).strip()
        english_translation = match.group(3).strip()
        
        return f'💬 **{topic}**<br>📝 {korean_example}<br><span style="margin-left:20px; color: inherit; opacity: 0.7; font-style:italic;">*\'{english_translation}\'*</span>'
    
    formatted = re.sub(content_pattern, replace_content_format, formatted)
    
    # === Advanced Grammar Pattern 포맷 처리 ===
    # 패턴: 🚀 Try this: '[패턴]' = '[의미]' 📝 Example: '[예시]' 💡 When to use: [설명]
    # 결과: 🚀 Try this: **'[패턴]'** = '[의미]' 📝 '[예시]' 💡 [설명]
    
    # Advanced Pattern 포맷 개선
    advanced_pattern1 = r'🚀\s*Try:\s*(.*?)<br>📝\s*Example:\s*(.*?)<br>💡\s*When to use:\s*(.*?)(?=<br>|$)'
    advanced_pattern2 = r'🚀\s*Try this:\s*(.*?)<br>📝\s*Example:\s*(.*?)<br>💡\s*When to use:\s*(.*?)(?=<br>|$)'
    
    def replace_advanced_format(match):
        pattern_desc = match.group(1).strip()
        example = match.group(2).strip()
        usage = match.group(3).strip()
        
        # 패턴 부분에서 큰따옴표나 작은따옴표로 감싸진 부분을 굵게 만들기
        pattern_desc = re.sub(r"'([^']+)'", r"**'\1'**", pattern_desc)
        pattern_desc = re.sub(r'"([^"]+)"', r'**"\1"**', pattern_desc)
        
        return f'🚀 Try this: {pattern_desc}<br>📝 {example}<br>💡 {usage}'
    
    formatted = re.sub(advanced_pattern1, replace_advanced_format, formatted)
    formatted = re.sub(advanced_pattern2, replace_advanced_format, formatted)
    
    # === 기존 포맷 처리 (fallback) ===
    # 영어 번역 줄: '…' 만 골라 들여쓰기 + 이탤릭 처리 (나이트 모드 최적화)
    formatted = re.sub(
        r"<br>\s*'(.*?)'",
        r"<br><span style='margin-left:20px; color: inherit; opacity: 0.7; font-style:italic;'>'\g<1>'</span>",
        formatted
    )
    
    # "Example: " 제거 (남아있는 경우)
    formatted = formatted.replace('Example: ', '')
    formatted = formatted.replace('When to use: ', '')
    
    return formatted


def display_grammar_tips_simplified(feedback):
    """
    간소화된 문법 팁 표시 (문자 단위 차이점 강조 + 3개 기본 + 더보기) - Streamlit expander 사용
    
    Args:
        feedback: 피드백 딕셔너리
    """
    grammar_issues = feedback.get('grammar_issues', [])
    
    if not grammar_issues:
        return
    
    # Streamlit expander를 사용하여 회색 박스 효과
    with st.expander("📝 Grammar Tips", expanded=True):
        st.markdown("*Areas where you can improve your Korean grammar:*")
        
        # 기본 3개 표시
        basic_issues = grammar_issues[:3]
        for i, issue in enumerate(basic_issues, 1):
            parsed = parse_grammar_issue(issue)
            
            # 문자 단위 차이점 강조 (Detailed Feedback용)
            highlighted_original, highlighted_fixed = highlight_differences_for_feedback(
                parsed['original'], 
                parsed['fix']
            )
            
            # Streamlit 마크다운으로 표시 (HTML 허용)
            st.markdown(f"**#{i} {parsed['error_type']}**")
            st.markdown(f"❌ {highlighted_original}", unsafe_allow_html=True)
            st.markdown(f"✅ {highlighted_fixed}", unsafe_allow_html=True)
            st.markdown(f"💡 {parsed['explanation']}")
            st.markdown("")  # 간격 추가
        
        # 더보기 기능 (3개 이상인 경우)
        if len(grammar_issues) > 3:
            # 더보기 상태 관리
            if 'show_more_grammar' not in st.session_state:
                st.session_state.show_more_grammar = False
            
            # 더보기 버튼
            if not st.session_state.show_more_grammar:
                if st.button("📖 Show More Grammar Tips", key="show_more_grammar_btn"):
                    st.session_state.show_more_grammar = True
                    st.rerun()
            else:
                # 추가 문법 팁 표시 (4번부터 끝까지)
                additional_issues = grammar_issues[3:]
                for i, issue in enumerate(additional_issues, 4):
                    parsed = parse_grammar_issue(issue)
                    
                    # 문자 단위 차이점 강조 (Detailed Feedback용)
                    highlighted_original, highlighted_fixed = highlight_differences_for_feedback(
                        parsed['original'], 
                        parsed['fix']
                    )
                    
                    # Streamlit 마크다운으로 표시 (HTML 허용)
                    st.markdown(f"**#{i} {parsed['error_type']}**")
                    st.markdown(f"❌ {highlighted_original}", unsafe_allow_html=True)
                    st.markdown(f"✅ {highlighted_fixed}", unsafe_allow_html=True)
                    st.markdown(f"💡 {parsed['explanation']}")
                    st.markdown("")  # 간격 추가
                
                # 접기 버튼
                if st.button("📖 Show Less", key="show_less_grammar_btn"):
                    st.session_state.show_more_grammar = False
                    st.rerun()


def display_improvement_metrics(improvement_assessment):
    """
    개선도 메트릭을 시각적으로 표시
    
    Args:
        improvement_assessment: 개선도 평가 딕셔너리
    """
    if not improvement_assessment:
        return
    
    score = improvement_assessment.get('improvement_score', 0)
    first_score = improvement_assessment.get('first_attempt_score', 0)
    second_score = improvement_assessment.get('second_attempt_score', 0)
    
    # 메트릭 표시
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if first_score > 0:
            st.metric("First Attempt", f"{first_score}/10", help="STT-based rubric score")
    
    with col2:
        if second_score > 0:
            difference = second_score - first_score if first_score > 0 else 0
            st.metric("Second Attempt", f"{second_score}/10", f"{difference:+.1f}")
    
    with col3:
        if score >= 8:
            st.metric("Improvement", "Excellent", f"{score}/10")
        elif score >= 6:
            st.metric("Improvement", "Good", f"{score}/10")
        elif score >= 4:
            st.metric("Improvement", "Fair", f"{score}/10")
        else:
            st.metric("Improvement", "Needs Practice", f"{score}/10")


def display_improvement_details(improvement_assessment):
    """
    개선도 상세 내용을 간단하게 표시 ('the student' → 'you' 변환 추가)
    
    Args:
        improvement_assessment: 개선도 평가 딕셔너리
    """
    if not improvement_assessment:
        return
    
    st.markdown("### 📈 Your Progress Analysis")
    
    # 기본 분석만 표시 (텍스트 변환 적용)
    if improvement_assessment.get('improvement_reason'):
        analysis_text = convert_student_to_you(improvement_assessment['improvement_reason'])
        st.info(f"📋 **Analysis:** {analysis_text}")
    
    # 전체 평가만 표시 (텍스트 변환 적용)
    if improvement_assessment.get('overall_assessment'):
        overall_text = convert_student_to_you(improvement_assessment['overall_assessment'])
        st.info(f"🎯 **Overall Summary:** {overall_text}")


def display_audio_comparison(first_audio, second_audio, duration1=0, duration2=0):
    """
    두 음성을 비교 표시 (2분 기준)
    
    Args:
        first_audio: 첫 번째 오디오 데이터
        second_audio: 두 번째 오디오 데이터
        duration1: 첫 번째 음성 길이
        duration2: 두 번째 음성 길이
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎤 First Attempt")
        if duration1 > 0:
            duration_status = get_duration_status(duration1)
            st.caption(f"Duration: {duration1:.1f}s ({duration_status})")
        if first_audio:
            if hasattr(first_audio, 'read'):
                # 업로드된 파일인 경우
                first_audio.seek(0)
                st.audio(first_audio.read())
                first_audio.seek(0)
            else:
                # 녹음된 파일인 경우
                st.audio(first_audio['bytes'])
    
    with col2:
        st.markdown("#### 🎤 Second Attempt")
        if duration2 > 0:
            duration_status = get_duration_status(duration2)
            st.caption(f"Duration: {duration2:.1f}s ({duration_status})")
        if second_audio:
            if hasattr(second_audio, 'read'):
                # 업로드된 파일인 경우
                second_audio.seek(0)
                st.audio(second_audio.read())
                second_audio.seek(0)
            else:
                # 녹음된 파일인 경우
                st.audio(second_audio['bytes'])


def get_duration_status(duration):
    """
    음성 길이 상태 반환 (1-2분 목표로 수정)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        str: 상태 설명
    """
    # config.py의 AUDIO_QUALITY 기준을 직접 활용하여 일관성을 높입니다.
    TARGET_EXCELLENT_DURATION = AUDIO_QUALITY["excellent_min_duration"] # 90초 (1.5분)
    TARGET_GOOD_DURATION = AUDIO_QUALITY["good_min_duration"] # 75초 (1분 15초)
    TARGET_FAIR_DURATION = AUDIO_QUALITY["fair_min_duration"] # 60초 (1분)

    if duration >= TARGET_EXCELLENT_DURATION: # 90초 이상
        return f"✅ Excellent! {duration:.1f}s — a perfect length (1-2 minutes) for the interview!"
    elif duration >= TARGET_GOOD_DURATION: # 75초 이상
        return f"🌟 Good! {duration:.1f}s — almost reached the 1-2 minute goal!"
    elif duration >= TARGET_FAIR_DURATION: # 60초 이상
        return f"⚠️ Fair! {duration:.1f}s — try for at least 1-2 minutes next time."
    else:
        return f"❌ Short! {duration:.1f}s — aim for at least 1-2 minutes for a better score."


def display_contact_info(session_id):
    """
    연락처 정보 표시
    
    Args:
        session_id: 세션 ID
    """
    st.markdown("### 📞 Contact Information")
    st.write("**For any questions or data requests:**")
    st.write("📧 Email: pen0226@gmail.com")
    st.write(f"📋 Subject: Korean Speaking Research - {session_id}")


def setup_sidebar():
    """
    사이드바 설정
    """
    with st.sidebar:
        st.title("🇰🇷 Korean Speaking Practice")
        
        # 시스템 상태 표시
        st.markdown("**⚙️ System Status:**")
        st.write("Recording: ✅ Ready")
        
        # API 상태 확인
        from config import OPENAI_API_KEY
        if OPENAI_API_KEY:
            st.write("AI Feedback: ✅ Ready")
        else:
            st.write("AI Feedback: ❌ Not Ready")
        
        # TTS 상태 확인
        try:
            from tts import display_tts_status
            display_tts_status()
        except ImportError:
            st.write("AI Model Voice: ❓ Module not loaded")
        
        # 세션 정보
        if st.session_state.get('session_id'):
            st.markdown("---")
            st.markdown("**👤 Your Session:**")
            display_name = getattr(st.session_state, 'original_nickname', st.session_state.session_id)
            st.write(f"ID: {display_name}")
            current_step_name = st.session_state.get('step', 'unknown').replace('_', ' ').title()
            st.write(f"Step: {current_step_name}")
        
        # 연구자 디버그 모드
        debug_mode = st.checkbox("🔬 Debug Mode", help="For researchers only")
        if debug_mode:
            display_debug_info()


def display_debug_info():
    """
    디버그 정보 표시 (연구자용)
    """
    st.markdown("---")
    st.markdown("**🔍 Debug Info:**")
    
    # 익명 ID 표시
    if st.session_state.get('session_id'):
        st.write(f"Anonymous ID: {st.session_state.session_id}")
    
    # GPT 디버그 정보
    if st.session_state.get('gpt_debug_info'):
        debug_info = st.session_state.gpt_debug_info
        if debug_info.get('model_used'):
            st.write(f"Model: {debug_info['model_used']}")
        if debug_info.get('attempts'):
            st.write(f"Attempts: {debug_info['attempts']}")
        
        # 텍스트 처리 정보 표시
        if debug_info.get('original_length') and debug_info.get('processed_length'):
            original_len = debug_info['original_length']
            processed_len = debug_info['processed_length']
            if original_len != processed_len:
                st.write(f"Text processed: {original_len} → {processed_len} chars")
    
    # 피드백 필드 요약
    if st.session_state.get('feedback'):
        feedback = st.session_state.feedback
        st.write(f"Feedback fields: {len(feedback.keys())}")
        
        # Grammar issues 상태
        grammar_count = len(feedback.get('grammar_issues', []))
        if grammar_count > 0:
            st.write(f"Grammar Issues: ✅ {grammar_count}")
        else:
            st.write("Grammar Issues: ❌ 0")


def display_completion_celebration():
    """
    완료 축하 효과
    """
    st.balloons()
    
    st.markdown("### 🎉 Experiment Complete!")
    st.success("Thank you for participating in our Korean learning research study!")
    st.success("✅ Survey completed successfully!")


def create_styled_button(label, button_type="primary", icon="", use_container_width=True, disabled=False):
    """
    스타일이 적용된 버튼 생성
    
    Args:
        label: 버튼 라벨
        button_type: 버튼 타입
        icon: 아이콘 (선택사항)
        use_container_width: 컨테이너 너비 사용 여부
        disabled: 비활성화 여부
        
    Returns:
        bool: 버튼 클릭 여부
    """
    full_label = f"{icon} {label}" if icon else label
    return st.button(full_label, type=button_type, use_container_width=use_container_width, disabled=disabled)


def display_error_message(message, solution=""):
    """
    에러 메시지 표시
    
    Args:
        message: 에러 메시지
        solution: 해결책 (선택사항)
    """
    st.error(f"❌ {message}")
    if solution:
        st.info(f"💡 Solution: {solution}")


def display_success_message(message):
    """
    성공 메시지 표시
    
    Args:
        message: 성공 메시지
    """
    st.success(f"✅ {message}")


def display_warning_message(message):
    """
    경고 메시지 표시
    
    Args:
        message: 경고 메시지
    """
    st.warning(f"⚠️ {message}")


def display_info_message(message):
    """
    정보 메시지 표시
    
    Args:
        message: 정보 메시지
    """
    st.info(f"ℹ️ {message}")