from src.core.risk import risk_score

def recommend(data):
    score = risk_score(data)

    if score <= 0:
        return ["채권 ETF", "고배당 ETF"]

    elif score <= 3:
        return ["S&P500 ETF", "배당 ETF"]

    else:
        return ["나스닥 ETF", "테마 ETF"]