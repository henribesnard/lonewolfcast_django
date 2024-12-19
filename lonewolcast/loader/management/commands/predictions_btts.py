from django.core.management.base import BaseCommand
from firebase_admin import db
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calcule les probabilités BTTS pour les matchs d\'une date donnée'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, help='Date au format YYYY-MM-DD')

    def safe_float(self, value, default=0.0):
        """Convertit une valeur en float de manière sécurisée"""
        try:
            if isinstance(value, str):
                value = value.strip('%')
            return float(value)
        except (ValueError, TypeError, AttributeError):
            return default

    def safe_get(self, data, path, default=0.0):
        """Récupère une valeur imbriquée de manière sécurisée"""
        try:
            result = data
            for key in path:
                result = result[key]
            return self.safe_float(result)
        except (KeyError, TypeError, AttributeError):
            return default

    def calculate_btts_probability(self, match_data):
        """Calcule la probabilité de BTTS pour un match"""
        try:
            total_score = 0
            prediction = match_data.get('prediction', {})

            if not prediction:
                logger.warning(f"Pas de données de prédiction pour le match {match_data.get('fixture', {}).get('id')}")
                return None

            scores = {
                'recent_form': self.analyze_recent_form(prediction),
                'offensive': self.analyze_offensive_stats(prediction),
                'defensive': self.analyze_defensive_stats(prediction),
                'comparison': self.analyze_comparisons(prediction)
            }

            total_score = sum(scores.values())

            # Log détaillé des scores
            self.stdout.write("\nDétail des scores:")
            self.stdout.write(f"- Forme récente: {scores['recent_form']}/35")
            self.stdout.write(f"- Stats offensives: {scores['offensive']}/25")
            self.stdout.write(f"- Stats défensives: {scores['defensive']}/25")
            self.stdout.write(f"- Comparaisons: {scores['comparison']}/15")
            self.stdout.write(f"Score total: {total_score}/100")

            # Calculer les probabilités
            probability = total_score / 100

            return {
                "1": round(probability, 3),
                "0": round(1 - probability, 3),
                "details": {
                    "scores": scores,
                    "total_score": total_score,
                    "stats": self.get_detailed_stats(prediction)
                }
            }

        except Exception as e:
            logger.error(f"Erreur dans le calcul BTTS: {str(e)}")
            return None

    def analyze_recent_form(self, prediction):
        """Analyse la forme récente (max 35 points)"""
        score = 0
        
        # Buts encaissés (max 20 points)
        home_last5_against = self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'against', 'total'])
        away_last5_against = self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'against', 'total'])
        
        if home_last5_against > 8 or away_last5_against > 8:
            score += 20
        elif home_last5_against > 6 or away_last5_against > 6:
            score += 15
        elif home_last5_against > 4 or away_last5_against > 4:
            score += 10
        
        # Buts marqués (max 15 points)
        home_last5_for = self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'for', 'total'])
        away_last5_for = self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'for', 'total'])
        
        if home_last5_for > 8 or away_last5_for > 8:
            score += 15
        elif home_last5_for > 6 or away_last5_for > 6:
            score += 10
        elif home_last5_for > 4 or away_last5_for > 4:
            score += 5
            
        return score

    def analyze_offensive_stats(self, prediction):
        """Analyse les statistiques offensives (max 25 points)"""
        score = 0
        
        # Moyenne de buts (max 15 points)
        home_goals_avg = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'average', 'total'])
        away_goals_avg = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'average', 'total'])
        
        if home_goals_avg > 1.6 and away_goals_avg > 1.6:
            score += 15
        elif home_goals_avg > 1.2 and away_goals_avg > 1.2:
            score += 10
        elif home_goals_avg > 1.0 and away_goals_avg > 1.0:
            score += 5

        # Over 2.5 (max 10 points)
        home_over25 = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'under_over', '2_5', 'over'])
        away_over25 = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'under_over', '2_5', 'over'])
        
        if home_over25 > 4 and away_over25 > 4:
            score += 10
        elif home_over25 > 2 and away_over25 > 2:
            score += 5
            
        return score

    def analyze_defensive_stats(self, prediction):
        """Analyse les statistiques défensives (max 25 points)"""
        score = 0
        
        # Moyenne de buts encaissés (max 15 points)
        home_against_avg = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'against', 'average', 'total'])
        away_against_avg = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'against', 'average', 'total'])
        
        if home_against_avg > 1.6 or away_against_avg > 1.6:
            score += 15
        elif home_against_avg > 1.3 or away_against_avg > 1.3:
            score += 10
        elif home_against_avg > 1.0 or away_against_avg > 1.0:
            score += 5

        # Clean sheets (max 10 points)
        home_clean_sheets = self.safe_get(prediction, ['teams', 'home', 'league', 'clean_sheet', 'total'])
        away_clean_sheets = self.safe_get(prediction, ['teams', 'away', 'league', 'clean_sheet', 'total'])
        
        if home_clean_sheets < 2 and away_clean_sheets < 2:
            score += 10
        elif home_clean_sheets < 4 and away_clean_sheets < 4:
            score += 5
            
        return score

    def analyze_comparisons(self, prediction):
        """Analyse les comparaisons d'équipes (max 15 points)"""
        score = 0
        
        home_att = self.safe_get(prediction, ['comparison', 'att', 'home'])
        away_att = self.safe_get(prediction, ['comparison', 'att', 'away'])
        
        if home_att > 60 and away_att > 40:
            score += 15
        elif home_att > 50 and away_att > 35:
            score += 10
        elif home_att > 40 and away_att > 30:
            score += 5
            
        return score

    def get_detailed_stats(self, prediction):
        """Récupère les statistiques détaillées pour le rapport"""
        return {
            "recent_form": {
                "home_last5_against": self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'against', 'total']),
                "away_last5_against": self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'against', 'total']),
                "home_last5_for": self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'for', 'total']),
                "away_last5_for": self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'for', 'total'])
            },
            "offensive": {
                "home_goals_avg": self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'average', 'total']),
                "away_goals_avg": self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'average', 'total'])
            },
            "defensive": {
                "home_against_avg": self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'against', 'average', 'total']),
                "away_against_avg": self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'against', 'average', 'total'])
            }
        }

    def handle(self, *args, **options):
        """Point d'entrée principal de la commande"""
        date = options['date']
        
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            self.stdout.write(self.style.ERROR('Format de date invalide. Utilisez YYYY-MM-DD'))
            return

        matches_ref = db.reference('matches')
        predictions_ref = db.reference('predictions')
        
        logger.info(f"Récupération des matchs pour le {date}...")
        matches = matches_ref.get()
        
        if not matches:
            logger.warning('Aucun match trouvé')
            return

        day_matches = {
            match_id: match_data
            for match_id, match_data in matches.items()
            if match_data.get('fixture', {}).get('date', '').split('T')[0] == date
        }

        if not day_matches:
            logger.warning(f'Aucun match trouvé pour le {date}')
            return

        logger.info(f"Analyse de {len(day_matches)} matchs...")
        
        for match_id, match_data in day_matches.items():
            fixture_id = str(match_data['fixture']['id'])
            match_info = f"{match_data['teams']['home']['name']} vs {match_data['teams']['away']['name']}"
            
            logger.info(f"\nAnalyse du match {match_info}...")
            
            btts_probabilities = self.calculate_btts_probability(match_data)
            
            if btts_probabilities:
                predictions_ref.child(fixture_id).update({
                    'btts': btts_probabilities,
                    'updated_at': datetime.datetime.now().isoformat()
                })
                
                self.stdout.write(self.style.SUCCESS(
                    f"Prédictions BTTS pour {match_info}:\n"
                    f"BTTS: Oui ({btts_probabilities['1']:.1%}), "
                    f"Non ({btts_probabilities['0']:.1%})"
                ))
            else:
                logger.warning(f"Impossible de calculer les probabilités pour {match_info}")

        logger.info(f'Prédictions terminées pour le {date}')