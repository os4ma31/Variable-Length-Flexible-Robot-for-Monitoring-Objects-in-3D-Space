% Data
x = [-10, -18.87, -22.71, -30.1, -36];      % ΔT (Tendon Distance) in mm
K_exp = [0.0051, 0.0094, 0.0123, 0.01463, 0.0187]; % Experimental curvature (mm^-1)
K_theo = [0.0052, 0.0098, 0.0117, 0.01556, 0.0181]; % Theoretical curvature (mm^-1)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Points used to calculate the theoretical values:
% #1 (-7.5, 1.2)(1.8, -0.5)(5.88, -1.1)
% #2 (-6.2, 0.5)(0, 0)(7.5, -1.1)
% #3 (-4.25, 1.42)(0, 0)(3.2, -0.9)
% #4 (-0.77, 3)(0, 0.6)(1, -3.1)
% #5 (-0.78, 3)(0, 0)(1, -3.1)"
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% --- Calculations ---
% Calculate the absolute error (|K_theoretical - K_experimental|)
K_error = abs(K_theo - K_exp);

% Calculate the error percentage relative to the theoretical value
Error_percentage = (K_error ./ K_theo) * 100;

% --- Plotting Section ---
% Create the first figure for the plot
figure('Name', 'Curvature Plot');

% Plot experimental curvature with error bars
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

% Labels and formatting for the plot
xlabel('\DeltaT (Tendon Pulling Length) [mm]', 'FontSize', 12);
ylabel('Curvature K [mm^{-1}]', 'FontSize', 12);
title('Curvature vs. Tendon Pulling Length with Error Bars', 'FontSize', 14);
legend('Location', 'northwest');
grid on;
hold off;

% --- Print Table to Command Window Section ---
% Display a title for the output in the command window
fprintf('\n--- Comparison of Experimental and Theoretical Curvature Data ---\n');

% Print the header for the table
fprintf('%-25s %-25s %-25s %-25s %-20s\n', ...
    'ΔT (mm)', ...
    'Experimental K (mm^-1)', ...
    'Theoretical K (mm^-1)', ...
    'Absolute Error (mm^-1)', ...
    'Percentage Error (%)');
    
% Print a separator line to make the table easier to read
fprintf([repmat('-', 1, 125) '\n']);

% Loop through the data and print each row of the table
% '%.4f' formats the numbers to show four decimal places
for i = 1:length(x)
    fprintf('%-25.2f %-25.4f %-25.4f %-25.4f %-20.2f\n', ...
        x(i), K_exp(i), K_theo(i), K_error(i), Error_percentage(i));
end
