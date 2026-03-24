# 0003 — ONNX Runtime local para embeddings en lugar de API externa


## Contexto

Para generar los embeddings vectoriales de los highlights se necesita un modelo de
lenguaje que convierta texto a vectores numéricos. Las opciones son: llamar a una
API externa (OpenAI, Cohere, etc.) o correr un modelo localmente.

## Decisión

Usar **ONNX Runtime** con el modelo `paraphrase-multilingual-MiniLM-L12-v2` descargado
localmente. El modelo se ejecuta en el worker de Celery sin conexión a internet.

Características del modelo elegido:
- 384 dimensiones
- Multilingüe (50+ idiomas, crítico para highlights en español)
- ~470 MB en formato ONNX
- Latencia ~50ms por texto en CPU

## Alternativas consideradas

**OpenAI text-embedding-ada-002 / text-embedding-3-small:** calidad alta, cero infraestructura,
pero costo por token que escala con el uso, dependencia de un servicio externo, y los datos
de los usuarios (sus highlights, notas personales) saldrían del sistema. Descartado por
privacidad y costo.

**sentence-transformers (PyTorch):** mismo modelo pero cargado con la librería de Hugging Face.
Requiere PyTorch (~1.5 GB de dependencias). ONNX Runtime es el runtime sin PyTorch:
el modelo está pre-convertido al formato ONNX. Descartado PyTorch por el tamaño de la imagen.

**Llamadas síncronas en el request:** generar el embedding en el momento del upload
bloquearía el request ~50ms por texto. Descartado: los embeddings se generan de forma
asíncrona en Celery.

## Consecuencias

- Los highlights de los usuarios nunca salen del sistema para ser procesados. Privacidad total.
- Costo de embeddings: cero por query.
- El worker de Celery requiere ~1 GB de RAM extra para cargar el modelo (configurado con `mem_limit: 3g` en docker-compose).
- El modelo (~470 MB) se persiste en el volumen `models_cache` para no descargarlo en cada restart.
- El management command `download_onnx_model` permite precargarlo manualmente.
- Si el modelo no está disponible (volumen vacío, primer start), `EmbeddingModelUnavailable` es manejado gracefully: la tarea devuelve un warning en lugar de fallar. Los highlights quedan sin embedding hasta que el modelo esté disponible.
- La tokenización usa la librería `tokenizers` de Hugging Face (Rust, liviana) sin necesidad de PyTorch.
