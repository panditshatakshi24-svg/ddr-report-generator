import json
from groq import Groq

DDR_PROMPT = """
You are an expert building diagnostics report writer.

You are given raw text from two documents:
1. INSPECTION REPORT - site observations and issue descriptions
2. THERMAL REPORT - temperature readings and thermal findings

Generate a DDR (Detailed Diagnostic Report) as a JSON object.

STRICT RULES:
- Do NOT invent facts not in the documents
- If info is missing → write "Not Available"
- If info conflicts → mention the conflict
- Use simple, client-friendly language
- No duplicate observations

Return ONLY valid JSON with this structure:
{
  "property_issue_summary": "Overall summary...",
  "area_wise_observations": [
    {
      "area": "Area name",
      "observations": ["observation 1", "observation 2"],
      "thermal_findings": ["thermal finding if any"],
      "image_tag": "inspection or thermal or none"
    }
  ],
  "probable_root_cause": [
    {"issue": "Issue name", "cause": "Explanation"}
  ],
  "severity_assessment": [
    {"area": "Area", "severity": "High/Medium/Low", "reasoning": "Why"}
  ],
  "recommended_actions": [
    {"action": "What to do", "priority": "Immediate/Short-term/Long-term"}
  ],
  "additional_notes": "Extra notes or Not Available",
  "missing_or_unclear_information": ["item 1", "item 2"]
}
"""

def generate_ddr(inspection_text: str, thermal_text: str, api_key: str) -> dict:
    client = Groq(api_key=api_key)

    user_message = f"""
INSPECTION REPORT:
{inspection_text}

---

THERMAL REPORT:
{thermal_text}

---

Generate the DDR JSON now.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": DDR_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    result = response.choices[0].message.content
    return json.loads(result)
