% Leer telemetría
df = readtable('D-3.csv');

% 1. Calcular el tiempo total
tiempo_total = max(df.tiempo) - min(df.tiempo);

% 2. Coger la última fila para el error final
x_f = df.x_act(end);
y_f = df.y_act(end);
th_f = df.th_act(end);

x_obj = df.x_obj(end);
y_obj = df.y_obj(end);
th_obj = df.th_obj(end);

% 3. Matemáticas
e_p = sqrt((x_obj - x_f)^2 + (y_obj - y_f)^2);
e_theta = abs(th_obj - th_f);

fprintf('Tiempo: %.2f s | Error Posición: %.2f px | Error Angular: %.2f º\n', tiempo_total, e_p, e_theta);

% 4. Dibujar la evolución del error para la Figura 6.1
error_vector = sqrt((df.x_obj - df.x_act).^2 + (df.y_obj - df.y_act).^2);
tiempo_relativo = df.tiempo - min(df.tiempo);

plot(tiempo_relativo, error_vector, 'LineWidth', 1.5);