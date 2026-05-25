from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_SMOKE_DIR = PROJECT_ROOT / "data" / "raw" / "smoke_test"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEFAULT_RUN_ID = "ci_fixture"


VEHICLES = [
    {
        "make": "HYUNDAI",
        "model": "SANTA FE",
        "model_year": 2022,
        "manufacturer": "Hyundai Motor America",
        "component": "ENGINE",
        "complaint_dates": [
            "01/01/2024",
            "01/08/2024",
            "01/15/2024",
            "01/22/2024",
            "02/05/2024",
            "02/19/2024",
            "03/04/2024",
            "03/18/2024",
            "04/01/2024",
            "05/06/2024",
            "06/03/2024",
            "07/01/2024",
            "08/05/2024",
            "09/02/2024",
            "10/07/2024",
        ],
        "recalls": [
            ("24V001000", "04/15/2024", "ENGINE"),
            ("24V901000", "12/31/2024", "ENGINE"),
        ],
    },
    {
        "make": "KIA",
        "model": "TELLURIDE",
        "model_year": 2022,
        "manufacturer": "Kia America, Inc.",
        "component": "ELECTRICAL SYSTEM",
        "complaint_dates": [
            "02/05/2024",
            "02/12/2024",
            "02/19/2024",
            "03/04/2024",
            "03/18/2024",
            "04/01/2024",
            "04/15/2024",
            "05/06/2024",
            "05/20/2024",
            "06/03/2024",
            "06/17/2024",
            "07/01/2024",
            "08/05/2024",
            "09/09/2024",
            "10/07/2024",
        ],
        "recalls": [
            ("24V002000", "07/15/2024", "ELECTRICAL SYSTEM"),
            ("24V902000", "12/31/2024", "ELECTRICAL SYSTEM"),
        ],
    },
]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)


def complaint_record(vehicle: dict[str, Any], date_text: str, index: int) -> dict[str, Any]:
    severe = index % 7 == 0
    return {
        "odiNumber": f"{vehicle['model_year']}{index:06d}",
        "manufacturer": vehicle["manufacturer"],
        "components": vehicle["component"],
        "dateComplaintFiled": date_text,
        "dateOfIncident": date_text,
        "crash": "False",
        "fire": "True" if severe else "False",
        "numberOfInjuries": 1 if severe else 0,
        "numberOfDeaths": 0,
        "vin": f"FIXTURE{index:04d}VIN",
        "summary": (
            f"Deterministic fixture complaint for {vehicle['make']} {vehicle['model']} "
            f"{vehicle['component']} on {date_text}."
        ),
        "products": [
            {
                "type": "Vehicle",
                "productMake": vehicle["make"],
                "productModel": vehicle["model"],
                "productYear": vehicle["model_year"],
                "manufacturer": vehicle["manufacturer"],
            }
        ],
    }


def recall_record(
    vehicle: dict[str, Any],
    campaign_number: str,
    report_received_date: str,
    component: str,
) -> dict[str, Any]:
    return {
        "NHTSACampaignNumber": campaign_number,
        "Make": vehicle["make"],
        "Model": vehicle["model"],
        "ModelYear": vehicle["model_year"],
        "Manufacturer": vehicle["manufacturer"],
        "Component": component,
        "ReportReceivedDate": report_received_date,
        "parkIt": "False",
        "parkOutSide": "False",
        "overTheAirUpdate": "False",
        "Summary": (
            f"Deterministic fixture recall for {vehicle['make']} {vehicle['model']} "
            f"{component}."
        ),
        "Consequence": "Fixture consequence.",
        "Remedy": "Fixture remedy.",
        "Notes": "Synthetic deterministic fixture for CI and clean-clone smoke E2E.",
    }


def payload(results: list[dict[str, Any]], endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "Count": len(results),
        "Message": "Synthetic fixture payload for offline smoke E2E.",
        "results": results,
        "_request": {
            "url": f"fixture://nhtsa{endpoint}",
            "endpoint": endpoint,
            "params": params,
            "fetched_at_utc": datetime.now(UTC).isoformat(),
        },
        "_response": {"http_status": 200, "treated_as_payload": False},
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown_report(summary: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# Smoke Fixture Report",
        "",
        f"- Run ID: `{summary['run_id']}`",
        f"- Generated at UTC: `{summary['generated_at_utc']}`",
        f"- Output dir: `{summary['output_dir']}`",
        "",
        "## Vehicles",
        "",
        "| Make | Model | Year | Component | Complaints | Recalls |",
        "|---|---|---:|---|---:|---:|",
    ]
    for item in summary["vehicles"]:
        lines.append(
            f"| {item['make']} | {item['model']} | {item['model_year']} "
            f"| {item['component']} | {item['complaints_count']} | {item['recalls_count']} |"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic offline raw JSON fixture for sample smoke E2E."
    )
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = RAW_SMOKE_DIR / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "run_id": args.run_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "output_dir": display_path(output_dir),
        "vehicles": [],
    }

    complaint_index = 1
    for vehicle in VEHICLES:
        params = {
            "make": vehicle["make"],
            "model": vehicle["model"],
            "modelYear": vehicle["model_year"],
        }
        vehicle_slug = (
            f"{slugify(vehicle['make'])}_{slugify(vehicle['model'])}_{vehicle['model_year']}"
        )
        complaints = [
            complaint_record(vehicle, date_text, complaint_index + idx)
            for idx, date_text in enumerate(vehicle["complaint_dates"])
        ]
        complaint_index += len(complaints)
        recalls = [
            recall_record(vehicle, campaign_number, report_date, component)
            for campaign_number, report_date, component in vehicle["recalls"]
        ]

        complaints_path = output_dir / f"{vehicle_slug}_complaints.json"
        recalls_path = output_dir / f"{vehicle_slug}_recalls.json"
        write_json(complaints_path, payload(complaints, "/complaints/complaintsByVehicle", params))
        write_json(recalls_path, payload(recalls, "/recalls/recallsByVehicle", params))

        summary["vehicles"].append(
            {
                "make": vehicle["make"],
                "model": vehicle["model"],
                "model_year": vehicle["model_year"],
                "component": vehicle["component"],
                "complaints_count": len(complaints),
                "recalls_count": len(recalls),
                "complaints_path": display_path(complaints_path),
                "recalls_path": display_path(recalls_path),
            }
        )

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    report_path = REPORTS_DIR / "smoke_fixture_latest.md"
    write_markdown_report(summary, report_path)

    print(f"Fixture run ID: {args.run_id}")
    print(f"Output dir:     {display_path(output_dir)}")
    print(f"Vehicles:       {len(summary['vehicles'])}")
    print(f"Wrote:          {display_path(summary_path)}")
    print(f"Wrote:          {display_path(report_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

