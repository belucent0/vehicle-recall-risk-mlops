# 프로젝트 범위: NHTSA 자동차 리콜 위험 조기 감지

## 한 줄 설명

미국 NHTSA 소비자 불만 데이터를 지속 수집하고, 차종/부품 단위 이상 신호를 계산해 향후 리콜 가능성이 높아지는 대상을 조기 감지하는 MLOps 프로젝트.

## 1차 MVP에서 하지 않을 것

- 전 세계 리콜 통합
- FDA/CPSC/EU 데이터 통합
- 실시간 스트리밍
- 복잡한 딥러닝 모델
- 완벽한 리콜 원인 매칭

## 1차 MVP에서 할 것

1. NHTSA complaints/recalls 수집
2. make/model/model_year/component 단위 정규화
3. 주간 집계 feature 생성
4. 미래 90일 또는 180일 내 리콜 여부 라벨 생성
5. baseline risk score 또는 간단한 classifier 학습
6. backtesting
7. batch inference 결과 저장
8. API/대시보드/알림으로 확장 가능한 구조 설계

## 핵심 평가 관점

일반 accuracy보다 다음 지표가 더 중요하다.

- Precision@K
- Recall@K
- PR-AUC
- Brier score / calibration
- 실제 리콜 전에 얼마나 일찍 위험 점수가 상승했는지
- 데이터 누수 없이 as-of 시점 기준으로 예측했는지

## 포트폴리오 메시지

> Built an early-warning MLOps pipeline using NHTSA consumer complaints and recall records to detect emerging vehicle safety risks in the U.S. market.

