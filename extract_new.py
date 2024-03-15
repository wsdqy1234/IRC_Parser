import os
import re
import json
import shutil
import codecs
import tarfile

# ENVIRONMENT VARIABLES -- CHANGE THESE TO FIT YOUR ENVIRONMENT
tgz_extract_directory = "./IRCdata/"
OUTFILE = os.path.join(tgz_extract_directory, "hands.json")
LOCAL_OS = "mac"  # valid values are "mac" or "pc"
# END ENVIRONMENT VARIABLES

# Code to use the local_os variable to control logic
SLASH = "/" if LOCAL_OS == "mac" else "\\"

# Global variables
pot_cats = ["f", "t", "r", "s"]  # f=flop, t=turn, r=river, s=showdown
folder_search_re = re.compile(r'\d{6}$', re.IGNORECASE)
tgz_search_re = re.compile(r'^\S*.\d{6}.tgz$', re.IGNORECASE)
valid_game_types = {"holdem", "holdem1", "holdem2", "holdem3", "holdemii", "holdempot", "nolimit"}



def extract_tgz(tgz_file, extract_dir):
    try:
        with tarfile.open(tgz_file, "r:gz") as tar:
            tar.extractall(path=extract_dir)

        # Search for relevant files after extraction
        hdb_file = None
        hroster_file = None
        pdb_file_dir = None

        for root, dirs, files in os.walk(extract_dir):
            for name in files:
                if name.lower().endswith(".hdb"):
                    hdb_file = os.path.join(root, name)
                elif name.lower().endswith(".hroster"):
                    hroster_file = os.path.join(root, name)
                elif name.lower().endswith(".pdb"):
                    pdb_file_dir = root

        if hdb_file is None or hroster_file is None or pdb_file_dir is None:
            raise FileNotFoundError("Required files not found in the extracted directory")

        return hdb_file, hroster_file, pdb_file_dir

    except (tarfile.TarError, FileNotFoundError) as e:
        print(f"Error extracting {tgz_file}: {e}")
        return None, None, None


def parse_hdb_file(hdb_file, hands, invalid_keys):
    try:
        split_filename = hdb_file.split(SLASH)
        id_prefix = split_filename[-3] + "_" + split_filename[-2] + "_"
        with open(hdb_file, "r") as hdb:
            for line in hdb:
                hand = {}
                pot_data = []
                board = []
                line_parts = line.strip("\n").split(" ")
                line_parts = [elem for elem in line_parts if elem != '']
                _id = id_prefix + line_parts[0]
                hand["_id"] = _id
                hand["game"] = split_filename[-3]
                hand["dealer"] = int(line_parts[1])
                hand["hand_num"] = int(line_parts[2])
                hand["num_players"] = int(line_parts[3])
                for lp in line_parts[4:8]:
                    pot_data.append(lp)
                for card in line_parts[8:]:
                    board.append(card)

                pots = []
                i = 0
                for p in pot_data:
                    pot = {}
                    pot["stage"] = pot_cats[i]
                    if len(p.split("/")) == 2:
                        pot["num_players"] = int(p.split("/")[0])
                        pot["size"] = int(p.split("/")[1])
                    else:
                        invalid_keys.add(_id)
                    pots.append(pot)
                    i = i + 1

                hand["pots"] = pots
                hand["board"] = board
                hands[_id] = hand
        return hands, id_prefix, invalid_keys

    except (KeyError, ValueError):
        invalid_keys.add(_id)
        return hands, id_prefix, invalid_keys


def parse_hroster_file(hroster_file, id_prefix, hands, invalid_keys):
    try:
        with open(hroster_file, "r") as hroster:
            for line in hroster:
                players = {}
                line_parts = line.strip("\n").split(" ")
                line_parts = [elem for elem in line_parts if elem != '']
                _id = id_prefix + line_parts[0]
                player_data = line_parts[2:]
                for p in player_data:
                    # If on pc replace "|" with "_" in the player's name
                    if LOCAL_OS == "pc":
                        p = re.sub(r'[|]', '_', p)
                    # end fix 1/4/16
                    player = {}
                    player["user"] = p
                    players[p] = player
                if _id in hands:
                    hands[_id]["players"] = players
                else:
                    invalid_keys.add(_id)
        return hands, invalid_keys

    except KeyError:
        invalid_keys.add(_id)
        return hands, invalid_keys


def parse_pdb_file(pdb_file, id_prefix, hands, invalid_keys):
    try:
        username = pdb_file.split(".")[-1]
        with open(pdb_file, "r") as pdb:
            for line in pdb:
                line_parts = line.strip("\n").split(" ")
                line_parts = [elem for elem in line_parts if elem != '']

                _id = id_prefix + line_parts[1]
                position = line_parts[3]

                bet_actions = []
                i = 0
                for item in line_parts:
                    bet_action = {}
                    bet_action["actions"] = []
                    if line_parts.index(item) >= 4 and line_parts.index(item) <= 7:
                        for b in item:
                            bet_action["actions"].append(b)
                        bet_action["stage"] = pot_cats[i]
                        bet_actions.append(bet_action)
                        i = i + 1
                bankroll, action, winnings = line_parts[8:11]

                player_cards = []
                if len(line_parts) == 13:
                    for card in line_parts[11:13]:
                        player_cards.append(card)

                if _id in hands:
                    if _id not in invalid_keys:
                        if username in hands[_id]["players"]:
                            hands[_id]["players"][username]["bets"] = bet_actions
                            hands[_id]["players"][username]["bankroll"] = int(bankroll)
                            hands[_id]["players"][username]["action"] = int(action)
                            hands[_id]["players"][username]["winnings"] = int(winnings)
                            hands[_id]["players"][username]["pocket_cards"] = player_cards
                            hands[_id]["players"][username]["pos"] = int(position)
                        else:
                            invalid_keys.add(_id)
                else:
                    invalid_keys.add(_id)
        return hands, invalid_keys

    except (IndexError, KeyError, ValueError):
        invalid_keys.add(_id)
        return hands, invalid_keys


def loop_pdb_files(pdb_file_directory, hands_col, id_prefix, invalid_keys):
    for root, _, files in os.walk(pdb_file_directory):
        for file in files:
            if file.endswith(".pdb"):
                pdb_file = os.path.join(root, file)
                hands_col, invalid_keys = parse_pdb_file(pdb_file, id_prefix, hands_col, invalid_keys)
    return hands_col, invalid_keys


def write_to_json(hands, outfile):
    with codecs.open(outfile, "w", "utf-8") as outfile:
        outfile.write(json.dumps(list(hands.values()), sort_keys=True, indent=4, separators=(",", ": ")))
        outfile.close()
    return


def process_data(tgz_directory):
    for root, _, files in os.walk(tgz_directory):
        for tgz_file in files:
            if tgz_search_re.match(tgz_file):
                hdb_file, hroster_file, pdb_file_dir = extract_tgz(os.path.join(root, tgz_file), tgz_extract_directory)
                if hdb_file is not None and hroster_file is not None and pdb_file_dir is not None:
                    hands = {}
                    invalid_keys = set()
                    hands, id_prefix, invalid_keys = parse_hdb_file(hdb_file, hands, invalid_keys)
                    hands, invalid_keys = parse_hroster_file(hroster_file, id_prefix, hands, invalid_keys)
                    hands, invalid_keys = loop_pdb_files(pdb_file_dir, hands, id_prefix, invalid_keys)

                    if len(invalid_keys) > 0:
                        print(f"WARNING: {len(invalid_keys)} invalid keys found and ignored in processing.")
                        print("Invalid keys:", invalid_keys)

                    if len(hands) > 0:
                        write_to_json(hands, OUTFILE)
                        print(f"Successfully processed the data from {tgz_file} and saved to {OUTFILE}")
                    else:
                        print(f"No valid hands found in the data from {tgz_file}.")
                else:
                    print(f"Error in extracting required files from {tgz_file}.")

# Execution starts here
process_data(".")