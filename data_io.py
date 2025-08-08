"""
data_io.py
실험 데이터 저장, 백업, 업로드 및 로그 관리 모듈 (TOPIK 엑셀 ZIP 포함 보장)
GCS 매핑 파일 동기화 최적화 적용
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

def extract_task_completion_check(detailed_feedback):
    """
    detailed_feedback에서 Task Completion Check 정보 추출
    
    Args:
        detailed_feedback: GPT가 생성한 detailed_feedback 텍스트
        
    Returns:
        dict: Task completion 정보
    """
    result = {
        'past_vacation_status': 'Unknown',
        'future_plans_status': 'Unknown',
        'tense_usage': 'Unknown',
        'both_topics_covered': False,
        'missing_topics': []
    }
    
    if not detailed_feedback:
        return result
    
    # Task Completion Check 섹션 찾기
    if '🚩 Task Completion Check' in detailed_feedback:
        lines = detailed_feedback.split('\n')
        for line in lines:
            line = line.strip()
            
            # Past vacation 체크
            if 'Past vacation:' in line:
                if '✅' in line:
                    if 'Covered well' in line:
                        result['past_vacation_status'] = 'Covered'
                    elif 'Partially' in line:
                        result['past_vacation_status'] = 'Partially'
                elif '❌' in line:
                    result['past_vacation_status'] = 'Missing'
                    result['missing_topics'].append('past_vacation')
            
            # Future plans 체크
            elif 'Future plans:' in line:
                if '✅' in line:
                    if 'Covered well' in line:
                        result['future_plans_status'] = 'Covered'
                    elif 'Partially' in line:
                        result['future_plans_status'] = 'Partially'
                elif '❌' in line:
                    result['future_plans_status'] = 'Missing'
                    result['missing_topics'].append('future_plans')
            
            # Tense usage 체크
            elif 'Tense usage:' in line:
                result['tense_usage'] = line.replace('⚠️', '').replace('Tense usage:', '').strip()
    
    # 두 주제 모두 다뤘는지 판단
    result['both_topics_covered'] = (
        result['past_vacation_status'] in ['Covered', 'Partially'] and
        result['future_plans_status'] in ['Covered', 'Partially']
    )
    
    return result

def save_session_data():
    """
    세션 데이터를 CSV로 저장 + 참고용 엑셀 파일 경로 반환
    
    Returns:
        tuple: (csv_filename, reference_excel_filename, audio_folder, saved_files, zip_filename, timestamp)
    """
    try:
        # 중복 저장 방지
        if hasattr(st.session_state, 'data_saved') and st.session_state.data_saved:
            if hasattr(st.session_state, 'saved_files'):
                st.info("ℹ️ Data already saved, using existing files.")
                existing_timestamp = getattr(st.session_state, 'saved_timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
                
                # 🔥 기존 저장된 파일들에 reference 엑셀 추가
                from save_reference_score import get_latest_reference_file
                reference_excel = get_latest_reference_file(existing_timestamp)
                
                # 기존 saved_files에 reference_excel 추가해서 반환
                saved_files = st.session_state.saved_files
                return saved_files[0], reference_excel, saved_files[2], saved_files[3], saved_files[4], existing_timestamp
        
        # 필요한 폴더 생성
        for folder in FOLDERS.values():
            os.makedirs(folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_data = build_session_data(timestamp)
        csv_filename = save_to_csv(session_data, timestamp)
        
        audio_folder, saved_files = save_audio_files(timestamp)
        
        # 🔥 참고용 엑셀 파일 경로 가져오기 (ZIP 생성 전에 확인)
        from save_reference_score import get_latest_reference_file
        reference_excel_filename = get_latest_reference_file(timestamp)
        
        # 🔥 엑셀 파일이 존재하는지 확인 후 ZIP 생성
        if reference_excel_filename and os.path.exists(reference_excel_filename):
            print(f"✅ Reference Excel found before ZIP creation: {reference_excel_filename}")
        else:
            print(f"⚠️ Reference Excel not found before ZIP creation: {reference_excel_filename}")
        
        zip_filename = create_comprehensive_backup_zip(st.session_state.session_id, timestamp, reference_excel_filename)
        
        return csv_filename, reference_excel_filename, audio_folder, saved_files, zip_filename, timestamp
    
    except Exception as e:
        st.error(f"❌ Error saving session data: {str(e)}")
        return None, None, None, [], None, None


def build_session_data(timestamp):
    """
    세션 데이터 딕셔너리 구성 (자기효능감 필드 + Task Completion Check 추가)
    
    ===== CSV 데이터 구조 문서화 =====
    이 함수는 실험 완료 후 저장되는 주요 CSV 파일의 모든 컬럼을 정의합니다.
    파일명 형식: korean_session{N}_{session_id}_{timestamp}.csv
    
    📋 주요 데이터 카테고리:
    1. 기본 식별 정보 (session_id, timestamp 등)
    2. 배경 정보 및 사전 측정 (학습기간, 자신감, 자기효능감 6개 항목)
    3. 실험 핵심 데이터 (질문, 1차/2차 전사, 음성 길이)
    4. AI 피드백 분석 (JSON 원본 + 주요 필드 추출)
    5. 연구용 정량 점수 (이중 평가 시스템: 정확성/유창성)
    6. 개선도 평가 (1차→2차 변화 분석)
    7. 동의서 및 윤리 정보 (GDPR 준수)
    8. 데이터 품질 및 관리 (보관기간, 품질 라벨)
    9. Task Completion Check (두 주제 커버 여부)
    
    📊 활용 목적:
    - 피드백 시스템 효과성 분석 (1차→2차 개선도)
    - 자기효능감과 학습 성과 상관관계 분석  
    - 발화 길이 최적화 (목표: 60-120초)
    - AI vs 전문가 채점 비교 연구
    - 학습자 유형별 맞춤 피드백 개발
    - Task Completion 분석 (주제 누락 패턴 연구)
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        dict: 완성된 세션 데이터 (CSV 저장용)
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
    
    # Task Completion Check 데이터 추출
    task_check_data = extract_task_completion_check(st.session_state.feedback.get('detailed_feedback', ''))

    session_data = {
        # ===== 1. 기본 식별 정보 =====
        'session_id': st.session_state.session_id,  # 실험 세션 고유번호 (익명화된 ID)
        'session_number': getattr(st.session_state, 'session_number', CURRENT_SESSION),  # 세션 차수 (1 or 2)
        'session_label': getattr(st.session_state, 'session_label', SESSION_LABELS.get(CURRENT_SESSION, "Session 1")),  # 세션 라벨
        'original_nickname': getattr(st.session_state, 'original_nickname', ''),  # 참여자가 입력한 원래 닉네임 (연구자 참조용)
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 실험 완료 시각
        
        # ===== 2. 배경 정보 및 사전 측정 =====
        'learning_duration': getattr(st.session_state, 'learning_duration', ''),  # 한국어 학습 기간 선택지
        'speaking_confidence': getattr(st.session_state, 'speaking_confidence', ''),  # 말하기 자신감 5점 척도
        
        # 자기효능감 6개 항목 (각 1-5점 리커트 척도)
        'self_efficacy_1': getattr(st.session_state, 'self_efficacy_1', ''),  # "I can use grammar accurately when speaking Korean"
        'self_efficacy_2': getattr(st.session_state, 'self_efficacy_2', ''),  # "I can use appropriate words when speaking Korean"
        'self_efficacy_3': getattr(st.session_state, 'self_efficacy_3', ''),  # "I can deliver what I want to say in Korean with confidence"
        'self_efficacy_4': getattr(st.session_state, 'self_efficacy_4', ''),  # "I can express my ideas clearly in Korean"
        'self_efficacy_5': getattr(st.session_state, 'self_efficacy_5', ''),  # "I can answer related questions well in Korean"
        'self_efficacy_6': getattr(st.session_state, 'self_efficacy_6', ''),  # "I can improve my speaking on my own through feedback"
        
        # ===== 3. 동의서 및 윤리 정보 =====
        'consent_given': getattr(st.session_state, 'consent_given', False),  # 동의서 작성 완료 여부
        'consent_timestamp': getattr(st.session_state, 'consent_timestamp', ''),  # 동의서 작성 시각
        'consent_participation': getattr(st.session_state, 'consent_participation', False),  # 연구 참여 동의
        'consent_audio_ai': getattr(st.session_state, 'consent_audio_ai', False),  # 음성 AI 분석 동의
        'consent_data_storage': getattr(st.session_state, 'consent_data_storage', False),  # 데이터 저장 동의
        'consent_privacy_rights': getattr(st.session_state, 'consent_privacy_rights', False),  # 개인정보 권리 인지
        'consent_final_confirmation': getattr(st.session_state, 'consent_final_confirmation', False),  # 최종 확인
        'consent_zoom_interview': getattr(st.session_state, 'consent_zoom_interview', False),  # Zoom 인터뷰 동의
        'gdpr_compliant': getattr(st.session_state, 'gdpr_compliant', False),  # GDPR 준수 여부
        'consent_file_generated': getattr(st.session_state, 'consent_file', '') != '',  # 동의서 파일 생성 여부
        'consent_file_filename': getattr(st.session_state, 'consent_file', ''),  # 동의서 파일명
        'consent_file_type': 'html',  # 동의서 파일 형식 (HTML: 한국어 지원)
        
        # ===== 4. 실험 핵심 데이터 =====
        'question': EXPERIMENT_QUESTION,  # 실험에서 제시된 질문 (한국어)
        'transcription_1': st.session_state.transcription_1,  # 첫 번째 녹음 STT 전사 결과
        'transcription_2': st.session_state.transcription_2,  # 두 번째 녹음 STT 전사 결과 (피드백 적용 후)
        'gpt_feedback_json': json.dumps(st.session_state.feedback, ensure_ascii=False),  # GPT가 생성한 전체 피드백 (JSON 원본)
        
        # ===== 4.5. Task Completion Check 데이터 (새로 추가) =====
        'task_check_past_vacation': task_check_data.get('past_vacation_status', 'Unknown'),  # Covered/Partially/Missing
        'task_check_future_plans': task_check_data.get('future_plans_status', 'Unknown'),  # Covered/Partially/Missing
        'task_check_tense_usage': task_check_data.get('tense_usage', 'Unknown'),  # 시제 사용 평가
        'task_check_both_topics_covered': task_check_data.get('both_topics_covered', False),  # 두 주제 모두 다뤘는지
        'task_check_json': json.dumps(task_check_data, ensure_ascii=False),  # 전체 Task Check 데이터
        
        # ===== 5. 연구용 정량 점수 (이중 평가 시스템) =====
        # 논문용 객관적 점수 (오류율, 단어수 기반 자동 계산)
        'research_accuracy_score': research_scores.get('accuracy_score', 0.0),  # 정확성 점수 (0-10점, 오류율 기반)
        'research_fluency_score': research_scores.get('fluency_score', 0.0),  # 유창성 점수 (0-10점, 단어수 기반)
        'research_error_rate': research_scores.get('error_rate', 0.0),  # 오류율 (%, 단어당 문법 오류)
        'research_word_count': research_scores.get('word_count', 0),  # 총 단어 수
        'research_duration_s': research_scores.get('duration_s', 0.0),  # 녹음 길이 (초)
        'research_error_count': research_scores.get('error_count', 0),  # 실제 문법 오류 개수
        'research_scores_json': json.dumps(research_scores, ensure_ascii=False),  # 연구용 점수 전체 (JSON)
        
        # ===== 6. 데이터 품질 분석 =====
        'audio_duration_1': getattr(st.session_state, 'audio_duration_1', 0.0),  # 첫 번째 녹음 길이 (초)
        'audio_duration_2': getattr(st.session_state, 'audio_duration_2', 0.0),  # 두 번째 녹음 길이 (초)
        'audio_quality_check_1': get_audio_quality_label(getattr(st.session_state, 'audio_duration_1', 0)),  # 첫 번째 녹음 품질 라벨
        'audio_quality_check_2': get_audio_quality_label(getattr(st.session_state, 'audio_duration_2', 0)),  # 두 번째 녹음 품질 라벨
        
        # ===== 7. 개선도 평가 데이터 =====
        'improvement_score': getattr(st.session_state, 'improvement_assessment', {}).get('improvement_score', 0),  # 1차→2차 개선도 점수 (1-10점)
        'improvement_reason': getattr(st.session_state, 'improvement_assessment', {}).get('improvement_reason', ''),  # 개선도 평가 이유
        'first_attempt_score': getattr(st.session_state, 'improvement_assessment', {}).get('first_attempt_score', 0),  # 1차 시도 평가 점수
        'second_attempt_score': getattr(st.session_state, 'improvement_assessment', {}).get('second_attempt_score', 0),  # 2차 시도 평가 점수
        'score_difference': getattr(st.session_state, 'improvement_assessment', {}).get('score_difference', 0),  # 점수 차이 (2차 - 1차)
        'feedback_application': getattr(st.session_state, 'improvement_assessment', {}).get('feedback_application', ''),  # 피드백 적용도 ("excellent/good/partial/minimal")
        'specific_improvements': json.dumps(getattr(st.session_state, 'improvement_assessment', {}).get('specific_improvements', []), ensure_ascii=False),  # 구체적 개선사항 목록
        'remaining_issues': json.dumps(getattr(st.session_state, 'improvement_assessment', {}).get('remaining_issues', []), ensure_ascii=False),  # 남은 과제 목록
        'overall_assessment': getattr(st.session_state, 'improvement_assessment', {}).get('overall_assessment', ''),  # 전체 평가 요약
        'improvement_assessment_json': json.dumps(getattr(st.session_state, 'improvement_assessment', {}), ensure_ascii=False),  # 개선도 평가 전체 (JSON)
        
        # ===== 8. 학생용 피드백 필드들 (UI 표시용) =====
        'suggested_model_sentence': st.session_state.feedback.get('suggested_model_sentence', ''),  # AI가 제안한 모범 답안 (한국어)
        'suggested_model_sentence_english': st.session_state.feedback.get('suggested_model_sentence_english', ''),  # 모범 답안 영어 번역
        'fluency_comment': st.session_state.feedback.get('fluency_comment', ''),  # 유창성 코멘트
        'interview_readiness_score': st.session_state.feedback.get('interview_readiness_score', ''),  # AI가 평가한 인터뷰 준비도 (1-10점)
        'interview_readiness_reason': st.session_state.feedback.get('interview_readiness_reason', ''),  # 인터뷰 준비도 점수 이유
        'grammar_expression_tip': st.session_state.feedback.get('grammar_expression_tip', ''),  # 고급 문법 패턴 제안
        
        # ===== 9. STT 루브릭 기반 피드백 분석 =====
        'grammar_issues_count': len(st.session_state.feedback.get('grammar_issues', [])),  # 발견된 문법 오류 개수
        'vocabulary_suggestions_count': len(st.session_state.feedback.get('vocabulary_suggestions', [])),  # 어휘 제안 개수
        'content_expansion_suggestions_count': len(st.session_state.feedback.get('content_expansion_suggestions', [])),  # 내용 확장 제안 개수
        'content_expansion_suggestions_json': json.dumps(st.session_state.feedback.get('content_expansion_suggestions', []), ensure_ascii=False),  # 내용 확장 제안 상세
        'grammar_issues_json': json.dumps(st.session_state.feedback.get('grammar_issues', []), ensure_ascii=False),  # 문법 오류 상세 분석
        'vocabulary_suggestions_json': json.dumps(st.session_state.feedback.get('vocabulary_suggestions', []), ensure_ascii=False),  # 어휘 제안 상세
        'highlight_targets_json': json.dumps(st.session_state.feedback.get('highlight_targets', {}), ensure_ascii=False),  # 하이라이트 대상 분석
        
        # ===== 10. 디버그 및 시스템 정보 =====
        'gpt_model_used': st.session_state.gpt_debug_info.get('model_used', ''),  # 사용된 GPT 모델명
        'gpt_attempts': st.session_state.gpt_debug_info.get('attempts', 0),  # GPT API 시도 횟수
        'dual_evaluation_used': st.session_state.gpt_debug_info.get('dual_evaluation', False),  # 이중 평가 시스템 사용 여부
        
        # ===== 11. 파일 관리 정보 =====
        'audio_folder': f"{FOLDERS['audio_recordings']}/{getattr(st.session_state, 'session_number', CURRENT_SESSION)}_{st.session_state.session_id}_{timestamp}",  # 음성 파일 저장 폴더
        'data_retention_until': (datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d'),  # 데이터 보관 만료일
        'deletion_requested': False,  # 삭제 요청 여부
        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 마지막 업데이트 시각
        'saved_at_step': 'second_recording_complete',  # 저장 시점 단계
        'save_trigger': 'auto_after_second_recording'  # 저장 트리거 방식
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
    참여자 정보 파일 생성 (자기효능감 + Task Completion Check 포함)
    
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
        
        # Task Completion Check 정보 추출
        task_check_data = extract_task_completion_check(st.session_state.feedback.get('detailed_feedback', ''))
        
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

=== TASK COMPLETION CHECK ===
Past Vacation Coverage: {task_check_data.get('past_vacation_status', 'Unknown')}
Future Plans Coverage: {task_check_data.get('future_plans_status', 'Unknown')}
Tense Usage: {task_check_data.get('tense_usage', 'Unknown')}
Both Topics Covered: {'Yes' if task_check_data.get('both_topics_covered') else 'No'}
Missing Topics: {', '.join(task_check_data.get('missing_topics', [])) if task_check_data.get('missing_topics') else 'None'}

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
Task Completion Check shows whether both topics (past/future) were covered.
Consent form is stored as HTML file for Korean language compatibility.
TOPIK reference scores (3 areas) stored in Excel file: reference_scores_{timestamp}.xlsx

Contact: pen0226@gmail.com for any data requests or questions.
"""
        
        with open(info_filename, 'w', encoding='utf-8') as f:
            f.write(info_content)
        
        return info_filename
    
    except Exception as e:
        return None
    
    

def create_comprehensive_backup_zip(session_id, timestamp, reference_excel_filename=None):
    """
    모든 세션 데이터를 포함한 완전한 백업 ZIP 생성 (TOPIK 엑셀 포함 보장)
    
    Args:
        session_id: 세션 ID
        timestamp: 타임스탬프
        reference_excel_filename: 참고용 엑셀 파일 경로 (명시적 전달)
        
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
                print(f"✅ CSV file included: session_data_{timestamp}.csv")
            
            # 🔥 TOPIK 참고용 엑셀 파일 추가 (확실한 경로 확인)
            excel_included = False
            
            # 방법 1: 명시적으로 전달받은 경로 사용
            if reference_excel_filename and os.path.exists(reference_excel_filename):
                zipf.write(reference_excel_filename, f"reference_scores_{timestamp}.xlsx")
                print(f"✅ Reference Excel file included (method 1): reference_scores_{timestamp}.xlsx")
                excel_included = True
            
            # 방법 2: 직접 경로 구성해서 찾기
            if not excel_included:
                reference_excel_direct = os.path.join(FOLDERS["data"], f"reference_scores_{timestamp}.xlsx")
                if os.path.exists(reference_excel_direct):
                    zipf.write(reference_excel_direct, f"reference_scores_{timestamp}.xlsx")
                    print(f"✅ Reference Excel file included (method 2): reference_scores_{timestamp}.xlsx")
                    excel_included = True
            
            # 방법 3: 패턴 매칭으로 찾기
            if not excel_included:
                import glob
                pattern = os.path.join(FOLDERS["data"], f"reference_scores_*.xlsx")
                excel_files = glob.glob(pattern)
                if excel_files:
                    # 가장 최신 파일 또는 timestamp 매칭하는 파일 사용
                    matching_files = [f for f in excel_files if timestamp in f]
                    if matching_files:
                        latest_excel = matching_files[0]
                    else:
                        latest_excel = max(excel_files, key=os.path.getctime)
                    
                    zipf.write(latest_excel, f"reference_scores_{timestamp}.xlsx")
                    print(f"✅ Reference Excel file included (method 3): reference_scores_{timestamp}.xlsx")
                    excel_included = True
            
            if not excel_included:
                print(f"⚠️ Reference Excel file NOT FOUND for inclusion in ZIP")
                print(f"   Checked paths:")
                print(f"   - {reference_excel_filename}")
                print(f"   - {os.path.join(FOLDERS['data'], f'reference_scores_{timestamp}.xlsx')}")
            
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
                print(f"✅ Audio files included from: {audio_folder}")
            
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
- reference_scores_{timestamp}.xlsx: TOPIK holistic reference scores for both attempts {'✅ INCLUDED' if excel_included else '❌ MISSING'}
- consent_form_{session_id}.html: Signed consent form (HTML format for Korean support)
- audio/: All recorded audio files (student + model pronunciations)

SELF-EFFICACY DATA:
- 6 items measured on 1-5 scale
- Average self-efficacy score: {efficacy_avg}/5.0
- Individual scores stored in CSV under self_efficacy_1 through self_efficacy_6

TOPIK REFERENCE SCORES:
- Holistic rubric scoring: Content/Task, Language Use, Delivery (STT-based)
- Each area scored 1-5 points (holistic impression-based)
- Total score: simple sum (3-15 points)

CONSENT FORM FORMAT:
- HTML format for perfect Korean language support
- Can be saved as PDF using browser print function (Ctrl+P)
- Avoids character encoding issues that occurred with direct PDF generation

RESEARCH WORKFLOW:
1. Use CSV data for basic analysis
2. Use Excel file for TOPIK reference scores (3 areas)
3. Raw audio files available for manual grading
4. All raw data preserved for transparency

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
        print(f"File uploaded: {blob_name}")
        
        return blob_url, f"Successfully uploaded: {blob_name}"
        
    except Exception as e:
        return None, f"Upload failed: {str(e)}"


def check_mapping_file_freshness():
    """
    매핑 파일의 최신 상태 확인 (consent.py에서 실시간 업로드했는지 체크)
    
    Returns:
        tuple: (needs_upload, reason)
    """
    try:
        # 현재 세션의 닉네임으로 최근 업데이트가 있었는지 확인
        original_nickname = getattr(st.session_state, 'original_nickname', '')
        if not original_nickname:
            return False, "No nickname in current session"
        
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        if not os.path.exists(mapping_file):
            return False, "No local mapping file found"
        
        # 현재 세션의 타임스탬프 확인
        current_timestamp = datetime.now()
        
        with open(mapping_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Nickname', '').strip().lower() == original_nickname.lower():
                    # 매핑 파일의 마지막 업데이트 시간 확인
                    file_timestamp_str = row.get('Timestamp', '')
                    if file_timestamp_str:
                        try:
                            file_timestamp = datetime.strptime(file_timestamp_str, '%Y-%m-%d %H:%M:%S')
                            time_diff = (current_timestamp - file_timestamp).total_seconds()
                            
                            # 5분 이내에 업데이트되었다면 최신 상태로 간주
                            if time_diff <= 300:  # 5분 = 300초
                                return False, f"Recently updated {time_diff:.0f}s ago by consent.py"
                            else:
                                return True, f"Last updated {time_diff:.0f}s ago, needs refresh"
                        except ValueError:
                            return True, "Invalid timestamp format, needs refresh"
                    break
        
        return True, "Nickname not found in mapping file, needs upload"
        
    except Exception as e:
        return True, f"Error checking freshness: {str(e)}"


def auto_backup_to_gcs(csv_filename, excel_filename, zip_filename, session_id, timestamp):
    """
    ZIP 파일만 GCS에 자동 백업 + 스마트한 nickname_mapping.csv 백업
    (consent.py에서 실시간 업로드했다면 중복 업로드 방지)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: 참고용 엑셀 파일 경로 (사용하지 않음 - ZIP에 포함됨)
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
    
    # ZIP 파일만 업로드 (엑셀은 ZIP 안에 포함됨)
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
    
    # 🔥 스마트한 nickname_mapping.csv 백업 (중복 방지)
    needs_upload, reason = check_mapping_file_freshness()
    
    if needs_upload:
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        if os.path.exists(mapping_file):
            try:
                mapping_blob_name = "nickname_mapping.csv"
                blob_url, result_msg = upload_to_gcs(mapping_file, mapping_blob_name)
                
                if blob_url:
                    uploaded_files.append(mapping_blob_name)
                    print(f"📝 Mapping file uploaded: {reason}")
                else:
                    errors.append(f"Mapping file upload failed: {result_msg}")
                    
            except Exception as e:
                errors.append(f"Mapping file upload error: {str(e)}")
        else:
            print(f"📝 No local mapping file to upload")
    else:
        print(f"📝 Mapping file upload skipped: {reason}")
    
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
    GCS 업로드 결과를 로그 파일에 기록 (매핑 파일 동기화 정보 포함)
    
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
        
        # 🔥 매핑 파일 동기화 상태 확인
        needs_upload, freshness_reason = check_mapping_file_freshness()
        mapping_sync_status = "SKIPPED (consent.py already synced)" if not needs_upload else "UPLOADED (needed refresh)"
        
        upload_status = "SUCCESS" if uploaded_files and not errors else "PARTIAL" if uploaded_files else "FAILED"
        
        log_entry = f"""
[{datetime.now().strftime(LOG_FORMAT['timestamp_format'])}] SESSION: {session_label} - {session_id}_{timestamp}
Nickname: {original_nickname}
Status: {upload_status}
Save Trigger: Auto-save after second recording completion
Dual Evaluation: {dual_eval_used} (Research scores: Accuracy={accuracy_score}, Fluency={fluency_score})
Self-Efficacy: Average {efficacy_avg}/5.0 (6 items collected)
TOPIK Scores: 3-area reference scores included in ZIP
GCS Enabled: {GCS_ENABLED} (Service Account method - ZIP-only backup)
Bucket: {GCS_BUCKET_NAME}
Files uploaded: {len(uploaded_files)} ({', '.join(uploaded_files) if uploaded_files else 'None'})
Mapping file sync: {mapping_sync_status} ({freshness_reason})
Errors: {len(errors)} ({'; '.join(errors) if errors else 'None'})
Email notification: {'Sent' if email_sent else 'Not sent/Failed'}
Data Safety: Secured before survey step
Consent Format: HTML (Korean language support)
Excel Format: TOPIK 3-area scores included in ZIP only
{'='*80}
"""
        
        with open(log_filename, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
        
        return True
    except Exception:
        return False


def display_download_buttons(csv_filename, excel_filename, zip_filename):
    """
    연구자용 다운로드 버튼들 표시 (TOPIK 엑셀은 ZIP에만 포함)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: 참고용 엑셀 파일 경로 (ZIP에 포함됨)
        zip_filename: ZIP 파일 경로
    """
    if GCS_ENABLED:
        st.info(f"📤 Session {CURRENT_SESSION} ZIP file (with TOPIK Excel inside) should be automatically uploaded to Google Cloud Storage. Use these downloads as backup only.")
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
        st.info("📊 TOPIK scores inside ZIP")
    
    st.caption(f"ℹ️ Session {CURRENT_SESSION} data includes self-efficacy scores, TOPIK 3-area scores (Excel inside ZIP), and consent form.")


def display_session_details():
    """
    연구자용 세션 상세 정보 표시 (매핑 파일 동기화 정보 포함)
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
    
    # 🔥 TOPIK 참고용 점수 정보 추가
    st.markdown("**📊 TOPIK Reference Scores:**")
    timestamp = getattr(st.session_state, 'saved_timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
    reference_file = f"data/reference_scores_{timestamp}.xlsx"
    if os.path.exists(reference_file):
        st.write(f"✅ TOPIK 3-area scores saved to Excel")
        st.write(f"File: reference_scores_{timestamp}.xlsx")
        st.write(f"Contains: Content/Task, Language Use, Delivery scores (1-5 each)")
        st.write(f"Location: Inside ZIP file only")
    else:
        st.write("❌ TOPIK reference scores not found")
    
    # 🔥 매핑 파일 동기화 상태 표시
    st.markdown("**🔄 Mapping File Sync Status:**")
    needs_upload, freshness_reason = check_mapping_file_freshness()
    
    if needs_upload:
        st.warning(f"⚠️ Mapping file needs update: {freshness_reason}")
    else:
        st.success(f"✅ Mapping file is current: {freshness_reason}")
    
    # GCS 연동 상태 표시
    st.markdown("**☁️ Google Cloud Storage Status:**")
    if GCS_ENABLED:
        st.success(f"✅ GCS upload is enabled (Service Account method)")
        if GCS_BUCKET_NAME:
            st.write(f"Bucket: {GCS_BUCKET_NAME}")
            st.write(f"Storage method: ZIP archives only")
            st.write(f"Consent format: HTML (Korean language support)")
            st.write(f"Self-efficacy: 6 items (1-5 scale) included")
            st.write(f"TOPIK scores: 3-area Excel inside ZIP")
            st.write(f"Save timing: Auto-save after 2nd recording")
            st.write(f"Mapping sync: Smart upload (avoid duplicates from consent.py)")
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