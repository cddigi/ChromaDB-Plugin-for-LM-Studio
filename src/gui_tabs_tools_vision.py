from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QThread, QUrl
import yaml
import multiprocessing
import vision_llava_module
import vision_cogvlm_module
from pathlib import Path
import platform

class VisionToolSettingsTab(QWidget):
    def __init__(self):
        super().__init__()

        # Main layout
        mainVLayout = QVBoxLayout()
        self.setLayout(mainVLayout)

        # Operations layout
        hBoxLayout = QHBoxLayout()
        mainVLayout.addLayout(hBoxLayout)

        # Select Image Folder Button
        selectFolderButton = QPushButton("Select Image")
        hBoxLayout.addWidget(selectFolderButton)
        selectFolderButton.clicked.connect(self.openFolderDialog)

        # Process Button
        processButton = QPushButton("Process")
        hBoxLayout.addWidget(processButton)
        processButton.clicked.connect(self.confirmationBeforeProcessing)

        # Folder Path Label
        self.folderPathLabel = QLabel("No File selected")
        mainVLayout.addWidget(self.folderPathLabel)

        # Initialize the WebEngineView
        self.webView = QWebEngineView()
        script_dir = Path(__file__).resolve().parent
        html_file_path = script_dir / 'vision_model_table.html'
        self.webView.setUrl(QUrl.fromLocalFile(str(html_file_path)))
        mainVLayout.addWidget(self.webView)

    def confirmationBeforeProcessing(self):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText("This will process a single image file that you've selected based on the vision model settings you've chosen in the Settings Tab. The purpose is to test the VRAM usage, speed, and quality of the output before adding images to the vector database. Do you want to proceed?")
        msgBox.setWindowTitle("Confirm Processing")
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Ok:
            self.startProcessing()
    
    def startProcessing(self):
        script_dir = Path(__file__).resolve().parent
        images_dir = script_dir / "Images_for_DB"

        with open('config.yaml', 'r') as file:
            updated_config = yaml.safe_load(file)

        if platform.system() == "Darwin" and any(images_dir.iterdir()):
            QMessageBox.warning(self, "Error",
                                "Image processing has been disabled for MacOS for the time being until a fix can be implemented. Please remove all files from the 'Images_for_DB' folder and try again.")
            return

        chosen_model = updated_config['vision']['chosen_model']

        if chosen_model in ['llava', 'bakllava']:
            processing_function = vision_llava_module.llava_process_images
        elif chosen_model == 'cogvlm':
            processing_function = vision_cogvlm_module.cogvlm_process_images
        elif chosen_model == 'salesforce':
            QMessageBox.warning(self, "Testing Salesforce",
                                "Testing Salesforce is not allowed here. It is too lightweight and should run on any semi-modern CPU and/or GPU. If your system can't handle processing multiple images with Salesforce, it's time to upgrade your computer.")
            return
        else:
            print("Error: Invalid model selected.")
            return

        self.processingThread = ProcessingThread(processing_function)
        self.processingThread.start()

    def openFolderDialog(self):
        file_types = "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image File", "", file_types)
        if file_path:
            self.folderPathLabel.setText(file_path)

            config_file_path = Path('config.yaml')
            if config_file_path.exists():
                try:
                    with open(config_file_path, 'r') as file:
                        config = yaml.safe_load(file)
                except Exception as e:
                    config = {}

            vision_config = config.get('vision', {})
            vision_config['test_image'] = file_path
            config['vision'] = vision_config

            with open(config_file_path, 'w') as file:
                yaml.dump(config, file)

class ProcessingThread(QThread):
    def __init__(self, processing_function):
        super().__init__()
        self.processing_function = processing_function

    def run(self):
        process = multiprocessing.Process(target=self.processing_function)
        process.start()
        process.join()