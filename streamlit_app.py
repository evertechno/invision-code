import streamlit as st
import os
import zipfile
import tempfile
import shutil
import base64
import requests

# --- Helper Functions ---
def call_gemini_api(prompt, api_key):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    data = {
        "model": "gemini-2.5-flash",
        "config": {
            "temperature": 2,
            "maxOutputTokens": 65535,
            "thinkingConfig": {"thinkingBudget": 0},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_LOW_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_LOW_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_LOW_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_LOW_AND_ABOVE"}
            ]
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]
    }
    # Replace with Gemini endpoint
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContentStream"
    resp = requests.post(endpoint, headers=headers, json=data, stream=True)
    output = ""
    for line in resp.iter_lines():
        if line:
            output += line.decode("utf-8")
    return output

def create_app_files(app_code, requirements, readme):
    temp_dir = tempfile.mkdtemp()
    files = {
        "app.py": app_code,
        "requirements.txt": requirements,
        "README.md": readme,
    }
    for fname, content in files.items():
        with open(os.path.join(temp_dir, fname), "w") as f:
            f.write(content)
    return temp_dir

def zip_dir(dir_path):
    zip_path = os.path.join(tempfile.gettempdir(), "invision_code_ai.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for foldername, subfolders, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                arcname = os.path.relpath(file_path, dir_path)
                zipf.write(file_path, arcname)
    return zip_path

def get_zip_download_link(zip_path):
    with open(zip_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/zip;base64,{b64}" download="invision_code_ai.zip">Download ZIP</a>'
    return href

def run_generated_app(code):
    try:
        local_vars = {}
        exec(code, {}, local_vars)
    except Exception as e:
        st.error(f"Error running generated app: {e}")

# --- Streamlit UI ---
st.set_page_config(page_title="Invision Code.AI", layout="wide")

if "app_code" not in st.session_state:
    st.session_state.app_code = ""
if "requirements" not in st.session_state:
    st.session_state.requirements = ""
if "readme" not in st.session_state:
    st.session_state.readme = ""
if "last_prompt" not in st.session_state:
    st.session_state.last_prompt = ""

st.sidebar.title("Invision Code.AI Admin")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("Gemini API Key loaded from Streamlit secrets.")
else:
    api_key = None
    st.sidebar.error("Please add GEMINI_API_KEY to your Streamlit secrets!")

tabs = st.tabs(["Chat", "Generated Files", "Preview"])

with tabs[0]:
    st.header("AI Chat Interface")
    prompt = st.text_area("Describe your Streamlit application requirements:", height=200)
    if st.button("Generate Application", key="generate_app"):
        if not api_key:
            st.error("No Gemini API Key found in Streamlit secrets.")
        elif not prompt:
            st.warning("Please write a prompt to describe your application.")
        else:
            st.info("Generating application... this may take a while with max tokens.")
            meta_prompt = f"""
Generate a fully working Streamlit application in Python based on the following user prompt. All code must use Streamlit ONLY.
Create 3 files: 
1. app.py (main Streamlit app code)
2. requirements.txt (all dependencies, include streamlit)
3. README.md (usage instructions).
Application prompt: {prompt}
"""
            output = call_gemini_api(meta_prompt, api_key)
            # Parse output for files (simple heuristics)
            def extract_code(tag, text):
                import re
                match = re.search(rf"{tag}\s*```(?:python|txt|markdown)?\s*(.*?)```", text, re.DOTALL)
                return match.group(1).strip() if match else ""
            st.session_state.app_code = extract_code("app.py", output)
            st.session_state.requirements = extract_code("requirements.txt", output)
            st.session_state.readme = extract_code("README.md", output)
            st.session_state.last_prompt = prompt
            st.success("Generation complete. See files and preview in next tabs.")

with tabs[1]:
    st.header("Generated Files")
    if st.session_state.app_code:
        st.subheader("app.py")
        st.code(st.session_state.app_code, language="python")
        st.subheader("requirements.txt")
        st.code(st.session_state.requirements, language="text")
        st.subheader("README.md")
        st.code(st.session_state.readme, language="markdown")
        temp_dir = create_app_files(
            st.session_state.app_code,
            st.session_state.requirements,
            st.session_state.readme
        )
        zip_path = zip_dir(temp_dir)
        st.markdown(get_zip_download_link(zip_path), unsafe_allow_html=True)
    else:
        st.info("No files generated yet. Please use the Chat tab first.")

with tabs[2]:
    st.header("Live Preview")
    if st.session_state.app_code:
        st.info("Below is a live preview of the generated Streamlit app. (Some features may not work in preview mode.)")
        run_generated_app(st.session_state.app_code)
    else:
        st.info("No application code yet. Generate your app in the Chat tab.")
