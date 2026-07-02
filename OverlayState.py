# overlay_state.py

class OverlayState:
    def __init__(self):
        self.data = {
            "visible": False,
            "type": None,
            "title": "",
            "players": []
        }

    def update(self, new_data):
        self.data.update(new_data)

    def get(self):
        return self.data


overlay = OverlayState()