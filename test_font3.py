import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet
app = QApplication(sys.argv)
apply_stylesheet(app, theme='dark_purple.xml', extra={'pyside6': True})
qss = app.styleSheet()
import re
stars = re.findall(r'\* \{[^}]*\}', qss)
print('Global * rules in qt_material:')
for s in set(stars):
    print(s)
