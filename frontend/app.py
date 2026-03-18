"""
Streamlit Frontend — AI Learning Agent
----------------------------------------
Pages:
  🏠 Home / Login / Register
  🎯 Onboarding — set goal + roadmap
  📅 Daily Taskszz
  📊 My Progress
  🏆 Group Leaderboard
"""

import streamlit as st
import requests
import json
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Learning Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

    .stApp { background: #0a0f1a; color: #e2e8f0; }

    .metric-card {
        background: #0f1d2e; border: 1px solid #1e3a5f;
        border-radius: 12px; padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-val  { font-size: 2rem; font-weight: 600; color: #38bdf8; }
    .metric-lbl  { font-size: 0.8rem; color: #64748b; margin-top: 4px; }

    .task-card {
        background: #0f1d2e; border: 1px solid #1e3a5f;
        border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem;
    }
    .task-title  { font-size: 1rem; font-weight: 600; color: #e2e8f0; }
    .task-desc   { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600; margin-right: 6px;
    }
    .badge-read    { background: #1e3a5f; color: #38bdf8; }
    .badge-quiz    { background: #1a1040; color: #a78bfa; }
    .badge-project { background: #0d2a1a; color: #34d399; }
    .badge-video   { background: #2a1a0d; color: #f59e0b; }

    .xp-pill {
        background: #1a2a10; color: #86efac;
        padding: 2px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 600;
    }

    .roadmap-phase {
        background: #0f1d2e; border-left: 3px solid #38bdf8;
        border-radius: 0 10px 10px 0; padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
    }

    .leaderboard-row {
        background: #0f1d2e; border-radius: 10px;
        padding: 0.8rem 1.2rem; margin-bottom: 0.5rem;
        display: flex; align-items: center;
    }

    div[data-testid="stSidebar"] {
        background: #060d18 !important;
        border-right: 1px solid #0f2a3f;
    }
    .stButton > button {
        background: #0c3a5f; color: #38bdf8;
        border: 1px solid #1e5a8f; border-radius: 8px;
        font-weight: 600; transition: all 0.2s;
    }
    .stButton > button:hover { background: #1e5a8f; }
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        background: #0f1d2e !important;
        border: 1px solid #1e3a5f !important;
        color: #e2e8f0 !important; border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State ────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "token": None, "user": None, "page": "login",
        "roadmap": None, "roadmap_id": None,
        "tasks": [], "day_number": 0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── API Helpers ──────────────────────────────────────────────────────────────

def api(method: str, path: str, data: dict = None, auth: bool = True) -> dict:
    headers = {"Content-Type": "application/json"}
    if auth and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        fn  = getattr(requests, method)
        res = fn(f"{API_URL}{path}", json=data, headers=headers, timeout=60)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def badge(task_type: str) -> str:
    return f'<span class="badge badge-{task_type}">{task_type.upper()}</span>'

# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("### 🤖 AI Learning Agent")
        st.markdown("---")

        if st.session_state.user:
            u = st.session_state.user
            st.markdown(f"**{u.get('name','User')}**")
            st.caption(u.get('email',''))
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔥 Streak", f"{u.get('streak',0)}d")
            with col2:
                st.metric("⚡ XP", u.get('total_xp', 0))
            st.markdown("---")

            pages = {
                "🏠 Dashboard":        "dashboard",
                "🎯 My Roadmap":       "roadmap",
                "📅 Today's Tasks":    "tasks",
                "📊 My Progress":      "progress",
                "🏆 Leaderboard":      "leaderboard",
            }
            for label, key in pages.items():
                if st.button(label, use_container_width=True, key=f"nav_{key}"):
                    st.session_state.page = key
                    st.rerun()

            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                for k in ["token","user","page","roadmap","roadmap_id","tasks"]:
                    st.session_state[k] = None if k != "page" else "login"
                st.session_state.tasks = []
                st.rerun()

# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## 🤖 AI Learning Agent")
        st.markdown("*Your personal RAG-powered study coach*")
        st.markdown("---")

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            email    = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login →", use_container_width=True, key="btn_login"):
                res = api("post", "/auth/login", {"email": email, "password": password}, auth=False)
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.session_state.token = res["token"]
                    st.session_state.user  = res
                    st.session_state.page  = "dashboard"
                    st.rerun()

        with tab2:
            name     = st.text_input("Full Name", key="reg_name")
            email2   = st.text_input("Email", key="reg_email")
            password2 = st.text_input("Password", type="password", key="reg_pass")
            mode     = st.selectbox("Mode", ["solo", "group"], key="reg_mode")
            if st.button("Create Account →", use_container_width=True, key="btn_reg"):
                res = api("post", "/auth/register",
                          {"name": name, "email": email2,
                           "password": password2, "mode": mode}, auth=False)
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.session_state.token = res["token"]
                    # Fetch full user
                    me = api("get", "/auth/me")
                    st.session_state.user = me
                    st.session_state.page = "onboarding"
                    st.rerun()


def page_dashboard():
    u = st.session_state.user or {}
    st.markdown(f"## 👋 Welcome back, {u.get('name','')}")
    st.markdown(f"*{datetime.now().strftime('%A, %B %d %Y')}*")
    st.markdown("---")

    # Fetch progress
    uid  = u.get("user_id","")
    prog = api("get", f"/progress/{uid}")

    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        ("⚡ Total XP",        u.get("total_xp", 0)),
        ("🔥 Day Streak",       u.get("streak", 0)),
        ("✅ Tasks Done",       prog.get("completed_tasks", 0)),
        ("📈 Avg Score",        f"{prog.get('avg_score', 0)}%"),
    ]
    for col, (label, val) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-val">{val}</div>
                <div class="metric-lbl">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📅 Today's Tasks")
        if st.button("Load Today's Tasks", use_container_width=True):
            st.session_state.page = "tasks"
            st.rerun()

    with col_b:
        st.markdown("### 🎯 Active Roadmap")
        rd = api("get", f"/roadmap/{uid}/active")
        if rd.get("roadmap"):
            st.success(f"📚 {rd.get('topic','')}")
            st.caption(f"{rd.get('duration_days',0)} day program")
        else:
            st.info("No roadmap yet")
            if st.button("Create Roadmap →", use_container_width=True):
                st.session_state.page = "onboarding"
                st.rerun()


def page_onboarding():
    st.markdown("## 🎯 Set Your Learning Goal")
    st.markdown("*Tell the AI what you want to learn — it will build your personalized roadmap*")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        topic    = st.text_input("What do you want to learn?",
                                  placeholder="e.g. Machine Learning, Python, Web Development, DSA...")
        goal     = st.text_area("What's your goal?",
                                 placeholder="e.g. I want to get a job as a data scientist / build my own app...",
                                 height=100)
        skill    = st.selectbox("Your current skill level",
                                 ["beginner", "intermediate", "advanced"])
        duration = st.slider("Duration (days)", 7, 90, 30)

    with col2:
        st.markdown("### 👥 Group Setup")
        u = st.session_state.user or {}
        if u.get("mode") == "group":
            action = st.radio("", ["Create Group", "Join Group"])
            if action == "Create Group":
                gname = st.text_input("Group Name")
                if st.button("Create Group"):
                    res = api("post", "/groups/create",
                              {"name": gname, "topic": topic})
                    if "invite_code" in res:
                        st.success(f"✅ Group created!\nInvite code: **{res['invite_code']}**")
            else:
                code = st.text_input("Invite Code")
                if st.button("Join Group"):
                    res = api("post", "/groups/join", {"invite_code": code})
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        st.success(f"✅ Joined {res.get('group_name','')}")

    st.markdown("---")
    if st.button("🤖 Generate My Roadmap →", use_container_width=True):
        if not topic:
            st.warning("Please enter a topic first!")
            return
        with st.spinner("🤖 AI is building your personalized roadmap..."):
            res = api("post", "/roadmap/generate", {
                "topic": topic, "goal": goal,
                "skill_level": skill, "duration_days": duration
            })
        if "error" in res:
            st.error(res["error"])
        else:
            st.session_state.roadmap    = res.get("roadmap")
            st.session_state.roadmap_id = res.get("roadmap_id")
            st.session_state.page       = "roadmap"
            st.rerun()


def page_roadmap():
    st.markdown("## 🗺️ Your Learning Roadmap")
    rd = st.session_state.roadmap

    if not rd:
        uid = (st.session_state.user or {}).get("user_id","")
        res = api("get", f"/roadmap/{uid}/active")
        rd  = res.get("roadmap")
        if rd:
            st.session_state.roadmap    = rd
            st.session_state.roadmap_id = res.get("roadmap_id")

    if not rd:
        st.info("No roadmap yet. Create one first!")
        if st.button("Create Roadmap"):
            st.session_state.page = "onboarding"
            st.rerun()
        return

    st.markdown(f"### 📚 {rd.get('title','')}")
    st.info(rd.get("overview",""))

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("📅 Duration",   f"{rd.get('total_days',0)} days")
    with col2: st.metric("⏱️ Daily Time", f"{rd.get('daily_time_minutes',45)} min")
    with col3: st.metric("📊 Level",       rd.get("skill_level","").title())

    st.markdown("---")
    st.markdown("### 📍 Learning Phases")

    for phase in rd.get("phases", []):
        with st.expander(f"Phase {phase.get('phase_number','')} — {phase.get('phase_name','')}  (Day {phase.get('days','')})"):
            st.markdown(f"**Objective:** {phase.get('objective','')}")
            st.markdown("**Topics:**")
            for t in phase.get("topics", []):
                st.markdown(f"  • {t}")

    if rd.get("resources"):
        st.markdown("---")
        st.markdown("### 📖 Resources")
        for r in rd.get("resources", []):
            st.markdown(f"  • {r}")

    st.markdown("---")
    rid = st.session_state.roadmap_id
    if rid:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Approve & Start Learning →", use_container_width=True):
                res = api("post", f"/roadmap/{rid}/approve")
                if res.get("status") == "approved":
                    st.success("🚀 Roadmap approved! Let's start learning.")
                    st.session_state.page = "tasks"
                    st.rerun()
        with col_b:
            if st.button("🔄 Regenerate Roadmap", use_container_width=True):
                st.session_state.page = "onboarding"
                st.rerun()


def page_tasks():
    u   = st.session_state.user or {}
    uid = u.get("user_id","")

    st.markdown(f"## 📅 Today's Tasks")
    st.markdown(f"*{datetime.now().strftime('%A, %B %d')}*")
    st.markdown("---")

    if st.button("🔄 Load Tasks", use_container_width=True) or not st.session_state.tasks:
        with st.spinner("Loading today's tasks..."):
            res = api("get", f"/tasks/{uid}/today")
        st.session_state.tasks      = res.get("tasks", [])
        st.session_state.day_number = res.get("day_number", 0)

    tasks = st.session_state.tasks
    if not tasks:
        st.info("No tasks yet — approve a roadmap first!")
        return

    st.markdown(f"### Day {st.session_state.day_number} — {len(tasks)} tasks")

    done  = sum(1 for t in tasks if t.get("status") == "completed")
    st.progress(done / len(tasks))
    st.caption(f"{done}/{len(tasks)} completed")

    for task in tasks:
        st.markdown("---")
        type_badge = badge(task.get("task_type","read"))
        status_icon = "✅" if task.get("status") == "completed" else "⏳"

        st.markdown(f"""<div class="task-card">
            <div class="task-title">{status_icon} {task.get('title','')}</div>
            {type_badge}
            <span class="xp-pill">+{task.get('xp_reward',10)} XP</span>
            <div class="task-desc">{task.get('description','')}</div>
        </div>""", unsafe_allow_html=True)

        if task.get("status") == "completed":
            if task.get("feedback"):
                st.success(f"💬 {task.get('feedback')}")
            if task.get("score"):
                st.metric("Score", f"{task.get('score')}%")
        else:
            with st.expander(f"Submit — {task.get('title','')}"):
                submission = st.text_area(
                    "What did you learn / What did you do?",
                    key=f"sub_{task['id']}",
                    placeholder="Describe what you learned, paste your code, answer the quiz questions...",
                    height=120
                )
                if st.button("Submit ✓", key=f"btn_{task['id']}"):
                    if not submission.strip():
                        st.warning("Please write something!")
                    else:
                        with st.spinner("🧠 AI is reviewing your work..."):
                            res = api("post", f"/tasks/{task['id']}/complete",
                                      {"submission": submission})
                        if "error" in res:
                            st.error(res["error"])
                        else:
                            assessment = res.get("assessment", {})
                            if assessment.get("passed"):
                                st.success(f"✅ {assessment.get('feedback')}")
                                st.balloons()
                            else:
                                st.warning(f"📝 {assessment.get('feedback')} — Try again!")
                            # Refresh tasks
                            r2 = api("get", f"/tasks/{uid}/today")
                            st.session_state.tasks = r2.get("tasks", [])
                            # Refresh user XP
                            me = api("get", "/auth/me")
                            st.session_state.user = me
                            st.rerun()


def page_progress():
    u   = st.session_state.user or {}
    uid = u.get("user_id","")

    st.markdown("## 📊 My Progress")
    st.markdown("---")

    prog = api("get", f"/progress/{uid}")

    col1, col2, col3, col4 = st.columns(4)
    stats = [
        ("⚡ Total XP",        u.get("total_xp", 0)),
        ("🔥 Current Streak",  u.get("streak", 0)),
        ("✅ Tasks Completed", prog.get("completed_tasks", 0)),
        ("📈 Completion Rate", f"{prog.get('completion_rate', 0)}%"),
    ]
    for col, (label, val) in zip([col1, col2, col3, col4], stats):
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-val">{val}</div>
                <div class="metric-lbl">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Average Score")
    score = prog.get("avg_score", 0)
    st.progress(score / 100)
    st.caption(f"{score}% average across all completed tasks")


def page_leaderboard():
    u        = st.session_state.user or {}
    group_id = u.get("group_id")

    st.markdown("## 🏆 Group Leaderboard")
    st.markdown("---")

    if not group_id:
        st.info("You're not in a group yet.")
        if st.button("Join or Create a Group"):
            st.session_state.page = "onboarding"
            st.rerun()
        return

    lb = api("get", f"/leaderboard/{group_id}")
    entries = lb.get("leaderboard", [])

    if not entries:
        st.info("No members found in your group.")
        return

    medals = ["🥇","🥈","🥉"]
    for entry in entries:
        rank  = entry.get("rank",0)
        medal = medals[rank-1] if rank <= 3 else f"#{rank}"
        st.markdown(f"""<div style="background:#0f1d2e;border:1px solid #1e3a5f;
            border-radius:10px;padding:0.8rem 1.2rem;margin-bottom:0.5rem;
            display:flex;justify-content:space-between;align-items:center">
            <span style="font-size:1.1rem">{medal} &nbsp; <b>{entry.get('name','')}</b></span>
            <span>⚡ <b style="color:#38bdf8">{entry.get('xp',0)}</b> XP &nbsp;&nbsp;
                  🔥 <b style="color:#f59e0b">{entry.get('streak',0)}</b>d streak</span>
        </div>""", unsafe_allow_html=True)

# ─── Router ───────────────────────────────────────────────────────────────────

def main():
    render_sidebar()

    page = st.session_state.page

    if not st.session_state.token and page not in ("login",):
        page_login()
    elif page == "login":
        page_login()
    elif page == "dashboard":
        page_dashboard()
    elif page == "onboarding":
        page_onboarding()
    elif page == "roadmap":
        page_roadmap()
    elif page == "tasks":
        page_tasks()
    elif page == "progress":
        page_progress()
    elif page == "leaderboard":
        page_leaderboard()
    else:
        page_dashboard()

if __name__ == "__main__":
    main()
