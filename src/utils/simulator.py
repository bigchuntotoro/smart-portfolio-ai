import pandas as pd


def run_retirement_simulation(
        current_age: int = 35,
        retirement_age: int = 60,
        life_expectancy: int = 85,
        current_asset: int = 10_000_000,
        monthly_contribution: int = 750_000,
        annual_return_accumulation: float = 0.07,  # 축적기 기대 수익률 (7%)
        annual_return_retirement: float = 0.04,  # 수령기 기대 수익률 (4%)
        annual_inflation_rate: float = 0.025,  # 물가상승률 (2.5%)
        target_monthly_withdrawal: int = 2_500_000,  # 은퇴 후 희망 월 수령액
) -> dict:
    """
    현재 연령부터 은퇴 및 기대수명 시점까지의 자산 성장 및 인출 시뮬레이션을 수행합니다.
    """
    records = []

    asset_nominal = float(current_asset)  # 명목 자산
    total_principal = float(current_asset)  # 총 투입 원금

    monthly_return_acc = (1 + annual_return_accumulation) ** (1 / 12) - 1
    monthly_return_ret = (1 + annual_return_retirement) ** (1 / 12) - 1
    monthly_inflation = (1 + annual_inflation_rate) ** (1 / 12) - 1

    depleted_age = None  # 자산 고갈 연령

    total_years = life_expectancy - current_age

    for year_idx in range(total_years + 1):
        age = current_age + year_idx
        is_retired = age >= retirement_age

        # 1년 단위 복리 연산 (12개월 반복)
        for month in range(12):
            if year_idx == 0 and month == 0:
                continue

            if not is_retired:
                # 축적기: 월 납입금 투입 + 수익률 반영
                asset_nominal = (asset_nominal + monthly_contribution) * (1 + monthly_return_acc)
                total_principal += monthly_contribution
            else:
                # 수령기: 물가상승률 반영된 희망 월 인출액 차감 + 잔여 자산 수익률 반영
                # 은퇴 시점 대비 물가상승이 반영된 월 인출 필요액 계산
                years_from_start = year_idx + (month / 12)
                adjusted_withdrawal = target_monthly_withdrawal * ((1 + annual_inflation_rate) ** years_from_start)

                asset_nominal = (asset_nominal - adjusted_withdrawal) * (1 + monthly_return_ret)

                # 자산 고갈 체크
                if asset_nominal <= 0 and depleted_age is None:
                    asset_nominal = 0
                    depleted_age = age

        # 실질 자산 가치 계산 (현재 가치 환산)
        real_asset = asset_nominal / ((1 + annual_inflation_rate) ** year_idx)

        records.append({
            "연령": age,
            "구분": "은퇴 후 수령기" if is_retired else "자산 축적기",
            "총 투입 원금": int(total_principal),
            "명목 자산": int(max(0, asset_nominal)),
            "실질 자산(현재가치)": int(max(0, real_asset)),
        })

    df_result = pd.DataFrame(records)

    # 은퇴 시점 자산
    retire_row = df_result[df_result["연령"] == retirement_age]
    asset_at_retirement = retire_row["명목 자산"].values[0] if not retire_row.empty else 0
    real_asset_at_retirement = retire_row["실질 자산(현재가치)"].values[0] if not retire_row.empty else 0

    return {
        "df": df_result,
        "asset_at_retirement": asset_at_retirement,
        "real_asset_at_retirement": real_asset_at_retirement,
        "total_principal_at_retirement": df_result[df_result["연령"] == retirement_age]["총 투입 원금"].values[0],
        "depleted_age": depleted_age,
    }