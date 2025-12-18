import sympy as sp
import braille_processor

def _format_sympy_object(obj):
    """Converts a sympy object to a human-readable string, handling infinity."""
    if isinstance(obj, (sp.Infinity, sp.oo)):
        return "inf"
    elif isinstance(obj, (sp.NegativeInfinity, -sp.oo)):
        return "-inf"
    elif isinstance(obj, sp.Interval):
        # Format interval (e.g., (-oo, 0), [0, 1))
        left_bracket = '[' if not obj.left_open else '('
        right_bracket = ']' if not obj.right_open else ')'
        return f"{left_bracket}{_format_sympy_object(obj.start)}, {_format_sympy_object(obj.end)}{right_bracket}"
    elif isinstance(obj, (int, float, sp.Float, sp.Integer)):
        return f"{obj:.2f}"
    elif isinstance(obj, sp.Expr):
        return sp.pretty(obj)
    return str(obj)

def _format_list_of_sympy_objects(lst):
    """Formats a list of sympy objects for display."""
    return ", ".join([_format_sympy_object(item) for item in lst])

def get_function_analysis(function_data, language='spanish', dots_mode=6):
    """
    Analyzes a function based on the provided function_data and returns
    the analysis in a structured dictionary, and Braille format.
    """
    analysis_result = {}
    analysis_text_summary = ""

    if function_data['type'] == 'linear':
        analysis_result = analyze_linear_function(
            function_data['slope'], 
            function_data['intercept']
        )
        analysis_text_summary = analysis_result.get('summary_text', "Análisis de función lineal.")
    elif function_data['type'] == 'quadratic':
        analysis_result = analyze_quadratic_function(
            function_data['a'], 
            function_data['b'], 
            function_data['c']
        )
        analysis_text_summary = analysis_result.get('summary_text', "Análisis de función cuadrática.")
    elif function_data['type'] == 'cubic':
        analysis_result = analyze_cubic_function(
            function_data['a'], 
            function_data['b'], 
            function_data['c'], 
            function_data['d']
        )
        analysis_text_summary = analysis_result.get('summary_text', "Análisis de función cúbica.")
    elif function_data['type'] == 'polynomial':
        analysis_result = analyze_polynomial_function(
            function_data['coeffs']
        )
        analysis_text_summary = analysis_result.get('summary_text', "Análisis de función polinómica.")
    elif function_data['type'] == 'points':
        analysis_result = {"error": "Análisis de puntos no implementado aún."}
        analysis_text_summary = "Análisis de puntos no implementado aún."
    elif function_data['type'] == 'composite':
        analysis_result = analyze_composite_function(
            function_data['functions']
        )
        analysis_text_summary = analysis_result.get('summary_text', "Análisis de función compuesta.")
    else:
        analysis_result = {"error": "Tipo de función no reconocido para análisis."}
        analysis_text_summary = "Tipo de función no reconocido para análisis."

    braille_analysis = braille_processor.convert_text_to_braille(analysis_text_summary, language, dots_mode)
    
    return analysis_result, braille_analysis


def _get_roots(f, x):
    try:
        return sp.solve(f, x)
    except Exception:
        return []

def _get_derivatives(f, x, order=1):
    return sp.diff(f, x, order)

def _analyze_extrema(f, x, domain=sp.Reals):
    f_prime = _get_derivatives(f, x, 1)
    critical_points = sp.solve(f_prime, x)
    
    local_extrema = []
    absolute_extrema = []

    # Filter for real critical points within the domain
    real_critical_points = [p for p in critical_points if p.is_real and (p in domain or domain == sp.Reals)]
    
    if not real_critical_points:
        # Check for absolute extrema if the function is defined on a closed interval
        # For open/unbounded domains, often no absolute extrema unless it's a constant function or specific polynomial
        pass # More complex handling for absolute extrema on bounded domains needed

    else:
        f_double_prime = _get_derivatives(f, x, 2)
        for p in real_critical_points:
            try:
                second_deriv_val = f_double_prime.subs(x, p)
                if second_deriv_val > 0:
                    local_extrema.append({'type': 'min', 'x': p, 'y': f.subs(x, p)})
                elif second_deriv_val < 0:
                    local_extrema.append({'type': 'max', 'x': p, 'y': f.subs(x, p)})
            except Exception:
                # If second derivative test is inconclusive (e.g., value is 0),
                # one would typically use the first derivative test (sign change).
                # For simplicity, we'll omit that for now, focusing on clear cases.
                pass
    
    # Simple check for absolute extrema for polynomials:
    # Even degree polynomials might have absolute extrema
    # Odd degree polynomials generally do not have absolute extrema over Reals
    if f.is_polynomial(x):
        degree = sp.degree(f, x)
        if degree % 2 == 0 and sp.LC(f, x) > 0: # Even degree, leading coefficient positive
            # Global minimum exists
            if local_extrema:
                min_y = min([e['y'] for e in local_extrema if e['type'] == 'min'])
                for e in local_extrema:
                    if e['y'] == min_y and e['type'] == 'min':
                        absolute_extrema.append({'type': 'min', 'x': e['x'], 'y': e['y']})
        elif degree % 2 == 0 and sp.LC(f, x) < 0: # Even degree, leading coefficient negative
            # Global maximum exists
            if local_extrema:
                max_y = max([e['y'] for e in local_extrema if e['type'] == 'max'])
                for e in local_extrema:
                    if e['y'] == max_y and e['type'] == 'max':
                        absolute_extrema.append({'type': 'max', 'x': e['x'], 'y': e['y']})

    return local_extrema, absolute_extrema

def _analyze_inflection_points(f, x):
    f_double_prime = _get_derivatives(f, x, 2)
    inflection_candidates = sp.solve(f_double_prime, x)
    
    inflection_points = []
    
    # Filter for real candidates and check for sign change in f_double_prime
    real_inflection_candidates = [p for p in inflection_candidates if p.is_real]
    
    for p in real_inflection_candidates:
        # Check a point slightly to the left and right of p
        # Need to handle cases where p is at the boundary of a valid domain for test points
        try:
            # Pick a small epsilon, ensure test points are distinct and on either side
            epsilon = sp.Abs(p) / 100 if sp.Abs(p) > 0 else sp.Rational(1, 100)
            
            val_left = f_double_prime.subs(x, p - epsilon)
            val_right = f_double_prime.subs(x, p + epsilon)

            # Check for sign change and that neither is zero at test point (might be pole)
            if (val_left * val_right < 0): # Check for a sign change
                inflection_points.append({'x': p, 'y': f.subs(x, p)})
        except Exception:
            # Could be a non-differentiable point or other issue, skip for now
            pass
            
    return inflection_points


def _analyze_concavity(f, x, domain=sp.Reals):
    f_double_prime = _get_derivatives(f, x, 2)
    
    concave_intervals = []
    convex_intervals = []

    if f_double_prime == 0: # e.g., linear function
        return concave_intervals, convex_intervals

    # Solve inequalities to find where f_double_prime is positive/negative
    try:
        convex_regions = sp.solve_univariate_inequality(f_double_prime > 0, x, relational=False)
        concave_regions = sp.solve_univariate_inequality(f_double_prime < 0, x, relational=False)
        
        # Intersect with the function's domain
        convex_intervals = convex_regions.intersect(domain)
        concave_intervals = concave_regions.intersect(domain)

    except Exception:
        # Handle cases where sympy can't solve the inequality
        pass
        
    return concave_intervals, convex_intervals

def analyze_linear_function(slope, intercept):
    x = sp.Symbol('x')
    f = slope * x + intercept

    analysis = {
        'function_type': 'linear',
        'equation': f"y = {slope}x + {intercept}",
        'domain': "Todos los números reales",
        'continuity': "Continua en todo su dominio",
        'extrema': {"local": [], "absolute": []},
        'inflection_points': [],
        'concavity': {"concave_intervals": [], "convex_intervals": []},
        'image': "",
        'roots': [],
        'y_intercept': None,
        'monotonicity': {"increasing_intervals": [], "decreasing_intervals": []}
    }

    # Range
    if slope != 0:
        analysis['image'] = "Todos los números reales"
    else:
        analysis['image'] = f"y = {_format_sympy_object(intercept)}"

    # Roots
    analysis['roots'] = _get_roots(f, x)

    # Y-intercept
    analysis['y_intercept'] = f.subs(x, 0)

    # Monotonicity
    if slope > 0:
        analysis['monotonicity']['increasing_intervals'].append(sp.Interval(-sp.oo, sp.oo))
    elif slope < 0:
        analysis['monotonicity']['decreasing_intervals'].append(sp.Interval(-sp.oo, sp.oo))

    # Generate summary text for Braille conversion and initial display
    summary_parts = [
        f"Análisis de la función {analysis['equation']}",
        "-------------------------------------------------",
        f"Dominio: {analysis['domain']}",
        f"Imagen: {analysis['image']}",
        f"Continuidad: {analysis['continuity']}",
        f"Raíces (corte con el eje X): {_format_list_of_sympy_objects(analysis['roots'])}",
        f"Punto de corte con el eje Y: y = {_format_sympy_object(analysis['y_intercept'])}",
    ]
    
    if analysis['monotonicity']['increasing_intervals']:
        summary_parts.append(f"Monotonía: Creciente en {_format_list_of_sympy_objects(analysis['monotonicity']['increasing_intervals'])}")
    elif analysis['monotonicity']['decreasing_intervals']:
        summary_parts.append(f"Monotonía: Decreciente en {_format_list_of_sympy_objects(analysis['monotonicity']['decreasing_intervals'])}")
    else:
        summary_parts.append("Monotonía: La función es constante.")

    summary_parts.append("Extremos: No tiene máximos ni mínimos locales ni absolutos.")
    summary_parts.append("Concavidad: No tiene (es una línea recta).")
    summary_parts.append("Puntos de inflexión: No tiene.")

    analysis['summary_text'] = "\n".join(summary_parts)
    return analysis

def analyze_quadratic_function(a, b, c):
    x = sp.Symbol('x')
    f = a * x**2 + b * x + c

    analysis = {
        'function_type': 'quadratic',
        'equation': f"y = {a}x^2 + {b}x + {c}",
        'domain': "Todos los números reales",
        'continuity': "Continua en todo su dominio",
        'extrema': {"local": [], "absolute": []},
        'inflection_points': [],
        'concavity': {"concave_intervals": [], "convex_intervals": []},
        'image': "",
        'roots': [],
        'y_intercept': None,
        'monotonicity': {"increasing_intervals": [], "decreasing_intervals": []}
    }

    # Roots
    analysis['roots'] = _get_roots(f, x)

    # Y-intercept
    analysis['y_intercept'] = f.subs(x, 0)

    # Extrema
    local_extrema, absolute_extrema = _analyze_extrema(f, x)
    analysis['extrema']['local'] = local_extrema
    analysis['extrema']['absolute'] = absolute_extrema

    # Monotonicity
    f_prime = _get_derivatives(f, x, 1)
    critical_points = _get_roots(f_prime, x)
    real_critical_points = [p for p in critical_points if p.is_real]
    
    if real_critical_points:
        vertex_x = real_critical_points[0] # For quadratic, there's only one real critical point
        if a > 0: # Parabola opens upwards
            analysis['monotonicity']['decreasing_intervals'].append(sp.Interval(-sp.oo, vertex_x))
            analysis['monotonicity']['increasing_intervals'].append(sp.Interval(vertex_x, sp.oo))
        else: # Parabola opens downwards
            analysis['monotonicity']['increasing_intervals'].append(sp.Interval(-sp.oo, vertex_x))
            analysis['monotonicity']['decreasing_intervals'].append(sp.Interval(vertex_x, sp.oo))

    # Range
    if analysis['extrema']['absolute']:
        if analysis['extrema']['absolute'][0]['type'] == 'min':
            analysis['image'] = f"y >= {_format_sympy_object(analysis['extrema']['absolute'][0]['y'])}"
        else:
            analysis['image'] = f"y <= {_format_sympy_object(analysis['extrema']['absolute'][0]['y'])}"
    else:
        analysis['image'] = "Todos los números reales" # Should not happen for quadratic

    # Concavity
    concave_intervals, convex_intervals = _analyze_concavity(f, x)
    analysis['concavity']['concave_intervals'] = concave_intervals
    analysis['concavity']['convex_intervals'] = convex_intervals

    # Inflection points - quadratic functions do not have inflection points
    analysis['inflection_points'] = _analyze_inflection_points(f, x) # Should be empty

    # Generate summary text
    summary_parts = [
        f"Análisis de la función {analysis['equation']}",
        "-------------------------------------------------",
        f"Dominio: {analysis['domain']}",
        f"Imagen: {analysis['image']}",
        f"Continuidad: {analysis['continuity']}",
        f"Raíces (corte con el eje X): {_format_list_of_sympy_objects(analysis['roots'])}",
        f"Punto de corte con el eje Y: y = {_format_sympy_object(analysis['y_intercept'])}",
    ]

    if analysis['monotonicity']['increasing_intervals'] or analysis['monotonicity']['decreasing_intervals']:
        mono_str = "Monotonía: "
        if analysis['monotonicity']['increasing_intervals']:
            mono_str += f"Creciente en {_format_list_of_sympy_objects(analysis['monotonicity']['increasing_intervals'])}"
        if analysis['monotonicity']['decreasing_intervals']:
            if len(analysis['monotonicity']['increasing_intervals']) > 0:
                mono_str += ", "
            mono_str += f"Decreciente en {_format_list_of_sympy_objects(analysis['monotonicity']['decreasing_intervals'])}"
        summary_parts.append(mono_str)
    
    if analysis['extrema']['local'] or analysis['extrema']['absolute']:
        extrema_str = "Extremos: "
        if analysis['extrema']['local']:
            local_str = ", ".join([f"{e['type']} local en x={_format_sympy_object(e['x'])}, y={_format_sympy_object(e['y'])}" for e in analysis['extrema']['local']])
            extrema_str += f"Local: {local_str}"
        if analysis['extrema']['absolute']:
            absolute_str = ", ".join([f"{e['type']} absoluto en x={_format_sympy_object(e['x'])}, y={_format_sympy_object(e['y'])}" for e in analysis['extrema']['absolute']])
            extrema_str += f"Absoluto: {absolute_str}"
        summary_parts.append(extrema_str)

    if analysis['concavity']['concave_intervals'] or analysis['concavity']['convex_intervals']:
        concavity_str = "Concavidad: "
        if analysis['concavity']['concave_intervals']:
            concavity_str += f"Cóncava en {_format_list_of_sympy_objects(analysis['concavity']['concave_intervals'])}"
        if analysis['concavity']['convex_intervals']:
            if len(analysis['concavity']['concave_intervals']) > 0:
                concavity_str += ", "
            concavity_str += f"Convexa en {_format_list_of_sympy_objects(analysis['concavity']['convex_intervals'])}"
        summary_parts.append(concavity_str)

    if analysis['inflection_points']:
        inflection_str = "Puntos de inflexión: " + ", ".join([f"x={_format_sympy_object(p['x'])}, y={_format_sympy_object(p['y'])}" for p in analysis['inflection_points']])
        summary_parts.append(inflection_str)
    else:
        summary_parts.append("Puntos de inflexión: No tiene.")

    analysis['summary_text'] = "\n".join(summary_parts)
    return analysis

def analyze_cubic_function(a, b, c, d):
    x = sp.Symbol('x')
    f = a * x**3 + b * x**2 + c * x + d

    analysis = {
        'function_type': 'cubic',
        'equation': f"y = {a}x^3 + {b}x^2 + {c}x + {d}",
        'domain': "Todos los números reales",
        'continuity': "Continua en todo su dominio",
        'extrema': {"local": [], "absolute": []},
        'inflection_points': [],
        'concavity': {"concave_intervals": [], "convex_intervals": []},
        'image': "Todos los números reales", # Cubic functions always have range (-inf, inf)
        'roots': [],
        'y_intercept': None,
        'monotonicity': {"increasing_intervals": [], "decreasing_intervals": []}
    }

    # Roots
    analysis['roots'] = _get_roots(f, x)

    # Y-intercept
    analysis['y_intercept'] = f.subs(x, 0)

    # Extrema
    local_extrema, absolute_extrema = _analyze_extrema(f, x)
    analysis['extrema']['local'] = local_extrema
    analysis['extrema']['absolute'] = absolute_extrema # Cubic functions generally don't have absolute extrema over R

    # Monotonicity
    f_prime = _get_derivatives(f, x, 1)
    critical_points = _get_roots(f_prime, x)
    real_critical_points = sorted([p for p in critical_points if p.is_real])
    
    if real_critical_points:
        intervals = [(-sp.oo)] + real_critical_points + [(sp.oo)]
        for i in range(len(intervals) - 1):
            interval_start = intervals[i]
            interval_end = intervals[i+1]
            
            # Choose a test point within the interval
            if interval_start == -sp.oo and interval_end == sp.oo:
                test_point = 0
            elif interval_start == -sp.oo:
                test_point = interval_end - 1
            elif interval_end == sp.oo:
                test_point = interval_start + 1
            else:
                test_point = (interval_start + interval_end) / 2
            
            # Avoid division by zero if test_point is 0 and f_prime has x in denominator
            if test_point == 0: test_point = sp.S(1)/100 # Use a small non-zero value
            
            try:
                sign = f_prime.subs(x, test_point)
                if sign > 0:
                    analysis['monotonicity']['increasing_intervals'].append(sp.Interval(interval_start, interval_end))
                elif sign < 0:
                    analysis['monotonicity']['decreasing_intervals'].append(sp.Interval(interval_start, interval_end))
            except (ValueError, TypeError): # Handle cases where substitution fails (e.g., complex numbers, division by zero)
                pass # Skip interval if analysis fails


    # Concavity and Inflection points
    concave_intervals, convex_intervals = _analyze_concavity(f, x)
    analysis['concavity']['concave_intervals'] = concave_intervals
    analysis['concavity']['convex_intervals'] = convex_intervals
    analysis['inflection_points'] = _analyze_inflection_points(f, x)

    # Generate summary text
    summary_parts = [
        f"Análisis de la función {analysis['equation']}",
        "-------------------------------------------------",
        f"Dominio: {analysis['domain']}",
        f"Imagen: {analysis['image']}",
        f"Continuidad: {analysis['continuity']}",
        f"Raíces (corte con el eje X): {_format_list_of_sympy_objects(analysis['roots'])}",
        f"Punto de corte con el eje Y: y = {_format_sympy_object(analysis['y_intercept'])}",
    ]

    if analysis['monotonicity']['increasing_intervals'] or analysis['monotonicity']['decreasing_intervals']:
        mono_str = "Monotonía: "
        if analysis['monotonicity']['increasing_intervals']:
            mono_str += f"Creciente en {_format_list_of_sympy_objects(analysis['monotonicity']['increasing_intervals'])}"
        if analysis['monotonicity']['decreasing_intervals']:
            if len(analysis['monotonicity']['increasing_intervals']) > 0:
                mono_str += ", "
            mono_str += f"Decreciente en {_format_list_of_sympy_objects(analysis['monotonicity']['decreasing_intervals'])}"
        summary_parts.append(mono_str)
    
    if analysis['extrema']['local'] or analysis['extrema']['absolute']:
        extrema_str = "Extremos: "
        if analysis['extrema']['local']:
            local_str = ", ".join([f"{e['type']} local en x={_format_sympy_object(e['x'])}, y={_format_sympy_object(e['y'])}" for e in analysis['extrema']['local']])
            extrema_str += f"Local: {local_str}"
        if analysis['extrema']['absolute']:
            absolute_str = ", ".join([f"{e['type']} absoluto en x={_format_sympy_object(e['x'])}, y={_format_sympy_object(e['y'])}" for e in analysis['extrema']['absolute']])
            extrema_str += f"Absoluto: {absolute_str}"
        summary_parts.append(extrema_str)

    if analysis['concavity']['concave_intervals'] or analysis['concavity']['convex_intervals']:
        concavity_str = "Concavidad: "
        if analysis['concavity']['concave_intervals']:
            concavity_str += f"Cóncava en {_format_list_of_sympy_objects(analysis['concavity']['concave_intervals'])}"
        if analysis['concavity']['convex_intervals']:
            if len(analysis['concavity']['concave_intervals']) > 0:
                concavity_str += ", "
            concavity_str += f"Convexa en {_format_list_of_sympy_objects(analysis['concavity']['convex_intervals'])}"
        summary_parts.append(concavity_str)

    if analysis['inflection_points']:
        inflection_str = "Puntos de inflexión: " + ", ".join([f"x={_format_sympy_object(p['x'])}, y={_format_sympy_object(p['y'])}" for p in analysis['inflection_points']])
        summary_parts.append(inflection_str)
    else:
        summary_parts.append("Puntos de inflexión: No tiene.")

    analysis['summary_text'] = "\n".join(summary_parts)
    return analysis

def analyze_polynomial_function(coeffs):
    x = sp.Symbol('x')
    f = sum(c * x**i for i, c in enumerate(reversed(coeffs)))

    analysis = {
        'function_type': 'polynomial',
        'equation': f"y = {str(f)}",
        'domain': "Todos los números reales",
        'continuity': "Continua en todo su dominio",
        'extrema': {"local": [], "absolute": []},
        'inflection_points': [],
        'concavity': {"concave_intervals": [], "convex_intervals": []},
        'image': "",
        'roots': [],
        'y_intercept': None,
        'monotonicity': {"increasing_intervals": [], "decreasing_intervals": []}
    }

    # Roots
    analysis['roots'] = _get_roots(f, x)

    # Y-intercept
    analysis['y_intercept'] = f.subs(x, 0)

    # Extrema
    local_extrema, absolute_extrema = _analyze_extrema(f, x)
    analysis['extrema']['local'] = local_extrema
    analysis['extrema']['absolute'] = absolute_extrema

    # Monotonicity
    f_prime = _get_derivatives(f, x, 1)
    critical_points = _get_roots(f_prime, x)
    real_critical_points = sorted([p for p in critical_points if p.is_real])

    if real_critical_points:
        intervals = [-sp.oo] + real_critical_points + [sp.oo]
        for i in range(len(intervals) - 1):
            test_point = (intervals[i] + intervals[i+1]) / 2
            if not test_point.is_real: # Handle cases where mid-point might not be real (e.g. inf + inf)
                if intervals[i] == -sp.oo and intervals[i+1] != sp.oo: test_point = intervals[i+1] - 1
                elif intervals[i] != -sp.oo and intervals[i+1] == sp.oo: test_point = intervals[i] + 1
                elif intervals[i] == -sp.oo and intervals[i+1] == sp.oo: test_point = 0
            
            # Avoid division by zero if test_point is 0 and f_prime has x in denominator
            if test_point == 0: test_point = sp.S(1)/100 # Use a small non-zero value
            
            try:
                sign = f_prime.subs(x, test_point)
                if sign > 0:
                    analysis['monotonicity']['increasing_intervals'].append(f"({intervals[i]}, {intervals[i+1]})")
                elif sign < 0:
                    analysis['monotonicity']['decreasing_intervals'].append(f"({intervals[i]}, {intervals[i+1]})")
            except (ValueError, TypeError): # Handle cases where substitution fails (e.g., complex numbers, division by zero)
                pass # Skip interval if analysis fails

    # Range
    if len(coeffs) % 2 == 1: # Odd degree
        analysis['image'] = "Todos los números reales"
    else: # Even degree
        if analysis['extrema']['absolute']:
            if analysis['extrema']['absolute'][0]['type'] == 'min':
                analysis['image'] = f"y >= {analysis['extrema']['absolute'][0]['y']}"
            else:
                analysis['image'] = f"y <= {analysis['extrema']['absolute'][0]['y']}"
        else:
            analysis['image'] = "No se pudo determinar (o no hay extremos absolutos)."


    # Concavity and Inflection points
    concave_intervals, convex_intervals = _analyze_concavity(f, x)
    analysis['concavity']['concave_intervals'] = concave_intervals
    analysis['concavity']['convex_intervals'] = convex_intervals
    analysis['inflection_points'] = _analyze_inflection_points(f, x)

    # Generate summary text
    summary_parts = [
        f"Análisis de la función {analysis['equation']}",
        "-------------------------------------------------",
        f"Dominio: {analysis['domain']}",
        f"Imagen: {analysis['image']}",
        f"Continuidad: {analysis['continuity']}",
        f"Raíces (corte con el eje X): {analysis['roots']}",
        f"Punto de corte con el eje Y: y = {analysis['y_intercept']}",
    ]

    if analysis['monotonicity']['increasing_intervals'] or analysis['monotonicity']['decreasing_intervals']:
        mono_str = "Monotonía: "
        if analysis['monotonicity']['increasing_intervals']:
            mono_str += f"Creciente en {', '.join(map(str, analysis['monotonicity']['increasing_intervals']))}"
        if analysis['monotonicity']['decreasing_intervals']:
            if len(analysis['monotonicity']['increasing_intervals']) > 0:
                mono_str += ", "
            mono_str += f"Decreciente en {', '.join(map(str, analysis['monotonicity']['decreasing_intervals']))}"
        summary_parts.append(mono_str)
    
    if analysis['extrema']['local'] or analysis['extrema']['absolute']:
        extrema_str = "Extremos: "
        if analysis['extrema']['local']:
            local_str = ", ".join([f"{e['type']} local en x={e['x']:.2f}, y={e['y']:.2f}" for e in analysis['extrema']['local']])
            extrema_str += f"Local: {local_str}"
        if analysis['extrema']['absolute']:
            absolute_str = ", ".join([f"{e['type']} absoluto en x={e['x']:.2f}, y={e['y']:.2f}" for e in analysis['extrema']['absolute']])
            extrema_str += f"Absoluto: {absolute_str}"
        summary_parts.append(extrema_str)

    if analysis['concavity']['concave_intervals'] or analysis['concavity']['convex_intervals']:
        concavity_str = "Concavidad: "
        if analysis['concavity']['concave_intervals']:
            concavity_str += f"Cóncava en {', '.join(map(str, analysis['concavity']['concave_intervals']))}"
        if analysis['concavity']['convex_intervals']:
            if len(analysis['concavity']['concave_intervals']) > 0:
                concavity_str += ", "
            concavity_str += f"Convexa en {', '.join(map(str, analysis['concavity']['convex_intervals']))}"
        summary_parts.append(concavity_str)

    if analysis['inflection_points']:
        inflection_str = "Puntos de inflexión: " + ", ".join([f"x={p['x']:.2f}, y={p['y']:.2f}" for p in analysis['inflection_points']])
        summary_parts.append(inflection_str)
    else:
        summary_parts.append("Puntos de inflexión: No tiene.")

    analysis['summary_text'] = "\n".join(summary_parts)
    return analysis

def analyze_composite_function(function_domain_pairs):
    x = sp.Symbol('x')
    composite_analysis = {
        'function_type': 'composite',
        'pieces_analysis': [],
        'connection_points_analysis': [],
        'summary_text': "",
        'y_intercept': None
    }
    summary_parts = ["Análisis de la Función Compuesta", "-------------------------------------------------"]

    y_intercept_found = False

    # Analyze each piece
    for i, (f_expr, domain_info) in enumerate(function_domain_pairs):
        f = sp.sympify(f_expr)
        
        # Create a sympy Interval object from the domain_info dictionary
        left_open = domain_info['left_bracket'] == '('
        right_open = domain_info['right_bracket'] == ')'
        domain_interval = sp.Interval(domain_info['lower_bound'], domain_info['upper_bound'], left_open, right_open)

        piece_analysis = {
            'piece_number': i + 1,
            'equation': str(f),
            'domain_interval': str(domain_interval),
            'continuity_in_piece': "",
            'roots': _get_roots(f, x),
            'y_intercept': None,
            'extrema': {"local": [], "absolute": []},
            'inflection_points': [],
            'concavity': {"concave_intervals": [], "convex_intervals": []},
            'monotonicity': {"increasing_intervals": [], "decreasing_intervals": []}
        }

        summary_parts.append(f"\nAnálisis del Tramo {i+1}: y = {f} en {domain_interval}")
        summary_parts.append("-------------------------------------------------")
        summary_parts.append(f"Dominio del tramo: {domain_interval}")

        # Y-intercept
        if not y_intercept_found and 0 in domain_interval:
            y_intercept_val = f.subs(x, 0)
            piece_analysis['y_intercept'] = y_intercept_val
            composite_analysis['y_intercept'] = y_intercept_val
            summary_parts.append(f"Punto de corte con el eje Y: y = {_format_sympy_object(y_intercept_val)}")
            y_intercept_found = True

        # Continuity within the interval
        discontinuities = sp.singularities(f, x, domain_interval)
        if not discontinuities:
            piece_analysis['continuity_in_piece'] = "Continua"
            summary_parts.append("Continuidad en el intervalo: Continua")
        else:
            piece_analysis['continuity_in_piece'] = f"Discontinua en {discontinuities}"
            summary_parts.append(f"Continuidad en el intervalo: Discontinua en {discontinuities}")

        summary_parts.append(f"Raíces en el tramo: {piece_analysis['roots']}")

        # Derivatives
        f_prime = _get_derivatives(f, x, 1)
        f_double_prime = _get_derivatives(f, x, 2)

        # Monotonicity
        try:
            increasing_intervals = sp.solve_univariate_inequality(f_prime > 0, x, relational=False).intersect(domain_interval)
            decreasing_intervals = sp.solve_univariate_inequality(f_prime < 0, x, relational=False).intersect(domain_interval)
            piece_analysis['monotonicity']['increasing_intervals'] = increasing_intervals
            piece_analysis['monotonicity']['decreasing_intervals'] = decreasing_intervals
            summary_parts.append(f"Intervalos de crecimiento: {increasing_intervals}")
            summary_parts.append(f"Intervalos de decrecimiento: {decreasing_intervals}")
        except Exception as e:
            summary_parts.append(f"No se pudo determinar la monotonía: {e}")

        # Extrema for the piece
        local_extrema_piece, absolute_extrema_piece = _analyze_extrema(f, x, domain=domain_interval)
        piece_analysis['extrema']['local'] = local_extrema_piece
        piece_analysis['extrema']['absolute'] = absolute_extrema_piece
        extrema_str = "Extremos locales en el intervalo: " + (", ".join([f"{e['type']} en x={float(e['x']):.2f}, y={float(e['y']):.2f}" for e in local_extrema_piece]) if local_extrema_piece else "No tiene.")
        summary_parts.append(extrema_str)

        # Concavity and Inflection points for the piece
        concave_intervals_piece, convex_intervals_piece = _analyze_concavity(f, x, domain=domain_interval)
        piece_analysis['concavity']['concave_intervals'] = concave_intervals_piece
        piece_analysis['concavity']['convex_intervals'] = convex_intervals_piece
        concavity_str = "Concavidad en el intervalo: "
        if concave_intervals_piece:
            concavity_str += f"Cóncava en {concave_intervals_piece}"
        if convex_intervals_piece:
            if concave_intervals_piece: concavity_str += ", "
            concavity_str += f"Convexa en {convex_intervals_piece}"
        if not concave_intervals_piece and not convex_intervals_piece: concavity_str += "No se pudo determinar."
        summary_parts.append(concavity_str)

        inflection_points_piece = _analyze_inflection_points(f, x)
        piece_analysis['inflection_points'] = inflection_points_piece
        inflection_str = "Puntos de inflexión en el intervalo: " + (", ".join([f"x={float(p['x']):.2f}, y={float(p['y']):.2f}" for p in inflection_points_piece]) if inflection_points_piece else "No tiene.")
        summary_parts.append(inflection_str)


        composite_analysis['pieces_analysis'].append(piece_analysis)

    # Analyze connection points
    summary_parts.append("\nAnálisis de los Puntos de Conexión")
    summary_parts.append("-------------------------------------------------")
    for i in range(len(function_domain_pairs) - 1):
        f1_expr, domain1 = function_domain_pairs[i]
        f2_expr, domain2 = function_domain_pairs[i+1]
        f1 = sp.sympify(f1_expr)
        f2 = sp.sympify(f2_expr)

        # Assume connection point is the end of the first interval
        connection_point_val = domain1['upper_bound']
        
        connection_point_analysis = {
            'point': connection_point_val,
            'continuity': False,
            'limit_f1_left': None,
            'limit_f2_right': None,
            'f1_val_at_point': None
        }

        try:
            limit_f1_left = sp.limit(f1, x, connection_point_val, dir='-')
            limit_f2_right = sp.limit(f2, x, connection_point_val, dir='+')
            f1_val_at_point = f1.subs(x, connection_point_val)

            connection_point_analysis['limit_f1_left'] = limit_f1_left
            connection_point_analysis['limit_f2_right'] = limit_f2_right
            connection_point_analysis['f1_val_at_point'] = f1_val_at_point

            summary_parts.append(f"Punto de conexión en x = {connection_point_val}:")
            summary_parts.append(f"  Límite por la izquierda (tramo {i+1}): {limit_f1_left}")
            summary_parts.append(f"  Límite por la derecha (tramo {i+2}): {limit_f2_right}")
            summary_parts.append(f"  Valor de la función en el punto (tramo {i+1}): {f1_val_at_point}")

            if limit_f1_left == limit_f2_right and limit_f1_left == f1_val_at_point:
                connection_point_analysis['continuity'] = True
                summary_parts.append("  => La función es continua en este punto.")
            else:
                summary_parts.append("  => La función es discontinua en este punto.")
        except Exception as e:
            summary_parts.append(f"No se pudo analizar la continuidad en x = {connection_point_val}: {e}")
        
        composite_analysis['connection_points_analysis'].append(connection_point_analysis)

    if not y_intercept_found:
        summary_parts.insert(2, "Punto de corte con el eje Y: No cruza el eje Y.")

    composite_analysis['summary_text'] = "\n".join(summary_parts)
    return composite_analysis