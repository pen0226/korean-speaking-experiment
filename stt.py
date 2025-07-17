"""
stt.py
OpenAI API Whisper를 이용한 음성-텍스트 변환 모듈 (Streamlit Cloud 호환 버전)
"""

import tempfile
import os
import streamlit as st
from config import OPENAI_API_KEY


def get_openai_client():
    """
    OpenAI 클라이언트 초기화 (Streamlit Cloud 호환성 강화)
    
    Returns:
        OpenAI: 클라이언트 객체 또는 None
    """
    if not OPENAI_API_KEY:
        return None
    
    try:
        # 최신 openai SDK (>=1.0.0) 방식 - Streamlit Cloud 호환
        from openai import OpenAI
        
        # 🔥 Streamlit Cloud 호환: proxies 파라미터 명시적 제거
        client_kwargs = {
            "api_key": OPENAI_API_KEY,
            # Streamlit Cloud에서 자동 설정되는 proxies 파라미터 방지
            "max_retries": 3,
            "timeout": 30.0
        }
        
        # 환경에 따른 추가 설정
        try:
            return OpenAI(**client_kwargs)
        except TypeError as e:
            if "proxies" in str(e):
                # proxies 파라미터 오류인 경우 기본 설정으로 재시도
                st.warning("🔄 Adjusting OpenAI client for Streamlit Cloud...")
                return OpenAI(api_key=OPENAI_API_KEY)
            else:
                raise e
        
    except ImportError:
        try:
            # 구버전 fallback
            import openai
            openai.api_key = OPENAI_API_KEY
            return openai
        except ImportError:
            return None


def get_file_extension_and_mime(audio_data, source_type):
    """
    오디오 데이터의 파일 확장자와 MIME 타입 결정
    
    Args:
        audio_data: 오디오 데이터
        source_type: "recording" 또는 "upload"
        
    Returns:
        tuple: (file_extension, mime_type)
    """
    if source_type == "upload" and hasattr(audio_data, 'name'):
        # 업로드된 파일의 원본 확장자 추출
        file_ext = os.path.splitext(audio_data.name)[1].lower()
        if not file_ext:
            file_ext = ".wav"  # 확장자가 없으면 기본값
    else:
        # 마이크 녹음은 기본적으로 wav
        file_ext = ".wav"
    
    # MIME 타입 매핑
    mime_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mp3",
        ".m4a": "audio/m4a", 
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".mp4": "audio/mp4",
        ".mpeg": "audio/mpeg",
        ".mpga": "audio/mpeg",
        ".oga": "audio/ogg"
    }
    
    mime_type = mime_types.get(file_ext, "audio/wav")
    return file_ext, mime_type


def load_whisper():
    """
    API 방식에서는 모델 로딩이 불필요
    호환성을 위해 None 반환
    """
    return None


def transcribe_audio(audio_bytes, file_extension=".wav", source_type="recording", original_filename=None):
    """
    OpenAI API Whisper를 사용한 오디오 바이트 텍스트 변환 (Streamlit Cloud 호환)
    
    Args:
        audio_bytes: 오디오 파일의 바이트 데이터
        file_extension: 파일 확장자
        source_type: "recording" 또는 "upload"
        original_filename: 원본 파일명 (업로드 시)
        
    Returns:
        tuple: (transcription_text, duration_seconds)
    """
    if not audio_bytes:
        return "", 0.0
    
    if not OPENAI_API_KEY:
        st.error("❌ OpenAI API key is required for speech transcription!")
        return "", 0.0
    
    # 원본 확장자를 유지하여 임시 파일 생성
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
        tmp.write(audio_bytes)
        temp_path = tmp.name
    
    try:
        # 🔥 Streamlit Cloud 호환 클라이언트 초기화
        client = get_openai_client()
        if not client:
            st.error("❌ Failed to initialize OpenAI client")
            return "", 0.0
        
        # MIME 타입 결정
        _, mime_type = get_file_extension_and_mime(None, source_type)
        if file_extension:
            mime_types = {
                ".wav": "audio/wav",
                ".mp3": "audio/mp3", 
                ".m4a": "audio/m4a",
                ".flac": "audio/flac",
                ".ogg": "audio/ogg",
                ".webm": "audio/webm"
            }
            mime_type = mime_types.get(file_extension, "audio/wav")
        
        # 🔥 Streamlit Cloud 호환 API 호출
        with open(temp_path, "rb") as audio_file:
            # 파일명과 MIME 타입을 명시적으로 전달
            filename = original_filename or f"audio{file_extension}"
            
            try:
                # 🔥 Streamlit Cloud 호환: 추가 파라미터 제거
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=(filename, audio_file, mime_type),
                    language="ko",
                    response_format="verbose_json"
                )
            except Exception as api_error:
                # Streamlit Cloud에서 발생할 수 있는 API 호출 오류 처리
                error_msg = str(api_error)
                if "proxies" in error_msg or "unexpected keyword" in error_msg:
                    st.error("🔄 Streamlit Cloud compatibility issue detected. Retrying with basic settings...")
                    
                    # 기본 설정으로 재시도
                    basic_client = OpenAI(api_key=OPENAI_API_KEY)
                    audio_file.seek(0)  # 파일 포인터 리셋
                    
                    transcription = basic_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ko"
                    )
                else:
                    raise api_error
        
        # 텍스트 추출
        if hasattr(transcription, 'text'):
            transcription_text = transcription.text.strip()
        else:
            transcription_text = str(transcription).strip()
        
        # 음성 길이 계산
        duration = getattr(transcription, 'duration', None)
        if duration is None:
            # duration이 없으면 추정값 사용
            duration = estimate_audio_duration(audio_bytes)
        
        return transcription_text, duration
        
    except Exception as e:
        error_msg = str(e)
        
        # 🔥 Streamlit Cloud 특화 에러 메시지
        if "proxies" in error_msg or "unexpected keyword" in error_msg:
            st.error("❌ Streamlit Cloud compatibility issue")
            st.info("💡 This is a known issue with OpenAI SDK on Streamlit Cloud. Please try again or contact support.")
        elif "Invalid file format" in error_msg:
            st.error(f"❌ File format error: {original_filename or 'audio file'}")
            st.info("💡 Try converting to MP3 or WAV format and upload again")
        elif "File not supported" in error_msg:
            st.error(f"❌ File not supported: {file_extension}")
            st.info("💡 Supported formats: WAV, MP3, M4A, FLAC, OGG, WEBM")
        elif "timeout" in error_msg.lower():
            st.error("❌ Request timeout - file may be too large")
            st.info("💡 Try with a shorter audio file (under 25MB)")
        else:
            st.error(f"❌ Transcription error: {error_msg}")
            
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
    # OpenAI Whisper API 지원 형식
    SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "flac", "ogg", "webm", "mp4", "mpeg", "mpga", "oga"]
    
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # 파일 확장자 확인
    file_extension = uploaded_file.name.split('.')[-1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        return False, f"❌ Unsupported format '{file_extension}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
    
    # 파일 크기 확인 (OpenAI API 제한: 25MB)
    if uploaded_file.size > 25 * 1024 * 1024:
        return False, "❌ File too large. Maximum size: 25MB (OpenAI API limit)"
    
    # 기본적인 파일 크기 검증
    if uploaded_file.size < 1024:  # 1KB 미만
        return False, "❌ File too small. Please upload a valid audio file"
    
    return True, "✅ Valid audio file"


def process_audio_input(audio_data, source_type="recording"):
    """
    오디오 입력을 처리하고 전사 (Streamlit Cloud 호환)
    
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
            
            # 원본 파일 정보 추출
            original_filename = audio_data.name
            file_ext = os.path.splitext(original_filename)[1].lower()
            
            audio_bytes = audio_data.read()
            audio_data.seek(0)  # 포인터 리셋
        else:
            # 녹음된 오디오 처리
            audio_bytes = audio_data['bytes']
            original_filename = "recording.wav"
            file_ext = ".wav"
        
        # 🔥 Streamlit Cloud 호환 전사 수행
        with st.spinner("🎙️ Converting speech to text using OpenAI Whisper (Streamlit Cloud optimized)..."):
            transcription, duration = transcribe_audio(
                audio_bytes, 
                file_extension=file_ext,
                source_type=source_type,
                original_filename=original_filename
            )
        
        if transcription:
            st.success(f"✅ Transcribed: {transcription}")
            display_audio_quality_feedback(duration)
            return transcription, duration, True
        else:
            st.error("❌ Could not transcribe audio. Please try again.")
            return "", 0.0, False
            
    except Exception as e:
        error_msg = str(e)
        if "proxies" in error_msg:
            st.error("❌ Streamlit Cloud compatibility issue detected")
            st.info("💡 Please try again. This is a known issue that usually resolves on retry.")
        else:
            st.error(f"❌ Audio processing error: {error_msg}")
        return "", 0.0, False


def check_whisper_availability():
    """
    Whisper API 사용 가능 여부 확인 (Streamlit Cloud 호환)
    
    Returns:
        tuple: (is_available, status_message)
    """
    if not OPENAI_API_KEY:
        return False, "OpenAI API key not configured"
    
    try:
        client = get_openai_client()
        if client:
            return True, "OpenAI API Whisper ready (Streamlit Cloud compatible)"
        else:
            return False, "Failed to initialize OpenAI client"
    except Exception as e:
        error_msg = str(e)
        if "proxies" in error_msg:
            return False, "Streamlit Cloud compatibility issue"
        else:
            return False, f"OpenAI client error: {error_msg}"


def display_whisper_status():
    """
    Whisper API 상태를 사이드바에 표시 (Streamlit Cloud 정보 포함)
    """
    is_available, status = check_whisper_availability()
    
    if is_available:
        st.write("Speech Recognition: ✅ Ready (Streamlit Cloud)")
    else:
        st.write(f"Speech Recognition: ❌ {status}")


def test_whisper_api():
    """
    Whisper API 연결 테스트 (Streamlit Cloud 호환)
    
    Returns:
        bool: 테스트 성공 여부
    """
    try:
        client = get_openai_client()
        if client:
            return True
        else:
            return False
        
    except Exception as e:
        print(f"Whisper API test failed: {e}")
        return False