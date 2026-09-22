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

    # 한글 발음 → 일본어 기본 변환
    phonetic_map = {
        "와타시": "私",
        "아나타": "あなた",
        "카레": "彼",
        "카노조": "彼女",
        "토모다치": "友達",
        "쿄우": "今日",
        "쿄오": "今日",
        "아시타": "明日",
        "키노우": "昨日",
        "카이모노": "買い物",
        "타베루": "食べる",
        "타베마스": "食べます",
        "노무": "飲む",
        "노미마스": "飲みます",
        "미루": "見る",
        "미마스": "見ます",
        "이쿠": "行く",
        "이키마스": "行きます",
        "오이시이": "おいしい",
        "타노시이": "楽しい",
        "카와이이": "かわいい",
        "아리가토우": "ありがとう",
        "스미마센": "すみません",
        "곤니치와": "こんにちは",
        "오하요우": "おはよう",
        "콘반와": "こんばんは"
    }

    # 한글 발음이 포함되어 있으면 먼저 일본어로 변환
    converted_diary = diary

    for korean, japanese in phonetic_map.items():
        converted_diary = converted_diary.replace(korean, japanese)

    prompt = f"""
당신은 초급 일본어 학습자를 위한 '일본어 일기 선생님'입니다.

사용자가 일본어와 한글을 섞어서 일기를 입력할 수 있습니다.

중요한 규칙:

1. 이미 일본어로 변환된 부분은 그대로 유지합니다.

2. 한글로 입력된 일반적인 단어나 문장은 문맥에 맞는 자연스러운 일본어로 변환합니다.

3. 한글 발음으로 입력한 일본어 단어도 반드시 일본어로 변환합니다.

4. 특히 다음과 같은 입력은 반드시 일본어로 변환합니다.

와타시 → 私
아나타 → あなた
토모다치 → 友達
쿄우 → 今日
아시타 → 明日
키노우 → 昨日
카이모노 → 買い物
타베루 → 食べる
이쿠 → 行く
오이시이 → おいしい

5. 최종 corrected에는 한글이 남지 않도록 합니다.

6. 중요한 한자에는 후리가나를 붙입니다.

예:
私（わたし）
今日（きょう）
友達（ともだち）
買い物（かいもの）
行（い）きました

7. 일본어 문법이나 표현이 어색하면 자연스럽게 고칩니다.

8. 원래 일기의 의미와 분위기는 최대한 유지합니다.

9. vocabulary에는 공부하기 좋은 단어 5~10개를 넣습니다.

10. corrections에는 중요한 교정 내용을 넣습니다.

11. input_conversions에는 한글 또는 한글 발음이 어떻게 일본어로 변환되었는지 기록합니다.

원래 입력:
{diary}

변환 후 입력:
{converted_diary}

반드시 아래 JSON 형식으로만 답하세요.

{{
  "corrected": "자연스럽게 교정된 일본어. 중요한 한자에는 후리가나를 붙입니다.",
  "summary_ko": "일기의 내용을 한국어로 간단히 요약",
  "level": "N5/N4/N3/N2/N1 중 하나",

  "input_conversions": [
    {{
      "original": "원래 한글 또는 한글 발음",
      "converted": "변환된 일본어",
      "reason_ko": "변환 이유"
    }}
  ],

  "corrections": [
    {{
      "original": "원래 표현",
      "corrected": "교정 표현",
      "type": "문법/자연스러운 표현/단어 선택/조사/활용 등",
      "reason_ko": "왜 고쳤는지 설명",
      "mini_example": "간단한 일본어 예문",
      "mini_example_ko": "예문의 한국어 뜻"
    }}
  ],

  "vocabulary": [
    {{
      "word": "단어",
      "furigana": "후리가나",
      "meaning_ko": "한국어 뜻",
      "part_of_speech": "품사",
      "example": "일본어 예문",
      "example_ko": "한국어 뜻"
    }}
  ],

  "expressions": [
    {{
      "expression": "표현",
      "meaning_ko": "한국어 뜻",
      "example": "일본어 예문",
      "example_ko": "한국어 뜻"
    }}
  ],

  "review_question": {{
    "question": "복습 문제",
    "options": ["보기1", "보기2", "보기3"],
    "answer": "정답",
    "explanation": "정답 설명"
  }},

  "beginner_tip": "초급 학습자를 위한 짧은 팁"
}}
"""

    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )

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
if r.get("input_conversions"):
    st.subheader("🔤 한글 → 일본어 변환")

    for item in r["input_conversions"]:
        st.markdown(
            f"**{item['original']} → {item['converted']}**"
        )
        if item.get("reason_ko"):
            st.caption(item["reason_ko"])
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
