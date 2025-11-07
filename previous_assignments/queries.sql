-- =====================================================
-- VALORANT CHAMPIONS 2024 DATA ANALYSIS QUERIES
-- =====================================================

-- 1. BASIC DATA EXPLORATION QUERIES
-- =====================================================

-- 1a. Check data structures - show first 10 rows from each table
SELECT * FROM event_info LIMIT 10;
SELECT * FROM matches LIMIT 10;
SELECT * FROM player_stats LIMIT 10;
SELECT * FROM maps_stats LIMIT 10;
SELECT * FROM agents_stats LIMIT 10;
SELECT * FROM economy_data LIMIT 10;
SELECT * FROM performance_data LIMIT 10;
SELECT * FROM detailed_matches_overview LIMIT 10;
SELECT * FROM detailed_matches_player_stats LIMIT 10;
SELECT * FROM detailed_matches_maps LIMIT 10;

-- 1b. Query with filtering, aggregation, and sorting
-- Top 10 players by rating (100+ rounds)
SELECT 
    player_name, 
    team, 
    rating, 
    acs, 
    kd_ratio, 
    rounds
FROM player_stats 
WHERE rounds > 100 
ORDER BY rating DESC 
LIMIT 10;

-- 1c. Aggregation with GROUP BY and functions (COUNT, AVG, MIN, MAX)
-- Team stats
SELECT 
    team,
    COUNT(*) as player_count,
    AVG(rating) as avg_rating,
    AVG(acs) as avg_acs,
    MIN(rating) as min_rating,
    MAX(rating) as max_rating,
    AVG(kd_ratio) as avg_kd_ratio
FROM player_stats 
GROUP BY team 
ORDER BY avg_rating DESC;

-- 1d. JOIN between tables
-- INNER JOIN: Players with match performance
SELECT 
    ps.player_name,
    ps.team,
    ps.rating as overall_rating,
    dmps.rating as match_rating,
    dmps.acs as match_acs,
    dmps.map_name,
    dmps.stat_type
FROM player_stats ps
INNER JOIN detailed_matches_player_stats dmps 
    ON ps.player_id = dmps.player_id
WHERE dmps.stat_type = 'map'
ORDER BY ps.rating DESC
LIMIT 10;

-- =====================================================
-- 2. ANALYTICAL TOPICS (10 QUERIES)
-- =====================================================

-- Topic 1: Top Performing Players by Overall Rating
-- Best players across all matches
SELECT 
    player_name,
    team,
    rating,
    acs,
    kd_ratio,
    rounds
FROM player_stats 
ORDER BY rating DESC 
LIMIT 15;

-- Topic 2: Map Win Rate Analysis
-- Maps favor attack vs defense
SELECT 
    map_name,
    times_played,
    attack_win_percent,
    defense_win_percent,
    CASE 
        WHEN attack_win_percent > defense_win_percent THEN 'Attack Favored'
        WHEN defense_win_percent > attack_win_percent THEN 'Defense Favored'
        ELSE 'Balanced'
    END as map_balance
FROM maps_stats 
ORDER BY times_played DESC
LIMIT 10;

-- Topic 3: Agent Utilization and Performance
-- LEFT JOIN: All agents and their utilization rates
SELECT 
    ag.agent_name,
    ag.total_utilization,
    COUNT(dmps.player_id) as times_picked,
    AVG(dmps.rating) as avg_rating_when_picked
FROM agents_stats ag
LEFT JOIN detailed_matches_player_stats dmps 
    ON ag.agent_name = dmps.agent
GROUP BY ag.agent_name, ag.total_utilization
ORDER BY ag.total_utilization DESC
LIMIT 10;

-- Topic 4: Team Economy Performance
-- RIGHT JOIN: Economy data for all teams
SELECT 
    ed."Team",
    COUNT(ed.match_id) as matches_analyzed,
    AVG(ed."Pistol Won") as avg_pistol_wins,
    SUM(CASE WHEN ed."Eco (won)" LIKE '%(%)' THEN 1 ELSE 0 END) as eco_rounds_won
FROM economy_data ed
RIGHT JOIN player_stats ps ON ed."Team" = ps.team
GROUP BY ed."Team"
ORDER BY avg_pistol_wins DESC
LIMIT 10;

-- Topic 5: Match Duration and Map Performance
-- INNER JOIN: Match details with map performance
SELECT 
    dmo.match_title,
    dmo.teams,
    dmo.score,
    dmm.map_name,
    dmm.map_order,
    dmm.score as map_score,
    dmm.winner as map_winner,
    dmm.duration
FROM detailed_matches_overview dmo
INNER JOIN detailed_matches_maps dmm 
    ON dmo.match_id = dmm.match_id
ORDER BY dmo.match_title, dmm.map_order
LIMIT 10;

-- Topic 6: Player Performance by Map
-- Complex JOIN: Player stats across maps
SELECT 
    dmps.player_name,
    dmps.player_team,
    dmps.map_name,
    dmps.rating,
    dmps.acs,
    dmps.k,
    dmps.d,
    dmps.a,
    ms.attack_win_percent,
    ms.defense_win_percent
FROM detailed_matches_player_stats dmps
INNER JOIN maps_stats ms ON dmps.map_name = ms.map_name
WHERE dmps.stat_type = 'map'
ORDER BY dmps.rating DESC, dmps.map_name
LIMIT 10;

-- Topic 7: Clutch Performance Analysis
-- Players' clutch performance (1vX situations)
SELECT 
    player_name,
    team,
    rating,
    clutches,
    k_max,
    kills,
    deaths,
    ROUND((kills::numeric / NULLIF(deaths, 0)), 2) as kd_ratio
FROM player_stats 
WHERE clutches IS NOT NULL 
    AND clutches != ''
ORDER BY rating DESC
LIMIT 10;

-- Topic 8: Headshot Accuracy Leaders
-- Best headshot percentage
SELECT 
    player_name,
    team,
    hs_percent,
    rating,
    acs,
    kills,
    deaths
FROM player_stats 
WHERE hs_percent IS NOT NULL
ORDER BY hs_percent DESC
LIMIT 10;

-- Topic 9: First Kill/First Death Impact
-- Players' impact on round starts
SELECT 
    player_name,
    team,
    first_kills,
    first_deaths,
    (first_kills - first_deaths) as fk_fd_diff,
                CAST((first_kills::float / NULLIF(first_kills + first_deaths, 0)) * 100 AS DECIMAL(5,2)) as fk_percentage,
    rating
FROM player_stats 
WHERE first_kills > 0 OR first_deaths > 0
ORDER BY fk_fd_diff DESC
LIMIT 10;

-- Topic 10: Tournament Overview and Match Statistics
-- Tournament statistics
SELECT 
    'Total Matches' as metric,
    COUNT(*)::text as value
FROM matches
UNION ALL
SELECT 
    'Total Players',
    COUNT(DISTINCT player_id)::text
FROM player_stats
UNION ALL
SELECT 
    'Total Maps Played',
    COUNT(DISTINCT map_name)::text
FROM maps_stats
UNION ALL
SELECT 
    'Total Agents Used',
    COUNT(DISTINCT agent_name)::text
FROM agents_stats
UNION ALL
SELECT 
    'Average Player Rating',
    ROUND(AVG(rating), 2)::text
FROM player_stats
UNION ALL
SELECT 
    'Highest Rating',
    ROUND(MAX(rating), 2)::text
FROM player_stats
LIMIT 10;
