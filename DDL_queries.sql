CREATE DATABASE IF NOT EXISTS mcsr_live_match_insights;
USE mcsr_live_match_insights;

DROP TABLE IF EXISTS timelines;
DROP TABLE IF EXISTS match_players;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS players;

CREATE TABLE players (
    uuid VARCHAR(32) PRIMARY KEY,

    nickname VARCHAR(50) NOT NULL,
    country VARCHAR(10),
    role_type INT,

    current_elo INT,
    current_rank INT,

    first_online BIGINT,
    last_online BIGINT,
    last_ranked BIGINT,

    total_matches INT DEFAULT 0,
    total_wins INT DEFAULT 0,
    total_losses INT DEFAULT 0,
    total_completions INT DEFAULT 0,
    total_forfeits INT DEFAULT 0,

    best_time_ms BIGINT,

    twitch_name VARCHAR(100),
    youtube_name VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE matches (
    match_id BIGINT PRIMARY KEY,

    match_type INT,
    season INT,

    category VARCHAR(20),
    game_mode VARCHAR(20),

    date_played BIGINT,

    winner_uuid VARCHAR(32),

    result_time_ms BIGINT,

    forfeited BOOLEAN DEFAULT FALSE,
    decayed BOOLEAN DEFAULT FALSE,

    seed_id VARCHAR(50),

    seed_type VARCHAR(50),
    bastion_type VARCHAR(50),

    overworld_structure VARCHAR(50),
    nether_structure VARCHAR(50),

    replay_exists BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (winner_uuid)
        REFERENCES players(uuid)
);

CREATE TABLE match_players (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    match_id BIGINT NOT NULL,
    player_uuid VARCHAR(32) NOT NULL,

    elo_before INT,
    rank_before INT,

    elo_change INT,
    elo_after INT,

    country VARCHAR(10),

    FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    FOREIGN KEY (player_uuid)
        REFERENCES players(uuid)
        ON DELETE CASCADE,

    UNIQUE KEY uq_match_player (
        match_id,
        player_uuid
    )
);

CREATE TABLE player_blind_stats(
    username VARCHAR(50) PRIMARY KEY,
    meanBlind float,
    sdBlind float,
    q1 float,
    q2 float,
    q3 float
);

CREATE TABLE timelines (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    match_id BIGINT NOT NULL,
    player_uuid VARCHAR(32) NOT NULL,

    event_time_ms BIGINT NOT NULL,

    event_type VARCHAR(100) NOT NULL,

    FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON DELETE CASCADE,

    FOREIGN KEY (player_uuid)
        REFERENCES players(uuid)
        ON DELETE CASCADE
);

CREATE INDEX idx_player_nickname
ON players(nickname);

CREATE INDEX idx_match_date
ON matches(date_played);

CREATE INDEX idx_match_season
ON matches(season);

CREATE INDEX idx_match_players_player
ON match_players(player_uuid);

CREATE INDEX idx_match_players_match
ON match_players(match_id);

CREATE INDEX idx_timelines_match
ON timelines(match_id);

CREATE INDEX idx_timelines_player
ON timelines(player_uuid);

CREATE INDEX idx_timelines_event
ON timelines(event_type);

CREATE INDEX idx_timelines_player_event
ON timelines(player_uuid, event_type);