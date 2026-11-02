import csv
import os
from datetime import datetime

import streamlit as st
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

PATIENT_INFO = ["PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS",
                "US_SSN", "MRN", "LOCATION"]
LOG_FILE = "audit_log.csv"


# 1. Load the detective once (it's slow to start, so we keep it ready)
@st.cache_resource
def load_tools():
    mrn_pattern = Pattern(name="mrn", regex=r"MRN[:#\s]*\d{6,10}", score=0.9)
    mrn_detector = PatternRecognizer(supported_entity="MRN", patterns=[mrn_pattern])
    analyzer = AnalyzerEngine()
    analyzer.registry.add_recognizer(mrn_detector)
    return analyzer, AnonymizerEngine()


# 2. Write one line in the audit log (NO patient details, only the types)
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


# 3. The web page
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
        analyzer, anonymizer = load_tools()
        results = analyzer.analyze(text=text, language="en",
                                   entities=PATIENT_INFO, score_threshold=0.35)
        cleaned = anonymizer.anonymize(text=text, analyzer_results=results).text
        write_log(user, [r.entity_type for r in results])

        if results:
            st.error(f"{len(results)} patient details found and hidden. "
                     "Only send the cleaned text below.")
        else:
            st.success("No patient details found.")

        st.subheader("Cleaned text (safe to send)")
        st.code(cleaned, language="text")

        if results:
            st.subheader("What was hidden")
            st.table([{"Type": r.entity_type, "Confidence": round(r.score, 2)}
                      for r in sorted(results, key=lambda r: r.start)])

# 4. Show the audit log
st.divider()
st.subheader("Audit log")
st.caption("Shows who checked text and what types were hidden. "
           "It never saves the patient details themselves.")
if os.path.exists(LOG_FILE):
    with open(LOG_FILE) as f:
        rows = list(csv.DictReader(f))
    st.table(rows[-10:][::-1])  # newest 10, newest first
else:
    st.write("No checks yet.")