from presidio_analyzer import AnalyzerEngine

# 1. Start the "detective" that looks for personal info
analyzer = AnalyzerEngine()

# 2. A FAKE doctor's note (not a real patient)
note = (
    "Patient John Carter, born 03/14/1982, was seen on 10/20/2026 for chest pain. "
    "Call him at 602-555-0147 or email john.carter@example.com. SSN 123-45-6789."
)

# 3. Ask the detective to find personal info in the note
results = analyzer.analyze(text=note, language="en")

# 4. Show what it found
print("Found", len(results), "pieces of patient info:\n")
for r in results:
    found_text = note[r.start:r.end]
    print(f"{r.entity_type:15} -> {found_text}   (confidence {r.score:.2f})")