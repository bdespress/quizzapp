from fastapi import FastAPI, Form, Request, HTTPException, WebSocket
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4
import json
import asyncio
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="bizarre")
app.mount("/static", StaticFiles(directory="static"), name="static")
 
class GestConnection: # Gestion des websocket
    def __init__(self):
        self.connections : list[WebSocket] = []
    async def connect(self, socket: WebSocket):
        await socket.accept()
        self.connections.append(socket)
    def disconnect(self, socket: WebSocket):
        self.connections.remove(socket)
    async def JSON_perso(self, socket: WebSocket, message):
        await socket.send_json(message)
    async def JSON_general(self, message):
        for client in self.connections:
            await client.send_json(message)
    def socket_index(self, socket: WebSocket):
        return self.connections.index(socket)+1

class GameManager: # variables d'une partie
    def __init__(self):
        self.quizz_started = False
        self.liste_joueurs : list = []
        self.question_index : int=0
        self.correction_index : int=0
        self.joueur_index : int=0

class EtatJoueur: # données d'un joueur
    def __init__(self):
        self.nom : str = None
        self.reponses: list = []
        self.score : int = 0

# Envoi la question aux joueurs et recupère les réponses à la fin du chrono
async def envoyer_quest_suiv(game, database, gest_connection) :
    while game.question_index < len(database):
        await gest_connection.JSON_general({"type" : "show_question", "data" : database[game.question_index]["question"]})
        await asyncio.sleep(15)
        await gest_connection.JSON_general({"type" : "get_reponse"})
        await asyncio.sleep(0.1)
        game.question_index += 1 
    await gest_connection.JSON_general({"type" : "fin_quizz", "data" : database[0], "nom_joueur" : game.liste_joueurs[0].nom, "rep_joueur" : game.liste_joueurs[0].reponses[0]})


gest_connection = GestConnection()

game = GameManager()

templates = Jinja2Templates(directory='templates')

# Base des questions / corrections
db = [{"question": "Quelle est la capitale de la France ?", "correction": "Paris"},
             {"question": "Combien font 3+3 ?", "correction": "6"}]





@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name = "quizzpage.html")

@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    await gest_connection.connect(socket)   # Connecte une websocket
    try:
        while True:
            brut = await socket.receive_text()
            message = json.loads(brut)
            if message["type"] == "nom_joueur": # Reçoit le nom d'un joueur
                joueur = EtatJoueur()
                joueur.nom = message["data"]
                game.liste_joueurs.append(joueur)
            if message["type"] == "start_quizz" and not game.quizz_started:   # Démarre le quizz
                game.quizz_started = True
                asyncio.create_task(envoyer_quest_suiv(game, db, gest_connection))
            if message["type"] == "reponse":    # Reçoit une réponse
                joueur.reponses.append(message["data"])
            if message["type"] == "next":   # Passe à la correction suivante
                if message.get("data"):     # Ajoute les points
                    game.liste_joueurs[game.joueur_index].score += 1
                if game.joueur_index < len(game.liste_joueurs)-1 :
                    game.joueur_index +=1
                    await gest_connection.JSON_general({"type" : "fin_quizz", "data" : db[game.correction_index], "nom_joueur" : game.liste_joueurs[game.joueur_index].nom, "rep_joueur" : game.liste_joueurs[game.joueur_index].reponses[game.correction_index]})
                else :
                    if game.correction_index < len(db)-1:
                        game.joueur_index = 0
                        game.correction_index += 1
                        await gest_connection.JSON_general({"type" : "fin_quizz", "data" : db[game.correction_index], "nom_joueur" : game.liste_joueurs[game.joueur_index].nom, "rep_joueur" : game.liste_joueurs[game.joueur_index].reponses[game.correction_index]})
                    else :
                        scores = ""
                        for j in game.liste_joueurs :
                            scores += f"\n{j.nom} : {j.score}pts"     
                        await gest_connection.JSON_general({"type" : "score_final", "data" : scores})

    except:
        gest_connection.disconnect(socket)