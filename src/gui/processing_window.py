from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QProgressBar, QPushButton, QTextEdit, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


class ProcessingWindow(QDialog):
    """
    A window that shows the progress of extraction processing.
    Displays current file being processed, overall progress, and a log of completed files.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing...")
        self.setWindowModality(Qt.ApplicationModal)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Track processing state
        self.current_file_index = 0
        self.total_files = 0
        self.current_filename = ""
        self.is_cancelled = False
        
        # Track statistics
        self.frames_generated = 0
        self.animations_generated = 0
        self.sprites_failed = 0
        self.start_time = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Extracting TextureAtlas Files")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Current file section
        current_file_frame = QFrame()
        current_file_frame.setFrameStyle(QFrame.StyledPanel)
        current_file_layout = QVBoxLayout(current_file_frame)
        
        self.current_file_label = QLabel("Current File:")
        current_file_layout.addWidget(self.current_file_label)
        
        self.current_filename_label = QLabel("Initializing...")
        self.current_filename_label.setWordWrap(True)
        current_filename_font = QFont()
        current_filename_font.setBold(True)
        self.current_filename_label.setFont(current_filename_font)
        current_file_layout.addWidget(self.current_filename_label)
        
        layout.addWidget(current_file_frame)
        
        # Progress section
        progress_frame = QFrame()
        progress_frame.setFrameStyle(QFrame.StyledPanel)
        progress_layout = QVBoxLayout(progress_frame)
        
        self.progress_label = QLabel("Progress: 0 / 0 files")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_frame)
        
        # Statistics section
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QVBoxLayout(stats_frame)
        
        stats_title = QLabel("Statistics:")
        stats_title_font = QFont()
        stats_title_font.setBold(True)
        stats_title.setFont(stats_title_font)
        stats_layout.addWidget(stats_title)
        
        self.frames_label = QLabel("Frames Generated: 0")
        self.animations_label = QLabel("Animations Generated: 0")
        self.failed_label = QLabel("Sprites Failed: 0")
        self.duration_label = QLabel("Duration: 00:00")
        
        stats_layout.addWidget(self.frames_label)
        stats_layout.addWidget(self.animations_label)
        stats_layout.addWidget(self.failed_label)
        stats_layout.addWidget(self.duration_label)
        
        layout.addWidget(stats_frame)
        
        # Processing log
        log_label = QLabel("Processing Log:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_processing)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)  # Disabled until processing completes
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def start_processing(self, total_files):
        """Initialize the processing with the total number of files."""
        print(f"[ProcessingWindow] Starting processing of {total_files} files")
        self.total_files = total_files
        self.current_file_index = 0
        self.progress_bar.setMaximum(max(total_files, 1))
        self.progress_bar.setValue(0)  # Start at 0
        
        # Reset statistics
        self.frames_generated = 0
        self.animations_generated = 0
        self.sprites_failed = 0
        import time
        self.start_time = time.time()
        
        self.update_display()
        self.log_text.append(f"Starting extraction of {total_files} files...")
        
        # Start duration timer
        self.duration_timer = QTimer(self)
        self.duration_timer.timeout.connect(self.update_duration)
        self.duration_timer.start(1000)  # Update every second
        
    def update_progress(self, current_file, total_files, filename=""):
        """Update the progress display."""
        print(f"[ProcessingWindow] update_progress: {current_file}/{total_files} - {filename}")
        self.current_file_index = current_file
        self.total_files = total_files
        self.current_filename = filename
        
        # Update the display immediately
        self.update_display()
        
        if filename:
            self.log_text.append(f"Processing: {filename}")
            # Auto-scroll to bottom
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.log_text.setTextCursor(cursor)
            
        # Force immediate UI refresh
        self.repaint()
        self.update()
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
            
    def update_display(self):
        """Update the display labels and progress bar."""
        if self.current_filename:
            self.current_filename_label.setText(self.current_filename)
        else:
            self.current_filename_label.setText("Initializing...")
            
        self.progress_label.setText(f"Progress: {self.current_file_index} / {self.total_files} files")
        
        if self.total_files > 0:
            # Ensure progress bar maximum is correct
            if self.progress_bar.maximum() != self.total_files:
                self.progress_bar.setMaximum(self.total_files)
            # Set progress bar value directly to current file index
            self.progress_bar.setValue(self.current_file_index)
        else:
            self.progress_bar.setValue(0)
            
        # Force UI update
        self.repaint()
        self.update()
            
    def update_duration(self):
        """Update the duration display."""
        if self.start_time:
            import time
            current_time = time.time()
            duration = current_time - self.start_time
            minutes, seconds = divmod(int(duration), 60)
            self.duration_label.setText(f"Duration: {minutes:02d}:{seconds:02d}")
    
    def update_statistics(self, frames_generated=None, animations_generated=None, sprites_failed=None):
        """Update the statistics display."""
        if frames_generated is not None:
            self.frames_generated = frames_generated
        if animations_generated is not None:
            self.animations_generated = animations_generated
        if sprites_failed is not None:
            self.sprites_failed = sprites_failed
            
        self.frames_label.setText(f"Frames Generated: {self.frames_generated}")
        self.animations_label.setText(f"Animations Generated: {self.animations_generated}")
        self.failed_label.setText(f"Sprites Failed: {self.sprites_failed}")

    def processing_completed(self, success=True, message=""):
        """Called when processing is completed."""
        # Stop the duration timer
        if hasattr(self, 'duration_timer'):
            self.duration_timer.stop()
            
        if success:
            self.current_filename_label.setText("Processing completed successfully!")
            self.log_text.append("✓ Extraction completed successfully!")
            if message:
                self.log_text.append(message)
        else:
            self.current_filename_label.setText("Processing failed!")
            self.log_text.append("✗ Extraction failed!")
            if message:
                self.log_text.append(f"Error: {message}")
                
        self.progress_bar.setValue(self.total_files)  # Set to total files instead of maximum
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Auto-scroll to bottom
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
    def cancel_processing(self):
        """Handle the cancel button click."""
        self.is_cancelled = True
        self.current_filename_label.setText("Cancelling...")
        self.cancel_button.setEnabled(False)
        self.log_text.append("Cancellation requested...")
        
    def closeEvent(self, event):
        """Handle window close event."""
        if self.cancel_button.isEnabled():
            # Processing is still active, cancel it
            self.cancel_processing()
        event.accept()
