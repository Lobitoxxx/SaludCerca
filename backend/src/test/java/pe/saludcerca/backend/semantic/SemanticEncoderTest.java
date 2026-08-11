package pe.saludcerca.backend.semantic;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;

/**
 * Verifica la reproducibilidad del {@link SemanticEncoder} Java contra la
 * implementación de referencia en Python ({@code data/embedding_encoder.py}).
 *
 * <p>Los valores esperados se generaron ejecutando el encoder Python:
 * {@code cos12 = 0.658356161831}, {@code cos13 = 0.537587202229}, etc.
 */
class SemanticEncoderTest {

    private static final double TOL = 1e-9;

    private static double coseno(double[] a, double[] b) {
        double s = 0.0;
        for (int i = 0; i < a.length; i++) {
            s += a[i] * b[i];
        }
        return s;
    }

    @Test
    void dimensionYNormalizacion() {
        double[] v = SemanticEncoder.embed("dolor de pecho y arritmia cardiaca");
        assertThat(v).hasSize(SemanticEncoder.DIMENSION);
        double norma = Math.sqrt(java.util.Arrays.stream(v).map(x -> x * x).sum());
        assertThat(norma).isCloseTo(1.0, within(TOL));
    }

    @Test
    void coincidenciaConReferenciaPython() {
        double[] v = SemanticEncoder.embed("dolor de pecho y arritmia cardiaca");
        double[] esperado = {
                0.0, -0.070710678119, 0.070710678119, 0.0, 0.141421356237,
                -0.070710678119, 0.0, 0.0, 0.0, 0.0};
        for (int i = 0; i < esperado.length; i++) {
            assertThat(v[i]).as("componente[%d]", i)
                    .isCloseTo(esperado[i], within(TOL));
        }
        assertThat(v[100]).isCloseTo(0.0, within(TOL));
        assertThat(v[101]).isCloseTo(0.0, within(TOL));
        assertThat(v[102]).isCloseTo(0.0, within(TOL));
        assertThat(v[103]).isCloseTo(0.0, within(TOL));
        assertThat(v[104]).isCloseTo(0.070710678119, within(TOL));
        assertThat(v[105]).isCloseTo(0.0, within(TOL));
    }

    @Test
    void relacionesSemanticasComoEnPython() {
        double[] v1 = SemanticEncoder.embed("dolor de pecho y arritmia cardiaca");
        double[] v2 = SemanticEncoder.embed("cardiologia atencion del corazon");
        double[] v3 = SemanticEncoder.embed("atencion dental limpieza de muelas");
        double cos12 = coseno(v1, v2);
        double cos13 = coseno(v1, v3);
        assertThat(cos12).isCloseTo(0.658356161831, within(1e-6));
        assertThat(cos13).isCloseTo(0.537587202229, within(1e-6));
        assertThat(cos12).isGreaterThan(cos13);
    }

    @Test
    void formatoPostgresYTextoVacio() {
        String literal = SemanticEncoder.embedPostgres("cardiologia");
        assertThat(literal).startsWith("[").endsWith("]");
        assertThat(literal.split(",")).hasSize(SemanticEncoder.DIMENSION);
        double[] vacio = SemanticEncoder.embed("   ");
        double esperado = 1.0 / Math.sqrt(SemanticEncoder.DIMENSION);
        assertThat(vacio[0]).isCloseTo(esperado, within(TOL));
    }
}
