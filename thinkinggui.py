"""
This module provides a GUI for the Gemini Chat Interface using PyQt6.
"""
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QLabel, QPushButton, QTextEdit, QScrollArea,
                            QFrame, QFileDialog, QProgressBar, QDialog, QLineEdit, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (QFont, QDragEnterEvent, QDropEvent, QIcon, QPalette, QColor)
from thinking import ProblemSolver  # Removed WorkflowStage from import
import sys
import os
from typing import List  # Added import
from datetime import datetime  # Added import
import markdown  # Added import
from loguru import logger  # Replace logging with loguru

class StepProgressBar(QProgressBar):
    """Custom progress bar with step descriptions for workflow visualization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2D2D2D;
                border-radius: 10px;
                background-color: #1E1E1E;
                color: white;
                text-align: center;
            }   
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 9px;
            }
        """)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setFormat("%p% - %v")
        self.setTextVisible(True)
        self.setFixedHeight(20)
        
    def set_animated_value(self, value):
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.setStartValue(self.value())
        self.animation.setEndValue(value)
        self.animation.start()

class ThinkingThread(QThread):
    """Background thread for AI processing."""
    finished = pyqtSignal(dict)  # Changed to emit dict instead of str
    progress_update = pyqtSignal(int, str)
    
    def __init__(self, message_history, api_key, parent=None):  # Removed image_path parameter
        super().__init__(parent)
        self.message_history = message_history
        self.api_key = api_key
        self.problem_solver = ProblemSolver(api_key=self.api_key)  # Pass the API key
    
    def run(self):
        """Run the thread."""
        try:
            results = self.problem_solver.solve_problem(
                message_history=self.message_history
            )
            self.finished.emit(results)
        except ValueError as e:
            logger.error(f"ValueError in ThinkingThread: {e}")
            self.finished.emit({"error": str(e)})
        except Exception as e:
            logger.error(f"Exception in ThinkingThread: {e}")
            self.finished.emit({"error": str(e)})

class EmojiButton(QPushButton):
    """Custom button with emoji and tooltip."""
    def __init__(self, emoji, tooltip, size=40, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setText(emoji)
        self.setToolTip(tooltip)
        self.setFont(QFont("Segoe UI Emoji", 14))
        self.setIconSize(self.size())
        self.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                border-radius: 20px;
                padding: 5px;
                color: white;
                transition: background-color 0.3s ease;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:pressed {
                background-color: #4D4D4D;
                margin: 1px;
                /* Removed unintended 's' character */
            }
        """)

class MessageInput(QTextEdit):
    """Custom input field with drag and drop support."""
    image_pasted = pyqtSignal(str)
    
    def __init__(self, send_callback, parent=None):
        super().__init__(parent)
        self.send_callback = send_callback
        self.setPlaceholderText("Type your message here or paste an image...")
        self.setFixedHeight(45)
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2D2D2D;
                border: 1px solid #3D3D3D;
                border-radius: 20px;
                margin: 0px 10px;
                color: white;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 2px solid #4CAF50;
                background-color: #3D3D3D;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send_callback()
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                self.image_pasted.emit(file_path)
                break

class MessageBubble(QFrame):
    """Chat message bubble with support for text and images."""
    def __init__(self, text, is_user=False, image_path=None, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        avatar = QLabel()
        avatar.setFixedSize(32, 32)
        avatar.setStyleSheet(f"""
            QLabel {{
                background-color: {'#4CAF50' if is_user else '#1E1E1E'};
                border-radius: 16px;
                color: white;
                font-size: 16px;
            }}
        """)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setText("👤" if is_user else "🤖")
        
        timestamp = QLabel(datetime.now().strftime("%I:%M %p"))
        timestamp.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                margin-top: 4px;
            }
        """)
        timestamp.setFixedHeight(15)
        
        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.setSpacing(2)
        
        if is_user:
            layout.addStretch()
            layout.addWidget(message_container)
            layout.addSpacing(8)
            layout.addWidget(avatar)
            layout.setAlignment(message_container, Qt.AlignmentFlag.AlignRight)  # Align to right
        else:
            layout.addWidget(avatar)
            layout.addSpacing(8)
            layout.addWidget(message_container)
            layout.setAlignment(message_container, Qt.AlignmentFlag.AlignLeft)  # Align to left
        
        # Add image if provided
        if image_path and not is_user:
            image_label = QLabel()
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
            image_label.setPixmap(scaled_pixmap)
            message_layout.addWidget(image_label)
        
        message_layout.addWidget(self.create_bubble(text, is_user))
        message_layout.addWidget(timestamp)
        
        layout.setContentsMargins(20, 5, 20, 5)

    def create_bubble(self, text, is_user):
        bubble = QFrame()
        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {'#4CAF50' if is_user else '#121212'};
                border-radius: 18px;
                padding: 2px;
                border: 1px solid {'#45a049' if is_user else '#2D2D2D'};
            }}
        """)
        
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(15, 10, 15, 10)
        
        message = QTextEdit()
        message.setReadOnly(True)
        
        # Convert URLs to clickable links in markdown
        if "Sources:" in text:
            text = text.replace("- http", "- [Link](http")
            
        html_content = markdown.markdown(text)
        message.setHtml(html_content)
        
        # Enable link interaction
        message.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        
        document = message.document()
        document.setTextWidth(message.viewport().width())
        
        message.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: transparent;
                color: #FFFFFF;
                font-size: 14px;
            }
            QTextEdit a {
                color: #4CAF50;
                text-decoration: none;
            }
            QTextEdit a:hover {
                text-decoration: underline;
            }
        """)
        message.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        message.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        document.adjustSize()
        content_width = min(int(document.idealWidth() + 30), 600)
        content_height = int(document.size().height() + 5)
        
        message.setFixedSize(content_width, content_height)
        bubble_layout.addWidget(message)
        
        bubble.setFixedWidth(content_width + 30)
        bubble.setMinimumHeight(content_height + 20)
        
        return bubble

class ChatView(QScrollArea):
    """Scrollable container for chat messages."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #121212;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #121212;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #2D2D2D;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3D3D3D;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background-color: #121212;")
        self.layout = QVBoxLayout(container)
        self.layout.addStretch()
        self.setWidget(container)

class SettingsDialog(QDialog):
    """Dialog to update application settings."""
    def __init__(self, current_api_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.layout = QFormLayout(self)

        self.api_key_input = QLineEdit(self)
        self.api_key_input.setText(current_api_key)
        self.layout.addRow("API Key:", self.api_key_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_api_key(self):
        return self.api_key_input.text()

class ModernChatWindow(QMainWindow):
    """Main chat window with enhanced image support and workflow visualization."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini Chat Interface")
        self.setWindowIcon(QIcon("assets/icons/chat_icon.png"))  # Updated icon
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QToolTip {
                background-color: #1E1E1E;
                color: white;
                border: 1px solid #2D2D2D;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
        self.api_key = "AIzaSyACCbhYudSe-lQzqHZp_yi3KSMbka5kTG8"  # Replace with your actual API key
        self.problem_solver = ProblemSolver(api_key=self.api_key)  # Pass API key
        self.setup_ui()
        # Removed self.memory as it's no longer needed
        
        self.theme = "Dark"

        # Add Settings button to header
        self.settings_button = EmojiButton("⚙️", "Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.header_layout.addWidget(self.settings_button)  # Use addWidget instead of addAction

        # Add Theme toggle button
        self.theme_button = EmojiButton("🌙", "Toggle Theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.header_layout.addWidget(self.theme_button)  # Ensure using addWidget

        self.thinking_thread = None
        self.message_history = []  # Initialize chat history

    def setup_ui(self):
        """Set up the user interface."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with smooth background
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1E1E1E, stop:1 #2D2D2D);
            }
        """)
        self.header_layout = QHBoxLayout(header)  # Ensure using self.header_layout
        self.header_layout.setContentsMargins(15, 0, 15, 0)  # Updated margins for better spacing
        
        title_label = QLabel("Gemini Chat")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.header_layout.addWidget(title_label)
        
        self.status_label = QLabel("🟢 Idle")
        self.status_label.setStyleSheet("color: #88CC88; font-size: 12px;")
        self.header_layout.addWidget(self.status_label)
        
        # Progress bar with animation
        self.progress_bar = StepProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.hide()
        self.header_layout.addWidget(self.progress_bar)
        
        # Add clear chat button with icon
        self.clear_button = EmojiButton("🗑���", "Clear Chat")
        self.clear_button.clicked.connect(self.clear_chat)
        self.header_layout.addStretch()
        
        # Chat view with smooth scrolling
        self.chat_view = ChatView()
        self.chat_view.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #121212;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #121212;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #2D2D2D;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #3D3D3D;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Input container with modern design
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                border-top: 1px solid #2D2D2D;
            }
        """)
        input_container.setFixedHeight(80)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 15)
        input_layout.setSpacing(10)
        
        self.input_field = MessageInput(self.send_message)
        
        self.send_button = EmojiButton("➤", "Send Message", size=50)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border-radius: 25px;
                padding: 5px;
                color: white;
                transition: background-color 0.3s ease;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                color: #666666;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        layout.addWidget(header)
        layout.addWidget(self.chat_view)
        layout.addWidget(input_container)
        
        # Add fade-in animation for the main window
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()
        
        self.add_message("👋 Hello! I'm your AI assistant. I can help answer questions and analyze images. Try dropping an image or using the upload button!", is_user=False)
    
    def add_message(self, text, is_user=False):
        """Add a message bubble to the chat view."""
        message_bubble = MessageBubble(text, is_user=is_user)
        self.chat_view.layout.addWidget(message_bubble)
        self.scroll_to_bottom()

    def clear_chat(self):
        """Clear all messages from the chat view."""
        container = self.chat_view.widget()
        for i in reversed(range(container.layout.count())):
            widget_item = container.layout.itemAt(i)
            if widget_item.widget():
                widget_item.widget().setParent(None)

    def scroll_to_bottom(self):
        """Scroll the chat view to the bottom."""
        QTimer.singleShot(100, lambda: self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum()))

    def update_progress(self, percentage, step_description):
        """Update the progress bar with the current progress."""
        self.progress_bar.set_animated_value(percentage)
        self.progress_bar.setFormat(f"{percentage}% - {step_description}")
        if percentage < 100:
            self.progress_bar.show()
        else:
            self.progress_bar.hide()

    def send_message(self):
        """Send the user's message and start the AI processing."""
        user_text = self.input_field.toPlainText().strip()
        if user_text:
            self.add_message(user_text, is_user=True)
            self.message_history.append({"role": "user", "content": user_text})  # Append to history
            self.input_field.clear()

            # Start the thinking thread with history and image_path
            self.thinking_thread = ThinkingThread(
                message_history=self.message_history,
                api_key=self.api_key
            )
            self.thinking_thread.finished.connect(self.handle_workflow_results)
            self.thinking_thread.progress_update.connect(self.update_progress)
            self.thinking_thread.start()
            self.status_label.setText("🟡 Working...")
            self.progress_bar.set_animated_value(0)
            self.progress_bar.show()

    def handle_workflow_results(self, results: dict):
        """Handle the results returned from the AI processing."""
        if 'error' in results:
            self.add_message(f"Error: {results['error']}", is_user=False)
            self.status_label.setText("🔴 Error")
        else:
            solution = results.get("solution", "No solution available.")
            self.add_message(solution, is_user=False)
            self.message_history.append({"role": "ai", "content": solution})  # Append AI response to history
            self.status_label.setText("🟢 Idle")
            self.progress_bar.set_animated_value(100)
            self.progress_bar.hide()
            
            # Display grounding sources if available
            grounding = results.get("grounding")
            if grounding and 'groundingChunks' in grounding:
                sources = [chunk['web']['uri'] for chunk in grounding['groundingChunks'] if 'web' in chunk]
                if sources:
                    sources_text = "\n\nSources:\n" + "\n".join([f"- {source}" for source in sources])
                    self.add_message(sources_text, is_user=False)

    def handle_image_pasted(self, file_path: str):
        """Handle an image pasted into the input field."""
        pass

    def open_settings(self):
        """Open the settings dialog to update the API key."""
        dialog = SettingsDialog(current_api_key=self.api_key, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.api_key = dialog.get_api_key()
            # Update the ProblemSolver instance
            self.problem_solver = ProblemSolver(api_key=self.api_key)
            logger.info("API key updated via settings.")

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        if self.theme == "Dark":
            self.set_light_theme()
            self.theme = "Light"
            self.theme_button.setText("🌞")
        else:
            self.set_dark_theme()
            self.theme = "Dark"
            self.theme_button.setText("🌙")

    def set_light_theme(self):
        """Set the GUI to light theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
            }
            /* Add additional light theme styles here */
        """)

    def set_dark_theme(self):
        """Set the GUI to dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            /* Add additional dark theme styles here */
        """)

    def keyPressEvent(self, event):
        """Handle global key events."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    
    window = ModernChatWindow()
    window.resize(1000, 800)
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())