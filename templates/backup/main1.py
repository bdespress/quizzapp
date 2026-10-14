from fastapi import FastAPI, Form, Request, HTTPException 
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
from starlette.middleware.sessions import SessionMiddleware
from uuid import uuid4

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="bizarre")

templates = Jinja2Templates(directory='templates')

questions = [{"question": "Combien font 2+2 ?", "choix": ["1", "3", "2", "4"], "reponse": 3},
             {"question": "Combien font 3+3 ?", "choix": ["1", "3", "6", "4"], "reponse": 2}]

etats_joueurs = {}

def get_etat_joueur(request: Request):
    id_joueur = request.session.get("id_joueur")
    if not id_joueur:
        id_joueur = str(uuid4())
        request.session["id_joueur"] = id_joueur
    if id_joueur not in etats_joueurs:
        etats_joueurs[id_joueur] = {"score": 0, "index": 0}
    return id_joueur, etats_joueurs[id_joueur]




@app.get("/")
def home(request: Request):
    id_joueur, etat_joueur = get_etat_joueur(request)
    return templates.TemplateResponse(request=request, name = "accueil.html", context={"index": etat_joueur["index"], "score": etat_joueur["score"]})

@app.get("/quiz")
def quiz(request: Request):
    id_joueur, etat_joueur = get_etat_joueur(request)
    current_question = questions[etat_joueur["index"]]
    return templates.TemplateResponse(request=request, name = "question.html", context={"quest": current_question, "index": etat_joueur["index"], "score": etat_joueur["score"]})


@app.post("/quiz")
def repondre(request: Request, user_reponse: int = Form(alias="bouton_rep")):
    id_joueur, etat_joueur = get_etat_joueur(request)
    current_question = questions[etat_joueur["index"]]

    if user_reponse  == current_question["reponse"]:
        etat_joueur["score"] = etat_joueur["score"] + 1

    if etat_joueur["index"] < len(questions) - 1: 
        etat_joueur["index"] = etat_joueur["index"] + 1
        current_question = questions[etat_joueur["index"]]
        return templates.TemplateResponse(request=request, name = "question.html", context={"quest": current_question, "index": etat_joueur["index"], "score": etat_joueur["score"]})
    else :
        etat_joueur["index"] = 0
        etat_joueur["score"] = 0
        return templates.TemplateResponse(request=request, name = "final.html", context={"index": etat_joueur["index"], "score": etat_joueur["score"]})