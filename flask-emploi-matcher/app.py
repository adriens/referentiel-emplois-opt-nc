from flask import Flask, render_template, request, jsonify
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration de la base de données depuis les variables d'environnement
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'port': 5432  # Port par défaut PostgreSQL
}

class JobMatcher:
    """Classe pour gérer la recherche et le matching des métiers"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
    
    def search_jobs(self, competences: str, souhait: Optional[str] = None) -> List[Dict]:
        """
        Recherche les métiers selon les compétences et souhaits
        
        Args:
            competences: Compétence principale recherchée
            souhait: Souhait d'emploi (optionnel)
            
        Returns:
            Liste des métiers correspondants avec leurs détails
        """
        try:
            # Connexion à la base de données PostgreSQL
            conn = self.connect_to_database()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Nettoyage et préparation des termes de recherche
            competences_clean = self.clean_search_term(competences)
            souhait_clean = self.clean_search_term(souhait) if souhait else None
            
            # Construction de la requête SQL
            query, params = self.build_search_query(competences_clean, souhait_clean)
            
            # Exécution de la requête
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Formatage des résultats
            jobs = self.format_results(results)
            
            # Tri par pertinence
            jobs = self.sort_by_relevance(jobs, competences_clean, souhait_clean)
            
            conn.close()
            logger.info(f"Trouvé {len(jobs)} métiers pour '{competences}' / '{souhait}'")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []
    
    def connect_to_database(self):
        """Établit la connexion à la base de données PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            raise
    
    def clean_search_term(self, term: str) -> str:
        """Nettoie et normalise un terme de recherche"""
        if not term:
            return ""
        
        # Suppression des caractères spéciaux et normalisation
        term = re.sub(r'[^\w\s]', ' ', term.lower().strip())
        term = re.sub(r'\s+', ' ', term)
        
        return term
    
    def build_search_query(self, competences: str, souhait: Optional[str]) -> tuple:
        """Construit la requête SQL de recherche pour PostgreSQL selon le schéma réel"""
        
        # Requête avec jointures selon votre schéma de DB
        base_query = """
        SELECT DISTINCT 
            e.intitule,
            e.code_tiahre,
            fp.intitule as poste_intitule,
            fp.structure_ref,
            fp.code_uo,
            sf.description as sous_famille_desc,
            f.type_f as famille_type,
            f.description as famille_desc
        FROM emploi e
        LEFT JOIN fiches_poste fp ON e.code_tiahre = fp.code_tiahre
        LEFT JOIN sous_familles sf ON e.id_sousf = sf.id_sousf
        LEFT JOIN familles f ON sf.id_f = f.id_f
        WHERE 1=1
        """
        
        params = []
        conditions = []
        
        # Recherche dans les compétences et descriptions
        if competences:
            conditions.append("""
                (e.intitule ILIKE %s 
                OR fp.intitule ILIKE %s 
                OR sf.description ILIKE %s 
                OR f.type_f ILIKE %s
                OR f.description ILIKE %s)
            """)
            competence_param = f"%{competences}%"
            params.extend([competence_param] * 5)
        
        # Recherche dans les souhaits/intitulés spécifiques
        if souhait:
            conditions.append("""
                (e.intitule ILIKE %s 
                OR fp.intitule ILIKE %s)
            """)
            souhait_param = f"%{souhait}%"
            params.extend([souhait_param, souhait_param])
        
        # Assemblage de la requête
        if conditions:
            query = base_query + " AND (" + " OR ".join(conditions) + ")"
        else:
            query = base_query
        
        query += " ORDER BY e.intitule ASC LIMIT 50"
        
        return query, params
    
    def format_results(self, results: List[Dict]) -> List[Dict]:
        """Formate les résultats selon le schéma de la base de données"""
        jobs = []
        
        for row in results:
            job = {
                'intitule': row['intitule'] if row['intitule'] else "Non spécifié",
                'code_Tiahre': str(row['code_tiahre']) if row['code_tiahre'] else "N/A",
                'poste_intitule': row['poste_intitule'] if row['poste_intitule'] else "",
                'structure_ref': row['structure_ref'] if row['structure_ref'] else "",
                'code_uo': row['code_uo'] if row['code_uo'] else "",
                'sous_famille_desc': row['sous_famille_desc'] if row['sous_famille_desc'] else "",
                'famille_type': row['famille_type'] if row['famille_type'] else "",
                'famille_desc': row['famille_desc'] if row['famille_desc'] else "",
                # Champs pour compatibilité avec l'ancien template
                'description': row['sous_famille_desc'] if row['sous_famille_desc'] else row['famille_desc'],
                'domaine': row['famille_type'] if row['famille_type'] else "",
                'competences_requises': f"{row['famille_desc']} - {row['sous_famille_desc']}" if row['famille_desc'] and row['sous_famille_desc'] else "",
                'niveau_requis': row['structure_ref'] if row['structure_ref'] else ""
            }
            jobs.append(job)
        
        return jobs
    
    def sort_by_relevance(self, jobs: List[Dict], competences: str, souhait: Optional[str]) -> List[Dict]:
        """Trie les résultats par pertinence selon le schéma réel"""
        
        def calculate_relevance_score(job: Dict) -> float:
            score = 0
            
            # Bonus si le terme de compétence apparaît dans l'intitulé principal
            if competences and competences.lower() in job['intitule'].lower():
                score += 15
            
            # Bonus si le terme apparaît dans l'intitulé du poste
            if competences and job['poste_intitule'] and competences.lower() in job['poste_intitule'].lower():
                score += 12
            
            # Bonus si le souhait correspond exactement à l'intitulé
            if souhait and souhait.lower() in job['intitule'].lower():
                score += 20
            
            # Bonus si le souhait correspond à l'intitulé du poste
            if souhait and job['poste_intitule'] and souhait.lower() in job['poste_intitule'].lower():
                score += 18
            
            # Bonus si le terme apparaît dans la famille
            if competences and job['famille_type'] and competences.lower() in job['famille_type'].lower():
                score += 8
            
            # Bonus si le terme apparaît dans la description de sous-famille
            if competences and job['sous_famille_desc'] and competences.lower() in job['sous_famille_desc'].lower():
                score += 5
            
            return score
        
        # Calcul des scores et tri
        for job in jobs:
            job['calculated_score'] = calculate_relevance_score(job)
        
        return sorted(jobs, key=lambda x: x['calculated_score'], reverse=True)


# Instance du matcher avec la configuration DB
job_matcher = JobMatcher(DB_CONFIG)

@app.route('/', methods=['GET', 'POST'])
def index():
    """Route principale pour la recherche d'emplois"""
    
    if request.method == 'POST':
        try:
            # Récupération des données du formulaire
            competences = request.form.get('competences', '').strip()
            souhait = request.form.get('souhait', '').strip()
            
            # Validation des données
            if not competences:
                return render_template('index.html', 
                                     metiers=[], 
                                     error="Veuillez saisir au moins une compétence.")
            
            # Recherche des métiers
            metiers = job_matcher.search_jobs(competences, souhait)
            
            # Log pour debug
            logger.info(f"Recherche: '{competences}' / '{souhait}' -> {len(metiers)} résultats")
            
            # Rendu de la page avec les résultats
            return render_template('index.html',
                                 metiers=metiers,
                                 competence=competences,  # Pour pré-remplir le formulaire
                                 souhait=souhait,
                                 search_performed=True)
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return render_template('index.html', 
                                 metiers=[], 
                                 error="Une erreur est survenue lors de la recherche. Veuillez réessayer.")
    
    else:
        # Affichage du formulaire vide (GET)
        return render_template('index.html', metiers=None)


@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint pour la recherche AJAX (optionnel)"""
    
    try:
        data = request.get_json()
        competences = data.get('competences', '').strip()
        souhait = data.get('souhait', '').strip()
        
        if not competences:
            return jsonify({'error': 'Compétence requise'}), 400
        
        metiers = job_matcher.search_jobs(competences, souhait)
        
        return jsonify({
            'success': True,
            'count': len(metiers),
            'jobs': metiers
        })
    
    except Exception as e:
        logger.error(f"Erreur API: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@app.route('/stats')
def stats():
    """Route pour afficher des statistiques (optionnel)"""
    
    try:
        # Vous pouvez ajouter des statistiques sur les recherches
        stats_data = {
            'total_jobs': 0,  # À calculer depuis votre DB
            'popular_skills': [],  # Compétences les plus recherchées
            'recent_searches': []  # Recherches récentes
        }
        
        return jsonify(stats_data)
    
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return render_template('index.html', 
                         metiers=None, 
                         error="Page non trouvée"), 404


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    logger.error(f"Erreur serveur: {error}")
    return render_template('index.html', 
                         metiers=None, 
                         error="Erreur interne du serveur"), 500


@app.route('/test_db')
def test_db():
    """Route pour tester la connexion à la base de données et afficher la structure"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Test de connexion
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Compter les enregistrements dans chaque table
        cursor.execute("SELECT COUNT(*) FROM emploi;")
        count_emploi = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fiches_poste;")
        count_fiches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sous_familles;")
        count_sous_familles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM familles;")
        count_familles = cursor.fetchone()[0]
        
        # Quelques exemples d'emplois
        cursor.execute("SELECT intitule, code_tiahre FROM emploi LIMIT 5;")
        exemples_emplois = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Connexion réussie',
            'db_version': version,
            'statistiques': {
                'emplois': count_emploi,
                'fiches_poste': count_fiches,
                'sous_familles': count_sous_familles,
                'familles': count_familles
            },
            'exemples_emplois': [{'intitule': emp[0], 'code_tiahre': emp[1]} for emp in exemples_emplois]
        })
    
    except Exception as e:
        logger.error(f"Erreur de connexion DB: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Vérification des variables d'environnement
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Variables d'environnement manquantes: {missing_vars}")
        exit(1)
    
    logger.info("Configuration DB chargée avec succès")
    logger.info(f"Host: {DB_CONFIG['host']}")
    logger.info(f"Database: {DB_CONFIG['database']}")
    logger.info(f"User: {DB_CONFIG['user']}")
    
    # Configuration pour le développement
    app.run(debug=True, host='0.0.0.0', port=5000)