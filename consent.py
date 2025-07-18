"""
consent.py
연구 참여 동의서 처리 및 PDF 생성 모듈 (학생 친화적 버전 - GDPR 준수)
"""

import streamlit as st
import csv
import os
from datetime import datetime, timedelta
from config import DATA_RETENTION_DAYS, FOLDERS, BACKGROUND_INFO, CURRENT_SESSION

# ReportLab import (전역 스코프)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def enhanced_consent_section():
    """
    학생 친화적 동의 수집 섹션 (GDPR 준수)
    
    Returns:
        tuple: (consent_completed, consent_details)
    """
    
    # 친근한 설명으로 시작
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
    
    # 탭으로 정보 구성 (덜 overwhelming하게)
    tab1, tab2, tab3 = st.tabs(["🎮 What You'll Experience", "🔒 Your Privacy", "📞 Contact Info"])
    
    with tab1:
        st.markdown("""
        ### 🎮 Practice Flow 
        - 2 sessions, each ~15-20 mins
        - Sessions held about a week apart       
        1. **First recording**
        2. **Get AI feedback**
        3. **Second recording**
        4. **Quick survey**           
        
        **Optional Zoom Interview** 💻 
        - 15-minute call to discuss your experience  
        - Audio recorded (video is optional) 
        
        **AI Tools Used:** 🛠️
        - **OpenAI Whisper** for transcription  
        - **GPT-4** for feedback  
        - **ElevenLabs** for pronunciation samples
        """)
    
    with tab2:
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
    
    with tab3:
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
    st.markdown("""
    ### 🤝 Ready to Start? Just Check These Boxes!
    
    *Don't worry - these are just to make sure you understand what the study involves.*
    """)
    
    # 시각적으로 더 친근한 체크박스 (3개로 간소화)
    col1, col2 = st.columns([1, 4])
    
    with col2:
        consent_participation = st.checkbox(
            "✅ **I agree to join this Korean speaking practice and understand it's voluntary.**"
        )
        
        consent_processing = st.checkbox(
            "🎙️ **I allow voice recording & AI feedback (Whisper→GPT→TTS).**"
        )
        
        consent_data_rights = st.checkbox(
            "🛡️ **I allow anonymous use of my data for research and know I can withdraw anytime.**"
        )
        
    
    # 모든 필수 동의가 완료되었는지 확인
    essential_consents = [consent_participation, consent_processing, consent_data_rights]
    
    if all(essential_consents):
        
        final_consent = st.checkbox(
            "✅ **Let's do this! I'm ready to start practicing Korean with AI feedback.**"
        )
        
        if final_consent:
            consent_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 성공 메시지
            st.success(f"🌟 Awesome! Welcome to your Korean practice session! ({consent_timestamp})")
            
            # 동의 정보 세션에 저장 (3개 항목으로 간소화)
            consent_details = {
                'consent_participation': consent_participation,
                'consent_processing': consent_processing,
                'consent_data_rights': consent_data_rights,
                'consent_final_confirm': final_consent,
                'consent_timestamp': consent_timestamp
            }
            
            # 세션 상태에 저장
            save_consent_to_session(consent_details)
            
            return True, consent_details
        else:
            st.info("👆 Just check the final box when you're ready to start!")
            return False, None
    else:
        st.info("📝 Please check all the boxes above to continue - they help follow research guidelines!")
        return False, None


def collect_background_information():
    """
    친근한 배경 정보 수집 섹션
    
    Returns:
        tuple: (background_completed, background_details)
    """
    st.markdown("""
    ### 📊 Tell About Your Korean Learning Journey
    
    *This helps provide better feedback!*
    """)
    
    # 학습 기간 질문 - 더 친근하게
    st.markdown("**🕐 How long have you been learning Korean?**")
    
    learning_duration = st.radio(
        "Pick the option that fits you best:",
        options=BACKGROUND_INFO["learning_duration_options"],
        key="bg_learning_duration",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 자신감 질문 - 격려하는 톤으로
    st.markdown("**🌟 How confident do you feel speaking Korean right now?**")
    
    speaking_confidence = st.radio(
        "Choose what describes you best:",
        options=BACKGROUND_INFO["confidence_options"],
        key="bg_speaking_confidence",
        label_visibility="collapsed"
    )
    
    # 모든 필수 항목이 선택되었는지 확인
    if learning_duration and speaking_confidence:
        background_details = {
            'learning_duration': learning_duration,
            'speaking_confidence': speaking_confidence
        }
        return True, background_details
    else:
        st.info("📝 Please answer both questions so the feedback can be personalized!")
        return False, None


def save_consent_to_session(consent_details):
    """
    동의 정보를 세션 상태에 저장 (3개 항목으로 간소화)
    
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
    배경 정보를 세션 상태에 저장
    
    Args:
        background_details: 배경 정보 딕셔너리
    """
    st.session_state.learning_duration = background_details['learning_duration']
    st.session_state.speaking_confidence = background_details['speaking_confidence']


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
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Nickname', '').strip().lower() == nickname.lower():
                            # 기존 닉네임 발견! 기존 ID 반환
                            existing_id = row.get('Anonymous_ID', '').strip()
                            if existing_id:
                                print(f"✅ Found existing ID for '{nickname}': {existing_id}")
                                return existing_id
            except Exception as e:
                print(f"Error reading mapping file: {e}")
        
        # 기존 닉네임 없음 → 새 ID 생성
        return generate_new_anonymous_id()
        
    except Exception as e:
        print(f"Error in find_or_create_anonymous_id: {e}")
        # 오류 시 타임스탬프 기반 ID
        return f"Student{datetime.now().strftime('%m%d%H%M')}"


def generate_new_anonymous_id():
    """
    새로운 순차적 익명 ID 생성 (Student01, Student02, ...)
    
    Returns:
        str: 생성된 새 익명 ID
    """
    try:
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        
        # 기존 파일에서 마지막 번호 찾기
        last_number = 0
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[1:]:  # 헤더 제외
                        if line.strip():
                            parts = line.strip().split(',')
                            if len(parts) > 0 and parts[0].startswith('Student'):
                                try:
                                    number = int(parts[0].replace('Student', ''))
                                    last_number = max(last_number, number)
                                except:
                                    continue
            except:
                pass
        
        # 다음 번호로 ID 생성
        next_number = last_number + 1
        new_id = f"Student{next_number:02d}"  # Student01, Student02, ...
        print(f"✨ Generated new ID: {new_id}")
        return new_id
        
    except Exception as e:
        print(f"Error generating new ID: {e}")
        # 오류 시 타임스탬프 기반 ID
        return f"Student{datetime.now().strftime('%m%d%H%M')}"


def save_nickname_mapping(anonymous_id, nickname, consent_details=None, background_details=None):
    """
    닉네임 매핑 정보를 CSV 파일에 저장 (연구자 전용) - 3개 동의 항목으로 간소화
    
    Args:
        anonymous_id: 익명 ID
        nickname: 사용자 닉네임
        consent_details: 동의 세부 정보
        background_details: 배경 정보
        
    Returns:
        bool: 저장 성공 여부
    """
    try:
        os.makedirs(FOLDERS["data"], exist_ok=True)
        mapping_file = os.path.join(FOLDERS["data"], 'nickname_mapping.csv')
        
        # 헤더가 없으면 생성 (3개 동의 항목으로 변경)
        if not os.path.exists(mapping_file):
            with open(mapping_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Anonymous_ID', 
                    'Nickname', 
                    'Timestamp',
                    'Data_Retention_Until',
                    'Deletion_Requested',
                    'Consent_Participation',
                    'Consent_Processing',
                    'Consent_Data_Rights',
                    'Consent_Final_Confirm',
                    'GDPR_Compliant',
                    'Learning_Duration',
                    'Speaking_Confidence',
                    'Session_Count',
                    'Last_Session',
                    'Notes'
                ])
        
        # 기존 엔트리 확인 (닉네임으로)
        existing_entry = None
        all_rows = []
        
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                all_rows = list(reader)
                
                for row in reader:
                    if row.get('Nickname', '').strip().lower() == nickname.lower():
                        existing_entry = row
                        break
        
        # 데이터 보관 만료일 계산
        retention_until = (datetime.now() + timedelta(days=DATA_RETENTION_DAYS)).strftime('%Y-%m-%d')
        
        # 동의 세부 정보 처리 (3개 항목으로 변경)
        if consent_details is None:
            consent_details = {
                'consent_participation': True,
                'consent_processing': True,
                'consent_data_rights': True,
                'consent_final_confirm': True,
            }
        
        # 배경 정보 처리
        if background_details is None:
            background_details = {
                'learning_duration': '',
                'speaking_confidence': ''
            }
        
        if existing_entry:
            # 기존 엔트리 업데이트 (세션 수 증가)
            session_count = int(existing_entry.get('Session_Count', 0)) + 1
            
            # 모든 행을 다시 쓰면서 해당 행만 업데이트
            with open(mapping_file, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'Anonymous_ID', 'Nickname', 'Timestamp', 'Data_Retention_Until',
                    'Deletion_Requested', 'Consent_Participation', 'Consent_Processing',
                    'Consent_Data_Rights', 'Consent_Final_Confirm', 'GDPR_Compliant', 
                    'Learning_Duration', 'Speaking_Confidence', 'Session_Count', 'Last_Session', 'Notes'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in all_rows:
                    if row.get('Nickname', '').strip().lower() == nickname.lower():
                        # 기존 엔트리 업데이트
                        row.update({
                            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Session_Count': session_count,
                            'Last_Session': CURRENT_SESSION,
                            'Learning_Duration': background_details.get('learning_duration', row.get('Learning_Duration', '')),
                            'Speaking_Confidence': background_details.get('speaking_confidence', row.get('Speaking_Confidence', ''))
                        })
                    writer.writerow(row)
        else:
            # 새 엔트리 추가
            with open(mapping_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    anonymous_id,
                    nickname,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    retention_until,
                    'FALSE',
                    consent_details.get('consent_participation', True),
                    consent_details.get('consent_processing', True),
                    consent_details.get('consent_data_rights', True),
                    consent_details.get('consent_final_confirm', True),
                    'TRUE',
                    background_details.get('learning_duration', ''),
                    background_details.get('speaking_confidence', ''),
                    1,  # 첫 참여이므로 세션 수는 1
                    CURRENT_SESSION,  # 현재 세션
                    ''
                ])
        
        return True
    except Exception as e:
        print(f"Mapping save failed: {e}")
        return False


def generate_consent_pdf(anonymous_id, consent_details, consent_timestamp):
    """
    참여자 동의서를 PDF로 생성 (논문 제출용)
    
    Args:
        anonymous_id: 익명 ID
        consent_details: 동의 세부 정보
        consent_timestamp: 동의 시간
        
    Returns:
        tuple: (pdf_filename, success_status)
    """
    if not REPORTLAB_AVAILABLE:
        return None, "reportlab not installed. Run: pip install reportlab"
    
    try:
        # PDF 파일명
        pdf_filename = os.path.join(FOLDERS["data"], f"{anonymous_id}_consent.pdf")
        
        # PDF 문서 생성
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4, topMargin=1*inch)
        story = []
        styles = getSampleStyleSheet()
        
        # 커스텀 스타일
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1  # 중앙 정렬
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.darkblue
        )
        
        # PDF 내용 구성
        story.extend(_build_pdf_content(anonymous_id, consent_details, consent_timestamp, 
                                       title_style, header_style, styles))
        
        # PDF 생성
        doc.build(story)
        
        return pdf_filename, True
        
    except Exception as e:
        return None, f"PDF generation failed: {str(e)}"


def _build_pdf_content(anonymous_id, consent_details, consent_timestamp, 
                      title_style, header_style, styles):
    """
    PDF 내용 구성 헬퍼 함수 (영한 병기) - 3개 동의 항목으로 간소화
    """
    story = []
    
    # 제목 (영한 병기)
    story.append(Paragraph("Research Participation Consent Form", title_style))
    story.append(Paragraph("연구 참여 동의서", title_style))
    story.append(Paragraph("AI-Based Korean Speaking Feedback System Study", title_style))
    story.append(Paragraph("AI 기반 한국어 말하기 피드백 시스템 연구", title_style))
    story.append(Spacer(1, 20))
    
    # 연구 정보 (영한 병기)
    story.append(Paragraph("Research Information / 연구 정보", header_style))
    research_info = """
    <b>Principal Investigator / 연구책임자:</b> Jeongyeon Kim<br/>
    <b>Institution / 소속기관:</b> Ewha Womans University, Graduate School / 이화여자대학교 대학원<br/>
    <b>Contact / 연락처:</b> pen0226@gmail.com<br/>
    <b>Research Title / 연구제목:</b> Effects of AI-Based Self-Feedback Systems on Korean Learners' Speaking Accuracy and Error Recognition / AI 기반 자가 피드백 시스템이 한국어 학습자의 말하기 정확성과 오류 인식에 미치는 영향<br/>
    <b>Academic Use / 학술적 활용:</b> Master's thesis research, potential academic conference presentations, and possible scholarly journal publications / 석사논문 연구, 학술대회 발표 가능성, 학술지 게재 가능성<br/>
    <b>Purpose / 연구 목적:</b> To improve AI feedback systems for Korean language education and help future students prepare for language placement interviews / 한국어 교육용 AI 피드백 시스템 개선 및 향후 학생들의 언어교육원 배치고사 준비 지원<br/>
    """
    story.append(Paragraph(research_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 참여자 정보 (영한 병기)
    story.append(Paragraph("Participant Information / 참여자 정보", header_style))
    participant_info = f"""
    <b>Participant ID / 참여자 ID:</b> {anonymous_id}<br/>
    <b>Consent Date / 동의 날짜:</b> {consent_timestamp}<br/>
    <b>Consent Method / 동의 방법:</b> Electronic Checkbox / 전자 체크박스<br/>
    """
    story.append(Paragraph(participant_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 동의 항목 표 (영한 병기) - 3개 항목으로 간소화
    story.append(Paragraph("Consent Items / 동의 항목", header_style))
    consent_data = [
        ['Consent Item / 동의 항목', 'Agreed / 동의', 'Description / 설명'],
        ['Research Participation / 연구 참여', 
         '✓' if consent_details.get('consent_participation') else '✗',
         'Voluntary participation in the research study / 연구에 자발적 참여'],
        ['Voice Recording & AI Processing / 음성 녹음 및 AI 처리', 
         '✓' if consent_details.get('consent_processing') else '✗',
         'Voice recording and AI feedback processing (Whisper→GPT→TTS) / 음성 녹음 및 AI 피드백 처리 (Whisper→GPT→TTS)'],
        ['Data Use & Rights Understanding / 데이터 사용 및 권리 이해', 
         '✓' if consent_details.get('consent_data_rights') else '✗',
         'Anonymous data use for research and understanding of withdrawal rights / 연구를 위한 익명 데이터 사용 및 철회 권리 이해'],
        ['Final Confirmation / 최종 확인', 
         '✓' if consent_details.get('consent_final_confirm') else '✗',
         'Final confirmation of all consent items / 모든 동의 항목에 대한 최종 확인'],
    ]
    
    consent_table = Table(consent_data, colWidths=[2.5*inch, 0.8*inch, 2.7*inch])
    consent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(consent_table)
    story.append(Spacer(1, 20))
    
    # GDPR 권리 안내 등 추가 내용
    story.extend(_build_additional_pdf_sections(anonymous_id, styles, header_style, consent_timestamp))
    
    return story


def _build_additional_pdf_sections(anonymous_id, styles, header_style, consent_timestamp):
    """
    PDF 추가 섹션 구성 (영한 병기)
    """
    story = []
    
    # GDPR 권리 안내 (영한 병기)
    story.append(Paragraph("Your Rights (GDPR) / 귀하의 권리 (GDPR)", header_style))
    rights_info = """
    You have the following rights regarding your personal data: / 개인정보와 관련하여 다음과 같은 권리를 가집니다:<br/>
    • <b>Right to Access / 접근권:</b> Request access to your data / 본인 데이터 열람 요청<br/>
    • <b>Right to Rectification / 정정권:</b> Correct inaccurate information / 부정확한 정보 수정<br/>
    • <b>Right to Erasure / 삭제권:</b> Request deletion of your data / 데이터 삭제 요청<br/>
    • <b>Right to Object / 이의제기권:</b> Object to data processing / 데이터 처리에 대한 이의제기<br/>
    • <b>Right to Withdraw / 철회권:</b> Withdraw consent at any time / 언제든지 동의 철회<br/>
    """
    story.append(Paragraph(rights_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 연락처 정보 (영한 병기)
    story.append(Paragraph("Contact for Data Rights / 데이터 권리 관련 연락처", header_style))
    contact_info = f"""
    <b>To exercise your rights or withdraw consent / 권리 행사 또는 동의 철회:</b><br/>
    Email: pen0226@gmail.com<br/>
    Subject: Data Rights Request - {anonymous_id}<br/>
    <br/>
    <b>Ewha Womans University Research Ethics Center / 이화여자대학교 연구윤리센터:</b><br/>
    Email: research@ewha.ac.kr<br/>
    Phone: 02-3277-7152<br/>
    """
    story.append(Paragraph(contact_info, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # 서명 섹션 (영한 병기)
    story.append(Paragraph("Electronic Consent Confirmation / 전자적 동의 확인", header_style))
    signature_info = f"""
    By checking all consent items above, the participant has provided electronic consent 
    to participate in this research study in accordance with GDPR and Korean research ethics guidelines.<br/>
    위의 모든 동의 항목을 체크함으로써 참여자는 GDPR 및 한국 연구윤리 가이드라인에 따라 
    본 연구 참여에 대한 전자적 동의를 제공하였습니다.<br/>
    <br/>
    <b>Consent completed / 동의 완료:</b> {consent_timestamp}<br/>
    <b>Participant ID / 참여자 ID:</b> {anonymous_id}<br/>
    <b>Method / 방법:</b> Electronic checkbox confirmation / 전자 체크박스 확인<br/>
    """
    story.append(Paragraph(signature_info, styles['Normal']))
    
    return story


def display_consent_pdf_download(pdf_filename, anonymous_id):
    """
    동의서 PDF 다운로드 버튼 표시
    
    Args:
        pdf_filename: PDF 파일 경로
        anonymous_id: 익명 ID
    """
    if pdf_filename and os.path.exists(pdf_filename):
        try:
            with open(pdf_filename, "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Your Consent Form",
                    data=pdf_file.read(),
                    file_name=f"{anonymous_id}_consent.pdf",
                    mime="application/pdf",
                    help="Download a copy of your consent form for your records"
                )
        except Exception as e:
            st.error(f"PDF download error: {e}")


def handle_nickname_input_with_consent():
    """
    닉네임 입력, 동의 처리, 배경 정보 수집을 통합한 함수
    
    Returns:
        bool: 처리 완료 여부
    """
    # 동의 섹션 처리
    consent_completed, consent_details = enhanced_consent_section()
    
    if not consent_completed:
        return False
    
    # 닉네임 입력 - 더 친근하게
    st.markdown("---")
    st.markdown("""
    ### 👤 Choose Your Nickname
    
    *Pick any nickname you like - this helps connect your two practice sessions!*
    """)
    
    # 친근한 안내
    st.info("💡 **Important:** Use the **same nickname** for both Session 1 and Session 2!")
    
    nickname = st.text_input(
        "Your nickname:",
        placeholder="e.g., KoreanLearner123, MyNickname, Student_A, etc.",
        help="Your nickname is just for linking your sessions. Your real identity stays private!"
    )
    
    st.caption("🔒 Don't worry - your nickname becomes an anonymous ID like 'Student01' in the records.")
    
    # 닉네임이 입력되지 않으면 배경 정보 섹션을 표시하지 않음
    if not nickname.strip():
        st.warning("👆 Please enter a nickname to continue")
        return False
    
    # 배경 정보 수집 섹션
    st.markdown("---")
    background_completed, background_details = collect_background_information()
    
    if not background_completed:
        return False
    
    # 모든 정보가 입력되면 시작 버튼 활성화
    st.markdown("---")
    st.markdown("### 🎉 Ready to Start Your Korean Practice?")
    
    if st.button("🚀 Let's Start!", type="primary", use_container_width=True):
        return _process_consent_completion(nickname.strip(), consent_details, background_details)
    
    return False


def _process_consent_completion(nickname, consent_details, background_details):
    """
    동의 완료 처리 (닉네임 매칭 시스템 + ZIP에서 GCS 업로드 처리)
    """
    # 🎯 닉네임 기반으로 기존 ID 찾거나 새로 생성
    anonymous_id = find_or_create_anonymous_id(nickname)
    
    # 매핑 정보 저장 (배경 정보 포함)
    save_nickname_mapping(anonymous_id, nickname, consent_details, background_details)
    
    # 세션 상태에 배경 정보 저장
    save_background_to_session(background_details)
    
    # 동의서 PDF 생성 (ZIP에 포함될 예정)
    with st.spinner("🎯 Setting up your Korean practice session..."):
        pdf_filename, pdf_result = generate_consent_pdf(
            anonymous_id, 
            consent_details, 
            st.session_state.consent_timestamp
        )
        
        if pdf_filename:
            st.session_state.consent_pdf = pdf_filename
            
            # 성공 메시지 - 더 친근하고 격려적으로
            st.success("🎉 Perfect! You're all set up!")
            st.info("📦 Your consent form is safely stored and will be included in the secure backup")
            
            # 사용자 다운로드 옵션은 여전히 제공
            display_consent_pdf_download(pdf_filename, anonymous_id)
        else:
            st.success("🎉 Great! You're ready to start practicing Korean!")
            st.info("✅ Your consent has been recorded securely")
    
    # 세션에 익명 ID 저장
    st.session_state.session_id = anonymous_id
    st.session_state.original_nickname = nickname  # 화면 표시용
    
    return True