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

def detect_blind_event(host, private_key):
    """This function checks for the blind event in the live match and runs the ESP predictor"""

    previous_timeline = {}
    initial_data_pull = False
    try:
        while True:
            current_data = get_live_pv_match_data()

            if current_data is None:
                print("No match data provided")
                return

            if not isinstance(current_data, dict):
                print(f"Skipping {current_data}")
                return

            if not initial_data_pull:
                match_id = current_data.get('id')
                match_time = current_data.get('time')

                players = current_data.get('players', []) or []
                print(f"Ongoing match:{match_id} found in {host} private room")
                initial_data_pull = True

                for player in players:
                    if not player or not isinstance(player, dict):
                        print(f"Skipping malformed player entry in match {match_id}: {player}")
                        continue
                    player_uuid = player.get('uuid')
                    nickname = player.get('nickname')

                # This is the main checkpoint that detects if a player has entered blind or not
                timeline = current_data.get('timelines', []) or []
                print(timeline)
                #Still in development
                break

    except Exception as e:
        print(f"Error inserting user data: {e}")
        conn.rollback()
def get_eye_spy_prediction(players, matchId, match_data=None):

    conn = db_connection()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()

    cursor = conn.cursor()
    try:
        for player in players:
            today = date.today()
            span = timedelta(days=5)
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
                host_username = print("Enter the username of the Host/co-host: ")
                private_key = print("Enter the Private key: ")
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