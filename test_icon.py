import sys
from PySide6.QtWidgets import QApplication
from pyrolist.ui.design.icons import Icon, MATERIAL_FONT
from qt_material import apply_stylesheet

app = QApplication(sys.argv)
lbl = Icon.label("home")
print("Before apply_stylesheet:")
print("lbl.styleSheet():", repr(lbl.styleSheet()))
print("lbl.font().family():", repr(lbl.font().family()))

apply_stylesheet(app, theme="light_purple.xml", extra={"pyside6": True})

print("\nAfter apply_stylesheet:")
print("lbl.styleSheet():", repr(lbl.styleSheet()))
print("lbl.font().family():", repr(lbl.font().family()))
