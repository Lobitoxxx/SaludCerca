package pe.saludcerca.backend.semantic;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.text.Normalizer;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Codificador semántico determinístico — espejo en Java de
 * {@code data/embedding_encoder.py} (mismo algoritmo, misma salida).
 *
 * <p>Algoritmo (idéntico a la versión Python):
 * <ol>
 *   <li>Normalizar y tokenizar el texto (NFKD → minúsculas → sin tildes → sin puntuación).</li>
 *   <li>Por cada n-grama de caracteres (n=1..4 con delimitadores {@code #}):</li>
 *   <li>{@code h = SHA-1(ngrama)[0:4]} como entero de 32 bits SIN signo.</li>
 *   <li>{@code v[h % 384] += +1} si {@code h} es par, {@code -1} si es impar.</li>
 *   <li>Normalizar L2. Texto vacío → vector uniforme {@code 1/sqrt(384)}.</li>
 * </ol>
 *
 * <p>El resultado es compatible con pgvector (dimensión fija 384) y con los
 * embeddings persistidos en la BD por el pipeline Python.
 */
public final class SemanticEncoder {

    public static final int DIMENSION = 384;

    private static final long UINT32_MASK = 0xFFFFFFFFL;
    private static final Pattern NON_ALNUM_WS = Pattern.compile("[^a-z0-9\\s]");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");

    private SemanticEncoder() {
    }

    /**
     * Convierte un texto en un vector L2-normalizado de {@code DIMENSION} dimensiones.
     */
    public static double[] embed(String texto) {
        double[] vector = new double[DIMENSION];
        for (String token : normalizar(texto).split(" ")) {
            if (token.isEmpty()) {
                continue;
            }
            for (String ngrama : ngramas(token)) {
                long h = hashUint32(ngrama);
                int idx = (int) (h % DIMENSION);
                vector[idx] += ((h & 1L) == 0L) ? 1.0 : -1.0;
            }
        }

        double norma = 0.0;
        for (double x : vector) {
            norma += x * x;
        }
        norma = Math.sqrt(norma);

        if (norma == 0.0) {
            // Vector nulo (texto vacío): vector uniforme normalizado
            double inv = 1.0 / Math.sqrt(DIMENSION);
            java.util.Arrays.fill(vector, inv);
            return vector;
        }
        for (int i = 0; i < vector.length; i++) {
            vector[i] /= norma;
        }
        return vector;
    }

    /**
     * Devuelve el embedding en formato literal de pgvector: {@code '[0.1,0.2,...]'}.
     */
    public static String embedPostgres(String texto) {
        double[] v = embed(texto);
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < v.length; i++) {
            if (i > 0) {
                sb.append(',');
            }
            sb.append(String.format(Locale.ROOT, "%.6f", v[i]));
        }
        return sb.append(']').toString();
    }

    /**
     * Normalización idéntica a Python: NFKD, minúsculas, sin marcas de
     * combinación, no-alfanuméricos a espacio y colapso de blancos.
     */
    static String normalizar(String texto) {
        String t = Normalizer.normalize(texto.toLowerCase(Locale.ROOT), Normalizer.Form.NFKD);
        StringBuilder sb = new StringBuilder(t.length());
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (Character.getType(c) != Character.NON_SPACING_MARK) {
                sb.append(c);
            }
        }
        String s = NON_ALNUM_WS.matcher(sb).replaceAll(" ");
        return WHITESPACE.matcher(s).replaceAll(" ").trim();
    }

    /** n-gramas de caracteres (n=1..4) del token con delimitadores {@code #}. */
    static Set<String> ngramas(String token) {
        String padded = "#" + token + "#";
        Set<String> set = new HashSet<>();
        for (int n = 1; n <= 4; n++) {
            for (int i = 0; i + n <= padded.length(); i++) {
                set.add(padded.substring(i, i + n));
            }
        }
        return set;
    }

    /** SHA-1 truncado a los primeros 4 bytes, big-endian, interpretado SIN signo. */
    static long hashUint32(String s) {
        byte[] digest = digestSha1(s);
        long h = ((long) (digest[0] & 0xFF) << 24)
                | ((long) (digest[1] & 0xFF) << 16)
                | ((long) (digest[2] & 0xFF) << 8)
                | (long) (digest[3] & 0xFF);
        return h & UINT32_MASK;
    }

    private static byte[] digestSha1(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-1");
            return md.digest(s.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-1 no disponible", e);
        }
    }
}
