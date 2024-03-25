import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from numpy import argmax
from pydantic import BaseModel
import pickle
import json
from datetime import date
import requests

from fastapi.middleware.cors import CORSMiddleware

from predict import getPrediction
from consts import SUPPORTED_LEAGUES, SUPPORTED_LEAGUES_IDS

API_KEY = 'f72581deb3mshb816475cf971a8ep19646djsn8a6c852447e1'
FIXTURES_API = 'https://api-football-v1.p.rapidapi.com/v3/fixtures'
STANDINGS_LEAGUE_API = 'https://api-football-v1.p.rapidapi.com/v3/standings'
TEAM_SEARCH_API_URL = 'https://api-football-v1.p.rapidapi.com/v3/teams'
HEADERS = {
    'X-RapidAPI-Key': API_KEY,
    'X-RapidAPI-Host': 'api-football-v1.p.rapidapi.com'
}
app = FastAPI()

origins = ["http://localhost:4200"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class model_input(BaseModel):
    team: str
    opponent: str
    competition: str


@app.get("/available_leagues")
def read_root():
    return SUPPORTED_LEAGUES_IDS


@app.post('/game_prediction')
def stroke_pred(input_parameters: model_input):
    input_data = input_parameters.json()
    input_dictionary = json.loads(input_data)
    team = input_dictionary['team']
    opponent = input_dictionary['opponent']
    competition = input_dictionary['competition']
    result = {
        0: "L",
        1: "D",
        2: "W"
    }
    print(team, opponent, competition)
    try:
        prediction_response, team_data, opponent_data = getPrediction(team, opponent, competition)
        print(prediction_response)
        today = date.today()
        with open("prediction_logs/logs/response_log_" + str(today) + ".txt", "a") as file:
            file.write(json.dumps({
                "result": result[argmax(prediction_response[0])],
                "win": str(prediction_response[0][2]),
                "draw": str(prediction_response[0][1]),
                "lose": str(prediction_response[0][0]),
                "team": team,
                "opponent": opponent
            }) + "\n")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=404, detail=str(e))
    return {"result": result[argmax(prediction_response[0])],
            "win": str(prediction_response[0][2]),
            "draw": str(prediction_response[0][1]),
            "lose": str(prediction_response[0][0]),
            "team": team,
            "opponent": opponent
            }


@app.get("/fixtures")
async def read_item(request: Request):
    # Save the parameters
    params = request.query_params
    print(params)
    response = call_football_api(params, FIXTURES_API)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="External API error")
    data = response.json()
    return data


@app.get("/standings")
async def read_item(request: Request):
    # Save the parameters
    params = request.query_params
    print(params)
    response = call_football_api(params, STANDINGS_LEAGUE_API)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="External API error")
    data = response.json()
    return data


@app.get("/teams")
async def read_item(request: Request):
    # Save the parameters
    params = request.query_params
    print(params)
    response = call_football_api(params, TEAM_SEARCH_API_URL)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="External API error")
    data = response.json()
    return data


def call_football_api(params, url):
    # Make a request to the external API with the parameters
    response = requests.get(url, params=params, headers=HEADERS)
    return response
