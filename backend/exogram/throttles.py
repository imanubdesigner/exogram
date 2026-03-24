from rest_framework.throttling import UserRateThrottle


class DefaultUserRateThrottle(UserRateThrottle):
    """
    Throttle por defecto para usuarios autenticados.

    Usa un scope explícito ('default_user') para poder ajustar la cuota
    global sin afectar otros scopes de UserRateThrottle más específicos.
    """

    scope = 'default_user'


class SearchThrottle(UserRateThrottle):
    """
    Throttle específico para búsqueda semántica.

    La inferencia ONNX es costosa (~470 MB de modelo, CPU-bound). Un límite
    explícito de 200/hour evita que un usuario acapare recursos de CPU
    del worker que procesa embeddings.
    """

    scope = 'search'
