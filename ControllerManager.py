import os
import json
import time
import subprocess
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QTimer

import serial.tools.list_ports


arduino_code = """\
#include <Servo.h>

Servo column;
Servo left_shoulder;
Servo right_shoulder;
Servo grip;

void setup() {
  Serial.begin(9600);
  column.attach(4);
  left_shoulder.attach(5);
  right_shoulder.attach(6);
  grip.attach(7);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\\n');
    int commaIndex = input.indexOf(',');
    if (commaIndex > 0) {
      int servoNum = input.substring(0, commaIndex).toInt();
      int angle = input.substring(commaIndex + 1).toInt();

      switch (servoNum) {
        case 1:
          column.write(angle);
          break;
        case 2:
          left_shoulder.write(angle);
          break;
        case 3:
          right_shoulder.write(angle);
          break;
        case 4:
          grip.write(angle);
          break;
      }
    }
  }
}
"""

class ServoControllerApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.command_listbox = None
        self.delay_entry = None
        self.speed_label = None
        self.angel_label = None
        self.angle_sliders = None
        self.speed_sliders = None
        self.connection_label = None
        self.port_combobox = None
        self.message_label = None
        self.available_ports = None
        self.ser = None
        self.target_angles = [90, 90, 90, 90]
        self.target_speeds = [50, 50, 50, 50]
        self.command_list = []
        self.command_queue = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.process_command_queue)
        self.timer.start(1)  # Периодический таймер с интервалом в 100 м

        self.company_info = ""
        self.program_info = "Программа: Менеджер Сервоприводов \nВерсия: 1.0\n© Разработчик: Василенко Евгений, 2024\n Лицензия:"

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Менеджер Сервоприводов")
        self.setWindowIcon(QtGui.QIcon("media/images/logo.svg"))
        self.setGeometry(100, 100, 910, 700)

        main_layout = QtWidgets.QVBoxLayout()

        # Создание меню
        self.create_menu(main_layout)

        # Основное содержимое
        layout = QtWidgets.QGridLayout()

        # Сканирование доступных COM-портов
        self.available_ports = self.get_ports()

        # Выбор порта
        port_label = QtWidgets.QLabel("Выберите COM порт:")
        layout.addWidget(port_label, 0, 0)

        self.port_combobox = QtWidgets.QComboBox()
        self.port_combobox.addItems(self.available_ports)
        layout.addWidget(self.port_combobox, 0, 1)

        if self.available_ports:
            self.port_combobox.setCurrentIndex(0)
        else:
            self.port_combobox.addItem("Нет доступных портов")
            self.port_combobox.setCurrentIndex(0)

        connect_button = QtWidgets.QPushButton("Подключиться")
        connect_button.clicked.connect(self.connect_port)
        layout.addWidget(connect_button, 0, 2)

        refresh_ports_button = QtWidgets.QPushButton("Обновить порты")
        refresh_ports_button.clicked.connect(self.refresh_ports)
        layout.addWidget(refresh_ports_button, 1, 0)

        # Метка для отображения состояния соединения
        self.connection_label = QtWidgets.QLabel("Нет соединения")
        layout.addWidget(self.connection_label, 1, 1)

        self.angel_label = QtWidgets.QLabel("Угол поворота")
        layout.addWidget(self.angel_label, 2, 1)

        self.speed_label = QtWidgets.QLabel("Скорость")
        layout.addWidget(self.speed_label, 2, 2)

        # Настройки для сервоприводов
        servo_names = ["Колонна", "Левое плечо", "Правое плечо", "Захват"]
        self.angle_sliders = []
        self.speed_sliders = []

        for i in range(4):
            servo_label = QtWidgets.QLabel(f"{servo_names[i]}")
            layout.addWidget(servo_label, i + 3, 0)

            # Создание контейнера для ползунка угла и меток
            angle_slider_layout = QtWidgets.QVBoxLayout()

            # Верхние метки значений для углов
            top_labels_layout = QtWidgets.QHBoxLayout()
            top_labels_layout.addWidget(QtWidgets.QLabel("0°"))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel("60°"))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel("120°"))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel(""))
            top_labels_layout.addWidget(QtWidgets.QLabel("180°"))
            angle_slider_layout.addLayout(top_labels_layout)

            # Создание ползунка угла
            angle_slider = QtWidgets.QSlider(Qt.Horizontal)
            angle_slider.setRange(0, 180)
            angle_slider.setValue(self.target_angles[i])
            angle_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)  # Метки под ползунком
            angle_slider.setTickInterval(60)  # Интервал между метками
            angle_slider.valueChanged.connect(
                lambda val, j=i: self.update_servo(j, val, self.speed_sliders[j].value())
            )
            angle_slider_layout.addWidget(angle_slider)

            layout.addLayout(angle_slider_layout, i + 3, 1)

            # Создание контейнера для ползунка скорости и меток
            speed_slider_layout = QtWidgets.QVBoxLayout()

            # Верхние метки значений для скорости
            speed_top_labels_layout = QtWidgets.QHBoxLayout()
            speed_top_labels_layout.addWidget(QtWidgets.QLabel("1°/с"))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel(""))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel("25°/с"))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel(""))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel("50°/с"))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel(""))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel("75°/с"))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel(""))
            speed_top_labels_layout.addWidget(QtWidgets.QLabel("100°/с"))
            speed_slider_layout.addLayout(speed_top_labels_layout)

            # Создание ползунка скорости
            speed_slider = QtWidgets.QSlider(Qt.Horizontal)
            speed_slider.setRange(1, 100)
            speed_slider.setValue(self.target_speeds[i])
            speed_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)  # Метки под ползунком
            speed_slider.setTickInterval(25)  # Интервал между метками
            speed_slider.valueChanged.connect(
                lambda val, j=i: self.update_servo(j, self.angle_sliders[j].value(), val)
            )
            speed_slider_layout.addWidget(speed_slider)

            layout.addLayout(speed_slider_layout, i + 3, 2)

            self.angle_sliders.append(angle_slider)
            self.speed_sliders.append(speed_slider)

        # Поле для ввода задержки
        delay_label = QtWidgets.QLabel("Задержка (мс):")
        layout.addWidget(delay_label, 8, 0)

        self.delay_entry = QtWidgets.QLineEdit()
        self.delay_entry.setText("500")
        layout.addWidget(self.delay_entry, 8, 1)

        # Кнопки для управления командами
        add_button = QtWidgets.QPushButton("Добавить команду")
        add_button.clicked.connect(self.add_command)
        layout.addWidget(add_button, 9, 0)

        delete_button = QtWidgets.QPushButton("Удалить команду")
        delete_button.clicked.connect(self.delete_command)
        layout.addWidget(delete_button, 9, 1)

        self.command_listbox = QtWidgets.QListWidget()
        layout.addWidget(self.command_listbox, 10, 0, 1, 2)

        step_play_button = QtWidgets.QPushButton("Пошаговое воспроизведение")
        step_play_button.clicked.connect(self.step_play)
        layout.addWidget(step_play_button, 9, 2)

        auto_play_button = QtWidgets.QPushButton("Автоматическое воспроизведение")
        auto_play_button.clicked.connect(self.auto_play)
        layout.addWidget(auto_play_button, 9, 3)

        # Кнопки для сохранения и загрузки команд
        save_button = QtWidgets.QPushButton("Сохранить команды в файл")
        save_button.clicked.connect(self.save_all_commands)
        layout.addWidget(save_button, 3, 3)

        load_button = QtWidgets.QPushButton("Загрузить команды из файла")
        load_button.clicked.connect(self.load_all_commands)
        layout.addWidget(load_button, 4, 3)

        # Метка для вывода сообщений пользователю
        self.message_label = QtWidgets.QLabel("")
        layout.addWidget(self.message_label, 10, 2, 1, 3)

        upload_button = QtWidgets.QPushButton("Загрузить прошивку")
        upload_button.clicked.connect(self.upload_firmware)
        layout.addWidget(upload_button, 0, 3)

        main_layout.addLayout(layout)
        self.setLayout(main_layout)

    def create_menu(self, main_layout):
        # Создание менюбар
        menubar = QtWidgets.QMenuBar(self)

        # Меню Справка
        help_menu = menubar.addMenu("Справка")

        # Пункт "О компании"
        about_company_action = QtWidgets.QAction("О компании", self)
        about_company_action.triggered.connect(self.show_company_info)
        help_menu.addAction(about_company_action)

        # Пункт "О программе"
        about_program_action = QtWidgets.QAction("О программе", self)
        about_program_action.triggered.connect(self.show_program_info)
        help_menu.addAction(about_program_action)

        # Добавление менюбар в основной макет
        main_layout.setMenuBar(menubar)

    def show_company_info(self):
        QtWidgets.QMessageBox.information(self, "О компании", self.company_info)

    def show_program_info(self):
        QtWidgets.QMessageBox.information(self, "О программе", self.program_info)

    @staticmethod
    def get_ports():
        return [port.device for port in serial.tools.list_ports.comports()]

    def refresh_ports(self):
        self.available_ports = self.get_ports()
        self.port_combobox.clear()
        self.port_combobox.addItems(self.available_ports)
        if self.available_ports:
            self.port_combobox.setCurrentIndex(0)
        else:
            self.port_combobox.addItem("Нет доступных портов")
            self.port_combobox.setCurrentIndex(0)
        self.connection_label.setText("Список портов обновлен")

    def send_servo_angle(self, servo_num, angle, speed):
        if self.ser and self.ser.is_open:
            command = f"{servo_num},{angle},{speed}\n"
            self.command_queue.append(command)
        else:
            QtWidgets.QMessageBox.critical(self, "Предупреждение",
                                           "При частой передаче сигнала пин на серво закрывается.")

    def process_command_queue(self):
        if self.ser and self.ser.is_open and len(self.command_queue) > 0:
            command = self.command_queue.pop(0)
            try:
                self.ser.write(command.encode("utf-8"))
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при отправке данных: {str(e)}")

    def update_servo(self, index, angle_value, speed_value):
        self.target_angles[index] = int(angle_value)
        self.target_speeds[index] = int(speed_value)
        self.send_servo_angle(index + 1, self.target_angles[index], self.target_speeds[index])

    def connect_port(self):
        port = self.port_combobox.currentText()
        if port and port != "Нет доступных портов":
            self.ser = serial.Serial(port, 9600, timeout=1)
            self.connection_label.setText(f"Подключено к {port}")
        else:
            self.connection_label.setText("Порт не выбран или недоступен")

    def add_command(self):
        command = {
            "angles": self.target_angles.copy(),
            "speeds": self.target_speeds.copy()
        }
        self.command_list.append(command)
        self.update_command_listbox()

    def update_command_listbox(self):
        self.command_listbox.clear()
        for index, cmd in enumerate(self.command_list):
            self.command_listbox.addItem(f"Команда {index + 1}: {cmd}")

    def play_command(self, index):
        if index < len(self.command_list):
            angles = self.command_list[index]["angles"]
            speeds = self.command_list[index]["speeds"]
            for i in range(4):
                self.send_servo_angle(i + 1, angles[i], speeds[i])

    def step_play(self):
        selected_indices = self.command_listbox.selectedIndexes()
        if selected_indices:
            current_index = selected_indices[0].row()
            self.play_command(current_index)
            self.message_label.setText(f"Воспроизведена команда {current_index + 1}")
        else:
            self.message_label.setText("Команда не выбрана.")

    def auto_play(self):
        delay = int(self.delay_entry.text())
        for i in range(len(self.command_list)):
            self.play_command(i)
            time.sleep(delay / 1000)

    def delete_command(self):
        selected_index = self.command_listbox.currentRow()
        if selected_index >= 0:
            self.command_list.pop(selected_index)
            self.update_command_listbox()

    def save_all_commands(self):
        with open("media/commands/commands.json", "w") as f:
            json.dump(self.command_list, f)
        self.message_label.setText("Команды сохранены в commands.json")

    def load_all_commands(self):
        try:
            with open("media/commands/commands.json", "r") as f:
                self.command_list = json.load(f)
            self.update_command_listbox()
            self.message_label.setText("Команды загружены из commands.json")
        except FileNotFoundError:
            self.command_list = []
            self.message_label.setText("Файл команд не найден.")


    @staticmethod
    def rename_file_to_directory_name(file_path):
        """
        Переименовывает файл так, чтобы его имя совпадало с именем текущей директории.

        :param file_path: Полный путь к файлу, который нужно переименовать.
        :return: Новый путь к переименованному файлу, если переименование успешно, иначе None.
        """
        directory = os.path.dirname(file_path)  # Директория, в которой находится файл
        new_name = os.path.basename(directory) + os.path.splitext(file_path)[1]  # Новое имя файла с сохранением расширения
        new_file_path = os.path.join(directory, new_name)
        os.rename(file_path, new_file_path)
        return new_file_path

    @staticmethod
    def create_ino_file(file_name, content):
        """
        Создает .ino файл с указанным содержимым.

        :param file_name: Имя файла (должно оканчиваться на .ino).
        :param content: Содержимое файла.
        :return: Полный путь к созданному файлу.
        """
        if not file_name.endswith('.ino'):
            raise ValueError("Имя файла должно заканчиваться на '.ino'")

        with open(file_name, 'w') as file:
            file.write(content)

        return os.path.abspath(file_name)

    def is_arduino_port(self, port):
        result = subprocess.run(["arduino-cli", "board", "list"], capture_output=True, text=True)
        return port in result.stdout

    def upload_firmware(self):
        current_directory_name = f"{os.path.basename(os.getcwd())}.ino"
        temp_name = self.create_ino_file(current_directory_name, arduino_code)

        if not os.path.exists(temp_name):
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Файл прошивки не найден:\n{temp_name}")
            return

        port = self.port_combobox.currentText()
        if not port or port == "Нет доступных портов":
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Выберите COM порт.")
            return

        # Проверяем, является ли выбранный порт портом Arduino
        if not self.is_arduino_port(port):
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Выбранный порт не поддерживает Arduino плату.")
            return

        try:
            subprocess.run(["arduino-cli", "core", "install", "arduino:avr"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["arduino-cli", "lib", "install", "Servo"], check=True, creationflags=subprocess.CREATE_NO_WINDOW)

            compile_command = [
                "arduino-cli",
                "compile",
                "--fqbn", "arduino:avr:nano:cpu=atmega168",
                temp_name
            ]
            subprocess.run(compile_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)

            upload_command = [
                "arduino-cli",
                "upload",
                "-p", port,
                "--fqbn", "arduino:avr:nano:cpu=atmega168",
                temp_name
            ]
            process = subprocess.run(upload_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW,  timeout=30)

            if process.returncode == 0:
                QtWidgets.QMessageBox.information(self, "Успех", "Прошивка успешно загружена!")
            else:
                QtWidgets.QMessageBox.critical(self, "Ошибка",
                                               f"Не удалось загрузить прошивку:\n{process.stderr.decode()}")
        except subprocess.TimeoutExpired:
        # Если загрузка длится слишком долго — выводим сообщение и прерываем процесс
            QtWidgets.QMessageBox.critical(self, "Предупреждение", "Выбран не тот порт или не правильная плата.")
        except subprocess.CalledProcessError as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить прошивку:\n{e.stderr.decode()}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Неожиданная ошибка", str(e))


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = ServoControllerApp()
    window.show()
    app.exec_()
