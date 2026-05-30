/*
 * fast_image.c — Módulo nativo C para Pyrolist
 *
 * Compilar con:
 *   gcc -O3 -march=native -ffast-math -shared -fPIC \
 *       -o fast_image.so fast_image.c -lm
 *
 * Funciones exportadas:
 *   extract_n_colors()    — extrae N colores dominantes de píxeles RGB
 *   update_blobs()        — actualiza posiciones de blobs del fondo animado
 *   adjust_hsv()          — ajusta saturación y brillo de un color RGB
 *   average_center_zone() — promedia el color de la zona central de una imagen
 */

#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* ─── Utilidades internas ─────────────────────────────────────────────────── */

static void rgb_to_hsv(
    double r, double g, double b,
    double *h, double *s, double *v
) {
    double max = r > g ? (r > b ? r : b) : (g > b ? g : b);
    double min = r < g ? (r < b ? r : b) : (g < b ? g : b);
    double delta = max - min;

    *v = max;
    *s = (max > 0.0) ? (delta / max) : 0.0;

    if (delta < 1e-9) {
        *h = 0.0;
        return;
    }
    if (max == r)      *h = (g - b) / delta + (g < b ? 6.0 : 0.0);
    else if (max == g) *h = (b - r) / delta + 2.0;
    else               *h = (r - g) / delta + 4.0;
    *h /= 6.0;
}

static void hsv_to_rgb(
    double h, double s, double v,
    double *r, double *g, double *b
) {
    if (s < 1e-9) { *r = *g = *b = v; return; }
    int i = (int)(h * 6.0);
    double f = h * 6.0 - i;
    double p = v * (1.0 - s);
    double q = v * (1.0 - f * s);
    double t = v * (1.0 - (1.0 - f) * s);
    switch (i % 6) {
        case 0: *r=v; *g=t; *b=p; break;
        case 1: *r=q; *g=v; *b=p; break;
        case 2: *r=p; *g=v; *b=t; break;
        case 3: *r=p; *g=q; *b=v; break;
        case 4: *r=t; *g=p; *b=v; break;
        default:*r=v; *g=p; *b=q; break;
    }
}

/* ─── Función 1: extract_n_colors ─────────────────────────────────────────── */
/*
 * Extrae n_colors colores dominantes dividiendo la imagen en zonas horizontales.
 *
 * Parámetros:
 *   pixels      — bytes RGB raw de la imagen (sin padding, 3 bytes por píxel)
 *   width       — ancho de la imagen en píxeles
 *   height      — alto de la imagen en píxeles
 *   n_colors    — número de colores a extraer (típicamente 3)
 *   colors_out  — array de salida: n_colors * 3 bytes (r, g, b por cada color)
 */
void extract_n_colors(
    const uint8_t *pixels,
    int width,
    int height,
    int n_colors,
    uint8_t *colors_out
) {
    if (!pixels || !colors_out || width <= 0 || height <= 0 || n_colors <= 0)
        return;

    int zone_w = width / n_colors;
    if (zone_w < 1) zone_w = 1;

    for (int zone = 0; zone < n_colors; zone++) {
        int x0 = zone * zone_w;
        int x1 = (zone == n_colors - 1) ? width : x0 + zone_w;

        long r_sum = 0, g_sum = 0, b_sum = 0;
        long count = 0;

        for (int y = 0; y < height; y++) {
            for (int x = x0; x < x1; x++) {
                int idx = (y * width + x) * 3;
                r_sum += pixels[idx];
                g_sum += pixels[idx + 1];
                b_sum += pixels[idx + 2];
                count++;
            }
        }

        if (count > 0) {
            colors_out[zone * 3]     = (uint8_t)(r_sum / count);
            colors_out[zone * 3 + 1] = (uint8_t)(g_sum / count);
            colors_out[zone * 3 + 2] = (uint8_t)(b_sum / count);
        }
    }
}

/* ─── Función 2: average_center_zone ──────────────────────────────────────── */
/*
 * Promedia el color de la zona CENTRAL (25%-75%) de la imagen.
 * Equivale al bucle Python en themes.extract_dominant_color().
 * Más preciso que extract_n_colors para obtener el color de acento.
 *
 * Parámetros:
 *   pixels      — bytes RGB raw
 *   width, height — dimensiones
 *   out_r, out_g, out_b — color resultante
 */
void average_center_zone(
    const uint8_t *pixels,
    int width,
    int height,
    uint8_t *out_r,
    uint8_t *out_g,
    uint8_t *out_b
) {
    if (!pixels || width <= 0 || height <= 0) {
        *out_r = *out_g = *out_b = 128;
        return;
    }

    int y0 = height / 4;
    int y1 = height * 3 / 4;
    int x0 = width  / 4;
    int x1 = width  * 3 / 4;

    long r_sum = 0, g_sum = 0, b_sum = 0;
    long count = 0;

    for (int y = y0; y < y1; y++) {
        for (int x = x0; x < x1; x++) {
            int idx = (y * width + x) * 3;
            r_sum += pixels[idx];
            g_sum += pixels[idx + 1];
            b_sum += pixels[idx + 2];
            count++;
        }
    }

    if (count > 0) {
        *out_r = (uint8_t)(r_sum / count);
        *out_g = (uint8_t)(g_sum / count);
        *out_b = (uint8_t)(b_sum / count);
    } else {
        *out_r = *out_g = *out_b = 128;
    }
}

/* ─── Función 3: adjust_hsv ────────────────────────────────────────────────── */
/*
 * Ajusta saturación y brillo de un color RGB, con valores mínimos forzados.
 * Reemplaza el bloque colorsys de themes.extract_dominant_color().
 *
 * Parámetros:
 *   in_r, in_g, in_b       — color de entrada (0-255)
 *   min_saturation         — saturación mínima (0.0-1.0), ej: 0.5
 *   min_value              — brillo mínimo (0.0-1.0), ej: 0.6
 *   out_r, out_g, out_b    — color de salida (0-255)
 */
void adjust_hsv(
    uint8_t in_r,  uint8_t in_g,  uint8_t in_b,
    double min_saturation,
    double min_value,
    uint8_t *out_r, uint8_t *out_g, uint8_t *out_b
) {
    double r = in_r / 255.0;
    double g = in_g / 255.0;
    double b = in_b / 255.0;

    double h, s, v;
    rgb_to_hsv(r, g, b, &h, &s, &v);

    if (s < min_saturation) s = min_saturation;
    if (v < min_value)      v = min_value;

    double ro, go, bo;
    hsv_to_rgb(h, s, v, &ro, &go, &bo);

    *out_r = (uint8_t)(ro * 255.0 + 0.5);
    *out_g = (uint8_t)(go * 255.0 + 0.5);
    *out_b = (uint8_t)(bo * 255.0 + 0.5);
}

/* ─── Función 4: update_blobs ──────────────────────────────────────────────── */
/*
 * Actualiza posiciones de los blobs del fondo animado de Pyrolist.
 * Reemplaza el bucle Python en AmbientBackgroundWidget._on_anim_step().
 *
 * Parámetros:
 *   xs, ys           — posiciones actuales (modificadas in-place)
 *   target_xs/ys     — posiciones objetivo
 *   n                — número de blobs (típicamente 3)
 *   dt               — delta de movimiento (típicamente 0.005)
 *   threshold_sq     — umbral al cuadrado para "alcanzó el objetivo" (ej: 0.0025)
 *
 * Retorna: número de blobs que han alcanzado su objetivo
 */
int update_blobs(
    double *xs,
    double *ys,
    const double *target_xs,
    const double *target_ys,
    int n,
    double dt,
    double threshold_sq
) {
    int reached = 0;
    for (int i = 0; i < n; i++) {
        double dx = target_xs[i] - xs[i];
        double dy = target_ys[i] - ys[i];
        xs[i] += dx * dt;
        ys[i] += dy * dt;
        if (dx * dx + dy * dy < threshold_sq)
            reached++;
    }
    return reached;
}
