"""
Streamlit 기반 할 일(To-Do) 관리 단일 페이지 애플리케이션
네이버 '공군' 관련 실시간 뉴스 (기사 제목 + 썸네일 이미지) 우측 배너 위젯 포함
프로젝트 규칙 및 아키텍처 가이드라인을 준수하여 작성되었습니다.
"""

from datetime import datetime
from html import unescape
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.parse import quote
import uuid
import requests
import streamlit as st

# ==============================================================================
# 상단 상수 정의 (Magic numbers & Strings 분리)
# ==============================================================================
PAGE_TITLE: str = "스마트 할 일 관리자 (To-Do)"
PAGE_ICON: str = "✅"
LAYOUT_MODE: str = "wide"  # 우측 배너 배치를 위한 와이드 레이아웃

SESSION_KEY_TODOS: str = "todos_list"
SESSION_KEY_INPUT: str = "new_todo_input_text"

FILTER_ALL: str = "전체"
FILTER_PENDING: str = "진행 중"
FILTER_COMPLETED: str = "완료됨"
FILTER_OPTIONS: Tuple[str, str, str] = (FILTER_ALL, FILTER_PENDING, FILTER_COMPLETED)

PROGRESS_DECIMAL_PLACES: int = 1
PERCENT_MULTIPLIER: float = 100.0

# 네이버 뉴스 관련 상수
NEWS_KEYWORD: str = "공군"
NEWS_SEARCH_URL: str = "https://search.naver.com/search.naver?where=news&query={keyword}"
NEWS_FETCH_COUNT: int = 6
NEWS_CACHE_TTL_SECONDS: int = 600  # 10분 캐시
NEWS_REQUEST_TIMEOUT_SECONDS: int = 5
NEWS_BANNER_HEADER: str = "🛩️ 공군 실시간 뉴스"

DEFAULT_SAMPLE_TODOS: List[Dict[str, Any]] = [
    {
        "id": "sample-1",
        "title": "Streamlit MVP 프로젝트 구조 설계하기",
        "is_completed": True,
        "created_at": "2026-09-07 10:00",
    },
    {
        "id": "sample-2",
        "title": "할 일 추가/완료/삭제 핵심 비즈니스 로직 작성",
        "is_completed": False,
        "created_at": "2026-09-07 11:30",
    },
    {
        "id": "sample-3",
        "title": "세션 상태 및 완료/미완료 요약 지표 실시간 연동",
        "is_completed": False,
        "created_at": "2026-09-07 13:00",
    },
]


# ==============================================================================
# 타입 정의 (Type Hints)
# ==============================================================================
class TodoItem(TypedDict):
    id: str
    title: str
    is_completed: bool
    created_at: str


class NewsItem(TypedDict):
    title: str
    link: str
    image_url: Optional[str]


# ==============================================================================
# 캐싱 및 외부 데이터 연동 함수 (@st.cache_data)
# ==============================================================================
@st.cache_data
def calculate_todo_metrics(
    todos_tuple: Tuple[Tuple[str, bool], ...]
) -> Dict[str, Any]:
    """
    할 일 목록의 완료 상태 튜플을 받아 전체, 완료, 미완료 개수 및 달성률을 계산합니다.
    불변 튜플을 인자로 받아 Streamlit 캐시를 안전하게 활용합니다.
    """
    total_count: int = len(todos_tuple)
    completed_count: int = sum(1 for _, is_done in todos_tuple if is_done)
    pending_count: int = total_count - completed_count

    completion_rate: float = (
        round((completed_count / total_count) * PERCENT_MULTIPLIER, PROGRESS_DECIMAL_PLACES)
        if total_count > 0
        else 0.0
    )

    return {
        "total": total_count,
        "completed": completed_count,
        "pending": pending_count,
        "rate": completion_rate,
    }


@st.cache_data(ttl=NEWS_CACHE_TTL_SECONDS)
def fetch_naver_news(
    keyword: str = NEWS_KEYWORD, max_count: int = NEWS_FETCH_COUNT
) -> List[Dict[str, Any]]:
    """
    네이버 뉴스 검색에서 키워드와 관련된 최신 기사(제목, 원문 링크, 썸네일 이미지)를 가져옵니다.
    @st.cache_data(ttl=600)을 적용하여 10분간 캐싱됩니다.
    """
    encoded_query: str = quote(keyword)
    url: str = NEWS_SEARCH_URL.format(keyword=encoded_query)
    headers: Dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    news_list: List[Dict[str, Any]] = []
    seen_links: set = set()

    try:
        response = requests.get(url, headers=headers, timeout=NEWS_REQUEST_TIMEOUT_SECONDS)
        if response.status_code == 200:
            text = response.text

            # 1. 썸네일 이미지 매핑 추출 (href -> unescape(img_src))
            img_matches = re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*data-heatmap-target="\.img"[^>]*>[\s\S]*?<img[^>]+src="([^"]+)"',
                text,
            )
            img_dict: Dict[str, str] = {href: unescape(src) for href, src in img_matches}

            # 2. 기사 제목 및 링크 추출
            tit_matches = re.findall(
                r'<a[^>]+href="([^"]+)"[^>]*data-heatmap-target="\.tit"[^>]*>([\s\S]*?)</a>',
                text,
            )

            # fallback: 만약 heatmap 타겟이 없을 경우 일반 링크 매칭
            if not tit_matches:
                tit_matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', text)

            for href, inner_text in tit_matches:
                if ("news" in href or "article" in href or "n.news.naver.com" in href) and href.startswith("http"):
                    clean_title: str = re.sub(r"<[^>]+>", "", inner_text).strip()
                    clean_title = (
                        clean_title.replace("새 창 열림", "")
                        .replace("&quot;", '"')
                        .replace("&amp;", "&")
                        .replace("&lt;", "<")
                        .replace("&gt;", ">")
                        .strip()
                    )
                    clean_title = unescape(clean_title)

                    if (
                        len(clean_title) >= 12
                        and href not in seen_links
                        and not any(ex in clean_title for ex in ["네이버뉴스", "언론사", "기사 바로가기"])
                    ):
                        seen_links.add(href)
                        img_url: Optional[str] = img_dict.get(href)
                        news_list.append({
                            "title": clean_title,
                            "link": href,
                            "image_url": img_url,
                        })
                        if len(news_list) >= max_count:
                            break
    except Exception:
        return []

    return news_list


# ==============================================================================
# 핵심 비즈니스 로직 (UI와 완전 분리된 순수 함수들)
# ==============================================================================
def create_todo_item(title: str) -> TodoItem:
    """새로운 할 일 데이터 객체를 생성합니다."""
    return {
        "id": str(uuid.uuid4())[:8],
        "title": title.strip(),
        "is_completed": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def add_todo(todos: List[Dict[str, Any]], title: str) -> List[Dict[str, Any]]:
    """할 일 목록에 새 항목을 추가합니다."""
    if not title or not title.strip():
        return todos
    new_item = create_todo_item(title)
    return [new_item] + todos


def toggle_todo(todos: List[Dict[str, Any]], item_id: str) -> List[Dict[str, Any]]:
    """특정 할 일의 완료 상태를 반전(토글)합니다."""
    updated: List[Dict[str, Any]] = []
    for item in todos:
        if item["id"] == item_id:
            copied = dict(item)
            copied["is_completed"] = not copied["is_completed"]
            updated.append(copied)
        else:
            updated.append(item)
    return updated


def delete_todo(todos: List[Dict[str, Any]], item_id: str) -> List[Dict[str, Any]]:
    """특정 할 일 항목을 목록에서 삭제합니다."""
    return [item for item in todos if item["id"] != item_id]


def clear_completed_todos(todos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """완료된 모든 할 일 항목을 목록에서 제거합니다."""
    return [item for item in todos if not item["is_completed"]]


def filter_todos(
    todos: List[Dict[str, Any]], filter_type: str, search_query: str = ""
) -> List[Dict[str, Any]]:
    """선택된 필터 조건(전체/진행 중/완료됨) 및 검색어에 따라 목록을 필터링합니다."""
    filtered = todos
    if filter_type == FILTER_COMPLETED:
        filtered = [item for item in filtered if item["is_completed"]]
    elif filter_type == FILTER_PENDING:
        filtered = [item for item in filtered if not item["is_completed"]]

    if search_query and search_query.strip():
        q = search_query.strip().lower()
        filtered = [item for item in filtered if q in item["title"].lower()]

    return filtered


# ==============================================================================
# 세션 상태(st.session_state) 관리
# ==============================================================================
def init_session_state() -> None:
    """세션 상태 초기화 및 기본값 설정"""
    if SESSION_KEY_TODOS not in st.session_state:
        st.session_state[SESSION_KEY_TODOS] = [dict(item) for item in DEFAULT_SAMPLE_TODOS]


def handle_add_todo() -> None:
    """입력 폼 제출 시 할 일을 세션에 추가하는 핸들러"""
    input_text: str = st.session_state.get(SESSION_KEY_INPUT, "")
    if input_text and input_text.strip():
        st.session_state[SESSION_KEY_TODOS] = add_todo(
            st.session_state[SESSION_KEY_TODOS], input_text
        )
        st.session_state[SESSION_KEY_INPUT] = ""


def handle_toggle_todo(item_id: str) -> None:
    """할 일 상태 토글 핸들러"""
    st.session_state[SESSION_KEY_TODOS] = toggle_todo(
        st.session_state[SESSION_KEY_TODOS], item_id
    )


def handle_delete_todo(item_id: str) -> None:
    """할 일 개별 삭제 핸들러"""
    st.session_state[SESSION_KEY_TODOS] = delete_todo(
        st.session_state[SESSION_KEY_TODOS], item_id
    )


def handle_clear_completed() -> None:
    """완료된 할 일 전체 삭제 핸들러"""
    st.session_state[SESSION_KEY_TODOS] = clear_completed_todos(
        st.session_state[SESSION_KEY_TODOS]
    )


# ==============================================================================
# UI 렌더링 함수들 (단일 책임 원칙 준수)
# ==============================================================================
def render_header() -> None:
    """헤더 및 앱 소개 영역 렌더링"""
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.caption("간편하게 일정을 관리하고 진행 상황을 한눈에 파악하세요.")
    st.divider()


def render_summary_metrics(todos: List[Dict[str, Any]]) -> None:
    """완료/미완료 개수 요약 카드 및 진행률 바 렌더링"""
    todos_tuple: Tuple[Tuple[str, bool], ...] = tuple(
        (item["id"], item["is_completed"]) for item in todos
    )
    metrics: Dict[str, Any] = calculate_todo_metrics(todos_tuple)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="전체 작업", value=f"{metrics['total']}개")
    with col2:
        st.metric(label="진행 중 (미완료)", value=f"{metrics['pending']}개")
    with col3:
        st.metric(label="완료됨", value=f"{metrics['completed']}개")
    with col4:
        st.metric(label="달성률", value=f"{metrics['rate']}%")

    progress_val: float = min(max(metrics["rate"] / PERCENT_MULTIPLIER, 0.0), 1.0)
    st.progress(progress_val, text=f"전체 달성률: {metrics['rate']}%")
    st.write("")


def render_sidebar(todos: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    사이드바에 필터 및 검색 위젯을 배치합니다. (UI Rules 준수)
    반환값: (선택된_필터, 검색어)
    """
    with st.sidebar:
        st.header("🔍 검색 및 필터")
        st.caption("작업을 검색하거나 상태별로 모아보세요.")

        search_query = st.text_input(
            label="할 일 검색",
            placeholder="검색어 입력...",
            key="sidebar_search_query",
        )

        st.write("")
        selected_filter = st.radio(
            label="상태 필터",
            options=FILTER_OPTIONS,
            index=0,
            key="sidebar_filter_radio",
        )

        st.divider()
        completed_count = sum(1 for item in todos if item["is_completed"])
        if completed_count > 0:
            st.button(
                label="완료 항목 일괄 정리 🧹",
                use_container_width=True,
                on_click=handle_clear_completed,
                help="완료된 모든 작업을 목록에서 삭제합니다.",
            )

    return selected_filter, search_query


def render_todo_input_form() -> None:
    """새로운 할 일 등록 입력창 렌더링"""
    with st.form(key="add_todo_form", clear_on_submit=True):
        col_input, col_button = st.columns([5, 1])
        with col_input:
            st.text_input(
                label="새로운 할 일 입력",
                placeholder="예: 프로젝트 보고서 작성하기...",
                key=SESSION_KEY_INPUT,
                label_visibility="collapsed",
            )
        with col_button:
            st.form_submit_button(
                label="추가",
                type="primary",
                use_container_width=True,
                on_click=handle_add_todo,
            )


def render_todo_item_row(item: Dict[str, Any]) -> None:
    """
    개별 할 일 행 컴포넌트 렌더링
    목록 항목에 상태 아이콘 표시 (완료 ✅ / 미완료 ⬜) - UI Rules 준수
    """
    item_id: str = item["id"]
    title: str = item["title"]
    is_done: bool = item["is_completed"]
    created_at: str = item.get("created_at", "")

    status_icon: str = "✅" if is_done else "⬜"

    col_chk, col_text, col_del = st.columns([0.8, 6.2, 1.0])

    with col_chk:
        st.checkbox(
            label=f"완료 체크 {item_id}",
            value=is_done,
            key=f"chk_{item_id}",
            on_change=handle_toggle_todo,
            args=(item_id,),
            label_visibility="collapsed",
        )

    with col_text:
        if is_done:
            st.markdown(
                f"{status_icon} ~~**{title}**~~ 　<small style='color: gray;'>({created_at} 완료)</small>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"{status_icon} **{title}** 　<small style='color: #888;'>({created_at} 등록)</small>",
                unsafe_allow_html=True,
            )

    with col_del:
        st.button(
            label="삭제",
            key=f"btn_del_{item_id}",
            use_container_width=True,
            on_click=handle_delete_todo,
            args=(item_id,),
        )


def render_todo_list(filtered_todos: List[Dict[str, Any]]) -> None:
    """할 일 목록 컨테이너 렌더링"""
    if not filtered_todos:
        st.info("해당하는 할 일 항목이 없습니다.")
        return

    st.markdown("---")
    for item in filtered_todos:
        render_todo_item_row(item)


def render_news_banner(news_items: List[Dict[str, Any]]) -> None:
    """
    우측 배너 영역에 네이버 실시간 공군 관련 뉴스 렌더링 (썸네일 이미지 + 기사 제목)
    """
    with st.container(border=True):
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            st.subheader(NEWS_BANNER_HEADER)
        with col_btn:
            if st.button("🔄", help="뉴스를 새로고침합니다.", key="btn_refresh_news"):
                st.cache_data.clear()
                st.rerun()

        st.caption(f"네이버 실시간 **'{NEWS_KEYWORD}'** 관련 주요 기사")
        st.divider()

        if not news_items:
            st.info("현재 공군 관련 뉴스를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
            return

        for news in news_items:
            title: str = news["title"]
            link: str = news["link"]
            img_url: Optional[str] = news.get("image_url")

            # 썸네일 이미지 HTML 또는 비행기 이모지 플레이스홀더 구성
            if img_url:
                img_element = (
                    f'<img src="{img_url}" alt="기사 썸네일" '
                    'style="width: 70px; height: 70px; object-fit: cover; border-radius: 8px; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.08);">'
                )
            else:
                img_element = (
                    '<div style="width: 70px; height: 70px; border-radius: 8px; background-color: rgba(30, 136, 229, 0.12); '
                    'display: flex; align-items: center; justify-content: center; font-size: 1.8rem; flex-shrink: 0;">🛩️</div>'
                )

            st.markdown(
                f"""
                <a href="{link}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: 10px; background-color: rgba(30, 136, 229, 0.05); border: 1px solid rgba(30, 136, 229, 0.15); transition: background 0.2s;">
                        {img_element}
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-size: 0.9rem; font-weight: 600; line-height: 1.35; color: inherit; word-break: keep-all; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                                {title}
                            </div>
                            <div style="margin-top: 5px; font-size: 0.75rem; color: #1E88E5; font-weight: 500;">
                                기사 바로가기 ↗
                            </div>
                        </div>
                    </div>
                </a>
                """,
                unsafe_allow_html=True,
            )


# ==============================================================================
# 메인 엔트리포인트 함수
# ==============================================================================
def main() -> None:
    """애플리케이션 메인 실행 함수"""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=LAYOUT_MODE,
    )

    init_session_state()
    render_header()

    current_todos: List[Dict[str, Any]] = st.session_state[SESSION_KEY_TODOS]

    # 사이드바에 필터 및 검색 위젯 배치 (UI Rules 준수)
    selected_filter, search_query = render_sidebar(current_todos)

    # 2열(컬럼) 레이아웃 구성: 좌측 할 일 관리(68%) / 우측 공군 뉴스 배너(32%)
    col_main, col_banner = st.columns([6.8, 3.2], gap="large")

    with col_main:
        # 요약 메트릭 및 진행률 표시
        render_summary_metrics(current_todos)

        # 신규 할 일 추가 폼
        render_todo_input_form()

        # 필터 및 검색 적용된 할 일 목록 표시
        display_todos = filter_todos(current_todos, selected_filter, search_query)
        render_todo_list(display_todos)

    with col_banner:
        # 네이버 실시간 공군 뉴스 배너 렌더링 (이미지 포함)
        news_items = fetch_naver_news(NEWS_KEYWORD, NEWS_FETCH_COUNT)
        render_news_banner(news_items)


if __name__ == "__main__":
    main()
