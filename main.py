from fastapi import FastAPI, HTTPException, status, Query
import uvicorn

import database
from my_types import *


def try_call_db_method(db: database.Database, method: str, **kwargs):
    try:
        res = getattr(db, method)(**kwargs)
    except database.WrongRequestException as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ex.reason)
    return res


db = database.Database()
app = FastAPI()


@app.post("/add-user", status_code=status.HTTP_201_CREATED, response_model=User,
          response_model_exclude_unset=True)
def add_user(user: User):
    return try_call_db_method(db, "add_user", user=user)


@app.post("/add-meeting", status_code=status.HTTP_201_CREATED, response_model=Meeting,
          response_model_exclude_unset=True)
def add_meeting(meeting: Meeting):
    if meeting.start >= meeting.end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid meeting interval")
    if meeting.period and meeting.period <= meeting.duration():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Meeting period is shorter than meeting duration")

    return try_call_db_method(db, "add_meeting", meeting=meeting)


@app.get("/get-meeting-info", status_code=status.HTTP_200_OK, response_model=Meeting,
         response_model_exclude_unset=True)
def get_meeting_info(meeting_id: MeetingId):
    return try_call_db_method(db, "get_meeting", meeting_id=meeting_id)


@app.get("/get-suggested-meetings", status_code=status.HTTP_200_OK, response_model=List[Meeting],
         response_model_exclude_unset=True)
def get_suggested_meetings(username: Username):
    return try_call_db_method(db, "get_suggested_meetings", username=username)


@app.put("/accept-meeting", status_code=status.HTTP_200_OK, response_model=Meeting,
         response_model_exclude_unset=True)
def accept_meeting(body: AcceptMeetingBody):
    return try_call_db_method(db, "accept_meeting", username=body.username, meeting_id=body.meeting_id)


@app.put("/decline-meeting", status_code=status.HTTP_200_OK, response_model=Meeting,
         response_model_exclude_unset=True)
def decline_meeting(body: DeclineMeetingBody):
    return try_call_db_method(db, "decline_meeting", username=body.username, meeting_id=body.meeting_id)


@app.get("/get-accepted-meetings", status_code=status.HTTP_200_OK, response_model=List[Meeting],
         response_model_exclude_unset=True)
def get_accepted_meetings(username: Username, start: Timepoint, end: Timepoint):
    if start >= end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid time interval")
    return try_call_db_method(db, "get_accepted_meetings", username=username, start=start, end=end)


@app.get("/get-first-available-interval", status_code=status.HTTP_200_OK, response_model=TimeInterval)
def get_first_available_interval(duration: Duration,
                                 search_until: Timepoint,
                                 usernames: Set[Username] = Query(...)):
    start = datetime.datetime.now()

    if search_until <= start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid searching upper bound")

    first_available_start = try_call_db_method(db, "get_first_available_start",
                                               usernames=usernames, duration=duration,
                                               start=start, end=search_until)
    if not first_available_start:
        return TimeInterval(start=None, end=None)

    return TimeInterval(start=first_available_start, end=first_available_start + duration)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
