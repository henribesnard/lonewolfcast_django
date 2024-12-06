from django.db import models


class Period(models.Model):
    first = models.IntegerField(null=True, blank=True)
    second = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"1st: {self.first}, 2nd: {self.second}"


class Venue(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        if self.name and self.city:
            return f"{self.name} ({self.city})"
        elif self.name:
            return self.name
        else:
            return "Unnamed Venue"


class Status(models.Model):
    short = models.CharField(max_length=10)
    long = models.CharField(max_length=255)
    elapsed = models.IntegerField(null=True, blank=True)
    extra = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.short} - {self.long}"


class League(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    logo = models.URLField()
    flag = models.URLField(null=True, blank=True)
    season = models.IntegerField()
    round = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.country})"


class Team(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    logo = models.URLField()
    winner = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.name


class Fixture(models.Model):
    id = models.IntegerField(primary_key=True)
    referee = models.CharField(max_length=255, null=True, blank=True)
    timezone = models.CharField(max_length=100)
    date = models.DateTimeField()
    timestamp = models.IntegerField()
    periods = models.ForeignKey(Period, on_delete=models.CASCADE, null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.CASCADE)

    def __str__(self):
        return f"Fixture {self.id}"


class Goals(models.Model):
    home = models.IntegerField(default=0, null=True, blank=True)
    away = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.home} - {self.away}"


class Score(models.Model):
    halftime = models.ForeignKey(Goals, related_name="halftime", on_delete=models.CASCADE, null=True, blank=True)
    fulltime = models.ForeignKey(Goals, related_name="fulltime", on_delete=models.CASCADE, null=True, blank=True)
    extratime = models.ForeignKey(Goals, related_name="extratime", on_delete=models.CASCADE, null=True, blank=True)
    penalty = models.ForeignKey(Goals, related_name="penalty", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"HT: {self.halftime}, FT: {self.fulltime}"


class Match(models.Model):
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    home_team = models.ForeignKey(Team, related_name="home_team", on_delete=models.CASCADE)
    away_team = models.ForeignKey(Team, related_name="away_team", on_delete=models.CASCADE)
    goals = models.ForeignKey(Goals, on_delete=models.CASCADE)
    score = models.ForeignKey(Score, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.home_team.name} vs {self.away_team.name}"

class Prediction(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name="prediction")
    predictions = models.JSONField(null=True, blank=True)  # Stocke les données du champ "predictions"
    comparison = models.JSONField(null=True, blank=True)  # Stocke les données du champ "comparison"
    h2h = models.JSONField(null=True, blank=True)  # Stocke les données du champ "h2h"

    created_at = models.DateTimeField(auto_now_add=True)  # Date de création
    updated_at = models.DateTimeField(auto_now=True)  # Date de mise à jour

    def __str__(self):
        return f"Prediction for Match {self.match.fixture.id}"

