"""
data_io.py
실험 데이터 저장, 백업, 업로드 및 로그 관리 모듈 (OAuth 방식 Google Drive 연동 최종 버전)
"""

import os
import csv
import json
import zipfile
from datetime import datetime, timedelta
import streamlit as st
from config import (
    FOLDERS, 
    DATA_RETENTION_DAYS, 
    EXPERIMENT_QUESTION,
    GOOGLE_DRIVE_ENABLED,
    GOOGLE_OAUTH_CREDENTIALS_JSON,  # OAuth 방식으로 변경
    GOOGLE_DRIVE_FOLDER_ID,
    LOG_FORMAT,
    CURRENT_SESSION,
    SESSION_LABELS
)


def save_session_data():
    """
    세션 데이터를 CSV 및 Excel 형식으로 저장
    
    Returns:
        tuple: (csv_filename, excel_filename, audio_folder, saved_files, zip_filename)
    """
    try:
        # 필요한 폴더 생성
        for folder in FOLDERS.values():
            os.makedirs(folder, exist_ok=True)
        
        # 고유한 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 세션 데이터 구성
        session_data = build_session_data(timestamp)
        
        # CSV 파일 저장
        csv_filename = save_to_csv(session_data, timestamp)
        
        # Excel 변환
        excel_filename = convert_csv_to_excel(csv_filename)
        
        # 음성 파일들 저장
        audio_folder, saved_files = save_audio_files(timestamp)
        
        # 백업 ZIP 생성
        zip_filename = create_backup_zip(st.session_state.session_id, timestamp)
        
        return csv_filename, excel_filename, audio_folder, saved_files, zip_filename
    
    except Exception as e:
        st.error(f"❌ Error saving session data: {str(e)}")
        return None, None, None, [], None


def build_session_data(timestamp):
    """
    세션 데이터 딕셔너리 구성 (배경 정보 포함)
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        dict: 완성된 세션 데이터
    """
    return {
        'session_id': st.session_state.session_id,
        'session_number': getattr(st.session_state, 'session_number', CURRENT_SESSION),
        'session_label': getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1")),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # === 배경 정보 (새로 추가) ===
        'learning_duration': getattr(st.session_state, 'learning_duration', ''),
        'speaking_confidence': getattr(st.session_state, 'speaking_confidence', ''),
        
        # === 강화된 동의 추적 ===
        'consent_given': getattr(st.session_state, 'consent_given', False),
        'consent_timestamp': getattr(st.session_state, 'consent_timestamp', ''),
        'consent_participation': getattr(st.session_state, 'consent_participation', False),
        'consent_audio_ai': getattr(st.session_state, 'consent_audio_ai', False),
        'consent_data_storage': getattr(st.session_state, 'consent_data_storage', False),
        'consent_privacy_rights': getattr(st.session_state, 'consent_privacy_rights', False),
        'consent_final_confirmation': getattr(st.session_state, 'consent_final_confirmation', False),
        'consent_zoom_interview': getattr(st.session_state, 'consent_zoom_interview', False),
        'gdpr_compliant': getattr(st.session_state, 'gdpr_compliant', False),
        'consent_pdf_generated': getattr(st.session_state, 'consent_pdf', '') != '',
        'consent_pdf_filename': getattr(st.session_state, 'consent_pdf', ''),
        'consent_drive_file_id': getattr(st.session_state, 'consent_drive_file_id', ''),
        
        # === 실험 데이터 ===
        'question': EXPERIMENT_QUESTION,
        'transcription_1': st.session_state.transcription_1,
        'transcription_2': st.session_state.transcription_2,
        'gpt_feedback_json': json.dumps(st.session_state.feedback, ensure_ascii=False),
        
        # === 데이터 품질 분석 필드 ===
        'audio_duration_1': getattr(st.session_state, 'audio_duration_1', 0.0),
        'audio_duration_2': getattr(st.session_state, 'audio_duration_2', 0.0),
        'audio_quality_check_1': get_audio_quality_label(getattr(st.session_state, 'audio_duration_1', 0)),
        'audio_quality_check_2': get_audio_quality_label(getattr(st.session_state, 'audio_duration_2', 0)),
        
        # === 개선도 평가 데이터 (STT 루브릭 기반) ===
        'improvement_score': getattr(st.session_state, 'improvement_assessment', {}).get('improvement_score', 0),
        'improvement_reason': getattr(st.session_state, 'improvement_assessment', {}).get('improvement_reason', ''),
        'first_attempt_score': getattr(st.session_state, 'improvement_assessment', {}).get('first_attempt_score', 0),
        'second_attempt_score': getattr(st.session_state, 'improvement_assessment', {}).get('second_attempt_score', 0),
        'score_difference': getattr(st.session_state, 'improvement_assessment', {}).get('score_difference', 0),
        'feedback_application': getattr(st.session_state, 'improvement_assessment', {}).get('feedback_application', ''),
        'specific_improvements': json.dumps(getattr(st.session_state, 'improvement_assessment', {}).get('specific_improvements', []), ensure_ascii=False),
        'remaining_issues': json.dumps(getattr(st.session_state, 'improvement_assessment', {}).get('remaining_issues', []), ensure_ascii=False),
        'overall_assessment': getattr(st.session_state, 'improvement_assessment', {}).get('overall_assessment', ''),
        'improvement_assessment_json': json.dumps(getattr(st.session_state, 'improvement_assessment', {}), ensure_ascii=False),
        
        # === 실제 사용되는 피드백 필드들만 ===
        'suggested_model_sentence': st.session_state.feedback.get('suggested_model_sentence', ''),
        'suggested_model_sentence_english': st.session_state.feedback.get('suggested_model_sentence_english', ''),
        'fluency_comment': st.session_state.feedback.get('fluency_comment', ''),
        'interview_readiness_score': st.session_state.feedback.get('interview_readiness_score', ''),
        'interview_readiness_reason': st.session_state.feedback.get('interview_readiness_reason', ''),
        'grammar_expression_tip': st.session_state.feedback.get('grammar_expression_tip', ''),
        
        # === STT 루브릭 기반 피드백 분석 ===
        'grammar_issues_count': len(st.session_state.feedback.get('grammar_issues', [])),
        'vocabulary_suggestions_count': len(st.session_state.feedback.get('vocabulary_suggestions', [])),
        'content_expansion_suggestions_count': len(st.session_state.feedback.get('content_expansion_suggestions', [])),
        'content_expansion_suggestions_json': json.dumps(st.session_state.feedback.get('content_expansion_suggestions', []), ensure_ascii=False),
        'grammar_issues_json': json.dumps(st.session_state.feedback.get('grammar_issues', []), ensure_ascii=False),
        'vocabulary_suggestions_json': json.dumps(st.session_state.feedback.get('vocabulary_suggestions', []), ensure_ascii=False),
        'highlight_targets_json': json.dumps(st.session_state.feedback.get('highlight_targets', {}), ensure_ascii=False),
        
        # 디버그 정보
        'gpt_model_used': st.session_state.gpt_debug_info.get('model_used', ''),
        'gpt_attempts': st.session_state.gpt_debug_info.get('attempts', 0),
        
        # 오디오 파일 정보 (세션 번호 포함)
        'audio_folder': f"{FOLDERS['audio_recordings']}/{getattr(st.session_state, 'session_number', CURRENT_SESSION)}_{st.session_state.session_id}_{timestamp}",
        
        # === 데이터 관리 정보 ===
        'data_retention_until': (datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d'),
        'deletion_requested': False,
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def get_audio_quality_label(duration):
    """
    음성 길이에 따른 품질 라벨 반환 (60초 목표)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        str: 품질 라벨
    """
    if duration >= 60:
        return 'excellent'
    elif duration >= 45:
        return 'good'
    elif duration >= 30:
        return 'fair'
    else:
        return 'very_short'


def save_to_csv(session_data, timestamp):
    """
    세션 데이터를 CSV로 저장
    
    Args:
        session_data: 세션 데이터 딕셔너리
        timestamp: 타임스탬프
        
    Returns:
        str: CSV 파일 경로
    """
    # 세션 번호를 파일명에 포함
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    csv_filename = os.path.join(
        FOLDERS["data"], 
        f"korean_session{session_num}_{st.session_state.session_id}_{timestamp}.csv"
    )
    
    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=session_data.keys())
        writer.writeheader()
        writer.writerow(session_data)
    
    return csv_filename


def convert_csv_to_excel(csv_filename):
    """
    CSV를 Excel로 변환
    
    Args:
        csv_filename: CSV 파일 경로
        
    Returns:
        str: Excel 파일 경로 또는 None
    """
    try:
        import pandas as pd
        
        # CSV 읽기
        df = pd.read_csv(csv_filename, encoding='utf-8')
        
        # Excel 파일명 생성
        excel_filename = csv_filename.replace('.csv', '.xlsx')
        
        # Excel로 저장
        df.to_excel(excel_filename, index=False, engine='openpyxl')
        
        return excel_filename
    except ImportError:
        st.warning("⚠️ Excel conversion requires pandas and openpyxl. Install with: pip install pandas openpyxl")
        return None
    except Exception as e:
        st.error(f"❌ Error converting to Excel: {e}")
        return None


def save_audio_files(timestamp):
    """
    음성 파일들을 저장
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        tuple: (folder_path, saved_files_list)
    """
    try:
        # 오디오 폴더 생성 (세션 번호 포함)
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        folder_name = os.path.join(
            FOLDERS["audio_recordings"], 
            f"session{session_num}_{st.session_state.session_id}_{timestamp}"
        )
        os.makedirs(folder_name, exist_ok=True)
        
        saved_files = []
        
        # 첫 번째 녹음
        if hasattr(st.session_state, 'first_audio') and st.session_state.first_audio:
            file_path = os.path.join(folder_name, "first_audio.wav")
            with open(file_path, "wb") as f:
                f.write(st.session_state.first_audio["bytes"])
            saved_files.append("first_audio.wav")
        
        # 두 번째 녹음
        if hasattr(st.session_state, 'second_audio') and st.session_state.second_audio:
            file_path = os.path.join(folder_name, "second_audio.wav")
            with open(file_path, "wb") as f:
                f.write(st.session_state.second_audio["bytes"])
            saved_files.append("second_audio.wav")
        
        # 모델 음성 (일반 속도)
        if st.session_state.model_audio.get("normal"):
            file_path = os.path.join(folder_name, "model_normal.mp3")
            with open(file_path, "wb") as f:
                f.write(st.session_state.model_audio["normal"])
            saved_files.append("model_normal.mp3")
        
        # 모델 음성 (느린 속도)
        if st.session_state.model_audio.get("slow"):
            file_path = os.path.join(folder_name, "model_slow.mp3")
            with open(file_path, "wb") as f:
                f.write(st.session_state.model_audio["slow"])
            saved_files.append("model_slow.mp3")
        
        return folder_name, saved_files
    
    except Exception as e:
        st.error(f"❌ Error saving audio files: {str(e)}")
        return None, []


def create_backup_zip(session_id, timestamp):
    """
    세션 데이터를 ZIP으로 백업
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        str: ZIP 파일 경로 또는 None
    """
    try:
        # 세션 번호를 ZIP 파일명에 포함
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        zip_filename = os.path.join(
            FOLDERS["data"], 
            f"backup_session{session_num}_{session_id}_{timestamp}.zip"
        )
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # CSV 파일 추가
            csv_file = os.path.join(FOLDERS["data"], f"korean_session{session_num}_{session_id}_{timestamp}.csv")
            if os.path.exists(csv_file):
                zipf.write(csv_file, f"session_data_{timestamp}.csv")
            
            # Excel 파일 추가
            excel_file = csv_file.replace('.csv', '.xlsx')
            if os.path.exists(excel_file):
                zipf.write(excel_file, f"session_data_{timestamp}.xlsx")
            
            # 동의서 PDF 추가
            consent_pdf = os.path.join(FOLDERS["data"], f"{session_id}_consent.pdf")
            if os.path.exists(consent_pdf):
                zipf.write(consent_pdf, f"consent_form_{session_id}.pdf")
            
            # 음성 파일들 추가
            audio_folder = os.path.join(FOLDERS["audio_recordings"], f"session{session_num}_{session_id}_{timestamp}")
            if os.path.exists(audio_folder):
                for file in os.listdir(audio_folder):
                    file_path = os.path.join(audio_folder, file)
                    zipf.write(file_path, f"audio/{file}")
        
        return zip_filename
    except Exception as e:
        st.error(f"❌ Error creating backup ZIP: {e}")
        return None


def get_google_drive_credentials():
    """
    OAuth 방식으로 Google Drive 인증 정보 가져오기
    
    Returns:
        tuple: (Credentials, status_message)
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        # OAuth 스코프 설정 (전체 드라이브 접근 권한)
        SCOPES = ['https://www.googleapis.com/auth/drive']
        
        creds = None
        token_file = 'token.json'
        
        # 기존 토큰 파일 확인
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        # 토큰이 없거나 만료된 경우 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 토큰 갱신 중...")
                creds.refresh(Request())
            else:
                if not GOOGLE_OAUTH_CREDENTIALS_JSON or not os.path.exists(GOOGLE_OAUTH_CREDENTIALS_JSON):
                    return None, "OAuth credentials file not found"
                
                print("🌐 브라우저에서 Google 인증을 진행해주세요...")
                flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_CREDENTIALS_JSON, SCOPES)
                creds = flow.run_local_server(port=0)
                print("✅ 인증 완료!")
            
            # 토큰 저장 (다음에 재사용)
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("💾 인증 토큰 저장됨")
        
        return creds, "Success"
        
    except ImportError as e:
        return None, f"Missing required libraries: {str(e)}. Run: pip install google-auth-oauthlib"
    except Exception as e:
        return None, f"Authentication failed: {str(e)}"


def upload_to_google_drive(file_path, filename, folder_id=None):
    """
    OAuth 방식으로 Google Drive에 파일 업로드
    
    Args:
        file_path: 업로드할 파일 경로
        filename: Drive에서 사용할 파일명
        folder_id: 대상 폴더 ID
        
    Returns:
        tuple: (file_id, status_message)
    """
    try:
        if not GOOGLE_DRIVE_ENABLED:
            return None, "Google Drive upload not configured"
        
        # OAuth 인증 정보 가져오기
        creds, auth_message = get_google_drive_credentials()
        if not creds:
            return None, f"Authentication failed: {auth_message}"
        
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        
        # Drive API 서비스 빌드
        service = build('drive', 'v3', credentials=creds)
        
        # 파일 메타데이터 설정
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # 파일 업로드
        media = MediaFileUpload(file_path)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name'
        ).execute()
        
        file_id = file.get('id')
        file_name = file.get('name')
        
        return file_id, f"Successfully uploaded: {file_name} (ID: {file_id})"
        
    except ImportError as e:
        return None, f"Missing required libraries: {str(e)}"
    except HttpError as e:
        return None, f"Google API error: {str(e)}"
    except FileNotFoundError:
        return None, f"File not found: {file_path}"
    except Exception as e:
        return None, f"Upload failed: {str(e)}"


def auto_backup_to_drive(csv_filename, excel_filename, zip_filename, session_id, timestamp):
    """
    실험 데이터를 Google Drive에 자동 백업 (OAuth 방식)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로
        zip_filename: ZIP 파일 경로
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        tuple: (uploaded_files, errors)
    """
    uploaded_files = []
    errors = []
    
    if not GOOGLE_DRIVE_ENABLED:
        errors.append("Google Drive upload is disabled in configuration")
        return uploaded_files, errors
    
    # 세션 번호를 Drive 파일명에 포함
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    session_label = SESSION_LABELS.get(session_num, f"Session {session_num}")
    
    files_to_upload = []
    
    # 업로드할 파일 목록 준비
    if csv_filename and os.path.exists(csv_filename):
        drive_filename = f"{session_label}_{session_id}_{timestamp}.csv"
        files_to_upload.append((csv_filename, drive_filename))
    
    if excel_filename and os.path.exists(excel_filename):
        drive_filename = f"{session_label}_{session_id}_{timestamp}.xlsx"
        files_to_upload.append((excel_filename, drive_filename))
    
    if zip_filename and os.path.exists(zip_filename):
        drive_filename = f"backup_{session_label}_{session_id}_{timestamp}.zip"
        files_to_upload.append((zip_filename, drive_filename))
    
    # 동의서 PDF도 업로드 (있는 경우)
    consent_pdf = os.path.join(FOLDERS["data"], f"{session_id}_consent.pdf")
    if os.path.exists(consent_pdf):
        drive_filename = f"{session_label}_{session_id}_consent.pdf"
        files_to_upload.append((consent_pdf, drive_filename))
    
    # 파일들 업로드 실행
    for file_path, drive_filename in files_to_upload:
        try:
            file_id, result = upload_to_google_drive(
                file_path, 
                drive_filename, 
                GOOGLE_DRIVE_FOLDER_ID
            )
            
            if file_id:
                uploaded_files.append(drive_filename)
                # 동의서 파일 ID 저장 (향후 참조용)
                if "consent" in drive_filename:
                    st.session_state.consent_drive_file_id = file_id
            else:
                errors.append(f"{drive_filename}: {result}")
                
        except Exception as e:
            errors.append(f"{drive_filename}: Unexpected error - {str(e)}")
    
    return uploaded_files, errors


def test_google_drive_connection():
    """
    OAuth 기반 Google Drive 연결 테스트
    
    Returns:
        tuple: (success, message)
    """
    try:
        if not GOOGLE_DRIVE_ENABLED:
            return False, "Google Drive upload is disabled in configuration"
        
        # OAuth 인증 정보 가져오기
        creds, auth_message = get_google_drive_credentials()
        if not creds:
            return False, f"Authentication failed: {auth_message}"
        
        from googleapiclient.discovery import build
        
        # Drive API 서비스 빌드
        service = build('drive', 'v3', credentials=creds)
        
        # 폴더 존재 확인
        if GOOGLE_DRIVE_FOLDER_ID:
            folder = service.files().get(
                fileId=GOOGLE_DRIVE_FOLDER_ID, 
                fields='id,name'
            ).execute()
            folder_name = folder.get('name', 'Unknown')
            return True, f"✅ Connected successfully to folder: {folder_name}"
        else:
            return True, "✅ Connection successful, but no target folder specified"
        
    except ImportError as e:
        return False, f"Missing libraries: {str(e)}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def log_upload_status(session_id, timestamp, uploaded_files, errors, email_sent=False):
    """
    Google Drive 업로드 결과를 로그 파일에 기록
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        uploaded_files: 업로드된 파일 목록
        errors: 오류 목록
        email_sent: 이메일 전송 여부
        
    Returns:
        bool: 로그 기록 성공 여부
    """
    try:
        # 로그 폴더 생성
        os.makedirs(FOLDERS["logs"], exist_ok=True)
        
        # 일별 로그 파일
        log_date = datetime.now().strftime('%Y%m%d')
        log_filename = os.path.join(
            FOLDERS["logs"], 
            f"upload_log_{log_date}.txt"
        )
        
        # 세션 정보 포함
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
        
        # 업로드 상태 결정
        upload_status = "SUCCESS" if uploaded_files and not errors else "PARTIAL" if uploaded_files else "FAILED"
        
        # 로그 엔트리 생성 (OAuth 방식 표시)
        log_entry = f"""
[{datetime.now().strftime(LOG_FORMAT['timestamp_format'])}] SESSION: {session_label} - {session_id}_{timestamp}
Status: {upload_status}
Google Drive Enabled: {GOOGLE_DRIVE_ENABLED} (OAuth method)
Files uploaded: {len(uploaded_files)} ({', '.join(uploaded_files) if uploaded_files else 'None'})
Errors: {len(errors)} ({'; '.join(errors) if errors else 'None'})
Email notification: {'Sent' if email_sent else 'Not sent/Failed'}
{'='*80}
"""
        
        # 로그 파일에 추가
        with open(log_filename, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
        
        return True
    except Exception as e:
        print(f"Logging failed: {e}")
        return False


def display_download_buttons(csv_filename, excel_filename, zip_filename):
    """
    연구자용 다운로드 버튼들 표시
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로  
        zip_filename: ZIP 파일 경로
    """
    if GOOGLE_DRIVE_ENABLED:
        st.info("📤 Data should be automatically uploaded to Google Drive (OAuth). Use these downloads as backup only.")
    else:
        st.warning("⚠️ Google Drive upload is disabled. Use these download buttons to save your data.")
    
    col1, col2, col3 = st.columns(3)
    
    # 세션 정보를 다운로드 파일명에 포함
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        # CSV 다운로드
        if csv_filename and os.path.exists(csv_filename):
            try:
                with open(csv_filename, 'r', encoding='utf-8') as f:
                    csv_data = f.read()
                st.download_button(
                    label="📄 Backup CSV",
                    data=csv_data,
                    file_name=f"session{session_num}_{st.session_state.session_id}_{timestamp_str}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            except:
                st.error("CSV download failed")
        else:
            st.info("CSV unavailable")
    
    with col2:
        # Excel 다운로드
        if excel_filename and os.path.exists(excel_filename):
            try:
                with open(excel_filename, 'rb') as f:
                    excel_data = f.read()
                st.download_button(
                    label="📊 Backup Excel",
                    data=excel_data,
                    file_name=f"session{session_num}_{st.session_state.session_id}_{timestamp_str}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
            except:
                st.info("Excel unavailable")
        else:
            st.info("Excel unavailable")
    
    with col3:
        # ZIP 완전 백업 다운로드
        if zip_filename and os.path.exists(zip_filename):
            try:
                with open(zip_filename, 'rb') as f:
                    zip_data = f.read()
                st.download_button(
                    label="📦 Backup ZIP",
                    data=zip_data,
                    file_name=f"backup_session{session_num}_{st.session_state.session_id}_{timestamp_str}.zip",
                    mime='application/zip',
                    use_container_width=True
                )
            except:
                st.info("ZIP unavailable")
        else:
            st.info("ZIP unavailable")


def display_session_details():
    """
    연구자용 세션 상세 정보 표시 (배경 정보 포함)
    """
    st.markdown("**📋 Session Details:**")
    display_name = getattr(st.session_state, 'original_nickname', st.session_state.session_id)
    session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
    st.write(f"**Participant:** {display_name} (ID: {st.session_state.session_id})")
    st.write(f"**Session:** {session_label}")
    st.write(f"**Question:** {EXPERIMENT_QUESTION}")
    st.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # === 배경 정보 표시 (새로 추가) ===
    learning_duration = getattr(st.session_state, 'learning_duration', '')
    speaking_confidence = getattr(st.session_state, 'speaking_confidence', '')
    if learning_duration:
        st.write(f"**Learning Duration:** {learning_duration}")
    if speaking_confidence:
        st.write(f"**Speaking Confidence:** {speaking_confidence}")
    
    # === Google Drive 파일 추적 정보 추가 ===
    if hasattr(st.session_state, 'consent_drive_file_id') and st.session_state.consent_drive_file_id:
        st.write(f"**Consent Drive ID:** {st.session_state.consent_drive_file_id}")
    
    # === Google Drive 연동 상태 표시 (OAuth 방식) ===
    st.markdown("**☁️ Google Drive Status (OAuth):**")
    if GOOGLE_DRIVE_ENABLED:
        st.success("✅ Google Drive upload is enabled (OAuth method)")
        if GOOGLE_DRIVE_FOLDER_ID:
            st.write(f"Target Folder ID: {GOOGLE_DRIVE_FOLDER_ID[:20]}...")
        else:
            st.warning("⚠️ No target folder specified")
        
        # OAuth 토큰 상태 확인
        if os.path.exists('token.json'):
            st.write("🔑 OAuth token: Available")
        else:
            st.write("🔑 OAuth token: Will be requested on first upload")
    else:
        st.warning("❌ Google Drive upload is disabled")


def display_data_quality_info():
    """
    데이터 품질 정보 표시 (STT 루브릭 기반 - 60초 목표)
    """
    st.markdown("**📊 Data Quality (STT Rubric-Based):**")
    col1, col2 = st.columns(2)
    
    with col1:
        duration1 = getattr(st.session_state, 'audio_duration_1', 0)
        if duration1 > 0:
            quality1 = get_quality_description(duration1)
            st.write(f"First recording: {duration1:.1f}s")
            st.caption(quality1)
        
        if st.session_state.feedback:
            issues_count = len(st.session_state.feedback.get('grammar_issues', []))
            vocab_count = len(st.session_state.feedback.get('vocabulary_suggestions', []))
            content_count = len(st.session_state.feedback.get('content_expansion_suggestions', []))
            st.write(f"Grammar issues: {issues_count}")
            st.write(f"Vocab suggestions: {vocab_count}")
            st.write(f"Content ideas: {content_count}")
            
            rubric_score = st.session_state.feedback.get('interview_readiness_score', 'N/A')
            st.write(f"STT Rubric Score: {rubric_score}/10")
    
    with col2:
        duration2 = getattr(st.session_state, 'audio_duration_2', 0)
        if duration2 > 0:
            quality2 = get_quality_description(duration2)
            st.write(f"Second recording: {duration2:.1f}s")
            st.caption(quality2)
        
        if hasattr(st.session_state, 'improvement_assessment'):
            improvement = st.session_state.improvement_assessment
            score = improvement.get('improvement_score', 0)
            first_score = improvement.get('first_attempt_score', 0)
            second_score = improvement.get('second_attempt_score', 0)
            st.write(f"Improvement score: {score}/10")
            st.write(f"Progress: {first_score} → {second_score}")
            improvements = len(improvement.get('specific_improvements', []))
            issues = len(improvement.get('remaining_issues', []))
            st.write(f"Improvements: {improvements}")
            st.write(f"Remaining issues: {issues}")


def get_quality_description(duration):
    """
    음성 길이에 따른 품질 설명 반환 (60초 목표)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        str: 품질 설명
    """
    if duration >= 60:
        return "✅ Excellent (60s+ target reached!)"
    elif duration >= 45:
        return "🌟 Good (45-60s, try for 60+)"
    elif duration >= 30:
        return "⚠️ Fair (30-45s, needs improvement)"
    else:
        return "❌ Very Short (under 30s, much more needed)"


def cleanup_old_files(days_old=7):
    """
    오래된 임시 파일들 정리
    
    Args:
        days_old: 삭제할 파일 나이 (일)
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for folder in FOLDERS.values():
            if os.path.exists(folder):
                for filename in os.listdir(folder):
                    file_path = os.path.join(folder, filename)
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            print(f"Cleaned up old file: {filename}")
    except Exception as e:
        print(f"Cleanup failed: {e}")