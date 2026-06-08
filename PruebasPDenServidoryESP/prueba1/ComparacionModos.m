
% =========================================================================
% SCRIPT PARA COMPARACIÓN: CONTROL LOCAL (ESP32) VS CONTROL EN SERVIDOR
% Dibuja trayectorias, calcula métricas y exporta resultados.
%
% Archivos esperados:
%   ESP1.csv, ESP2.csv, ..., ESP5.csv
%   SERV1.csv, SERV2.csv, ..., SERV5.csv
%
% Columnas esperadas en cada CSV:
%   tiempo, robot, x_act, y_act, th_act, x_obj, y_obj, th_obj, modo_pid
% =========================================================================

clear; clc; close all;

%% ========================================================================
% 1. PARÁMETROS DE LA PRUEBA
% ========================================================================

num_repeticiones = 10;

% Umbral para considerar que el robot ha llegado al objetivo
umbral_llegada_px = 20;

% Colores
color_esp  = [0, 0.4470, 0.7410];
color_serv = [0.8500, 0.3250, 0.0980];

% Colores aclarados para que varias repeticiones se vean bien
color_esp_claro  = 0.65 * color_esp  + 0.35 * [1 1 1];
color_serv_claro = 0.65 * color_serv + 0.35 * [1 1 1];

%% ========================================================================
% 2. CREAR TABLA DE RESULTADOS VACÍA, PERO CON COLUMNAS DEFINIDAS
% ========================================================================

resultados = table( ...
    strings(0,1), ...   % Modo
    zeros(0,1), ...     % Repeticion
    zeros(0,1), ...     % XInicial
    zeros(0,1), ...     % YInicial
    zeros(0,1), ...     % XFinal
    zeros(0,1), ...     % YFinal
    zeros(0,1), ...     % XObjetivo
    zeros(0,1), ...     % YObjetivo
    zeros(0,1), ...     % ErrorFinal_px
    zeros(0,1), ...     % ErrorAngularFinal_deg
    zeros(0,1), ...     % TiempoTotal_s
    zeros(0,1), ...     % TiempoLlegada_s
    zeros(0,1), ...     % LongitudTrayectoria_px
    zeros(0,1), ...     % DistanciaRecta_px
    zeros(0,1), ...     % Eficiencia
    'VariableNames', { ...
        'Modo', ...
        'Repeticion', ...
        'XInicial', ...
        'YInicial', ...
        'XFinal', ...
        'YFinal', ...
        'XObjetivo', ...
        'YObjetivo', ...
        'ErrorFinal_px', ...
        'ErrorAngularFinal_deg', ...
        'TiempoTotal_s', ...
        'TiempoLlegada_s', ...
        'LongitudTrayectoria_px', ...
        'DistanciaRecta_px', ...
        'Eficiencia' ...
    });

%% ========================================================================
% 3. FIGURA 1: TRAYECTORIAS X-Y
% ========================================================================

fig1 = figure( ...
    'Name', 'Comparativa de Arquitecturas de Control', ...
    'Color', 'w', ...
    'Position', [100, 100, 900, 600]);

hold on;
grid on;

h_esp = [];
h_serv = [];
h_ini = [];
h_obj = [];

ultimo_df_valido = [];

% -------------------------------------------------------------------------
% Procesar repeticiones ESP32
% -------------------------------------------------------------------------
for i = 1:num_repeticiones
    filename = sprintf('ESP%d.csv', i);

    if isfile(filename)
        df = readtable(filename);

        x = obtener_columna_num(df, 'x_act');
        y = obtener_columna_num(df, 'y_act');

        h = plot(x, y, '-', ...
            'LineWidth', 1.5, ...
            'Color', color_esp_claro);

        if isempty(h_esp)
            h_esp = h;
        end

        met = calcular_metricas(df, "ESP32", i, umbral_llegada_px);
        resultados = [resultados; met];

        ultimo_df_valido = df;
    else
        warning('No se encontró el archivo %s', filename);
    end
end

% -------------------------------------------------------------------------
% Procesar repeticiones Servidor
% -------------------------------------------------------------------------
for i = 1:num_repeticiones
    filename = sprintf('SERV%d.csv', i);

    if isfile(filename)
        df = readtable(filename);

        x = obtener_columna_num(df, 'x_act');
        y = obtener_columna_num(df, 'y_act');

        h = plot(x, y, '-', ...
            'LineWidth', 1.5, ...
            'Color', color_serv_claro);

        if isempty(h_serv)
            h_serv = h;
        end

        met = calcular_metricas(df, "Servidor", i, umbral_llegada_px);
        resultados = [resultados; met];

        ultimo_df_valido = df;
    else
        warning('No se encontró el archivo %s', filename);
    end
end

% -------------------------------------------------------------------------
% Comprobar que se ha cargado al menos un archivo
% -------------------------------------------------------------------------
if height(resultados) == 0
    error(['No se ha procesado ningún CSV. Revisa que los archivos se llamen ', ...
           'ESP1.csv, ESP2.csv, ..., SERV1.csv, SERV2.csv, ... y que estén ', ...
           'en la misma carpeta que este script.']);
end

% -------------------------------------------------------------------------
% Dibujar punto inicial y objetivo
% -------------------------------------------------------------------------
if ~isempty(ultimo_df_valido)
    x_obj = obtener_columna_num(ultimo_df_valido, 'x_obj');
    y_obj = obtener_columna_num(ultimo_df_valido, 'y_obj');
    x_act = obtener_columna_num(ultimo_df_valido, 'x_act');
    y_act = obtener_columna_num(ultimo_df_valido, 'y_act');

    h_ini = plot(x_act(1), y_act(1), 'ko', ...
        'MarkerSize', 7, ...
        'MarkerFaceColor', 'k');

    h_obj = plot(x_obj(1), y_obj(1), 'kx', ...
        'MarkerSize', 11, ...
        'LineWidth', 2.2);
end

% -------------------------------------------------------------------------
% Estética de figura
% -------------------------------------------------------------------------
title('Comparativa de Trayectorias: Control Local (ESP32) vs Centralizado (Servidor)', ...
      'FontSize', 13, ...
      'FontWeight', 'bold');

xlabel('Posición en el Eje X (píxeles)', ...
    'FontSize', 12, ...
    'FontWeight', 'bold');

ylabel('Posición en el Eje Y (píxeles)', ...
    'FontSize', 12, ...
    'FontWeight', 'bold');

% OpenCV tiene el eje Y hacia abajo
set(gca, 'YDir', 'reverse');

if ~isempty(h_esp) && ~isempty(h_serv) && ~isempty(h_ini) && ~isempty(h_obj)
    lgd = legend([h_esp, h_serv, h_ini, h_obj], ...
        {'Control en Nodo (ESP32)', ...
         'Control en Servidor', ...
         'Posición inicial', ...
         'Posición objetivo'}, ...
        'Location', 'best');

    lgd.FontSize = 11;
end

set(gca, ...
    'FontSize', 11, ...
    'GridAlpha', 0.4, ...
    'LineWidth', 1);

axis equal;

exportgraphics(fig1, 'comparativa_trayectorias_pd.pdf', 'ContentType', 'vector');
exportgraphics(fig1, 'comparativa_trayectorias_pd.png', 'Resolution', 300);

disp('Figura de trayectorias guardada como comparativa_trayectorias_pd.pdf y .png');

%% ========================================================================
% 4. TABLA INDIVIDUAL DE RESULTADOS
% ========================================================================

disp(' ');
disp('================ RESULTADOS INDIVIDUALES ================');
disp(resultados);

writetable(resultados, 'resultados_comparacion_pd_individual.csv');

disp('Tabla individual guardada como resultados_comparacion_pd_individual.csv');

%% ========================================================================
% 5. TABLA RESUMEN POR MODO
% ========================================================================

modos = unique(resultados.Modo, 'stable');

resumen = table( ...
    strings(0,1), ...
    zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), ...
    zeros(0,1), zeros(0,1), ...
    'VariableNames', { ...
        'Modo', ...
        'ErrorFinalMedio_px', 'ErrorFinalSTD_px', ...
        'ErrorAngularMedio_deg', 'ErrorAngularSTD_deg', ...
        'TiempoTotalMedio_s', 'TiempoTotalSTD_s', ...
        'TiempoLlegadaMedio_s', 'TiempoLlegadaSTD_s', ...
        'LongitudMedia_px', 'LongitudSTD_px', ...
        'EficienciaMedia', 'EficienciaSTD' ...
    });

for i = 1:length(modos)
    modo_actual = modos(i);
    idx = resultados.Modo == modo_actual;

    nueva_fila = table( ...
        modo_actual, ...
        mean(resultados.ErrorFinal_px(idx), 'omitnan'), ...
        std(resultados.ErrorFinal_px(idx), 'omitnan'), ...
        mean(resultados.ErrorAngularFinal_deg(idx), 'omitnan'), ...
        std(resultados.ErrorAngularFinal_deg(idx), 'omitnan'), ...
        mean(resultados.TiempoTotal_s(idx), 'omitnan'), ...
        std(resultados.TiempoTotal_s(idx), 'omitnan'), ...
        mean(resultados.TiempoLlegada_s(idx), 'omitnan'), ...
        std(resultados.TiempoLlegada_s(idx), 'omitnan'), ...
        mean(resultados.LongitudTrayectoria_px(idx), 'omitnan'), ...
        std(resultados.LongitudTrayectoria_px(idx), 'omitnan'), ...
        mean(resultados.Eficiencia(idx), 'omitnan'), ...
        std(resultados.Eficiencia(idx), 'omitnan'), ...
        'VariableNames', resumen.Properties.VariableNames);

    resumen = [resumen; nueva_fila];
end

disp(' ');
disp('================ RESUMEN POR MODO ================');
disp(resumen);

writetable(resumen, 'resultados_comparacion_pd_resumen.csv');

disp('Tabla resumen guardada como resultados_comparacion_pd_resumen.csv');

%% ========================================================================
% 6. FIGURA 2: ERROR DE DISTANCIA AL OBJETIVO FRENTE AL TIEMPO
% ========================================================================

fig2 = figure( ...
    'Name', 'Error de distancia al objetivo', ...
    'Color', 'w', ...
    'Position', [150, 150, 900, 550]);

hold on;
grid on;

h_esp_error = [];
h_serv_error = [];

% Dibujar errores ESP32
for i = 1:num_repeticiones
    filename = sprintf('ESP%d.csv', i);

    if isfile(filename)
        df = readtable(filename);

        t = obtener_tiempo_relativo(df);
        e = calcular_error_distancia(df);

        h = plot(t, e, '-', ...
            'LineWidth', 1.3, ...
            'Color', color_esp_claro);

        if isempty(h_esp_error)
            h_esp_error = h;
        end
    end
end

% Dibujar errores Servidor
for i = 1:num_repeticiones
    filename = sprintf('SERV%d.csv', i);

    if isfile(filename)
        df = readtable(filename);

        t = obtener_tiempo_relativo(df);
        e = calcular_error_distancia(df);

        h = plot(t, e, '-', ...
            'LineWidth', 1.3, ...
            'Color', color_serv_claro);

        if isempty(h_serv_error)
            h_serv_error = h;
        end
    end
end

yline(umbral_llegada_px, '--k', ...
    sprintf('Umbral llegada = %d px', umbral_llegada_px), ...
    'LabelHorizontalAlignment', 'left');

title('Evolución del error de distancia al objetivo', ...
    'FontSize', 13, ...
    'FontWeight', 'bold');

xlabel('Tiempo relativo (s)', ...
    'FontSize', 12, ...
    'FontWeight', 'bold');

ylabel('Error de distancia al objetivo (píxeles)', ...
    'FontSize', 12, ...
    'FontWeight', 'bold');

if ~isempty(h_esp_error) && ~isempty(h_serv_error)
    lgd = legend([h_esp_error, h_serv_error], ...
        {'Control en Nodo (ESP32)', 'Control en Servidor'}, ...
        'Location', 'best');

    lgd.FontSize = 11;
end

set(gca, ...
    'FontSize', 11, ...
    'GridAlpha', 0.4, ...
    'LineWidth', 1);

exportgraphics(fig2, 'error_distancia_comparacion_pd.pdf', 'ContentType', 'vector');
exportgraphics(fig2, 'error_distancia_comparacion_pd.png', 'Resolution', 300);

disp('Figura de error de distancia guardada como error_distancia_comparacion_pd.pdf y .png');

%% ========================================================================
% 7. FILAS LATEX PARA TABLA RESUMEN
% ========================================================================

disp(' ');
disp('================ FILAS LATEX PARA TABLA RESUMEN ================');

for i = 1:height(resumen)
    fprintf('%s & %.2f & %.2f & %.2f & %.2f & %.3f \\\\ \n', ...
        resumen.Modo(i), ...
        resumen.ErrorFinalMedio_px(i), ...
        resumen.ErrorAngularMedio_deg(i), ...
        resumen.TiempoLlegadaMedio_s(i), ...
        resumen.LongitudMedia_px(i), ...
        resumen.EficienciaMedia(i));
end

disp(' ');
disp('Script finalizado correctamente.');

%% ========================================================================
% FUNCIONES AUXILIARES
% ========================================================================

function met = calcular_metricas(df, modo, repeticion, umbral_llegada_px)

    x = obtener_columna_num(df, 'x_act');
    y = obtener_columna_num(df, 'y_act');

    x_obj_col = obtener_columna_num(df, 'x_obj');
    y_obj_col = obtener_columna_num(df, 'y_obj');

    x_obj = x_obj_col(1);
    y_obj = y_obj_col(1);

    x_ini = x(1);
    y_ini = y(1);

    x_final = x(end);
    y_final = y(end);

    % Error final de posición
    error_final = sqrt((x_obj - x_final)^2 + (y_obj - y_final)^2);

    % Longitud de trayectoria
    dx = diff(x);
    dy = diff(y);
    longitud = sum(sqrt(dx.^2 + dy.^2), 'omitnan');

    % Distancia recta ideal
    distancia_recta = sqrt((x_obj - x_ini)^2 + (y_obj - y_ini)^2);

    % Eficiencia de trayectoria
    if longitud > 0
        eficiencia = distancia_recta / longitud;
    else
        eficiencia = NaN;
    end

    % Tiempo
    t = obtener_tiempo_relativo(df);
    tiempo_total = t(end) - t(1);

    % Tiempo hasta entrar en el umbral
    error_distancia = calcular_error_distancia(df);
    idx_llegada = find(error_distancia <= umbral_llegada_px, 1, 'first');

    if isempty(idx_llegada)
        tiempo_llegada = NaN;
    else
        tiempo_llegada = t(idx_llegada) - t(1);
    end

    % Error angular final
    error_angular_final = calcular_error_angular_final(df);

    met = table( ...
        string(modo), ...
        repeticion, ...
        x_ini, y_ini, ...
        x_final, y_final, ...
        x_obj, y_obj, ...
        error_final, ...
        error_angular_final, ...
        tiempo_total, ...
        tiempo_llegada, ...
        longitud, ...
        distancia_recta, ...
        eficiencia, ...
        'VariableNames', { ...
            'Modo', ...
            'Repeticion', ...
            'XInicial', ...
            'YInicial', ...
            'XFinal', ...
            'YFinal', ...
            'XObjetivo', ...
            'YObjetivo', ...
            'ErrorFinal_px', ...
            'ErrorAngularFinal_deg', ...
            'TiempoTotal_s', ...
            'TiempoLlegada_s', ...
            'LongitudTrayectoria_px', ...
            'DistanciaRecta_px', ...
            'Eficiencia' ...
        });
end

function v = obtener_columna_num(df, nombre_columna)

    if ~ismember(nombre_columna, df.Properties.VariableNames)
        error('No existe la columna "%s" en el CSV.', nombre_columna);
    end

    v = df.(nombre_columna);

    % Si ya es numérica, se devuelve directamente
    if isnumeric(v)
        return;
    end

    % Si viene como texto/celda/string, se convierte a double
    v = str2double(string(v));

    if any(isnan(v))
        warning('La columna "%s" contiene valores que no se han podido convertir a número.', nombre_columna);
    end
end

function t = obtener_tiempo_relativo(df)

    nombres_posibles = {'tiempo', 'tiempo_relativo', 'timestamp', 'time', 't'};
    col_encontrada = '';

    for i = 1:length(nombres_posibles)
        if ismember(nombres_posibles{i}, df.Properties.VariableNames)
            col_encontrada = nombres_posibles{i};
            break;
        end
    end

    if isempty(col_encontrada)
        fps = 24;
        t = (0:height(df)-1)' / fps;
        return;
    end

    t = obtener_columna_num(df, col_encontrada);

    % Normalizar para empezar en cero
    t = t - t(1);
end

function e = calcular_error_distancia(df)

    x = obtener_columna_num(df, 'x_act');
    y = obtener_columna_num(df, 'y_act');

    x_obj_col = obtener_columna_num(df, 'x_obj');
    y_obj_col = obtener_columna_num(df, 'y_obj');

    x_obj = x_obj_col(1);
    y_obj = y_obj_col(1);

    e = sqrt((x_obj - x).^2 + (y_obj - y).^2);
end

function error_ang = calcular_error_angular_final(df)

    if ~ismember('th_act', df.Properties.VariableNames) || ...
       ~ismember('th_obj', df.Properties.VariableNames)

        error_ang = NaN;
        return;
    end

    th_act = obtener_columna_num(df, 'th_act');
    th_obj = obtener_columna_num(df, 'th_obj');

    theta_final = th_act(end);
    theta_obj = th_obj(1);

    diferencia = theta_obj - theta_final;

    % Normalizar a [-180, 180]
    diferencia = mod(diferencia + 180, 360) - 180;

    error_ang = abs(diferencia);
end

