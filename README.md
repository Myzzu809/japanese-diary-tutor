# 🇯🇵 일본어 일기 선생님 — 스마트폰 웹앱 테스트판

현재 PC용 v2를 바탕으로, **스마트폰에서 URL로 접속해 사용하는 1차 웹앱**입니다.

## 가장 중요한 변경
- 앱 화면에서 OpenAI API Key를 입력하지 않습니다.
- Streamlit Cloud의 **Secrets**에 `OPENAI_API_KEY`를 넣습니다.
- SQLite는 1차 테스트용입니다. 여러 사용자용 서비스로 확장할 때는 PostgreSQL/Supabase로 교체합니다.

## Streamlit Cloud 배포
1. GitHub에 이 폴더의 파일을 업로드합니다.
2. Streamlit Community Cloud에서 저장소와 `app.py`를 선택해 Deploy합니다.
3. 앱의 Settings → Secrets에 다음을 입력합니다.

```toml
OPENAI_API_KEY = "sk-여기에_API_Key"
```

4. 스마트폰에서 생성된 `streamlit.app` 주소를 엽니다.
5. Chrome 메뉴에서 홈 화면에 추가합니다.

## 주의
이 테스트판의 SQLite 저장 데이터는 클라우드 환경 특성상 영구 저장을 보장하지 않습니다. 실제 서비스 단계에서는 사용자 로그인 + PostgreSQL/Supabase DB로 전환합니다.
