PROJECT CODE:
a12bc3

PROJECT SUMMARY:
The user wants to build a graphing calculator application. The current canvas shows a wireframe of the application, featuring an input area for equations and a graphing display with Cartesian axes. A sample equation "y=x" is shown, and its corresponding graph is plotted.

USER GOAL:
To develop a functional web application that allows users to input mathematical equations and visualize their graphs on a Cartesian plane.

TODO LIST:

[HIGH PRIORITY]
- Implement a frontend framework (e.g., React, Vue, Angular) for the graphing calculator application.
- Develop a backend API (e.g., using Python/Flask, Node.js/Express) to handle equation parsing and calculation.
- Integrate a charting library (e.g., Chart.js, Plotly.js, D3.js) for rendering mathematical graphs.
- Create a UI component for inputting mathematical equations, including syntax validation.
- Implement the Cartesian coordinate system rendering on the canvas.
- Develop logic to parse user-inputted equations (e.g., "y=x", "y=2x+1", "y=x^2").
- Implement a function to calculate y-values for a given range of x-values based on the parsed equation.
- Display the calculated graph on the canvas, ensuring it accurately represents the equation.
- Add a visual indicator (red dot) for the currently active or selected equation.
- Implement functionality to add new equations and manage a list of equations.

[MEDIUM PRIORITY]
- Add support for various mathematical functions (e.g., trigonometric, logarithmic, exponential).
- Implement zoom and pan functionality for the graph.
- Allow users to customize graph appearance (e.g., line color, thickness).
- Add a feature to clear the graph and all entered equations.
- Implement error handling for invalid equation inputs.
- Design and implement responsive UI for different screen sizes.

[LOW PRIORITY]
- Add a feature to save and load graph sessions.
- Implement a history of previously entered equations.
- Integrate unit testing for equation parsing and graphing logic.
- Explore options for real-time equation evaluation and graph updates.
- Add documentation for the application's features and usage.

TECHNICAL NOTES:
- The current canvas shows a basic wireframe. The "equation" text and "y=x" input field