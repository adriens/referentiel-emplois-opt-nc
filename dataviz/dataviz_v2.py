from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt


url: str = "https://ejykmsqrppsdbmwxpjve.supabase.co"   # URL du projet sur database
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqeWttc3FycHBzZGJtd3hwanZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgwNzQ5NjMsImV4cCI6MjA3MzY1MDk2M30.DyuMi404mcmA-j0Jw2jdH4m2p6Vj5YqMjOE48FKAulw"  # API Key 

# Connexion à Supabase
supabase: Client = create_client(url, key)

# 1. Récupérer les données de la table Emploi et faire une jointure avec Sous_familles
response = supabase.table("emploi").select(
    "*, sous_familles:id_sousf(description, Familles:id_f(description))"
).execute()

# 2. Transformer les données en DataFrame
data_list = []
for item in response.data:
    if item['sous_familles']:
        famille_desc = item['sous_familles']['Familles']['description'] if item['sous_familles']['Familles'] else None
        sous_famille_desc = item['sous_familles']['description']
        
        data_list.append({
            "famille_description": famille_desc,
            "sous_famille_description": sous_famille_desc,
            "intitule_emploi": item["intitule"]
        })

df = pd.DataFrame(data_list)
print(df.head())

# EXEMPLES DE DATAVIZ

# 1️ Répartition des emplois par famille
if "famille_description" in df.columns:
    famille_counts = df["famille_description"].value_counts()
    famille_counts.plot(kind="bar", figsize=(8,4))
    plt.title("Répartition des emplois par famille")
    plt.xlabel("Famille")
    plt.ylabel("Nombre d'emplois")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()


# 2️ Répartition des emplois par sous-famille (description)
if "sous_famille_description" in df.columns:
    sous_famille_counts = df["sous_famille_description"].value_counts().head(10)
    sous_famille_counts.plot(kind="barh", figsize=(8,5))
    plt.title("Top 10 des sous-familles demandées")
    plt.xlabel("Nombre d'emplois")
    plt.ylabel("Sous-famille")
    plt.tight_layout()
    plt.show()