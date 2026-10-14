from fastapi import FastAPI, Form, Request, HTTPException, WebSocket
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4
import json

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="bizarre")
 
JOUEURS = []
INDEX_QUESTION = 0
ATTENTE_REP = 0

class Gestconnection:
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
    
class Etatjoueur:
    def __init__(self):
        self.numero : int = len(JOUEURS)+1
        self.score  : int = 0
        self.idquestion : int = 0   
        
Gest = Gestconnection()


templates = Jinja2Templates(directory='templates')

db = [{"question": "Quelle est la capitale de la France ?", "reponse": "Paris"},
             {"question": "Combien font 3+3 ?", "reponse": "4"}]





@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name = "accueil.html")

@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    global INDEX_QUESTION, ATTENTE_REP
    await Gest.connect(socket)
    joueur = Etatjoueur()
    JOUEURS.append(joueur)
    try:
        while True:
            brut = await socket.receive_text()
            message = json.loads(brut)
            if message["type"] == "ordre":
                await Gest.JSON_general({"type" : "quest", "intitule" : db[INDEX_QUESTION]["question"]})
            if message["type"] == "reponse":
                if message["contenu"] == db[INDEX_QUESTION]["reponse"]:
                    joueur.score += 1
                    await Gest.JSON_perso(socket, {"type" : "affiche", "contenu" : "Bonne réponse !!!"})
                else:
                    await Gest.JSON_perso(socket, {"type" : "affiche", "contenu" : "Mauvais réponse..."})
                ATTENTE_REP += 1
            if ATTENTE_REP == len(JOUEURS):
                ATTENTE_REP = 0
                INDEX_QUESTION += 1
                await Gest.JSON_general({"type" : "quest", "intitule" : db[INDEX_QUESTION]["question"]})
                
    except:
        Gest.disconnect(socket)

# @app.get("/question/{question_index}")
# def home(request: Request, question_index: int):
#     current_question = db[question_index]["question"]
#     return templates.TemplateResponse(request=request, name = "question.html", context={"question": current_question})

# @app.websocket("/question/{question_index}/ws")
# async def websocket_endpoint(socket: WebSocket, question_index: int):
#     await Gest.connect(socket)
#     current_reponse = db[question_index]["reponse"]
#     try:
#         while True:
#             message = await socket.receive_text()
#             if message == current_reponse:
#                 await Gest.message_perso(socket, "Bonne réponse !")
#             else:
#                 await Gest.message_perso(socket, "Mauvaise réponse...")
#     except:
#         Gest.disconnect(socket)

# @app.get("/quiz")
# def quiz(request: Request):
#     id_joueur, etat_joueur = get_etat_joueur(request)
#     current_question = questions[etat_joueur["index"]]
#     return templates.TemplateResponse(request=request, name = "question.html", context={"quest": current_question, "index": etat_joueur["index"], "score": etat_joueur["score"]})


# @app.post("/quiz")
# def repondre(request: Request, user_reponse: int = Form(alias="bouton_rep")):
#     id_joueur, etat_joueur = get_etat_joueur(request)
#     current_question = questions[etat_joueur["index"]]

#     if user_reponse  == current_question["reponse"]:
#         etat_joueur["score"] = etat_joueur["score"] + 1

#     if etat_joueur["index"] < len(questions) - 1: 
#         etat_joueur["index"] = etat_joueur["index"] + 1
#         current_question = questions[etat_joueur["index"]]
#         return templates.TemplateResponse(request=request, name = "question.html", context={"quest": current_question, "index": etat_joueur["index"], "score": etat_joueur["score"]})
#     else :
#         etat_joueur["index"] = 0
#         etat_joueur["score"] = 0
#         return templates.TemplateResponse(request=request, name = "final.html", context={"index": etat_joueur["index"], "score": etat_joueur["score"]})