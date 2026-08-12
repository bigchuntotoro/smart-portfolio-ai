from dataclasses import dataclass
from typing import List


# =========================================================
# 연금 납입 항목
# =========================================================

@dataclass
class ContributionItem:
    """
    하나의 연금 납입 상품을 표현합니다.
    """

    account: str
    name: str

    # 연간 목표 납입액
    annual_target: int

    # 전체 계획에서의 비중
    weight: float

    # 현재까지 납입한 금액
    current_amount: int = 0

    # -----------------------------------------------------
    # 남은 납입액
    # -----------------------------------------------------

    @property
    def remaining_amount(self) -> int:
        """
        연간 목표액에서 현재 납입액을 차감한
        남은 납입 금액을 반환합니다.
        """

        target = max(
            int(self.annual_target),
            0,
        )

        current = max(
            int(self.current_amount),
            0,
        )

        return max(
            target - current,
            0,
        )

    # -----------------------------------------------------
    # 월 기본 납입액
    # -----------------------------------------------------

    @property
    def monthly_target(self) -> int:
        """
        연간 목표액을 12개월로 나눈
        기본 월 납입액입니다.
        """

        return self.annual_target // 12


# =========================================================
# 납입 계획 계산
# =========================================================

def calculate_contribution_plan(
    items: List[ContributionItem],
) -> List[ContributionItem]:
    """
    현재 납입액을 검증하고
    목표액을 초과하지 않도록 조정합니다.

    반환값:
        ContributionItem 리스트
    """

    for item in items:

        # 음수 방지
        if item.current_amount < 0:
            item.current_amount = 0

        # 목표액 초과 방지
        if item.current_amount > item.annual_target:
            item.current_amount = item.annual_target

    return items


# =========================================================
# 전체 요약
# =========================================================

def get_summary(
    items: List[ContributionItem],
) -> dict:
    """
    전체 연금 납입 계획을 요약합니다.
    """

    total_target = sum(
        max(
            int(item.annual_target),
            0,
        )
        for item in items
    )

    total_current = sum(
        max(
            int(item.current_amount),
            0,
        )
        for item in items
    )

    total_remaining = sum(
        item.remaining_amount
        for item in items
    )

    total_monthly = sum(
        item.monthly_target
        for item in items
    )

    return {
        "total_target": total_target,
        "total_current": total_current,
        "total_remaining": total_remaining,
        "total_monthly": total_monthly,
    }


# =========================================================
# 남은 기간 기준 납입 계획
# =========================================================

def calculate_remaining_plan(
    items: List[ContributionItem],
    start_month: int,
    end_month: int,
) -> list:
    """
    특정 월부터 연말까지 남은 납입액을 계산합니다.

    예:
        8월까지 납입 완료
        start_month = 9
        end_month = 12

    → 9~12월에 납입해야 할 금액 계산
    """

    if not 1 <= start_month <= 12:
        raise ValueError(
            "start_month는 1~12 사이여야 합니다."
        )

    if not 1 <= end_month <= 12:
        raise ValueError(
            "end_month는 1~12 사이여야 합니다."
        )

    if start_month > end_month:
        return []

    remaining_months = (
        end_month - start_month + 1
    )

    result = []

    for item in items:

        target_amount = max(
            int(item.annual_target),
            0,
        )

        current_amount = max(
            int(item.current_amount),
            0,
        )

        # 현재 납입액이 목표액을 초과하지 않도록 제한
        current_amount = min(
            current_amount,
            target_amount,
        )

        remaining_amount = max(
            target_amount - current_amount,
            0,
        )

        if remaining_amount > 0:

            monthly_amount = round(
                remaining_amount
                / remaining_months
            )

        else:

            monthly_amount = 0

        result.append(
            {
                "account": item.account,
                "name": item.name,
                "target_amount": target_amount,
                "current_amount": current_amount,
                "remaining_amount": remaining_amount,
                "monthly_amount": monthly_amount,
                "weight": item.weight,
            }
        )

    return result


# =========================================================
# 월별 납입 계획
# =========================================================

def build_monthly_schedule(
    plan: list,
    start_month: int,
    end_month: int,
) -> list:
    """
    남은 납입액을 실제 월별로 배분합니다.

    마지막 달까지 남은 금액을 정확하게 맞추기 위해
    매월 남은 금액 / 남은 개월 수 방식으로 계산합니다.
    """

    if not 1 <= start_month <= 12:
        raise ValueError(
            "start_month는 1~12 사이여야 합니다."
        )

    if not 1 <= end_month <= 12:
        raise ValueError(
            "end_month는 1~12 사이여야 합니다."
        )

    if start_month > end_month:
        return []

    schedule = []

    # -----------------------------------------------------
    # 상품별 남은 금액을 복사
    # -----------------------------------------------------

    remaining_by_item = {}

    for index, item in enumerate(plan):

        key = index

        remaining_by_item[key] = max(
            int(item["remaining_amount"]),
            0,
        )

    # -----------------------------------------------------
    # 월별 계산
    # -----------------------------------------------------

    for month in range(
        start_month,
        end_month + 1,
    ):

        months_left = (
            end_month - month + 1
        )

        month_items = []
        month_total = 0

        for index, item in enumerate(plan):

            remaining = remaining_by_item[index]

            # 이미 목표 달성
            if remaining <= 0:

                amount = 0

            # 마지막 달
            elif months_left == 1:

                amount = remaining

            # 일반 월
            else:

                amount = round(
                    remaining / months_left
                )

                amount = min(
                    amount,
                    remaining,
                )

            # 남은 금액 갱신
            remaining_by_item[index] = (
                remaining - amount
            )

            month_items.append(
                {
                    "name": item["name"],
                    "account": item["account"],
                    "amount": amount,
                }
            )

            month_total += amount

        schedule.append(
            {
                "month": month,
                "total": month_total,
                "items": month_items,
            }
        )

    return schedule

