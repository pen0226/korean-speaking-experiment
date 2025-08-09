"""
save_reference_score.py
TOPIK 참고용 점수 저장 모듈 (홀리스틱 루브릭 - 채점자 감각 기반 + 이유 컬럼 추가)
"""

import pandas as pd
import os
import re
from datetime import datetime
from config import KST

def calculate_content_task_score_holistic(transcript):
    """
    내용 및 과제 수행 점수 계산 (Task Completion Check 반영 - 홀리스틱 방식 1-5점 + 이유)
    
    Args:
        transcript: STT 전사 텍스트
        
    Returns:
        tuple: (점수, 이유) - (int, str)
    """
    if not transcript or not transcript.strip():
        return 1, "No meaningful content detected"
    
    # 과거 방학 체크 (더 정확한 키워드)
    past_keywords = ["지난", "작년", "여름", "겨울", "방학", "휴가", "여행", "갔어요", "했어요", "먹었어요", "봤어요", "놀았어요"]
    past_mentioned = sum(1 for k in past_keywords if k in transcript)
    
    # 미래 계획 체크 (더 정확한 키워드)
    future_keywords = ["다음", "내년", "할 거예요", "갈 거예요", "하려고", "계획", "하고 싶어요", "갈 예정", "할 계획"]
    future_mentioned = sum(1 for k in future_keywords if k in transcript)
    
    # 이유 체크
    reason_keywords = ["왜냐하면", "때문에", "해서", "좋아해서", "싶어서", "위해서", "재미있어서", "배우고 싶어서"]
    reason_mentioned = any(k in transcript for k in reason_keywords)
    
    word_count = len(transcript.split())
    sentence_count = len([s for s in transcript.split('.') if s.strip()])
    
    # 🆕 두 주제 모두 다뤘는지 명확히 체크
    both_topics = past_mentioned >= 2 and future_mentioned >= 2
    one_topic_only = (past_mentioned >= 2 and future_mentioned < 2) or (past_mentioned < 2 and future_mentioned >= 2)
    
    # 홀리스틱 평가 (Task Completion 중심)
    if both_topics and reason_mentioned and word_count >= 60:
        # 5점: 두 주제 완전히 다루고, 이유도 명확, 체계적 구성
        if word_count >= 80 and sentence_count >= 4:
            return 5, f"Both topics FULLY covered with clear reasons ({word_count} words, past:{past_mentioned} keywords, future:{future_mentioned} keywords)"
        # 4점: 두 주제 다루지만 한쪽이 약간 부족하거나 이유가 약함
        else:
            return 4, f"Both topics covered with reasons ({word_count} words, past:{past_mentioned}, future:{future_mentioned})"
    elif both_topics and word_count >= 40:
        # 3점: 두 주제 언급하지만 내용이 얕거나 구성이 어색
        reason_text = " with some reasons" if reason_mentioned else " but lacks clear reasons"
        return 3, f"Both topics mentioned but shallow content ({word_count} words){reason_text}"
    elif one_topic_only and word_count >= 20:
        # 2점: 한 주제만 제대로 다루거나 매우 짧음
        if past_mentioned >= 2:
            missing = "future plans (다음 방학 계획)"
        else:
            missing = "past vacation (지난 방학)"
        return 2, f"Only one topic covered adequately, MISSING {missing} ({word_count} words)"
    else:
        # 1점: 최소한의 응답만 시도 또는 두 주제 모두 미흡
        return 1, f"Task not completed - both topics missing or minimal ({word_count} words, past:{past_mentioned}, future:{future_mentioned})"


def calculate_language_use_score_holistic(transcript):
    """
    언어 사용 점수 계산 (홀리스틱 방식 1-5점 + 이유)
    
    Args:
        transcript: STT 전사 텍스트
        
    Returns:
        tuple: (점수, 이유) - (int, str)
    """
    if not transcript or not transcript.strip():
        return 1, "No language use detected"
    
    words = transcript.split()
    word_count = len(words)
    
    # 기본적인 문법 패턴 확인
    basic_patterns = ["했어요", "갔어요", "할 거예요", "이에요", "예요", "습니다", "해요", "와요", "봤어요"]
    pattern_count = sum(1 for pattern in basic_patterns if pattern in transcript)
    
    # 어휘 다양성 확인
    unique_words = set(words)
    diversity_ratio = len(unique_words) / word_count if word_count > 0 else 0
    
    # 홀리스틱 평가 (전체적 인상 기반)
    if word_count >= 60 and pattern_count >= 4 and diversity_ratio >= 0.75:
        # 5점: 문법 정확하고 어휘 풍부, 자연스러운 표현
        return 5, f"Accurate grammar with rich vocabulary and natural expressions ({word_count} words, {pattern_count} patterns, {diversity_ratio:.2f} diversity)"
    elif word_count >= 50 and pattern_count >= 3 and diversity_ratio >= 0.65:
        # 4점: 대체로 정확하지만 몇 가지 실수
        return 4, f"Mostly accurate with minor mistakes ({word_count} words, {pattern_count} patterns, {diversity_ratio:.2f} diversity)"
    elif word_count >= 30 and pattern_count >= 2 and diversity_ratio >= 0.50:
        # 3점: 의사소통 가능하지만 문법/어휘 오류 눈에 띔
        return 3, f"Communicable but grammar/vocabulary errors noticeable ({word_count} words, {pattern_count} patterns, {diversity_ratio:.2f} diversity)"
    elif word_count >= 20 and pattern_count >= 1:
        # 2점: 기본 의사소통 가능하지만 오류 많음
        return 2, f"Basic communication possible but many errors ({word_count} words, {pattern_count} patterns)"
    else:
        # 1점: 매우 기초적, 오류로 인해 이해 어려움
        return 1, f"Very basic, errors hinder understanding ({word_count} words, {pattern_count} patterns)"


def calculate_delivery_score_holistic(transcript, duration):
    """
    발화 전달력 점수 계산 (홀리스틱 방식 1-5점 + 이유) - 60초/70초 기준
    
    Args:
        transcript: STT 전사 텍스트
        duration: 발화 길이 (초)
        
    Returns:
        tuple: (점수, 이유) - (int, str)
    """
    if not transcript or not transcript.strip() or duration <= 0:
        return 1, "No delivery detected or invalid duration"
    
    word_count = len(transcript.split())
    
    # 🔥 핵심: 60초 미만은 최대 2점만 가능
    if duration < 60:
        if duration >= 45:
            return 2, f"Length insufficient for higher scores ({duration:.1f}s, 45-60s range, max 2 points)"
        else:
            return 1, f"Extremely short delivery ({duration:.1f}s, under 45s)"
    
    # 60초 이상부터 3-5점 가능
    words_per_minute = (word_count / duration) * 60 if duration > 0 else 0
    
    # 문장 완성도 추정 (STT 기반)
    sentences = transcript.count('.') + transcript.count('!') + transcript.count('?')
    if sentences == 0:  # 문장 부호가 없으면 어미로 추정
        sentences = len([s for s in transcript.split() if s.endswith(('요', '다', '까', '어요', '아요'))])
    
    # 홀리스틱 평가
    if duration >= 70:
        # 70초 이상: 4-5점 가능
        if words_per_minute >= 60 and sentences >= 4 and word_count >= 60:
            # 5점: 충분한 길이, 유창하고 자연스러움
            return 5, f"Sufficient length, fluent and natural ({duration:.1f}s, {words_per_minute:.1f} wpm, {sentences} sentences)"
        else:
            # 4점: 충분한 길이, 약간의 망설임은 있지만 전반적으로 자연스러움
            return 4, f"Sufficient length, minor hesitation but generally natural ({duration:.1f}s, {words_per_minute:.1f} wpm)"
    else:
        # 60-70초: 3점
        # 3점: 기본 요구 충족, 내용은 전달되지만 어색함이나 짧은 멈춤
        return 3, f"Adequate length but some awkwardness or short pauses ({duration:.1f}s, 60-70s range)"


def calculate_total_topik_score(content_score, language_score, delivery_score):
    """
    전체 TOPIK 점수 계산 (단순 합산)
    
    Args:
        content_score: 내용 점수 (1-5)
        language_score: 언어 점수 (1-5)
        delivery_score: 전달력 점수 (1-5)
        
    Returns:
        int: 전체 점수 (3-15점)
    """
    return content_score + language_score + delivery_score


def save_reference_score(session_id, attempt, transcript, duration, timestamp=None):
    """
    TOPIK 참고용 점수 저장 (홀리스틱 루브릭 적용 + 이유 컬럼 추가)
    
    ===== EXCEL 데이터 구조 문서화 =====
    이 함수는 TOPIK 기반 참고용 점수를 Excel 파일로 저장합니다.
    파일명 형식: reference_scores_{timestamp}.xlsx
    
    📊 Excel 컬럼 구조:
    
    1. 기본 정보:
       - session_id: 세션 고유번호 (CSV 파일과 연결 키)
       - attempt: 시도 번호 (1=첫번째 녹음, 2=두번째 녹음)
       - transcript: STT 전사 텍스트 (점수 산정 근거)
       - duration_s: 녹음 길이 (초, 60초 미만은 점수 제한)
       - timestamp: 점수 생성 시각
    
    2. TOPIK 3영역 홀리스틱 점수 (각 1-5점):
       - topik_content_task_score_auto: 내용 및 과제 수행 점수
         → 여름방학+한국계획 두 주제 모두 다뤘는지, 이유 설명했는지 평가
       - topik_language_use_score_auto: 언어 사용 점수  
         → 문법 정확성, 어휘 다양성, 자연스러운 표현 종합 평가
       - topik_delivery_score(stt)_auto: 전달력 점수 (STT 기반)
         → 발화 길이, 유창성, 완성도 종합 평가 (60초 미만은 최대 2점)
    
    3. 점수 산정 이유 (자동 생성):
       - topik_content_task_reason: 내용 점수 이유 설명
       - topik_language_use_reason: 언어 사용 점수 이유 설명  
       - topik_delivery_reason: 전달력 점수 이유 설명
    
    4. 총점:
       - topik_total_score_auto: 3영역 단순 합산 (3-15점)
    
    🎯 점수 기준 (홀리스틱 루브릭):
    - 5점: 매우 우수 (면접 준비 완료 수준)
    - 4점: 우수 (약간의 개선으로 면접 준비 가능)
    - 3점: 보통 (기본 요구사항 충족, 추가 연습 필요)
    - 2점: 미흡 (상당한 개선 필요)
    - 1점: 매우 미흡 (기초부터 다시 연습 필요)
    
    📈 활용 목적:
    - CSV의 AI 점수와 비교하여 자동채점 정확성 검증
    - 전문가 채점 기준과 비교 연구
    - 학습자 진단 및 레벨 평가 기준 개발
    - 피드백 시스템 개선을 위한 벤치마크 점수
    
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
        timestamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")  # 🔥 KST 추가
    
    # 홀리스틱 방식으로 3영역 점수 + 이유 계산
    content_task_score, content_task_reason = calculate_content_task_score_holistic(transcript)
    language_use_score, language_use_reason = calculate_language_use_score_holistic(transcript)
    delivery_score, delivery_reason = calculate_delivery_score_holistic(transcript, duration)
    total_score = calculate_total_topik_score(content_task_score, language_use_score, delivery_score)
    
    # timestamp 기반 파일명
    filename = f"data/reference_scores_{timestamp}.xlsx"
    
    # 새 데이터 (홀리스틱 루브릭 컬럼 + 이유 컬럼 + 상세 주석)
    new_data = {
        # === 기본 식별 정보 ===
        'session_id': session_id,              # 세션 고유번호 (CSV와 연결)
        'attempt': attempt,                    # 시도 번호 (1=피드백 전, 2=피드백 후)
        'transcript': transcript,              # STT 전사 텍스트 (채점 근거)
        'duration_s': duration,                # 녹음 길이 (초) - 60초 미만은 점수 제한
        'timestamp': timestamp,                # 점수 생성 시각 (파일명과 동일)
        
        # === TOPIK 3영역 홀리스틱 점수 (각 1-5점) ===
        'topik_content_task_score_auto': content_task_score,        # 내용 및 과제 수행 (여름방학+한국계획 주제 완성도)
        'topik_language_use_score_auto': language_use_score,        # 언어 사용 (문법 정확성 + 어휘 다양성)  
        'topik_delivery_score(stt)_auto': delivery_score,           # 전달력 (유창성 + 발화 길이, STT 기반)
        
        # === 점수 산정 이유 (자동 생성, 투명성 확보) ===
        'topik_content_task_reason': content_task_reason,           # 내용 점수 근거 설명
        'topik_language_use_reason': language_use_reason,           # 언어 사용 점수 근거 설명
        'topik_delivery_reason': delivery_reason,                   # 전달력 점수 근거 설명
        
        # === 총점 (연구 분석용) ===
        'topik_total_score_auto': total_score,                      # 3영역 단순 합산 (3-15점)
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
        
        # 홀리스틱 점수 로그 출력
        duration_status = "✅ 60s+" if duration >= 60 else "❌ <60s"
        quality_level = get_score_quality_description(total_score)
        
        print(f"✅ Holistic TOPIK scores with reasons saved: {filename}")
        print(f"   📊 Content: {content_task_score}/5 ({content_task_reason})")
        print(f"   📊 Language: {language_use_score}/5 ({language_use_reason})")
        print(f"   📊 Delivery: {delivery_score}/5 ({delivery_reason})")
        print(f"   🎯 Total: {total_score}/15 ({quality_level})")
        print(f"   ⏱️ Duration: {duration:.1f}s ({duration_status}), Words: {len(transcript.split())}")
        return filename
        
    except Exception as e:
        print(f"⚠️ Reference score save failed: {e}")
        return None


def get_score_quality_description(total_score):
    """
    총점에 따른 품질 설명 반환
    
    Args:
        total_score: 총 점수 (3-15)
        
    Returns:
        str: 품질 설명
    """
    if total_score >= 13:
        return "Excellent"
    elif total_score >= 11:
        return "Good"
    elif total_score >= 8:
        return "Fair"
    elif total_score >= 6:
        return "Poor"
    else:
        return "Very Poor"


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
    점수 요약 출력 (홀리스틱 루브릭 + 이유 반영)
    
    Args:
        session_id: 세션 ID
        attempt: 시도 번호
        scores: 점수 딕셔너리
    """
    total_score = scores.get('topik_total_score_auto', 0)
    quality_desc = get_score_quality_description(total_score)
    
    print(f"\n📊 Holistic TOPIK Scores with Reasons - {session_id} (Attempt {attempt})")
    print(f"   Content & Task: {scores.get('topik_content_task_score_auto', 0)}/5")
    print(f"   → {scores.get('topik_content_task_reason', 'No reason available')}")
    print(f"   Language Use: {scores.get('topik_language_use_score_auto', 0)}/5")
    print(f"   → {scores.get('topik_language_use_reason', 'No reason available')}")
    print(f"   Delivery (STT): {scores.get('topik_delivery_score(stt)_auto', 0)}/5")
    print(f"   → {scores.get('topik_delivery_reason', 'No reason available')}")
    print(f"   📈 Total: {total_score}/15 ({quality_desc})")
    print(f"   🎯 Holistic Rubric: Overall impression-based scoring with detailed reasoning")
    print("=" * 80)