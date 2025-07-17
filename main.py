"""
main.py
AI 기반 한국어 말하기 피드백 시스템 - 메인 애플리케이션 (설문 완료 확인 시스템 개선 최종 버전)
"""

import streamlit as st
from datetime import datetime
import re

# 모듈 imports (배경 정보 추가)
from config import PAGE_CONFIG, GOOGLE_FORM_URL, CURRENT_SESSION, SESSION_LABELS, BACKGROUND_INFO
from stt import process_audio_input
from feedback import get_gpt_feedback, get_improvement_assessment
from tts import process_feedback_audio, display_model_audio
from consent import handle_nickname_input_with_consent
from data_io import save_session_data, auto_backup_to_drive, log_upload_status, display_download_buttons, display_session_details, display_data_quality_info
from utils import (
    show_progress_indicator, display_question, record_audio,
    display_transcription_with_highlights, display_model_sentence_with_highlights,
    display_improvement_metrics, display_improvement_details,
    display_audio_comparison, display_contact_info, setup_sidebar,
    create_styled_button,
    display_error_message, display_success_message, display_info_message,
    display_ai_model_voice_section, highlight_differences, format_content_ideas,
    parse_grammar_issue, parse_vocabulary_suggestion, display_vocabulary_tips_simplified, display_grammar_tips_simplified
)


def initialize_session_state():
    """세션 상태 초기화 (배경 정보 필드 추가)"""
    if 'step' not in st.session_state:
        st.session_state.step = 'nickname_input'
        st.session_state.session_number = CURRENT_SESSION
        st.session_state.session_label = SESSION_LABELS.get(CURRENT_SESSION, "Session 1")
        st.session_state.session_id = ""
        st.session_state.transcription_1 = ""
        st.session_state.transcription_2 = ""
        st.session_state.feedback = {}
        st.session_state.model_audio = {}
        st.session_state.gpt_debug_info = {}
        
        # 배경 정보 초기화 (새로 추가)
        st.session_state.learning_duration = ""
        st.session_state.speaking_confidence = ""


def handle_nickname_input_step():
    """닉네임 입력 및 동의 단계 처리 (배경 정보 포함)"""
    show_progress_indicator('nickname_input')
    
    st.markdown("### 📝 Consent to Participate")
    st.markdown("Please read and agree to participate in this research study.")
    
    # handle_nickname_input_with_consent() 함수가 이미 배경 정보까지 모든 것을 처리함
    if handle_nickname_input_with_consent():
        st.session_state.step = 'first_recording'
        st.rerun()


def handle_first_recording_step():
    """첫 번째 녹음 단계 처리 - 1분 목표"""
    show_progress_indicator('first_recording')
    
    # 질문 표시
    display_question("Interview Question")
    
    # 녹음 가이드 (1분으로 변경)
    st.write("🎯 Try to speak in Korean for **at least 1 minute (60+ seconds)**. Take your time to express your thoughts naturally.")
    
    st.markdown("### 🎤 Step 2: First Recording")
    
    # 첫 번째 오디오 상태 초기화
    if "first_audio" not in st.session_state:
        st.session_state.first_audio = None
    
    # 녹음 인터페이스
    audio = record_audio("first_recording", "Record your answer:")
    if audio:
        st.session_state.first_audio = audio
    
    # 처리 버튼
    if st.session_state.first_audio:
        st.markdown("---")
        if create_styled_button("🔄 Process First Recording", "primary", "🎙️"):
            process_first_recording()


def process_first_recording():
    """첫 번째 녹음 처리"""
    with st.spinner("🎙️ Processing your recording..."):
        # STT 처리
        transcription, duration, success = process_audio_input(
            st.session_state.first_audio, "recording"
        )
        
        if success:
            st.session_state.transcription_1 = transcription
            st.session_state.audio_duration_1 = duration
            
            # GPT 피드백 생성 (duration 정보 포함)
            with st.spinner("🧠 Getting AI feedback..."):
                feedback = get_gpt_feedback(transcription, attempt_number=1, duration=duration)
                st.session_state.feedback = feedback
            
            if feedback:
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
    """피드백 표시 단계 처리 - 간소화된 버전 + 하이라이트 개선"""
    show_progress_indicator('feedback')
    
    st.markdown("### 🧠 Step 3: AI Feedback")
    
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
        st.markdown("### 🌟 Perfect Answer Example")
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
            
            # 모델 답안 (개선된 부분 표시)
            st.markdown(
                f"""
                <div style='
                    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
                    border: 3px solid #22c55e;
                    border-radius: 12px;
                    padding: 25px;
                    margin: 20px 0;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                '>
                    <div style='font-size: 18px; line-height: 1.6; color: #1f2937; margin-bottom: 15px;'>
                        {highlighted_model}
                    </div>
                    {f'<div style="color: #166534; font-style: italic; font-size: 14px; padding-top: 10px; border-top: 1px solid #22c55e;">"{english_translation}"</div>' if english_translation else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # AI Model Voice 섹션
            display_ai_model_voice_section()
            
            # 모델 발음 표시
            if st.session_state.model_audio:
                display_model_audio(st.session_state.model_audio)
            else:
                st.warning("⚠️ Model audio not available. Check TTS configuration.")
        
        st.markdown("---")
        
        # ===== 상세 피드백 섹션 =====
        st.markdown("### 📚 Detailed Feedback")
        st.markdown("*Specific tips to improve your Korean:*")
        
        # Grammar Tips (utils.py의 함수 사용)
        display_grammar_tips_simplified(feedback)
        
        # Vocabulary Tips (utils.py의 함수 사용)
        has_vocab = feedback.get('vocabulary_suggestions') and len(feedback['vocabulary_suggestions']) > 0
        if has_vocab:
            with st.expander("💭 Vocabulary Tips", expanded=False):
                st.markdown("*Better word choices for more natural Korean:*")
                display_vocabulary_tips_simplified(feedback)
        
        # Content Ideas (줄바꿈 처리 개선)
        content_suggestions = feedback.get('content_expansion_suggestions', [])
        if content_suggestions:
            with st.expander("💡 Content Ideas - Make Your Answer Longer", expanded=False):
                st.markdown("*You can add these topics to speak for at least 1 minute (60+ seconds):*")
                for i, suggestion in enumerate(content_suggestions[:2], 1):  # 최대 2개만
                    # Content suggestion 줄바꿈 처리
                    formatted_suggestion = format_content_ideas(suggestion)
                    
                    # 새로운 포맷으로 표시 (번호 없이 깔끔하게)
                    st.markdown(f"{formatted_suggestion}", unsafe_allow_html=True)
                    
                    # 각 항목 사이에 여백 추가
                    if i < len(content_suggestions[:2]):
                        st.markdown("")
                
                st.success("🎯 **Tip:** Try to include 1-2 of these ideas to reach at least 1 minute (60+ seconds)!")
        
        # Advanced Grammar Pattern (접을 수 있는 형태) - 포맷 개선
        if feedback.get('grammar_expression_tip'):
            with st.expander("🚀 Advanced Grammar Pattern", expanded=False):
                st.markdown("*A useful pattern to enhance your Korean:*")
                # format_content_ideas 함수를 사용해서 깔끔하게 포맷팅
                formatted_tip = format_content_ideas(feedback['grammar_expression_tip'])
                st.markdown(formatted_tip, unsafe_allow_html=True)
        
        # Performance Summary (접을 수 있는 형태)
        with st.expander("📊 Performance Summary", expanded=False):
            # Interview Readiness Score
            score = feedback.get('interview_readiness_score', 6)
            st.metric("Interview Readiness Score", f"{score}/10")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if feedback.get('fluency_comment'):
                    st.markdown("#### 🗣️ Speaking Flow")
                    st.write(feedback['fluency_comment'])
            
            with col2:
                if feedback.get('interview_readiness_reason'):
                    st.markdown("#### 📋 Detailed Feedback")
                    st.write(feedback['interview_readiness_reason'])
            
            # 녹음 시간 정보
            duration = getattr(st.session_state, 'audio_duration_1', 0)
            if duration > 0:
                st.markdown("#### ⏱️ Speaking Duration")
                if duration >= 60:
                    st.success(f"{duration:.1f} seconds - Excellent! Met the 1-minute goal!")
                elif duration >= 45:
                    st.info(f"{duration:.1f} seconds - Good, try to reach at least 1 minute (60+ seconds)!")
                else:
                    st.warning(f"{duration:.1f} seconds - Aim for at least 1 minute (60+ seconds) next time!")
        
        st.markdown("---")
        
        # ===== 다음 단계 준비 =====
        st.markdown("### ✅ Ready for Your Second Try?")
        
        # 간단한 팁 리스트
        st.info("""
        **Quick Tips for Your Next Recording:**
        1. 🎯 Aim for **at least 1 minute (60+ seconds)** of speaking
        2. 🎤 Listen to the model pronunciation above
        3. 📝 Try to fix the grammar points
        4. 💡 Add some personal details from the content ideas
        """)
        
        # 다음 단계 버튼
        if create_styled_button("🎤 Record Again with Improvements", "primary"):
            st.session_state.step = 'second_recording'
            st.rerun()
    
    else:
        st.error("❌ No feedback available. Please try recording again.")


def format_simple_feedback(content):
    """피드백을 간단하게 포맷팅"""
    if not content:
        return ""
    
    # 복잡한 기호들 제거
    content = content.replace('\\n', ' ')
    content = content.replace('**', '')
    content = content.replace('💡', '•')
    content = content.replace('📝', '•')
    content = content.replace('🎯', '•')
    content = content.replace('🧠', '-')
    
    # 너무 긴 내용은 줄이기
    if len(content) > 150:
        content = content[:147] + "..."
    
    return content


def handle_second_recording_step():
    """두 번째 녹음 단계 처리 - 1분 목표"""
    show_progress_indicator('second_recording')
    
    st.markdown("### 🎤 Step 4: Second Recording")
    
    # 뒤로가기 버튼
    if create_styled_button("Back to Feedback", "secondary"):
        st.session_state.step = 'feedback'
        st.rerun()
    
    st.write("🚀 Now try again! Apply the feedback you received to improve your answer.")
    st.write("🎯 Try to speak for **at least 1 minute (60+ seconds)**, using the suggestions from your feedback.")
    
    # 질문 재표시
    display_question("Same Question - Second Attempt")
    
    # 두 번째 오디오 상태 초기화
    if "second_audio" not in st.session_state:
        st.session_state.second_audio = None
    
    # 녹음 인터페이스
    audio = record_audio("second_recording", "Record your improved answer:")
    if audio:
        st.session_state.second_audio = audio
    
    # 처리 버튼
    if st.session_state.second_audio:
        st.markdown("---")
        if create_styled_button("🔄 Process Second Recording", "primary", "🎤"):
            process_second_recording()


def process_second_recording():
    """두 번째 녹음 처리"""
    with st.spinner("🎙️ Processing your improved recording..."):
        # STT 처리
        transcription, duration, success = process_audio_input(
            st.session_state.second_audio, "recording"
        )
        
        if success:
            st.session_state.transcription_2 = transcription
            st.session_state.audio_duration_2 = duration
            
            display_success_message(f"Second attempt transcribed: {transcription}")
            
            # 개선도 평가
            if st.session_state.feedback and st.session_state.transcription_1:
                with st.spinner("📊 Analyzing your improvement using STT-based rubric..."):
                    improvement_data = get_improvement_assessment(
                        st.session_state.transcription_1,
                        transcription,
                        st.session_state.feedback
                    )
                    st.session_state.improvement_assessment = improvement_data
                    
                    # 개선도 요약 표시
                    display_improvement_summary(improvement_data)
            
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
    """설문조사 단계 처리 (설문 완료 확인 시스템 개선된 최종 버전)"""
    show_progress_indicator('survey')
    
    st.markdown("### 📋 Step 5: Required Survey")
    
    # 데이터 자동 저장
    if not hasattr(st.session_state, 'data_saved'):
        save_and_backup_data()
    
    # 설문조사 안내
    st.markdown("---")
    st.markdown("### 📝 Complete the Survey")
    display_info_message("This survey is essential for the research study. Your feedback helps improve AI language learning tools!")
    
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
    
    # ===== 🎯 새로 추가: 설문 완료 확인 시스템 =====
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
    """데이터 저장 및 백업"""
    result = save_session_data()
    if result[0]:  # csv_filename exists
        st.session_state.data_saved = True
        st.session_state.saved_files = result
        
        # Google Drive 자동 업로드
        csv_filename, excel_filename, audio_folder, saved_files, zip_filename = result
        with st.spinner("💾 Finalizing your session..."):
            uploaded_files, errors = auto_backup_to_drive(
                csv_filename, excel_filename, zip_filename, 
                st.session_state.session_id, 
                datetime.now().strftime('%Y%m%d_%H%M%S')
            )
            
            # 로그 기록
            log_upload_status(
                st.session_state.session_id,
                datetime.now().strftime('%Y%m%d_%H%M%S'),
                uploaded_files,
                errors,
                False
            )


def handle_completion_step():
    """완료 단계 처리"""
    show_progress_indicator('completion')
    
    # 완료 축하 (간소화된 버전)
    st.balloons()
    
    # 감사 메시지
    st.markdown("---")
    st.markdown("### 🙏 Thank You! 감사합니다!")
    display_info_message(f"🚀 Your participation in {st.session_state.session_label} helps advance AI-powered language education!")
    
    # 진행상황 표시 (선택사항)
    display_optional_progress_view()
    
    # 연구자 모드
    display_researcher_mode()
    
    # 마지막 안내
    st.markdown("---")
    st.markdown("### 🚀 Next Steps")
    display_info_message("You may now close this page. Your participation in this research study is complete!")
    
    # 연락처 정보
    display_contact_info(st.session_state.session_id)


def display_optional_progress_view():
    """선택적 진행상황 표시"""
    if hasattr(st.session_state, 'saved_files') and st.session_state.saved_files[0]:
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
            
            # 개선도 분석
            if hasattr(st.session_state, 'improvement_assessment'):
                st.markdown("---")
                st.markdown("### 📈 STT-Based Improvement Analysis")
                
                improvement = st.session_state.improvement_assessment
                display_improvement_metrics(improvement)
                display_improvement_details(improvement)


def display_researcher_mode():
    """연구자 모드 표시 (배경 정보 포함)"""
    debug_mode = st.sidebar.checkbox("🔬 Researcher Mode", help="For research data access")
    if debug_mode:
        with st.expander("🔬 Researcher: Data Management", expanded=False):
            if hasattr(st.session_state, 'saved_files'):
                csv_filename, excel_filename, audio_folder, saved_files, zip_filename = st.session_state.saved_files
                
                # 다운로드 버튼들
                display_download_buttons(csv_filename, excel_filename, zip_filename)
                
                # 세션 상세 정보 (배경 정보 포함)
                display_session_details()
                
                # 데이터 품질 정보
                display_data_quality_info()


def main():
    """메인 애플리케이션 함수"""
    # 페이지 설정
    st.set_page_config(**PAGE_CONFIG)
    
    # 제목 및 경고 (세션 정보 포함)
    session_info = f" - {SESSION_LABELS.get(CURRENT_SESSION, 'Session 1')}"
    st.title(f"🇰🇷 Korean Speaking Practice with AI Feedback{session_info}")
    st.warning("⚠️ This feedback is automatically generated by AI and may not be perfect. Please use it as a helpful reference.")
    
    # 세션 상태 초기화 (배경 정보 포함)
    initialize_session_state()
    
    # 사이드바 설정
    setup_sidebar()
    
    # 단계별 처리
    current_step = st.session_state.step
    
    if current_step == 'nickname_input':
        handle_nickname_input_step()
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
        st.session_state.step = 'nickname_input'
        st.rerun()


if __name__ == "__main__":
    main()