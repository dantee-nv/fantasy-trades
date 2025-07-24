#Just a test
import requests
import csv
import itertools
from difflib import get_close_matches

def load_adp(csv_path="preseason_adp.csv"):
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

def match_player_name(name, adp_map_keys, cutoff=0.8):
    matches = get_close_matches(name, adp_map_keys, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return None

def get_rosters_with_adp(rosters, user_map, players_data, adp_data):
    adp_names = adp_data.keys()
    lines = []
    for roster in rosters:
        owner_id = roster["owner_id"]
        owner_name = user_map.get(owner_id, "Unknown Owner")
        player_ids = roster.get("players", [])
        lines.append(f"🏈 Team: {owner_name} ({owner_id})")
        for pid in player_ids:
            player = players_data.get(pid, {})
            name = player.get("full_name", "Unknown")
            pos = player.get("position", "N/A")
            team = player.get("team", "FA")
            adp = adp_data.get(name)
            if adp is None:
                matched_name = match_player_name(name, adp_names)
                if matched_name:
                    adp = adp_data[matched_name]
            adp_str = f"{adp:.2f}" if adp is not None else "N/A"
            lines.append(f" - {name} ({pos} - {team}) | ADP: {adp_str}")
        lines.append("")  # blank line between teams
    return "\n".join(lines)

def get_trade_suggestions(my_roster, other_rosters, players_data, adp_data, min_adp_gain=5.0):
    trades = []
    adp_names = adp_data.keys()

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

        for my_p in my_players:
            for opp_p in opponent_players:
                adp_gain = my_p["adp"] - opp_p["adp"]
                if adp_gain >= min_adp_gain:
                    trades.append(f"🟢 1-for-1: Trade {my_p['name']} (ADP: {my_p['adp']:.2f}) → {opp_p['name']} (ADP: {opp_p['adp']:.2f}) | Net Gain: +{adp_gain:.2f}")

        for my_combo in itertools.combinations(my_players, 2):
            my_total_adp = sum(p["adp"] for p in my_combo)
            my_names = [p["name"] for p in my_combo]
            for opp_p in opponent_players:
                adp_gain = my_total_adp - opp_p["adp"]
                if adp_gain >= min_adp_gain:
                    combo_str = " + ".join(my_names)
                    trades.append(f"🟢 2-for-1: Trade {combo_str} (ADP total: {my_total_adp:.2f}) → {opp_p['name']} (ADP: {opp_p['adp']:.2f}) | Net Gain: +{adp_gain:.2f}")

    trades.sort(key=lambda t: float(t.split("+")[-1]), reverse=True)  # crude sort by gain

    if trades:
        return "=== Trade Suggestions Sorted by Net ADP Gain ===\n" + "\n".join(trades)
    else:
        return "No trades found with the specified ADP gain."

def run_trade_suggestions(username, league_id):
    try:
        adp_data = load_adp()

        user_res = requests.get(f"https://api.sleeper.app/v1/user/{username}")
        user_res.raise_for_status()
        user_id = user_res.json()["user_id"]

        users_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/users")
        users_res.raise_for_status()
        users = users_res.json()
        user_map = {u["user_id"]: u["display_name"] for u in users}

        rosters_res = requests.get(f"https://api.sleeper.app/v1/league/{league_id}/rosters")
        rosters_res.raise_for_status()
        rosters = rosters_res.json()

        players_res = requests.get("https://api.sleeper.app/v1/players/nfl")
        players_res.raise_for_status()
        players_data = players_res.json()

        rosters_text = get_rosters_with_adp(rosters, user_map, players_data, adp_data)

        my_roster = None
        other_rosters = []
        for roster in rosters:
            if roster["owner_id"] == user_id:
                my_roster = roster.get("players", [])
            else:
                other_rosters.append(roster)

        if not my_roster:
            trades_text = "⚠️ Could not find your roster. Check username and league ID."
        else:
            trades_text = get_trade_suggestions(my_roster, other_rosters, players_data, adp_data)

        return rosters_text, trades_text

    except Exception as e:
        error_msg = f"Error: {e}"
        return error_msg, error_msg

adp_data = load_adp("preseason_adp.csv")
print(f"Loaded ADP entries: {len(adp_data)}")