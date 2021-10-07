from fastapi.testclient import TestClient
import datetime

from main import app

client = TestClient(app)

global_start = datetime.datetime.now() + datetime.timedelta(minutes=10)
meeting_duration = datetime.timedelta(minutes=30)


def test_add_users():
    for num in range(1, 4):
        body = {"username": f"test_user_{num}"}
        response = client.post("/add-user", json=body)
        assert response.status_code == 201
        assert response.json() == body


def test_add_meeting():
    end = global_start + meeting_duration
    body = {
        "start": global_start.isoformat(),
        "end": end.isoformat(),
        "creator_username": "test_user_1",
        "invited": [
            "test_user_2",
            "test_user_3"
        ]
    }
    response = client.post("/add-meeting", json=body)
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["start"] == body["start"]
    assert response_json["end"] == body["end"]
    assert response_json["creator_username"] == "test_user_1"
    assert sorted(response_json["invited"]) == sorted(body["invited"])
    assert response_json["id"] == 0
    assert response_json["participants"] == ["test_user_1"]


def test_get_suggested_meetings():
    for username in ["test_user_2", "test_user_3"]:
        response = client.get('/get-suggested-meetings', params={"username": username})
        assert response.status_code == 200
        response_json = response.json()
        assert len(response_json) == 1
        assert response_json[0]["id"] == 0


def test_accept_meeting():
    body = {"username": "test_user_2", "meeting_id": 0}
    response = client.put("/accept-meeting", json=body)
    assert response.status_code == 200
    response_json = response.json()
    assert sorted(response_json["participants"]) == ["test_user_1", "test_user_2"]
    assert response_json["invited"] == ["test_user_3"]


def test_decline_meeting():
    body = {"username": "test_user_3", "meeting_id": 0}
    response = client.put("/decline-meeting", json=body)
    assert response.status_code == 200
    response_json = response.json()
    assert sorted(response_json["participants"]) == ["test_user_1", "test_user_2"]
    assert response_json["invited"] == []


def test_get_meeting_info():
    response = client.get('/get-meeting-info', params={"meeting_id": 0})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["start"] == global_start.isoformat()
    assert response_json["end"] == (global_start + meeting_duration).isoformat()
    assert response_json["creator_username"] == "test_user_1"
    assert sorted(response_json["invited"]) == []
    assert response_json["id"] == 0
    assert sorted(response_json["participants"]) == ["test_user_1", "test_user_2"]


def test_add_regular_meeting():
    new_start = global_start + meeting_duration + datetime.timedelta(minutes=30)
    new_end = new_start + meeting_duration
    period = datetime.timedelta(hours=2)
    body = {
        "start": new_start.isoformat(),
        "end": new_end.isoformat(),
        "creator_username": "test_user_2",
        "invited": [
            "test_user_3"
        ],
        "period": period.seconds
    }
    response = client.post("/add-meeting", json=body)
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["start"] == body["start"]
    assert response_json["end"] == body["end"]
    assert response_json["creator_username"] == "test_user_2"
    assert sorted(response_json["invited"]) == sorted(body["invited"])
    assert response_json["id"] == 1
    assert response_json["participants"] == ["test_user_2"]


def test_accept_regular_meeting():
    body = {"username": "test_user_3", "meeting_id": 1}
    response = client.put("/accept-meeting", json=body)
    assert response.status_code == 200
    response_json = response.json()
    assert sorted(response_json["participants"]) == ["test_user_2", "test_user_3"]


def test_get_accepted_meetings():
    search_start = global_start
    search_end = (global_start + meeting_duration) + datetime.timedelta(minutes=90)
    response = client.get('get-accepted-meetings',
                          params={"username": "test_user_2",
                                  "start": search_start.isoformat(),
                                  "end": search_end.isoformat()})
    assert response.status_code == 200
    response_json = response.json()
    # only two meetings occurs in this time interval: single meeting with id 0
    # and the first copy of regular meeting with id 1
    assert len(response_json) == 2
    assert {body["id"] for body in response_json} == {0, 1}


def test_get_accepted_meetings_2():
    search_start = global_start
    search_end = (global_start + meeting_duration) + datetime.timedelta(hours=3)
    response = client.get('get-accepted-meetings',
                          params={"username": "test_user_2",
                                  "start": search_start.isoformat(),
                                  "end": search_end.isoformat()})
    assert response.status_code == 200
    response_json = response.json()
    # three meetings occurs in this time interval: single meeting with id 0
    # and two copies of regular meeting with id 1
    assert len(response_json) == 3
    assert sorted([body["id"] for body in response_json]) == [0, 1, 1]


def test_get_first_available_interval():
    # some timepoint far away enough from global start
    until = global_start + datetime.timedelta(hours=5)
    duration = datetime.timedelta(minutes=30)
    response = client.get('/get-first-available-interval',
                          params={"usernames": ["test_user_1", "test_user_2", "test_user_3"],
                                  "search_until": until.isoformat(),
                                  "duration": duration.seconds})
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["start"] == (global_start + meeting_duration).isoformat()
    assert response_json["end"] == (global_start + meeting_duration + duration).isoformat()


def test_get_first_available_interval_2():
    # some timepoint far away enough from global start
    until = global_start + datetime.timedelta(hours=5)
    # now create big enough duration so the only available interval is after the second meeting
    # (which is the first copy of the regular meeting with id 1)
    duration = datetime.timedelta(minutes=50)
    response = client.get('/get-first-available-interval',
                          params={"usernames": ["test_user_1", "test_user_2", "test_user_3"],
                                  "search_until": until.isoformat(),
                                  "duration": duration.seconds})
    assert response.status_code == 200
    response_json = response.json()
    expected_start = global_start + meeting_duration + datetime.timedelta(minutes=30) + meeting_duration
    assert response_json["start"] == expected_start.isoformat()
    assert response_json["end"] == (expected_start + duration).isoformat()


# test some errors
def test_wrong_meeting_id():
    response = client.get('/get-meeting-info', params={"meeting_id": 3})
    assert response.status_code == 400


def test_wrong_username():
    search_start = global_start
    search_end = (global_start + meeting_duration) + datetime.timedelta(minutes=90)
    response = client.get('get-accepted-meetings',
                          params={"username": "spounchebob",
                                  "start": search_start.isoformat(),
                                  "end": search_end.isoformat()})
    assert response.status_code == 400


def test_invalid_time_interval():
    end = global_start - meeting_duration
    body = {
        "start": global_start.isoformat(),
        "end": end.isoformat(),
        "creator_username": "test_user_1",
        "invited": [
            "test_user_2",
            "test_user_3"
        ]
    }
    response = client.post("/add-meeting", json=body)
    assert response.status_code == 400

