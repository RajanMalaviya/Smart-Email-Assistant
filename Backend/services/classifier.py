import os
from typing import List, Dict, Any
from datetime import datetime
from services.db_service import get_unclassified_emails, update_email_classification
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate

CATEGORIES = [
    "Work / Professional",
    "Personal",
    "Support / Service Requests",
    "Promotions / Marketing",
    "Spam / Junk",
    "Finance / Bills",
    "Meetings / Scheduling",
    "Notifications / Updates",
    "Other"
]

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)

classifier_prompt = ChatPromptTemplate.from_template(
"""
You are a highly accurate email classification agent.

Your task is to classify an email into ONE of the following categories:
{categories}

Guidelines:
- Always choose the BEST possible category, even if the email is ambiguous.
- Use ALL available context (subject, snippet, body, sender, labels, etc.).
- Be consistent across similar emails.
- Confidence should reflect how strongly the text fits the chosen category (0.0 = guess, 1.0 = very certain).

Return ONLY a JSON object with the following fields:
- category: the chosen category (string, must be from the provided list)
- confidence: a number between 0 and 1
- reasoning: a short sentence explaining why you chose this category
- summary: a brief summary of the email content (1-2 sentences)
Here is an example output:
```json
{{
  "category": "Work / Professional",
  "confidence": 0.92,
  "reasoning": "The email discusses project updates and deadlines, which are typical of professional work communications.",
  "summary": "The email provides updates on the current project status and upcoming deadlines."
}}
```

Email Details:
- Subject: {subject}
- From: {sender}
- Snippet: {snippet}
- Body: {body}
"""
)

# 🔹 Classify Function (updated for reasoning)
def classify_email(email: Dict[str, Any]) -> Dict[str, Any]:
    """Classify a single email using Gemini with reasoning + confidence."""
    chain = classifier_prompt | llm
    result = chain.invoke({
        "categories": CATEGORIES,
        "subject": email.get("subject", ""),
        "sender": email.get("from", ""),   # ✅ added sender
        "snippet": email.get("snippet", ""),
        "body": email.get("body_plain", "") or email.get("body_html", "")
    })

    raw_output = result.content.strip()

    # Clean markdown wrappers like ```json ... ```
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`").replace("json", "", 1).strip()

    try:
        import json
        classification = json.loads(raw_output)

        category = classification.get("category", "Other")
        confidence = float(classification.get("confidence", 0.5))
        reasoning = classification.get("reasoning", "No reasoning provided")
        summary = classification.get("summary", "")

    except Exception as e:
        print(f"[ERROR] Failed to parse classification result: {raw_output}")
        category, confidence, reasoning, summary = "Other", 0.5, "Parsing error", ""

    # Print confirmation (for logs/debugging)
    print(f"[CLASSIFIED] {email.get('subject', '')[:40]}... → {category} "
          f"(confidence: {confidence:.2f}) | reason: {reasoning} | summary: {summary}")

    return {
        "category": category,
        "confidence": confidence,
        "reasoning": reasoning,
        "summary": summary
    }

# 🔹 Main Agent Function
import time

def classify_unclassified_emails(limit: int = 5, delay: int = 6):
    emails = get_unclassified_emails()
    if not emails:
        print("[INFO] No unclassified emails found ✅")
        return

    for i, email in enumerate(emails[:limit]):
        print(f"\n[PROCESSING {i+1}/{limit}] From: {email.get('from')} | Subject: {email.get('subject', '')[:50]}")
        classification = classify_email(email)
        update_email_classification(
            provider_message_id=email["provider_message_id"],
            category=classification["category"],
            confidence=classification["confidence"],
            reasoning=classification["reasoning"],
            summary=classification["summary"]
        )
        time.sleep(delay)  # prevent hitting quota

    print("\n[FINISHED] Classification batch completed ✅")

# 🔹 Run Script
if __name__ == "__main__":
    classify_unclassified_emails()
