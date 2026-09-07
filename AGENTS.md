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


## UI Rules (이번 비교 실습 추가분)

-필터·검색 위젯은 st.sidebar 에 배치한다
-목록 항목엔 상태 아이콘을 표시한다 (완료 ✅ / 미완료 ⬜)
-레이아웃·위젯 선택은 위 규칙을 우선해 매 작업마다 동일하게 재현한다

## Verify (추가분)

-변경 후 내장 브라우저로 UI를 자동으로 열어 동작을 검증하고 스크린샷 Artifact를 남긴다