from django.db import models
from django.contrib.auth.models import User

class EstadoJuego(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    estado = models.JSONField(default=list)
    x1 = models.IntegerField(null=True, blank=True)
    x2 = models.IntegerField(null=True, blank=True)
    puede_jugar = models.BooleanField(default=True)
    puntos = models.IntegerField(default=0)
    intentos = models.IntegerField(default=0)
    nivel = models.CharField(max_length=20, default='basico')  # opcional para guardar nivel

    def __str__(self):
        return f"{self.usuario.username} - Puntos: {self.puntos} - Intentos: {self.intentos}"


from django.db import models
from django.contrib.auth.models import User

class EstadisticasJugador(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    total_victorias = models.PositiveIntegerField(default=0)
    total_derrotas = models.PositiveIntegerField(default=0)
    partidas_jugadas = models.PositiveIntegerField(default=0)
    tiempo_total_segundos = models.PositiveIntegerField(default=0)  # Para calcular promedio
    nivel_mas_jugado = models.CharField(max_length=10, blank=True, null=True)

    def promedio_tiempo(self):
        if self.partidas_jugadas == 0:
            return 0
        return self.tiempo_total_segundos / self.partidas_jugadas
    
    def __str__(self):
        return f"{self.usuario.username} - Victorias: {self.total_victorias}, Derrotas: {self.total_derrotas}"
