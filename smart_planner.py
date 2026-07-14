import os
import streamlit as st
from groq import Groq
from datetime import date
import plotly.graph_objects as go

st.set_page_config(page_title="Smart Study Planner", page_icon="📚", layout="wide")

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #F0F4FF; }
[data-testid="stHeader"]           { background: transparent; }
[data-testid="stSidebar"]          { background: #FFFFFF; border-right: 1px solid #E2E8F0; }

/* Fix all text inputs — make them clearly visible */
input[type="text"], input[type="password"],
[data-testid="stTextInput"] input {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 8px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #4F46E5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.15) !important;
}

/* Buttons */
[data-testid="stButton"] > button {
    background: #4F46E5 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
[data-testid="stButton"] > button:hover {
    background: #4338CA !important;
}

.topbar {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
    border-radius: 16px; padding: 1.4rem 2rem; margin-bottom: 1.5rem;
}
.topbar h1 { margin:0; font-size:1.7rem; font-weight:800; color:#FFFFFF; }
.topbar p  { margin:0; color:#C4B5FD; font-size:0.88rem; }

.kpi-row { display:flex; gap:1rem; margin-bottom:1.25rem; }
.kpi {
    flex:1; background:#FFFFFF; border-radius:14px;
    padding:1.1rem 1.25rem; border:1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.kpi-label { font-size:0.72rem; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em; }
.kpi-value { font-size:1.9rem; font-weight:800; color:#1E293B; line-height:1.1; }
.kpi-sub   { font-size:0.76rem; color:#64748B; margin-top:2px; }

.card {
    background:#FFFFFF; border-radius:14px;
    padding:1.25rem 1.5rem; margin-bottom:1.25rem;
    border:1px solid #E2E8F0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.card-title { font-size:1rem; font-weight:700; color:#1E293B; margin-bottom:.75rem; }

.ai-box {
    background:#EEF2FF; border:1px solid #C7D2FE;
    border-radius:12px; padding:1rem 1.25rem;
    font-size:0.92rem; color:#312E81; line-height:1.65;
    margin-top:.75rem;
}
.tip-item { font-size:0.85rem; color:#475569; padding: 5px 0; border-bottom: 1px solid #F1F5F9; }
.tip-item:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SUBJECT_COLORS = {
    "Mathematics":  "#4F46E5",
    "Physics":      "#0891B2",
    "Chemistry":    "#059669",
    "Biology":      "#65A30D",
    "History":      "#D97706",
    "Geography":    "#EA580C",
    "English":      "#DC2626",
    "Computer Sc.": "#7C3AED",
    "Economics":    "#0D9488",
    "Other":        "#6B7280",
}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"subjects": [], "schedule": [], "ai_tip": "", "ai_history": []}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
def total_scheduled(subj=None):
    return sum(r["hours"] for r in st.session_state.schedule if not subj or r["subject"] == subj)

def total_done(subj=None):
    return sum(r["hours"] for r in st.session_state.schedule
               if r["done"] and (not subj or r["subject"] == subj))

def pct(done, total):
    return int(done / total * 100) if total else 0

def color_for(name):
    return next((s["color"] for s in st.session_state.subjects if s["name"] == name), "#6B7280")

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
    st.divider()

    st.markdown("**➕ Add Subject**")
    new_subj = st.selectbox("Subject", list(SUBJECT_COLORS.keys()))
    target_h = st.slider("Weekly target (hrs)", 1, 20, 5)
    if st.button("Add Subject", use_container_width=True):
        if new_subj in [s["name"] for s in st.session_state.subjects]:
            st.warning("Already added.")
        else:
            st.session_state.subjects.append(
                {"name": new_subj, "target_hours": target_h, "color": SUBJECT_COLORS[new_subj]}
            )
            st.rerun()

    st.divider()
    st.markdown("**📅 Add Study Slot**")
    if st.session_state.subjects:
        slot_day  = st.selectbox("Day", DAYS)
        slot_subj = st.selectbox("Subject", [s["name"] for s in st.session_state.subjects])
        slot_hrs  = st.number_input("Hours", 0.5, 8.0, 1.0, 0.5)
        if st.button("Add Slot", use_container_width=True):
            st.session_state.schedule.append(
                {"day": slot_day, "subject": slot_subj, "hours": slot_hrs, "done": False}
            )
            st.rerun()
    else:
        st.info("Add a subject first.")

    st.divider()
    if st.button("🗑 Reset Everything", use_container_width=True):
        st.session_state.subjects   = []
        st.session_state.schedule   = []
        st.session_state.ai_tip     = ""
        st.session_state.ai_history = []
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER + KPIs
# ══════════════════════════════════════════════════════════════════════════════
today_str = date.today().strftime("%A, %d %B %Y")
st.markdown(f"""
<div class="topbar">
  <h1>📚 Smart Study Planner</h1>
  <p>AI-powered weekly schedule · progress tracking · insights &nbsp;|&nbsp; 📅 {today_str}</p>
</div>""", unsafe_allow_html=True)

ts = total_scheduled()
td = total_done()
st.markdown(f"""
<div class="kpi-row">
  <div class="kpi"><div class="kpi-label">Subjects</div>
    <div class="kpi-value">{len(st.session_state.subjects)}</div><div class="kpi-sub">being tracked</div></div>
  <div class="kpi"><div class="kpi-label">Scheduled</div>
    <div class="kpi-value">{ts:.1f}h</div><div class="kpi-sub">this week</div></div>
  <div class="kpi"><div class="kpi-label">Completed</div>
    <div class="kpi-value">{td:.1f}h</div><div class="kpi-sub">marked done</div></div>
  <div class="kpi"><div class="kpi-label">Progress</div>
    <div class="kpi-value">{pct(td,ts)}%</div><div class="kpi-sub">of weekly plan</div></div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TWO COLUMNS
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns([1.1, 1], gap="large")

# ── LEFT: Schedule + Charts ───────────────────────────────────────────────────
with col_left:

    # Schedule card
    with st.container(border=True):
        st.markdown("#### 📅 Weekly Schedule")
        if not st.session_state.schedule:
            st.info("No slots yet — add subjects and study slots from the sidebar.")
        else:
            for day in DAYS:
                day_slots = [(i, r) for i, r in enumerate(st.session_state.schedule) if r["day"] == day]
                if not day_slots:
                    continue
                st.markdown(f"**{day}**")
                for i, row in day_slots:
                    c1, c2, c3 = st.columns([3, 1, 0.5])
                    c1.markdown(
                        f"<span style='color:{color_for(row['subject'])};font-weight:600;"
                        f"font-size:0.9rem'>{row['subject']}</span>",
                        unsafe_allow_html=True
                    )
                    c2.markdown(
                        f"<span style='color:#64748B;font-size:0.85rem'>{row['hours']}h</span>",
                        unsafe_allow_html=True
                    )
                    new_done = c3.checkbox("✓", value=row["done"], key=f"chk_{i}")
                    if new_done != row["done"]:
                        st.session_state.schedule[i]["done"] = new_done
                        st.rerun()

    # Charts
    if st.session_state.subjects and st.session_state.schedule:
        names  = [s["name"]  for s in st.session_state.subjects]
        sched  = [total_scheduled(n) for n in names]
        done_h = [total_done(n)      for n in names]
        colors = [s["color"] for s in st.session_state.subjects]

        with st.container(border=True):
            st.markdown("#### 📊 Hours by Subject")
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(name="Scheduled", x=names, y=sched,
                                  marker_color="#C7D2FE", marker_line_width=0))
            fig1.add_trace(go.Bar(name="Completed",  x=names, y=done_h,
                                  marker_color="#4F46E5", marker_line_width=0))
            fig1.update_layout(
                barmode="overlay", height=230,
                margin=dict(l=0, r=0, t=24, b=0),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11, color="#475569"),
                legend=dict(orientation="h", y=1.18, x=0),
                yaxis=dict(gridcolor="#F1F5F9", ticksuffix="h"),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

        with st.container(border=True):
            st.markdown("#### 🥧 Time Allocation")
            fig2 = go.Figure(go.Pie(
                labels=names, values=sched, marker=dict(colors=colors),
                hole=0.55, textinfo="label+percent", textfont=dict(size=11),
            ))
            fig2.update_layout(
                height=230, margin=dict(l=0, r=0, t=10, b=0),
                paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ── RIGHT: Progress + AI Coach + Tips ────────────────────────────────────────
with col_right:

    # Subject progress
    with st.container(border=True):
        st.markdown("#### 🎯 Subject Progress")
        if not st.session_state.subjects:
            st.info("Add subjects from the sidebar to track progress.")
        else:
            for subj in st.session_state.subjects:
                n = subj["name"]
                t = subj["target_hours"]
                d = total_done(n)
                p = pct(d, t)
                st.markdown(
                    f"<p style='margin:0 0 2px;font-size:0.88rem;font-weight:600;"
                    f"color:{subj['color']}'>{n}</p>",
                    unsafe_allow_html=True
                )
                st.progress(min(p / 100, 1.0))
                st.caption(f"{d}h done / {t}h target · {p}% of weekly goal")

    # ── AI Coach ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 🤖 AI Study Coach")

        # Use a form so Enter key submits and the input is clearly styled
        with st.form(key="ai_form", clear_on_submit=True):
            ai_q = st.text_input(
                "Your question",
                placeholder="e.g. How should I balance Maths and Physics this week?",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("💬 Get AI Advice", use_container_width=True)

        if submitted:
            if not api_key:
                st.warning("Enter your Groq API key in the sidebar first.")
            elif not ai_q.strip():
                st.warning("Please type a question above.")
            else:
                subj_ctx = ", ".join(
                    f"{s['name']} ({total_done(s['name'])}h done / {s['target_hours']}h target)"
                    for s in st.session_state.subjects
                ) or "No subjects added"
                sched_ctx = "\n".join(
                    f"  {r['day']}: {r['subject']} {r['hours']}h {'✓' if r['done'] else '○'}"
                    for r in st.session_state.schedule
                ) or "No schedule yet"
                system = (
                    f"You are an encouraging, practical student study coach.\n"
                    f"Student subjects: {subj_ctx}\n"
                    f"Schedule:\n{sched_ctx}\n"
                    f"Give 3-5 sentences of specific, actionable advice."
                )
                with st.spinner("Coach is thinking..."):
                    try:
                        client = Groq(api_key=api_key)
                        st.session_state.ai_history.append({"role": "user", "content": ai_q})
                        resp = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "system", "content": system}]
                                     + st.session_state.ai_history,
                            temperature=0.7, max_tokens=400,
                        )
                        reply = resp.choices[0].message.content.strip()
                        st.session_state.ai_history.append({"role": "assistant", "content": reply})
                        st.session_state.ai_tip = reply
                    except Exception as e:
                        st.error(f"API Error: {e}")

        if st.session_state.ai_tip:
            st.markdown(
                f'<div class="ai-box">💡 {st.session_state.ai_tip}</div>',
                unsafe_allow_html=True
            )

        if len(st.session_state.ai_history) > 2:
            with st.expander("📜 View chat history"):
                for msg in st.session_state.ai_history[-6:]:
                    label = "🧑 You" if msg["role"] == "user" else "🤖 Coach"
                    st.markdown(f"**{label}:** {msg['content']}")

    # ── Study Tips ────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 💡 Study Tips")
        for tip in [
            "📌 Pomodoro technique — 25 min focus, 5 min break.",
            "🔁 Review notes within 24 hrs to boost retention by 60%.",
            "🎯 Prioritise subjects where you're behind your weekly target.",
            "😴 Sleep consolidates memory — don't sacrifice it for late-night cramming.",
        ]:
            st.markdown(f'<p class="tip-item">{tip}</p>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("📚 Smart Study Planner · Powered by Groq LPU + LLaMA 3.3 70B · Built with Streamlit")