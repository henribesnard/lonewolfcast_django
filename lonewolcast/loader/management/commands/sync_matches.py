from django.core.management.base import BaseCommand
from loader.match_service import MatchService
from datetime import datetime

class Command(BaseCommand):
    help = """
    Gestion des matchs de football:
    
    Commandes disponibles:
        --sync              : Synchronise tous les matchs pour toutes les leagues et saisons configurées
        --update           : Met à jour uniquement les matchs non terminés
        --clear           : Supprime toutes les données
            options:
            --season YEAR   : Supprime une saison spécifique
            --league LEAGUE : Supprime une league spécifique (requiert --season)
            --force        : Ne pas demander de confirmation pour la suppression
    
    Exemples:
        python manage.py sync_matches --sync
        python manage.py sync_matches --update
        python manage.py sync_matches --clear --force
        python manage.py sync_matches --clear --season 2024
        python manage.py sync_matches --clear --season 2024 --league 39
    """

    def add_arguments(self, parser):
        # Groupe mutuellement exclusif pour les actions principales
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--sync',
            action='store_true',
            help='Synchronise tous les matchs'
        )
        group.add_argument(
            '--update',
            action='store_true',
            help='Met à jour les matchs non terminés'
        )
        group.add_argument(
            '--clear',
            action='store_true',
            help='Supprime des données'
        )

        # Arguments pour le nettoyage ciblé
        parser.add_argument(
            '--season',
            type=int,
            help='Année de la saison à supprimer'
        )
        parser.add_argument(
            '--league',
            type=int,
            help='ID de la league à supprimer (requiert --season)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ne pas demander de confirmation pour la suppression'
        )

    def handle(self, *args, **options):
        service = MatchService()

        try:
            if options['sync']:
                self.handle_sync(service)
            elif options['update']:
                self.handle_update(service)
            elif options['clear']:
                self.handle_clear(service, options)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Erreur: {str(e)}'))

    def handle_sync(self, service):
        """Gestion de la synchronisation complète."""
        self.stdout.write(self.style.HTTP_INFO('🔄 Début de la synchronisation...'))
        total = service.sync_all_matches()
        self.stdout.write(self.style.SUCCESS(f'✅ {total} match(s) synchronisé(s)'))

    def handle_update(self, service):
        """Gestion de la mise à jour des matchs non terminés."""
        self.stdout.write(self.style.HTTP_INFO('🔄 Mise à jour des matchs non terminés...'))
        updated = service.update_unfinished_matches()
        self.stdout.write(self.style.SUCCESS(f'✅ {updated} match(s) mis à jour'))

    def handle_clear(self, service, options):
        """Gestion de la suppression des données."""
        season = options.get('season')
        league = options.get('league')
        force = options.get('force')

        # Validation des arguments
        if league and not season:
            self.stderr.write(self.style.ERROR('--league requiert --season'))
            return

        # Construction du message de confirmation
        action = "toutes les données"
        if season:
            action = f"la saison {season}"
            if league:
                action += f" de la league {league}"

        # Demande de confirmation si --force n'est pas utilisé
        if not force:
            confirm = input(f'⚠️ Voulez-vous vraiment supprimer {action} ? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.SUCCESS('Opération annulée'))
                return

        # Exécution de la suppression
        self.stdout.write(self.style.WARNING(f'🗑️ Suppression de {action} en cours...'))
        success = False

        if league:
            success = service.clear_league(season, league)
        elif season:
            success = service.clear_season(season)
        else:
            success = service.clear_all()

        if success:
            self.stdout.write(self.style.SUCCESS('✅ Suppression réussie'))
        else:
            self.stderr.write(self.style.ERROR('❌ Erreur lors de la suppression'))