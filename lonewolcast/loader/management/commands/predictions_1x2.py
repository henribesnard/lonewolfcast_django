from django.core.management.base import BaseCommand
from firebase_admin import db
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Calcule les probabilités de résultat (1X2) pour les matchs d\'une date donnée'

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
        """Récupère une valeur nested de manière sécurisée"""
        try:
            result = data
            for key in path:
                result = result[key]
            return self.safe_float(result)
        except (KeyError, TypeError, AttributeError):
            return default

    def calculate_match_probabilities(self, match_data):
        """Calcule les probabilités 1X2 pour un match"""
        try:
            prediction = match_data.get('prediction', {})
            if not prediction:
                logger.warning(f"Pas de données de prédiction pour le match {match_data.get('fixture', {}).get('id')}")
                return None

            scores = {
                'home': self.calculate_home_score(prediction),
                'draw': self.calculate_draw_score(prediction),
                'away': self.calculate_away_score(prediction)
            }

            # Log détaillé des scores
            self.stdout.write("\nDétail des scores:")
            self.stdout.write(f"Score domicile (max 100): {scores['home']}")
            self.stdout.write(f"Score nul (max 100): {scores['draw']}")
            self.stdout.write(f"Score extérieur (max 100): {scores['away']}")

            # Convertir en probabilités
            total = sum(scores.values())
            probabilities = {
                "1": round(scores['home'] / total, 3),
                "X": round(scores['draw'] / total, 3),
                "2": round(scores['away'] / total, 3),
                "details": {
                    "raw_scores": scores,
                    "stats": self.get_detailed_stats(prediction)
                }
            }

            return probabilities

        except Exception as e:
            logger.error(f"Erreur dans le calcul 1X2: {str(e)}")
            return None

    def calculate_home_score(self, prediction):
        """Calcule le score pour une victoire à domicile"""
        score = 0
        
        # Comparaisons (max 30 points)
        home_total = self.safe_get(prediction, ['comparison', 'total', 'home'])
        if home_total > 0.6:
            score += 30
        elif home_total > 0.5:
            score += 20
        elif home_total > 0.4:
            score += 10

        # Forme récente (max 25 points)
        home_form = self.safe_get(prediction, ['teams', 'home', 'last_5', 'form'])
        home_wins = self.safe_get(prediction, ['teams', 'home', 'league', 'fixtures', 'wins', 'total'])
        home_matches = self.safe_get(prediction, ['teams', 'home', 'league', 'fixtures', 'played', 'total'])
        
        if home_matches > 0:
            win_rate = home_wins / home_matches
            if win_rate > 0.6:
                score += 25
            elif win_rate > 0.5:
                score += 15
            elif win_rate > 0.4:
                score += 10

        # Performance offensive/défensive (max 25 points)
        home_goals_avg = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'average', 'total'])
        home_defense = self.safe_get(prediction, ['comparison', 'def', 'home'])
        
        if home_goals_avg > 2:
            score += 15
        elif home_goals_avg > 1.5:
            score += 10
        elif home_goals_avg > 1:
            score += 5

        if home_defense > 0.6:
            score += 10
        elif home_defense > 0.5:
            score += 5

        # Séries (max 20 points)
        home_streak = self.safe_get(prediction, ['teams', 'home', 'league', 'biggest', 'streak', 'wins'])
        if home_streak >= 3:
            score += 20
        elif home_streak >= 2:
            score += 10
        elif home_streak >= 1:
            score += 5

        return score

    def calculate_draw_score(self, prediction):
        """Calcule le score pour un match nul"""
        score = 0
        
        # Comparaisons proches (max 40 points)
        home_total = self.safe_get(prediction, ['comparison', 'total', 'home'])
        away_total = self.safe_get(prediction, ['comparison', 'total', 'away'])
        
        diff = abs(home_total - away_total)
        if diff < 0.1:
            score += 40
        elif diff < 0.2:
            score += 30
        elif diff < 0.3:
            score += 20

        # Statistiques similaires (max 40 points)
        home_goals_avg = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'average', 'total'])
        away_goals_avg = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'average', 'total'])
        
        goals_diff = abs(home_goals_avg - away_goals_avg)
        if goals_diff < 0.3:
            score += 40
        elif goals_diff < 0.5:
            score += 30
        elif goals_diff < 0.8:
            score += 20

        # Historique de nuls (max 20 points)
        home_draws = self.safe_get(prediction, ['teams', 'home', 'league', 'fixtures', 'draws', 'total'])
        away_draws = self.safe_get(prediction, ['teams', 'away', 'league', 'fixtures', 'draws', 'total'])
        
        if home_draws > 5 and away_draws > 5:
            score += 20
        elif home_draws > 3 and away_draws > 3:
            score += 10

        return score

    def calculate_away_score(self, prediction):
        """Calcule le score pour une victoire à l'extérieur"""
        score = 0
        
        # Comparaisons (max 30 points)
        away_total = self.safe_get(prediction, ['comparison', 'total', 'away'])
        if away_total > 0.6:
            score += 30
        elif away_total > 0.5:
            score += 20
        elif away_total > 0.4:
            score += 10

        # Forme récente (max 25 points)
        away_form = self.safe_get(prediction, ['teams', 'away', 'last_5', 'form'])
        away_wins = self.safe_get(prediction, ['teams', 'away', 'league', 'fixtures', 'wins', 'total'])
        away_matches = self.safe_get(prediction, ['teams', 'away', 'league', 'fixtures', 'played', 'total'])
        
        if away_matches > 0:
            win_rate = away_wins / away_matches
            if win_rate > 0.5:
                score += 25
            elif win_rate > 0.4:
                score += 15
            elif win_rate > 0.3:
                score += 10

        # Performance offensive/défensive (max 25 points)
        away_goals_avg = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'average', 'total'])
        away_defense = self.safe_get(prediction, ['comparison', 'def', 'away'])
        
        if away_goals_avg > 1.8:
            score += 15
        elif away_goals_avg > 1.3:
            score += 10
        elif away_goals_avg > 1:
            score += 5

        if away_defense > 0.55:
            score += 10
        elif away_defense > 0.45:
            score += 5

        # Séries (max 20 points)
        away_streak = self.safe_get(prediction, ['teams', 'away', 'league', 'biggest', 'streak', 'wins'])
        if away_streak >= 2:
            score += 20
        elif away_streak >= 1:
            score += 10

        return score

    def get_detailed_stats(self, prediction):
        """Récupère les statistiques détaillées"""
        return {
            "comparisons": {
                "home_total": self.safe_get(prediction, ['comparison', 'total', 'home']),
                "away_total": self.safe_get(prediction, ['comparison', 'total', 'away']),
                "home_defense": self.safe_get(prediction, ['comparison', 'def', 'home']),
                "away_defense": self.safe_get(prediction, ['comparison', 'def', 'away'])
            },
            "form": {
                "home_wins": self.safe_get(prediction, ['teams', 'home', 'league', 'fixtures', 'wins', 'total']),
                "away_wins": self.safe_get(prediction, ['teams', 'away', 'league', 'fixtures', 'wins', 'total']),
                "home_draws": self.safe_get(prediction, ['teams', 'home', 'league', 'fixtures', 'draws', 'total']),
                "away_draws": self.safe_get(prediction, ['teams', 'away', 'league', 'fixtures', 'draws', 'total'])
            },
            "performance": {
                "home_goals_avg": self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'average', 'total']),
                "away_goals_avg": self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'average', 'total'])
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
            
            result_probabilities = self.calculate_match_probabilities(match_data)
            
            if result_probabilities:
                predictions_ref.child(fixture_id).update({
                    'result': result_probabilities,
                    'updated_at': datetime.datetime.now().isoformat()
                })
                
                self.stdout.write(self.style.SUCCESS(
                    f"Prédictions 1X2 pour {match_info}:\n"
                    f"1: {result_probabilities['1']:.1%}, "
                    f"X: {result_probabilities['X']:.1%}, "
                    f"2: {result_probabilities['2']:.1%}"
                ))
            else:
                logger.warning(f"Impossible de calculer les probabilités pour {match_info}")

        logger.info(f'Prédictions terminées pour le {date}')
