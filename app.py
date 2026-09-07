"""
Streamlit 기반 할 일(To-Do) 관리 단일 페이지 애플리케이션
프로젝트 규칙 및 아키텍처 가이드라인을 준수하여 작성되었습니다.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict
import uuid
import streamlit as st

# ==============================================================================
# 상단 상수 정의 (Magic numbers & Strings 분리)
# ==============================================================================
PAGE_TITLE: str = "스마트 할 일 관리자 (To-Do)"
PAGE_ICON: str = "✅"
LAYOUT_MODE: str = "centered"

SESSION_KEY_TODOS: str = "todos_list"
SESSION_KEY_INPUT: str = "new_todo_input_text"

FILTER_ALL: str = "전체"
FILTER_PENDING: str = "진행 중"
FILTER_COMPLETED: str = "완료됨"
FILTER_OPTIONS: Tuple[str, str, str] = (FILTER_ALL, FILTER_PENDING, FILTER_COMPLETED)

PROGRESS_DECIMAL_PLACES: int = 1
PERCENT_MULTIPLIER: float = 100.0

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


# ==============================================================================
# 캐싱 및 비용 연산 함수 (@st.cache_data)
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
    # 캐시를 위한 불변 튜플 변환
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

    # 달성률 진행 바 표시
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

        # 검색 위젯
        search_query = st.text_input(
            label="할 일 검색",
            placeholder="검색어 입력...",
            key="sidebar_search_query",
        )

        st.write("")
        # 필터 위젯
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

    # 상태 아이콘 규칙: 완료 ✅ / 미완료 ⬜
    status_icon: str = "✅" if is_done else "⬜"

    col_chk, col_text, col_del = st.columns([0.8, 6.2, 1.0])

    with col_chk:
        # 체크박스 상태 변경 시 토글 핸들러 실행
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

    # 요약 메트릭 및 진행률 표시
    render_summary_metrics(current_todos)

    # 신규 할 일 추가 폼
    render_todo_input_form()

    # 필터 및 검색 적용된 할 일 목록 표시
    display_todos = filter_todos(current_todos, selected_filter, search_query)
    render_todo_list(display_todos)


if __name__ == "__main__":
    main()
