try:
    import sys, warnings
    from qtpy.QtWidgets import QApplication

    # Start QApplication if not running yet.
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

except ImportError:
    warnings.warn(
        "QtPy package not found." "GUI will not be available.", ImportWarning
    )
