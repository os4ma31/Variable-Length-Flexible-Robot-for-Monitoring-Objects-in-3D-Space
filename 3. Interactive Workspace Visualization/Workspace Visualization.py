import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons
import numpy as np
from scipy.spatial import ConvexHull

# --- Data from Manual Measurements (Max Length) - UPDATED ---
# Using the corrected values you provided.
max_length_points = {
    "Zero-Zero": {
        "end_effector": [6.5, -1.3, 2], "link1": [6.5, 17.2, 1.4], "base": [6.5, 32.5, 4]
    },
    "Up-Up": {
        "end_effector": [6.5, 20, 19], "link1": [6.5, 16.5, 10], "base": [6.5, 32.5, 4]
    },
    "Up-Right": {
        "end_effector": [10, 24, 17], "link1": [6.5, 17.5, 7.5], "base": [6.5, 32.5, 4]
    },
    "Up-Left": {
        "end_effector": [1.25, 20, 16.5], "link1": [4.5, 16, 4.5], "base": [6.5, 32.5, 4]
    },
    "Right-Right": {
        "end_effector": [-11, 7, -3.5], "link1": [3, 17, 1.4], "base": [6.5, 32.5, 4]
    },
    "Left-Left": {
        "end_effector": [21, 4, -3.5], "link1": [8.45, 16.5, 1.4], "base": [6.5, 32.5, 4]
    }
}


# --- Generate Min Length Data ---
# This automatically uses the updated max_length_points
min_length_points = {}
for name, config in max_length_points.items():
    min_length_points[name] = {
        "end_effector": [config["end_effector"][0], config["end_effector"][1] + 10, config["end_effector"][2]],
        "link1": [config["link1"][0], config["link1"][1] + 10, config["link1"][2]],
        "base": [config["base"][0], config["base"][1] + 10, config["base"][2]]
    }

# --- Setup the Plot ---
fig = plt.figure(figsize=(15, 10))
# Adjust main plot to make space for widgets on the left
ax = fig.add_axes([0.25, 0.1, 0.7, 0.8], projection='3d')
fig.subplots_adjust(left=0.25)


# --- Plotting Logic ---
# Dictionaries to hold the plot artist objects (lines and text) for toggling visibility
plotted_artists = {'Max': {}, 'Min': {}}
all_end_effectors = []

# Function to plot a single arm configuration and store its artists
def plot_arm(config, arm_color, length_type, config_name):
    base, link1, ee = config["base"], config["link1"], config["end_effector"]
    # The workspace is defined by the end-effector positions
    all_end_effectors.append(ee)
    
    # Plot segments and store the line objects
    line1, = ax.plot([base[0], link1[0]], [base[1], link1[1]], [base[2], link1[2]], color=arm_color, marker='o', linestyle='-', visible=False)
    line2, = ax.plot([link1[0], ee[0]], [link1[1], ee[1]], [link1[2], ee[2]], color=arm_color, marker='o', linestyle='-', visible=False)
    
    # Add text labels for each point
    text_base = ax.text(base[0], base[1], base[2], 'Base', color='black', visible=False)
    text_link1 = ax.text(link1[0], link1[1], link1[2], 'Link 1', color='purple', visible=False)
    text_ee = ax.text(ee[0], ee[1], ee[2], 'EE', color='red', visible=False)

    # Store all artists (lines and text) for easy access later
    plotted_artists[length_type][config_name] = [line1, line2, text_base, text_link1, text_ee]

# Plot all configurations but keep them invisible initially
for name, config in max_length_points.items():
    plot_arm(config, 'blue', 'Max', name)
for name, config in min_length_points.items():
    plot_arm(config, 'green', 'Min', name)

# --- Plot Workspace (Convex Hull) ---
# The hull is calculated from ALL end-effector points (min and max length).
# It represents the reachable volume of the end-effector.
all_end_effectors = np.array(all_end_effectors)
hull = ConvexHull(all_end_effectors)
# The Poly3DCollection is the object representing the hull surface
hull_surface = ax.plot_trisurf(
    all_end_effectors[:, 0], all_end_effectors[:, 1], all_end_effectors[:, 2],
    triangles=hull.simplices, color='red', alpha=0.2
)
hull_surface.set_visible(False) # Initially hidden

# --- Create Interactive Widgets ---
# Define positions for the widgets
rax_len = plt.axes([0.02, 0.7, 0.18, 0.10])  # Checkboxes for length
rax_conf = plt.axes([0.02, 0.4, 0.18, 0.25]) # Checkboxes for configurations
rax_ws = plt.axes([0.02, 0.3, 0.18, 0.05])   # Checkbox for workspace

# Create the widgets
config_labels = list(max_length_points.keys())
# All configs start as unchecked
initial_visibility = [False] * len(config_labels)

# Changed from RadioButtons to CheckButtons to allow multiple selections
check_len = CheckButtons(rax_len, ('Max Length', 'Min Length'), [False, False])
check_conf = CheckButtons(rax_conf, config_labels, initial_visibility)
check_ws = CheckButtons(rax_ws, ['Show Workspace'], [False])

# --- Update Function ---
# This function is called whenever a widget is clicked
def update_visibility(label):
    # Get visibility status for lengths and configurations
    len_visibility = check_len.get_status()    # [is_max_visible, is_min_visible]
    conf_visibility = check_conf.get_status()  # [is_zero_visible, is_upup_visible, ...]
    
    show_max = len_visibility[0]
    show_min = len_visibility[1]

    # Iterate through each configuration type (e.g., "Up-Up")
    for i, config_name in enumerate(config_labels):
        # Check if this specific configuration should be shown
        show_config = conf_visibility[i]

        # Set visibility for Max Length artists
        for artist in plotted_artists['Max'][config_name]:
            artist.set_visible(show_max and show_config)

        # Set visibility for Min Length artists
        for artist in plotted_artists['Min'][config_name]:
            artist.set_visible(show_min and show_config)
            
    # Toggle workspace visibility
    workspace_visible = check_ws.get_status()[0]
    hull_surface.set_visible(workspace_visible)
    
    # Redraw the plot with the new visibility settings
    plt.draw()

# Connect the widgets to the update function
check_len.on_clicked(update_visibility)
check_conf.on_clicked(update_visibility)
check_ws.on_clicked(update_visibility)

# --- Final Plot Adjustments ---
ax.set_xlabel('X-axis (cm)')
ax.set_ylabel('Y-axis (cm)')
ax.set_zlabel('Z-axis (cm)')
ax.set_title('Interactive Workspace of Hyper-Redundant Manipulator')
ax.grid(True)
# Set axis limits to ensure all points are visible regardless of selection
ax.set_xlim(-15, 25)
ax.set_ylim(-5, 55) # Increased Y-limit to accommodate new base positions + 10
ax.set_zlim(-5, 25)

plt.show()
