import requests
import csv
import itertools
from difflib import get_close_matches
import sys

# CHANGE THESE VALUES 👇
USERNAME = "dantenv"
LEAGUE_ID = "1235875187103109120"
ADP_CSV_PATH = "preseason_adp.csv"

MIN_ADP_GAIN = 5.0  # minimum net ADP improvement to suggest trades

# Load ADP CSV into a dict (name -> adp)
def load_adp(csv_path):
    adp_map = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            player_name = row['Name'].strip()
            try:
                adp_value = float(row['ADP'])
                adp_map[player_name] = adp_value
            except ValueError:
                continue
    return adp_map

# Helper: fuzzy match player name from Sleeper to ADP names
def match_player_name(name, adp_map_keys, cutoff=0.8):
    matches = get_close_matches(name, adp_map_keys, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return None

def print_rosters_with_adp(rosters, user_map, players_data, adp_data):
    print("\n=== League Rosters with ADP ===")
    adp_names = adp_data.keys()

    for roster in rosters:
        owner_id = roster["owner_id"]
        owner_name = user_map.get(owner_id, "Unknown Owner")
        player_ids = roster.get("players", [])

        print(f"\n🏈 Team: {owner_name} ({owner_id})")
        for pid in player_ids:
            player = players_data.get(pid, {})
            name = player.get("full_name", "Unknown")
            pos = player.get("position", "N/A")
            team = player.get("team", "FA")

            # Try exact match
            adp = adp_data.get(name)
            # If no exact match, try fuzzy matching
            if adp is None:
                matched_name = match_player_name(name, adp_names)
                if matched_name:
                    adp = adp_data[matched_name]

            adp_str = f"{adp:.2f}" if adp is not None else "N/A"
            print(f" - {name} ({pos} - {team}) | ADP: {adp_str}")

def suggest_trades(my_roster, other_rosters, players_data, adp_data, min_adp_gain=MIN_ADP_GAIN):
    print(f"\n=== Trade Suggestions (Min Net Gain: +{min_adp_gain} ADP) ===\n")

    adp_names = adp_data.keys()

    # Build your players with ADP
    my_players = []
    for pid in my_roster:
        player = players_data.get(pid, {})
        name = player.get("full_name", "Unknown")
        adp = adp_data.get(name)
        if adp is None:
            matched_name = match_player_name(name, adp_names)
            if matched_name:
                adp = adp_data[matched_name]
        if adp is not None:
            my_players.append({"id": pid, "name": name, "adp": adp})

    for roster in other_rosters:
        opponent_id = roster["owner_id"]
        opponent_players = []
        for pid in roster.get("players", []):
            player = players_data.get(pid, {})
            name = player.get("full_name", "Unknown")
            adp = adp_data.get(name)
            if adp is None:
                matched_name = match_player_name(name, adp_names)
                if matched_name:
                    adp = adp_data[matched_name]
            if adp is not None:
                opponent_players.append({"id": pid, "name": name, "adp": adp})

        # 1-for-1 trades
        for my_p in my_players:
            for opp_p in opponent_players:
                adp_gain = my_p["adp"] - opp_p["adp"]
                if adp_gain >= min_adp_gain:
                    print(f"🟢 1-for-1: Trade {my_p['name']} (ADP: {my_p['adp']:.2f}) → {opp_p['name']} (ADP: {opp_p['adp']:.2f}) | Net Gain: +{adp_gain:.2f}")

        # 2-for-1 trades
        for my_combo in itertools.combinations(my_players, 2):
            my_total_adp = sum(p["adp"] for p in my_combo)
            my_names = [p["name"] for p in my_combo]
            for opp_p in opponent_players:
                adp_gain = my_total_adp - opp_p["adp"]
                if adp_gain >= min_adp_gain:
                    combo_str = f"{my_names[0]} + {my_names[1]}"
                    print(f"🟢 2-for-1: Trade {combo_str} (ADP total: {my_total_adp:.2f}) → {opp_p['name']} (ADP: {opp_p['adp']:.2f}) | Net Gain: +{adp_gain:.2f}")

def main():
    adp_data = load_adp(ADP_CSV_PATH)

    # Sleeper API requests
    user_res = requests.get(f"https://api.sleeper.app/v1/user/{USERNAME}")
    user_res.raise_for_status()
    user_id = user_res.json()["user_id"]

    users_res = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/users")
    users_res.raise_for_status()
    users = users_res.json()
    user_map = {u["user_id"]: u["display_name"] for u in users}

    rosters_res = requests.get(f"https://api.sleeper.app/v1/league/{LEAGUE_ID}/rosters")
    rosters_res.raise_for_status()
    rosters = rosters_res.json()

    players_res = requests.get("https://api.sleeper.app/v1/players/nfl")
    players_res.raise_for_status()
    players_data = players_res.json()

    # Print all rosters with ADP
    print_rosters_with_adp(rosters, user_map, players_data, adp_data)

    # Find your roster and others
    my_roster = None
    other_rosters = []
    for roster in rosters:
        if roster["owner_id"] == user_id:
            my_roster = roster.get("players", [])
        else:
            other_rosters.append(roster)

    if not my_roster:
        print("⚠️ Could not find your roster. Check USERNAME and LEAGUE_ID.")
        return

    # Suggest trades
    suggest_trades(my_roster, other_rosters, players_data, adp_data)

    # Open output files
    with open("rosters_with_adp.txt", "w", encoding="utf-8") as roster_file, \
         open("trade_suggestions.txt", "w", encoding="utf-8") as trades_file:

        # Save original stdout
        original_stdout = sys.stdout

        # Redirect print to rosters file and call roster print function
        sys.stdout = roster_file
        print_rosters_with_adp(rosters, user_map, players_data, adp_data)

        # Restore stdout before next print redirect
        sys.stdout = original_stdout
        print("Rosters printed to rosters_with_adp.txt")

        # Redirect print to trades file and call trade suggestion function
        sys.stdout = trades_file
        suggest_trades(my_roster, other_rosters, players_data, adp_data)

        # Restore stdout again
        sys.stdout = original_stdout
        print("Trade suggestions printed to trade_suggestions.txt")

if __name__ == "__main__":
    main()

