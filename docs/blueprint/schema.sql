-- SQLite 3 audit/forecast contract prototype, version 1.0.
-- Large source/play/frame/sample datasets live in immutable artifacts (e.g. Parquet).
-- Production DuckDB schemas need an explicit migration; this is not that migration.
PRAGMA foreign_keys = ON;

CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    season INTEGER NOT NULL,
    home_team_id TEXT NOT NULL REFERENCES teams(team_id),
    away_team_id TEXT NOT NULL REFERENCES teams(team_id),
    CHECK (home_team_id <> away_team_id)
);

CREATE TABLE raw_requests (
    request_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    parameters_json TEXT NOT NULL CHECK (json_valid(parameters_json)),
    retrieved_at TEXT NOT NULL CHECK (julianday(retrieved_at) IS NOT NULL),
    http_status INTEGER NOT NULL,
    response_count INTEGER,
    suspected_truncation INTEGER NOT NULL DEFAULT 0 CHECK (suspected_truncation IN (0,1)),
    payload_uri TEXT NOT NULL,
    payload_hash TEXT NOT NULL
);

-- A response can hold facts with different publication evidence. Version at fact level.
CREATE TABLE source_records (
    record_version_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES raw_requests(request_id),
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    event_time TEXT CHECK (event_time IS NULL OR julianday(event_time) IS NOT NULL),
    available_at TEXT CHECK (available_at IS NULL OR julianday(available_at) IS NOT NULL),
    ingested_at TEXT NOT NULL CHECK (julianday(ingested_at) IS NOT NULL),
    availability_evidence TEXT NOT NULL CHECK (
        availability_evidence IN ('prospective_observation','archived_publication','reconstructed','unknown')
    ),
    source_version TEXT NOT NULL,
    normalized_payload_json TEXT NOT NULL CHECK (json_valid(normalized_payload_json)),
    payload_hash TEXT NOT NULL,
    CHECK (availability_evidence NOT IN ('prospective_observation','archived_publication') OR available_at IS NOT NULL),
    CHECK (available_at IS NULL OR julianday(available_at) <= julianday(ingested_at)),
    UNIQUE(entity_type, entity_key, source_version, payload_hash)
);
CREATE INDEX source_records_temporal ON source_records(entity_type, entity_key, available_at);
CREATE TRIGGER source_records_no_update BEFORE UPDATE ON source_records
BEGIN SELECT RAISE(ABORT, 'source versions are immutable; insert a correction'); END;
CREATE TRIGGER source_records_no_delete BEFORE DELETE ON source_records
BEGIN SELECT RAISE(ABORT, 'source versions are immutable'); END;

CREATE TABLE player_identity_links (
    link_id TEXT PRIMARY KEY,
    source_player_key TEXT NOT NULL,
    player_id TEXT REFERENCES players(player_id),
    status TEXT NOT NULL CHECK (status IN ('verified','proposed','ambiguous','unresolved')),
    evidence_json TEXT NOT NULL CHECK (json_valid(evidence_json)),
    record_version_id TEXT NOT NULL REFERENCES source_records(record_version_id),
    CHECK (status <> 'verified' OR player_id IS NOT NULL)
);
CREATE TABLE roster_memberships (
    membership_version_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL REFERENCES players(player_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    valid_from TEXT CHECK (valid_from IS NULL OR julianday(valid_from) IS NOT NULL),
    valid_to TEXT CHECK (valid_to IS NULL OR julianday(valid_to) IS NOT NULL),
    status TEXT NOT NULL,
    record_version_id TEXT NOT NULL REFERENCES source_records(record_version_id),
    CHECK (valid_from IS NULL OR valid_to IS NULL OR julianday(valid_to) > julianday(valid_from))
);
CREATE TABLE transfer_events (
    transfer_version_id TEXT PRIMARY KEY,
    player_id TEXT REFERENCES players(player_id),
    origin_team_id TEXT REFERENCES teams(team_id),
    destination_team_id TEXT REFERENCES teams(team_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('entry','commitment','withdrawal','enrollment','unknown')),
    identity_link_id TEXT REFERENCES player_identity_links(link_id),
    record_version_id TEXT NOT NULL REFERENCES source_records(record_version_id)
);

CREATE TABLE feature_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    information_cutoff TEXT NOT NULL CHECK (julianday(information_cutoff) IS NOT NULL),
    replay_mode TEXT NOT NULL CHECK (replay_mode IN ('strict','reconstructed')),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sealed')),
    manifest_uri TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    coverage_json TEXT NOT NULL CHECK (json_valid(coverage_json))
);
CREATE TABLE snapshot_members (
    snapshot_id TEXT NOT NULL REFERENCES feature_snapshots(snapshot_id),
    record_version_id TEXT NOT NULL REFERENCES source_records(record_version_id),
    PRIMARY KEY(snapshot_id, record_version_id)
);
CREATE TRIGGER snapshot_members_check BEFORE INSERT ON snapshot_members
BEGIN
    SELECT CASE WHEN (SELECT status FROM feature_snapshots WHERE snapshot_id=NEW.snapshot_id) <> 'draft'
        THEN RAISE(ABORT, 'sealed snapshot cannot acquire new facts') END;
    SELECT CASE WHEN (SELECT replay_mode FROM feature_snapshots WHERE snapshot_id=NEW.snapshot_id)='strict'
        AND EXISTS (
            SELECT 1 FROM source_records r JOIN feature_snapshots s ON s.snapshot_id=NEW.snapshot_id
            WHERE r.record_version_id=NEW.record_version_id
            AND (r.available_at IS NULL
                OR r.availability_evidence NOT IN ('prospective_observation','archived_publication')
                OR julianday(r.available_at)>julianday(s.information_cutoff))
        ) THEN RAISE(ABORT, 'strict snapshot rejects future or unevidenced availability') END;
END;
CREATE TRIGGER snapshot_members_no_update BEFORE UPDATE ON snapshot_members
BEGIN SELECT RAISE(ABORT, 'snapshot members cannot be updated'); END;
CREATE TRIGGER snapshot_members_no_delete BEFORE DELETE ON snapshot_members
WHEN (SELECT status FROM feature_snapshots WHERE snapshot_id=OLD.snapshot_id)='sealed'
BEGIN SELECT RAISE(ABORT, 'sealed snapshot is immutable'); END;
CREATE TRIGGER snapshots_sealed_no_update BEFORE UPDATE ON feature_snapshots
WHEN OLD.status='sealed'
BEGIN SELECT RAISE(ABORT, 'sealed snapshot is immutable'); END;
CREATE TRIGGER snapshots_sealed_no_delete BEFORE DELETE ON feature_snapshots
WHEN OLD.status='sealed'
BEGIN SELECT RAISE(ABORT, 'sealed snapshot is immutable'); END;

CREATE TABLE model_runs (
    run_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES feature_snapshots(snapshot_id),
    stage TEXT NOT NULL,
    model_version TEXT NOT NULL,
    training_end TEXT NOT NULL CHECK (julianday(training_end) IS NOT NULL),
    seed INTEGER NOT NULL,
    dependency_lock_hash TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    artifact_uri TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed','failed')),
    diagnostics_json TEXT NOT NULL CHECK (json_valid(diagnostics_json))
);
CREATE TRIGGER model_runs_check BEFORE INSERT ON model_runs
BEGIN
    SELECT CASE WHEN (SELECT status FROM feature_snapshots WHERE snapshot_id=NEW.snapshot_id)<>'sealed'
        THEN RAISE(ABORT, 'model run requires a sealed snapshot') END;
    SELECT CASE WHEN julianday(NEW.training_end)>
        (SELECT julianday(information_cutoff) FROM feature_snapshots WHERE snapshot_id=NEW.snapshot_id)
        THEN RAISE(ABORT, 'model training end exceeds forecast cutoff') END;
END;
CREATE TRIGGER model_runs_no_update BEFORE UPDATE ON model_runs
BEGIN SELECT RAISE(ABORT, 'finalized model runs are immutable'); END;
CREATE TRIGGER model_runs_no_delete BEFORE DELETE ON model_runs
BEGIN SELECT RAISE(ABORT, 'finalized model runs are immutable'); END;

CREATE TABLE forecast_summaries (
    forecast_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES model_runs(run_id),
    game_id TEXT NOT NULL REFERENCES games(game_id),
    horizon_minutes INTEGER NOT NULL CHECK (horizon_minutes>=0),
    actual_lead_minutes REAL NOT NULL,
    schedule_version TEXT NOT NULL,
    generated_at TEXT NOT NULL CHECK (julianday(generated_at) IS NOT NULL),
    evaluation_class TEXT NOT NULL CHECK (evaluation_class IN ('prospective','archived_replay','reconstructed')),
    product TEXT NOT NULL CHECK (product IN ('football_only','market_informed')),
    home_win_probability REAL NOT NULL CHECK (home_win_probability BETWEEN 0 AND 1),
    away_win_probability REAL NOT NULL CHECK (away_win_probability BETWEEN 0 AND 1),
    expected_home_score REAL NOT NULL CHECK (expected_home_score>=0),
    expected_away_score REAL NOT NULL CHECK (expected_away_score>=0),
    margin_q10 REAL NOT NULL,
    margin_q50 REAL NOT NULL,
    margin_q90 REAL NOT NULL,
    total_q10 REAL NOT NULL CHECK (total_q10>=0),
    total_q50 REAL NOT NULL,
    total_q90 REAL NOT NULL,
    samples_uri TEXT NOT NULL,
    samples_hash TEXT NOT NULL,
    sample_count INTEGER NOT NULL CHECK (sample_count>0),
    monte_carlo_se REAL CHECK (monte_carlo_se IS NULL OR monte_carlo_se>=0),
    quality_flags_json TEXT NOT NULL CHECK (json_valid(quality_flags_json)),
    CHECK (abs(home_win_probability+away_win_probability-1.0)<0.000000001),
    CHECK (margin_q10<=margin_q50 AND margin_q50<=margin_q90),
    CHECK (total_q10<=total_q50 AND total_q50<=total_q90),
    CHECK (evaluation_class<>'prospective' OR actual_lead_minutes>0),
    UNIQUE(run_id,game_id,horizon_minutes,product)
);
CREATE TRIGGER forecast_check BEFORE INSERT ON forecast_summaries
BEGIN
    SELECT CASE WHEN (SELECT status FROM model_runs WHERE run_id=NEW.run_id)<>'passed'
        THEN RAISE(ABORT, 'forecast requires a passed model run') END;
    SELECT CASE WHEN julianday(NEW.generated_at)<(
        SELECT julianday(s.information_cutoff) FROM model_runs r JOIN feature_snapshots s USING(snapshot_id)
        WHERE r.run_id=NEW.run_id)
        THEN RAISE(ABORT, 'forecast generation predates its information cutoff') END;
    SELECT CASE WHEN NEW.evaluation_class IN ('prospective','archived_replay') AND (
        SELECT s.replay_mode FROM model_runs r JOIN feature_snapshots s USING(snapshot_id)
        WHERE r.run_id=NEW.run_id)<>'strict'
        THEN RAISE(ABORT, 'prospective or archived replay requires strict snapshot') END;
END;
CREATE TRIGGER forecasts_no_update BEFORE UPDATE ON forecast_summaries
BEGIN SELECT RAISE(ABORT, 'forecasts are immutable; insert a revision'); END;
CREATE TRIGGER forecasts_no_delete BEFORE DELETE ON forecast_summaries
BEGIN SELECT RAISE(ABORT, 'forecasts are immutable'); END;

CREATE TABLE decision_records (
    decision_id TEXT PRIMARY KEY,
    forecast_id TEXT NOT NULL REFERENCES forecast_summaries(forecast_id),
    policy_version TEXT NOT NULL,
    decision_type TEXT NOT NULL CHECK (decision_type IN ('winner','spread','total')),
    forced_choice TEXT,
    recommendation TEXT NOT NULL,
    market_record_version_id TEXT REFERENCES source_records(record_version_id),
    expected_net_return_per_unit REAL,
    reason_codes_json TEXT NOT NULL CHECK (json_valid(reason_codes_json)),
    input_hash TEXT NOT NULL,
    decision_hash TEXT NOT NULL,
    UNIQUE(forecast_id,policy_version,decision_type)
);
CREATE TRIGGER decisions_no_update BEFORE UPDATE ON decision_records
BEGIN SELECT RAISE(ABORT, 'decisions are immutable'); END;
CREATE TRIGGER decisions_no_delete BEFORE DELETE ON decision_records
BEGIN SELECT RAISE(ABORT, 'decisions are immutable'); END;

CREATE TABLE outcome_versions (
    outcome_version_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(game_id),
    home_score INTEGER NOT NULL CHECK (home_score>=0),
    away_score INTEGER NOT NULL CHECK (away_score>=0),
    status TEXT NOT NULL CHECK (status IN ('final','corrected_final')),
    observed_at TEXT NOT NULL CHECK (julianday(observed_at) IS NOT NULL),
    record_version_id TEXT NOT NULL REFERENCES source_records(record_version_id)
);
CREATE TABLE evaluation_results (
    evaluation_id TEXT PRIMARY KEY,
    forecast_id TEXT NOT NULL REFERENCES forecast_summaries(forecast_id),
    outcome_version_id TEXT NOT NULL REFERENCES outcome_versions(outcome_version_id),
    protocol_version TEXT NOT NULL,
    metrics_json TEXT NOT NULL CHECK (json_valid(metrics_json)),
    UNIQUE(forecast_id,outcome_version_id,protocol_version)
);
CREATE TRIGGER evaluation_game_check BEFORE INSERT ON evaluation_results
BEGIN
    SELECT CASE WHEN (SELECT game_id FROM forecast_summaries WHERE forecast_id=NEW.forecast_id)<>
        (SELECT game_id FROM outcome_versions WHERE outcome_version_id=NEW.outcome_version_id)
        THEN RAISE(ABORT, 'evaluation outcome belongs to another game') END;
END;
CREATE TRIGGER outcomes_no_update BEFORE UPDATE ON outcome_versions
BEGIN SELECT RAISE(ABORT, 'outcome corrections require a new version'); END;
CREATE TRIGGER evaluations_no_update BEFORE UPDATE ON evaluation_results
BEGIN SELECT RAISE(ABORT, 'evaluation revisions require a new version'); END;

CREATE VIEW v_game_forecast AS
SELECT f.*, g.home_team_id, g.away_team_id, g.season,
       r.model_version, r.snapshot_id, s.information_cutoff, s.replay_mode,
       f.expected_home_score-f.expected_away_score AS expected_margin,
       f.expected_home_score+f.expected_away_score AS expected_total,
       CASE WHEN f.home_win_probability>0.5 THEN g.home_team_id
            WHEN f.home_win_probability<0.5 THEN g.away_team_id
            WHEN g.home_team_id COLLATE BINARY < g.away_team_id COLLATE BINARY THEN g.home_team_id
            ELSE g.away_team_id END AS winner_v1_forced_team_id
FROM forecast_summaries f
JOIN games g USING(game_id)
JOIN model_runs r USING(run_id)
JOIN feature_snapshots s USING(snapshot_id);

CREATE TRIGGER winner_decision_check BEFORE INSERT ON decision_records
WHEN NEW.decision_type='winner' AND NEW.policy_version='winner_v1'
BEGIN
    SELECT CASE WHEN NEW.forced_choice IS NULL OR NEW.forced_choice<>(
        SELECT winner_v1_forced_team_id FROM v_game_forecast WHERE forecast_id=NEW.forecast_id)
        THEN RAISE(ABORT, 'winner choice contradicts unrounded forecast policy') END;
END;

CREATE VIEW v_game_decision AS
SELECT d.*, f.game_id, f.information_cutoff, f.model_version,
       f.home_win_probability, f.away_win_probability,
       f.winner_v1_forced_team_id, f.quality_flags_json
FROM decision_records d JOIN v_game_forecast f USING(forecast_id);

-- No implicit latest join: select an explicit snapshot/forecast ID in historical screens.
CREATE VIEW v_data_quality AS
SELECT snapshot_id, information_cutoff, replay_mode, status, coverage_json
FROM feature_snapshots;

CREATE VIEW v_model_performance AS
SELECT e.*, f.game_id, f.product, f.horizon_minutes, f.evaluation_class,
       r.model_version, s.information_cutoff, o.home_score, o.away_score
FROM evaluation_results e JOIN forecast_summaries f USING(forecast_id)
JOIN model_runs r USING(run_id) JOIN feature_snapshots s USING(snapshot_id)
JOIN outcome_versions o USING(outcome_version_id);

-- Application/warehouse responsibilities beyond this prototype:
-- verify manifest hashes/membership, sample-score support, Monte Carlo dependence,
-- summary-to-sample reconciliation, game identity in outcome/forecast joins,
-- verified identity status at snapshot cutoff, market availability and odds,
-- actual lead time from schedule version, and full normalized domain schemas.
