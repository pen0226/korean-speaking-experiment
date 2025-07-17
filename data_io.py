"""
data_io.py
실험 데이터 저장, 백업, 업로드 및 로그 관리 모듈 (Excel 변환 제거 - 간소화 버전)
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
    GCS_ENABLED,
    GCS_BUCKET_NAME,
    GCS_SERVICE_ACCOUNT,
    GCS_SIMPLE_STRUCTURE,
    LOG_FORMAT,
    CURRENT_SESSION,
    SESSION_LABELS
)


def save_session_data():
    """
    세션 데이터를 CSV 형식으로 저장 (Excel 변환 제거)
    
    Returns:
        tuple: (csv_filename, excel_filename, audio_folder, saved_files, zip_filename, timestamp)
    """
    try:
        # 🎯 중복 저장 방지 로직
        if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
            if hasattr(st.session_state, 'saved_files'):
                st.info("ℹ️ Data already saved, using existing files.")
                # 기존 timestamp도 함께 반환
                existing_timestamp = getattr(st.session_state, 'saved_timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
                return st.session_state.saved_files + (existing_timestamp,)
        
        # 필요한 폴더 생성
        for folder in FOLDERS.values():
            os.makedirs(folder, exist_ok=True)
        
        # 고유한 타임스탬프 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 세션 데이터 구성
        session_data = build_session_data(timestamp)
        
        # CSV 파일 저장
        csv_filename = save_to_csv(session_data, timestamp)
        
        # Excel 변환 제거 - None 반환
        excel_filename = None
        
        # 음성 파일들 저장
        audio_folder, saved_files = save_audio_files(timestamp)
        
        # 백업 ZIP 생성 (participant_info.txt 포함)
        zip_filename = create_comprehensive_backup_zip(st.session_state.session_id, timestamp)
        
        return csv_filename, excel_filename, audio_folder, saved_files, zip_filename, timestamp
    
    except Exception as e:
        st.error(f"❌ Error saving session data: {str(e)}")
        return None, None, None, [], None, None


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
        'original_nickname': getattr(st.session_state, 'original_nickname', ''),  # 닉네임 추가
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # === 배경 정보 ===
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
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # === 저장 타이밍 정보 추가 ===
        'saved_at_step': 'second_recording_complete',  # 언제 저장되었는지 기록
        'save_trigger': 'auto_after_second_recording'  # 저장 트리거 기록
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
    CSV를 Excel로 변환 - 기능 제거 (용량 절약)
    
    Args:
        csv_filename: CSV 파일 경로
        
    Returns:
        None: Excel 변환 기능 제거됨
    """
    # Excel 변환 기능 제거 - pandas/openpyxl 의존성 제거
    # 연구자는 CSV 파일을 Excel에서 직접 열어서 사용
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


def create_participant_info_file(session_id, timestamp):
    """
    참여자 정보 파일 생성 (ZIP에 포함될 텍스트 파일)
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        str: 생성된 파일 경로
    """
    try:
        info_filename = os.path.join(FOLDERS["data"], f"{session_id}_participant_info.txt")
        
        # 참여자 정보 수집
        original_nickname = getattr(st.session_state, 'original_nickname', 'Unknown')
        session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
        learning_duration = getattr(st.session_state, 'learning_duration', 'Not specified')
        speaking_confidence = getattr(st.session_state, 'speaking_confidence', 'Not specified')
        
        # 정보 파일 내용 생성
        info_content = f"""=== PARTICIPANT INFORMATION ===
Anonymous ID: {session_id}
Original Nickname: {original_nickname}
Session: {session_label} (Session {CURRENT_SESSION})
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Save Trigger: Auto-save after second recording completion

=== BACKGROUND INFORMATION ===
Learning Duration: {learning_duration}
Speaking Confidence: {speaking_confidence}

=== EXPERIMENT DETAILS ===
Question: {EXPERIMENT_QUESTION}
First Recording Duration: {getattr(st.session_state, 'audio_duration_1', 0):.1f} seconds
Second Recording Duration: {getattr(st.session_state, 'audio_duration_2', 0):.1f} seconds
Interview Readiness Score: {st.session_state.feedback.get('interview_readiness_score', 'N/A')}/10

=== CONSENT INFORMATION ===
Consent Given: {getattr(st.session_state, 'consent_given', False)}
Consent Timestamp: {getattr(st.session_state, 'consent_timestamp', 'N/A')}
GDPR Compliant: {getattr(st.session_state, 'gdpr_compliant', False)}
Zoom Interview Consent: {getattr(st.session_state, 'consent_zoom_interview', False)}

=== DATA MANAGEMENT ===
Data Retention Until: {(datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')}
Storage Method: GCS ZIP Archive (Auto-save after 2nd recording)
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== FOR RESEARCHER ===
This file contains the link between the anonymous ID and the original nickname.
Data was automatically saved after second recording completion.
Contact: pen0226@gmail.com for any data requests or questions.
"""
        
        # 파일 저장
        with open(info_filename, 'w', encoding='utf-8') as f:
            f.write(info_content)
        
        return info_filename
    
    except Exception as e:
        print(f"Error creating participant info file: {e}")
        return None


def create_comprehensive_backup_zip(session_id, timestamp):
    """
    모든 세션 데이터를 포함한 완전한 백업 ZIP 생성 (Excel 파일 제외)
    
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
            f"{session_id}_{timestamp}.zip"
        )
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 🎯 참여자 정보 파일 생성 및 추가
            participant_info_file = create_participant_info_file(session_id, timestamp)
            if participant_info_file and os.path.exists(participant_info_file):
                zipf.write(participant_info_file, "participant_info.txt")
            
            # CSV 파일 추가
            csv_file = os.path.join(FOLDERS["data"], f"korean_session{session_num}_{session_id}_{timestamp}.csv")
            if os.path.exists(csv_file):
                zipf.write(csv_file, f"session_data_{timestamp}.csv")
            
            # Excel 파일 추가 제거 (기능 제거됨)
            # excel_file = csv_file.replace('.csv', '.xlsx')
            # if os.path.exists(excel_file):
            #     zipf.write(excel_file, f"session_data_{timestamp}.xlsx")
            
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
            
            # 📝 ZIP 내용 요약 파일 추가 (Excel 제거 반영)
            readme_content = f"""=== ZIP CONTENTS SUMMARY ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Participant: {session_id} (Session {session_num})
Save Trigger: Auto-save after second recording completion

Files included:
- participant_info.txt: Participant details and nickname mapping
- session_data_{timestamp}.csv: Complete session data in CSV format
- consent_form_{session_id}.pdf: Signed consent form
- audio/: All recorded audio files (student + model pronunciations)

NOTE: Excel file generation has been removed for faster deployment.
The CSV file can be opened directly in Excel for analysis.

IMPORTANT: Data was automatically saved after second recording completion.
This ensures no data loss even if survey is not completed.

Contact researcher: pen0226@gmail.com
"""
            
            readme_path = os.path.join(FOLDERS["data"], f"{session_id}_readme.txt")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            zipf.write(readme_path, "README.txt")
        
        # 임시 파일들 정리
        temp_files = [participant_info_file, readme_path]
        for temp_file in temp_files:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        return zip_filename
    except Exception as e:
        st.error(f"❌ Error creating comprehensive backup ZIP: {e}")
        return None


# === Google Cloud Storage 함수들 (ZIP 전용) ===

def get_gcs_client():
    """
    GCS 클라이언트 초기화
    
    Returns:
        tuple: (client, bucket, status_message)
    """
    try:
        from google.cloud import storage
        import json
        
        if not GCS_ENABLED:
            return None, None, "GCS upload is disabled in configuration"
        
        if not GCS_SERVICE_ACCOUNT:
            return None, None, "GCS service account not configured"
        
        # 서비스 계정 정보를 딕셔너리로 변환
        if isinstance(GCS_SERVICE_ACCOUNT, dict):
            credentials_dict = dict(GCS_SERVICE_ACCOUNT)
        else:
            credentials_dict = json.loads(GCS_SERVICE_ACCOUNT)
        
        # GCS 클라이언트 초기화
        client = storage.Client.from_service_account_info(credentials_dict)
        
        # 버킷 객체 생성
        bucket = client.bucket(GCS_BUCKET_NAME)
        
        return client, bucket, "Success"
        
    except ImportError as e:
        return None, None, f"Missing required libraries: {str(e)}. Run: pip install google-cloud-storage"
    except Exception as e:
        return None, None, f"GCS client initialization failed: {str(e)}"


def upload_to_gcs(local_path, blob_name):
    """
    GCS에 파일 업로드
    
    Args:
        local_path: 업로드할 로컬 파일 경로
        blob_name: GCS에서 사용할 파일명 (경로 포함)
        
    Returns:
        tuple: (blob_url, status_message)
    """
    try:
        client, bucket, status = get_gcs_client()
        if not client:
            return None, f"GCS client error: {status}"
        
        # 파일 존재 확인
        if not os.path.exists(local_path):
            return None, f"File not found: {local_path}"
        
        # 블롭 생성 및 업로드
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        
        # 공개 URL 생성 (필요한 경우)
        blob_url = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        
        return blob_url, f"Successfully uploaded: {blob_name}"
        
    except Exception as e:
        return None, f"Upload failed: {str(e)}"


def auto_backup_to_gcs(csv_filename, excel_filename, zip_filename, session_id, timestamp):
    """
    ZIP 파일만 GCS에 자동 백업 + nickname_mapping.csv 백업
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로 (None - 기능 제거됨)
        zip_filename: ZIP 파일 경로 (메인 업로드)
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        tuple: (uploaded_files, errors)
    """
    uploaded_files = []
    errors = []
    
    if not GCS_ENABLED:
        errors.append("GCS upload is disabled in configuration")
        return uploaded_files, errors
    
    # 세션 번호와 간단한 폴더 구조 설정
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    session_folder = GCS_SIMPLE_STRUCTURE.get(session_num, GCS_SIMPLE_STRUCTURE[1])
    
    # 🎯 ZIP 파일만 업로드
    if zip_filename and os.path.exists(zip_filename):
        try:
            # 간단한 블롭 이름: session1/Student01_20250117_123456.zip
            blob_name = f"{session_folder}{session_id}_{timestamp}.zip"
            
            blob_url, result_msg = upload_to_gcs(zip_filename, blob_name)
            
            if blob_url:
                uploaded_files.append(blob_name)
                print(f"✅ ZIP uploaded: {blob_name}")
            else:
                errors.append(f"ZIP upload failed: {result_msg}")
                
        except Exception as e:
            errors.append(f"ZIP upload error: {str(e)}")
    else:
        errors.append("ZIP file not found for upload")
    
    # 🎯 nickname_mapping.csv GCS 백업 (전체 매핑 테이블)
    mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
    if os.path.exists(mapping_file):
        try:
            # 최상위 레벨에 매핑 파일 저장
            mapping_blob_name = "nickname_mapping.csv"
            
            blob_url, result_msg = upload_to_gcs(mapping_file, mapping_blob_name)
            
            if blob_url:
                uploaded_files.append(mapping_blob_name)
                print(f"✅ Mapping file updated: {mapping_blob_name}")
            else:
                errors.append(f"Mapping file upload failed: {result_msg}")
                
        except Exception as e:
            errors.append(f"Mapping file upload error: {str(e)}")
    
    return uploaded_files, errors


def test_gcs_connection():
    """
    GCS 연결 테스트
    
    Returns:
        tuple: (success, message)
    """
    try:
        client, bucket, status = get_gcs_client()
        if not client:
            return False, f"GCS connection failed: {status}"
        
        # 버킷 존재 확인
        if bucket.exists():
            return True, f"✅ Connected successfully to bucket: {GCS_BUCKET_NAME}"
        else:
            return False, f"❌ Bucket not found: {GCS_BUCKET_NAME}"
        
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"


def log_upload_status(session_id, timestamp, uploaded_files, errors, email_sent=False):
    """
    GCS 업로드 결과를 로그 파일에 기록
    
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
        original_nickname = getattr(st.session_state, 'original_nickname', 'Unknown')
        
        # 업로드 상태 결정
        upload_status = "SUCCESS" if uploaded_files and not errors else "PARTIAL" if uploaded_files else "FAILED"
        
        # 로그 엔트리 생성 (ZIP 전용 방식 + 저장 타이밍 정보 표시)
        log_entry = f"""
[{datetime.now().strftime(LOG_FORMAT['timestamp_format'])}] SESSION: {session_label} - {session_id}_{timestamp}
Nickname: {original_nickname}
Status: {upload_status}
Save Trigger: Auto-save after second recording completion
GCS Enabled: {GCS_ENABLED} (Service Account method - ZIP only)
Bucket: {GCS_BUCKET_NAME}
Files uploaded: {len(uploaded_files)} ({', '.join(uploaded_files) if uploaded_files else 'None'})
Errors: {len(errors)} ({'; '.join(errors) if errors else 'None'})
Email notification: {'Sent' if email_sent else 'Not sent/Failed'}
Data Safety: ✅ Secured before survey step
Excel conversion: ❌ Removed for faster deployment (CSV only)
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
    연구자용 다운로드 버튼들 표시 (Excel 제거 버전)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로 (None - 기능 제거됨)
        zip_filename: ZIP 파일 경로
    """
    if GCS_ENABLED:
        st.info("📤 ZIP file should be automatically uploaded to Google Cloud Storage. Use these downloads as backup only.")
    else:
        st.warning("⚠️ GCS upload is disabled. Use these download buttons to save your data.")
    
    # Excel 제거로 2개 컬럼만 사용
    col1, col2 = st.columns(2)
    
    # 세션 정보를 다운로드 파일명에 포함
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        # 📦 ZIP 완전 백업 다운로드 (메인)
        if zip_filename and os.path.exists(zip_filename):
            try:
                with open(zip_filename, 'rb') as f:
                    zip_data = f.read()
                st.download_button(
                    label="📦 Complete Backup ZIP",
                    data=zip_data,
                    file_name=f"{st.session_state.session_id}_{timestamp_str}.zip",
                    mime='application/zip',
                    use_container_width=True
                )
            except:
                st.info("ZIP unavailable")
        else:
            st.info("ZIP unavailable")
    
    with col2:
        # CSV 다운로드
        if csv_filename and os.path.exists(csv_filename):
            try:
                with open(csv_filename, 'r', encoding='utf-8') as f:
                    csv_data = f.read()
                st.download_button(
                    label="📄 CSV Data (Open in Excel)",
                    data=csv_data,
                    file_name=f"session{session_num}_{st.session_state.session_id}_{timestamp_str}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
            except:
                st.error("CSV download failed")
        else:
            st.info("CSV unavailable")
    
    # Excel 제거 안내
    st.caption("ℹ️ Excel file generation has been removed for faster deployment. The CSV file can be opened directly in Excel.")


def display_session_details():
    """
    연구자용 세션 상세 정보 표시 (닉네임 정보 포함 + GCS 상태)
    """
    st.markdown("**📋 Session Details:**")
    display_name = getattr(st.session_state, 'original_nickname', st.session_state.session_id)
    session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
    st.write(f"**Participant:** {display_name} (ID: {st.session_state.session_id})")
    st.write(f"**Session:** {session_label}")
    st.write(f"**Question:** {EXPERIMENT_QUESTION}")
    st.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"**Data Saved:** After second recording completion")
    
    # === 배경 정보 표시 ===
    learning_duration = getattr(st.session_state, 'learning_duration', '')
    speaking_confidence = getattr(st.session_state, 'speaking_confidence', '')
    if learning_duration:
        st.write(f"**Learning Duration:** {learning_duration}")
    if speaking_confidence:
        st.write(f"**Speaking Confidence:** {speaking_confidence}")
    
    # === GCS 연동 상태 표시 (ZIP 전용) ===
    st.markdown("**☁️ Google Cloud Storage Status:**")
    if GCS_ENABLED:
        st.success("✅ GCS upload is enabled (Service Account method - ZIP only)")
        if GCS_BUCKET_NAME:
            st.write(f"Bucket: {GCS_BUCKET_NAME}")
            st.write(f"Storage method: ZIP archives + nickname mapping")
            st.write(f"Save timing: Auto-save after 2nd recording")
        else:
            st.warning("⚠️ No bucket specified")
        
        # 연결 테스트
        success, message = test_gcs_connection()
        if success:
            st.write("🔗 Connection: ✅ Active")
        else:
            st.write(f"🔗 Connection: ❌ {message}")
    else:
        st.warning("❌ GCS upload is disabled")


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
        
        # 저장 상태 표시
        if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
            st.write("💾 **Data Status:** ✅ Safely saved")
        else:
            st.write("💾 **Data Status:** ⚠️ Not yet saved")


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


def retry_gcs_upload():
    """
    GCS 업로드 재시도 (선택적 기능)
    
    Returns:
        tuple: (success, message)
    """
    if not hasattr(st.session_state, 'saved_files') or not st.session_state.saved_files[4]:
        return False, "No local files to upload"
    
    try:
        zip_filename = st.session_state.saved_files[4]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        uploaded_files, errors = auto_backup_to_gcs(
            None, None, zip_filename,
            st.session_state.session_id,
            timestamp
        )
        
        if uploaded_files and not errors:
            return True, "Upload successful"
        else:
            return False, f"Upload failed: {'; '.join(errors)}"
            
    except Exception as e:
        return False, f"Retry failed: {str(e)}"