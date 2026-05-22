# Workflow

이 프로젝트는 한 번에 크게 만들지 않고, **작은 작업을 하나씩 완료한 뒤 체크하고 다음 단계로 넘어가는 방식**으로 진행한다.

## 진행 원칙

각 작업은 다음 구조로 관리한다.

```text
1. 할 작업
2. 왜 하는지
3. 무엇을 어떻게 했는지
4. 실행 명령
5. 결과 파일
6. 결과 해석
7. 이 결과로 무엇을 알게 되었는지
8. 다음에 무엇을 할지
```

## Gate 방식

각 단계는 아래 조건을 만족해야 다음 단계로 넘어간다.

```text
작업 구현
  -> 실행
  -> 결과 파일 생성
  -> 결과 해석
  -> 문서화
  -> 다음 작업 결정
```

## 지금은 무엇을 만들고 있는가

현재 목표는 완성형 MLOps 포트폴리오가 아니다.

현재 목표:

```text
NHTSA 자동차 리콜 위험 감지 MVP를 만들기 위한 데이터/모델 feasibility 확인
```

즉, 지금은 다음을 확인하는 단계다.

- NHTSA 데이터가 실제로 수집되는가
- complaints와 recalls를 정규화할 수 있는가
- 주간 feature를 만들 수 있는가
- 향후 90일 리콜 발생 라벨을 만들 수 있는가
- 최소한의 baseline 학습/평가 루프가 도는가

## MVP 이후로 미룰 것

아래는 지금 당장 하지 않는다.

- Airflow/Prefect
- MLflow
- FastAPI 본격 serving
- Grafana/Metabase dashboard
- Docker 배포
- GitHub Actions CI
- model registry
- 실시간 모니터링

이것들은 MVP 이후 MLOps 포트폴리오화 단계에서 진행한다.

