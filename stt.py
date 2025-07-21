"""
stt.py
OpenAI API Whisper를 이용한 음성-텍스트 변환 모듈 (파일명 접근 수정 버전)
"""

import tempfile
import os
import streamlit as st
from config import OPENAI_API_KEY


def detect_openai_version():
    """
    OpenAI SDK 버전 감지
    
    Returns:
        str: "v1" (modern) 또는 "v0" (legacy)
    """
    try:
        import openai
        # v1.0.0+ 에서는 openai.OpenAI 클래스가 존재
        if hasattr(openai, 'OpenAI'):
            return "v1"
        else:
            return "v0"
    except ImportError:
        return None


def is_streamlit_cloud():
    """
    Streamlit Cloud 환경인지 정확히 감지 (수정 버전)
    
    Returns:
        bool: Streamlit Cloud 여부
    """
    try:
        # 🔥 더 정확한 Streamlit Cloud 감지
        cloud_indicators = [
            # 환경변수 기반 감지
            os.environ.get('STREAMLIT_CLOUD') == 'true',
            'streamlit.app' in os.environ.get('HOSTNAME', ''),
            'share.streamlit.io' in os.environ.get('HOSTNAME', ''),
            
            # secrets 실제 존재 여부 확인 (중요!)
            hasattr(st, 'secrets') and _check_secrets_available()
        ]
        
        # 모든 조건 중 하나라도 충족되면 클라우드
        return any(cloud_indicators)
    except:
        return False


def _check_secrets_available():
    """
    st.secrets가 실제로 사용 가능한지 확인
    
    Returns:
        bool: secrets 사용 가능 여부
    """
    try:
        # secrets에 실제로 접근해보기
        _ = len(st.secrets)
        return True
    except:
        # secrets 접근 실패 = 로컬 환경
        return False


def get_openai_client():
    """
    OpenAI 클라이언트 초기화 (환경 감지 수정)
    
    Returns:
        client: OpenAI 클라이언트 객체 또는 None
    """
    if not OPENAI_API_KEY:
        return None
    
    version = detect_openai_version()
    
    if version == "v1":
        # 🔥 Modern SDK (v1.0.0+) 방식
        try:
            from openai import OpenAI
            
            # 🔥 수정된 환경 감지
            is_cloud = is_streamlit_cloud()
            
            if is_cloud:
                # Streamlit Cloud: proxies 문제 대응
                try:
                    return OpenAI(api_key=OPENAI_API_KEY)
                except TypeError as e:
                    if "proxies" in str(e):
                        # proxies 문제 발생시 환경변수 방식으로 재시도
                        import openai
                        openai.api_key = OPENAI_API_KEY
                        return openai
                    raise e
            else:
                # 로컬 환경: 정상적인 클라이언트 생성
                return OpenAI(api_key=OPENAI_API_KEY)
                
        except ImportError:
            return None
    
    elif version == "v0":
        # 🔥 Legacy SDK (v0.x) 방식
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            return openai
        except ImportError:
            return None
    
    else:
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
    if source_type == "upload":
        # 🔥 업로드 파일 파일명 접근 수정
        if isinstance(audio_data, dict):
            # main.py에서 변환된 딕셔너리 형태
            filename = audio_data.get('name', 'uploaded_file')
        else:
            # 원본 UploadedFile 객체
            filename = getattr(audio_data, 'name', 'uploaded_file')
        
        # 업로드된 파일의 원본 확장자 추출
        file_ext = os.path.splitext(filename)[1].lower()
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


def transcribe_audio_modern(client, temp_path, file_extension, original_filename):
    """
    Modern SDK (v1.0.0+)를 사용한 전사
    
    Args:
        client: OpenAI 클라이언트
        temp_path: 임시 파일 경로
        file_extension: 파일 확장자
        original_filename: 원본 파일명
        
    Returns:
        tuple: (transcription_text, duration)
    """
    with open(temp_path, "rb") as audio_file:
        filename = original_filename or f"audio{file_extension}"
        
        # Modern SDK API 호출
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_file, f"audio/{file_extension[1:]}"),
            language="ko",
            response_format="verbose_json"
        )
    
    # 텍스트 및 duration 추출
    transcription_text = transcription.text.strip()
    duration = getattr(transcription, 'duration', None)
    
    return transcription_text, duration


def transcribe_audio_legacy(client, temp_path):
    """
    Legacy SDK (v0.x)를 사용한 전사
    
    Args:
        client: OpenAI 클라이언트 (모듈)
        temp_path: 임시 파일 경로
        
    Returns:
        tuple: (transcription_text, duration)
    """
    with open(temp_path, "rb") as audio_file:
        # Legacy SDK API 호출
        transcription = client.Audio.transcribe(
            model="whisper-1",
            file=audio_file,
            language="ko",
            response_format="verbose_json"
        )
    
    # 텍스트 및 duration 추출
    if isinstance(transcription, dict):
        transcription_text = transcription.get('text', '').strip()
        duration = transcription.get('duration', None)
    else:
        transcription_text = str(transcription).strip()
        duration = None
    
    return transcription_text, duration


def transcribe_audio(audio_bytes, file_extension=".wav", source_type="recording", original_filename=None):
    """
    OpenAI API Whisper를 사용한 오디오 바이트 텍스트 변환 (환경 감지 수정)
    
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
        # 🔥 환경 감지 및 클라이언트 초기화
        client = get_openai_client()
        if not client:
            st.error("❌ Failed to initialize OpenAI client")
            return "", 0.0
        
        # 🔥 환경 정보 출력 (디버그용)
        is_cloud = is_streamlit_cloud()
        version = detect_openai_version()
        
        print(f"🔍 Environment: {'Streamlit Cloud' if is_cloud else 'Local'}")
        print(f"🔍 OpenAI SDK: v{version}")
        print(f"🔍 API Key: {'✅' if OPENAI_API_KEY else '❌'}")
        
        # SDK 버전에 따른 API 호출
        if version == "v1":
            # Modern SDK 사용
            transcription_text, duration = transcribe_audio_modern(
                client, temp_path, file_extension, original_filename
            )
        elif version == "v0":
            # Legacy SDK 사용
            transcription_text, duration = transcribe_audio_legacy(
                client, temp_path
            )
        else:
            raise Exception("Unsupported OpenAI SDK version")
        
        # duration이 없으면 추정값 사용
        if duration is None:
            duration = estimate_audio_duration(audio_bytes)
        
        return transcription_text, duration
        
    except Exception as e:
        error_msg = str(e)
        
        # 🔥 상세한 에러 처리
        if "secrets" in error_msg.lower():
            st.error("❌ Configuration error detected")
            st.info("💡 Please check your .env file contains OPENAI_API_KEY")
        elif "proxies" in error_msg.lower():
            st.error("❌ Streamlit Cloud compatibility issue detected")
            st.info("💡 This is a known issue. Please try again.")
        elif "api_key" in error_msg.lower():
            st.error("❌ Invalid OpenAI API key")
            st.info("💡 Please check your API key configuration")
        elif "quota" in error_msg.lower():
            st.error("❌ OpenAI API quota exceeded")
            st.info("💡 Please check your OpenAI account usage")
        elif "timeout" in error_msg.lower():
            st.error("❌ Request timeout - file may be too large")
            st.info("💡 Try with a shorter audio file (under 25MB)")
        elif "file" in error_msg.lower() and "format" in error_msg.lower():
            st.error(f"❌ File format error: {original_filename or 'audio file'}")
            st.info("💡 Supported formats: WAV, MP3, M4A, FLAC, OGG, WEBM")
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
    음성 길이를 기반으로 품질 평가 (1분~2분 목표로 수정)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        dict: 품질 평가 정보
    """
    from config import AUDIO_QUALITY
    
    TARGET_MIN_DURATION = 60  # 1분
    TARGET_MAX_DURATION = 120 # 2분

    if TARGET_MIN_DURATION <= duration <= TARGET_MAX_DURATION:
        return {
            "status": "excellent",
            "icon": "✅",
            "message": f"Excellent! Your recording is {duration:.1f}s — a perfect length (1-2 minutes) for the interview!",
            "color": "success"
        }
    elif duration > TARGET_MAX_DURATION:
        return {
            "status": "long",
            "icon": "📝",
            "message": f"Great! ({duration:.1f}s) You've provided plenty of content",
            "color": "info"
        }
    elif duration >= AUDIO_QUALITY["good_min_duration"]:  # config.py의 "good_min_duration" 값에 따라 1분 미만이지만 양호한 범위
        return {
            "status": "good",
            "icon": "🌟",
            "message": f"Good start! ({duration:.1f}s) Aim for 1-2 minutes for best results.",
            "color": "info"
        }
    elif duration >= AUDIO_QUALITY["fair_min_duration"]:  # config.py의 "fair_min_duration" 값에 따라 다소 짧은 범위
        return {
            "status": "fair",
            "icon": "⚠️",
            "message": f"Fair start! ({duration:.1f}s) Aim for 1-2 minutes to show better fluency.",
            "color": "warning"
        }
    else:  # 최소 길이 미만
        return {
            "status": "very_short",
            "icon": "❌",
            "message": f"Too brief! ({duration:.1f}s) Please speak for at least 1 minute, ideally 60–120 seconds.",
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
        uploaded_file: Streamlit 업로드 파일 객체 또는 딕셔너리
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # OpenAI Whisper API 지원 형식
    SUPPORTED_FORMATS = ["wav", "mp3", "m4a", "flac", "ogg", "webm", "mp4", "mpeg", "mpga", "oga"]
    
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # 🔥 파일명 접근 수정
    if isinstance(uploaded_file, dict):
        # main.py에서 변환된 딕셔너리 형태
        filename = uploaded_file.get('name', 'uploaded_file')
        file_size = len(uploaded_file.get('bytes', b''))
    else:
        # 원본 UploadedFile 객체
        filename = getattr(uploaded_file, 'name', 'uploaded_file')
        file_size = getattr(uploaded_file, 'size', 0)
    
    # 파일 확장자 확인
    file_extension = filename.split('.')[-1].lower()
    if file_extension not in SUPPORTED_FORMATS:
        return False, f"❌ Unsupported format '{file_extension}'. Supported: {', '.join(SUPPORTED_FORMATS)}"
    
    # 파일 크기 확인 (OpenAI API 제한: 25MB)
    if file_size > 25 * 1024 * 1024:
        return False, "❌ File too large. Maximum size: 25MB (OpenAI API limit)"
    
    # 기본적인 파일 크기 검증
    if file_size < 1024:  # 1KB 미만
        return False, "❌ File too small. Please upload a valid audio file"
    
    return True, "✅ Valid audio file"


def process_audio_input(audio_data, source_type="recording"):
    """
    오디오 입력을 처리하고 전사 (파일명 접근 수정)
    
    Args:
        audio_data: 오디오 데이터 (녹음 또는 업로드 - 딕셔너리 또는 원본 객체)
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
            
            # 🔥 파일명 접근 수정 - 딕셔너리와 원본 객체 모두 처리
            if isinstance(audio_data, dict):
                # main.py에서 변환된 딕셔너리 형태
                original_filename = audio_data.get('name', 'uploaded_file')
                audio_bytes = audio_data.get('bytes', b'')
            else:
                # 원본 UploadedFile 객체 (혹시 변환 안 된 경우)
                original_filename = getattr(audio_data, 'name', 'uploaded_file')
                audio_bytes = audio_data.read()
                audio_data.seek(0)  # 포인터 리셋
            
            file_ext = os.path.splitext(original_filename)[1].lower()
        else:
            # 녹음된 오디오 처리
            audio_bytes = audio_data['bytes']
            original_filename = "recording.wav"
            file_ext = ".wav"
        
        # 🔥 환경 정보 표시
        is_cloud = is_streamlit_cloud()
        version = detect_openai_version()
        env_info = f"{'Streamlit Cloud' if is_cloud else 'Local'} + OpenAI SDK v{version}"
        
        with st.spinner(f"🎙️ Converting speech to text ..."):
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
        st.error(f"❌ Audio processing error: {error_msg}")
        return "", 0.0, False


def check_whisper_availability():
    """
    Whisper API 사용 가능 여부 확인 (환경 감지 수정)
    
    Returns:
        tuple: (is_available, status_message)
    """
    if not OPENAI_API_KEY:
        return False, "OpenAI API key not configured"
    
    try:
        client = get_openai_client()
        version = detect_openai_version()
        is_cloud = is_streamlit_cloud()
        
        if client and version:
            env_info = f"{'Cloud' if is_cloud else 'Local'} + SDK v{version}"
            return True, f"OpenAI API Whisper ready"
        else:
            return False, "Failed to initialize OpenAI client"
    except Exception as e:
        return False, f"OpenAI client error: {str(e)}"


def display_whisper_status():
    """
    Whisper API 상태를 사이드바에 표시 (환경 정보 포함)
    """
    is_available, status = check_whisper_availability()
    
    if is_available:
        st.write(f"Speech Recognition: ✅ Ready ({status})")
    else:
        st.write(f"Speech Recognition: ❌ {status}")


def test_whisper_api():
    """
    Whisper API 연결 테스트 (환경 감지 수정)
    
    Returns:
        bool: 테스트 성공 여부
    """
    try:
        client = get_openai_client()
        version = detect_openai_version()
        
        if client and version:
            return True
        else:
            return False
        
    except Exception as e:
        print(f"Whisper API test failed: {e}")
        return False