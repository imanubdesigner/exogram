"""
Moderación automática de comentarios.

Nivel base: lista negra de palabras + heurísticas de toxicidad.
Nivel avanzado (futuro): TF-IDF + clasificador sklearn.

IMPORTANTE: Toda la moderación es LOCAL — cero datos enviados
a APIs externas de IA (Privacy by Design).
"""
import re
from typing import Tuple

# Lista de palabras/patrones tóxicos (nivel base)
# Se puede expandir según las necesidades de la comunidad
TOXIC_PATTERNS = [
    # Insultos directos
    r'\b(idiota|imbécil|estúpid[oa]|pelotud[oa]|bolud[oa])\b',
    r'\b(mierda|cagar|carajo)\b',
    # Discurso de odio
    r'\b(naz[i]|fasc[i]sta)\b',
    # Spam patterns
    r'(.)\1{10,}',  # 10+ caracteres repetidos
    r'\b(compra|gana dinero|hazte rico|click aquí)\b',
]

# Umbral de toxicidad: por encima de esto se rechaza automáticamente
TOXICITY_THRESHOLD = 0.7

# Umbral de revisión: entre este valor y TOXICITY_THRESHOLD queda 'pending'
REVIEW_THRESHOLD = 0.3


def analyze_toxicity(text: str) -> Tuple[float, str]:
    """
    Analiza la toxicidad de un texto.

    Args:
        text: Contenido a analizar

    Returns:
        (score, reason): Score 0.0-1.0 y razón si es tóxico
    """
    if not text or not text.strip():
        return 0.0, ''

    text_lower = text.lower().strip()
    score = 0.0
    reasons = []

    # Check contra patrones tóxicos
    for pattern in TOXIC_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            score += 0.3 * len(matches)
            reasons.append(f'Patrón detectado: {pattern[:30]}')

    # Spam por múltiples URLs (separadas o no).
    url_count = len(re.findall(r'https?://\S+', text_lower, re.IGNORECASE))
    if url_count >= 3:
        score += 0.3
        reasons.append(f'Spam detectado: {url_count} URLs')

    # Heurísticas adicionales
    # Demasiadas mayúsculas (gritando)
    if len(text) > 10:
        upper_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if upper_ratio > 0.7:
            score += 0.2
            reasons.append('Exceso de mayúsculas')

    # Texto muy corto y con signos de exclamación
    if len(text) < 20 and text.count('!') > 2:
        score += 0.15
        reasons.append('Mensaje agresivo corto')

    # Repetición excesiva de caracteres especiales
    if re.search(r'[!?]{4,}', text):
        score += 0.1
        reasons.append('Puntuación excesiva')

    # Cap score a 1.0
    score = min(score, 1.0)

    reason = '; '.join(reasons) if reasons else ''
    return score, reason


def moderate_comment(text: str) -> Tuple[str, float, str]:
    """
    Modera un comentario y determina su estado.

    Args:
        text: Contenido del comentario

    Returns:
        (status, score, reason):
        - status: 'approved', 'pending', o 'rejected'
        - score: score de toxicidad (0.0-1.0)
        - reason: razón si fue rechazado o marcado
    """
    score, reason = analyze_toxicity(text)

    if score >= TOXICITY_THRESHOLD:
        return 'rejected', score, reason
    elif score >= REVIEW_THRESHOLD:
        return 'pending', score, reason
    else:
        return 'approved', score, ''
