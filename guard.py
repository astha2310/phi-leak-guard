from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# 1. Teach the detective what a hospital record number (MRN) looks like
#    Example: "MRN 4482913" or "MRN: 55120934"
mrn_pattern = Pattern(name="mrn", regex=r"MRN[:#\s]*\d{6,10}", score=0.9)
mrn_detector = PatternRecognizer(supported_entity="MRN", patterns=[mrn_pattern])

# 2. Start the detective and give it the new MRN skill
analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(mrn_detector)

# 3. Only look for these kinds of patient info (this stops the false "URL" alarms)
PATIENT_INFO = ["PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS",
                "US_SSN", "MRN", "LOCATION"]

# 4. A FAKE doctor's note (not a real patient)
note = (
    "Patient John Carter, MRN 4482913, born 03/14/1982, lives in Tempe. "
    "Seen on 10/20/2026 for chest pain. Call 602-555-0147 or "
    "email john.carter@example.com. SSN 512-48-3721."
)

# 5. Find the patient info
results = analyzer.analyze(text=note, language="en",
                           entities=PATIENT_INFO, score_threshold=0.35)

# 6. Black it out
anonymizer = AnonymizerEngine()
cleaned = anonymizer.anonymize(text=note, analyzer_results=results)

# 7. Show before and after
print("BEFORE (unsafe to send to AI):")
print(note)
print("\nAFTER (safe to send to AI):")
print(cleaned.text)
print("\nWhat was hidden:")
for r in sorted(results, key=lambda r: r.start):
    print(f"  {r.entity_type:14} -> {note[r.start:r.end]}")