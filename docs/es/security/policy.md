# Política de Seguridad

## Versiones soportadas

| Versión | Soporte |
|---------|---------|
| `main` (última) | ✅ |
| Ramas anteriores | ❌ |

## Reportar una vulnerabilidad

**Por favor, no abras un Issue público de GitHub para reportar vulnerabilidades de seguridad.**

Reportá problemas de seguridad de forma privada a través de **GitHub Security Advisories**:

[Reportar una vulnerabilidad](https://github.com/matzalazar/exogram/security/advisories/new)

Incluí en tu reporte:
- Descripción de la vulnerabilidad y su impacto potencial
- Pasos para reproducirla (prueba de concepto si es posible)
- Componentes afectados (backend, frontend, infraestructura)
- Solución sugerida si la tenés

## Tiempos de respuesta

| Etapa | Objetivo |
|-------|----------|
| Confirmación de recepción | ≤ 48 horas |
| Evaluación inicial | ≤ 5 días hábiles |
| Corrección o mitigación | ≤ 30 días para críticas, ≤ 90 días para las demás |
| Divulgación pública | Coordinada con quien reportó, después del fix en producción |

## Alcance

En alcance:
- Autenticación y gestión de sesiones (app `accounts`)
- Manejo de tokens de invitación
- Controles de acceso a datos (visibilidad, modo hermit, autorización)
- Endpoints de la API y validación de inputs
- Configuración de infraestructura (Docker, Caddy, CI/CD)

Fuera de alcance:
- Ataques que requieren acceso físico al servidor
- Denegación de servicio por agotamiento de recursos
- Problemas en dependencias de terceros (reportalos upstream; nosotros hacemos seguimiento y actualizamos)
- Ataques de ingeniería social

## Política de divulgación

Seguimos divulgación coordinada. Te pedimos que nos des tiempo razonable para corregir el problema antes de publicar los detalles. Daremos crédito a quienes reportan en las notas de versión, salvo que prefieran mantenerse anónimos.
