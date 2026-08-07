def simulate(years, monthly, rate):
    result = 0
    for _ in range(years * 12):
        result = (result + monthly) * (1 + rate / 12)
    return int(result)