// START OF FILE codebase_graph_vis.js
var fileInfo = `codebase_graph_vis.js   11-04 0714`;
console.log('=== JavaScript file loaded: ', fileInfo, ' ===');

function logNodePosition(nodeId) {
  let node = network.body.data.nodes.get(nodeId);
  if (node) {
      let nodePosition = network.getPositions([nodeId])[nodeId];
      let nodeBoundingBox = network.getBoundingBox(nodeId);
      
      let roundedNodePosition = {
          x: Math.round(nodePosition.x),
          y: Math.round(nodePosition.y)
      };
      let roundedNodeBoundingBox = {
          left: Math.round(nodeBoundingBox.left),
          top: Math.round(nodeBoundingBox.top),
          right: Math.round(nodeBoundingBox.right),
          bottom: Math.round(nodeBoundingBox.bottom)
      };
      let width = nodeBoundingBox.right - nodeBoundingBox.left;
      let height = nodeBoundingBox.bottom - nodeBoundingBox.top;

      console.log(`Node ID: ${nodeId}`);
      console.log(`  Center: {x: ${roundedNodePosition.x}, y: ${roundedNodePosition.y}}`);
      console.log(`  Bounding Box: {minX: ${roundedNodeBoundingBox.left}, minY: ${roundedNodeBoundingBox.top}, maxX: ${roundedNodeBoundingBox.right}, maxY: ${roundedNodeBoundingBox.bottom}}`);
      console.log(`  Dimensions: {Width: ${Math.round(width)}, Height: ${Math.round(height)}}`);
  } else {
      console.log(`Node with ID ${nodeId} not found.`);
  }
}

function getGraphBoundingBox() {
  let allNodes = network.body.data.nodes.get();
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

  allNodes.forEach(node => {
      let nodeBoundingBox = network.getBoundingBox(node.id);
      if (nodeBoundingBox.left < minX) minX = nodeBoundingBox.left;
      if (nodeBoundingBox.top < minY) minY = nodeBoundingBox.top;
      if (nodeBoundingBox.right > maxX) maxX = nodeBoundingBox.right;
      if (nodeBoundingBox.bottom > maxY) maxY = nodeBoundingBox.bottom;
  });

  return { 
    minX: Math.round(minX), 
    minY: Math.round(minY), 
    maxX: Math.round(maxX), 
    maxY: Math.round(maxY) 
  };
}

// ### LOG ALL COORDS
function logAllCoords() {
  console.log("LOG ALL COORDINATES");
  console.log("  Canvas dimensions:", {
      width: network.canvas.frame.clientWidth,
      height: network.canvas.frame.clientHeight
  });
  console.log("  Visible area dimensions:", {
      width: network.canvas.frame.offsetWidth,
      height: network.canvas.frame.offsetHeight
  });
  console.log("  Body dimensions:", {
      width: document.body.clientWidth,
      height: document.body.clientHeight
  });
  let boundingBox = getGraphBoundingBox();
  console.log("  Graph bounding box:", boundingBox);
  console.log(`  Graph bounding dimensions: {width: ${boundingBox.maxX - boundingBox.minX}, height: ${boundingBox.maxY - boundingBox.minY}}`);
}
function logAllCoordsUICREATE() {
  // Add an Align Nodes Left button
  var alignNodesLeftButton = document.createElement('button');
  alignNodesLeftButton.innerHTML = 'Log All Coords';
  alignNodesLeftButton.style.position = 'absolute';
  alignNodesLeftButton.style.left = '320px';
  alignNodesLeftButton.style.top = '10px';
  alignNodesLeftButton.style.zIndex = '1000';
  alignNodesLeftButton.onclick = logAllCoords;
  document.body.appendChild(alignNodesLeftButton);
}
logAllCoordsUICREATE();

// ### AUTO FIT GRAPH
function autoFitGraph() {
  if (!network || !network.body || !network.body.data.nodes.length) {
    console.error('Network is not ready or empty.');
    return;
  }

  const TOP_MARGIN = 30;

  const container = network.canvas.frame;
  const containerWidth = container.clientWidth;
  const containerHeight = container.clientHeight;
  console.log(`Auto Scale Graph`);
  console.log(`   Container dimensions - Width: ${containerWidth}, Height: ${containerHeight}`);

  const graphBoundingBox = getGraphBoundingBox();
  const graphWidth = graphBoundingBox.maxX - graphBoundingBox.minX;
  const graphHeight = graphBoundingBox.maxY - graphBoundingBox.minY;
  console.log(`   Graph bounding dimensions: {width: ${graphWidth}, height: ${graphHeight}}`);

  const scaleX = containerWidth / graphWidth;
  const scaleY = (containerHeight - TOP_MARGIN) / graphHeight;
  const scale = Math.min(scaleX, scaleY);
  console.log(`   Scale factors - scaleX: ${scaleX.toFixed(3)}, scaleY: ${scaleY.toFixed(3)}, scale: ${scale.toFixed(3)}`);

  const offsetX = (graphBoundingBox.minX + graphBoundingBox.maxX) / 2;
  const offsetY = ((graphBoundingBox.minY + graphBoundingBox.maxY) / 2) - TOP_MARGIN / 2;
  console.log(`   Offsets - offsetX: ${offsetX}, offsetY: ${offsetY}`);

  network.moveTo({
    position: {x: offsetX, y: offsetY},
    scale: scale,
    animation: false
  });
}
function autoFitGraphUICREATE() {
  // Add an Auto Fit Graph button
  var autoFitButton = document.createElement('button');
  autoFitButton.innerHTML = 'Auto Fit Graph';
  autoFitButton.style.position = 'absolute';
  autoFitButton.style.left = '460px';
  autoFitButton.style.top = '10px';
  autoFitButton.style.zIndex = '1000';
  autoFitButton.onclick = autoFitGraph;
  document.body.appendChild(autoFitButton);
}
autoFitGraphUICREATE();

// ### SHOW ENTIRE CONTAINER
function showEntireContainer() {
  if (!network || !network.body || !network.body.data.nodes.length) {
    console.error('Network is not ready or empty.');
    return;
  }

  const container = network.canvas.frame; // Corrected from network.container.frame to network.canvas.frame
  const containerWidth = container.clientWidth;
  const containerHeight = container.clientHeight;
  console.log(`SHOW ENTIRE CONTAINER: width: ${containerWidth}, height: ${containerHeight}`);

  // Get the browser window dimensions
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;
  console.log(`   Window dimensions - Width: ${windowWidth}, Height: ${windowHeight}`);

  // Calculate the scale to fit the container into the window
  const scaleX = windowWidth / containerWidth;
  const scaleY = windowHeight / containerHeight;
  const scale = Math.min(scaleX, scaleY);
  console.log(`   Scale factors - scaleX: ${scaleX.toFixed(2)}, scaleY: ${scaleY.toFixed(2)}, scale: ${scale.toFixed(2)}`);

  // Center the container in the window
  const offsetX = (windowWidth - containerWidth * scale) / 2;
  const offsetY = (windowHeight - containerHeight * scale) / 2;
  console.log(`   Offsets - offsetX: ${offsetX.toFixed(2)}, offsetY: ${offsetY.toFixed(2)}`);

  // Move the network to fit the entire container in the viewport
  network.moveTo({
    position: { x: containerWidth / 2, y: containerHeight / 2 },
    offset: { x: offsetX, y: offsetY },
    scale: scale,
    animation: false
  });
}
function showEntireContainerUICREATE() {
  // Add a Show Entire Container button
  var showEntireContainerButton = document.createElement('button');
  showEntireContainerButton.innerHTML = 'Show Entire Container';
  showEntireContainerButton.style.position = 'absolute';
  showEntireContainerButton.style.left = '600px';
  showEntireContainerButton.style.top = '10px';
  showEntireContainerButton.style.zIndex = '1000';
  showEntireContainerButton.onclick = showEntireContainer;
  document.body.appendChild(showEntireContainerButton);
}
showEntireContainerUICREATE();

function setStartingEdgeColors() {
  const allEdges = edges.get();
  const controllerToWorkerCount = allEdges.filter(edge => edge.type === 'controller_to_worker').length;

  console.log(`Number of controller_to_worker edges: ${controllerToWorkerCount}`);

  edges.update(allEdges.map(edge => {
    if (edge.type === 'controller_to_worker') {
      return {
        ...edge,
        hidden: false,
        dashes: false,
        color: {color: 'red'}
      };
    } else {
      return {
        ...edge,
        hidden: false,
        dashes: false,
        color: {color: 'black'}
      };
    }
  }));

  console.log(`Total number of edges: ${allEdges.length}`);
}

// ### SET INITIAL VIEW
// Store the initial view state
let initialViewState = null;
function setInitialView() {
  if (network && network.body && network.body.data.nodes.length > 0) {
      logAllCoords();
      logNodePosition('fileops.py');
      console.log('Setting initial view');
      console.log('Graph Dimensions:', graphDimensions);

      // First, fit the entire graph
      network.fit({
          animation: false
      });

      // Get the current position after fitting
      let currentPosition = network.getViewPosition();

      // Set an offset (e.g., 500 pixels right and down) and a specific zoom level
      // let offsetX = 1490;
      // let offsetY = 2050;
      // let scale = 0.85;  // Adjust this value to zoom in or out
      let offsetX = 0;
      let offsetY = 0;
      let scale = .5;  // Adjust this value to zoom in or out

      // Move to the new position with offset and apply the scale
      network.moveTo({
          position: {x: currentPosition.x + offsetX, y: currentPosition.y + offsetY},
          scale: scale,
          animation: false
      });

      // Store the initial view state
      initialViewState = {
        position: network.getViewPosition(),
        scale: network.getScale()
      };

      // alignNodesLeft();
      // dimUnconnectedNodes(dimUnconnectedCheckbox.checked);
  } else {
      console.log('Network not ready or empty');
  }
}
// Ensure setInitialView is called after the network is fully loaded
// network.once("afterDrawing", setInitialViewToHome);
setInitialView()
logViewPosition()
alignNodesLeft()
autoFitGraph()
setStartingEdgeColors()

// ### RESET VIEW TO HOME
function resetViewToHome() {
  setInitialViewToHome()
}
function resetViewToHomeUICREATE() {
  var setInitialViewButton = document.createElement('button');
  setInitialViewButton.innerHTML = 'Reset View To Home';
  setInitialViewButton.style.position = 'absolute';
  setInitialViewButton.style.left = '10px'; // Positioned to the right of the initial reset button
  setInitialViewButton.style.top = '10px';
  setInitialViewButton.style.zIndex = '1000';
  setInitialViewButton.onclick = resetViewToHome;
  document.body.appendChild(setInitialViewButton);
}
resetViewToHomeUICREATE()

// ### SET HOME VIEW
function setHomeView() {
  
}
function setHomeViewUICREATE() {
  var setInitialViewButton = document.createElement('button');
  setInitialViewButton.innerHTML = 'Set Home View';
  setInitialViewButton.style.position = 'absolute';
  setInitialViewButton.style.left = '180px';
  setInitialViewButton.style.top = '10px';
  setInitialViewButton.style.zIndex = '1000';
  setInitialViewButton.onclick = resetViewToHome;
  document.body.appendChild(setInitialViewButton);
}
setHomeViewUICREATE()

function logViewPosition() {
    const center = network.getViewPosition();
    const scale = network.getScale();
    const canvas = network.canvas.frame;
    
    // Calculate top-left corner
    const topLeft = {
        x: Math.round(center.x - (canvas.clientWidth / (2 * scale))),
        y: Math.round(center.y - (canvas.clientHeight / (2 * scale)))
    };

    // Calculate bottom-right corner
    const bottomRight = {
        x: Math.round(center.x + (canvas.clientWidth / (2 * scale))),
        y: Math.round(center.y + (canvas.clientHeight / (2 * scale)))
    };

    // Calculate width and height
    const width = bottomRight.x - topLeft.x;
    const height = bottomRight.y - topLeft.y;
    
    console.log(`CURRENT VIEW POSITION`);
    console.log(`  minX: ${topLeft.x}, minY: ${topLeft.y}, maxX: ${bottomRight.x}, maxY: ${bottomRight.y}`);
    console.log(`  width: ${width}, height: ${height}, scale: ${scale.toFixed(2)}`);
}
network.on("dragEnd", logViewPosition);
network.on("zoom", logViewPosition);



// ### FOCUS NODE
function getFunctionNodesFromModuleOrSub(moduleOrSubID) {  // helper that returns array of function node IDs
  var allNodes = nodes.get();
  var moduleOrSubIDNode = nodes.get(moduleOrSubID);
  var functionNodeIds = [];

  if (moduleOrSubIDNode.group === 'module') {
    console.log(`Focus on module node: ${moduleOrSubIDNode.id}`);
    functionNodeIds = allNodes
      .filter(node => node.group === 'function' && node.module === moduleOrSubIDNode.id)
      .map(node => node.id);
  } else if (moduleOrSubIDNode.group === 'submodule') {
    var submoduleName = moduleOrSubIDNode.id.split('.').pop(); // Strip everything before and including the last dot
    console.log(`Focus on submodule node: ${moduleOrSubIDNode.id}`);
    console.log(`  Submodule name: ${submoduleName}`);
    functionNodeIds = allNodes
      .filter(node => node.group === 'function' && node.submodule === submoduleName)
      .map(node => node.id);
  }

  console.log(`  Number of function nodes: ${functionNodeIds.length}`);

  return functionNodeIds;
}

function tracebackFunction(nodeID) {  // returns array of node IDs reachable thru outgoing edges excluding input node
  var allEdges = edges.get();
  var tracedNodeIDs = new Set();
  var nodesToProcess = [nodeID];

  while (nodesToProcess.length > 0) {
    var currentNodeID = nodesToProcess.pop();

    // Find all outgoing edges from the current node
    var outgoingEdges = allEdges.filter(edge => edge.from === currentNodeID);

    // Add the target nodes of these edges to the processing queue
    outgoingEdges.forEach(edge => {
      if (!tracedNodeIDs.has(edge.to) && edge.to !== nodeID) {
        // Check if the edge is a controller_to_worker edge and if it should be traced
        if (edge.type === 'controller_to_worker' && edge.applies_to_functions && !edge.applies_to_functions.includes(nodeID)) {
          return;
        }
        tracedNodeIDs.add(edge.to);
        nodesToProcess.push(edge.to);
      }
    });
  }

  console.log(`  Number of nodes traced back: ${tracedNodeIDs.size}`);
  return Array.from(tracedNodeIDs);
}

function focusNodes(nodeId) {
  var focusedNode = nodes.get(nodeId);
  var allEdges = edges.get();
  var functionNodeIds = [];
  var parentNodeIds = [];

  resetFocus()

  // Select focus for all nodes in a module or sub or just the single input node
  if (focusedNode.group === 'module' || focusedNode.group === 'submodule') {
    functionNodeIds = getFunctionNodesFromModuleOrSub(focusedNode.id);
  } else if (focusedNode.group === 'function') {
    functionNodeIds = [nodeId];
  }

  // Modify border and font for all focus function nodes
  functionNodeIds.forEach(function(nodeId) {
    console.log(`Modifying style of focus function node: ${nodeId}`);
    var node = nodes.get(nodeId);
    node.borderWidth = 4;
    node.font = { 
      ...node.font, 
      bold: true
    };
    nodes.update(node);
  });
    
  // Find parent nodes (immediate callers of the focus nodes)
  parentNodeIds = allEdges
    .filter(edge => functionNodeIds.includes(edge.to))
    .map(edge => edge.from);

  // Show and style edges
  allEdges.forEach(function(edge) {
    if (functionNodeIds.includes(edge.to) && parentNodeIds.includes(edge.from)) {
      // Incoming edges to the focus nodes (from parent nodes)
      edge.hidden = false;
      edge.dashes = [5, 5]; // Dotted line
    } else {
      edge.hidden = true;
    }
  });

  // Trace back function nodes and update functionNodeIds
  let tracedNodeIds = new Set(functionNodeIds);
  functionNodeIds.forEach(function(nodeId) {
    tracebackFunction(nodeId).forEach(id => tracedNodeIds.add(id));
  });
  functionNodeIds = Array.from(tracedNodeIds);

  // Show outgoing edges for all traced nodes
  var directChildNodeIds = allEdges
    .filter(edge => edge.from === nodeId)
    .map(edge => edge.to);

  allEdges.forEach(function(edge) {
    if (functionNodeIds.includes(edge.from)) {
      // Outgoing edges from any function in the traced nodes
      edge.hidden = false;
      edge.dashes = false; // Solid line
      edge.color = 'blue';
      if (!directChildNodeIds.includes(edge.to)) {
        edge.color = 'black';
      }
    }
  });

  // Hide controller_to_worker edges that do not apply to the current focus node
  allEdges.forEach(function(edge) {
    if (edge.type === 'controller_to_worker' && edge.applies_to_functions && !edge.applies_to_functions.includes(nodeId)) {
      edge.hidden = true;
    }
  });

  edges.update(allEdges);

  // Reapply dimming based on current checkbox state
  dimUnconnectedNodes(dimUnconnectedCheckbox.checked);

  network.redraw();
}

// Call this after focusNode
network.on("click", function(params) {
  if (params.nodes.length > 0) {
      var nodeId = params.nodes[0];
      focusNodes(nodeId);
  }
});


// ### RESET FOCUS
// shows all function-to-function connected edges
function resetFocus() {
  var allNodes = nodes.get();
  var allEdges = edges.get();

  //console.log("Before Reset Focus:", edges.get().map(e => e.color));

  // Reset all node styles
  allNodes.forEach(function(node) {
      node.borderWidth = 1;
      node.font = {
          ...node.font,
          size: node.font.size, // Reset to original size
          bold: false
      };
  });

  // Show all edges and reset dashes
  allEdges.forEach(function(edge) {
      edge.hidden = false;
      edge.dashes = false;
  });

  //setEdgeColors()

  nodes.update(allNodes);
  edges.update(allEdges);

  // Reapply dimming based on current checkbox state
  dimUnconnectedNodes(dimUnconnectedCheckbox.checked);

  network.redraw();
  //console.log("After Reset Focus:", edges.get().map(e => e.color));
}

function resetFocusUICREATE() {
  var resetToInitialButton = document.createElement("button");
  resetToInitialButton.innerHTML = "Reset Focus";
  resetToInitialButton.style.position = "absolute";
  resetToInitialButton.style.left = "960px";
  resetToInitialButton.style.top = "10px";
  resetToInitialButton.onclick = function() {
    network.unselectAll();
    resetFocus();
  };
  document.body.appendChild(resetToInitialButton);
}

resetFocusUICREATE()


// ### ALIGN NODES LEFT
function alignNodesLeft() {
  console.log("Aligning non-module nodes to the left...");
  var allNodes = nodes.get();
  var nonModuleNodes = allNodes.filter(node => node.group !== 'module');
  var nodesToUpdate = [];

  if (nonModuleNodes.length === 0) {
    console.log("No non-module nodes found.");
    return;
  }

  // Group nodes by their column for alignment
  var columnGroups = {};
  allNodes.forEach(node => {
    var nodeBox = network.getBoundingBox(node.id);
    var nodeLeftEdge = Math.round(node.x - (nodeBox.right - nodeBox.left) / 2);
    var columnKey = Math.round(node.x); // Use rounded x-coordinate as a key for grouping

    if (!columnGroups[columnKey]) {
      columnGroups[columnKey] = {
        leftEdge: nodeLeftEdge,
        nodes: []
      };
    }

    columnGroups[columnKey].nodes.push(node);

    // Update the leftmost edge if this node is further left
    if (nodeLeftEdge < columnGroups[columnKey].leftEdge) {
      columnGroups[columnKey].leftEdge = nodeLeftEdge;
    }
  });

  // Align all nodes in each column to the leftmost edge
  Object.values(columnGroups).forEach(group => {
    group.nodes.forEach(node => {
      var nodeBox = network.getBoundingBox(node.id);
      var nodeLeftEdge = Math.round(node.x - (nodeBox.right - nodeBox.left) / 2);
      var shiftX = group.leftEdge - nodeLeftEdge;

      if (node.group === 'function') {
        node.x += shiftX; // Shift the x position to align with the leftmost node with an additional offset
      } else {
        node.x += shiftX - 20; // Shift the x position to align with the leftmost node without additional offset
      }
      nodesToUpdate.push(node);
    });
  });

  if (nodesToUpdate.length > 0) {
    nodes.update(nodesToUpdate);
    network.fit();
    console.log(`${nodesToUpdate.length} nodes updated and aligned.`);
  } else {
    console.log("No nodes were updated.");
  }
}
function alignNodesLeftUICREATE() {
  // Add an Align Nodes Left button
  var alignNodesLeftButton = document.createElement('button');
  alignNodesLeftButton.innerHTML = 'Align Nodes Left';
  alignNodesLeftButton.style.position = 'absolute';
  alignNodesLeftButton.style.left = '800px'; // Positioned further to the right of the reset view button
  alignNodesLeftButton.style.top = '10px';
  alignNodesLeftButton.style.zIndex = '1000';
  alignNodesLeftButton.onclick = alignNodesLeft;
  document.body.appendChild(alignNodesLeftButton);
}
alignNodesLeftUICREATE();


// ### DIM UNCONNECTED NODES
function dimUnconnectedNodes(checked) {
    var allNodes = network.body.data.nodes.get();
    var nodesToUpdate = [];
    var connectedNodeCount = 0;
    var moduleToFunctions = {};  // Track functions per module
    var moduleConnectivity = {}; // Track connected functions per module

    // Initialize module tracking
    allNodes.forEach(function(node) {
        if (node.group === 'module') {
            moduleToFunctions[node.id] = 0;
            moduleConnectivity[node.id] = 0;
        }
        if (node.group === 'function') {
            let moduleId = node.module;
            moduleToFunctions[moduleId] = (moduleToFunctions[moduleId] || 0) + 1;
        }
    });

    // First pass: determine function node connectivity
    allNodes.forEach(function(node) {
        if (node.group === 'function') {
            if (checked) {
                var connectedEdges = network.getConnectedEdges(node.id).filter(edgeId => {
                    var edge = network.body.data.edges.get(edgeId);
                    return edge.hidden !== true;
                });

                if (connectedEdges.length > 0) {
                    node.opacity = 1;
                    moduleConnectivity[node.module]++;
                    connectedNodeCount++;
                } else {
                    node.opacity = 0.2;
                }
            } else {
                node.opacity = 1;
                moduleConnectivity[node.module]++;
            }
            nodesToUpdate.push(node);
        }
    });

    // Second pass: update module nodes based on their functions' connectivity
    allNodes.forEach(function(node) {
        if (node.group === 'module') {
            if (checked) {
                // Dim module if all its functions are dimmed or if it has no functions
                let totalFunctions = moduleToFunctions[node.id] || 0;
                let connectedFunctions = moduleConnectivity[node.id] || 0;
                node.opacity = (totalFunctions > 0 && connectedFunctions > 0) ? 1 : 0.2;
            } else {
                node.opacity = 1;
            }
            nodesToUpdate.push(node);
        }
    });

    console.log(`Dimming unconnected nodes for all but ${connectedNodeCount} nodes.`);
    network.body.data.nodes.update(nodesToUpdate);
    network.redraw();
}
function dimUnconnectedNodesUICREATE() {
  var dimUnconnectedCheckbox = document.createElement('input');
  dimUnconnectedCheckbox.type = 'checkbox';
  dimUnconnectedCheckbox.id = 'dimUnconnectedCheckbox';
  dimUnconnectedCheckbox.checked = true; // Initially checked
  dimUnconnectedCheckbox.style.position = 'absolute';
  dimUnconnectedCheckbox.style.left = '1100px';
  dimUnconnectedCheckbox.style.top = '20px';
  dimUnconnectedCheckbox.style.zIndex = '1000';
  document.body.appendChild(dimUnconnectedCheckbox);

  var dimUnconnectedLabel = document.createElement('label');
  dimUnconnectedLabel.htmlFor = 'dimUnconnectedCheckbox';
  dimUnconnectedLabel.innerHTML = 'Dim Unconnected Nodes';
  dimUnconnectedLabel.style.position = 'absolute';
  dimUnconnectedLabel.style.left = '1120px';
  dimUnconnectedLabel.style.top = '15px';
  dimUnconnectedLabel.style.zIndex = '1000';
  document.body.appendChild(dimUnconnectedLabel);

  var dimUnconnectedButton = document.createElement('button');
  dimUnconnectedButton.innerHTML = 'Dim';
  dimUnconnectedButton.style.position = 'absolute';
  dimUnconnectedButton.style.left = '1320px';
  dimUnconnectedButton.style.top = '10px';
  dimUnconnectedButton.style.zIndex = '1000';
  document.body.appendChild(dimUnconnectedButton);
  dimUnconnectedButton.onclick = function() {dimUnconnectedNodes(true);};

  dimUnconnectedCheckbox.addEventListener('change', function() {
      dimUnconnectedNodes(this.checked);
  });
}
dimUnconnectedNodesUICREATE();



// Log the network data for debugging
//console.log('Network nodes:', network.body.data.nodes.get());

