import unittest
from unittest.mock import patch, MagicMock
import ESP_app


class TestESP(unittest.TestCase):

    @patch.object(ESP_app, 'get_live_pv_match_data')
    def test_detect_blind_event_no_data(self, mock_get_data):
        mock_get_data.return_value = None
        result = ESP_app.detect_blind_event('test_host', 'fake_key')
        self.assertIsNone(result)

    @patch.object(ESP_app, 'get_live_pv_match_data')
    def test_detect_blind_event_invalid_data(self, mock_get_data):
        mock_get_data.return_value = "not a dict"
        result = ESP_app.detect_blind_event('test_host', 'fake_key')
        self.assertIsNone(result)

    @patch.object(ESP_app, 'get_live_pv_match_data')
    def test_detect_blind_event_all_players_fortress(self, mock_get_data):
        match_data = {
            'id': 'match123',
            'players': [
                {'uuid': 'player1'},
                {'uuid': 'player2'}
            ],
            'data': {
                'timelines': [
                    {'uuid': 'player1', 'type': 'nether.find_fortress'},
                    {'uuid': 'player2', 'type': 'nether.find_fortress'}
                ]
            }
        }
        mock_get_data.return_value = match_data
        with patch('builtins.print') as mock_print:
            result = ESP_app.detect_blind_event('test_host', 'fake_key')
        self.assertIsNone(result)
        mock_print.assert_any_call("Both players have entered the fort. Aborting insight prediction.")

    @patch.object(ESP_app, 'time')
    @patch.object(ESP_app, 'get_single_eye_spy_prediction')
    @patch.object(ESP_app, 'get_live_pv_match_data')
    def test_detect_blind_event_eligible_players(self, mock_get_data, mock_predictor, mock_time):
        match_data_setup = {
            'id': 'match123',
            'players': [
                {'uuid': 'player1'},
                {'uuid': 'player2'}
            ],
            'data': {
                'timelines': [
                    {'uuid': 'player1', 'type': 'nether.find_fortress'}
                ]
            }
        }
        match_data_blind = {
            'id': 'match123',
            'players': [
                {'uuid': 'player1'},
                {'uuid': 'player2'}
            ],
            'data': {
                'timelines': [
                    {'uuid': 'player1', 'type': 'nether.find_fortress'},
                    {'uuid': 'player2', 'type': 'projectelo.timeline.blind_travel'}
                ]
            }
        }
        mock_get_data.side_effect = [match_data_setup, match_data_blind]
        with patch('builtins.print') as mock_print:
            result = ESP_app.detect_blind_event('test_host', 'fake_key')
        self.assertIsNone(result)
        mock_time.sleep.assert_called()
        mock_predictor.assert_called_once()

    @patch.object(ESP_app, 'time')
    @patch.object(ESP_app, 'get_single_eye_spy_prediction')
    @patch.object(ESP_app, 'get_live_pv_match_data')
    def test_detect_blind_event_all_eligible_processed(self, mock_get_data, mock_predictor, mock_time):
        match_data = {
            'id': 'match123',
            'players': [
                {'uuid': 'player1'},
                {'uuid': 'player2'}
            ],
            'data': {
                'timelines': [
                    {'uuid': 'player1', 'type': 'projectelo.timeline.blind_travel'},
                    {'uuid': 'player2', 'type': 'projectelo.timeline.blind_travel'}
                ]
            }
        }
        mock_get_data.return_value = match_data
        with patch('builtins.print') as mock_print:
            result = ESP_app.detect_blind_event('test_host', 'fake_key')
        self.assertIsNone(result)
        self.assertEqual(mock_predictor.call_count, 2)

    @patch('requests.get')
    def test_get_live_players_no_matches(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {'data': {'liveMatches': []}}
        mock_get.return_value = mock_response
        result = ESP_app.get_live_players()
        self.assertIsNone(result)

    @patch('requests.get')
    @patch('builtins.input', side_effect=['invalid', '1'])
    def test_get_live_players_retry_then_select(self, mock_input, mock_get):
        match_data = {'id': 'm1', 'players': [{'nickname': 'Player1'}, {'nickname': 'Player2'}]}
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'liveMatches': [match_data]
            }
        }
        mock_get.return_value = mock_response
        with patch('builtins.print'):
            participants, selected = ESP_app.get_live_players()
        self.assertEqual(participants, ['Player1', 'Player2'])
        self.assertEqual(selected, match_data)

    @patch('requests.get')
    @patch('builtins.input', side_effect=['1'])
    def test_get_live_players_valid_selection(self, mock_input, mock_get):
        match_data = {'id': 'm1', 'players': [{'nickname': 'Player1'}, {'nickname': 'Player2'}]}
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'liveMatches': [match_data]
            }
        }
        mock_get.return_value = mock_response
        with patch('builtins.print'):
            participants, selected = ESP_app.get_live_players()
        self.assertEqual(participants, ['Player1', 'Player2'])
        self.assertEqual(selected, match_data)


if __name__ == '__main__':
    unittest.main()
