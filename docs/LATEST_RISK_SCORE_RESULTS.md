# Latest Risk Score Results

작성일: 2026-05-15 KST

## 할 작업

```text
M9. 최신 risk score 리포트 생성
```

## 왜 하는가

MVP 최종 산출물에는 "현재 어떤 차량/부품 조합이 위험 신호가 높은가"를 보여주는 결과물이 필요하다.

## 무엇을 어떻게 했는가

다음 스크립트를 만들었다.

```text
pipelines/generate_latest_risk_report.py
```

역할:

```text
1. latest_risk_scores.csv 읽기
2. 최신 week의 top risk score 정리
3. score 의미와 한계 문서화
4. markdown report 생성
```

## 실행 명령

```bash
python pipelines/generate_latest_risk_report.py --run-id 20260515T114046Z --top-k 25
```

## 결과 파일

```text
reports/latest_risk_score_report.md
docs/LATEST_RISK_SCORE_RESULTS.md
data/processed/backfill/20260515T114046Z/latest_risk_report_summary.json
```

## 최신 기준 week

```text
2026-05-11
```

## score 의미

현재 MVP에서 `baseline_risk_score`는 리콜 확률이 아니다.

의미:

```text
최근 complaint count가 과거 8주 평균 대비 얼마나 튀었는가
```

즉:

```text
높은 점수 = 최근 해당 차량/부품 조합의 complaint spike가 있었다
낮은 점수 = 최근 spike 신호가 약하다
```

## Top risk score 일부

| Rank | Make | Model | Year | Component | Week | Complaints | Score |
|---:|---|---|---:|---|---:|---:|---:|
| 1 | FORD | BRONCO SPORT | 2021 | UNKNOWN OR OTHER | 2026-05-11 | 2 | 2.8062 |
| 2 | FORD | BRONCO SPORT | 2022 | ENGINE | 2026-05-11 | 1 | 2.4749 |
| 3 | FORD | ESCAPE | 2015 | POWER TRAIN | 2026-05-11 | 1 | 2.4749 |
| 4 | FORD | EXPLORER | 2020 | STRUCTURE | 2026-05-11 | 1 | 2.4749 |
| 5 | FORD | EXPLORER | 2021 | ENGINE | 2026-05-11 | 1 | 2.4749 |
| 10 | HYUNDAI | KONA | 2020 | VEHICLE SPEED CONTROL | 2026-05-11 | 1 | 2.4749 |
| 19 | KIA | EV6 | 2022 | POWER TRAIN | 2026-05-11 | 1 | 2.4749 |
| 25 | KIA | TELLURIDE | 2021 | STRUCTURE | 2026-05-11 | 1 | 2.4749 |

## 해석

1. 최신 week에서는 대부분 complaint count가 1건이다.
2. 과거 baseline이 낮은 entity에서는 1건만 발생해도 spike score가 높게 나온다.
3. 따라서 이 리포트는 "확정 위험"이 아니라 "최근 이상 신호 후보"로 해석해야 한다.
4. MVP에서는 이 정도 리포트면 충분하다.

## 한계

```text
1. complaint spike만 사용한다.
2. component mapping이 아직 거칠다.
3. investigation/manufacturer communication 데이터가 없다.
4. F-150처럼 complaints endpoint coverage가 약한 모델은 과소평가될 수 있다.
5. score calibration이 되지 않았다.
```

## 결정

M9는 완료로 본다.

다음 단계에서는 README와 MVP 재현 절차를 정리한다.

## 다음 작업

```text
M10. MVP README 정리
```

