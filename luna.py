import speech_recognition as sr
import pyttsx3
import requests
import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import ai_api
import json

class LunaCommandLine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.settings = self.load_settings()
        self.setup_voice()
        
        # Initialize AI creativity from settings
        ai_creativity = self.settings.get('ai_creativity', 0.7)
        ai_api.set_ai_creativity(ai_creativity)
        
    def load_settings(self):
        """Load settings from file or use defaults."""
        settings_file = "luna_settings.json"
        default_settings = {
            "voice_rate": 200,
            "voice_volume": 0.9,
            "voice_id": 0,
            "recognition_timeout": 5,
            "phrase_timeout": 1,
            "ai_creativity": 0.7,  # Added AI creativity setting
            "default_city": ""
        }
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    loaded = json.load(f)
                    settings = default_settings.copy()
                    settings.update(loaded)
                    return settings
        except Exception:
            pass
        return default_settings
    
    def setup_voice(self):
        """Configure text-to-speech settings."""
        voices = self.engine.getProperty('voices')
        if voices and len(voices) > self.settings.get('voice_id', 0):
            self.engine.setProperty('voice', voices[self.settings.get('voice_id', 0)].id)
        
        self.engine.setProperty('rate', self.settings.get('voice_rate', 200))
        self.engine.setProperty('volume', self.settings.get('voice_volume', 0.9))

    def listen(self):
        """Capture voice input and convert it to text."""
        with sr.Microphone() as source:
            print("🎤 Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=self.settings.get('recognition_timeout', 5),
                    phrase_time_limit=self.settings.get('phrase_timeout', 1)
                )
                command = self.recognizer.recognize_google(audio)
                print(f"👤 You said: {command}")
                return command.lower()
            except sr.WaitTimeoutError:
                print("⏰ Listening timeout - no speech detected")
                return None
            except sr.UnknownValueError:
                print("❌ Sorry, I didn't catch that.")
                return None
            except sr.RequestError as e:
                print(f"❌ Speech recognition error: {e}")
                return None

    def speak(self, text):
        """Convert text to speech and output it."""
        print(f"🤖 Luna: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def get_time(self):
        """Get current time."""
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    def get_date(self):
        """Get current date."""
        current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return f"Today is {current_date}."

    def show_help(self):
        """Display available commands."""
        help_text = """
📋 LUNA STREAMLINED EDITION - AVAILABLE COMMANDS:

🤖 LOCAL AI CONVERSATION:
    • Chat naturally with Luna (instant responses!)
    • Ask questions and have conversations
    • No internet needed for basic chat

🌤️  WEATHER:
    • "weather" - Current weather
    • "weather in [city]" - Weather for specific city

🔍 WEB SEARCH:
    • "search for [topic]"
    • "what is [something]"
    • "who is [person]"
    • "find information about [topic]"

⚙️  SYSTEM COMMANDS:
    • "open notepad" - Open text editor
    • "open calculator" - Open calculator  
    • "open browser" - Open web browser
    • "open file manager" - Open file explorer
    • "volume up/down/mute" - Control volume
    • "screenshot" - Take screenshot

🕐 TIME & DATE:
    • "time" - Current time
    • "date" - Current date

🔧 SETTINGS:
    • "settings" - Configure Luna
    • "creativity" - Adjust AI response creativity
    • "help" - Show this help
    • "exit/quit" - Exit Luna

✨ NEW FEATURES:
    • Much faster conversation responses
    • No API tokens or keys needed for chat
    • Adjustable AI creativity levels
    • Improved conversation patterns
        """
        print(help_text)
        return "Here are the available commands for the streamlined Luna."

    def configure_creativity(self):
        """Configure AI creativity level."""
        print("\n🎨 AI CREATIVITY SETTINGS")
        print("=" * 40)
        
        current_creativity = self.settings.get('ai_creativity', 0.7)
        print(f"Current creativity level: {current_creativity}")
        print("\nCreativity levels:")
        print("• 0.1-0.3: Conservative, predictable responses")
        print("• 0.4-0.7: Balanced variety and consistency")
        print("• 0.8-1.0: Maximum creativity and response variety")
        
        try:
            new_creativity = input("\nEnter new creativity level (0.1-1.0, or press Enter to keep current): ")
            if new_creativity.strip():
                try:
                    creativity = float(new_creativity)
                    if 0.1 <= creativity <= 1.0:
                        self.settings['ai_creativity'] = creativity
                        ai_api.set_ai_creativity(creativity)
                        
                        # Save to file
                        with open("luna_settings.json", 'w') as f:
                            json.dump(self.settings, f, indent=2)
                        
                        print(f"✅ AI creativity level set to {creativity}")
                        return f"AI creativity updated to {creativity}. You should notice different response patterns now!"
                    else:
                        print("❌ Creativity level must be between 0.1 and 1.0")
                        return "Please enter a valid creativity level."
                except ValueError:
                    print("❌ Invalid creativity value.")
                    return "Please enter a valid number."
        except Exception as e:
            print(f"❌ Error configuring creativity: {e}")
            return "There was an error updating creativity settings."
        
        return "Creativity level unchanged."

    def configure_settings(self):
        """Interactive settings configuration."""
        print("\n🔧 LUNA SETTINGS")
        print("=" * 40)
        
        try:
            # Voice settings
            print(f"Current voice rate: {self.settings['voice_rate']}")
            new_rate = input("Enter new voice rate (150-300, or press Enter to keep current): ")
            if new_rate.strip() and new_rate.isdigit():
                rate = int(new_rate)
                if 150 <= rate <= 300:
                    self.settings['voice_rate'] = rate
                    self.engine.setProperty('rate', rate)

            print(f"Current voice volume: {self.settings['voice_volume']}")
            new_volume = input("Enter new voice volume (0.0-1.0, or press Enter to keep current): ")
            if new_volume.strip():
                try:
                    volume = float(new_volume)
                    if 0.0 <= volume <= 1.0:
                        self.settings['voice_volume'] = volume
                        self.engine.setProperty('volume', volume)
                except ValueError:
                    print("Invalid volume value.")

            # Recognition settings
            print(f"Current recognition timeout: {self.settings['recognition_timeout']} seconds")
            new_timeout = input("Enter new recognition timeout (1-10 seconds, or press Enter to keep current): ")
            if new_timeout.strip() and new_timeout.isdigit():
                timeout = int(new_timeout)
                if 1 <= timeout <= 10:
                    self.settings['recognition_timeout'] = timeout
            
            # Default city
            print(f"Current default city: {self.settings.get('default_city', 'Beavercreek,Ohio')}")
            new_city = input("Enter new default city (City,State format, or press Enter to keep current): ")
            if new_city.strip():
                self.settings['default_city'] = new_city.strip()

            # Save settings
            with open("luna_settings.json", 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            print("✅ Settings saved successfully!")
            return "Settings have been updated."
            
        except Exception as e:
            print(f"❌ Error configuring settings: {e}")
            return "There was an error updating settings."

    def process_command(self, command):
        """Process the user's command and respond accordingly."""
        if not command:
            return True
            
        command = command.lower().strip()
        
        # Built-in commands
        if command in ["exit", "quit", "goodbye", "bye"]:
            self.speak("Goodbye! Have a great day!")
            return False
        
        elif command in ["help", "commands", "what can you do"]:
            response = self.show_help()
            self.speak(response)
            return True
        
        elif command in ["settings", "configure", "config"]:
            response = self.configure_settings()
            self.speak(response)
            return True
        
        elif command in ["creativity", "creative", "ai creativity"]:
            response = self.configure_creativity()
            self.speak(response)
            return True
        
        elif "time" in command:
            response = self.get_time()
            self.speak(response)
            return True
        
        elif "date" in command:
            response = self.get_date()
            self.speak(response)
            return True
        
        # Use streamlined AI API for all other commands
        # This now includes fast local conversation!
        else:
            try:
                print("🔄 Processing your request...")
                response = ai_api.call_ai_api(command)
                self.speak(response)
            except Exception as e:
                error_msg = "I'm having trouble processing that request right now."
                print(f"❌ Error: {e}")
                self.speak(error_msg)
        
        return True

    def text_mode(self):
        """Run Luna in text-only mode."""
        creativity_level = self.settings.get('ai_creativity', 0.7)
        print(f"💬 TEXT MODE - AI Creativity: {creativity_level}")
        print("Type your commands (or 'voice' to switch to voice mode)")
        print("Type 'help' for available commands, 'exit' to quit")
        
        while True:
            try:
                command = input("\n👤 You: ").strip()
                if command.lower() == "voice":
                    print("🎤 Switching to voice mode...")
                    return self.voice_mode()
                
                if not self.process_command(command):
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def voice_mode(self):
        """Run Luna in voice mode."""
        creativity_level = self.settings.get('ai_creativity', 0.7)
        print(f"🎤 VOICE MODE - AI Creativity: {creativity_level}")
        self.speak(f"Voice mode activated with creativity level {creativity_level}. I'm listening for your commands.")
        
        while True:
            try:
                command = self.listen()
                
                if command:
                    if "text mode" in command:
                        print("💬 Switching to text mode...")
                        self.speak("Switching to text mode.")
                        return self.text_mode()
                    
                    if not self.process_command(command):
                        break
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                self.speak("Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def main(self):
        """Main loop to run the Luna assistant."""
        print("🚀 LUNA STREAMLINED EDITION")
        print("=" * 50)
        print("✨ Features: Fast Local AI • No API Keys • Instant Chat")
        
        # Choose mode
        while True:
            mode = input("Choose mode - (v)oice, (t)ext, or (q)uit: ").lower().strip()
            
            if mode in ['q', 'quit', 'exit']:
                print("👋 Goodbye!")
                break
            elif mode in ['v', 'voice']:
                self.voice_mode()
                break
            elif mode in ['t', 'text']:
                self.text_mode()
                break
            else:
                print("❌ Invalid choice. Please enter 'v' for voice, 't' for text, or 'q' to quit.")

if __name__ == "__main__":
    try:
        luna = LunaCommandLine()
        luna.main()
    except Exception as e:
        print(f"❌ Failed to start Luna: {e}")
        print("Make sure you have installed the required packages:")
        print("pip install speechrecognition pyttsx3 requests pyaudio duckduckgo-search PySide6")