def analyze_portfolio(data):
    total = data["cash"] + sum(p["amount"] for p in data["products"])

    cash_ratio = data["cash"] / total
    invest_ratio = 1 - cash_ratio

    return {
        "total": total,
        "cash_ratio": round(cash_ratio, 2),
        "invest_ratio": round(invest_ratio, 2)
    }