# ===== START OF FILE docs/vis/codebase_graph_vis.py =====

import os
import json
from pyvis.network import Network

# Make sure to run create_codeindex.py - this updates the json file with all of the graph data for the code
# The main function in this code file uses that json of the function node data as it's input file
# To see the output html file
#   - Install the VS Code extension 'Live Server'
#   - right click on the output html file and (docs/codeindex/codebase_graph_vis_corpus-tools.html)
#   - choose 'Open with Live Server' at the top

''' SELECTION OF GRAPH DATA JSON FILE
{
  "nodes": [
    {
      "id": "fileops.custom_formatwarning",
      "label": "custom_formatwarning",
      "group": "function",
      "module": "fileops.py",
      "line": 18
    },
    {
      "id": "fileops.verbose_print",
      "label": "verbose_print",
      "group": "function",
      "module": "fileops.py",
      "line": 32
    },
    {
      "id": "fileops.check_file_exists",
      "label": "check_file_exists",
      "group": "function",
      "module": "fileops.py",
      "line": 51
    },
    {
      "id": "fileops.print_chars_with_indices",
      "label": "print_chars_with_indices",
      "group": "function",
      "module": "fileops.py",
      "line": 66
    },
    {
      "id": "fileops.get_suffix",
      "label": "get_suffix",
      "group": "function",
      "module": "fileops.py",
      "line": 94
    }
    ],
  "edges": [
    {
      "from": "fileops.sub_suffix_in_str",
      "to": "fileops.get_suffix"
    },
    {
      "from": "fileops.remove_all_suffixes_in_str",
      "to": "fileops.get_suffix"
    },
    {
      "from": "fileops.handle_overwrite_prompt",
      "to": "fileops.check_file_exists"
    },
    {
      "from": "fileops.handle_overwrite_prompt",
      "to": "fileops.get_suffix"
    }]
}
'''

# Constants
NETWORK_HEIGHT = "100vh"  # 100% of the viewport height
NETWORK_WIDTH = "100vw"   # 100% of the viewport width
# NETWORK_HEIGHT = "4800px"  # Height of a 5K monitor
# NETWORK_WIDTH = "5120px"  # Width of a 5K monitor
X_SPACING = 300
Y_SPACING = 50

# Styling constants
COLOR_SCHEME = {  # Comment out modules to not display in the current graph
    'fileops.py': '#76b7b2',  # Cyan
    'transcribe.py': '#f28e2c',  # Orange
    'llm.py': '#edc948',  # Yellow
    'vectordb.py': '#9c755f',  # Brown
    'rag.py': '#ff9da7',  # Pink
    'conversion.py': '#e15759',  # Red
    'docwork.py': '#59a14f',  # Green
    'structured.py': '#b07aa1',  # Purple
    'corpuses.py': '#4e79a7',  # Blue
    'webflow_api.py': '#ba55d3',  # Medium Orchid
    'video.py': '#bab0ac',  # Gray
    'aws.py': '#D2B48C',  # Tan
    'aws_valid.py': '#98FB98',  # Pale Green
    #'rag_prompts_routes.py': '#bab0ac'   # Gray
}
#COLUMN_WRAP_SUBMODULES = ['MISC FILE', 'FIND AND REPLACE', 'NUMERAL CONVERT', 'LLM FUNCTION CALLING']
COLUMN_WRAP_SUBMODULES = ['MISC FILE', 'FIND AND REPLACE', 'NUMERAL CONVERT', 'LLM PROCESSING', 'QA BY SECTIONS - Q ONLY']
NO_WRAP_MODULES = ['rag.py', 'docwork.py']

BACKGROUND_COLOR = "#000000"  # Hex for black: #000000, Hex for white: #FFFFFF
FONT_COLOR = "black"
MODULE_NODE_SHAPE = "ellipse"
MODULE_NODE_SIZE = 60
MODULE_FONT_SIZE = 24  # 24 for 5K monitor
FUNCTION_NODE_SHAPE = "box"
FUNCTION_NODE_SIZE = 40
FUNCTION_FONT_SIZE = 14  # 14 for 5K monitor
SUBMODULE_NODE_SHAPE = "box"
SUBMODULE_FONT_SIZE = 18
SUBMODULE_NODE_SIZE = 30
SUBMODULE_NODE_COLOR = '#ffffff'  # for white
SUBMODULE_TEXT_WRAP = 30

EDGE_COLOR = "rgba(255,0,0,.5)"  # semi-transparent white (rgba(255,255,255,0.5), black black, use: "rgba(0,0,0,0.5)
EDGE_WIDTH = .5

def style_graph_vis(net):
    options = {
        "physics": {
            "enabled": False
        },
        "nodes": {
            "font": {
                "color": FONT_COLOR
            },
            "shapeProperties": {
                "useBorderWithImage": False
            }
        },
        "edges": {
            "color": {
                "color": EDGE_COLOR,
                "inherit": False
            },
            "width": EDGE_WIDTH,
            "arrows": {
                "to": {
                    "enabled": True,
                    "scaleFactor": 1
                }
            },
            "smooth": {
                "enabled": True,
                "type": "dynamic"
            }
        },
        "layout": {
            "improvedLayout": True
        },
        "interaction": {
            "hover": True,
            "zoomView": True,
            "dragView": True
        }
    }

    # Set node colors, shapes, and font sizes based on their module
    for node in net.nodes:
        if node['group'] == 'module':
            module = node['id']  # set the style for module nodes based on their id, e.g. 'fileops.py'
            node['shape'] = MODULE_NODE_SHAPE
            node['size'] = MODULE_NODE_SIZE
            node['font'] = {"size": MODULE_FONT_SIZE}
        elif node['group'] == 'function':
            module = node.get('module') # set the style for function nodes based on their module attribute, e.g. 'fileops.py'
            node['shape'] = FUNCTION_NODE_SHAPE
            node['size'] = FUNCTION_NODE_SIZE
            node['font'] = {"size": FUNCTION_FONT_SIZE}
        node['color'] = COLOR_SCHEME[module]
        if node['group'] == 'submodule':
            node['shape'] = SUBMODULE_NODE_SHAPE
            node['size'] = SUBMODULE_NODE_SIZE
            node['color'] = SUBMODULE_NODE_COLOR
            node['font'] = {"size": SUBMODULE_FONT_SIZE}

    # Update the network options
    net.options.update(options)
    
def create_custom_js(output_folder):
    js_content = """

    """

    js_file_path = os.path.join(output_folder, 'custom.js')
    with open(js_file_path, 'w') as f:
        f.write(js_content)
    return js_file_path

def add_js_to_html(html_file, js_file):
    """
    Add JavaScript from a file to an HTML file just before the closing </body> tag.
    
    :param html_file: Path to the HTML file
    :param js_file: Path to the JavaScript file
    """
    # Read custom JavaScript
    with open(js_file, 'r') as f:
        custom_js = f.read()

    # Read the HTML file
    with open(html_file, 'r') as f:
        html_content = f.read()

    # Insert custom JavaScript before the closing </body> tag
    html_content = html_content.replace('</body>', f'<script>{custom_js}</script></body>')

    # Write the modified HTML content back to the file
    with open(html_file, 'w') as f:
        f.write(html_content)

class CustomNetwork(Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

    def write_html(self, name, notebook=False):
        """Override the write_html method to use absolute paths for library files."""
        html = self.generate_html()
        
        # Replace relative paths with absolute paths
        for lib in ['utils', 'vis-network.min']:
            relative_path = f'lib/bindings/{lib}.js'
            absolute_path = os.path.join(self.project_root, relative_path)
            html = html.replace(f'"{relative_path}"', f'"{os.path.relpath(absolute_path, os.path.dirname(name))}"')

        with open(name, 'w') as out:
            out.write(html)

def wrap_text_left(text, max_width):
    """
    Wraps text at a specified character width and returns the wrapped text.
    :return: Wrapped text with line breaks.
    """
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        if len(' '.join(current_line + [word])) <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return '\n'.join(lines)

def reorder_nodes(graph_data, color_scheme):
    """
    Reorder nodes based on the order in the color scheme dictionary.
    Omit nodes whose module is not in the color scheme.
    """
    ordered_nodes = []
    for module in color_scheme.keys():
        for node in graph_data['nodes']:
            if node['module'] == module:
                ordered_nodes.append(node)
    
    # Update the graph data with the ordered nodes
    graph_data['nodes'] = ordered_nodes
    
    # Filter edges to only include connections between remaining nodes
    valid_node_ids = set(node['id'] for node in ordered_nodes)
    graph_data['edges'] = [
        edge for edge in graph_data['edges']
        if edge['from'] in valid_node_ids and edge['to'] in valid_node_ids
    ]
    
    return graph_data

def create_module_based_network(input_json_file, output_html_file, input_js_file='docs/vis/codebase_graph_vis.js'):
    '''
    order of the nodes in the json determines the order of the modules in the graph - so order if from file_paths list
    '''
    # Load the graph data
    with open(input_json_file, 'r') as f:
        graph_data = json.load(f)

    # Reorder nodes based on COLOR_SCHEME
    graph_data = reorder_nodes(graph_data, COLOR_SCHEME)

    # Create a CustomNetwork instead of Network
    net = CustomNetwork(height=NETWORK_HEIGHT, width=NETWORK_WIDTH, directed=True)

    # Group nodes by module
    modules = {}
    for node in graph_data['nodes']:
        if node['module'] not in modules:
            modules[node['module']] = []
        modules[node['module']].append(node)

    # Add nodes to the network, grouped by module
    node_positions = {}  # Store node positions for edge routing
    last_submodule = None
    column = 0  # Initialize column

    for module, nodes in modules.items():
        # Add module node
        module_id = module  # module includes extension so 'fileops.py'
        if module_id not in NO_WRAP_MODULES:
            row = 0
            column += 1
        row += 1  # Add an extra row for when different modules appear in the same column.
        pos_x = column * X_SPACING
        pos_y = row * Y_SPACING
        print(f"New column for module '{module}' at column: {column}, pos_x: {pos_x}, pos_y: {pos_y}")
        net.add_node(module_id, label=module, x=pos_x, y=pos_y, group='module')
        node_positions[module_id] = (pos_x, pos_y)
        
        # Sort nodes by line number
        nodes.sort(key=lambda node: node.get('line', float('inf')) or float('inf'))
        row += 1  # for row directly under the modules

        for node in nodes:
            # Handle submodule nodes
            if node['submodule'] != last_submodule:
                if node['submodule'] in COLUMN_WRAP_SUBMODULES:
                    row = 2
                    column += 1
                    pos_x = column * X_SPACING
                module_noext = module.rsplit('.', 1)[0]
                submodule_id = f"{module_noext}.{node['submodule']}"
                pos_y = row * Y_SPACING
                net.add_node(submodule_id, label=node['submodule'], x=pos_x, y=pos_y, group='submodule', module=module)
                node_positions[submodule_id] = (pos_x, pos_y)
                last_submodule = node['submodule']
                row += 1

            pos_y = row * Y_SPACING
            net.add_node(node['id'], label=node['label'], group=node['group'], 
                        title=f"{node['def']}\n\n{node['docstring']}", x=pos_x, y=pos_y, 
                        module=node['module'], submodule=node['submodule'], line=node['line'])
            node_positions[node['id']] = (pos_x, pos_y)
            row += 1

    # Add edges to the network with custom routing
    for edge in graph_data['edges']:
        from_pos = node_positions[edge['from']]
        to_pos = node_positions[edge['to']]
        
        # Determine if it's a vertical connection (same module) or horizontal (different modules)
        if abs(from_pos[0] - to_pos[0]) < 1:  # Same module
            net.add_edge(edge['from'], edge['to'], smooth={"type": "curvedCW", "roundness": 0.2}, 
                         type=edge.get('type', 'default'), 
                         applies_to_functions=edge.get('applies_to_functions', []))
        else:  # Different modules
            # Calculate control points for a curved edge
            mid_x = (from_pos[0] + to_pos[0]) / 2
            control_point1 = f"{from_pos[0] + 50},{from_pos[1]}"
            control_point2 = f"{to_pos[0] - 50},{to_pos[1]}"
            net.add_edge(edge['from'], edge['to'], smooth={"type": "cubicBezier", 
                                                           "forceDirection": "horizontal",
                                                           "roundness": 0.4},
                         control_points={"x": [mid_x], "y": [(from_pos[1] + to_pos[1]) / 2]},
                         type=edge.get('type', 'default'), 
                         applies_to_functions=edge.get('applies_to_functions', []))
    
    # Set network options
    net.set_options(json.dumps({
        "physics": {"enabled": False},
        "layout": {"improvedLayout": True},
        "interaction": {"zoomView": True, "dragView": True}
    }))

    # Style the graph
    style_graph_vis(net)

    print(f"Create module based network in COLUMNS - Number nodes: {len(net.nodes)}, Number edges: {len(net.edges)}")

    # Calculate the bounding box of all nodes
    all_x = [node['x'] for node in net.nodes]
    all_y = [node['y'] for node in net.nodes]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    # Calculate dimensions
    width = max_x - min_x
    height = max_y - min_y

    dimensions = {
        "minX": min_x,
        "minY": min_y,
        "maxX": max_x,
        "maxY": max_y,
        "width": width,
        "height": height,
        "centerX": (min_x + max_x) / 2,
        "centerY": (min_y + max_y) / 2
    }

    # Save the network
    net.save_graph(output_html_file)
    print(f"Module-based network visualization has been saved to {output_html_file}")

    # Add custom JavaScript to the HTML file
    add_js_to_html(output_html_file, input_js_file)

    # Inject graph dimensions into the HTML file
    inject_graph_dimensions(output_html_file, dimensions)

    return net  # Return the network object

def inject_graph_dimensions(html_file, dimensions):
    with open(html_file, 'r') as f:
        content = f.read()

    graph_dimensions_js = f"""
    <script>
    const graphDimensions = {json.dumps(dimensions)};
    </script>
    """

    # Insert the graph dimensions just before the closing </head> tag
    content = content.replace('</head>', f'{graph_dimensions_js}</head>')

    with open(html_file, 'w') as f:
        f.write(content)

if __name__ == "__main__":
    # input_json_file = 'docs/codeindex/all_graph_dev.json'
    # output_html_file = 'docs/codeindex/codebase_graph_vis_corpus-tools.html'
    input_json_file = 'docs/codeindex/all_graph_dev.json'
    output_html_file = 'docs/codeindex/column_layout_graph.html'

    create_module_based_network(input_json_file, output_html_file)


### PHYSICS NETWORK
def inject_switch_button(html_file):
    with open(html_file, 'r') as f:
        content = f.read()

    switch_button_html = """
    <div style="position: fixed; top: 10px; left: 10px; z-index: 1000;">
        <button id="switchButton" onclick="switchView()">Switch View</button>
    </div>
    """

    switch_button_js = """
    <script>
    function switchView() {
        var iframe1 = document.getElementById('columnLayout');
        var iframe2 = document.getElementById('physicsLayout');
        if (iframe1.style.display === 'none') {
            iframe1.style.display = 'block';
            iframe2.style.display = 'none';
        } else {
            iframe1.style.display = 'none';
            iframe2.style.display = 'block';
        }
    }
    </script>
    """

    # Insert the button HTML just after the opening <body> tag
    content = content.replace('<body>', f'<body>{switch_button_html}')

    # Insert the JavaScript just before the closing </body> tag
    content = content.replace('</body>', f'{switch_button_js}</body>')

    with open(html_file, 'w') as f:
        f.write(content)

def add_inter_module_edges(net):
    """
    Add edges between modules, submodules, and functions to create a hierarchical structure.
    """
    modules = {}
    submodules = {}

    # First pass: identify modules and submodules
    for node in net.nodes:
        if node['group'] == 'module':
            modules[node['id']] = node
        elif node['group'] == 'submodule':
            submodules[node['id']] = node

    # Second pass: create hierarchical edges
    for node in net.nodes:
        if node['group'] == 'submodule':
            # Create edge from module to submodule
            module_id = node['module']
            net.add_edge(module_id, node['id'], arrows='to', color={'color': 'blue', 'opacity': 0.6})
        elif node['group'] == 'function':
            # Create edge from submodule to function
            submodule_id = f"{node['module'].split('.')[0]}.{node['submodule']}"
            if submodule_id in submodules:
                net.add_edge(submodule_id, node['id'], arrows='to', color={'color': 'green', 'opacity': 0.4})
            else:
                # If no submodule, connect directly to module
                net.add_edge(node['module'], node['id'], arrows='to', color={'color': 'red', 'opacity': 0.3})

def hide_inter_function_edges(net):
    """
    Hide edges between functions from different modules.
    """
    for edge in net.edges:
        from_node = edge['from'].split('.')
        to_node = edge['to'].split('.')
        if from_node[0] != to_node[0]:  # If the modules are different
            edge['hidden'] = True
            edge['color'] = {'opacity': 0.2}

def hide_function_nodes(net):
    for node in net.nodes:
        if node['group'] == 'function':
            node['hidden'] = True

def process_network_data_for_physics(network_data):
    net = CustomNetwork(height=NETWORK_HEIGHT, width=NETWORK_WIDTH, directed=True)

    nodes, edges, *_ = network_data

    # Add all nodes from the original network
    for node in nodes:
        # Remove position data
        node.pop('x', None)
        node.pop('y', None)
        net.add_node(node['id'], **node)

    # Add all edges from the original network
    for edge in edges:
        net.add_edge(edge['from'], edge['to'])

    # Add inter-module edges
    add_inter_module_edges(net)

    # Hide inter-function edges
    hide_inter_function_edges(net)

    print(f"Create module based network for PHYSICS - Number nodes: {len(net.nodes)}, Number edges: {len(net.edges)}")

    return net

def set_physics_options(net):
    options = {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 25,
                "onlyDynamicEdges": False,
                "fit": True
            }
        },
        "layout": {
            "improvedLayout": True
        },
        "interaction": {
            "hover": True,
            "zoomView": True,
            "dragView": True,
            "navigationButtons": True
        }
    }
    
    # Convert the options dictionary to a JSON string
    options_json = json.dumps(options)
    
    # Set the physics options
    net.set_options(options_json)

def create_physics_enabled_network(network_data, output_html_file):
    # Create a Pyvis network with the example settings
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    
    nodes, edges, *_ = network_data

    # Add nodes to the network
    for node in nodes:
        net.add_node(node['id'], label=node['label'], title=node.get('title', node['label']), 
                     group=node['group'], color=node.get('color'))

    # Add edges to the network
    for edge in edges:
        net.add_edge(edge['from'], edge['to'])

    # Set physics options directly
    physics_options = {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0
            },
            "maxVelocity": 50,
            "minVelocity": 0.1,
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 25,
                "onlyDynamicEdges": False,
                "fit": True
            }
        },
        "layout": {
            "improvedLayout": True
        },
        "interaction": {
            "hover": True,
            "zoomView": True,
            "dragView": True,
            "navigationButtons": True
        }
    }

    net.set_options(json.dumps(physics_options))

    # Optionally hide function nodes
    # hide_function_nodes(net)

    # Save the network
    net.save_graph(output_html_file)
    print(f"Physics-enabled network visualization has been saved to {output_html_file}")

# if __name__ == "__main__":
#     input_json_file = 'docs/codeindex/all_graph_dev.json'
#     output_column_html = 'docs/codeindex/column_layout_graph.html'
#     output_physics_html = 'docs/codeindex/physics_layout_graph.html'
#     output_combined_html = 'docs/codeindex/combined_graph_views.html'

#     # Create the column-based layout
#     column_network = create_module_based_network(input_json_file, output_column_html)

#     # Debugging: Print information about the network data
#     network_data = column_network.get_network_data()
#     print("Type of network_data:", type(network_data))
#     print("Length of network_data:", len(network_data))
#     print("First few elements of network_data:")
#     for i, item in enumerate(network_data[:5]):
#         item_str = str(item)
#         if len(item_str) > 200:
#             item_str = item_str[:197] + "..."
#         print(f"Item {i}:", type(item), item_str)

#     # Create the physics-enabled layout
#     create_physics_enabled_network(network_data, output_physics_html)

#     # Create a combined HTML file with both views
#     combined_html_content = f"""
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <title>Combined Graph Views</title>
#         <style>
#             body, html {{
#                 margin: 0;
#                 padding: 0;
#                 height: 100%;
#                 overflow: hidden;
#             }}
#             iframe {{
#                 width: 100%;
#                 height: 100%;
#                 border: none;
#             }}
#         </style>
#     </head>
#     <body>
#         <iframe id="columnLayout" src="{os.path.basename(output_column_html)}"></iframe>
#         <iframe id="physicsLayout" src="{os.path.basename(output_physics_html)}" style="display:none;"></iframe>
#     </body>
#     </html>
#     """

#     with open(output_combined_html, 'w') as f:
#         f.write(combined_html_content)

#     # Inject the switch button into the combined HTML file
#     inject_switch_button(output_combined_html)

#     print(f"Combined view with switch button has been saved to {output_combined_html}")

# ===== END OF FILE docs/vis/codebase_graph_vis.py =====