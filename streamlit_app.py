import streamlit as st
import os
import zipfile
import shutil
import tempfile
import subprocess
from pathlib import Path
import google.generativeai as genai
# types is not needed for direct content creation this way
# from google.generativeai import types

# ----------------------------------------------------
# Gemini Client (Streamlit settings for API Key)
# ----------------------------------------------------
def get_gemini_client():
    # Configure the API key globally before creating the model
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    # Create the GenerativeModel instance
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "temperature": 1,
            "max_output_tokens": 65535,
        },
        safety_settings=[],
    )
    return model

# ----------------------------------------------------
# Generate Code using Gemini
# ----------------------------------------------------
def generate_code(prompt: str) -> dict:
    client = get_gemini_client()
    # Correct way to structure content for genai.GenerativeModel.generate_content
    # Pass the prompt directly as a string, or a dictionary if you need roles.
    # For a single user prompt, a string is often sufficient.
    # If you need to specify roles explicitly for more complex multi-turn, use:
    contents = {
        "role": "user",
        "parts": [{"text": prompt}],
    }

    response = client.generate_content(contents)
    return {"app.py": response.text}

# ----------------------------------------------------
# Package files into zip
# ----------------------------------------------------
def package_project(files: dict) -> str:
    tmpdir = tempfile.mkdtemp()
    for filename, content in files.items():
        with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    # Default files
    with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
        f.write("streamlit\npython-dotenv\ngoogle-generativeai\n")

    with open(os.path.join(tmpdir, ".env"), "w") as f:
        f.write("GEMINI_API_KEY=your-generated-app-key\n")

    with open(os.path.join(tmpdir, "README.md"), "w") as f:
        f.write("# Generated Streamlit App\n\nRun with:\n```\nstreamlit run app.py\n```")

    zip_path = os.path.join(tmpdir, "project.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for root, _, filenames in os.walk(tmpdir):
            for filename in filenames:
                if filename != "project.zip":
                    zipf.write(os.path.join(root, filename), arcname=filename)

    return zip_path

# ----------------------------------------------------
# Streamlit Tabs
# ----------------------------------------------------
st.set_page_config(page_title="Invision Code.AI", layout="wide")
st.title("💡 Invision Code.AI — Streamlit Application Generator")

tab1, tab2, tab3 = st.tabs(["💬 Chat", "📂 Code & Download", "🚀 Preview"])

# --- Tab 1: Chat Interface ---
with tab1:
    st.subheader("Describe the app you want to build")
    user_prompt = st.text_area("Prompt", height=200)
    if st.button("Generate App Code"):
        if user_prompt.strip():
            with st.spinner("Generating with Gemini..."):
                files = generate_code(user_prompt)
                st.session_state["files"] = files
                st.success("Code generated!")

# --- Tab 2: Generated Code & Download ---
with tab2:
    st.subheader("Generated Files")
    if "files" in st.session_state:
        for filename, content in st.session_state["files"].items():
            st.download_button(
                f"Download {filename}",
                data=content,
                file_name=filename,
                mime="text/plain",
            )
            st.code(content, language="python")

        zip_path = package_project(st.session_state["files"])
        with open(zip_path, "rb") as f:
            st.download_button("⬇️ Download Full Project (ZIP)", f, file_name="project.zip")
    else:
        st.info("No files yet. Generate from the Chat tab.")

# --- Tab 3: Preview ---
with tab3:
    st.subheader("Live Preview")
    if "files" in st.session_state:
        tmpdir = tempfile.mkdtemp()
        app_file = os.path.join(tmpdir, "app.py")
        with open(app_file, "w", encoding="utf-8") as f:
            f.write(st.session_state["files"]["app.py"])

        # Run streamlit app inside iframe
        st.info("⚡ Preview runs only locally. On Streamlit Cloud, use download & deploy.")
        st.code(open(app_file).read(), language="python")
    else:
        st.info("No app generated yet.")
