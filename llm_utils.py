import openai
from config import Config

openai.api_key = Config.OPENAI_API_KEY

def get_embedding(text, model="text-embedding-3-large"):
    response = openai.embeddings.create(
        input=[text],
        model=model
    )
    return response.data[0].embedding

def generate_completion(prompt, model="gpt-4o-mini", temperature=0.7, max_tokens=500):
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content

ANALYSIS_PROMPT_TEMPLATE = """
You are a financial analyst. Given the following excerpts from a company's financial reports, provide a detailed analysis focusing on:

- Revenue trends
- Risks and challenges
- Growth opportunities
- Any anomalies or important points

Summarize the key points clearly and concisely.

Report excerpts:
{report_text}

Analysis:
"""

def analyze_report(chunks):
    combined_text = "\n\n".join(chunks)
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(report_text=combined_text)
    return generate_completion(prompt)
