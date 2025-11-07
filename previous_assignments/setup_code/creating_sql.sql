CREATE TABLE "event_info" (
  "url" TEXT,
  "title" TEXT,
  "subtitle" TEXT,
  "dates" TEXT,
  "prize_pool" TEXT,
  "location" TEXT
);

CREATE TABLE "matches" (
  "match_id" VARCHAR(255) PRIMARY KEY,
  "date" DATE,
  "time" VARCHAR(50),
  "team1" VARCHAR(255),
  "score1" INTEGER,
  "team2" VARCHAR(255),
  "score2" INTEGER,
  "score" VARCHAR(50),
  "winner" VARCHAR(255),
  "status" VARCHAR(50),
  "week" VARCHAR(50),
  "stage" VARCHAR(100)
);

CREATE TABLE "player_stats" (
  "player_id" VARCHAR(255) PRIMARY KEY,
  "player" VARCHAR(255),
  "player_name" VARCHAR(255),
  "team" VARCHAR(255),
  "agents_count" INTEGER,
  "agents" TEXT,
  "rounds" INTEGER,
  "rating" DECIMAL(3,2),
  "acs" INTEGER,
  "kd_ratio" DECIMAL(3,2),
  "kast" INTEGER,
  "adr" INTEGER,
  "kpr" DECIMAL(3,2),
  "apr" DECIMAL(3,2),
  "fkpr" DECIMAL(3,2),
  "fdpr" DECIMAL(3,2),
  "hs_percent" INTEGER,
  "cl_percent" INTEGER,
  "clutches" VARCHAR(50),
  "k_max" INTEGER,
  "kills" INTEGER,
  "deaths" INTEGER,
  "assists" INTEGER,
  "first_kills" INTEGER,
  "first_deaths" INTEGER
);

CREATE TABLE "maps_stats" (
  "map_name" VARCHAR(100) PRIMARY KEY,
  "times_played" INTEGER,
  "attack_win_percent" INTEGER,
  "defense_win_percent" INTEGER
);

CREATE TABLE "agents_stats" (
  "agent_name" VARCHAR(100) PRIMARY KEY,
  "total_utilization" DECIMAL(4,1),
  "map_utilizations" TEXT
);

CREATE TABLE "economy_data" (
  "match_id" VARCHAR(255),
  "map" VARCHAR(100),
  "Team" VARCHAR(255),
  "Pistol Won" INTEGER,
  "Eco (won)" VARCHAR(50),
  "Semi-eco (won)" VARCHAR(50),
  "Semi-buy (won)" VARCHAR(50),
  "Full buy(won)" VARCHAR(50),
  PRIMARY KEY ("match_id", "map", "Team")
);

CREATE TABLE "performance_data" (
  "Match ID" VARCHAR(255),
  "Map" VARCHAR(100),
  "Player" VARCHAR(255),
  "Team" VARCHAR(255),
  "Agent" VARCHAR(100),
  "2K" INTEGER,
  "3K" INTEGER,
  "4K" INTEGER,
  "5K" INTEGER,
  "1v1" INTEGER,
  "1v2" INTEGER,
  "1v3" INTEGER,
  "1v4" INTEGER,
  "1v5" INTEGER,
  "ECON" INTEGER,
  "PL" INTEGER,
  "DE" INTEGER,
  PRIMARY KEY ("Match ID", "Map", "Player", "Team")
);

CREATE TABLE "detailed_matches_player_stats" (
  "match_id" VARCHAR(255),
  "event_name" VARCHAR(255),
  "event_stage" VARCHAR(100),
  "match_date" DATE,
  "team1" VARCHAR(255),
  "team2" VARCHAR(255),
  "score_overall" VARCHAR(50),
  "player_name" VARCHAR(255),
  "player_id" VARCHAR(255),
  "player_team" VARCHAR(255),
  "stat_type" VARCHAR(50),
  "agent" VARCHAR(100),
  "rating" DECIMAL(3,2),
  "acs" INTEGER,
  "k" INTEGER,
  "d" INTEGER,
  "a" INTEGER,
  "kd_diff" INTEGER,
  "kast" INTEGER,
  "adr" INTEGER,
  "hs_percent" INTEGER,
  "fk" INTEGER,
  "fd" INTEGER,
  "fk_fd_diff" INTEGER,
  "map_name" VARCHAR(100),
  "map_winner" VARCHAR(255),
  PRIMARY KEY ("match_id", "player_id", "map_name", "stat_type")
);

CREATE TABLE "detailed_matches_overview" (
  "match_id" VARCHAR(255) PRIMARY KEY,
  "match_title" VARCHAR(500),
  "event" VARCHAR(255),
  "date" DATE,
  "format" VARCHAR(100),
  "teams" VARCHAR(500),
  "score" VARCHAR(50),
  "maps_played" INTEGER,
  "patch" VARCHAR(50),
  "pick_ban_info" TEXT
);

CREATE TABLE "detailed_matches_maps" (
  "match_id" VARCHAR(255),
  "map_name" VARCHAR(100),
  "map_order" INTEGER,
  "score" VARCHAR(50),
  "winner" VARCHAR(255),
  "duration" VARCHAR(50),
  "picked_by" VARCHAR(255),
  PRIMARY KEY ("match_id", "map_name")
);

COMMENT ON TABLE "event_info" IS 'Standalone event details; no PK defined';

ALTER TABLE "detailed_matches_overview" ADD CONSTRAINT "fk_detailed_overview_matches"
FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id");

-- Foreign key constraints for economy_data
ALTER TABLE "economy_data" ADD CONSTRAINT "fk_economy_matches" 
FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id");

-- Foreign key constraints for performance_data  
ALTER TABLE "performance_data" ADD CONSTRAINT "fk_performance_matches"
FOREIGN KEY ("Match ID") REFERENCES "matches" ("match_id");

-- Foreign key constraints for detailed_matches_player_stats
ALTER TABLE "detailed_matches_player_stats" ADD CONSTRAINT "fk_detailed_player_matches"
FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id");

-- Foreign key constraints for detailed_matches_maps
ALTER TABLE "detailed_matches_maps" ADD CONSTRAINT "fk_detailed_maps_matches"
FOREIGN KEY ("match_id") REFERENCES "matches" ("match_id");

-- Foreign key constraints for player_stats
ALTER TABLE "detailed_matches_player_stats" ADD CONSTRAINT "fk_detailed_player_player_stats"
FOREIGN KEY ("player_id") REFERENCES "player_stats" ("player_id");


-- Foreign key constraints for maps_stats
ALTER TABLE "economy_data" ADD CONSTRAINT "fk_economy_maps_stats"
FOREIGN KEY ("map") REFERENCES "maps_stats" ("map_name");

ALTER TABLE "performance_data" ADD CONSTRAINT "fk_performance_maps"
FOREIGN KEY ("Map") REFERENCES "maps_stats" ("map_name");

ALTER TABLE "detailed_matches_player_stats" ADD CONSTRAINT "fk_detailed_player_maps"
FOREIGN KEY ("map_name") REFERENCES "maps_stats" ("map_name");

ALTER TABLE "detailed_matches_maps" ADD CONSTRAINT "fk_detailed_maps_maps_stats"
FOREIGN KEY ("map_name") REFERENCES "maps_stats" ("map_name");

-- Foreign key constraints for agents_stats
ALTER TABLE "performance_data" ADD CONSTRAINT "fk_performance_agents"
FOREIGN KEY ("Agent") REFERENCES "agents_stats" ("agent_name");

ALTER TABLE "detailed_matches_player_stats" ADD CONSTRAINT "fk_detailed_player_agents"
FOREIGN KEY ("agent") REFERENCES "agents_stats" ("agent_name");

