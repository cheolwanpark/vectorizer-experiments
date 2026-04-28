#ifndef PARSEC_BAREMETAL_MATH_H
#define PARSEC_BAREMETAL_MATH_H

static inline double fabs(double value) {
    return value < 0.0 ? -value : value;
}

static inline float fabsf(float value) {
    return value < 0.0f ? -value : value;
}

static inline int parsec_floor_to_int(double value) {
    int whole = (int)value;
    if ((double)whole > value) {
        whole -= 1;
    }
    return whole;
}

static inline double parsec_scale_pow2(int exponent) {
    double result = 1.0;

    if (exponent >= 0) {
        for (int i = 0; i < exponent; ++i) {
            result *= 2.0;
        }
        return result;
    }
    for (int i = 0; i < -exponent; ++i) {
        result *= 0.5;
    }
    return result;
}

static inline double sqrt(double value) {
    double guess;

    if (value <= 0.0) {
        return 0.0;
    }
    guess = value > 1.0 ? value : 1.0;
    for (int i = 0; i < 16; ++i) {
        guess = 0.5 * (guess + (value / guess));
    }
    return guess;
}

static inline double exp(double value) {
    const double ln2 = 0.6931471805599453;
    int exponent;
    double reduced;
    double term;
    double sum;

    if (value > 88.0) {
        value = 88.0;
    } else if (value < -88.0) {
        value = -88.0;
    }

    exponent = parsec_floor_to_int((value / ln2) + (value >= 0.0 ? 0.5 : -0.5));
    reduced = value - ((double)exponent * ln2);
    term = 1.0;
    sum = 1.0;
    for (int i = 1; i <= 12; ++i) {
        term *= reduced / (double)i;
        sum += term;
    }
    return sum * parsec_scale_pow2(exponent);
}

static inline double log(double value) {
    const double ln2 = 0.6931471805599453;
    double mantissa;
    double y;
    double y2;
    double sum;
    int exponent = 0;

    if (value <= 0.0) {
        return -1.0e30;
    }

    mantissa = value;
    while (mantissa >= 2.0) {
        mantissa *= 0.5;
        exponent += 1;
    }
    while (mantissa < 1.0) {
        mantissa *= 2.0;
        exponent -= 1;
    }

    y = (mantissa - 1.0) / (mantissa + 1.0);
    y2 = y * y;
    sum = y;
    sum += (y * y2) / 3.0;
    sum += (y * y2 * y2) / 5.0;
    sum += (y * y2 * y2 * y2) / 7.0;
    sum += (y * y2 * y2 * y2 * y2) / 9.0;
    return (2.0 * sum) + ((double)exponent * ln2);
}

#endif
