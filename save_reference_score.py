"""
save_reference_score.py
TOPIK 참고용 점수 저장 모듈 (3영역 세부 채점 포함)
"""

import pandas as pd
import os
import re
from datetime import datetime

def calculate_content_task_score(transcript):
    """
    내용 및 과제 수행 점수 계산 (5점 만점)
    
    Args:
        transcript: STT 전사 텍스트
        
    Returns:
        int: 내용 및 과제 수행 점수 (1-5점)
    """
    if not transcript or not transcript.strip():
        return 1
    
    score = 1  # 기본 1점
    text = transcript.lower()
    
    # 1. 여름방학 주제 언급 (1점)
    summer_keywords = ["여름", "방학", "휴가", "여행"]
    summer_mentioned = any(keyword in transcript for keyword in summer_keywords)
    if summer_mentioned:
        score += 1
    
    # 2. 한국계획 주제 언급 (1점)
    korea_keywords = ["한국", "계획", "할 거예요", "하려고", "갈 거예요", "공부할", "배울"]
    korea_mentioned = any(keyword in transcript for keyword in korea_keywords)
    if korea_mentioned:
        score += 1
    
    # 3. 여름방학 이유 설명 (1점)
    reason_keywords = ["왜냐하면", "때문에", "해서", "좋아해서", "재미있어서", "아름다워서", "맛있어서"]
    summer_with_reason = summer_mentioned and any(keyword in transcript for keyword in reason_keywords)
    if summer_with_reason:
        score += 1
    
    # 4. 담화 구성 - 두 주제가 모두 언급되고 적절한 길이 (1점)
    if summer_mentioned and korea_mentioned and len(transcript.split()) >= 30:
        score += 1
    
    return min(5, score)


def calculate_language_use_score(transcript):
    """
    언어 사용 점수 계산 (5점 만점)
    
    Args:
        transcript: STT 전사 텍스트
        
    Returns:
        int: 언어 사용 점수 (1-5점)
    """
    if not transcript or not transcript.strip():
        return 1
    
    score = 1  # 기본 1점
    words = transcript.split()
    word_count = len(words)
    
    # 1. 기본 문법 정확성 추정 (2점) - 단어 수와 문장 완성도 기반
    if word_count >= 40:
        # 기본적인 문법 패턴 확인
        basic_patterns = ["했어요", "갔어요", "할 거예요", "이에요", "예요", "습니다"]
        pattern_count = sum(1 for pattern in basic_patterns if pattern in transcript)
        
        if pattern_count >= 3:  # 다양한 문법 패턴 사용
            score += 2
        elif pattern_count >= 1:  # 기본적인 문법 패턴 사용
            score += 1
    
    # 2. 어휘 정확성 및 다양성 (2점)
    if word_count >= 30:
        # 어휘 다양성 확인 (중복 단어 비율)
        unique_words = set(words)
        diversity_ratio = len(unique_words) / word_count
        
        if diversity_ratio >= 0.7:  # 높은 어휘 다양성
            score += 2
        elif diversity_ratio >= 0.5:  # 적당한 어휘 다양성
            score += 1
    
    return min(5, score)


def calculate_delivery_score(transcript, duration):
    """
    발화 전달력 점수 계산 (5점 만점) - STT 기반 추론
    
    Args:
        transcript: STT 전사 텍스트
        duration: 발화 길이 (초)
        
    Returns:
        int: 발화 전달력 점수 (1-5점)
    """
    if not transcript or not transcript.strip() or duration <= 0:
        return 1
    
    score = 1  # 기본 1점
    word_count = len(transcript.split())
    
    # 1. 발화 길이 (2점) - 60초 이상이면 모두 좋음
    if duration >= 60:
        score += 2
    elif duration >= 45:
        score += 1
    
    # 2. 유창성 - 분당 단어수 (2점)
    words_per_minute = (word_count / duration) * 60 if duration > 0 else 0
    
    if words_per_minute >= 60:  # 자연스러운 속도
        score += 2
    elif words_per_minute >= 40:  # 적당한 속도
        score += 1
    
    # 3. 명확성 추정 (1점) - STT 품질과 문장 완성도로 추론
    sentences = transcript.count('.') + transcript.count('!') + transcript.count('?')
    if sentences == 0:  # 문장 부호가 없으면 문장 길이로 추정
        sentences = len([s for s in transcript.split() if s.endswith(('요', '다', '까'))])
    
    # 적절한 문장 수와 길이
    if sentences >= 3 and word_count >= 30:
        score += 1
    
    return min(5, score)


def calculate_simple_topik_score(transcript, duration):
    """
    전체 TOPIK 점수 계산 (1-5점) - 3영역 평균 기반
    
    Args:
        transcript: STT 전사 텍스트
        duration: 길이 (초)
        
    Returns:
        float: TOPIK 전체 점수 (1-5점)
    """
    if not transcript or not transcript.strip():
        return 1.0
    
    # 3영역 점수 계산
    content_score = calculate_content_task_score(transcript)
    language_score = calculate_language_use_score(transcript)
    delivery_score = calculate_delivery_score(transcript, duration)
    
    # 가중 평균 (내용 40%, 언어 40%, 전달력 20%)
    overall_score = (content_score * 0.4) + (language_score * 0.4) + (delivery_score * 0.2)
    
    return round(overall_score, 1)


def save_reference_score(session_id, attempt, transcript, duration, timestamp=None):
    """
    TOPIK 참고용 점수 저장 (3영역 세부 점수 포함)
    
    Args:
        session_id: 세션 ID
        attempt: 시도 번호 (1 or 2)
        transcript: 전사 텍스트
        duration: 길이 (초)
        timestamp: 타임스탬프 (필수 - main.py에서 전달)
        
    Returns:
        str: 저장된 파일명
    """
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 3영역 세부 점수 계산
    content_task_score = calculate_content_task_score(transcript)
    language_use_score = calculate_language_use_score(transcript)
    delivery_score = calculate_delivery_score(transcript, duration)
    overall_score = calculate_simple_topik_score(transcript, duration)
    
    # timestamp 기반 파일명
    filename = f"data/reference_scores_{timestamp}.xlsx"
    
    # 새 데이터 (컬럼 순서 정리)
    new_data = {
        'session_id': session_id,
        'attempt': attempt,
        'transcript': transcript,
        'duration_s': duration,
        'topik_overall_auto': overall_score,
        'topik_content_task_score_auto': content_task_score,
        'topik_language_use_score_auto': language_use_score,
        'topik_delivery_score(stt)_auto': delivery_score,
        'timestamp': timestamp
    }
    
    # 파일 있으면 기존 데이터에 추가, 없으면 새로 생성
    try:
        os.makedirs("data", exist_ok=True)
        
        if os.path.exists(filename):
            df = pd.read_excel(filename)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        
        df.to_excel(filename, index=False)
        print(f"✅ Reference scores saved: {filename}")
        print(f"   📊 Content/Task: {content_task_score}/5, Language: {language_use_score}/5, Delivery: {delivery_score}/5, Overall: {overall_score}/5")
        return filename
        
    except Exception as e:
        print(f"⚠️ Reference score save failed: {e}")
        return None


def get_latest_reference_file(timestamp=None):
    """
    timestamp에 해당하는 reference 파일 경로 반환
    
    Args:
        timestamp: 타임스탬프
        
    Returns:
        str: 파일 경로 또는 None
    """
    if timestamp:
        filename = f"data/reference_scores_{timestamp}.xlsx"
        if os.path.exists(filename):
            return filename
    
    # timestamp가 없거나 파일이 없으면 가장 최신 파일 찾기
    import glob
    pattern = "data/reference_scores_*.xlsx"
    files = glob.glob(pattern)
    if files:
        return max(files, key=os.path.getctime)
    
    return None


def display_score_summary(session_id, attempt, scores):
    """
    점수 요약 출력 (디버깅용)
    
    Args:
        session_id: 세션 ID
        attempt: 시도 번호
        scores: 점수 딕셔너리
    """
    print(f"\n📊 TOPIK Reference Scores - {session_id} (Attempt {attempt})")
    print(f"   Overall: {scores.get('topik_overall_auto', 0)}/5")
    print(f"   Content & Task: {scores.get('topik_content_task_score_auto', 0)}/5")
    print(f"   Language Use: {scores.get('topik_language_use_score_auto', 0)}/5")
    print(f"   Delivery (STT): {scores.get('topik_delivery_score(stt)_auto', 0)}/5")
    print("=" * 50)