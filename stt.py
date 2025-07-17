"""
stt.py
Whisper를 이용한 음성-텍스트 변환 모듈 (최종 버전 - 40초 목표)
"""

import whisper
import tempfile
import os
import streamlit as st
from config import WHISPER_MODEL


@st.cache_resource
def load_whisper():
    """Whisper 모델 로드 (캐시 사용)"""
    try:
        return whisper.load_model(WHISPER_MODEL)
    except Exception as e:
        st.error(f"Whisper model loading failed: {str(e)}")
        return None


def transcribe_audio(audio_bytes):
    """
    오디오 바이트를 한국어 텍스트로 변환
    
    Args:
        audio_bytes: 오디오 파일의 바이트 데이터
        
    Returns:
        tuple: (transcription_text, duration_seconds)
    """
    if not audio_bytes:
        return "", 0.0
    
    # 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name
    
    try:
        # Whisper 모델 로드
        model = load_whisper()
        if model is None:
            return "", 0.0
        
        # 음성 인식 수행
        result = model.transcribe(temp_path, language='ko', verbose=True)
        
        # 음성 길이 계산
        duration = calculate_audio_duration(result, audio_bytes)
        
        # 텍스트 정리
        transcription = result["text"].strip()
        
        return transcription, duration
        
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return "", 0.0
    finally:
        # 임시 파일 삭제
        try:
            os.unlink(temp_path)
        except:
            pass


def calculate_audio_duration(whisper_result, audio_bytes):
    """
    음성 길이 계산
    
    Args:
        whisper_result: Whisper 결과 객체
        audio_bytes: 오디오 바이트 데이터
        
    Returns:
        float: 음성 길이 (초)
    """
    try:
        # Whisper segments에서 정확한 길이 추출
        if 'segments' in whisper_result and whisper_result['segments']:
            return whisper_result['segments'][-1]['end']
        else:
            # segments가 없으면 추정값 사용 (16kHz, 16bit 가정)
            return len(audio_bytes) / (16000 * 2)
    except:
        # 모든 방법이 실패하면 기본값
        return len(audio_bytes) / (16000 * 2)


def get_audio_quality_assessment(duration):
    """
    음성 길이를 기반으로 품질 평가 (40초 목표)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        dict: 품질 평가 정보
    """
    from config import AUDIO_QUALITY
    
    if duration >= AUDIO_QUALITY["excellent_min_duration"]:  # 40초 이상
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
    elif duration >= AUDIO_QUALITY["good_min_duration"]:  # 30-40초
        return {
            "status": "good",
            "icon": "🌟",
            "message": f"Good! ({duration:.1f}s) Try to reach 40+ seconds for an even better score.",
            "color": "info"
        }
    elif duration >= AUDIO_QUALITY["fair_min_duration"]:  # 20-30초
        return {
            "status": "fair",
            "icon": "⚠️",
            "message": f"Fair start! ({duration:.1f}s) Aim for 40+ seconds to show better fluency.",
            "color": "warning"
        }
    else:  # 20초 미만
        return {
            "status": "very_short",
            "icon": "❌",
            "message": f"Too brief! ({duration:.1f}s) Please speak for at least 20+ seconds, ideally 40+ seconds.",
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
    
    # 파일 크기 확인 (50MB 제한)
    if uploaded_file.size > 50 * 1024 * 1024:
        return False, "File too large. Maximum size: 50MB"
    
    return True, "Valid file"


def process_audio_input(audio_data, source_type="recording"):
    """
    오디오 입력을 처리하고 전사
    
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
        
        # 전사 수행
        with st.spinner("🎙️ Converting speech to text..."):
            transcription, duration = transcribe_audio(audio_bytes)
        
        if transcription:
            st.success(f"✅ Transcribed: {transcription}")
            display_audio_quality_feedback(duration)
            return transcription, duration, True
        else:
            st.error("❌ Could not transcribe audio. Please try again.")
            return "", 0.0, False
            
    except Exception as e:
        st.error(f"Audio processing error: {str(e)}")
        return "", 0.0, False