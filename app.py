import os, json, sqlite3
from pathlib import Path
from datetime import datetime, date
import streamlit as st
from openai import OpenAI
import streamlit.components.v1 as components

APP_DIR = Path(__file__).resolve().parent
DB = APP_DIR / "diary_history.db"

st.set_page_config(page_title="일본어 일기 선생님", page_icon="🇯🇵", layout="centered")


def get_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        key = ""
    return (key or os.getenv("OPENAI_API_KEY", "")).strip()


def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS diaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        diary_date TEXT NOT NULL,
        original TEXT NOT NULL,
        corrected TEXT NOT NULL,
        analysis TEXT NOT NULL
    )""")
    conn.commit(); conn.close()


def save_diary(diary_date, original, result):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO diaries(created_at, diary_date, original, corrected, analysis) VALUES (?, ?, ?, ?, ?)",
                 (datetime.now().isoformat(timespec="seconds"), diary_date.isoformat(), original, result["corrected"], json.dumps(result, ensure_ascii=False)))
    conn.commit(); conn.close()


def get_history():
    conn = sqlite3.connect(DB)
    rows = conn.execute("SELECT id, created_at, diary_date, original, corrected, analysis FROM diaries ORDER BY id DESC").fetchall()
    conn.close(); return rows


def analyze_diary(api_key, diary):
    client = OpenAI(api_key=api_key)
    prompt = f'''당신은 한국인 일본어 학습자를 위한 친절한 일본어 원어민 선생님입니다. 학습자는 왕초보~초중급입니다.
아래 일본어 일기를 분석하세요.

[일기]\n{diary}

반드시 JSON 형식으로만 답하세요.
{{
  "corrected": "자연스러운 일본어로 고친 전체 일기",
  "summary_ko": "일기의 자연스러운 한국어 요약",
  "level": "N5/N4/N3/N2/N1 중 하나",
  "corrections": [{{"original":"원래 표현","corrected":"수정 표현","type":"문법 오류/자연스러운 표현/단어 선택/조사/활용/기타 중 하나","reason_ko":"왕초보도 이해할 수 있게 쉬운 한국어 설명","mini_example":"짧은 예문","mini_example_ko":"예문 뜻"}}],
  "vocabulary": [{{"word":"단어","furigana":"히라가나","meaning_ko":"뜻","part_of_speech":"품사","example":"짧은 예문","example_ko":"예문 뜻"}}],
  "expressions": [{{"expression":"주요 표현","furigana":"히라가나","meaning_ko":"뜻","example":"짧은 예문","example_ko":"예문 뜻"}}],
  "review_question": {{"question":"짧은 객관식 문제","options":["보기1","보기2","보기3"],"answer":"정답 보기","explanation":"쉬운 설명"}},
  "beginner_tip":"오늘 꼭 기억할 초보자용 핵심 팁"
}}
규칙: 원문의 의미와 감정은 바꾸지 마세요. 맞는 문장은 억지로 고치지 마세요. 실제로 고칠 가치가 있는 항목만 corrections에 넣으세요. vocabulary는 공부 가치가 높은 단어 5~10개를 고르세요. 한자 단어는 정확한 후리가나를 적으세요. 예문은 짧고 쉽게 만드세요. review_question은 오늘 일기에서 실제로 배운 표현을 사용하세요.'''
    response = client.responses.create(model="gpt-5", input=prompt)
    text = response.output_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def speak(text):
    safe = json.dumps(text, ensure_ascii=False)
    components.html(f'''<script>const u=new SpeechSynthesisUtterance({safe});u.lang="ja-JP";u.rate=.85;speechSynthesis.cancel();speechSynthesis.speak(u);</script>''', height=0)


init_db()
api_key = get_api_key()

st.title("🇯🇵 일본어 일기 선생님")
st.caption("매일 일본어로 일기를 쓰고, 교정·한국어 설명·단어·복습까지 한 번에 공부해요.")

if not api_key:
    st.warning("배포 설정에 OpenAI API Key가 아직 연결되지 않았습니다. 아래 안내를 따라 한 번만 설정해주세요.")
    with st.expander("🔐 관리자용 API Key 설정 안내", expanded=True):
        st.markdown("1. Streamlit Cloud에서 이 앱의 **Settings → Secrets**를 엽니다.\n2. 아래 한 줄을 추가합니다.\n3. 저장 후 앱을 재실행합니다.")
        st.code('OPENAI_API_KEY = "sk-여기에_API_Key"', language="toml")
        st.caption("API Key는 앱 화면에 입력하지 않고 서버의 Secrets에만 보관합니다.")
    st.stop()

with st.sidebar:
    st.header("📱 사용법")
    st.write("① 일본어 일기를 씁니다.")
    st.write("② 분석하기를 누릅니다.")
    st.write("③ 교정·단어·표현을 공부합니다.")
    st.write("④ 1분 복습을 합니다.")
    st.divider()
    st.caption("API Key는 서버 Secrets에서 관리됩니다.")

tab1, tab2, tab3 = st.tabs(["✍️ 오늘의 일기", "📚 학습 기록", "🧠 복습"])

with tab1:
    diary_date = st.date_input("📅 일기 날짜", value=date.today())
    diary = st.text_area("오늘의 일본어 일기", height=220, placeholder="例：今日は友達とカフェに行きました。\nとても楽しかったです。")
    if st.button("✨ 일기 분석하기", type="primary", use_container_width=True):
        if not diary.strip(): st.warning("먼저 일본어 일기를 입력해주세요.")
        else:
            with st.spinner("일기를 꼼꼼하게 분석하고 있어요…"):
                try:
                    r = analyze_diary(api_key, diary)
                    st.session_state["result"] = r
                    save_diary(diary_date, diary, r)
                except Exception as e:
                    st.error(f"분석 중 문제가 발생했습니다: {e}")

    if "result" in st.session_state:
        r = st.session_state["result"]
        st.divider()
        st.subheader("🌸 자연스러운 일본어")
        st.info(r["corrected"])
        if st.button("🔊 일본어 읽어주기", key="read_corrected"): speak(r["corrected"])
        st.caption(f"예상 JLPT 난이도: **{r.get('level','N/A')}**")
        st.subheader("🇰🇷 한국어로 뜻 확인")
        st.write(r.get("summary_ko", ""))
        st.subheader("🔎 어색하거나 틀린 부분")
        cs = r.get("corrections", [])
        if not cs: st.success("특별히 고칠 부분이 없습니다. 아주 자연스럽습니다! 👏")
        for i,c in enumerate(cs,1):
            with st.expander(f"{i}. {c['original']} → {c['corrected']}"):
                st.caption(c.get("type","")); st.markdown(f"**왜 고칠까요?** {c['reason_ko']}"); st.markdown(f"**예문:** {c['mini_example']}"); st.write(c['mini_example_ko'])
        st.subheader("📚 오늘의 주요 단어")
        for i,v in enumerate(r.get("vocabulary",[])):
            with st.expander(f"{v['word']}（{v['furigana']}） — {v['meaning_ko']}"):
                st.markdown(f"### {v['word']}（{v['furigana']}）"); st.caption(v.get('part_of_speech','')); st.markdown(f"**예문:** {v['example']}"); st.write(v['example_ko'])
                if st.button(f"🔊 발음 · {v['word']}", key=f"word_{i}"): speak(v['word'])
        st.subheader("💬 오늘의 주요 표현")
        for i,e in enumerate(r.get("expressions",[])):
            with st.expander(f"{e['expression']} — {e['meaning_ko']}"):
                st.markdown(f"**{e['expression']}**（{e.get('furigana','')}）"); st.markdown(f"**예문:** {e['example']}"); st.write(e['example_ko'])
                if st.button(f"🔊 표현 듣기 · {i+1}", key=f"expr_{i}"): speak(e['example'])
        st.subheader("🧠 오늘의 1분 복습")
        q=r.get('review_question',{})
        if q:
            st.write(q.get('question','')); choice=st.radio("정답을 골라보세요.", q.get('options',[]), key="review_choice")
            if st.button("정답 확인", key="check_review"):
                st.success("정답이에요! 🎉") if choice==q.get('answer') else st.error(f"정답은 **{q.get('answer')}**입니다.")
                st.info(q.get('explanation',''))
        st.subheader("🌱 초보자 학습 팁"); st.success(r.get('beginner_tip',''))

with tab2:
    history=get_history()
    st.metric("총 일기 수", len(history))
    if not history: st.info("아직 저장된 일기가 없습니다.")
    for _,created,dd,orig,corr,analysis in history:
        with st.expander(f"📅 {dd}"):
            st.markdown("**원문**"); st.write(orig); st.markdown("**교정문**"); st.write(corr)
            try:
                old=json.loads(analysis); st.caption(f"난이도 {old.get('level','N/A')} · 교정 {len(old.get('corrections',[]))}개")
            except Exception: pass

with tab3:
    history=get_history(); allc=[]
    for row in history:
        try: allc.extend(json.loads(row[5]).get('corrections',[]))
        except Exception: pass
    st.subheader("🔴 내가 다듬었던 표현")
    if allc:
        for i,c in enumerate(allc[:30],1): st.markdown(f"**{i}. {c['original']} → {c['corrected']}**  \n{c['reason_ko']}")
    else: st.info("일기를 쓰면 복습할 표현이 쌓입니다.")
    st.divider(); st.subheader("📊 학습 통계")
    total_words=sum(len(json.loads(row[5]).get('vocabulary',[])) for row in history if row[5]) if history else 0
    st.write(f"작성한 일기: **{len(history)}개** · 학습 단어: **{total_words}개** · 교정 기록: **{len(allc)}개**")
