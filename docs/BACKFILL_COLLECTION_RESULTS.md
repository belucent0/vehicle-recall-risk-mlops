# MVP Backfill Collection Results

작성일: 2026-05-15 KST

## 할 작업

```text
M5. MVP 후보 vehicle backfill 수집 실행
```

## 왜 하는가

M4에서 `vehicle_models_mvp.csv`를 만들었다. 이제 이 후보 목록에 대해 NHTSA complaints/recalls raw JSON을 실제로 수집해야 한다.

## 무엇을 어떻게 했는가

다음 명령으로 MVP 후보에 대한 backfill 수집을 실행했다.

```bash
python pipelines/collect_backfill.py --vehicle-models data/interim/vehicle_models_mvp.csv --limit 0
```

`vehicle_models_mvp.csv`는 1012 rows였지만, collector가 `make/model/model_year` 기준으로 중복 제거한 뒤 실제 수집 대상은 917개 unique vehicle-year였다.

## 실행 중 발생한 이슈

raw JSON 수집은 끝까지 완료되었지만, 마지막 summary 작성 단계에서 상대경로 처리 오류가 발생했다.

원인:

```text
relative path로 입력한 vehicle_models_mvp.csv를 PROJECT_ROOT 기준 relative_to() 처리하면서 ValueError 발생
```

조치:

```text
1. collect_backfill.py의 경로 처리 버그 수정
2. 이미 저장된 raw JSON에서 manifest/summary/report 복구
3. 재수집은 하지 않음
```

복구 스크립트:

```text
pipelines/recover_backfill_manifest.py
```

복구 실행:

```bash
python pipelines/recover_backfill_manifest.py --run-id 20260515T114046Z
```

## 결과 파일

```text
data/raw/backfill/20260515T114046Z/
data/raw/backfill/20260515T114046Z/manifest.csv
data/raw/backfill/20260515T114046Z/summary.json
reports/backfill_collection_latest.md
docs/BACKFILL_COLLECTION_RESULTS.md
```

## 결과 요약

| Metric | Value |
|---|---:|
| Unique vehicle-year count | 917 |
| Request count | 1834 |
| Raw JSON files | 1834 |

## Endpoint summary

| Endpoint | Requests | Non-empty | Empty | Total records | Status counts |
|---|---:|---:|---:|---:|---|
| complaints | 917 | 605 | 312 | 103440 | `{'200': 668, '400': 249}` |
| recalls | 917 | 636 | 281 | 3018 | `{'200': 636, '400': 281}` |

## 알게 된 것

1. MVP 후보 목록으로 충분히 큰 raw 데이터가 수집되었다.
2. complaints 103,440건, recalls 3,018건을 확보했다.
3. empty/HTTP 400 결과는 여전히 많지만 manifest로 추적 가능하다.
4. F-150 등 일부 모델의 complaints empty 이슈는 계속 존재한다.
5. 이제 모델 성능을 논할 수 있을 만큼 데이터 범위가 커졌다.

## 결정

M5는 완료로 본다.

다음 단계에서는 raw JSON을 정규화해서 backfill용 complaints/recalls CSV를 만든다.

## 다음 작업

```text
M6. Backfill 정규화
```

목표:

```text
data/raw/backfill/20260515T114046Z/*.json
  -> data/interim/backfill/20260515T114046Z/complaints.csv
  -> data/interim/backfill/20260515T114046Z/recalls.csv
```

