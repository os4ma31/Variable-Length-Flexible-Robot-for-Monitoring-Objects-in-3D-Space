% Data
x = [-10, -18.87, -22.71, -30.1, -36];  % ΔT (Tendon Distance) in mm
K_exp = [0.0051, 0.0094, 0.0123, 0.01463, 0.0187];   % Experimental curvature (mm^-1)
K_theo = [0.0052, 0.0098, 0.0117, 0.01556, 0.0181];  % Theoretical curvature (mm^-1)

% Real error values (K_exp - K_theo)
K_error = abs(K_exp - K_theo);

% Plot experimental curvature with error bars
figure;
errorbar(x, K_exp, K_error, 'o', ...
    'MarkerFaceColor', 'b', 'Color', 'b', 'LineWidth', 1.5, ...
    'DisplayName', 'Experimental Curvature');

hold on;

% Plot theoretical curvature
plot(x, K_theo, '--r', 'LineWidth', 1.5, 'DisplayName', 'Theoretical Curvature');

% Show value labels for both curves
for i = 1:length(x)
    % Experimental values with error
    text(x(i), K_exp(i) + K_error(i) + 0.0003, ...
        sprintf('%.5f', K_exp(i)), ...
        'FontSize', 10, 'Color', 'b', 'HorizontalAlignment', 'center');

    % Theoretical values
    text(x(i), K_theo(i) - 0.0005, ...
        sprintf('%.5f', K_theo(i)), ...
        'FontSize', 10, 'Color', 'r', 'HorizontalAlignment', 'center');
end

% Labels and formatting
xlabel('\DeltaT (Tendon Pulling Length) [mm]', 'FontSize', 12);
ylabel('Curvature K [mm^{-1}]', 'FontSize', 12);
title('Curvature vs. Tendon Pulling Length with Error Bars', 'FontSize', 14);
legend('Location', 'northwest');
grid on;
