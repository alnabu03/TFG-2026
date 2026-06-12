% =========================================================================
% COMPARACIÓN ENTRE CONTROL PD EN ESP32 Y CONTROL PD EN SERVIDOR
% Figura resumen con valores medios y desviaciones típicas
% =========================================================================

clear; clc; close all;

%% Datos medios obtenidos en las pruebas

modos = categorical({'ESP32', 'Servidor'});
modos = reordercats(modos, {'ESP32', 'Servidor'});

% Valores medios
error_pos_media = [18.86, 16.93];     % e_f (px)
error_ang_media = [4.22, 6.49];       % e_theta (grados)
tiempo_media    = [8.42, 8.13];       % t (s)
ef_media        = [0.955, 0.967];     % eta

% Desviaciones típicas
error_pos_std = [5.15, 3.87];         % sigma(e_f)
error_ang_std = [1.58, 1.79];         % sigma(e_theta)
tiempo_std    = [0.74, 0.67];         % sigma(t)
ef_std        = [0.025, 0.018];       % sigma(eta)

%% Crear figura

fig = figure('Name', 'Comparación control ESP32 vs Servidor', ...
             'Color', 'w', ...
             'Position', [100, 100, 900, 650]);

%% 1. Error final de posición

subplot(2,2,1);
bar(modos, error_pos_media, 0.55);
hold on; grid on; box on;

errorbar(modos, error_pos_media, error_pos_std, ...
    'k.', 'LineWidth', 1.4, 'CapSize', 12);

ylabel('Error final e_f (px)', 'FontWeight', 'bold');
title('Error final de posición', 'FontWeight', 'bold');
ylim([0, max(error_pos_media + error_pos_std) * 1.25]);

% Etiquetas numéricas
for i = 1:length(modos)
    text(i, error_pos_media(i) + error_pos_std(i) + 1, ...
        sprintf('%.2f', error_pos_media(i)), ...
        'HorizontalAlignment', 'center', ...
        'FontSize', 10);
end

%% 2. Error angular final

subplot(2,2,2);
bar(modos, error_ang_media, 0.55);
hold on; grid on; box on;

errorbar(modos, error_ang_media, error_ang_std, ...
    'k.', 'LineWidth', 1.4, 'CapSize', 12);

ylabel('Error angular e_\theta (°)', 'FontWeight', 'bold');
title('Error angular final', 'FontWeight', 'bold');
ylim([0, max(error_ang_media + error_ang_std) * 1.25]);

for i = 1:length(modos)
    text(i, error_ang_media(i) + error_ang_std(i) + 0.4, ...
        sprintf('%.2f', error_ang_media(i)), ...
        'HorizontalAlignment', 'center', ...
        'FontSize', 10);
end

%% 3. Tiempo de llegada

subplot(2,2,3);
bar(modos, tiempo_media, 0.55);
hold on; grid on; box on;

errorbar(modos, tiempo_media, tiempo_std, ...
    'k.', 'LineWidth', 1.4, 'CapSize', 12);

ylabel('Tiempo de llegada t (s)', 'FontWeight', 'bold');
title('Tiempo de llegada', 'FontWeight', 'bold');
ylim([0, max(tiempo_media + tiempo_std) * 1.25]);

for i = 1:length(modos)
    text(i, tiempo_media(i) + tiempo_std(i) + 0.35, ...
        sprintf('%.2f', tiempo_media(i)), ...
        'HorizontalAlignment', 'center', ...
        'FontSize', 10);
end

%% 4. Eficiencia de trayectoria

subplot(2,2,4);
bar(modos, ef_media, 0.55);
hold on; grid on; box on;

errorbar(modos, ef_media, ef_std, ...
    'k.', 'LineWidth', 1.4, 'CapSize', 12);

ylabel('Eficiencia \eta', 'FontWeight', 'bold');
title('Eficiencia de trayectoria', 'FontWeight', 'bold');

% Como eta está cerca de 1, conviene ajustar el eje Y
ylim([0.90, 1.00]);

for i = 1:length(modos)
    text(i, ef_media(i) + ef_std(i) + 0.003, ...
        sprintf('%.3f', ef_media(i)), ...
        'HorizontalAlignment', 'center', ...
        'FontSize', 10);
end

%% Ajustes generales

sgtitle('Comparación entre control PD en ESP32 y control PD en servidor', ...
    'FontSize', 13, ...
    'FontWeight', 'bold');

set(findall(fig, '-property', 'FontSize'), 'FontSize', 11);

%% Exportar para LaTeX

exportgraphics(fig, 'comparacion_control_esp32_servidor.pdf', ...
    'ContentType', 'vector');

exportgraphics(fig, 'comparacion_control_esp32_servidor.png', ...
    'Resolution', 300);

disp('Figura comparativa generada correctamente.');

%% Mostrar resumen en consola

fprintf('\n--- Resumen de métricas ---\n');
fprintf('ESP32    -> e_f = %.2f ± %.2f px | e_theta = %.2f ± %.2f º | t = %.2f ± %.2f s | eta = %.3f ± %.3f\n', ...
    error_pos_media(1), error_pos_std(1), error_ang_media(1), error_ang_std(1), tiempo_media(1), tiempo_std(1), ef_media(1), ef_std(1));

fprintf('Servidor -> e_f = %.2f ± %.2f px | e_theta = %.2f ± %.2f º | t = %.2f ± %.2f s | eta = %.3f ± %.3f\n', ...
    error_pos_media(2), error_pos_std(2), error_ang_media(2), error_ang_std(2), tiempo_media(2), tiempo_std(2), ef_media(2), ef_std(2));