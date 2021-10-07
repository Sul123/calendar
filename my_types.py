import datetime
from typing import List, Dict, Set, Optional
from pydantic import BaseModel

Username = str
MeetingId = int
Timepoint = datetime.datetime
Duration = datetime.timedelta


class TimeInterval(BaseModel):
    start: Optional[Timepoint]
    end: Optional[Timepoint]


class User(BaseModel):
    username: Username
    info: Optional[str]


class Meeting(BaseModel):
    id: Optional[MeetingId] = None
    start: Timepoint
    end: Timepoint
    creator_username: Username
    invited: Set[str]
    participants: Optional[Set[str]] = set()
    period: Optional[Duration] = None

    def duration(self) -> Duration:
        return self.end - self.start


class AcceptMeetingBody(BaseModel):
    username: Username
    meeting_id: MeetingId


class DeclineMeetingBody(BaseModel):
    username: Username
    meeting_id: MeetingId
