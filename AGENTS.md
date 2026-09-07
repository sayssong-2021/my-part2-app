# AGENTS.md

## Project Overview

-Streamlit 기반 단일 페이지 MVP
-순수 Python, 외부 DB 없음, 세션 내 상태만 사용

## Setup Commands

-설치: pip install -r requirements.txt
-실행: streamlit run app.py

## Code Style

-타입 힌트 사용, 함수는 단일 책임으로 작게
-비용 큰 연산은 @st.cache_data 로 캐싱
-UI 텍스트와 주석은 한국어
-매직 넘버 대신 상단 상수로 분리

## Testing

-핵심 로직은 UI와 분리해 함수로 작성
-변경 후 반드시 streamlit run 으로 실행 확인

## Security

-API 키/시크릿 하드코딩 금지
-비밀은 .streamlit/secrets.toml 또는 환경변수
-secrets 파일은 .gitignore 에 추가