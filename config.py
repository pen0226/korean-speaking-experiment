"""
config.py
실험 전역 설정 및 상수 정의 (로컬 .env + Streamlit Cloud secrets 완벽 지원)
"""

import os
import streamlit as st
from dotenv import load_dotenv
from pytz import timezone  # 🔥 이 줄 추가!

# 한국 시간대 설정 🔥 이 줄도 추가!
KST = timezone('Asia/Seoul')

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
CURRENT_SESSION = 2  # 1차 세션: 1, 2차 세션: 2로 변경
SESSION_LABELS = {
    1: "Session 1",
    2: "Session 2"
}

# 🔥 수정된 실험 질문
EXPERIMENT_QUESTION = "Please speak for about 1~2 minutes in total and talk about both topics below. 1️⃣ 지난 방학에 뭐 했어요?  2️⃣ 다음 방학에는 뭐 할 거예요? 왜요?"

# 🔥 수정된 세션별 질문 설정
SESSION_QUESTIONS = {
    1: "Please speak for about 1~2 minutes in total and talk about both topics below. 1️⃣ 지난 방학에 뭐 했어요?  2️⃣ 다음 방학에는 뭐 할 거예요? 왜요?",
    2: "Please speak for about 1~2 minutes in total and talk about both topics below. 1️⃣ 지난 방학에 뭐 했어요?  2️⃣ 다음 방학에는 뭐 할 거예요? 왜요?"
}
# 현재 세션에 맞는 질문으로 자동 설정
EXPERIMENT_QUESTION = SESSION_QUESTIONS.get(CURRENT_SESSION, SESSION_QUESTIONS[1])

# 배경 정보 설정
BACKGROUND_INFO = {
    "learning_duration_options": [
        "Less than 6 months",
        "6 months – 1 year",
        "1 – 2 years", 
        "2 - 3 years",
        "More than 3 years"
    ]
}

# 자기효능감 문항 설정 (12개 문항 - 5점 만점)
SELF_EFFICACY_ITEMS = [
    "I can talk about the given topic in Korean.",
    "I can speak in a clear and logical way in Korean.",
    "I can give enough details and examples to fully explain my ideas in Korean.",
    "I can use Korean grammar correctly when I speak.",
    "I can use appropriate vocabulary when I speak Korean.",
    "I can choose the appropriate level of politeness and speech style when speaking Korean.",
    "I can pronounce Korean accurately and naturally.",
    "I can speak with natural Korean intonation.",
    "I can adjust my speaking speed and pauses to make my Korean easier to understand.",
    "I can continue speaking in Korean even if I make mistakes.",
    "I can speak in Korean even when I feel nervous.",
    "I can answer in Korean even if I am asked an unexpected question."
]

SELF_EFFICACY_SCALE = [
    "1️⃣ Strongly Disagree",
    "2️⃣ Disagree", 
    "3️⃣ Neutral",
    "4️⃣ Agree",
    "5️⃣ Strongly Agree"
]

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
    "page_title": f"Korean Speaking Experiment - {SESSION_LABELS.get(CURRENT_SESSION, 'Session 2')}",
    "page_icon": "🇰🇷",
    "layout": "wide"
}

# 실험 단계 정의 (2단계 분리: consent → background_info)
EXPERIMENT_STEPS = {
    'consent': ('Step 1', 'Consent Form'),
    'background_info': ('Step 2', 'Background Info'),
    'first_recording': ('Step 3', 'First Recording'),
    'feedback': ('Step 4', 'AI Feedback'),
    'second_recording': ('Step 5', 'Second Recording'),
    'survey': ('Step 6', 'Required Survey'),
    'completion': ('Complete', 'Thank You!')  # ← Step 7 → Complete로 수정
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
    },
    "Word Order": {
        "korean": "어순",
        "description": "Unnatural word order in sentences"
    },
    "Connectives": {
        "korean": "연결어",
        "description": "Inappropriate connecting expressions or overuse"
    },
    "Others": {
        "korean": "기타",
        "description": "Other grammar mistakes not fitting specific categories"
    }
}

# 🔥 오디오 품질 기준 (1-2분 목표로 수정)
AUDIO_QUALITY = {
    "excellent_min_duration": 90,   # 1.5분 (중간값)
    "good_min_duration": 75,        # 1분 15초
    "fair_min_duration": 60,        # 1분
    "max_recommended_duration": 180 # 3분
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
        "stability": 0.95,
        "similarity_boost": 0.4,
        "style": 0.1,
        "use_speaker_boost": True,
        "speed": 0.9
    },
    "slow": {
        "stability": 0.95,
        "similarity_boost": 0.30,
        "style": 0.1,
        "use_speaker_boost": True,
        "speed": 0.7
    }
}

# GPT 프롬프트 설정
GPT_SYSTEM_PROMPT = """You are a Korean language teaching expert specializing in TOPIK 1-2 level learners. 
Focus on precise error analysis and practical improvements. 
Always respond with valid JSON only."""

# 🔥 개선된 피드백 생성 프롬프트 템플릿 (수정된 질문 반영)
FEEDBACK_PROMPT_TEMPLATE = """Analyze this Korean speaking response from a beginner student.

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
- **Example for clarity:** If student says "저는 학생이에요. 한국에 갑니다." model should suggest "저는 학생이에요. 한국에 갑니다." NOT "저는 학생입니다. 한국에 갑니다."

**ANALYSIS REQUIREMENTS:** 1. **Grammar Issues**
   - Carefully check each sentence for grammar issues that beginners often make.
   - Look for particles (은/는, 이/가, 을/를), verb endings, and tense errors.
   - Also include minor errors and awkward constructions related to grammar.
   - Check word order, honorifics, and overall sentence structure.
   - MUST include "Original:" and "→ Fix:" format.
   - **CRITICAL: DO NOT classify unnatural word choice as a grammar issue if the grammar itself is correct.**
   - **Target: Find up to 6 issues if they exist.**

2. **Vocabulary (vs format for educational comparison, including unnatural word choice)**
   - Only suggest if you find word choice issues that need comparison between similar words OR if the student used an **unnatural/incorrect word choice** for the context.
   - Format: "❓ **Word A vs Word B**\\n💡 Word A: [explanation of when to use A]\\n💡 Word B: [explanation of when to use B]\\n🟢 [examples showing both words in context]\\n📝 [key difference and usage rule]"
   - Focus on commonly confused pairs for beginners (공부하다 vs 배우다, 좋다 vs 좋아하다, 가다 vs 오다, etc.)
   - **Example for unnatural word choice:** If student says "친구를 만들고 싶어요", suggest "❓ **만들다 vs 사귀다**\\n💡 만들다: To create or build a physical object/abstract concept.\\n💡 사귀다: To make friends or build a relationship.\\n🟢 집을 만들어요 (I build a house) / 친구를 사귀어요 (I make friends).\\n📝 '사귀다' is used for friends/relationships."
   - Emphasize when to use each word, not that one is "wrong" (unless clearly incorrect for context).
   - **Target: Provide 1–2 vocabulary comparisons when improvements are possible.**
   - **CRITICAL: This section should handle unnatural/incorrect word choices. DO NOT overlap with grammar corrections.**

3. **Content Expansion** (2 specific ideas)
   - Give two concrete, personal topics they can add.
   - Each idea should help them speak at least 30 more seconds.
   - Use examples they can directly copy.
   - **CRITICAL: Topic names must be in ENGLISH, Korean sentences in Korean.**
   
4. **One Advanced Pattern** (something to aspire to)
   - Provide one useful pattern for the placement interview.
   - Must be appropriate for their level (TOPIK 1–2).

**GRAMMAR ERROR TYPES**
- **Particle**: Wrong particle (은/는, 이/가, 을/를, etc.)
- **Verb Ending**: Wrong verb ending or politeness ending (예요/이에요, 아요/어요, etc.)
- **Verb Tense**: Incorrect verb tense usage (past/present/future)
- **Others**: For grammar mistakes that do not fit the above three categories

**Required JSON Structure:**
{{
    "suggested_model_sentence": "Write one perfect Korean paragraph that answers both the past vacation and future plans questions, based strictly on the student's answer. Keep all original ideas and details from the student's response, correcting any grammar or vocabulary errors and using appropriate TOPIK 2 level expressions.",
    "suggested_model_sentence_english": "English translation",
    "grammar_issues": [
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form",
        "❗️ [Type]\\n• Original: '[exactly what they said]' → Fix: '[corrected version]'\\n🧠 Simple explanation with why the original is wrong and when to use the correct form"
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
    "interview_readiness_score": [1-10],
    "interview_readiness_reason": "Encouraging explanation of score"
}}

**Scoring Guide:**
- Score 9 to 10: Spoke 60s+, covered BOTH past vacation AND future plans completely with rich personal details, only minor errors
- Score 7 to 8: Spoke 60s+, covered BOTH topics with good details, some errors but understandable
- Score 5 to 6: Spoke 60s+, covered BOTH topics with basic content, OR covered only ONE topic well, several errors
- Score 2 to 4: Spoke 60s+ but missing one major topic OR spoke under 60s with limited content
- Score 1: Spoke under 60s, missing both topics or major communication issues"""

# 🔥 개선도 평가 프롬프트 템플릿 (수정된 질문 반영)
IMPROVEMENT_PROMPT_TEMPLATE = """Compare two Korean speaking attempts from a beginner student.

QUESTION: "{question}"
FIRST ATTEMPT: "{first_transcript}"
SECOND ATTEMPT: "{second_transcript}"
ORIGINAL FEEDBACK GIVEN: {original_feedback}

**Task:** Evaluate improvement between attempts. Be encouraging and specific!

**Focus on:**
1. Did they speak longer? (Most important! Target: at least 1-2 minutes / 90+ seconds)
2. Did they add more personal details?
3. Did they fix any grammar issues?
4. Did they use the vocabulary suggestions?
5. Did they apply the content expansion ideas?
6. Did they maintain allowed speech styles ({allowed_styles})?

**Scoring Guide:**
- Score 9 to 10: Major improvement - much longer (closer to 70s+), richer content, applied feedback well
- Score 6 to 8: Good improvement - somewhat longer, some new content, tried to apply feedback
- Score 4 to 5: Some improvement - slight changes, minimal new content
- Score 1 to 3: Little/no improvement - similar or shorter

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

# 🔥 기본 피드백 데이터 (수정된 질문에 맞게 조정)
FALLBACK_FEEDBACK_DATA = {
    "suggested_model_sentence": "지난 방학에는 가족과 함께 여행을 갔어요. 새로운 도시에서 맛있는 음식도 먹고 사진도 많이 찍었어요. 다음 방학에는 한국어 수업을 들을 거예요. 한국 문화를 더 배우고 싶어서 한국 친구들도 사귀고 싶어요.",
    "suggested_model_sentence_english": "During my last vacation, I went on a trip with my family. We ate delicious food in a new city and took lots of photos. Next vacation, I will take Korean language classes. I want to learn more about Korean culture, so I want to make Korean friends too.",
    "grammar_issues": [
        "Particle|친구가 만났어요|친구를 만났어요|Use '를' to indicate the object and change '전공이에요' to '전공해요'",
        "Verb Tense|내일 한국어 공부해요|내일 한국어 공부할 거예요|Use future tense '할 거예요' for definite future plans",
        "Verb Ending|음악을 좋아요|음악을 좋아해요|Use '좋아해요' when expressing that you like something"
    ],
    "vocabulary_suggestions": [
        "❓ **공부하다 vs 배우다**\\n💡 공부하다: Academic studying or reviewing material at a desk\\n💡 배우다: Learning new skills or acquiring new knowledge\\n🟢 시험을 위해 공부해요 (I study for exams) / 한국어를 배우고 있어요 (I'm learning Korean)\\n📝 Use '배우다' for new skills, '공부하다' for reviewing",
        "❓ **좋다 vs 좋아하다**\\n💡 좋다: Adjective - something is good (state/quality)\\n💡 좋아하다: Verb - to like something (preference)\\n🟢 날씨가 좋아요 (The weather is nice) / 음악을 좋아해요 (I like music)\\n📝 Use '이/가 좋다' vs '을/를 좋아하다'"
    ],
    "content_expansion_suggestions": [
        "💬 Topic: Last vacation details\\n📝 Example: '친구들과 함께 해변에서 놀았어요. 일출도 보고 바베큐도 했어요.'\\n   'I had fun at the beach with friends. We watched the sunrise and had a barbecue.'",
        "💬 Topic: Specific plans for next vacation\\n📝 Example: '한국 전통 음식을 배우고 싶어요. 김치 만드는 방법도 배울 거예요.'\\n   'I want to learn Korean traditional food. I will also learn how to make kimchi.'"
    ],
    "grammar_expression_tip": "🚀 Try these useful patterns:\\n• 'X와/과 함께 Y했어요' = 'I did Y together with X'\\n📝 Example: '가족과 함께 여행했어요'\\n• 'X고 싶어서 Y할 거예요' = 'I will do Y because I want to X'\\n📝 Example: '한국어를 배우고 싶어서 수업을 들을 거예요'\\n💡 Use to make your answers more detailed and natural",
    "interview_readiness_score": 6,
    "interview_readiness_reason": "Good start! Focus on speaking for at least 1-2 minutes (90+ seconds) to score higher. You can do it!",
    "encouragement_message": "Learning Korean is challenging, but you're making real progress! 화이팅!"
}

# 🔥 기본 개선도 평가 데이터 (1-2분 기준)
FALLBACK_IMPROVEMENT_DATA = {
    "first_attempt_score": 5,
    "second_attempt_score": 5,
    "score_difference": 0,
    "improvement_score": 5,
    "improvement_reason": "Technical error - manual review needed",
    "specific_improvements": ["Attempted Korean speaking"],
    "remaining_issues": ["Practice speaking for at least 1-2 minutes (90+ seconds)"],
    "feedback_application": "unknown",
    "overall_assessment": "Keep practicing - focus on at least 1-2 minutes (90+ seconds) with personal details",
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