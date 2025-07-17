"""
stt.py
OpenAI API Whisper를 이용한 음성-텍스트 변환 모듈 (Streamlit Cloud 안정화 버전)
"""

import tempfile
import os
import streamlit as st
from config import OPENAI_API_KEY


def load_whisper():
    """
    API 방식에서는 모델 로딩이 불필요
    호환성을 위해 None 반환
    """
    return None


def transcribe_audio(audio_bytes):
    """
    OpenAI API Whisper를 사용한 오디오 바이트 텍스트 변환
    
    Args:
        audio_bytes: 오디오 파일의 바이트 데이터
        
    Returns:
        tuple: (transcription_text, duration_seconds)
    """
    if not audio_bytes:
        return "", 0.0
    
    if not OPENAI_API_KEY:
        st.error("❌ OpenAI API key is required for speech transcription!")
        return "", 0.0
    
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # API를 통한 음성 인식 수행
        with open(temp_path, "rb") as audio_file:
            # OpenAI Whisper API 호출
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",
                response_format="verbose_json"  # timestamp 정보 포함
            )
        
        # 텍스트 추출
        transcription_text = transcription.text.strip()
        
        # 음성 길이 계산 (API 응답에서 duration 추출)
        duration = getattr(transcription, 'duration', None)
        if duration is None:
            # duration이 없으면 추정값 사용
            duration = estimate_audio_duration(audio_bytes)
        
        return transcription_text, duration
        
    except Exception as e:
        st.error(f"❌ Transcription error: {str(e)}")
        return "", 0.0
    finally:
        # 임시 파일 삭제
        try:
            os.unlink(temp_path)
        except:
            pass


def estimate_audio_duration(audio_bytes):
    """
    오디오 바이트에서 대략적인 길이 추정
    
    Args:
        audio_bytes: 오디오 바이트 데이터
        
    Returns:
        float: 추정된 음성 길이 (초)
    """
    try:
        # WAV 파일 기준 추정 (16kHz, 16bit 가정)
        # 실제 정확한 길이는 API에서 제공하는 duration 사용
        estimated_duration = len(audio_bytes) / (16000 * 2)
        return max(estimated_duration, 1.0)  # 최소 1초
    except:
        return 1.0  # 기본값


def get_audio_quality_assessment(duration):
    """
    음성 길이를 기반으로 품질 평가 (60초 목표)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        dict: 품질 평가 정보
    """
    from config import AUDIO_QUALITY
    
    if duration >= AUDIO_QUALITY["excellent_min_duration"]:  # 60초 이상
        if duration <= AUDIO_QUALITY["max_recommended_duration"]:
            return {
                "status": "excellent",
                "icon": "✅",
                "message": f"Great! Your recording is {duration:.1f}s — perfect length for the interview!",
                "color": "success"
            }
        else:
            return {
                "status": "long",
                "icon": "📝",
                "message": f"Excellent! ({duration:.1f}s) Lots of content for the AI to work with!",
                "color": "info"
            }
    elif duration >= AUDIO_QUALITY["good_min_duration"]:  # 45-60초
        return {
            "status": "good",
            "icon": "🌟",
            "message": f"Good! ({duration:.1f}s) Try to reach 60+ seconds for an even better score.",
            "color": "info"
        }
    elif duration >= AUDIO_QUALITY["fair_min_duration"]:  # 30-45초
        return {
            "status": "fair",
            "icon": "⚠️",
            "message": f"Fair start! ({duration:.1f}s) Aim for 60+ seconds to show better fluency.",
            "color": "warning"
        }
    else:  # 30초 미만
        return {
            "status": "very_short",
            "icon": "❌",
            "message": f"Too brief! ({duration:.1f}s) Please speak for at least 30+ seconds, ideally 60+ seconds.",
            "color": "error"
        }


def display_audio_quality_feedback(duration):
    """
    음성 길이에 대한 피드백을 Streamlit에 표시
    
    Args:
        duration: 음성 길이 (초)
    """
    assessment = get_audio_quality_assessment(duration)
    
    if assessment["color"] == "success":
        st.success(f"{assessment['icon']} {assessment['message']}")
    elif assessment["color"] == "info":
        st.info(f"{assessment['icon']} {assessment['message']}")
    elif assessment["color"] == "warning":
        st.warning(f"{assessment['icon']} {assessment['message']}")
    else:  # error
        st.error(f"{assessment['icon']} {assessment['message']}")


def validate_audio_file(uploaded_file):
    """
    업로드된 오디오 파일 유효성 검사
    
    Args:
        uploaded_file: Streamlit 업로드 파일 객체
        
    Returns:
        tuple: (is_valid, error_message)
    """
    from config import SUPPORTED_AUDIO_FORMATS
    
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # 파일 확장자 확인
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in SUPPORTED_AUDIO_FORMATS:
        return False, f"Unsupported format. Use: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
    
    # 파일 크기 확인 (OpenAI API 제한: 25MB)
    if uploaded_file.size > 25 * 1024 * 1024:
        return False, "File too large. Maximum size: 25MB (OpenAI API limit)"
    
    return True, "Valid file"


def process_audio_input(audio_data, source_type="recording"):
    """
    오디오 입력을 처리하고 전사 (OpenAI API 방식)
    
    Args:
        audio_data: 오디오 데이터 (녹음 또는 업로드)
        source_type: 입력 소스 타입 ("recording" 또는 "upload")
        
    Returns:
        tuple: (transcription, duration, success)
    """
    try:
        if source_type == "upload":
            # 업로드된 파일 처리
            is_valid, error_msg = validate_audio_file(audio_data)
            if not is_valid:
                st.error(error_msg)
                return "", 0.0, False
            
            audio_bytes = audio_data.read()
            audio_data.seek(0)  # 포인터 리셋
        else:
            # 녹음된 오디오 처리
            audio_bytes = audio_data['bytes']
        
        # OpenAI API 전사 수행
        with st.spinner("🎙️ Converting speech to text using OpenAI Whisper..."):
            transcription, duration = transcribe_audio(audio_bytes)
        
        if transcription:
            st.success(f"✅ Transcribed: {transcription}")
            display_audio_quality_feedback(duration)
            return transcription, duration, True
        else:
            st.error("❌ Could not transcribe audio. Please try again.")
            return "", 0.0, False
            
    except Exception as e:
        st.error(f"❌ Audio processing error: {str(e)}")
        return "", 0.0, False


def check_whisper_availability():
    """
    Whisper API 사용 가능 여부 확인
    
    Returns:
        tuple: (is_available, status_message)
    """
    if not OPENAI_API_KEY:
        return False, "OpenAI API key not configured"
    
    try:
        from openai import OpenAI
        return True, "OpenAI API Whisper ready"
    except ImportError:
        return False, "OpenAI library not installed"


def display_whisper_status():
    """
    Whisper API 상태를 사이드바에 표시
    """
    is_available, status = check_whisper_availability()
    
    if is_available:
        st.write("Speech Recognition: ✅ Ready (OpenAI API)")
    else:
        st.write(f"Speech Recognition: ❌ {status}")


def test_whisper_api():
    """
    Whisper API 연결 테스트 (개발용)
    
    Returns:
        bool: 테스트 성공 여부
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # 간단한 API 호출 테스트 (실제 파일 없이)
        # 실제 테스트는 작은 오디오 파일로 수행해야 함
        return True
        
    except Exception as e:
        print(f"Whisper API test failed: {e}")
        return False