import streamlit as st
import json
import re
import os
from dotenv import load_dotenv
from client import gem3
import streamlit.components.v1 as components
from serpapi import GoogleSearch

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# --- SerpAPI Search Function with Caching ---
@st.cache_data(show_spinner=False)
def serpapi_search(query, num_results=3):
    """Perform Google search via SerpAPI and return a list of links."""
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num_results
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    links = []
    for item in results.get("organic_results", []):
        link = item.get("link")
        if link:
            links.append(link)
        if len(links) >= num_results:
            break
    return links

# --- Fetch real links for a mini-topic ---
def fetch_resource_links(skill, week_num, mini_title):
    articles = serpapi_search(
        f"{skill} educational article for high school students Week {week_num} - {mini_title}",
        num_results=3
    )
    courses = serpapi_search(
        f"{skill} reputable online course Coursera edX Stanford community college high school Week {week_num} - {mini_title}",
        num_results=3
    )
    videos = serpapi_search(
        f"{skill} tutorial video for high school students Week {week_num} - {mini_title} site:youtube.com",
        num_results=3
    )
    return {"articles": articles, "courses": courses, "videos": videos}

# --- Roadmap Generator ---
def roadmap_generator(skill):

    # --- Session State Defaults ---
    if "roadmap" not in st.session_state:
        st.session_state.roadmap = None
    if "progress" not in st.session_state:
        st.session_state.progress = {}
    if "deep_dives" not in st.session_state:
        st.session_state.deep_dives = {}

    # --- Helper Functions ---
    def clean_json(raw):
        raw = raw.strip()
        raw = re.sub(r"```json", "", raw)
        raw = re.sub(r"```", "", raw)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        return raw.strip()

    def repair_json(raw):
        raw = raw.replace("'", '"')
        raw = re.sub(r",\s*}", "}", raw)
        raw = re.sub(r",\s*]", "]", raw)
        return raw

    def safe_get(d, key, fallback):
        if isinstance(d, dict):
            val = d.get(key)
            if val in [None, "", [], {}]:
                return fallback
            return val
        return fallback

    def generate_week_focus(overview):
        prompt = f"""
Summarize the following learning week overview into a concise 3–5 word phrase that captures the focus:
Overview: \"\"\"{overview}\"\"\"
Phrase:
"""
        try:
            raw = gem3(prompt)
            phrase = raw.strip().strip('"').strip("'")
            return phrase if phrase else "Week Focus"
        except:
            return "Week Focus"

    # --- Render Quiz for a Mini-Topic ---
    def render_quiz(mini_key, topic, skill):
        quiz_key = f"{mini_key}_quiz"
        if quiz_key not in st.session_state:
            prompt = f"""
Return STRICT JSON only. Generate a 5-question multiple choice quiz for the topic "{topic}" in the skill "{skill}".
Each question must have:
- "question": a complete sentence
- "options": 4 choices
- "answer": correct option text
- "explanation": short explanation
Do NOT leave any field empty.
Example format:
{{
"quiz":[{{"question":"Sample?","options":["A","B","C","D"],"answer":"A","explanation":"A is correct"}}]
}}
"""
            try:
                raw = gem3(prompt)
                cleaned = clean_json(raw)
                quiz_data = json.loads(cleaned).get("quiz", [])
            except:
                quiz_data = []

            while len(quiz_data) < 5:
                quiz_data.append({
                    "question": f"Placeholder Question {len(quiz_data)+1}",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "answer": "Option A",
                    "explanation": "Option A is correct as placeholder."
                })
            st.session_state[quiz_key] = quiz_data

        quiz = st.session_state[quiz_key]
        with st.expander("📋 Quiz (Read Only)"):
            for i, q in enumerate(quiz):
                st.markdown(f"**Q{i+1}: {q['question']}**")
                for opt in q["options"]:
                    st.markdown(f"- {opt}")
            with st.expander("Reveal Answers"):
                st.markdown("### ✅ Answers & Explanations")
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q['answer']}** — {q['explanation']}")

    # --- Generate Roadmap JSON via AI ---
    if st.session_state.roadmap is None:
        prompt = f"""
Return STRICT JSON only. Write a 4-week roadmap for "{skill}".
Each week must have 3 mini-topics, each with 3 resources (video, article, course).
Format:
{{
  "Week 1": {{
    "overview": "...",
    "goal": "...",
    "weekly_project": {{
      "title": "...",
      "steps": ["Step 1","Step 2","Step 3"],
      "deliverable": "...",
      "difficulty": "easy/medium/hard"
    }},
    "mini_topics":[{{"title":"...","description":"...","resources":{{"video":[],"article":[],"course":[]}}}}...]
  }},
  "Week 2": {{ ... }},
  "Week 3": {{ ... }},
  "Week 4": {{ ... }}
}}
"""
        with st.spinner("Generating roadmap..."):
            raw_output = gem3(prompt)
        try:
            cleaned = clean_json(raw_output)
            roadmap = json.loads(cleaned)
        except:
            try:
                repaired = repair_json(cleaned)
                roadmap = json.loads(repaired)
                st.warning("⚠️ JSON auto-repaired")
            except Exception as e:
                st.error("❌ Failed to parse roadmap JSON")
                st.write(e)
                st.subheader("Raw Model Output:")
                st.code(raw_output)
                st.stop()
        st.session_state.roadmap = roadmap

    roadmap = st.session_state.roadmap
    if not roadmap:
        st.error("No roadmap data found.")
        return

    # --- Render Roadmap ---
    total_tasks = sum(len(week.get("mini_topics", [])) for week in roadmap.values())
    completed_tasks = sum(1 for v in st.session_state.progress.values() if v)
    if total_tasks > 0:
        st.progress(completed_tasks / total_tasks)
        st.caption(f"Overall Progress: {completed_tasks}/{total_tasks} mini-topics completed")

    for week_name, week_data in roadmap.items():
        week_num = int(re.search(r'\d+', week_name).group(0))
        overview = safe_get(week_data, "overview", "Overview not provided")
        week_heading = f"{week_name} – {generate_week_focus(overview)}"

        with st.expander(f"📘 {week_heading}"):
            goal = safe_get(week_data, "goal", "Goal not provided")
            st.markdown(f"**Overview:** {overview}")
            st.markdown(f"**Goal:** {goal}")

            mini_topics = week_data.get("mini_topics", [])
            total_mini = len(mini_topics)
            completed_mini = sum(
                1 for idx in range(total_mini)
                if st.session_state.progress.get(f"{week_name}_{idx}_done")
            )
            if total_mini > 0:
                st.progress(completed_mini / total_mini)
                st.caption(f"Week Progress: {completed_mini}/{total_mini} mini-topics completed")

            for idx, mini in enumerate(mini_topics):
                mini_key = f"{week_name}_{idx}"
                mini_title = safe_get(mini, "title", "Untitled Topic")
                with st.expander(f"▶ {mini_title}"):
                    st.markdown(safe_get(mini, "description", "No description"))

                    # Fetch resources with caching
                    resources = fetch_resource_links(skill, week_num, mini_title)
                    mini["resources"] = {
                        "video": resources.get("videos", []),
                        "article": resources.get("articles", []),
                        "course": resources.get("courses", [])
                    }

                    # Display resources with actual link text
                    for res_type, res_list in mini["resources"].items():
                        st.markdown(f"**{res_type.capitalize()}s:**")
                        for link in res_list:
                            st.markdown(f"- [{link}]({link})")

                    # Completion checkbox
                    done_key = f"{mini_key}_done"
                    done = st.checkbox("Mark Complete", key=done_key)
                    st.session_state.progress[done_key] = done

                    # Quiz inside mini-topic
                    render_quiz(mini_key, mini_title, skill)

                    # --- Deep Dive ---
                    deep_key = f"{mini_key}_deep"
                    if deep_key not in st.session_state:
                        st.session_state[deep_key] = None
                    with st.expander("🔍 Go Deeper"):
                        if st.session_state[deep_key] is None:
                            with st.spinner("Generating deep dive..."):
                                deep_prompt = f"""
Return STRICT JSON only. Expand the topic "{mini_title}" in {skill}.
Fill every field realistically. Format:
{{
"advanced_concepts":["concept1","concept2","concept3"],
"detailed_explanation":"Explain the topic in detail.",
"mini_project":{{"title":"Project","description":"Describe","steps":["Step1","Step2","Step3"]}}
}}
"""
                                raw = gem3(deep_prompt)
                                cleaned = clean_json(raw)
                                try:
                                    deep_data = json.loads(cleaned)
                                except:
                                    deep_data = {}
                                st.session_state[deep_key] = deep_data

                        deep = st.session_state[deep_key]
                        if deep:
                            st.markdown("### 🧠 Advanced Concepts")
                            for concept in safe_get(deep, "advanced_concepts", []):
                                st.markdown(f"- {concept}")
                            st.markdown("### 📖 Explanation")
                            st.write(safe_get(deep, "detailed_explanation", "No explanation"))
                            proj = safe_get(deep, "mini_project", {})
                            st.markdown(f"### 🚀 Challenge Project: {safe_get(proj,'title','Project')}")
                            st.write(safe_get(proj, "description","No description"))
                            st.markdown("**Steps:**")
                            for step in safe_get(proj,"steps",[]):
                                st.markdown(f"- {step}")

                            st.markdown("---")  # separates deep dive from Q&A

                            # --- User-Driven Deep Dive / Q&A ---
                            st.markdown("**AI Guidance / Resources:**")
                            with st.expander("💬 Curious? Ask a question"):
                                user_q_key = f"{mini_key}_user_question"
                                user_answer_key = f"{mini_key}_user_answer"
                                context = f"Topic: {mini_title}\nSkill: {skill}\n"
                                deep_context = json.dumps(deep, indent=2) if deep else ""

                                user_question = st.text_input(
                                    "Ask any question about this topic or project:",
                                    key=user_q_key
                                )

                                if st.button("Get Guidance / Resources", key=f"{mini_key}_ask_btn"):
                                    if user_question.strip():
                                        with st.spinner("Fetching guidance..."):
                                            prompt = f"""
You are an AI learning assistant. The user wants help with the following learning roadmap topic or project. Provide guidance, resources, and/or explanations as needed.

Context:
{context}
Deep Dive Content:
{deep_context}

User Question:
\"\"\"{user_question}\"\"\"

Answer in a concise, practical way with guidance, resources, and/or steps.
"""
                                            try:
                                                response = gem3(prompt)
                                            except:
                                                response = "Sorry, guidance could not be generated."

                                            st.session_state[user_answer_key] = response

                                if st.session_state.get(user_answer_key):
                                    st.markdown("**AI Guidance / Resources:**")
                                    st.write(st.session_state[user_answer_key])

            # --- Weekly Project ---
            proj = safe_get(week_data, "weekly_project", {})
            st.markdown(f"### Project: {safe_get(proj,'title','Weekly Project')}")
            steps = safe_get(proj, "steps", [])
            for step in steps:
                st.markdown(f"- {step}")
            st.info(f"Deliverable: {safe_get(proj,'deliverable','N/A')} ({safe_get(proj,'difficulty','medium')})")
