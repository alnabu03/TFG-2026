% =========================================================================
% SCRIPT DE ANÁLISIS ESTADÍSTICO (MÚLTIPLES ARCHIVOS CSV)
% Lee cada prueba independiente y calcula el desfase medio
% =========================================================================

clear; clc; close all;

% 1. Definir los archivos de las pruebas
% Escribe aquí el nombre de todos tus CSV
%archivos = {'prueba1.csv', 'prueba2.csv', 'prueba3.csv', 'prueba4.csv'}; 

% (Si tienes 50 pruebas y no quieres escribirlas, puedes comentar la línea
% de arriba y descomentar esta de abajo para que lea todos los CSV de la carpeta):
 info_archivos = dir('*.csv'); 
 archivos = {info_archivos.name};

num_pruebas = length(archivos);
desfases_ms = zeros(num_pruebas, 1);
umbral_pixeles = 1.5; % Mínimo salto para considerarlo arranque

fprintf('==================================================\n');
fprintf('       REPORTE ESTADÍSTICO DE SINCRONISMO         \n');
fprintf('==================================================\n');

for k = 1:num_pruebas
    nombre_archivo = archivos{k};
    
    % 2. Leer el archivo actual
    opts = detectImportOptions(nombre_archivo);
    df = readtable(nombre_archivo, opts);
    
    robot0 = df(df.marker_id == 0, :);
    robot1 = df(df.marker_id == 1, :);
    % 3. Buscar el primer instante de movimiento (POR DESPLAZAMIENTO)
    % Cogemos la coordenada exacta en la que estaba el robot antes de moverse
    x0_inicial = robot0.x(1);
    y0_inicial = robot0.y(1);
    x1_inicial = robot1.x(1);
    y1_inicial = robot1.y(1);
    
    % Calculamos a qué distancia está en cada fotograma respecto a su inicio
    dist0_total = sqrt((robot0.x - x0_inicial).^2 + (robot0.y - y0_inicial).^2);
    dist1_total = sqrt((robot1.x - x1_inicial).^2 + (robot1.y - y1_inicial).^2);
    
    % Buscamos el primer fotograma donde se haya alejado más de 2 píxeles 
    % de su posición de reposo absoluto.
    idx0 = find(dist0_total > 2.0, 1, 'first');
    idx1 = find(dist1_total > 2.0, 1, 'first');
    
    % Seguro antierrores por si en un CSV no se movieron
    if isempty(idx0) || isempty(idx1)
        fprintf('Prueba %d (%s): DESCARTADA (No se detectó movimiento)\n', k, nombre_archivo);
        desfases_ms(k) = NaN; % Marcamos como nulo para ignorarlo luego
        continue;
    end
    
    % 4. Extraer timestamps y comparar
    t0_start = robot0.timestamp(idx0);
    t1_start = robot1.timestamp(idx1);
    
    desfase = abs(t0_start - t1_start) * 1000; % Convertido a milisegundos
    desfases_ms(k) = desfase;
    
    fprintf('Prueba %d (%s): Desfase físico de %.2f ms\n', k, nombre_archivo, desfase);
end

% 5. Limpiar pruebas descartadas (las marcadas con NaN)
desfases_ms = desfases_ms(~isnan(desfases_ms));
pruebas_validas = length(desfases_ms);

% 6. Matemáticas finales
if pruebas_validas > 0
    media_ms = mean(desfases_ms);
    desviacion_ms = std(desfases_ms);
    maximo_ms = max(desfases_ms);

    fprintf('\n--- RESULTADOS FINALES (%d pruebas válidas) ---\n', pruebas_validas);
    fprintf('Desfase Medio (Media):   %.2f ms\n', media_ms);
    fprintf('Desviación Estándar:     %.2f ms\n', desviacion_ms);
    fprintf('Desfase Máximo (Peor):   %.2f ms\n', maximo_ms);
else
    fprintf('\nNo hay pruebas válidas para calcular estadísticas.\n');
end
fprintf('==================================================\n');