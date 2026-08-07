import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_advice(summary):
    prompt = f"""
    다음 자산 상태를 분석해서 투자 전략을 설명해줘:

    {summary}

    현실적인 조언을 해줘.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content