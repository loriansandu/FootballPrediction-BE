import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
import cfscrape
import difflib
import time
import requests
import numpy as np
from dateutil import parser
from consts import API_TEAMS_IDS
from utils import get_team_id_from_consts_file


def fetch_and_save_GENERAL_data():
    def scrape_matches(years):
        all_matches = []
        all_matches_more_stats = []
        standings_url = "https://fbref.com/en/comps/9/Premier-League-Stats"

        for year in years:
            data = requests.get(standings_url).text.replace('<!--', '').replace('-->', '')
            soup = BeautifulSoup(data, 'html.parser')
            standings_table = soup.select('table.stats_table')[0]
            links = [l.get("href") for l in standings_table.find_all('a') if '/squads/' in l]
            team_urls = [f"https://fbref.com{l}" for l in links]

            previous_season = soup.select("a.prev")[0].get("href")
            standings_url = f"https://fbref.com{previous_season}"

            for team_url in team_urls:
                team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
                data = requests.get(team_url).text.replace('<!--', '').replace('-->', '')
                matches = pd.read_html(data, match="Scores & Fixtures")[0]
                soup = BeautifulSoup(data, 'html.parser')
                links = [l.get("href") for l in soup.find_all('a') if l and 'all_comps/shooting/' in l]
                data = requests.get(f"https://fbref.com{links[0]}").text.replace('<!--', '').replace('-->', '')
                shooting = pd.read_html(data, match="Shooting")[0]
                shooting.columns = shooting.columns.droplevel()

                try:
                    team_data = matches.merge(shooting[["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"]], on="Date")
                except ValueError:
                    continue

                team_data = team_data[team_data["Comp"] == "Premier League"]
                team_data["Season"] = year
                team_data["Team"] = team_name
                all_matches.append(team_data)
                time.sleep(10)

        match_df = pd.concat(all_matches)
        match_df.columns = [c.lower() for c in match_df.columns]

        standings_url = "https://fbref.com/en/comps/9/Premier-League-Stats"
        for year in years:
            data = requests.get(standings_url).text.replace('<!--', '').replace('-->', '')
            soup = BeautifulSoup(data, 'html.parser')
            standings_table = soup.select('table.stats_table')[0]
            links = [l.get("href") for l in standings_table.find_all('a') if '/squads/' in l]
            team_urls = [f"https://fbref.com{l}" for l in links]

            previous_season = soup.select("a.prev")[0].get("href")
            standings_url = f"https://fbref.com{previous_season}"

            for team_url in team_urls:
                team_name = team_url.split("/")[-1].replace("-Stats", "").replace("-", " ")
                data = requests.get(team_url).text.replace('<!--', '').replace('-->', '')
                soup = BeautifulSoup(data, 'html.parser')
                links = [l.get("href") for l in soup.find_all('a') if l and 'all_comps/misc/' in l]
                data = requests.get(f"https://fbref.com{links[0]}").text.replace('<!--', '').replace('-->', '')
                other_stats = pd.read_html(data, match="Miscellaneous Stats")[0]
                other_stats.columns = other_stats.columns.droplevel()

                try:
                    team_data = other_stats[["Date", "Comp", "CrdR", "PKwon", "OG", "2CrdY"]]
                except ValueError:
                    continue

                team_data = team_data[team_data["Comp"] == "Premier League"]
                team_data["Team"] = team_name
                all_matches_more_stats.append(team_data)
                time.sleep(5)

        match_df_2 = pd.concat(all_matches_more_stats)
        match_df_2.columns = [c.lower() for c in match_df_2.columns]

        final_Csv = match_df.merge(match_df_2[['crdr', 'pkwon', 'og', '2crdy', 'date', 'team']], on=['date', 'team'],
                                   how='outer')
        final_Csv.to_csv("data/EPL_games_2020-2021_2021-2022_2022-2023.csv")

    years = list(range(2022, 2019, -1))
    scrape_matches(years)


def fetch_and_save_POINTS_data():
    current_matchweek = 29
    years = list(range(2022, 2019, -1))
    weeks = list(range(1, 39))
    all_data = []
    for year in years:
        if year == 2022:
            weeks = list(range(1, current_matchweek))
        else:
            weeks = list(range(1, 39))
        for week in weeks:
            standings_url = "https://www.transfermarkt.co.uk/premier-league/formtabelle/wettbewerb/GB1?saison_id=%s&min=1" \
                            "&max=%s" % (
                                year, week)
            scraper = cfscrape.create_scraper()
            data = scraper.get(standings_url).content
            matchweek_data = pd.read_html(data)[1]
            matchweek_data = matchweek_data[['Club.1', 'Pts']]
            matchweek_data['season'] = year
            matchweek_data['round'] = "Matchweek %s" % str(int(week) + 1)
            matchweek_data['team'] = matchweek_data['Club.1']
            all_data.append(matchweek_data)
            matchweek_data.drop(columns=matchweek_data.columns[0], axis=1, inplace=True)

    match_df = pd.concat(all_data)

    all_data2 = []
    for year in years:
        if year == 2022:
            weeks = list(range(1, current_matchweek))
        else:
            weeks = list(range(1, 39))
        for week in weeks:
            if week < 5:
                before = 1
            else:
                before = week - 4
            standings_url = "https://www.transfermarkt.co.uk/premier-league/formtabelle/wettbewerb/GB1?saison_id=%s&min=%s" \
                            "&max=%s" % (
                                year, before, week)
            scraper = cfscrape.create_scraper()
            data = scraper.get(standings_url).content
            matchweek_data = pd.read_html(data)[1]
            matchweek_data = matchweek_data[['Club.1', 'Pts', 'Form']]
            matchweek_data['season'] = year
            matchweek_data['round'] = "Matchweek %s" % str(int(week) + 1)
            matchweek_data['team'] = matchweek_data['Club.1']
            form_list = []
            for x in matchweek_data['Form']:
                x = x.split()
                if len(x) >= 3:
                    x = x[-3:]
                sum = 0
                for idx in x:
                    if idx == 'W':
                        sum += 3
                    elif idx == 'D':
                        sum += 1
                form_list.append(sum)
            matchweek_data['Form'] = form_list
            all_data2.append(matchweek_data)
            matchweek_data.drop(columns=matchweek_data.columns[0], axis=1, inplace=True)

    match_df_2 = pd.concat(all_data2)

    final_Csv = match_df.merge(match_df_2[['season', 'round', 'team', 'Form']], on=['season', 'team', 'round'],
                               how='outer')
    final_Csv.to_csv("data/EPL_points_and_form_2020-2021_2021-2022_2022-2023.csv")


def fetch_and_save_BETS_data():
    data = pd.read_csv("/Users/lorian-andreisandu/Downloads/data/E0.csv")
    data2 = pd.read_csv("/Users/lorian-andreisandu/Downloads/data-2/E0.csv")
    data3 = pd.read_csv("/Users/lorian-andreisandu/Downloads/data-3/E0.csv")

    data = data.append(data2)
    data = data.append(data3)
    data = data[["Date", "HomeTeam", "AwayTeam", "B365H", "B365D", "B365A"]]
    iterrows = data.iterrows()
    for index, row in iterrows:
        data.loc[len(data)] = [row["Date"], row["AwayTeam"], row["HomeTeam"], row["B365A"], row["B365D"], row["B365H"]]

    data.rename(
        columns={'Date': 'date', 'HomeTeam': 'team', 'AwayTeam': 'opponent', 'B365H': 'B365T', 'B365A': 'B365O'},
        inplace=True)
    data['date'] = pd.to_datetime(data['date'], dayfirst=True)
    data.to_csv("data/EPL_bets_2020-2021_2021-2022_2022-2023.csv")


def fetch_and_save_H2H_data():
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

    def save_data(dataframe, team_name):
        matches = dataframe[dataframe["team"] == team_name]
        teams = list(API_TEAMS_IDS["Premier League"].keys())
        columns_list = ["team", "opponent"
            , "wins"
            , "losses"
            , "draws"
            , "date"]

        try:
            df = pd.read_csv("data/h2h.csv")
            df.drop(columns=df.columns[0], axis=1, inplace=True)
        except FileNotFoundError:
            df = pd.DataFrame(columns=columns_list)

        for index, row in matches.iterrows():
            print("--")
            opponent = row["opponent"].replace(" ", "")
            team = row["team"].replace(" ", "")
            date = row["date"]
            team = difflib.get_close_matches(team, teams, cutoff=0.5)[0]
            opponent = difflib.get_close_matches(opponent, teams, cutoff=0.5)[0]
            print(f"team {team} opponent {opponent} date {date}")
            if (not df[(df["opponent"] == team) & (df["team"] == opponent) & (df["date"] == date)].empty) or (
                    not df[(df["opponent"] == opponent) & (df["team"] == team) & (df["date"] == date)].empty):
                continue
            id1 = get_team_id_from_consts_file(team, "Premier League", API_TEAMS_IDS)
            id2 = get_team_id_from_consts_file(opponent, "Premier League", API_TEAMS_IDS)
            try:
                wins, losses, draws = get_h2h(id1, id2, date, "Premier League")
                values = {
                    "team": team,
                    "opponent": opponent,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "date": row["date"]
                }
                df = df.append(values, ignore_index=True)
                print(df)
                df.to_csv("data/h2h.csv")
            except:
                print("EROARE ------")
                time.sleep(20)
                wins, losses, draws = get_h2h(id1, id2, date, "Premier League")
                values = {
                    "team": team,
                    "opponent": opponent,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "date": row["date"]
                }
                df = df.append(values, ignore_index=True)
                df.to_csv("data/h2h.csv")

    def save_h2h_data_csv():
        team_name = "Arsenal"
        matches = pd.read_csv("data/EPL_full_2020-2021_2021-2022_2022-2023.csv")
        save_data(matches, team_name)

    def clone_rows():
        data = pd.read_csv("data/h2h.csv")
        data.drop(columns=data.columns[0], axis=1, inplace=True)
        iterrows = data.iterrows()
        print(data)
        for index, row in iterrows:
            data.loc[len(data)] = [row["opponent"], row["team"], row["losses"], row["wins"], row["draws"], row["date"]]
        data.to_csv("data/h2h.csv")

    save_h2h_data_csv()


def merge_data():
    def synchronize_team_names():
        points['team'] = points['team'].replace('Man City', 'Manchester City')
        points['team'] = points['team'].replace('Man Utd', 'Manchester United')
        points['team'] = points['team'].replace('Leeds', 'Leeds United')
        points['team'] = points['team'].replace('Newcastle', 'Newcastle United')
        points['team'] = points['team'].replace('Leicester', 'Leicester City')
        points['team'] = points['team'].replace('Norwich', 'Norwich City')
        points['team'] = points['team'].replace('Nottm Forest', 'Nottingham Forest')
        points['team'] = points['team'].replace('Sheff Utd', 'Sheffield United')
        bets['team'] = bets['team'].replace('Man City', 'Manchester City')
        bets['team'] = bets['team'].replace('Man United', 'Manchester United')
        bets['team'] = bets['team'].replace('Leeds', 'Leeds United')
        bets['team'] = bets['team'].replace('Newcastle', 'Newcastle United')
        bets['team'] = bets['team'].replace('Leicester', 'Leicester City')
        bets['team'] = bets['team'].replace('Norwich', 'Norwich City')
        bets['team'] = bets['team'].replace("Nott'm Forest", 'Nottingham Forest')
        bets['opponent'] = bets['opponent'].replace('Man City', 'Manchester City')
        bets['opponent'] = bets['opponent'].replace('Man United', 'Manchester United')
        bets['opponent'] = bets['opponent'].replace('Leeds', 'Leeds United')
        bets['opponent'] = bets['opponent'].replace('Newcastle', 'Newcastle United')
        bets['opponent'] = bets['opponent'].replace('Leicester', 'Leicester City')
        bets['opponent'] = bets['opponent'].replace('Norwich', 'Norwich City')
        bets['opponent'] = bets['opponent'].replace("Nott'm Forest", 'Nottingham Forest')
        matches['opponent'] = matches['opponent'].replace('Sheffield Utd', 'Sheffield United')
        matches['opponent'] = matches['opponent'].replace("Nott'ham Forest", "Nottingham Forest")
        matches['team'] = matches['team'].replace("Tottenham Hotspur", "Tottenham")
        matches['team'] = matches['team'].replace("West Bromwich Albion", "West Brom")
        matches['opponent'] = matches['opponent'].replace('Newcastle Utd', 'Newcastle United')
        matches['opponent'] = matches['opponent'].replace('Manchester Utd', 'Manchester United')
        matches['team'] = matches['team'].replace('Brighton and Hove Albion', 'Brighton')
        matches['team'] = matches['team'].replace('Wolverhampton Wanderers', 'Wolves')
        matches['team'] = matches['team'].replace('West Ham United', 'West Ham')
        h2h['team'] = h2h['team'].replace('Newcastle', 'Newcastle United')
        h2h['opponent'] = h2h['opponent'].replace('Newcastle', 'Newcastle United')
        h2h['team'] = h2h['team'].replace('Leeds', 'Leeds United')
        h2h['opponent'] = h2h['opponent'].replace('Leeds', 'Leeds United')
        h2h['team'] = h2h['team'].replace('Leicester', 'Leicester City')
        h2h['opponent'] = h2h['opponent'].replace('Leicester', 'Leicester City')
        h2h['team'] = h2h['team'].replace('Norwich', 'Norwich City')
        h2h['opponent'] = h2h['opponent'].replace('Norwich', 'Norwich City')
        h2h['team'] = h2h['team'].replace('Sheffield Utd', 'Sheffield United')
        h2h['opponent'] = h2h['opponent'].replace('Sheffield Utd', 'Sheffield United')
    matches = pd.read_csv("data/EPL_games_2020-2021_2021-2022_2022-2023.csv")
    points = pd.read_csv("data/EPL_points_and_form_2020-2021_2021-2022_2022-2023.csv")
    bets = pd.read_csv('data/EPL_bets_2020-2021_2021-2022_2022-2023.csv')
    h2h = pd.read_csv('data/h2h.csv')
    synchronize_team_names()
    try:
        list = ["team", "season", "round"]
        list2 = ["date", "team", "opponent"]
        first_merge = matches.merge(points[['Pts', 'Form', 'team', 'season', 'round']], on=list, how='outer')
        second_merge = first_merge.merge(bets[["date", "team", "opponent", "B365T", "B365D", "B365O"]], on=list2,
                                         how='outer')
        third_merge = second_merge.merge(h2h[["date", "team", "opponent", "wins", "losses", "draws"]], on=list2,
                                         how='outer')
        team_data = third_merge
    except ValueError:
        print("error")
    team_data.drop(columns=team_data.columns[0], axis=1, inplace=True)
    team_data.drop(columns='match report', axis=1, inplace=True)
    team_data.drop(columns='notes', axis=1, inplace=True)
    team_data.rename(columns={'Pts': 'team points'}, inplace=True)
    team_data.rename(columns={'Form': 'team last_3_games'}, inplace=True)

    try:
        points.rename(columns={'team': 'opponent'}, inplace=True)
        list = ["opponent", "season", "round"]
        team_data = team_data.merge(points[['Pts', 'Form', 'opponent', 'season', 'round']], on=list, how='outer')

    except ValueError:
        print("error")
    team_data.rename(columns={'Pts': 'opponent points'}, inplace=True)
    team_data.rename(columns={'Form': 'opponent last_3_games'}, inplace=True)

    team_data['team points'].fillna(0, inplace=True)
    team_data['opponent points'].fillna(0, inplace=True)
    team_data['team last_3_games'].fillna(0, inplace=True)
    team_data['opponent last_3_games'].fillna(0, inplace=True)
    team_data['team points'] = team_data['team points'].astype(np.int64)
    team_data['opponent points'] = team_data['opponent points'].astype(np.int64)
    team_data['team last_3_games'] = team_data['team last_3_games'].astype(np.int64)
    team_data['opponent last_3_games'] = team_data['opponent last_3_games'].astype(np.int64)
    team_data['venue_code'] = team_data['venue'].astype('category').cat.codes

    team_data = team_data.drop(
        team_data[(team_data.result != 'W') & (team_data.result != 'L') & (team_data.result != 'D')].index)
    team_data["target"] = team_data['result'].replace({'W': 1, 'L': -1, 'D': 0})

    data = []
    data.append(team_data)
    match_df = pd.concat(data)
    match_df.to_csv("data/EPL_full_2020-2021_2021-2022_2022-2023.csv")

