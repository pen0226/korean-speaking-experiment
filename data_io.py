"""
data_io.py
실험 데이터 저장, 백업, 업로드 및 로그 관리 모듈 (단순화됨)
"""

import os
import csv
import json
import zipfile
import pandas as pd
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
    세션 데이터를 CSV로 저장 (단순화됨)
    
    Returns:
        tuple: (csv_filename, None, audio_folder, saved_files, zip_filename, timestamp)
    """
    try:
        # 중복 저장 방지
        if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
            if hasattr(st.session_state, 'saved_files'):
                st.info("ℹ️ Data already saved, using existing files.")
                existing_timestamp = getattr(st.session_state, 'saved_timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
                return st.session_state.saved_files + (existing_timestamp,)
        
        # 필요한 폴더 생성
        for folder in FOLDERS.values():
            os.makedirs(folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_data = build_session_data(timestamp)
        csv_filename = save_to_csv(session_data, timestamp)
        
        audio_folder, saved_files = save_audio_files(timestamp)
        zip_filename = create_comprehensive_backup_zip(st.session_state.session_id, timestamp)
        
        return csv_filename, None, audio_folder, saved_files, zip_filename, timestamp
    
    except Exception as e:
        st.error(f"❌ Error saving session data: {str(e)}")
        return None, None, None, [], None, None


def build_session_data(timestamp):
    """
    세션 데이터 딕셔너리 구성 (자기효능감 필드 추가)
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        dict: 완성된 세션 데이터
    """
    research_scores = getattr(st.session_state, 'research_scores', {})
    
    # 기본값 설정
    default_research_scores = {
        'accuracy_score': 0.0,
        'fluency_score': 0.0,
        'error_rate': 0.0,
        'word_count': 0,
        'duration_s': 0.0,
        'error_count': 0
    }
    
    for key, default_value in default_research_scores.items():
        if key not in research_scores:
            research_scores[key] = default_value

    session_data = {
        'session_id': st.session_state.session_id,
        'session_number': getattr(st.session_state, 'session_number', CURRENT_SESSION),
        'session_label': getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1")),
        'original_nickname': getattr(st.session_state, 'original_nickname', ''),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # 배경 정보
        'learning_duration': getattr(st.session_state, 'learning_duration', ''),
        'speaking_confidence': getattr(st.session_state, 'speaking_confidence', ''),
        
        # 자기효능감 점수 6개 추가
        'self_efficacy_1': getattr(st.session_state, 'self_efficacy_1', ''),
        'self_efficacy_2': getattr(st.session_state, 'self_efficacy_2', ''),
        'self_efficacy_3': getattr(st.session_state, 'self_efficacy_3', ''),
        'self_efficacy_4': getattr(st.session_state, 'self_efficacy_4', ''),
        'self_efficacy_5': getattr(st.session_state, 'self_efficacy_5', ''),
        'self_efficacy_6': getattr(st.session_state, 'self_efficacy_6', ''),
        
        # 강화된 동의 추적 (HTML 파일로 수정)
        'consent_given': getattr(st.session_state, 'consent_given', False),
        'consent_timestamp': getattr(st.session_state, 'consent_timestamp', ''),
        'consent_participation': getattr(st.session_state, 'consent_participation', False),
        'consent_audio_ai': getattr(st.session_state, 'consent_audio_ai', False),
        'consent_data_storage': getattr(st.session_state, 'consent_data_storage', False),
        'consent_privacy_rights': getattr(st.session_state, 'consent_privacy_rights', False),
        'consent_final_confirmation': getattr(st.session_state, 'consent_final_confirmation', False),
        'consent_zoom_interview': getattr(st.session_state, 'consent_zoom_interview', False),
        'gdpr_compliant': getattr(st.session_state, 'gdpr_compliant', False),
        'consent_file_generated': getattr(st.session_state, 'consent_file', '') != '',
        'consent_file_filename': getattr(st.session_state, 'consent_file', ''),
        'consent_file_type': 'html',
        
        # 실험 데이터
        'question': EXPERIMENT_QUESTION,
        'transcription_1': st.session_state.transcription_1,
        'transcription_2': st.session_state.transcription_2,
        'gpt_feedback_json': json.dumps(st.session_state.feedback, ensure_ascii=False),
        
        # 연구용 점수 필드
        'research_accuracy_score': research_scores.get('accuracy_score', 0.0),
        'research_fluency_score': research_scores.get('fluency_score', 0.0),
        'research_error_rate': research_scores.get('error_rate', 0.0),
        'research_word_count': research_scores.get('word_count', 0),
        'research_duration_s': research_scores.get('duration_s', 0.0),
        'research_error_count': research_scores.get('error_count', 0),
        'research_scores_json': json.dumps(research_scores, ensure_ascii=False),
        
        # 데이터 품질 분석 필드
        'audio_duration_1': getattr(st.session_state, 'audio_duration_1', 0.0),
        'audio_duration_2': getattr(st.session_state, 'audio_duration_2', 0.0),
        'audio_quality_check_1': get_audio_quality_label(getattr(st.session_state, 'audio_duration_1', 0)),
        'audio_quality_check_2': get_audio_quality_label(getattr(st.session_state, 'audio_duration_2', 0)),
        
        # 개선도 평가 데이터
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
        
        # 학생용 피드백 필드들
        'suggested_model_sentence': st.session_state.feedback.get('suggested_model_sentence', ''),
        'suggested_model_sentence_english': st.session_state.feedback.get('suggested_model_sentence_english', ''),
        'fluency_comment': st.session_state.feedback.get('fluency_comment', ''),
        'interview_readiness_score': st.session_state.feedback.get('interview_readiness_score', ''),
        'interview_readiness_reason': st.session_state.feedback.get('interview_readiness_reason', ''),
        'grammar_expression_tip': st.session_state.feedback.get('grammar_expression_tip', ''),
        
        # STT 루브릭 기반 피드백 분석
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
        'dual_evaluation_used': st.session_state.gpt_debug_info.get('dual_evaluation', False),
        
        # 오디오 파일 정보
        'audio_folder': f"{FOLDERS['audio_recordings']}/{getattr(st.session_state, 'session_number', CURRENT_SESSION)}_{st.session_state.session_id}_{timestamp}",
        
        # 데이터 관리 정보
        'data_retention_until': (datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d'),
        'deletion_requested': False,
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # 저장 타이밍 정보
        'saved_at_step': 'second_recording_complete',
        'save_trigger': 'auto_after_second_recording'
    }
    
    return session_data


def get_audio_quality_label(duration):
    """
    음성 길이에 따른 품질 라벨 반환 (1-2분 목표 기준)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        str: 품질 라벨
    """
    if duration >= 90:  # 1.5분 (중간값)
        return 'excellent'
    elif duration >= 75:  # 1분 15초
        return 'good'
    elif duration >= 60:  # 1분
        return 'fair'
    else:
        return 'very_short'


def calculate_self_efficacy_average():
    """
    자기효능감 평균 계산
    
    Returns:
        float: 자기효능감 평균 (1-5점)
    """
    efficacy_scores = []
    for i in range(1, 7):
        score = getattr(st.session_state, f'self_efficacy_{i}', 0)
        if score and isinstance(score, (int, float)) and 1 <= score <= 5:
            efficacy_scores.append(score)
    
    return round(sum(efficacy_scores) / len(efficacy_scores), 2) if efficacy_scores else 0


def save_to_csv(session_data, timestamp):
    """
    세션 데이터를 CSV로 저장
    
    Args:
        session_data: 세션 데이터 딕셔너리
        timestamp: 타임스탬프
        
    Returns:
        str: CSV 파일 경로
    """
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


def save_audio_files(timestamp):
    """
    음성 파일들을 저장
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        tuple: (folder_path, saved_files_list)
    """
    try:
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
    참여자 정보 파일 생성 (자기효능감 포함)
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        str: 생성된 파일 경로
    """
    try:
        info_filename = os.path.join(FOLDERS["data"], f"{session_id}_participant_info.txt")
        
        original_nickname = getattr(st.session_state, 'original_nickname', 'Unknown')
        session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
        learning_duration = getattr(st.session_state, 'learning_duration', 'Not specified')
        speaking_confidence = getattr(st.session_state, 'speaking_confidence', 'Not specified')
        
        # 자기효능감 점수 수집 (6개)
        efficacy_scores = []
        for i in range(1, 7):
            score = getattr(st.session_state, f'self_efficacy_{i}', 'N/A')
            efficacy_scores.append(f"Item {i}: {score}/5")
        
        efficacy_avg = calculate_self_efficacy_average()
        
        research_scores = getattr(st.session_state, 'research_scores', {})
        accuracy_score = research_scores.get('accuracy_score', 'N/A')
        fluency_score = research_scores.get('fluency_score', 'N/A')
        error_rate = research_scores.get('error_rate', 'N/A')
        word_count = research_scores.get('word_count', 'N/A')
        
        info_content = f"""=== PARTICIPANT INFORMATION ===
Anonymous ID: {session_id}
Original Nickname: {original_nickname}
Session: {session_label} (Session {CURRENT_SESSION})
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Save Trigger: Auto-save after second recording completion

=== BACKGROUND INFORMATION ===
Learning Duration: {learning_duration}
Speaking Confidence: {speaking_confidence}

=== SELF-EFFICACY SCORES (1-5 scale) ===
{chr(10).join(efficacy_scores)}
Average Self-Efficacy: {efficacy_avg}/5.0

=== EXPERIMENT DETAILS ===
Question: {EXPERIMENT_QUESTION}
First Recording Duration: {getattr(st.session_state, 'audio_duration_1', 0):.1f} seconds
Second Recording Duration: {getattr(st.session_state, 'audio_duration_2', 0):.1f} seconds
Student UI Score: {st.session_state.feedback.get('interview_readiness_score', 'N/A')}/10

=== RESEARCH SCORES ===
Accuracy Score: {accuracy_score}/10 (Error rate: {error_rate}%)
Fluency Score: {fluency_score}/10 (Word count: {word_count})
Dual Evaluation System: {getattr(st.session_state, 'gpt_debug_info', {}).get('dual_evaluation', False)}

=== CONSENT INFORMATION ===
Consent Given: {getattr(st.session_state, 'consent_given', False)}
Consent Timestamp: {getattr(st.session_state, 'consent_timestamp', 'N/A')}
GDPR Compliant: {getattr(st.session_state, 'gdpr_compliant', False)}
Zoom Interview Consent: {getattr(st.session_state, 'consent_zoom_interview', False)}
Consent File Type: HTML (Korean language support)

=== DATA MANAGEMENT ===
Data Retention Until: {(datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')}
Storage Method: GCS ZIP Archive (Auto-save after 2nd recording)
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== FOR RESEARCHER ===
This file contains the link between the anonymous ID and the original nickname.
Data was automatically saved after second recording completion.
Self-efficacy scores (1-5 scale) collected before experiment.
Consent form is stored as HTML file for Korean language compatibility.

Contact: pen0226@gmail.com for any data requests or questions.
"""
        
        with open(info_filename, 'w', encoding='utf-8') as f:
            f.write(info_content)
        
        return info_filename
    
    except Exception as e:
        return None


def create_comprehensive_backup_zip(session_id, timestamp):
    """
    모든 세션 데이터를 포함한 완전한 백업 ZIP 생성 (단순화됨)
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        
    Returns:
        str: ZIP 파일 경로 또는 None
    """
    try:
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        zip_filename = os.path.join(
            FOLDERS["data"], 
            f"{session_id}_{timestamp}.zip"
        )
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 참여자 정보 파일 생성 및 추가
            participant_info_file = create_participant_info_file(session_id, timestamp)
            if participant_info_file and os.path.exists(participant_info_file):
                zipf.write(participant_info_file, "participant_info.txt")
            
            # CSV 파일 추가
            csv_file = os.path.join(FOLDERS["data"], f"korean_session{session_num}_{session_id}_{timestamp}.csv")
            if os.path.exists(csv_file):
                zipf.write(csv_file, f"session_data_{timestamp}.csv")
            
            # HTML 동의서 파일 추가
            consent_html = os.path.join(FOLDERS["data"], f"{session_id}_consent.html")
            if os.path.exists(consent_html):
                zipf.write(consent_html, f"consent_form_{session_id}.html")
                print(f"✅ Consent HTML file included: {session_id}_consent.html")
            else:
                print(f"⚠️ Consent HTML file not found: {session_id}_consent.html")
            
            # 음성 파일들 추가
            audio_folder = os.path.join(FOLDERS["audio_recordings"], f"session{session_num}_{session_id}_{timestamp}")
            if os.path.exists(audio_folder):
                for file in os.listdir(audio_folder):
                    file_path = os.path.join(audio_folder, file)
                    zipf.write(file_path, f"audio/{file}")
            
            # ZIP 내용 요약 파일 추가
            research_scores = getattr(st.session_state, 'research_scores', {})
            efficacy_avg = calculate_self_efficacy_average()
            
            readme_content = f"""=== ZIP CONTENTS SUMMARY ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Participant: {session_id} (Session {session_num})
Save Trigger: Auto-save after second recording completion

Files included:
- participant_info.txt: Participant details + Research scores + Self-efficacy scores
- session_data_{timestamp}.csv: Complete session data with dual evaluation + self-efficacy data
- consent_form_{session_id}.html: Signed consent form (HTML format for Korean support)
- audio/: All recorded audio files (student + model pronunciations)

SELF-EFFICACY DATA:
- 6 items measured on 1-5 scale
- Average self-efficacy score: {efficacy_avg}/5.0
- Individual scores stored in CSV under self_efficacy_1 through self_efficacy_6

CONSENT FORM FORMAT:
- HTML format for perfect Korean language support
- Can be saved as PDF using browser print function (Ctrl+P)
- Avoids character encoding issues that occurred with direct PDF generation

RESEARCH WORKFLOW:
1. Use CSV data for basic analysis
2. Raw audio files available for manual grading
3. All raw data preserved for transparency

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
        
        print(f"✅ Comprehensive backup ZIP created: {zip_filename}")
        return zip_filename
        
    except Exception as e:
        st.error(f"❌ Error creating comprehensive backup ZIP: {e}")
        return None


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
        
        try:
            if isinstance(GCS_SERVICE_ACCOUNT, dict):
                credentials_dict = dict(GCS_SERVICE_ACCOUNT)
                print(f"Using TOML format service account (Project: {credentials_dict.get('project_id', 'Unknown')})")
            elif isinstance(GCS_SERVICE_ACCOUNT, str):
                credentials_dict = json.loads(GCS_SERVICE_ACCOUNT)
                print(f"Using JSON format service account (Project: {credentials_dict.get('project_id', 'Unknown')})")
            else:
                return None, None, f"Unexpected service account type: {type(GCS_SERVICE_ACCOUNT)}"
                
        except json.JSONDecodeError:
            return None, None, "Invalid JSON format in service account"
        except Exception as parse_error:
            return None, None, f"Service account parsing error: {str(parse_error)}"
        
        client = storage.Client.from_service_account_info(credentials_dict)
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
        blob_name: GCS에서 사용할 파일명
        
    Returns:
        tuple: (blob_url, status_message)
    """
    try:
        client, bucket, status = get_gcs_client()
        if not client:
            return None, f"GCS client error: {status}"
        
        if not os.path.exists(local_path):
            return None, f"File not found: {local_path}"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        
        blob_url = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        print(f"ZIP uploaded: {blob_name}")
        
        return blob_url, f"Successfully uploaded: {blob_name}"
        
    except Exception as e:
        return None, f"Upload failed: {str(e)}"


def auto_backup_to_gcs(csv_filename, excel_filename, zip_filename, session_id, timestamp):
    """
    ZIP 파일만 GCS에 자동 백업 + nickname_mapping.csv 백업
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로 (사용안함)
        zip_filename: ZIP 파일 경로
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
    
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    session_folder = GCS_SIMPLE_STRUCTURE.get(session_num, GCS_SIMPLE_STRUCTURE[1])
    
    # ZIP 파일 업로드
    if zip_filename and os.path.exists(zip_filename):
        try:
            blob_name = f"{session_folder}{session_id}_{timestamp}.zip"
            blob_url, result_msg = upload_to_gcs(zip_filename, blob_name)
            
            if blob_url:
                uploaded_files.append(blob_name)
                print(f"✅ Session {session_num} ZIP uploaded: {blob_name}")
            else:
                errors.append(f"ZIP upload failed: {result_msg}")
                
        except Exception as e:
            errors.append(f"ZIP upload error: {str(e)}")
    else:
        errors.append("ZIP file not found for upload")
    
    # nickname_mapping.csv 백업
    mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
    if os.path.exists(mapping_file):
        try:
            mapping_blob_name = "nickname_mapping.csv"
            blob_url, result_msg = upload_to_gcs(mapping_file, mapping_blob_name)
            
            if blob_url:
                uploaded_files.append(mapping_blob_name)
            else:
                errors.append(f"Mapping file upload failed: {result_msg}")
                
        except Exception as e:
            errors.append(f"Mapping file upload error: {str(e)}")
    
    return uploaded_files, errors


def test_gcs_connection():
    """
    GCS 연결 상태 테스트
    
    Returns:
        tuple: (success, message)
    """
    try:
        client, bucket, status = get_gcs_client()
        if not client:
            return False, f"GCS connection failed: {status}"
        
        if bucket.exists():
            project_id = "Unknown"
            if isinstance(GCS_SERVICE_ACCOUNT, dict):
                project_id = GCS_SERVICE_ACCOUNT.get('project_id', 'Unknown')
                format_type = "TOML format"
            else:
                import json
                try:
                    service_info = json.loads(GCS_SERVICE_ACCOUNT)
                    project_id = service_info.get('project_id', 'Unknown')
                    format_type = "JSON format"
                except:
                    format_type = "Unknown format"
            
            return True, f"Connected successfully to bucket: {GCS_BUCKET_NAME} (Project: {project_id} - {format_type})"
        else:
            return False, f"Bucket not found: {GCS_BUCKET_NAME}"
        
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
        os.makedirs(FOLDERS["logs"], exist_ok=True)
        
        log_date = datetime.now().strftime('%Y%m%d')
        log_filename = os.path.join(
            FOLDERS["logs"], 
            f"upload_log_{log_date}.txt"
        )
        
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
        original_nickname = getattr(st.session_state, 'original_nickname', 'Unknown')
        
        research_scores = getattr(st.session_state, 'research_scores', {})
        accuracy_score = research_scores.get('accuracy_score', 'N/A')
        fluency_score = research_scores.get('fluency_score', 'N/A')
        dual_eval_used = getattr(st.session_state, 'gpt_debug_info', {}).get('dual_evaluation', False)
        
        # 자기효능감 평균 계산 (6개)
        efficacy_avg = calculate_self_efficacy_average()
        
        upload_status = "SUCCESS" if uploaded_files and not errors else "PARTIAL" if uploaded_files else "FAILED"
        
        log_entry = f"""
[{datetime.now().strftime(LOG_FORMAT['timestamp_format'])}] SESSION: {session_label} - {session_id}_{timestamp}
Nickname: {original_nickname}
Status: {upload_status}
Save Trigger: Auto-save after second recording completion
Dual Evaluation: {dual_eval_used} (Research scores: Accuracy={accuracy_score}, Fluency={fluency_score})
Self-Efficacy: Average {efficacy_avg}/5.0 (6 items collected)
GCS Enabled: {GCS_ENABLED} (Service Account method - ZIP backup only)
Bucket: {GCS_BUCKET_NAME}
Files uploaded: {len(uploaded_files)} ({', '.join(uploaded_files) if uploaded_files else 'None'})
Errors: {len(errors)} ({'; '.join(errors) if errors else 'None'})
Email notification: {'Sent' if email_sent else 'Not sent/Failed'}
Data Safety: Secured before survey step
Consent Format: HTML (Korean language support)
{'='*80}
"""
        
        with open(log_filename, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
        
        return True
    except Exception:
        return False


def display_download_buttons(csv_filename, excel_filename, zip_filename):
    """
    연구자용 다운로드 버튼들 표시 (단순화됨)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로 (사용안함)
        zip_filename: ZIP 파일 경로
    """
    if GCS_ENABLED:
        st.info(f"📤 Session {CURRENT_SESSION} ZIP file should be automatically uploaded to Google Cloud Storage. Use these downloads as backup only.")
    else:
        st.warning("⚠️ GCS upload is disabled. Use these download buttons to save your data.")
    
    col1, col2, col3 = st.columns(3)
    
    session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        # ZIP 완전 백업 다운로드
        if zip_filename and os.path.exists(zip_filename):
            try:
                with open(zip_filename, 'rb') as f:
                    zip_data = f.read()
                st.download_button(
                    label=f"📦 Session {session_num} Complete Backup ZIP",
                    data=zip_data,
                    file_name=f"session{session_num}_{st.session_state.session_id}_{timestamp_str}.zip",
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
    
    with col3:
        st.info("📊 Reference scores saved separately")
    
    st.caption(f"ℹ️ Session {CURRENT_SESSION} data includes self-efficacy scores and consent form. ZIP contains all files.")


def display_session_details():
    """
    연구자용 세션 상세 정보 표시
    """
    st.markdown("**📋 Session Details:**")
    display_name = getattr(st.session_state, 'original_nickname', st.session_state.session_id)
    session_label = getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1"))
    st.write(f"**Participant:** {display_name} (ID: {st.session_state.session_id})")
    st.write(f"**Session:** {session_label}")
    st.write(f"**Question:** {EXPERIMENT_QUESTION}")
    st.write(f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.write(f"**Data Saved:** After second recording completion")
    
    # 배경 정보 표시
    learning_duration = getattr(st.session_state, 'learning_duration', '')
    speaking_confidence = getattr(st.session_state, 'speaking_confidence', '')
    if learning_duration:
        st.write(f"**Learning Duration:** {learning_duration}")
    if speaking_confidence:
        st.write(f"**Speaking Confidence:** {speaking_confidence}")
    
    # 자기효능감 점수 표시 (6개)
    efficacy_avg = calculate_self_efficacy_average()
    if efficacy_avg > 0:
        st.write(f"**Self-Efficacy:** {efficacy_avg}/5.0 (6 items)")
        with st.expander("🎯 Self-Efficacy Details", expanded=False):
            for i in range(1, 7):
                score = getattr(st.session_state, f'self_efficacy_{i}', 0)
                if score:
                    st.write(f"Item {i}: {score}/5")
    
    # 연구용 점수 정보 표시
    research_scores = getattr(st.session_state, 'research_scores', {})
    if research_scores:
        st.markdown("**🔬 Research Scores:**")
        accuracy = research_scores.get('accuracy_score', 'N/A')
        fluency = research_scores.get('fluency_score', 'N/A')
        error_rate = research_scores.get('error_rate', 'N/A')
        word_count = research_scores.get('word_count', 'N/A')
        st.write(f"Accuracy Score: {accuracy}/10 (Error rate: {error_rate}%)")
        st.write(f"Fluency Score: {fluency}/10 (Word count: {word_count})")
        dual_eval = getattr(st.session_state, 'gpt_debug_info', {}).get('dual_evaluation', False)
        st.write(f"Dual Evaluation System: {'✅ Active' if dual_eval else '❌ Not used'}")
    else:
        st.write("**🔬 Research Scores:** ❌ Not calculated")
    
    # GCS 연동 상태 표시
    st.markdown("**☁️ Google Cloud Storage Status:**")
    if GCS_ENABLED:
        st.success(f"✅ GCS upload is enabled (Service Account method)")
        if GCS_BUCKET_NAME:
            st.write(f"Bucket: {GCS_BUCKET_NAME}")
            st.write(f"Storage method: ZIP archives + nickname mapping")
            st.write(f"Consent format: HTML (Korean language support)")
            st.write(f"Self-efficacy: 6 items (1-5 scale) included")
            st.write(f"Save timing: Auto-save after 2nd recording")
        else:
            st.warning("⚠️ No bucket specified")
        
        success, message = test_gcs_connection()
        if success:
            st.write("🔗 Connection: ✅ Active")
        else:
            st.write(f"🔗 Connection: ❌ {message}")
    else:
        st.warning("❌ GCS upload is disabled")


def display_data_quality_info():
    """
    데이터 품질 정보 표시
    """
    st.markdown("**📊 Data Quality:**")
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
            
            student_score = st.session_state.feedback.get('interview_readiness_score', 'N/A')
            st.write(f"Student UI Score: {student_score}/10")
        
        # 자기효능감 요약 (6개)
        efficacy_avg = calculate_self_efficacy_average()
        if efficacy_avg > 0:
            st.write(f"**🎯 Self-Efficacy:** {efficacy_avg}/5.0")
    
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
        
        if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
            st.write("💾 **Data Status:** ✅ Safely saved")
        else:
            st.write("💾 **Data Status:** ⚠️ Not yet saved")


def get_quality_description(duration):
    """
    음성 길이에 따른 품질 설명 반환 (1-2분 목표 기준)
    
    Args:
        duration: 음성 길이 (초)
        
    Returns:
        str: 품질 설명
    """
    if duration >= 90:
        return "✅ Excellent (1.5min+ target reached!)"
    elif duration >= 75:
        return "🌟 Good (1.25-1.5min, try for 1.5min+)"
    elif duration >= 60:
        return "⚠️ Fair (1-1.25min, needs improvement)"
    else:
        return "❌ Very Short (under 1min, much more needed)"