def risk_score(data):
    score = 0

    if data["age"] > 50:
        score -= 2

    if data["cash"] > (data["cash"] + sum(p["amount"] for p in data["products"])) * 0.6:
        score -= 1

    if any(p["type"] == "ETF" for p in data["products"]):
        score += 2

    return score