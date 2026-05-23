import sys
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QFont

app = QApplication(sys.argv)
app.setFont(QFont('Arial', 14))

lbl = QLabel('Test')
f = QFont('Times', 40)
lbl.setFont(f)
lbl.setStyleSheet('font-family: "Courier";')

print('Font family:', lbl.font().family())
print('Font size (points):', lbl.font().pointSize())
print('Font size (pixels):', lbl.font().pixelSize())
