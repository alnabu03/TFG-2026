% =========================================================================
% SCRIPT PARA VALIDACIÓN DE SINCRONISMO (TFG)
% Lee los datos de telemetría y grafica el inicio del movimiento.
% =========================================================================

clear; clc; close all;

% 1. Leer los datos del archivo CSV
opts = detectImportOptions('prueba1tfgsincronismo.csv');
df = readtable('prueba1tfgsincronismo.csv', opts);

% 2. Separar los datos por robot según su ID de marcador
robot0 = df(df.marker_id == 0, :);
robot1 = df(df.marker_id == 1, :);

% 3. Normalizar el tiempo para que la gráfica empiece en t = 0s
tiempo_base = min(df.timestamp);
t_robot0 = robot0.timestamp - tiempo_base;
t_robot1 = robot1.timestamp - tiempo_base;

% 4. Configurar la figura (Tamaño adaptado para documento A4)
fig = figure('Name', 'Sincronismo Físico', 'Color', 'w', 'Position', [100, 100, 800, 400]);
hold on;
grid on;

% 5. Trazar las líneas de posición Y (con marcadores para ver los frames exactos)
plot(t_robot0, robot0.y, '-o', 'LineWidth', 1.5, 'MarkerSize', 5, ...
    'Color', '#0072BD', 'MarkerFaceColor', '#0072BD', 'DisplayName', 'Robot 0 (EP2)');

plot(t_robot1, robot1.y, '-s', 'LineWidth', 1.5, 'MarkerSize', 5, ...
    'Color', '#D95319', 'MarkerFaceColor', '#D95319', 'DisplayName', 'Robot 1 (EP1)');

% 6. Estética académica (Títulos, ejes y leyenda)
title('Validación de Sincronismo Físico ante Jitter de Red', 'FontSize', 14, 'FontWeight', 'bold');
xlabel('Tiempo relativo (s)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('Posición en el Eje Y (píxeles)', 'FontSize', 12, 'FontWeight', 'bold');

% Estilo de la leyenda
lgd = legend('Location', 'best');
lgd.FontSize = 11;
set(gca, 'FontSize', 11, 'GridAlpha', 0.4, 'LineWidth', 1);

% =========================================================================
% ¡ATENCIÓN! Ajuste de Zoom:
% Descomenta y cambia estos valores para hacer zoom en el momento exacto
% donde los robots empiezan a moverse (por ejemplo, entre el segundo 1 y 2).
% =========================================================================
% xlim([1.5, 2.5]); 
% ylim([275, 290]); 

% 7. Exportar la gráfica en formato vectorial para LaTeX
exportgraphics(fig, 'grafica_sincronismo.pdf', 'ContentType', 'vector');
disp('¡Gráfica generada y guardada como grafica_sincronismo.pdf!');