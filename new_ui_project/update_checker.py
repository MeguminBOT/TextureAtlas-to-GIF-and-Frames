import requests

class UpdateChecker:
    def __init__(self, current_version):
        self.current_version = current_version
        self.latest_version = None

    def check_for_updates(self):
        try:
            response = requests.get('https://raw.githubusercontent.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/main/latestVersion.txt')
            self.latest_version = response.text.strip()

            if self.latest_version > self.current_version:
                print("Update available.")
                return True
            else:
                print("You are using the latest version of the application.")
                return False
        except requests.exceptions.RequestException as err:
            print("No internet connection or something went wrong, could not check for updates.")
            print("Error details:", err)
            return False