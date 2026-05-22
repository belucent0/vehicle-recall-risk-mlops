# Roadmap

## 프로젝트명

**NHTSA Recall Risk MLOps**

## 목표

미국 NHTSA의 소비자 불만 및 리콜 데이터를 이용해 차량/부품 단위의 리콜 위험 신호를 조기 감지하는 MLOps 파이프라인을 만든다.

## 기본 전략

현재 기준은 **2026년 5월**이다. 따라서 프로젝트는 최신 운영성을 먼저 보여주기 위해 다음 순서로 진행한다.

1. **2025-01-01 ~ 2026-05 현재 데이터 우선 수집**
2. 샘플 제조사/차종 대상으로 end-to-end 파이프라인 완성
3. 이후 2015년까지 과거 데이터 backfill
4. 90일 horizon 기준으로 모델 학습/검증

## 1차 MVP 범위

### 제조사

- HYUNDAI
- KIA
- TOYOTA
- FORD
- TESLA

### 연식

- 2020 ~ 2026

### 예측 단위

```text
make / model / model_year / component / week
```

### 예측 목표

```text
향후 90일 내 관련 리콜 발생 가능성
```

처음부터 복잡한 ML 모델을 만들지 않고, complaint spike 기반 baseline risk score부터 만든다.

## 2주 실행 계획

### Day 1-2: 데이터 수집 smoke test

- NHTSA recalls API 호출
- NHTSA complaints API 호출
- HYUNDAI/KIA/TESLA 일부 모델 기준 raw JSON 저장
- API 응답 스키마 파악

실행:

```bash
python pipelines/collect_sample.py
```

### Day 3-4: 정규화

- complaints 테이블 생성
- recalls 테이블 생성
- make/model/model_year/component 필드 정규화
- 날짜 필드 파싱
- VPIC model list를 이용한 모델명 정규화

실행:

```bash
python pipelines/normalize_sample.py
```

### Day 5-6: feature 생성

- 주간 complaint count
- 최근 4주/8주 rolling count
- complaint spike z-score
- crash/fire/injury/death 키워드 feature

실행:

```bash
python pipelines/build_features_sample.py
```

### Day 7-8: label 생성

- 각 entity-week 기준 향후 90일 내 리콜 발생 여부 생성
- 데이터 누수 방지를 위해 as-of 기준 유지
- 너무 최근이라 90일 후 리콜 여부를 아직 모르는 row는 `label_available=0` 처리

실행:

```bash
python pipelines/build_training_dataset_sample.py
```

### Day 9-10: baseline 모델

- rule-based risk score
- logistic regression 또는 tree model 1개
- precision@k, PR-AUC, calibration 평가

실행:

```bash
python pipelines/train_baseline_sample.py
```

### Day 11-12: 파이프라인화

- `pipelines/run_daily.py` 구현
- raw/interim/processed 저장 분리
- DuckDB 또는 Postgres 저장

### Day 13-14: 포트폴리오 출력물

- FastAPI health/risk endpoint 연결
- 대시보드용 테이블 생성
- backtest report 작성
- README에 아키텍처와 결과 정리

## 성공 기준

첫 사이클 성공 기준은 모델 성능이 높게 나오는 것이 아니다.

다음이 되면 성공이다.

- 최신 NHTSA 데이터를 실제로 수집한다.
- raw → normalized → features → scores 흐름이 돈다.
- 특정 차량/부품 조합의 risk score가 산출된다.
- backtest 결과를 재현할 수 있다.
- API나 dashboard-ready table로 결과를 볼 수 있다.

## 나중에 확장할 것

- 전체 제조사/연식으로 backfill
- NHTSA investigations 데이터 추가
- manufacturer communications 데이터 추가
- CPSC/FDA 리콜 데이터 확장
- MLflow 실험 관리
- Prefect/Airflow 스케줄링
- Slack/Discord 알림
