import csv
import os
from datetime import datetime

import ollama
import streamlit as st
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

PATIENT_INFO = ["PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS",
                "US_SSN", "MRN", "LOCATION"]
LOG_FILE = "audit_log.csv"
AI_MODEL = "qwen2.5:3b"
SYSTEM_MESSAGE = (
    "You are a helpful assistant for hospital staff. The text you receive has "
    "already been de-identified: tags like <PERSON>, <MRN> and <DATE_TIME> replace "
    "private details, so it contains no real patient information and is safe to "
    "work with. Do only the task you are asked, and keep your answer short. "
    "Focus on the medical facts. Do not repeat contact details or ID tags "
    "(like <PHONE_NUMBER>, <EMAIL_ADDRESS>, <US_SSN>, <MRN>) unless asked. "
    "Never try to guess what a tag hides."
)


# 1. Load the detective once
@st.cache_resource
def load_tools():
    mrn_pattern = Pattern(name="mrn", regex=r"MRN[:#\s]*\d{6,10}", score=0.9)
    mrn_detector = PatternRecognizer(supported_entity="MRN", patterns=[mrn_pattern])
    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(mrn_detector)
    return analyzer, AnonymizerEngine()


# 2. Find and black out patient info in any text
def clean_text(text):
    analyzer, anonymizer = load_tools()
    results = analyzer.analyze(text=text, language="en",
                               entities=PATIENT_INFO, score_threshold=0.35)
    cleaned = anonymizer.anonymize(text=text, analyzer_results=results).text
    return cleaned, results


# 3. Write one line in the audit log (NO patient details, only the types)
def write_log(user, types_found):
    is_new_file = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(["time", "user", "items_hidden", "types_hidden"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user,
            len(types_found),
            ", ".join(sorted(set(types_found))) or "none",
        ])


# 4. The page
st.title("PHI Leak Guard")
st.write("Paste text here **before** you send it to an AI tool. "
         "Patient details are hidden first.")

user = st.text_input("Your name or staff ID", "nurse.demo")
text = st.text_area("Text to check", height=200,
                    placeholder="Paste a note here (use fake patients only)...")

if st.button("Check and clean"):
    if not text.strip():
        st.warning("Paste some text first.")
    else:
        cleaned, results = clean_text(text)
        write_log(user, [r.entity_type for r in results])
        # Remember the results, so they stay on screen after other clicks
        st.session_state["cleaned"] = cleaned
        st.session_state["found"] = [(r.entity_type, round(r.score, 2))
                                     for r in sorted(results, key=lambda r: r.start)]
        st.session_state["ai_answer"] = None

if "cleaned" in st.session_state:
    found = st.session_state["found"]
    if found:
        st.error(f"{len(found)} patient details found and hidden. "
                 "Only the cleaned text below can go to the AI.")
    else:
        st.success("No patient details found.")

    st.subheader("Cleaned text (safe to send)")
    st.code(st.session_state["cleaned"], language="text", wrap_lines=True)

    if found:
        st.subheader("What was hidden")
        st.table([{"Type": t, "Confidence": s} for t, s in found])

    # 5. Ask the AI, which only ever gets the cleaned text
    st.subheader("Ask the AI")
    st.caption("The AI runs on this computer and only receives the cleaned text.")
    question = st.text_input("What should the AI do?",
                             "Summarize this note in 2 short sentences.")

    if st.button("Send cleaned text to AI"):
        # Double-check at the door: clean the question too,
        # in case someone typed a patient's name into it
        prompt, extra = clean_text(question + "\n\n" + st.session_state["cleaned"])
        if extra:
            write_log(user, [r.entity_type for r in extra])
        with st.spinner("The AI is thinking..."):
            try:
                reply = ollama.chat(model=AI_MODEL, messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ])
                st.session_state["ai_answer"] = reply.message.content
                st.session_state["sent_prompt"] = prompt
            except Exception as error:
                st.session_state["ai_answer"] = None
                st.error(f"Could not reach the AI. Is the Ollama app open? ({error})")

    if st.session_state.get("ai_answer"):
        st.markdown("**AI answer:**")
        st.write(st.session_state["ai_answer"])
        with st.expander("Exactly what the AI received"):
            st.code(st.session_state["sent_prompt"], language="text", wrap_lines=True)

# 6. Audit log
st.divider()
st.subheader("Audit log")
st.caption("Shows who checked text and what types were hidden. "
           "It never saves the patient details themselves.")
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        rows = list(csv.DictReader(f))
    st.table(rows[-10:][::-1])
else:
    st.write("No checks yet.")