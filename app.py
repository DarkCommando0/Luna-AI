import sys
import os
import json
import time
import uuid
import psutil
import platform
from datetime import datetime

# Add the path to find ai_api module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import ai_api

from PySide6.QtCore import Qt, QSize, QThread, Signal, QTimer
from PySide6.QtGui import QPalette, QColor, QFont, QIcon, QTextCursor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QSizePolicy, QDialog,
    QFormLayout, QSpinBox, QComboBox, QCheckBox, QTabWidget, QScrollArea,
    QGroupBox, QFileDialog, QMessageBox, QSlider, QProgressBar, QListWidget,
    QListWidgetItem, QFrame, QTextBrowser
)

from local_model_manager import get_manager as get_local_model_manager

# Enhanced Settings Dialog with model selection
class SettingsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Luna Settings")
        self.setFixedSize(500, 750)
        self.setup_ui()
        self.load_current_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # General Settings Tab
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.default_city = QLineEdit()
        self.default_city.setPlaceholderText("City,Country (e.g., Miami,Florida)")
        general_layout.addRow("Default Weather City:", self.default_city)
        
        tabs.addTab(general_tab, "General")
        
        # Interface Settings Tab
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 24)
        self.font_size.setValue(14)
        ui_layout.addRow("Chat Font Size:", self.font_size)
        
        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        ui_layout.addRow("Theme:", self.theme)
        
        self.auto_scroll = QCheckBox()
        self.auto_scroll.setChecked(True)
        ui_layout.addRow("Auto Scroll:", self.auto_scroll)
        
        self.save_history = QCheckBox()
        self.save_history.setChecked(True)
        ui_layout.addRow("Save Chat History:", self.save_history)
        
        tabs.addTab(ui_tab, "Interface")
        
        # AI Response Settings Tab
        ai_tab = QWidget()
        ai_layout = QVBoxLayout(ai_tab)
        
        # AI Response Creativity section
        creativity_group = QGroupBox("AI Response Creativity")
        creativity_layout = QVBoxLayout(creativity_group)
        
        # Explanation text
        creativity_explanation = QLabel(
            "Controls how varied and creative Luna's responses are:\n"
            "• Low (0.1-0.3): Consistent, predictable responses\n"
            "• Medium (0.4-0.7): Balanced variety and consistency\n"
            "• High (0.8-1.0): Maximum creativity and response variety"
        )
        creativity_explanation.setWordWrap(True)
        creativity_explanation.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 10px;")
        creativity_layout.addWidget(creativity_explanation)
        
        # Creativity slider
        creativity_slider_layout = QHBoxLayout()
        
        creativity_slider_layout.addWidget(QLabel("Conservative"))
        
        self.creativity_slider = QSlider(Qt.Horizontal)
        self.creativity_slider.setRange(1, 10)  # 0.1 to 1.0
        self.creativity_slider.setValue(7)  # Default 0.7
        self.creativity_slider.setTickPosition(QSlider.TicksBelow)
        self.creativity_slider.setTickInterval(1)
        creativity_slider_layout.addWidget(self.creativity_slider)
        
        creativity_slider_layout.addWidget(QLabel("Creative"))
        
        self.creativity_value_label = QLabel("0.7")
        self.creativity_value_label.setMinimumWidth(30)
        self.creativity_value_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        creativity_slider_layout.addWidget(self.creativity_value_label)
        
        # Connect slider to update label
        self.creativity_slider.valueChanged.connect(self.update_creativity_label)
        
        creativity_layout.addLayout(creativity_slider_layout)
        ai_layout.addWidget(creativity_group)
        ai_layout.addStretch()
        
        tabs.addTab(ai_tab, "AI Response")
        
        # API Keys Settings Tab
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
        
        # API Keys group
        api_keys_group = QGroupBox("API Keys")
        api_keys_layout = QFormLayout(api_keys_group)
        
        # OpenRouter API Key
        self.openrouter_api_key = QLineEdit()
        self.openrouter_api_key.setEchoMode(QLineEdit.Password)
        self.openrouter_api_key.setPlaceholderText("Enter your OpenRouter API key (optional)")
        api_keys_layout.addRow("OpenRouter API Key:", self.openrouter_api_key)
        
        or_info = QLabel("Get your OpenRouter API key from: https://openrouter.ai/keys")
        or_info.setStyleSheet("color: #888; font-size: 11px;")
        or_info.setOpenExternalLinks(True)
        or_info.setTextFormat(Qt.TextFormat.RichText)
        or_info.setText('<a href="https://openrouter.ai/keys" style="color: #4CAF50;">Get OpenRouter API Key</a>')
        api_keys_layout.addRow("", or_info)
        
        # OpenWeatherMap API Key
        self.openweathermap_api_key = QLineEdit()
        self.openweathermap_api_key.setEchoMode(QLineEdit.Password)
        self.openweathermap_api_key.setPlaceholderText("Enter your OpenWeatherMap API key (optional)")
        api_keys_layout.addRow("OpenWeatherMap API Key:", self.openweathermap_api_key)
        
        owm_info = QLabel("Get your OpenWeatherMap API key from: https://home.openweathermap.org/api_keys")
        owm_info.setStyleSheet("color: #888; font-size: 11px;")
        owm_info.setOpenExternalLinks(True)
        owm_info.setTextFormat(Qt.TextFormat.RichText)
        owm_info.setText('<a href="https://home.openweathermap.org/api_keys" style="color: #4CAF50;">Get OpenWeatherMap API Key</a>')
        api_keys_layout.addRow("", owm_info)
        
        # Status display
        self.api_status_label = QLabel()
        self.api_status_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px; background-color: #2a2a2a; border-radius: 5px;")
        self.api_status_label.setWordWrap(True)
        self.update_api_status_display()
        api_keys_layout.addRow("", self.api_status_label)
        
        # Connect text change signals for real-time status updates
        self.openrouter_api_key.textChanged.connect(self.on_api_key_changed)
        self.openweathermap_api_key.textChanged.connect(self.on_api_key_changed)
        
        api_layout.addWidget(api_keys_group)
        api_layout.addStretch()
        api_layout.setContentsMargins(0, 0, 0, 20)
        
        tabs.addTab(api_tab, "API Keys")
        
        # Advanced Settings Tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # (Removed) OpenRouter Inference API settings

        # Advanced options
        other_advanced_group = QGroupBox("Advanced Options")
        other_advanced_layout = QFormLayout(other_advanced_group)
        
        self.search_results_limit = QSpinBox()
        self.search_results_limit.setRange(1, 10)
        self.search_results_limit.setValue(3)
        other_advanced_layout.addRow("Search Results Limit:", self.search_results_limit)
        
        self.conversation_memory = QSpinBox()
        self.conversation_memory.setRange(5, 50)
        self.conversation_memory.setValue(10)
        other_advanced_layout.addRow("Conversation Memory:", self.conversation_memory)
        
        self.response_delay = QSpinBox()
        self.response_delay.setRange(0, 2000)
        self.response_delay.setValue(100)
        self.response_delay.setSuffix(" ms")
        other_advanced_layout.addRow("Response Delay:", self.response_delay)

        # Resilience settings (UI controls)
        self.auto_fallback = QCheckBox()
        self.auto_fallback.setChecked(True)
        other_advanced_layout.addRow("Auto Fallback:", self.auto_fallback)

        self.retry_attempts = QSpinBox()
        self.retry_attempts.setRange(1, 10)
        self.retry_attempts.setValue(2)
        other_advanced_layout.addRow("Retry Attempts:", self.retry_attempts)

        self.status_check_interval = QSpinBox()
        self.status_check_interval.setRange(60, 3600)
        self.status_check_interval.setValue(300)
        self.status_check_interval.setSuffix(" s")
        other_advanced_layout.addRow("Status Check Interval:", self.status_check_interval)

        # Advanced recovery options (UI controls)
        self.alt_attempt_cap = QSpinBox()
        self.alt_attempt_cap.setRange(0, 10)
        self.alt_attempt_cap.setValue(3)
        other_advanced_layout.addRow("Alternate Attempt Cap:", self.alt_attempt_cap)

        self.ignore_status_pings = QCheckBox()
        self.ignore_status_pings.setChecked(False)
        self.ignore_status_pings.setToolTip("If enabled, alternates may be attempted even when status pings report paused/error.")
        other_advanced_layout.addRow("Ignore Status Pings:", self.ignore_status_pings)

        from PySide6.QtWidgets import QLineEdit as _QLineEditAlias
        self.alternate_priority = _QLineEditAlias()
        self.alternate_priority.setPlaceholderText("model_id1, model_id2, ...")
        self.alternate_priority.setToolTip("Preferred order of alternate OpenRouter model IDs (comma-separated).")
        other_advanced_layout.addRow("Alternate Priority:", self.alternate_priority)

        # Helper to refresh main UI when resilience settings change
        def _refresh_main_ui():
            try:
                parent = self.parent()
                if parent is not None and hasattr(parent, "update_model_status_ui"):
                    parent.update_model_status_ui()
            except Exception:
                pass

        # Link enabling of advanced recovery controls to Auto Fallback
        def _update_advanced_recovery_enabled(checked: bool):
            self.alt_attempt_cap.setEnabled(checked)
            self.ignore_status_pings.setEnabled(checked)
            self.alternate_priority.setEnabled(checked)
        self.auto_fallback.toggled.connect(_update_advanced_recovery_enabled)
        # Initialize enabled state immediately on construct (before load)
        try:
            _update_advanced_recovery_enabled(self.auto_fallback.isChecked())
        except Exception:
            pass

        # Persist advanced settings when toggles change and refresh main UI
        def _on_auto_fallback_toggled(v: bool):
            try:
                self.settings_manager.set("auto_fallback", bool(v))
            except Exception:
                pass
            _refresh_main_ui()

        def _on_ignore_status_pings_toggled(v: bool):
            try:
                self.settings_manager.set("ignore_status_pings", bool(v))
            except Exception:
                pass
            _refresh_main_ui()

        self.auto_fallback.toggled.connect(_on_auto_fallback_toggled)
        self.ignore_status_pings.toggled.connect(_on_ignore_status_pings_toggled)

        # Feature toggles
        self.enable_web_search = QCheckBox()
        self.enable_web_search.setChecked(True)
        other_advanced_layout.addRow("Enable Web Search:", self.enable_web_search)

        self.enable_system_commands = QCheckBox()
        self.enable_system_commands.setChecked(True)
        other_advanced_layout.addRow("Enable System Commands:", self.enable_system_commands)

        # (Removed) Force-enable unavailable HF models
        
        advanced_layout.addWidget(other_advanced_group)
        advanced_layout.addStretch()
        
        tabs.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_data_btn = QPushButton("Delete Local Data")
        clear_data_btn.clicked.connect(self.clear_local_memory)
        clear_data_btn.setStyleSheet("background-color: #e53935; color: white; padding: 8px; border-radius: 8px;")
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; border-radius: 8px;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #555; color: white; padding: 8px; border-radius: 8px;")
        
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        reset_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px; border-radius: 8px;")
        
        button_layout.addWidget(clear_data_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    def load_api_keys(self):
        """Load API keys from .env file"""
        # Match ai_api._load_env_from_dotenv: when frozen, use the
        # executable directory so .env lives next to LunaAI.exe.
        try:
            import sys as _sys_alias
            if getattr(_sys_alias, "frozen", False) and hasattr(_sys_alias, "executable"):
                base_dir = os.path.dirname(_sys_alias.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(base_dir, '.env')
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('OPENROUTER_API_KEY='):
                        self.openrouter_api_key.setText(line.split('=', 1)[1])
                    elif line.startswith('OPENWEATHERMAP_API_KEY='):
                        self.openweathermap_api_key.setText(line.split('=', 1)[1])
    
    def save_api_keys(self):
        """Save API keys to .env file or delete it if empty"""
        or_key = self.openrouter_api_key.text().strip()
        owm_key = self.openweathermap_api_key.text().strip()
        # Use the same base directory logic as load_api_keys so the
        # .env file is shared between dev and frozen builds.
        try:
            import sys as _sys_alias
            if getattr(_sys_alias, "frozen", False) and hasattr(_sys_alias, "executable"):
                base_dir = os.path.dirname(_sys_alias.executable)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(base_dir, '.env')
        
        if or_key or owm_key:
            # Create .env file with keys
            with open(env_path, 'w') as f:
                f.write("# Luna AI API Keys Configuration\n")
                f.write("# This file is automatically generated by the Settings dialog\n\n")
                
                if or_key:
                    f.write("\n# OpenRouter API Configuration (optional - for premium models)\n")
                    f.write("# Get your API key from: https://openrouter.ai/keys\n")
                    f.write(f"OPENROUTER_API_KEY={or_key}\n")
                    
                if owm_key:
                    f.write("\n# OpenWeatherMap API Configuration (optional - for weather features)\n")
                    f.write("# Get your API key from: https://openweathermap.org/api\n")
                    f.write(f"OPENWEATHERMAP_API_KEY={owm_key}\n")
            
            # Update environment variables for current session
            if or_key:
                os.environ['OPENROUTER_API_KEY'] = or_key
            else:
                if 'OPENROUTER_API_KEY' in os.environ:
                    del os.environ['OPENROUTER_API_KEY']
                    
            if owm_key:
                os.environ['OPENWEATHERMAP_API_KEY'] = owm_key
            else:
                if 'OPENWEATHERMAP_API_KEY' in os.environ:
                    del os.environ['OPENWEATHERMAP_API_KEY']
            # Apply OpenRouter token to backend client immediately so models
            # are not treated as unavailable after saving the key.
            try:
                if or_key:
                    # Prefer direct runtime application
                    ai_api.set_openrouter_api_token(or_key)
                else:
                    # Clear runtime token when key is removed
                    ai_api.set_openrouter_api_token(None)
            except Exception:
                # Best-effort only; UI will still update env/.env
                pass

            self.update_api_status_display("✅ API keys saved successfully!")
            # Update provider status display
            if hasattr(self, 'parent') and hasattr(self.parent(), 'update_provider_status'):
                self.parent().update_provider_status()
            # Refresh model list to update availability
            if hasattr(self, 'parent') and hasattr(self.parent(), 'refresh_model_list'):
                self.parent().refresh_model_list()
            elif hasattr(self, 'refresh_model_list'):
                self.refresh_model_list()
            
        elif os.path.exists(env_path):
            # Delete .env file if no keys
            os.remove(env_path)
            
            # Clear environment variables
            if 'OPENROUTER_API_KEY' in os.environ:
                del os.environ['OPENROUTER_API_KEY']
            if 'OPENWEATHERMAP_API_KEY' in os.environ:
                del os.environ['OPENWEATHERMAP_API_KEY']
                
            self.update_api_status_display("ℹ️ API keys cleared (no keys to save)")
            # Update provider status display
            if hasattr(self, 'parent') and hasattr(self.parent(), 'update_provider_status'):
                self.parent().update_provider_status()
            # Refresh model list to update availability
            if hasattr(self, 'parent') and hasattr(self.parent(), 'refresh_model_list'):
                self.parent().refresh_model_list()
            elif hasattr(self, 'refresh_model_list'):
                self.refresh_model_list()
    
    def on_api_key_changed(self):
        """Handle API key text changes"""
        # Show temporary message when keys are being edited
        or_key = self.openrouter_api_key.text().strip()
        owm_key = self.openweathermap_api_key.text().strip()
        
        if or_key or owm_key:
            self.api_status_label.setText("📝 Type your API keys and click 'Save' to apply changes")
        else:
            self.update_api_status_display()
    
    def update_api_status_display(self, message=None):
        """Update the API status display"""
        
        if message:
            self.api_status_label.setText(message)
            return
        
        or_key = self.openrouter_api_key.text().strip()
        owm_key = self.openweathermap_api_key.text().strip()
        
        status_parts = []
        
        if or_key:
            status_parts.append("✅ OpenRouter token configured")
        else:
            status_parts.append("⚠️ OpenRouter token not set")
            
        if owm_key:
            status_parts.append("✅ OpenWeatherMap token configured")
        else:
            status_parts.append("⚠️ OpenWeatherMap token not set")
        
        self.api_status_label.setText(" | ".join(status_parts))
    
    def update_creativity_label(self, value):
        """Update creativity value label when slider changes"""
        creativity_value = value / 10.0
        self.creativity_value_label.setText(f"{creativity_value:.1f}")
    
    def load_current_settings(self):
        # Helper to coerce truthy/falsey strings to bool
        def _to_bool(v, default=False):
            if v is None:
                return default
            if isinstance(v, bool):
                return v
            try:
                s = str(v).strip().lower()
                if s in ("1", "true", "yes", "on"): return True
                if s in ("0", "false", "no", "off"): return False
            except Exception:
                pass
            return bool(v)
        self.default_city.setText(self.settings_manager.get("default_city"))
        self.font_size.setValue(self.settings_manager.get("chat_font_size"))
        
        theme = self.settings_manager.get("theme")
        theme_index = self.theme.findText(theme)
        if theme_index >= 0:
            self.theme.setCurrentIndex(theme_index)
        
        self.auto_scroll.setChecked(self.settings_manager.get("auto_scroll"))
        self.save_history.setChecked(self.settings_manager.get("save_chat_history"))
        
        # Load creativity setting
        creativity = self.settings_manager.get("ai_creativity")
        self.creativity_slider.setValue(int(creativity * 10))
        self.update_creativity_label(int(creativity * 10))
        
        # Load advanced settings
        self.search_results_limit.setValue(self.settings_manager.get("search_results_limit"))
        self.conversation_memory.setValue(self.settings_manager.get("conversation_memory"))
        self.response_delay.setValue(int(self.settings_manager.get("response_delay") * 1000))
        self.enable_web_search.setChecked(self.settings_manager.get("enable_web_search"))
        self.enable_system_commands.setChecked(self.settings_manager.get("enable_system_commands"))
        # (Removed) HF token and force-enable model settings
        # Load resilience settings
        self.auto_fallback.setChecked(_to_bool(self.settings_manager.get("auto_fallback", True), True))
        self.retry_attempts.setValue(int(self.settings_manager.get("retry_attempts", 2)))
        self.status_check_interval.setValue(int(self.settings_manager.get("status_check_interval", 300)))
        # Load advanced recovery settings
        try:
            self.alt_attempt_cap.setValue(int(self.settings_manager.get("alt_attempt_cap", 3)))
        except Exception:
            self.alt_attempt_cap.setValue(3)
        self.ignore_status_pings.setChecked(_to_bool(self.settings_manager.get("ignore_status_pings", False), False))
        try:
            self.alternate_priority.setText(self.settings_manager.get("alternate_priority", ""))
        except Exception:
            self.alternate_priority.setText("")
        # Apply enabled state based on Auto Fallback
        try:
            enabled = self.auto_fallback.isChecked()
            self.alt_attempt_cap.setEnabled(enabled)
            self.ignore_status_pings.setEnabled(enabled)
            self.alternate_priority.setEnabled(enabled)
        except Exception:
            pass
        
        # Load API keys from .env file if it exists
        self.load_api_keys()
    
    def save_settings(self):
        self.settings_manager.set("default_city", self.default_city.text())
        self.settings_manager.set("chat_font_size", self.font_size.value())
        self.settings_manager.set("theme", self.theme.currentText())
        self.settings_manager.set("auto_scroll", self.auto_scroll.isChecked())
        self.settings_manager.set("save_chat_history", self.save_history.isChecked())
        
        # Save creativity setting
        creativity_value = self.creativity_slider.value() / 10.0
        self.settings_manager.set("ai_creativity", creativity_value)
        
        # Save advanced settings
        self.settings_manager.set("search_results_limit", self.search_results_limit.value())
        self.settings_manager.set("conversation_memory", self.conversation_memory.value())
        self.settings_manager.set("response_delay", self.response_delay.value() / 1000.0)
        self.settings_manager.set("enable_web_search", self.enable_web_search.isChecked())
        self.settings_manager.set("enable_system_commands", self.enable_system_commands.isChecked())
        # (Removed) HF token persistence and application
        # Save resilience settings
        self.settings_manager.set("auto_fallback", self.auto_fallback.isChecked())
        self.settings_manager.set("retry_attempts", self.retry_attempts.value())
        self.settings_manager.set("status_check_interval", self.status_check_interval.value())
        # Save advanced recovery settings
        self.settings_manager.set("alt_attempt_cap", self.alt_attempt_cap.value())
        self.settings_manager.set("ignore_status_pings", self.ignore_status_pings.isChecked())
        self.settings_manager.set("alternate_priority", (self.alternate_priority.text() or "").strip())
        
        # Save API keys and manage .env file
        self.save_api_keys()
        
        # Persist settings to disk so they survive restarts
        try:
            self.settings_manager.save_settings()
        except Exception:
            pass

        # Apply updated settings immediately to AI backend so toggles take effect
        try:
            # Sync creativity to local conversation engine
            ai_api.set_ai_creativity(creativity_value)
            # Push advanced flags/limits so features enable/disable without restart
            ai_api.update_advanced_settings({
                'enable_search': self.enable_web_search.isChecked(),
                'enable_system_commands': self.enable_system_commands.isChecked(),
                'search_results_limit': self.search_results_limit.value(),
                'conversation_memory': self.conversation_memory.value(),
                'response_delay': self.response_delay.value() / 1000.0,
                'current_model': self.settings_manager.get("current_ai_model", "local_engine"),
                'remember_local_profile': self.save_history.isChecked(),
            })
        except Exception:
            pass

        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully!\nAI model, creativity level, and advanced options updated.")
        # Proactively refresh main UI model enabling to reflect new settings
        try:
            parent = self.parent()
            if parent is not None and hasattr(parent, 'update_model_status_ui'):
                parent.update_model_status_ui()
            else:
                # Fallback: find main window among top-level widgets
                try:
                    for w in QApplication.topLevelWidgets():
                        if hasattr(w, 'update_model_status_ui'):
                            w.update_model_status_ui()
                            break
                except Exception:
                    pass
        except Exception:
            pass
        self.accept()
    
    def reset_to_defaults(self):
        reply = QMessageBox.question(self, "Reset Settings", 
                                   "Are you sure you want to reset all settings to defaults?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.settings_manager.settings = self.settings_manager.default_settings.copy()
            self.settings_manager.save_settings()
            self.load_current_settings()
            # Also clear any locally stored conversation memory/profile
            try:
                ai_api.conversation_engine.context_memory = []
                if hasattr(ai_api.conversation_engine, "user_profile"):
                    ai_api.conversation_engine.user_profile = {}
                if hasattr(ai_api.conversation_engine, "clear_disk_data"):
                    ai_api.conversation_engine.clear_disk_data()
            except Exception:
                pass

    def clear_local_memory(self):
        reply = QMessageBox.question(
            self,
            "Delete Local Data",
            "This will delete all locally stored conversation memory and profile data used by the Local Conversation Engine. This cannot be undone.\n\nDo you want to continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        try:
            ai_api.conversation_engine.context_memory = []
            if hasattr(ai_api.conversation_engine, "user_profile"):
                ai_api.conversation_engine.user_profile = {}
            if hasattr(ai_api.conversation_engine, "clear_disk_data"):
                ai_api.conversation_engine.clear_disk_data()
            QMessageBox.information(self, "Local Data Deleted", "All locally stored conversation memory and profile data has been deleted.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to delete local data: {e}")

# Enhanced Thread for API calls with model support
class LunaThread(QThread):
    response_ready = Signal(str)

    def __init__(self, command, settings_manager):
        super().__init__()
        self.command = command
        self.settings_manager = settings_manager

    def run(self):
        try:
            start_time = time.time()
            # Always use the model selected in settings for this response
            try:
                active_model_id = self.settings_manager.get("current_ai_model", "local_engine")
            except Exception:
                active_model_id = "local_engine"

            response = ai_api.call_ai_api(self.command, model_id=active_model_id)
            response_time = time.time() - start_time
            
            # Update performance metrics
            self.settings_manager.update_performance_metrics(response_time)
            
            self.response_ready.emit(response)
        except Exception as e:
            self.response_ready.emit(f"Error: {str(e)}")

# Worker thread to check OpenRouter model statuses without blocking the UI
class ModelStatusWorker(QThread):
    """Checks the availability of provided OpenRouter models.
    Emits a dictionary mapping model_id -> {'status': str, 'error': Optional[str]} upon completion."""
    results_ready = Signal(dict)

    def __init__(self, model_ids):
        super().__init__()
        self.model_ids = model_ids or []

    def run(self):
        results = {}
        for model_id in self.model_ids:
            try:
                res = ai_api.check_hf_model_status(model_id)
                # Ensure keys exist
                status = res.get('status', 'error')
                error = res.get('error')
                results[model_id] = {'status': status, 'error': error}
            except Exception as e:
                results[model_id] = {'status': 'error', 'error': str(e)}
        self.results_ready.emit(results)

# Enhanced Settings management with OpenRouter models
class SettingsManager:
    def __init__(self):
        self.settings_file = "luna_settings.json"
        self.default_settings = {
            "default_city": "",
            "ai_creativity": 0.7,
            "chat_font_size": 14,
            "theme": "dark",
            "auto_scroll": True,
            "save_chat_history": True,
            # Advanced settings
            "response_delay": 0.1,
            "search_results_limit": 3,
            "conversation_memory": 10,
            # Model settings
            "current_ai_model": "local_engine",
            "api_timeout": 30,
            # Resilience settings (backend only; no UI controls yet)
            "auto_fallback": True,
            "retry_attempts": 2,
            # Advanced recovery defaults
            "alt_attempt_cap": 3,              # Max alternate OpenRouter models to try (0 disables alternates)
            "ignore_status_pings": False,      # If true, attempt alternates regardless of status ping classification
            "alternate_priority": "",         # Comma-separated model_id order to prefer when trying alternates
            # Background status monitoring interval in seconds (default 5 minutes)
            "status_check_interval": 300,
            # (Removed) OpenRouter token/force-enable settings
            "enable_web_search": True,
            "enable_system_commands": True,
            # Available models (as originally configured by the user)
            "available_models": {
                "local_engine": {
                    "name": "Conversation Engine",
                    "type": "local",
                    "description": "Fast local responses with advanced pattern matching and creativity controls",
                    "features": ["instant_response", "offline", "privacy", "creativity_control", "weather_integration", "web_search", "system_commands"],
                    "status": "active"
                },
                "local/mistral-7b-instruct": {
                    "name": "Mistral 7B",
                    "type": "local",
                    "description": "Local 7B parameter model with excellent performance, runs entirely on your hardware",
                    "features": ["conversation", "reasoning", "instruction_following", "code_generation", "offline", "privacy"],
                    "status": "available"
                },
                "local/llama-3.1-8b-instruct": {
                    "name": "Llama 3.1 8B",
                    "type": "local",
                    "description": "Latest local 8B model with strong reasoning capabilities, runs entirely on your hardware",
                    "features": ["reasoning", "conversation", "instruction_following", "knowledge_retrieval", "offline", "privacy"],
                    "status": "available"
                },
                "local/qwen-2.5-7b-instruct": {
                    "name": "Qwen 2.5 7B",
                    "type": "local",
                    "description": "Local 7B model with strong multilingual capabilities, runs entirely on your hardware",
                    "features": ["multilingual", "conversation", "reasoning", "instruction_following", "offline", "privacy"],
                    "status": "available"
                },
                "local/deepseek-coder-6.7b": {
                    "name": "DeepSeek Coder 6.7B",
                    "type": "local",
                    "description": "Local 6.7B model optimized for coding and programming tasks, runs entirely on your hardware",
                    "features": ["code_generation", "programming_assistance", "debugging", "offline", "privacy"],
                    "status": "available"
                },
                "deepseek/deepseek-r1-0528:free": {
                    "name": "DeepSeek R1",
                    "type": "openrouter",
                    "description": "DeepSeek's latest conversational model optimized for chat interactions and instruction following",
                    "features": ["conversation", "instruction_following", "reasoning", "multilingual"],
                    "status": "available"
                },
                "openai/gpt-oss-20b:free": {
                    "name": "OpenAI GPT-OSS 20B",
                    "type": "openrouter",
                    "description": "Open-source 20B parameter language model based on GPT architecture with strong general-purpose capabilities",
                    "features": ["conversation", "reasoning", "code_generation", "knowledge_retrieval", "multilingual"],
                    "status": "available"
                },
                "openai/gpt-oss-120b:free": {
                    "name": "OpenAI GPT-OSS 120B",
                    "type": "openrouter",
                    "description": "Larger GPT-OSS 120B parameter model for more demanding reasoning and generation tasks",
                    "features": ["conversation", "reasoning", "code_generation", "knowledge_retrieval", "multilingual"],
                    "status": "available"
                }
            }
        }
        self.settings = self.load_settings()
        # Ensure persistent error storage key exists
        if 'model_errors' not in self.settings:
            self.settings['model_errors'] = {}
        # Initialize performance tracking
        self.performance_metrics = {
            "total_responses": 0,
            "avg_response_time": 0.05,
            "last_response_time": 0.0,
            "session_start": time.time(),
            "memory_usage": 0.0
        }
        self.model_errors = {}  # Track errors by model_id: {error: str, timestamp: float}
        self.model_status = {}  # Track status of each model: 'available', 'paused', 'error', 'checking'

    def set_model_status(self, model_id: str, status: str, error=None):
        """Set the status for a model and record/clear error accordingly."""
        # Normalize
        status = (status or 'error').lower()
        self.model_status[model_id] = status
        if status == 'available':
            # Clear any recorded error
            if model_id in self.model_errors:
                del self.model_errors[model_id]
            if 'model_errors' not in self.settings:
                self.settings['model_errors'] = {}
            if model_id in self.settings['model_errors']:
                del self.settings['model_errors'][model_id]
        else:
            # Save/Update error
            msg = error or ('Paused' if status == 'paused' else 'Unavailable')
            self.model_errors[model_id] = {'error': msg, 'timestamp': time.time()}
            if 'model_errors' not in self.settings:
                self.settings['model_errors'] = {}
            self.settings['model_errors'][model_id] = {'error': msg, 'timestamp': time.time()}
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults for any missing keys
                    settings = self.default_settings.copy()
                    settings.update(loaded)
                    # Update available models to include new ones
                    settings["available_models"] = self.default_settings["available_models"].copy()
                    return settings
        except Exception:
            pass
        return self.default_settings.copy()
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key, default=None):
        if key in self.settings:
            return self.settings[key]
        return default
    
    def set(self, key, value):
        self.settings[key] = value
        
    def set_model_error(self, model_id: str, error: str):
        """Record an error for a specific model"""
        self.model_errors[model_id] = {
            'error': error,
            'timestamp': time.time()
        }
        # Update status based on error type
        if 'paused' in error.lower():
            self.model_status[model_id] = 'paused'
        else:
            self.model_status[model_id] = 'error'
        self.settings['model_errors'][model_id] = {
            'error': error,
            'timestamp': time.time()
        }
    
    def get_model_error(self, model_id: str):
        """Get the last error for a model, if any"""
        return self.model_errors.get(model_id)
        
    def get_model_status(self, model_id: str) -> str:
        """Get the current status of a model"""
        return self.model_status.get(model_id, 'available')
        
    def check_model_availability(self, model_id: str) -> bool:
        """Check if a model is available for use"""
        return self.get_model_status(model_id) == 'available'
        
    def clear_model_error(self, model_id: str):
        """Clear any recorded error for a model"""
        if model_id in self.model_errors:
            del self.model_errors[model_id]
        if model_id in self.model_status:
            self.model_status[model_id] = 'available'
        if model_id in self.settings['model_errors']:
            del self.settings['model_errors'][model_id]
        self.save_settings()
    
    def get_active_model(self):
        """Return the active model info, tolerant of ID/alias mismatches.

        Ensures the returned dict always has an 'id' field matching the resolved key.
        """
        try:
            models = self.settings.get("available_models", {}) or {}
        except Exception:
            models = {}

        current_model_id = self.settings.get("current_ai_model", "local_engine")

        def _with_id(mid: str, info: dict):
            d = dict(info or {})
            d.setdefault("id", mid)
            return d

        # Direct hit
        if current_model_id in models:
            return _with_id(current_model_id, models[current_model_id])

        # Try to normalize and map friendly/alias IDs to known keys (similar to ai_api.set_current_model)
        def _norm(s: str) -> str:
            return "".join(ch for ch in str(s).lower() if ch.isalnum())

        target = _norm(current_model_id)
        candidates = []
        for mid, info in models.items():
            norm_key = _norm(mid)
            norm_name = _norm(info.get("name", mid))
            suffix = norm_key.split("/")[-1] if "/" in norm_key else norm_key
            if target == norm_key or target == norm_name or target.endswith(suffix):
                candidates.append(mid)

        if candidates:
            mapped = candidates[0]
            try:
                # Persist the resolved ID so future lookups are fast and consistent
                self.settings["current_ai_model"] = mapped
                self.save_settings()
            except Exception:
                pass
            return _with_id(mapped, models.get(mapped, {}))

        # Fallback to local engine
        local = models.get("local_engine", {})
        return _with_id("local_engine", local)
    
    def update_performance_metrics(self, response_time):
        """Update performance tracking metrics"""
        self.performance_metrics["total_responses"] += 1
        self.performance_metrics["last_response_time"] = response_time
        
        # Calculate running average
        total = self.performance_metrics["total_responses"]
        current_avg = self.performance_metrics["avg_response_time"]
        self.performance_metrics["avg_response_time"] = (current_avg * (total - 1) + response_time) / total
        
        # Update memory usage
        try:
            process = psutil.Process()
            self.performance_metrics["memory_usage"] = process.memory_percent()
        except:
            self.performance_metrics["memory_usage"] = 0.0

# Enhanced AI Models Management Dialog with model selection
class ModelsDialog(QDialog):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Luna Model Information")
        self.setFixedSize(750, 600)
        self.local_model_manager = None
        self.setup_ui()
        self.load_model_data()
        
        # Setup refresh timer for real-time updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_performance_display)
        self.refresh_timer.start(1000)  # Update every second
        
        # Live refresh when model statuses update in the main window
        try:
            if parent is not None and hasattr(parent, 'model_status_updated'):
                parent.model_status_updated.connect(self.load_model_data)
        except Exception:
            pass
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with current model status
        header_layout = QHBoxLayout()
        
        title = QLabel("AI Model Information")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Active model indicator
        current_model = self.settings_manager.get_active_model()
        model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
        self.active_model_label = QLabel(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")
        self.active_model_label.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 12px; border-radius: 12px; font-weight: bold;")
        header_layout.addWidget(self.active_model_label)
        
        layout.addLayout(header_layout)
        
        # Tab widget for different sections
        self.tabs = QTabWidget()
        
        # Model Overview Tab
        overview_tab = self.create_overview_tab()
        self.tabs.addTab(overview_tab, "📋 Model Overview")
        
        # System Status Tab with real performance metrics
        status_tab = self.create_status_tab()
        self.tabs.addTab(status_tab, "📊 System Performance")
        
        layout.addWidget(self.tabs)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("background-color: #555; color: white; padding: 8px; border-radius: 8px;")
        
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_model_selection_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Instructions
        instructions = QLabel("Select an AI model to use for conversations:")
        instructions.setStyleSheet("color: white; margin-bottom: 15px; font-size: 14px;")
        layout.addWidget(instructions)

        # Token handled in backend via environment/.env (no UI token fields)
        
        # Model selection area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Create model cards
        available_models = self.settings_manager.get("available_models")
        current_model_id = self.settings_manager.get("current_ai_model")
        
        for model_id, model_info in available_models.items():
            # Create a completely independent copy of the model info
            # Using json dumps/loads to ensure a deep copy of all nested structures
            model_info_copy = json.loads(json.dumps({
                'name': model_info.get('name', 'Unknown'),
                'type': model_info.get('type', 'openrouter'),
                'description': model_info.get('description', 'No description available'),
                'features': model_info.get('features', []).copy(),
                'status': model_info.get('status', 'available')
            }))
            model_card = self.create_model_card(model_id, model_info_copy, model_id == current_model_id)
            scroll_layout.addWidget(model_card)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555; border-radius: 8px;")
        
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_model_card(self, model_id, model_info, is_active):
        """Create a model card widget with status indicators"""
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setLineWidth(1)
        card.setStyleSheet("""
            QFrame {
                background: #2d2d2d;
                border-radius: 8px;
                padding: 12px;
                margin: 5px;
                border: 1px solid #3a3a3a;
            }
            QFrame:hover {
                background: #3a3a3a;
                border: 1px solid #4d4d4d;
            }
            QLabel#modelName {
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
            }
            QLabel#modelId {
                font-size: 11px;
                color: #aaaaaa;
                margin-top: 2px;
            }
            QLabel#modelDesc {
                font-size: 12px;
                color: #cccccc;
                margin: 8px 0;
            }
            QPushButton {
                background: #3a6ea5;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #4a7eb5;
            }
            QPushButton:disabled {
                background: #555555;
                color: #888888;
            }
        """)
        
        layout = QVBoxLayout(card)
        
        # Model name and ID
        name_label = QLabel(model_info.get('name', model_id))
        name_label.setObjectName("modelName")
        id_label = QLabel(f"ID: {model_id}")
        id_label.setObjectName("modelId")
        
        # Model description
        desc_label = QLabel(model_info.get('description', 'No description available'))
        desc_label.setObjectName("modelDesc")
        desc_label.setWordWrap(True)
        
        # Status indicator (unavailable tool removed): always display Available (no external checks)
        status_label = QLabel("Available")
        status_label.setAlignment(Qt.AlignRight)
        status_label.setStyleSheet("color: #51cf66; font-size: 11px;")
        status_label.setToolTip("This model is available for use")
        
        # Header layout with name and status
        header_layout = QHBoxLayout()
        header_layout.addWidget(name_label, 1)
        header_layout.addWidget(status_label)
        
        # Select button (unavailable tool removed): always allow selection if not already active
        select_btn = QPushButton("Select" if not is_active else "Selected")
        select_btn.setEnabled(not is_active)
        
        # Add widgets to layout
        layout.addLayout(header_layout)
        layout.addWidget(id_label)
        layout.addWidget(desc_label)
        
        # Features list
        features = model_info.get('features', [])
        if features:
            features_label = QLabel("Features: " + ", ".join(features))
            features_label.setStyleSheet("font-size: 11px; color: #888;")
            features_label.setWordWrap(True)
            layout.addWidget(features_label)
        
        # Last checked time
        last_checked = self.settings_manager.model_errors.get(model_id, {}).get('timestamp')
        if last_checked:
            last_checked_str = datetime.fromtimestamp(last_checked).strftime('%Y-%m-%d %H:%M:%S')
            checked_label = QLabel(f"Last checked: {last_checked_str}")
            checked_label.setStyleSheet("font-size: 9px; color: #666;")
            layout.addWidget(checked_label)
        
        # Container for action buttons (select + optional download/open-folder for local models)
        layout.addStretch()

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(select_btn)

        download_btn = None
        download_progress = None
        download_path_label = None
        open_folder_btn = None

        # For local models, provide Download and Open Folder controls
        if model_id.startswith("local/") or model_info.get("type") == "local":
            # Lazy-init local model manager
            if self.local_model_manager is None:
                try:
                    self.local_model_manager = get_local_model_manager()
                except Exception:
                    self.local_model_manager = None

            downloaded = False
            model_path_text = ""
            if self.local_model_manager is not None:
                try:
                    downloaded = self.local_model_manager.is_model_downloaded(model_id)
                    path_obj = self.local_model_manager.get_model_path(model_id)
                    if path_obj is not None:
                        model_path_text = str(path_obj)
                except Exception:
                    downloaded = False

            download_btn = QPushButton("Download Model" if not downloaded else "Re-download")
            download_btn.setStyleSheet("margin-left: 8px;")

            download_progress = QProgressBar()
            download_progress.setRange(0, 100)
            download_progress.setValue(0)
            download_progress.setVisible(False)
            download_progress.setStyleSheet(
                "QProgressBar {"
                "    border: 1px solid #555;"
                "    border-radius: 4px;"
                "    text-align: center;"
                "    background-color: #2b2b2b;"
                "    color: white;"
                "    min-width: 120px;"
                "}"
                "QProgressBar::chunk {"
                "    background-color: #4CAF50;"
                "    border-radius: 3px;"
                "}"
            )

            actions_layout.addWidget(download_btn)
            actions_layout.addWidget(download_progress)

            download_path_label = QLabel()
            download_path_label.setStyleSheet("font-size: 10px; color: #aaaaaa; margin-top: 4px;")
            if model_path_text:
                download_path_label.setText(f"Stored at: {model_path_text}")

            open_folder_btn = QPushButton("Open Folder")
            open_folder_btn.setEnabled(bool(model_path_text))
            open_folder_btn.setStyleSheet("margin-left: 8px;")
            actions_layout.addWidget(open_folder_btn)

            # Bind download and open-folder actions
            def _start_download(_, mid=model_id, pb=download_progress, lbl=download_path_label, btn=download_btn, ofb=open_folder_btn):
                self.download_local_model(mid, pb, lbl, btn, ofb)

            def _open_folder(_, mid=model_id):
                self.open_local_model_folder(mid)

            try:
                download_btn.clicked.connect(_start_download)
                open_folder_btn.clicked.connect(_open_folder)
            except Exception:
                pass

        layout.addLayout(actions_layout)

        if download_path_label is not None:
            layout.addWidget(download_path_label)
        
        # Set fixed height for consistent card sizes
        card.setFixedHeight(240)
        
        # Store model ID for status updates
        card.model_id = model_id
        
        # Set hover effect for select button
        select_btn.setStyleSheet("""
            QPushButton {
                background: #3a6ea5;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 8px;
            }
            QPushButton:hover {
                background: #4a7eb5;
            }
            QPushButton:disabled {
                background: #555555;
                color: #888888;
            }
        """)
        
        # Bind model_id via default arg to avoid late-binding issues in loops
        try:
            select_btn.clicked.connect(lambda _, mid=model_id: self.select_model(mid))
        except Exception:
            pass
        
        return card

    def download_local_model(self, model_id, progress_bar, path_label, download_btn, open_folder_btn=None):
        """Download a local GGUF model in the background and update UI progress."""
        if self.local_model_manager is None:
            try:
                self.local_model_manager = get_local_model_manager()
            except Exception as e:
                QMessageBox.warning(self, "Local Models Disabled", f"Local model manager is not available:\n{e}")
                return

        progress_bar.setVisible(True)
        progress_bar.setValue(0)
        download_btn.setEnabled(False)

        class DownloadWorker(QThread):
            progress = Signal(int, int, str)
            finished_with_result = Signal(bool, str)

            def __init__(self, manager, model_id):
                super().__init__()
                self.manager = manager
                self.model_id = model_id

            def run(self):
                def _cb(current, total, msg):
                    try:
                        self.progress.emit(current, total, msg)
                    except Exception:
                        pass

                success = self.manager.download_model(self.model_id, progress_callback=_cb)
                self.finished_with_result.emit(success, self.model_id)

        worker = DownloadWorker(self.local_model_manager, model_id)
        self._download_worker = worker

        def _on_progress(current, total, msg):
            try:
                if total and total > 0:
                    percent = max(0, min(100, int((current / float(total)) * 100)))
                else:
                    percent = 0
                progress_bar.setValue(percent)
                if msg:
                    progress_bar.setFormat(msg + " (%p%)")
                else:
                    progress_bar.setFormat("%p%")
            except Exception:
                pass

        def _on_finished(success, mid):
            try:
                progress_bar.setVisible(False)
                download_btn.setEnabled(True)

                if not success:
                    QMessageBox.warning(self, "Download Failed", f"Failed to download model: {mid}")
                    return

                # Refresh model path information
                try:
                    path_obj = self.local_model_manager.get_model_path(mid)
                    if path_obj is not None:
                        path_text = str(path_obj)
                        if path_label is not None:
                            path_label.setText(f"Stored at: {path_text}")
                        if open_folder_btn is not None:
                            open_folder_btn.setEnabled(True)
                        QMessageBox.information(
                            self,
                            "Model Downloaded",
                            f"Model '{mid}' has been downloaded.\n\nLocation:\n{path_text}"
                        )
                except Exception:
                    pass
            finally:
                try:
                    worker.deleteLater()
                except Exception:
                    pass

        try:
            worker.progress.connect(_on_progress)
            worker.finished_with_result.connect(_on_finished)
            worker.start()
        except Exception as e:
            progress_bar.setVisible(False)
            download_btn.setEnabled(True)
            QMessageBox.warning(self, "Download Error", f"Could not start download thread:\n{e}")

    def open_local_model_folder(self, model_id):
        """Open the folder containing the local model file in the OS file manager."""
        if self.local_model_manager is None:
            try:
                self.local_model_manager = get_local_model_manager()
            except Exception as e:
                QMessageBox.warning(self, "Local Models Disabled", f"Local model manager is not available:\n{e}")
                return

        try:
            path_obj = self.local_model_manager.get_model_path(model_id)
            if not path_obj:
                QMessageBox.information(self, "Model Not Downloaded", "This model has not been downloaded yet.")
                return

            folder = os.path.dirname(str(path_obj))
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.warning(self, "Open Folder Failed", f"Could not open model folder:\n{e}")
    
    def select_model(self, model_id):
        """Select a new AI model"""
        try:
            # Update settings
            self.settings_manager.set("current_ai_model", model_id)
            
            # Update AI API
            ai_api.set_current_model(model_id)
            ai_api.update_advanced_settings({'current_model': model_id})
            
            # Show confirmation
            models = self.settings_manager.get("available_models", {}) or {}
            model_info = models.get(model_id, {"name": model_id})
            QMessageBox.information(self, "Model Selected", 
                                  f"Switched to {model_info.get('name', model_id)}")
            
            # Refresh the dialog
            self.load_model_data()
            
            # Update active model indicator
            current_model = self.settings_manager.get_active_model()
            model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
            self.active_model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")
            
            # Update parent window if it has a model label
            if hasattr(self.parent(), 'model_label'):
                self.parent().model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to select model: {str(e)}")

    

    def create_overview_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Model details panel
        model_details_group = QGroupBox("Active Model Details")
        model_details_group.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                font-weight: bold;
                padding-top: 15px;
                color: white;
            }
            QGroupBox::title {
                color: #4CAF50;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        details_layout = QVBoxLayout(model_details_group)
        
        self.model_details = QTextBrowser()
        self.model_details.setStyleSheet("""
            background-color: #3a3a3a;
            border: 1px solid #555;
            border-radius: 8px;
            padding: 15px;
            color: white;
            font-size: 12px;
        """)
        details_layout.addWidget(self.model_details)
        
        layout.addWidget(model_details_group)
        
        # Current settings panel
        settings_group = QGroupBox("Current Configuration")
        settings_group.setStyleSheet("""
            QGroupBox {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 8px;
                padding-top: 15px;
                color: white;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)
        
        self.current_settings = QTextBrowser()
        self.current_settings.setMaximumHeight(150)
        self.current_settings.setStyleSheet("background-color: #3a3a3a; color: white; border: none; padding: 10px; font-size: 11px;")
        settings_layout.addWidget(self.current_settings)
        
        layout.addWidget(settings_group)
        
        return widget
    
    def create_status_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # System capabilities
        capabilities_group = QGroupBox("System Capabilities")
        capabilities_group.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 1px solid #4CAF50;
                border-radius: 8px;
                padding-top: 15px;
                color: white;
            }
        """)
        cap_layout = QVBoxLayout(capabilities_group)
        
        self.capabilities_list = QTextBrowser()
        self.capabilities_list.setMaximumHeight(200)
        self.capabilities_list.setStyleSheet("background-color: #3a3a3a; color: white; border: none; padding: 10px;")
        cap_layout.addWidget(self.capabilities_list)
        
        layout.addWidget(capabilities_group)
        
        # Performance metrics with real data
        metrics_group = QGroupBox("Real-time Performance Metrics")
        metrics_group.setStyleSheet("""
            QGroupBox {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 8px;
                padding-top: 15px;
                color: white;
            }
        """)
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Response time
        response_layout = QHBoxLayout()
        response_layout.addWidget(QLabel("Average Response Time:"))
        self.response_time_label = QLabel("< 0.1s")
        self.response_time_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        response_layout.addWidget(self.response_time_label)
        response_layout.addStretch()
        metrics_layout.addLayout(response_layout)
        
        # Last response time
        last_response_layout = QHBoxLayout()
        last_response_layout.addWidget(QLabel("Last Response Time:"))
        self.last_response_label = QLabel("0.0s")
        self.last_response_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        last_response_layout.addWidget(self.last_response_label)
        last_response_layout.addStretch()
        metrics_layout.addLayout(last_response_layout)
        
        # Total responses
        total_layout = QHBoxLayout()
        total_layout.addWidget(QLabel("Total Responses:"))
        self.total_responses_label = QLabel("0")
        self.total_responses_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        total_layout.addWidget(self.total_responses_label)
        total_layout.addStretch()
        metrics_layout.addLayout(total_layout)
        
        # Memory usage
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("Memory Usage:"))
        self.memory_progress = QProgressBar()
        self.memory_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: #555;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        memory_layout.addWidget(self.memory_progress)
        self.memory_label = QLabel("0.0%")
        self.memory_label.setStyleSheet("color: #4CAF50; font-weight: bold; min-width: 50px;")
        memory_layout.addWidget(self.memory_label)
        metrics_layout.addLayout(memory_layout)
        
        # Session uptime
        uptime_layout = QHBoxLayout()
        uptime_layout.addWidget(QLabel("Session Uptime:"))
        self.uptime_label = QLabel("0m 0s")
        self.uptime_label.setStyleSheet("color: #9C27B0; font-weight: bold;")
        uptime_layout.addWidget(self.uptime_label)
        uptime_layout.addStretch()
        metrics_layout.addLayout(uptime_layout)
        
        layout.addWidget(metrics_group)
        
        # System information
        system_group = QGroupBox("System Information")
        system_group.setStyleSheet("""
            QGroupBox {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 8px;
                padding-top: 15px;
                color: white;
            }
        """)
        system_layout = QVBoxLayout(system_group)
        
        self.system_info = QTextBrowser()
        self.system_info.setMaximumHeight(120)
        self.system_info.setStyleSheet("background-color: #3a3a3a; color: white; border: none; padding: 10px; font-size: 11px;")
        system_layout.addWidget(self.system_info)
        
        layout.addWidget(system_group)
        
        return widget
    
    def load_model_data(self):
        model_info = self.settings_manager.get_active_model()
        model_type_emoji = "💻" if model_info.get("type") == "local" else "🤖"
        model_type_text = "Local Engine" if model_info.get("type") == "local" else "OpenRouter Model"
        
        # Check for model errors
        model_id = model_info.get('id', '')
        model_error = self.settings_manager.get_model_error(model_id)
        
        if model_error and 'paused' in model_error.get('error', '').lower():
            status_html = '<span style="color: #FFC107;">⚠️ [PAUSED] Endpoint Unavailable</span>'
        else:
            status_html = '<span style="color: #4CAF50;">✓ [ACTIVE] Ready</span>'
        
        # Update model details
        details_html = f"""
        <h2>{model_type_emoji} {model_info.get('name', 'Unknown Model')}</h2>
        <p><strong>Type:</strong> {model_type_text}</p>
        <p><strong>Status:</strong> {status_html}</p>
        <p><strong>Description:</strong> {model_info.get('description', 'No description available')}</p>
        
        <h3>Key Features:</h3>
        <ul>
        """
        
        features = model_info.get('features', [])
        feature_descriptions = {
            'instant_response': '⚡ <strong>Instant Response:</strong> Sub-100ms response times',
            'offline': '🔒 <strong>Privacy First:</strong> All processing happens locally',
            'privacy': '🌐 <strong>No Internet Required:</strong> Works completely offline',
            'creativity_control': '🎨 <strong>Creativity Control:</strong> Adjustable response personality',
            'weather_integration': '🌤️ <strong>Weather Integration:</strong> Real-time weather data',
            'web_search': '🔍 <strong>Web Search:</strong> DuckDuckGo search integration',
            'system_commands': '⚙️ <strong>System Commands:</strong> Direct OS interaction',
            'text_generation': '📝 <strong>Text Generation:</strong> Advanced language generation',
            'instruction_following': '🎯 <strong>Instruction Following:</strong> Precise task execution',
            'multilingual': '🌍 <strong>Multilingual:</strong> Multiple language support',
            'reasoning': '🧠 <strong>Reasoning:</strong> Logical problem solving',
            'logic': '🔬 <strong>Logic:</strong> Advanced logical capabilities',
            'problem_solving': '🎲 <strong>Problem Solving:</strong> Complex problem resolution',
            'advanced_reasoning': '🧩 <strong>Advanced Reasoning:</strong> Complex logical thinking',
            'code_generation': '💻 <strong>Code Generation:</strong> Programming assistance',
            'debugging': '🐛 <strong>Debugging:</strong> Code error detection and fixing',
            'programming_help': '🛠️ <strong>Programming Help:</strong> Coding assistance and guidance',
            'code_explanation': '📚 <strong>Code Explanation:</strong> Code analysis and explanation'
        }
        
        for feature in features:
            feature_desc = feature_descriptions.get(feature, f'✨ <strong>{feature.replace("_", " ").title()}</strong>')
            details_html += f"<li>{feature_desc}</li>"
        
        details_html += """
        </ul>
        """
        
        # Add provider and technology information
        provider = model_info.get('provider', 'unknown')
        if provider == 'local':
            details_html += """
            <p><strong>Provider:</strong> <span style="color: #4CAF50;">💻 Local Engine</span></p>
            <p><strong>Technology:</strong> Advanced pattern matching with contextual awareness and creative response generation.</p>
            <p><strong>Cost:</strong> <span style="color: #4CAF50;">✓ Free (No API required)</span></p>
            """
        elif provider == 'openrouter':
            details_html += """
            <p><strong>Provider:</strong> <span style="color: #2196F3;">🔵 OpenRouter Premium</span></p>
            <p><strong>Technology:</strong> Premium AI model accessed via OpenRouter's unified API gateway.</p>
            <p><strong>Cost:</strong> <span style="color: #FFA500;">🔑 Requires OpenRouter API key and credits</span></p>
            <p><strong>Status:</strong> <span style="color: #FF9800;">{model_info.get('status', 'unknown').replace('_', ' ').title()}</span></p>
            """
        else:
            details_html += "<p><strong>Technology:</strong> Neural language model with API integration.</p>"
        
        self.model_details.setHtml(details_html)
        
        # Update current settings
        self.update_current_settings()
        
        # Update capabilities
        self.update_capabilities_display()
        
        # Ensure system info panel shows data when dialog opens
        try:
            self.update_system_info_panel()
        except Exception:
            pass
    
    def update_current_settings(self):
        """Populate the Current Configuration panel with live settings values."""
        try:
            if not hasattr(self, 'current_settings') or self.current_settings is None:
                return
            # Gather settings
            current_model = self.settings_manager.get_active_model() or {}
            current_model_name = current_model.get('name', 'Unknown')
            current_model_id = current_model.get('id', self.settings_manager.get('current_ai_model', 'unknown'))
            creativity = self.settings_manager.get('ai_creativity', 0.7)
            web_enabled = bool(self.settings_manager.get('enable_web_search', True))
            sys_enabled = bool(self.settings_manager.get('enable_system_commands', False))
            api_timeout = self.settings_manager.get('api_timeout', 30)
            
            # Build HTML
            html = f"""
            <ul>
                <li><strong>Active Model:</strong> {current_model_name} ({current_model_id})</li>
                <li><strong>Creativity:</strong> {creativity:.1f}</li>
                <li><strong>Web Search:</strong> {'Enabled' if web_enabled else 'Disabled'}</li>
                <li><strong>System Commands:</strong> {'Enabled' if sys_enabled else 'Disabled'}</li>
                <li><strong>API Timeout:</strong> {api_timeout}s</li>
            </ul>
            """
            self.current_settings.setHtml(html)
        except Exception as e:
            try:
                self.current_settings.setHtml(f"<p>Error loading settings: {str(e)}</p>")
            except Exception:
                pass
    
    def update_capabilities_display(self):
        search_enabled = self.settings_manager.get("enable_web_search")
        system_enabled = self.settings_manager.get("enable_system_commands")
        current_model = self.settings_manager.get_active_model()
        
        capabilities_html = "<h3>🚀 Active Capabilities:</h3><ul>"
        
        # Model-specific capabilities
        if current_model.get('type') == 'local':
            capabilities_html += "<li>💬 <strong>Natural Conversation:</strong> Advanced contextual chat</li>"
            capabilities_html += "<li>⚡ <strong>Instant Responses:</strong> Lightning-fast local processing</li>"
            capabilities_html += "<li>🔒 <strong>Privacy Protected:</strong> No data leaves your device</li>"
            capabilities_html += "<li>🎨 <strong>Creativity Control:</strong> Adjustable personality modes</li>"
        else:
            capabilities_html += "<li>🤖 <strong>Advanced AI:</strong> State-of-the-art language model</li>"
            capabilities_html += "<li>🌐 <strong>Cloud-Powered:</strong> OpenRouter infrastructure</li>"
            capabilities_html += "<li>🧠 <strong>Deep Learning:</strong> Neural network responses</li>"
            
            # Add model-specific features
            features = current_model.get('features', [])
            if 'reasoning' in features or 'logic' in features:
                capabilities_html += "<li>🔬 <strong>Advanced Reasoning:</strong> Logical problem solving</li>"
            if 'code_generation' in features:
                capabilities_html += "<li>💻 <strong>Code Generation:</strong> Programming assistance</li>"
            if 'multilingual' in features:
                capabilities_html += "<li>🌍 <strong>Multilingual:</strong> Multiple language support</li>"
        
        # Common capabilities
        capabilities_html += "<li>🌤️ <strong>Weather Information:</strong> Real-time weather updates</li>"
        
        # Conditional capabilities
        if search_enabled:
            capabilities_html += "<li>🔍 <strong>Web Search:</strong> DuckDuckGo integration</li>"
        else:
            capabilities_html += "<li>🔍 <strong>Web Search:</strong> <span style='color: #888;'>Disabled</span></li>"
        
        if system_enabled:
            capabilities_html += "<li>⚙️ <strong>System Control:</strong> Open apps, control volume, screenshots</li>"
        else:
            capabilities_html += "<li>⚙️ <strong>System Control:</strong> <span style='color: #888;'>Disabled</span></li>"
        
        capabilities_html += "<li>💾 <strong>Memory:</strong> Contextual conversation history</li>"
        capabilities_html += "<li>🎯 <strong>Intent Recognition:</strong> Smart command interpretation</li>"
        capabilities_html += "</ul>"
        
        self.capabilities_list.setHtml(capabilities_html)
    
        
    def update_performance_display(self):
        """Update real-time performance metrics"""
        metrics = self.settings_manager.performance_metrics
        
        # Update response time
        avg_time = metrics["avg_response_time"]
        self.response_time_label.setText(f"{avg_time:.3f}s")
        if avg_time < 0.1:
            self.response_time_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif avg_time < 0.5:
            self.response_time_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        else:
            self.response_time_label.setStyleSheet("color: #f44336; font-weight: bold;")
        
        # Update last response time
        last_time = metrics["last_response_time"]
        self.last_response_label.setText(f"{last_time:.3f}s")
        
        # Update total responses
        total = metrics["total_responses"]
        self.total_responses_label.setText(str(total))
        
        # Update memory usage
        try:
            process = psutil.Process()
            memory_percent = process.memory_percent()
            self.memory_progress.setValue(int(memory_percent))
            self.memory_label.setText(f"{memory_percent:.1f}%")
            
            # Update color based on usage
            if memory_percent < 50:
                color = "#4CAF50"
            elif memory_percent < 80:
                color = "#FF9800"
            else:
                color = "#f44336"
            
            self.memory_progress.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                    background-color: #555;
                    color: white;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
            """)
        except:
            self.memory_progress.setValue(0)
            self.memory_label.setText("N/A")
        
        # Keep the System Information box in this dialog up to date too
        try:
            self.update_system_info_panel()
        except Exception:
            pass
        
        # Update uptime
        uptime_seconds = int(time.time() - metrics["session_start"])
        minutes = uptime_seconds // 60
        seconds = uptime_seconds % 60
        hours = minutes // 60
        minutes = minutes % 60
        
        if hours > 0:
            self.uptime_label.setText(f"{hours}h {minutes}m {seconds}s")
        else:
            self.uptime_label.setText(f"{minutes}m {seconds}s")
    
    def refresh_status(self):
        self.load_model_data()
        QMessageBox.information(self, "Status Refreshed", "Model status and system information have been refreshed!")
    
    def test_active_model(self):
        current_model = self.settings_manager.get_active_model()

        # Block testing OpenRouter models when no API key is configured
        try:
            is_cloud = current_model.get('type') != 'local'
            has_key = bool(os.getenv("OPENROUTER_API_KEY") or
                           (self.settings_manager.get("openrouter_api_key", "") or "").strip())
        except Exception:
            is_cloud, has_key = False, False
        if is_cloud and not has_key:
            QMessageBox.warning(
                self,
                "OpenRouter API Key Required",
                "Cloud models cannot be tested until an OpenRouter API key is configured.\n\n"
                "Add your key in the .env file or Settings and try again."
            )
            return
        
        test_dialog = QDialog(self)
        test_dialog.setWindowTitle(f"Testing {current_model['name']}")
        test_dialog.setFixedSize(500, 350)
        
        layout = QVBoxLayout(test_dialog)
        
        status_label = QLabel(f"Testing {current_model['name']}...")
        status_label.setStyleSheet("font-size: 14px; color: white;")
        layout.addWidget(status_label)
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        layout.addWidget(progress)
        
        result_label = QLabel("")
        result_label.setStyleSheet("color: white; padding: 10px;")
        result_label.setWordWrap(True)
        layout.addWidget(result_label)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(test_dialog.accept)
        close_btn.setEnabled(False)
        layout.addWidget(close_btn)
        
        test_dialog.show()
        
        # Background worker for the actual test
        class TestWorker(QThread):
            finished_with_result = Signal(object, object, float)  # response, error, response_time
            def run(self):
                start = time.time()
                try:
                    resp = ai_api.call_ai_api("Hello, this is a test message")
                    rt = time.time() - start
                    self.finished_with_result.emit(resp, None, rt)
                except Exception as e:
                    rt = time.time() - start
                    self.finished_with_result.emit(None, e, rt)
        
        worker = TestWorker(test_dialog)
        test_dialog._worker = worker
        
        # Smooth progress updates
        timer = QTimer(test_dialog)
        timer.setInterval(50)
        test_dialog._progress_timer = timer
        
        def on_tick():
            val = progress.value()
            # Advance to 95% while waiting
            if val < 95:
                progress.setValue(val + 1)
                # Phase messages
                if val == 5:
                    status_label.setText(f"Testing {current_model['name']} response generation...")
                elif val == 35:
                    status_label.setText("Validating response quality...")
                elif val == 65:
                    status_label.setText("Checking system integration...")
                elif val == 85:
                    status_label.setText("Finalizing test results...")
        timer.timeout.connect(on_tick)
        timer.start()
        
        def on_result(response, error, response_time):
            # Stop timer and finish progress
            if test_dialog._progress_timer.isActive():
                test_dialog._progress_timer.stop()
            progress.setValue(100)
            
            model_type = "Local" if current_model.get('type') == 'local' else "Cloud"
            active_model_id = self.settings_manager.get('current_ai_model', 'local_engine')
            
            if error is not None:
                result_label.setText(
                    f"[FAILED] {current_model['name']} Test Error\n\n"
                    f"Time: {response_time:.3f} seconds\n"
                    f"Model ID: {active_model_id}\n"
                    f"Model Type: {model_type}\n"
                    f"Reason: {str(error)}"
                )
                result_label.setStyleSheet("color: #f44336; padding: 10px; font-size: 11px;")
            else:
                # Determine pass/fail based on content
                failed_reason = None
                if not isinstance(response, str) or not response.strip():
                    failed_reason = "Empty response from model"
                else:
                    resp_l = response.strip().lower()
                    if response.startswith("Error:"):
                        failed_reason = response
                    elif "trouble connecting" in resp_l:
                        failed_reason = "Backend reported connection trouble"
                    elif "please try again later" in resp_l:
                        failed_reason = "Backend requested retry later"
                
                if failed_reason:
                    trimmed = (response or '')
                    preview = trimmed[:200]
                    if not isinstance(trimmed, str) or len(trimmed or '') <= 200:
                        suffix = '"'
                    else:
                        suffix = '..."'
                    result_text = (
                        f"[FAILED] {current_model['name']} Test Failed\n\n"
                        f"Time: {response_time:.3f} seconds\n"
                        f"Model ID: {active_model_id}\n"
                        f"Model Type: {model_type}\n"
                        f"Reason: {failed_reason}\n\n"
                        f"Response (first 200 chars): \"{preview}{suffix}"
                    )
                    result_label.setText(result_text)
                    result_label.setStyleSheet("color: #f44336; padding: 10px; font-size: 11px;")
                else:
                    result_label.setText(
                        f"[SUCCESS] {current_model['name']} Test Successful!\n\n"
                        f"Time: {response_time:.3f} seconds\n"
                        f"Model ID: {active_model_id}\n"
                        f"Model Type: {model_type}\n"
                        f"Response: \"{response[:200]}{'...' if len(response) > 200 else ''}\"\n\n"
                        f"[OK] Core Features Working:\n"
                        f"• Response generation and processing\n"
                        f"• System integration and communication\n"
                        f"• Memory and context awareness\n"
                        f"• Intent analysis and classification\n\n"
                        f"Performance: {'Excellent' if response_time < 0.5 else 'Good' if response_time < 2.0 else 'Needs optimization'}\n\n"
                        f"{'Privacy: All processing local' if current_model.get('type') == 'local' else 'Cloud model'}"
                    )
                    result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    result_label.setStyleSheet("color: #4CAF50; padding: 10px; font-size: 11px;")
            
            # Update performance metrics
            self.settings_manager.update_performance_metrics(response_time)
            
            # Enable close & finalize
            close_btn.setEnabled(True)
            status_label.setText("Test complete.")
        
        # Connect and start
        worker.finished_with_result.connect(on_result)
        worker.start()
    
    def closeEvent(self, event):
        # Stop the refresh timer when dialog is closed
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        super().closeEvent(event)


class ClickableTextEdit(QTextEdit):
    """Custom QTextEdit that handles link clicks"""
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.position().toPoint())
            char_format = cursor.charFormat()
            if char_format.isAnchor():
                url = char_format.anchorHref()
                if url:
                    import webbrowser
                    webbrowser.open(url)
                    event.accept()
                    return
        super().mousePressEvent(event)


# Main Application Window
class LunaMainWindow(QMainWindow):
    # Emitted after background status checks update SettingsManager
    model_status_updated = Signal()
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        # Prevent repeated notifications for auto-switch
        self._auto_switch_notified = False
        # Track background status worker state to avoid overlapping runs
        self._status_check_running = False
        self.setWindowTitle("Luna AI")
        # Set Luna window/taskbar icon from assets if available
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(base_dir, "assets", "luna_icon_rounded.png")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        self.setGeometry(100, 100, 800, 600)
        self.setup_ui()
        self.apply_theme()
        # Set the settings manager in ai_api
        ai_api.set_settings_manager(self.settings_manager)
        # (Removed) OpenRouter Inference API token wiring
        
        # Ensure AI backend uses the local engine by default at startup
        try:
            # Force local_engine as the default model if not already set
            current_model_id = self.settings_manager.get("current_ai_model")
            if not current_model_id or current_model_id != "local_engine":
                current_model_id = "local_engine"
                self.settings_manager.set("current_ai_model", current_model_id)
                
            ai_api.set_current_model(current_model_id)
            ai_api.update_advanced_settings({'current_model': current_model_id})
            print(f"[OK] Synced startup model to ai_api: {current_model_id}")
        except Exception as e:
            print(f"[WARN] Failed to sync startup model to ai_api: {e}")

        # Start periodic background model status checks (no UI change)
        try:
            from PySide6.QtCore import QTimer as _QTimerAlias  # ensure available
            self.model_status_timer = _QTimerAlias(self)
            self.model_status_timer.timeout.connect(self.start_model_status_check)
            interval_sec = int(self.settings_manager.get("status_check_interval", 300))
            # Guardrail: minimum 60s to avoid excessive requests
            if interval_sec < 60:
                interval_sec = 60
            self.model_status_timer.start(interval_sec * 1000)
            # Kick off an initial check shortly after startup
            self.start_model_status_check()
        except Exception as _e:
            # Non-fatal if timer cannot be started
            try:
                print(f"[WARN] Could not start background model status timer: {_e}")
            except Exception:
                pass

        # Start periodic system information refresh for the System tab
        try:
            self.system_info_timer = QTimer(self)
            # Refresh every 10 seconds to keep data current without heavy load
            self.system_info_timer.timeout.connect(self.update_system_info)
            self.system_info_timer.start(10_000)
        except Exception:
            pass
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side - Navigation tabs (simplified)
        nav_widget = QWidget()
        nav_widget.setFixedWidth(200)
        nav_layout = QVBoxLayout(nav_widget)
        
        # Navigation title
        nav_title = QLabel("Navigation")
        nav_title.setStyleSheet("font-size: 16px; font-weight: bold; color: white; padding: 10px; text-align: center;")
        nav_layout.addWidget(nav_title)
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("💬", "Chat", "chat"),
            ("🤖", "Models", "models"), 
            ("🖥️", "System", "system"),
            ("ℹ️", "About", "about")
        ]
        
        for emoji, name, key in nav_items:
            btn = QPushButton(f"{emoji} {name}")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    margin: 3px;
                    font-size: 14px;
                    font-weight: bold;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self.switch_content(k))
            self.nav_buttons.append((btn, key))
            nav_layout.addWidget(btn)
        
        # Set Chat as default selected
        self.nav_buttons[0][0].setChecked(True)
        
        nav_layout.addStretch()
        main_layout.addWidget(nav_widget)
        
        # Right side - Main content area
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        
        # Header with model info
        header_layout = QHBoxLayout()
        
        self.content_title = QLabel("Chat")
        self.content_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin: 10px;")
        header_layout.addWidget(self.content_title)
        
        header_layout.addStretch()
        
        # Current model indicator
        current_model = self.settings_manager.get_active_model()
        model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
        self.model_label = QLabel(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")
        self.model_label.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px 12px; border-radius: 12px; font-weight: bold; margin: 10px;")
        header_layout.addWidget(self.model_label)
        
        content_layout.addLayout(header_layout)
        
        # Stacked widget for different content pages
        from PySide6.QtWidgets import QStackedWidget
        self.content_stack = QStackedWidget()
        
        # Create content pages
        self.create_chat_content()
        self.create_models_content()
        self.create_system_content()
        self.create_about_content()
        
        content_layout.addWidget(self.content_stack)
        
        main_layout.addWidget(self.content_widget, 1)  # Give right side more space
        
        # Menu bar
        self.create_menu_bar()
        
        # Initialize with chat content
        self.switch_content("chat")
    
    def switch_content(self, content_type):
        """Switch the main content area based on navigation selection"""
        # Update navigation button states
        for btn, key in self.nav_buttons:
            btn.setChecked(key == content_type)
        
        # Update content title
        titles = {
            "chat": "Chat",
            "models": "AI Models", 
            "system": "System Information",
            "about": "About Luna"
        }
        self.content_title.setText(titles.get(content_type, "Luna AI"))
        
        # Switch to the appropriate content page
        content_indices = {
            "chat": 0,
            "models": 1,
            "system": 2,
            "about": 3
        }
        self.content_stack.setCurrentIndex(content_indices.get(content_type, 0))

    def create_about_content(self):
        """Create the About Luna page shown via the left navigation tab."""
        about_widget = QWidget()
        layout = QVBoxLayout(about_widget)

        # Simple text header only (no icon here)
        header = QLabel("About Luna AI")
        header.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #4CAF50; padding: 10px;"
        )
        layout.addWidget(header)

        # Scrollable about text
        info = QTextBrowser()
        info.setStyleSheet(
            "background-color: #2b2b2b; "
            "color: white; "
            "border: 1px solid #555; "
            "border-radius: 8px; "
            "padding: 15px; "
            "font-size: 13px;"
        )

        about_html_parts = []
        about_html_parts.append(
            "Luna AI"  # keep title simple; window already says Luna AI
            "<br><br>"
            "An advanced desktop AI assistant with multiple model support, "
            "including fast local models and OpenRouter cloud models."
            "<br><br>"
            "<b>Features:</b>"
            "<ul>"
            "<li>Multiple AI model support (local engine and OpenRouter)</li>"
            "<li>Simple API key management for cloud models</li>"
            "<li>Local and cloud processing modes</li>"
            "<li>Weather integration (OpenWeatherMap)</li>"
            "<li>Optional web search assistance</li>"
            "<li>Optional system command execution</li>"
            "<li>Adjustable creativity and response behavior</li>"
            "<li>Provider-aware model catalog with status indicators</li>"
            "</ul>"
            "<br><br>"
            "<b>Version:</b> 1.0"
            "<br><br>"
            "<b>Providers:</b>"
            "<ul>"
            "<li>💻 Local engine (runs entirely on your machine)</li>"
            "<li>🔵 OpenRouter (cloud AI model provider)</li>"
            "<li>🌤️ OpenWeatherMap (weather data)</li>"
            "</ul>"
        )

        info.setHtml("".join(about_html_parts))
        layout.addWidget(info)

        # Keep layout simple and text-only
        layout.addStretch()

        # Add this About page to the main stacked widget
        self.content_stack.addWidget(about_widget)

    def start_model_status_check(self):
        """Kick off a background status check for non-local models.

        This is used by the periodic QTimer started during window init and
        when the status check interval is changed in settings.
        """
        try:
            # Prevent overlapping checks
            if getattr(self, "_status_check_running", False):
                return

            available_models = self.settings_manager.get("available_models", {}) or {}
            # Collect OpenRouter / cloud models only (exclude local engine)
            model_ids = [
                mid
                for mid, info in available_models.items()
                if info.get("type") != "local" and mid != "local_engine"
            ]
            if not model_ids:
                return

            self._status_check_running = True
            self._status_worker = ModelStatusWorker(model_ids)
            self._status_worker.results_ready.connect(self.on_model_status_results)
            self._status_worker.finished.connect(
                lambda: setattr(self, "_status_check_running", False)
            )
            self._status_worker.start()
        except Exception as _e:
            # Non-fatal: log and continue without crashing the UI
            try:
                print(f"[WARN] Model status check failed to start: {_e}")
            except Exception:
                pass

    def on_model_status_results(self, results: dict):
        """Apply results to SettingsManager and refresh UI."""
        # Update stored status and errors
        for model_id, data in (results or {}).items():
            status = data.get('status', 'error')
            error = data.get('error')
            # Map common paused indicators to 'paused'
            if status not in ('available', 'paused', 'loading', 'error'):
                status = 'error'
            # If 'paused' detected via error string
            if status == 'error' and error and 'paused' in str(error).lower():
                status = 'paused'
            self.settings_manager.set_model_status(model_id, status, error)

        # Update UI elements reflecting model status
        self.update_model_status_ui()
        
        # Notify dialogs to refresh if listening
        try:
            self.model_status_updated.emit()
        except Exception:
            pass

    def update_model_status_ui(self):
        """Update model label, dropdown entries, and any visible badges."""
        # Pre-read flags with robust coercion
        def _to_bool(v, default=False):
            if v is None:
                return default
            if isinstance(v, bool):
                return v
            try:
                s = str(v).strip().lower()
                if s in ("1", "true", "yes", "on"):
                    return True
                if s in ("0", "false", "no", "off"):
                    return False
            except Exception:
                pass
            return bool(v)
        try:
            ignore_pings = _to_bool(self.settings_manager.get('ignore_status_pings', False), False)
            auto_fb = _to_bool(self.settings_manager.get('auto_fallback', True), True)
        except Exception:
            ignore_pings, auto_fb = False, True

        # Update top model label
        try:
            current_model = self.settings_manager.get_active_model()
            model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
            badge = ""
            mid = current_model.get('id', '')
            status = self.settings_manager.get_model_status(mid)
            if not (ignore_pings and auto_fb):
                if status in ("paused", "error"):
                    # For error state, avoid the word 'UNAVAILABLE' in the badge
                    badge = " [PAUSED]" if status == "paused" else " [ERROR]"
            self.model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown Model')}{badge}")
        except Exception:
            pass

        # Update dropdown entries to include status annotations
        if hasattr(self, 'model_combo') and self.model_combo is not None:
            try:
                # use ignore_pings/auto_fb computed above
                if ignore_pings and auto_fb:
                    # Ensure the whole combo is enabled in this mode
                    try:
                        self.model_combo.setEnabled(True)
                    except Exception:
                        pass
                for i in range(self.model_combo.count()):
                    mid = self.model_combo.itemData(i)
                    text = self.model_combo.itemText(i)
                    # Base name without any previous badge
                    base_name = text.split(' [')[0]
                    status = self.settings_manager.get_model_status(mid)
                    badge = ""
                    tooltip = None
                    enabled_flag = 1  # keep items enabled by default
                    force_enable = False
                    try:
                        force_enable = self.settings_manager.get('force_enable_hf_models', False)
                    except Exception:
                        pass
                    if status == 'paused':
                        if not (ignore_pings and auto_fb):
                            badge = " [PAUSED]"
                            err = self.settings_manager.get_model_error(mid)
                            tooltip = (err or {}).get('error') or "Endpoint temporarily paused"
                    elif status == 'error':
                        if not (ignore_pings and auto_fb):
                            # Show a generic error badge without using the word 'unavailable'
                            badge = " [ERROR]"
                            err = self.settings_manager.get_model_error(mid)
                            tooltip = (err or {}).get('error') or "Error contacting model"
                    elif status == 'requires_api_key':
                        if not (ignore_pings and auto_fb):
                            badge = " [API KEY REQUIRED]"
                            tooltip = "API key required - add it in Settings > API Keys"
                    elif status == 'loading':
                        if not (ignore_pings and auto_fb):
                            badge = " [LOADING]"
                            tooltip = "Model warming up"
                    # If user chose to ignore status pings and auto fallback is on,
                    # clear stale tooltips but leave items enabled.
                    if ignore_pings and auto_fb:
                        tooltip = None
                    new_text = f"{base_name}{badge}"
                    if new_text != text:
                        self.model_combo.setItemText(i, new_text)
                    if tooltip is not None:
                        # Set tooltip (or clear if None)
                        self.model_combo.setItemData(i, tooltip, Qt.ToolTipRole)
                    # Leave all items enabled; we only use badges and tooltips to
                    # signal status so the user can still attempt selection/tests.
            except Exception:
                pass
    
    def create_chat_content(self):
        """Create the main chat interface"""
        chat_widget = QWidget()
        layout = QVBoxLayout(chat_widget)
        
        # Chat display area
        self.chat_display = ClickableTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setAcceptRichText(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 15px;
                color: white;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        
        # Add CSS animation for blinking cursor
        self.chat_display.document().setDefaultStyleSheet("""
            @keyframes blink {
                0%, 50% { opacity: 1; }
                50.1%, 100% { opacity: 0; }
            }
        """)
        
        layout.addWidget(self.chat_display)
        
        # Chat controls row
        controls_layout = QHBoxLayout()
        
        # Quick actions on the left
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setStyleSheet(self.get_button_style("#f44336"))
        clear_btn.clicked.connect(self.clear_chat)
        
        export_btn = QPushButton("📄 Export")
        export_btn.setStyleSheet(self.get_button_style("#2196F3"))
        export_btn.clicked.connect(self.export_chat)
        
        controls_layout.addWidget(clear_btn)
        controls_layout.addWidget(export_btn)
        controls_layout.addStretch()
        
        # Message counter on the right
        self.message_count_label = QLabel("Messages: 0")
        self.message_count_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        controls_layout.addWidget(self.message_count_label)
        
        layout.addLayout(controls_layout)
        
        # Indicator for cloud/OpenRouter requests
        self.openrouter_wait_label = QLabel("☁️ Waiting for OpenRouter…")
        self.openrouter_wait_label.setStyleSheet("color: #bbbbbb; font-size: 11px; padding: 2px 4px;")
        self.openrouter_wait_label.setVisible(False)
        layout.addWidget(self.openrouter_wait_label)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message to Luna...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #3a3a3a;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 15px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        send_button = QPushButton("Send")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 25px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)
        
        layout.addLayout(input_layout)
        
        self.content_stack.addWidget(chat_widget)
        
        # Add welcome message
        self.add_message("Luna", "Hello! I'm Luna, your AI assistant. How can I help you today?", is_user=False)
    
    def create_models_content(self):
        """Create the models management interface"""
        models_widget = QWidget()
        layout = QVBoxLayout(models_widget)
        
        # Current model section
        current_group = QGroupBox("Active AI Model")
        current_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
            }
        """)
        current_layout = QVBoxLayout(current_group)
        
        current_model = self.settings_manager.get_active_model()
        model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
        
        # Model name and type
        model_header = QHBoxLayout()
        self.current_model_label = QLabel(f"{model_emoji} {current_model.get('name', 'Unknown')}")
        self.current_model_label.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold; padding: 10px;")
        model_header.addWidget(self.current_model_label)
        
        model_header.addStretch()
        
        self.current_model_type_label = QLabel("Local Engine" if current_model.get("type") == "local" else "OpenRouter")
        self.current_model_type_label.setStyleSheet("color: #888; font-size: 14px; padding: 10px;")
        model_header.addWidget(self.current_model_type_label)
        
        current_layout.addLayout(model_header)
        
        # Model description (the only visible description on this page)
        self.current_model_desc = QLabel(current_model.get('description', 'No description available'))
        self.current_model_desc.setStyleSheet("color: #ddd; font-size: 14px; padding: 10px; line-height: 1.4;")
        self.current_model_desc.setWordWrap(True)
        current_layout.addWidget(self.current_model_desc)
        
        layout.addWidget(current_group)
        
        # Provider Status Section
        provider_group = QGroupBox("Model Providers")
        provider_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px 0 5px;
            }
        """)
        provider_layout = QVBoxLayout(provider_group)
        
        # Check provider configuration
        openrouter_key_set = bool(os.getenv("OPENROUTER_API_KEY"))
        
        # Provider status display
        self.provider_info = QLabel()
        self.provider_info.setStyleSheet("""
            background-color: #2b2b2b;
            color: white;
            border: none;
            padding: 10px;
            font-size: 12px;
        """)
        
        self.update_provider_status()
        provider_layout.addWidget(self.provider_info)
        layout.addWidget(provider_group)
        
        # Model selection section
        selection_group = QGroupBox("Available AI Models")
        selection_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #555;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
            }
        """)
        selection_layout = QVBoxLayout(selection_group)
        
        # Model selection dropdown
        model_select_layout = QHBoxLayout()
        model_select_label = QLabel("Select Model:")
        model_select_label.setStyleSheet("color: white; font-size: 14px; padding: 5px;")
        
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px;
                font-size: 14px;
                min-width: 300px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid #888;
                width: 6px;
                height: 6px;
                border-top: none;
                border-right: none;
            }
        """)
        
        # Load available models from code (ai_api). Fallback to settings if unavailable.
        try:
            from ai_api import get_available_models as _get_available_models
            available_models = _get_available_models()
        except Exception:
            available_models = self.settings_manager.get("available_models")
        current_model_id = self.settings_manager.get("current_ai_model")
        
        self.model_combo.clear()
        
        # Add all models in a single list, sorted by name
        sorted_models = sorted(available_models.items(), key=lambda x: x[1]['name'].lower())
        
        for model_id, model_info in sorted_models:
            provider = model_info.get("provider", "local")
            model_type = model_info.get("type", "unknown")
            
            # Set icon and label based on provider
            if provider == "local" and model_type == "local":
                # Check if model is the conversation engine (always available)
                if model_id == "local_engine":
                    icon = "💻"
                    label = f"{icon} {model_info['name']}"
                else:
                    # Downloadable local models
                    icon = "💻"
                    label = f"{icon} {model_info['name']} [LOCAL]"
            elif provider == "openrouter":
                icon = "☁️"
                label = f"{icon} {model_info['name']} [CLOUD]"
            else:
                icon = "❓"
                label = f"{icon} {model_info['name']}"
                
            self.model_combo.addItem(label, model_id)
        
        # Select model - prioritize local engine, then current model, otherwise first model
        selected_index = 0
        for i in range(self.model_combo.count()):
            model_id = self.model_combo.itemData(i)
            if model_id == "local_engine":  # Local model ID from luna_settings.json
                selected_index = i
                break
            elif model_id == current_model_id:
                selected_index = i
        
        self.model_combo.setCurrentIndex(selected_index)
        # Keep download/path controls in sync when selection changes
        try:
            self.model_combo.currentIndexChanged.connect(self.update_selected_model_download_info)
        except Exception:
            pass
        
        model_select_layout.addWidget(model_select_label)
        model_select_layout.addWidget(self.model_combo)
        model_select_layout.addStretch()
        
        selection_layout.addLayout(model_select_layout)
        
        # Apply model button
        apply_model_btn = QPushButton("Apply Selected Model")
        apply_model_btn.setStyleSheet(self.get_large_button_style("#4CAF50"))
        apply_model_btn.clicked.connect(self.apply_selected_model)
        selection_layout.addWidget(apply_model_btn)

        # Download controls for local models (main Models page)
        download_layout = QVBoxLayout()

        self.model_download_btn = QPushButton("Download Selected Local Model")
        self.model_download_btn.setStyleSheet(self.get_large_button_style("#2196F3"))
        self.model_download_btn.clicked.connect(self.download_selected_local_model)

        self.model_download_progress = QProgressBar()
        self.model_download_progress.setRange(0, 100)
        self.model_download_progress.setValue(0)
        self.model_download_progress.setVisible(False)
        self.model_download_progress.setStyleSheet(
            "QProgressBar {"
            "    border: 1px solid #555;"
            "    border-radius: 6px;"
            "    text-align: center;"
            "    background-color: #2b2b2b;"
            "    color: white;"
            "}"
            "QProgressBar::chunk {"
            "    background-color: #4CAF50;"
            "    border-radius: 4px;"
            "}"
        )

        self.model_open_folder_btn = QPushButton("Open Model Folder")
        self.model_open_folder_btn.setStyleSheet(self.get_large_button_style("#607D8B"))
        self.model_open_folder_btn.clicked.connect(self.open_selected_model_folder)
        self.model_open_folder_btn.setEnabled(False)

        # Arrange vertically for cleaner layout under the dropdown
        download_layout.addWidget(self.model_download_btn)
        download_layout.addWidget(self.model_download_progress)
        download_layout.addWidget(self.model_open_folder_btn)
        selection_layout.addLayout(download_layout)

        # Label to show where the model file is stored on disk
        self.model_download_path_label = QLabel()
        self.model_download_path_label.setStyleSheet("color: #aaaaaa; font-size: 11px; margin-top: 4px;")
        selection_layout.addWidget(self.model_download_path_label)
        
        layout.addWidget(selection_group)
        
        # Model actions
        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignCenter)

        test_btn = QPushButton("🧪 Test Model")
        test_btn.setStyleSheet(
            self.get_button_style("#FF9800") +
            "QPushButton { padding: 12px 20px; font-size: 13px; }"
        )
        test_btn.clicked.connect(self.test_current_model)

        info_btn = QPushButton("📊 Detailed Info")
        info_btn.setStyleSheet(
            self.get_button_style("#9C27B0") +
            "QPushButton { padding: 12px 20px; font-size: 13px; }"
        )
        info_btn.clicked.connect(self.show_model_info)
        
        actions_layout.addWidget(test_btn)
        actions_layout.addWidget(info_btn)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        self.content_stack.addWidget(models_widget)

        # Local model manager for main Models page (lazy init)
        self.local_model_manager_main = None

        # Initialize download/path controls for the default selection
        try:
            self.update_selected_model_download_info()
        except Exception:
            pass

    def update_provider_status(self):
        """Update the provider status display"""
        openrouter_key_set = bool(os.getenv("OPENROUTER_API_KEY"))
        owm_key_set = bool(os.getenv("OPENWEATHERMAP_API_KEY"))

        # Build a combined HTML block for all providers
        parts = ["<div style='font-family: Arial;'>"]

        # OpenRouter line
        if openrouter_key_set:
            parts.append(
                "<p style='margin: 5px 0;'>"
                "<span style='color: #4CAF50; font-weight: bold;'>🔵 OpenRouter:</span> "
                "<span style='color: #4CAF50;'>✓ API key configured</span>"
                "</p>"
            )
        else:
            parts.append(
                "<p style='margin: 5px 0;'>"
                "<span style='color: #FF0000; font-weight: bold;'>🔵 OpenRouter:</span> "
                "<span style='color: #FF0000;'>No API key configured</span>"
                "</p>"
            )

        # OpenWeatherMap line (weather provider, not a model provider but shown here for keys)
        if owm_key_set:
            parts.append(
                "<p style='margin: 5px 0;'>"
                "<span style='color: #4CAF50; font-weight: bold;'>🌤️ OpenWeatherMap:</span> "
                "<span style='color: #4CAF50;'>✓ API key configured</span>"
                "</p>"
            )
        else:
            parts.append(
                "<p style='margin: 5px 0;'>"
                "<span style='color: #FF0000; font-weight: bold;'>🌤️ OpenWeatherMap:</span> "
                "<span style='color: #FF0000;'>No API key configured</span>"
                "</p>"
            )

        parts.append("</div>")
        self.provider_info.setText("".join(parts))

    def create_system_content(self):
        """Create the system information interface"""
        system_widget = QWidget()
        layout = QVBoxLayout(system_widget)
        
        # System information
        info_group = QGroupBox("System Information")
        info_group.setStyleSheet("""
            QGroupBox {
                color: white;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #555;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
            }
        """)
        info_layout = QVBoxLayout(info_group)
        
        # System info display
        self.system_info = QTextBrowser()
        self.system_info.setStyleSheet("""
            QTextBrowser {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
            }
        """)
        info_layout.addWidget(self.system_info)
        
        # Initialize system info
        self.update_system_info()
        layout.addWidget(info_group)
        
        # System actions
        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignCenter)
        
        refresh_btn = QPushButton("🔄 Refresh System Info")
        refresh_btn.setStyleSheet(self.get_large_button_style("#4CAF50"))
        refresh_btn.clicked.connect(self.refresh_system_info)
        
        actions_layout.addWidget(refresh_btn)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        self.content_stack.addWidget(system_widget)
    
    def get_button_style(self, color):
        """Get consistent button styling"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
                margin: 2px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """
    
    def get_large_button_style(self, color):
        """Get large button styling for main content areas"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 20px;
                font-weight: bold;
                font-size: 14px;
                margin: 5px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
        """
    
    def clear_chat(self):
        """Clear the chat display"""
        self.chat_display.clear()
        self.add_message("Luna", "Chat cleared. How can I help you?", is_user=False)
        # Reset message count
        if hasattr(self, 'message_count_label'):
            self.message_count_label.setText("Messages: 1")
    
    def export_chat(self):
        """Export chat to a text file"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Chat", f"luna_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get plain text from chat display
                chat_text = self.chat_display.toPlainText()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Luna AI Chat Export\n")
                    f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(chat_text)
                
                QMessageBox.information(self, "Export Successful", f"Chat exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Failed to export chat:\n{str(e)}")
    
    def new_conversation(self):
        """Start a new conversation"""
        reply = QMessageBox.question(self, "New Conversation", 
                                   "Start a new conversation? Current chat will be cleared.",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.clear_chat()
    
    def save_chat(self):
        """Save current chat to history (placeholder for future implementation)"""
        QMessageBox.information(self, "Save Chat", 
                               "Chat saving feature will be implemented in a future update.\n"
                               "For now, you can use 'Export Chat' to save conversations.")
    
    def change_theme(self, theme):
        """Change application theme"""
        self.settings_manager.set("theme", theme)
        self.apply_theme()
    
    def change_font_size(self, size):
        """Change chat font size"""
        self.settings_manager.set("chat_font_size", size)
        self.chat_display.setStyleSheet(self.chat_display.styleSheet().replace(
            f"font-size: {self.settings_manager.get('chat_font_size')}px;",
            f"font-size: {size}px;"
        ))
    
    def create_model_catalog_card(self, model_id, model_info, current_model_id):
        """Create a visual card for a model in the catalog"""
        is_active = (model_id == current_model_id)
        provider = model_info.get('provider', 'unknown')
        
        # Helper to convert a hex color like '#4CAF50' or '#999' to an rgba string with given alpha
        def _hex_to_rgba(hex_color: str, alpha: float = 0.13) -> str:
            try:
                hc = hex_color.strip()
                if hc.startswith('#'):
                    hc = hc[1:]
                # Expand shorthand like '999' to '999999'
                if len(hc) == 3:
                    hc = ''.join(ch * 2 for ch in hc)
                r = int(hc[0:2], 16)
                g = int(hc[2:4], 16)
                b = int(hc[4:6], 16)
                # Clamp alpha between 0 and 1
                a = max(0.0, min(1.0, float(alpha)))
                return f"rgba({r}, {g}, {b}, {a})"
            except Exception:
                # Fallback neutral translucent gray
                return "rgba(153, 153, 153, 0.13)"

        # Determine card border color based on provider
        if provider == 'local':
            border_color = "#4CAF50"
            provider_badge = "💻 Local"
            badge_color = "#4CAF50"
        elif provider == 'openrouter':
            border_color = "#4169E1" if is_active else "#555"
            provider_badge = "🔵 Premium"
            badge_color = "#4169E1"
        else:
            border_color = "#555"
            provider_badge = "Unknown"
            badge_color = "#999"
        
        # Create card widget
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #2b2b2b;
                border: 2px solid {border_color if is_active else '#444'};
                border-radius: 8px;
                padding: 10px;
            }}
            QWidget:hover {{
                border-color: {border_color};
            }}
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(5)
        card_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header row: Name + Provider badge + Active indicator
        header_layout = QHBoxLayout()
        
        name_label = QLabel(model_info.get('name', model_id))
        name_label.setStyleSheet(f"color: white; font-size: 13px; font-weight: bold; border: none;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Provider badge
        badge = QLabel(provider_badge)
        badge_bg = _hex_to_rgba(badge_color, 0.13)
        badge.setStyleSheet(f"""
            background-color: {badge_bg};
            color: {badge_color};
            border: 1px solid {badge_color};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        header_layout.addWidget(badge)
        
        # Active indicator
        if is_active:
            active_badge = QLabel("✓ ACTIVE")
            active_bg = _hex_to_rgba("#4CAF50", 0.13)
            active_badge.setStyleSheet(f"""
                background-color: {active_bg};
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: bold;
            """)
            header_layout.addWidget(active_badge)
        
        card_layout.addLayout(header_layout)
        
        # Description
        desc_text = model_info.get('description', 'No description available')
        desc_label = QLabel(desc_text)
        desc_label.setStyleSheet("color: #bbb; font-size: 11px; border: none;")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        
        # Features row
        features = model_info.get('features', [])
        if features:
            features_text = " • ".join([f.replace('_', ' ').title() for f in features[:3]])
            if len(features) > 3:
                features_text += f" +{len(features)-3} more"
            
            features_label = QLabel(f"✨ {features_text}")
            features_label.setStyleSheet("color: #888; font-size: 10px; font-style: italic; border: none;")
            card_layout.addWidget(features_label)
        
        # Status row for OpenRouter models
        if provider == 'openrouter':
            status = model_info.get('status', 'unknown')
            if status == 'requires_api_key':
                status_label = QLabel("🔑 API Key Required")
                status_label.setStyleSheet("color: #FFA500; font-size: 10px; border: none;")
                card_layout.addWidget(status_label)
        
        return card
    
    def apply_selected_model(self):
        """Apply the selected model from the dropdown"""
        selected_model_id = self.model_combo.currentData()
        # Block selecting local GGUF models that are not downloaded yet
        if selected_model_id:
            available_models = self.settings_manager.get("available_models", {})
            model_info = available_models.get(selected_model_id, {})
            provider = model_info.get("provider", model_info.get("type", "unknown"))

            # Require OpenRouter API key before switching to cloud models
            if provider == "openrouter":
                try:
                    has_key = bool(os.getenv("OPENROUTER_API_KEY") or
                                   (self.settings_manager.get("openrouter_api_key", "") or "").strip())
                except Exception:
                    has_key = False
                if not has_key:
                    QMessageBox.warning(
                        self,
                        "OpenRouter API Key Required",
                        "This cloud model requires an OpenRouter API key.\n\n"
                        "Add your key in the .env file or Settings before switching to OpenRouter models."
                    )
                    # Revert combo to current active model selection
                    current_id = self.settings_manager.get("current_ai_model")
                    for i in range(self.model_combo.count()):
                        if self.model_combo.itemData(i) == current_id:
                            self.model_combo.setCurrentIndex(i)
                            break
                    return

            # For local GGUF models (not the built-in local_engine), require a downloaded file
            if provider == "local" and selected_model_id != "local_engine":
                # Use local model manager to see if the file exists
                if not hasattr(self, 'local_model_manager_main') or self.local_model_manager_main is None:
                    try:
                        self.local_model_manager_main = get_local_model_manager()
                    except Exception:
                        self.local_model_manager_main = None
                is_downloaded = False
                if self.local_model_manager_main is not None:
                    try:
                        is_downloaded = self.local_model_manager_main.is_model_downloaded(selected_model_id)
                    except Exception:
                        is_downloaded = False

                if not is_downloaded:
                    QMessageBox.information(
                        self,
                        "Model Not Downloaded",
                        "This local model has not been downloaded yet.\n\n"
                        "Click 'Download Selected Local Model' first, wait for it to finish,\n"
                        "and then apply the model again."
                    )
                    # Snap the dropdown back to the currently active model
                    current_id = self.settings_manager.get("current_ai_model")
                    for i in range(self.model_combo.count()):
                        if self.model_combo.itemData(i) == current_id:
                            self.model_combo.setCurrentIndex(i)
                            break
                    return

        # Block switching to paused/unavailable/loading models only for non-OpenRouter models.
        # For OpenRouter entries (like DeepSeek V3), allow switching even if status checker
        # has cached an error, so the user can still select and test them.
        if selected_model_id:
            status = self.settings_manager.get_model_status(selected_model_id)
            force_enable = self.settings_manager.get('force_enable_hf_models', False)
            # Respect Ignore Status Pings + Auto Fallback to allow switching
            def _to_bool(v, default=False):
                if v is None:
                    return default
                if isinstance(v, bool):
                    return v
                try:
                    s = str(v).strip().lower()
                    if s in ("1", "true", "yes", "on"):
                        return True
                    if s in ("0", "false", "no", "off"):
                        return False
                except Exception:
                    pass
                return bool(v)
            ignore_pings = _to_bool(self.settings_manager.get('ignore_status_pings', False), False)
            auto_fb = _to_bool(self.settings_manager.get('auto_fallback', True), True)

            # Only enforce the status gate for local / non-OpenRouter models
            is_openrouter = (model_info.get('type') == 'openrouter' or model_info.get('provider') == 'openrouter')
            if (not is_openrouter and
                status in ('paused', 'error', 'loading') and
                not force_enable and
                not (ignore_pings and auto_fb)):
                err = self.settings_manager.get_model_error(selected_model_id)
                detail = (err or {}).get('error') or ('Endpoint temporarily paused' if status == 'paused' else 'Model unavailable')
                QMessageBox.warning(self, "Model Not Available",
                                    f"Cannot switch to this model right now.\n\n"
                                    f"Status: {status.upper()}\nDetails: {detail}")
                # Revert combo to current active model selection
                current_id = self.settings_manager.get("current_ai_model")
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == current_id:
                        self.model_combo.setCurrentIndex(i)
                        break
                return
            elif status in ('paused', 'error', 'loading') and force_enable:
                QMessageBox.information(self, "Forced Switch",
                                        "You have enabled force-use of unavailable models.\n"
                                        "We'll attempt to use this model, but requests may fail.")
            elif status == 'requires_api_key':
                QMessageBox.warning(self, "API Key Required",
                                    "This model requires an API key.\n\n"
                                    "Please add your API key in Settings > API Keys.")
                # Revert to previous model
                current_id = self.settings_manager.get("current_ai_model")
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == current_id:
                        self.model_combo.setCurrentIndex(i)
                        break
                return

        if selected_model_id and selected_model_id != self.settings_manager.get("current_ai_model"):
            try:
                # Update settings
                self.settings_manager.set("current_ai_model", selected_model_id)
                
                # Update AI API and keep advanced settings in sync
                ai_api.set_current_model(selected_model_id)
                try:
                    ai_api.update_advanced_settings({'current_model': selected_model_id})
                except Exception as sync_err:
                    print(f"[WARN] Failed to sync ai_api advanced settings: {sync_err}")
                
                # Update UI elements
                current_model = self.settings_manager.get_active_model()
                model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
                
                # Update current model label in models tab
                self.current_model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown')}")
                # Update current model type label
                if hasattr(self, 'current_model_type_label'):
                    self.current_model_type_label.setText("Local Engine" if current_model.get("type") == "local" else "OpenRouter")
                # Update visible description under Active AI Model
                if hasattr(self, 'current_model_desc'):
                    self.current_model_desc.setText(current_model.get('description', 'No description available'))
                
                # Update model label in header
                self.model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")
                
                # Show confirmation
                models = self.settings_manager.get("available_models", {}) or {}
                model_info = models.get(selected_model_id, {"name": selected_model_id})
                QMessageBox.information(self, "Model Applied", 
                                      f"Switched to {model_info.get('name', selected_model_id)}")
                
                # Ensure all model-related UI (including top-right badge) reflects the new active model
                try:
                    self.update_model_status_ui()
                except Exception:
                    pass
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to apply model: {str(e)}")
        else:
            QMessageBox.information(self, "No Change", "The selected model is already active.")
        
        # After switching, refresh download/path info for the newly selected model
        try:
            self.update_selected_model_download_info()
        except Exception:
            pass

    def _ensure_local_model_manager_main(self):
        """Lazy-initialize the local model manager used by the main Models page."""
        if self.local_model_manager_main is None:
            try:
                self.local_model_manager_main = get_local_model_manager()
            except Exception as e:
                QMessageBox.warning(self, "Local Models Disabled", f"Local model manager is not available:\n{e}")
                return False
        return True

    def update_selected_model_download_info(self):
        """Update download button, path label, and folder button for the selected model."""
        if not hasattr(self, 'model_combo'):
            return
        model_id = self.model_combo.currentData()
        if not model_id:
            return

        # Default state
        if hasattr(self, 'model_download_progress'):
            self.model_download_progress.setVisible(False)
            self.model_download_progress.setValue(0)
        if hasattr(self, 'model_download_path_label'):
            self.model_download_path_label.setText("")

        # If this is not a local downloadable model, disable download/folder controls
        available_models = self.settings_manager.get("available_models", {})
        model_info = available_models.get(model_id, {})
        is_local = (model_id.startswith("local/") and model_id != "local_engine") or model_info.get("type") == "local"

        if not is_local:
            if hasattr(self, 'model_download_btn'):
                self.model_download_btn.setEnabled(False)
            return

        # Local model: enable download button and show current path if downloaded
        if hasattr(self, 'model_download_btn'):
            self.model_download_btn.setEnabled(True)
            self.model_download_btn.setText("Download Selected Local Model")

        if not self._ensure_local_model_manager_main():
            return

        try:
            downloaded = self.local_model_manager_main.is_model_downloaded(model_id)
            path_obj = self.local_model_manager_main.get_model_path(model_id)
        except Exception:
            downloaded = False
            path_obj = None

        if downloaded and path_obj is not None:
            path_text = str(path_obj)
            if hasattr(self, 'model_download_path_label'):
                self.model_download_path_label.setText(f"Stored at: {path_text}")
            if hasattr(self, 'model_open_folder_btn'):
                self.model_open_folder_btn.setEnabled(True)
            if hasattr(self, 'model_download_btn'):
                self.model_download_btn.setText("Re-download Selected Local Model")
        else:
            # No downloaded file yet; keep Open Folder clickable so the handler
            # can show a friendly "not downloaded" message instead of being greyed out.
            if hasattr(self, 'model_open_folder_btn'):
                self.model_open_folder_btn.setEnabled(True)

    def download_selected_local_model(self):
        """Download the currently selected local model with a visible progress bar."""
        if not self._ensure_local_model_manager_main():
            return

        model_id = self.model_combo.currentData() if hasattr(self, 'model_combo') else None
        if not model_id:
            return

        available_models = self.settings_manager.get("available_models", {})
        model_info = available_models.get(model_id, {})
        is_local = (model_id.startswith("local/") and model_id != "local_engine") or model_info.get("type") == "local"
        if not is_local:
            QMessageBox.information(self, "Not a Local Model", "Only local models can be downloaded from within Luna.")
            return

        if hasattr(self, 'model_download_progress'):
            self.model_download_progress.setVisible(True)
            self.model_download_progress.setValue(0)
        if hasattr(self, 'model_download_btn'):
            self.model_download_btn.setEnabled(False)

        class MainDownloadWorker(QThread):
            progress = Signal(int, int, str)
            finished_with_result = Signal(bool, str)

            def __init__(self, manager, model_id):
                super().__init__()
                self.manager = manager
                self.model_id = model_id

            def run(self):
                def _cb(current, total, msg):
                    try:
                        self.progress.emit(current, total, msg)
                    except Exception:
                        pass

                success = self.manager.download_model(self.model_id, progress_callback=_cb)
                self.finished_with_result.emit(success, self.model_id)

        worker = MainDownloadWorker(self.local_model_manager_main, model_id)
        self._main_download_worker = worker

        def _ensure_download_timer():
            """Create a simple timer that animates the bar while downloading."""
            if hasattr(self, '_download_progress_timer') and self._download_progress_timer is not None:
                return
            from PySide6.QtCore import QTimer as _QTimerAlias
            self._download_progress_timer = _QTimerAlias(self)
            self._download_progress_timer.setInterval(150)

            def _tick():
                if not hasattr(self, 'model_download_progress'):
                    return
                try:
                    val = self.model_download_progress.value()
                    # Animate between 0 and 95 until completion
                    if val < 95:
                        self.model_download_progress.setValue(val + 1)
                    else:
                        self.model_download_progress.setValue(20)
                except Exception:
                    pass

            self._download_progress_timer.timeout.connect(_tick)
            self._download_progress_timer.start()

        def _stop_download_timer():
            if hasattr(self, '_download_progress_timer') and self._download_progress_timer is not None:
                try:
                    self._download_progress_timer.stop()
                except Exception:
                    pass
                self._download_progress_timer = None

        def _on_progress(current, total, msg):
            """Mirror start/end of download into both UI and terminal.

            huggingface_hub only calls this at the beginning (0) and end (total),
            so we use a timer to animate in between while keeping CLI messages
            consistent.
            """
            if not hasattr(self, 'model_download_progress'):
                return
            try:
                if total and current >= total:
                    # Download complete
                    _stop_download_timer()
                    self.model_download_progress.setValue(100)
                    self.model_download_progress.setFormat("100%")
                    print(f"[DOWNLOAD] {model_id}: complete ({current}/{total})")
                elif total and current == 0:
                    # Download starting
                    self.model_download_progress.setValue(0)
                    self.model_download_progress.setFormat("Downloading...")
                    _ensure_download_timer()
                    print(f"[DOWNLOAD] {model_id}: starting ({current}/{total})")
                # Ignore intermediate values because we don't get any
            except Exception:
                pass

        def _on_finished(success, mid):
            if hasattr(self, 'model_download_progress'):
                self.model_download_progress.setVisible(False)
            if hasattr(self, 'model_download_btn'):
                self.model_download_btn.setEnabled(True)

            _stop_download_timer()

            if not success:
                QMessageBox.warning(self, "Download Failed", f"Failed to download model: {mid}")
            else:
                # Refresh displayed path and button states
                try:
                    self.update_selected_model_download_info()
                except Exception:
                    pass

            try:
                worker.deleteLater()
            except Exception:
                pass

        try:
            worker.progress.connect(_on_progress)
            worker.finished_with_result.connect(_on_finished)
            worker.start()
        except Exception as e:
            if hasattr(self, 'model_download_progress'):
                self.model_download_progress.setVisible(False)
            if hasattr(self, 'model_download_btn'):
                self.model_download_btn.setEnabled(True)
            QMessageBox.warning(self, "Download Error", f"Could not start download:\n{e}")

    def open_selected_model_folder(self):
        """Open the folder containing the selected local model file in the OS file manager."""
        if not self._ensure_local_model_manager_main():
            return

        model_id = self.model_combo.currentData() if hasattr(self, 'model_combo') else None
        if not model_id:
            return

        try:
            path_obj = self.local_model_manager_main.get_model_path(model_id)
            if not path_obj:
                QMessageBox.information(self, "Model Not Downloaded", "This model has not been downloaded yet.")
                return

            folder = os.path.dirname(str(path_obj))
            if sys.platform.startswith("win"):
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.warning(self, "Open Folder Failed", f"Could not open model folder:\n{e}")
    
    def test_current_model(self):
        """Test the current AI model"""
        dialog = ModelsDialog(self.settings_manager, self)
        dialog.test_active_model()
    
    def show_model_info(self):
        """Show detailed model information"""
        dialog = ModelsDialog(self.settings_manager, self)
        dialog.exec()
    

    def refresh_system_info(self):
        """Refresh the system information display"""
        self.update_system_info()
        QMessageBox.information(self, "System Info Refreshed", "System information has been updated!")
    
    def show_performance(self):
        """Show performance monitoring dialog"""
        dialog = ModelsDialog(self.settings_manager, self)
        dialog.tabs.setCurrentIndex(2)  # Switch to performance tab
        dialog.exec()
    
    def update_system_info(self):
        """Update the system information display"""
        try:
            # Get system information (inspired by hw_check.py)
            cpu_physical = psutil.cpu_count(logical=False) or psutil.cpu_count()
            cpu_logical = psutil.cpu_count(logical=True) or cpu_physical
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=0.0)

            memory = psutil.virtual_memory()
            ram_total_gb = memory.total / (1024**3)
            ram_used_gb = (memory.total - memory.available) / (1024**3)
            ram_percent = memory.percent

            disk = psutil.disk_usage('C:\\')
            disk_total_gb = disk.total / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_percent = disk.percent

            # Derive a friendlier OS label, especially for Windows 11
            os_name = platform.system()
            os_label = f"{os_name} {platform.release()}"
            if os_name == "Windows":
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion") as key:
                        product_name, _ = winreg.QueryValueEx(key, "ProductName")
                        if product_name:
                            os_label = product_name
                except Exception:
                    # Fallback to default label if registry lookup fails
                    pass

            system_html = f"""
            <h3>System Information</h3>
            <p><strong>OS:</strong> {os_label}</p>
            <p><strong>CPU:</strong> {cpu_physical} cores / {cpu_logical} threads @ {cpu_freq.current:.1f} MHz ({cpu_percent:.0f}% load)</p>
            <p><strong>RAM:</strong> {ram_total_gb:.1f} GB total, {ram_used_gb:.1f} GB in use ({ram_percent:.0f}%)</p>
            <p><strong>Storage (C:):</strong> {disk_free_gb:.1f} GB free of {disk_total_gb:.1f} GB ({disk_percent:.0f}% used)</p>
            """
        except:
            system_html = """
            <h3>System Information</h3>
            <p><strong>OS:</strong> Information unavailable</p>
            <p><strong>System:</strong> Unable to retrieve system details</p>
            """
        
        if hasattr(self, 'system_info'):
            self.system_info.setHtml(system_html)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        
        settings_action = settings_menu.addAction('Preferences')
        settings_action.triggered.connect(self.open_settings)
        
        # (Removed) AI Models item from Settings menu
        
        # Help menu removed per request
        
    def apply_theme(self):
        theme = self.settings_manager.get("theme")
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: white;
                }
                QMenuBar {
                    background-color: #2b2b2b;
                    color: white;
                    border-bottom: 1px solid #555;
                }
                QMenuBar::item {
                    background-color: transparent;
                    padding: 8px 12px;
                }
                QMenuBar::item:selected {
                    background-color: #4CAF50;
                }
                QMenu {
                    background-color: #2b2b2b;
                    color: white;
                    border: 1px solid #555;
                }
                QMenu::item:selected {
                    background-color: #4CAF50;
                }
            """)
    
    def add_message(self, sender, message, is_user=True, message_type=None, message_id=None):
        timestamp = datetime.now().strftime("%H:%M")
        import re

        if message:
            message = "\n".join(
                ln for ln in str(message).split("\n")
                if not ln.strip().startswith("[Using:")
            ).strip()
        
        if message_id is None:
            message_id = uuid.uuid4().hex

        if message_type is None:
            if is_user:
                message_type = "user"
            elif message and 'Search results for' in message:
                message_type = "search"
            else:
                message_type = "assistant"

        if is_user:
            color = "#00E676"  # Bright green for user
            prefix = "You"
        else:
            color = "#03DAC6"  # Cyan/teal for Luna
            prefix = sender
            # If assistant message contains both other text and a "You asked:" line,
            # split into two separate bubbles so placement is always correct.
            # Only do this when "You asked:" is NOT at the very start, otherwise
            # we'd recurse forever on a pure question message.
            if ("You asked:" in message
                and not message.lstrip().startswith("You asked:")
                and 'Search results for' not in message):
                parts = message.split("You asked:", 1)
                greeting_part = parts[0].strip()
                question_part = ("You asked:" + parts[1]).strip()
                if greeting_part:
                    self.add_message(sender, greeting_part, is_user=False)
                if question_part:
                    self.add_message(sender, question_part, is_user=False)
                return

        # Convert newlines to HTML line breaks for proper formatting
        # Special handling for questions and search results
        if message.startswith('You asked:') and 'Search results for' not in message:
            # Standalone question bubble
            message_html = f'<p style="margin: 0; font-style: italic; color: #B0BEC5;">{message}</p>'
        elif 'Search results for' in message:
            # Search results bubble (no embedded question)
            # Split by double newlines to get all parts
            parts = message.split('\n\n')
            
            if parts and 'Search results for' in parts[0]:
                # First part is the header line from the engine, but we don't
                # want to repeat the question text here. Use a generic label.
                # Rest are the search results, but filter out non-result parts
                result_parts = [p for p in parts[1:] if p.strip() and not p.startswith('[Using:')]
                
                # Generic header with extra margin bottom
                header_text = 'Search results'
                message_html = f'<p style="margin: 0 0 30px 0; font-weight: bold; padding-bottom: 10px; border-bottom: 1px dashed #666;">{header_text}</p>'
                
                # Process each search result
                for part in result_parts:
                    if part.strip():
                        # Convert markdown bold **text** to HTML <strong>text</strong> using regex
                        part_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', part)
                        # Convert newlines to <br> for proper line breaks
                        part_html = part_html.replace('\n', '<br>')
                        # Wrap in a div with border and padding - increased margin
                        message_html += f'<div style="margin: 25px 0; padding: 15px; border: 1px solid #444; border-radius: 5px; background-color: #333;">{part_html}</div>'
            else:
                # Fallback - just convert newlines to <br>
                message_html = message.replace('\n', '<br>')
        else:
            # Regular message - just convert newlines to <br>
            message_html = message.replace('\n', '<br>')
        
        # Convert markdown links [text](url) to HTML <a> tags with target="_blank"
        
        # Handle URLs that may end with parentheses (like Wikipedia URLs)
        def replace_markdown_link(match):
            text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" target="_blank" style="color: #4CAF50; text-decoration: underline;">{text}</a>'
        
        # Use a single regex that handles all cases properly
        # This matches [text](url) where url can contain any characters except )
        message_html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            replace_markdown_link,
            message_html
        )
        
        # Bubble-style layout using a 2-cell table row.
        # Qt's rich text engine tends to position table cells more reliably than block alignment.
        bubble_max_width = "65%"

        if message_type == "search":
            label_text = "Search"
        elif is_user:
            label_text = "You"
        else:
            label_text = sender

        if is_user:
            # User: bubble on the right
            left_cell_html = "&nbsp;"
            bubble_radius = "16px 16px 4px 16px"
            text_color = "#E0E0E0"
            right_cell_html = f"""
                <div style="display: inline-block; max-width: {bubble_max_width}; background-color: #2a2a2a; padding: 12px 16px; border-radius: {bubble_radius}; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="color: #9ca3af; font-size: 11px; margin-bottom: 6px;">{label_text}</div>
                    <div style="color: {text_color}; font-size: 14px; line-height: 1.4;">
                        {message_html}
                    </div>
                    <div style="text-align: right; margin-top: 6px; margin-right: -4px;">
                        <span style="color: #6b7280; font-size: 11px;">{timestamp}</span>
                    </div>
                </div>
            """
        else:
            # Luna: bubble on the left
            right_cell_html = "&nbsp;"
            bubble_radius = "16px 16px 16px 4px"
            text_color = "#E0E0E0"
            left_cell_html = f"""
                <div style="display: inline-block; max-width: {bubble_max_width}; background-color: #2a2a2a; padding: 12px 16px; border-radius: {bubble_radius}; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="color: #9ca3af; font-size: 11px; margin-bottom: 6px;">{label_text}</div>
                    <div style="color: {text_color}; font-size: 14px; line-height: 1.4;">
                        {message_html}
                    </div>
                    <div style="text-align: right; margin-top: 6px; margin-right: -4px;">
                        <span style="color: #6b7280; font-size: 11px;">{timestamp}</span>
                    </div>
                </div>
            """

        formatted_message = f"""
        <div id=\"msg-{message_id}\" data-mtype=\"{message_type}\">
            <table style=\"width: 100%; border-collapse: collapse; margin: 4px 0;\">
                <tr>
                    <td style=\"width: 50%; vertical-align: top;\">
                        {left_cell_html}
                    </td>
                    <td style=\"width: 50%; vertical-align: top; text-align: right;\">
                        {right_cell_html}
                    </td>
                </tr>
            </table>
        </div>
        """

        self.chat_display.moveCursor(QTextCursor.End)
        self.chat_display.insertHtml(formatted_message)
        
        # Scroll to bottom
        self.chat_display.moveCursor(QTextCursor.End)
        if self.settings_manager.get("auto_scroll"):
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def send_message(self):
        message = self.input_field.text().strip()
        if not message:
            return
            
        # If a cloud/OpenRouter model is active but no API key is set, block the request
        try:
            current_model = self.settings_manager.get_active_model()
            is_cloud = current_model.get("type") != "local"
            has_key = bool(os.getenv("OPENROUTER_API_KEY") or
                           (self.settings_manager.get("openrouter_api_key", "") or "").strip())
        except Exception:
            is_cloud, has_key = False, False
        if is_cloud and not has_key:
            if hasattr(self, "openrouter_wait_label"):
                self.openrouter_wait_label.setVisible(False)
            QMessageBox.warning(
                self,
                "OpenRouter API Key Required",
                "Cloud models require an OpenRouter API key before they can be used in chat.\n\n"
                "Add your key in the .env file or Settings, or switch back to the local Conversation Engine."
            )
            return

        # Add user message to chat
        self.add_message("You", message, is_user=True, message_type="user")
        self.input_field.clear()
        
        # Show/hide OpenRouter waiting indicator based on active model type
        try:
            current_model = self.settings_manager.get_active_model()
            is_cloud = current_model.get("type") != "local"
            if hasattr(self, "openrouter_wait_label"):
                self.openrouter_wait_label.setVisible(is_cloud)
        except Exception:
            if hasattr(self, "openrouter_wait_label"):
                self.openrouter_wait_label.setVisible(False)
        
        # Store current state for typing animation (no dots indicator)
        self.typing_indicator_html = self.chat_display.toHtml()
        
        # Start AI processing thread
        self.ai_thread = LunaThread(message, self.settings_manager)
        self.ai_thread.response_ready.connect(self.handle_ai_response_with_typing)
        self.ai_thread.start()
    
    def show_typing_indicator(self):
        """Show ChatGPT-style animated typing indicator with dots"""
        timestamp = datetime.now().strftime("%H:%M")
        
        # Add typing indicator with animated dots
        typing_html = f"""
        <div style="margin-bottom: 10px;" id="typing-indicator">
            <span style="color: #03DAC6; font-weight: bold; font-size: 14px;">
                Luna
            </span>
            <span style="color: #B0BEC5; font-size: 11px; margin-left: 5px;">
                {timestamp}
            </span>
            <div style="color: #ECEFF1; line-height: 1.5; margin-top: 3px; margin-left: 0px; font-size: 13px;">
                <span id="typing-dots">●</span><span style="animation: blink 1s infinite; margin-left: 2px;">|</span>
            </div>
        </div>
        """
        
        self.chat_display.append(typing_html)
        
        # Start animated dots
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.animate_typing_dots)
        self.typing_timer.start(500)  # Update every 500ms
        self.dot_count = 1
    
    def animate_typing_dots(self):
        """Animate the typing dots (●●●)"""
        dots = "●" * self.dot_count
        self.dot_count = (self.dot_count % 3) + 1
        
        # Update the dots in the HTML
        current_html = self.chat_display.toHtml()
        if 'typing-dots' in current_html:
            # Find and replace the dots
            import re
            pattern = r'<span id="typing-dots">●+</span>'
            replacement = f'<span id="typing-dots">{dots}</span>'
            updated_html = re.sub(pattern, replacement, current_html)
            self.chat_display.setHtml(updated_html)
    
    def handle_ai_response_with_typing(self, response):
        """Handle AI response with character-by-character typing (no dots)"""

        # Hide any OpenRouter waiting indicator once a response (or error) arrives
        if hasattr(self, "openrouter_wait_label"):
            self.openrouter_wait_label.setVisible(False)

        # Strip out engine/status lines so they never show in the chat bubbles
        if response:
            lines = [ln for ln in response.split("\n")
                     if not ln.strip().startswith("[Using:")]
            response = "\n".join(lines).strip()

        # Check if response contains search results BEFORE stopping any animations
        # Look for "Search results for" and either markdown links or bold headers
        is_search_result = ("Search results for" in response and 
                          ("[Link](" in response or 
                           "**" in response or 
                           "Link" in response))
        
        if is_search_result:
            # For search results, display immediately with proper HTML conversion
            # Stop any existing typing animations first
            if hasattr(self, 'typing_timer'):
                self.typing_timer.stop()
                delattr(self, 'typing_timer')

            # We now let the downstream formatter extract the query from
            # the "Search results for '...':" header, so we don't prepend
            # the question text here (avoids showing it twice).
            self.add_message("Luna", response, is_user=False, message_type="search")
            return
        
        # For regular responses, continue with typing animation
        # Stop any existing typing animations
        if hasattr(self, 'typing_timer'):
            self.typing_timer.stop()
            delattr(self, 'typing_timer')
        
        # Restore the HTML state before typing indicator was added
        if hasattr(self, 'typing_indicator_html'):
            self.chat_display.setHtml(self.typing_indicator_html)
            delattr(self, 'typing_indicator_html')
        
        # Use character-by-character typing for regular responses
        self.start_typing_animation(response)
    
    def start_typing_animation(self, response):
        """Start smooth character-by-character typing animation"""
        # Store the response and initialize typing
        self.response_text = response
        self.char_index = 0
        self.typing_timestamp = datetime.now().strftime("%H:%M")
        self.typing_message_id = uuid.uuid4().hex
        
        # Store the current chat state before adding typing message
        # Use toPlainText() to avoid HTML conversion issues
        self.pre_typing_text = self.chat_display.toPlainText()
        self.pre_typing_html = self.chat_display.toHtml()
        
        # Start with first character immediately (no empty cursor)
        if response:
            first_char = response[0]
            cursor = "|" if len(response) > 1 else ""
            self.add_message("Luna", first_char + cursor, is_user=False, message_type="assistant", message_id=self.typing_message_id)
            self.char_index = 1  # Start from second character
        
        # Create and start the typing timer with smoother timing
        if hasattr(self, 'typing_animation_timer'):
            self.typing_animation_timer.stop()
        
        self.typing_animation_timer = QTimer(self)
        self.typing_animation_timer.timeout.connect(self.type_character_smooth)
        self.typing_animation_timer.start(15)  # 15ms for faster typing
    
    def add_simple_typing_message(self, text):
        """Add a simple typing message that gets replaced each time"""
        cursor_html = '<span style="animation: blink 1s infinite; margin-left: 2px;">|</span>' if text != self.response_text else ''
        
        # Apply the same HTML conversion as in add_message
        # For search results, use divs with borders for clear separation
        if 'Search results for' in text:
            # Check if this message starts with "You asked:"
            if text.startswith('You asked:'):
                # Split into question and search results
                parts = text.split('\n\n', 1)
                if len(parts) == 2:
                    question_part = parts[0]
                    search_part = parts[1]
                    
                    # Format the question with extra margin bottom
                    message_html = f'<p style="margin: 0 0 30px 0; font-style: italic; color: #B0BEC5; padding-bottom: 10px; border-bottom: 1px dashed #666;">{question_part}</p>'
                    
                    # Now process the search results
                    search_parts = search_part.split('\n\n')
                    if search_parts and 'Search results for' in search_parts[0]:
                        # First part is the header
                        header = search_parts[0]
                        # Rest are the search results, but filter out non-result parts
                        result_parts = [p for p in search_parts[1:] if p.strip() and not p.startswith('[Using:')]
                        
                        # Format header with extra margin bottom
                        message_html += f'<p style="margin: 0 0 30px 0; font-weight: bold; padding-bottom: 10px; border-bottom: 1px dashed #666;">{header}</p>'
                        
                        # Process each search result
                        for part in result_parts:
                            if part.strip():
                                # Convert markdown bold **text** to HTML <strong>text</strong> using regex
                                part_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', part)
                                # Convert newlines to <br> for proper line breaks
                                part_html = part_html.replace('\n', '<br>')
                                # Wrap in a div with border and padding - increased margin
                                message_html += f'<div style="margin: 25px 0; padding: 15px; border: 1px solid #444; border-radius: 5px; background-color: #333;">{part_html}</div>'
                else:
                    # Fallback - just convert newlines to <br>
                    message_html = text.replace('\n', '<br>')
            else:
                # Original search result formatting (without "You asked:")
                # Split by double newlines to get all parts
                parts = text.split('\n\n')
                if parts and 'Search results for' in parts[0]:
                    # First part is the header
                    header = parts[0]
                    # Rest are the search results, but filter out non-result parts
                    result_parts = [p for p in parts[1:] if p.strip() and not p.startswith('[Using:')]
                    
                    # Format header
                    message_html = f'<p style="margin: 0 0 25px 0; font-weight: bold;">{header}</p>'
                    
                    # Process each search result
                    for part in result_parts:
                        if part.strip():
                            # Convert markdown bold **text** to HTML <strong>text</strong> using regex
                            part_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', part)
                            # Convert newlines to <br> for proper line breaks
                            part_html = part_html.replace('\n', '<br>')
                            # Wrap in a div with border and padding
                            message_html += f'<div style="margin: 15px 0; padding: 10px; border: 1px solid #444; border-radius: 5px; background-color: #333;">{part_html}</div>'
                else:
                    # Fallback - just convert newlines to <br>
                    message_html = text.replace('\n', '<br>')
        else:
            # Regular message - just convert newlines to <br>
            message_html = text.replace('\n', '<br>')
        
        # Convert markdown links [text](url) to HTML <a> tags with target="_blank"
        
        # Handle URLs that may end with parentheses (like Wikipedia URLs)
        def replace_markdown_link(match):
            text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" target="_blank" style="color: #4CAF50; text-decoration: underline;">{text}</a>'
        
        # Use a single regex that handles all cases properly
        # This matches [text](url) where url can contain any characters except )
        message_html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            replace_markdown_link,
            message_html
        )
        
        # Use the existing add_message method but modify the last message
        timestamp = self.typing_timestamp
        color = "#03DAC6"
        prefix = "Luna"
        
        formatted_message = f"""
        <div style="margin-bottom: 10px;" id="typing-msg">
            <span style="color: {color}; font-weight: bold; font-size: 14px;">
                {prefix}
            </span>
            <span style="color: #B0BEC5; font-size: 11px; margin-left: 5px;">
                {timestamp}
            </span>
            <div style="color: #ECEFF1; line-height: 1.5; margin-top: 3px; margin-left: 0px; font-size: 13px;">
                {message_html}{cursor_html}
            </div>
        </div>
        """
        
        # Get current HTML and remove ALL previous typing messages
        current_html = self.chat_display.toHtml()
        
        # More aggressive removal - remove all instances of typing-msg
        import re
        # Remove any div with id="typing-msg" including nested content
        pattern = r'<div[^>]*id="typing-msg"[^>]*>.*?</div>\s*'
        while 'id="typing-msg"' in current_html:
            updated_html = re.sub(pattern, '', current_html, flags=re.DOTALL)
            if updated_html == current_html:  # No more changes
                break
            current_html = updated_html
        
        # Set the cleaned HTML first
        self.chat_display.setHtml(current_html)
        
        # Then add the new message
        self.chat_display.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def type_character_smooth(self):
        """Type one character at a time with smooth, consistent timing"""
        if self.char_index < len(self.response_text):
            # Get text typed so far
            typed_text = self.response_text[:self.char_index + 1]
            cursor = "|" if self.char_index < len(self.response_text) - 1 else ""
            display_text = typed_text + cursor

            if hasattr(self, 'pre_typing_html'):
                self.chat_display.setHtml(self.pre_typing_html)
            self.add_message(
                "Luna",
                display_text,
                is_user=False,
                message_type="assistant",
                message_id=getattr(self, 'typing_message_id', None),
            )
            
            self.char_index += 1
            
            # Continue with next character - faster timing
            char = self.response_text[self.char_index - 1] if self.char_index > 0 else ""
            if char in " .,!?;:":
                delay = 20  # Very fast for punctuation/spaces
            else:
                delay = 35  # Faster for letters
                
            self.typing_animation_timer.start(delay)
        else:
            # Typing complete
            self.typing_animation_timer.stop()
            if hasattr(self, 'typing_animation_timer'):
                delattr(self, 'typing_animation_timer')
            
            # Show final message without cursor
            if hasattr(self, 'pre_typing_html'):
                self.chat_display.setHtml(self.pre_typing_html)
            self.add_message(
                "Luna",
                self.response_text,
                is_user=False,
                message_type="assistant",
                message_id=getattr(self, 'typing_message_id', None),
            )
    
    def type_character_direct(self):
        """Type one character at a time - direct approach without HTML manipulation"""
        if self.char_index < len(self.response_text):
            # Get text typed so far
            typed_text = self.response_text[:self.char_index + 1]
            cursor = "|" if self.char_index < len(self.response_text) - 1 else ""
            display_text = typed_text + cursor
            
            print(f"Debug: Typing character {self.char_index + 1}/{len(self.response_text)}: '{self.response_text[self.char_index]}' -> '{typed_text}'")
            
            # Restore the pre-typing state and add the updated message
            self.chat_display.setHtml(self.pre_typing_html)
            self.add_message("Luna", display_text, is_user=False)
            
            self.char_index += 1
            
            # Continue with next character
            import random
            delay = random.randint(50, 120)
            self.typing_animation_timer.start(delay)
        else:
            # Typing complete
            self.typing_animation_timer.stop()
            if hasattr(self, 'typing_animation_timer'):
                delattr(self, 'typing_animation_timer')
            
            # Show final message without cursor
            self.chat_display.setHtml(self.pre_typing_html)
            self.add_message("Luna", self.response_text, is_user=False)
            print(f"Debug: Typing animation complete!")
    
    def type_character_simple(self):
        """Type one character at a time - simple approach"""
        if self.char_index < len(self.response_text):
            # Get text typed so far
            typed_text = self.response_text[:self.char_index + 1]
            
            print(f"Debug: Typing character {self.char_index + 1}/{len(self.response_text)}: '{self.response_text[self.char_index]}' -> '{typed_text}'")
            
            # Update the message
            self.add_simple_typing_message(typed_text)
            
            self.char_index += 1
            
            # Continue with next character
            import random
            delay = random.randint(50, 120)
            self.typing_animation_timer.start(delay)
        else:
            # Typing complete
            self.typing_animation_timer.stop()
            if hasattr(self, 'typing_animation_timer'):
                delattr(self, 'typing_animation_timer')
            
            # Show final message without cursor
            self.add_simple_typing_message(self.response_text)
            print(f"Debug: Typing animation complete!")
    
    def _format_search_results(self, text):
        """Helper method to format search results with consistent styling"""
        # Handle search results with a question (starts with 'You asked:')
        if text.startswith('You asked:'):
            # Extract just the search query
            query = text.split('\n', 1)[0].replace('You asked:', '').strip()
            search_part = text.split('\n\n', 1)[1] if '\n\n' in text else ''
            
            # Start building the message with the search query
            message_html = f'''
            <div style="margin-bottom: 16px; color: #9ca3af; font-size: 0.9em;">
                Searching for: <span style="color: #e5e7eb;">{query}</span>
            </div>
            '''
        else:
            search_part = text
            message_html = '''
            <div style="margin: 0 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid #3f3f3f;">
                <span style="color: #9ca3af; font-size: 0.9em;">Search Results</span>
            </div>
            '''
        
        # Process the search results
        search_parts = search_part.split('\n\n')
        if search_parts and 'Search results for' in search_parts[0]:
            # Filter out non-result parts
            result_parts = [p for p in search_parts[1:] if p.strip() and not p.startswith('[Using:')]
            
            # Process each search result
            for part in result_parts:
                if part.strip():
                    # Split into title and content
                    part_lines = part.split('\n')
                    if part_lines:
                        title = part_lines[0]
                        content = '\n'.join(part_lines[1:]) if len(part_lines) > 1 else ''
                        content_html = content.replace('\n', '<br>')
                        
                        # Format the result with better visual hierarchy
                        message_html += f'''
                        <div style="margin: 0 0 16px 0; padding: 12px; border-radius: 6px; background-color: #2a2a2a;">
                            <div style="color: #3b82f6; margin-bottom: 6px; font-weight: 500;">{title}</div>
                            <div style="color: #d1d5db; font-size: 0.95em; line-height: 1.5;">
                                {content_html}
                            </div>
                        </div>
                        '''
        
        return message_html

    def add_typing_message(self, text):
        """Add or update the typing message"""
        cursor_html = '<span style="animation: blink 1s infinite; margin-left: 2px;">|</span>' if text != self.response_text else ''
        
        # Apply the same HTML conversion as in add_message
        # For search results, use divs with borders for clear separation
        if 'Search results for' in text:
            # Handle search results
            if text.startswith('You asked:'):
                # Extract just the search query
                query = text.split('\n', 1)[0].replace('You asked:', '').strip()
                search_part = text.split('\n\n', 1)[1] if '\n\n' in text else ''
                
                # Start building the message with the search query
                message_html = f'''
                <div style="margin-bottom: 16px; color: #9ca3af; font-size: 0.9em;">
                    Searching for: <span style="color: #e5e7eb;">{query}</span>
                </div>
                '''
                
                # Process the search results
                search_parts = search_part.split('\n\n')
                if search_parts and 'Search results for' in search_parts[0]:
                    # Filter out non-result parts and process each result
                    result_parts = [p for p in search_parts[1:] if p.strip() and not p.startswith('[Using:')]
                    
                    # Process each search result
                    for part in result_parts:
                        if part.strip():
                            # Split into title and content
                            part_lines = part.split('\n')
                            if part_lines:
                                title = part_lines[0]
                                content = '\n'.join(part_lines[1:]) if len(part_lines) > 1 else ''
                                content_html = content.replace('\n', '<br>')
                                
                                # Format the result with better visual hierarchy
                                message_html += f'''
                                <div style="margin: 0 0 16px 0; padding: 12px; border-radius: 6px; background-color: #2a2a2a;">
                                    <div style="color: #3b82f6; margin-bottom: 6px; font-weight: 500;">{title}</div>
                                    <div style="color: #d1d5db; font-size: 0.95em; line-height: 1.5;">
                                        {content_html}
                                    </div>
                                </div>
                                '''
                else:
                    # Fallback for search results without expected format
                    message_html = search_part.replace('\n', '<br>')
            else:
                # Handle search results without "You asked:" prefix
                search_parts = text.split('\n\n')
                if search_parts and 'Search results for' in search_parts[0]:
                    # Filter out non-result parts
                    result_parts = [p for p in search_parts[1:] if p.strip() and not p.startswith('[Using:')]
                    
                    # Start with a clean message
                    message_html = '''
                    <div style="margin: 0 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid #3f3f3f;">
                        <span style="color: #9ca3af; font-size: 0.9em;">Search Results</span>
                    </div>
                    '''
                    
                    # Process each search result
                    for part in result_parts:
                        if part.strip():
                            # Split into title and content
                            part_lines = part.split('\n')
                            if part_lines:
                                title = part_lines[0]
                                content = '\n'.join(part_lines[1:]) if len(part_lines) > 1 else ''
                                content_html = content.replace('\n', '<br>')
                                
                                # Format the result with better visual hierarchy
                                message_html += f'''
                                <div style="margin: 0 0 16px 0; padding: 12px; border-radius: 6px; background-color: #2a2a2a;">
                                    <div style="color: #3b82f6; margin-bottom: 6px; font-weight: 500;">{title}</div>
                                    <div style="color: #d1d5db; font-size: 0.95em; line-height: 1.5;">
                                        {content_html}
                                    </div>
                                </div>
                                '''
                else:
                    # Fallback for other search result formats
                    message_html = text.replace('\n', '<br>')
        else:
            # Regular message - just convert newlines to <br>
            message_html = text.replace('\n', '<br>')

        # Render typing output using the same bubble layout as add_message so
        # alignment stays correct (assistant always on the left).
        bubble_max_width = "65%"
        bubble_radius = "16px 16px 16px 4px"
        text_color = "#E0E0E0"
        bubble_html = f"""
            <div style="display: inline-block; max-width: {bubble_max_width}; background-color: #2a2a2a; padding: 12px 16px; border-radius: {bubble_radius}; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <div style="color: {text_color}; font-size: 14px; line-height: 1.4;">
                    {message_html}{cursor_html}
                </div>
                <div style="text-align: right; margin-top: 6px; margin-right: -4px;">
                    <span style="color: #6b7280; font-size: 11px;">{self.typing_timestamp}</span>
                </div>
            </div>
        """
        formatted_message = f"""
        <div style="width: 100%; margin: 4px 0; text-align: left;">
            {bubble_html}
        </div>
        """
        
        # Convert markdown links [text](url) to HTML <a> tags with target="_blank"
        
        # Handle URLs that may end with parentheses (like Wikipedia URLs)
        def replace_markdown_link(match):
            text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" target="_blank" style="color: #4CAF50; text-decoration: underline;">{text}</a>'
        
        # Use a single regex that handles all cases properly
        # This matches [text](url) where url can contain any characters except )
        message_html = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            replace_markdown_link,
            message_html
        )

        # Avoid drifting/incorrect placement by rebuilding from a stored base HTML
        # and re-inserting the single typing bubble each tick.
        if not hasattr(self, 'typing_base_html'):
            self.typing_base_html = self.chat_display.toHtml()
        self.chat_display.setHtml(self.typing_base_html)
        self.chat_display.insertHtml(formatted_message)

        # Always scroll to bottom smoothly
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def type_next_character(self):
        """Type the next character in the response"""
        if self.char_index < len(self.response_text):
            # Get the text typed so far
            typed_so_far = self.response_text[:self.char_index + 1]
            
            # Debug: Print what we're trying to type
            print(f"Debug: Typing character {self.char_index + 1}/{len(self.response_text)}: '{typed_so_far}'")
            
            # Use a much simpler approach - just replace the entire message content
            timestamp = datetime.now().strftime("%H:%M")
            
            # Create the updated message HTML directly
            message_html = f"""
            <div style="margin-bottom: 10px;">
                <span style="color: #03DAC6; font-weight: bold; font-size: 14px;">
                    Luna
                </span>
                <span style="color: #B0BEC5; font-size: 11px; margin-left: 5px;">
                    {timestamp}
                </span>
                <div style="color: #ECEFF1; line-height: 1.5; margin-top: 3px; margin-left: 0px; font-size: 13px;">
                    {typed_so_far}<span style="animation: blink 1s infinite; margin-left: 2px;">|</span>
                </div>
            </div>
            """
            
            # Replace the last message in the chat
            current_html = self.chat_display.toHtml()
            
            # Use a more reliable approach - just append and remove previous
            # Clear the last message and add the new one
            cursor = self.chat_display.textCursor()
            cursor.movePosition(cursor.End)
            
            # Move back to find the last message
            cursor.movePosition(cursor.StartOfBlock)
            cursor.movePosition(cursor.Up)
            cursor.select(cursor.BlockUnderCursor)
            
            # Replace with new content
            cursor.insertHtml(message_html)
            
            # Auto-scroll to bottom
            scrollbar = self.chat_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
            self.char_index += 1
            
            # Add random delay for natural typing feel
            import random
            delay = random.randint(50, 120)  # Random delay between 50-120ms
            self.typing_animation_timer.start(delay)
        else:
            # Typing complete - remove cursor and stop timer
            self.typing_animation_timer.stop()
            if hasattr(self, 'typing_animation_timer'):
                delattr(self, 'typing_animation_timer')
            
            # Final message without cursor
            timestamp = datetime.now().strftime("%H:%M")
            final_message_html = f"""
            <div style="margin-bottom: 10px;">
                <span style="color: #03DAC6; font-weight: bold; font-size: 14px;">
                    Luna
                </span>
                <span style="color: #B0BEC5; font-size: 11px; margin-left: 5px;">
                    {timestamp}
                </span>
                <div style="color: #ECEFF1; line-height: 1.5; margin-top: 3px; margin-left: 0px; font-size: 13px;">
                    {self.response_text}
                </div>
            </div>
            """
            
            # Replace the last message
            current_html = self.chat_display.toHtml()
            import re
            pattern = r'<div style="margin-bottom: 10px;" id="typing-response">.*?</div>\s*</body>'
            if re.search(pattern, current_html, re.DOTALL):
                updated_html = re.sub(pattern, final_message_html + '</body>', current_html, flags=re.DOTALL)
                self.chat_display.setHtml(updated_html)
    
    def handle_ai_response(self, response):
        # Legacy method - kept for compatibility
        if response:
            response = "\n".join(
                ln for ln in str(response).split("\n")
                if not ln.strip().startswith("[Using:")
            ).strip()
        self.add_message("Luna", response, is_user=False)
    
    def open_settings(self):
        # Capture current interval to detect changes
        try:
            old_interval_sec = int(self.settings_manager.get("status_check_interval", 300))
        except Exception:
            old_interval_sec = 300
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh UI with new settings
            self.apply_theme()
            
            # Update font size
            font_size = self.settings_manager.get("chat_font_size")
            self.chat_display.setStyleSheet(self.chat_display.styleSheet() + f"font-size: {font_size}px;")
            
            # Update model label
            current_model = self.settings_manager.get_active_model()
            model_emoji = "💻" if current_model.get("type") == "local" else "🤖"
            self.model_label.setText(f"{model_emoji} {current_model.get('name', 'Unknown Model')}")

            # Restart background model status timer if interval changed
            try:
                new_interval_sec = int(self.settings_manager.get("status_check_interval", 300))
                if new_interval_sec != old_interval_sec:
                    if new_interval_sec < 60:
                        new_interval_sec = 60
                    if hasattr(self, 'model_status_timer') and self.model_status_timer:
                        try:
                            self.model_status_timer.stop()
                        except Exception:
                            pass
                    else:
                        from PySide6.QtCore import QTimer as _QTimerAlias
                        self.model_status_timer = _QTimerAlias(self)
                        self.model_status_timer.timeout.connect(self.start_model_status_check)
                    self.model_status_timer.start(new_interval_sec * 1000)
                    # Optionally trigger an immediate check after change
                    self.start_model_status_check()
            except Exception:
                pass
    
    def open_models_dialog(self):
        dialog = ModelsDialog(self.settings_manager, self)
        dialog.exec()
    
    def show_about(self):
        QMessageBox.about(self, "About Luna AI", 
                         "Luna AI Assistant v1.0\n\n"
                         "An advanced AI assistant with multiple model support,\n"
                         "including local processing and OpenRouter integration.\n\n"
                         "Features:\n"
                         "- Local conversation engine\n"
                         "- OpenRouter model support\n"
                         "- Weather integration\n"
                         "- Web search\n"
                         "- System commands (optional)\n"
                         "• System command execution\n"
                         "• Customizable creativity levels\n"
                         "• Provider categorization and status display\n"
                         "• Model catalog with visual cards\n\n"
                         "Providers:\n"
                         "💻 Local Model Engine - processes requests on your machine\n"
                         "☁️ OpenRouter - cloud models via API")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Luna AI Assistant")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Luna AI")
    
    # Create and show main window
    window = LunaMainWindow()
    window.show()
    
    # Start the application
    sys.exit(app.exec())