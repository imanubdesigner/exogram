"""
Generación de embeddings usando ONNX Runtime puro.

Modelo: paraphrase-multilingual-MiniLM-L12-v2 (Xenova/HuggingFace)
Formato: ONNX — sin dependencias de PyTorch/Transformers/SentencePiece.
Dimensiones: 384
Tamaño del archivo: ~470MB
"""
import logging
import threading
from pathlib import Path
from typing import List, Union

import numpy as np
import onnxruntime as ort
import requests
from tokenizers import Tokenizer

logger = logging.getLogger(__name__)


class EmbeddingModelUnavailable(RuntimeError):
    """El modelo ONNX no está disponible (descarga fallida o modelo corrupto)."""


# Lock para inicialización thread-safe del singleton
_model_lock = threading.Lock()
_model = None
_model_error: Exception | None = None


class PureONNXEmbeddingModel:
    """
    Modelo de embeddings usando ONNX Runtime puro.

    Modelo: paraphrase-multilingual-MiniLM-L12-v2
    - Multilingüe (50+ idiomas), incluyendo español
    - 384 dimensiones de salida
    - ~470MB en disco / ~1GB en RAM en runtime
    - Sin dependencias de PyTorch, Transformers o SentencePiece
    """

    # URLs del modelo multilingüe en HuggingFace (Xenova ONNX exports)
    MODEL_URL = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/onnx/model.onnx"
    TOKENIZER_URL = "https://huggingface.co/Xenova/paraphrase-multilingual-MiniLM-L12-v2/resolve/main/tokenizer.json"

    # Tamaños mínimos esperados para validar integridad de los archivos
    MIN_SIZES = {
        'paraphrase-multilingual-MiniLM-L12-v2.onnx': 400 * 1024 * 1024,  # 400MB mínimo (real: ~470MB)
        'tokenizer.json': 1 * 1024 * 1024,  # 1MB mínimo
    }

    def __init__(self, cache_dir: str = "./models_cache"):
        """
        Inicializa el modelo ONNX. Si los archivos no están en cache,
        los descarga desde HuggingFace.

        Args:
            cache_dir: Directorio donde cachear el modelo descargado
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.model_path = self.cache_dir / "paraphrase-multilingual-MiniLM-L12-v2.onnx"
        self.tokenizer_path = self.cache_dir / "tokenizer.json"

        self.session = None
        self.tokenizer = None
        self._load_model()

    def _download_file(self, url: str, dest: Path):
        """
        Descarga un archivo si no existe o está corrupto (incompleto).

        Usa timeout de (10s conexión, 300s por chunk de lectura) para evitar
        bloqueos indefinidos si el servidor frena la transferencia.
        """
        filename = dest.name
        min_size = self.MIN_SIZES.get(filename, 0)

        if dest.exists():
            actual_size = dest.stat().st_size
            if actual_size >= min_size:
                logger.info(f"Usando modelo cacheado {dest} ({actual_size // 1024 // 1024}MB)")
                return
            else:
                logger.warning(
                    f"Archivo {dest} parece corrupto ({actual_size} bytes, mínimo esperado {min_size}). "
                    f"Eliminando y re-descargando..."
                )
                dest.unlink()

        logger.info(f"Descargando {url}...")
        logger.info("Esto puede tardar varios minutos (~470MB). No interrumpir.")

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(url, stream=True, timeout=(10, 300))
                response.raise_for_status()

                downloaded = 0
                with open(dest, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if downloaded % (50 * 1024 * 1024) == 0:
                                logger.info(f"  Descargado: {downloaded // 1024 // 1024}MB...")

                final_size = dest.stat().st_size
                logger.info(f"Descarga completa: {dest} ({final_size // 1024 // 1024}MB)")

                if final_size < min_size:
                    dest.unlink()
                    raise RuntimeError(
                        f"Descarga incompleta: {final_size} bytes (mínimo esperado: {min_size}). "
                        f"Verificá tu conexión e intentá de nuevo."
                    )
                return  # éxito

            except Exception as e:
                if dest.exists():
                    dest.unlink()
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"Descarga fallida (intento {attempt}/{max_retries}), reintentando en {wait}s: {e}")
                    import time
                    time.sleep(wait)
                else:
                    raise EmbeddingModelUnavailable(
                        f"No se pudo descargar el modelo desde {url} tras {max_retries} intentos: {e}"
                    ) from e

    def _load_model(self):
        """Descarga (si es necesario) y carga el modelo ONNX + tokenizer."""
        try:
            self._download_file(self.MODEL_URL, self.model_path)
            self._download_file(self.TOKENIZER_URL, self.tokenizer_path)

            # Limitar threads internos de ONNX Runtime para no saturar el CPU
            # en un entorno Docker compartido con otros procesos.
            # 2 threads es suficiente para throughput razonable sin congelar el host.
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 2
            sess_options.inter_op_num_threads = 1

            logger.info("Cargando sesión ONNX...")
            self.session = ort.InferenceSession(
                str(self.model_path),
                sess_options=sess_options,
                providers=['CPUExecutionProvider']
            )

            # Tokenizer de Rust — ultra rápido, sin overhead de Python
            self.tokenizer = Tokenizer.from_file(str(self.tokenizer_path))

            logger.info("Modelo paraphrase-multilingual-MiniLM-L12-v2 cargado correctamente.")

        except EmbeddingModelUnavailable:
            raise  # propagate as-is
        except Exception as e:
            logger.error(f"Error cargando el modelo ONNX: {e}")
            raise EmbeddingModelUnavailable(f"No se pudo cargar el modelo ONNX: {e}") from e

    def _tokenize(self, text: str, max_length: int = 128) -> dict:
        """
        Tokeniza un texto usando el tokenizer HuggingFace nativo (Rust).

        Args:
            text: Texto a tokenizar
            max_length: Longitud máxima de la secuencia (trunca y padea)

        Returns:
            dict con 'input_ids' y 'attention_mask' como arrays numpy int64
        """
        encoding = self.tokenizer.encode(text)

        # Truncar al máximo
        ids = encoding.ids[:max_length]
        mask = encoding.attention_mask[:max_length]

        # Padding con token 0
        pad_len = max_length - len(ids)
        ids = ids + [0] * pad_len
        mask = mask + [0] * pad_len

        return {
            'input_ids': np.array([ids], dtype=np.int64),
            'attention_mask': np.array([mask], dtype=np.int64),
        }

    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Genera embeddings de 384 dimensiones para uno o más textos.

        Args:
            texts: Texto o lista de textos
            normalize: Si True, normaliza los vectores (recomendado para cosine similarity)

        Returns:
            Array numpy de shape (n_texts, 384)
        """
        if isinstance(texts, str):
            texts = [texts]

        embeddings = []

        for text in texts:
            inputs = self._tokenize(text)

            inputs_onnx = {
                'input_ids': inputs['input_ids'],
                'attention_mask': inputs['attention_mask'],
            }

            # Algunos exports de Xenova requieren token_type_ids
            input_names = [i.name for i in self.session.get_inputs()]
            if 'token_type_ids' in input_names:
                inputs_onnx['token_type_ids'] = np.zeros_like(inputs['input_ids'])

            outputs = self.session.run(None, inputs_onnx)

            # Mean pooling ponderado por attention mask
            token_embeddings = outputs[0][0]  # [seq_len, hidden_size]
            attention_mask = inputs['attention_mask'][0]

            mask_expanded = np.expand_dims(attention_mask, -1).astype(float)
            sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=0)
            sum_mask = np.sum(mask_expanded, axis=0)
            embedding = sum_embeddings / np.maximum(sum_mask, 1e-9)

            embeddings.append(embedding)

        embeddings = np.array(embeddings)

        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / np.maximum(norms, 1e-9)

        return embeddings


def get_model() -> PureONNXEmbeddingModel:
    """
    Retorna el modelo ONNX con inicialización lazy por proceso.

    Si la carga falla, la excepción se cachea para no reintentar en cada tarea.
    Para reiniciar el proceso de carga, reiniciar el worker Celery.
    """
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error is not None:
        raise _model_error
    with _model_lock:
        if _model is not None:
            return _model
        if _model_error is not None:
            raise _model_error
        try:
            _model = PureONNXEmbeddingModel()
        except EmbeddingModelUnavailable as e:
            _model_error = e
            raise
    return _model


def get_embedding_model() -> PureONNXEmbeddingModel:
    """Alias retrocompatible para callers existentes."""
    return get_model()


def encode_text(text: str) -> np.ndarray:
    """
    Genera el embedding de un texto.

    Args:
        text: Texto a codificar

    Returns:
        Vector numpy de 384 dimensiones normalizado
    """
    model = get_model()
    return model.encode(text)[0]


def encode_batch(texts: List[str]) -> np.ndarray:
    """
    Genera embeddings para una lista de textos.

    Args:
        texts: Lista de textos

    Returns:
        Array numpy de shape (len(texts), 384)
    """
    model = get_model()
    return model.encode(texts)
