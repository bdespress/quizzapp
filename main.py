from fastapi import FastAPI, Form, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4
import json
import asyncio
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import json
import gspread
import logging

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="bizarre") # Je comprends pas cette ligne
app.mount("/static", StaticFiles(directory="static"), name="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GestConnection: # Gestion des websocket
    def __init__(self):
        self.connections : set[WebSocket] = set()
        self.lock = asyncio.Lock()
    async def connect(self, socket: WebSocket):
        await socket.accept()
        async with self.lock:
            self.connections.add(socket)
    async def disconnect(self, socket: WebSocket):
        async with self.lock:
            self.connections.discard(socket)
    async def JSON_perso(self, socket: WebSocket, message):
        try:
            await asyncio.wait_for(socket.send_json(message), timeout=5)
        except (WebSocketDisconnect, RuntimeError, asyncio.TimeoutError):
            logger.warning("Echec d'envoi à un client")
    async def JSON_general(self, message):
        async with self.lock:
            clients = list(self.connections)
        async def envoyer(client):
            try:
                await asyncio.wait_for(client.send_json(message), timeout=5)
                return None
            except (WebSocketDisconnect, RuntimeError, asyncio.TimeoutError) as e:
                logger.warning("Client déconnecté ou bloqué : %s", e)
                return client
            except Exception:
                logger.exception("Erreur lors de l'envoi à un client")
        resultats = await asyncio.gather(*(envoyer(client) for client in clients))
        for client in resultats:
            if client is not None:
                await self.disconnect(client)

class GameManager: # variables d'une partie
    def __init__(self):
        self.quizz_started = False
        self.liste_joueurs : list = []
        self.question_index : int=0
        self.correction_index : int=0
        self.joueur_index : int=0
        self.database : list = []
        self.lock = asyncio.Lock()
    def reset(self):
        self.quizz_started = False
        self.liste_joueurs : list = []
        self.question_index : int=0
        self.correction_index : int=0
        self.joueur_index : int=0
        self.database : list = []

class EtatJoueur: # données d'un joueur
    def __init__(self):
        self.nom : str = None
        self.reponses: list = []
        self.score : int = 0

#
def get_database():      # récupère les questions du googlesheet
    credentials_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]    # clef de connection au googlesheet caché en variable d'environnement
    credentials_dict = json.loads(credentials_json)     # transforme la clef JSON en dictionnaire

    gc = gspread.service_account_from_dict(credentials_dict)
    googlesheet = gc.open('questions_excel')        # accède au fichier 
    sheet = googlesheet.worksheet("Feuille 1")      # accède à la feuille
    all = sheet.get_all_records()              # récupère les données sous forme de dictionnaire
    questions_actives = []
    for row in all:
        if row.get("visible") == 1 and row.get("intitule"):
            questions_actives.append(row) 
    return questions_actives

# Envoi la question aux joueurs et recupère les réponses à la fin du chrono
async def envoyer_quest_suiv(game, database, gest_connection) :
    while game.question_index < len(database):
        await gest_connection.JSON_general({"type" : "show_question", "data" : {"intitule" : database[game.question_index]["intitule"], "image" : database[game.question_index]["image"]}})
        await asyncio.sleep(30)
        await gest_connection.JSON_general({"type" : "get_reponse"})
        await asyncio.sleep(0.1)
        game.question_index += 1 
    await gest_connection.JSON_general({"type" : "fin_quizz", "data" : database[0], "nom_joueur" : game.liste_joueurs[0].nom, "rep_joueur" : game.liste_joueurs[0].reponses[0]})


gest_connection = GestConnection()

game = GameManager()

templates = Jinja2Templates(directory='templates')

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
                game.database = get_database()     # charge la base des questions / corrections
                if not game.database:
                    await gest_connection.JSON_general({"type": "erreur", "data": "Aucune question disponible"})
                    continue
                game.quizz_started = True
                asyncio.create_task(envoyer_quest_suiv(game, game.database, gest_connection))
            if message["type"] == "reponse":    # Reçoit une réponse
                joueur.reponses.append(message["data"])
            if message["type"] == "next":   # Passe à la correction suivante
                if message.get("data"):     # Ajoute les points
                    game.liste_joueurs[game.joueur_index].score += 1
                if game.joueur_index < len(game.liste_joueurs)-1 :
                    game.joueur_index +=1
                    await gest_connection.JSON_general({"type" : "fin_quizz", "data" : game.database[game.correction_index], "nom_joueur" : game.liste_joueurs[game.joueur_index].nom, "rep_joueur" : game.liste_joueurs[game.joueur_index].reponses[game.correction_index]})
                else :
                    if game.correction_index < len(game.database)-1:
                        game.joueur_index = 0
                        game.correction_index += 1
                        await gest_connection.JSON_general({"type" : "fin_quizz", "data" : game.database[game.correction_index], "nom_joueur" : game.liste_joueurs[game.joueur_index].nom, "rep_joueur" : game.liste_joueurs[game.joueur_index].reponses[game.correction_index]})
                    else :
                        scores = ""
                        for j in game.liste_joueurs :
                            scores += f"\n{j.nom} : {j.score}pts"     
                        await gest_connection.JSON_general({"type" : "score_final", "data" : scores})
                        game.reset()

    except WebSocketDisconnect:
        logger.info("Un joueur s'est déconnecté")
    except json.JSONDecodeError:
        logger.warning("Message JSON invalide reçu")
    except Exception:
        logger.exception("Erreur dans le traitement WebSocket")
    finally:
        await gest_connection.disconnect(socket)