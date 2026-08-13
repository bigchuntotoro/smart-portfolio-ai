from typing import Any, Dict, List


def calculate_portfolio_weights(portfolio_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    현재 포트폴리오의 평가금액과 목표 비중을 바탕으로
    종목별 현재 비중 및 괴리율(Drift)을 계산합니다.
    """
    total_val = sum(item.get("current_val", 0) for item in portfolio_items)
    results = []
    max_drift = 0.0

    for item in portfolio_items:
        current_val = item.get("current_val", 0)
        target_weight = item.get("target_weight", 0.0)  # 예: 0.25 (25%)

        current_weight = (current_val / total_val) if total_val > 0 else 0.0
        drift = current_weight - target_weight  # 양수: 비중 초과, 음수: 비중 부족

        if abs(drift) > max_drift:
            max_drift = abs(drift)

        results.append({
            "account": item.get("account", "공통"),
            "name": item["name"],
            "current_val": current_val,
            "target_weight": target_weight,
            "current_weight": current_weight,
            "drift": drift,
        })

    return {
        "total_val": total_val,
        "max_drift": max_drift,
        "items": results,
    }


def calculate_buy_only_rebalancing(
        portfolio_items: List[Dict[str, Any]],
        new_contribution: int,
        threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    매도 없이 이번 달 신규 납입금(new_contribution)만으로
    목표 비중에 가깝게 채워 넣는 매수 전용 리밸런싱 실행 계획을 산출합니다.
    """
    analysis = calculate_portfolio_weights(portfolio_items)
    total_current = analysis["total_val"]
    total_future = total_current + new_contribution

    items_analysis = analysis["items"]
    rebalance_needed = analysis["max_drift"] >= threshold

    # 1. 납입 후 목표 가치 대비 부족한 금액 계산
    needed_buys = []
    for item in items_analysis:
        target_future_val = total_future * item["target_weight"]
        needed = max(0.0, target_future_val - item["current_val"])
        needed_buys.append(needed)

    total_needed = sum(needed_buys)

    # 2. 신규 납입금 범위 내 매수액 배분 (10,000원 단위 절사)
    buy_plans = []
    for idx, item in enumerate(items_analysis):
        needed = needed_buys[idx]

        if total_needed > 0 and new_contribution > 0:
            allocated = new_contribution * (needed / total_needed)
        elif new_contribution > 0:
            allocated = new_contribution * item["target_weight"]
        else:
            allocated = 0.0

        # 실제 증권사 주문 편의성을 위해 1만원 단위 절사
        recommended_buy = (int(allocated) // 10000) * 10000

        buy_plans.append({
            "account": item["account"],
            "name": item["name"],
            "current_val": item["current_val"],
            "current_weight": item["current_weight"],
            "target_weight": item["target_weight"],
            "drift": item["drift"],
            "recommended_buy": recommended_buy,
        })

    return {
        "total_current": total_current,
        "new_contribution": new_contribution,
        "rebalance_needed": rebalance_needed,
        "max_drift": analysis["max_drift"],
        "buy_plans": buy_plans,
    }