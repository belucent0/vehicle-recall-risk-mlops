CREATE SCHEMA IF NOT EXISTS recall_risk;

CREATE TABLE IF NOT EXISTS recall_risk.backfill_manifest (
    run_id TEXT,
    vehicle_index TEXT,
    make TEXT,
    model TEXT,
    model_year TEXT,
    endpoint TEXT,
    http_status TEXT,
    count TEXT,
    message TEXT,
    raw_path TEXT,
    url TEXT,
    fetched_at_utc TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.complaints (
    source TEXT,
    odi_number TEXT,
    make TEXT,
    model TEXT,
    model_year TEXT,
    manufacturer TEXT,
    components TEXT,
    component_primary TEXT,
    date_complaint_filed TEXT,
    date_of_incident TEXT,
    crash TEXT,
    fire TEXT,
    number_of_injuries TEXT,
    number_of_deaths TEXT,
    vin_prefix TEXT,
    summary TEXT,
    summary_length TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.recalls (
    source TEXT,
    nhtsa_campaign_number TEXT,
    make TEXT,
    model TEXT,
    model_year TEXT,
    manufacturer TEXT,
    component TEXT,
    component_primary TEXT,
    report_received_date TEXT,
    park_it TEXT,
    park_outside TEXT,
    over_the_air_update TEXT,
    summary TEXT,
    consequence TEXT,
    remedy TEXT,
    notes TEXT,
    summary_length TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.weekly_features (
    make TEXT,
    model TEXT,
    model_year TEXT,
    component_primary TEXT,
    week_start TEXT,
    complaint_count TEXT,
    crash_count TEXT,
    fire_count TEXT,
    injury_count TEXT,
    death_count TEXT,
    severe_complaint_count TEXT,
    rolling_4w_complaint_mean_prior TEXT,
    rolling_8w_complaint_mean_prior TEXT,
    rolling_8w_complaint_std_prior TEXT,
    complaint_spike_z TEXT,
    baseline_risk_score TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.training_dataset (
    make TEXT,
    model TEXT,
    model_year TEXT,
    component_primary TEXT,
    component_family TEXT,
    week_start TEXT,
    as_of_date TEXT,
    label_observation_end_date TEXT,
    complaint_count TEXT,
    crash_count TEXT,
    fire_count TEXT,
    injury_count TEXT,
    death_count TEXT,
    severe_complaint_count TEXT,
    rolling_4w_complaint_mean_prior TEXT,
    rolling_8w_complaint_mean_prior TEXT,
    rolling_8w_complaint_std_prior TEXT,
    complaint_spike_z TEXT,
    baseline_risk_score TEXT,
    label_available TEXT,
    next_90d_recall TEXT,
    recall_count_90d TEXT,
    days_to_first_recall TEXT,
    first_recall_date_90d TEXT,
    matched_campaign_numbers TEXT,
    matched_recall_components TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.training_dataset_labeled_only (
    LIKE recall_risk.training_dataset INCLUDING ALL
);

CREATE TABLE IF NOT EXISTS recall_risk.latest_risk_scores (
    rank TEXT,
    make TEXT,
    model TEXT,
    model_year TEXT,
    component_primary TEXT,
    week_start TEXT,
    complaint_count TEXT,
    crash_count TEXT,
    fire_count TEXT,
    injury_count TEXT,
    death_count TEXT,
    severe_complaint_count TEXT,
    rolling_8w_complaint_mean_prior TEXT,
    complaint_spike_z TEXT,
    baseline_risk_score TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.baseline_test_predictions (
    split TEXT,
    make TEXT,
    model TEXT,
    model_year TEXT,
    component_family TEXT,
    week_start TEXT,
    as_of_date TEXT,
    next_90d_recall TEXT,
    recall_count_90d TEXT,
    days_to_first_recall TEXT,
    matched_campaign_numbers TEXT,
    rule_score TEXT,
    logistic_score TEXT,
    complaint_count TEXT,
    severe_complaint_count TEXT,
    complaint_spike_z TEXT,
    baseline_risk_score TEXT
);

CREATE TABLE IF NOT EXISTS recall_risk.baseline_logistic_coefficients (
    feature TEXT,
    coefficient TEXT
);

CREATE INDEX IF NOT EXISTS idx_complaints_entity
    ON recall_risk.complaints (make, model, model_year, component_primary);

CREATE INDEX IF NOT EXISTS idx_recalls_entity
    ON recall_risk.recalls (make, model, model_year, component_primary);

CREATE INDEX IF NOT EXISTS idx_weekly_features_week
    ON recall_risk.weekly_features (week_start);

CREATE INDEX IF NOT EXISTS idx_training_dataset_label
    ON recall_risk.training_dataset (label_available, next_90d_recall);

CREATE INDEX IF NOT EXISTS idx_latest_risk_scores_rank
    ON recall_risk.latest_risk_scores (rank);

CREATE OR REPLACE VIEW recall_risk.v_latest_risk_scores AS
SELECT
    NULLIF(rank, '')::INTEGER AS rank,
    make,
    model,
    NULLIF(model_year, '')::INTEGER AS model_year,
    component_primary,
    NULLIF(week_start, '')::DATE AS week_start,
    NULLIF(complaint_count, '')::INTEGER AS complaint_count,
    NULLIF(severe_complaint_count, '')::INTEGER AS severe_complaint_count,
    NULLIF(complaint_spike_z, '')::DOUBLE PRECISION AS complaint_spike_z,
    NULLIF(baseline_risk_score, '')::DOUBLE PRECISION AS baseline_risk_score
FROM recall_risk.latest_risk_scores;

CREATE OR REPLACE VIEW recall_risk.v_training_dataset AS
SELECT
    make,
    model,
    NULLIF(model_year, '')::INTEGER AS model_year,
    component_family,
    NULLIF(week_start, '')::DATE AS week_start,
    NULLIF(as_of_date, '')::DATE AS as_of_date,
    NULLIF(complaint_count, '')::INTEGER AS complaint_count,
    NULLIF(baseline_risk_score, '')::DOUBLE PRECISION AS baseline_risk_score,
    NULLIF(label_available, '')::INTEGER AS label_available,
    NULLIF(next_90d_recall, '')::INTEGER AS next_90d_recall
FROM recall_risk.training_dataset;

