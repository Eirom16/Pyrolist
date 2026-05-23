import sys
from PySide6.QtWidgets import QApplication, QLabel
from pyrolist.ui.design.icons import Icon
from qt_material import apply_stylesheet

app = QApplication(sys.argv)
# Explicitly set app font to something else
from pyrolist.ui.design.fonts import load_fonts, AppFont
load_fonts()
app.setFont(AppFont.body())

lbl = Icon.label('home')

apply_stylesheet(app, theme='light_purple.xml', extra={'pyside6': True})

base_qss = app.styleSheet()
print('Before stripping Roboto:')
print('lbl font family:', lbl.font().family())

base_qss = base_qss.replace('font-family: Roboto;', '')
app.setStyleSheet(base_qss)

print('After stripping Roboto:')
print('lbl font family:', lbl.font().family())
