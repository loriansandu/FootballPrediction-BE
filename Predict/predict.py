import copy
import difflib
import json
import pickle

from utils import transform_all_values_to_string_from_dict, get_h2h
from consts import *
from pickle import load
from datetime import date, timedelta

import cfscrape
import numpy as np
import pandas as pd
import random
import math

import requests
from consts import MODEL_COLUMNS
from unidecode import unidecode

venue_code = 1

columns = MODEL_COLUMNS


def get_team_id(team):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"

    querystring = {"name": team}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    team_id = response.json()["response"][0]["team"]["id"]
    return team_id


def get_fixtures(team):
    team_id = get_team_id(team)
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

    querystring = {"team": team_id, "next": "10"}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)

    fixtures = response.json()["response"]
    return fixtures


def check_if_game_exists(away_team, home_team_next_games):
    return [game["fixture"]["id"] for game in home_team_next_games if away_team == game["teams"]["away"]["name"]]


def get_game_id(team, opponent):
    fixtures = get_fixtures(team)
    game_id = check_if_game_exists(opponent, fixtures)
    if not game_id:
        raise Exception("Game doesn't exist")
    return game_id


def get_odds(game_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"

    querystring = {"fixture": game_id, "bookmaker": 8}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    try:
        odds = response.json()["response"][0]["bookmakers"][0]["bets"][0]["values"]
    except Exception:
        raise Exception("Couldn't find odds for this game!")

    return odds[0]["odd"], odds[1]["odd"], odds[2]["odd"]


def poisson_prob(k, lamb):
    """
    Returns the probability of k events occurring in a Poisson distribution
    with mean lamb.
    """
    return (lamb ** k * math.exp(-lamb)) / math.factorial(k)


def predict_value(expected_penalties):
    """
    Predicts the number of penalties for a team in a football game
    based on a Poisson distribution with the given expected number
    of penalties per game.
    """
    num_penalties = 0
    prob_threshold = random.uniform(0, 1)
    prob_sum = poisson_prob(num_penalties, expected_penalties)
    while prob_sum < prob_threshold:
        num_penalties += 1
        prob_sum += poisson_prob(num_penalties, expected_penalties)
    return num_penalties


def get_index_of_StandardStats_Table(data):
    for item in list(data):
        if 'Squad Standard Stats' in item:
            return data[item]
    return 0


def get_index_of_Shooting_Table(data):
    for item in list(data):
        if 'Squad Shooting' in item:
            return data[item]
    return 0


def get_tables_index(data):
    return [
        0,
        get_index_of_StandardStats_Table(data),
        get_index_of_Shooting_Table(data),
        get_index_of_Squad_Miscellaneous_Table(data)
    ]


def get_index_of_Squad_Miscellaneous_Table(data):
    for item in list(data):
        if 'Squad Miscellaneous Stats' in item:
            return data[item]
    return 0


def getStats(team, opponent, competition_name):
    competition_name = unidecode(competition_name)
    if competition_name in SUPPORTED_LEAGUES.keys():
        teams = SUPPORTED_LEAGUES[competition_name]['teams']
        link = SUPPORTED_LEAGUES[competition_name]['data_links']
        tables = get_tables_index(SUPPORTED_LEAGUES[competition_name]['tables'])
        print(tables)
    else:
        raise Exception("Predictions for this competition are not supported yet!")
    try:
        team_name_copy = team
        opponent_name_copy = opponent
        team_id = get_team_id(team_name_copy)
        opponent_id = get_team_id(opponent_name_copy)
        B365T, B365D, B365O = get_odds(get_game_id(team_name_copy, opponent_name_copy))
        wins, losses, draws = get_h2h(team_id, opponent_id, str(date.today() - timedelta(days=1)), competition_name)
    except Exception as e:
        raise Exception(str(e))
    try:
        team = difflib.get_close_matches(team, teams, cutoff=0.3)[0]
        opponent = difflib.get_close_matches(opponent, teams, cutoff=0.3)[0]
        print(team, opponent)
    except IndexError:
        raise Exception("Wrong team names")
    try:
        scraper = cfscrape.create_scraper()
        data = scraper.get(link).content
        team_data, opponent_data = getData(data, team, opponent, tables)
    except Exception as e:
        raise Exception(str(e))
    team_data.update({
        "B365T": B365T,
        "B365D": B365D,
        "B365O": B365O,
        "wins": wins,
        "losses": losses,
        "draws": draws
    })
    opponent_data.update({
        "B365T": B365O,
        "B365D": B365D,
        "B365O": B365T,
        "wins": losses,
        "losses": wins,
        "draws": draws
    })
    return team_data, opponent_data


def getPrediction(team, opponent, competition):
    team_data, opponent_data = getStats(team, opponent, competition)
    print(team_data, opponent_data)
    if team_data is None or opponent_data is None:
        raise Exception("Data error")

    scaler = load(open('models/scaler/scaler.pkl', 'rb'))
    loaded_model = pickle.load(open('models/pkl/LogisticRegression_model.pkl', 'rb'))
    team_test_data = copy.deepcopy(team_data)
    team_test_data = updateTestData(opponent_data, team_test_data)
    scaled_features = scaler.transform(team_test_data)
    team_test_data[columns] = scaled_features
    team_prediction = loaded_model.predict(team_test_data)
    team_prediction_percentages = loaded_model.predict_proba(team_test_data)

    opponent_test_data = copy.deepcopy(opponent_data)
    opponent_test_data = updateTestData(team_data, opponent_test_data)
    opponent_test_data["venue_code"] = int(not venue_code)
    scaled_features = scaler.transform(opponent_test_data)
    opponent_test_data[columns] = scaled_features
    opponent_prediction = loaded_model.predict(opponent_test_data)
    opponent_prediction_percentages = loaded_model.predict_proba(opponent_test_data)
    # result = [{k: int(v) for k, v in d.items()} for d in map(lambda x: dict(x), listD)]
    # print(result)
    return np.mean([team_prediction_percentages, opponent_prediction_percentages[:, [2, 1, 0]]],
                   axis=0), transform_all_values_to_string_from_dict(
        team_data), transform_all_values_to_string_from_dict(opponent_data)


def updateTestData(opponent_data, team_test_data):
    team_test_data.update(
        {"opponent points": opponent_data["points"], "opponent last_3_games": opponent_data["last_3_games"],
         "venue_code": venue_code})
    team_test_data["team points"], team_test_data["team last_3_games"] = team_test_data.pop(
        "points"), team_test_data.pop("last_3_games")
    team_test_data.pop("games_played")
    team_test_data.pop("name")
    team_test_data = pd.DataFrame(team_test_data, index=[0])
    team_test_data = team_test_data[columns]
    return team_test_data


def getBets(team, opponent, competition_link):
    url = f"https://odds.p.rapidapi.com/v4/sports/{competition_link}/odds"
    querystring = {"regions": "us", "oddsFormat": "decimal", "markets": "h2h,spreads", "dateFormat": "iso"}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "odds.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    json_object = json.loads(response.text)

    B365T, B365O, B365D = None, None, None
    matches = [item for item in json_object if (item["home_team"] in team) or team in item["home_team"]]
    bookmakers = [bookmaker for match in matches for bookmaker in match["bookmakers"] if
                  bookmaker["key"] == "unibet_us"]
    outcomes = [outcome for bookmaker in bookmakers for market in bookmaker["markets"] if market.get("outcomes") for
                outcome
                in market["outcomes"]]
    for outcome in outcomes:
        if outcome["name"] in team or team in outcome["name"]:
            B365T = outcome["price"]
        elif outcome["name"] in opponent or opponent in outcome["name"]:
            B365O = outcome["price"]
        else:
            B365D = outcome["price"]

    return B365T, B365D, B365O


def getData(data1, team, opponent, tables_index):
    # # data = pd.read_html(data1)[21]
    #
    # data = pd.read_html(data1)[8]
    # data = changeColumns(data)
    # data = data.set_index(['Squad'])
    # if team_data.empty:
    #     raise Exception("Couldn't find table with crdR 2crdy og")
    # all_stats_team.update({
    #     # 'crdr': predict_value(team_data.iloc[0]['CrdR'] / team_games_played),
    #     #   '2crdy': predict_value(team_data.iloc[0]['2CrdY'] / team_games_played),
    #     #   'og': predict_value(team_data.iloc[0]['OG'] / team_games_played)
    #     'crdr': 0,
    #     '2crdy': 0,
    #     'og': 0
    # })
    # all_stats_opponent.update({
    #     # 'crdr': predict_value(team_data.iloc[0]['CrdR'] / team_games_played),
    #     #   '2crdy': predict_value(team_data.iloc[0]['2CrdY'] / team_games_played),
    #     #   'og': predict_value(team_data.iloc[0]['OG'] / team_games_played)
    #     'crdr': 0,
    #     '2crdy': 0,
    #     'og': 0
    # })
    data_tables = tables_index
    counter = 0

    for table_index in data_tables:
        data = pd.read_html(data1)[table_index]
        if table_index != 0:
            data = changeColumns(data)
        data = data.set_index(['Squad'])
        if team in data.index and opponent in data.index:
            team_data, opponent_data = data.loc[team], data.loc[opponent]
        else:
            data = pd.read_html(data1)[2]
            data = data.set_index(['Squad'])
            team_data, opponent_data = data.loc[team], data.loc[opponent]
        if team_data.empty or opponent_data.empty:
            raise Exception(f"Couldn't find table at index {table_index}")
        if counter == 0:
            try:
                all_stats_team, team_games_played = getPointsGamesPlayedForm(team, team_data)
                all_stats_opponent, opponent_games_played = getPointsGamesPlayedForm(opponent, opponent_data)
            except Exception as e:
                raise Exception(str(e))
        elif counter == 1:
            try:
                addPoss(all_stats_team, team_data)
                addPoss(all_stats_opponent, opponent_data)
            except Exception as e:
                raise Exception(str(e))
        if counter == 2:
            try:
                addShSotFkPkPkatt(all_stats_team, team_data, team_games_played)
                addShSotFkPkPkatt(all_stats_opponent, opponent_data, opponent_games_played)
            except Exception as e:
                raise Exception(str(e))
        elif counter == 3:
            keys = ['crdr', '2crdy', 'og']
            values = [0, 0, 0]
            all_stats_team.update(dict(zip(keys, values)))
            all_stats_opponent.update(dict(zip(keys, values)))
        counter += 1
    return all_stats_team, all_stats_opponent


def addShSotFkPkPkatt(all_stats_team, team_data, team_games_played):
    sh90 = 0
    sot90 = 0
    fk = 0
    if 'Sh/90' in team_data.index:
        sh90 = team_data['Sh/90']
    if 'SoT/90' in team_data.index:
        sot90 = team_data['SoT/90']
    if 'FK' in team_data.index:
        fk = int(team_data['FK'] / team_games_played + 0.5) if team_data['FK'] / team_games_played >= 0 else int(
            team_data['FK'] / team_games_played - 0.5),
    all_stats_team.update({'sh': sh90,
                           'sot': sot90,
                           'fk': fk,
                           # 'pk': predict_value(team_data.iloc[0]['PK'] / team_games_played),
                           'pk': 0,
                           # 'pkatt': predict_value(team_data.iloc[0]['PKatt'] / team_games_played)
                           'pkatt': 0})


def addPoss(all_stats_team, team_data):
    value_team = team_data['Poss'] if not pd.isna(team_data['Poss']) else 0
    all_stats_team['poss'] = value_team


def changeColumns(data):
    data = data.T.reset_index().T.reset_index(drop=True)
    new_header = data.iloc[1]
    data = data[2:]
    data.columns = new_header
    return data


def getPointsGamesPlayedForm(team, team_data):
    team_games_played = team_data['MP']
    team_last_3_games = team_data['Last 5']
    all_stats_team = {"name": team,
                      'games_played': team_games_played,
                      'points': team_data['Pts'],
                      'last_3_games': sum(
                          [3 if x == 'W' else 1 if x == 'D' else 0 for x in team_last_3_games.split()[-3:]])}
    return all_stats_team, team_games_played

# print(getPrediction(team, opponent, competition))
