# This Module consists the code behind Nether terrain navigation Analytic plus the algorithm of the NDI(Nether difficulty index)

#Dependencies
import requests
import os 
import dotenv

dotenv.load_dotenv("credentials.env")

MCSR_BASE_URL = os.getenv("MCSR_API_ENDPOINT", "https://api.mcsrranked.com").rstrip("/")


def calculate_time_to_bastin(matchID):
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

    print(data)
    return data


calculate_time_to_bastin("10761504")

