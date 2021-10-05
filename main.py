from fastapi import FastAPI, HTTPException, status, Query
from typing import List, Set, Optional
from pydantic import BaseModel

import database


def try_call_db_method(db: database.Database, method: str, **kwargs):
    try:
        res = getattr(db, method)(**kwargs)
    except database.WrongRequestException as ex:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ex.reason)
    return res


db = database.Database()
app = FastAPI()


@app.post("/add-user", status_code=status.HTTP_201_CREATED, response_model=database.User)
def add_user(user: database.User):
    return try_call_db_method(db, "add_user", user=user)


@app.post("/add-meeting", status_code=status.HTTP_201_CREATED, response_model=database.Meeting,
          response_model_exclude_unset=True)
def add_meeting(meeting: database.Meeting):
    return try_call_db_method(db, "add_meeting", meeting=meeting)


@app.get("/get-meeting", status_code=status.HTTP_200_OK, response_model=database.Meeting,
         response_model_exclude_unset=True)
def get_meeting(meeting_id: database.MeetingId):
    return try_call_db_method(db, "get_meeting", meeting_id=meeting_id)


@app.get("/get-suggested-meetings", status_code=status.HTTP_200_OK, response_model=List[database.Meeting],
         response_model_exclude_unset=True)
def get_suggested_meetings(user_id: database.UserId):
    return try_call_db_method(db, "get_suggested_meetings", user_id=user_id)


class AcceptMeetingBody(BaseModel):
    user_id: database.UserId
    meeting_id: database.MeetingId


@app.put("/accept-meeting", status_code=status.HTTP_200_OK, response_model=database.Meeting,
         response_model_exclude_unset=True)
def accept_meeting(body: AcceptMeetingBody):
    return try_call_db_method(db, "accept_meeting", user_id=body.user_id, meeting_id=body.meeting_id)


DeclineMeetingBody = AcceptMeetingBody


@app.put("/decline-meeting", status_code=status.HTTP_200_OK, response_model=database.Meeting,
         response_model_exclude_unset=True)
def decline_meeting(body: DeclineMeetingBody):
    return try_call_db_method(db, "decline_meeting", user_id=body.user_id, meeting_id=body.meeting_id)


@app.get("/get-accepted-meetings", status_code=status.HTTP_200_OK, response_model=List[database.Meeting],
         response_model_exclude_unset=True)
def get_accepted_meetings(user_id: database.UserId, start: database.Timepoint, end: database.Timepoint):
    return try_call_db_method(db, "get_accepted_meetings", user_id=user_id, start=start, end=end)


class Interval(BaseModel):
    start: database.Timepoint
    end: database.Timepoint

    def __init__(self, start, end):
        super().__init__()
        self.start = start
        self.end = end


@app.get("/get-first-available-interval", status_code=status.HTTP_200_OK, response_model=Optional[Interval])
def get_first_available_interval(duration: database.Duration,
                                 start: database.Timepoint, end: database.Timepoint,
                                 user_ids: Set[database.UserId] = Query(set())):
    first_available_start = try_call_db_method(db, "get_first_available_start",
                                               user_ids=user_ids, duration=duration,
                                               start=start, end=end)
    if not first_available_start:
        return None
    return Interval(first_available_start, first_available_start + duration)




