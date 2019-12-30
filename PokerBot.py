# PokerBot.py

import os
import discord
from discord.ext import commands
from Scripts import seleniumScraper

PLAYER_IDENTIFIERS = {'\'', '`', '~', '!', '@', '#', '$', '%', '^', '&', '*', '?'}
# get tokens
CURRENT_GAME_LINK = None
TOKEN = ""
dirName = os.getcwd()
CONFIG_FILE = os.path.join(dirName, 'config.txt')
SCORES_FILE = os.path.join(dirName, 'scores.txt')

config = open(CONFIG_FILE, encoding='utf-8', mode='r')

for line in config:
    if line.startswith("token"):
        tmp = line.split("=")
        TOKEN = tmp[1].strip()
config.close()

# instance of Client()
Client = discord.Client()
# bot prefix it responds to
bot_prefix = "$"
client = commands.Bot(command_prefix=bot_prefix)


# #####COMMANDS######

# ping command
@client.command(pass_context=True)
async def ping(ctx):
    await client.say("Pong!")


# logout command
@client.command(pass_context=True)
async def logout(ctx):
    await client.say("Going offline.")
    print("Bot going offline")
    await client.logout()


# list all commands command
@client.command(pass_context=True)
async def commands(ctx):
    # UPDATE THIS LIST
    await client.say(
        f"Poker related commands:\n{bot_prefix}start: [no arguments]Generates a new poker game and returns a link\n"
        f"{bot_prefix}end: [no arguments]Updates leader boards and stops tracking the las tgame\n"
        f"{bot_prefix}Display the leader board\n{bot_prefix}get_score[player / player_identifier]"
        f"(noargs = poster's score): More specific individual player stats\n"
        f"{bot_prefix}add[player_name][discord_id][player_identifier]"
        f"(noargs = poster's discord id): add a player to leader board tracking\n")


# placeholder for the let it go meme
@client.command(pass_context=True)
async def let_go(ctx):
    await client.say("https://i.imgur.com/vKcJOHu.jpg")


@client.command(pass_context=True)
async def hulk(ctx):
    await client.say("Hulk would have killed everybody :BibleThump:")


@client.command(pass_context=True)
async def add(ctx, player_iden, discord_name=None):
    # format in the text file (line start)PLAYER_IDENTIFIER,Discord_author,score,rounds won
    games_won = 0
    if discord_name is None:
        discord_name = ctx.message.author
    starting_score = 0
    with open(SCORES_FILE, encoding='utf-8', mode='r+') as f:
        # check if player identifier/discord_name is already in use
        used_identifiers = set()
        used_discord_names = []
        for entry in f:
            entry = entry.split(',')
            used_identifiers.add(entry[0])
            used_discord_names.append(entry[1])
        if player_iden in used_identifiers:
            await client.say(f"Identifier already in use. Choose from: {PLAYER_IDENTIFIERS - used_identifiers}")
        elif discord_name in used_discord_names:
            await client.say("Discord ID already in use.")
        elif discord_name is None:
            await client.say(f"Added {discord_name} with identifier "
                             f"{player_iden} to the leader board with a score of {starting_score}")
            f.write(f"{player_iden},{discord_name},{starting_score}\n")
        elif player_iden[0] not in PLAYER_IDENTIFIERS:
            await client.say(f"Please use a valid player identifier from {PLAYER_IDENTIFIERS}")
        elif discord_name is not None:
            await client.say(f"Added {discord_name} with identifier "
                             f"{player_iden} to the leader board with a score of {starting_score}")
            f.write(f"{player_iden},{discord_name},{starting_score},{games_won}\n")


# Info Poker Start Command
@client.command(pass_context=True)
async def start(ctx):
    global CURRENT_GAME_LINK
    CURRENT_GAME_LINK = seleniumScraper.start_poker_game()  # this has significant delay
    await client.say(f"Starting poker game at: {CURRENT_GAME_LINK}")


# Poker End Command
@client.command(pass_context=True)
async def end(ctx):
    global CURRENT_GAME_LINK
    if CURRENT_GAME_LINK is not None:
        await client.say(f"Poker game on: {CURRENT_GAME_LINK} over, scores recorded")

    else:
        await client.say("No poker game active. Use $start to generate a link.")

    CURRENT_GAME_LINK = None


# Poker scores
@client.command(pass_context=True)
async def scores(ctx):
    response = f"Current leader board:\n"
    with open(SCORES_FILE, encoding='utf-8', mode='r') as f:
        leader_board = []
        for i in f:
            i = i.split(',')
            newdict = dict(id=i[1], score=int(i[2]), identifier=i[0], games_won=i[3])
            leader_board.append(newdict)
    # Sort scores
    print(leader_board)
    leader_board = sorted(leader_board, key=lambda x: x['score'], reverse=True)
    print(leader_board)
    for i in leader_board:
        temp = f"{i['id']}:{i['score']}\n"
        response += temp
    await client.say(response)


# #######EVENTS########

# Called when the bot connects to the server
@client.event
async def on_ready():
    print("Bot Online!")
    print("Name: {}".format(client.user.name))
    print("ID: {}".format(client.user.id))
    await client.change_presence(game=discord.Game(name='type $commands'))


# #######POKER GAME FUNCTIONS######### #
def parse_game_log(log_lines):
    trackable_players = get_players()

    for i in log_lines:
        for player in trackable_players:
            if i['player'] == player['identifier']:
                score_change = 0
                # determine valid player stack changes
                if i['action_type'] == "win":      # positive stack changes
                    score_change = i['stack_change']
                    player['games_won'] += 1

                elif i['action_type'] == 'calls':  # negative stack changes
                    if player['last_action']['action_type'] == 'blind':
                        if i['betting_cycle'] != player['last_action']['betting_cycle']:
                            score_change = i['stack_change'] * -1
                        else:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                    elif player['last_action']['action_type'] == 'calls':    # case 3
                        # check if new betting round has began or its looped
                        if i['betting_cycle'] == player['last_action']['betting_cycle']:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                        else:
                            score_change = i['stack_change'] * -1
                    elif player['last_action']['action_type'] == 'raises':
                        if i['betting_cycle'] == player['last_action']['betting_cycle']:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                        else:
                            score_change = i['stack_change'] * -1
                    else:
                        score_change = i['stack_change'] * -1

                elif i['action_type'] == 'raises':
                    if player['last_action']['action_type'] == 'blind':
                        if i['betting_cycle'] != player['last_action']['betting_cycle']:
                            score_change = i['stack_change'] * -1
                        else:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                    elif player['last_action']['action_type'] == 'calls':    # case 3
                        # check if new betting round has began or its looped
                        if i['betting_cycle'] == player['last_action']['betting_cycle']:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                        else:
                            score_change = i['stack_change'] * -1
                    elif player['last_action']['action_type'] == 'raises':
                        if i['betting_cycle'] == player['last_action']['betting_cycle']:
                            score_change = (i['stack_change'] - int(player['last_action']['stack_change'])) * -1
                        else:
                            score_change = i['stack_change'] * -1
                    else:
                        score_change = i['stack_change'] * -1
                elif i['action_type'] == 'blind':       # case 1
                    score_change = i['stack_change'] * -1
                player['score'] = player['score'] + score_change
                print(player['score'], player['id'], i['action_type'], (player['last_action']['action_type']), i['betting_cycle'], player['last_action']['betting_cycle'])
                player['last_action'] = i
    return trackable_players


def get_players():
    with open(SCORES_FILE, encoding='utf-8', mode='r') as f:
        players = []
        for i in f:
            i = i.split(',')
            # initialize betting cycles
            newdict = dict(id=i[1], score=int(i[2]), identifier=i[0], games_won=int(i[3]), last_action=dict(action_type=None, betting_cycle=1))
            players.append(newdict)
    return players


def update_scores(new_scores):
    with open(SCORES_FILE, encoding='utf-8', mode='r+') as f:
        f.truncate()
        for player in new_scores:
            f.write(f"{player['identifier']},{player['id']},{player['score']},{player['games_won']}\n")


client.run(TOKEN)
