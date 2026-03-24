"""
Tests para el parser de Kindle My Clippings.txt.
"""
from django.test import TestCase

from books.parsers.kindle_parser import KindleClippingsParser


class KindleParserTest(TestCase):
    def setUp(self):
        self.sample_clippings = """Cosmos (Carl Sagan)
- Your Highlight on Location 42-45 | Added on Monday, February 10, 2025 6:30:00 PM

The cosmos is all that is or was or ever will be.
==========
Cosmos (Carl Sagan)
- Your Highlight on Location 100-102 | Added on Monday, February 10, 2025 7:00:00 PM

Somewhere, something incredible is waiting to be known.
==========
Contact (Carl Sagan)
- Your Highlight on Location 200-205 | Added on Tuesday, February 11, 2025 8:00:00 AM

The universe is a pretty big place. If it's just us, seems like an awful waste of space.
=========="""

    def test_parse_basic(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        self.assertEqual(len(results), 3)

    def test_parse_book_title(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        self.assertEqual(results[0]['title'], 'Cosmos')

    def test_parse_author(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        self.assertEqual(results[0]['author'], 'Carl Sagan')

    def test_parse_content(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        self.assertIn('The cosmos is all that is', results[0]['content'])

    def test_parse_location(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        self.assertIn('42', results[0]['location'])

    def test_parse_multiple_books(self):
        parser = KindleClippingsParser()
        results = parser.parse(self.sample_clippings)
        titles = set(r['title'] for r in results)
        self.assertEqual(len(titles), 2)
        self.assertIn('Cosmos', titles)
        self.assertIn('Contact', titles)

    def test_parse_empty(self):
        parser = KindleClippingsParser()
        results = parser.parse('')
        self.assertEqual(len(results), 0)

    def test_parse_malformed(self):
        parser = KindleClippingsParser()
        results = parser.parse('Some random text\n==========\n')
        self.assertEqual(len(results), 0)

    def test_parse_note_associated_with_highlight(self):
        clip = """El Mundo (Autor)
- Tu resaltado en la página 10 | Añadido el lunes, 10 de febrero de 2026 10:00:00

Este es el texto del subrayado.
==========
El Mundo (Autor)
- Tu nota en la página 10 | Añadido el lunes, 10 de febrero de 2026 10:05:00

Esta es una nota sobre el texto.
=========="""
        parser = KindleClippingsParser()
        results = parser.parse(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'Este es el texto del subrayado.')
        self.assertEqual(results[0]['note'], 'Esta es una nota sobre el texto.')

    def test_parse_duplicate_and_expanded_highlight(self):
        clip = """El Mundo (Autor)
- Tu resaltado en la página 10 | Añadido el lunes, 10 de febrero de 2026 10:00:00

Este es el texto del sub.
==========
El Mundo (Autor)
- Tu resaltado en la página 10 | Añadido el lunes, 10 de febrero de 2026 10:05:00

Este es el texto del subrayado.
=========="""
        parser = KindleClippingsParser()
        results = parser.parse(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'Este es el texto del subrayado.')

    def test_parse_note_with_substring_location(self):
        clip = """Vigilancia permanente - Edward Snowden (Edward Snowden)
- Tu resaltado en la página 132 | posición 1664-1665 | Añadido el lunes, 16 de febrero de 2026 15:53:57

Declaración de Independencia del Ciberespacio de John Perry Barlow,
==========
Vigilancia permanente - Edward Snowden (Edward Snowden)
- La nota en la página 132 | posición 1665 | Añadido el lunes, 16 de febrero de 2026 15:54:19

bus
==========
Vigilancia permanente - Edward Snowden (Edward Snowden)
- La nota en la página 132 | posición 1665 | Añadido el lunes, 16 de febrero de 2026 15:54:23

Busca
==========
Vigilancia permanente - Edward Snowden (Edward Snowden)
- La nota en la página 132 | posición 1665 | Añadido el lunes, 16 de febrero de 2026 15:54:25

|
==========
Vigilancia permanente - Edward Snowden (Edward Snowden)
- La nota en la página 132 | posición 1665 | Añadido el lunes, 16 de febrero de 2026 15:54:27

Buscar.
=========="""
        parser = KindleClippingsParser()
        results = parser.parse(clip)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'Declaración de Independencia del Ciberespacio de John Perry Barlow,')
        self.assertIn('Buscar.', results[0]['note'])
