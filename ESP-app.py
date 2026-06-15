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

from db_queries import get_match_data
from EyeSpy_predictor import calculate_expected_time, main

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


def display_expected_time(players):
    conn = db_connection()
    cursor = conn.cursor()
    if not conn:
        print("No DB connection")
        return pd.DataFrame()
    
    #Check if the player stats are created or upto date
    for player in players:
        today = date.today
        span = timedelta(days=5)
        until = today-span
        starting_date=until.strftime()
        end_date=today.strftime

        cursor.execute("SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",(player, starting_date, end_date))
        stats=cursor.fetchall()

        if stats is not None:
            avg = stats[2]
            sd = stats[3]
            esfr= stats[4]
            cr = stats[5]
            fbr = stats[6]
            CS_score = stats[7]
            avg_blind_ahead = stats[8]
            avg_blind_behind = stats[9]

            calculate_expected_time(player, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind)
        else:
            print("No stats or invalid stats creating new blind stats for {player}")
            main()

            cursor.execute("SELECT * FROM player_blind_stats WHERE username = %s AND date_time BETWEEN %s AND %s ORDER BY date_time DESC LIMIT 1;",(player, starting_date, end_date))
            stats=cursor.fetchall()
    
            if stats is not None:
                avg = stats[2]
                sd = stats[3]
                esfr= stats[4]
                cr = stats[5]
                fbr = stats[6]
                CS_score = stats[7]
                avg_blind_ahead = stats[8]
                avg_blind_behind = stats[9]
    
                calculate_expected_time(player, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind)



if __name__ == '__main__':
    conn = db_connection()
    while True:
      print("1) Match Id")
      print("2) Live Matches")
      choice = int(input("Select option: "))
      if choice in [1, 2, 3]:
              print("You have selected option " + str(choice))
              print("*Please note enter a valid match ID that is already finished to get ESP insights. NOte that the predicted data will be stored for future testing.* ")
              print("\n")
              if choice == 1:
                  matchId = input("Enter match ID: ")
                  players = get_match_data(matchId)
                  display_expected_time(players)
                  print("\n")
              elif choice == 2:
                  print("Hi still in development")
              elif choice == 3:
                      print("\n")
                      break
      else:
        print("Invalid choice. Please enter a number between 1 and 4.")
        conn.close()
          
    if conn:
        conn.close()
        print("Database connection closed")