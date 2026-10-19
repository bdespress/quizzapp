import sqlite3 as sq
import csv

fichier_sql = "database.db"
fichier_excel = "excel_questions.csv"

con = sq.connect('database.db')
curs = con.cursor()

# créé la table 'questions', avec les bonnes colonnes, si elle n'existe pas
sql1 = '''CREATE TABLE IF NOT EXISTS  questions(
        numero INTEGER PRIMARY KEY,
        intitule TEXT,
        correction TEXT,
        image TEXT,
        difficulte INTEGER,
        categorie TEXT,
        visible INTEGER
        );'''

curs.execute(sql1)
con.commit()

with open (fichier_excel, "r", newline="") as file:
    lecteur = csv.DictReader(file, delimiter=";", quotechar='"')   
    colonnes = lecteur.fieldnames                                   # Récupère les noms des colonnes du csv
    entetes = ", ".join(f'"{colonne}"' for colonne in colonnes)     # les concatène, séparés d'une virgule
    placeholders = ", ".join("?" for _ in colonnes)                 # met autant de '?' que de colonnes

    sql2 = (f'INSERT OR REPLACE INTO questions ({entetes})'         # Insère les nouvelles lignes du csv dans la database ou remplace si le numéro existe déjà
            f'VALUES ({placeholders})')

    curs.executemany(sql2, ([ligne[colonne] for colonne in colonnes] for ligne in lecteur))

sql3 = "SELECT * FROM questions;"       # Affiche toutes les ligne de la table 'question'
curs.execute(sql3)
rows = curs.fetchall()
print(rows)


con.commit()
con.close()


