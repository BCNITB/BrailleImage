import sys
import pytest
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt, QTimer
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, 'C:\\App\\braille\\0_new')

from ui.main_window import MainWindow
from ui.math_dialogs import PointsDialog
from ui.points_graph_widget import PointsGraphWidget

@pytest.fixture
def app(qtbot):
    test_app = QApplication.instance()
    if test_app is None:
        test_app = QApplication([])
    
    main_window = MainWindow()
    main_window.show()
    qtbot.addWidget(main_window)
    yield main_window
    main_window.close()

def test_open_points_graph_dialog(app, qtbot):
    # Mock the PointsDialog to control its execution
    with patch('ui.main_window.PointsDialog') as mock_points_dialog:
        # Configure the mock dialog instance
        mock_dialog_instance = MagicMock()
        mock_points_dialog.return_value = mock_dialog_instance
        mock_dialog_instance.exec.return_value = QDialog.Accepted
        mock_dialog_instance.get_points.return_value = [(1, 2), (3, 4), (5, 6)]

        # Mock the QProgressDialog to prevent it from showing
        with patch('ui.main_window.QProgressDialog'):
            # Mock the PointsGraphDisplayDialog to prevent it from actually showing
                # Find the "Graficar Puntos" action and trigger it
                graph_points_action = None
                for action in app.math_menu.actions():
                    if action.text() == "Graficar &Puntos":
                        graph_points_action = action
                        break
                
                assert graph_points_action is not None, "Action 'Graficar &Puntos' not found in math menu"
                
                # Trigger the action
                graph_points_action.trigger()

                # Wait until the graph widget has been created and added to the tab
                qtbot.waitUntil(lambda: app.graph_tabs.count() > 0, timeout=1000)

                # Verify that PointsDialog was created and executed
                mock_points_dialog.assert_called_once_with(app)
                mock_dialog_instance.exec.assert_called_once()
                mock_dialog_instance.get_points.assert_called_once()

                # Verify that a new tab was added and it contains a PointsGraphWidget
                assert app.graph_tabs.count() == 1
                new_widget = app.graph_tabs.widget(0)
                assert isinstance(new_widget, PointsGraphWidget)
                # Verify that the widget has the correct points
                assert new_widget.points == [(1, 2), (3, 4), (5, 6)]

def test_adjust_function_in_points_graph_dialog(app, qtbot):
    points = [(1, 1), (2, 2), (3, 3)]
    graph_dialog = PointsGraphWidget(points, app)
    qtbot.addWidget(graph_dialog)

    # Mock the plot and generate_braille_graph methods
    with patch.object(graph_dialog, 'plot_points_graph') as mock_plot, \
         patch.object(graph_dialog, 'generate_braille_graph') as mock_generate_braille_graph:
        
        # The generate_braille_graph is called once in __init__, so reset the mock
        mock_generate_braille_graph.reset_mock()

        # Simulate user input for polynomial degree
        with patch('PySide6.QtWidgets.QInputDialog.getInt', return_value=(1, True)): # Linear fit
            graph_dialog.adjust_function()

        # Verify that the fitted function is set and coefficients are rounded
        assert graph_dialog.fitted_function is not None
        # For points (1,1), (2,2), (3,3), a linear fit should be y = 1.00x + 0.00
        assert "y = 1.00x" in graph_dialog.fitted_function_str or "y = 1.00x + 0.00" in graph_dialog.fitted_function_str

        # Verify that the plot and braille graph were updated
        mock_plot.assert_called_once_with(graph_dialog.fitted_function)
        mock_generate_braille_graph.assert_called_once()
