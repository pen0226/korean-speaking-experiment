"""
data_io.py
실험 데이터 저장, 백업, 업로드 및 로그 관리 모듈 (연구용 TOPIK 분석 시트 추가)
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
from research_scoring import (
    get_research_analysis_data,
    generate_grading_summary_row
)


def save_session_data():
    """
    세션 데이터를 CSV + 연구용 Excel로 저장 (자기효능감 + TOPIK 분석 포함)
    
    Returns:
        tuple: (csv_filename, excel_filename, audio_folder, saved_files, zip_filename, timestamp)
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
        
        # 🆕 연구용 Excel 파일 생성
        excel_filename = save_research_excel(timestamp)
        
        audio_folder, saved_files = save_audio_files(timestamp)
        zip_filename = create_comprehensive_backup_zip(st.session_state.session_id, timestamp)
        
        return csv_filename, excel_filename, audio_folder, saved_files, zip_filename, timestamp
    
    except Exception as e:
        st.error(f"❌ Error saving session data: {str(e)}")
        return None, None, None, [], None, None


def save_research_excel(timestamp):
    """
    연구용 TOPIK 분석 Excel 파일 생성
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        str: Excel 파일 경로
    """
    try:
        session_num = getattr(st.session_state, 'session_number', CURRENT_SESSION)
        excel_filename = os.path.join(
            FOLDERS["data"], 
            f"research_analysis_session{session_num}_{st.session_state.session_id}_{timestamp}.xlsx"
        )
        
        # Excel 작성기 생성
        with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
            
            # === 시트 1: 채점자용 요약 테이블 ===
            grading_summary = create_grading_summary_sheet()
            if grading_summary:
                grading_df = pd.DataFrame([grading_summary])
                grading_df.to_excel(writer, sheet_name='채점자용_요약', index=False)
            
            # === 시트 2: 1차 시도 상세 분석 ===
            if st.session_state.transcription_1:
                research_data_1 = generate_research_data_for_attempt(1)
                if research_data_1:
                    analysis_df_1 = create_detailed_analysis_sheet(research_data_1, 1)
                    analysis_df_1.to_excel(writer, sheet_name='1차_상세분석', index=False)
            
            # === 시트 3: 2차 시도 상세 분석 ===
            if st.session_state.transcription_2:
                research_data_2 = generate_research_data_for_attempt(2)
                if research_data_2:
                    analysis_df_2 = create_detailed_analysis_sheet(research_data_2, 2)
                    analysis_df_2.to_excel(writer, sheet_name='2차_상세분석', index=False)
            
            # === 시트 4: TOPIK 점수 비교 ===
            if st.session_state.transcription_1 and st.session_state.transcription_2:
                comparison_df = create_score_comparison_sheet()
                comparison_df.to_excel(writer, sheet_name='점수_비교', index=False)
            
            # === 시트 5: 원본 데이터 ===
            original_session_data = build_session_data(timestamp)
            original_df = pd.DataFrame([original_session_data])
            original_df.to_excel(writer, sheet_name='원본_세션데이터', index=False)
        
        print(f"✅ Research Excel created: {excel_filename}")
        return excel_filename
        
    except Exception as e:
        st.error(f"❌ Error creating research Excel: {str(e)}")
        return None


def create_grading_summary_sheet():
    """
    채점자용 요약 시트 데이터 생성
    
    Returns:
        dict: 채점자용 요약 데이터
    """
    try:
        # 1차, 2차 연구 데이터 생성
        research_data_1 = generate_research_data_for_attempt(1) if st.session_state.transcription_1 else None
        research_data_2 = generate_research_data_for_attempt(2) if st.session_state.transcription_2 else None
        
        if research_data_1:
            # 채점자용 요약 행 생성
            summary_row = generate_grading_summary_row(research_data_1, research_data_2)
            
            # 추가 메타데이터
            summary_row.update({
                "experiment_question": EXPERIMENT_QUESTION,
                "learning_duration": getattr(st.session_state, 'learning_duration', ''),
                "speaking_confidence": getattr(st.session_state, 'speaking_confidence', ''),
                "self_efficacy_average": calculate_self_efficacy_average(),
                "consent_given": getattr(st.session_state, 'consent_given', False),
                "data_quality_notes": generate_data_quality_notes()
            })
            
            return summary_row
        
        return None
        
    except Exception as e:
        print(f"Error creating grading summary: {e}")
        return None


def create_detailed_analysis_sheet(research_data, attempt_number):
    """
    상세 분석 시트 데이터 생성
    
    Args:
        research_data: 연구 분석 데이터
        attempt_number: 시도 번호
        
    Returns:
        DataFrame: 상세 분석 데이터프레임
    """
    try:
        # 분석 데이터를 플랫하게 변환
        flattened_data = flatten_research_data(research_data, attempt_number)
        
        # 데이터프레임 생성 (세로 형태로 키-값 쌍)
        analysis_rows = []
        for category, data in flattened_data.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    analysis_rows.append({
                        "카테고리": category,
                        "항목": key,
                        "값": str(value),
                        "설명": get_item_description(category, key)
                    })
            else:
                analysis_rows.append({
                    "카테고리": category,
                    "항목": category,
                    "값": str(data),
                    "설명": get_item_description(category, category)
                })
        
        return pd.DataFrame(analysis_rows)
        
    except Exception as e:
        print(f"Error creating detailed analysis sheet: {e}")
        return pd.DataFrame()


def create_score_comparison_sheet():
    """
    점수 비교 시트 생성
    
    Returns:
        DataFrame: 점수 비교 데이터프레임
    """
    try:
        research_data_1 = generate_research_data_for_attempt(1)
        research_data_2 = generate_research_data_for_attempt(2)
        
        if not research_data_1 or not research_data_2:
            return pd.DataFrame()
        
        # 점수 비교 데이터
        comparison_data = []
        
        # TOPIK 3영역 점수 비교
        scores_1 = research_data_1['summary_indicators']
        scores_2 = research_data_2['summary_indicators']
        
        topik_areas = [
            ("내용 및 과제 수행", "content_task_performance_score"),
            ("언어 사용", "language_use_score"),
            ("발화 전달력", "speech_delivery_score"),
            ("전체 평균", "overall_auto_score")
        ]
        
        for area_name, score_key in topik_areas:
            score_1 = scores_1.get(score_key, 0)
            score_2 = scores_2.get(score_key, 0)
            improvement = score_2 - score_1
            
            comparison_data.append({
                "TOPIK_영역": area_name,
                "1차_자동점수": score_1,
                "2차_자동점수": score_2,
                "개선도": improvement,
                "개선율": f"{(improvement/score_1*100):.1f}%" if score_1 > 0 else "N/A",
                "1차_수동점수_채점자1": "",
                "1차_수동점수_채점자2": "",
                "2차_수동점수_채점자1": "",
                "2차_수동점수_채점자2": "",
                "수동점수_개선도": ""
            })
        
        # 세부 지표 비교
        detailed_comparison = []
        
        # 기본 지표들
        basic_metrics = [
            ("녹음 길이", "duration_seconds", "초"),
            ("단어 수", lambda d: d['task_performance']['content_richness']['total_words'], "개"),
            ("문장 수", lambda d: d['task_performance']['content_richness']['sentences_count'], "개"),
            ("문법 오류", lambda d: d['language_use']['grammar_accuracy']['total_grammar_errors'], "개"),
            ("오류율", lambda d: d['language_use']['grammar_accuracy']['error_rate'], "%"),
            ("어휘 다양성", lambda d: d['language_use']['vocabulary_usage']['vocabulary_diversity'], "비율"),
            ("분당 단어수", lambda d: d['speech_delivery_indicators']['fluency_indicators']['words_per_minute'], "wpm")
        ]
        
        for metric_name, metric_key, unit in basic_metrics:
            if callable(metric_key):
                value_1 = metric_key(research_data_1)
                value_2 = metric_key(research_data_2)
            else:
                value_1 = research_data_1.get(metric_key, 0)
                value_2 = research_data_2.get(metric_key, 0)
            
            change = value_2 - value_1
            
            detailed_comparison.append({
                "세부_지표": metric_name,
                "1차_값": value_1,
                "2차_값": value_2,
                "변화량": change,
                "단위": unit,
                "평가": evaluate_change(metric_name, change)
            })
        
        # 두 데이터프레임 합치기
        comparison_df = pd.DataFrame(comparison_data)
        detailed_df = pd.DataFrame(detailed_comparison)
        
        # 빈 행으로 구분
        separator = pd.DataFrame([{"TOPIK_영역": "=== 세부 지표 비교 ==="}])
        
        # 컬럼 맞추기
        max_cols = max(len(comparison_df.columns), len(detailed_df.columns))
        for df in [comparison_df, separator, detailed_df]:
            while len(df.columns) < max_cols:
                df[f"빈컬럼_{len(df.columns)}"] = ""
        
        return pd.concat([comparison_df, separator, detailed_df], ignore_index=True)
        
    except Exception as e:
        print(f"Error creating score comparison sheet: {e}")
        return pd.DataFrame()


def generate_research_data_for_attempt(attempt_number):
    """
    특정 시도에 대한 연구 데이터 생성
    
    Args:
        attempt_number: 시도 번호 (1 or 2)
        
    Returns:
        dict: 연구 분석 데이터
    """
    try:
        if attempt_number == 1:
            transcript = st.session_state.transcription_1
            duration = getattr(st.session_state, 'audio_duration_1', 0)
        elif attempt_number == 2:
            transcript = st.session_state.transcription_2
            duration = getattr(st.session_state, 'audio_duration_2', 0)
        else:
            return None
        
        if not transcript:
            return None
        
        # GPT 피드백 데이터
        feedback_data = st.session_state.feedback if attempt_number == 1 else {}
        grammar_issues = feedback_data.get('grammar_issues', [])
        
        # 연구 분석 데이터 생성
        research_data = get_research_analysis_data(
            transcript=transcript,
            grammar_issues=grammar_issues,
            duration_s=duration,
            feedback_data=feedback_data,
            attempt_number=attempt_number
        )
        
        return research_data
        
    except Exception as e:
        print(f"Error generating research data for attempt {attempt_number}: {e}")
        return None


def flatten_research_data(research_data, attempt_number):
    """
    연구 데이터를 플랫한 구조로 변환
    
    Args:
        research_data: 연구 분석 데이터
        attempt_number: 시도 번호
        
    Returns:
        dict: 플랫한 구조의 데이터
    """
    flattened = {
        f"기본정보_시도{attempt_number}": {
            "세션ID": research_data.get("session_id", ""),
            "시도번호": research_data.get("attempt", ""),
            "분석시간": research_data.get("timestamp", ""),
            "녹음길이": f"{research_data.get('duration_seconds', 0)}초"
        },
        
        "과제수행_분석": {
            "여름방학_언급": research_data["task_performance"]["topics_mentioned"]["summer_vacation"],
            "한국계획_언급": research_data["task_performance"]["topics_mentioned"]["korea_plans"],
            "양주제_완료": research_data["task_performance"]["topics_mentioned"]["both_topics_covered"],
            "이유제시_완성도": research_data["task_performance"]["reasoning_provided"]["reasoning_completeness"],
            "총단어수": research_data["task_performance"]["content_richness"]["total_words"],
            "고유단어수": research_data["task_performance"]["content_richness"]["unique_words"],
            "문장수": research_data["task_performance"]["content_richness"]["sentences_count"],
            "세부사항_개수": research_data["task_performance"]["content_richness"]["detail_count"],
            "담화구성_점수": research_data["task_performance"]["discourse_organization"]["organization_score"]
        },
        
        "언어사용_분석": {
            "문법오류_총개수": research_data["language_use"]["grammar_accuracy"]["total_grammar_errors"],
            "오류율": f"{research_data['language_use']['grammar_accuracy']['error_rate']}%",
            "정확성_점수": research_data["language_use"]["grammar_accuracy"]["accuracy_score"],
            "어휘다양성": research_data["language_use"]["vocabulary_usage"]["vocabulary_diversity"],
            "존댓말_수준": research_data["language_use"]["language_appropriateness"]["speech_level"],
            "존댓말_일관성": research_data["language_use"]["language_appropriateness"]["consistency"]
        },
        
        "발화전달력_분석": {
            "분당단어수": research_data["speech_delivery_indicators"]["fluency_indicators"]["words_per_minute"],
            "망설임표지": ", ".join(research_data["speech_delivery_indicators"]["fluency_indicators"]["hesitation_markers"]),
            "반복횟수": research_data["speech_delivery_indicators"]["fluency_indicators"]["repetition_count"],
            "평균문장길이": research_data["speech_delivery_indicators"]["speech_patterns"]["average_sentence_length"],
            "미완성문장수": research_data["speech_delivery_indicators"]["speech_patterns"]["incomplete_sentences"]
        },
        
        "TOPIK_자동점수": {
            "내용및과제수행": research_data["summary_indicators"]["content_task_performance_score"],
            "언어사용": research_data["summary_indicators"]["language_use_score"],
            "발화전달력": research_data["summary_indicators"]["speech_delivery_score"],
            "전체평균": research_data["summary_indicators"]["overall_auto_score"]
        },
        
        "세부점수": research_data["summary_indicators"]["detailed_scores"],
        
        "채점참고사항": {
            "주요특징": "; ".join(research_data["summary_indicators"]["grading_notes"]),
            "주의사항": "; ".join(research_data["summary_indicators"]["attention_points"]),
            "발화분석": research_data["summary_indicators"]["speech_delivery_breakdown"]["delivery_explanation"]
        }
    }
    
    return flattened


def get_item_description(category, key):
    """
    항목별 설명 반환
    
    Args:
        category: 카테고리
        key: 키
        
    Returns:
        str: 설명
    """
    descriptions = {
        "과제수행_분석": {
            "여름방학_언급": "여름방학 관련 내용 언급 여부",
            "한국계획_언급": "한국에서의 계획 관련 내용 언급 여부",
            "양주제_완료": "두 주제 모두 다룸 여부",
            "이유제시_완성도": "각 주제에 대한 이유 설명 완성도 (both/partial/none)",
            "세부사항_개수": "구체적인 세부사항의 개수",
            "담화구성_점수": "담화 조직성 점수 (1-5점)"
        },
        "언어사용_분석": {
            "오류율": "총 단어 수 대비 문법 오류 비율",
            "어휘다양성": "고유 단어 수 / 총 단어 수",
            "존댓말_수준": "주로 사용한 존댓말 수준"
        },
        "발화전달력_분석": {
            "분당단어수": "말하기 속도 지표 (60-80이 적절)",
            "망설임표지": "음, 어, 그 등의 망설임 표현",
            "평균문장길이": "문장당 평균 단어 수"
        },
        "TOPIK_자동점수": {
            "내용및과제수행": "과제 완성도 + 내용 풍부함 + 담화 구성 (1-5점)",
            "언어사용": "문법 정확성 + 어휘 다양성 (1-5점)",
            "발화전달력": "속도 + 유창성 + 일관성 간접 지표 (1-5점)"
        }
    }
    
    return descriptions.get(category, {}).get(key, "")


def evaluate_change(metric_name, change):
    """
    변화량 평가
    
    Args:
        metric_name: 지표명
        change: 변화량
        
    Returns:
        str: 평가 결과
    """
    if metric_name in ["녹음 길이", "단어 수", "문장 수", "어휘 다양성", "분당 단어수"]:
        # 증가가 좋은 지표들
        if change > 0:
            return "개선"
        elif change == 0:
            return "동일"
        else:
            return "감소"
    elif metric_name in ["문법 오류", "오류율"]:
        # 감소가 좋은 지표들
        if change < 0:
            return "개선"
        elif change == 0:
            return "동일"
        else:
            return "증가"
    else:
        return "변화"


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


def generate_data_quality_notes():
    """
    데이터 품질 참고사항 생성
    
    Returns:
        str: 품질 참고사항
    """
    notes = []
    
    # 녹음 길이 체크
    duration_1 = getattr(st.session_state, 'audio_duration_1', 0)
    duration_2 = getattr(st.session_state, 'audio_duration_2', 0)
    
    if duration_1 >= 90:
        notes.append("1차녹음 우수길이")
    elif duration_1 >= 60:
        notes.append("1차녹음 적정길이")
    else:
        notes.append("1차녹음 짧음")
    
    if duration_2 >= 90:
        notes.append("2차녹음 우수길이")
    elif duration_2 >= 60:
        notes.append("2차녹음 적정길이")
    else:
        notes.append("2차녹음 짧음")
    
    # 자기효능감 체크
    efficacy_avg = calculate_self_efficacy_average()
    if efficacy_avg > 0:
        notes.append(f"자기효능감 {efficacy_avg}/5.0")
    
    # 동의서 체크
    if getattr(st.session_state, 'consent_given', False):
        notes.append("동의완료")
    
    return "; ".join(notes)


# === 기존 함수들 (수정 없음) ===

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
        
        # 🆕 TOPIK 자동 점수 추가
        'topik_content_task_auto_1': get_topik_score(1, 'content_task_performance_score'),
        'topik_language_use_auto_1': get_topik_score(1, 'language_use_score'),
        'topik_speech_delivery_auto_1': get_topik_score(1, 'speech_delivery_score'),
        'topik_overall_auto_1': get_topik_score(1, 'overall_auto_score'),
        'topik_content_task_auto_2': get_topik_score(2, 'content_task_performance_score'),
        'topik_language_use_auto_2': get_topik_score(2, 'language_use_score'),
        'topik_speech_delivery_auto_2': get_topik_score(2, 'speech_delivery_score'),
        'topik_overall_auto_2': get_topik_score(2, 'overall_auto_score'),
        
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


def get_topik_score(attempt_number, score_type):
    """
    특정 시도의 TOPIK 점수 반환
    
    Args:
        attempt_number: 시도 번호 (1 or 2)
        score_type: 점수 타입
        
    Returns:
        float: TOPIK 점수
    """
    try:
        research_data = generate_research_data_for_attempt(attempt_number)
        if research_data:
            return research_data['summary_indicators'].get(score_type, 0)
        return 0
    except:
        return 0


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
    참여자 정보 파일 생성 (자기효능감 + TOPIK 점수 포함)
    
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
        
        # TOPIK 자동 점수 정보
        topik_scores_1 = []
        topik_scores_2 = []
        
        for attempt in [1, 2]:
            research_data = generate_research_data_for_attempt(attempt)
            if research_data:
                scores = research_data['summary_indicators']
                score_text = f"내용및과제수행: {scores.get('content_task_performance_score', 'N/A')}/5, 언어사용: {scores.get('language_use_score', 'N/A')}/5, 발화전달력: {scores.get('speech_delivery_score', 'N/A')}/5, 전체: {scores.get('overall_auto_score', 'N/A')}/5"
                if attempt == 1:
                    topik_scores_1.append(score_text)
                else:
                    topik_scores_2.append(score_text)
        
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

=== TOPIK-BASED AUTO SCORES (NEW) ===
1차 시도: {topik_scores_1[0] if topik_scores_1 else 'N/A'}
2차 시도: {topik_scores_2[0] if topik_scores_2 else 'N/A'}

=== RESEARCH SCORES (LEGACY) ===
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
Storage Method: GCS ZIP Archive + Research Excel (Auto-save after 2nd recording)
Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== FOR RESEARCHER ===
This file contains the link between the anonymous ID and the original nickname.
Data was automatically saved after second recording completion.
NEW: TOPIK-based 3-area scoring system implemented for research analysis.
Research Excel file includes detailed analysis sheets for manual grading.
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
    모든 세션 데이터를 포함한 완전한 백업 ZIP 생성 (연구용 Excel 포함)
    
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
            
            # 🆕 연구용 Excel 파일 추가
            excel_file = os.path.join(FOLDERS["data"], f"research_analysis_session{session_num}_{session_id}_{timestamp}.xlsx")
            if os.path.exists(excel_file):
                zipf.write(excel_file, f"research_analysis_{timestamp}.xlsx")
                print(f"✅ Research Excel included: research_analysis_{timestamp}.xlsx")
            
            # HTML 동의서 파일 추가
            consent_html = os.path.join(FOLDERS["data"], f"{session_id}_consent.html")
            if os.path.exists(consent_html):
                zipf.write(consent_html, f"consent_form_{session_id}.html")
                print(f"✅ Consent HTML file included: {session_id}_consent.html")
            else:
                print(f"⚠️ Consent HTML file not found: {session_id}_consent.html")
            
            # 혹시나 PDF 파일도 있다면 함께 포함 (하위 호환성)
            consent_pdf = os.path.join(FOLDERS["data"], f"{session_id}_consent.pdf")
            if os.path.exists(consent_pdf):
                zipf.write(consent_pdf, f"consent_form_{session_id}.pdf")
                print(f"✅ Consent PDF file also included: {session_id}_consent.pdf")
            
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
- participant_info.txt: Participant details + Research scores + Self-efficacy scores + TOPIK auto scores
- session_data_{timestamp}.csv: Complete session data with dual evaluation + TOPIK scores + self-efficacy data
- research_analysis_{timestamp}.xlsx: ⭐ NEW: Comprehensive research analysis with TOPIK-based scoring
- consent_form_{session_id}.html: Signed consent form (HTML format for Korean support)
- audio/: All recorded audio files (student + model pronunciations)

🆕 RESEARCH EXCEL SHEETS:
1. 채점자용_요약: Grading summary with auto/manual score columns (_auto, _rater1, _rater2)
2. 1차_상세분석: Detailed analysis of first attempt (task performance, language use, speech delivery)
3. 2차_상세분석: Detailed analysis of second attempt
4. 점수_비교: Score comparison between attempts with improvement metrics  
5. 원본_세션데이터: Original session data for reference

🎯 TOPIK-BASED AUTO SCORING (1-5 points each):
- 내용 및 과제 수행: Task completion + content richness + discourse organization
- 언어 사용: Grammar accuracy + vocabulary diversity + appropriateness
- 발화 전달력: Speaking pace + fluency indicators + consistency (indirect measures)

SELF-EFFICACY DATA:
- 6 items measured on 1-5 scale
- Average self-efficacy score: {efficacy_avg}/5.0
- Individual scores stored in CSV under self_efficacy_1 through self_efficacy_6

CONSENT FORM FORMAT:
- HTML format for perfect Korean language support
- Can be saved as PDF using browser print function (Ctrl+P)
- Avoids character encoding issues that occurred with direct PDF generation

DUAL EVALUATION SYSTEM:
- Student UI Score: Educational feedback (GPT-generated with TOPIK criteria)
- Research Auto Scores: TOPIK-based objective metrics for academic analysis
- Manual Grading Support: Excel templates for human raters with reference data

RESEARCH WORKFLOW:
1. Use research_analysis.xlsx for systematic manual grading
2. Auto scores provide baseline reference for human raters
3. Compare auto vs manual scores for reliability studies
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
        
        print(f"✅ Comprehensive backup ZIP created with research Excel: {zip_filename}")
        return zip_filename
        
    except Exception as e:
        st.error(f"❌ Error creating comprehensive backup ZIP: {e}")
        return None


# === GCS 관련 함수들 (수정 없음) ===

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
        excel_filename: Excel 파일 경로 (연구용)
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
    
    # ZIP 파일 업로드 (연구용 Excel 포함)
    if zip_filename and os.path.exists(zip_filename):
        try:
            blob_name = f"{session_folder}{session_id}_{timestamp}.zip"
            blob_url, result_msg = upload_to_gcs(zip_filename, blob_name)
            
            if blob_url:
                uploaded_files.append(blob_name)
                print(f"✅ ZIP with HTML consent + self-efficacy + research Excel uploaded: {blob_name}")
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
    GCS 업로드 결과를 로그 파일에 기록 (연구용 Excel 정보 포함)
    
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
        
        # TOPIK 점수 정보
        topik_1 = get_topik_score(1, 'overall_auto_score')
        topik_2 = get_topik_score(2, 'overall_auto_score')
        
        upload_status = "SUCCESS" if uploaded_files and not errors else "PARTIAL" if uploaded_files else "FAILED"
        
        log_entry = f"""
[{datetime.now().strftime(LOG_FORMAT['timestamp_format'])}] SESSION: {session_label} - {session_id}_{timestamp}
Nickname: {original_nickname}
Status: {upload_status}
Save Trigger: Auto-save after second recording completion
Dual Evaluation: {dual_eval_used} (Research scores: Accuracy={accuracy_score}, Fluency={fluency_score})
Self-Efficacy: Average {efficacy_avg}/5.0 (6 items collected)
        TOPIK Auto Scores: 1차={topik_1}/5, 2차={topik_2}/5 (NEW: 3-area scoring system)
GCS Enabled: {GCS_ENABLED} (Service Account method - ZIP with research Excel)
Bucket: {GCS_BUCKET_NAME}
Files uploaded: {len(uploaded_files)} ({', '.join(uploaded_files) if uploaded_files else 'None'})
Errors: {len(errors)} ({'; '.join(errors) if errors else 'None'})
Email notification: {'Sent' if email_sent else 'Not sent/Failed'}
Data Safety: Secured before survey step
Research Excel: TOPIK-based analysis with grading support included
Research Data: TOPIK 3-area auto scores + self-efficacy calculated and stored
Consent Format: HTML (Korean language support) - Fixed backup inclusion
{'='*80}
"""
        
        with open(log_filename, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
        
        return True
    except Exception:
        return False


def display_download_buttons(csv_filename, excel_filename, zip_filename):
    """
    연구자용 다운로드 버튼들 표시 (연구용 Excel 포함)
    
    Args:
        csv_filename: CSV 파일 경로
        excel_filename: Excel 파일 경로 (연구용)
        zip_filename: ZIP 파일 경로
    """
    if GCS_ENABLED:
        st.info("📤 ZIP file (including research Excel + HTML consent + self-efficacy data) should be automatically uploaded to Google Cloud Storage. Use these downloads as backup only.")
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
                    label="📦 Complete Backup ZIP (w/ Research Excel)",
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
        # 🆕 연구용 Excel 다운로드
        if excel_filename and os.path.exists(excel_filename):
            try:
                with open(excel_filename, 'rb') as f:
                    excel_data = f.read()
                st.download_button(
                    label="📊 Research Analysis Excel",
                    data=excel_data,
                    file_name=f"research_analysis_{st.session_state.session_id}_{timestamp_str}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
            except:
                st.info("Research Excel unavailable")
        else:
            st.info("Research Excel unavailable")
    
    with col3:
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
    
    st.caption("ℹ️ 🆕 Research Excel includes TOPIK-based analysis with manual grading templates. ZIP contains all files. HTML consent + self-efficacy data included.")


def display_session_details():
    """
    연구자용 세션 상세 정보 표시 (TOPIK 점수 포함)
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
    
    # 🆕 TOPIK 자동 점수 정보 표시
    st.markdown("**🎯 TOPIK-Based Auto Scores (NEW):**")
    topik_data_1 = generate_research_data_for_attempt(1)
    topik_data_2 = generate_research_data_for_attempt(2)
    
    if topik_data_1:
        scores_1 = topik_data_1['summary_indicators']
        st.write(f"1차 시도: 내용및과제수행 {scores_1.get('content_task_performance_score', 'N/A')}/5, 언어사용 {scores_1.get('language_use_score', 'N/A')}/5, 발화전달력 {scores_1.get('speech_delivery_score', 'N/A')}/5")
    
    if topik_data_2:
        scores_2 = topik_data_2['summary_indicators']
        st.write(f"2차 시도: 내용및과제수행 {scores_2.get('content_task_performance_score', 'N/A')}/5, 언어사용 {scores_2.get('language_use_score', 'N/A')}/5, 발화전달력 {scores_2.get('speech_delivery_score', 'N/A')}/5")
    
    if not topik_data_1 and not topik_data_2:
        st.write("❌ TOPIK auto scores not calculated")
    
    # 기존 연구용 점수 정보 표시
    research_scores = getattr(st.session_state, 'research_scores', {})
    if research_scores:
        st.markdown("**🔬 Legacy Research Scores:**")
        accuracy = research_scores.get('accuracy_score', 'N/A')
        fluency = research_scores.get('fluency_score', 'N/A')
        error_rate = research_scores.get('error_rate', 'N/A')
        word_count = research_scores.get('word_count', 'N/A')
        st.write(f"Accuracy Score: {accuracy}/10 (Error rate: {error_rate}%)")
        st.write(f"Fluency Score: {fluency}/10 (Word count: {word_count})")
        dual_eval = getattr(st.session_state, 'gpt_debug_info', {}).get('dual_evaluation', False)
        st.write(f"Dual Evaluation System: {'✅ Active' if dual_eval else '❌ Not used'}")
    else:
        st.write("**🔬 Legacy Research Scores:** ❌ Not calculated")
    
    # GCS 연동 상태 표시
    st.markdown("**☁️ Google Cloud Storage Status:**")
    if GCS_ENABLED:
        st.success("✅ GCS upload is enabled (Service Account method - ZIP with research Excel)")
        if GCS_BUCKET_NAME:
            st.write(f"Bucket: {GCS_BUCKET_NAME}")
            st.write(f"Storage method: ZIP archives + nickname mapping")
            st.write(f"Research Excel: TOPIK-based analysis with grading support")
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
    데이터 품질 정보 표시 (TOPIK 점수 포함)
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
        
        # 🆕 TOPIK 자동 점수 (1차)
        topik_data_1 = generate_research_data_for_attempt(1)
        if topik_data_1:
            st.write("**🎯 TOPIK Auto (1차):**")
            scores = topik_data_1['summary_indicators']
            st.write(f"내용: {scores.get('content_task_performance_score', 'N/A')}/5")
            st.write(f"언어: {scores.get('language_use_score', 'N/A')}/5")
            st.write(f"전달: {scores.get('speech_delivery_score', 'N/A')}/5")
        
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
        
        # 🆕 TOPIK 자동 점수 (2차)
        topik_data_2 = generate_research_data_for_attempt(2)
        if topik_data_2:
            st.write("**🎯 TOPIK Auto (2차):**")
            scores = topik_data_2['summary_indicators']
            st.write(f"내용: {scores.get('content_task_performance_score', 'N/A')}/5")
            st.write(f"언어: {scores.get('language_use_score', 'N/A')}/5")
            st.write(f"전달: {scores.get('speech_delivery_score', 'N/A')}/5")
            
            # 개선도 표시
            if topik_data_1:
                scores_1 = topik_data_1['summary_indicators']
                improvement = scores['overall_auto_score'] - scores_1['overall_auto_score']
                st.write(f"전체 개선: {improvement:+.1f}")
        
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