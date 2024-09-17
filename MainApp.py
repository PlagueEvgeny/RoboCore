import os
import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import subprocess

textManagerServo = "Управляет сервоприводами и сенсорами для роботов и устройств, обеспечивает управление углами и скоростью."
textRoboSpider = "Управляет роботом-пауком, обеспечивая его передвижение, манипуляции и взаимодействие с окружающей средой."
textHaus = "Автоматизация и управление системами умного дома, включая освещение, безопасность и климат-контроль."


# Главное окно выбора программы
class MainApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("РобоЯдро")
        self.setWindowIcon(QtGui.QIcon("media/images/logo.svg"))
        self.resize(800, 400)
        layout = QtWidgets.QHBoxLayout()

        # Создаем три карточки
        card1 = self.create_card("Менеджер Сервоприводов", textManagerServo, "media/images/servo.png",
                                 self.launch_controller_manager)
        card2 = self.create_card("РобоПаук", textRoboSpider, "media/images/pauk.png", self.launch_program_two)
        card3 = self.create_card("Умный Дом", textHaus, "media/images/smarthouse.png", self.launch_program_three)

        # Выравниваем карточки по центру
        layout.addWidget(card1)
        layout.addWidget(card2)
        layout.addWidget(card3)

        # Настраиваем основной layout
        self.setLayout(layout)

    def create_card(self, title, description, image_path, on_click):
        # Карточка — это QVBoxLayout, содержащий картинку, текст и кнопку
        card_layout = QtWidgets.QVBoxLayout()

        # Изображение
        image_label = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(image_path)
        image_label.setPixmap(pixmap.scaled(200, 150, QtCore.Qt.KeepAspectRatio))
        image_label.setAlignment(QtCore.Qt.AlignCenter)

        # Заголовок
        title_label = QtWidgets.QLabel(title)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))

        # Описание
        desc_label = QtWidgets.QLabel(description)
        desc_label.setAlignment(QtCore.Qt.AlignCenter)
        desc_label.setWordWrap(True)

        # Кнопка
        button = QtWidgets.QPushButton("Запустить")
        button.clicked.connect(on_click)

        # Добавляем все элементы в layout карточки
        card_layout.addWidget(image_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(desc_label)
        card_layout.addWidget(button)

        # Создаем контейнер для карточки
        card_widget = QtWidgets.QWidget()
        card_widget.setLayout(card_layout)
        return card_widget

    @staticmethod
    def launch_controller_manager():
        from ControllerManager import ServoControllerApp
        window = ServoControllerApp()
        window.show()

    @staticmethod
    def launch_program_two(self):
        subprocess.Popen(['python', 'program_two.py'])

    @staticmethod
    def launch_program_three(self):
        subprocess.Popen(['python', 'program_three.py'])


# Основной блок программы
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec_())
