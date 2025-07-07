import streamlit as st
import pypdf
import tempfile
import os
import google.generativeai as genai
from fpdf import FPDF

# --- Google Gemini API Configuration ---
# IMPORTANT:
# You need to set an environment variable named 'GOOGLE_API_KEY'
# with your actual Gemini API key before running this script.

# How to set it in your environment:
# 1. For macOS/Linux (Bash/Zsh):
#    Open your terminal and type:
#    export GOOGLE_API_KEY="AIzaSyDTYgPWA-qegXx3lSRnEdNzkBsqXwzlxsk"
#    (Replace with YOUR actual key. For permanent setting, add this line to your ~/.bashrc or ~/.zshrc file
#    and then run `source ~/.bashrc` or `source ~/.zshrc` in the terminal.)
# 2. For Windows (Command Prompt):
#    set GOOGLE_API_KEY="AIzaSyDTYgPWA-qegXx3lSRnEdNzkBsqXwzlxsk"
#    (Replace with YOUR actual key. For permanent setting, use `setx GOOGLE_API_KEY "YOUR_KEY_HERE"` in Command Prompt,
#    you may need to restart your terminal/IDE.)
# 3. For Google Colab:
#    Use the "Secrets" feature (key icon 🔑 on the left sidebar). Add a new secret
#    named `GOOGLE_API_KEY` and paste your API key there. Ensure "Notebook access" is toggled ON.

# Get the API key from environment variables
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- IMPORTANT: API Key Validation ---
if not GEMINI_API_KEY:
    st.error("Error: Google Gemini API key not found in environment variables.")
    st.warning("Please set the 'GOOGLE_API_KEY' environment variable with your actual API key.")
    st.stop() # Stop the Streamlit app if the API key is not set

# Configure the Google Generative AI library with the API key
genai.configure(api_key=GEMINI_API_KEY)

# --- End of Configuration ---

def extract_text_from_pdf(pdf_file):
    """
    Extracts text content from a given PDF file.
    """
    try:
        pdf_reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            # Ensure extract_text() result is handled in case it's None
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""

def ask_question_to_gemini(text, question):
    """
    Sends the PDF content and a question to a Google Gemini model
    and returns the generated answer.
    """
    if not text.strip():
        return "PDF content is empty or could not be extracted. Cannot ask questions."

    # --- FIX: Changed model from 'gemini-pro' to 'gemini-1.5-flash' ---
    # 'gemini-pro' might not be available in all regions or for all API versions.
    # 'gemini-1.5-flash' is a generally good and widely available model.
    model = genai.GenerativeModel('gemini-1.5-flash')
    # If 'gemini-1.5-flash' also gives a 404 error, you can try:
    # model = genai.GenerativeModel('gemini-1.0-pro')
    # Or, uncomment the following to list available models:
    # try:
    #     available_models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
    #     st.info(f"Available models for generateContent: {', '.join(available_models)}")
    # except Exception as e:
    #     st.warning(f"Could not list models: {e}")

    prompt = f"PDF Content:\n{text}\n\nQuestion: {question}\nAnswer:"
    try:
        # Generate content using the Gemini model
        response = model.generate_content(prompt)
        # Check if response.text is not empty or None
        if response.text:
            return response.text.strip()
        else:
            return "Gemini returned an empty answer. Please try a different question or PDF content."
    except Exception as e:
        # Display a more specific error message if the API call fails
        st.error(f"Error calling Gemini API: {e}. This might be due to an invalid model name, API key, network issues, or exceeding rate limits.")
        return "Could not get an answer from the AI. Please check your API key, model name, internet connection, or try again later."

def export_answers_to_pdf(answers):
    """
    Exports a list of questions and their corresponding answers to a PDF file.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    # Add a title to the PDF
    pdf.cell(200, 10, txt="Saved Q&A from Notes to PDF", ln=True, align="C")
    pdf.ln(10)

    # Add each question and answer to the PDF
    for idx, qa in enumerate(answers):
        # Use .get for robustness in case 'question' or 'answer' keys are missing
        question_str = str(qa.get('question', 'N/A Question'))
        answer_str = str(qa.get('answer', 'N/A Answer'))
        pdf.multi_cell(0, 10, txt=f"Q{idx+1}: {question_str}\nA{idx+1}: {answer_str}\n")

    # Create a temporary file to save the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
        pdf.output(tmpfile.name)
        return tmpfile.name

# --- Streamlit User Interface ---
st.set_page_config(page_title="Notes to PDF - AI Assistant", layout="centered")
st.title("🧠 Notes to PDF: AI-powered Q&A App")

st.markdown("Upload a PDF and ask questions. Save answers during your session!")

# Initialize session state
if 'saved_answers' not in st.session_state:
    st.session_state.saved_answers = []

# Upload PDF
uploaded_file = st.file_uploader("Upload your PDF", type="pdf")

# Extract text if file is uploaded
if uploaded_file:
    pdf_text = extract_text_from_pdf(uploaded_file)

    if pdf_text:
        # Text input
        question = st.text_input("Ask a question about the PDF content")

        # Ask question
        if st.button("Get Answer") and question:
            with st.spinner("Getting answer from AI..."):
                answer = ask_question_to_gemini(pdf_text, question)
                st.session_state.last_answer = answer
                st.session_state.last_question = question
                #st.write("**Answer:**", answer)

        # Show answer from session (even after rerun)
        if "last_answer" in st.session_state and st.session_state.last_answer:
            st.write("**Answer:**", st.session_state.last_answer)

            if "Could not get an answer" not in st.session_state.last_answer:
                if st.button("Save this Answer"):
                    st.session_state.saved_answers.append({
                        "question": st.session_state.last_question,
                        "answer": st.session_state.last_answer
                    })
                    st.success("Answer saved!")
    else:
        st.warning("Could not extract text from the PDF. Please ensure it's a valid, text-based PDF.")

# Display saved answers
if st.session_state.saved_answers:
    st.subheader("📒 Saved Answers")
    for idx, qa in enumerate(st.session_state.saved_answers):
        st.markdown(f"**Q{idx+1}: {qa.get('question', 'N/A Question')}**")
        st.markdown(f"_A{idx+1}: {qa.get('answer', 'N/A Answer')}_")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear All Saved Answers"):
            st.session_state.saved_answers = []
            st.info("Saved answers cleared.")
    with col2:
        if st.button("📄 Export All as PDF"):
            pdf_path = export_answers_to_pdf(st.session_state.saved_answers)
            with open(pdf_path, "rb") as file:
                st.download_button(
                    label="Download PDF",
                    data=file,
                    file_name="saved_answers.pdf",
                    mime="application/pdf"
                )
            os.remove(pdf_path)
# Clean up the temporary PDF file after download

#set GOOGLE_API_KEY="AIzaSyDHQxpok1gRIntR-Gc_4nHSMfYtaK2hAG4"