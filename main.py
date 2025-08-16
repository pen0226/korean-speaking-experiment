"""
main.py
AI 기반 한국어 말하기 피드백 시스템 - 메인 애플리케이션 (iPhone 스크롤 최적화)
"""

import streamlit as st
from datetime import datetime
import re

# 모듈 imports (간단한 참고용 점수 모듈 추가)
from config import PAGE_CONFIG, GOOGLE_FORM_URL, CURRENT_SESSION, SESSION_LABELS, BACKGROUND_INFO, KST 
from stt import process_audio_input
from feedback import get_gpt_feedback, get_improvement_assessment
from tts import process_feedback_audio, display_model_audio
from consent import handle_consent_only, handle_background_info_only
from data_io import save_session_data, auto_backup_to_gcs, log_upload_status, display_download_buttons, display_session_details, display_data_quality_info
from save_reference_score import save_reference_score  # 🆕 간단한 참고용 점수 모듈
from utils import (
    show_progress_indicator, display_question, record_audio,
    display_transcription_with_highlights, display_model_sentence_with_highlights,
    display_improvement_metrics, display_improvement_details,
    display_audio_comparison, display_contact_info, setup_sidebar,
    create_styled_button,
    display_error_message, display_success_message, display_info_message,
    highlight_differences, format_content_ideas,
    parse_grammar_issue, parse_vocabulary_suggestion, display_vocabulary_tips_simplified, display_grammar_tips_simplified,
    format_detailed_feedback  # 🔥 새로 추가된 함수
)


def scroll_to_top():
    """강화된 페이지 스크롤 초기화 (iPhone Safari 완벽 호환)"""
    st.markdown(
        """
        <script>
        // 0.1초 뒤 강제 스크롤 (렌더링 이후 적용)
        setTimeout(function(){
            // 앵커 스크롤
            var pageTop = document.getElementById('page-top');
            if(pageTop && pageTop.scrollIntoView){
                pageTop.scrollIntoView({behavior:'auto', block:'start'});
            }
            
            // 기본 스크롤
            window.scrollTo(0,0);
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
            
            // Streamlit 컨테이너까지 스크롤
            var containers = ['.main','.block-container','[data-testid="stAppViewContainer"]','[data-testid="stApp"]','.stApp'];
            containers.forEach(function(sel){
                var el = document.querySelector(sel);
                if(el){
                    el.scrollTop = 0;
                    if(el.scrollTo) el.scrollTo(0,0);
                }
            });
            
            // 상위 프레임 처리 (iframe 환경)
            try {
                window.parent.scrollTo(0,0);
                var parentContainers = window.parent.document.querySelectorAll('.main,.block-container');
                parentContainers.forEach(function(el){
                    if(el){
                        el.scrollTop = 0;
                        if(el.scrollTo) el.scrollTo(0,0);
                    }
                });
            } catch(e) {
                // 크로스 오리진 오류 무시
            }
        }, 300);
        
        // 즉시 한 번 더 시도 (보험)
        var pageTop = document.getElementById('page-top');
        if(pageTop && pageTop.scrollIntoView){
            pageTop.scrollIntoView({behavior:'auto', block:'start'});
        }
        window.scrollTo(0,0);
        </script>
        """,
        unsafe_allow_html=True
    )


def initialize_session_state():
    """세션 상태 초기화 (자기효능감 필드 추가)"""
    if 'step' not in st.session_state:
        st.session_state.step = 'consent'  # 첫 단계를 'consent'로 변경
        st.session_state.session_number = CURRENT_SESSION
        st.session_state.session_label = SESSION_LABELS.get(CURRENT_SESSION, "Session 1")
        st.session_state.session_id = ""
        st.session_state.transcription_1 = ""
        st.session_state.transcription_2 = ""
        st.session_state.feedback = {}
        st.session_state.model_audio = {}
        st.session_state.gpt_debug_info = {}
        
        # 배경 정보 초기화
        st.session_state.learning_duration = ""
        
        # 자기효능감 점수 초기화 (12개)
        for i in range(1, 13):
            setattr(st.session_state, f'self_efficacy_{i}', '')


def handle_consent_step():
    """동의서 단계 처리"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('consent')
    
    st.markdown("### 📝 Consent to Participate")
    st.markdown("Please read and agree to participate in this research study.")
    
    if handle_consent_only():
        st.session_state.step = 'background_info'
        st.rerun()


def handle_background_info_step():
    """배경 정보 단계 처리 (닉네임 + 학습기간 + 자신감 + 자기효능감)"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('background_info')
    
    st.markdown("### 📊 Background Information")
    st.markdown("Please provide some information about your Korean learning journey.")
    
    if handle_background_info_only():
        st.session_state.step = 'first_recording'
        st.rerun()


def handle_first_recording_step():
    """첫 번째 녹음 단계 처리 - 개선된 레이아웃 (나이트 모드 최적화, 수정된 질문 반영)"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('first_recording')
    
    # 1) 🔥 수정된 질문 영역을 박스로 분리 (나이트 모드 최적화)
    st.markdown(
        """
        <div style='
            background: rgba(0, 0, 0, 0.05); 
            border: 2px solid rgba(229, 231, 235, 0.5); 
            border-radius: 12px; 
            padding: 25px; 
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: inherit;
        '>
            <div style='font-weight: bold; margin-bottom: 20px; color: inherit; opacity: 0.8; font-size: 16px;'>📝 Interview Question:</div>
            <div style='text-align: center;'>
                <div style='font-size: 22px; font-weight: bold; margin-bottom: 15px; color: inherit; line-height: 1.4;'>
                    Please speak for about 1~2 minutes in total and talk about both topics below.
                </div>
                <div style='font-size: 20px; color: inherit; margin: 10px 0;'>
                    1️⃣ <strong>지난 방학에 뭐 했어요? </strong>
                </div>
                <div style='font-size: 20px; color: inherit; margin: 10px 0;'>
                    2️⃣ <strong>다음 방학에는 뭐 할 거예요? 왜요?</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 2) 녹음 안내를 간결하게 (1-2분 목표로 수정)
    st.markdown(
        "🔴 **Aim for about 1~2 minutes total** | 🎧 **Quiet environment & headphones recommended**"
    )
    
    # 3) 녹음 단계 제목
    st.markdown("### 🎤 Step 3: First Recording")
    
    # 첫 번째 오디오 상태 초기화
    if "first_audio" not in st.session_state:
        st.session_state.first_audio = None
        st.session_state.first_audio_type = None
    
    # 녹음 인터페이스 (깔끔한 UI)
    audio_data, source_type = record_audio("first_recording", "")
    if audio_data and source_type:
        st.session_state.first_audio = audio_data
        st.session_state.first_audio_type = source_type
    
    # 처리 버튼
    if st.session_state.first_audio:
        st.markdown("---")
        if create_styled_button("🔄 Process First Recording", "primary", "🎙️"):
            process_first_recording()


def process_first_recording():
    """첫 번째 녹음 처리 (참고용 TOPIK 점수 생성 추가)"""
    with st.spinner("🎙️ Processing your recording..."):
        # 🔥 업로드 파일이면 바이트로 변환하되 파일명도 같이 저장
        if st.session_state.first_audio_type == "upload":
            original_filename = st.session_state.first_audio.name  # 파일명 미리 저장
            st.session_state.first_audio.seek(0)
            audio_bytes = st.session_state.first_audio.read()
            st.session_state.first_audio = {
                "bytes": audio_bytes,
                "name": original_filename  # 파일명도 함께 저장
            }
        
        # STT 처리 (source_type 전달)
        source_type = getattr(st.session_state, 'first_audio_type', 'recording')
        transcription, duration, success = process_audio_input(
            st.session_state.first_audio, source_type
        )
        
        if success:
            st.session_state.transcription_1 = transcription
            st.session_state.audio_duration_1 = duration
            
            # 🔥 timestamp 생성 (나중에 모든 파일에서 같은 timestamp 사용)
            timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")  # 🔥 KST 추가
            st.session_state.current_timestamp = timestamp
            
            # GPT 피드백 생성 (duration 정보 포함)
            with st.spinner("🧠 Getting AI feedback..."):
                feedback = get_gpt_feedback(transcription, attempt_number=1, duration=duration)
                st.session_state.feedback = feedback
            
            if feedback:
                # 🆕 간단한 참고용 점수 저장 (timestamp 전달)
                save_reference_score(
                    st.session_state.session_id, 
                    attempt=1, 
                    transcript=transcription,
                    duration=duration,
                    timestamp=timestamp
                )
                
                # TTS 생성
                model_audio = process_feedback_audio(feedback)
                st.session_state.model_audio = model_audio
                
                st.session_state.step = 'feedback'
                st.rerun()
            else:
                display_error_message("Unable to generate feedback. Please try again.")
        else:
            display_error_message("Could not process audio. Please try recording again.")


def handle_feedback_step():
    """피드백 표시 단계 처리 - 간소화된 버전 + 하이라이트 개선 (나이트 모드 최적화)"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('feedback')
    
    # 🔥 피드백 경고 배너를 이 단계에서만 표시
    st.warning("⚠️ This feedback is automatically generated by AI and may not be perfect. Please use it as a helpful reference.")
    
    st.markdown("### 🧠 Step 4: AI Feedback")
    st.markdown("")  # Step 4 타이틀 아래 여백 추가 (20-24px)
    
    if st.session_state.feedback:
        feedback = st.session_state.feedback
        
        # What You Said 섹션 (음성 포함)
        display_transcription_with_highlights(
            transcription=st.session_state.transcription_1,
            feedback=feedback,
            title="📝 What You Said",
            audio_data=st.session_state.first_audio
        )
        
        st.markdown("---")
        
        # ===== 모델 문장 표시 =====
        st.markdown("#### 🌟 Perfect Answer Example")
        st.markdown("*Here's how you could say it perfectly in the interview:*")
        
        # 모델 문장과 학생 답안 비교
        model_sentence = feedback.get('suggested_model_sentence', '')
        english_translation = feedback.get('suggested_model_sentence_english', '')
        student_transcription = st.session_state.transcription_1
        
        if model_sentence:
            # 하이라이트 적용된 텍스트 생성
            _, highlighted_model = highlight_differences(
                student_transcription, 
                model_sentence
            )
            
            # 모델 답안 (개선된 부분 표시, 나이트 모드 최적화)
            st.markdown(
                f"""
                <div style='
                    background: rgba(16, 185, 129, 0.1);
                    border: 3px solid #22c55e;
                    border-radius: 12px;
                    padding: 25px;
                    margin: 5px 0 15px 0;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    color: inherit;
                '>
                    <div style='font-size: 18px; line-height: 1.6; color: inherit; margin-bottom: 15px;'>
                        {highlighted_model}
                    </div>
                    {f'<div style="color: #22c55e; font-style: italic; font-size: 14px; padding-top: 10px; border-top: 1px solid #22c55e;">"{english_translation}"</div>' if english_translation else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # 모델 발음 표시 (중복 타이틀 제거됨)
            if st.session_state.model_audio:
                display_model_audio(st.session_state.model_audio)
            else:
                st.warning("⚠️ Model audio not available. Check TTS configuration.")
        
        st.markdown("---")
        
        # ===== 상세 피드백 섹션 =====
        st.markdown("#### 📚 Detailed Feedback")
        st.markdown("*Specific tips to improve your Korean:*")
        
        # Grammar Tips (utils.py의 함수 사용)
        display_grammar_tips_simplified(feedback)
        
        # Vocabulary Tips (utils.py의 함수 사용) - 개인맞춤형으로 표시
        has_vocab = feedback.get('vocabulary_suggestions') and len(feedback['vocabulary_suggestions']) > 0
        if has_vocab:
            with st.expander("💭 Vocabulary Tips", expanded=False):
                st.markdown("*Personalized word choice improvements based on your answer:*")
                display_vocabulary_tips_simplified(feedback)
        # 🔥 어휘 제안이 없으면 expander 자체를 표시하지 않음 (학생이 모든 단어를 올바르게 사용한 경우)
        
        
        # Pattern & Sentence Tips (통합된 형태) - 포맷 개선
        if feedback.get('grammar_expression_tip') or feedback.get('sentence_connection_tip'):
            with st.expander("🚀 Pattern & Sentence Tips", expanded=False):
                st.markdown("*Use these patterns to make your Korean more natural and fluent!*")
                
                # Advanced Pattern 섹션
                if feedback.get('grammar_expression_tip'):
                    st.markdown("**✨ Advanced Pattern**")
                    
                    # Advanced Pattern을 HTML 스타일로 통일
                    grammar_tip = feedback['grammar_expression_tip']
                    
                    # 기본 파싱 (간단한 구조 가정)
                    if "Try this:" in grammar_tip and "Example:" in grammar_tip and "When to use:" in grammar_tip:
                        lines = grammar_tip.replace('\\n', '\n').split('\n')
                        pattern_line = ""
                        example_line = ""
                        usage_line = ""
                        
                        for line in lines:
                            line = line.strip()
                            if line.startswith('🚀 Try this:') or line.startswith('🚀 Try:'):
                                pattern_line = line.replace('🚀 Try this:', '').replace('🚀 Try:', '').strip()
                            elif line.startswith('📝 Example:'):
                                example_line = line.replace('📝 Example:', '').strip()
                            elif line.startswith('💡 When to use:'):
                                usage_line = line.replace('💡 When to use:', '').strip()
                        
                        # HTML로 통일된 스타일 적용 (나이트 모드 최적화)
                        st.markdown(f"""
                        <div style='font-size: 16px; line-height: 1.5; color: inherit;'>
                            <strong>🚀 Try this:</strong> {pattern_line}<br>
                            <strong>📝 Example:</strong> {example_line}<br>
                            <span style='color: inherit; opacity: 0.7; font-size: 14px;'>💡 {usage_line}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # fallback: 기존 format_content_ideas 사용
                        formatted_tip = format_content_ideas(grammar_tip)
                        st.markdown(formatted_tip, unsafe_allow_html=True)
                    
                    # 구분선
                    if feedback.get('sentence_connection_tip'):
                        st.markdown("---")
                
                # Sentence Connection 섹션
                if feedback.get('sentence_connection_tip'):
                    st.markdown("**🔗 Sentence Connection**")
                    
                    # 문장 연결 팁 파싱 및 표시
                    from utils import parse_sentence_connection_tip
                    sentence_tip = feedback['sentence_connection_tip']
                    parsed_tip = parse_sentence_connection_tip(sentence_tip)
                    
                    st.markdown(f"""
                    <div style='font-size: 16px; line-height: 1.5; color: inherit;'>
                        <strong>❌ Before:</strong> {parsed_tip['before_sentences']}<br>
                        <strong>✅ After:</strong> {parsed_tip['after_sentence']}<br>
                        <span style='color: inherit; opacity: 0.7; font-size: 14px;'>💡 Use connectives like <strong>그리고</strong>, <strong>그래서</strong>, <strong>-고</strong>, <strong>-아서/어서</strong> to sound more natural</span>
                    </div>
                    """, unsafe_allow_html=True)


        # Content Ideas (줄바꿈 처리 개선)
        content_suggestions = feedback.get('content_expansion_suggestions', [])
        if content_suggestions:
            with st.expander("💡 Content Ideas - Make Your Answer Longer", expanded=False):
                st.markdown("*You can add these topics to speak for at least 1~2 minutes (90+ seconds):*")
                for i, suggestion in enumerate(content_suggestions[:2], 1):  # 최대 2개만
                    # Content suggestion 줄바꿈 처리
                    formatted_suggestion = format_content_ideas(suggestion)
                    
                    # 새로운 포맷으로 표시 (번호 없이 깔끔하게)
                    st.markdown(f"{formatted_suggestion}", unsafe_allow_html=True)
                    
                    # 각 항목 사이에 여백 추가
                    if i < len(content_suggestions[:2]):
                        st.markdown("")
                
                st.success("🎯 **Tip:** Try to include 1-2 of these ideas to reach at least 1~2 minutes (90+ seconds)!")

        
        # Performance Summary (간소화된 형태)
        with st.expander("📊 Performance Summary", expanded=False):
            # Interview Readiness Score
            score = feedback.get('interview_readiness_score', 6)
            st.metric("Interview Readiness Score", f"{score}/10")
            
            # 📋 Teacher's Notes (전체 너비로 확장)
            if feedback.get('detailed_feedback'):
                st.markdown("#### 📋 Teacher's Notes")
                st.markdown("*Interview preparation guidance from your Korean teacher:*")
                
                # 🔥 구조화된 피드백 포맷팅 적용
                detailed_text = feedback['detailed_feedback']
                formatted_feedback = format_detailed_feedback(detailed_text)
                st.markdown(formatted_feedback, unsafe_allow_html=True)
            
            # 🔥 녹음 시간 정보 (1-2분 목표로 수정)
            duration = getattr(st.session_state, 'audio_duration_1', 0)
            if duration > 0:
                st.markdown("#### ⏱️ Speaking Duration")
                if duration >= 90:
                    st.success(f"{duration:.1f} seconds - Excellent! Met the 1~2 minute goal!")
                elif duration >= 75:
                    st.info(f"{duration:.1f} seconds - Good, try to reach about 1~2 minutes (90+ seconds)!")
                elif duration >= 60:
                    st.warning(f"{duration:.1f} seconds - Fair, aim for about 1~2 minutes (90+ seconds) next time!")
                else:
                    st.error(f"{duration:.1f} seconds - Too short, aim for about 1~2 minutes (90+ seconds)!")
        
        st.markdown("---")
        
        # ===== 다음 단계 준비 =====
        st.markdown("### ✅ Ready for Your Second Try?")
        
        # 🔥 간단한 팁 리스트 (1-2분 목표로 수정)
        st.info("""
        **Quick Tips for Your Next Recording:**
        1. 🎤 **Listen to the model pronunciation above**
        2. 📝 **Use the grammar fixes** from the feedback
        3. 💡 **Add 2–3 extra details** for each topic (time, place, feelings, reasons)
        4. 🔄 **Try 1–2 new words or expressions** you learned from the model sentence
        5. 🎯 **Speak for 1~2 minutes** and answer **both topics fully**
        6. 🎤 **Speak clearly** and keep a steady speed for easier listening
        """)
        
        # 다음 단계 버튼
        if create_styled_button("🎤 Record Again with Improvements", "primary"):
            st.session_state.step = 'second_recording'
            st.rerun()
    
    else:
        st.error("❌ No feedback available. Please try recording again.")


def handle_second_recording_step():
    """두 번째 녹음 단계 처리 - 개선된 레이아웃 (나이트 모드 최적화, 수정된 질문 반영)"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('second_recording')
    
    st.markdown("### 🎤 Step 5: Second Recording")
    
    # 뒤로가기 버튼
    if create_styled_button("Back to Feedback", "secondary"):
        st.session_state.step = 'feedback'
        st.rerun()
    
    # 1) 🔥 수정된 질문 영역을 박스로 분리 (나이트 모드 최적화)
    st.markdown(
        """
        <div style='
            background: rgba(0, 0, 0, 0.05); 
            border: 2px solid rgba(229, 231, 235, 0.5); 
            border-radius: 12px; 
            padding: 25px; 
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: inherit;
        '>
            <div style='font-weight: bold; margin-bottom: 20px; color: inherit; opacity: 0.8; font-size: 16px;'>📝 Same Question - Second Attempt:</div>
            <div style='text-align: center;'>
                <div style='font-size: 22px; font-weight: bold; margin-bottom: 15px; color: inherit; line-height: 1.4;'>
                    Please speak for about 1~2 minutes in total and talk about both topics below.
                </div>
                <div style='font-size: 20px; color: inherit; margin: 10px 0;'>
                    1️⃣ <strong>지난 방학에 뭐 했어요? </strong>
                </div>
                <div style='font-size: 20px; color: inherit; margin: 10px 0;'>
                    2️⃣ <strong>다음 방학에는 뭐 할 거예요? 왜요?</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 2) 녹음 안내 추가 (1-2분 목표로 수정)
    st.markdown(
        "🔴 **Aim for about 1~2 minutes total** | 🎧 **Quiet environment & headphones recommended**"
    )
    
    st.write("🚀 Now try again! Apply the feedback you received to improve your answer.")
    
    # 두 번째 오디오 상태 초기화
    if "second_audio" not in st.session_state:
        st.session_state.second_audio = None
        st.session_state.second_audio_type = None
    
    # 녹음 인터페이스 (깔끔한 UI)
    audio_data, source_type = record_audio("second_recording", "")
    if audio_data and source_type:
        st.session_state.second_audio = audio_data
        st.session_state.second_audio_type = source_type
    
    # 처리 버튼
    if st.session_state.second_audio:
        st.markdown("---")
        if create_styled_button("🔄 Process Second Recording", "primary", "🎤"):
            process_second_recording()


def process_second_recording():
    """두 번째 녹음 처리 + 즉시 데이터 저장 (참고용 TOPIK 점수 생성 추가)"""
    with st.spinner("🎙️ Processing your improved recording..."):
        # 🔥 업로드 파일이면 바이트로 변환하되 파일명도 같이 저장
        if st.session_state.second_audio_type == "upload":
            original_filename = st.session_state.second_audio.name  # 파일명 미리 저장
            st.session_state.second_audio.seek(0)
            audio_bytes = st.session_state.second_audio.read()
            st.session_state.second_audio = {
                "bytes": audio_bytes,
                "name": original_filename  # 파일명도 함께 저장
            }
        
        # STT 처리 (source_type 전달)
        source_type = getattr(st.session_state, 'second_audio_type', 'recording')
        transcription, duration, success = process_audio_input(
            st.session_state.second_audio, source_type
        )
        
        if success:
            st.session_state.transcription_2 = transcription
            st.session_state.audio_duration_2 = duration
            
            # 🔥 첫 번째 녹음에서 생성한 timestamp 재사용 (파일들 간 일관성 유지)
            timestamp = getattr(st.session_state, 'current_timestamp', datetime.now(KST).strftime("%Y%m%d_%H%M%S"))  # 🔥 KST 추가
            
            # 🆕 간단한 참고용 점수 저장 (같은 timestamp 사용)
            save_reference_score(
                st.session_state.session_id,
                attempt=2,
                transcript=transcription, 
                duration=duration,
                timestamp=timestamp
            )
            
            display_success_message(f"Second attempt transcribed: {transcription}")
            
            # 개선도 평가
            if st.session_state.feedback and st.session_state.transcription_1:
                with st.spinner("📊 Analyzing your improvement ..."):
                    improvement_data = get_improvement_assessment(
                        st.session_state.transcription_1,
                        transcription,
                        st.session_state.feedback
                    )
                    st.session_state.improvement_assessment = improvement_data
                    
                    # 개선도 요약 표시
                    display_improvement_summary(improvement_data)
            
            # 🎯 즉시 데이터 저장 및 백업 (참고용 엑셀 포함)
            st.markdown("---")
            with st.spinner("💾 Saving your experiment data..."):
                save_result = save_and_backup_data()
                
                if save_result and save_result[0]:  # 저장 성공
                    st.session_state.data_saved = True
                    st.session_state.saved_files = save_result
                    st.success("✅ Your experiment data has been safely saved!")
                    st.info("📋 Next: Please complete the survey to help our research.")
                else:
                    st.error("❌ Data save failed. Please try again or contact the researcher.")
                    if st.button("🔄 Retry Save"):
                        st.rerun()
                    return  # 저장 실패시 다음 단계로 진행 안 함
            
            st.session_state.step = 'survey'
            st.rerun()
        else:
            display_error_message("Could not process audio. Please try recording again.")


def display_improvement_summary(improvement_data):
    """개선도 요약 표시"""
    score = improvement_data.get('improvement_score', 0)
    first_score = improvement_data.get('first_attempt_score', 0)
    second_score = improvement_data.get('second_attempt_score', 0)
    
    if score >= 8:
        display_success_message(f"Excellent improvement! (Score: {score}/10)")
    elif score >= 6:
        display_info_message(f"Good progress! (Score: {score}/10)")
    elif score >= 4:
        display_info_message(f"Some improvement (Score: {score}/10)")
    else:
        display_info_message(f"Keep practicing (Score: {score}/10)")
    
    # 점수 진행상황 표시
    if first_score > 0 and second_score > 0:
        st.metric("STT Rubric Score Progress", f"{second_score}/10", f"{second_score - first_score:+.1f}")
    
    if improvement_data.get('improvement_reason'):
        st.write("**📋 Analysis:** " + improvement_data['improvement_reason'])


def handle_survey_step():
    """설문조사 단계 처리 (데이터는 이미 저장된 상태)"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('survey')
    
    st.markdown("### 📋 Step 6: Required Survey")

    # 데이터 저장 상태 확인 및 안내
    if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
        st.success("✅ Your experiment data has been safely saved!")
    else:
        st.warning("⚠️ Data may not be saved. Please contact the researcher if you see this message.")
    
        # 진행상황 표시 (선택사항)
    display_optional_progress_view()

    # 설문조사 안내
    st.markdown("---")
    st.markdown("### 📝 Complete the Survey")
    st.warning("ℹ️ This survey is essential for the research study. Your feedback helps improve AI language learning tools!")
    
    # 설문조사 버튼 (빨간색 강조)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            f"""
            <div style="margin: 20px 0;">
                <a href="https://docs.google.com/forms/d/e/1FAIpQLSds3zsmZYjN3QSc-RKRtbDPTF0ybLrwJW4qVLDg2_xoumBLDw/viewform?usp=header" 
                   target="_blank" 
                   style="
                       background-color: #dc2626; 
                       color: white; 
                       padding: 16px 32px; 
                       border-radius: 8px; 
                       text-decoration: none; 
                       font-weight: bold; 
                       font-size: 18px;
                       display: inline-block;
                       width: 100%;
                       text-align: center;
                       box-shadow: 0 4px 8px rgba(220, 38, 38, 0.3);
                       border: none;
                       cursor: pointer;
                       transition: all 0.2s ease;
                   "
                   onmouseover="this.style.backgroundColor='#b91c1c'; this.style.transform='translateY(-2px)'"
                   onmouseout="this.style.backgroundColor='#dc2626'; this.style.transform='translateY(0px)'">
                   ⭐ 📝 Complete Survey Now ⭐
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # ===== 설문 완료 확인 시스템 =====
    st.markdown("---")
    st.markdown("### ✅ After Completing the Survey")
    st.markdown("*Please complete the survey above first, then proceed below:*")
    
    # 완료 확인 체크박스
    survey_completed = st.checkbox(
        "✅ I have completed and submitted the survey above", 
        help="Check this box after you finish and submit the Google Form survey"
    )
    
    # 완료 버튼 (체크박스 선택 시에만 활성화)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if survey_completed:
            if st.button("🎉 Finish Experiment", type="primary", use_container_width=True):
                st.session_state.step = 'completion'
                st.rerun()
        else:
            st.button("🎉 Finish Experiment", disabled=True, use_container_width=True)
            st.caption("👆 Please complete the survey first, then check the box above")


def save_and_backup_data():
    """데이터 저장 및 백업 (중복 저장 방지 포함 + 참고용 엑셀)"""
    # 중복 저장 방지
    if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
        if hasattr(st.session_state, 'saved_files'):
            return st.session_state.saved_files
    
    # 새로운 저장 수행 (참고용 엑셀 포함)
    result = save_session_data()
    if result[0]:  # csv_filename exists
        # 🔥 참고용 엑셀 파일이 포함된 결과 언패킹
        csv_filename, reference_excel_filename, audio_folder, saved_files, zip_filename, timestamp = result
        
        # 세션에 timestamp 저장 (중복 저장 방지용)
        st.session_state.saved_timestamp = timestamp
        
        # 🔥 GCS 자동 업로드 (참고용 엑셀 파일도 포함)
        uploaded_files, errors = auto_backup_to_gcs(
            csv_filename, reference_excel_filename, zip_filename, 
            st.session_state.session_id, 
            timestamp  # 새로 생성하지 않고 기존 timestamp 사용
        )
        
        # 로그 기록
        log_upload_status(
            st.session_state.session_id,
            timestamp,  # 같은 timestamp 사용
            uploaded_files,
            errors,
            False
        )
        
        # 업로드 결과 표시
        if errors:
            st.warning(f"⚠️ Cloud backup had issues: {'; '.join(errors[:2])}")
            st.info("💾 Your data is saved locally and can be downloaded below.")
        else:
            st.success("☁️ Data successfully backed up to cloud storage!")
    
    return result


def handle_completion_step():
    """완료 단계 처리"""
    # 🔥 앵커 + 스크롤을 맨 처음에!
    st.markdown('<div id="page-top" style="position:absolute;top:0;height:1px;visibility:hidden;"></div>', unsafe_allow_html=True)
    scroll_to_top()
    
    show_progress_indicator('completion')
    
    # 완료 축하 (간소화된 버전)
    st.balloons()
    
    # 감사 메시지
    st.markdown("---")
    st.markdown("### 🙏 Thank You! 감사합니다!")
    display_info_message(f"🚀 Your participation in {st.session_state.session_label} helps advance AI-powered language education!")
    
    
    # 연구자 모드
    display_researcher_mode()
    
    # 마지막 안내
    st.markdown("---")
    st.markdown("### 🚀 Next Steps")
    display_info_message("You may now close this page. Your participation in this research study is complete!")
    
    # 연락처 정보
    display_contact_info(st.session_state.session_id)


def display_optional_progress_view():
    """선택적 진행상황 표시 (2인칭 톤으로 수정)"""
    if hasattr(st.session_state, 'saved_files') and st.session_state.saved_files:
        # saved_files의 첫 번째 요소(csv_filename)가 존재하는지 확인
        if len(st.session_state.saved_files) > 0 and st.session_state.saved_files[0]:
            with st.expander("📊 View Your Progress (Optional)", expanded=False):
                # 오디오 비교
                display_audio_comparison(
                    st.session_state.get('first_audio'),
                    st.session_state.get('second_audio'),
                    getattr(st.session_state, 'audio_duration_1', 0),
                    getattr(st.session_state, 'audio_duration_2', 0)
                )
                
                # 전사 텍스트 표시
                col1, col2 = st.columns(2)
                with col1:
                    st.code(st.session_state.transcription_1, language=None)
                with col2:
                    st.code(st.session_state.transcription_2, language=None)
                
                # 개선도 분석 (제목 변경 및 2인칭 톤 적용)
                if hasattr(st.session_state, 'improvement_assessment'):
                    st.markdown("---")
                    st.markdown("### 📈 Improvement Analysis")  # 🔥 제목 변경
                    
                    improvement = st.session_state.improvement_assessment
                    
                    # 🔥 2인칭 톤으로 개선도 메트릭 표시
                    display_improvement_metrics_personal(improvement)
                    display_improvement_details_personal(improvement)


def display_improvement_metrics_personal(improvement):
    """개선도 메트릭 표시 (원래 점수 사용)"""
    col1, col2 = st.columns(2)
    
    with col1:
        # 🔥 수정: 원래 1차 녹음에서 받은 실제 점수 사용
        original_first_score = st.session_state.feedback.get('interview_readiness_score', 0)
        st.metric("Your First Attempt", f"{original_first_score}/10")
    
    with col2:
        second_score = improvement.get('second_attempt_score', 0)
        # 🔥 수정: 실제 점수 차이로 계산
        difference = second_score - original_first_score
        st.metric("Your Second Attempt", f"{second_score}/10", f"{difference:+.1f}")
    

def display_improvement_details_personal(improvement):
    """개선도 상세 정보 표시 (구체적이고 실용적으로 개편)"""
    
    # ✅ 핵심 요약 (한 줄로 간단히)
    st.markdown("#### ✅ Key Feedback")
    analysis_text = improvement.get('improvement_reason', '')
    overall_assessment = improvement.get('overall_assessment', '')
    
    # 간단한 요약 생성
    if analysis_text or overall_assessment:
        summary = convert_to_actionable_summary(analysis_text, overall_assessment)
        st.info(summary)
    else:
        st.info("Good effort! Focus on speaking longer with more specific details.")
    
    # 🔧 핵심 개선사항 (Top 3)
    st.markdown("#### 🔧 Fix These 3 Things")
    
    # 구체적인 개선사항 생성
    actionable_tips = generate_actionable_tips(improvement)
    
    for i, tip in enumerate(actionable_tips, 1):
        st.markdown(f"**{i}. {tip['category']}** → {tip['description']}")
        if tip.get('example'):
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;👉 **예:** {tip['example']}")
        st.markdown("")  # 간격 추가
    
    # 💡 Quick Tip
    st.markdown("#### 💡 Quick Tip")
    st.success("Practice these expressions before your next recording!")


def convert_to_actionable_summary(analysis_text, overall_assessment):
    """추상적 텍스트를 간단한 핵심 요약으로 변환"""
    # 2인칭으로 변환
    text = convert_to_second_person(analysis_text + " " + overall_assessment)
    
    # 핵심 키워드 기반 요약 생성
    if "longer" in text.lower() or "length" in text.lower():
        if "grammar" in text.lower() or "error" in text.lower():
            return "Good progress adding details! Next time, focus on grammar accuracy and topic clarity."
        else:
            return "Great job speaking longer! Next time, focus more on the specific question topics."
    elif "grammar" in text.lower() or "error" in text.lower():
        return "Good effort! Next time, focus on grammar accuracy and adding more details."
    elif "topic" in text.lower() or "focus" in text.lower():
        return "Good attempt! Next time, focus more on answering the specific topics in the question."
    else:
        return "Good progress! Keep practicing to improve clarity and add more specific details."


def generate_actionable_tips(improvement):
    """구체적이고 실용적인 개선 팁 3개 생성 (수정된 질문에 맞게 조정)"""
    tips = []
    
    # 기본 개선사항들에서 구체적 팁 추출
    remaining_issues = improvement.get('remaining_issues', [])
    specific_improvements = improvement.get('specific_improvements', [])
    
    # 1. Topic Focus (가장 중요) - 수정된 질문에 맞게 조정
    if any("topic" in issue.lower() or "focus" in issue.lower() for issue in remaining_issues):
        tips.append({
            'category': 'Topic focus',
            'description': 'Talk more about 지난 방학 experiences and 다음 방학 plans',
            'example': '"지난 방학에 친구랑 부산에 여행 갔어요" / "다음 방학에는 한국 회사에 취직하려고 해요"'
        })
    
    # 2. Grammar (두 번째 중요)
    if any("grammar" in issue.lower() for issue in remaining_issues):
        tips.append({
            'category': 'Grammar',
            'description': 'Past tense: 갔어요, 했어요 / Future tense: 할 거예요, 가려고 해요',
            'example': '"지난 방학에 가족과 여행했어요" / "다음 방학에는 한국어를 더 배우려고 해요"'
        })
    
    # 3. Content Expansion (세 번째)
    if any("detail" in issue.lower() or "content" in issue.lower() or "expand" in issue.lower() for issue in remaining_issues):
        tips.append({
            'category': 'Content expansion',
            'description': 'Add 1-2 more sentences with specific details for each topic',
            'example': '"부산에서 해운대도 갔어요. 가족과 함께 맛있는 음식도 먹었어요"'
        })
    
    # 기본 팁들로 채우기 (3개 미만인 경우)
    if len(tips) < 3:
        default_tips = [
            {
                'category': 'Speaking length',
                'description': 'Try to speak for at least 60-90 seconds total',
                'example': 'Add more details about what you did and why you plan to do something'
            },
            {
                'category': 'Connecting words',
                'description': 'Use 그리고 (and), 그래서 (so), 그런데 (but) to connect ideas',
                'example': '"여행 갔어요. 그리고 맛있는 음식도 먹었어요"'
            },
            {
                'category': 'Clear reasons',
                'description': 'Explain why for your vacation plans using 왜냐하면 or ~어서/아서',
                'example': '"한국어를 배우고 싶어서 다음 방학에 한국에 갈 거예요"'
            }
        ]
        
        for tip in default_tips:
            if len(tips) < 3:
                tips.append(tip)
    
    return tips[:3]  # 최대 3개만 반환


def convert_to_second_person(text):
    """3인칭 표현을 2인칭으로 변환하고 더 따뜻한 톤으로 수정"""
    if not text:
        return text
    
    # 기본적인 3인칭 → 2인칭 변환
    text = text.replace("The student", "You")
    text = text.replace("the student", "you")
    text = text.replace("They ", "You ")
    text = text.replace("they ", "you ")
    text = text.replace("Their ", "Your ")
    text = text.replace("their ", "your ")
    text = text.replace("Them ", "You ")
    text = text.replace("them ", "you ")
    
    # 더 격려적인 표현으로 변경
    text = text.replace("significantly improved", "made wonderful progress")
    text = text.replace("effectively applied", "successfully used")
    text = text.replace("addressed previous grammar issues", "fixed grammar points beautifully")
    text = text.replace("incorporated vocabulary suggestions", "applied vocabulary tips well")
    text = text.replace("made major improvements", "showed amazing improvement")
    text = text.replace("extending your speaking time", "speaking much longer - great job!")
    text = text.replace("enriching your content", "adding wonderful personal details")
    text = text.replace("showing a strong understanding", "demonstrating excellent progress")
    
    return text


def test_gcs_connection_simple():
    """간단한 GCS 연결 테스트"""
    try:
        from config import GCS_ENABLED, GCS_SERVICE_ACCOUNT, GCS_BUCKET_NAME
        
        if not GCS_ENABLED:
            return False, "GCS_ENABLED is False"
        
        if not GCS_SERVICE_ACCOUNT:
            return False, "Service account not configured"
        
        if not GCS_BUCKET_NAME:
            return False, "Bucket name not configured"
        
        # JSON 파싱 테스트
        import json
        try:
            service_account_info = json.loads(GCS_SERVICE_ACCOUNT)
            project_id = service_account_info.get('project_id', 'Unknown')
            return True, f"GCS Ready - Project: {project_id}"
        except json.JSONDecodeError:
            return False, "Invalid JSON format"
            
    except Exception as e:
        return False, f"GCS test failed: {str(e)}"


def display_researcher_mode():
    """연구자 모드 표시 (참고용 엑셀 지원 추가)"""
    debug_mode = st.sidebar.checkbox("🔬 Researcher Mode", help="For research data access")
    if debug_mode:
        with st.expander("🔬 Researcher: Data Management", expanded=False):
            # 🔥 간소화된 시스템 테스트
            st.markdown("#### 🔍 System Diagnostics")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Test GCS Connection"):
                    success, message = test_gcs_connection_simple()
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
            
            with col2:
                from tts import test_elevenlabs_connection
                if st.button("🔊 Test TTS Connection"):
                    success, message, details = test_elevenlabs_connection()
                    if success:
                        st.success(f"✅ {message}")
                        st.info(f"📋 {details}")
                    else:
                        st.error(f"❌ {message}")
                        st.warning(f"⚠️ {details}")
            
            st.markdown("---")
            
            if hasattr(st.session_state, 'saved_files'):
                # 🔥 참고용 엑셀 파일 포함하여 처리
                csv_filename = st.session_state.saved_files[0] if len(st.session_state.saved_files) > 0 else None
                reference_excel_filename = st.session_state.saved_files[1] if len(st.session_state.saved_files) > 1 else None
                zip_filename = st.session_state.saved_files[4] if len(st.session_state.saved_files) > 4 else None
                
                # 다운로드 버튼들 (참고용 엑셀 정보 포함)
                display_download_buttons(csv_filename, reference_excel_filename, zip_filename)
                
                # 세션 상세 정보
                display_session_details()
                
                # 데이터 품질 정보
                display_data_quality_info()


def main():
    """메인 애플리케이션 함수 (iPhone 스크롤 최적화 + 참고용 TOPIK 점수 통합)"""
    # 페이지 설정
    st.set_page_config(**PAGE_CONFIG)
    
    # 세션 상태 초기화 (자기효능감 포함)
    initialize_session_state()
    
    # 제목 (세션 정보 포함)
    session_info = f" - {SESSION_LABELS.get(CURRENT_SESSION, 'Session 1')}"
    st.title(f"🇰🇷 Korean Speaking Practice with AI Feedback{session_info}")
    
    # 🔥 경고 배너는 피드백 단계에서만 표시 (handle_feedback_step()에서 처리)
    
    # 사이드바 설정
    setup_sidebar()
    
    # 단계별 처리 (consent → background_info → first_recording → ...)
    current_step = st.session_state.step
    
    if current_step == 'consent':
        handle_consent_step()
    elif current_step == 'background_info':
        handle_background_info_step()
    elif current_step == 'first_recording':
        handle_first_recording_step()
    elif current_step == 'feedback':
        handle_feedback_step()
    elif current_step == 'second_recording':
        handle_second_recording_step()
    elif current_step == 'survey':
        handle_survey_step()
    elif current_step == 'completion':
        handle_completion_step()
    else:
        display_error_message(f"Unknown step: {current_step}")
        st.session_state.step = 'consent'
        st.rerun()


if __name__ == "__main__":
    main()