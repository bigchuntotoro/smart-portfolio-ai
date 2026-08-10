import json
import os


class ETFData:

    def __init__(self):
        # 프로젝트 루트 기준으로 etf_list.json 위치 지정
        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        self.file = os.path.join(
            base_dir,
            "src",
            "data",
            "etf_list.json"
        )

        # 리스크 변환 맵
        self.risk_map = {
            "낮음": 1,
            "중간": 3,
            "높음": 5,
        }

    def _convert_risk(self, etf: dict) -> dict:
        """리스크를 숫자로 변환하고 원본 리스크 이름도 유지합니다."""

        risk_str = etf.get(
            "risk",
            "중간"
        )

        return {
            **etf,
            "risk": self.risk_map.get(
                risk_str,
                3
            ),
            "risk_label": risk_str,
        }

    def get_etfs(self) -> list:
        """JSON에서 ETF 데이터를 읽고 안정화된 리스트를 반환합니다."""

        try:
            with open(
                self.file,
                "r",
                encoding="utf-8"
            ) as f:

                raw_data = json.load(f)

        except FileNotFoundError:
            print(
                f"ETF 파일을 찾을 수 없습니다: {self.file}"
            )
            return []

        except json.JSONDecodeError as e:
            print(
                f"ETF JSON 형식 오류: {e}"
            )
            return []

        safe_data = []

        for etf in raw_data:

            try:
                converted = self._convert_risk(
                    etf
                )

                # 데이터 타입 안정화
                converted["price"] = float(
                    converted.get(
                        "price",
                        0
                    )
                )

                converted["return_1y"] = float(
                    converted.get(
                        "return_1y",
                        0
                    )
                )

                converted["dividend"] = float(
                    converted.get(
                        "dividend",
                        0
                    )
                )

                converted["risk"] = int(
                    converted.get(
                        "risk",
                        3
                    )
                )

                safe_data.append(
                    converted
                )

            except Exception as e:

                print(
                    f"ETF 데이터 오류: "
                    f"{etf.get('name')} / {e}"
                )

        return safe_data
