import difflib
import json

import cfscrape
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser

from consts import *


def get_h2h(id_1, id_2, match_date, league):
    # time.sleep(1)
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/headtohead"

    querystring = {"h2h": f"{id_1}-{id_2}"}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    data_list = response.json()["response"]
    h2h_list = list()
    dates_list = list()
    for data in data_list:
        if data["league"]["name"] == league:
            date = data["fixture"]["date"]
            date = parser.parse(date).date()
            if date < parser.parse(match_date).date():
                dates_list.append(date)
                h2h_list.append((data["teams"]))

    id_1_wins = 0
    id_2_wins = 0
    dates_list.sort()
    for item in h2h_list:
        if (item["home"]["id"] == id_1 and item["home"]["winner"] is True) or item["away"]["id"] == id_1 and \
                item["away"]["winner"] is True:
            id_1_wins += 1
        elif (item["home"]["id"] == id_2 and item["home"]["winner"] is True) or item["away"]["id"] == id_2 and \
                item["away"]["winner"] is True:
            id_2_wins += 1
    return id_1_wins, id_2_wins, len(h2h_list) - id_1_wins - id_2_wins

def get_teams_ids_from_API(season, league, country):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"

    querystring = {"league": {league}, "season": {season}, "country": {country}}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    data_list = dict()
    response = response.json()["response"]
    for item in response:
        data_list[item["team"]["name"]] = item["team"]["id"]
    return data_list


def get_league_id_from_API(country, league):
    url = "https://api-football-v1.p.rapidapi.com/v3/leagues"
    querystring = {"name": {league}, "country": {country}}

    headers = {
        "X-RapidAPI-Key": "f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1",
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }

    response = requests.request("GET", url, headers=headers, params=querystring)
    return response.json()["response"][0]["league"]["id"]


def get_teams_ids(country, league, league_id):
    teams = {league: get_teams_ids_from_API("2022", league_id, country)}
    teams[league].update(get_teams_ids_from_API("2021", league_id, country))
    teams[league].update(get_teams_ids_from_API("2020", league_id, country))
    return teams[league]


def save_as_json_file(teams_ids):
    with open("jsons/teams_ids.json", "w") as outfile:
        json.dump(teams_ids, outfile, indent=4)


def save_data_to_consts_file(data, variable_name):
    data = list(data)
    with open('consts.py', 'r+') as file_object:
        content = file_object.read()
        file_object.seek(0, 0)
        file_object.write(f"{variable_name} = {str(data)}\n" + content)


def save_raw_data_to_consts_file(data, variable_name):
    with open('consts.py', 'r+') as file_object:
        content = file_object.read()
        file_object.seek(0, 0)
        file_object.write(f"{variable_name} = {data}\n" + content)


def get_team_id_from_consts_file(team, league, teams_ids):
    return teams_ids[league][team]


def get_teams_ids_from_top5_leagues():
    teams_ids = dict()
    for league in SUPPORTED_LEAGUES:
        country = SUPPORTED_LEAGUES[league]['country']
        league_id = get_league_id_from_API(country, league)
        teams_ids[league] = get_teams_ids(country, league, league_id)
    return teams_ids


def get_teams_names_from_league_from_fbref(league):
    link = DATA_LINKS[league]
    scraper = cfscrape.create_scraper()
    data = scraper.get(link).content
    data = pd.read_html(data)[2]
    data = data["Squad"].values
    save_data_to_consts_file(data, f"{league.upper().replace(' ', '_' )}_TEAMS")


def transform_all_values_to_string_from_dict(data):
    return {key: str(value) if not isinstance(value, str) else value for key, value in data.items()}


def get_tables(link):
    scraper = cfscrape.create_scraper()
    data = scraper.get(link).content
    soup = BeautifulSoup(data, 'html.parser')
    tables = soup.find_all('table')
    title_indices = {}
    for i, table in enumerate(tables):
        title_element = table.find('caption')
        if title_element:
            title = title_element.get_text()
            if title not in title_indices:
                title_indices[title] = i
    return title_indices


def get_tables_data(league):
    link = DATA_LINKS[league]
    tables = get_tables(link)
    save_raw_data_to_consts_file(tables, f"{league.upper().replace(' ', '_')}_TABLES")


# get_teams_names_from_league_from_fbref('Major League Soccer')
# get_tables_data('Liga Profesional Argentina')