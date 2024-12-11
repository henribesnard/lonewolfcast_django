from django.core.management.base import BaseCommand
from firebase_admin import db
import datetime

class Command(BaseCommand):
    help = 'Calcule les probabilités BTTS pour les matchs d\'une date donnée'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str, help='Date au format YYYY-MM-DD')

    def safe_float(self, value, default=0.0):
        try:
            if isinstance(value, str):
                value = value.strip('%')
            return float(value)
        except (ValueError, TypeError, AttributeError):
            return default

    def safe_get(self, data, path, default=0.0):
        try:
            result = data
            for key in path:
                result = result[key]
            return self.safe_float(result)
        except (KeyError, TypeError, AttributeError):
            return default

    def calculate_btts_probability(self, match_data):
        try:
            base_probability = 52.3
            score_adjustments = 0
            
            prediction = match_data.get('prediction', {})
            if not prediction:
                self.stdout.write(self.style.WARNING(f"Pas de données de prédiction pour le match {match_data.get('fixture', {}).get('id')}"))
                return None

            # 1. Comparaison attaque/défense (±7%)
            home_att = self.safe_get(prediction, ['comparison', 'att', 'home'])
            away_att = self.safe_get(prediction, ['comparison', 'att', 'away'])
            home_def = self.safe_get(prediction, ['comparison', 'def', 'home'])
            away_def = self.safe_get(prediction, ['comparison', 'def', 'away'])
            
            self.stdout.write(f"Forces - Home: Att {home_att}% Def {home_def}%, Away: Att {away_att}% Def {away_def}%")
            
            if home_att > 60 and away_att > 40:
                score_adjustments += 7
            elif home_att > 50 and away_att > 35:
                score_adjustments += 4
            if home_def < 45 and away_def < 45:
                score_adjustments += 7
            elif home_def < 50 and away_def < 50:
                score_adjustments += 4
            if home_def > 65 or away_def > 65:
                score_adjustments -= 5

            # 2. Historique Over 2.5 (±6%)
            home_over25 = self.safe_get(prediction, ['teams', 'home', 'league', 'goals', 'for', 'under_over', '2_5', 'over'])
            away_over25 = self.safe_get(prediction, ['teams', 'away', 'league', 'goals', 'for', 'under_over', '2_5', 'over'])
            
            self.stdout.write(f"Over 2.5 - Home: {home_over25}, Away: {away_over25}")
            
            if home_over25 > 4 and away_over25 > 3:
                score_adjustments += 6
            elif home_over25 > 3 and away_over25 > 2:
                score_adjustments += 4
            elif home_over25 < 1 and away_over25 < 1:
                score_adjustments -= 6
            elif home_over25 < 2 and away_over25 < 2:
                score_adjustments -= 4

            # 3. Buts encaissés récents (±5%)
            home_against_avg = self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'against', 'average'])
            away_against_avg = self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'against', 'average'])
            
            self.stdout.write(f"Buts encaissés avg - Home: {home_against_avg}, Away: {away_against_avg}")
            
            if home_against_avg > 1.5 or away_against_avg > 1.5:
                score_adjustments += 5
            elif home_against_avg > 1.2 or away_against_avg > 1.2:
                score_adjustments += 3
            elif home_against_avg < 0.8 or away_against_avg < 0.8:
                score_adjustments -= 3
            elif home_against_avg < 0.5 or away_against_avg < 0.5:
                score_adjustments -= 5

            # 4. Force offensive récente (±5%)
            home_goals_avg = self.safe_get(prediction, ['teams', 'home', 'last_5', 'goals', 'for', 'average'])
            away_goals_avg = self.safe_get(prediction, ['teams', 'away', 'last_5', 'goals', 'for', 'average'])
            
            self.stdout.write(f"Buts marqués avg - Home: {home_goals_avg}, Away: {away_goals_avg}")
            
            if home_goals_avg > 1.5 and away_goals_avg > 1.5:
                score_adjustments += 5
            elif home_goals_avg > 1.2 or away_goals_avg > 1.2:
                score_adjustments += 3
            elif home_goals_avg < 0.8 and away_goals_avg < 0.8:
                score_adjustments -= 5
            elif home_goals_avg < 1.0 or away_goals_avg < 1.0:
                score_adjustments -= 3

            final_probability = base_probability + score_adjustments
            final_probability = max(min(final_probability, 100), 0)
            
            self.stdout.write(f"Ajustements: {score_adjustments}, Probabilité finale: {final_probability}")
            
            return {
                "1": round(final_probability / 100, 3),
                "0": round(1 - (final_probability / 100), 3)
            }
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur dans le calcul BTTS: {str(e)}"))
            return None

    def handle(self, *args, **options):
        date = options['date']
        
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            self.stdout.write(self.style.ERROR('Format de date invalide. Utilisez YYYY-MM-DD'))
            return

        matches_ref = db.reference('matches')
        predictions_ref = db.reference('predictions')
        
        self.stdout.write(f"Récupération des matchs pour le {date}...")
        matches = matches_ref.get()
        
        if not matches:
            self.stdout.write(self.style.WARNING('Aucun match trouvé'))
            return

        day_matches = {
            match_id: match_data
            for match_id, match_data in matches.items()
            if match_data.get('fixture', {}).get('date', '').split('T')[0] == date
        }

        if not day_matches:
            self.stdout.write(self.style.WARNING(f'Aucun match trouvé pour le {date}'))
            return

        self.stdout.write(f"Analyse de {len(day_matches)} matchs...")
        
        for match_id, match_data in day_matches.items():
            fixture_id = str(match_data['fixture']['id'])
            match_info = f"{match_data['teams']['home']['name']} vs {match_data['teams']['away']['name']}"
            
            self.stdout.write(f"\nAnalyse du match {match_info}...")
            
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
                self.stdout.write(self.style.WARNING(
                    f"Impossible de calculer les probabilités pour {match_info}"
                ))

        self.stdout.write(self.style.SUCCESS(f'Prédictions terminées pour le {date}'))