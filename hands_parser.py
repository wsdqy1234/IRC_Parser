import os
import json
from ColorPrint import GREEN, RED, RESET
from pprint import pprint

ROLE_LIST = ['small blind', 'big blind', 'button']
STAGE_LIST = {
    "p": "preflop",
    "f": "flop",
    "t": "turn",
    "r": "river",
    "s": "showdown"
}
ACTION_LIST = {
    '-': 'no action',
    'B': 'blind bet',
    'f': 'fold',
    'k': 'check',
    'b': 'bet',
    'c': 'call',
    'r': 'raise',
    'A': 'all-in',
    'Q': 'quits game',
    'K': 'kicked from game'
}


def get_role_position(pos, num_player):
    """
    return: {'position': 2, 'role': 'big blind'}
    """
    res = dict()
    res['position'] = pos # start from 1
    if num_player == 2:
        res['role'] = ROLE_LIST[pos-1]
    else:
        res['role'] = ROLE_LIST[pos-1] if pos < 3 else 'position ' + str(pos)
        
    return res


def get_bankroll_for_all_roles(input_dict):
    """
    return: {'bankroll': {'small blind': 80933, 'position 3': 32088, 'big blind': 26880, 'position 6': 13167, 'position 5': 32709, 'position 4': 76432}}
    """
    players = input_dict['players']
    num_players = input_dict['num_players']
    res_k = dict()
    # for k,v in players.items():
    #     temp_dict = get_role_position(k, num_players)
    #     res_k[temp_dict['role']] = v['bankroll']
    for player in players:
        temp_dict = get_role_position(player['pos'], num_players)
        res_k[temp_dict['role']] = player['bankroll']
    return {'bankroll': res_k}


def get_user_from_input_dict_by_pos(pos, input_dict):
    players = input_dict['players']
    for player in players:
        if player['pos'] == pos:
            return player

    raise KeyError


def get_context(pos, stage, input_dict):
    """
    return: 
    {'num_players': 6, 'position': 1, 'role': 'small blind', 'bankroll': {'small blind': 80933, 'position 3': 32088, 'big blind': 26880, 'position 6': 13167, 'position 5': 32709, 'position 4': 76432}, 'pocket_cards': ['7s', 'Js'], 'board': []}
    """
    res = dict()
    res['num_players'] = input_dict['num_players']
    res.update(get_role_position(pos, res['num_players']))
    res.update(get_bankroll_for_all_roles(input_dict))
    res['pocket_cards'] = get_user_from_input_dict_by_pos(pos, input_dict)['pocket_cards']
    if stage == 'p':
        res['board'] = []
    elif stage == 'f':
        res['board'] = input_dict['board'][:4]
    elif stage == 't':
        res['board'] = input_dict['board'][:5]
    else:
        res['board'] = input_dict['board']
    return res



def bets_to_actions(bets, hand):
    actions = []
    stages_new = ['p', 'f', 't', 'r']
    
    context_list = []
    
    for j in range(len(stages_new)):
        for round_id in range(len(bets[0][j])):
            for i in range(len(bets)):
                if round_id >= len(bets[i][j]["actions"]):
                    continue
                else:
                    # actions.append((i+1, stages_new[j], bets[i][j]["actions"][round_id])) # (player_id, stage, action), i.e., (1, 'f', 'B')
                    actions.append(
                        (get_role_position(i+1, len(bets))["role"],  STAGE_LIST[stages_new[j]], ACTION_LIST[bets[i][j]["actions"][round_id]])
                    )
                    context_list.append(get_context(i+1, stages_new[j], hand))
                
    return actions, context_list


def acts_to_history_next(actions):
    history_acts_list = []
    next_acts_list = []
    for i in range(len(actions)):
        # idx begin from 0
        history_acts = actions[:i]
        next_act = actions[i]
        
        history_actions = {}
        for i, act in enumerate(history_acts):
            history_actions[str(i+1)] = {
                "role": act[0],
                "stage": act[1],
                "action": act[2]
            }
            
        next_action = {
            "role": next_act[0],
            "stage": next_act[1],
            "action": next_act[2]
        }
        history_acts_list.append(history_actions)
        next_acts_list.append(next_action)
        
    return history_acts_list, next_acts_list


def browse(hand):
    print('{}{:>7}{} : {}'.format(GREEN, 'time', RESET, hand['time']), end='')
    print('{}{:>14}{} : {}'.format(GREEN, 'id', RESET, hand['id']))
    print('{}{:>7}{} : {}'.format(GREEN, 'board', RESET, hand['board']))
    print('{}{:>7}{} : '.format(GREEN, 'pots', RESET), end='')
    pots = []
    for stage in ['f', 't', 'r', 's']:
        p = [h for h in hand['pots'] if h['stage'] == stage][0]
        pots.append((p['num_players'], p['size']))
    print(pots)
    print('{}{:>7}{} : '.format(GREEN, 'players', RESET))
    hand['players'] = {player['pos']: player for player in hand['players']}
    for pos in range(1, hand['num_players'] + 1):
        description = hand['players'][pos].copy()
        user = description['user']
        del description['user'], description['pos']
        print('{}{:^60}{}'.format(RED, user + ' (#' + str(pos) + ')', RESET))
        pprint(description)
        print(('· ' if pos < hand['num_players'] else '##') * 30)
    return


if __name__ == "__main__":
    try:
        with open('hands_valid.json', 'r') as f:
            cnt = 1
            for line in f:
                hand = json.loads(line)
                
                num_players = hand["num_players"]
                board = hand["board"]
                pots = [] # 如果pots中的pot为（0，0），意味着有人All in，需要到Turn stage才会显示真实pot
                stages = ['f', 't', 'r', 's']
                
                for stage in stages:
                    p = [h for h in hand['pots'] if h['stage'] == stage][0]
                    pots.append((p['num_players'], p['size']))
                
                hand_copy = hand.copy()
                # browse(hand_copy)
                
                hand['players'] = {player['pos']: player for player in hand['players']} # 调整playid成为德扑游戏内id
                bets = []
                for pos in range(1, num_players+1):
                    player = hand['players'][pos]
                    bets.append(player["bets"])
                
                ## context & actions_history & next_action
                try:
                    actions, context_list = bets_to_actions(bets, hand_copy)
                    history_acts_list, next_acts_list = acts_to_history_next(actions)
                except:
                    continue

                # 这里创建一个文件夹，每一万个json文件保存到一个文件夹里，避免打不开/不好处理/以及不知道idx多少的时候报错的问题
                num_save_folder = 10000
                folder_idx = (cnt-1) // num_save_folder
                output_base_dir = "Parser"
                output_folder_path = os.path.join(output_base_dir, f'parser_{folder_idx*num_save_folder+1}-{(folder_idx+1)*num_save_folder}')
                os.makedirs(output_folder_path, exist_ok=True)
                
                output_file_path = os.path.join(output_folder_path, f"hands_valid_{cnt}.json")
                with open(output_file_path,'w') as json_file:
                    for i,_ in enumerate(context_list):
                        tmp = {
                            "context": context_list[i],
                            "action_history": history_acts_list[i],
                            "next_action": next_acts_list[i]
                        }
                        json_file.write(json.dumps(tmp)+ "\n")
                
                cnt+=1
        print("finished")
                
                
    except:
        print("Error idx:{}".format(cnt))