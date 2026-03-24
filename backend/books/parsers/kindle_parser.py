"""
Parser para archivos My Clippings.txt de Kindle.

Formato esperado:
```
El Mundo y Sus Demonios (Sagan, Carl)
- Tu subrayado en la página 45 | posición 678-680 | Añadido el martes, 15 de febrero de 2022 19:30:45

La ciencia es mucho más que un cuerpo de conocimiento. Es una manera de pensar.
==========
```
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class KindleClippingsParser:
    """Parser para archivos My Clippings.txt de Kindle."""

    SEPARATOR = "=========="

    def parse(self, file_content: str) -> List[Dict]:
        """
        Parsea el contenido completo del archivo.

        Args:
            file_content: Contenido del archivo My Clippings.txt

        Returns:
            Lista de highlights con estructura:
            {
                'title': str,
                'author': str,
                'content': str,
                'note': str,
                'location': str,
                'created_at': datetime
            }
        """
        raw_items = []
        entries = file_content.split(self.SEPARATOR)

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            try:
                item = self._parse_entry(entry)
                if item:
                    raw_items.append(item)
            except Exception as e:
                # Log error pero continúa parseando
                logger.warning("Error parsing Kindle clipping entry: %s", e)
                continue

        return self._process_raw_items(raw_items)

    def _parse_entry(self, entry: str) -> Optional[Dict]:
        """
        Parsea una entrada individual.

        Formato:
        Línea 1: Título (Autor)
        Línea 2: Metadatos
        Línea 3+: Contenido
        """
        lines = [line.strip() for line in entry.split('\n') if line.strip()]

        if len(lines) < 3:
            return None

        # Línea 1: Título y autor
        title, author = self._parse_title_author(lines[0])
        if not title:
            return None

        # Línea 2: Metadatos
        meta_line = lines[1]
        location, created_at = self._extract_metadata(meta_line)

        is_note = False
        if (re.search(r'-\s+(?:La|Tu)\s+nota', meta_line, re.IGNORECASE)
                or re.search(r'-\s+Your\s+Note', meta_line, re.IGNORECASE)):
            is_note = True

        # Línea 3+: Contenido
        content = '\n'.join(lines[2:]).strip()
        if not content:
            return None

        return {
            'title': title,
            'author': author,
            'content': content,
            'location': location,
            'created_at': created_at,
            'is_note': is_note
        }

    def _parse_title_author(self, line: str) -> Tuple[str, str]:
        """
        Parsea "Título (Autor)" -> (titulo, autor)

        Casos especiales:
        - Múltiples paréntesis: "El Arte de la Guerra (Sun Tzu (Traducción))"
        - Sin autor: "Documento sin autor"
        """
        # Buscar el último par de paréntesis
        line = line.lstrip('\ufeff').strip()
        match = re.search(r'^(.+?)\s*\(([^)]+)\)\s*$', line)

        if match:
            title = match.group(1).strip()
            author = match.group(2).strip()

            # Normalizar autor: "Sagan, Carl" -> "Carl Sagan"
            author = self._normalize_author(author)

            return title, author
        else:
            # No hay autor en paréntesis
            return line.strip(), "Unknown Author"

    def _normalize_author(self, author_str: str) -> str:
        """
        Normaliza formato de autor.

        "Sagan, Carl" -> "Carl Sagan"
        "Carl Sagan" -> "Carl Sagan"
        """
        if ',' in author_str and author_str.count(',') == 1:
            parts = author_str.split(',', 1)
            if len(parts) == 2:
                last, first = parts
                return f"{first.strip()} {last.strip()}"

        return author_str.strip()

    def _translate_spanish_date(self, date_str: str) -> str:
        """Traduce meses y días del español al inglés para el dateutil parser."""
        translations = {
            # Meses completos
            'enero': 'january', 'febrero': 'february', 'marzo': 'march',
            'abril': 'april', 'mayo': 'may', 'junio': 'june',
            'julio': 'july', 'agosto': 'august', 'septiembre': 'september',
            'octubre': 'october', 'noviembre': 'november', 'diciembre': 'december',
            # Abrev meses (comunes en Kindle)
            'ene': 'jan', 'feb': 'feb', 'abr': 'apr', 'jun': 'jun',
            'jul': 'jul', 'ago': 'aug', 'sep': 'sep', 'oct': 'oct', 'nov': 'nov', 'dic': 'dec',
            # Días completos
            'lunes': 'monday', 'martes': 'tuesday', 'miércoles': 'wednesday',
            'miercoles': 'wednesday', 'jueves': 'thursday', 'viernes': 'friday',
            'sábado': 'saturday', 'sabado': 'saturday', 'domingo': 'sunday',
            # Abrev días
            'lun': 'mon', 'mar': 'tue', 'mié': 'wed', 'mie': 'wed', 'jue': 'thu', 'vie': 'fri',
            'sáb': 'sat', 'sab': 'sat', 'dom': 'sun',
            # Conectores y otros
            ' de ': ' ',
            ' del ': ' '
        }

        # Limpiar puntuación común y normalizar
        date_str_lower = date_str.lower().replace('.', '').replace(',', '')

        # Reemplazar palabras (usamos expresiones regulares para evitar reemplazos parciales incorrectos)
        # pero para Kindle clippings el diccionario simple suele bastar si el orden es correcto
        # Primero las palabras más largas (diciembre antes de dic)
        sorted_keys = sorted(translations.keys(), key=len, reverse=True)
        for es in sorted_keys:
            if es in date_str_lower:
                date_str_lower = date_str_lower.replace(es, translations[es])

        return date_str_lower

    def _extract_metadata(self, line: str) -> Tuple[str, datetime]:
        """
        Extrae ubicación y fecha de la línea de metadatos.

        Formatos soportados:
        - "- Tu subrayado en la página 45 | Añadido el martes, 15 de febrero de 2022 19:30:45"
        - "- Your Highlight on page 45 | Added on Tuesday, February 15, 2022 7:30:45 PM"
        - "- Tu subrayado en la posición 678-680 | Añadido el ..."
        """
        location = "Unknown"
        created_at = datetime.now()

        # Extraer ubicación (página o posición)
        page_match = re.search(r'(?:página|page)\s+(\d+)', line, re.IGNORECASE)
        if page_match:
            location = f"Page {page_match.group(1)}"
        else:
            pos_match = re.search(r'(?:posición|location)\s+([\d-]+)', line, re.IGNORECASE)
            if pos_match:
                location = f"Loc {pos_match.group(1)}"

        # Extraer fecha
        # Buscar patrón después de "Añadido" o "Added"
        date_match = re.search(
            r'(?:Añadido|Added)\s+(?:el|on)\s+(.+?)(?:\s*\||$)',
            line,
            re.IGNORECASE
        )

        if date_match:
            date_str = date_match.group(1).strip()

            # Detectar idioma para el formato de fecha (MDY vs DMY)
            is_spanish = "añadido" in line.lower()

            # TRADUCCIÓN: Ayuda al parser si el texto está en español
            translated_date_str = self._translate_spanish_date(date_str) if is_spanish else date_str

            try:
                # dateutil.parser es muy robusto.
                # Si es español, día primero (15 de febrero).
                # Si es inglés US, mes primero (February 15).
                created_at = date_parser.parse(
                    translated_date_str,
                    fuzzy=True,
                    dayfirst=is_spanish
                )
            except Exception:
                logger.debug(
                    'No se pudo parsear fecha "%s", usando fecha actual como fallback',
                    translated_date_str,
                    exc_info=True,
                )
                created_at = datetime.now()

        return location, created_at

    def _process_raw_items(self, raw_items: List[Dict]) -> List[Dict]:
        """
        Procesa la lista cruda de items:
        - Agrupa por libro
        - Ordena cronológicamente
        - Deduplica highlights (mantiene el más largo cuando se superponen)
        - Asocia notas al highlight correspondiente
        """
        grouped = {}
        for item in raw_items:
            # Añadir campo note por defecto si no lo tiene
            if 'note' not in item:
                item['note'] = ''
            title = item['title']
            if title not in grouped:
                grouped[title] = []
            grouped[title].append(item)

        final_highlights = []

        for title, items in grouped.items():
            # Ordenar por fecha de creación
            items.sort(key=lambda x: x['created_at'])

            book_highlights = []

            for item in items:
                if item.get('is_note', False):
                    # Encontrar el highlight más reciente con la misma ubicación
                    # o simplemente el último highlight si no hay coincidencia exacta de ubicación
                    target_highlight = None
                    for h in reversed(book_highlights):
                        if h['location'] == item['location']:
                            target_highlight = h
                            break

                    if not target_highlight:
                        # Fallback: intentar ver si la ubicación de la nota forma parte de otra más larga
                        # Ej: Nota en "Loc 1665" pero Highlight en "Loc 1664-1665"
                        nota_loc_parts = item['location'].split()
                        if len(nota_loc_parts) > 1:
                            nota_num = nota_loc_parts[1]
                            for h in reversed(book_highlights):
                                h_loc_parts = h['location'].split()
                                if len(h_loc_parts) > 1 and nota_num in h_loc_parts[1]:
                                    target_highlight = h
                                    break

                    if not target_highlight and book_highlights:
                        target_highlight = book_highlights[-1]

                    if target_highlight:
                        prev_time = target_highlight.get('_last_note_time')
                        curr_time = item['created_at']
                        note_text = item['content'].strip()

                        is_incremental = (
                            prev_time and
                            (curr_time - prev_time).total_seconds() < 60 and
                            target_highlight.get('note')
                        )

                        if is_incremental:
                            target_highlight['note'] = note_text  # sobreescribe
                        else:
                            if target_highlight.get('note'):
                                target_highlight['note'] += f"\n\n{note_text}"
                            else:
                                target_highlight['note'] = note_text

                        target_highlight['_last_note_time'] = curr_time

                else:
                    # Eliminar is_note para que no vaya al modelo
                    item.pop('is_note', None)
                    book_highlights.append(item)

            # Segunda pasada para limpiar duplicados/extensiones
            dedup_highlights = []
            for h in book_highlights:
                # Comprobar si h es una extensión de un highlight existente o viceversa
                matched = False
                for existing in dedup_highlights:
                    # Si tienen textos muy similares, son probablemente el mismo
                    # Una forma simple es ver si uno contiene al otro, o si comparten el mismo inicio

                    is_match = False
                    # Normalizamos los textos para la comparación
                    t1 = existing['content'].strip()
                    t2 = h['content'].strip()

                    if t1 in t2 or t2 in t1:
                        is_match = True
                    else:
                        # Comprobar si comparten un prefijo significativo (ej: 80% del más corto)
                        min_len = min(len(t1), len(t2))
                        if min_len > 15:  # Solo comparar si tienen una longitud razonable
                            prefix_len = int(min_len * 0.8)
                            if t1[:prefix_len] == t2[:prefix_len]:
                                is_match = True

                    if is_match:
                        # h es una versión más larga (o igual).
                        if len(t2) > len(t1):
                            existing['content'] = t2
                            existing['location'] = h['location']
                            existing['created_at'] = h['created_at']

                        # Conservar nota (concatenando si hay conflicto)
                        if h['note']:
                            if existing['note']:
                                existing['note'] += f"\n\n{h['note']}"
                            else:
                                existing['note'] = h['note']

                        matched = True
                        break

                if not matched:
                    dedup_highlights.append(h)

            final_highlights.extend(dedup_highlights)

        return final_highlights


def group_by_book(highlights: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Agrupa highlights por libro.

    Args:
        highlights: Lista de highlights

    Returns:
        Dict con estructura:
        {
            'Book Title': [highlight1, highlight2, ...],
            ...
        }
    """
    grouped = {}

    for highlight in highlights:
        title = highlight['title']
        if title not in grouped:
            grouped[title] = []
        grouped[title].append(highlight)

    return grouped
