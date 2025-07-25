"""
feedback.py
GPT를 이용한 한국어 학습 피드백 생성 (이중 평가 시스템: 연구용 + 학생용)
"""

import openai
import json
import time
import re  # 추가: Simple explanation 레이블 제거용
import streamlit as st
from config import (
    OPENAI_API_KEY, 
    EXPERIMENT_QUESTION, 
    GPT_SYSTEM_PROMPT, 
    STT_RUBRIC,
    FEEDBACK_PROMPT_TEMPLATE,
    IMPROVEMENT_PROMPT_TEMPLATE,
    FALLBACK_FEEDBACK_DATA,
    FALLBACK_IMPROVEMENT_DATA,
    GRAMMAR_ERROR_TYPES,
    FEEDBACK_LEVEL,
    GPT_FEEDBACK_MAX_TOKENS,
    GPT_FEEDBACK_MAX_CHARS
)


# === 간소화된 오류 분류 상수 ===
INDIVIDUAL_PARTICLES = ["을", "를", "은", "는", "이", "가", "에서", "에게", "에", "와", "과", "의", "로", "으로"]
TIME_INDICATORS = ["어제", "내일", "지금", "오늘", "내년", "작년", "다음 주", "지난주", "방금", "나중에"]
VERB_ENDINGS = ["예요", "이에요", "아요", "어요", "습니다", "세요", "ㅂ니다", "다", "ㄴ다", "는다"]
TENSE_MARKERS = ["했어요", "할 거예요", "하고 있어요", "한 적이", "했었어요", "할게요"]

# 초급 학습자 자주 틀리는 패턴
COMMON_BEGINNER_ERRORS = {
    "좋아요_좋아해요": {"pattern": "좋아요", "correct": "좋아해요", "type": "Verb Ending"},
    "입니다_이에요": {"pattern": "입니다", "correct": "이에요", "type": "Verb Ending"},
    "전공이에요_전공해요": {"pattern": "전공이에요", "correct": "전공해요", "type": "Verb Ending"}
}


# === 이중 평가 시스템: 연구용 함수들 ===

def count_grammar_errors(grammar_issues):
    """
    GPT가 찾은 실제 문법 오류만 정확히 카운팅
    
    Args:
        grammar_issues: GPT가 생성한 문법 이슈 리스트
        
    Returns:
        int: 실제 유효한 문법 오류 개수
    """
    valid_errors = 0
    for issue in grammar_issues:
        if isinstance(issue, str) and '|' in issue:
            # "error_type|original|fix|explanation" 형식 검증
            parts = issue.split('|')
            if len(parts) >= 3 and parts[1].strip() and parts[2].strip():
                valid_errors += 1
    return valid_errors


def get_research_scores(transcript, grammar_issues, duration_s):
    """
    연구용 정확한 수치 계산 (논문용) - 60-120초 기준으로 수정
    - Accuracy: 오류율 기반 (10 - (error_rate / 10))
    - Fluency: 단어수 기반 (word_count / 120 * 10) - 1.5분 기준으로 120단어
    
    Args:
        transcript: STT 전사 텍스트
        grammar_issues: GPT가 찾은 문법 이슈들
        duration_s: 녹음 길이 (초)
        
    Returns:
        dict: 연구용 점수 데이터
    """
    # 기본값 설정
    if not transcript or not isinstance(transcript, str):
        transcript = ""
    
    if not grammar_issues or not isinstance(grammar_issues, list):
        grammar_issues = []
    
    if not duration_s or not isinstance(duration_s, (int, float)):
        duration_s = 0.0
    
    # 단어 수 계산 (공백 기준)
    total_words = len(transcript.split()) if transcript.strip() else 0
    
    # 실제 문법 오류 개수 계산
    error_count = count_grammar_errors(grammar_issues)
    
    # 오류율 계산 (0으로 나누기 방지)
    if total_words > 0:
        error_rate = (error_count / total_words) * 100
    else:
        error_rate = 0.0
    
    # Accuracy Score: 10에서 오류율의 1/10을 뺀 값 (최소 0, 최대 10)
    accuracy_score = max(0, min(10, 10 - (error_rate / 10)))
    
    # 🔥 Fluency Score: 120단어를 기준으로 10점 만점 (1.5분 기준으로 수정)
    fluency_score = max(0, min(10, (total_words / 120) * 10))
    
    return {
        "accuracy_score": round(accuracy_score, 1),
        "fluency_score": round(fluency_score, 1),
        "error_rate": round(error_rate, 2),
        "word_count": total_words,
        "duration_s": round(duration_s, 1),
        "error_count": error_count
    }


def get_student_feedback(transcript, research_scores, original_feedback):
    """
    학생용 격려적 피드백 생성 (원본 GPT 피드백 유지)
    - 원본 GPT 피드백을 그대로 유지하여 교육적 가치 보존
    - 연구용 점수는 백그라운드에서만 계산
    
    Args:
        transcript: STT 전사 텍스트
        research_scores: 연구용 점수 데이터
        original_feedback: GPT가 생성한 원본 피드백
        
    Returns:
        dict: 학생용 피드백 데이터 (원본 GPT 피드백 유지)
    """
    # 기본값 처리
    if not original_feedback or not isinstance(original_feedback, dict):
        original_feedback = get_fallback_feedback()
    
    if not research_scores or not isinstance(research_scores, dict):
        research_scores = {
            "accuracy_score": 5.0,
            "fluency_score": 5.0,
            "error_rate": 20.0,
            "word_count": 60,
            "duration_s": 60.0,
            "error_count": 3
        }
    
    # 🎯 원본 GPT 피드백을 그대로 반환 (교육적 가치 유지)
    # 연구용 점수는 이미 st.session_state.research_scores에 저장되어 있음
    
    # 원본 피드백 그대로 사용 (GPT가 생성한 교육적 피드백 유지)
    student_feedback = original_feedback.copy()
    
    # 연구용 메타데이터만 추가 (학생에게는 보이지 않음)
    student_feedback.update({
        "_research_metadata": {
            "accuracy_score": research_scores.get("accuracy_score", 0),
            "fluency_score": research_scores.get("fluency_score", 0),
            "error_rate": research_scores.get("error_rate", 0),
            "word_count": research_scores.get("word_count", 0),
            "duration_s": research_scores.get("duration_s", 0),
            "dual_evaluation_applied": True
        }
    })
    
    return student_feedback


def generate_encouraging_feedback_message(word_count, error_rate, duration_s, score):
    """격려적인 피드백 메시지 생성 (60-120초 기준)"""
    messages = []
    
    # 🔥 길이 피드백 (60-120초 기준으로 수정)
    if duration_s >= 90:
        messages.append(f"Excellent! You spoke for {duration_s:.1f} seconds - perfect length!")
    elif duration_s >= 75:
        messages.append(f"Good job speaking for {duration_s:.1f} seconds! Try to reach 90+ seconds next time.")
    else:
        messages.append(f"You spoke for {duration_s:.1f} seconds. Aim for at least 90 seconds to score higher!")
    
    # 정확성 피드백
    if error_rate <= 5:
        messages.append("Your grammar is very accurate!")
    elif error_rate <= 15:
        messages.append("Good grammar overall with room for improvement.")
    else:
        messages.append("Focus on grammar practice - you're learning!")
    
    # 🔥 단어 수 피드백 (60-120초 기준으로 수정)
    if word_count >= 120:
        messages.append(f"Great vocabulary use with {word_count} words!")
    elif word_count >= 80:
        messages.append(f"Good speaking volume with {word_count} words.")
    else:
        messages.append(f"Try to add more details - you used {word_count} words.")
    
    return " ".join(messages)


def generate_improvement_areas(research_scores, original_feedback):
    """개선 영역 제안 생성 (60-120초 기준)"""
    areas = []
    
    # 🔥 Duration 기반 (60-120초 기준으로 수정)
    if research_scores.get("duration_s", 0) < 90:
        areas.append("Speaking length - aim for 90+ seconds")
    
    # 오류율 기반
    if research_scores.get("error_rate", 0) > 15:
        areas.append("Grammar accuracy")
    
    # 🔥 단어 수 기반 (60-120초 기준으로 수정)
    if research_scores.get("word_count", 0) < 60:
        areas.append("Adding more personal details")
    
    # 원본 피드백에서 추가 영역
    if original_feedback.get("grammar_issues"):
        areas.append("Particle usage")
    
    if original_feedback.get("content_expansion_suggestions"):
        areas.append("Content expansion")
    
    return areas[:3]  # 최대 3개


def generate_encouragement_message(score):
    """점수 기반 격려 메시지"""
    if score >= 8:
        return "Outstanding work! You're interview-ready! 🌟"
    elif score >= 7:
        return "Great progress! You're almost there! 💪"
    elif score >= 6:
        return "Good job! Keep practicing and you'll improve! 🚀"
    elif score >= 5:
        return "You're learning well! Every practice helps! 📚"
    else:
        return "Great start! Keep practicing - you can do it! 🌱"


def generate_duration_feedback(duration_s):
    """녹음 길이 기반 피드백 (60-120초 기준)"""
    if duration_s >= 90:
        return f"Perfect! {duration_s:.1f} seconds meets the 60-120 seconds goal!"
    elif duration_s >= 75:
        return f"Good length at {duration_s:.1f} seconds. Try for 90+ next time!"
    elif duration_s >= 60:
        return f"Fair length at {duration_s:.1f} seconds. Aim for 90+ seconds!"
    else:
        return f"Too short at {duration_s:.1f} seconds. Much more needed for good score!"


def generate_accuracy_feedback(error_rate):
    """정확성 기반 피드백"""
    if error_rate <= 5:
        return "Excellent grammar accuracy!"
    elif error_rate <= 10:
        return "Good accuracy with minor errors."
    elif error_rate <= 20:
        return "Fair accuracy - focus on common mistakes."
    else:
        return "Work on grammar basics - you're improving!"


def generate_fluency_feedback(word_count):
    """유창성 기반 피드백 (60-120초 기준)"""
    if word_count >= 120:
        return f"Excellent fluency with {word_count} words!"
    elif word_count >= 90:
        return f"Good fluency with {word_count} words."
    elif word_count >= 60:
        return f"Fair fluency with {word_count} words - add more details!"
    else:
        return f"Work on speaking more - only {word_count} words used."


# === 기존 함수들 (수정 없음) ===

def split_korean_sentences(text):
    """
    한국어 문장을 적절히 분할
    
    Args:
        text: 분할할 텍스트
        
    Returns:
        list: 분할된 문장들
    """
    # 한국어 문장 구분자: ., !, ?, 요/어요/습니다 뒤의 공백
    pattern = r'([.!?]|(?:요|어요|습니다|세요|해요|이에요|예요)\s*)'
    sentences = re.split(pattern, text)
    
    # 분할된 부분을 다시 조합
    result = []
    for i in range(0, len(sentences)-1, 2):
        if i+1 < len(sentences):
            sentence = sentences[i] + sentences[i+1]
            if sentence.strip():
                result.append(sentence.strip())
    
    # 마지막 부분이 남아있다면 추가
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())
    
    return [s for s in result if len(s.strip()) > 3]  # 너무 짧은 문장 제외


def preprocess_long_transcript_fallback(transcript, max_chars=GPT_FEEDBACK_MAX_CHARS):
    """
    문자 수 기반 긴 텍스트 처리
    
    Args:
        transcript: 전사된 텍스트
        max_chars: 최대 문자 수
        
    Returns:
        str: 처리된 텍스트
    """
    if len(transcript) <= max_chars:
        return transcript
    
    # 문장 단위로 자르기 시도
    sentences = split_korean_sentences(transcript)
    
    if not sentences:
        # 문장 분할 실패시 적당한 위치에서 자르기
        cutoff = transcript.rfind(' ', 0, max_chars)
        if cutoff == -1:
            cutoff = max_chars
        return transcript[:cutoff]
    
    # 문장 단위로 최대한 포함
    result = ""
    for sentence in sentences:
        temp = result + " " + sentence if result else sentence
        if len(temp) <= max_chars:
            result = temp
        else:
            break
    
    return result if result else sentences[0][:max_chars]


def preprocess_long_transcript(transcript):
    """
    긴 전사 텍스트 전처리 메인 함수 (문자 수 기반만 사용)
    
    Args:
        transcript: 전사된 텍스트
        
    Returns:
        str: 처리된 텍스트
    """
    if not transcript or len(transcript.strip()) == 0:
        return transcript
    
    # 간단한 정리
    cleaned = transcript.strip()
    
    # 문자 수 기반 처리 (tiktoken 제거)
    if len(cleaned) <= GPT_FEEDBACK_MAX_CHARS:
        return cleaned
    else:
        # 긴 텍스트는 문자 수 기반으로 문장 단위로 자르기
        return preprocess_long_transcript_fallback(cleaned)


# === 개선된 오류 분류 함수 (3개 주요 유형 + 기타) ===
def classify_error_type(issue_text):
    """
    피드백 텍스트를 분석하여 4개 오류 타입 중 하나 반환
    - 3개 주요 유형: Particle, Verb Ending, Verb Tense (모두 동등하게 중요)
    - 기타: Others (모든 다른 문법 오류)
    
    Args:
        issue_text: 분석할 피드백 텍스트
        
    Returns:
        str: 분류된 오류 타입 (Particle, Verb Ending, Verb Tense, 또는 None)
              None인 경우 호출부에서 "Others"로 분류됨
    """
    issue_lower = issue_text.lower()
    
    # Original과 Fix 부분 추출 (개선된 파싱)
    original_text = ""
    fix_text = ""
    
    # GPT 피드백에서 original과 fix 추출
    if "❌" in issue_text and "✅" in issue_text:
        try:
            # ❌ 가족이랑 부산여행 갔다. ✅ 가족이랑 부산여행 갔어요. 형태
            parts = issue_text.split("❌")[1].split("✅")
            if len(parts) >= 2:
                original_text = parts[0].strip().strip(".")
                fix_text = parts[1].split("💡")[0].strip().strip(".")
        except:
            pass
    elif "Original:" in issue_text and "→" in issue_text:
        try:
            original_text = issue_text.split("Original:")[1].split("→")[0].strip().strip("'\"")
            if "Fix:" in issue_text:
                fix_text = issue_text.split("Fix:")[1].split("💡")[0].strip().strip("'\"")
            else:
                fix_text = issue_text.split("→")[1].split("💡")[0].strip().strip("'\"")
        except:
            pass
    
    print(f"🔍 Debug - Original: '{original_text}' | Fix: '{fix_text}'")  # 디버깅용
    
    # 1. 초급자 자주 틀리는 패턴 우선 확인
    for pattern_info in COMMON_BEGINNER_ERRORS.values():
        if pattern_info["pattern"] in original_text and pattern_info["correct"] in fix_text:
            print(f"✅ {pattern_info['type']} (common pattern): {pattern_info['pattern']} → {pattern_info['correct']}")
            return pattern_info["type"]
    
    # 2. Particle 확인
    for particle in INDIVIDUAL_PARTICLES:
        if f"'{particle}'" in issue_text or f" {particle} " in issue_text:
            print(f"✅ Particle detected: keyword '{particle}'")
            return "Particle"
        if original_text and fix_text:
            if particle in fix_text and particle not in original_text:
                print(f"✅ Particle detected: added '{particle}'")
                return "Particle"
    
    if "particle" in issue_lower or "조사" in issue_text:
        print(f"✅ Particle detected: keyword")
        return "Particle"
    
    # 3. Verb Tense 확인 (시간 표현이 있는 경우)
    for indicator in TIME_INDICATORS + TENSE_MARKERS:
        if indicator in issue_text:
            print(f"✅ Verb Tense detected: time indicator '{indicator}'")
            return "Verb Tense"
    
    if "tense" in issue_lower or "시제" in issue_text or "past tense" in issue_lower:
        print(f"✅ Verb Tense detected: keyword")
        return "Verb Tense"
    
    # 4. Verb Ending 확인
    for ending in VERB_ENDINGS:
        if ending in issue_text:
            print(f"✅ Verb Ending detected: ending '{ending}'")
            return "Verb Ending"

    # 반말 → 존댓말 패턴 확인 (정확한 어미 확인)
    if original_text and fix_text:
        informal_endings = ["다", "ㄴ다", "는다", "냐", "나", "지", "야"]
        formal_endings = ["요", "습니다", "세요", "어요", "아요", "이에요", "예요"]
        
        # 원본이 반말로 끝나고, 수정본이 존댓말로 끝나는 경우
        original_has_informal = any(original_text.endswith(ending) for ending in informal_endings)
        fix_has_formal = any(fix_text.endswith(ending) for ending in formal_endings)
        
        if original_has_informal and fix_has_formal:
            print(f"✅ Verb Ending detected: {original_text} → {fix_text} (informal to formal)")
            return "Verb Ending"

    if "ending" in issue_lower or "verb form" in issue_lower or "어미" in issue_text:
        print(f"✅ Verb Ending detected: keyword")
        return "Verb Ending"
    
    # 🔥 3개 주요 유형에 해당하지 않으면 None 반환 (호출부에서 "Others"로 분류됨)
    print(f"❓ No specific type detected, will be classified as 'Others'")
    return None


# === 🔥 스마트한 중복 필터링 함수 (vs 방식으로 수정됨) ===
def extract_grammar_corrections(grammar_issues):
    """
    문법 피드백에서 실제 수정 내용 추출
    
    Args:
        grammar_issues: 문법 이슈 리스트
        
    Returns:
        list: (original, fix) 튜플들의 리스트
    """
    corrections = []
    
    for issue in grammar_issues:
        if isinstance(issue, str) and '|' in issue:
            parts = issue.split('|')
            if len(parts) >= 3:
                original = parts[1].strip().strip("'\"")
                fix = parts[2].strip().strip("'\"")
                if original and fix:
                    corrections.append((original.lower(), fix.lower()))
    
    return corrections


def extract_vs_words_from_vocabulary(vocab_suggestions):
    """
    vs 방식 어휘 제안에서 단어들 추출
    
    Args:
        vocab_suggestions: 어휘 제안 리스트 (vs 방식)
        
    Returns:
        list: [(word_a, word_b), ...] 형태의 단어 쌍들
    """
    vs_pairs = []
    
    for suggestion in vocab_suggestions:
        if "❓ **" in suggestion and " vs " in suggestion:
            try:
                # ❓ **공부하다 vs 배우다** 부분 추출
                lines = suggestion.replace('\\n', '\n').split('\n')
                for line in lines:
                    if line.startswith('❓ **') and ' vs ' in line:
                        title_text = line.replace('❓ **', '').replace('**', '').strip()
                        if ' vs ' in title_text:
                            words = title_text.split(' vs ')
                            if len(words) >= 2:
                                word_a = words[0].strip()
                                word_b = words[1].strip()
                                vs_pairs.append((word_a.lower(), word_b.lower()))
                        break
            except:
                continue
    
    return vs_pairs


def filter_grammar_from_vocabulary(vocab_suggestions, grammar_issues):
    """
    🔥 스마트한 중복 필터링: 실제 문법 피드백과 중복되는 어휘 팁만 제거 (vs 방식)
    
    Args:
        vocab_suggestions: 어휘 제안 리스트 (vs 방식)
        grammar_issues: 문법 이슈 리스트
        
    Returns:
        list: 중복이 제거된 어휘 제안 리스트
    """
    # 문법 피드백에서 실제 수정된 내용들 추출
    grammar_corrections = extract_grammar_corrections(grammar_issues)
    
    # vs 어휘 제안에서 단어 쌍들 추출
    vs_word_pairs = extract_vs_words_from_vocabulary(vocab_suggestions)
    
    filtered = []
    for vocab_tip in vocab_suggestions:
        is_duplicate = False
        
        # 이 어휘 팁의 단어 쌍 찾기
        current_vs_pairs = extract_vs_words_from_vocabulary([vocab_tip])
        
        for word_a, word_b in current_vs_pairs:
            # 문법 수정 내용과 비교
            for grammar_old, grammar_new in grammar_corrections:
                # 어휘 팁의 단어들이 문법 수정에 포함되어 있는지 확인
                if ((word_a in grammar_old or grammar_old in word_a) and 
                    (word_b in grammar_new or grammar_new in word_b)) or \
                   ((word_b in grammar_old or grammar_old in word_b) and 
                    (word_a in grammar_new or grammar_new in word_a)):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                break
        
        # 중복이 아닌 경우만 포함
        if not is_duplicate:
            filtered.append(vocab_tip)
    
    return filtered


def get_default_vocabulary_suggestions():
    """
    🔥 vs 방식 기본 어휘 제안 (단어 비교 교육)
    """
    return [
        "❓ **공부하다 vs 배우다**\\n💡 공부하다: Academic studying or reviewing material at a desk\\n💡 배우다: Learning new skills or acquiring new knowledge\\n🟢 시험을 위해 공부해요 (I study for exams) / 한국어를 배우고 있어요 (I'm learning Korean)\\n📝 Use '배우다' for new skills, '공부하다' for reviewing",
        "❓ **좋다 vs 좋아하다**\\n💡 좋다: Adjective - something is good (state/quality)\\n💡 좋아하다: Verb - to like something (preference)\\n🟢 날씨가 좋아요 (The weather is nice) / 음악을 좋아해요 (I like music)\\n📝 Use '이/가 좋다' vs '을/를 좋아하다'"
    ]


def ensure_required_fields(data, required_fields):
    """필수 필드가 누락된 경우 기본값으로 보완"""
    for field, default_value in required_fields.items():
        if field not in data or not data[field]:
            data[field] = default_value
    return data


def generate_prompt(template, **kwargs):
    """통합 프롬프트 생성 함수"""
    kwargs.update({
        'target_level': FEEDBACK_LEVEL.get("target_level", "TOPIK 2"),
        'allowed_styles': ", ".join(FEEDBACK_LEVEL.get("allowed_speech_styles", ["합니다체", "해요체"])),
        'forbidden_styles': ", ".join(FEEDBACK_LEVEL.get("forbidden_speech_styles", ["반말"]))
    })
    return template.format(**kwargs)


# === 🔥 개선된 피드백 프롬프트 템플릿 (문장 연결 팁 추가) ===
IMPROVED_FEEDBACK_PROMPT_TEMPLATE = """Analyze this Korean speaking response from a beginner student.

Student answered "{question}": {transcript}

**IMPORTANT GUIDELINES:**
1. Be encouraging and positive - these are beginners learning Korean
2. Keep grammar explanations simple and beginner-friendly
3. Always praise what they did well first
4. Target level: {target_level}
5. Allowed speech styles: {allowed_styles}
6. Forbidden speech styles: {forbidden_styles}

**⚠️⚠️ CRITICAL STYLE MATCHING REQUIREMENT: ADHERE TO STUDENT'S ORIGINAL SPEECH STYLE PER SENTENCE ⚠️⚠️**
- **ABSOLUTELY DO NOT change all sentences into one style.** You MUST preserve the student's speech style for EACH sentence individually.
- If a sentence uses 해요(해요, 이에요, 가요, 와요, 봐요, etc.), write that sentence in 해요-style.
- If a sentence uses 합니다(합니다, 입니다, 갑니다, 옵니다, etc.), write that sentence in 합니다-style.
- If the student mixes styles within their response, you MUST reflect that mix in the `suggested_model_sentence`.
- **STRICTLY PROHIBITED:** Do NOT use 반말 or plain dictionary-style endings (e.g., "‑다"). ONLY use speech styles that are appropriate for an interview: either 합니다-style or 해요-style, following the student's usage.

**🔥 ANALYSIS REQUIREMENTS:** 

1. **Grammar Issues (3-6개, 다양한 유형 우선)**
   - **우선순위 적용**: 의사소통에 가장 큰 영향을 주는 오류부터 선택
   - **유형 다양화 필수**: 조사 오류가 많아도 최대 1-2개만 선택하고, 반드시 다른 유형 포함
   - **포함할 유형들**:
     * Particle (조사): 가장 명확한 1-2개만 (을/를, 은/는, 이/가, 에 등)
     * Verb Tense (동사 시제): 과거/현재/미래 혼용 오류
     * Verb Ending (동사 어미): 반말/존댓말, 불규칙 활용, 어미 선택
     * Word Order (어순): 부자연스러운 어순
     * Connectives (연결어): 부적절한 연결표현, 그리고 남용
     * Others: 기타 문법 오류
   
   - **선택 기준**: 
     1. 의사소통에 가장 큰 영향을 주는 오류
     2. 초급자가 자주 틀리는 패턴
     3. 쉽게 고칠 수 있는 오류
     
   - **MUST include "Original:" and "→ Fix:" format.**
   - **CRITICAL: DO NOT classify unnatural word choice as a grammar issue if the grammar itself is correct.**
   - **Target: Find 3-6 issues with TYPE DIVERSITY if they exist.**

2. **Vocabulary (2-3개, 학생 답변 기반 실용적 개선)**
   - **학생이 실제로 사용한 표현의 개선에 초점**
   - **포함할 내용**:
     * 부자연스러운 표현 → 자연스러운 표현 (예: "많이 갔어요" → "여러 곳에 갔어요")
     * 반복된 단어 → 다양한 표현 (예: "그리고" 남용 → 다양한 연결어)
     * 더 정확한 어휘 선택 (맥락에 맞는 단어)
     * vs 형식 유지하되 실용적 개선
   
   - **Format: "❓ **Word A vs Word B**\\n💡 Word A: [explanation of when to use A]\\n💡 Word B: [explanation of when to use B]\\n🟢 [examples showing both words in context]\\n📝 [key difference and usage rule]"**
   - **Focus on student's actual expressions that could be more natural**
   - **Target: Provide 2-3 practical improvements when possible.**

3. **Content Expansion (2개, 구체적이고 실용적)**
   - **학생이 언급한 주제를 기반으로 확장**
   - **예시**: 학생이 "바다 갔어요"라고 했으면 → "바다에서 수영도 하고 조개껍데기도 주웠어요" 같은 구체적 확장
   - Give two concrete, personal topics they can add based on what they mentioned.
   - Each idea should help them speak at least 30 more seconds.
   - Use examples they can directly copy.
   - **CRITICAL: Topic names must be in ENGLISH, Korean sentences in Korean.**
   
4. **One Advanced Pattern (학생 답변 기반)**
   - **학생이 사용한 패턴을 확장하는 방향**
   - **예시**: 학생이 "~고 싶다" 많이 사용 → "~고 싶어서" 이유 표현 가르치기
   - Provide one useful pattern for the placement interview.
   - Must be appropriate for their level (TOPIK 1–2).
   - Connect to what the student actually said.

5. **🔥 Sentence Connection Tip (학생 답변 기반 문장 연결)**
   - **학생이 실제로 사용한 짧은 문장들을 찾아서 연결 방법 제시**
   - **연결어 활용**: 그리고, 그래서, -고, -아서/어서
   - **Before/After 형식**으로 명확한 개선 예시 제공
   - **학생의 실제 발화에서 2-3개 짧은 문장을 선택하여 하나의 긴 문장으로 연결**
   - **Format**: "🎯 **Tip for Longer Sentences**\\n❌ [student's actual short sentences] \\n✅ [combined longer sentence using connectives]\\n💡 Use connectives like 그리고, 그래서, -고, -아서/어서 to sound more natural"

**GRAMMAR ERROR TYPES**
- **Particle**: Wrong particle (은/는, 이/가, 을/를, etc.)
- **Verb Ending**: Wrong verb ending or politeness ending (예요/이에요, 아요/어요, etc.)
- **Verb Tense**: Incorrect verb tense usage (past/present/future)
- **Word Order**: Unnatural word order
- **Connectives**: Inappropriate connecting expressions
- **Others**: For grammar mistakes that do not fit the above categories

**🔥 Performance Summary (구체적 맞춤형 피드백)**
- **구체적 칭찬**: 학생이 실제로 잘한 부분 언급 (예: "Excellent! You covered both topics completely and explained WHY you want to work in Korea")
- **핵심 개선점**: 2-3개로 집중
- **개선 예문**: 학생 답변을 기반으로 한 구체적 예문 제시
- **길이 피드백**: 90초 목표 언급

**Required JSON Structure:**
{{
    "suggested_model_sentence": "Natural, complete Korean sentence showing perfect answer",
    "suggested_model_sentence_english": "English translation",
    "grammar_issues": [
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation"
    ],
    "vocabulary_suggestions": [
        "❓ **Word A vs Word B**\\n💡 Word A: [explanation of when to use A]\\n💡 Word B: [explanation of when to use B]\\n🟢 [examples showing both in context]\\n📝 [key difference]",
        "❓ **Word A vs Word B**\\n💡 Word A: [explanation of when to use A]\\n💡 Word B: [explanation of when to use B]\\n🟢 [examples showing both in context]\\n📝 [key difference]"
    ],
    "content_expansion_suggestions": [
        "💬 Topic: [English topic name]\\n📝 Example: '[Korean sentence they can use]'\\n   '[English translation]'",
        "💬 Topic: [English topic name]\\n📝 Example: '[Korean sentence they can use]'\\n   '[English translation]'"
    ],
    "grammar_expression_tip": "🚀 Try this: '[pattern]' = '[meaning]'\\n📝 Example: '[Korean example]'\\n💡 When to use: [simple explanation]",
    "sentence_connection_tip": "🎯 **Tip for Longer Sentences**\\n❌ [student's actual short sentences from their response]\\n✅ [combined longer sentence using connectives]\\n💡 Use connectives like 그리고, 그래서, -고, -아서/어서 to sound more natural",
    "interview_readiness_score": [1-10],
    "interview_readiness_reason": "Encouraging explanation of score with specific praise and improvements",
    "detailed_feedback": "🌟 What You Did Well\\n- [specific praise point 1 with example from their answer]\\n- [specific praise point 2] 👍\\n\\n🎯 Things to Improve\\n- [specific grammar issue with concrete example: 'Instead of X, try Y']\\n- [specific suggestion with clear example]\\n- [specific content suggestion with example]\\n\\n📝 Try This Next Time\\n1. [actionable tip 1]\\n2. [actionable tip 2]\\n3. [actionable tip 3]"
}}

**Scoring Guide:**
- Score 8 to 10: Spoke 60s+, rich personal content, only minor errors
- Score 6 to 7: Spoke 60s+, good content, some errors but understandable
- Score 4 to 5: Spoke 60s+, basic content, several errors
- Score 1 to 3: Spoke under 60s, limited content, major communication issues"""


# === 메인 피드백 함수들 (개선된 프롬프트 적용) ===
def get_gpt_feedback(transcript, attempt_number=1, duration=0):
    """
    STT 기반 루브릭을 적용한 GPT 피드백 생성 (이중 평가 시스템 적용 + 개선된 프롬프트)
    
    Args:
        transcript: 전사된 텍스트
        attempt_number: 시도 번호
        duration: 음성 길이 (초)
        
    Returns:
        dict: 학생용 피드백 (연구용 점수는 별도 저장)
    """
    if not OPENAI_API_KEY:
        st.error("Critical Error: OpenAI API key is required for feedback!")
        return {}
    
    # 긴 텍스트 전처리 (문자 수 기반)
    processed_transcript = preprocess_long_transcript(transcript)
    
    # 전처리 결과 로깅
    if len(transcript) != len(processed_transcript):
        st.info(f"📝 Text processed: {len(transcript)} → {len(processed_transcript)} characters for better AI analysis")
    
    # 🔥 개선된 프롬프트 템플릿 사용
    enhanced_prompt_template = IMPROVED_FEEDBACK_PROMPT_TEMPLATE + f"""

**STUDENT SPEAKING DURATION:** {duration:.1f} seconds

**IMPORTANT TONE GUIDANCE - SPEAK DIRECTLY TO THE STUDENT:**
- Always use "You" instead of "The student" 
- Write feedback as if you're a warm Korean teacher talking directly to the student
- Be encouraging and personal: "Great job! You spoke for..." instead of "The student spoke for..."
- Use friendly, supportive language throughout all feedback sections

**REMEMBER: Write ALL feedback sections using "You" and speak directly to the student with warmth and encouragement!**

Use the actual duration ({duration:.1f}s) when generating your feedback and scoring."""

    prompt = generate_prompt(enhanced_prompt_template, question=EXPERIMENT_QUESTION, transcript=processed_transcript)
    debug_info = {
        'attempts': 0, 
        'errors': []
    }
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # 2번 시도 (타임아웃 30초로 연장)
    for attempt in range(2):
        debug_info['attempts'] = attempt + 1
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": GPT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=30  # 20초 → 30초로 연장
            )
            
            raw_content = response.choices[0].message.content.strip()
            debug_info['errors'] = []  # 성공시 에러 리스트 초기화
            
            original_feedback = parse_gpt_response(raw_content)
            
            if original_feedback and original_feedback.get('suggested_model_sentence'):
                # 🎯 이중 평가 시스템 적용
                
                # 1. 연구용 점수 계산
                research_scores = get_research_scores(
                    transcript, 
                    original_feedback.get('grammar_issues', []), 
                    duration
                )
                
                # 2. 학생용 피드백 생성
                student_feedback = get_student_feedback(
                    transcript, 
                    research_scores, 
                    original_feedback
                )
                
                # 3. 세션에 연구용 점수 저장
                st.session_state.research_scores = research_scores
                
                # 4. 디버그 정보 저장
                st.session_state.gpt_debug_info = debug_info
                
                st.success("✅ AI feedback ready!")
                return student_feedback
            else:
                raise ValueError("Missing required fields")
                
        except Exception as e:
            error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
            debug_info['errors'].append(error_msg)
            
            if attempt < 1:
                st.warning(f"⚠️ AI feedback error, retrying...")
                time.sleep(0.5)
    
    # 모든 시도 실패 - fallback 피드백 사용
    st.error("❌ AI feedback failed after 2 attempts")
    st.info("Using basic feedback to continue experiment")
    
    debug_info['errors'].append("All attempts failed - using fallback")
    st.session_state.gpt_debug_info = debug_info
    
    # Fallback에서도 이중 평가 시스템 적용
    fallback_feedback = get_fallback_feedback()
    
    # Fallback용 연구 점수 계산
    research_scores = get_research_scores(transcript, [], duration)
    student_feedback = get_student_feedback(transcript, research_scores, fallback_feedback)
    
    # 세션에 저장
    st.session_state.research_scores = research_scores
    
    return student_feedback


def parse_gpt_response(raw_content):
    """GPT 응답을 JSON으로 파싱"""
    try:
        result = json.loads(raw_content)
        return validate_and_fix_feedback(result)
    except json.JSONDecodeError:
        try:
            if "```json" in raw_content:
                start = raw_content.find("```json") + 7
                end = raw_content.find("```", start)
                clean_content = raw_content[start:end].strip()
                result = json.loads(clean_content)
                return validate_and_fix_feedback(result)
        except:
            pass
    
    return None


def validate_and_fix_feedback(feedback):
    """피드백 구조를 검증하고 누락된 필수 필드를 추가"""
    
    # 🔥 필수 필드 기본값 (vs 방식 어휘팁 + 2인칭 톤 + detailed_feedback + sentence_connection_tip)
    required_fields = {
        "suggested_model_sentence": "여름 방학에는 가족하고 여행을 갔어요. 바다에서 수영도 하고 맛있는 음식도 많이 먹었어요. 한국에서는 한국어 수업을 들을 거예요. 한국 문화를 더 배우고 싶어서 한국 친구들도 사귀고 싶어요.",
        "suggested_model_sentence_english": "During summer vacation, I went on a trip with my family. I swam in the sea and ate a lot of delicious food. In Korea, I will take Korean language classes. I want to learn more about Korean culture, so I want to make Korean friends too.",
        "content_expansion_suggestions": [
            "💬 Topic: Summer vacation details\\n📝 Example: '친구들하고 캠핑도 갔어요. 밤에 별도 보고 바베큐도 했어요.'\\n   'I went camping with friends too. We looked at stars at night and had a barbecue.'",
            "💬 Topic: Specific plans in Korea\\n📝 Example: '한국 전통 음식을 배우고 싶어요. 김치 만드는 방법도 배울 거예요.'\\n   'I want to learn Korean traditional food. I will also learn how to make kimchi.'"
        ],
        "vocabulary_suggestions": get_default_vocabulary_suggestions(),  # 🔥 vs 방식 어휘팁
        "fluency_comment": "Keep practicing to speak more naturally!",
        "interview_readiness_score": 6,
        "sentence_connection_tip": "🎯 **Tip for Longer Sentences**\\n❌ 바다 갔어요. 수영했어요.\\n✅ 바다에 가서 수영했어요.\\n💡 Use connectives like 그리고, 그래서, -고, -아서/어서 to sound more natural",  # 🔥 새로 추가
    "detailed_feedback": "🌟 What You Did Well\\n- You answered both topics really well! I could clearly understand your summer vacation activities and your plans for Korea 😊\\n- Your motivation was so clear when you said '한국 문화를 좋아해서' - that connection was perfect! 👍\\n- I loved how you mentioned specific activities like going to the beach. That made your answer much more interesting!\\n\\n🎯 Key Improvements\\n- I noticed some particles were missing. For example, you said '친구 만났어요' but it should be '친구를 만났어요' to sound more natural\\n- Try to keep your tense consistent - when talking about past vacation, stick with past tense endings like '갔어요, 했어요'\\n- Your answer was a bit short (about 45 seconds). Try to add one more detail for each topic to reach 90+ seconds\\n\\n📝 Try This Next Time\\n1. Before speaking, quickly think: 'Am I using 을/를 correctly?'\\n2. Add one specific example when explaining reasons: 'I like Korean food, especially kimchi and bulgogi'\\n3. Use connecting words like '그리고' or '그래서' to make longer, smoother sentences",
        "encouragement_message": "Every practice makes you better! You're doing great learning Korean!"
    }
    
    feedback = ensure_required_fields(feedback, required_fields)
    
    # 🔥 Grammar issues 검증 및 개선 (최대 6개, 모든 오류 표시 + 유형 분류 유지)
    if 'grammar_issues' in feedback and feedback['grammar_issues']:
        valid_issues = []
        for i, issue in enumerate(feedback['grammar_issues'][:6]):  # 최대 6개
            if isinstance(issue, str) and len(issue) > 10:
                # 🎯 오류 타입 분류 (3개 주요 유형 + 기타)
                error_type = classify_error_type(issue)
                if not error_type:  # 3개 유형에 해당하지 않으면
                    error_type = "Others"  # "Others" 유형으로 분류
                
                # 🔥 모든 유효한 문법 오류를 포함 (필터링 제거)
                standardized_issue = standardize_grammar_issue(issue, error_type)
                valid_issues.append(standardized_issue)
        
        if valid_issues:
            feedback['grammar_issues'] = valid_issues
        else:
            feedback['grammar_issues'] = get_default_grammar_issues()
    else:
        feedback['grammar_issues'] = get_default_grammar_issues()
    
    # 🔥 Vocabulary suggestions 재구성 (vs 방식 + 스마트 중복 필터링)
    if 'vocabulary_suggestions' in feedback and feedback['vocabulary_suggestions']:
        # 🎯 스마트한 중복 필터링: 실제 문법 피드백과 중복되는 내용만 제거
        filtered_vocab = filter_grammar_from_vocabulary(
            feedback['vocabulary_suggestions'], 
            feedback.get('grammar_issues', [])
        )
        
        if filtered_vocab:
            # GPT가 생성한 vs 방식 어휘 제안이 있으면 우선 사용
            feedback['vocabulary_suggestions'] = filtered_vocab[:2]  # 최대 2개
        else:
            # 모든 어휘 제안이 문법과 중복되어 필터링된 경우 기본값 사용
            feedback['vocabulary_suggestions'] = get_default_vocabulary_suggestions()
    else:
        # GPT가 어휘 제안을 생성하지 않았으면 기본값 사용
        feedback['vocabulary_suggestions'] = get_default_vocabulary_suggestions()
    
    # 점수 검증
    score = feedback.get("interview_readiness_score", 6)
    if not isinstance(score, (int, float)) or score < 1 or score > 10:
        feedback["interview_readiness_score"] = 6
    
    return feedback


def standardize_grammar_issue(issue_text, error_type):
    """문법 이슈를 간단한 표준 형식으로 변환"""
    
    # Original과 Fix 추출
    original_text = ""
    fix_text = ""
    explanation = ""
    
    if "Original:" in issue_text and "→" in issue_text:
        try:
            original_text = issue_text.split("Original:")[1].split("→")[0].strip().strip("'\"")
            if "Fix:" in issue_text:
                fix_text = issue_text.split("Fix:")[1].split("🧠")[0].strip().strip("'\"")
            else:
                fix_text = issue_text.split("→")[1].split("🧠")[0].strip().strip("'\"")
            
            if "🧠" in issue_text:
                explanation = issue_text.split("🧠")[1].strip()
                # "Simple explanation:" 제거
                explanation = re.sub(r'^(?:💡\s*)?Simple explanation:\s*', '', explanation)
        except:
            pass
    
    # 간단한 표준 형식으로 구성
    if original_text and fix_text:
        if not explanation:
            explanation = get_default_explanation(error_type)
        
        return f"{error_type}|{original_text}|{fix_text}|{explanation}"
    else:
        # 형식이 명확하지 않은 경우 기본 처리
        return f"{error_type}||Basic grammar point|Review this grammar carefully"


def get_default_explanation(error_type):
    """오류 타입별 기본 설명 (4개 유형 지원)"""
    explanations = {
        "Particle": "Use the appropriate particle to mark the grammatical role",
        "Verb Ending": "Use the correct verb ending form",
        "Verb Tense": "Use the appropriate tense marker",
        "Others": "Review this grammar point carefully"  # 🔥 "Others" 유형 추가
    }
    return explanations.get(error_type, "Review this grammar point")


def get_default_grammar_issues():
    """기본 문법 이슈들 (3개 주요 유형)"""
    return [
        "Particle|저는 경제 전공이에요|저는 경제를 전공해요|Use '를' to indicate the object and change '전공이에요' to '전공해요'",
        "Verb Ending|좋아요|좋아해요|Use '좋아해요' when expressing that you like doing activities",
        "Verb Tense|어제 가요|어제 갔어요|Use past tense with time indicators like '어제'"
    ]


def get_fallback_feedback():
    """API 실패시 사용할 기본 피드백 (60-120초 기준, vs 방식 어휘 제안 포함, 2인칭 톤, detailed_feedback 포함, sentence_connection_tip 추가)"""
    return {
        "suggested_model_sentence": "여름 방학에는 가족하고 여행을 갔어요. 바다에서 수영도 하고 맛있는 음식도 많이 먹었어요. 한국에서는 한국어 수업을 들을 거예요. 한국 문화를 더 배우고 싶어서 한국 친구들도 사귀고 싶어요.",
        "suggested_model_sentence_english": "During summer vacation, I went on a trip with my family. I swam in the sea and ate a lot of delicious food. In Korea, I will take Korean language classes. I want to learn more about Korean culture, so I want to make Korean friends too.",
        "grammar_issues": get_default_grammar_issues(),
        "vocabulary_suggestions": get_default_vocabulary_suggestions(),  # 🔥 vs 방식 어휘팁 포함
        "content_expansion_suggestions": [
            "💬 Topic: Summer vacation details\\n📝 Example: '친구들하고 캠핑도 갔어요. 밤에 별도 보고 바베큐도 했어요.'\\n   'I went camping with friends too. We looked at stars at night and had a barbecue.'",
            "💬 Topic: Specific plans in Korea\\n📝 Example: '한국 전통 음식을 배우고 싶어요. 김치 만드는 방법도 배울 거예요.'\\n   'I want to learn Korean traditional food. I will also learn how to make kimchi.'"
        ],
        "grammar_expression_tip": "🚀 Try: '저는 X를 좋아해요' = 'I like X'\\n📝 Example: '저는 한국 음식을 좋아해요'\\n💡 Use to express preferences",
        "sentence_connection_tip": "🎯 **Tip for Longer Sentences**\\n❌ 바다 갔어요. 수영했어요.\\n✅ 바다에 가서 수영했어요.\\n💡 Use connectives like 그리고, 그래서, -고, -아서/어서 to sound more natural",  # 🔥 새로 추가
        "fluency_comment": "Keep practicing! Try to speak for at least 60+ seconds to build fluency.",
        "interview_readiness_score": 5,
        "detailed_feedback": "Good effort attempting both topics! Here are some tips to improve: • Try to speak for at least 60+ seconds to meet interview expectations • Add specific details about your experiences - what exactly did you do? • Practice connecting your ideas with phrases like '그리고' (and) and '그래서' (so/therefore) to sound more natural",
        "encouragement_message": "Every practice session helps! Keep going! 화이팅!"
    }


def get_improvement_assessment(first_transcript, second_transcript, original_feedback):
    """STT 기반 루브릭을 사용한 개선도 평가 (2인칭 톤)"""
    if not OPENAI_API_KEY:
        return get_fallback_improvement_assessment()
    
    # 🔥 개선도 평가 프롬프트에도 2인칭 톤 지침 추가
    enhanced_improvement_template = IMPROVEMENT_PROMPT_TEMPLATE.replace(
        "**Task:** Evaluate improvement between attempts. Be encouraging and specific!",
        """**Task:** Evaluate improvement between attempts. Be encouraging and specific!

**IMPORTANT TONE GUIDANCE - SPEAK DIRECTLY TO THE STUDENT:**
- Always use "You" instead of "The student" 
- Write feedback as if you're a warm Korean teacher talking directly to the student
- Be encouraging and personal: "Great improvement! You spoke much longer..." instead of "The student improved..."
- Use friendly, supportive language throughout all assessment sections"""
    )
    
    prompt = generate_prompt(
        enhanced_improvement_template,
        question=EXPERIMENT_QUESTION,
        first_transcript=first_transcript,
        second_transcript=second_transcript,
        original_feedback=json.dumps(original_feedback, ensure_ascii=False)
    )
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Korean teacher evaluating progress. Respond only with valid JSON. Always speak directly to the student using 'You' instead of 'The student'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            timeout=15
        )
        
        raw_content = response.choices[0].message.content.strip()
        result = parse_gpt_response(raw_content)
        
        if result:
            return validate_and_fix_improvement(result)
        else:
            raise ValueError("Failed to parse response")
            
    except Exception as e:
        print(f"Improvement assessment failed: {e}")
        return get_fallback_improvement_assessment()


def validate_and_fix_improvement(improvement):
    """개선도 평가를 검증하고 누락된 필수 필드를 추가 (2인칭 톤)"""
    required_fields = {
        "first_attempt_score": 5,
        "second_attempt_score": 5,
        "score_difference": 0,
        "improvement_score": 5,
        "improvement_reason": "Continue practicing for better fluency and accuracy",
        "specific_improvements": ["Attempted Korean speaking practice"],
        "remaining_issues": ["Focus on speaking longer (60+ seconds) with more details and address both topics"],
        "feedback_application": "unknown",
        "overall_assessment": "Keep practicing! Focus on speaking for 60+ seconds with personal details and clear reasons for both topics.",
        "encouragement_message": "Every practice session makes you better! Keep going!"
    }
    
    improvement = ensure_required_fields(improvement, required_fields)
    
    # 점수들 검증 (1-10 범위)
    score_fields = ["first_attempt_score", "second_attempt_score", "improvement_score"]
    for field in score_fields:
        score = improvement.get(field, 5)
        if not isinstance(score, (int, float)) or score < 1 or score > 10:
            improvement[field] = 5
    
    # score_difference 계산
    try:
        improvement["score_difference"] = improvement["second_attempt_score"] - improvement["first_attempt_score"]
    except:
        improvement["score_difference"] = 0
    
    # 리스트 필드들 검증
    list_fields = ["specific_improvements", "remaining_issues"]
    for field in list_fields:
        if not isinstance(improvement.get(field), list) or not improvement[field]:
            improvement[field] = ["Attempted Korean speaking practice"] if field == "specific_improvements" else ["Continue practicing for better fluency"]
    
    # feedback_application 검증
    valid_applications = ["excellent", "good", "partial", "poor", "unclear"]
    if improvement.get("feedback_application") not in valid_applications:
        improvement["feedback_application"] = "unclear"
    
    return improvement


def get_fallback_improvement_assessment():
    """개선도 평가 실패시 기본값 (2인칭 톤)"""
    return {
        "first_attempt_score": 5,
        "second_attempt_score": 5,
        "score_difference": 0,
        "improvement_score": 5,
        "improvement_reason": "Technical error - manual review needed",
        "specific_improvements": ["You attempted Korean speaking practice"],
        "remaining_issues": ["Practice speaking for at least 60-120 seconds"],
        "feedback_application": "unknown",
        "overall_assessment": "Keep practicing - focus on at least 60-120 seconds with personal details",
        "encouragement_message": "Every practice session makes you better! Keep going!"
    }


def get_score_category_info(score):
    """점수에 따른 카테고리 정보 반환"""
    for category, info in STT_RUBRIC.items():
        if info["min_score"] <= score <= info["max_score"]:
            return info
    return STT_RUBRIC["fair"]


def display_score_with_category(score, label="Score"):
    """점수를 카테고리와 함께 표시"""
    if isinstance(score, (int, float)):
        category_info = get_score_category_info(score)
        st.markdown(
            f"<h2 style='color: {category_info['color']}; text-align: center;'>{score}/10</h2>", 
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p style='color: {category_info['color']}; text-align: center; font-weight: bold;'>{category_info['label']}</p>", 
            unsafe_allow_html=True
        )
    else:
        st.write(f"**{label}:** {score}")


def display_score_with_encouragement(score, duration=0):
    """점수를 격려 메시지와 함께 표시 (60-120초 기준)"""
    category_info = get_score_category_info(score)
    
    # 점수 표시
    st.markdown(
        f"<h2 style='color: {category_info['color']}; text-align: center; margin: 20px 0;'>{score}/10</h2>", 
        unsafe_allow_html=True
    )
    
    # 🔥 격려 메시지 (TOPIK 기준으로 수정, 60-120초 목표)
    if score >= 8:
        st.balloons()
        message = "🌟 Outstanding! Excellent task completion with rich content!"
        if duration >= 90:
            message += " Perfect length too!"
    elif score >= 7:
        message = "🎯 Great job! Good task completion and content!"
        if duration < 60:
            message += " Try to speak for at least 60 seconds next time."
    elif score >= 6:
        message = "💪 Good work! You're improving steadily!"
        if duration < 60:
            message += " Aim for 60+ seconds."
    elif score >= 5:
        message = "🚀 Keep going! You're learning!"
        if duration < 60:
            message += " Focus on reaching 60 seconds."
    else:
        message = "🌱 Everyone starts somewhere! Keep practicing!"
        message += " Work towards 60+ seconds with both topics covered."
    
    # 메시지 표시
    st.markdown(
        f"""
        <div style='
            background-color: {category_info['color']}20;
            border: 2px solid {category_info['color']};
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            margin: 10px 0;
        '>
            <p style='
                color: {category_info['color']};
                font-weight: bold;
                font-size: 16px;
                margin: 0;
            '>
                {message}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )