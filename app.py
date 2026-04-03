import streamlit as st
import time
from client import gem3
from roadmap import roadmap_generator
import urllib.parse
import os
from googleapiclient.discovery import build
import json

# Load the summer programs database once
with open("ivy_scholars_db.json", "r", encoding="utf-8") as f:
    summer_programs = json.load(f)

# Load SerpAPI key and search function
import serpapi
from dotenv import load_dotenv
load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def serpapi_search(query, num_results=1):
    if not SERPAPI_KEY:
        return ["#"] * num_results
    client = serpapi.Client(api_key=SERPAPI_KEY)
    results = client.search({
        "engine": "google",
        "q": query,
        "num": num_results,
        "hl": "en",
        "gl": "us"
    })
    links = [item.get("link") for item in results.get("organic_results", []) if item.get("link")]
    # fill with placeholder if not enough results
    while len(links) < num_results:
        links.append("#")
    return links[:num_results]


# --- APP CONFIGURATION ---
st.set_page_config(page_title="Career Granny", layout="wide", page_icon="🚀")

# --- PROFESSIONAL STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    div.stButton > button:first-child {
        background-color: #007bff; color: white; border-radius: 8px; border: none; transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #0056b3; border: none; }
    
    /* Clickable Card Styling */
    .career-card {
        background-color: black; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #007bff;
        margin-bottom: 15px; cursor: pointer; transition: transform 0.2s;
    }
    .career-card:hover { transform: translateY(-5px); border-left: 5px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.user_data = {}
    st.session_state.profiles = [] # Saved Profiles
    st.session_state.target = ""
    st.session_state.recommendations = None

# --- SHARED FUNCTIONS ---
def multi_step_loader(messages):
    """Simulates a multi-step professional loading process."""
    container = st.empty()
    progress_bar = st.progress(0)
    for i, msg in enumerate(messages):
        container.info(f"⏳ {msg}...")
        progress_bar.progress((i + 1) / len(messages))
        time.sleep(0.8)
    container.empty()
    progress_bar.empty()

def save_profile():
    if st.session_state.user_data:
        profile = {
            "name": f"Analysis {len(st.session_state.profiles) + 1}",
            "data": st.session_state.user_data,
            "target": st.session_state.target
        }
        st.session_state.profiles.append(profile)
        st.toast("✅ Profile saved!")

# --- SIDEBAR: PROFILE MANAGEMENT ---
with st.sidebar:
    st.title("👤 Student Portal")
    if st.button("➕ New Analysis"):
        st.session_state.step = 1
        st.session_state.target = ""
        st.rerun()
    
    st.divider()
    st.subheader("Saved Profiles")
    if not st.session_state.profiles:
        st.caption("No profiles saved yet.")
    for idx, p in enumerate(st.session_state.profiles):
        if st.sidebar.button(f"📂 {p['name']}: {p['target'] if p['target'] else 'New'}", key=f"prof_{idx}"):
            st.session_state.user_data = p['data']
            st.session_state.target = p['target']
            st.session_state.step = 3 if p['target'] else 2
            st.rerun()

# --- MAIN APP FLOW ---

# STEP 1: SMART INPUT
if st.session_state.step == 1:
    st.title("Career Granny")
    st.markdown("#### *Let's build your personalized future roadmap.*")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.subheader("Your Background")
            skills = st.text_area("What are you good at?", placeholder="e.g. Python, Graphic Design, Public Speaking")
            courses = st.text_area("Advanced Courses", placeholder="e.g. AP Physics, IB English, Honors Math")
            enrichment = st.text_area("Extracurriculars & Hobbies", placeholder="e.g. Robotics Club, Volunteering, Blogging")

            if st.button("Generate My Path ➔"):
                if skills and courses:
                    st.session_state.user_data = {"skills": skills, "courses": courses}
                    multi_step_loader(["Analyzing skills", "Matching with college majors", "Scanning industry trends"])
                    st.session_state.step = 2
                    st.rerun()
                else:
                    st.warning("Please fill in your background to proceed.")
    with col2:
        st.image("https://illustrations.popsy.co", width=True)

# --- STEP 2: LIST CAREER & COLLEGE PATHS WITH DESCRIPTIONS ---
elif st.session_state.step == 2:
    st.subheader("🎯 Recommended Career & College Paths")
    st.caption("Click on the path name to explore more details.")

    data = st.session_state.user_data
    if not st.session_state.recommendations:
        prompt = (f"Suggest 3 high-impact career paths and 3 high-impact college majors for a student with skills: {data['skills']} "
                  f"and courses: {data['courses']}. Return ONLY a comma-separated list of titles.")
        raw_rec = gem3(prompt)
        st.session_state.recommendations = [r.strip() for r in raw_rec.split(',')]

    # Show paths with description; path name clickable
    for idx, rec in enumerate(st.session_state.recommendations):
        description_prompt = f"Provide 2-3 sentence description for the career/college path: {rec}."
        desc = gem3(description_prompt)

        st.markdown(f"[**{rec}**](#)", unsafe_allow_html=True)
        st.markdown(desc)

        if st.button(f"Explore {rec}", key=f"explore_{idx}"):
            st.session_state.target = rec
            st.session_state.step = 3
            st.rerun()


# --- STEP 3: ENRICHMENT & CATEGORIZED ADVICE ---
elif st.session_state.step == 3:
    target = st.session_state.target
    st.title(f"🔍 Career Deep Dive: {target}")

    # Load summer programs DB
    with open("ivy_scholars_db.json", "r", encoding="utf-8") as f:
        summer_programs = json.load(f)

    # GPT selects 3 best summer programs plus 3 additional recommendations
    program_summaries = [f"{p['name']}: {p['description'][:300]}" for p in summer_programs]
    program_prompt = f"""
    You are a California college counselor. A student is interested in the following career/major: "{target}".
    From the list below of summer programs (name and short description), select the 3 programs that would best help this student in this field.
    Add 3 more different summer programs that are high rigor, prestigious, and relevant to this career/major that are NOT in the list.
    Return ONLY a comma-separated list of program names.

    Programs:
    {chr(10).join(program_summaries)}
    """
    selected_programs_raw = gem3(program_prompt)
    selected_programs = [s.strip() for s in selected_programs_raw.split(",")]


    skill_query = gem3(f"List the top 5 technical skills for {target}. Return ONLY a comma-separated list.")
    skills_list = [s.strip() for s in skill_query.split(",")]

    # Save skills to session state for Step 4
    st.session_state.skills_list = skills_list

    # --- ENRICHMENT / COURSES / COMPETITIONS / SUMMER PROGRAMS ---
    st.divider()
    st.subheader("Growth Opportunities")
    enrichment_prompt = (f"Act as a personal college and career counselor. For a student interested in {target}, "
                         f"provide a report with these EXACT headings:\n"
                         f"### Online Courses\n(List 4 reputable courses from Coursera/edX/Stanford and 2 community college courses)\n"
                         f"### Competitions & Fairs\n(List 6 prestigious science/writing/industry competitions)\n"
                         f"### Summer Programs\n(Include the selected summer programs with full descriptions)\n"
                         f"### Key Skills\n(List the top 5 technical skills neededfor {target})\n"
                         f"### UC Application Tips\n(Provide a strategic tip for the Personal Insight Questions).")

    with st.container(border=True):
        enrichment_result = gem3(enrichment_prompt)
        st.markdown(enrichment_result)

    # --- CLICKABLE SKILL LINKS FOR ROADMAP ---
    st.write("---")
    st.write("#### 🛠 Build a Roadmap\nClick on a key technical skill to start learning:")
    for idx, skill in enumerate(st.session_state.skills_list[:5]):  # top 5 skills
        if st.button(f"💡 {skill}", key=f"skill_{idx}"):
            st.session_state.skill = skill
            st.session_state.step = 4
            st.rerun()


# --- STEP 4: VERIFIED ROADMAP ---
elif st.session_state.step == 4:
    skill = st.session_state.get("skill", None)
    if not skill:
        st.error("No skill selected. Returning to Strategy page...")
        st.session_state.step = 3
        st.rerun()

    st.title(f"📅 4-Week Mastery: {skill}")

    roadmap = roadmap_generator(skill)

    # If it's a dict already
    st.json(roadmap)


    if st.button("⬅️ Back to Insights"):
        st.session_state.step = 3
        st.rerun()
