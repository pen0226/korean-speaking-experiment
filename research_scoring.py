"""
research_scoring.py
TOPIK 말하기 기준 연구용 점수 계산 및 채점 보조 데이터 생성 모듈
"""

import re
import json
from datetime import datetime
import streamlit as st
from config import EXPERIMENT_QUESTION, CURRENT_SESSION


# === TOPIK 3영역 자동 점수 계산 함수들 ===

def calculate_topik_3_scores(transcript, grammar_issues, duration_s, feedback_data):
    """
    TOPIK 말하기 3영역 자동 점수 계산 (1-5점)
    
    Args:
        transcript: STT 전사 텍스트
        grammar_issues: GPT가 찾은 문법 이슈들
        duration_s: 녹음 길이 (초)
        feedback_data: GPT 피드백 데이터
        
    Returns:
        dict: TOPIK 3영역 자동 점수
    """
    # 1. 내용 및 과제 수행 점수
    content_task_score = calculate_content_task_performance_score(
        transcript, duration_s, feedback_data
    )
    
    # 2. 언어 사용 점수  
    language_use_score = calculate_language_use_score(
        transcript, grammar_issues, feedback_data
    )
    
    # 3. 발화 전달력 점수 (간접 지표)
    speech_delivery_score = calculate_speech_delivery_score(
        transcript, duration_s
    )
    
    # 전체 평균
    overall_score = (content_task_score + language_use_score + speech_delivery_score) / 3
    
    return {
        "content_task_performance_score": round(content_task_score, 1),
        "language_use_score": round(language_use_score, 1),
        "speech_delivery_score": round(speech_delivery_score, 1),
        "overall_auto_score": round(overall_score, 1)
    }


def calculate_content_task_performance_score(transcript, duration_s, feedback_data):
    """
    내용 및 과제 수행 자동 점수 계산 (1-5점)
    
    Args:
        transcript: 전사 텍스트
        duration_s: 길이 (초)
        feedback_data: 피드백 데이터
        
    Returns:
        float: 과제 수행 점수 (1-5)
    """
    score = 0.0
    
    # 1. 과제 완성도 (2점 만점)
    task_completion = analyze_task_completion(transcript)
    if task_completion["both_topics_covered"]:
        score += 1.5
    elif task_completion["topics_mentioned"]["summer_vacation"] or task_completion["topics_mentioned"]["korea_plans"]:
        score += 0.8
    
    if task_completion["reasoning_provided"]["reasoning_completeness"] == "both":
        score += 0.5
    elif task_completion["reasoning_provided"]["reasoning_completeness"] == "partial":
        score += 0.3
    
    # 2. 내용 풍부함 (2점 만점)
    content_richness = analyze_content_richness(transcript, feedback_data)
    detail_score = min(2.0, content_richness["detail_count"] * 0.4)  # 최대 2점
    score += detail_score
    
    # 3. 담화 구성 (1점 만점)
    organization = analyze_discourse_organization(transcript)
    if organization["organization_score"] >= 4:
        score += 1.0
    elif organization["organization_score"] >= 3:
        score += 0.7
    elif organization["organization_score"] >= 2:
        score += 0.4
    
    return min(5.0, max(1.0, score))


def calculate_language_use_score(transcript, grammar_issues, feedback_data):
    """
    언어 사용 자동 점수 계산 (1-5점)
    
    Args:
        transcript: 전사 텍스트
        grammar_issues: 문법 이슈들
        feedback_data: 피드백 데이터
        
    Returns:
        float: 언어 사용 점수 (1-5)
    """
    score = 0.0
    
    # 1. 문법 정확성 (2.5점 만점)
    accuracy_analysis = analyze_grammar_accuracy(transcript, grammar_issues)
    error_rate = accuracy_analysis["error_rate"]
    
    if error_rate <= 3:
        score += 2.5
    elif error_rate <= 6:
        score += 2.0
    elif error_rate <= 10:
        score += 1.5
    elif error_rate <= 15:
        score += 1.0
    else:
        score += 0.5
    
    # 2. 어휘 다양성 및 적절성 (2.5점 만점)
    vocabulary_analysis = analyze_vocabulary_usage(transcript, feedback_data)
    diversity = vocabulary_analysis["vocabulary_diversity"]
    
    if diversity >= 0.7:
        score += 2.5
    elif diversity >= 0.6:
        score += 2.0
    elif diversity >= 0.5:
        score += 1.5
    elif diversity >= 0.4:
        score += 1.0
    else:
        score += 0.5
    
    return min(5.0, max(1.0, score))


def calculate_speech_delivery_score(transcript, duration_s):
    """
    발화 전달력 간접 점수 계산 (1-5점)
    
    Args:
        transcript: 전사 텍스트
        duration_s: 길이 (초)
        
    Returns:
        float: 발화 전달력 점수 (1-5)
    """
    score = 0.0
    
    # 1. 말하기 속도 적절성 (2점 만점)
    pace_score = calculate_pace_appropriateness(transcript, duration_s)
    score += pace_score * 2
    
    # 2. 유창성 지표 (2점 만점)
    fluency_score = calculate_fluency_indicators(transcript)
    score += fluency_score * 2
    
    # 3. 발화 일관성 (1점 만점)
    consistency_score = calculate_speech_consistency(transcript)
    score += consistency_score
    
    return min(5.0, max(1.0, score))


# === 세부 분석 함수들 ===

def analyze_task_completion(transcript):
    """
    과제 완성도 분석
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        dict: 과제 완성도 분석 결과
    """
    # 여름방학 관련 키워드
    summer_keywords = ["여름", "방학", "휴가", "여행", "놀러", "쉬", "했어요", "갔어요"]
    
    # 한국 계획 관련 키워드  
    korea_keywords = ["한국", "계획", "할 거예요", "하려고", "배우", "공부", "살", "머물", "갈 거예요"]
    
    # 이유 표현 키워드
    reason_keywords = ["때문에", "위해서", "원해서", "좋아서", "싶어서", "해서", "니까", "어서"]
    
    summer_mentioned = any(keyword in transcript for keyword in summer_keywords)
    korea_mentioned = any(keyword in transcript for keyword in korea_keywords)
    both_topics = summer_mentioned and korea_mentioned
    
    # 이유 제시 여부 확인
    reason_provided = any(keyword in transcript for keyword in reason_keywords)
    
    # 문장 분할로 더 세밀한 분석
    sentences = split_korean_sentences(transcript)
    summer_sentences = [s for s in sentences if any(kw in s for kw in summer_keywords)]
    korea_sentences = [s for s in sentences if any(kw in s for kw in korea_keywords)]
    
    summer_has_reason = any(any(kw in s for kw in reason_keywords) for s in summer_sentences)
    korea_has_reason = any(any(kw in s for kw in reason_keywords) for s in korea_sentences)
    
    if summer_has_reason and korea_has_reason:
        reasoning_completeness = "both"
    elif summer_has_reason or korea_has_reason:
        reasoning_completeness = "partial"
    else:
        reasoning_completeness = "none"
    
    return {
        "topics_mentioned": {
            "summer_vacation": summer_mentioned,
            "korea_plans": korea_mentioned,
            "both_topics_covered": both_topics
        },
        "reasoning_provided": {
            "summer_vacation_reason": summer_has_reason,
            "korea_plans_reason": korea_has_reason,
            "reasoning_completeness": reasoning_completeness
        }
    }


def analyze_content_richness(transcript, feedback_data):
    """
    내용 풍부함 분석
    
    Args:
        transcript: 전사 텍스트
        feedback_data: 피드백 데이터
        
    Returns:
        dict: 내용 풍부함 분석 결과
    """
    words = transcript.split()
    total_words = len(words)
    unique_words = len(set(words))
    sentences_count = len(split_korean_sentences(transcript))
    
    # 구체적 세부사항 추출
    specific_details = extract_specific_details(transcript)
    
    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "sentences_count": sentences_count,
        "specific_details": specific_details,
        "detail_count": len(specific_details),
        "vocabulary_diversity": unique_words / total_words if total_words > 0 else 0
    }


def analyze_discourse_organization(transcript):
    """
    담화 구성 분석
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        dict: 담화 구성 분석 결과
    """
    # 주제 전환 표현
    transition_words = ["그리고", "또", "그리고는", "다음에", "그 다음", "두 번째로"]
    
    # 시간 표현
    time_expressions = ["여름 방학에", "한국에서", "지금", "앞으로", "미래에", "나중에"]
    
    # 연결어
    connecting_words = ["그래서", "왜냐하면", "때문에", "그런데", "하지만", "그러나"]
    
    transitions_used = [word for word in transition_words if word in transcript]
    time_exprs_used = [expr for expr in time_expressions if expr in transcript]
    connectors_used = [word for word in connecting_words if word in transcript]
    
    # 조직성 점수 계산 (1-5)
    org_score = 1  # 기본 1점
    
    if transitions_used:
        org_score += 1
    if len(time_exprs_used) >= 2:
        org_score += 1
    if connectors_used:
        org_score += 1
    if len(split_korean_sentences(transcript)) >= 5:  # 충분한 문장 수
        org_score += 1
    
    return {
        "topic_transition_used": len(transitions_used) > 0,
        "time_expressions": time_exprs_used,
        "connecting_words": connectors_used,
        "organization_score": min(5, org_score)
    }


def analyze_grammar_accuracy(transcript, grammar_issues):
    """
    문법 정확성 분석
    
    Args:
        transcript: 전사 텍스트
        grammar_issues: 문법 이슈들
        
    Returns:
        dict: 문법 정확성 분석 결과
    """
    total_words = len(transcript.split()) if transcript.strip() else 0
    
    # 유효한 문법 오류 개수 계산
    valid_errors = 0
    error_types = {"Particle": 0, "Verb_Ending": 0, "Verb_Tense": 0, "Others": 0}
    
    for issue in grammar_issues:
        if isinstance(issue, str) and '|' in issue:
            parts = issue.split('|')
            if len(parts) >= 3 and parts[1].strip() and parts[2].strip():
                valid_errors += 1
                error_type = parts[0].strip()
                if error_type in error_types:
                    error_types[error_type] += 1
                else:
                    error_types["Others"] += 1
    
    error_rate = (valid_errors / total_words * 100) if total_words > 0 else 0
    accuracy_score = max(0, min(10, 10 - (error_rate / 10)))
    
    return {
        "total_grammar_errors": valid_errors,
        "error_types": error_types,
        "error_rate": round(error_rate, 2),
        "accuracy_score": round(accuracy_score, 1)
    }


def analyze_vocabulary_usage(transcript, feedback_data):
    """
    어휘 사용 분석
    
    Args:
        transcript: 전사 텍스트
        feedback_data: 피드백 데이터
        
    Returns:
        dict: 어휘 사용 분석 결과
    """
    words = transcript.split()
    total_words = len(words)
    unique_words = len(set(words))
    
    # 반복 단어 분석
    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1
    
    repeated_words = {word: count for word, count in word_counts.items() if count > 1}
    
    # 고급 어휘 탐지 (임시)
    advanced_vocab = ["전통", "문화", "경험", "기회", "목표", "계획", "여행", "활동"]
    found_advanced = [word for word in advanced_vocab if word in transcript]
    
    # 기본 어휘 비율 계산
    basic_words = ["이", "그", "저", "것", "하다", "가다", "오다", "보다", "말하다", "좋다"]
    basic_count = sum(1 for word in words if any(basic in word for basic in basic_words))
    basic_ratio = basic_count / total_words if total_words > 0 else 0
    
    vocabulary_diversity = unique_words / total_words if total_words > 0 else 0
    
    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "vocabulary_diversity": round(vocabulary_diversity, 3),
        "repeated_words": repeated_words,
        "advanced_vocabulary": found_advanced,
        "basic_vocabulary_ratio": round(basic_ratio, 3)
    }


def analyze_speech_delivery_indicators(transcript, duration_s):
    """
    발화 전달력 간접 지표 분석
    
    Args:
        transcript: 전사 텍스트
        duration_s: 길이 (초)
        
    Returns:
        dict: 발화 전달력 지표
    """
    words = transcript.split()
    total_words = len(words)
    
    # 분당 단어 수
    words_per_minute = (total_words / duration_s * 60) if duration_s > 0 else 0
    
    # 망설임 표지 탐지
    hesitation_markers = ["음", "어", "그", "뭐", "그게"]
    found_hesitations = [marker for marker in hesitation_markers if marker in transcript]
    
    # 반복 패턴 탐지
    repetition_count = count_repetitions(transcript)
    
    # 미완성 문장 추정 (문장 부호 없이 끝나는 경우)
    sentences = split_korean_sentences(transcript)
    incomplete_sentences = sum(1 for s in sentences if not s.strip().endswith(('요', '다', '니다', '.', '!', '?')))
    
    # 평균 문장 길이
    avg_sentence_length = total_words / len(sentences) if sentences else 0
    
    return {
        "fluency_indicators": {
            "words_per_minute": round(words_per_minute, 1),
            "hesitation_markers": found_hesitations,
            "repetition_count": repetition_count,
            "self_correction": 0  # STT로는 탐지 어려움
        },
        "speech_patterns": {
            "average_sentence_length": round(avg_sentence_length, 1),
            "pause_indicators": len(found_hesitations),  # 간접 지표
            "incomplete_sentences": incomplete_sentences
        }
    }


def calculate_pace_appropriateness(transcript, duration_s):
    """
    말하기 속도 적절성 계산 (0-1)
    
    Args:
        transcript: 전사 텍스트
        duration_s: 길이 (초)
        
    Returns:
        float: 속도 적절성 점수 (0-1)
    """
    words = len(transcript.split())
    wpm = (words / duration_s * 60) if duration_s > 0 else 0
    
    # 이상적 범위: 60-80 wpm
    if 60 <= wpm <= 80:
        return 1.0
    elif 50 <= wpm < 60 or 80 < wpm <= 90:
        return 0.8
    elif 40 <= wpm < 50 or 90 < wpm <= 100:
        return 0.6
    elif 30 <= wpm < 40 or 100 < wpm <= 120:
        return 0.4
    else:
        return 0.2


def calculate_fluency_indicators(transcript):
    """
    유창성 지표 계산 (0-1)
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        float: 유창성 점수 (0-1)
    """
    # 망설임 표지 개수
    hesitation_markers = ["음", "어", "그", "뭐"]
    hesitation_count = sum(transcript.count(marker) for marker in hesitation_markers)
    
    # 반복 개수
    repetition_count = count_repetitions(transcript)
    
    # 총 단어 수 대비 망설임/반복 비율
    total_words = len(transcript.split())
    if total_words == 0:
        return 0.0
    
    disruption_ratio = (hesitation_count + repetition_count) / total_words
    
    # 비율이 낮을수록 높은 점수
    if disruption_ratio <= 0.05:
        return 1.0
    elif disruption_ratio <= 0.1:
        return 0.8
    elif disruption_ratio <= 0.15:
        return 0.6
    elif disruption_ratio <= 0.2:
        return 0.4
    else:
        return 0.2


def calculate_speech_consistency(transcript):
    """
    발화 일관성 계산 (0-1)
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        float: 일관성 점수 (0-1)
    """
    sentences = split_korean_sentences(transcript)
    if len(sentences) < 2:
        return 0.5
    
    # 문장 길이 편차 계산
    sentence_lengths = [len(s.split()) for s in sentences]
    avg_length = sum(sentence_lengths) / len(sentence_lengths)
    
    # 표준편차 계산
    variance = sum((length - avg_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
    std_dev = variance ** 0.5
    
    # 편차가 작을수록 높은 점수
    if std_dev <= 2:
        return 1.0
    elif std_dev <= 4:
        return 0.8
    elif std_dev <= 6:
        return 0.6
    elif std_dev <= 8:
        return 0.4
    else:
        return 0.2


# === 보조 함수들 ===

def split_korean_sentences(text):
    """
    한국어 문장 분할
    
    Args:
        text: 분할할 텍스트
        
    Returns:
        list: 분할된 문장들
    """
    pattern = r'([.!?]|(?:요|어요|습니다|세요|해요|이에요|예요)\s*)'
    sentences = re.split(pattern, text)
    
    result = []
    for i in range(0, len(sentences)-1, 2):
        if i+1 < len(sentences):
            sentence = sentences[i] + sentences[i+1]
            if sentence.strip():
                result.append(sentence.strip())
    
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())
    
    return [s for s in result if len(s.strip()) > 3]


def extract_specific_details(transcript):
    """
    구체적 세부사항 추출
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        list: 구체적 세부사항들
    """
    details = []
    
    # 장소 관련
    places = ["바다", "산", "집", "학교", "카페", "식당", "공원", "도서관", "여행지"]
    for place in places:
        if place in transcript:
            details.append(f"장소: {place}")
    
    # 활동 관련
    activities = ["수영", "등산", "요리", "공부", "운동", "독서", "쇼핑", "영화", "게임"]
    for activity in activities:
        if activity in transcript:
            details.append(f"활동: {activity}")
    
    # 사람 관련
    people = ["가족", "친구", "부모님", "형제", "선생님", "동료"]
    for person in people:
        if person in transcript:
            details.append(f"사람: {person}")
    
    # 음식 관련
    foods = ["김치", "불고기", "비빔밥", "떡볶이", "치킨", "피자", "라면"]
    for food in foods:
        if food in transcript:
            details.append(f"음식: {food}")
    
    return details[:10]  # 최대 10개


def count_repetitions(transcript):
    """
    반복 패턴 개수 세기
    
    Args:
        transcript: 전사 텍스트
        
    Returns:
        int: 반복 개수
    """
    words = transcript.split()
    repetition_count = 0
    
    for i in range(len(words) - 1):
        if words[i] == words[i + 1]:
            repetition_count += 1
    
    return repetition_count


# === 메인 연구용 데이터 생성 함수 ===

def get_research_analysis_data(transcript, grammar_issues, duration_s, feedback_data, attempt_number=1):
    """
    채점자용 완전한 연구 분석 데이터 생성
    
    Args:
        transcript: STT 전사 텍스트
        grammar_issues: GPT가 찾은 문법 이슈들
        duration_s: 녹음 길이 (초)
        feedback_data: GPT 피드백 데이터
        attempt_number: 시도 번호 (1 or 2)
        
    Returns:
        dict: 완전한 연구 분석 데이터
    """
    # TOPIK 3영역 자동 점수 계산
    topik_scores = calculate_topik_3_scores(transcript, grammar_issues, duration_s, feedback_data)
    
    # 세부 분석들
    task_analysis = analyze_task_completion(transcript)
    content_richness = analyze_content_richness(transcript, feedback_data)
    discourse_org = analyze_discourse_organization(transcript)
    grammar_analysis = analyze_grammar_accuracy(transcript, grammar_issues)
    vocabulary_analysis = analyze_vocabulary_usage(transcript, feedback_data)
    delivery_indicators = analyze_speech_delivery_indicators(transcript, duration_s)
    
    # 발화전달력 세부 점수들
    pace_score = calculate_pace_appropriateness(transcript, duration_s)
    fluency_score = calculate_fluency_indicators(transcript)
    consistency_score = calculate_speech_consistency(transcript)
    
    return {
        # 기본 정보
        "session_id": st.session_state.session_id,
        "attempt": attempt_number,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": round(duration_s, 1),
        
        # === 1. 내용 및 과제 수행 ===
        "task_performance": {
            **task_analysis,
            "content_richness": content_richness,
            "discourse_organization": discourse_org
        },
        
        # === 2. 언어 사용 ===
        "language_use": {
            "grammar_accuracy": grammar_analysis,
            "vocabulary_usage": vocabulary_analysis,
            "language_appropriateness": {
                "speech_level": detect_speech_level(transcript),
                "consistency": check_speech_consistency(transcript),
                "formality_appropriate": True,  # 기본값
                "mixed_speech_levels": False    # 기본값
            }
        },
        
        # === 3. 발화 전달력 간접 지표 ===
        "speech_delivery_indicators": delivery_indicators,
        
        # === 4. TOPIK 3영역 종합 지표 ===
        "summary_indicators": {
            **topik_scores,
            "detailed_scores": {
                "task_completion": calculate_task_completion_detailed_score(task_analysis, content_richness),
                "content_richness": calculate_content_richness_detailed_score(content_richness),
                "language_accuracy": grammar_analysis["accuracy_score"] / 2,  # 5점 만점으로 변환
                "vocabulary_diversity": vocabulary_analysis["vocabulary_diversity"] * 5,  # 5점 만점으로 변환
                "pace_appropriateness": pace_score * 5,
                "fluency_indicators": fluency_score * 5
            },
            "grading_notes": generate_grading_notes(transcript, grammar_analysis, vocabulary_analysis, delivery_indicators),
            "attention_points": generate_attention_points(transcript, grammar_issues, duration_s, content_richness),
            "speech_delivery_breakdown": {
                "pace_score": round(pace_score * 5, 1),
                "fluency_score": round(fluency_score * 5, 1),
                "consistency_score": round(consistency_score * 5, 1),
                "delivery_explanation": generate_delivery_explanation(pace_score, fluency_score, consistency_score, delivery_indicators)
            }
        },
        
        # === 5. 원본 데이터 ===
        "raw_data": {
            "transcript": transcript,
            "gpt_feedback": feedback_data,
            "audio_file_path": f"session{CURRENT_SESSION}/{st.session_state.session_id}_attempt{attempt_number}.wav"
        }
    }


def generate_grading_summary_row(research_data_1, research_data_2=None):
    """
    채점자용 요약 테이블 행 생성 (CSV 컬럼 구조)
    
    Args:
        research_data_1: 1차 시도 연구 데이터
        research_data_2: 2차 시도 연구 데이터 (선택적)
        
    Returns:
        dict: CSV 컬럼 구조 데이터
    """
    summary = {
        "participant_id": st.session_state.session_id,
        "session": CURRENT_SESSION,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # 1차 시도 기본 정보
        "attempt1_duration": f"{research_data_1['duration_seconds']}s",
        "attempt1_word_count": research_data_1['task_performance']['content_richness']['total_words'],
        "attempt1_sentence_count": research_data_1['task_performance']['content_richness']['sentences_count'],
        
        # 1차 시도 TOPIK 자동 점수
        "attempt1_content_task_performance_auto": research_data_1['summary_indicators']['content_task_performance_score'],
        "attempt1_language_use_auto": research_data_1['summary_indicators']['language_use_score'],
        "attempt1_speech_delivery_auto": research_data_1['summary_indicators']['speech_delivery_score'],
        "attempt1_total_auto": research_data_1['summary_indicators']['overall_auto_score'] * 3,  # 15점 만점으로 변환
        
        # 1차 시도 수동 점수 (채점자 입력용)
        "attempt1_content_task_performance_rater1": "",
        "attempt1_content_task_performance_rater2": "",
        "attempt1_content_task_performance_average": "",
        "attempt1_language_use_rater1": "",
        "attempt1_language_use_rater2": "",
        "attempt1_language_use_average": "",
        "attempt1_speech_delivery_rater1": "",
        "attempt1_speech_delivery_rater2": "",
        "attempt1_speech_delivery_average": "",
        "attempt1_total_rater1": "",
        "attempt1_total_rater2": "",
        "attempt1_total_average": "",
        
        # 1차 시도 세부 참고 지표
        "attempt1_task_completion_details": generate_task_completion_summary(research_data_1),
        "attempt1_grammar_errors": research_data_1['language_use']['grammar_accuracy']['total_grammar_errors'],
        "attempt1_error_rate": f"{research_data_1['language_use']['grammar_accuracy']['error_rate']}%",
        "attempt1_vocab_diversity": f"{research_data_1['language_use']['vocabulary_usage']['vocabulary_diversity']*100:.1f}%",
        "attempt1_speech_level": research_data_1['language_use']['language_appropriateness']['speech_level'],
        "attempt1_pace_indicator": f"{research_data_1['speech_delivery_indicators']['fluency_indicators']['words_per_minute']} wpm",
        "attempt1_fluency_indicator": generate_fluency_summary(research_data_1),
        
        # 1차 시도 원본 데이터 참조
        "attempt1_transcript": research_data_1['raw_data']['transcript'],
        "attempt1_audio_file": research_data_1['raw_data']['audio_file_path']
    }
    
    # 2차 시도 데이터가 있으면 추가
    if research_data_2:
        summary.update({
            # 2차 시도 기본 정보
            "attempt2_duration": f"{research_data_2['duration_seconds']}s",
            "attempt2_word_count": research_data_2['task_performance']['content_richness']['total_words'],
            "attempt2_sentence_count": research_data_2['task_performance']['content_richness']['sentences_count'],
            
            # 2차 시도 TOPIK 자동 점수
            "attempt2_content_task_performance_auto": research_data_2['summary_indicators']['content_task_performance_score'],
            "attempt2_language_use_auto": research_data_2['summary_indicators']['language_use_score'],
            "attempt2_speech_delivery_auto": research_data_2['summary_indicators']['speech_delivery_score'],
            "attempt2_total_auto": research_data_2['summary_indicators']['overall_auto_score'] * 3,
            
            # 2차 시도 수동 점수 (채점자 입력용)
            "attempt2_content_task_performance_rater1": "",
            "attempt2_content_task_performance_rater2": "",
            "attempt2_content_task_performance_average": "",
            "attempt2_language_use_rater1": "",
            "attempt2_language_use_rater2": "",
            "attempt2_language_use_average": "",
            "attempt2_speech_delivery_rater1": "",
            "attempt2_speech_delivery_rater2": "",
            "attempt2_speech_delivery_average": "",
            "attempt2_total_rater1": "",
            "attempt2_total_rater2": "",
            "attempt2_total_average": "",
            
            # 2차 시도 세부 참고 지표
            "attempt2_task_completion_details": generate_task_completion_summary(research_data_2),
            "attempt2_grammar_errors": research_data_2['language_use']['grammar_accuracy']['total_grammar_errors'],
            "attempt2_error_rate": f"{research_data_2['language_use']['grammar_accuracy']['error_rate']}%",
            "attempt2_vocab_diversity": f"{research_data_2['language_use']['vocabulary_usage']['vocabulary_diversity']*100:.1f}%",
            "attempt2_speech_level": research_data_2['language_use']['language_appropriateness']['speech_level'],
            "attempt2_pace_indicator": f"{research_data_2['speech_delivery_indicators']['fluency_indicators']['words_per_minute']} wpm",
            "attempt2_fluency_indicator": generate_fluency_summary(research_data_2),
            
            # 2차 시도 원본 데이터 참조
            "attempt2_transcript": research_data_2['raw_data']['transcript'],
            "attempt2_audio_file": research_data_2['raw_data']['audio_file_path'],
            
            # 개선도 비교
            "improvement_content_task": research_data_2['summary_indicators']['content_task_performance_score'] - research_data_1['summary_indicators']['content_task_performance_score'],
            "improvement_language_use": research_data_2['summary_indicators']['language_use_score'] - research_data_1['summary_indicators']['language_use_score'],
            "improvement_speech_delivery": research_data_2['summary_indicators']['speech_delivery_score'] - research_data_1['summary_indicators']['speech_delivery_score'],
            "improvement_total": (research_data_2['summary_indicators']['overall_auto_score'] - research_data_1['summary_indicators']['overall_auto_score']) * 3
        })
    
    return summary


# === 보조 생성 함수들 ===

def detect_speech_level(transcript):
    """존댓말 수준 탐지"""
    if "습니다" in transcript or "입니다" in transcript:
        return "합니다체"
    elif "요" in transcript or "이에요" in transcript or "예요" in transcript:
        return "해요체"
    else:
        return "반말/기타"


def check_speech_consistency(transcript):
    """존댓말 일관성 확인"""
    formal_count = transcript.count("습니다") + transcript.count("입니다")
    informal_count = transcript.count("요") + transcript.count("이에요") + transcript.count("예요")
    
    if formal_count > 0 and informal_count > 0:
        return False  # 혼용
    return True


def calculate_task_completion_detailed_score(task_analysis, content_richness):
    """과제 완성도 세부 점수"""
    score = 1.0
    if task_analysis["topics_mentioned"]["both_topics_covered"]:
        score += 2.0
    if task_analysis["reasoning_provided"]["reasoning_completeness"] == "both":
        score += 1.5
    if content_richness["detail_count"] >= 3:
        score += 0.5
    return min(5.0, score)


def calculate_content_richness_detailed_score(content_richness):
    """내용 풍부함 세부 점수"""
    score = 1.0
    if content_richness["detail_count"] >= 5:
        score += 2.0
    elif content_richness["detail_count"] >= 3:
        score += 1.5
    elif content_richness["detail_count"] >= 1:
        score += 1.0
    
    if content_richness["vocabulary_diversity"] >= 0.6:
        score += 1.0
    elif content_richness["vocabulary_diversity"] >= 0.5:
        score += 0.5
    
    return min(5.0, score)


def generate_grading_notes(transcript, grammar_analysis, vocabulary_analysis, delivery_indicators):
    """채점자 참고사항 생성"""
    notes = []
    
    # 과제 수행 관련
    task_analysis = analyze_task_completion(transcript)
    if task_analysis["topics_mentioned"]["both_topics_covered"]:
        notes.append("Both topics covered with clear reasons")
    
    # 어휘 다양성
    diversity = vocabulary_analysis["vocabulary_diversity"]
    if diversity >= 0.6:
        notes.append(f"Good vocabulary diversity ({diversity*100:.0f}%)")
    elif diversity >= 0.4:
        notes.append(f"Fair vocabulary diversity ({diversity*100:.0f}%)")
    
    # 문법 정확성
    error_rate = grammar_analysis["error_rate"]
    if error_rate <= 5:
        notes.append("Excellent grammar accuracy")
    elif error_rate <= 10:
        notes.append("Minor grammar errors but communication clear")
    else:
        notes.append("Several grammar errors present")
    
    # 존댓말 사용
    speech_level = detect_speech_level(transcript)
    if speech_level in ["합니다체", "해요체"]:
        notes.append("Appropriate speech level maintained")
    
    # 말하기 속도
    wpm = delivery_indicators["fluency_indicators"]["words_per_minute"]
    if 60 <= wpm <= 80:
        notes.append(f"Natural speaking pace ({wpm:.0f} wpm)")
    
    return notes


def generate_attention_points(transcript, grammar_issues, duration_s, content_richness):
    """주의사항 생성"""
    points = []
    
    # 문법 오류 예시
    if grammar_issues:
        for issue in grammar_issues[:2]:  # 최대 2개
            if isinstance(issue, str) and '|' in issue:
                parts = issue.split('|')
                if len(parts) >= 3:
                    error_type = parts[0].strip()
                    original = parts[1].strip()
                    fix = parts[2].strip()
                    if original and fix:
                        points.append(f"{error_type} error: {original} → {fix}")
    
    # 길이 평가
    if duration_s >= 90:
        points.append(f"Excellent length ({duration_s:.1f}s)")
    elif duration_s >= 60:
        points.append(f"Adequate length ({duration_s:.1f}s)")
    else:
        points.append(f"Too short ({duration_s:.1f}s)")
    
    # 세부사항 풍부함
    detail_count = content_richness["detail_count"]
    if detail_count >= 4:
        points.append("Rich personal details provided")
    elif detail_count >= 2:
        points.append("Some personal details provided")
    else:
        points.append("Limited personal details")
    
    # 망설임 패턴
    hesitations = analyze_speech_delivery_indicators(transcript, duration_s)["fluency_indicators"]["hesitation_markers"]
    if hesitations:
        points.append(f"Some hesitation markers present: {', '.join(hesitations[:3])}")
    
    return points


def generate_delivery_explanation(pace_score, fluency_score, consistency_score, delivery_indicators):
    """발화전달력 설명 생성"""
    wpm = delivery_indicators["fluency_indicators"]["words_per_minute"]
    hesitations = len(delivery_indicators["fluency_indicators"]["hesitation_markers"])
    
    explanation_parts = []
    
    # 속도 평가
    if pace_score >= 0.8:
        explanation_parts.append(f"Good pace ({wpm:.0f} wpm)")
    elif pace_score >= 0.6:
        explanation_parts.append(f"Fair pace ({wpm:.0f} wpm)")
    else:
        explanation_parts.append(f"Pace needs adjustment ({wpm:.0f} wpm)")
    
    # 유창성 평가
    if hesitations <= 2:
        explanation_parts.append("minor hesitations")
    elif hesitations <= 4:
        explanation_parts.append("some hesitations")
    else:
        explanation_parts.append("frequent hesitations")
    
    # 일관성 평가
    if consistency_score >= 0.8:
        explanation_parts.append("consistent flow")
    else:
        explanation_parts.append("inconsistent flow")
    
    return ", ".join(explanation_parts)


def generate_task_completion_summary(research_data):
    """과제 완성도 요약"""
    task_perf = research_data['task_performance']
    topics = task_perf['topics_mentioned']
    reasoning = task_perf['reasoning_provided']
    
    summary_parts = []
    
    if topics['both_topics_covered']:
        summary_parts.append("양 주제 완료")
    elif topics['summer_vacation'] or topics['korea_plans']:
        summary_parts.append("한 주제만 완료")
    else:
        summary_parts.append("주제 불완전")
    
    if reasoning['reasoning_completeness'] == "both":
        summary_parts.append("이유 제시")
    elif reasoning['reasoning_completeness'] == "partial":
        summary_parts.append("일부 이유 제시")
    else:
        summary_parts.append("이유 부족")
    
    return ", ".join(summary_parts)


def generate_fluency_summary(research_data):
    """유창성 요약"""
    delivery = research_data['speech_delivery_indicators']
    hesitations = len(delivery['fluency_indicators']['hesitation_markers'])
    repetitions = delivery['fluency_indicators']['repetition_count']
    
    if hesitations <= 1 and repetitions == 0:
        return "매우 유창"
    elif hesitations <= 3 and repetitions <= 1:
        return f"망설임 {hesitations}회, 반복 {repetitions}회"
    else:
        return f"망설임 {hesitations}회, 반복 {repetitions}회 (개선 필요)"