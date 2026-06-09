% COMPARACIÓN GLOBAL DE CONFIGURACIONES DEL CONTROLADOR PD
clear; clc; close all;

% Configuraciones evaluadas
configs = categorical({'A','B','C','D','E','F'});
configs = reordercats(configs, {'A','B','C','D','E','F'});

% Valores medios obtenidos
error_pos_px  = [21.19, 20.70, 21.68, 21.792, 22.592, 20.226];
error_ang_deg = [6.42,  7.88,  4.12,  3.84,   7.42,   5.08];
tiempo_s      = [11.202, 8.72,  8.262, 7.588,  8.278,  8.246];

% Crear figura
fig = figure('Name', 'Comparación configuraciones PD', ...
             'Color', 'w', ...
             'Position', [100, 100, 900, 650]);

% --- Error de posición ---
subplot(3,1,1);
bar(configs, error_pos_px, 'FaceColor', '#0072BD');
grid on;
ylabel('Error posición (px)', 'FontWeight', 'bold');
title('Comparación global de configuraciones del controlador PD', ...
      'FontWeight', 'bold');
ylim([0, max(error_pos_px)*1.25]);

% --- Error angular ---
subplot(3,1,2);
bar(configs, error_ang_deg, 'FaceColor', '#77AC30');
grid on;
ylabel('Error angular (°)', 'FontWeight', 'bold');
ylim([0, max(error_ang_deg)*1.30]);

% --- Tiempo de llegada ---
subplot(3,1,3);
bar(configs, tiempo_s, 'FaceColor', '#D95319');
grid on;
ylabel('Tiempo (s)', 'FontWeight', 'bold');
xlabel('Configuración', 'FontWeight', 'bold');
ylim([0, max(tiempo_s)*1.25]);

% Ajustes generales
set(findall(fig, '-property', 'FontSize'), 'FontSize', 11);

% Exportar para LaTeX
exportgraphics(fig, 'comparacion_configuraciones_pd.pdf', 'ContentType', 'vector');
exportgraphics(fig, 'comparacion_configuraciones_pd.png', 'Resolution', 300);
disp('Figura comparativa generada correctamente.');