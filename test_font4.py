import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet
app = QApplication(sys.argv)
apply_stylesheet(app, theme='dark_purple.xml', extra={'pyside6': True})
qss = app.styleSheet()
import re
sizes = re.findall(r'[^}]*\{\s*[^}]*font-size:[^;]*;[^}]*\}', qss)
print('Selectors with font-size in qt_material:')
for s in set(sizes):
    name = s.split('{')[0].strip()
    if name != '*':
        print(name)
