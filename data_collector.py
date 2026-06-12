# This is to get data from MCSR API and store it in a database and some functions are here to collect data for the predictors


#Dependencies
import requests
import os 
import dotenv
import mariadb
import mysql.connector
import traceback
import time
import pandas as pd

dotenv.load_dotenv("credentials.env")

MCSR_BASE_URL = os.getenv("MCSR_API_ENDPOINT", "https://api.mcsrranked.com").rstrip("/")
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

conn=""

def db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        print("Database connected successfully")
        return conn
    except Exception as e:
        print(e)
        return None


def match_data_collector(matchID, quiet=False):
    url = f"{MCSR_BASE_URL}/matches/{matchID}"
    params = {}
    #if season is not None:
        #params["season"] = season

    response = requests.get(url, params=params)
    print("REQUEST URL:", response.url)
    print("STATUS CODE:", response.status_code)

    try:
        data = response.json()
    except requests.JSONDecodeError:
        print("Response is not valid JSON:")
        print(response.text)
        raise

    if not quiet:
        print(data)
    return data

def user_data_collector(username, quiet=False):
    url = f"{MCSR_BASE_URL}/users/{username}"
    params = {}

    response = requests.get(url, params=params)
    print("REQUEST URL:", response.url)
    print("STATUS CODE:", response.status_code)

    try:
        data = response.json()
    except requests.JSONDecodeError:
        print("Response is not valid JSON:")
        print(response.text)
        raise
    if not quiet:
        print(data)
    return data

def user_matches_data_collector(username, quiet=False):
    url = f"{MCSR_BASE_URL}/users/{username}/matches?count=100&season=11"
    params = {}

    response = requests.get(url, params=params)
    print("REQUEST URL:", response.url)
    print("STATUS CODE:", response.status_code)

    try:
        data = response.json()
    except requests.JSONDecodeError:
        print("Response is not valid JSON:")
        print(response.text)
        raise
    if not quiet:
        print(data)
    return data


def insert_match_data(conn, match_data):
    """Insert match data into matches and match_players tables"""
    if not conn:
        print("No database connection")
        return
    try:
        cursor = conn.cursor()
        # match_data can be either the full API response {'data': {...}}
        # or a match object directly. Normalize to `match` dict.
        if match_data is None:
            print("No match data provided")
            return
        if isinstance(match_data, dict) and 'data' in match_data and isinstance(match_data['data'], dict):
            match = match_data['data']
        elif isinstance(match_data, dict) and 'id' in match_data:
            match = match_data
        else:
            match = {}

        if not match or not isinstance(match, dict):
            print(f"Skipping insert: malformed match_data: {match_data}")
            return

        match_id = match.get('id')
        match_type = match.get('type')
        season = match.get('season')
        category = match.get('category')
        game_mode = match.get('gameMode')
        date_played = match.get('date')
        forfeited = match.get('forfeited', False)
        decayed = match.get('decayed', False)
        replay_exists = match.get('replayExist', False)
        
        # Seed data
        seed = match.get('seed') or {}
        seed_id = seed.get('id')
        seed_type = match.get('seedType')
        bastion_type = match.get('bastionType')
        overworld = seed.get('overworld')
        nether = seed.get('nether')
        
        # Result data
        result = match.get('result') or {}
        winner_uuid = result.get('uuid')
        result_time = result.get('time')
        
        # Insert players first to satisfy FK constraints (winner_uuid may reference a player)
        players = match.get('players', []) or []
        for player in players:
            if not player or not isinstance(player, dict):
                print(f"Skipping malformed player entry in match {match_id}: {player}")
                continue
            player_uuid = player.get('uuid')
            nickname = player.get('nickname')
            role_type = player.get('roleType')
            country = player.get('country')

            # Insert/update into players table
            player_query = """
                INSERT INTO players (uuid, nickname, role_type, country)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nickname=VALUES(nickname), country=VALUES(country)
            """
            cursor.execute(player_query, (player_uuid, nickname, role_type, country))

        # Now insert into matches table (players exist)
        match_query = """
            INSERT INTO matches 
            (match_id, match_type, season, category, game_mode, date_played, 
             winner_uuid, result_time_ms, forfeited, decayed, seed_id, seed_type, 
             bastion_type, overworld_structure, nether_structure, replay_exists)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                season=VALUES(season), winner_uuid=VALUES(winner_uuid), 
                result_time_ms=VALUES(result_time_ms), forfeited=VALUES(forfeited), decayed=VALUES(decayed)
        """
        cursor.execute(match_query, (
            match_id, match_type, season, category, game_mode, date_played,
            winner_uuid, result_time, forfeited, decayed, seed_id, seed_type,
            bastion_type, overworld, nether, replay_exists
        ))

        # Insert match_players records
        for player in players:
            if not player or not isinstance(player, dict):
                continue
            player_uuid = player.get('uuid')
            changes = match.get('changes', []) or []
            elo_change = 0
            elo_after = player.get('eloRate', 0) or 0
            elo_before = elo_after - elo_change

            for change in changes:
                if change.get('uuid') == player_uuid:
                    elo_change = change.get('change', 0) or 0
                    elo_after = change.get('eloRate', elo_after) or elo_after
                    elo_before = elo_after - elo_change
                    break

            rank_before = player.get('eloRank', 0) or 0

            match_player_query = """
                INSERT INTO match_players 
                (match_id, player_uuid, elo_before, rank_before, elo_change, elo_after, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    elo_change=VALUES(elo_change), elo_after=VALUES(elo_after), country=VALUES(country)
            """
            cursor.execute(match_player_query, (
                match_id, player_uuid, elo_before, rank_before, elo_change, elo_after, player.get('country')
            ))
        
        # Insert timelines
        timelines = match.get('timelines', []) or []
        timeline_query = """
            INSERT INTO timelines (match_id, player_uuid, event_time_ms, event_type)
            VALUES (%s, %s, %s, %s)
        """
        for timeline in timelines:
            if not timeline or not isinstance(timeline, dict):
                print(f"Skipping malformed timeline in match {match_id}: {timeline}")
                continue
            cursor.execute(timeline_query, (
                match_id,
                timeline.get('uuid'),
                timeline.get('time'),
                timeline.get('type')
            ))
        
        conn.commit()
        print(f"Match {match_id} inserted successfully")
        cursor.close()
        
    except Exception as e:
        print(f"Error inserting match data: {e}")
        print(traceback.format_exc())
        conn.rollback()


def insert_user_data(conn, user_data):
    """Insert user data into players table"""
    if not conn:
        print("No database connection")
        return
    
    try:
        cursor = conn.cursor()
        user = user_data.get('data', {})
        
        uuid = user.get('uuid')
        nickname = user.get('nickname')
        country = user.get('country')
        role_type = user.get('roleType')
        current_elo = user.get('eloRate')
        current_rank = user.get('eloRank')
        
        # Timestamp data
        timestamp = user.get('timestamp', {})
        first_online = timestamp.get('firstOnline')
        last_online = timestamp.get('lastOnline')
        last_ranked = timestamp.get('lastRanked')
        
        # Statistics - total
        stats = user.get('statistics', {})
        total_stats = stats.get('total', {})
        total_matches = total_stats.get('playedMatches', {}).get('ranked', 0)
        total_wins = total_stats.get('wins', {}).get('ranked', 0)
        total_losses = total_stats.get('loses', {}).get('ranked', 0)
        total_completions = total_stats.get('completions', {}).get('ranked', 0)
        total_forfeits = total_stats.get('forfeits', {}).get('ranked', 0)
        best_time = total_stats.get('bestTime', {}).get('ranked')
        
        # Connections
        connections = user.get('connections', {})
        twitch_name = connections.get('twitch', {}).get('name')
        youtube_name = connections.get('youtube', {}).get('name')
        
        # Insert/update into players table
        query = """
            INSERT INTO players 
            (uuid, nickname, country, role_type, current_elo, current_rank, 
             first_online, last_online, last_ranked, total_matches, total_wins, 
             total_losses, total_completions, total_forfeits, best_time_ms, 
             twitch_name, youtube_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nickname=VALUES(nickname),
                country=VALUES(country),
                current_elo=VALUES(current_elo),
                current_rank=VALUES(current_rank),
                last_online=VALUES(last_online),
                last_ranked=VALUES(last_ranked),
                total_matches=VALUES(total_matches),
                total_wins=VALUES(total_wins),
                total_losses=VALUES(total_losses),
                total_completions=VALUES(total_completions),
                total_forfeits=VALUES(total_forfeits),
                best_time_ms=VALUES(best_time_ms)
        """
        cursor.execute(query, (
            uuid, nickname, country, role_type, current_elo, current_rank,
            first_online, last_online, last_ranked, total_matches, total_wins,
            total_losses, total_completions, total_forfeits, best_time,
            twitch_name, youtube_name
        ))
        
        conn.commit()
        print(f"User {nickname} inserted successfully")
        cursor.close()
        
    except Exception as e:
        print(f"Error inserting user data: {e}")
        conn.rollback()


def insert_user_matches_data(conn, user_matches_data):
    """Insert user's match history into database"""
    if not conn:
        print("No database connection")
        return
    
    try:
        if not user_matches_data or not isinstance(user_matches_data, dict):
            print(f"No user matches data to insert: {user_matches_data}")
            return
        matches = user_matches_data.get('data', []) or []

        inserted = 0
        for idx, match in enumerate(matches):
            if not match or not isinstance(match, dict):
                print(f"Skipping non-dict match at index {idx}: {match}")
                continue
            try:
                # Create match_data wrapper to reuse insert_match_data
                match_wrapper = {'data': match}
                insert_match_data(conn, match_wrapper)
                inserted += 1
            except Exception as ie:
                print(f"Error inserting match at index {idx}: {ie}")
                print(traceback.format_exc())

        print(f"Inserted {inserted} matches for user (out of {len(matches)})")

    except Exception as e:
        print(f"Error inserting user matches data: {e}")
        print(traceback.format_exc())

############################################################################################
#This part contains functions that is used by predictors to pull data from the db

def get_blind_splits(username):
    # Connect to DB and fetch player's UUID
    conn = db_connection()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM players WHERE nickname=%s", (username,))
        row = cursor.fetchone()
        if not row:
            print(f"No player found with nickname {username}")
            cursor.close()
            conn.close()
            return pd.DataFrame()

        player_uuid = row[0]

        # Aggregate blind enter and stronghold enter times per match
        query = (
            "SELECT match_id, "
            "MIN(CASE WHEN event_type='projectelo.timeline.blind_travel' THEN event_time_ms END) AS blind_time, "
            "MIN(CASE WHEN event_type='story.follow_ender_eye' THEN event_time_ms END) AS strong_time "
            "FROM timelines "
            "WHERE player_uuid=%s AND event_type IN ('projectelo.timeline.blind_travel','story.follow_ender_eye') "
            "GROUP BY match_id "
            "HAVING blind_time IS NOT NULL AND strong_time IS NOT NULL"
        )

        cursor.execute(query, (player_uuid,))
        results = cursor.fetchall()

        # Build dataframe with requested keys: matchid, blind_entertime, stronghold_entertime, blind_split_ms
        records = []
        for match_id, blind_time, strong_time in results:
            try:
                split = None
                if blind_time is not None and strong_time is not None:
                    split = int(strong_time) - int(blind_time)
                records.append({
                    'matchid': match_id,
                    'blind_entertime': blind_time,
                    'stronghold_entertime': strong_time,
                    'blind_split_ms': split
                })
            except Exception as e:
                print("Error creating the list")
        df = pd.DataFrame(records)
        cursor.close()
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching blind splits: {e}")
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass
        return pd.DataFrame()

def get_player_match_data(username):
    conn = db_connection()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT uuid FROM players WHERE nickname=%s", (username,))
        row = cursor.fetchone()
        if not row:
            print(f"No player found with nickname {username}")
            cursor.close()
            conn.close()
            return pd.DataFrame()

        player_uuid = row[0]

        query = (
            "SELECT "
            "t.match_id, "
            "MIN(CASE WHEN t.event_type='story.enter_the_nether' THEN t.event_time_ms END) AS nether_enter_time, "
            "MIN(CASE WHEN t.event_type='nether.find_bastion' THEN t.event_time_ms END) AS bastion_enter_time, "
            "MIN(CASE WHEN t.event_type='nether.find_fortress' THEN t.event_time_ms END) AS fortress_enter_time, "
            "MIN(CASE WHEN t.event_type='projectelo.timeline.blind_travel' AND t.player_uuid = %s THEN t.event_time_ms END) AS blind_time, "
            "MIN(CASE WHEN t.event_type='story.follow_ender_eye' AND t.player_uuid = %s THEN t.event_time_ms END) AS stronghold_time, "
            "MIN(CASE WHEN t.event_type='story.enter_the_end' AND t.player_uuid = %s THEN t.event_time_ms END) AS end_enter_time, "
            "MIN(CASE WHEN t.event_type='projectelo.timeline.blind_travel' AND t.player_uuid <> %s THEN t.event_time_ms END) AS opponent_blind_time, "
            "MIN(CASE WHEN t.event_type='story.follow_ender_eye' AND t.player_uuid <> %s THEN t.event_time_ms END) AS opponent_stronghold_time "
            "FROM timelines t "
            "WHERE t.match_id IN ("
            "    SELECT DISTINCT match_id "
            "    FROM timelines "
            "    WHERE player_uuid=%s "
            "      AND event_type IN ('story.enter_the_nether', 'nether.find_bastion', 'nether.find_fortress', "
            "'projectelo.timeline.blind_travel', 'story.follow_ender_eye', 'story.enter_the_end')"
            ") "
            "AND t.event_type IN ('story.enter_the_nether', 'nether.find_bastion', 'nether.find_fortress', "
            "'projectelo.timeline.blind_travel', 'story.follow_ender_eye', 'story.enter_the_end') "
            "GROUP BY t.match_id "
            "HAVING "
            "MIN(CASE WHEN t.event_type='story.enter_the_nether' THEN t.event_time_ms END) IS NOT NULL "
            "OR MIN(CASE WHEN t.event_type='nether.find_bastion' THEN t.event_time_ms END) IS NOT NULL "
            "OR MIN(CASE WHEN t.event_type='nether.find_fortress' THEN t.event_time_ms END) IS NOT NULL "
            "OR MIN(CASE WHEN t.event_type='projectelo.timeline.blind_travel' THEN t.event_time_ms END) IS NOT NULL "
            "OR MIN(CASE WHEN t.event_type='story.follow_ender_eye' THEN t.event_time_ms END) IS NOT NULL "
            "OR MIN(CASE WHEN t.event_type='story.enter_the_end' THEN t.event_time_ms END) IS NOT NULL"
        )

        cursor.execute(query, (player_uuid, player_uuid, player_uuid, player_uuid, player_uuid, player_uuid))
        results = cursor.fetchall()

        records = []
        for match_id, nether_enter_time, bastion_enter_time, fortress_enter_time, blind_time, stronghold_time, end_enter_time, opponent_blind_time, opponent_stronghold_time in results:
            records.append({
                'matchid': match_id,
                'nether_enter_time': nether_enter_time,
                'bastion_enter_time': bastion_enter_time,
                'fortress_enter_time': fortress_enter_time,
                'blind_time': blind_time,
                'stronghold_time': stronghold_time,
                'end_enter_time': end_enter_time,
                'opponent_blind_time': opponent_blind_time,
                'opponent_stronghold_time': opponent_stronghold_time,
            })

        df = pd.DataFrame(records)
        cursor.close()
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching player match data: {e}")
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass
        return pd.DataFrame()

if __name__ == '__main__':
    conn = db_connection()
    while True:
      print("1) Players")
      print("2) Matches")
      print("3) ADD individual Match info")
      choice = int(input("Select option: "))
      if choice in [1, 2, 3, 4]:
              print("You have selected option " + str(choice))
              print("\n")
              if choice == 1:
                  username = input("Enter username: ")
                  user_data = user_data_collector(username)
                  insert_user_data(conn, user_data)
                  print("\n")
              elif choice == 2:
                  username = input("Enter username: ")
                  user_matches_data = user_matches_data_collector(username, quiet=True)

                  matches = user_matches_data.get('data', []) or []
                  total = len(matches)
                  print(f"Found {total} matches for {username}. Processing...")

                  # optional delay between requests (seconds)
                  delay = float(os.getenv('MCSR_REQUEST_DELAY', '0'))

                  processed = 0
                  for idx, m in enumerate(matches):
                      if not m or not isinstance(m, dict):
                          continue
                      match_id = m.get('id')
                      if not match_id:
                          continue
                      # progress print only
                      print(f"Processing {idx+1}/{total}: match {match_id}")
                      match_data = match_data_collector(match_id, quiet=True)
                      insert_match_data(conn, match_data)
                      processed += 1
                      if delay > 0:
                          time.sleep(delay)

                  print(f"Processed {processed}/{total} matches for user")
                  print("\n")
              elif choice == 3:
                  matchId = input("Enter the match ID: ")
                  match_data = match_data_collector(matchId)
                  insert_match_data(conn, match_data)
              elif choice == 4:
                      print("\n")
                      break
      else:
        print("Invalid choice. Please enter a number between 1 and 4.")
        conn.close()
          
    if conn:
        conn.close()
        print("Database connection closed")

