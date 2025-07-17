# 🇰🇷 AI-Based Korean Speaking Feedback System

이화여자대학교 대학원 연구 프로젝트: AI 기반 한국어 말하기 피드백 시스템의 효과성 연구

## 📋 연구 개요

본 시스템은 한국어 학습자들이 말하기 능력을 향상시킬 수 있도록 돕는 AI 기반 피드백 도구입니다. 초급 학습자들을 대상으로 개인화된 피드백을 제공하여 배치고사 준비와 말하기 정확성 향상을 지원합니다.

### 🎯 주요 기능
- **음성 인식**: OpenAI Whisper를 통한 정확한 한국어 STT
- **AI 피드백**: GPT-4o 기반 개인화된 문법/어휘/내용 개선 제안
- **발음 모델**: ElevenLabs TTS로 생성된 모범 발음 제공
- **진행도 분석**: 1차-2차 녹음 비교를 통한 개선도 평가
- **연구 데이터**: GDPR 준수 데이터 수집 및 안전한 저장

## 🚀 라이브 데모

**파일럿 테스트 URL**: [여기에 배포된 URL이 들어갑니다]

### 테스트 참여 방법
1. 위 링크 접속
2. 연구 참여 동의
3. 한국어로 1분간 자기소개 녹음
4. AI 피드백 확인 후 개선된 답변 재녹음
5. 설문조사 완료

## 🛠️ 기술 스택

- **Frontend**: Streamlit (웹 인터페이스)
- **Speech-to-Text**: OpenAI Whisper
- **AI Feedback**: OpenAI GPT-4o
- **Text-to-Speech**: ElevenLabs
- **Data Storage**: Google Drive (OAuth)
- **Document Generation**: ReportLab (PDF)

## 💻 로컬 개발 환경 설정

### 1. 필수 요구사항
- Python 3.8+
- OpenAI API 키
- ElevenLabs API 키

### 2. 설치 방법
```bash
# 레포지토리 클론
git clone https://github.com/YOUR_USERNAME/korean-speaking-experiment.git
cd korean-speaking-experiment

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 API 키들을 설정:
```bash
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVEN_VOICE_ID=your_voice_id
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

### 4. 로컬 실행
```bash
streamlit run main.py
```

## 🌐 Streamlit Cloud 배포

### 1. GitHub 레포지토리 준비
- 모든 파일을 GitHub에 업로드 (`.env` 파일 제외)
- `.gitignore`에 민감한 파일들 추가

### 2. Streamlit Cloud 설정
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. GitHub 계정으로 로그인
3. "New app" → 레포지토리 선택 → `main.py` 지정

### 3. Secrets 설정
앱 대시보드에서 "Manage app" → "Secrets"에 다음 추가:
```toml
OPENAI_API_KEY = "your_openai_api_key"
ELEVENLABS_API_KEY = "your_elevenlabs_api_key"  
ELEVEN_VOICE_ID = "your_voice_id"
GOOGLE_DRIVE_ENABLED = "true"
GOOGLE_DRIVE_FOLDER_ID = "your_folder_id"
```

## 📊 연구 데이터

### 수집 데이터
- 음성 녹음 파일 (1차, 2차 시도)
- STT 전사 텍스트
- AI 피드백 및 개선도 분석
- 참여자 배경 정보 (학습 기간, 자신감 수준)
- 사용자 만족도 설문 응답

### 개인정보 보호
- GDPR 완전 준수
- 익명화된 참여자 ID (Student01, Student02...)
- 암호화된 클라우드 저장
- 2년 후 자동 삭제
- 언제든 데이터 삭제 요청 가능

## 🔧 트러블슈팅

### 자주 발생하는 문제들

#### 1. API 키 오류
```
Error: OpenAI API key is required for feedback!
```
**해결방법**: Streamlit Cloud Secrets에 `OPENAI_API_KEY` 올바르게 설정

#### 2. 음성 녹음 문제
```
Could not transcribe audio. Please try again.
```
**해결방법**: 
- 마이크 권한 확인
- 브라우저에서 HTTPS 접속 확인
- 파일 업로드 방식으로 대체 시도

#### 3. TTS 생성 실패
```
TTS generation failed
```
**해결방법**: ElevenLabs API 키와 Voice ID 확인

#### 4. Google Drive 업로드 실패
```
Google Drive upload failed
```
**해결방법**: 
- OAuth credentials 설정 확인
- 폴더 권한 확인
- 일시적으로 비활성화: `GOOGLE_DRIVE_ENABLED = "false"`

## 📞 연구 문의

- **연구자**: 김정연 (이화여자대학교 국제대학원 한국학과)
- **이메일**: pen0226@gmail.com
- **연구 기관**: 이화여자대학교 연구윤리센터 (research@ewha.ac.kr)

## 📄 라이선스

이 프로젝트는 연구 목적으로 개발되었으며, 학술 연구 및 교육 목적으로만 사용 가능합니다.

## 🙏 참여해 주신 분들께 감사드립니다!

Your participation helps advance AI-powered language education research! 

여러분의 참여가 AI 언어 교육 연구 발전에 큰 도움이 됩니다! 🚀
