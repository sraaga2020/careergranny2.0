import streamlit as st
import time
from client import gem3
from roadmap import roadmap_generator
import os
import json
import serpapi
from dotenv import load_dotenv

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Career Granny", layout="wide", page_icon="🚀")
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# -------------------- CACHED LOADERS --------------------
@st.cache_data
def load_summer_programs():
    with open("ivy_scholars_db.json", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(show_spinner=False)
def cached_gem3(prompt):
    return gem3(prompt)

@st.cache_data(show_spinner=False)
def get_recommendations(skills, courses):
    prompt = (
        f"Suggest 3 high-impact career paths and 3 high-impact college majors for a student with skills: {skills} "
        f"and courses: {courses}. Return ONLY a comma-separated list of titles."
    )
    raw = cached_gem3(prompt)
    return [r.strip() for r in raw.split(',')]

@st.cache_data(show_spinner=False)
def get_description(rec):
    return cached_gem3(f"Provide 2-3 sentence description for the career/college path: {rec}.")

@st.cache_data(show_spinner=False)
def get_step3_data(target, program_summaries):
    program_prompt = f"""
    You are a California college counselor. A student is interested in the following career/major: \"{target}\".
    From the list below of summer programs (name and short description), select the 3 programs that would best help this student in this field.
    Add 3 more different summer programs that are high rigor, prestigious, and relevant to this career/major that are NOT in the list.
    Return ONLY a comma-separated list of program names.

    Programs:
    {chr(10).join(program_summaries)}
    """

    enrichment_prompt = (
        f"Act as a personal college and career counselor. For a student interested in {target}, "
        f"provide a report with these EXACT headings:\n"
        f"### Online Courses\n"
        f"### Competitions & Fairs\n"
        f"### Summer Programs\n"
        f"### Key Skills\n"
        f"### UC Application Tips"
    )

    programs = cached_gem3(program_prompt)
    skills = cached_gem3(f"List the top 5 technical skills for {target}. Return ONLY a comma-separated list.")
    enrichment = cached_gem3(enrichment_prompt)

    return {
        "programs": [s.strip() for s in programs.split(",")],
        "skills": [s.strip() for s in skills.split(",")],
        "enrichment": enrichment
    }

# -------------------- HELPERS --------------------
def multi_step_loader(messages):
    container = st.empty()
    progress_bar = st.progress(0)
    for i, msg in enumerate(messages):
        container.info(f"⏳ {msg}...")
        progress_bar.progress((i + 1) / len(messages))
        time.sleep(0.2)
    container.empty()
    progress_bar.empty()

# -------------------- SESSION INIT --------------------
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.user_data = {}
    st.session_state.profiles = []
    st.session_state.target = ""
    st.session_state.recommendations = None
    st.session_state.step3_data = None

# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.title("👤 Student Portal")
    if st.button("➕ New Analysis"):
        st.session_state.step = 1
        st.session_state.target = ""
        st.session_state.recommendations = None
        st.session_state.step3_data = None
        st.rerun()

# -------------------- LOAD DATA ONCE --------------------
summer_programs = load_summer_programs()

# -------------------- STEP 1 --------------------
if st.session_state.step == 1:
    st.title("Career Granny")

    skills = st.text_area("What are you good at?")
    courses = st.text_area("Advanced Courses")

    if st.button("Generate My Path ➔"):
        if skills and courses:
            st.session_state.user_data = {"skills": skills, "courses": courses}
            multi_step_loader(["Analyzing skills", "Matching careers"])
            st.session_state.step = 2
            st.rerun()
        else:
            st.warning("Fill required fields")

# -------------------- STEP 2 --------------------
elif st.session_state.step == 2:
    st.subheader("🎯 Recommended Paths")

    data = st.session_state.user_data

    if not st.session_state.recommendations:
        st.session_state.recommendations = get_recommendations(data['skills'], data['courses'])

    for idx, rec in enumerate(st.session_state.recommendations):
        desc = get_description(rec)
        st.markdown(f"**{rec}**")
        st.markdown(desc)

        if st.button(f"Explore {rec}", key=f"explore_{idx}"):
            st.session_state.target = rec
            st.session_state.step = 3
            st.session_state.step3_data = None
            st.rerun()

# -------------------- STEP 3 --------------------
elif st.session_state.step == 3:
    target = st.session_state.target
    st.title(f"🔍 Career Deep Dive: {target}")

    if not st.session_state.step3_data:
        summaries = [f"{p['name']}: {p['description'][:300]}" for p in summer_programs]
        st.session_state.step3_data = get_step3_data(target, summaries)

    data = st.session_state.step3_data

    st.subheader("Growth Opportunities")
    st.markdown(data["enrichment"])

    st.write("#### 🛠 Build a Roadmap")
    for idx, skill in enumerate(data["skills"]):
        if st.button(f"💡 {skill}", key=f"skill_{idx}"):
            st.session_state.skill = skill
            st.session_state.step = 4
            st.rerun()

# -------------------- STEP 4 --------------------
elif st.session_state.step == 4:
    skill = st.session_state.get("skill")
    st.title(f"📅 4-Week Mastery: {skill}")

    roadmap = roadmap_generator(skill)
    st.json(roadmap)

    if st.button("⬅️ Back"):
        st.session_state.step = 3
        st.rerun()
