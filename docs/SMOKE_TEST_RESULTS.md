# Smoke Test Results

## Run: 2026-05-14 UTC

실행 명령:

```bash
python pipelines/collect_sample.py
```

생성된 로컬 산출물:

```text
data/raw/smoke_test/20260514T154719Z/
reports/smoke_test_latest.md
```

## Counts

| Make | Model | Year | Complaints | Recalls | Note |
|---|---:|---:|---:|---:|---|
| HYUNDAI | SANTA FE | 2022 | 175 | 5 | OK |
| KIA | TELLURIDE | 2022 | 294 | 6 | OK |
| TESLA | MODEL 3 | 2022 | 741 | 17 | OK |
| FORD | F-150 | 2022 | 0 | 22 | complaints endpoint returned HTTP 400 with empty JSON result |
| TOYOTA | RAV4 | 2022 | 124 | 1 | OK |

## Observed complaint fields

```text
components
crash
dateComplaintFiled
dateOfIncident
fire
manufacturer
numberOfDeaths
numberOfInjuries
odiNumber
products
summary
vin
```

## Observed recall fields

```text
Component
Consequence
Make
Manufacturer
Model
ModelYear
NHTSACampaignNumber
Notes
Remedy
ReportReceivedDate
Summary
overTheAirUpdate
parkIt
parkOutSide
```

## Immediate findings

1. NHTSA API 호출은 성공한다.
2. complaints와 recalls는 필드명 casing이 다르다.
   - complaints: lower/camel style, e.g. `dateComplaintFiled`
   - recalls: PascalCase style, e.g. `ReportReceivedDate`
3. 핵심 날짜 필드는 다음으로 보인다.
   - complaints: `dateComplaintFiled`, `dateOfIncident`
   - recalls: `ReportReceivedDate`
4. 핵심 component 필드는 다음으로 보인다.
   - complaints: `components`
   - recalls: `Component`
5. FORD F-150처럼 모델명 표기 이슈 또는 endpoint quirks가 있을 수 있다.
   - 다음 단계에서 VPIC model list를 이용해 모델명을 정규화해야 한다.

