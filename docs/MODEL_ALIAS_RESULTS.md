# Model Alias Check Results

작성일: 2026-05-15 KST

## 할 작업

```text
M2. 모델명 alias/정규화 확인
```

## 왜 하는가

이전 smoke test에서 다음 현상이 있었다.

```text
FORD F-150 2022
complaints = 0
recalls = 22
```

그런데 VPIC 모델 리스트에서는 `FORD F-150`이 정상적으로 존재했다.

따라서 backfill 전에 다음을 확인해야 했다.

```text
NHTSA complaints/recalls API에 어떤 model 문자열을 넣어야 데이터가 안정적으로 오는가?
```

## 무엇을 어떻게 했는가

alias 후보 config를 만들었다.

```text
configs/model_aliases.yaml
```

alias 후보별로 NHTSA complaints/recalls endpoint를 호출하는 스크립트를 만들었다.

```text
pipelines/check_model_aliases_sample.py
```

검사 대상:

```text
FORD F-150 2021/2022/2023
TESLA MODEL 3 2022
HYUNDAI SANTA FE 2022
```

TESLA와 HYUNDAI는 정상 동작 control case로 넣었다.

## 실행 명령

```bash
python pipelines/check_model_aliases_sample.py
```

## 결과 파일

```text
data/interim/model_alias_check.csv
data/interim/model_alias_check_summary.json
reports/model_alias_check_latest.md
docs/MODEL_ALIAS_RESULTS.md
```

## 주요 결과

| Make | Canonical | Year | Best complaints query | Complaints | Best recalls query | Recalls |
|---|---|---:|---|---:|---|---:|
| FORD | F-150 | 2021 | F-150 | 0 | F-150 | 27 |
| FORD | F-150 | 2022 | F-150 | 0 | F-150 | 22 |
| FORD | F-150 | 2023 | F-150 | 0 | F-150 | 11 |
| HYUNDAI | SANTA FE | 2022 | SANTA FE | 175 | SANTA FE | 5 |
| TESLA | MODEL 3 | 2022 | MODEL 3 | 741 | MODEL 3 | 17 |

## 세부 관찰

### FORD F-150

확인한 alias:

```text
F-150
F150
F 150
F-SERIES
F SERIES
F-150 REGULAR CAB
F-150 SUPERCREW
F-150 SUPER CAB
```

결과:

```text
recalls: F-150에서 정상 조회
complaints: 모든 alias에서 0건 또는 HTTP 400 empty result
```

따라서 현재 범위에서는 F-150 문제가 단순 alias 문제라고 보기 어렵다.

가능성:

```text
1. NHTSA complaintsByVehicle endpoint의 특정 모델 조회 제약
2. F-150 complaints 데이터가 다른 모델명/차체명으로 분산
3. API endpoint보다 bulk complaints 데이터가 더 적합할 가능성
```

### TESLA MODEL 3

```text
MODEL 3: 정상
MODEL3: 실패
MODEL-3: 실패
```

공백 포함 canonical model name이 중요하다.

### HYUNDAI SANTA FE

```text
SANTA FE: 정상
SANTAFE: 실패
SANTA-FE: 실패
```

역시 canonical model name이 중요하다.

## 알게 된 것

1. VPIC canonical model name을 기본 query model로 쓰는 것이 맞다.
2. 임의로 공백/하이픈을 제거하면 오히려 조회가 실패한다.
3. F-150은 alias 몇 개로 해결되지 않는다.
4. backfill collector는 empty/HTTP 400 결과를 실패로 죽이지 말고 기록해야 한다.
5. backfill 이후 Ford F-150 같은 모델은 별도 품질 리포트에서 확인해야 한다.

## 결정

MVP에서는 다음 전략을 사용한다.

```text
1. 기본적으로 VPIC model_name을 그대로 NHTSA query model로 사용한다.
2. alias는 아직 전역 적용하지 않는다.
3. endpoint별 count/status를 모두 기록한다.
4. complaints가 0이고 recalls가 많은 모델은 data quality issue로 표시한다.
```

## 다음 작업

```text
M3. Backfill collector 구현
```

목표:

```text
data/interim/vehicle_models.csv를 읽어서
다수 차량 모델의 complaints/recalls를 수집한다.
```

출력 예정:

```text
pipelines/collect_backfill.py
data/raw/backfill/<run_id>/*.json
reports/backfill_collection_latest.md
docs/BACKFILL_COLLECTION_RESULTS.md
```

