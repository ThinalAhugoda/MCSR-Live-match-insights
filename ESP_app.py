#Main algorithm of ESP Graphic
#Dependencies
import requests
import os 
import dotenv
import mariadb
import mysql.connector
import traceback
import time
import pandas as pd
from datetime import date, timedelta

from db_queries import get_match_data, get_player_match_data
from EyeSpy_predictor import calculate_expected_time, main, calculate_expected_time_live
from data_collector import get_live_pv_match_data

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
        return conn
    except Exception as e:
        print(e)
        return None

def get_live_players():
    url = f"https://api.mcsrranked.com/live"
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

    live_matches = data.get('data', {}).get('liveMatches', []) or []

    if not live_matches:
        print("No ongoing matches found.")
        return None

    print("\n")
    print("===============================================")
    print("ONGOING MATCHES")
    print("===============================================")
    print("\n")

    for idx, match in enumerate(live_matches, start=1):
        players = match.get('players', []) or []
        if len(players) >= 2:
            player1 = players[0].get('nickname', 'Unknown')
            player2 = players[1].get('nickname', 'Unknown')
            print(f"Match {idx} - {player1} vs {player2}")
        else:
            print(f"Match {idx} - Incomplete match data")

    print("\n")
    while True:
        try:
            print("Press 'Q' to quit")
            choice = int(input("Select a match number to generate insights: "))

            if choice == 'Q':
                print("Blind insight calculation canceled......")
                return None, None
            
            if 1 <= choice <= len(live_matches):
                selected_match = live_matches[choice - 1]
                players = selected_match.get('players', []) or []
                participant_names = [p.get('nickname') for p in players if p and isinstance(p, dict)]
                match_Id = selected_match.get('id')
                print(f"\nSelected: {' vs '.join(participant_names)}")
                return participant_names, selected_match
            else:
                print(f"Please enter a number between 1 and {len(live_matches)}")
        except ValueError:
            print("Please enter a valid number.")

import time

def detect_blind_event(host, private_key):
    """This function checks for the blind event in the live match and runs the ESP predictor"""

    initial_data_pull = False
    found_players = []
    eligible_players = []
    processed_players = set()  # Track who we already ran the predictor for

    try:
        while True:
            current_data = get_live_pv_match_data(host, private_key)

            if current_data is None:
                print("No match data provided")
                return

            if not isinstance(current_data, dict):
                print(f"Skipping invalid data format: {current_data}")
                return

            #  ONE-TIME INITIAL SETUP
            if not initial_data_pull:
                players = current_data.get("data", {}).get("players", [])
                print(f"Ongoing match: found in {host}s private room")
                
                for player in players:
                    if player and isinstance(player, dict):
                        found_players.append(player.get('uuid'))
                        nickname = player.get('nickname')
                        role_type = player.get('roleType')
                        country = player.get('country')


                # Determine who is eligible 
                target_type = 'nether.find_fortress'
                fort_results = {
                    player_id: [
                        item for item in current_data['data']['timelines'] 
                        if item['uuid'] == player_id and item['type'] == target_type
                    ]
                    for player_id in found_players
                }
                print(fort_results)

                eligible_players = [pid for pid, timeline in fort_results.items() if len(timeline) == 0]

                if len(eligible_players) == 0:
                    print("Both players have entered the fort. Aborting insight prediction.")
                    return
                
                print(f"Eligible players for tracking: {eligible_players}")
                initial_data_pull = True  # Setup done

            target_type = 'projectelo.timeline.blind_travel'

            # Get blind results ONLY for eligible players who haven't finished yet
            blind_results = {
                player_id: [
                    item for item in current_data['data']['timelines'] 
                    if item['uuid'] == player_id and item['type'] == target_type
                ]
                for player_id in eligible_players if player_id not in processed_players
            }
            
            # Check who just entered blind travel on this pull
            newly_entered = [pid for pid, timeline in blind_results.items() if len(timeline) > 0]
            
            if newly_entered:
                match_id = current_data.get('id')
                
                for player_id in newly_entered:
                    print(f"Player {player_id} entered blind!")
                    
                    # Fire off the single prediction calculation immediately
                    get_single_eye_spy_prediction(player_id, nickname, role_type, country, match_id, match_data=current_data)
                    
                    processed_players.add(player_id)

            if len(processed_players) == len(eligible_players):
                print("All eligible players have entered blind and been processed. Ending tracking.")
                return  
            
            else:
                print("Waiting for remaining player(s) to enter blind split...")
                time.sleep(5)

    except Exception as e:
        print(f"Error in tracking loop: {e}")

    return True

def get_single_eye_spy_prediction(player_uuid, nickname, role_type, country, matchId, match_data=None):
    """Fetches stats and runs the ESP predictor for ONE specific player instantly"""
    conn = db_connection()
    if not conn:
        print("No DB connection")
        return None

    cursor = conn.cursor()
    try:
        today = date.today()
        span = timedelta(days=25)
        until = today - span
        starting_date = until.strftime('%Y-%m-%d')

        tomorrow = today + timedelta(days=1)
        end_date = tomorrow.strftime('%Y-%m-%d')

        #Get the username from the passed UUID if not add a new player record
        cursor.execute("SELECT * FROM players WHERE uuid=%s ;", (player_uuid),)
        player = cursor.fetchone()

        if player is None:
            # Insert/update into players table
            player_query = """
                INSERT INTO players (uuid, nickname, role_type, country)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nickname=VALUES(nickname), country=VALUES(country)
            """
            cursor.execute(player_query, (player_uuid, nickname, role_type, country))

        # Look up just this specific player's historical metrics
        cursor.execute(
            "SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",
            (nickname, starting_date, end_date),
        )
        stats = cursor.fetchone()

        if not stats:
            print(f"No stats for {nickname}; generating new blind stats...")
            main(nickname) 
            time.sleep(3)
            conn.commit()
            
            cursor.execute(
                "SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",
                (nickname, starting_date, end_date),
            )
            stats = cursor.fetchone()

        if stats:
            # Unpack the metrics
            avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind = stats[2:10]

            if match_data is not None:
                final_time_ms = calculate_expected_time_live(
                    nickname, matchId, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind, match_data
                )
            else:
                final_time_ms = calculate_expected_time(
                    nickname, matchId, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind
                )

            final_time_s = int(final_time_ms / 1000)
            minutes, seconds = divmod(final_time_s, 60)
            eye_spy_first_rate = esfr * 100

            print("\n" + "="*47)
            print("LOGGED INSIGHT: MCSR EYE SPY PREDICTION")
            print("="*47)
            print(f"Player   : {nickname}")
            print(f"ETA Split: {int(minutes):02d}:{seconds:05.2f}")
            print(f"ESFR     : {eye_spy_first_rate:.2f}%")
            print("="*47 + "\n")
            
            return final_time_ms
        else:
            print(f"Unable to obtain blind stats for {nickname} after generation")
            return None

    except TypeError as e:
        print(f"Type Error occurred when collecting player blind stats: {e}")
        return None
    finally:
        cursor.close()
        conn.close()
def get_eye_spy_prediction(players, matchId, match_data=None):

    conn = db_connection()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()

    cursor = conn.cursor()
    try:
        for player in players:
            today = date.today()
            span = timedelta(days=25)
            until = today - span
            starting_date = until.strftime('%Y-%m-%d')

            tomorrow = today + timedelta(days=1)
            end_date = tomorrow.strftime('%Y-%m-%d')


            cursor.execute(
                "SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",
                (player, starting_date, end_date),
            )
            stats = cursor.fetchone()

            if not stats:
                print(f"No stats or invalid stats for {player}; creating new blind stats")
                main(player)
                time.sleep(3)
                conn.commit()
                cursor.execute(
                    "SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",
                    (player, starting_date, end_date),
                )
                stats = cursor.fetchone()

            if stats:
                avg = stats[2]
                sd = stats[3]
                esfr = stats[4]
                cr = stats[5]
                fbr = stats[6]
                CS_score = stats[7]
                avg_blind_ahead = stats[8]
                avg_blind_behind = stats[9]

                if match_data is not None:
                    final_time_ms = calculate_expected_time_live(
                        player,
                        matchId,
                        avg,
                        sd,
                        esfr,
                        cr,
                        fbr,
                        CS_score,
                        avg_blind_ahead,
                        avg_blind_behind,
                        match_data,
                    )
                else:
                    final_time_ms = calculate_expected_time(
                        player,
                        matchId,
                        avg,
                        sd,
                        esfr,
                        cr,
                        fbr,
                        CS_score,
                        avg_blind_ahead,
                        avg_blind_behind,
                    )

                final_time_s = int(final_time_ms / 1000)
                minutes, seconds = divmod(final_time_s, 60)
                eye_spy_first_rate = esfr * 100

                print("\n")
                print("===============================================")
                print("EYE SPY BATTLE : MCSR Ranked Insights")
                print("===============================================")
                print("\n")
                print(f"{player} - Expected strong hold time:")
                print(f"{int(minutes):02d}:{seconds:05.2f}")
                print(f"ESFR : {eye_spy_first_rate:.2f}%")

                time.sleep(3)
            else:
                print(f"Unable to obtain blind stats for {player} after generation")

    except TypeError as e:
        print(f"Type Error occured when collecting player blind stats: {e}")
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass



if __name__ == '__main__':
    conn = db_connection()
    while True:
        print("\n")
        print("Welcome to the EYE SPY predictor - MCSR LIVE INSIGHTS")
        print("=======================================================")
        print("\n")
        print("1) Match Id - Enter a matchID of a concluded match and get the player blind split predictions")
        print("2) Live Matches - Detects a ongiong live matche which is capable of creating insights and let the user to generate live insights")
        print("3) Private room matches - Using private rook key generate insights")
        print("4) Exit")
        print("\n")
        choice = int(input("Select option: "))
        if choice in [1, 2, 3, 4]:
            print("You have selected option " + str(choice))
            print("*Please note enter a valid match ID that is already finished to get ESP insights. NOte that the predicted data will be stored for future testing.* ")
            print("\n")
            if choice == 1:
                matchId = input("Enter match ID: ")
                players = get_match_data(matchId)
                mode="Normal"
                get_eye_spy_prediction(players, matchId)
                print("\n")
            elif choice == 2:
                print("Fetching live matches...")
                participants, match_data = get_live_players()
                if participants:
                    print(match_data)
                    match_id = match_data.get('id') if match_data else None
                    mode="Live"
                    get_eye_spy_prediction(participants, match_id, match_data)
            elif choice == 3:
                host_username = input("Enter the username of the Host/co-host: ")
                private_key = input("Enter the Private key: ")
                detect_blind_event(host_username, private_key)
            elif choice == 4:
                print("Thanks for using the MCSR LIVE INSIGHTS")
                print("\n")
                break
        else:
            print("Invalid choice. Please enter a number between 1 and 4.")
            print("\n")
    if conn:
        conn.close()
        print("Database connection closed")