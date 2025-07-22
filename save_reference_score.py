"""
save_reference_score.py
간단한 TOPIK 참고용 점수 저장 모듈
"""

import pandas as pd
import os
from datetime import datetime

def calculate_simple_topik_score(transcript, duration):
    """
    간단한 TOPIK 전체 점수 계산 (참고용)
    
    Args:
        transcript: STT 전사 텍스트
        duration: 길이 (초)
        
    Returns:
        float: TOPIK 전체 점수 (1-5점)
    """
    if not transcript or not transcript.strip():
        return 1.0
    
    score = 1.0  # 기본 1점
    
    # 1. 길이 기준 (0-2점)
    if duration >= 90:
        score += 2.0
    elif duration >= 60:
        score += 1.5
    elif duration >= 45:
        score += 1.0
    elif duration >= 30:
        score += 0.5
    
    # 2. 단어 수 기준 (0-1점)
    word_count = len(transcript.split())
    if word_count >= 80:
        score += 1.0
    elif word_count >= 60:
        score += 0.8
    elif word_count >= 40:
        score += 0.5
    elif word_count >= 20:
        score += 0.3
    
    # 3. 주제 완성도 기준 (0-1점)
    summer_keywords = ["여름", "방학", "휴가", "여행"]
    korea_keywords = ["한국", "계획", "할 거예요", "하려고"]
    
    summer_mentioned = any(keyword in transcript for keyword in summer_keywords)
    korea_mentioned = any(keyword in transcript for keyword in korea_keywords)
    
    if summer_mentioned and korea_mentioned:
        score += 1.0
    elif summer_mentioned or korea_mentioned:
        score += 0.5
    
    return min(5.0, round(score, 1))


def save_reference_score(session_id, attempt, transcript, duration, timestamp=None):
    """
    참고용 TOPIK 점수만 간단히 저장
    
    Args:
        session_id: 세션 ID
        attempt: 시도 번호 (1 or 2)
        transcript: 전사 텍스트
        duration: 길이 (초)
        timestamp: 타임스탬프 (선택적)
        
    Returns:
        str: 저장된 파일명
    """
    if not timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 간단한 TOPIK 점수 계산
    topik_score = calculate_simple_topik_score(transcript, duration)
    
    filename = f"data/reference_scores_{timestamp}.xlsx"
    
    # 새 데이터
    new_data = {
        'session_id': session_id,
        'attempt': attempt,
        'transcript': transcript,
        'duration_s': duration,
        'topik_overall_auto': topik_score,
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
        print(f"✅ Reference score saved: {filename}")
        return filename
        
    except Exception as e:
        print(f"⚠️ Reference score save failed: {e}")
        return None