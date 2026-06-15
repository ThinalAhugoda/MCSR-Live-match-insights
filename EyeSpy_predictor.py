import importlib
import db_queries
import data_collector
import matplotlib.pyplot as plt



def get_avg_std(df):
    avg_blind = df["blind_split_ms"].mean()
    std_blind = df["blind_split_ms"].std()
    print("Average blind split (ms):", avg_blind)
    print("SD of blind split: ", std_blind)
    return avg_blind, std_blind



def calculate_lead_rate(df):
    """Calculate the rate of matches where the player reaches stronghold earlier than their opponent."""
    valid_df = df.dropna(subset=["stronghold_time", "opponent_stronghold_time"])

    if valid_df.empty:
        print("ESFR: 0.0 (no comparable stronghold records found)")
        return 0.0

    count = int((valid_df["stronghold_time"] < valid_df["opponent_stronghold_time"]).sum())
    eye_spy_first_rate = count / len(valid_df)
    print("ESFR: ", eye_spy_first_rate)
    return eye_spy_first_rate

def calculate_comeback_rate(df):
    """Calculate the rate of matches where the player reaches stronghold first despite the opponent having a lower blind time."""
    valid_df = df.dropna(subset=["blind_time", "opponent_blind_time", "stronghold_time", "opponent_stronghold_time"])

    if valid_df.empty:
        print("Comeback rate: 0.0 (no comparable data found)")
        return 0.0

    count = int(
        ((valid_df["stronghold_time"] < valid_df["opponent_stronghold_time"]) &
         (valid_df["blind_time"] > valid_df["opponent_blind_time"]))
        .sum()
    )
    comeback_rate = count / len(valid_df)
    print("Comeback rate: ", comeback_rate)
    return comeback_rate

def fast_blind_rate(avg, df):
    """This function calculates the probability of player beating his own average"""
    
    count = int((avg > df["blind_split_ms"]).sum())
    faster_blind=count/len(df)
    print("FBR: ", faster_blind)
    return faster_blind

def calculate_conditional_blind_mean(avg, df, df1):
    valid_df = df1.dropna(
        subset=["blind_time", "opponent_blind_time", "stronghold_time", "opponent_stronghold_time"]
    ).copy()

    # Use actual blind-split durations
    valid_df["player_blind_split_ms"] = valid_df["stronghold_time"] - valid_df["blind_time"]
    valid_df["opponent_blind_split_ms"] = (
        valid_df["opponent_stronghold_time"] - valid_df["opponent_blind_time"]
    )

    # Ahead: player reached blind travel earlier than opponent.
    blind_avg_ahead = valid_df.loc[
        valid_df["blind_time"] < valid_df["opponent_blind_time"],
        "player_blind_split_ms"
    ]

    # Behind: opponent reached blind travel earlier than player.
    blind_avg_behind = valid_df.loc[
        valid_df["blind_time"] > valid_df["opponent_blind_time"],
        "player_blind_split_ms"
    ]

    avg_blind_ahead = blind_avg_ahead.mean() if not blind_avg_ahead.empty else 0.0
    avg_blind_behind = blind_avg_behind.mean() if not blind_avg_behind.empty else 0.0
    print("Average blind split time when player is ahead:", avg_blind_ahead)
    print("Average blind split time when player is behind:", avg_blind_behind)
    return avg_blind_ahead, avg_blind_behind

def calculate_correlation_gap_ESFR(df1):
    valid_df = df1.dropna(
        subset=["blind_time", "opponent_blind_time", "stronghold_time", "opponent_stronghold_time"]
    ).copy()

################################################################################################
def calculate_expected_time(username, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind):
    return "Hi still in development"
    
def main():
    # Reload the module so the notebook uses the latest version of get_player_match_data
    importlib.reload(db_queries)
    importlib.reload(data_collector)

    username = input("Enter the username: ")
    df = db_queries.get_blind_splits(username)
    print(df)

    if not df.empty:
        print("Data received successfully")
        df1 = db_queries.get_player_match_data(username)
        print("Columns in df1:", list(df1.columns))
        print("Shape of df1:", df1.shape)
        print(df1)
        avg,sd=get_avg_std(df)
        esfr = calculate_lead_rate(df1)
        cr = calculate_comeback_rate(df1)
        fbr = fast_blind_rate(avg,df)
        CS_score = 100 * (1-sd/avg)
        print("Consistency Score: ", CS_score)
        avg_blind_ahead, avg_blind_behind = calculate_conditional_blind_mean(avg, df, df1)
        data_collector.insert_player_blind_stats(username, avg, sd, esfr, cr, fbr, CS_score, avg_blind_ahead, avg_blind_behind)
    else:
        print("No data available to plot.")

if __name__ == '__main__':
    main()