package pe.saludcerca.backend.service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import pe.saludcerca.backend.web.dto.RutaDto;

/**
 * Motor de rutas sobre Valhalla self-hosted (ADR-005, fase F-C2).
 * El ajuste fino por hora llegará con trafico_segmentos (telemetría de flota).
 */
@Service
public class RutaService {

    private static final List<String> COSTINGS_VALIDOS =
            List.of("auto", "bicycle", "pedestrian", "motorcycle");

    private final HttpClient http = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();
    private final ObjectMapper mapper = new ObjectMapper();
    private final String baseUrl;

    public RutaService(@Value("${app.valhalla.url}") String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public RutaDto ruta(double latOrigen, double lonOrigen,
                        double latDestino, double lonDestino,
                        String costing) {
        String c = (costing == null || costing.isBlank()) ? "auto" : costing.toLowerCase();
        if (!COSTINGS_VALIDOS.contains(c)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST,
                    "costing inválido: use auto|bicycle|pedestrian|motorcycle");
        }
        Map<String, Object> peticion = Map.of(
                "locations", List.of(
                        Map.of("lat", latOrigen, "lon", lonOrigen),
                        Map.of("lat", latDestino, "lon", lonDestino)),
                "costing", c,
                "directions_options", Map.of("units", "kilometers"));

        try {
            HttpRequest req = HttpRequest.newBuilder(URI.create(baseUrl + "/route"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(
                            mapper.writeValueAsString(peticion)))
                    .build();
            HttpResponse<String> resp =
                    http.send(req, HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() != 200) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY,
                        "Valhalla respondió " + resp.statusCode() + ": "
                                + truncar(resp.body()));
            }
            JsonNode trip = mapper.readTree(resp.body()).path("trip");
            JsonNode summary = trip.path("summary");
            return new RutaDto(
                    summary.path("length").asDouble(),
                    Math.round(summary.path("time").asDouble() / 6.0) / 10.0,
                    c,
                    decodificarPolyline6(trip.path("legs").get(0).path("shape").asText()));
        } catch (ResponseStatusException e) {
            throw e;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Consulta a Valhalla interrumpida");
        } catch (java.io.IOException | IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "No se pudo calcular la ruta: " + e.getMessage());
        }
    }

    private static String truncar(String s) {
        if (s == null) return "";
        return s.length() > 300 ? s.substring(0, 300) : s;
    }

    /** Decodifica encoded polyline precisión 6 (formato nativo de Valhalla) → [[lat,lon],...]. */
    static List<List<Double>> decodificarPolyline6(String shape) {
        var puntos = new ArrayList<List<Double>>();
        int i = 0;
        long lat = 0, lon = 0;
        long[] pos = new long[1];
        while (i < shape.length()) {
            lat += delta(shape, i, pos);
            i = (int) pos[0];
            lon += delta(shape, i, pos);
            i = (int) pos[0];
            puntos.add(List.of(lat * 1e-6, lon * 1e-6));
        }
        return puntos;
    }

    private static int delta(String s, int desde, long[] nuevaPos) {
        long resultado = 0, desplazamiento = 0;
        int i = desde, b;
        do {
            b = s.charAt(i++) - 63;
            resultado |= ((long) (b & 0x1f)) << desplazamiento;
            desplazamiento += 5;
        } while ((b & 0x20) != 0 && i < s.length());
        nuevaPos[0] = i;
        long valor = resultado >> 1;
        return (int) ((resultado & 1) != 0 ? ~valor : valor);
    }
}
