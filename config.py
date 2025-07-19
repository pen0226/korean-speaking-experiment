"""
config.py
실험 전역 설정 및 상수 정의 (로컬 .env + Streamlit Cloud secrets 완벽 지원)
"""

import os
import streamlit as st
from dotenv import load_dotenv

# 환경변수 로드 (로컬 개발용)
load_dotenv()


def is_streamlit_cloud():
    """Streamlit Cloud 환경인지 감지"""
    try:
        cloud_indicators = [
            'STREAMLIT_CLOUD' in os.environ,
            'HOSTNAME' in os.environ and 'streamlit' in os.environ.get('HOSTNAME', '').lower(),
            hasattr(st, 'secrets') and len(st.secrets) > 0
        ]
        return any(cloud_indicators)
    except:
        return False


def get_secret(key, default=None):
    """
    로컬(.env) + Streamlit Cloud(secrets) 완벽 지원
    
    동작 방식:
    - 로컬: .env 파일에서 읽기
    - Streamlit Cloud: st.secrets에서 읽기
    """
    
    if is_streamlit_cloud():
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception as e:
            print(f"Streamlit secrets error for {key}: {e}")
    
    return os.getenv(key, default)


# 세션 설정
CURRENT_SESSION = 1  # 1차 세션: 1, 2차 세션: 2로 변경
SESSION_LABELS = {
    1: "Session 1",
    2: "Session 2"
}

# 실험 설정
EXPERIMENT_QUESTION = "자기소개를 해 보세요. (예: 이름, 나이, 전공, 성격, 취미, 가족)"

# 세션별 질문 설정
SESSION_QUESTIONS = {
    1: "자기소개를 해 보세요. (예: 이름, 나이, 전공, 성격, 취미, 가족)",
    2: "이번 여름에 한국에서 뭐 하려고 하세요? 특별한 계획이 있으세요?"
}

# 현재 세션에 맞는 질문으로 자동 설정
EXPERIMENT_QUESTION = SESSION_QUESTIONS.get(CURRENT_SESSION, SESSION_QUESTIONS[1])

# 배경 정보 설정
BACKGROUND_INFO = {
    "learning_duration_options": [
        "Less than 6 months",
        "6 months – 1 year",
        "1 – 2 years", 
        "More than 2 years"
    ],
    "confidence_options": [
        "1️⃣ Not confident at all",
        "2️⃣ Not very confident",
        "3️⃣ Neutral", 
        "4️⃣ Quite confident",
        "5️⃣ Very confident"
    ]
}

# AI 모델 설정
GPT_MODELS = ["gpt-4o"]
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# GPT 피드백 토큰 제한 설정
GPT_FEEDBACK_MAX_TOKENS = 800
GPT_FEEDBACK_MAX_CHARS = 1000

# API 키 설정
OPENAI_API_KEY = get_secret('OPENAI_API_KEY')
ELEVENLABS_API_KEY = get_secret('ELEVENLABS_API_KEY')
ELEVEN_VOICE_ID = get_secret('ELEVEN_VOICE_ID')

# Google Cloud Storage 설정
GCS_ENABLED = get_secret('GCS_ENABLED', 'False').lower() == 'true'
GCS_BUCKET_NAME = get_secret('GCS_BUCKET_NAME', 'korean-speaking-experiment')
GCS_SERVICE_ACCOUNT = get_secret('gcp_service_account')

# 간소화된 GCS 폴더 구조
GCS_SIMPLE_STRUCTURE = {
    1: "session1/",
    2: "session2/"
}

# Streamlit 페이지 설정
PAGE_CONFIG = {
    "page_title": f"Korean Speaking Experiment - {SESSION_LABELS.get(CURRENT_SESSION, 'Session 1')}",
    "page_icon": "🇰🇷",
    "layout": "wide"
}

# 실험 단계 정의
EXPERIMENT_STEPS = {
    'nickname_input': ('Step 1', 'Enter Nickname'),
    'first_recording': ('Step 2', 'First Recording'),
    'feedback': ('Step 3', 'AI Feedback'),
    'second_recording': ('Step 4', 'Second Recording'),
    'survey': ('Step 5', 'Required Survey'),
    'completion': ('Step 6', 'Complete')
}

# 설문조사 URL
GOOGLE_FORM_URLS = {
    1: "https://docs.google.com/forms/d/e/1FAIpQLSds3zsmZYjN3QSc-RKRtbDPTF0ybLrwJW4qVLDg2_xoumBLDw/viewform?usp=header",
    2: "https://docs.google.com/forms/d/e/1FAIpQLSds3zsmZYjN3QSc-RKRtbDPTF0ybLrwJW4qVLDg2_xoumBLDw/viewform?usp=header"
}

GOOGLE_FORM_URL = GOOGLE_FORM_URLS.get(CURRENT_SESSION, GOOGLE_FORM_URLS[1])

# 피드백 난이도 설정
FEEDBACK_LEVEL = {
    "target_level": "TOPIK 2",
    "encourage_level_3": True,
    "allowed_speech_styles": ["합니다체", "해요체"],
    "forbidden_speech_styles": ["반말"]
}

# STT 기반 루브릭 설정
STT_RUBRIC = {
    "excellent": {"min_score": 9, "max_score": 10, "label": "Excellent", "color": "#059669"},
    "good": {"min_score": 7, "max_score": 8, "label": "Good", "color": "#0891b2"},
    "fair": {"min_score": 5, "max_score": 6, "label": "Fair", "color": "#ea580c"},
    "poor": {"min_score": 3, "max_score": 4, "label": "Poor", "color": "#dc2626"},
    "very_poor": {"min_score": 1, "max_score": 2, "label": "Very Poor", "color": "#991b1b"}
}

# 문법 오류 유형 정의
GRAMMAR_ERROR_TYPES = {
    "Particle": {
        "korean": "조사",
        "description": "Wrong particle choice (은/는, 이/가, 을/를, etc.)"
    },
    "Verb Ending": {
        "korean": "동사어미",
        "description": "Wrong verb endings (아요/어요, 예요/이에요, etc.)"
    },
    "Verb Tense": {
        "korean": "동사시제", 
        "description": "Wrong tense with time indicators"
    }
}

# 오디오 품질 기준
AUDIO_QUALITY = {
    "excellent_min_duration": 60,
    "good_min_duration": 45,
    "fair_min_duration": 30,
    "max_recommended_duration": 120
}

# 데이터 보관 설정
DATA_RETENTION_DAYS = 730

# 로컬 폴더 구조
FOLDERS = {
    "data": "data",
    "logs": "logs",
    "audio_recordings": "audio_recordings"
}

# TTS 설정
TTS_SETTINGS = {
    "normal": {
        "stability": 0.75,
        "similarity_boost": 0.80,
        "style": 0.15,
        "use_speaker_boost": False,
        "speed": 1.0
    },
    "slow": {
        "stability": 0.85,
        "similarity_boost": 0.80,
        "style": 0.20,
        "use_speaker_boost": False,
        "speed": 0.7
    }
}

# GPT 프롬프트 설정
GPT_SYSTEM_PROMPT = """You are a Korean language teaching expert specializing in TOPIK 1-2 level learners. 
Focus on precise error analysis and practical improvements. 
Always respond with valid JSON only."""

# 개선된 피드백 생성 프롬프트 템플릿
FEEDBACK_PROMPT_TEMPLATE = """Analyze this Korean speaking response from a beginner student.

Student answered "{question}": {transcript}

**IMPORTANT GUIDELINES:**
1. Be encouraging and positive - these are beginners learning Korean
2. Content expansion is MOST important - help them speak for at least 1 minute (60+ seconds)
3. Keep grammar explanations simple and beginner-friendly
4. Always praise what they did well first
5. Target level: {target_level}
6. Allowed speech styles: {allowed_styles}
7. Forbidden speech styles: {forbidden_styles}

**STYLE MATCHING REQUIREMENT:**
- First analyze the student's speech style from their transcript
- If student uses 해요체 (해요, 이에요, 가요, 와요, 봐요, etc.), generate model sentence in 해요체
- If student uses 합니다체 (합니다, 입니다, 갑니다, 옵니다, etc.), generate model sentence in 합니다체
- Keep the same politeness level as the student throughout the entire model sentence
- This ensures natural consistency with the student's preferred speech style

**ANALYSIS REQUIREMENTS:**

1. **Content Expansion** (2 specific ideas) - MOST IMPORTANT!
   - Give concrete, personal topics they can add
   - Each idea should help them speak 15+ more seconds
   - Use examples they can directly copy
   
2. **Grammar Issues** (up to 6 maximum) - Keep it simple!
   - Only point out the most important errors
   - Use simple language, avoid technical terms
   - Show clear before/after examples
   - Focus on these 3 types: Particle, Verb Ending, Verb Tense
   - MUST include "Original:" and "→ Fix:" format

3. **Vocabulary** (1-2 suggestions) - WORD CHOICE ONLY!
   - Suggest ONLY alternative words or phrases for better expression
   - Do NOT correct particles (은/는, 이/가, 을/를), verb endings, or tense markers here
   - Focus on synonyms, better word choices, or more natural expressions
   - Example: '많이' → '정말', '좋다' → '재미있다', '공부하다' → '배우다'
   - Avoid grammar corrections - those belong in Grammar Issues section

4. **One Advanced Pattern** - Something to aspire to
   - One useful pattern for the placement interview
   - Must be appropriate for their level

**GRAMMAR ERROR TYPES (use only these 3):**
- **Particle**: Wrong particle (은/는, 이/가, 을/를, etc.)
- **Verb Ending**: Wrong ending (예요/이에요, 아요/어요, etc.)
- **Verb Tense**: Wrong time expression (past/present/future)

**Required JSON Structure:**
{{
    "suggested_model_sentence": "Natural, complete Korean sentence showing perfect answer",
    "suggested_model_sentence_english": "English translation",
    "grammar_issues": [
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation"
    ],
    "vocabulary_suggestions": [
        "💭 Better: '[old word/phrase]' → '[new word/phrase]'\\n🧠 Why: [very simple reason]"
    ],
    "content_expansion_suggestions": [
        "💬 Topic: [Specific personal topic]\\n📝 Example: '[Korean sentence they can use]'\\n   '[English translation]'",
        "💬 Topic: [Specific personal topic]\\n📝 Example: '[Korean sentence they can use]'\\n   '[English translation]'"
    ],
    "grammar_expression_tip": "🚀 Try this: '[pattern]' = '[meaning]'\\n📝 Example: '[Korean example]'\\n💡 When to use: [simple explanation]",
    "interview_readiness_score": [1-10],
    "interview_readiness_reason": "Encouraging explanation of score"
}}

**TONE:** Be warm, encouraging, and supportive. These are beginners who need confidence!

**Scoring Guide:**
- 8-10: Spoke 60s+, rich personal content, only minor errors
- 6-7: Spoke 45-60s, good content, some errors but understandable
- 4-5: Spoke 30-45s, basic content, several errors
- 1-3: Spoke under 30s, limited content, major communication issues

Remember: The goal is to help them speak for at least 1 minute (60+ seconds) with MORE PERSONAL DETAILS!"""

# 개선도 평가 프롬프트 템플릿
IMPROVEMENT_PROMPT_TEMPLATE = """Compare two Korean speaking attempts from a beginner student.

QUESTION: "{question}"
FIRST ATTEMPT: "{first_transcript}"
SECOND ATTEMPT: "{second_transcript}"
ORIGINAL FEEDBACK GIVEN: {original_feedback}

**Task:** Evaluate improvement between attempts. Be encouraging and specific!

**Focus on:**
1. Did they speak longer? (Most important! Target: at least 1 minute / 60+ seconds)
2. Did they add more personal details?
3. Did they fix any grammar issues?
4. Did they use the vocabulary suggestions?
5. Did they apply the content expansion ideas?
6. Did they maintain allowed speech styles ({allowed_styles})?

**Scoring Guide:**
- 8-10: Major improvement - much longer (closer to 60s), richer content, applied feedback well
- 6-7: Good improvement - somewhat longer, some new content, tried to apply feedback
- 4-5: Some improvement - slight changes, minimal new content
- 1-3: Little/no improvement - similar or shorter

**JSON Response:**
{{
    "first_attempt_score": [1-10],
    "second_attempt_score": [1-10], 
    "score_difference": [difference],
    "improvement_score": [1-10],
    "improvement_reason": "Encouraging analysis focusing on what they improved",
    "specific_improvements": [
        "Specific thing they did better",
        "Another improvement",
        "Any new content they added"
    ],
    "remaining_issues": [
        "Gentle suggestion for next time",
        "Another area to work on"
    ],
    "feedback_application": "excellent/good/partial/minimal",
    "overall_assessment": "Warm, encouraging summary with specific next steps",
    "encouragement_message": "Personal message praising their effort and progress"
}}

Be specific about improvements and always find something positive to say!"""

# 기본 피드백 데이터
FALLBACK_FEEDBACK_DATA = {
    "suggested_model_sentence": "안녕하세요. 저는 [이름]이에요. 한국학을 전공해요. 취미는 음악 듣기와 영화 보기예요.",
    "suggested_model_sentence_english": "Hello. I'm [name]. I major in Korean Studies. My hobbies are listening to music and watching movies.",
    "grammar_issues": [
        "Particle|저는 경제 전공이에요|저는 경제를 전공해요|Use '를' to indicate the object and change '전공이에요' to '전공해요'",
        "Verb Ending|좋아요|좋아해요|Use '좋아해요' when expressing that you like doing activities",
        "Verb Tense|어제 가요|어제 갔어요|Use past tense with time indicators like '어제'"
    ],
    "vocabulary_suggestions": [
        "❓ **공부하다 vs 배우다**\\n💡 공부하다: Academic studying or reviewing material at a desk\\n💡 배우다: Learning new skills or acquiring new knowledge\\n🟢 시험을 위해 공부해요 (I study for exams) / 한국어를 배우고 있어요 (I'm learning Korean)\\n📝 Use '배우다' for new skills, '공부하다' for reviewing",
        "❓ **좋다 vs 좋아하다**\\n💡 좋다: Adjective - something is good (state/quality)\\n💡 좋아하다: Verb - to like something (preference)\\n🟢 날씨가 좋아요 (The weather is nice) / 음악을 좋아해요 (I like music)\\n📝 Use '이/가 좋다' vs '을/를 좋아하다'"
    ],
    "content_expansion_suggestions": [
        "💬 Topic: Favorite Korean food\\n📝 Example: '제가 가장 좋아하는 한국 음식은 불고기예요. 불고기는 달콤하고 맛있어요.'\\n   'My favorite Korean food is bulgogi. It is sweet and delicious.'",
        "💬 Topic: Why you study Korean\\n📝 Example: '한국 문화가 재미있어서 한국어를 공부해요.'\\n   'I study Korean because Korean culture is interesting.'"
    ],
    "grammar_expression_tip": "🚀 Try: '저는 X를 좋아해요' = 'I like X'\\n📝 Example: '저는 한국 음식을 좋아해요'\\n💡 Use to express preferences",
    "interview_readiness_score": 6,
    "interview_readiness_reason": "Good start! Focus on speaking for at least 1 minute (60+ seconds) to score higher. You can do it!",
    "encouragement_message": "Learning Korean is challenging, but you're making real progress! 화이팅!"
}

# 기본 개선도 평가 데이터
FALLBACK_IMPROVEMENT_DATA = {
    "first_attempt_score": 5,
    "second_attempt_score": 5,
    "score_difference": 0,
    "improvement_score": 5,
    "improvement_reason": "Technical error - manual review needed",
    "specific_improvements": ["Attempted Korean speaking"],
    "remaining_issues": ["Practice speaking for at least 1 minute (60+ seconds)"],
    "feedback_application": "unknown",
    "overall_assessment": "Keep practicing - focus on at least 1 minute (60+ seconds) with personal details",
    "encouragement_message": "Every practice session makes you better! Keep going!"
}

# 파일 확장자 설정
SUPPORTED_AUDIO_FORMATS = ["wav", "mp3", "m4a", "flac", "ogg", "webm"]

# UI 색상 테마
UI_COLORS = {
    "primary": "#0369a1",
    "success": "#059669",
    "warning": "#ea580c", 
    "error": "#dc2626",
    "info": "#0891b2",
    "background": "#f8fafc",
    "border": "#e2e8f0"
}

# 로그 설정
LOG_FORMAT = {
    "timestamp_format": "%Y-%m-%d %H:%M:%S",
    "filename_format": "upload_log_%Y%m%d.txt"
}

# GCS 연결 테스트 함수
def test_gcs_connection():
    """GCS 연결 상태 테스트"""
    try:
        if not GCS_ENABLED:
            return False, "GCS_ENABLED is False"
        
        if not GCS_SERVICE_ACCOUNT:
            return False, "Service account not found in secrets"
        
        if not GCS_BUCKET_NAME:
            return False, "GCS_BUCKET_NAME not configured"
        
        import json
        try:
            if isinstance(GCS_SERVICE_ACCOUNT, dict):
                service_account_info = dict(GCS_SERVICE_ACCOUNT)
                project_id = service_account_info.get('project_id', 'Unknown')
                return True, f"GCS Ready - Project: {project_id} (TOML format)"
            
            elif isinstance(GCS_SERVICE_ACCOUNT, str):
                service_account_info = json.loads(GCS_SERVICE_ACCOUNT)
                project_id = service_account_info.get('project_id', 'Unknown')
                return True, f"GCS Ready - Project: {project_id} (JSON format)"
            
            else:
                return False, f"Unexpected service account type: {type(GCS_SERVICE_ACCOUNT)}"
                
        except json.JSONDecodeError:
            return False, "Invalid JSON format in service account"
        except Exception as parse_error:
            return False, f"Service account parsing error: {str(parse_error)}"
            
    except Exception as e:
        return False, f"GCS test failed: {str(e)}"

# 환경 정보 출력 (간소화)
if not is_streamlit_cloud():
    api_status = "✅ Loaded" if OPENAI_API_KEY else "❌ Missing"
    gcs_status = "✅ Ready" if GCS_ENABLED else "❌ Disabled"
else:
    api_status = "✅ Loaded" if OPENAI_API_KEY else "❌ Missing"
    gcs_status = "✅ Ready" if GCS_ENABLED else "❌ Disabled"
    
    # GCS 연결 상태 자동 테스트
    gcs_test_status, gcs_message = test_gcs_connection()
    if gcs_test_status:
        print(f"🗄️ GCS Status: ✅ {gcs_message}")
    else:
        print(f"🗄️ GCS Status: ❌ {gcs_message}")