from rest_framework.throttling import UserRateThrottle


class ChatPollingThrottle(UserRateThrottle):
    """
    Throttle específico para GET de detalle de hilo (polling).

    Evita penalizar a usuarios que dejan el chat abierto durante sesiones
    largas mientras mantenemos límites más estrictos en otros endpoints.
    """

    scope = 'chat_polling'
