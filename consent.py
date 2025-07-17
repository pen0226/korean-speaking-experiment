"""
consent.py
연구 참여 동의서 처리 및 PDF 생성 모듈 (최종 버전 - GDPR 준수 + 닉네임 매칭 시스템)
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
    강화된 동의 수집 섹션 (GDPR 준수)
    
    Returns:
        tuple: (consent_completed, consent_details)
    """
    
    with st.expander("📋 Research Information", expanded=True):
        st.markdown("""
        **Research Overview:**
        - **English**: This study is part of a research project at Ewha Womans University, including a master's thesis and potential academic publications
        - **한국어**: 이 연구는 이화여자대학교 대학원의 석사논문 및 향후 학술 발표/소논문 게재를 포함한 연구 프로젝트의 일부입니다
        - **Purpose**: To provide AI feedback that helps prepare for Korean Language Education Center placement interviews
        - **목적**: 언어교육원 배치고사 말하기 인터뷰 준비에 도움이 되는 AI 피드백 제공
        
        **Experimental Procedure:**
        1. **Session 1 & 2**: Record two voice responses to Korean questions (≈1 minute each)
           **세션 1 & 2**: 한국어 질문에 대한 음성 답변 2회 녹음 (각 약 1분)
        2. Receive personalized AI feedback and pronunciation models
           AI를 통한 개인화된 피드백 제공 및 발음 모델 제시  
        3. **Optional**: 15-minute Zoom interview for deeper feedback analysis
           **선택적**: 심층 피드백 분석을 위한 15분 Zoom 인터뷰
        
        **AI Tools Used:**
        - **OpenAI Whisper**: Speech-to-text conversion / 음성-텍스트 변환
        - **OpenAI GPT-4o**: Korean analysis and educational feedback / 한국어 분석 및 교육적 피드백  
        - **ElevenLabs TTS**: Speech synthesis for corrected sentences / 교정 문장 음성 생성
        - All AI tools are processed via international servers / 모든 AI 도구는 국제 서버를 통해 처리됩니다
        
        **Data Processing and Storage:**
        - **Storage**: Encrypted cloud storage (Google Cloud Storage) / 암호화된 클라우드 저장소 (구글 클라우드 스토리지)
        - **Access**: Researcher access only / 연구자 단독 접근
        - **Retention**: Up to 2 years post-completion, immediate deletion upon request / 논문 완성 후 최대 2년, 요청 시 즉시 삭제
        - **Anonymization**: Nickname converted to anonymous ID (e.g., Student01) / 닉네임을 익명 ID로 변환 (예: Student01)
        
        **Privacy Protection (GDPR Compliant):**
        - Transparency: Full transparency of data processing / 모든 데이터 처리 과정 공개
        - Purpose limitation: Limited to research and educational purposes / 연구 및 교육 목적으로만 사용
        - Data minimization: Minimal data collection / 필요한 최소한의 데이터만 수집
        - Accuracy: Right to correct inaccurate information / 부정확한 정보 수정 권리
        - Storage limitation: Storage limitation to necessary period / 필요 기간만 보관
        - Integrity: Secure encrypted storage / 안전한 암호화 저장
        - Accountability: Accountability in all processing / 모든 처리 과정 기록
        
        **International Data Transfer Notice:**
        - **Transfer to**: International AI service providers and Google Cloud Storage / 국제 AI 서비스 제공업체 및 구글 클라우드 스토리지
        - **Purpose**: AI feedback functionality and secure data storage / AI 피드백 기능 및 안전한 데이터 저장
        - **Protection**: Protection under respective privacy policies and international standards / 각 서비스의 개인정보 처리방침 및 국제 표준 적용
        - **GDPR compliance**: Lawful processing for academic research / 학술 연구 목적의 적법한 처리
        
        **Participant Rights (GDPR Rights):**
        - Right to access: Access collected data / 수집된 데이터 확인권
        - Right to rectification: Correct inaccurate information / 부정확한 정보 수정권
        - Right to erasure: Request data deletion anytime / 언제든 데이터 삭제 요청권
        - Right to restriction: Request limitation of data processing / 데이터 처리 제한 요청권
        - Right to portability: Request data transfer / 데이터 이동 요청권
        - Right to object: Object to data processing / 데이터 처리에 대한 이의제기권
        - Right to withdraw: Withdraw consent anytime / 언제든 동의 철회권
        
        **Risks and Benefits:**
        - **Minimal risks**: Korean speaking anxiety, technical issues / 한국어 말하기 부담감, 기술적 문제
        - **Direct benefit**: Personalized AI feedback for language education center placement preparation / 언어교육원 배치고사 준비를 위한 개인화된 AI 피드백
        - **Research benefit**: Contributing to AI language learning development / AI 언어 학습 도구 발전에 기여
        
        **Contact Information:**
        - **Researcher**: Jeongyeon Kim (pen0226@gmail.com)
        - **Ewha Womans University Research Ethics Center**: research@ewha.ac.kr, 02-3277-7152
        """)
    
    # Simplified consent for minimal burden while meeting GDPR requirements
    st.markdown("### 📝 Research Consent")
    st.info("✅ Simple checkboxes for your consent | 간단한 체크만으로 동의하실 수 있습니다")
    
    # Essential consent items only
    st.markdown("**Essential Consent Items:**")
    
    consent_research = st.checkbox(
        "🔬 **Research Participation Consent:**\n"
        "I understand the research information and voluntarily agree to participate / "
        "연구 정보를 이해하고 자발적으로 참여에 동의합니다"
    )
    
    consent_recording = st.checkbox(
        "🎙️ **Audio Recording & AI Processing Consent:**\n"
        "I consent to audio recording and analysis via international AI services / "
        "음성 녹음과 국제 AI 서비스를 통한 분석에 동의합니다"
    )
    
    consent_data = st.checkbox(
        "💾 **Data Storage & Research Use Consent:**\n"
        "I consent to encrypted storage and the use of my anonymized data for academic research, including thesis writing, conference presentations, and academic publications / "
        "암호화된 저장과 함께, 내 익명화된 데이터가 석사논문, 학술대회 발표, 학술지 게재 등의 학문적 연구에 사용되는 것에 동의합니다"
    )
    
    consent_rights = st.checkbox(
        "🛡️ **Privacy Rights Understanding:**\n"
        "I understand my right to withdraw and request data deletion anytime / "
        "언제든 참여 중단 및 데이터 삭제 요청 권리가 있음을 이해합니다"
    )
    
    consent_zoom = st.checkbox(
        "🎥 **Optional Zoom Interview Consent (≈15 minutes):**  \n"
        "I understand that after the main experiment I may participate in a ~15-minute Zoom interview about my experience using the AI feedback system (satisfaction, suggestions for improvement, etc.). This session will be audio-recorded and transcribed for research purposes only. All data will be anonymized. /  \n"
        "실험 종료 후 약 15분간 Zoom 인터뷰를 통해 AI 피드백 시스템 사용 경험(만족도, 개선 제안 등)에 대해 인터뷰를 진행합니다. 인터뷰 내용은 음성만 녹음·전사되어 연구 목적으로만 사용되며, 모든 데이터는 익명 처리됩니다. 이에 동의합니다."
    )
    
    # Check if all essential consents are given
    all_consents = [consent_research, consent_recording, consent_data, consent_rights]
    
    if all(all_consents):
        # Simple final confirmation without signature
        st.markdown("---")
        final_consent = st.checkbox(
            "✅ **Final Confirmation:** I confirm all the above and agree to participate in this research / "
            "**최종 확인:** 위 모든 사항을 확인했으며 연구에 참여하겠습니다"
        )
        
        if final_consent:
            consent_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.success(f"🎉 Consent completed! ({consent_timestamp})")
            
            # 동의 정보 세션에 저장
            consent_details = {
                'consent_participation': consent_research,
                'consent_audio_ai': consent_recording,
                'consent_data_storage': consent_data,
                'consent_privacy_rights': consent_rights,
                'consent_final_confirm': final_consent,
                'consent_zoom_interview': consent_zoom,  # 새로 추가
                'consent_timestamp': consent_timestamp
            }
            
            # 세션 상태에 저장
            save_consent_to_session(consent_details)
            
            return True, consent_details
        else:
            st.warning("⚠️ Please check the final confirmation")
            return False, None
    else:
        st.warning("⚠️ Please consent to all essential items")
        return False, None


def collect_background_information():
    """
    배경 정보 수집 섹션
    
    Returns:
        tuple: (background_completed, background_details)
    """
    st.markdown("### 📊 Background Information")
    st.markdown("Please provide some background information about your Korean learning experience.")
    
    # 학습 기간 질문 (필수)
    st.markdown("**How long have you been learning Korean?** *(Required)*")
    learning_duration = st.radio(
        "Select your learning duration:",
        options=BACKGROUND_INFO["learning_duration_options"],
        key="bg_learning_duration",  # 키 이름 변경
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 자신감 질문 (필수)
    st.markdown("**How confident do you feel when speaking Korean right now?** *(Required - Please choose one)*")
    speaking_confidence = st.radio(
        "Select your confidence level:",
        options=BACKGROUND_INFO["confidence_options"],
        key="bg_speaking_confidence",  # 키 이름 변경
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
        st.warning("⚠️ Please answer both questions to continue")
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
    st.session_state.consent_audio_ai = consent_details['consent_audio_ai']
    st.session_state.consent_data_storage = consent_details['consent_data_storage']
    st.session_state.consent_privacy_rights = consent_details['consent_privacy_rights']
    st.session_state.consent_final_confirmation = consent_details['consent_final_confirm']
    st.session_state.consent_zoom_interview = consent_details['consent_zoom_interview']  # 새로 추가
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
    닉네임 매핑 정보를 CSV 파일에 저장 (연구자 전용) - 배경 정보 포함
    
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
        
        # 헤더가 없으면 생성 (배경 정보 컬럼 추가)
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
                    'Consent_Audio_AI',
                    'Consent_Data_Storage',
                    'Consent_Privacy_Rights',
                    'Consent_Final_Confirm',
                    'Consent_Zoom_Interview',
                    'GDPR_Compliant',
                    'Learning_Duration',  # 새로 추가
                    'Speaking_Confidence',  # 새로 추가
                    'Session_Count',  # 참여한 세션 수
                    'Last_Session',  # 마지막 참여 세션
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
        
        # 동의 세부 정보 처리
        if consent_details is None:
            consent_details = {
                'consent_participation': True,
                'consent_audio_ai': True,
                'consent_data_storage': True,
                'consent_privacy_rights': True,
                'consent_final_confirm': True,
                'consent_zoom_interview': False
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
                    'Deletion_Requested', 'Consent_Participation', 'Consent_Audio_AI',
                    'Consent_Data_Storage', 'Consent_Privacy_Rights', 'Consent_Final_Confirm',
                    'Consent_Zoom_Interview', 'GDPR_Compliant', 'Learning_Duration',
                    'Speaking_Confidence', 'Session_Count', 'Last_Session', 'Notes'
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
                    consent_details.get('consent_audio_ai', True),
                    consent_details.get('consent_data_storage', True),
                    consent_details.get('consent_privacy_rights', True),
                    consent_details.get('consent_final_confirm', True),
                    consent_details.get('consent_zoom_interview', False),
                    'TRUE',
                    background_details.get('learning_duration', ''),  # 새로 추가
                    background_details.get('speaking_confidence', ''),  # 새로 추가
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
    PDF 내용 구성 헬퍼 함수
    """
    story = []
    
    # 제목
    story.append(Paragraph("Research Participation Consent Form", title_style))
    story.append(Paragraph("AI-Based Korean Speaking Feedback System Study", title_style))
    story.append(Spacer(1, 20))
    
    # 연구 정보
    story.append(Paragraph("Research Information", header_style))
    research_info = """
    <b>Principal Investigator:</b> Jeongyeon Kim<br/>
    <b>Institution:</b> Ewha Womans University, Graduate School<br/>
    <b>Contact:</b> pen0226@gmail.com<br/>
    <b>Research Title:</b> Effectiveness of AI-Based Korean Speaking Feedback Systems<br/>
    <b>Purpose:</b> To analyze the effectiveness of AI feedback for Korean language learning and contribute to future academic research including conference presentations and scholarly publications<br/>
    """
    story.append(Paragraph(research_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 참여자 정보
    story.append(Paragraph("Participant Information", header_style))
    participant_info = f"""
    <b>Participant ID:</b> {anonymous_id}<br/>
    <b>Consent Date:</b> {consent_timestamp}<br/>
    <b>Consent Method:</b> Electronic Checkbox<br/>
    """
    story.append(Paragraph(participant_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 동의 항목 표
    story.append(Paragraph("Consent Items", header_style))
    consent_data = [
        ['Consent Item', 'Agreed', 'Description'],
        ['Research Participation', 
         '✓' if consent_details.get('consent_participation') else '✗',
         'Voluntary participation in the research study'],
        ['Audio Recording & AI Processing', 
         '✓' if consent_details.get('consent_audio_ai') else '✗',
         'Recording and analysis via international AI services'],
        ['Data Storage & Research Use', 
         '✓' if consent_details.get('consent_data_storage') else '✗',
         'Encrypted storage for academic research including thesis, conferences, and publications'],
        ['Privacy Rights Understanding', 
         '✓' if consent_details.get('consent_privacy_rights') else '✗',
         'Understanding of data protection rights'],
        ['Final Confirmation', 
         '✓' if consent_details.get('consent_final_confirm') else '✗',
         'Final confirmation of all consent items'],
        ['Optional Zoom Interview', 
         '✓' if consent_details.get('consent_zoom_interview') else '✗',
         '15-minute optional interview for deeper feedback analysis']
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
    PDF 추가 섹션 구성
    """
    story = []
    
    # GDPR 권리 안내
    story.append(Paragraph("Your Rights (GDPR)", header_style))
    rights_info = """
    You have the following rights regarding your personal data:<br/>
    • <b>Right to Access:</b> Request access to your data<br/>
    • <b>Right to Rectification:</b> Correct inaccurate information<br/>
    • <b>Right to Erasure:</b> Request deletion of your data<br/>
    • <b>Right to Object:</b> Object to data processing<br/>
    • <b>Right to Withdraw:</b> Withdraw consent at any time<br/>
    """
    story.append(Paragraph(rights_info, styles['Normal']))
    story.append(Spacer(1, 15))
    
    # 연락처 정보
    story.append(Paragraph("Contact for Data Rights", header_style))
    contact_info = f"""
    <b>To exercise your rights or withdraw consent:</b><br/>
    Email: pen0226@gmail.com<br/>
    Subject: Data Rights Request - {anonymous_id}<br/>
    <br/>
    <b>Ewha Womans University Research Ethics Center:</b><br/>
    Email: research@ewha.ac.kr<br/>
    Phone: 02-3277-7152<br/>
    """
    story.append(Paragraph(contact_info, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # 서명 섹션
    story.append(Paragraph("Electronic Consent Confirmation", header_style))
    signature_info = f"""
    By checking all consent items above, the participant has provided electronic consent 
    to participate in this research study in accordance with GDPR and Korean research ethics guidelines.<br/>
    <br/>
    <b>Consent completed:</b> {consent_timestamp}<br/>
    <b>Participant ID:</b> {anonymous_id}<br/>
    <b>Method:</b> Electronic checkbox confirmation<br/>
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
    
    # 닉네임 입력
    st.markdown("---")
    st.markdown("### 👤 Step 1: Enter Your Nickname")
    st.write("Please enter a nickname to identify your experiment session.")
    
    # 중요 안내 강조
    st.info("📌 Use the **SAME NICKNAME** in Session 1 and Session 2 to link your data.")
    
    # 덜 중요한 프라이버시 안내는 caption 또는 tooltip으로 분리
    nickname = st.text_input(
        "Nickname:",
        placeholder="e.g., Student123, MyNickname, etc.",
        help="Your nickname is only used for linking your answers. All data is stored anonymously."
    )
    st.caption("🔒 Nickname is for linking only. Your data will be stored anonymously.")
    
    # 닉네임이 입력되지 않으면 배경 정보 섹션을 표시하지 않음
    if not nickname.strip():
        st.warning("⚠️ Please enter a nickname to continue")
        return False
    
    # 배경 정보 수집 섹션
    st.markdown("---")
    background_completed, background_details = collect_background_information()
    
    if not background_completed:
        return False
    
    # 모든 정보가 입력되면 시작 버튼 활성화
    st.markdown("---")
    if st.button("🚀 Start Experiment", type="primary"):
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
    with st.spinner("📄 Preparing your session..."):
        pdf_filename, pdf_result = generate_consent_pdf(
            anonymous_id, 
            consent_details, 
            st.session_state.consent_timestamp
        )
        
        if pdf_filename:
            st.session_state.consent_pdf = pdf_filename
            
            # ✅ GCS 업로드는 data_io.py의 ZIP 프로세스에서 처리
            st.success("✅ Consent completed successfully!")
            st.info("📦 Your consent form will be included in the secure data backup")
            
            # 사용자 다운로드 옵션은 여전히 제공
            display_consent_pdf_download(pdf_filename, anonymous_id)
        else:
            st.success("✅ Consent completed successfully!")
            st.info("ℹ️ Your consent has been recorded")
    
    # 세션에 익명 ID 저장
    st.session_state.session_id = anonymous_id
    st.session_state.original_nickname = nickname  # 화면 표시용
    
    return True