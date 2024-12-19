class MatchStatus:
    # Statuts des matchs programmés
    TBD = 'TBD'      # Time To Be Defined
    NS = 'NS'        # Not Started
    PST = 'PST'      # Postponed

    # Statuts des matchs en cours
    LIVE_STATUSES = {
        '1H',        # First Half
        'HT',        # Halftime
        '2H',        # Second Half
        'ET',        # Extra Time
        'BT',        # Break Time (during extra time)
        'P',         # Penalty In Progress
        'SUSP',      # Match Suspended
        'INT',       # Match Interrupted
        'LIVE'       # In Progress (rare cases)
    }

    # Statuts des matchs terminés
    FINISHED_STATUSES = {
        'FT',        # Regular time
        'AET',       # After extra time
        'PEN',       # After penalties
        'ABD',       # Abandoned
        'AWD',       # Technical Loss
        'WO',        # Walkover
        'CANC'       # Cancelled
    }

    @classmethod
    def is_live(cls, status):
        """Vérifie si le match est en cours."""
        return status in cls.LIVE_STATUSES

    @classmethod
    def is_finished(cls, status):
        """Vérifie si le match est terminé."""
        return status in cls.FINISHED_STATUSES

    @classmethod
    def is_scheduled(cls, status):
        """Vérifie si le match est programmé."""
        return status in {cls.TBD, cls.NS, cls.PST}