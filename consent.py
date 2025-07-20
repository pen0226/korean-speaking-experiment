"""
consent.py
연구 참여 동의서 처리 및 HTML 동의서 생성 모듈 (동의서와 배경정보 분리 버전)
"""

import streamlit as st
import csv
import os
from datetime import datetime, timedelta
from config import DATA_RETENTION_DAYS, FOLDERS, BACKGROUND_INFO, CURRENT_SESSION, SELF_EFFICACY_ITEMS, SELF_EFFICACY_SCALE


def enhanced_consent_section():
    """
    학생 친화적 동의 수집 섹션 (GDPR 준수) - 동의서만 처리
    
    Returns:
        bool: 동의 완료 여부
    """
    
    # 탭으로 정보 구성 (5개 탭, Privacy 3번째로 배치)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔬 Experiment Flow", "🎁 What You'll Get", "🔒 Your Privacy", "🛠️ AI Tools Used", "📞 Contact Info"])
    
    with tab1:
        st.markdown("""
        ### 🔬 Experiment Flow
        
        **📅 2 Sessions** (~15-20 mins each, 1 week apart)
        
        **🔄 Each Session:**
        
        🎙️ First Record → 🤖 AI Feedback → 🎙️ Second Record → 📝 Survey
        
        **💻 Optional:** 15-min Zoom chat about your experience
        """)
    
    with tab2:
        st.markdown("""
        ### 🎯 What You'll Get From This Study
        
        **🎁 For You:**
        - Personalized AI feedback on your Korean speaking
        - AI pronunciation examples to practice with
        - Quick tips for your Language Education Center interview
        - A free practice session—just like a mini Korean tutor
        
        **📚 For Research:**
        - Improve AI tools for Korean learners
        - Support a master's thesis project
        - Help shape future research and publications
        """)
    
    with tab3:
        st.markdown("""
        ### 🔒 Your Data is Kept Safe & You Stay In Control
        
        **🏠 How Your Data is Stored:**
        - Encrypted Google Cloud Storage bucket 
        - Your real name is never used - only nicknames → anonymous IDs
        - Only the researcher can access your data
        
        **⏰ How Long It's Kept:**
        - Maximum 2 years after the study ends
        
        **🌍 International Processing:**
        - AI services process data internationally (standard for AI tools)
        - Your data is protected under the same high security and privacy standards as Netflix, Spotify, and Google
        
        **✨ Your Rights (You're Always In Control!)**
        - 📧 **Contact anytime** to view your data  
        - ✏️ **Request corrections** if you spot any errors  
        - 🗑️ **Withdraw at any time** — if before analysis starts, your data will be deleted; afterward, only anonymized results remain  
        - 📤 **Request a copy of your data** after the study ends 
        """)
    
    with tab4:
        st.markdown("""
        ### 🛠️ AI Tools Used:
        
        - **OpenAI Whisper** for transcription
        - **GPT-4** for feedback
        - **ElevenLabs** for pronunciation samples
        """)
    
    with tab5:
        st.markdown("""
        ### 📞 Questions?
        
        **👩‍🎓 Researcher:**
        - **Jeongyeon Kim** (Master's student at Ewha Womans University)
        - **Email:** pen0226@gmail.com
        
        **🏛️ University Ethics Office:**
        - **Ewha Womans University Research Ethics Center**
        - **Email:** research@ewha.ac.kr
        - **Phone:** 02-3277-7152
        """)
    
    # 간단하고 친근한 동의 체크박스
    st.markdown("---")
    st.markdown("### 🤝 Ready to Start? Just Check These Boxes!")
    
    # 시각적으로 더 친근한 체크박스 (3개로 간소화)
    col1, col2 = st.columns([1, 4])
    
    with col2:
        consent_participation = st.checkbox(
            "✅ **I agree to join this Korean speaking practice and understand it's voluntary.**"
        )
        
        consent_processing = st.checkbox(
            "🎙️ **I allow voice recording & AI feedback.**"
        )
        
        consent_data_rights = st.checkbox(
            "🛡️ **I allow anonymous use of my data for research and know I can withdraw anytime.**"
        )
        
    
    # 모든 필수 동의가 완료되었는지 확인
    essential_consents = [consent_participation, consent_processing, consent_data_rights]
    
    if all(essential_consents):
        # 동의 완료 시점에 timestamp 생성
        consent_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 성공 메시지 (원래 메시지 유지)
        st.success(f"🌟 Awesome! Welcome to your Korean practice session! ({consent_timestamp})")
        
        # 동의 정보 세션에 저장 (최종 확인은 자동으로 True)
        consent_details = {
            'consent_participation': consent_participation,
            'consent_processing': consent_processing,
            'consent_data_rights': consent_data_rights,
            'consent_final_confirm': True,  # 자동으로 True 설정
            'consent_timestamp': consent_timestamp
        }
        
        # 세션 상태에 저장
        save_consent_to_session(consent_details)
        
        # 다음 단계 버튼
        st.markdown("---")
        if st.button("🔄 Next: Background Information", type="primary", use_container_width=True):
            return True
        
        return False
    else:
        st.warning("📝 Please check all the boxes above to continue")
        return False


def collect_background_information():
    """
    배경 정보 수집 섹션 (닉네임 + 학습기간 + 자신감 + 자기효능감 8문항)
    
    Returns:
        tuple: (background_completed, background_details)
    """
    st.markdown("### 👤 Choose Your Nickname")
    st.info("🔗 **Use the exact same nickname** in Session 1 & Session 2 — links your data.")
    
    nickname = st.text_input(
        "Your nickname:",
        placeholder="e.g., KoreanLearner123, MyNickname, Student_A, etc.",
        help="Your nickname becomes an anonymous ID like 'Student01'. Your real identity stays private!"
    )
    
    if not nickname.strip():
        st.warning("👆 Please enter a nickname to continue")
        return False, None
    
    st.markdown("---")
    st.markdown("### 📊 Tell About Your Korean Learning Journey")
    
    # 학습 기간 질문
    st.markdown("**🕐 How long have you been learning Korean?**")
    
    learning_duration = st.radio(
        "Pick the option that fits you best:",
        options=BACKGROUND_INFO["learning_duration_options"],
        key="bg_learning_duration",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 자신감 질문
    st.markdown("**🌟 How confident do you feel speaking Korean right now?**")
    
    speaking_confidence = st.radio(
        "Choose what describes you best:",
        options=BACKGROUND_INFO["confidence_options"],
        key="bg_speaking_confidence",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 자기효능감 문항 6개 추가
    st.markdown("### 🎯 Korean Speaking Self-Efficacy")
    st.markdown("*Please rate how much you agree with each statement:*")
    
    self_efficacy_scores = {}
    
    for i, item in enumerate(SELF_EFFICACY_ITEMS, 1):
        st.markdown(f"**{i}. {item}**")
        
        score = st.radio(
            f"Your rating for statement {i}:",
            options=SELF_EFFICACY_SCALE,
            key=f"radio_self_efficacy_{i}",  # 위젯 키를 다르게 설정
            label_visibility="collapsed"
        )
        
        if score:
            # "1️⃣ Strongly Disagree" → 1로 변환
            score_value = int(score.split('️⃣ ')[0].replace('1', '1').replace('2', '2').replace('3', '3').replace('4', '4').replace('5', '5'))
            self_efficacy_scores[f'self_efficacy_{i}'] = score_value
        
        # 문항 사이 여백
        if i < len(SELF_EFFICACY_ITEMS):
            st.markdown("")
    
    # 모든 필수 항목이 선택되었는지 확인
    required_items = [learning_duration, speaking_confidence] + [nickname.strip()]
    all_efficacy_answered = len(self_efficacy_scores) == len(SELF_EFFICACY_ITEMS)
    
    if all(required_items) and all_efficacy_answered:
        background_details = {
            'nickname': nickname.strip(),
            'learning_duration': learning_duration,
            'speaking_confidence': speaking_confidence,
            **self_efficacy_scores  # 자기효능감 점수 8개 추가
        }
        return True, background_details
    else:
        missing_count = len(SELF_EFFICACY_ITEMS) - len(self_efficacy_scores)
        if missing_count > 0:
            st.caption(f"📝 Please answer all questions above ({missing_count} self-efficacy items remaining)")
        else:
            st.caption("📝 Please answer all questions above")
        return False, None


def save_consent_to_session(consent_details):
    """
    동의 정보를 세션 상태에 저장
    
    Args:
        consent_details: 동의 세부 정보 딕셔너리
    """
    st.session_state.consent_given = True
    st.session_state.consent_timestamp = consent_details['consent_timestamp']
    st.session_state.consent_participation = consent_details['consent_participation']
    st.session_state.consent_processing = consent_details['consent_processing']
    st.session_state.consent_data_rights = consent_details['consent_data_rights']
    st.session_state.consent_final_confirmation = consent_details['consent_final_confirm']
    st.session_state.gdpr_compliant = True


def save_background_to_session(background_details):
    """
    배경 정보를 세션 상태에 저장 (자기효능감 포함)
    
    Args:
        background_details: 배경 정보 딕셔너리 (자기효능감 점수 포함)
    """
    st.session_state.original_nickname = background_details['nickname']
    st.session_state.learning_duration = background_details['learning_duration']
    st.session_state.speaking_confidence = background_details['speaking_confidence']
    
    # 자기효능감 점수 6개 저장
    for i in range(1, 7):
        key = f'self_efficacy_{i}'
        if key in background_details:
            setattr(st.session_state, key, background_details[key])


def find_or_create_anonymous_id(nickname):
    """
    닉네임 기반으로 기존 익명 ID를 찾거나 새로 생성 (세션 간 매칭을 위함)
    
    Args:
        nickname: 사용자 닉네임
        
    Returns:
        str: 기존 또는 새로 생성된 익명 ID
    """
    try:
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        
        # 기존 매핑 파일에서 닉네임 검색
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Nickname', '').strip().lower() == nickname.lower():
                        existing_id = row.get('Anonymous_ID', '').strip()
                        if existing_id:
                            return existing_id
        
        # 기존 닉네임 없음 → 새 ID 생성
        return generate_new_anonymous_id()
        
    except Exception:
        return f"Student{datetime.now().strftime('%m%d%H%M')}"


def generate_new_anonymous_id():
    """
    새로운 순차적 익명 ID 생성 (Student01, Student02, ...)
    
    Returns:
        str: 생성된 새 익명 ID
    """
    try:
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        last_number = 0
        
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:  # 헤더 제외
                    if line.strip() and line.startswith('Student'):
                        try:
                            number = int(line.split(',')[0].replace('Student', ''))
                            last_number = max(last_number, number)
                        except:
                            continue
        
        next_number = last_number + 1
        return f"Student{next_number:02d}"
        
    except Exception:
        return f"Student{datetime.now().strftime('%m%d%H%M')}"


def save_nickname_mapping(anonymous_id, nickname, consent_details=None, background_details=None):
    """
    닉네임 매핑 정보를 CSV 파일에 저장 (자기효능감 점수 포함)
    
    Args:
        anonymous_id: 익명 ID
        nickname: 사용자 닉네임
        consent_details: 동의 세부 정보
        background_details: 배경 정보 (자기효능감 포함)
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        os.makedirs(FOLDERS["data"], exist_ok=True)
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        
        # 헤더가 없으면 생성 (자기효능감 필드 6개 추가)
        if not os.path.exists(mapping_file):
            with open(mapping_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                headers = [
                    'Anonymous_ID', 'Nickname', 'Timestamp', 'Data_Retention_Until',
                    'Deletion_Requested', 'Consent_Participation', 'Consent_Processing',
                    'Consent_Data_Rights', 'Consent_Final_Confirm', 'GDPR_Compliant',
                    'Learning_Duration', 'Speaking_Confidence', 'Session_Count', 'Last_Session'
                ]
                # 자기효능감 필드 6개 추가
                for i in range(1, 7):
                    headers.append(f'Self_Efficacy_{i}')
                headers.append('Notes')
                
                writer.writerow(headers)
        
        # 기존 엔트리 확인
        all_rows = []
        existing_entry = None
        
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                all_rows = list(reader)
                for row in all_rows:
                    if row.get('Nickname', '').strip().lower() == nickname.lower():
                        existing_entry = row
                        break
        
        # 기본값 설정
        if not consent_details:
            consent_details = {
                'consent_participation': True, 'consent_processing': True,
                'consent_data_rights': True, 'consent_final_confirm': True
            }
        if not background_details:
            background_details = {'learning_duration': '', 'speaking_confidence': ''}
        
        retention_until = (datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')
        
        # 자기효능감 점수 추출 (6개)
        efficacy_scores = []
        for i in range(1, 7):
            key = f'self_efficacy_{i}'
            efficacy_scores.append(background_details.get(key, ''))
        
        if existing_entry:
            # 기존 엔트리 업데이트
            session_count = int(existing_entry.get('Session_Count', 0)) + 1
            with open(mapping_file, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'Anonymous_ID', 'Nickname', 'Timestamp', 'Data_Retention_Until',
                    'Deletion_Requested', 'Consent_Participation', 'Consent_Processing',
                    'Consent_Data_Rights', 'Consent_Final_Confirm', 'GDPR_Compliant',
                    'Learning_Duration', 'Speaking_Confidence', 'Session_Count', 'Last_Session'
                ]
                for i in range(1, 7):
                    fieldnames.append(f'Self_Efficacy_{i}')
                fieldnames.append('Notes')
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in all_rows:
                    if row.get('Nickname', '').strip().lower() == nickname.lower():
                        row.update({
                            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Session_Count': session_count,
                            'Last_Session': CURRENT_SESSION,
                            'Learning_Duration': background_details.get('learning_duration', row.get('Learning_Duration', '')),
                            'Speaking_Confidence': background_details.get('speaking_confidence', row.get('Speaking_Confidence', ''))
                        })
                        # 자기효능감 점수 업데이트 (6개)
                        for i in range(1, 7):
                            key = f'Self_Efficacy_{i}'
                            row[key] = background_details.get(f'self_efficacy_{i}', row.get(key, ''))
                    writer.writerow(row)
        else:
            # 새 엔트리 추가
            with open(mapping_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                row_data = [
                    anonymous_id, nickname, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    retention_until, 'FALSE',
                    consent_details.get('consent_participation', True),
                    consent_details.get('consent_processing', True),
                    consent_details.get('consent_data_rights', True),
                    consent_details.get('consent_final_confirm', True),
                    'TRUE',
                    background_details.get('learning_duration', ''),
                    background_details.get('speaking_confidence', ''),
                    1, CURRENT_SESSION
                ]
                # 자기효능감 점수 6개 추가
                row_data.extend(efficacy_scores)
                row_data.append('')  # Notes
                
                writer.writerow(row_data)
        
        return True
    except Exception:
        return False


def generate_consent_html(anonymous_id, consent_details, consent_timestamp):
    """
    한글 완벽 지원 HTML 동의서 생성
    
    Args:
        anonymous_id: 익명 ID
        consent_details: 동의 세부 정보
        consent_timestamp: 동의 시간
        
    Returns:
        tuple: (html_filename, success_status)
    """
    try:
        html_filename = os.path.join(FOLDERS["data"], f"{anonymous_id}_consent.html")
        
        # HTML 콘텐츠 생성
        html_content = _build_html_consent_content(anonymous_id, consent_details, consent_timestamp)
        
        # HTML 파일 저장
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_filename, True
        
    except Exception as e:
        return None, f"HTML generation failed: {str(e)}"


def _build_html_consent_content(anonymous_id, consent_details, consent_timestamp):
    """
    HTML 동의서 내용 구성 (한글 완벽 지원)
    """
    
    # 동의 항목들 체크 표시
    participation_check = "✓" if consent_details.get('consent_participation') else "✗"
    processing_check = "✓" if consent_details.get('consent_processing') else "✗"
    data_rights_check = "✓" if consent_details.get('consent_data_rights') else "✗"
    final_check = "✓" if consent_details.get('consent_final_confirm') else "✗"
    
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>연구 참여 동의서 - Research Participation Consent Form</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #0369a1;
            padding-bottom: 20px;
        }}
        .title {{
            font-size: 24px;
            font-weight: bold;
            color: #0369a1;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 18px;
            color: #666;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: bold;
            color: #0369a1;
            border-left: 4px solid #0369a1;
            padding-left: 10px;
            margin-bottom: 15px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .info-table th, .info-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        .info-table th {{
            background-color: #f8f9fa;
            font-weight: bold;
        }}
        .consent-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .consent-table th, .consent-table td {{
            border: 1px solid #333;
            padding: 15px 10px;
            text-align: left;
            vertical-align: top;
        }}
        .consent-table th {{
            background-color: #666;
            color: white;
            font-weight: bold;
            text-align: center;
        }}
        .consent-table .agreed {{
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            color: #059669;
        }}
        .rights-list {{
            list-style: none;
            padding-left: 0;
        }}
        .rights-list li {{
            margin-bottom: 10px;
            padding-left: 20px;
            position: relative;
        }}
        .rights-list li:before {{
            content: "•";
            color: #0369a1;
            font-weight: bold;
            position: absolute;
            left: 0;
        }}
        .contact-info {{
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #0369a1;
        }}
        .signature-section {{
            background-color: #f0fdf4;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #059669;
            margin-top: 30px;
        }}
        .print-note {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }}
        @media print {{
            .print-note {{ display: none; }}
            body {{ margin: 0; padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="print-note">
        <strong>💡 사용 방법:</strong> 브라우저에서 Ctrl+P (또는 Cmd+P)를 눌러 PDF로 저장하실 수 있습니다.<br>
        <strong>💡 How to use:</strong> Press Ctrl+P (or Cmd+P) in your browser to save as PDF.
    </div>

    <div class="header">
        <div class="title">Research Participation Consent Form</div>
        <div class="title">연구 참여 동의서</div>
        <div class="subtitle">AI-Based Korean Speaking Feedback System Study</div>
        <div class="subtitle">AI 기반 한국어 말하기 피드백 시스템 연구</div>
    </div>

    <div class="section">
        <div class="section-title">Research Information / 연구 정보</div>
        <table class="info-table">
            <tr>
                <th>Principal Investigator / 연구책임자</th>
                <td>Jeongyeon Kim / 김정연</td>
            </tr>
            <tr>
                <th>Institution / 소속기관</th>
                <td>Ewha Womans University, Graduate School of International Studies / 이화여자대학교 국제대학원</td>
            </tr>
            <tr>
                <th>Contact / 연락처</th>
                <td>pen0226@gmail.com</td>
            </tr>
            <tr>
                <th>Research Title / 연구제목</th>
                <td>Effects of AI-Based Self-Feedback Systems on Korean Learners' Speaking Accuracy and Error Recognition<br>
                AI 기반 자가 피드백 시스템이 한국어 학습자의 말하기 정확성과 오류 인식에 미치는 영향</td>
            </tr>
            <tr>
                <th>Academic Use / 학술적 활용</th>
                <td>Master's thesis research, potential academic conference presentations, and possible scholarly journal publications<br>
                석사논문 연구, 학술대회 발표 가능성, 학술지 게재 가능성</td>
            </tr>
            <tr>
                <th>Purpose / 연구 목적</th>
                <td>To improve AI feedback systems for Korean language education and help future students prepare for language placement interviews<br>
                한국어 교육용 AI 피드백 시스템 개선 및 향후 학생들의 언어교육원 배치고사 준비 지원</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Participant Information / 참여자 정보</div>
        <table class="info-table">
            <tr>
                <th>Participant ID / 참여자 ID</th>
                <td>{anonymous_id}</td>
            </tr>
            <tr>
                <th>Consent Date / 동의 날짜</th>
                <td>{consent_timestamp}</td>
            </tr>
            <tr>
                <th>Consent Method / 동의 방법</th>
                <td>Electronic Checkbox / 전자 체크박스</td>
            </tr>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Consent Items / 동의 항목</div>
        <table class="consent-table">
            <thead>
                <tr>
                    <th>Consent Item / 동의 항목</th>
                    <th>Agreed<br>동의</th>
                    <th>Description / 설명</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Research Participation<br><strong>연구 참여</strong></td>
                    <td class="agreed">{participation_check}</td>
                    <td>Voluntary participation in the research study<br><strong>연구에 자발적 참여</strong></td>
                </tr>
                <tr>
                    <td>Voice Recording & AI Processing<br><strong>음성 녹음 및 AI 처리</strong></td>
                    <td class="agreed">{processing_check}</td>
                    <td>Voice recording and AI feedback processing (Whisper→GPT→Elevenlabs)<br><strong>음성 녹음 및 AI 피드백 처리 (Whisper→GPT→Elevenlabs)</strong></td>
                </tr>
                <tr>
                    <td>Data Use & Rights Understanding<br><strong>데이터 사용 및 권리 이해</strong></td>
                    <td class="agreed">{data_rights_check}</td>
                    <td>Anonymous data use for research and understanding of withdrawal rights<br><strong>연구를 위한 익명 데이터 사용 및 철회 권리 이해</strong></td>
                </tr>
                <tr>
                    <td>Final Confirmation<br><strong>최종 확인</strong></td>
                    <td class="agreed">{final_check}</td>
                    <td>Final confirmation of all consent items<br><strong>모든 동의 항목에 대한 최종 확인</strong></td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Your Rights (GDPR) / 귀하의 권리 (GDPR)</div>
        <p>You have the following rights regarding your personal data: / <strong>개인정보와 관련하여 다음과 같은 권리를 가집니다:</strong></p>
        <ul class="rights-list">
            <li><strong>Right to Access / 접근권:</strong> Request access to your data / 본인 데이터 열람 요청</li>
            <li><strong>Right to Rectification / 정정권:</strong> Correct inaccurate information / 부정확한 정보 수정</li>
            <li><strong>Right to Erasure / 삭제권:</strong> Request deletion of your data / 데이터 삭제 요청</li>
            <li><strong>Right to Object / 이의제기권:</strong> Object to data processing / 데이터 처리에 대한 이의제기</li>
            <li><strong>Right to Withdraw / 철회권:</strong> Withdraw consent at any time / 언제든지 동의 철회</li>
        </ul>
    </div>

    <div class="section">
        <div class="section-title">Contact for Data Rights / 데이터 권리 관련 연락처</div>
        <div class="contact-info">
            <p><strong>To exercise your rights or withdraw consent / 권리 행사 또는 동의 철회:</strong></p>
            <p>📧 <strong>Email:</strong> pen0226@gmail.com<br>
            📋 <strong>Subject:</strong> Data Rights Request - {anonymous_id}</p>
            
            <p><strong>Ewha Womans University Research Ethics Center / 이화여자대학교 연구윤리센터:</strong></p>
            <p>📧 <strong>Email:</strong> research@ewha.ac.kr<br>
            📞 <strong>Phone:</strong> 02-3277-7152</p>
        </div>
    </div>

    <div class="signature-section">
        <div class="section-title">Electronic Consent Confirmation / 전자적 동의 확인</div>
        <p>By checking all consent items above, the participant has provided electronic consent to participate in this research study in accordance with GDPR and Korean research ethics guidelines.</p>
        <p><strong>위의 모든 동의 항목을 체크함으로써 참여자는 GDPR 및 한국 연구윤리 가이드라인에 따라 본 연구 참여에 대한 전자적 동의를 제공하였습니다.</strong></p>
        
        <table class="info-table" style="margin-top: 20px;">
            <tr>
                <th>Consent completed / 동의 완료</th>
                <td>{consent_timestamp}</td>
            </tr>
            <tr>
                <th>Participant ID / 참여자 ID</th>
                <td>{anonymous_id}</td>
            </tr>
            <tr>
                <th>Method / 방법</th>
                <td>Electronic checkbox confirmation / 전자 체크박스 확인</td>
            </tr>
        </table>
    </div>

    <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 14px;">
        <p>Generated by Korean Speaking Research System / 한국어 말하기 연구 시스템에서 생성됨</p>
        <p>For research inquiries: pen0226@gmail.com</p>
    </div>
</body>
</html>"""
    
    return html_content


def display_consent_html_download(html_filename, anonymous_id):
    """
    HTML 동의서 다운로드 버튼 표시
    
    Args:
        html_filename: HTML 파일 경로
        anonymous_id: 익명 ID
    """
    if html_filename and os.path.exists(html_filename):
        try:
            with open(html_filename, "r", encoding='utf-8') as f:
                html_content = f.read()
                
            st.download_button(
                label="📄 Download Your Consent Form (HTML)",
                data=html_content.encode('utf-8'),
                file_name=f"{anonymous_id}_consent.html",
                mime="text/html"
            )
            
            st.info("💡 **How to save as PDF:** Open the downloaded HTML file in your browser, then press Ctrl+P (or Cmd+P) and choose 'Save as PDF'")
            
        except Exception:
            st.error("HTML download failed")


def handle_consent_only():
    """
    동의서만 처리하는 함수
    
    Returns:
        bool: 동의 완료 여부
    """
    consent_completed = enhanced_consent_section()
    return consent_completed


def handle_background_info_only():
    """
    배경 정보만 처리하는 함수 (닉네임 + 학습기간 + 자신감 + 자기효능감)
    
    Returns:
        bool: 배경 정보 수집 완료 여부
    """
    background_completed, background_details = collect_background_information()
    
    if background_completed:
        # 시작 버튼
        st.markdown("---")
        st.markdown("### 🎉 Ready to Start Your Korean Practice?")
        
        if st.button("🚀 Let's Start!", type="primary", use_container_width=True):
            return _process_background_completion(background_details)
    
    return False


def _process_background_completion(background_details):
    """
    배경 정보 완료 처리 (HTML 파일 저장)
    """
    nickname = background_details['nickname']
    
    # 익명 ID 생성
    anonymous_id = find_or_create_anonymous_id(nickname)
    
    # 세션에서 저장된 동의 정보 가져오기
    consent_details = {
        'consent_participation': getattr(st.session_state, 'consent_participation', True),
        'consent_processing': getattr(st.session_state, 'consent_processing', True),
        'consent_data_rights': getattr(st.session_state, 'consent_data_rights', True),
        'consent_final_confirm': getattr(st.session_state, 'consent_final_confirmation', True),
        'consent_timestamp': getattr(st.session_state, 'consent_timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    }
    
    # 매핑 정보 저장 (자기효능감 포함)
    save_nickname_mapping(anonymous_id, nickname, consent_details, background_details)
    save_background_to_session(background_details)
    
    # HTML 동의서 생성
    with st.spinner("🎯 Setting up your Korean practice session..."):
        html_filename, html_result = generate_consent_html(
            anonymous_id, 
            consent_details,
            consent_details['consent_timestamp']
        )
        
        if html_filename:
            st.session_state.consent_file = html_filename
            st.session_state.consent_file_type = "html"
            st.success("🎉 Perfect! You're all set up!")
            st.info("📦 Your consent form is safely stored and will be included in the secure backup")
            display_consent_html_download(html_filename, anonymous_id)
        else:
            st.success("🎉 Great! You're ready to start practicing Korean!")
            st.info("✅ Your consent has been recorded securely")
    
    # 세션에 ID 저장
    st.session_state.session_id = anonymous_id
    
    return True