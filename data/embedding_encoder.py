# ============================================================================
# SALUD CERCA - Codificador semántico (pgvector)
# ----------------------------------------------------------------------------
# Embeddings determinísticos basados en hashing de n-gramas de caracteres.
#
# Por qué este enfoque:
#   1. No requiere modelos externos ni GPU -> reproducible en cualquier aula.
#   2. Es independiente del idioma y robusto a errores tipográficos.
#   3. Produce VECTORES L2-normalizados de dimensión fija (384) compatibles con
#      pgvector y sus índices HNSW/IVFFlat.
#   4. Existe una implementación espejo en Java (SemanticEncoder.java) que usa
#      exactamente el mismo algoritmo (SHA-1 + módulo), garantizando que el
#      backend Spring Boot genere los MISMOS embeddings que el pipeline Python.
#
# En producción, este módulo se sustituye por un encoder real
# (p.ej. sentence-transformers / all-MiniLM-L6-v2) sin cambiar el esquema.
# ============================================================================

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

DIMENSION = 384

# Máscara para interpretar los 4 primeros bytes del digest como entero SIN signo
_UINT32_MASK = 0xFFFFFFFF


def _normalizar(texto: str) -> str:
    """Normaliza el texto: minúsculas, sin acentos y sin puntuación."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return " ".join(texto.split())


def _ngramas(token: str) -> set[str]:
    """Genera los n-gramas de caracteres (n=1..4) del token con delimitadores."""
    padded = f"#{token}#"
    ngrams: set[str] = set()
    for n in range(1, 5):
        for i in range(len(padded) - n + 1):
            ngrams.add(padded[i : i + n])
    return ngrams


def embed(texto: str) -> list[float]:
    """Convierte texto en un vector L2-normalizado de `DIMENSION` dimensiones.

    Algoritmo (idéntico a la versión Java `SemanticEncoder`):
      1. Normalizar y tokenizar el texto.
      2. Por cada n-grama: h = SHA-1(ngrama)[0:4] como entero sin signo.
      3. v[h % DIM] += +1 si h es par, -1 si es impar.
      4. Normalizar L2.
    """
    vector = [0.0] * DIMENSION
    for token in _normalizar(texto).split():
        for ngrama in _ngramas(token):
            digest = hashlib.sha1(ngrama.encode("utf-8")).digest()[:4]
            h = int.from_bytes(digest, "big") & _UINT32_MASK
            vector[h % DIMENSION] += 1.0 if (h & 1) == 0 else -1.0

    norma = math.sqrt(sum(x * x for x in vector))
    if norma == 0.0:
        # Vector nulo (texto vacío): vector uniforme normalizado
        inv = 1.0 / math.sqrt(DIMENSION)
        return [inv] * DIMENSION
    return [x / norma for x in vector]


def embed_postgres(texto: str) -> str:
    """Devuelve el embedding en formato literal de pgvector ('[0.1,0.2,...]')."""
    return "[" + ",".join(f"{v:.6f}" for v in embed(texto)) + "]"


if __name__ == "__main__":
    # Smoke test: textos semánticamente cercanos deben quedar cerca en el espacio
    a = embed("dolor de pecho y arritmia cardiaca")
    b = embed("cardiologia atencion del corazon")
    c = embed("atencion dental limpieza de muelas")
    cos = lambda x, y: sum(i * j for i, j in zip(x, y))
    print(f"sim(a,b) = {cos(a, b):.4f}   (cardio vs cardio)")
    print(f"sim(a,c) = {cos(a, c):.4f}   (cardio vs dental, debe ser menor)")
    assert cos(a, b) > cos(a, c), "El encoder debe agrupar conceptos relacionados"
    print(f"Dimensión = {DIMENSION}. OK")
