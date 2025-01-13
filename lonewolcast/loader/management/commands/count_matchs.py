from django.core.management.base import BaseCommand
from firebase_admin import db
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Compter les matchs dans Firebase avec différentes options de filtrage."

    FINISHED_STATUSES = {'FT', 'AET', 'PEN'}  # Statuts des matchs terminés

    def add_arguments(self, parser):
        # Les options sont mutuellement exclusives pour le comptage global
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--all',
            action='store_true',
            help='Compter tous les matchs'
        )

        # Arguments optionnels pour filtrer
        parser.add_argument(
            '--league',
            type=int,
            help="Spécifier l'ID de la ligue"
        )
        parser.add_argument(
            '--season',
            type=int,
            help="Spécifier l'année de la saison"
        )
        parser.add_argument(
            '--team',
            type=int,
            help="Spécifier l'ID de l'équipe"
        )
        parser.add_argument(
            '--finished',
            action='store_true',
            help='Ne compter que les matchs terminés (FT, AET, PEN)'
        )

    def is_match_finished(self, match_data):
        """Vérifie si un match est terminé."""
        return match_data.get('metadata', {}).get('status') in self.FINISHED_STATUSES

    def is_team_match(self, match_data, team_id, team_location='all'):
        """Vérifie si un match concerne une équipe spécifique."""
        teams = match_data.get('teams', {})
        home_team = teams.get('home', {}).get('id')
        away_team = teams.get('away', {}).get('id')

        if not home_team or not away_team:
            return False

        if team_location == 'home':
            return home_team == team_id
        elif team_location == 'away':
            return away_team == team_id
        else:  # 'all'
            return home_team == team_id or away_team == team_id

    def count_matches(self, all_nodes, league_id=None, season=None, team_id=None, finished=False):
        root_ref = db.reference('matches')
        matches = root_ref.get() or {}
        total_count = 0

        try:
            if all_nodes:
                for season_key, season_data in matches.items():
                    if season and season_key != f'season_{season}':
                        continue

                    for league_key, league_data in season_data.items():
                        if league_id and league_key != f'league_{league_id}':
                            continue

                        fixtures = league_data.get('fixtures', {})
                        for match_key, match_data in fixtures.items():
                            if finished and not self.is_match_finished(match_data):
                                continue
                            if team_id and not self.is_team_match(match_data, team_id):
                                continue
                            total_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Total des matchs{' terminés' if finished else ''}{f' pour l\'équipe {team_id}' if team_id else ''}: {total_count}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR("Aucune option valide fournie. Utilisez --all pour compter les matchs.")
                )

            return total_count

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors du comptage des matchs: {str(e)}")
            )
            return 0

    def handle(self, *args, **options):
        """Point d'entrée de la commande."""
        try:
            count = self.count_matches(
                options['all'],
                league_id=options.get('league'),
                season=options.get('season'),
                team_id=options.get('team'),
                finished=options.get('finished', False)
            )

            if count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nOpération terminée avec succès. "
                        f"Total: {count} matchs{' terminés' if options.get('finished') else ''}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Aucun match trouvé avec les critères spécifiés")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors de l'exécution de la commande: {str(e)}")
            )
