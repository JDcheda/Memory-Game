import random
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.conf import settings
from .models import EstadoJuego, EstadisticasJugador
from django.utils import timezone
from django.views.decorators.http import require_POST

IMAGENES = [
    "coco.png", "manzana.png", "limon.png", "naranja.png",
    "pera.png", "pina.png", "platano.png", "sandia.png"
]

INTENTOS_POR_DIFICULTAD = {
    'basico': 6,
    'medio': 4,
    'avanzado': 2,
}

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'juego/register.html', {'form': form})

@login_required
def seleccionar_dificultad(request):
    if request.method == 'POST':
        dificultad = request.POST.get('dificultad')
        if dificultad in INTENTOS_POR_DIFICULTAD:
            request.session['dificultad'] = dificultad

            # Reiniciar o crear estado de juego con intentos y nivel
            estado, creado = EstadoJuego.objects.get_or_create(usuario=request.user)
            estado.nivel = dificultad
            estado.intentos = INTENTOS_POR_DIFICULTAD[dificultad]
            estado.estado = []
            estado.x1 = None
            estado.x2 = None
            estado.puede_jugar = True
            estado.puntos = 0
            estado.save()

            return redirect('juego_memoria')

    return render(request, 'juego/dificultad.html')

@login_required
def juego_memoria(request):
    usuario = request.user
    estado, creado = EstadoJuego.objects.get_or_create(usuario=usuario)

    dificultad = request.session.get('dificultad')
    if not dificultad:
        return redirect('seleccionar_dificultad')

    intentos_maximos = INTENTOS_POR_DIFICULTAD.get(dificultad, 4)

    if creado or not estado.estado or all(c['descubierto'] for c in estado.estado):
        # Reinicia partida y establece intentos
        imagenes = IMAGENES * 2
        random.shuffle(imagenes)
        estado.estado = [{'imagen': img, 'mostrar': False, 'descubierto': False} for img in imagenes]
        estado.x1 = None
        estado.x2 = None
        estado.intentos = intentos_maximos
        estado.puntos = 0
        estado.puede_jugar = True
        estado.nivel = dificultad
        estado.save()

    if estado.intentos <= 0:
        from django.contrib import messages
        messages.error(request, "Perdiste, elige de nuevo tu nivel.")
        # Puedes eliminar estado o reiniciarlo
        estado.delete()
        return redirect('home')  # o 'seleccionar_dificultad'
    request.session['inicio_juego'] = timezone.now().isoformat()

    return render(request, 'juego/juego_ajax.html', {
        'cuadros': estado.estado,
        'puntos': estado.puntos,
        'intentos': estado.intentos,
        'nivel': dificultad,
        'mensaje': request.GET.get('mensaje', ''),
    })



@login_required
def juego_ajax(request):
    usuario = request.user
    estado = EstadoJuego.objects.get(usuario=usuario)

    if request.method == "POST":
        # Detectar si es una solicitud JSON
        tipo = request.POST.get('tipo')
        if not tipo and request.content_type == "application/json":
            import json
            body = json.loads(request.body)
            tipo = body.get("tipo")

        #  Manejo de tiempo agotado
        if tipo == 'tiempo_agotado':
            estado.puede_jugar = False
            estado.intentos = 0
            estado.save()
            from django.urls import reverse
            return JsonResponse({
                'status': 'perdio',
                'mensaje': 'Se te acabó el tiempo. ¡Has perdido!',
                'url_redirect': reverse('seleccionar_dificultad')
            })

        index = int(request.POST.get('index'))
        cuadros = estado.estado

        if not estado.puede_jugar or cuadros[index]['mostrar'] or cuadros[index]['descubierto']:
            return JsonResponse({'status': 'ignorado', 'puntos': estado.puntos, 'cuadros': cuadros, 'intentos': estado.intentos})

        cuadros[index]['mostrar'] = True

        if estado.x1 is None:
            estado.x1 = index
        else:
            estado.x2 = index
            i1 = estado.x1
            i2 = estado.x2

            if cuadros[i1]['imagen'] == cuadros[i2]['imagen']:
                cuadros[i1]['descubierto'] = True
                cuadros[i2]['descubierto'] = True
                estado.puntos += 10
                estado.x1 = None
                estado.x2 = None
                estado.puede_jugar = True

                if all(c['descubierto'] for c in cuadros):
                    # Ganó, reinicia el juego manteniendo puntos e intentos
                    imagenes = IMAGENES * 2
                    random.shuffle(imagenes)
                    nuevo_estado = [{'imagen': img, 'mostrar': False, 'descubierto': False} for img in imagenes]
                    estado.estado = nuevo_estado
                    estado.x1 = None
                    estado.x2 = None
                    estado.puede_jugar = True
                    estado.save()
                    # Calcular tiempo
                    inicio_juego = request.session.pop('inicio_juego', None)
                    tiempo_transcurrido = 0
                    if inicio_juego:
                     tiempo_inicio = timezone.datetime.fromisoformat(inicio_juego)
                     tiempo_transcurrido = int((timezone.now() - tiempo_inicio).total_seconds())
                    actualizar_estadisticas(usuario, gano=True, tiempo_transcurrido=tiempo_transcurrido)

                    return JsonResponse({
                        'status': 'gano',
                        'puntos': estado.puntos,
                        'intentos': estado.intentos,
                        'mensaje': '¡Ganaste! El juego se reinició para continuar acumulando puntos.',
                        'cuadros': nuevo_estado,
                        'reiniciado': True
                    })
            else:
                estado.intentos -= 1
                estado.puede_jugar = False
                if estado.intentos <= 0:
                    from django.contrib import messages
                    messages.error(request, "Perdiste, elige de nuevo tu nivel.")
                    # Calcular tiempo
                    inicio_juego = request.session.pop('inicio_juego', None)
                    tiempo_transcurrido = 0
                    if inicio_juego:
                        tiempo_inicio = timezone.datetime.fromisoformat(inicio_juego)
                        tiempo_transcurrido = int((timezone.now() - tiempo_inicio).total_seconds())

                        actualizar_estadisticas(usuario, gano=False, tiempo_transcurrido=tiempo_transcurrido)
                    estado.delete()
                    return JsonResponse({
                        'status': 'perdio',
                        'mensaje': 'Se acabaron tus intentos.',
                        'puntos': 0,
                        'intentos': 0,
                        'redirect': True,
                        'url_redirect': '/'
                    })

        estado.estado = cuadros
        estado.save()

        return JsonResponse({
            'status': 'ok',
            'cuadros': cuadros,
            'puntos': estado.puntos,
            'intentos': estado.intentos,
            'reiniciado': False
        })

    # Ocultar pares incorrectos después de delay (backend)
    if estado.x1 is not None and estado.x2 is not None and not estado.puede_jugar:
        cuadros = estado.estado
        cuadros[estado.x1]['mostrar'] = False
        cuadros[estado.x2]['mostrar'] = False
        estado.x1 = None
        estado.x2 = None
        estado.puede_jugar = True
        estado.estado = cuadros
        estado.save()

    return JsonResponse({
        'status': 'ok',
        'cuadros': estado.estado,
        'puntos': estado.puntos,
        'intentos': estado.intentos,
        'reiniciado': False
    })



@require_POST
@login_required
def reiniciar_juego(request):
    usuario = request.user
    estado = EstadoJuego.objects.get(usuario=usuario)

    imagenes = IMAGENES * 2
    random.shuffle(imagenes)
    estado.estado = [{'imagen': img, 'mostrar': False, 'descubierto': False} for img in imagenes]
    estado.x1 = None
    estado.x2 = None
    estado.puede_jugar = True
    estado.intentos = INTENTOS_POR_DIFICULTAD.get(estado.nivel, 4)
    estado.save()

    return JsonResponse({'status': 'reiniciado', 'mensaje': '¡Nuevo juego iniciado!'})

@login_required
def home(request):
    estado, _ = EstadoJuego.objects.get_or_create(usuario=request.user)
    mensaje = request.GET.get('mensaje', '')
    return render(request, 'juego/home.html', {
        'puntos': estado.puntos,
        'mensaje': mensaje,
    })

def actualizar_estadisticas(usuario, gano, tiempo_transcurrido):
     stats, _ = EstadisticasJugador.objects.get_or_create(usuario=usuario)

     stats.partidas_jugadas += 1
     stats.tiempo_total_segundos += tiempo_transcurrido

     if gano:
         stats.total_victorias += 1
     else:
         stats.total_derrotas += 1

#     # Nivel actual
     estado = EstadoJuego.objects.get(usuario=usuario)
     nivel_actual = estado.nivel

#     # Actualizar nivel más jugado (opcional y simple, solo si es diferente)
     if not stats.nivel_mas_jugado:
         stats.nivel_mas_jugado = nivel_actual
     else:
#         # puedes mejorar esto contando los niveles más jugados si quieres precisión
         pass
     stats.save()

@login_required
def perfil_usuario(request):
    stats, _ = EstadisticasJugador.objects.get_or_create(usuario=request.user)

    contexto = {
        'stats': stats,
        'promedio_tiempo': round(stats.promedio_tiempo(), 2)
    }
    return render(request, 'juego/perfil.html', contexto)


