#This module contains the functions that retreives data from the db for data analysis and prediction

import os

import dotenv
import mysql.connector
import pandas as pd

from data_collector import match_data_collector, insert_match_data

dotenv.load_dotenv("credentials.env")

DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')


def db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
        )
        return conn
    except Exception as e:
        print(e)
        return None


def get_blind_splits(username):
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
                    'blind_split_ms': split,
                })
            except Exception:
                print("Error creating the list")

        df = pd.DataFrame(records)
        cursor.close()
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching blind splits: {e}")
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
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
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return pd.DataFrame()
    

#########################################################################################
#Functions used by the ESP-app.py

def get_match_data(matchId):
    """This function will pull relevant match data if not found will be pulling data using the API"""
    conn = db_connection()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT player_uuid FROM match_players WHERE match_id = %s ORDER BY id LIMIT 2;", (matchId,))
        player_uuids = cursor.fetchall()
        participants = []

        if player_uuids:
            for player_row in player_uuids:
                player_uuid = player_row[0]
                cursor.execute("SELECT nickname FROM players WHERE uuid=%s", (player_uuid,))
                player = cursor.fetchone()
                if player:
                    nickname = player[0]
                    print(f"Player found for match:{matchId} - {nickname}")
                    participants.append(nickname)
                else:
                    print(f"No nickname found for uuid {player_uuid} in match {matchId}")

        else:
            # Pull from the API
            match_data = match_data_collector(matchId, quiet=True)
            insert_match_data(match_data)

            if match_data is None:
                print("No match data provided")
                return
            if isinstance(match_data, dict) and 'data' in match_data and isinstance(match_data['data'], dict):
                match = match_data['data']
            elif isinstance(match_data, dict) and 'id' in match_data:
                match = match_data
            else:
                match = {}
            
            players = match.get('players', []) or []
            for player in players:
                if not player or not isinstance(player, dict):
                  print(f"Skipping malformed player entry in match {matchId}: {player}")
                  continue
                nickname = player.get('nickname')
                participants.append(nickname)
                
    except Exception as e:
        print(f"A error occured while looking for match data: {e}")

    return participants

        
