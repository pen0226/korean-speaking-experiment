"""
tts.py
ElevenLabs를 이용한 텍스트-음성 변환 및 오디오 재생 모듈 (최종 클린 버전)
"""

import streamlit as st
import re
from config import (
    ELEVENLABS_API_KEY, 
    ELEVEN_VOICE_ID, 
    ELEVENLABS_MODEL, 
    TTS_SETTINGS
)


def fix_tts_sentence_punctuation(text):
    """
    자연스러운 억양을 위한 마침표 자동 보정 (억양 내림 유도)
    
    Args:
        text: 보정할 텍스트
        
    Returns:
        str: 마침표가 보정된 텍스트
    """
    text = text.strip()
    
    # 🎯 한국어 TTS 억양 개선: 모든 문장 끝에 명확한 마침표
    if text.endswith(('?', '!')):
        # 의문문, 감탄문은 그대로 유지
        return text
    elif text.endswith(('.', '...')):
        # 이미 마침표가 있으면 정리만
        return text.rstrip('.') + '.'
    else:
        # 한국어 어미로 끝나더라도 명확한 마침표 추가
        return text + '.'


def apply_slow_speed_formatting(text):
    """
    SSML을 사용한 느린 속도 포맷팅 (fallback용 - 500ms 일시정지 + 70% 속도)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: SSML로 포맷팅된 텍스트
    """
    # 1. 문장 단위로 분리 (한국어 문장 구분자 기준)
    sentences = re.split(r'([.!?])', text)
    
    # 2. 각 문장 끝에 500ms 일시정지 추가
    formatted_parts = []
    for i in range(0, len(sentences)-1, 2):
        if i+1 < len(sentences):
            sentence = sentences[i] + sentences[i+1]  # 문장 + 구분자
            if sentence.strip():
                formatted_parts.append(sentence + '<break time="500ms"/>')
    
    # 마지막 부분이 남아있다면 추가
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        formatted_parts.append(sentences[-1])
    
    # 3. 전체를 prosody rate 70%로 감싸기 (ElevenLabs speed 제한에 맞춤)
    formatted_text = ''.join(formatted_parts)
    return f'<prosody rate="70%">{formatted_text}</prosody>'


def apply_fallback_slow_formatting(text):
    """
    SSML 지원하지 않을 경우 텍스트 기반 느린 속도 구현 (fallback용)
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 느린 속도용으로 포맷팅된 텍스트
    """
    # 문장마다 추가 마침표로 자연스러운 일시정지 생성
    sentences = re.split(r'([.!?])', text)
    slow_parts = []
    
    for i in range(0, len(sentences)-1, 2):
        if i+1 < len(sentences):
            sentence = sentences[i] + sentences[i+1]
            if sentence.strip():
                # 문장 끝에 추가 마침표와 공백으로 일시정지 효과
                slow_parts.append(sentence + '. ')
    
    # 마지막 부분 처리
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        slow_parts.append(sentences[-1])
    
    return ''.join(slow_parts)


def apply_natural_pacing(text):
    """
    자연스러운 말하기 속도를 위한 포맷팅
    
    Args:
        text: 원본 텍스트
        
    Returns:
        str: 자연스럽게 포맷팅된 텍스트
    """
    # 일반 속도는 원본 텍스트 그대로 반환
    return text


def synthesize_audio(text, speed="normal"):
    """
    텍스트를 음성으로 변환 (ElevenLabs 공식 speed 파라미터 사용)
    
    Args:
        text: 변환할 텍스트
        speed: 속도 ("normal" 또는 "slow")
        
    Returns:
        bytes: 생성된 오디오 데이터 또는 None
    """
    if not ELEVENLABS_API_KEY:
        return None
    
    try:
        from elevenlabs.client import ElevenLabs
        
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        
        # 🎯 자연스러운 억양을 위한 마침표 보정
        text = fix_tts_sentence_punctuation(text)
        original_text = text
        
        # 속도별 voice_settings 설정
        voice_settings = TTS_SETTINGS.get(speed, TTS_SETTINGS["normal"]).copy()
        
        # 🚀 ElevenLabs 공식 speed 파라미터 사용
        if speed == "slow":
            voice_settings["stability"] = 0.95  # 매우 높은 안정성
            voice_settings["style"] = 0.05      # 최소한의 스타일 (단조로운 억양)
            voice_settings["similarity_boost"] = 0.95  # 높은 일관성
        else:
            voice_settings["stability"] = 0.75  # 일반 속도 안정성
            voice_settings["style"] = 0.45      # 적당한 스타일
            voice_settings["similarity_boost"] = 0.80  # 일관성
        
        # 공식 speed 파라미터 사용
        clean_settings = voice_settings.copy()
        if 'speed_modifier' in clean_settings:
            del clean_settings['speed_modifier']
        
        # ElevenLabs 공식 speed 파라미터를 사용한 오디오 생성
        try:
            audio_generator = client.generate(
                text=text,
                voice=ELEVEN_VOICE_ID,
                model=ELEVENLABS_MODEL,
                voice_settings=clean_settings
            )
            
            # Convert generator to bytes
            audio_data = b"".join(audio_generator)
            
            if audio_data:
                return audio_data
            else:
                raise Exception("No audio data generated")
                
        except Exception as speed_error:
            # 공식 speed 파라미터 실패시 SSML fallback 시도
            if speed == "slow":
                # Fallback 1: SSML 속도 제어
                ssml_text = apply_slow_speed_formatting(original_text)
                
                # speed 파라미터 제거하고 SSML로 시도
                fallback_settings = clean_settings.copy()
                if 'speed' in fallback_settings:
                    del fallback_settings['speed']
                
                try:
                    audio_generator = client.generate(
                        text=ssml_text,
                        voice=ELEVEN_VOICE_ID,
                        model=ELEVENLABS_MODEL,
                        voice_settings=fallback_settings
                    )
                    
                    audio_data = b"".join(audio_generator)
                    
                    if audio_data:
                        return audio_data
                    
                except Exception as ssml_error:
                    # Fallback 2: 텍스트 기반 느린 속도
                    fallback_text = apply_fallback_slow_formatting(original_text)
                    
                    # voice_settings도 더 극단적으로 조정
                    fallback_settings["stability"] = 0.98
                    fallback_settings["style"] = 0.02
                    
                    try:
                        audio_generator = client.generate(
                            text=fallback_text,
                            voice=ELEVEN_VOICE_ID,
                            model=ELEVENLABS_MODEL,
                            voice_settings=fallback_settings
                        )
                        
                        audio_data = b"".join(audio_generator)
                        
                        if audio_data:
                            return audio_data
                        
                    except Exception as final_error:
                        st.warning(f"TTS generation failed: {final_error}")
                        return None
            else:
                # 일반 속도에서는 원본 텍스트로 재시도 (speed 파라미터 없이)
                fallback_settings = clean_settings.copy()
                if 'speed' in fallback_settings:
                    del fallback_settings['speed']
                
                try:
                    audio_generator = client.generate(
                        text=original_text,
                        voice=ELEVEN_VOICE_ID,
                        model=ELEVENLABS_MODEL,
                        voice_settings=fallback_settings
                    )
                    
                    audio_data = b"".join(audio_generator)
                    
                    if audio_data:
                        return audio_data
                        
                except Exception as normal_error:
                    st.warning(f"TTS generation failed: {normal_error}")
                    return None
    
    except ImportError as ie:
        st.warning(f"ElevenLabs import error: {str(ie)}")
        return None
    except Exception as e:
        st.warning(f"TTS generation failed: {str(e)}")
        return None


def generate_model_audio(text):
    """
    일반속도와 느린속도 모델 음성 생성 (ElevenLabs 공식 speed 파라미터 사용)
    
    Args:
        text: 변환할 텍스트
        
    Returns:
        dict: {"normal": audio_data, "slow": audio_data}
    """
    model_audio = {}
    
    with st.spinner("🔊 Generating model pronunciation..."):
        # 일반 속도 생성
        with st.spinner("🚀 Creating natural speed version..."):
            normal_audio = synthesize_audio(text, "normal")
            if normal_audio:
                model_audio["normal"] = normal_audio
        
        # 느린 속도 생성 (ElevenLabs 공식 speed 파라미터 사용)
        with st.spinner("🐌 Creating slow speed version..."):
            slow_audio = synthesize_audio(text, "slow")
            if slow_audio:
                model_audio["slow"] = slow_audio
    
    return model_audio


def audio_card(audio_data, title, description=""):
    """
    통일된 오디오 카드 컴포넌트
    
    Args:
        audio_data: 오디오 바이트 데이터
        title: 카드 제목
        description: 설명 텍스트
    """
    if audio_data:
        st.markdown(
            f"""<div style='padding: 15px; border: 1px solid #e2e8f0; border-radius: 8px; margin: 10px 0; background-color: #ffffff;'>
            <h5 style='margin: 0 0 10px 0; color: #374151;'>{title}</h5>
            </div>""",
            unsafe_allow_html=True
        )
        st.audio(audio_data)
        if description:
            st.caption(description)
    else:
        st.info(f"{title} (ElevenLabs API not configured)")


def display_model_audio(model_audio_dict):
    """
    모델 발음 오디오를 표시 (학생 친화적 메시지로 수정)
    
    Args:
        model_audio_dict: {"normal": audio_data, "slow": audio_data}
    """
    if not model_audio_dict:
        st.info("🔊 Model pronunciation (ElevenLabs API not configured)")
        return
    
    st.markdown("#### 🎯 Model Pronunciation")
    st.info("🎧 **Two different speeds** - Listen to both and practice speaking along!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        audio_card(
            model_audio_dict.get('slow'), 
            "🐌 Slow & Clear", 
            "📚 Perfect for learning - slower and clearer"
        )
    
    with col2:
        audio_card(
            model_audio_dict.get('normal'), 
            "🚀 Natural Speed", 
            "🎯 Interview pace - practice matching this speed"
        )


def check_tts_availability():
    """
    TTS 기능 사용 가능 여부 확인
    
    Returns:
        tuple: (is_available, status_message)
    """
    if not ELEVENLABS_API_KEY:
        return False, "ElevenLabs API key not configured"
    
    if not ELEVEN_VOICE_ID:
        return False, "Voice ID not configured"
    
    try:
        from elevenlabs.client import ElevenLabs
        return True, "TTS ready"
    except ImportError:
        return False, "ElevenLabs library not installed"


def display_tts_status():
    """
    AI Model Voice 상태를 사이드바에 표시
    """
    is_available, status = check_tts_availability()
    
    if is_available:
        st.write("AI Model Voice: ✅ Ready ")
    else:
        st.write(f"AI Model Voice: ❌ {status}")


def save_audio_to_session(model_audio_dict, session_key="model_audio"):
    """
    생성된 오디오를 세션 상태에 저장
    
    Args:
        model_audio_dict: 오디오 딕셔너리
        session_key: 세션 저장 키
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = {}
    
    st.session_state[session_key].update(model_audio_dict)


def get_audio_from_session(session_key="model_audio"):
    """
    세션에서 오디오 데이터 가져오기
    
    Args:
        session_key: 세션 키
        
    Returns:
        dict: 오디오 딕셔너리
    """
    return st.session_state.get(session_key, {})


def create_audio_download_links(model_audio_dict, prefix="model"):
    """
    오디오 다운로드 링크 생성
    
    Args:
        model_audio_dict: 오디오 딕셔너리
        prefix: 파일명 접두사
    """
    if not model_audio_dict:
        return
    
    st.markdown("📥 **Download Audio Files:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if model_audio_dict.get("normal"):
            st.download_button(
                label="📁 Download Natural Speed",
                data=model_audio_dict["normal"],
                file_name=f"{prefix}_natural.mp3",
                mime="audio/mpeg"
            )
    
    with col2:
        if model_audio_dict.get("slow"):
            st.download_button(
                label="📁 Download Slow Speed", 
                data=model_audio_dict["slow"],
                file_name=f"{prefix}_slow.mp3",
                mime="audio/mpeg"
            )


def validate_text_for_tts(text):
    """
    TTS 생성을 위한 텍스트 유효성 검사
    
    Args:
        text: 검사할 텍스트
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Empty text provided"
    
    if len(text) > 1000:
        return False, "Text too long (max 1000 characters)"
    
    # 한국어 문자가 포함되어 있는지 확인
    has_korean = any('\uac00' <= char <= '\ud7af' for char in text)
    if not has_korean:
        return False, "No Korean text detected"
    
    return True, "Valid text"


def process_feedback_audio(feedback_dict):
    """
    피드백에서 모델 문장을 추출하여 오디오 생성 (ElevenLabs 공식 speed 파라미터 사용)
    
    Args:
        feedback_dict: GPT 피드백 딕셔너리
        
    Returns:
        dict: 생성된 오디오 딕셔너리
    """
    model_sentence = feedback_dict.get('suggested_model_sentence', '')
    
    # 🎯 자연스러운 억양 유도: 마침표 자동 추가
    model_sentence = fix_tts_sentence_punctuation(model_sentence)
    
    if not model_sentence:
        st.warning("⚠️ No model sentence found in feedback")
        return {}
    
    # 텍스트 유효성 검사
    is_valid, error_msg = validate_text_for_tts(model_sentence)
    if not is_valid:
        st.error(f"❌ TTS Error: {error_msg}")
        return {}
    
    # TTS 가용성 확인
    is_available, status = check_tts_availability()
    if not is_available:
        st.info(f"ℹ️ TTS not available: {status}")
        return {}
    
    # 오디오 생성
    return generate_model_audio(model_sentence)


def display_audio_generation_progress():
    """
    오디오 생성 진행상황 표시
    """
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 단계별 진행상황 시뮬레이션
    steps = [
        "🔊 Initializing TTS engine...",
        "🎯 Processing Korean text...", 
        "🚀 Generating natural speed audio...",
        "🐌 Generating slow speed audio...",
        "✅ Audio generation complete!"
    ]
    
    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        
    # 완료 후 정리
    status_text.empty()
    progress_bar.empty()